# This module contains the terrain layer definitions and geographical bounds for the Netherlands.
# Checked 2026-10-19: AHN4 (0.5 m, flown 2020-22) as heights from the PDOK WCS is the only official,
# CC0 and live source for the whole country; the app shades it itself (dem_shade.py).
import json
import os

bounds = {
    "netherlands": [[50.7, 3.3], [53.6, 7.3]]
}

# Provinces and the national border as [lat, lon] rings (PDOK Bestuurlijke Gebieden, © Kadaster, CC BY 4.0;
# provinces simplified to 25 m with shared borders, the national outline to 100 m). The borders include
# IJsselmeer, Wadden Sea and the estuaries, where AHN still has beaches, salt marshes and islands.
with open(os.path.join(os.path.dirname(__file__), "netherlands_regions.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

PROVINCES = ['NL-DR', 'NL-FL', 'NL-FR', 'NL-GE', 'NL-GR', 'NL-LI', 'NL-NB', 'NL-NH', 'NL-OV', 'NL-UT', 'NL-ZE', 'NL-ZH']

terrain_layers = {
    # AHN4 terrain model 0.5 m. Buildings, water and some dense vegetation are gaps in an elevation model
    # of the ground; they stay transparent so the coarse base relief shows through. The flat country
    # needs a stronger exaggeration to show its relief.
    'nl_ahn4': {
        'type': 'dem_wcs',
        'url': 'https://service.pdok.nl/rws/ahn/wcs/v1_0?INTERPOLATION=BILINEAR',
        'options': {
            'clipTo': PROVINCES,
            'coverage': 'dtm_05m',
            'subsetAxes': ['x', 'y'],
            'validRange': [-10, 330],
            'zFactor': 2.5,
            'transparentNoData': True,
            'tileSize': 512,
            'retryBlank': False,
            'maxZoom': 20,
            'maxNativeZoom': 18,
            'attribution': 'AHN4 DTM 0,5 m &copy; Rijkswaterstaat / AHN via PDOK, CC0 (Schummerung berechnet)'
        }
    },
    # Base: AHN5 5 m with filled gaps via Mapterhorn (its finest level for NL is grid zoom 14 = app zoom 15).
    'nl_ahn5_5m': {
        'type': 'dem_terrarium',
        'url': 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp',
        'options': {
            'clipTo': ['netherlands'],
            'fallbackFor': PROVINCES,
            'fallbackFrom': 99,   # always under the AHN4 layer: it fills AHN4's gaps (buildings, water)
            'zFactor': 2.5,
            'tileSize': 512,
            'retryBlank': False,
            'maxZoom': 20,
            'maxNativeZoom': 15,
            'attribution': 'AHN5 5 m &copy; AHN.nl, CC BY 4.0 via &copy; Mapterhorn (Schummerung berechnet)'
        }
    },
}

for _info in terrain_layers.values():
    _pts = [pt for code in _info['options']['clipTo'] for ring in outlines[code] for pt in ring]
    _info['options']['bounds'] = [[round(min(p[0] for p in _pts) - 0.01, 4), round(min(p[1] for p in _pts) - 0.01, 4)],
                                  [round(max(p[0] for p in _pts) + 0.01, 4), round(max(p[1] for p in _pts) + 0.01, 4)]]

layer_logic = {
    "netherlands": {
        "9": ['nl_ahn4', 'nl_ahn5_5m'],
        "0": ['nl_ahn5_5m'],
    }
}

country = {'id': 'NL', 'name': 'Niederlande'}
base_relief = {'layers': ['nl_ahn5_5m'], 'name': 'Grundrelief', 'resolution': '5 m', 'source': 'AHN5 via Mapterhorn'}
_AHN = {'layers': ['nl_ahn4'], 'resolution': '50 cm', 'source': 'AHN4 (PDOK, berechnet)'}
regions = [
    {'id': 'NL-DR', 'name': 'Drenthe', **_AHN},
    {'id': 'NL-FL', 'name': 'Flevoland', **_AHN},
    {'id': 'NL-FR', 'name': 'Friesland', **_AHN},
    {'id': 'NL-GE', 'name': 'Gelderland', **_AHN},
    {'id': 'NL-GR', 'name': 'Groningen', **_AHN},
    {'id': 'NL-LI', 'name': 'Limburg', **_AHN},
    {'id': 'NL-NB', 'name': 'Nordbrabant', **_AHN},
    {'id': 'NL-NH', 'name': 'Nordholland', **_AHN},
    {'id': 'NL-OV', 'name': 'Overijssel', **_AHN},
    {'id': 'NL-UT', 'name': 'Utrecht', **_AHN},
    {'id': 'NL-ZE', 'name': 'Seeland', **_AHN},
    {'id': 'NL-ZH', 'name': 'Südholland', **_AHN},
]
