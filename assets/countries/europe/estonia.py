# This module contains the terrain layer definitions and geographical bounds for Estonia.
# Checked 2026-10-19: the Maa- ja Ruumiamet (former Maa-amet) publishes the LiDAR elevation data 2021-2024 as
# open data, and its WMS (kaart.maaamet.ee/wms/fotokaart, layers "reljeef" and "vreljeef") and tile cache
# (tiles.maaamet.ee, reljeef@LEST) show a hillshade of it, free and without a key - but only in L-EST97
# (EPSG:3301): EPSG:3857 requests answer a ServiceException and the tile cache has no Mercator relief
# (only foto/kaart/hybriid/hallkaart@GMC). The app cannot reproject, so the national services are not usable.
# Mapterhorn holds the same 1 m terrain model (source "ee", Maa- ja Ruumiamet open data licence 2025) for
# the whole country (grid 16 everywhere, grid 17 answers 404) and serves it in ~0.2-1.3 s per tile.
import json
import os

bounds = {
    "estonia": [[57.5, 21.7], [59.75, 28.25]]
}

# Counties (maakonnad, ISO 3166-2 EE-37 .. EE-87 = EHAK codes since 2017) and the national border as [lat, lon]
# rings (Maa- ja Ruumiamet, Haldus- ja asustusjaotus, maakond_shp of 2026, open data; counties simplified
# to 50 m with shared borders, the national outline (their union) to 100 m; islands under 10 ha left out).
with open(os.path.join(os.path.dirname(__file__), "estonia_regions.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

REGIONS = ['EE-37', 'EE-39', 'EE-45', 'EE-50', 'EE-52', 'EE-56', 'EE-60', 'EE-64', 'EE-68', 'EE-71', 'EE-74',
           'EE-79', 'EE-81', 'EE-84', 'EE-87']
_MT = 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp'

terrain_layers = {
    # Kõrgusmudel 1 m (LiDAR 2021-2024) via Mapterhorn: grid-16 tiles (~0.6 m/px) are native.
    'ee_lidar': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': REGIONS, 'transparentNoData': True, 'tileSize': 512, 'retryBlank': False,
            'zFactor': 2.0,   # mostly flat land: stronger relief, as for the Netherlands and Poland
            'maxZoom': 20, 'maxNativeZoom': 17,
            'attribution': 'K&otilde;rgusandmed 1 m (2021-2024) &copy; Maa- ja Ruumiamet via &copy; Mapterhorn (Schummerung berechnet)'
        }
    },
    # Base: the same model via Mapterhorn, resampled (grid 14 = zoom 15), always underneath.
    'ee_base': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': ['estonia'], 'fallbackFor': REGIONS, 'fallbackFrom': 99, 'tileSize': 512,
            'retryBlank': False, 'maxZoom': 20, 'maxNativeZoom': 15,
            'attribution': 'K&otilde;rgusandmed &copy; Maa- ja Ruumiamet via &copy; Mapterhorn (Schummerung berechnet)'
        }
    },
}

for _info in terrain_layers.values():
    _pts = [pt for code in _info['options']['clipTo'] for ring in outlines[code] for pt in ring]
    _info['options']['bounds'] = [[round(min(p[0] for p in _pts) - 0.01, 4), round(min(p[1] for p in _pts) - 0.01, 4)],
                                  [round(max(p[0] for p in _pts) + 0.01, 4), round(max(p[1] for p in _pts) + 0.01, 4)]]

layer_logic = {
    "estonia": {
        "8": ['ee_lidar', 'ee_base'],
        "0": ['ee_base'],
    }
}

country = {'id': 'EE', 'name': 'Estland'}
base_relief = {'layers': ['ee_base'], 'name': 'Grundrelief', 'resolution': '2,5 m', 'source': 'Maa- ja Ruumiamet via Mapterhorn'}
_LID = {'layers': ['ee_lidar'], 'resolution': '1 m', 'source': 'Maa- ja Ruumiamet Kõrgusmudel 1 m (LiDAR 2021-24) via Mapterhorn'}
regions = [
    {'id': 'EE-37', 'name': 'Harjumaa (Harrien)', **_LID},
    {'id': 'EE-39', 'name': 'Hiiumaa (Dagö)', **_LID},
    {'id': 'EE-45', 'name': 'Ida-Virumaa (Ost-Wierland)', **_LID},
    {'id': 'EE-50', 'name': 'Jõgevamaa', **_LID},
    {'id': 'EE-52', 'name': 'Järvamaa (Jerwen)', **_LID},
    {'id': 'EE-56', 'name': 'Läänemaa (Wiek)', **_LID},
    {'id': 'EE-60', 'name': 'Lääne-Virumaa (West-Wierland)', **_LID},
    {'id': 'EE-68', 'name': 'Pärnumaa (Pernau)', **_LID},
    {'id': 'EE-64', 'name': 'Põlvamaa', **_LID},
    {'id': 'EE-71', 'name': 'Raplamaa', **_LID},
    {'id': 'EE-74', 'name': 'Saaremaa (Ösel)', **_LID},
    {'id': 'EE-79', 'name': 'Tartumaa (Dorpat)', **_LID},
    {'id': 'EE-81', 'name': 'Valgamaa (Walk)', **_LID},
    {'id': 'EE-84', 'name': 'Viljandimaa (Fellin)', **_LID},
    {'id': 'EE-87', 'name': 'Võrumaa (Werro)', **_LID},
]
