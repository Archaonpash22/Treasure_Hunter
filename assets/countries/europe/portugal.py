# This module contains the terrain layer definitions and geographical bounds for Portugal.
# Checked 2026-10-19: DGT publishes its LiDAR terrain models (MDT 50 cm / 2 m, flights 2024-25) only as
# downloads behind a login (CDD); there is no live WMS/WCS/hillshade of them. Mapterhorn holds the DGT
# MDT 50 cm for ~87 % of the mainland (missing: the north-east east of ~7.3 W - Bragança, eastern Guarda
# with the Côa valley, north-eastern Castelo Branco - and a small patch near Arouca), there GLO-30 shows.
# Madeira: 10 m via Mapterhorn. Azores: only Copernicus GLO-30 (regional models non-commercial / login).
import json
import os

bounds = {
    "portugal": [[29.9, -31.4], [42.2, -6.1]]
}

# Districts (ISO 3166-2 PT-01 .. PT-18), the autonomous regions PT-20 (Azores) and PT-30 (Madeira) and
# the national outline as [lat, lon] rings (DGT CAOP 2025, CC BY 4.0 dgterritorio.gov.pt; districts and
# islands simplified to 50 m with shared borders, the outline to 100 m; Viseu has a hole for the Guarda
# exclave).
with open(os.path.join(os.path.dirname(__file__), "portugal_regions.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

DISTRICTS = [f'PT-{i:02d}' for i in range(1, 19)]
_MT = 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp'

terrain_layers = {
    # DGT MDT 0.5 m (LiDAR 2024-25) via Mapterhorn: grid-17 tiles (0.46 m/px) are native. In the
    # north-east gap the tiles answer 404 and the GLO-30 base shows.
    'pt_mdt05': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': DISTRICTS, 'transparentNoData': True, 'tileSize': 512, 'retryBlank': False,
            'maxZoom': 20, 'maxNativeZoom': 18,
            'attribution': 'MDT 50 cm LiDAR &copy; Direção-Geral do Território, CC BY 4.0 via &copy; Mapterhorn '
                           '(Schummerung berechnet)'
        }
    },
    # Madeira MDT 10 m (grid 13); the Azores have nothing finer than the base, so they answer 404 here.
    'pt_ilhas': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': ['PT-20', 'PT-30'], 'transparentNoData': True, 'tileSize': 512, 'retryBlank': False,
            'maxZoom': 20, 'maxNativeZoom': 14,
            'attribution': 'MDT Madeira 10 m &copy; Instituto Geográfico Português, CC BY 4.0 via &copy; Mapterhorn (Schummerung berechnet)'
        }
    },
    # Base: Copernicus GLO-30 via Mapterhorn, always underneath (fills the north-east gap and the Azores).
    'pt_glo30': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': ['portugal'], 'fallbackFor': DISTRICTS + ['PT-20', 'PT-30'], 'fallbackFrom': 99,
            'tileSize': 512, 'retryBlank': False, 'maxZoom': 20, 'maxNativeZoom': 13,
            'attribution': 'Copernicus GLO-30 &copy; DLR/Airbus via &copy; Mapterhorn (Schummerung berechnet)'
        }
    },
}

for _info in terrain_layers.values():
    _pts = [pt for code in _info['options']['clipTo'] for ring in outlines[code] for pt in ring]
    _info['options']['bounds'] = [[round(min(p[0] for p in _pts) - 0.01, 4), round(min(p[1] for p in _pts) - 0.01, 4)],
                                  [round(max(p[0] for p in _pts) + 0.01, 4), round(max(p[1] for p in _pts) + 0.01, 4)]]

layer_logic = {
    "portugal": {
        "8": ['pt_mdt05', 'pt_ilhas', 'pt_glo30'],
        "0": ['pt_glo30'],
    }
}

country = {'id': 'PT', 'name': 'Portugal'}
base_relief = {'layers': ['pt_glo30'], 'name': 'Grundrelief', 'resolution': '30 m', 'source': 'Copernicus via Mapterhorn'}
_MDT = {'layers': ['pt_mdt05'], 'resolution': '50 cm', 'source': 'DGT LiDAR 2024-25 via Mapterhorn'}
_PART = {'layers': ['pt_mdt05'], 'resolution': '50 cm'}
regions = [
    {'id': 'PT-20', 'name': 'Azoren', 'layers': ['pt_ilhas'], 'resolution': '30 m', 'source': 'nur Copernicus GLO-30'},
    {'id': 'PT-01', 'name': 'Aveiro', **_MDT},
    {'id': 'PT-02', 'name': 'Beja', **_MDT},
    {'id': 'PT-03', 'name': 'Braga', **_MDT},
    {'id': 'PT-04', 'name': 'Bragança', **_PART, 'source': 'DGT 50 cm nur im äußersten Westen, sonst 30 m'},
    {'id': 'PT-05', 'name': 'Castelo Branco', **_PART, 'source': 'DGT 50 cm, Nordosten (Idanha/Penamacor) 30 m'},
    {'id': 'PT-06', 'name': 'Coimbra', **_MDT},
    {'id': 'PT-07', 'name': 'Évora', **_MDT},
    {'id': 'PT-08', 'name': 'Faro', **_MDT},
    {'id': 'PT-09', 'name': 'Guarda', **_PART, 'source': 'DGT 50 cm im Westen, Osten und Côa-Tal 30 m'},
    {'id': 'PT-10', 'name': 'Leiria', **_MDT},
    {'id': 'PT-11', 'name': 'Lissabon', **_MDT},
    {'id': 'PT-30', 'name': 'Madeira', 'layers': ['pt_ilhas'], 'resolution': '10 m', 'source': 'IGP via Mapterhorn'},
    {'id': 'PT-12', 'name': 'Portalegre', **_MDT},
    {'id': 'PT-13', 'name': 'Porto', **_MDT},
    {'id': 'PT-14', 'name': 'Santarém', **_MDT},
    {'id': 'PT-15', 'name': 'Setúbal', **_MDT},
    {'id': 'PT-16', 'name': 'Viana do Castelo', **_MDT},
    {'id': 'PT-17', 'name': 'Vila Real', **_PART, 'source': 'DGT 50 cm, schmaler Oststreifen 30 m'},
    {'id': 'PT-18', 'name': 'Viseu', **_MDT},
]
