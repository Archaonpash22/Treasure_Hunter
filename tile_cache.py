"""Local tile cache and proxy for the terrain overlays (LiDAR / DTM hillshades).

Every terrain tile the map requests goes through a tiny HTTP server on 127.0.0.1.
The server builds the real upstream request (WMS, ArcGIS ImageServer or plain XYZ),
stores the answer under  tile_cache/<layer>/<z>/<x>/<y>.png  and serves it from disk
on every later request. Areas you have looked at once therefore keep working without
internet, and a bulk downloader can pre-fill the cache for a map area and zoom range.
"""
import bisect
import collections
import json
import math
import os
import sys
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests
from requests.adapters import HTTPAdapter

import dem_analysis
import dem_shade
from PyQt6.QtCore import QThread, pyqtSignal

ORIGIN_SHIFT = 20037508.342789244  # half the circumference of the Web-Mercator world
TILE_SIZE = 256
USER_AGENT = "TreasureHunter/1.0 (local tile cache)"
# Tiles this small are (nearly) empty images. Outside a layer's coverage that is correct,
# but overloaded WMS servers (e.g. the MASE LiDAR service) sometimes answer a request
# inside the coverage with an empty image too. Such tiles are retried once right away
# and re-checked once they are older than BLANK_RECHECK_SECONDS. Layers that are legitimately
# empty over large areas (e.g. a German state's LiDAR outside the state) set 'retryBlank': False.
BLANK_MAX_BYTES = 1024
BLANK_RECHECK_SECONDS = 24 * 3600


# --------------------------------------------------------------------------- geometry

def tile_bounds_3857(z, x, y, pad_left_px=0):
    """Web-Mercator bbox (minx, miny, maxx, maxy) of a tile, optionally widened to the west."""
    size = 2 * ORIGIN_SHIFT / (2 ** z)
    resolution = size / TILE_SIZE
    minx = -ORIGIN_SHIFT + x * size - pad_left_px * resolution
    maxx = -ORIGIN_SHIFT + (x + 1) * size
    maxy = ORIGIN_SHIFT - y * size
    miny = ORIGIN_SHIFT - (y + 1) * size
    return minx, miny, maxx, maxy


def tile_size_of(layer_info):
    """Pixel size of a layer's tiles: 256, or 512 for WMS layers that set 'tileSize': 512.

    A 512 px tile at map zoom z covers the same area as the 256 px tile (z - 1, x, y), so
    the tile grid of zoom z - 1 is used to address it. Bigger tiles mean far fewer requests
    to slow WMS servers (a 512 px image takes ~1.5x as long as a 256 px one, for 4x the area).
    """
    return int(layer_info.get('options', {}).get('tileSize', TILE_SIZE))


def zoom_shift(tile_size):
    return int(round(math.log2(tile_size / TILE_SIZE)))


def lonlat_to_tile(lon, lat, z):
    n = 2 ** z
    lat = max(min(lat, 85.05112878), -85.05112878)
    x = int((lon + 180.0) / 360.0 * n)
    lat_r = math.radians(lat)
    y = int((1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n)
    return min(max(x, 0), n - 1), min(max(y, 0), n - 1)


def _lonlat_to_tile_float(lon, lat, n):
    lat = max(min(lat, 85.05112878), -85.05112878)
    lat_r = math.radians(lat)
    return ((lon + 180.0) / 360.0 * n,
            (1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n)


def polygon_tile_rows(rings, z):
    """Tiles of zoom z touched by the polygon(s), as {row y: [(x_first, x_last), ...]}.

    rings: list of [[lat, lon], ...] rings (outer rings and holes, even-odd rule).
    Interior tiles come from scanlines through the tile centres, tiles crossed by the border
    from walking every edge. Runs are kept per row so millions of tiles stay cheap to count.
    """
    n = 2 ** z
    crossings = collections.defaultdict(list)
    border = collections.defaultdict(set)
    for ring in rings:
        pts = [_lonlat_to_tile_float(lon, lat, n) for lat, lon in ring]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
            steps = int(max(abs(x1 - x0), abs(y1 - y0)) * 4) + 1
            for i in range(steps + 1):
                t = i / steps
                border[int(y0 + (y1 - y0) * t)].add(int(x0 + (x1 - x0) * t))
            if y0 == y1:
                continue
            lo, hi = (y0, y1) if y0 < y1 else (y1, y0)
            for row in range(math.ceil(lo - 0.5), math.ceil(hi - 0.5)):
                yc = row + 0.5
                crossings[row].append(x0 + (yc - y0) * (x1 - x0) / (y1 - y0))
    rows = {}
    for row in set(crossings) | set(border):
        runs = []
        xs = sorted(crossings.get(row, ()))
        for a, b in zip(xs[0::2], xs[1::2]):
            first, last = math.ceil(a - 0.5), math.floor(b - 0.5)
            if first <= last:
                runs.append((first, last))
        runs.extend((x, x) for x in border.get(row, ()))
        runs.sort()
        merged = []
        for first, last in runs:
            if merged and first <= merged[-1][1] + 1:
                merged[-1] = (merged[-1][0], max(merged[-1][1], last))
            else:
                merged.append((first, last))
        rows[row] = merged
    return rows


def _in_rows(rows, x, y):
    runs = rows.get(y)
    if not runs:
        return False
    i = bisect.bisect_right(runs, (x, float('inf'))) - 1
    return i >= 0 and runs[i][0] <= x <= runs[i][1]


def count_tile_rows(rows):
    return sum(last - first + 1 for runs in rows.values() for first, last in runs)


def tiles_in_bbox(south, west, north, east, z):
    x0, y0 = lonlat_to_tile(west, north, z)
    x1, y1 = lonlat_to_tile(east, south, z)
    for x in range(min(x0, x1), max(x0, x1) + 1):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            yield x, y


def build_upstream_url(layer_info, z, x, y):
    """Reproduce the request the Leaflet page would make for this tile."""
    url = layer_info['url']
    opts = layer_info.get('options', {})
    layer_type = layer_info.get('type')

    size = tile_size_of(layer_info)
    gz = z - zoom_shift(size)  # zoom of the 256 px grid that addresses this tile

    if layer_type == 'arcgis_image':
        minx, miny, maxx, maxy = tile_bounds_3857(gz, x, y)
        params = {
            'f': 'image', 'bbox': f"{minx},{miny},{maxx},{maxy}", 'bboxSR': 3857, 'imageSR': 3857,
            'size': f"{size},{size}", 'format': opts.get('imageFormat', 'png'), 'transparent': 'true'
        }
        if opts.get('renderingRule'):
            params['renderingRule'] = json.dumps(opts['renderingRule'])
        return url.rstrip('/') + '/exportImage?' + urllib.parse.urlencode(params)

    if layer_type == 'arcgis_map':  # ArcGIS MapServer without WMS: /export
        minx, miny, maxx, maxy = tile_bounds_3857(gz, x, y)
        params = {
            'f': 'image', 'bbox': f"{minx},{miny},{maxx},{maxy}", 'bboxSR': 3857, 'imageSR': 3857,
            'size': f"{size},{size}", 'format': opts.get('imageFormat', 'png'), 'transparent': 'false'
        }
        return url.rstrip('/') + '/export?' + urllib.parse.urlencode(params)

    if '{z}' in url:  # plain XYZ / WMTS-REST template
        return (url.replace('{z}', str(z)).replace('{x}', str(x)).replace('{y}', str(y))
                   .replace('{s}', 'a').replace('{r}', ''))

    # WMS, optionally widened to the west so the page can crop a watermark strip away
    crop = int(opts.get('cropLeft', 0)) if layer_type == 'wms_crop' else 0
    minx, miny, maxx, maxy = tile_bounds_3857(gz, x, y, pad_left_px=crop * TILE_SIZE / size)
    version = str(opts.get('version', '1.1.1'))
    # The SRS must come before the bbox: MapServer (e.g. the MASE LiDAR WMS) returns an
    # empty image for some tiles when bbox is listed first. Leaflet uses this order too.
    params = {
        'service': 'WMS', 'request': 'GetMap', 'version': version,
        'layers': opts.get('layers', ''), 'styles': opts.get('styles', ''),
        'format': opts.get('format', 'image/png'),
        'transparent': 'true' if opts.get('transparent', True) else 'false',
        'width': size + crop, 'height': size,
        'crs' if version == '1.3.0' else 'srs': 'EPSG:3857',
        'bbox': f"{minx},{miny},{maxx},{maxy}",
    }
    if url.endswith('?') or url.endswith('&'):
        sep = ''
    else:
        sep = '&' if '?' in url else '?'
    return url + sep + urllib.parse.urlencode(params)


# --------------------------------------------------------------------------- cache

class TileCache:
    def __init__(self, terrain_data, cache_dir):
        self.layers = {}
        self.outlines = {}
        for country in terrain_data.values():
            for key, info in country.get('layers', {}).items():
                self.layers.setdefault(key, info)
            self.outlines.update(country.get('outlines', {}))
        self._clip_rows = {}
        self._clip_lock = threading.Lock()
        self._heights = None   # height tile source of the analysis layers, created on first use
        self.cache_dir = cache_dir
        self.offline = False
        self.stats = {'hits': 0, 'network': 0, 'errors': 0}
        self.last_errors = collections.deque(maxlen=30)
        self._stats_lock = threading.Lock()
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT
        adapter = HTTPAdapter(pool_connections=8, pool_maxsize=16)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    def _count(self, name):
        with self._stats_lock:
            self.stats[name] += 1

    def _fail(self, key, z, x, y, reason):
        with self._stats_lock:
            self.stats['errors'] += 1
            self.last_errors.append(f"{key} {z}/{x}/{y}: {reason}")
        return None, None, reason

    def clip_rows(self, codes, z):
        """polygon_tile_rows() of the states in codes at grid zoom z (cached)."""
        cache_key = (tuple(codes), z)
        with self._clip_lock:
            rows = self._clip_rows.get(cache_key)
        if rows is None:
            rings = [ring for code in codes for ring in self.outlines.get(code, [])]
            rows = polygon_tile_rows(rings, z)
            with self._clip_lock:
                self._clip_rows[cache_key] = rows
        return rows

    def path_for(self, key, z, x, y):
        size = tile_size_of(self.layers.get(key, {}))
        folder = key if size == TILE_SIZE else f"{key}@{size}"  # different tile grid, own folder
        return os.path.join(self.cache_dir, folder, str(z), str(x), f"{y}.png")

    def has(self, key, z, x, y):
        return os.path.isfile(self.path_for(key, z, x, y))

    @staticmethod
    def _content_type(data):
        return 'image/jpeg' if data[:2] == b'\xff\xd8' else 'image/png'

    def get_tile(self, key, z, x, y):
        """Return (bytes, content_type, source). bytes is None when the tile is unavailable."""
        path = self.path_for(key, z, x, y)
        cached = None
        if os.path.isfile(path):
            try:
                with open(path, 'rb') as f:
                    cached = f.read()
                stale_blank = (len(cached) <= BLANK_MAX_BYTES and not self.offline
                               and time.time() - os.path.getmtime(path) > BLANK_RECHECK_SECONDS)
            except OSError:
                cached, stale_blank = None, False
            if cached is not None and not stale_blank:
                self._count('hits')
                return cached, self._content_type(cached), 'cache'
        if self.offline:
            return None, None, 'offline mode, tile not cached'
        info = self.layers.get(key)
        if not info:
            return None, None, f'unknown layer {key}'
        if info.get('type') in dem_shade.DEM_TYPES:
            return self._get_dem_tile(key, info, z, x, y, path, cached)
        if info.get('type') == 'dem_analysis':
            return self._get_analysis_tile(key, info, z, x, y, path)
        url = build_upstream_url(info, z, x, y)
        retry_blank = info.get('options', {}).get('retryBlank', True)
        for attempt in range(2):
            try:
                response = self.session.get(url, timeout=(10, 90))
            except requests.RequestException as exc:
                response, error = None, str(exc)
            else:
                content_type = response.headers.get('Content-Type', '')
                error = None
                if response.status_code != 200 or not content_type.startswith('image/'):
                    error = f'upstream {response.status_code} {content_type[:40]}'
            if error or len(response.content) > BLANK_MAX_BYTES or attempt or not retry_blank:
                break
            time.sleep(1)  # empty image: give the server one more try
        if error:
            if cached is not None:  # keep serving the old (empty) tile rather than nothing
                return cached, self._content_type(cached), 'cache'
            return self._fail(key, z, x, y, error)
        self._store(path, response.content)
        self._count('network')
        return response.content, content_type.split(';')[0], 'network'

    def _get_dem_tile(self, key, info, z, x, y, path, cached):
        """Fetch heights for the tile and shade them locally (see dem_shade.py)."""
        if not dem_shade.available():
            return self._fail(key, z, x, y, 'numpy/Pillow fehlen (pip install -r requirements.txt)')
        size = tile_size_of(info)
        url, bbox, res = dem_shade.request_url(info, z - zoom_shift(size), x, y, size)
        try:
            response = self.session.get(url, timeout=(10, 120))
            if response.status_code != 200:
                raise ValueError(f'upstream {response.status_code}')
            data = dem_shade.shade(response.content, bbox, res, size, info.get('options', {}),
                                   terrarium=info.get('type') == 'dem_terrarium')
        except Exception as exc:  # network errors, error XML instead of a TIFF, broken images
            if cached is not None:
                return cached, self._content_type(cached), 'cache'
            return self._fail(key, z, x, y, str(exc)[:120])
        self._store(path, data)
        self._count('network')
        return data, 'image/jpeg', 'network'

    def _get_analysis_tile(self, key, info, z, x, y, path):
        """Local relief / multi-hillshade / sky-view / slope from height tiles (see dem_analysis.py)."""
        if not dem_analysis.available():
            return self._fail(key, z, x, y, 'numpy/Pillow fehlen (pip install -r requirements.txt)')
        if self._heights is None:
            self._heights = dem_analysis.HeightSource(info['url'], os.path.join(self.cache_dir, '_heights'), self.session)
        try:
            data = dem_analysis.tile_jpeg(info['options']['analysis'], self._heights, z - 1, x, y)
        except Exception as exc:
            return self._fail(key, z, x, y, str(exc)[:120])
        if data is None:
            return None, None, 'keine Höhendaten'
        self._store(path, data)
        self._count('network')
        return data, 'image/jpeg', 'network'

    def _store(self, path, data):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.{threading.get_ident()}.tmp"
        with open(tmp, 'wb') as f:
            f.write(data)
        os.replace(tmp, path)

    def summary(self):
        per_layer = {}
        total_files = 0
        total_bytes = 0
        if os.path.isdir(self.cache_dir):
            for key in os.listdir(self.cache_dir):
                layer_dir = os.path.join(self.cache_dir, key)
                if not os.path.isdir(layer_dir):
                    continue
                files = 0
                size = 0
                for root, _dirs, names in os.walk(layer_dir):
                    for name in names:
                        if name.endswith('.png'):
                            files += 1
                            try:
                                size += os.path.getsize(os.path.join(root, name))
                            except OSError:
                                pass
                per_layer[key] = {'tiles': files, 'bytes': size}
                total_files += files
                total_bytes += size
        with self._stats_lock:
            session = dict(self.stats)
            last_errors = list(self.last_errors)
        return {'cache_dir': self.cache_dir, 'tiles': total_files, 'bytes': total_bytes,
                'layers': per_layer, 'offline': self.offline, 'session': session,
                'last_errors': last_errors}


# --------------------------------------------------------------------------- HTTP proxy

class _TileHandler(BaseHTTPRequestHandler):
    cache = None  # set on the generated subclass
    protocol_version = 'HTTP/1.1'

    def log_message(self, *_args):  # keep the console quiet
        pass

    def _send(self, status, body, content_type, extra_headers=()):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        for name, value in extra_headers:
            self.send_header(name, value)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (ConnectionError, OSError):
            pass

    def do_GET(self):
        parts = self.path.split('?')[0].strip('/').split('/')
        if parts == ['status']:
            self._send(200, json.dumps(self.cache.summary()).encode('utf-8'), 'application/json',
                       [('Cache-Control', 'no-store')])
            return
        if len(parts) == 5 and parts[0] == 'tile':
            try:
                key = parts[1]
                z, x = int(parts[2]), int(parts[3])
                y = int(parts[4].rsplit('.', 1)[0])
            except ValueError:
                self._send(400, b'bad tile address', 'text/plain')
                return
            data, content_type, source = self.cache.get_tile(key, z, x, y)
            if data is None:
                self._send(404, source.encode('utf-8', 'replace'), 'text/plain', [('Cache-Control', 'no-store')])
                return
            # CORS lets the page read tile pixels on a canvas (layers with 'whiteToAlpha').
            self._send(200, data, content_type, [('Cache-Control', 'max-age=3600'), ('X-Tile-Source', source),
                                                 ('Access-Control-Allow-Origin', '*')])
            return
        self._send(404, b'not found', 'text/plain')


class _QuietThreadingServer(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        # The browser aborts tile requests whenever the map moves; that is not an error.
        exc = sys.exc_info()[1]
        if isinstance(exc, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)


class TileCacheServer:
    """Runs the proxy on several free local ports (daemon threads), all sharing one cache.

    Browsers open at most ~6 connections per host:port. With every terrain layer going
    through a single local endpoint that would throttle tile loading badly, so the page
    spreads its requests over `ports` like map tile "subdomains".
    """

    def __init__(self, terrain_data, cache_dir, port_count=4):
        self.cache = TileCache(terrain_data, cache_dir)
        handler = type('TileHandler', (_TileHandler,), {'cache': self.cache})
        self.host = '127.0.0.1'
        self._servers = [_QuietThreadingServer((self.host, 0), handler) for _ in range(max(1, port_count))]
        self.ports = [srv.server_address[1] for srv in self._servers]
        self.port = self.ports[0]
        self.base_url = f"http://{self.host}:{self.port}"
        self._threads = [threading.Thread(target=srv.serve_forever, name=f'tile-cache-{srv.server_address[1]}', daemon=True)
                         for srv in self._servers]

    @property
    def proxy_info(self):
        """What the map page needs to build tile URLs: host plus the list of ports."""
        return {'host': self.host, 'ports': self.ports}

    def start(self):
        for thread in self._threads:
            thread.start()

    def stop(self):
        for srv in self._servers:
            srv.shutdown()
            srv.server_close()


# --------------------------------------------------------------------------- bulk download

def plan_download(cache, bbox, stacks, min_zoom, max_zoom):
    """List the (layer, z, x, y) tiles needed for bbox=(south, west, north, east).

    stacks maps a zoom level (int or str) to the layers the map would show there: a layer key, or
    [key, codes] when the page cuts the layer to fewer regions than its 'clipTo' (regions switched
    off, or the base relief only filling gaps). Each layer is clipped to its own 'bounds' option and
    to those region polygons, so nothing is fetched outside coverage.
    """
    south, west, north, east = bbox
    jobs = []
    seen = set()
    for z in range(min_zoom, max_zoom + 1):
        keys = stacks.get(z) or stacks.get(str(z)) or []
        for entry in keys:
            key, clip = (entry[0], entry[1]) if isinstance(entry, (list, tuple)) else (entry, None)
            info = cache.layers.get(key)
            if not info:
                continue
            # Above maxNativeZoom the map enlarges tiles of that zoom instead of loading new ones.
            native = info.get('options', {}).get('maxNativeZoom')
            tz = min(z, native) if native is not None else z
            s, w, n, e = south, west, north, east
            layer_bounds = info.get('options', {}).get('bounds')
            if layer_bounds:
                (bs, bw), (bn, be) = layer_bounds
                s, w, n, e = max(s, bs), max(w, bw), min(n, bn), min(e, be)
                if s >= n or w >= e:
                    continue
            gz = tz - zoom_shift(tile_size_of(info))
            clip = clip or info.get('options', {}).get('clipTo')
            rows = cache.clip_rows(clip, gz) if clip else None
            for x, y in tiles_in_bbox(s, w, n, e, gz):
                if rows is not None and not _in_rows(rows, x, y):
                    continue  # tile does not touch the layer's state; the page never requests it
                job = (key, tz, x, y)
                if job not in seen:
                    seen.add(job)
                    jobs.append(job)
    return jobs


class TileDownloadThread(QThread):
    progress = pyqtSignal(int, int, int)      # done, total, failed
    finished_summary = pyqtSignal(str)

    def __init__(self, cache, jobs, workers=6, parent=None):
        super().__init__(parent)
        self.cache = cache
        self.jobs = jobs
        self.workers = workers
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def _fetch(self, job):
        if self._stop.is_set():
            return None
        key, z, x, y = job
        if self.cache.has(key, z, x, y):
            return True
        data, _ctype, _source = self.cache.get_tile(key, z, x, y)
        return data is not None

    def run(self):
        total = len(self.jobs)
        done = failed = 0
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            for ok in pool.map(self._fetch, self.jobs):
                if ok is None:
                    break
                done += 1
                if not ok:
                    failed += 1
                if done % 5 == 0 or done == total:
                    self.progress.emit(done, total, failed)
        if self._stop.is_set():
            self.finished_summary.emit(f"Download abgebrochen: {done}/{total} Kacheln verarbeitet, {failed} fehlgeschlagen.")
        else:
            self.finished_summary.emit(f"Download fertig: {done} Kacheln, {failed} fehlgeschlagen.")
