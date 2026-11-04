# This module contains the terrain layer definitions and geographical bounds for Bulgaria.
# Checked 2026-10-19: Bulgaria has no open LiDAR terrain model and no open live elevation service. The
# Ministry of Agriculture's INSPIRE "Orthophoto and DEM" view service is restricted (INSPIRE Art. 13(1)(d))
# and its download service charges fees; the Geodesy, Cartography and Cadastre Agency (AGKK) publishes only
# cadastre, buildings, names and administrative units; the military geographic service (gis.armf.bg) was
# not reachable. Mapterhorn has no Bulgarian source (attribution.json 2026-10-19). So only Copernicus
# GLO-30 (30 m, a surface model: forests and buildings included) shows.
import json
import os

bounds = {
    "bulgaria": [[41.2, 22.3], [44.25, 28.65]]
}

# Provinces (oblasti, ISO 3166-2 BG-01 .. BG-28) and the national border as [lat, lon] rings (AGKK, INSPIRE
# Administrative Units, MapServer inspire.cadastre.bg Administrative_Unit, layer "2nd Order", 19.10.2026;
# provinces simplified to 50 m with shared borders, the national outline (their union) to 100 m).
with open(os.path.join(os.path.dirname(__file__), "bulgaria_regions.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

REGIONS = [f'BG-{i:02d}' for i in range(1, 29)]

terrain_layers = {
    # Base: Copernicus GLO-30 (30 m) via Mapterhorn, up to grid 12 (= zoom 13), enlarged above.
    'bg_glo30': {
        'type': 'dem_terrarium',
        'url': 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp',
        'options': {
            'clipTo': ['bulgaria'],
            'fallbackFor': REGIONS,
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
    "bulgaria": {
        "0": ['bg_glo30'],
    }
}

country = {'id': 'BG', 'name': 'Bulgarien'}
base_relief = {'layers': ['bg_glo30'], 'name': 'Grundrelief', 'resolution': '30 m', 'source': 'Copernicus via Mapterhorn'}
_NONE = {'layers': [], 'resolution': '30 m', 'source': 'nur Copernicus GLO-30', 'note': 'kein offenes LiDAR / DGM'}
regions = [
    {'id': 'BG-01', 'name': 'Blagoewgrad', **_NONE},
    {'id': 'BG-02', 'name': 'Burgas', **_NONE},
    {'id': 'BG-08', 'name': 'Dobritsch', **_NONE},
    {'id': 'BG-07', 'name': 'Gabrowo', **_NONE},
    {'id': 'BG-26', 'name': 'Haskowo', **_NONE},
    {'id': 'BG-28', 'name': 'Jambol', **_NONE},
    {'id': 'BG-09', 'name': 'Kardschali', **_NONE},
    {'id': 'BG-10', 'name': 'Kjustendil', **_NONE},
    {'id': 'BG-11', 'name': 'Lowetsch', **_NONE},
    {'id': 'BG-12', 'name': 'Montana', **_NONE},
    {'id': 'BG-13', 'name': 'Pasardschik', **_NONE},
    {'id': 'BG-14', 'name': 'Pernik', **_NONE},
    {'id': 'BG-15', 'name': 'Plewen', **_NONE},
    {'id': 'BG-16', 'name': 'Plowdiw', **_NONE},
    {'id': 'BG-17', 'name': 'Rasgrad', **_NONE},
    {'id': 'BG-18', 'name': 'Russe', **_NONE},
    {'id': 'BG-27', 'name': 'Schumen', **_NONE},
    {'id': 'BG-19', 'name': 'Silistra', **_NONE},
    {'id': 'BG-20', 'name': 'Sliwen', **_NONE},
    {'id': 'BG-21', 'name': 'Smoljan', **_NONE},
    {'id': 'BG-23', 'name': 'Sofia (Oblast)', **_NONE},
    {'id': 'BG-22', 'name': 'Sofia (Stadt)', **_NONE},
    {'id': 'BG-24', 'name': 'Stara Sagora', **_NONE},
    {'id': 'BG-25', 'name': 'Targowischte', **_NONE},
    {'id': 'BG-03', 'name': 'Warna', **_NONE},
    {'id': 'BG-04', 'name': 'Weliko Tarnowo', **_NONE},
    {'id': 'BG-05', 'name': 'Widin', **_NONE},
    {'id': 'BG-06', 'name': 'Wraza', **_NONE},
]
