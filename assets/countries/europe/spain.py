# This module contains the terrain layer definitions and geographical bounds for Spain.
# Checked 2026-10-19: IGN publishes no usable live heights or LiDAR hillshade; Mapterhorn holds the IGN
# PNOA-LiDAR models (MDT02 2 m everywhere, MDT50 0.5 m from the 3rd coverage 2022-25 in large parts).
# Finer or cleaner regional services: Catalonia (ICGC 0.5 m), Navarre (IDENA 0.5 m), Galicia (IDEG 1 m).
# Not used: Cantabria and the Canaries (non-commercial licences), the rest is not better than Mapterhorn.
import json
import os

bounds = {
    "spain": [[27.6, -18.2], [43.8, 4.4]]
}

# Autonomous communities + Ceuta/Melilla and the national outline as [lat, lon] rings (IGN BDDAE,
# CC BY 4.0 ign.es; regions simplified to 50 m with shared borders, outline to 100 m).
with open(os.path.join(os.path.dirname(__file__), "spain_regions.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

REGIONS = ['ES-AN', 'ES-AR', 'ES-AS', 'ES-CB', 'ES-CE', 'ES-CL', 'ES-CM', 'ES-CN', 'ES-CT', 'ES-EX', 'ES-GA',
           'ES-IB', 'ES-MC', 'ES-MD', 'ES-ML', 'ES-NC', 'ES-PV', 'ES-RI', 'ES-VC']
_MT = 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp'

terrain_layers = {
    'ct_icgc05': {
        'url': 'https://geoserveis.icgc.cat/servei/catalunya/elevacions-territorial/wms',
        'options': {
            'clipTo': ['ES-CT'], 'layers': 'model-elevacions-terreny-ombrejat-catalunya-lidar-50cm-2021-2023',
            'format': 'image/jpeg', 'transparent': False, 'version': '1.3.0', 'tileSize': 512, 'retryBlank': False,
            'maxZoom': 20, 'maxNativeZoom': 18,
            'attribution': 'MET 0,5 m LiDAR 2021-2023 &copy; ICGC, CC BY 4.0'
        }
    },
    'nc_idena05': {
        'url': 'https://idena.navarra.es/ogc/wms',
        'options': {
            'clipTo': ['ES-NC'], 'layers': 'mapa_relieve_bn', 'format': 'image/png', 'transparent': True,
            'version': '1.3.0', 'tileSize': 512, 'retryBlank': False, 'maxZoom': 20, 'maxNativeZoom': 18,
            'attribution': 'MDT LiDAR 2024 0,5 m - Servicio proporcionado por el Gobierno de Navarra (CC BY 4.0)'
        }
    },
    # The ImageServer is already a hillshade (no rendering rule needed).
    'ga_ideg1m': {
        'type': 'arcgis_image',
        'url': 'https://ideg.xunta.gal/servizos/rest/services/Elevacions/Sombreado_Mdt1_PNOA15_16_ImageServer/ImageServer',
        'options': {
            'clipTo': ['ES-GA'], 'imageFormat': 'png', 'tileSize': 512, 'retryBlank': False, 'maxZoom': 20,
            'maxNativeZoom': 17,
            'attribution': 'Sombreado MDT 1 m PNOA-LiDAR 2015-16 &copy; Xunta de Galicia (IET), CC BY 4.0 scne.es'
        }
    },
    # 0.5 m (MDT50, 3rd coverage) from zoom 18 where Mapterhorn has it; elsewhere it answers 404 and the
    # 2 m base shows. Some grid-17 tiles are only enlarged 2 m data (vertical stripes).
    'es_mdt05': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': REGIONS, 'transparentNoData': True, 'tileSize': 512, 'retryBlank': False,
            'maxZoom': 20, 'maxNativeZoom': 18,
            'attribution': 'MDT50 PNOA-LiDAR 3. cob. CC BY 4.0 scne.es via &copy; Mapterhorn (Schummerung berechnet)'
        }
    },
    # Base: MDT02 / MDT05 (PNOA-LiDAR, 2 m) via Mapterhorn, always underneath.
    'es_mdt02': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': ['spain'], 'fallbackFor': REGIONS, 'fallbackFrom': 99, 'tileSize': 512, 'retryBlank': False,
            'maxZoom': 20, 'maxNativeZoom': 16,
            'attribution': 'MDT02/MDT05 PNOA-LiDAR CC BY 4.0 scne.es via &copy; Mapterhorn (Schummerung berechnet)'
        }
    },
}

for _info in terrain_layers.values():
    _pts = [pt for code in _info['options']['clipTo'] for ring in outlines[code] for pt in ring]
    _info['options']['bounds'] = [[round(min(p[0] for p in _pts) - 0.01, 4), round(min(p[1] for p in _pts) - 0.01, 4)],
                                  [round(max(p[0] for p in _pts) + 0.01, 4), round(max(p[1] for p in _pts) + 0.01, 4)]]

layer_logic = {
    "spain": {
        "18": ['ct_icgc05', 'nc_idena05', 'es_mdt05', 'ga_ideg1m', 'es_mdt02'],
        "8": ['ct_icgc05', 'nc_idena05', 'ga_ideg1m', 'es_mdt02'],
        "0": ['es_mdt02'],
    }
}

country = {'id': 'ES', 'name': 'Spanien'}
base_relief = {'layers': ['es_mdt02'], 'name': 'Grundrelief', 'resolution': '2 m', 'source': 'IGN PNOA-LiDAR via Mapterhorn'}
_PNOA = {'layers': ['es_mdt05'], 'resolution': '2 m', 'source': 'IGN PNOA-LiDAR; 0,5 m ab Zoom 18, wo schon beflogen'}
regions = [
    {'id': 'ES-AN', 'name': 'Andalusien', **_PNOA},
    {'id': 'ES-AR', 'name': 'Aragonien', **_PNOA},
    {'id': 'ES-AS', 'name': 'Asturien', **_PNOA},
    {'id': 'ES-IB', 'name': 'Balearen', **_PNOA},
    {'id': 'ES-PV', 'name': 'Baskenland', **_PNOA},
    {'id': 'ES-CE', 'name': 'Ceuta', **_PNOA},
    {'id': 'ES-EX', 'name': 'Extremadura', **_PNOA},
    {'id': 'ES-GA', 'name': 'Galicien', 'layers': ['ga_ideg1m', 'es_mdt05'], 'resolution': '1 m',
     'source': 'Xunta de Galicia 1 m; 0,5 m ab Zoom 18, wo schon beflogen'},
    {'id': 'ES-CN', 'name': 'Kanaren', **_PNOA},
    {'id': 'ES-CB', 'name': 'Kantabrien', **_PNOA},
    {'id': 'ES-CM', 'name': 'Kastilien-La Mancha', **_PNOA},
    {'id': 'ES-CL', 'name': 'Kastilien und León', **_PNOA},
    {'id': 'ES-CT', 'name': 'Katalonien', 'layers': ['ct_icgc05'], 'resolution': '50 cm', 'source': 'ICGC (LiDAR 2021-23)'},
    {'id': 'ES-RI', 'name': 'La Rioja', **_PNOA},
    {'id': 'ES-MD', 'name': 'Madrid', **_PNOA},
    {'id': 'ES-ML', 'name': 'Melilla', **_PNOA},
    {'id': 'ES-MC', 'name': 'Murcia', **_PNOA},
    {'id': 'ES-NC', 'name': 'Navarra', 'layers': ['nc_idena05'], 'resolution': '50 cm', 'source': 'IDENA (LiDAR 2024)'},
    {'id': 'ES-VC', 'name': 'Valencia', **_PNOA},
]
