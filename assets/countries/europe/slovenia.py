# This module contains the terrain layer definitions and geographical bounds for Slovenia.
# Checked 2026-10-19: the Slovenian Environment Agency (ARSO) serves a hillshade of the national 1 m
# LiDAR terrain model (LSS 2011-15) for the whole country as an ArcGIS MapServer (/export in EPSG:3857,
# no watermark, transparent outside). Mapterhorn holds the same ARSO DMR 1 m (CC BY 4.0) up to its zoom 16.
# Not usable: the GURS layer SI.GURS.ZPDZ:LIDAR (GeoWebCache only in EPSG:3794) and the new CLSS 2023-25
# scan (0.5 m), which is so far only in the clss.si viewer and as downloads.
import json
import os

bounds = {
    "slovenia": [[45.4, 13.3], [46.9, 16.7]]
}

# The 12 statistical regions, keyed by their NUTS 3 codes SI031 .. SI044 (ISO 3166-2:SI only lists
# municipalities), and the national border as [lat, lon] rings (GURS register of spatial units, WFS
# SI.GURS.RPE:STATISTICNE_REGIJE, CC BY 4.0; regions simplified to 25 m with shared borders, the
# national outline to 100 m; two small Croatian enclaves on the Kolpa as holes).
with open(os.path.join(os.path.dirname(__file__), "slovenia_regions.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

REGIONS = ['SI031', 'SI032', 'SI033', 'SI034', 'SI035', 'SI036', 'SI037', 'SI038', 'SI041', 'SI042', 'SI043',
           'SI044']

terrain_layers = {
    # ArcGIS MapServer /export (cached in D96/TM, reprojected by the server); about 1.5 s per tile.
    # Low zooms alias badly (no smoothing), so it only starts at zoom 10.
    'si_arso1m': {
        'type': 'arcgis_map',
        'url': 'https://gis.arso.gov.si/arcgis/rest/services/Lidar_hillshade_D96TM/MapServer',
        'options': {
            'clipTo': REGIONS,
            'imageFormat': 'jpg',
            'tileSize': 512,
            'retryBlank': False,
            'maxZoom': 20,
            'maxNativeZoom': 17,
            'attribution': 'LiDAR DMR 1 m 2011-2015 &copy; ARSO (gis.arso.gov.si), CC BY 4.0'
        }
    },
    # Base: ARSO DMR 1 m via Mapterhorn (data up to Mapterhorn zoom 16 = app zoom 17), always underneath.
    'si_dmr1m': {
        'type': 'dem_terrarium',
        'url': 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp',
        'options': {
            'clipTo': ['slovenia'],
            'fallbackFor': REGIONS,
            'fallbackFrom': 99,
            'tileSize': 512,
            'retryBlank': False,
            'maxZoom': 20,
            'maxNativeZoom': 17,
            'attribution': 'DMR 1 m &copy; ARSO, CC BY 4.0, via &copy; Mapterhorn (Schummerung berechnet)'
        }
    },
}

for _info in terrain_layers.values():
    _pts = [pt for code in _info['options']['clipTo'] for ring in outlines[code] for pt in ring]
    _info['options']['bounds'] = [[round(min(p[0] for p in _pts) - 0.01, 4), round(min(p[1] for p in _pts) - 0.01, 4)],
                                  [round(max(p[0] for p in _pts) + 0.01, 4), round(max(p[1] for p in _pts) + 0.01, 4)]]

layer_logic = {
    "slovenia": {
        "10": ['si_arso1m', 'si_dmr1m'],
        "0": ['si_dmr1m'],
    }
}

country = {'id': 'SI', 'name': 'Slowenien'}
base_relief = {'layers': ['si_dmr1m'], 'name': 'Grundrelief', 'resolution': '1 m', 'source': 'ARSO LiDAR via Mapterhorn'}
_ARSO = {'layers': ['si_arso1m'], 'resolution': '1 m', 'source': 'ARSO (LiDAR 2011-15)'}
regions = [
    {'id': 'SI043', 'name': 'Goriška', **_ARSO},
    {'id': 'SI033', 'name': 'Koroška (Slowenisch-Kärnten)', **_ARSO},
    {'id': 'SI044', 'name': 'Küstenland-Karst', **_ARSO},
    {'id': 'SI042', 'name': 'Oberkrain (Gorenjska)', **_ARSO},
    {'id': 'SI032', 'name': 'Podravje', **_ARSO},
    {'id': 'SI031', 'name': 'Pomurje', **_ARSO},
    {'id': 'SI036', 'name': 'Posavje', **_ARSO},
    {'id': 'SI038', 'name': 'Primorska-Notranjska', **_ARSO},
    {'id': 'SI034', 'name': 'Savinjska', **_ARSO},
    {'id': 'SI037', 'name': 'Südost-Slowenien', **_ARSO},
    {'id': 'SI035', 'name': 'Zasavje', **_ARSO},
    {'id': 'SI041', 'name': 'Zentralslowenien (Ljubljana)', **_ARSO},
]
