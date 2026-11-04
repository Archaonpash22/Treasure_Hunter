# This module contains the terrain layer definitions and geographical bounds for Ireland (Republic; Northern
# Ireland belongs to the UK).
# Checked 2026-10-19: Ireland has no nationwide open LiDAR model yet. Geological Survey Ireland (GSI) serves
# the LiDAR it has collected from several agencies as hillshade ImageServers (gsi.geodata.gov.ie/imagehost,
# EPSG:3857 export, no key, CC BY 4.0): Heritage/Discovery Programme blocks 0.125-1 m (Brú na Bóinne,
# Rathcroghan region, Sligo ...), GSI Phase 2 1 m (small blocks in Galway/Mayo/Roscommon), OPW coastal 2 m,
# TII road corridors 2 m, Westmeath 25 cm (Uisneach) and the OPW NASC survey 2 m, which is only published as
# a surface model (DSM: buildings and trees included). By download-tile footprint about 19 % of the country
# has a LiDAR DTM and 31 % any LiDAR. Mapterhorn holds no Irish source, so elsewhere only Copernicus
# GLO-30 (30 m, a surface model) shows. The TII and Phase 2 services declare no NoData value and paint the
# area without data opaque black; their URL therefore carries 'noData=0' (see below).
# Not used: OPW Cork 12.5 cm (city, coarse TIN artefacts), NYU Dublin DSM 1 m and the photogrammetric
# DSM 25 cm (tiny surface models).
import json
import os

bounds = {
    "ireland": [[51.4, -10.7], [55.45, -5.98]]
}

# The 26 counties (ISO 3166-2 IE-CW .. IE-WW) and the national outline as [lat, lon] rings (Tailte Éireann,
# Counties - National Statutory Boundaries 2019, generalised 20 m, CC BY 4.0; counties simplified to 50 m
# with shared borders, islands below 2 ha left out, the national outline (their union) to 100 m).
with open(os.path.join(os.path.dirname(__file__), "ireland_regions.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

REGIONS = ['IE-CE', 'IE-CN', 'IE-CO', 'IE-CW', 'IE-D', 'IE-DL', 'IE-G', 'IE-KE', 'IE-KK', 'IE-KY', 'IE-LD', 'IE-LH',
           'IE-LK', 'IE-LM', 'IE-LS', 'IE-MH', 'IE-MN', 'IE-MO', 'IE-OY', 'IE-RN', 'IE-SO', 'IE-TA', 'IE-WD', 'IE-WH',
           'IE-WW', 'IE-WX']
_MT = 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp'
_GSI = 'https://gsi.geodata.gov.ie/imagehost/rest/services/Lidar/IE_GSI_LiDAR_'
# The app appends '/exportImage?f=image&...' to the URL. For services without a NoData value the URL ends
# in 'exportImage?noData=0&f=image&_=': the appended path then lands in the dummy parameter '_', the server
# still answers exportImage and black (0) becomes transparent.
_NODATA0 = '/exportImage?noData=0&f=image&_='
_CC = 'Contains Irish Public Sector Data (Geological Survey Ireland'


def _gsi(service, clip, native, attribution, nodata_fix=False):
    return {
        'type': 'arcgis_image',
        'url': _GSI + service + '_ITM_MH_TIFF/ImageServer' + (_NODATA0 if nodata_fix else ''),
        'options': {
            'clipTo': clip, 'imageFormat': 'png', 'tileSize': 512, 'retryBlank': False,
            'maxZoom': 20, 'maxNativeZoom': native, 'attribution': attribution
        }
    }


terrain_layers = {
    # Westmeath County Council 25 cm (Hill of Uisneach, 2020), ~1.4 s per 512 px tile.
    'ie_wm025': _gsi('DTM_HS_WMCoCo_25cm_Westmeath', ['IE-WH'], 19,
                     'LiDAR DTM 25 cm Schummerung: ' + _CC + ' &amp; Westmeath County Council), CC BY 4.0'),
    # GSI / Dept. of Culture, Heritage / Discovery Programme / Heritage Council, 0.125-1 m: heritage
    # landscapes in 13 counties (Brú na Bóinne, Sligo, Roscommon, Cork, Kerry blocks ...), 0.5-7.7 s.
    'ie_heritage': _gsi('DTM_HS_GSI_DCHG_DP_MS_IE26',
                        ['IE-CO', 'IE-G', 'IE-KE', 'IE-KK', 'IE-KY', 'IE-LH', 'IE-LM', 'IE-LS', 'IE-MH', 'IE-MO',
                         'IE-OY', 'IE-RN', 'IE-SO'], 19,
                        'LiDAR DTM 0,125-1 m Schummerung: ' + _CC + ', DCHG, Discovery Programme, Heritage Council), CC BY 4.0'),
    # GSI Phase 2 1 m (2018, small blocks in the west), ~0.6-2.9 s; no NoData value (see above).
    'ie_gsi1m': _gsi('DTM_HS_GSI_Phase2_1m_IE26', ['IE-CE', 'IE-G', 'IE-LD', 'IE-MO', 'IE-RN'], 17,
                     'LiDAR DTM 1 m Schummerung: ' + _CC + '), CC BY 4.0', nodata_fix=True),
    # OPW coastal / flood survey 2 m (Blom 2006-07), ~0.4-0.6 s.
    'ie_opw2m': _gsi('DTM_HS_OPW_2m_IE26',
                     ['IE-CE', 'IE-CO', 'IE-D', 'IE-G', 'IE-KK', 'IE-KY', 'IE-LK', 'IE-SO', 'IE-WD', 'IE-WW', 'IE-WX'], 16,
                     'LiDAR DTM 2 m Schummerung: ' + _CC + ' &amp; the Office of Public Works), CC BY 4.0'),
    # TII road corridors 2 m (2010-11, all counties), ~0.3-2 s; no NoData value (see above).
    'ie_tii2m': _gsi('DTM_HS_TII_2m_IE26', REGIONS, 16,
                     'LiDAR DTM 2 m Schummerung: ' + _CC + ' &amp; Transport Infrastructure Ireland), CC BY 4.0',
                     nodata_fix=True),
    # OPW National Aerial Survey Contract 2 m (2011-12, ~13 800 km2), surface model with buildings and trees,
    # ~0.4-1.2 s. Below the terrain models, above GLO-30.
    'ie_nasc_dsm': _gsi('DSM_HS_OPW_NASC_IE26_2m', REGIONS, 16,
                        'LiDAR DSM 2 m Schummerung (Oberfläche): ' + _CC + ' &amp; the Office of Public Works), CC BY 4.0'),
    # Base: Copernicus GLO-30 (30 m) via Mapterhorn, up to grid 12 (= zoom 13), always underneath.
    'ie_glo30': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': ['ireland'], 'fallbackFor': REGIONS, 'fallbackFrom': 99, 'tileSize': 512,
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
    "ireland": {
        "12": ['ie_wm025', 'ie_heritage', 'ie_gsi1m', 'ie_opw2m', 'ie_tii2m', 'ie_nasc_dsm', 'ie_glo30'],
        "0": ['ie_glo30'],
    }
}

country = {'id': 'IE', 'name': 'Irland'}
base_relief = {'layers': ['ie_glo30'], 'name': 'Grundrelief', 'resolution': '30 m', 'source': 'Copernicus via Mapterhorn'}
# Shares by GSI download-tile footprint (the TII corridors themselves are narrower than their 2 km tiles).
regions = [
    {'id': 'IE-CW', 'name': 'Carlow', 'layers': ['ie_tii2m', 'ie_nasc_dsm'], 'resolution': '2 m',
     'source': 'GSI LiDAR: TII 2 m ~21 %, DSM 2 m ~28 %; sonst GLO-30'},
    {'id': 'IE-CN', 'name': 'Cavan', 'layers': ['ie_tii2m', 'ie_nasc_dsm'], 'resolution': '2 m',
     'source': 'GSI LiDAR: TII 2 m ~9 %, DSM 2 m ~8 %; sonst GLO-30'},
    {'id': 'IE-CE', 'name': 'Clare', 'layers': ['ie_gsi1m', 'ie_opw2m', 'ie_tii2m', 'ie_nasc_dsm'], 'resolution': '1 m',
     'source': 'GSI LiDAR: GSI 1 m ~2 %, OPW 2 m ~4 %, TII 2 m ~10 %, DSM 2 m ~17 %; sonst GLO-30'},
    {'id': 'IE-CO', 'name': 'Cork', 'layers': ['ie_heritage', 'ie_opw2m', 'ie_tii2m', 'ie_nasc_dsm'], 'resolution': '0,1-1 m',
     'source': 'GSI LiDAR: Heritage 0,125-1 m ~4 %, OPW 2 m ~5 %, TII 2 m ~14 %, DSM 2 m ~7 %; sonst GLO-30'},
    {'id': 'IE-DL', 'name': 'Donegal', 'layers': ['ie_tii2m', 'ie_nasc_dsm'], 'resolution': '2 m',
     'source': 'GSI LiDAR: TII 2 m ~10 %, DSM 2 m ~16 %; sonst GLO-30'},
    {'id': 'IE-D', 'name': 'Dublin', 'layers': ['ie_opw2m', 'ie_tii2m', 'ie_nasc_dsm'], 'resolution': '2 m',
     'source': 'GSI LiDAR: OPW 2 m <1 %, TII 2 m ~42 %, DSM 2 m ~59 %; sonst GLO-30'},
    {'id': 'IE-G', 'name': 'Galway', 'layers': ['ie_heritage', 'ie_gsi1m', 'ie_opw2m', 'ie_tii2m', 'ie_nasc_dsm'],
     'resolution': '0,1-1 m',
     'source': 'GSI LiDAR: Heritage 0,125-1 m ~4 %, GSI 1 m ~4 %, OPW 2 m ~1 %, TII 2 m ~11 %, DSM 2 m ~17 %; sonst GLO-30'},
    {'id': 'IE-KY', 'name': 'Kerry', 'layers': ['ie_heritage', 'ie_opw2m', 'ie_tii2m', 'ie_nasc_dsm'], 'resolution': '0,1-1 m',
     'source': 'GSI LiDAR: Heritage 0,125-1 m ~3 %, OPW 2 m ~4 %, TII 2 m ~11 %, DSM 2 m ~19 %; sonst GLO-30'},
    {'id': 'IE-KE', 'name': 'Kildare', 'layers': ['ie_heritage', 'ie_tii2m', 'ie_nasc_dsm'], 'resolution': '2 m',
     'source': 'GSI LiDAR: Heritage <1 %, TII 2 m ~23 %, DSM 2 m ~60 %; sonst GLO-30'},
    {'id': 'IE-KK', 'name': 'Kilkenny', 'layers': ['ie_heritage', 'ie_opw2m', 'ie_tii2m', 'ie_nasc_dsm'], 'resolution': '2 m',
     'source': 'GSI LiDAR: Heritage <1 %, OPW 2 m ~1 %, TII 2 m ~24 %, DSM 2 m ~20 %; sonst GLO-30'},
    {'id': 'IE-LS', 'name': 'Laois', 'layers': ['ie_heritage', 'ie_tii2m', 'ie_nasc_dsm'], 'resolution': '0,1-1 m',
     'source': 'GSI LiDAR: Heritage 0,125-1 m ~1 %, TII 2 m ~19 %, DSM 2 m ~18 %; sonst GLO-30'},
    {'id': 'IE-LM', 'name': 'Leitrim', 'layers': ['ie_heritage', 'ie_tii2m', 'ie_nasc_dsm'], 'resolution': '0,1-1 m',
     'source': 'GSI LiDAR: Heritage 0,125-1 m ~2 %, TII 2 m ~6 %, DSM 2 m ~16 %; sonst GLO-30'},
    {'id': 'IE-LK', 'name': 'Limerick', 'layers': ['ie_opw2m', 'ie_tii2m', 'ie_nasc_dsm'], 'resolution': '2 m',
     'source': 'GSI LiDAR: OPW 2 m ~7 %, TII 2 m ~19 %, DSM 2 m ~35 %; sonst GLO-30'},
    {'id': 'IE-LD', 'name': 'Longford', 'layers': ['ie_gsi1m', 'ie_tii2m', 'ie_nasc_dsm'], 'resolution': '1 m',
     'source': 'GSI LiDAR: GSI 1 m ~3 %, TII 2 m ~14 %, DSM 2 m ~21 %; sonst GLO-30'},
    {'id': 'IE-LH', 'name': 'Louth', 'layers': ['ie_heritage', 'ie_tii2m', 'ie_nasc_dsm'], 'resolution': '0,1-1 m',
     'source': 'GSI LiDAR: Heritage 0,125-1 m ~5 %, TII 2 m ~37 %, DSM 2 m ~44 %; sonst GLO-30'},
    {'id': 'IE-MO', 'name': 'Mayo', 'layers': ['ie_heritage', 'ie_gsi1m', 'ie_tii2m', 'ie_nasc_dsm'], 'resolution': '0,1-1 m',
     'source': 'GSI LiDAR: Heritage 0,125-1 m ~1 %, GSI 1 m ~2 %, TII 2 m ~6 %, DSM 2 m ~12 %; sonst GLO-30'},
    {'id': 'IE-MH', 'name': 'Meath', 'layers': ['ie_heritage', 'ie_tii2m', 'ie_nasc_dsm'], 'resolution': '0,1-1 m',
     'source': 'GSI LiDAR: Heritage 0,125-1 m ~8 % (Brú na Bóinne), TII 2 m ~21 %, DSM 2 m ~28 % (Tara); sonst GLO-30'},
    {'id': 'IE-MN', 'name': 'Monaghan', 'layers': ['ie_tii2m', 'ie_nasc_dsm'], 'resolution': '2 m',
     'source': 'GSI LiDAR: TII 2 m ~23 %, DSM 2 m ~16 %; sonst GLO-30'},
    {'id': 'IE-OY', 'name': 'Offaly', 'layers': ['ie_heritage', 'ie_tii2m', 'ie_nasc_dsm'], 'resolution': '0,1-1 m',
     'source': 'GSI LiDAR: Heritage 0,125-1 m ~2 %, TII 2 m ~9 %, DSM 2 m ~31 %; sonst GLO-30'},
    {'id': 'IE-RN', 'name': 'Roscommon', 'layers': ['ie_heritage', 'ie_gsi1m', 'ie_tii2m', 'ie_nasc_dsm'], 'resolution': '0,1-1 m',
     'source': 'GSI LiDAR: Heritage 0,125-1 m ~7 %, GSI 1 m ~1 %, TII 2 m ~11 %, DSM 2 m ~20 %; sonst GLO-30 '
               '(Rathcroghan selbst ohne LiDAR)'},
    {'id': 'IE-SO', 'name': 'Sligo', 'layers': ['ie_heritage', 'ie_opw2m', 'ie_tii2m', 'ie_nasc_dsm'], 'resolution': '0,1-1 m',
     'source': 'GSI LiDAR: Heritage 0,125-1 m ~18 %, OPW 2 m ~5 %, TII 2 m ~19 %, DSM 2 m ~18 %; sonst GLO-30'},
    {'id': 'IE-TA', 'name': 'Tipperary', 'layers': ['ie_tii2m', 'ie_nasc_dsm'], 'resolution': '2 m',
     'source': 'GSI LiDAR: TII 2 m ~17 %, DSM 2 m ~6 %; sonst GLO-30'},
    {'id': 'IE-WD', 'name': 'Waterford', 'layers': ['ie_opw2m', 'ie_tii2m', 'ie_nasc_dsm'], 'resolution': '2 m',
     'source': 'GSI LiDAR: OPW 2 m ~18 %, TII 2 m ~15 %, DSM 2 m ~20 %; sonst GLO-30'},
    {'id': 'IE-WH', 'name': 'Westmeath', 'layers': ['ie_wm025', 'ie_tii2m', 'ie_nasc_dsm'], 'resolution': '25 cm',
     'source': 'GSI LiDAR: Westmeath 25 cm ~1 % (Uisneach), TII 2 m ~24 %, DSM 2 m ~11 %; sonst GLO-30'},
    {'id': 'IE-WX', 'name': 'Wexford', 'layers': ['ie_opw2m', 'ie_tii2m', 'ie_nasc_dsm'], 'resolution': '2 m',
     'source': 'GSI LiDAR: OPW 2 m ~17 %, TII 2 m ~19 %, DSM 2 m ~22 %; sonst GLO-30'},
    {'id': 'IE-WW', 'name': 'Wicklow', 'layers': ['ie_opw2m', 'ie_tii2m', 'ie_nasc_dsm'], 'resolution': '2 m',
     'source': 'GSI LiDAR: OPW 2 m ~6 %, TII 2 m ~11 %, DSM 2 m ~23 %; sonst GLO-30'},
]
