# This module contains the terrain layer definitions and geographical bounds for Belgium.
# Checked 2026-10-19: Flanders serves the DHMV II hillshade 0.25 m (LiDAR 2013-15, also covers Brussels)
# and Wallonia the MNT 2021-2022 hillshade 0.5 m as open WMS (EPSG:3857, no key). Both are requested as
# opaque JPEG: as transparent PNG the brightest slopes come back see-through. Mapterhorn holds the same
# models (Flanders only 1 m, Wallonia 0.5 m) and is the base underneath.
import json
import os

bounds = {
    "belgium": [[49.45, 2.5], [51.55, 6.45]]
}

# The three regions and the national outline as [lat, lon] rings (Statbel statistical sectors 01/01/2025,
# Statbel open data licence, dissolved per region; regions simplified to 25 m with shared
# borders, the outline to 100 m). Baarle-Hertog, Voeren and Comines-Warneton are own rings, the German
# Vennbahn enclaves and Brussels are holes.
with open(os.path.join(os.path.dirname(__file__), "belgium_regions.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

REGIONS = ['BE-BRU', 'BE-VLG', 'BE-WAL']
_MT = 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp'

terrain_layers = {
    # DHMV II hillshade 0.25 m (Flanders + Brussels), ~0.3 s per 512 px tile. Outside its area the
    # service answers a plain grey tile; the page cuts it to the two regions.
    'be_vl_dhmv2': {
        'url': 'https://geo.api.vlaanderen.be/DHMV/wms',
        'options': {
            'clipTo': ['BE-VLG', 'BE-BRU'], 'layers': 'DHMV_II_HILL_25cm', 'format': 'image/jpeg',
            'transparent': False, 'version': '1.3.0', 'tileSize': 512, 'retryBlank': False,
            'maxZoom': 20, 'maxNativeZoom': 19,
            'attribution': 'DHMV II Hillshade 25 cm &copy; Digitaal Vlaanderen, Modellicentie Gratis Hergebruik'
        }
    },
    # MNT 2021-2022 hillshade 0.5 m (Wallonia), 0.3-1.2 s per tile; noisy below zoom 12, so it starts there.
    'be_wal_mnt': {
        'url': 'https://geoservices.wallonie.be/arcgis/services/RELIEF/WALLONIE_MNT_2021_2022_HILLSHADE/MapServer/WMSServer',
        'options': {
            'clipTo': ['BE-WAL'], 'layers': '0', 'format': 'image/jpeg', 'transparent': False,
            'version': '1.3.0', 'tileSize': 512, 'retryBlank': False, 'maxZoom': 20, 'maxNativeZoom': 18,
            'attribution': 'MNT 2021-2022 Hillshade 0,5 m &copy; SPW, CC BY 4.0'
        }
    },
    # Base: DHMV II 1 m / SPW MNT 0.5 m via Mapterhorn (grid zoom 16 everywhere, 17 only in Wallonia).
    'be_base': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': ['belgium'], 'fallbackFor': REGIONS, 'fallbackFrom': 99, 'tileSize': 512,
            'retryBlank': False, 'maxZoom': 20, 'maxNativeZoom': 17,
            'attribution': 'DHMV II 1 m &copy; Digitaal Vlaanderen / MNT 2021-22 &copy; SPW (CC BY 4.0) via &copy; Mapterhorn '
                           '(Schummerung berechnet)'
        }
    },
}

for _info in terrain_layers.values():
    _pts = [pt for code in _info['options']['clipTo'] for ring in outlines[code] for pt in ring]
    _info['options']['bounds'] = [[round(min(p[0] for p in _pts) - 0.01, 4), round(min(p[1] for p in _pts) - 0.01, 4)],
                                  [round(max(p[0] for p in _pts) + 0.01, 4), round(max(p[1] for p in _pts) + 0.01, 4)]]

layer_logic = {
    "belgium": {
        "12": ['be_vl_dhmv2', 'be_wal_mnt', 'be_base'],
        "0": ['be_base'],
    }
}

country = {'id': 'BE', 'name': 'Belgien'}
base_relief = {'layers': ['be_base'], 'name': 'Grundrelief', 'resolution': '1 m', 'source': 'DHMV II / SPW via Mapterhorn'}
_VL = {'layers': ['be_vl_dhmv2'], 'resolution': '25 cm', 'source': 'DHMV II Hillshade (Digitaal Vlaanderen, LiDAR 2013-15)'}
regions = [
    {'id': 'BE-BRU', 'name': 'Brüssel', **_VL},
    {'id': 'BE-VLG', 'name': 'Flandern', **_VL},
    {'id': 'BE-WAL', 'name': 'Wallonien', 'layers': ['be_wal_mnt'], 'resolution': '50 cm',
     'source': 'SPW Hillshade (LiDAR 2021-22)'},
]
