# This module contains the terrain layer definitions and geographical bounds for Hungary.
# Checked 2026-10-19: Hungary has no open LiDAR terrain model. Lechner Tudásközpont sells the national
# DDM 5 m (from 1:10 000 contours) and LiDAR data through geoshop.hu; openly (CC BY 4.0, INSPIRE HVD) it
# only publishes the DDM 25 m as a coloured hillshade WMS (geoservices/ddm25) - smoother and less detailed
# than Copernicus GLO-30, so not used. Mapterhorn has no Hungarian source either (attribution.json
# 2026-10-19); its tiles above grid 12 over Győr-Moson-Sopron, Nógrád, Vas and Zala only enlarge coarse
# border data. So only Copernicus GLO-30 (30 m, a surface model: forests and buildings included) shows.
import json
import os

bounds = {
    "hungary": [[45.7, 16.1], [48.6, 22.9]]
}

# Counties (vármegyék, ISO 3166-2 HU-BA .. HU-ZA), Budapest (HU-BU) and the national border as [lat, lon]
# rings (Lechner Tudásközpont, INSPIRE Administrative Units 2025, valid from 01.09.2025, WFS
# geoserver/AU.2025, CC BY 4.0; counties simplified to 50 m with shared borders, the national outline
# (their union) to 100 m; Budapest is a hole ring in Pest).
with open(os.path.join(os.path.dirname(__file__), "hungary_regions.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

REGIONS = ['HU-BA', 'HU-BE', 'HU-BK', 'HU-BU', 'HU-BZ', 'HU-CS', 'HU-FE', 'HU-GS', 'HU-HB', 'HU-HE', 'HU-JN',
           'HU-KE', 'HU-NO', 'HU-PE', 'HU-SO', 'HU-SZ', 'HU-TO', 'HU-VA', 'HU-VE', 'HU-ZA']

terrain_layers = {
    # Base: Copernicus GLO-30 (30 m) via Mapterhorn, up to grid 12 (= zoom 13), enlarged above.
    'hu_glo30': {
        'type': 'dem_terrarium',
        'url': 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp',
        'options': {
            'clipTo': ['hungary'],
            'fallbackFor': REGIONS,
            'fallbackFrom': 99,
            'tileSize': 512,
            'retryBlank': False,
            'maxZoom': 20,
            'maxNativeZoom': 13,
            'attribution': 'Copernicus GLO-30 &copy; DLR/Airbus via &copy; Mapterhorn (Schummerung berechnet)'
        }
    },
}

for _info in terrain_layers.values():
    _pts = [pt for code in _info['options']['clipTo'] for ring in outlines[code] for pt in ring]
    _info['options']['bounds'] = [[round(min(p[0] for p in _pts) - 0.01, 4), round(min(p[1] for p in _pts) - 0.01, 4)],
                                  [round(max(p[0] for p in _pts) + 0.01, 4), round(max(p[1] for p in _pts) + 0.01, 4)]]

layer_logic = {
    "hungary": {
        "0": ['hu_glo30'],
    }
}

country = {'id': 'HU', 'name': 'Ungarn'}
base_relief = {'layers': ['hu_glo30'], 'name': 'Grundrelief', 'resolution': '30 m', 'source': 'Copernicus via Mapterhorn'}
_NONE = {'layers': [], 'resolution': '30 m', 'source': 'nur Copernicus GLO-30',
         'note': 'kein offenes LiDAR (Lechner DDM 5 m / LiDAR nur kostenpflichtig über geoshop.hu)'}
regions = [
    {'id': 'HU-BK', 'name': 'Bács-Kiskun', **_NONE},
    {'id': 'HU-BA', 'name': 'Baranya (Branau)', **_NONE},
    {'id': 'HU-BE', 'name': 'Békés', **_NONE},
    {'id': 'HU-BZ', 'name': 'Borsod-Abaúj-Zemplén', **_NONE},
    {'id': 'HU-BU', 'name': 'Budapest', **_NONE},
    {'id': 'HU-CS', 'name': 'Csongrád-Csanád', **_NONE},
    {'id': 'HU-FE', 'name': 'Fejér (Weißenburg)', **_NONE},
    {'id': 'HU-GS', 'name': 'Győr-Moson-Sopron (Raab-Wieselburg-Ödenburg)', **_NONE},
    {'id': 'HU-HB', 'name': 'Hajdú-Bihar', **_NONE},
    {'id': 'HU-HE', 'name': 'Heves', **_NONE},
    {'id': 'HU-JN', 'name': 'Jász-Nagykun-Szolnok', **_NONE},
    {'id': 'HU-KE', 'name': 'Komárom-Esztergom (Komorn-Gran)', **_NONE},
    {'id': 'HU-NO', 'name': 'Nógrád (Neograd)', **_NONE},
    {'id': 'HU-PE', 'name': 'Pest', **_NONE},
    {'id': 'HU-SO', 'name': 'Somogy (Schomodei)', **_NONE},
    {'id': 'HU-SZ', 'name': 'Szabolcs-Szatmár-Bereg', **_NONE},
    {'id': 'HU-TO', 'name': 'Tolna (Tolnau)', **_NONE},
    {'id': 'HU-VA', 'name': 'Vas (Eisenburg)', **_NONE},
    {'id': 'HU-VE', 'name': 'Veszprém (Wesprim)', **_NONE},
    {'id': 'HU-ZA', 'name': 'Zala (Sala)', **_NONE},
]
