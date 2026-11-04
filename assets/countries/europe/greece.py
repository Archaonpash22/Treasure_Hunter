# This module contains the terrain layer definitions and geographical bounds for Greece.
# Checked 2026-10-19: there is no open live LiDAR or fine elevation service. The Hellenic Cadastre
# (Ktimatologio) serves only its orthophoto basemap openly (gis.ktimanet.gr/wms/wmsopen, layer BASEMAP);
# its DEM/DSM 5 m (LSO 2007-09) is not offered as an open WMS/WCS, the former INSPIRE endpoints answer 404
# and geodata.gov.gr does not respond. Greek LiDAR exists only as project data (motorways, single
# archaeological sites). Mapterhorn holds no Greek source either, so Greece shows only Copernicus GLO-30
# (30 m, a surface model).
import json
import os

bounds = {
    "greece": [[34.79, 19.36], [41.76, 29.66]]
}

# The 13 regions (periferies, ISO 3166-2 GR-A .. GR-M) and the Autonomous Monastic State of Mount Athos
# (GR-69) as [lat, lon] rings (OpenStreetMap administrative boundaries, © OpenStreetMap contributors, ODbL,
# cut to the OSM land polygons (osmdata.openstreetmap.de) because the OSM regions reach into the sea;
# regions simplified to 50 m with shared borders, islands below 10 ha left out, the national outline
# (their union) to 100 m).
with open(os.path.join(os.path.dirname(__file__), "greece_regions.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

REGIONS = ['GR-69', 'GR-A', 'GR-B', 'GR-C', 'GR-D', 'GR-E', 'GR-F', 'GR-G', 'GR-H', 'GR-I', 'GR-J', 'GR-K', 'GR-L',
           'GR-M']
_MT = 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp'

terrain_layers = {
    # Copernicus GLO-30 (30 m) via Mapterhorn, up to grid 12 (= zoom 13), 0.1-1 s per tile.
    'gr_glo30': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': ['greece'], 'fallbackFor': REGIONS, 'fallbackFrom': 99, 'tileSize': 512,
            'retryBlank': False, 'maxZoom': 20, 'maxNativeZoom': 13,
            'attribution': 'Copernicus GLO-30 &copy; DLR/Airbus via &copy; Mapterhorn (Schummerung berechnet)'
        }
    },
}

for _info in terrain_layers.values():
    _pts = [pt for code in _info['options']['clipTo'] for ring in outlines[code] for pt in ring]
    _info['options']['bounds'] = [[round(min(p[0] for p in _pts) - 0.01, 4), round(min(p[1] for p in _pts) - 0.01, 4)],
                                  [round(max(p[0] for p in _pts) + 0.01, 4), round(max(p[1] for p in _pts) + 0.01, 4)]]

layer_logic = {
    "greece": {
        "0": ['gr_glo30'],
    }
}

country = {'id': 'GR', 'name': 'Griechenland'}
base_relief = {'layers': ['gr_glo30'], 'name': 'Grundrelief', 'resolution': '30 m', 'source': 'Copernicus via Mapterhorn'}
_NONE = {'layers': [], 'resolution': '30 m', 'source': 'nur Copernicus GLO-30',
         'note': 'kein offenes LiDAR/DGM (Ktimatologio-DGM 5 m nicht als offener Dienst)'}
regions = [
    {'id': 'GR-I', 'name': 'Attika', **_NONE},
    {'id': 'GR-69', 'name': 'Berg Athos (Mönchsrepublik)', **_NONE},
    {'id': 'GR-D', 'name': 'Epirus', **_NONE},
    {'id': 'GR-F', 'name': 'Ionische Inseln', **_NONE},
    {'id': 'GR-M', 'name': 'Kreta', **_NONE},
    {'id': 'GR-H', 'name': 'Mittelgriechenland', **_NONE},
    {'id': 'GR-K', 'name': 'Nördliche Ägäis', **_NONE},
    {'id': 'GR-A', 'name': 'Ostmakedonien und Thrakien', **_NONE},
    {'id': 'GR-J', 'name': 'Peloponnes', **_NONE},
    {'id': 'GR-L', 'name': 'Südliche Ägäis', **_NONE},
    {'id': 'GR-E', 'name': 'Thessalien', **_NONE},
    {'id': 'GR-G', 'name': 'Westgriechenland', **_NONE},
    {'id': 'GR-C', 'name': 'Westmakedonien', **_NONE},
    {'id': 'GR-B', 'name': 'Zentralmakedonien', **_NONE},
]
