# This module contains the terrain layer definitions and geographical bounds for Luxembourg.
# Checked 2026-10-19: the ACT serves the hillshade of its LiDAR 2024 terrain model (0.5 m, CC0) on the open
# geoportail WMS (layer id 2978 "Ombrage (MNT) 2024", EPSG:3857, no key), the whole country, ~0.5 s per tile.
# Mapterhorn holds the LiDAR 2019 MNT but only ~40 % of the country at its finest level.
import json
import os

bounds = {
    "luxembourg": [[49.4, 5.7], [50.2, 6.55]]
}

# The 12 cantons (ISO 3166-2) and the national outline as [lat, lon] rings (INSPIRE Administrative Units,
# © ACT Luxembourg, CC0; cantons simplified to 25 m with shared borders, the outline to 100 m).
with open(os.path.join(os.path.dirname(__file__), "luxembourg_regions.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

CANTONS = ['LU-CA', 'LU-CL', 'LU-DI', 'LU-EC', 'LU-ES', 'LU-GR', 'LU-LU', 'LU-ME', 'LU-RD', 'LU-RM', 'LU-VD', 'LU-WI']

terrain_layers = {
    # Hillshade of the MNT 2024 0.5 m. Opaque JPEG (outside the country the service answers white,
    # the page cuts it to the cantons).
    'lu_omb2024': {
        'url': 'https://wms.geoportail.lu/public_map_layers/service',
        'options': {
            'clipTo': CANTONS, 'layers': '2978', 'format': 'image/jpeg', 'transparent': False,
            'version': '1.3.0', 'tileSize': 512, 'retryBlank': False, 'maxZoom': 20, 'maxNativeZoom': 18,
            'attribution': 'Ombrage MNT LiDAR 2024 0,5 m &copy; ACT Luxembourg, CC0'
        }
    },
    # Base: LiDAR 2019 MNT via Mapterhorn (grid zoom 16 everywhere, 17 only in parts).
    'lu_base': {
        'type': 'dem_terrarium',
        'url': 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp',
        'options': {
            'clipTo': ['luxembourg'], 'fallbackFor': CANTONS, 'fallbackFrom': 99, 'tileSize': 512,
            'retryBlank': False, 'maxZoom': 20, 'maxNativeZoom': 17,
            'attribution': 'MNT LiDAR 2019 &copy; ACT Luxembourg, CC0 via &copy; Mapterhorn (Schummerung berechnet)'
        }
    },
}

for _info in terrain_layers.values():
    _pts = [pt for code in _info['options']['clipTo'] for ring in outlines[code] for pt in ring]
    _info['options']['bounds'] = [[round(min(p[0] for p in _pts) - 0.01, 4), round(min(p[1] for p in _pts) - 0.01, 4)],
                                  [round(max(p[0] for p in _pts) + 0.01, 4), round(max(p[1] for p in _pts) + 0.01, 4)]]

layer_logic = {
    "luxembourg": {
        "11": ['lu_omb2024', 'lu_base'],
        "0": ['lu_base'],
    }
}

country = {'id': 'LU', 'name': 'Luxemburg'}
base_relief = {'layers': ['lu_base'], 'name': 'Grundrelief', 'resolution': '1 m', 'source': 'ACT LiDAR 2019 via Mapterhorn'}
_ACT = {'layers': ['lu_omb2024'], 'resolution': '50 cm', 'source': 'ACT Ombrage (LiDAR 2024)'}
regions = [
    {'id': 'LU-CA', 'name': 'Capellen', **_ACT},
    {'id': 'LU-CL', 'name': 'Clerf', **_ACT},
    {'id': 'LU-DI', 'name': 'Diekirch', **_ACT},
    {'id': 'LU-EC', 'name': 'Echternach', **_ACT},
    {'id': 'LU-ES', 'name': 'Esch an der Alzette', **_ACT},
    {'id': 'LU-GR', 'name': 'Grevenmacher', **_ACT},
    {'id': 'LU-LU', 'name': 'Luxemburg', **_ACT},
    {'id': 'LU-ME', 'name': 'Mersch', **_ACT},
    {'id': 'LU-RD', 'name': 'Redingen', **_ACT},
    {'id': 'LU-RM', 'name': 'Remich', **_ACT},
    {'id': 'LU-VD', 'name': 'Vianden', **_ACT},
    {'id': 'LU-WI', 'name': 'Wiltz', **_ACT},
]
