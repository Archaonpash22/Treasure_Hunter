# This module contains the terrain layer definitions and geographical bounds for France (mainland + Corsica).
# Checked 2026-10-19: IGN LiDAR HD (0.5 m, flown 2021-26) covers 93.5 % of metropolitan France and is served
# as Float32 heights by the Géoplateforme WMS-R; the app shades it itself (dem_shade.py). Gaps (west
# Finistère/Morbihan, Morvan, Limousin, Nord, east Île-de-France) show RGE ALTI 1 m via Mapterhorn.
import json
import os

bounds = {
    "france": [[41.3, -5.2], [51.1, 9.6]]
}

# The 13 metropolitan regions and the national outline as [lat, lon] rings (IGN ADMIN EXPRESS COG 2026,
# Licence Ouverte 2.0; regions simplified to 50 m with shared borders, outline to 100 m). The borders end at
# the coastline.
with open(os.path.join(os.path.dirname(__file__), "france_regions.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

REGIONS = ['FR-ARA', 'FR-BFC', 'FR-BRE', 'FR-COR', 'FR-CVL', 'FR-GES', 'FR-HDF', 'FR-IDF', 'FR-NAQ', 'FR-NOR',
           'FR-OCC', 'FR-PAC', 'FR-PDL']

terrain_layers = {
    # LiDAR HD terrain model 0.5 m as heights (NoData -9999 = not flown yet: transparent, the base shows).
    # The Géoplateforme allows 40 WMS-R requests per second per IP, far above what the map sends.
    'fr_lidarhd': {
        'type': 'dem_wms',
        'url': 'https://data.geopf.fr/wms-r/wms',
        'options': {
            'clipTo': REGIONS,
            'layers': 'IGNF_LIDAR-HD_MNT_ELEVATION.ELEVATIONGRIDCOVERAGE.LAMB93',
            'version': '1.3.0',
            'demFormat': 'image/tiff',
            'validRange': [-50, 4900],
            'transparentNoData': True,
            'tileSize': 512,
            'retryBlank': False,
            'maxZoom': 20,
            'maxNativeZoom': 18,
            'attribution': 'MNT LiDAR HD 0,5 m &copy; IGN, Licence Ouverte 2.0 (Schummerung berechnet)'
        }
    },
    # Base: RGE ALTI 1 m (and older LiDAR HD blocks) via Mapterhorn, always under LiDAR HD.
    'fr_base': {
        'type': 'dem_terrarium',
        'url': 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp',
        'options': {
            'clipTo': ['france'],
            'fallbackFor': REGIONS,
            'fallbackFrom': 99,
            'tileSize': 512,
            'retryBlank': False,
            'maxZoom': 20,
            'maxNativeZoom': 17,
            'attribution': 'RGE ALTI 1 m / MNT LiDAR HD &copy; IGN, Licence Ouverte 2.0 via &copy; Mapterhorn (Schummerung berechnet)'
        }
    },
}

for _info in terrain_layers.values():
    _pts = [pt for code in _info['options']['clipTo'] for ring in outlines[code] for pt in ring]
    _info['options']['bounds'] = [[round(min(p[0] for p in _pts) - 0.01, 4), round(min(p[1] for p in _pts) - 0.01, 4)],
                                  [round(max(p[0] for p in _pts) + 0.01, 4), round(max(p[1] for p in _pts) + 0.01, 4)]]

layer_logic = {
    "france": {
        "12": ['fr_lidarhd', 'fr_base'],
        "0": ['fr_base'],
    }
}

country = {'id': 'FR', 'name': 'Frankreich'}
base_relief = {'layers': ['fr_base'], 'name': 'Grundrelief', 'resolution': '1 m', 'source': 'RGE ALTI via Mapterhorn'}


def _hd(share):
    note = 'IGN LiDAR HD' if share == 100 else f'IGN LiDAR HD auf {share} %, sonst RGE ALTI 1 m'
    return {'layers': ['fr_lidarhd'], 'resolution': '50 cm', 'source': note}


regions = [
    {'id': 'FR-ARA', 'name': 'Auvergne-Rhône-Alpes', **_hd(98)},
    {'id': 'FR-BFC', 'name': 'Bourgogne-Franche-Comté', **_hd(94)},
    {'id': 'FR-BRE', 'name': 'Bretagne', **_hd(64)},
    {'id': 'FR-CVL', 'name': 'Centre-Val de Loire', **_hd(95)},
    {'id': 'FR-GES', 'name': 'Grand Est', **_hd(100)},
    {'id': 'FR-HDF', 'name': 'Hauts-de-France', **_hd(74)},
    {'id': 'FR-IDF', 'name': 'Île-de-France', **_hd(66)},
    {'id': 'FR-COR', 'name': 'Korsika', **_hd(100)},
    {'id': 'FR-NOR', 'name': 'Normandie', **_hd(97)},
    {'id': 'FR-NAQ', 'name': 'Nouvelle-Aquitaine', **_hd(92)},
    {'id': 'FR-OCC', 'name': 'Occitanie', **_hd(100)},
    {'id': 'FR-PDL', 'name': 'Pays de la Loire', **_hd(100)},
    {'id': 'FR-PAC', 'name': "Provence-Alpes-Côte d'Azur", **_hd(100)},
]
