# This module contains the terrain layer definitions and geographical bounds for Finland.
# Checked 2026-10-19: the National Land Survey (Maanmittauslaitos, MML) publishes the elevation model 2 m
# (from airborne laser scanning) and its hillshade ("rinnevarjoste", korkeusmalli_vinovalo) as open data
# under CC BY 4.0, but every live MML interface needs an API key (avoin-karttakuva WMTS, OGC API: 401
# without key). Paikkatietoikkuna serves the hillshade only in ETRS-TM35FIN (EPSG:3067), GTK's elevation
# services (gtkdata.gtk.fi Rajapinnat/Korkeusmalli, Korkeusmalli2018) are blank or coarse. Mapterhorn holds
# the MML elevation model 2 m (source "fi", downloaded via GeoCubes, CC BY 4.0) for the whole country:
# grid-15 tiles (~1.1 m/px) south of about 63-64 N, north of it (most of Lapland, Kainuu, North Ostrobothnia)
# only grid 14 (~2 m/px, which matches the 2 m model there). Answers ~0.2-1.2 s per tile.
import json
import os

bounds = {
    "finland": [[59.7, 19.0], [70.1, 31.6]]
}

# Regions (maakunnat, ISO 3166-2 FI-01 .. FI-19) and the national border as [lat, lon] rings (Statistics
# Finland, tilastointialueet:maakunta1000k_2026 = MML 1:1 000 000 generalised boundaries, CC BY 4.0;
# simplified to 100 m with shared borders, islands under 10 ha left out). Inland borders are therefore
# only accurate to some 100 m; MML's detailed boundaries also need an API key.
with open(os.path.join(os.path.dirname(__file__), "finland_regions.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

REGIONS = ['FI-01', 'FI-02', 'FI-03', 'FI-04', 'FI-05', 'FI-06', 'FI-07', 'FI-08', 'FI-09', 'FI-10', 'FI-11',
           'FI-12', 'FI-13', 'FI-14', 'FI-15', 'FI-16', 'FI-17', 'FI-18', 'FI-19']
_MT = 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp'

terrain_layers = {
    # Korkeusmalli 2 m via Mapterhorn: grid 15 native in the south; in the north grid 15 answers 404 and the
    # base (grid 14) shows, which there already holds the full 2 m.
    'fi_lidar': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': REGIONS, 'transparentNoData': True, 'tileSize': 512, 'retryBlank': False,
            'maxZoom': 20, 'maxNativeZoom': 16,
            'attribution': 'Korkeusmalli 2 m &copy; Maanmittauslaitos, CC BY 4.0 via &copy; Mapterhorn (Schummerung berechnet)'
        }
    },
    # Base: the same model via Mapterhorn up to grid 14 (= zoom 15), always underneath.
    'fi_base': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': ['finland'], 'fallbackFor': REGIONS, 'fallbackFrom': 99, 'tileSize': 512,
            'retryBlank': False, 'maxZoom': 20, 'maxNativeZoom': 15,
            'attribution': 'Korkeusmalli 2 m &copy; Maanmittauslaitos, CC BY 4.0 via &copy; Mapterhorn (Schummerung berechnet)'
        }
    },
}

for _info in terrain_layers.values():
    _pts = [pt for code in _info['options']['clipTo'] for ring in outlines[code] for pt in ring]
    _info['options']['bounds'] = [[round(min(p[0] for p in _pts) - 0.01, 4), round(min(p[1] for p in _pts) - 0.01, 4)],
                                  [round(max(p[0] for p in _pts) + 0.01, 4), round(max(p[1] for p in _pts) + 0.01, 4)]]

layer_logic = {
    "finland": {
        "8": ['fi_lidar', 'fi_base'],
        "0": ['fi_base'],
    }
}

country = {'id': 'FI', 'name': 'Finnland'}
base_relief = {'layers': ['fi_base'], 'name': 'Grundrelief', 'resolution': '2 m', 'source': 'MML Korkeusmalli via Mapterhorn'}
_KM = {'layers': ['fi_lidar'], 'resolution': '2 m', 'source': 'MML Korkeusmalli 2 m (Laserscanning) via Mapterhorn'}
regions = [
    {'id': 'FI-01', 'name': 'Åland (Ahvenanmaa)', **_KM},
    {'id': 'FI-05', 'name': 'Kainuu (Kajanaland)', **_KM},
    {'id': 'FI-06', 'name': 'Kanta-Häme (Tavastland)', **_KM},
    {'id': 'FI-09', 'name': 'Kymenlaakso (Kymmenedalen)', **_KM},
    {'id': 'FI-10', 'name': 'Lappland (Lappi)', **_KM},
    {'id': 'FI-08', 'name': 'Mittelfinnland (Keski-Suomi)', **_KM},
    {'id': 'FI-07', 'name': 'Mittelösterbotten (Keski-Pohjanmaa)', **_KM},
    {'id': 'FI-13', 'name': 'Nordkarelien (Pohjois-Karjala)', **_KM},
    {'id': 'FI-14', 'name': 'Nordösterbotten (Pohjois-Pohjanmaa)', **_KM},
    {'id': 'FI-15', 'name': 'Nordsavo (Pohjois-Savo)', **_KM},
    {'id': 'FI-12', 'name': 'Österbotten (Pohjanmaa)', **_KM},
    {'id': 'FI-16', 'name': 'Päijät-Häme (Päijänne-Tavastland)', **_KM},
    {'id': 'FI-11', 'name': 'Pirkanmaa (Birkaland)', **_KM},
    {'id': 'FI-17', 'name': 'Satakunta', **_KM},
    {'id': 'FI-02', 'name': 'Südkarelien (Etelä-Karjala)', **_KM},
    {'id': 'FI-03', 'name': 'Südösterbotten (Etelä-Pohjanmaa)', **_KM},
    {'id': 'FI-04', 'name': 'Südsavo (Etelä-Savo)', **_KM},
    {'id': 'FI-18', 'name': 'Uusimaa (Nyland)', **_KM},
    {'id': 'FI-19', 'name': 'Varsinais-Suomi (Eigentliches Finnland)', **_KM},
]
