# This module contains the terrain layer definitions and geographical bounds for Denmark.
# Checked 2026-10-19: the official DHM services (Dataforsyningen WMS "dhm" with dhm_terraen_skyggekort,
# WCS dhm_wcs, Datafordeler) need a free token from a user account for every map request; the app uses
# none. Mapterhorn holds DHM/Terræn 0.4 m (CC BY 4.0) at its finest level (grid zoom 17) for the whole
# country, apart from a strip of a few hundred metres at the German border and a gap of ~22 x 5 km around
# Tønder / Møgeltønder (8.79-9.14 E, 54.93-54.98 N) with nothing above grid zoom 12 (checked 2026-10-19).
import json
import os

bounds = {
    "denmark": [[54.5, 7.9], [57.8, 15.3]]
}

# The five regions and the national outline as [lat, lon] rings (OpenStreetMap region relations, which
# follow the DAGI borders and the coastline, © OpenStreetMap contributors, ODbL; regions simplified to
# 50 m with shared borders, islands from 5 ha as own rings, the outline to 100 m).
with open(os.path.join(os.path.dirname(__file__), "denmark_regions.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

REGIONS = ['DK-81', 'DK-82', 'DK-83', 'DK-84', 'DK-85']
_MT = 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp'

terrain_layers = {
    # DHM/Terræn 0.4 m via Mapterhorn: grid-17 tiles (0.68 m/px) are its finest. Where they are
    # missing (border strip, Tønder gap) the tiles answer 404 and the base shows.
    'dk_dhm04': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': REGIONS, 'transparentNoData': True, 'zFactor': 1.5, 'tileSize': 512, 'retryBlank': False,
            'maxZoom': 20, 'maxNativeZoom': 18,
            'attribution': 'DHM/Terræn 0,4 m &copy; Klimadatastyrelsen, CC BY 4.0 via &copy; Mapterhorn (Schummerung berechnet)'
        }
    },
    # Base: the same model at grid zoom 12 (~10 m), which also exists in the Tønder gap.
    'dk_base': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': ['denmark'], 'fallbackFor': REGIONS, 'fallbackFrom': 99, 'zFactor': 1.5, 'tileSize': 512,
            'retryBlank': False, 'maxZoom': 20, 'maxNativeZoom': 13,
            'attribution': 'DHM/Terræn &copy; Klimadatastyrelsen, CC BY 4.0 via &copy; Mapterhorn (Schummerung berechnet)'
        }
    },
}

for _info in terrain_layers.values():
    _pts = [pt for code in _info['options']['clipTo'] for ring in outlines[code] for pt in ring]
    _info['options']['bounds'] = [[round(min(p[0] for p in _pts) - 0.01, 4), round(min(p[1] for p in _pts) - 0.01, 4)],
                                  [round(max(p[0] for p in _pts) + 0.01, 4), round(max(p[1] for p in _pts) + 0.01, 4)]]

layer_logic = {
    "denmark": {
        "8": ['dk_dhm04', 'dk_base'],
        "0": ['dk_base'],
    }
}

country = {'id': 'DK', 'name': 'Dänemark'}
base_relief = {'layers': ['dk_base'], 'name': 'Grundrelief', 'resolution': '10 m', 'source': 'DHM via Mapterhorn'}
_DHM = {'layers': ['dk_dhm04'], 'resolution': '40 cm', 'source': 'DHM/Terræn via Mapterhorn'}
regions = [
    {'id': 'DK-84', 'name': 'Hauptstadtregion', **_DHM},
    {'id': 'DK-82', 'name': 'Mitteljütland', **_DHM},
    {'id': 'DK-81', 'name': 'Nordjütland', **_DHM},
    {'id': 'DK-85', 'name': 'Seeland', **_DHM},
    {'id': 'DK-83', 'name': 'Süddänemark', **_DHM, 'source': 'DHM/Terræn via Mapterhorn; um Tønder nur ~10 m'},
]
