# This module contains the terrain layer definitions and geographical bounds for Slovakia.
# Checked 2026-10-19: ÚGKK SR has LiDAR terrain models for the whole country: DMR 5.0 (1 m, ALS 2017-23)
# and, from the 2nd ALS cycle, DMR 6.0 (0.5 m, flown 2022-25 so far, about a quarter of the country in
# the west and centre). DMR 6.0 is only live as the hillshade cache of the ZBGIS MapServer "LLS_DMR6".
# For DMR 5.0 Mapterhorn holds the same 1 m model; its tiles come from a CDN and are faster and more
# reliable than the ZBGIS cache, which timed out under parallel load. The ZBGIS /export calls are
# pale, and DMR 6.0 /export sometimes answers with an empty image. The INSPIRE WCS (DMR 5.0 heights)
# takes 4-19 s per tile and shows resampling stripes, so it is not used.
import json
import os

bounds = {
    "slovakia": [[47.7, 16.8], [49.7, 22.6]]
}

# Regions (kraje, ISO 3166-2 SK-BC .. SK-ZI) and the national border as [lat, lon] rings (ÚGKK SR / GKÚ
# Bratislava, ZBGIS territorial and administrative units, basic level, as of 30.06.2026, CC BY 4.0;
# regions simplified to 25 m with shared borders, the national outline to 100 m).
with open(os.path.join(os.path.dirname(__file__), "slovakia_regions.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

REGIONS = ['SK-BC', 'SK-BL', 'SK-KI', 'SK-NI', 'SK-PV', 'SK-TA', 'SK-TC', 'SK-ZI']
DMR6_REGIONS = ['SK-BC', 'SK-BL', 'SK-NI', 'SK-TA', 'SK-TC', 'SK-ZI']   # regions with DMR 6.0 lots
_MT = 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp'

terrain_layers = {
    # DMR 6.0 0.5 m: cached hillshade (256 px, EPSG:3857, zoom 0-18) over a green-to-brown elevation
    # tint, which 'grayscale' removes. Outside the finished lots it answers with a small transparent
    # PNG, and from zoom 19 on with HTTP 503.
    'sk_dmr6': {
        'url': 'https://zbgis.skgeodesy.sk/zbgis/rest/services/LLS_DMR6/MapServer/tile/{z}/{y}/{x}',
        'options': {
            'clipTo': DMR6_REGIONS,
            'grayscale': True,
            'retryBlank': False,
            'maxZoom': 20,
            'maxNativeZoom': 18,
            'attribution': 'DMR 6.0 0,5 m (LLS 2. cyklus) &copy; ÚGKK SR, CC BY 4.0'
        }
    },
    # DMR 5.0 1 m for the whole country via Mapterhorn (its grid-16 tiles are native; grid 17 answers 404).
    'sk_dmr5': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': REGIONS,
            'tileSize': 512,
            'retryBlank': False,
            'maxZoom': 20,
            'maxNativeZoom': 17,
            'attribution': 'DMR 5.0 &copy; ÚGKK SR, CC BY 4.0 via &copy; Mapterhorn (Schummerung berechnet)'
        }
    },
    # Base: the same DMR 5.0 via Mapterhorn but coarser (3 m), always under the regional layers.
    'sk_base': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': ['slovakia'],
            'fallbackFor': REGIONS,
            'fallbackFrom': 99,
            'tileSize': 512,
            'retryBlank': False,
            'maxZoom': 20,
            'maxNativeZoom': 15,
            'attribution': 'DMR 5.0 &copy; ÚGKK SR, CC BY 4.0 via &copy; Mapterhorn (Schummerung berechnet)'
        }
    },
}

for _info in terrain_layers.values():
    _pts = [pt for code in _info['options']['clipTo'] for ring in outlines[code] for pt in ring]
    _info['options']['bounds'] = [[round(min(p[0] for p in _pts) - 0.01, 4), round(min(p[1] for p in _pts) - 0.01, 4)],
                                  [round(max(p[0] for p in _pts) + 0.01, 4), round(max(p[1] for p in _pts) + 0.01, 4)]]

layer_logic = {
    "slovakia": {
        "12": ['sk_dmr6', 'sk_dmr5', 'sk_base'],
        "8": ['sk_dmr5', 'sk_base'],
        "0": ['sk_base'],
    }
}

country = {'id': 'SK', 'name': 'Slowakei'}
base_relief = {'layers': ['sk_base'], 'name': 'Grundrelief', 'resolution': '3 m', 'source': 'ÚGKK DMR 5.0 via Mapterhorn'}
_DMR5 = {'layers': ['sk_dmr5'], 'resolution': '1 m', 'source': 'ÚGKK DMR 5.0 (LiDAR 2017-23) via Mapterhorn'}
_DMR6 = {'layers': ['sk_dmr6', 'sk_dmr5']}
regions = [
    {'id': 'SK-KI', 'name': 'Kaschau (Košice)', **_DMR5},
    {'id': 'SK-BC', 'name': 'Neusohl (Banská Bystrica)', **_DMR6, 'resolution': '1 m',
     'source': 'ÚGKK DMR 5.0; 0,5 m (DMR 6.0) im Westen: Neusohl, Kremnitz, Schemnitz'},
    {'id': 'SK-NI', 'name': 'Neutra (Nitra)', **_DMR6, 'resolution': '1 m',
     'source': 'ÚGKK DMR 5.0; 0,5 m (DMR 6.0) im Westen: Neutra, Neuhäusel'},
    {'id': 'SK-BL', 'name': 'Pressburg (Bratislava)', **_DMR6, 'resolution': '1 m',
     'source': 'ÚGKK DMR 5.0; 0,5 m (DMR 6.0) außer im Záhorie'},
    {'id': 'SK-PV', 'name': 'Preschau (Prešov)', **_DMR5},
    {'id': 'SK-ZI', 'name': 'Sillein (Žilina)', **_DMR6, 'resolution': '1 m',
     'source': 'ÚGKK DMR 5.0; 0,5 m (DMR 6.0) um Sillein und im Turz (Martin)'},
    {'id': 'SK-TC', 'name': 'Trentschin (Trenčín)', **_DMR6, 'resolution': '50 cm',
     'source': 'ÚGKK DMR 6.0 (LiDAR 2022-25) auf ~3/4, sonst DMR 5.0 1 m'},
    {'id': 'SK-TA', 'name': 'Tyrnau (Trnava)', **_DMR6, 'resolution': '50 cm',
     'source': 'ÚGKK DMR 6.0 (LiDAR 2022-25) auf ~3/4, sonst DMR 5.0 1 m (Záhorie)'},
]
