# This module contains the terrain layer definitions and geographical bounds for Croatia.
# Checked 2026-10-19: the State Geodetic Administration (DGU) serves a hillshade of its 1 m LiDAR terrain
# model (flown 2021-23) for the whole country except a strip along the Danube (flight restrictions).
import json
import os

bounds = {
    "croatia": [[42.3, 13.4], [46.6, 19.5]]
}

# Counties (ISO 3166-2 HR-01 .. HR-21, HR-21 = City of Zagreb) and the national border as [lat, lon]
# rings (DGU register of spatial units, INSPIRE AU, 18.10.2026, "Otvorena dozvola"; counties simplified
# to 25 m with shared borders, the national outline to 100 m; islands as their own rings).
with open(os.path.join(os.path.dirname(__file__), "croatia_regions.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

COUNTIES = [f'HR-{i:02d}' for i in range(1, 22)]

terrain_layers = {
    # Every image carries a "GEOPORTAL" watermark in its centre (~0.74 of the width): the tile is requested
    # 1300 px wider to the west and only its clean right-hand 512 px are drawn ('wms_crop').
    'hr_dmr': {
        'type': 'wms_crop',
        'url': 'https://geoportal.dgu.hr/services/dmr/ows',
        'options': {
            'clipTo': COUNTIES,
            'layers': 'Hillshade',
            'format': 'image/png',
            'transparent': True,
            'version': '1.3.0',
            'cropLeft': 1300,
            'tileSize': 512,
            'retryBlank': False,
            'maxZoom': 20,
            'maxNativeZoom': 17,
            'attribution': 'DMR LiDAR 2021-2023 &copy; Državna geodetska uprava (geoportal.dgu.hr)'
        }
    },
    # Base: Copernicus GLO-30 (30 m) via Mapterhorn, always under the LiDAR (fills the Danube strip).
    'hr_glo30': {
        'type': 'dem_terrarium',
        'url': 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp',
        'options': {
            'clipTo': ['croatia'],
            'fallbackFor': COUNTIES,
            'fallbackFrom': 99,
            'tileSize': 512,
            'retryBlank': False,
            'maxZoom': 20,
            'maxNativeZoom': 13,
            'attribution': 'Copernicus GLO-30 &copy; DLR/Airbus via &copy; Mapterhorn (Schummerung berechnet)'
        }
    },
}

for _info in terrain_layers.values():
    _pts = [pt for code in _info['options']['clipTo'] for ring in outlines[code] for pt in ring]
    _info['options']['bounds'] = [[round(min(p[0] for p in _pts) - 0.01, 4), round(min(p[1] for p in _pts) - 0.01, 4)],
                                  [round(max(p[0] for p in _pts) + 0.01, 4), round(max(p[1] for p in _pts) + 0.01, 4)]]

layer_logic = {
    "croatia": {
        "8": ['hr_dmr', 'hr_glo30'],
        "0": ['hr_glo30'],
    }
}

country = {'id': 'HR', 'name': 'Kroatien'}
base_relief = {'layers': ['hr_glo30'], 'name': 'Grundrelief', 'resolution': '30 m', 'source': 'Copernicus via Mapterhorn'}
_DMR = {'layers': ['hr_dmr'], 'resolution': '1 m', 'source': 'DGU (LiDAR 2021-23)'}
regions = [
    {'id': 'HR-07', 'name': 'Bjelovar-Bilogora', **_DMR},
    {'id': 'HR-12', 'name': 'Brod-Posavina', **_DMR},
    {'id': 'HR-19', 'name': 'Dubrovnik-Neretva', **_DMR},
    {'id': 'HR-21', 'name': 'Grad Zagreb', **_DMR},
    {'id': 'HR-18', 'name': 'Istrien', **_DMR},
    {'id': 'HR-04', 'name': 'Karlovac', **_DMR},
    {'id': 'HR-06', 'name': 'Koprivnica-Križevci', **_DMR},
    {'id': 'HR-02', 'name': 'Krapina-Zagorje', **_DMR},
    {'id': 'HR-09', 'name': 'Lika-Senj', **_DMR},
    {'id': 'HR-20', 'name': 'Međimurje', **_DMR},
    {'id': 'HR-14', 'name': 'Osijek-Baranja', **_DMR, 'source': 'DGU (ohne Ost-Baranja/Donau-Streifen)'},
    {'id': 'HR-11', 'name': 'Požega-Slawonien', **_DMR},
    {'id': 'HR-08', 'name': 'Primorje-Gorski kotar', **_DMR},
    {'id': 'HR-03', 'name': 'Sisak-Moslavina', **_DMR},
    {'id': 'HR-17', 'name': 'Split-Dalmatien', **_DMR},
    {'id': 'HR-15', 'name': 'Šibenik-Knin', **_DMR},
    {'id': 'HR-05', 'name': 'Varaždin', **_DMR},
    {'id': 'HR-10', 'name': 'Virovitica-Podravina', **_DMR},
    {'id': 'HR-16', 'name': 'Vukovar-Srijem', **_DMR, 'source': 'DGU (ohne Vukovar/Ilok, Donau-Streifen)'},
    {'id': 'HR-13', 'name': 'Zadar', **_DMR},
    {'id': 'HR-01', 'name': 'Zagreb (Gespanschaft)', **_DMR},
]
