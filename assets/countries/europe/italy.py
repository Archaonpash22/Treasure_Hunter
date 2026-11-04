# This module contains the terrain layer definitions and geographical bounds for Italy.
# Checked region by region on 2026-10-19 (see LIDAR_TODO.md). Every regional layer is cut to its
# region (ISTAT boundaries), so neighbouring sources never overlap; TINITALY fills the rest.
import json
import os

# Bounding box of the country; the outline below decides what is "in Italy".
bounds = {
    "italy": [[35.4, 6.6], [47.1, 18.6]]
}

# Regions and the two autonomous provinces as [lat, lon] rings (ISTAT "Confini delle unità
# amministrative" 01.01.2026, CC BY 4.0; simplified to 25 m with shared borders) plus "italy"
# (national outline, 100 m).
with open(os.path.join(os.path.dirname(__file__), "italy_regions.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

REGIONS = ['IT-21', 'IT-23', 'IT-25', 'IT-BZ', 'IT-TN', 'IT-34', 'IT-36', 'IT-42', 'IT-45', 'IT-52', 'IT-55',
           'IT-57', 'IT-62', 'IT-65', 'IT-67', 'IT-72', 'IT-75', 'IT-77', 'IT-78', 'IT-82', 'IT-88']

_ER_IMAGE_SERVICES = 'https://servizigis.regione.emilia-romagna.it/arcgis/rest/services/public/'
# Regione Toscana "Geoscopio" morphology WMS. Every image carries a vertical source-credit
# watermark along its left edge; 'wms_crop' requests a wider image and crops that strip away.
_TOSCANA_WMS = 'https://www502.regione.toscana.it/wmsraster/com.rt.wms.RTmap/wms?map=wmsmorfologia'
_MAPTERHORN = 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp'


def _er_lidar(service, attribution):
    """Emilia-Romagna 0.5 m LiDAR DTM ImageServer, multidirectional hillshade rendered by the server."""
    return {
        'type': 'arcgis_image',
        'url': _ER_IMAGE_SERVICES + service + '/ImageServer',
        'options': {
            'clipTo': ['IT-45'],
            'renderingRule': {'rasterFunction': 'Hillshade',
                              'rasterFunctionArguments': {'HillshadeType': 1, 'ZFactor': 1}},
            'imageFormat': 'png',
            'tileSize': 512,
            'retryBlank': False,
            'maxZoom': 20,
            'maxNativeZoom': 18,
            'attribution': attribution
        }
    }


def _mapterhorn(code, max_native, attribution):
    """Mapterhorn height tiles for one region, shaded locally (dem_shade.py)."""
    return {
        'type': 'dem_terrarium',
        'url': _MAPTERHORN,
        'options': {
            'clipTo': [code],
            'tileSize': 512,
            'retryBlank': False,
            'maxZoom': 20,
            'maxNativeZoom': max_native,
            'attribution': attribution + ' via &copy; Mapterhorn (Schummerung berechnet)'
        }
    }


# maxNativeZoom matches the data: 0.5 m -> 18, 1 m -> 17, 2 m -> 16, 5 m -> 15, 10 m -> 14.
terrain_layers = {
    # Country-wide base: TINITALY 10 m DEM hillshade (INGV, CC BY 4.0), covers every island.
    'it_dtm': {
        'url': 'https://tinitaly.pi.ingv.it/TINItaly_1_1/wms?',
        'options': {
            'clipTo': ['italy'],
            'fallbackFor': REGIONS,
            'fallbackFrom': 14,
            'layers': 'tinitaly_hshd',
            'format': 'image/png',
            'transparent': True,
            'version': '1.3.0',
            'tileSize': 512,
            'maxZoom': 20,
            'maxNativeZoom': 14,
            'attribution': 'TINITALY 10 m &copy; INGV (CC BY 4.0)'
        }
    },
    # --- Südtirol: 0.5 m in the valleys and settlements (transparent elsewhere) over 2.5 m everywhere
    'bz_dtm05': {
        'url': 'https://geoservices.buergernetz.bz.it/mapproxy/wms',
        'options': {
            'clipTo': ['IT-BZ'], 'layers': 'p_bz-Elevation:DigitalTerrainModel-0.5m-Hillshade',
            'format': 'image/png', 'transparent': True, 'version': '1.3.0', 'tileSize': 512, 'retryBlank': False,
            'maxZoom': 20, 'maxNativeZoom': 18,
            'attribution': 'DGM 0,5 m &copy; Autonome Provinz Bozen – Südtirol (CC0)'
        }
    },
    'bz_dtm25': {
        'url': 'https://geoservices.buergernetz.bz.it/mapproxy/wms',
        'options': {
            'clipTo': ['IT-BZ'], 'layers': 'p_bz-Elevation:DigitalTerrainModel-2.5m-Hillshade',
            'format': 'image/png', 'transparent': True, 'version': '1.3.0', 'tileSize': 512, 'retryBlank': False,
            'maxZoom': 20, 'maxNativeZoom': 16,
            'attribution': 'DGM 2,5 m &copy; Autonome Provinz Bozen – Südtirol (CC0)'
        }
    },
    # --- Trentino: LiDAR PAT 2014/2018 hillshade for the whole province (opaque outside: clipped)
    'tn_lidar': {
        'url': 'https://siat.provincia.tn.it/geoserver/stem/ows',
        'options': {
            'clipTo': ['IT-TN'], 'layers': 'dtm_315_wg', 'format': 'image/jpeg', 'transparent': False,
            'version': '1.3.0', 'tileSize': 512, 'retryBlank': False, 'maxZoom': 20, 'maxNativeZoom': 17,
            'attribution': 'LiDAR PAT 2014/2018 &copy; Provincia autonoma di Trento – SIAT'
        }
    },
    # --- Friuli Venezia Giulia: LiDAR 2017-20 DTM 0.5 m hillshade, whole region (sea and abroad black)
    'fvg_lidar': {
        'url': 'https://irdat-ortofoto.regione.fvg.it/geoserver/ortofoto/ows',
        'options': {
            'clipTo': ['IT-36'], 'layers': 'Hillshade', 'format': 'image/jpeg', 'transparent': False,
            'version': '1.3.0', 'tileSize': 512, 'retryBlank': False, 'maxZoom': 20, 'maxNativeZoom': 17,
            'attribution': 'LiDAR DTM 0,5 m 2017-20 &copy; Regione Autonoma FVG – IRDAT'
        }
    },
    # --- Emilia-Romagna: four 0.5 m LiDAR surveys (together ~70 % of the region) over the 5 m DTM
    'er_lidar_2025': _er_lidar('DtmRER2025_26', 'LiDAR DTM 0,5 m RER 2025-26 &copy; Regione Emilia-Romagna (CC BY 4.0)'),
    'er_lidar_2022': _er_lidar('DtmRER2022', 'LiDAR DTM 0,5 m RER 2022 &copy; Regione Emilia-Romagna (CC BY 4.0)'),
    'er_lidar_05m': _er_lidar('DtmRER2023_24', 'LiDAR DTM 0,5 m RER 2023-24 &copy; Regione Emilia-Romagna (CC BY 4.0)'),
    'er_lidar_bo': _er_lidar('Dtm_comune_BO_2023', 'LiDAR DTM Comune di Bologna 2023 &copy; Regione Emilia-Romagna (CC BY 4.0)'),
    'er_dtm5m': {
        'type': 'arcgis_image',
        'url': _ER_IMAGE_SERVICES + 'Dtm5x5/ImageServer',
        'options': {
            'clipTo': ['IT-45'],
            'renderingRule': {'rasterFunction': 'Hillshade',
                              'rasterFunctionArguments': {'Azimuth': 315, 'Altitude': 45, 'ZFactor': 1}},
            'imageFormat': 'png', 'tileSize': 512, 'retryBlank': False, 'maxZoom': 20, 'maxNativeZoom': 15,
            'attribution': 'DTM 5 m &copy; Regione Emilia-Romagna (CC BY 4.0)'
        }
    },
    # --- Toscana: 1 m LiDAR hillshade (centre, east, Versilia; served from zoom 13) over the 1 m DSM
    # 2021 (photogrammetric surface model with trees and buildings) which covers the whole region and
    # fills the LiDAR gaps (Apuan Alps, Garfagnana, Lunigiana, west coast, islands).
    'tos_lidar_1m': {
        'type': 'wms_crop',
        'url': _TOSCANA_WMS,
        'options': {
            'clipTo': ['IT-52'], 'layers': 'rt_morfologia.iddtm.1m.hs.irs', 'cropLeft': 32, 'tileSize': 512,
            'retryBlank': False, 'maxZoom': 20, 'maxNativeZoom': 17,
            'attribution': 'LiDAR DTM 1 m &copy; Regione Toscana / IRS (CC BY-NC-SA)'
        }
    },
    'tos_dsm_1m': {
        'type': 'wms_crop',
        'url': _TOSCANA_WMS,
        'options': {
            'clipTo': ['IT-52'], 'layers': 'rt_morfologia.iddsm2021.1m.hs.rt', 'cropLeft': 32, 'tileSize': 512,
            'retryBlank': False, 'maxZoom': 20, 'maxNativeZoom': 17,
            'attribution': 'DSM 1 m 2021 &copy; Regione Toscana'
        }
    },
    # --- Sardegna: 1 m DTM mosaic (coasts, towns, river corridors, Gallura/Campidano/Sulcis); STYLES must be 'raster'
    'sar_dtm1m': {
        'url': 'https://webgis.regione.sardegna.it/geoserverraster/ows',
        'options': {
            'clipTo': ['IT-88'], 'layers': 'raster:DTM_1M_MOSAICO_OMBRE', 'styles': 'raster', 'format': 'image/png',
            'transparent': True, 'version': '1.3.0', 'tileSize': 512, 'retryBlank': False, 'maxZoom': 20,
            'maxNativeZoom': 17,
            'attribution': 'DTM 1 m &copy; Regione Autonoma della Sardegna (CC BY 4.0)'
        }
    },
    # --- Campania: 5 m DTM (CTR 2020, photogrammetric), hillshade rendered by the ImageServer
    'cam_dtm5m': {
        'type': 'arcgis_image',
        'url': 'https://geomaps.regione.campania.it/server/rest/services/DG5009/CTR2020_DTM5K_tif/ImageServer',
        'options': {
            'clipTo': ['IT-72'], 'renderingRule': {'rasterFunction': 'Hillshade'}, 'imageFormat': 'png',
            'tileSize': 512, 'retryBlank': False, 'maxZoom': 20, 'maxNativeZoom': 15,
            'attribution': 'DTM 5 m (CTR 2020) &copy; Regione Campania (CC BY 4.0)'
        }
    },
    # --- Basilicata: 5 m DTM (CTR 1:5000), tinted hillshade
    'bas_dtm5m': {
        'url': 'https://rsdi.regione.basilicata.it/rbgeoserver2016/ows',
        'options': {
            'clipTo': ['IT-77'], 'layers': 'elevazione:dtm_hill_color_4326', 'format': 'image/png',
            'grayscale': True,   # the service tints the relief green-yellow
            'transparent': True, 'version': '1.3.0', 'tileSize': 512, 'retryBlank': False, 'maxZoom': 20,
            'maxNativeZoom': 15,
            'attribution': 'DTM 5 m &copy; Regione Basilicata – RSDI'
        }
    },
    # --- Mapterhorn where it holds better data than TINITALY
    'sic_dtm2m': _mapterhorn('IT-82', 16, 'MDT 2 m ATA 2012-13 &copy; Regione Siciliana – S.I.T.R. (CC BY 4.0)'),
    'vda_dtm2m': _mapterhorn('IT-23', 16, 'DTM 2 m &copy; Regione Autonoma Valle d\'Aosta (CC BY 4.0)'),
    'pie_dtm5m': _mapterhorn('IT-21', 15, 'DTM 5 m (ICE 2009-11) &copy; Regione Piemonte'),
    'lom_dtm5m': _mapterhorn('IT-25', 15, 'DTM 5 m &copy; Regione Lombardia (CC BY 4.0)'),
}

# Layer bounding boxes from the region outlines (the page skips layers out of view).
for _info in terrain_layers.values():
    _pts = [pt for code in _info['options']['clipTo'] for ring in outlines[code] for pt in ring]
    _info['options']['bounds'] = [[round(min(p[0] for p in _pts) - 0.01, 4), round(min(p[1] for p in _pts) - 0.01, 4)],
                                  [round(max(p[0] for p in _pts) + 0.01, 4), round(max(p[1] for p in _pts) + 0.01, 4)]]

# (layer key, first zoom), finest first; all are cut to their region, so they stack for the whole country.
_REGION_LAYERS = [
    ('bz_dtm05', 9), ('er_lidar_2025', 9), ('er_lidar_2022', 9), ('er_lidar_05m', 9), ('er_lidar_bo', 9),
    ('fvg_lidar', 9), ('tn_lidar', 9), ('sar_dtm1m', 10), ('tos_lidar_1m', 13), ('tos_dsm_1m', 15),
    ('bz_dtm25', 9), ('sic_dtm2m', 9), ('vda_dtm2m', 9), ('cam_dtm5m', 10), ('bas_dtm5m', 10),
    ('er_dtm5m', 10), ('pie_dtm5m', 10), ('lom_dtm5m', 10),
]


def _italy_logic():
    logic = {}
    for t in sorted({0} | {z for _, z in _REGION_LAYERS}):
        logic[str(t)] = [k for k, z in _REGION_LAYERS if t >= z] + ['it_dtm']
    return logic


layer_logic = {"italy": _italy_logic()}

# What the terrain panel lists (see germany.py).
country = {'id': 'IT', 'name': 'Italien'}
base_relief = {'layers': ['it_dtm'], 'name': 'Grundrelief', 'resolution': '10 m', 'source': 'INGV TINITALY'}
_NO_LIDAR = 'kein offener LiDAR-Dienst (geprüft 2026-10-19)'
regions = [
    {'id': 'IT-65', 'name': 'Abruzzen', 'layers': [], 'note': _NO_LIDAR},
    {'id': 'IT-23', 'name': 'Aostatal', 'layers': ['vda_dtm2m'], 'resolution': '2 m', 'source': 'Region via Mapterhorn'},
    {'id': 'IT-75', 'name': 'Apulien', 'layers': [], 'note': _NO_LIDAR},
    {'id': 'IT-77', 'name': 'Basilikata', 'layers': ['bas_dtm5m'], 'resolution': '5 m', 'source': 'RSDI'},
    {'id': 'IT-BZ', 'name': 'Südtirol (Bozen)', 'layers': ['bz_dtm05', 'bz_dtm25'], 'resolution': '50 cm',
     'source': 'Provinz Bozen (0,5 m in Tälern, sonst 2,5 m)'},
    {'id': 'IT-36', 'name': 'Friaul-Julisch Venetien', 'layers': ['fvg_lidar'], 'resolution': '50 cm', 'source': 'IRDAT FVG'},
    {'id': 'IT-45', 'name': 'Emilia-Romagna',
     'layers': ['er_lidar_2025', 'er_lidar_2022', 'er_lidar_05m', 'er_lidar_bo', 'er_dtm5m'], 'resolution': '50 cm',
     'source': 'Regione ER (0,5 m auf ~70 %, sonst 5 m)'},
    {'id': 'IT-78', 'name': 'Kalabrien', 'layers': [], 'note': 'Geoportal nicht erreichbar (2026-10-19)'},
    {'id': 'IT-72', 'name': 'Kampanien', 'layers': ['cam_dtm5m'], 'resolution': '5 m', 'source': 'Regione Campania'},
    {'id': 'IT-62', 'name': 'Latium', 'layers': [], 'note': _NO_LIDAR},
    {'id': 'IT-42', 'name': 'Ligurien', 'layers': [], 'note': _NO_LIDAR},
    {'id': 'IT-25', 'name': 'Lombardei', 'layers': ['lom_dtm5m'], 'resolution': '5 m', 'source': 'Region via Mapterhorn'},
    {'id': 'IT-57', 'name': 'Marken', 'layers': [], 'note': _NO_LIDAR},
    {'id': 'IT-67', 'name': 'Molise', 'layers': [], 'note': _NO_LIDAR},
    {'id': 'IT-21', 'name': 'Piemont', 'layers': ['pie_dtm5m'], 'resolution': '5 m', 'source': 'Region via Mapterhorn'},
    {'id': 'IT-88', 'name': 'Sardinien', 'layers': ['sar_dtm1m'], 'resolution': '1 m', 'source': 'Regione Sardegna (~50 %)'},
    {'id': 'IT-82', 'name': 'Sizilien', 'layers': ['sic_dtm2m'], 'resolution': '2 m', 'source': 'S.I.T.R. via Mapterhorn'},
    {'id': 'IT-52', 'name': 'Toskana', 'layers': ['tos_lidar_1m', 'tos_dsm_1m'], 'resolution': '1 m',
     'source': 'Regione Toscana (LiDAR, Lücken mit DSM)'},
    {'id': 'IT-TN', 'name': 'Trentino (Trient)', 'layers': ['tn_lidar'], 'resolution': '1 m', 'source': 'SIAT Trento'},
    {'id': 'IT-55', 'name': 'Umbrien', 'layers': [], 'note': _NO_LIDAR},
    {'id': 'IT-34', 'name': 'Venetien', 'layers': [], 'note': _NO_LIDAR},
]
