"""Background jobs for the window: address search and own position."""
import requests
from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal

USER_AGENT = "TreasureHunter/1.0 (desktop app)"


class GeocodeThread(QThread):
    """Address / place search: Nominatim first, Photon (komoot) when Nominatim fails or finds nothing."""
    found = pyqtSignal(list)      # [{'lat', 'lon', 'label', 'bbox': [[s, w], [n, e]] or None}]
    failed = pyqtSignal(str)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        errors = []
        for search in (self._nominatim, self._photon):
            try:
                results = search()
            except (requests.RequestException, ValueError, KeyError) as e:
                errors.append(str(e))
                continue
            if results:
                self.found.emit(results)
                return
        self.failed.emit('; '.join(errors) if errors else 'nichts gefunden')

    def _nominatim(self):
        r = requests.get('https://nominatim.openstreetmap.org/search', timeout=10,
                         headers={'User-Agent': USER_AGENT, 'Accept-Language': 'de'},
                         params={'q': self.query, 'format': 'jsonv2', 'limit': 6})
        r.raise_for_status()
        out = []
        for item in r.json():
            bb = item.get('boundingbox')
            out.append({'lat': float(item['lat']), 'lon': float(item['lon']), 'label': item.get('display_name', ''),
                        'bbox': [[float(bb[0]), float(bb[2])], [float(bb[1]), float(bb[3])]] if bb else None})
        return out

    def _photon(self):
        r = requests.get('https://photon.komoot.io/api/', timeout=10, headers={'User-Agent': USER_AGENT},
                         params={'q': self.query, 'limit': 6, 'lang': 'de'})
        r.raise_for_status()
        out = []
        for f in r.json().get('features', []):
            lon, lat = f['geometry']['coordinates']
            p = f.get('properties', {})
            parts = [' '.join(x for x in (p.get('street') or p.get('name'), p.get('housenumber')) if x),
                     ' '.join(x for x in (p.get('postcode'), p.get('city') or p.get('district')) if x), p.get('country')]
            ext = p.get('extent')  # [west, north, east, south]
            out.append({'lat': lat, 'lon': lon, 'label': ', '.join(x for x in parts if x),
                        'bbox': [[ext[3], ext[0]], [ext[1], ext[2]]] if ext else None})
        return out


class _IpLocateThread(QThread):
    found = pyqtSignal(float, float, str)
    failed = pyqtSignal(str)

    def run(self):
        try:
            r = requests.get('https://ipapi.co/json/', timeout=8, headers={'User-Agent': USER_AGENT})
            d = r.json()
            self.found.emit(float(d['latitude']), float(d['longitude']), d.get('city') or '')
        except (requests.RequestException, ValueError, KeyError, TypeError) as e:
            self.failed.emit(str(e))


class Locator(QObject):
    """Own position: Windows location service (Wi-Fi/GPS), falling back to a rough IP lookup."""
    located = pyqtSignal(float, float, str)   # lat, lon, how it was found
    failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._source = None
        self._ip_thread = None
        self._done = True

    def locate(self):
        self._done = False
        try:
            from PyQt6.QtPositioning import QGeoPositionInfoSource
            self._source = QGeoPositionInfoSource.createDefaultSource(self)
        except ImportError:
            self._source = None
        if self._source is None:
            self._by_ip()
            return
        self._source.positionUpdated.connect(self._on_position)
        self._source.errorOccurred.connect(lambda _e: self._by_ip())
        self._source.requestUpdate(10000)
        QTimer.singleShot(12000, self._by_ip)  # some drivers never answer

    def _on_position(self, info):
        if self._done:
            return
        self._done = True
        c = info.coordinate()
        acc = info.attribute(info.Attribute.HorizontalAccuracy)
        how = f'Windows-Ortung (±{acc:.0f} m)' if acc == acc and acc > 0 else 'Windows-Ortung'
        self.located.emit(c.latitude(), c.longitude(), how)

    def _by_ip(self):
        if self._done or (self._ip_thread and self._ip_thread.isRunning()):
            return
        self._ip_thread = _IpLocateThread()
        self._ip_thread.found.connect(self._on_ip)
        self._ip_thread.failed.connect(self._on_ip_failed)
        self._ip_thread.start()

    def _on_ip(self, lat, lon, city):
        if self._done:
            return
        self._done = True
        self.located.emit(lat, lon, f'ungefähr per IP{" (" + city + ")" if city else ""}')

    def _on_ip_failed(self, message):
        if not self._done:
            self._done = True
            self.failed.emit(message)


# FOSSGIS routing servers (OSRM on OpenStreetMap data, free for light use with attribution).
ROUTING_PROFILES = {'foot': 'routed-foot', 'bike': 'routed-bike', 'car': 'routed-car'}


class RouteThread(QThread):
    """Route through [(lat, lon), ...] in order; emits distance (m), duration (s) and [[lat, lon], ...]."""
    found = pyqtSignal(float, float, list)
    failed = pyqtSignal(str)

    def __init__(self, points, mode):
        super().__init__()
        self.points = points
        self.mode = mode

    def run(self):
        coords = ';'.join(f'{lon:.6f},{lat:.6f}' for lat, lon in self.points)
        url = f'https://routing.openstreetmap.de/{ROUTING_PROFILES[self.mode]}/route/v1/driving/{coords}'
        try:
            r = requests.get(url, params={'overview': 'full', 'geometries': 'geojson'}, timeout=20,
                             headers={'User-Agent': USER_AGENT})
            d = r.json()
            if d.get('code') != 'Ok' or not d.get('routes'):
                raise ValueError(d.get('message') or d.get('code') or f'HTTP {r.status_code}')
            route = d['routes'][0]
            line = [[lat, lon] for lon, lat in route['geometry']['coordinates']]
            self.found.emit(float(route['distance']), float(route['duration']), line)
        except (requests.RequestException, ValueError, KeyError) as e:
            self.failed.emit(str(e))
