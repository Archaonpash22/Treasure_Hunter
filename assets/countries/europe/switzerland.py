# This module contains the terrain layer definitions and geographical bounds for Switzerland and Liechtenstein.
# Checked 2026-10-19: swisstopo swissALTI3D (0.5 m, LiDAR, OGD) covers CH and LI completely; the
# multidirectional hillshade comes as cached WMTS tiles up to zoom 18 (transparent outside CH/LI).
# Finer, all OGD: Zürich DTM 2022 0.25 m, Geneva 2025 0.2 m, Solothurn 2019 0.25 m, Basel-Stadt 2024 0.25 m.
# Not used: Aargau, Bern (0.5 m, no gain), Luzern 2024 0.25 m and Basel-Landschaft 2018 0.25 m (finer but so
# pale they show less than swissALTI3D), Neuchâtel 2016, Fribourg, Schaffhausen (older). Liechtenstein's own WMS (same 2018 swisstopo
# data) is only free for non-commercial use and not finer, so LI uses swisstopo. Mapterhorn holds the
# same swissALTI3D (and ZH 0.25 m) and feeds the analysis views.
import json
import os

bounds = {
    "switzerland": [[45.8, 5.9], [47.85, 10.5]]
}

# Cantons, Liechtenstein and the national outline as [lat, lon] rings (swisstopo swissBOUNDARIES3D
# 2026-01, OGD, © swisstopo; cantons and LI simplified to 25 m with shared borders, outline to 100 m).
# Lakes are inside the cantons (Bodensee split TG/SG as in swissBOUNDARIES3D); Büsingen (DE) and
# Campione d'Italia (IT) are holes.
with open(os.path.join(os.path.dirname(__file__), "switzerland_regions.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

CANTONS = ['CH-AG', 'CH-AI', 'CH-AR', 'CH-BE', 'CH-BL', 'CH-BS', 'CH-FR', 'CH-GE', 'CH-GL', 'CH-GR', 'CH-JU',
           'CH-LU', 'CH-NE', 'CH-NW', 'CH-OW', 'CH-SG', 'CH-SH', 'CH-SO', 'CH-SZ', 'CH-TG', 'CH-TI', 'CH-UR',
           'CH-VD', 'CH-VS', 'CH-ZG', 'CH-ZH']
UNITS = CANTONS + ['LI']

terrain_layers = {
    # Kanton Zürich LiDAR 2022, DTM hillshade 0.25 m (OGD). PNG: transparent outside the canton (JPEG
    # would be black there and show as a sliver along the simplified border).
    'zh_dtm025': {
        'url': 'https://wms.zh.ch/LidarZHWMS',
        'options': {
            'clipTo': ['CH-ZH'], 'layers': 'dtm_relief', 'format': 'image/png', 'transparent': True,
            'version': '1.3.0', 'tileSize': 512, 'retryBlank': False, 'maxZoom': 20, 'maxNativeZoom': 19,
            'attribution': 'DTM Relief 2022 0,25 m &copy; Kanton Zürich (GIS-ZH), OGD'
        }
    },
    # Geneva LiDAR March 2025, terrain hillshade 0.2 m (SITG, OGD). Black outside the canton (the app sends
    # no noData), so it must stay clipped.
    'ge_sitg02': {
        'type': 'arcgis_image',
        'url': 'https://raster.sitg.ge.ch/arcgis/rest/services/MNA_RELIEF_OMBRE_TERRAIN_2025_03/ImageServer',
        'options': {
            'clipTo': ['CH-GE'], 'imageFormat': 'png', 'tileSize': 512, 'retryBlank': False, 'maxZoom': 20,
            'maxNativeZoom': 19,
            'attribution': 'Relief ombré MNT LiDAR 2025 0,2 m &copy; SITG, OGD'
        }
    },
    # Solothurn LiDAR 2019, DTM hillshade 0.25 m (AGI SO, OGD). Covers the canton south of about 47.43 N;
    # Dorneck/Thierstein are missing there and show swissALTI3D underneath.
    'so_dtm025': {
        'url': 'https://geo.so.ch/api/wms',
        'options': {
            'clipTo': ['CH-SO'], 'layers': 'ch.so.agi.lidar_2019.dtm_relief', 'format': 'image/png',
            'transparent': True, 'version': '1.3.0', 'tileSize': 512, 'retryBlank': False, 'maxZoom': 20,
            'maxNativeZoom': 19,
            'attribution': 'LiDAR 2019 DTM Relief 0,25 m &copy; Kanton Solothurn (AGI), OGD'
        }
    },
    # Basel-Stadt LiDAR 2024, DTM hillshade 0.25 m (GVA BS, OGD).
    'bs_dtm025': {
        'url': 'https://wms.geo.bs.ch/',
        'options': {
            'clipTo': ['CH-BS'], 'layers': 'HM_DTM_Hillshade_2024_25cm', 'format': 'image/png',
            'transparent': True, 'version': '1.3.0', 'tileSize': 512, 'retryBlank': False, 'maxZoom': 20,
            'maxNativeZoom': 19,
            'attribution': 'DTM Hillshade 2024 0,25 m &copy; Kanton Basel-Stadt (GVA), OGD'
        }
    },
    # swissALTI3D multidirectional hillshade 0.5 m, cached WMTS (256 px, EPSG:3857, zoom 0-18). Every canton
    # (and LI) lists it, so it can be switched per canton; under the four finer cantonal layers it fills their edges.
    'ch_alti3d': {
        'url': 'https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.swissalti3d-reliefschattierung/default/current/3857/{z}/{x}/{y}.png',
        'options': {
            'clipTo': UNITS, 'retryBlank': False,
            'maxZoom': 20, 'maxNativeZoom': 18,
            'attribution': 'swissALTI3D Relief 0,5 m &copy; swisstopo (OGD)'
        }
    },
}

for _info in terrain_layers.values():
    _pts = [pt for code in _info['options']['clipTo'] for ring in outlines[code] for pt in ring]
    _info['options']['bounds'] = [[round(min(p[0] for p in _pts) - 0.01, 4), round(min(p[1] for p in _pts) - 0.01, 4)],
                                  [round(max(p[0] for p in _pts) + 0.01, 4), round(max(p[1] for p in _pts) + 0.01, 4)]]

layer_logic = {
    "switzerland": {
        "11": ['zh_dtm025', 'ge_sitg02', 'so_dtm025', 'bs_dtm025', 'ch_alti3d'],
        "0": ['ch_alti3d'],
    }
}

country = {'id': 'CH', 'name': 'Schweiz'}
_ALTI = {'layers': ['ch_alti3d'], 'resolution': '50 cm', 'source': 'swisstopo swissALTI3D'}
regions = [
    {'id': 'CH-AG', 'name': 'Aargau', **_ALTI},
    {'id': 'CH-AR', 'name': 'Appenzell Ausserrhoden', **_ALTI},
    {'id': 'CH-AI', 'name': 'Appenzell Innerrhoden', **_ALTI},
    {'id': 'CH-BL', 'name': 'Basel-Landschaft', **_ALTI},
    {'id': 'CH-BS', 'name': 'Basel-Stadt', 'layers': ['bs_dtm025', 'ch_alti3d'], 'resolution': '25 cm', 'source': 'Kanton Basel-Stadt (LiDAR 2024)'},
    {'id': 'CH-BE', 'name': 'Bern', **_ALTI},
    {'id': 'CH-FR', 'name': 'Freiburg', **_ALTI},
    {'id': 'CH-GE', 'name': 'Genf', 'layers': ['ge_sitg02', 'ch_alti3d'], 'resolution': '20 cm', 'source': 'SITG (LiDAR 2025)'},
    {'id': 'CH-GL', 'name': 'Glarus', **_ALTI},
    {'id': 'CH-GR', 'name': 'Graubünden', **_ALTI},
    {'id': 'CH-JU', 'name': 'Jura', **_ALTI},
    {'id': 'CH-LU', 'name': 'Luzern', **_ALTI},
    {'id': 'CH-NE', 'name': 'Neuenburg', **_ALTI},
    {'id': 'CH-NW', 'name': 'Nidwalden', **_ALTI},
    {'id': 'CH-OW', 'name': 'Obwalden', **_ALTI},
    {'id': 'CH-SH', 'name': 'Schaffhausen', **_ALTI},
    {'id': 'CH-SZ', 'name': 'Schwyz', **_ALTI},
    {'id': 'CH-SO', 'name': 'Solothurn', 'layers': ['so_dtm025', 'ch_alti3d'], 'resolution': '25 cm', 'source': 'Kanton Solothurn (LiDAR 2019); Norden swissALTI3D'},
    {'id': 'CH-SG', 'name': 'St. Gallen', **_ALTI},
    {'id': 'CH-TI', 'name': 'Tessin', **_ALTI},
    {'id': 'CH-TG', 'name': 'Thurgau', **_ALTI},
    {'id': 'CH-UR', 'name': 'Uri', **_ALTI},
    {'id': 'CH-VS', 'name': 'Wallis', **_ALTI},
    {'id': 'CH-VD', 'name': 'Waadt', **_ALTI},
    {'id': 'CH-ZG', 'name': 'Zug', **_ALTI},
    {'id': 'CH-ZH', 'name': 'Zürich', 'layers': ['zh_dtm025', 'ch_alti3d'], 'resolution': '25 cm', 'source': 'Kanton Zürich (LiDAR 2022)'},
    {'id': 'LI', 'name': 'Liechtenstein', **_ALTI},
]
