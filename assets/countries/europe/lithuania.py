# This module contains the terrain layer definitions and geographical bounds for Lithuania.
# Checked 2026-10-19: the national LiDAR terrain model (DTM-LT 1 m / SEŽP_0.5LT, Nacionalinė žemės tarnyba)
# has no open live service: geoportal.lt's map proxy answers 401 for every relief service name
# (e.g. gisc_reljefas), only the background map is public. HNIT-Baltic shows DTM-LT 1 m and 10 m through
# ArcGIS Online / maps.lt, but licensed for non-commercial use inside Esri software only. Mapterhorn has no
# Lithuanian source; it serves Copernicus GLO-30 (30 m, a surface model) up to grid 12 (= zoom 13).
import json
import os

bounds = {
    "lithuania": [[53.85, 20.9], [56.5, 26.9]]
}

# Counties (apskritys, ISO 3166-2 LT-AL .. LT-VL) and the national border as [lat, lon] rings (VĮ Registrų
# centras, adresų registras open data adr_gra_apskritys of 01.10.2026; counties simplified to 50 m with shared
# borders, the national outline (their union) to 100 m; Klaipėda includes the Curonian Lagoon part).
with open(os.path.join(os.path.dirname(__file__), "lithuania_regions.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

REGIONS = ['LT-AL', 'LT-KL', 'LT-KU', 'LT-MR', 'LT-PN', 'LT-SA', 'LT-TA', 'LT-TE', 'LT-UT', 'LT-VL']
_MT = 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp'

terrain_layers = {
    # Base: Copernicus GLO-30 (30 m) via Mapterhorn, up to grid 12 (= zoom 13), always underneath.
    'lt_glo30': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': ['lithuania'], 'fallbackFor': REGIONS, 'fallbackFrom': 99, 'tileSize': 512,
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
    "lithuania": {
        "0": ['lt_glo30'],
    }
}

country = {'id': 'LT', 'name': 'Litauen'}
base_relief = {'layers': ['lt_glo30'], 'name': 'Grundrelief', 'resolution': '30 m', 'source': 'Copernicus via Mapterhorn'}
_NONE = {'layers': [], 'resolution': '30 m', 'source': 'nur Copernicus GLO-30',
         'note': 'kein offenes LiDAR (DTM-LT 1 m nicht öffentlich abrufbar)'}
regions = [
    {'id': 'LT-AL', 'name': 'Alytus', **_NONE},
    {'id': 'LT-KU', 'name': 'Kaunas', **_NONE},
    {'id': 'LT-KL', 'name': 'Klaipėda (Memel)', **_NONE},
    {'id': 'LT-MR', 'name': 'Marijampolė', **_NONE},
    {'id': 'LT-PN', 'name': 'Panevėžys (Ponewiesch)', **_NONE},
    {'id': 'LT-SA', 'name': 'Šiauliai (Schaulen)', **_NONE},
    {'id': 'LT-TA', 'name': 'Tauragė (Tauroggen)', **_NONE},
    {'id': 'LT-TE', 'name': 'Telšiai (Telschen)', **_NONE},
    {'id': 'LT-UT', 'name': 'Utena', **_NONE},
    {'id': 'LT-VL', 'name': 'Vilnius (Wilna)', **_NONE},
]
