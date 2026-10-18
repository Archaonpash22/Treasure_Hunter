# This module contains the terrain layer definitions and geographical bounds for Austria.
import json
import os

# Bounding box defines the geographical area for Austria.
# The format is [south_lat, west_lon], [north_lat, east_lon]
bounds = {
    "austria": [[46.3, 9.5], [49.1, 17.2]]
}

_here = os.path.dirname(__file__)
# National border and the nine Bundesländer ([lat, lon] rings, BEV Verwaltungsgrenzen VGD 01.04.2026,
# CC BY 4.0; states simplified to 7 m with shared borders, the national outline to 100 m).
with open(os.path.join(_here, "austria_outline.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)
with open(os.path.join(_here, "austria_states.json"), encoding="utf-8") as _f:
    outlines.update(json.load(_f))

STATES = ['AT-1', 'AT-2', 'AT-3', 'AT-4', 'AT-5', 'AT-6', 'AT-7', 'AT-8', 'AT-9']

# Checked 2026-10-18. No usable open hillshade finer than basemap.at in Burgenland, Niederösterreich
# and Wien; Kärnten serves its DGM only in EPSG:31258, Salzburg's service shows a grey grid instead of
# relief in Pinzgau, Pongau and Lungau, and the BEV ALS service requires registration.
terrain_layers = {
    # Austria-wide shaded relief from the states' ALS terrain models (about 1 m), cached XYZ tiles up
    # to zoom 17. Opaque, so it is cut to the national border.
    'at_dtm': {
        'url': 'https://mapsneu.wien.gv.at/basemap/bmapgelaende/grau/google3857/{z}/{y}/{x}.jpeg',
        'options': {
            'clipTo': ['austria'],
            'fallbackFor': STATES,
            'fallbackFrom': 14,
            'maxZoom': 20,
            'maxNativeZoom': 17,
            'attribution': 'Gelände &copy; basemap.at, CC BY 4.0'
        }
    },
    'tirol_dgm05': {
        'url': 'https://gis.tirol.gv.at/arcgis/services/Service_Public/terrain/MapServer/WMSServer',
        'options': {
            'clipTo': ['AT-7'],
            'layers': 'Image_Schummerung_Gelaendemodell',
            'format': 'image/jpeg',
            'transparent': False,
            'version': '1.3.0',
            'tileSize': 512,
            'retryBlank': False,
            'maxZoom': 20,
            'maxNativeZoom': 18,
            'attribution': 'ALS DGM 0,5 m &copy; Land Tirol – data.tirol.gv.at, CC BY 4.0'
        }
    },
    'vbg_dgm025': {
        'url': 'https://vogis.cnv.at/cgi-bin/mapserv?map=i_schummerung_2023_r_wms.map',
        'options': {
            'clipTo': ['AT-8'],
            'layers': 'schummerung_2023_gelaende_25cm',
            'format': 'image/jpeg',
            'transparent': False,
            'version': '1.3.0',
            'tileSize': 512,
            'retryBlank': False,
            'maxZoom': 20,
            'maxNativeZoom': 19,
            'attribution': 'ALS DGM 25 cm 2023 &copy; Land Vorarlberg – data.vorarlberg.gv.at, CC BY 4.0'
        }
    },
    # ArcGIS MapServer /export (no WMS); the resolution is not documented, plough furrows are
    # visible at 0.3 m per pixel, so it is treated as 0.5 m.
    'ooe_dgm05': {
        'type': 'arcgis_map',
        'url': 'https://ags.doris.at/arcgis/rest/services/Rasterdaten/Schummerung/MapServer',
        'options': {
            'clipTo': ['AT-4'],
            'imageFormat': 'jpg',
            'tileSize': 512,
            'retryBlank': False,
            'maxZoom': 20,
            'maxNativeZoom': 18,
            'attribution': 'ALS Schummerung &copy; Land OÖ / doris.at, CC BY 4.0'
        }
    },
    'stmk_dgm1': {
        'url': 'https://gis.stmk.gv.at/arcgis/services/OGD/als_schummerung/MapServer/WmsServer',
        'options': {
            'clipTo': ['AT-6'],
            'layers': 'Digitales_Gelaendemodell_DGM',
            'format': 'image/jpeg',
            'transparent': False,
            'version': '1.3.0',
            'tileSize': 512,
            'retryBlank': False,
            'maxZoom': 20,
            'maxNativeZoom': 17,
            'attribution': 'ALS DGM 1 m &copy; Land Steiermark – GIS-Steiermark, CC BY 4.0'
        }
    },
}

# Bounding boxes of the clipped layers, from their outlines (the page skips layers out of view).
for _info in terrain_layers.values():
    _pts = [pt for code in _info['options']['clipTo'] for ring in outlines[code] for pt in ring]
    _info['options']['bounds'] = [[round(min(p[0] for p in _pts) - 0.01, 4), round(min(p[1] for p in _pts) - 0.01, 4)],
                                  [round(max(p[0] for p in _pts) + 0.01, 4), round(max(p[1] for p in _pts) + 0.01, 4)]]

# This dictionary defines which terrain layer(s) to use based on the region and zoom level,
# finest first (see italy.py).
layer_logic = {
    "austria": {
        "9": ['vbg_dgm025', 'tirol_dgm05', 'ooe_dgm05', 'stmk_dgm1', 'at_dtm'],
        "0": ['at_dtm']
    }
}

# What the terrain panel lists (see germany.py).
country = {'id': 'AT', 'name': 'Österreich'}
base_relief = {'layers': ['at_dtm'], 'name': 'Grundrelief (ALS)', 'resolution': '1 m', 'source': 'basemap.at'}
regions = [
    {'id': 'AT-1', 'name': 'Burgenland', 'layers': [], 'note': 'kein eigener Dienst, basemap.at 1 m'},
    {'id': 'AT-2', 'name': 'Kärnten', 'layers': [], 'note': 'Dienst nur in EPSG:31258, basemap.at 1 m'},
    {'id': 'AT-3', 'name': 'Niederösterreich', 'layers': [], 'note': 'kein eigener Dienst, basemap.at 1 m'},
    {'id': 'AT-4', 'name': 'Oberösterreich', 'layers': ['ooe_dgm05'], 'resolution': '50 cm', 'source': 'DORIS'},
    {'id': 'AT-5', 'name': 'Salzburg', 'layers': [], 'note': 'Landesdienst fehlerhaft, basemap.at 1 m'},
    {'id': 'AT-6', 'name': 'Steiermark', 'layers': ['stmk_dgm1'], 'resolution': '1 m', 'source': 'GIS-Steiermark'},
    {'id': 'AT-7', 'name': 'Tirol', 'layers': ['tirol_dgm05'], 'resolution': '50 cm', 'source': 'Land Tirol'},
    {'id': 'AT-8', 'name': 'Vorarlberg', 'layers': ['vbg_dgm025'], 'resolution': '25 cm', 'source': 'VoGIS'},
    {'id': 'AT-9', 'name': 'Wien', 'layers': [], 'note': 'nur Höhenraster, basemap.at 1 m'},
]
