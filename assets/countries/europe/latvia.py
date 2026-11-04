# This module contains the terrain layer definitions and geographical bounds for Latvia.
# Checked 2026-10-19: LĢIA has a 1 m terrain model from its airborne laser scanning, but publishes only the
# 20 m grid as open data (CC BY 4.0); its elevation WMS/WMTS (DEM 20 m, DSM) need a signed licence and an
# account, the open folder of wms.lgia.gov.lv holds only orthophotos and the topographic map. LVM GEO's
# relief WMS (lvmgeoserver.lvm.lv, layer public:ZemeLKS, 1 m from the LĢIA point cloud) no longer resolves
# (NXDOMAIN), its "open access WMS/WMTS" page says "coming soon". There is no open live LiDAR service.
# Mapterhorn lists the LĢIA 20 m terrain model (source "aalv", CC BY 4.0) but serves Latvia only up to
# grid 12 (~10 m/px), like the Copernicus GLO-30 surface model; the hillshade shows forest edges, so it
# cannot be told apart from GLO-30 with certainty. This is all that is available.
import json
import os

bounds = {
    "latvia": [[55.6, 20.9], [58.1, 28.3]]
}

# The five planning regions (plānošanas reģioni, own keys LV-KUR/LAT/RIG/VID/ZEM; no ISO codes exist) and
# the national border as [lat, lon] rings (VZD/data.gov.lv "Administratīvās teritorijas 2026", 42
# municipalities, CC0, dissolved per region after MK noteikumi Nr. 418 in the version of 25.09.2026;
# simplified to 50 m with shared borders, the national outline (their union) to 100 m).
with open(os.path.join(os.path.dirname(__file__), "latvia_regions.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

REGIONS = ['LV-KUR', 'LV-LAT', 'LV-RIG', 'LV-VID', 'LV-ZEM']
_MT = 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp'

terrain_layers = {
    # Base: LĢIA 20 m / Copernicus GLO-30 via Mapterhorn, up to grid 12 (= zoom 13), always underneath.
    'lv_base': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': ['latvia'], 'fallbackFor': REGIONS, 'fallbackFrom': 99, 'tileSize': 512,
            'retryBlank': False, 'maxZoom': 20, 'maxNativeZoom': 13,
            'attribution': 'DRM 20 m &copy; LĢIA, CC BY 4.0 / Copernicus GLO-30 &copy; DLR/Airbus via &copy; Mapterhorn '
                           '(Schummerung berechnet)'
        }
    },
}

for _info in terrain_layers.values():
    _pts = [pt for code in _info['options']['clipTo'] for ring in outlines[code] for pt in ring]
    _info['options']['bounds'] = [[round(min(p[0] for p in _pts) - 0.01, 4), round(min(p[1] for p in _pts) - 0.01, 4)],
                                  [round(max(p[0] for p in _pts) + 0.01, 4), round(max(p[1] for p in _pts) + 0.01, 4)]]

layer_logic = {
    "latvia": {
        "0": ['lv_base'],
    }
}

country = {'id': 'LV', 'name': 'Lettland'}
base_relief = {'layers': ['lv_base'], 'name': 'Grundrelief', 'resolution': '20 m', 'source': 'LĢIA / Copernicus via Mapterhorn'}
_NONE = {'layers': [], 'resolution': '20 m', 'source': 'nur LĢIA DRM 20 m bzw. Copernicus GLO-30',
         'note': 'kein offenes LiDAR (LĢIA-Höhendienste nur mit Lizenzvertrag, LVM-GEO-WMS offline)'}
regions = [
    {'id': 'LV-KUR', 'name': 'Kurzeme (Kurland)', **_NONE},
    {'id': 'LV-LAT', 'name': 'Latgale (Lettgallen)', **_NONE},
    {'id': 'LV-RIG', 'name': 'Riga', **_NONE},
    {'id': 'LV-VID', 'name': 'Vidzeme (Livland)', **_NONE},
    {'id': 'LV-ZEM', 'name': 'Zemgale (Semgallen)', **_NONE},
]
