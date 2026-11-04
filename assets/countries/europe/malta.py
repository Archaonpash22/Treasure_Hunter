# This module contains the terrain layer definitions and geographical bounds for Malta.
# Checked 2026-10-19: the Planning Authority's LiDAR terrain model DTM 1 m (ERDF156 survey of 17 February
# 2012) is served as an INSPIRE WCS (rasdaman, hosted by wetransform; no key) with coarser pyramid
# coverages (2-32 m) for low zooms. It answers EPSG:3857 subsets (axes E/N, scaling axes X/Y) in ~0.8-1.5 s
# per 512 px tile; the tile cache computes the hillshade. Sea and building footprints are NoData (-999) and
# come out flat grey (as transparent holes the blocky GLO-30 would show through every house).
# Licence: the INSPIRE metadata states "no conditions to access and use", the national MSDI GeoPortal
# lists CC BY-NC-ND 4.0 for the same DTM; credit the Planning Authority either way. Mapterhorn holds no
# Maltese source (only Copernicus GLO-30, 30 m, a surface model), which is the base.
import json
import os

bounds = {
    "malta": [[35.77, 14.17], [36.1, 14.59]]
}

# The three inhabited islands (own keys MT-MLT, MT-GOZ, MT-COM; islets go to the nearest island) and the
# national outline as [lat, lon] rings (OpenStreetMap coastline islands, © OpenStreetMap contributors,
# ODbL; simplified to 25 m, islets below 0.5 ha left out). Malta has no official regions of this kind.
with open(os.path.join(os.path.dirname(__file__), "malta_regions.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

REGIONS = ['MT-COM', 'MT-GOZ', 'MT-MLT']
_MT = 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp'

terrain_layers = {
    # Planning Authority LiDAR DTM 1 m 2012 (WCS heights, hillshade computed locally).
    'mt_dtm1': {
        'type': 'dem_wcs',
        'url': 'https://malta.coverage.wetransform.eu/dtm_1m_2012/ows',
        'options': {
            'clipTo': REGIONS,
            'coverage': 'dtm_1m_2012',
            'pyramid': {2: 'dtm_1m_2012_2', 4: 'dtm_1m_2012_4', 8: 'dtm_1m_2012_8', 16: 'dtm_1m_2012_16',
                        32: 'dtm_1m_2012_32'},
            'subsetAxes': ['E', 'N'],
            'scaleAxes': ['X', 'Y'],
            'validRange': [-50, 300],
            'tileSize': 512,
            'retryBlank': False,
            'maxZoom': 20,
            'maxNativeZoom': 17,
            'attribution': 'LiDAR DTM 1 m 2012 &copy; Planning Authority Malta (ERDF156), INSPIRE-WCS (Schummerung berechnet)'
        }
    },
    # Base: Copernicus GLO-30 (30 m) via Mapterhorn, up to grid 12 (= zoom 13), always underneath.
    'mt_glo30': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': ['malta'], 'fallbackFor': REGIONS, 'fallbackFrom': 99, 'tileSize': 512,
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
    "malta": {
        "11": ['mt_dtm1', 'mt_glo30'],
        "0": ['mt_glo30'],
    }
}

country = {'id': 'MT', 'name': 'Malta'}
base_relief = {'layers': ['mt_glo30'], 'name': 'Grundrelief', 'resolution': '30 m', 'source': 'Copernicus via Mapterhorn'}
_DTM = {'layers': ['mt_dtm1'], 'resolution': '1 m', 'source': 'Planning Authority LiDAR DTM 2012 (ERDF156), WCS'}
regions = [
    {'id': 'MT-COM', 'name': 'Comino (Kemmuna)', **_DTM},
    {'id': 'MT-GOZ', 'name': 'Gozo (Għawdex)', **_DTM},
    {'id': 'MT-MLT', 'name': 'Malta (Hauptinsel)', **_DTM},
]
