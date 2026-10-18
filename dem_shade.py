"""Hillshade tiles computed locally from raw elevation services.

Some states publish their LiDAR terrain model only as heights (WMS with a float GeoTIFF format, or
WCS), not as a rendered hillshade. For layers of type 'dem_wms' / 'dem_wcs' the tile cache fetches
the heights for a tile plus a one-pixel border, shades them here and stores the result as JPEG.
'dem_terrarium' reads Terrarium-encoded height tiles (Mapterhorn: the states' DGM1 as 512 px WebP,
height = R * 256 + G + B / 256 - 32768); those come without a border, so the edge pixels use
one-sided slopes.
"""
import io
import math
import urllib.parse

try:
    import numpy as np
    from PIL import Image
except ImportError:  # the app still runs, these layers just stay empty
    np = None
    Image = None

ORIGIN_SHIFT = 20037508.342789244
DEM_TYPES = ('dem_wms', 'dem_wcs', 'dem_terrarium')
PAD = 1  # extra pixels on each side so the slope at the tile edge is right
TIFF_PIXEL_SCALE = 33550
TIFF_TIEPOINT = 33922

AZIMUTH = 315.0
ALTITUDE = 45.0


def available():
    return np is not None


def _tile_box(gz, x, y, size, pad):
    """Web-Mercator bbox of a tile on the 256 grid of zoom gz, widened by pad pixels of a size-px tile."""
    span = 2 * ORIGIN_SHIFT / (2 ** gz)
    res = span / size
    minx = -ORIGIN_SHIFT + x * span - pad * res
    maxy = ORIGIN_SHIFT - y * span + pad * res
    return minx, maxy - span - 2 * pad * res, minx + span + 2 * pad * res, maxy, res


def request_url(layer_info, gz, x, y, size):
    """(url, bbox, res) for the heights of a tile with a PAD-pixel border (no border for Terrarium tiles)."""
    opts = layer_info.get('options', {})
    if layer_info.get('type') == 'dem_terrarium':
        # A 512 px tile at grid zoom gz covers the same area as the 256 px tile (gz, x, y).
        minx, miny, maxx, maxy, res = _tile_box(gz, x, y, size, 0)
        url = layer_info['url'].replace('{z}', str(gz)).replace('{x}', str(x)).replace('{y}', str(y))
        return url, (minx, miny, maxx, maxy), res
    minx, miny, maxx, maxy, res = _tile_box(gz, x, y, size, PAD)
    n = (size + 2 * PAD) * int(opts.get('oversample', 1))
    url = layer_info['url']
    if layer_info.get('type') == 'dem_wms':
        version = str(opts.get('version', '1.3.0'))
        params = [('SERVICE', 'WMS'), ('REQUEST', 'GetMap'), ('VERSION', version),
                  ('LAYERS', opts.get('layers', '')), ('STYLES', ''),
                  ('CRS' if version == '1.3.0' else 'SRS', 'EPSG:3857'),
                  ('BBOX', f'{minx},{miny},{maxx},{maxy}'), ('WIDTH', n), ('HEIGHT', n),
                  ('FORMAT', opts.get('demFormat', 'image/tiff'))]
    else:
        coverage = opts['coverage']
        # Coarser pyramid levels where the tile's pixels are bigger than theirs (much faster).
        for factor in sorted(opts.get('pyramid', {}), reverse=True):
            if res / int(opts.get('oversample', 1)) >= factor * opts.get('demResolution', 1.0):
                coverage = opts['pyramid'][factor]
                break
        ex, ny = opts.get('subsetAxes', ['x', 'y'])
        sx, sy = opts.get('scaleAxes', [ex, ny])
        crs = 'http://www.opengis.net/def/crs/EPSG/0/3857'
        params = [('SERVICE', 'WCS'), ('VERSION', '2.0.1'), ('REQUEST', 'GetCoverage'),
                  ('COVERAGEID', coverage), ('FORMAT', 'image/tiff'),
                  ('SUBSET', f'{ex}({minx},{maxx})'), ('SUBSET', f'{ny}({miny},{maxy})'),
                  ('SUBSETTINGCRS', crs), ('OUTPUTCRS', crs), ('SCALESIZE', f'{sx}({n}),{sy}({n})')]
    sep = '&' if '?' in url else '?'
    return url + sep + urllib.parse.urlencode(params), (minx, miny, maxx, maxy), res


def _heights(data, bbox, n, opts):
    """Float heights on the requested n x n grid; NaN where the service has no data."""
    img = Image.open(io.BytesIO(data))
    a = np.asarray(img, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError('not a single-band elevation image')
    lo, hi = opts.get('validRange', (-500.0, 9000.0))
    a = np.where((a >= lo) & (a <= hi), a, np.nan)
    h, w = a.shape
    minx, miny, maxx, maxy = bbox
    tags = getattr(img, 'tag_v2', {})
    scale, tie = tags.get(TIFF_PIXEL_SCALE), tags.get(TIFF_TIEPOINT)
    if scale and tie and len(tie) >= 6:
        # Some WCS answers cover a slightly larger area than asked: map our grid onto theirs.
        x0, y0, px, py = tie[3] - tie[0] * scale[0], tie[4] + tie[1] * scale[1], scale[0], scale[1]
    else:
        x0, y0, px, py = minx, maxy, (maxx - minx) / w, (maxy - miny) / h
    if (w, h) == (n, n) and abs(x0 - minx) < px * 0.01 and abs(y0 - maxy) < py * 0.01 \
            and abs(px * n - (maxx - minx)) < px * 0.01:
        return a
    step = (maxx - minx) / n
    centres = (np.arange(n) + 0.5) * step
    cols = (minx + centres - x0) / px - 0.5
    rows = (y0 - (maxy - centres)) / py - 0.5
    c0 = np.clip(np.floor(cols).astype(int), 0, w - 2)
    r0 = np.clip(np.floor(rows).astype(int), 0, h - 2)
    fc = np.clip(cols - c0, 0, 1)[None, :]
    fr = np.clip(rows - r0, 0, 1)[:, None]
    tl = a[r0][:, c0]
    tr = a[r0][:, c0 + 1]
    bl = a[r0 + 1][:, c0]
    br = a[r0 + 1][:, c0 + 1]
    return (tl * (1 - fc) + tr * fc) * (1 - fr) + (bl * (1 - fc) + br * fc) * fr


def _terrarium_heights(data, size):
    rgb = np.asarray(Image.open(io.BytesIO(data)).convert('RGB'), dtype=np.float64)
    if rgb.shape[:2] != (size, size):
        raise ValueError(f'unexpected tile size {rgb.shape[:2]}')
    return rgb[..., 0] * 256 + rgb[..., 1] + rgb[..., 2] / 256 - 32768


def shade(data, bbox, res, size, opts, terrarium=False):
    """JPEG bytes of the hillshade of one tile from the raw service answer."""
    pad = 0 if terrarium else PAD
    n = size + 2 * pad
    k = 1 if terrarium else int(opts.get('oversample', 1))
    z = _terrarium_heights(data, size) if terrarium else _heights(data, bbox, n * k, opts)
    if k > 1:
        # The server picks single pixels when it scales down (stair artefacts); average k x k instead.
        with np.errstate(invalid='ignore'):
            z = np.nanmean(z.reshape(n, k, n, k), axis=(1, 3))
    lat = math.degrees(2 * math.atan(math.exp((bbox[1] + bbox[3]) / 2 / 6378137.0)) - math.pi / 2)
    ground = res * math.cos(math.radians(lat))  # metres per pixel on the ground
    # Exaggerate the relief where pixels are coarse, otherwise overview zooms look flat
    # (about x1 at 1 m per pixel, x2.2 at 13 m, x4 at 100 m).
    zf = opts.get('zFactor', 1.0) * min(max(ground, 1.0) ** 0.3, 4.0)
    dzdx = np.gradient(z, axis=1) / ground * zf
    dzdn = -np.gradient(z, axis=0) / ground * zf  # rows run southwards
    az, alt = math.radians(AZIMUTH), math.radians(ALTITUDE)
    lx, ly, lz = math.sin(az) * math.cos(alt), math.cos(az) * math.cos(alt), math.sin(alt)
    hs = (-dzdx * lx - dzdn * ly + lz) / np.sqrt(dzdx * dzdx + dzdn * dzdn + 1)
    hs = np.where(np.isnan(hs), lz, hs)   # no data: flat grey, the page clips it to the state anyway
    out = (np.clip(hs, 0, 1) * 255).astype(np.uint8)[pad:pad + size, pad:pad + size]
    buf = io.BytesIO()
    Image.fromarray(out, 'L').save(buf, 'JPEG', quality=88)
    return buf.getvalue()
