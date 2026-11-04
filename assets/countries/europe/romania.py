# This module contains the terrain layer definitions and geographical bounds for Romania.
# Checked 2026-10-19: ANCPI's geoportal (geoportal.ancpi.ro, with the LAKI LiDAR viewer) does not resolve;
# after the e-Terra outage of August 2026 ANCPI restarts its platforms in stages and the geoportal is not
# back yet. There is no other open live elevation service. Mapterhorn holds the ANCPI LAKI II terrain model
# 0.5 m (LiDAR 2013-17, OGL-ROU-1.0) for a block in the west, roughly west of 23.8 E between 45.2 and
# 47.6 N: Arad, Bihor and Hunedoara completely, Alba ~80 %, Cluj ~1/3, Gorj, Caraș-Severin, Timiș partly,
# small edges of Sălaj, Satu Mare, Sibiu and Vâlcea. Its grid-16 tiles (~0.8 m/px) are native, grid 17
# answers 404; a faint square grid pattern of the source shows at zoom 17. Elsewhere only Copernicus
# GLO-30 (30 m, a surface model) shows. LAKI III (2019-23, 8 more counties) is not published openly.
import json
import os

bounds = {
    "romania": [[43.6, 20.25], [48.3, 29.75]]
}

# Counties (județe, ISO 3166-2 RO-AB .. RO-VN), Bucharest (RO-B) and the national border as [lat, lon]
# rings (ANCPI via OCHA COD-AB Romania, HDX, boundaries of 09.03.2022, CC BY-IGO; counties simplified to
# 50 m with shared borders, the national outline (their union) to 100 m; Bucharest is a hole ring in Ilfov).
with open(os.path.join(os.path.dirname(__file__), "romania_regions.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

REGIONS = ['RO-AB', 'RO-AG', 'RO-AR', 'RO-B', 'RO-BC', 'RO-BH', 'RO-BN', 'RO-BR', 'RO-BT', 'RO-BV', 'RO-BZ',
           'RO-CJ', 'RO-CL', 'RO-CS', 'RO-CT', 'RO-CV', 'RO-DB', 'RO-DJ', 'RO-GJ', 'RO-GL', 'RO-GR', 'RO-HD',
           'RO-HR', 'RO-IF', 'RO-IL', 'RO-IS', 'RO-MH', 'RO-MM', 'RO-MS', 'RO-NT', 'RO-OT', 'RO-PH', 'RO-SB',
           'RO-SJ', 'RO-SM', 'RO-SV', 'RO-TL', 'RO-TM', 'RO-TR', 'RO-VL', 'RO-VN', 'RO-VS']
LAKI_REGIONS = ['RO-AB', 'RO-AR', 'RO-BH', 'RO-CJ', 'RO-CS', 'RO-GJ', 'RO-HD', 'RO-SB', 'RO-SJ', 'RO-SM', 'RO-TM',
                'RO-VL']   # counties with LAKI II 0.5 m in Mapterhorn
_MT = 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp'

terrain_layers = {
    # LAKI II 0.5 m via Mapterhorn; outside the LiDAR block the tiles answer 404 and the base shows.
    'ro_laki': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': LAKI_REGIONS, 'transparentNoData': True, 'tileSize': 512, 'retryBlank': False,
            'maxZoom': 20, 'maxNativeZoom': 17,
            'attribution': 'LAKI II MNT 0,5 m &copy; ANCPI, OGL-ROU-1.0 via &copy; Mapterhorn (Schummerung berechnet)'
        }
    },
    # Base: Copernicus GLO-30 (30 m) via Mapterhorn, up to grid 12 (= zoom 13), always underneath.
    'ro_glo30': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': ['romania'], 'fallbackFor': REGIONS, 'fallbackFrom': 99, 'tileSize': 512,
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
    "romania": {
        "8": ['ro_laki', 'ro_glo30'],
        "0": ['ro_glo30'],
    }
}

country = {'id': 'RO', 'name': 'Rumänien'}
base_relief = {'layers': ['ro_glo30'], 'name': 'Grundrelief', 'resolution': '30 m', 'source': 'Copernicus via Mapterhorn'}
_NONE = {'layers': [], 'resolution': '30 m', 'source': 'nur Copernicus GLO-30',
         'note': 'kein offenes LiDAR (LAKI III nicht offen, ANCPI-Geoportal offline)'}
_LAKI = {'layers': ['ro_laki'], 'resolution': '50 cm', 'source': 'ANCPI LAKI II (LiDAR, Projekt 2013-17) via Mapterhorn'}
_EDGE = {'layers': ['ro_laki'], 'resolution': '30 m'}
regions = [
    {'id': 'RO-AB', 'name': 'Alba (Weißenburg)', **_LAKI, 'source': 'ANCPI LAKI II 0,5 m via Mapterhorn außer im Osten (~80 %)'},
    {'id': 'RO-AR', 'name': 'Arad', **_LAKI},
    {'id': 'RO-AG', 'name': 'Argeș', **_NONE},
    {'id': 'RO-BC', 'name': 'Bacău', **_NONE},
    {'id': 'RO-BH', 'name': 'Bihor', **_LAKI},
    {'id': 'RO-BN', 'name': 'Bistrița-Năsăud (Bistritz-Nassod)', **_NONE},
    {'id': 'RO-BT', 'name': 'Botoșani', **_NONE},
    {'id': 'RO-BR', 'name': 'Brăila', **_NONE},
    {'id': 'RO-BV', 'name': 'Brașov (Kronstadt)', **_NONE},
    {'id': 'RO-B', 'name': 'Bukarest', **_NONE},
    {'id': 'RO-BZ', 'name': 'Buzău', **_NONE},
    {'id': 'RO-CL', 'name': 'Călărași', **_NONE},
    {'id': 'RO-CS', 'name': 'Caraș-Severin', **_EDGE, 'source': 'GLO-30; LAKI II 0,5 m nur im Nordosten (~1/6)'},
    {'id': 'RO-CJ', 'name': 'Cluj (Klausenburg)', **_LAKI, 'source': 'ANCPI LAKI II 0,5 m im Südwesten (~1/3), sonst 30 m'},
    {'id': 'RO-CT', 'name': 'Constanța (Konstanza)', **_NONE},
    {'id': 'RO-CV', 'name': 'Covasna', **_NONE},
    {'id': 'RO-DB', 'name': 'Dâmbovița', **_NONE},
    {'id': 'RO-DJ', 'name': 'Dolj', **_NONE},
    {'id': 'RO-GL', 'name': 'Galați', **_NONE},
    {'id': 'RO-GR', 'name': 'Giurgiu', **_NONE},
    {'id': 'RO-GJ', 'name': 'Gorj', **_EDGE, 'source': 'GLO-30; LAKI II 0,5 m im gebirgigen Norden (~1/4)'},
    {'id': 'RO-HR', 'name': 'Harghita', **_NONE},
    {'id': 'RO-HD', 'name': 'Hunedoara (Eisenmarkt)', **_LAKI},
    {'id': 'RO-IL', 'name': 'Ialomița', **_NONE},
    {'id': 'RO-IS', 'name': 'Iași', **_NONE},
    {'id': 'RO-IF', 'name': 'Ilfov', **_NONE},
    {'id': 'RO-MM', 'name': 'Maramureș (Marmarosch)', **_NONE},
    {'id': 'RO-MH', 'name': 'Mehedinți', **_NONE},
    {'id': 'RO-MS', 'name': 'Mureș (Mieresch)', **_NONE},
    {'id': 'RO-NT', 'name': 'Neamț', **_NONE},
    {'id': 'RO-OT', 'name': 'Olt', **_NONE},
    {'id': 'RO-PH', 'name': 'Prahova', **_NONE},
    {'id': 'RO-SJ', 'name': 'Sălaj', **_EDGE, 'source': 'GLO-30; LAKI II 0,5 m nur am Westrand (~1/10)'},
    {'id': 'RO-SM', 'name': 'Satu Mare (Sathmar)', **_EDGE, 'source': 'GLO-30; LAKI II 0,5 m nur am Südrand (~1/20)'},
    {'id': 'RO-SB', 'name': 'Sibiu (Hermannstadt)', **_EDGE, 'source': 'GLO-30; LAKI II 0,5 m nur am Westrand (~1/15)'},
    {'id': 'RO-SV', 'name': 'Suceava', **_NONE},
    {'id': 'RO-TR', 'name': 'Teleorman', **_NONE},
    {'id': 'RO-TM', 'name': 'Timiș (Temesch)', **_EDGE, 'source': 'GLO-30; LAKI II 0,5 m nur am Nordrand (~1/7)'},
    {'id': 'RO-TL', 'name': 'Tulcea', **_NONE},
    {'id': 'RO-VL', 'name': 'Vâlcea', **_EDGE, 'source': 'GLO-30; LAKI II 0,5 m nur am Westrand (klein)'},
    {'id': 'RO-VS', 'name': 'Vaslui', **_NONE},
    {'id': 'RO-VN', 'name': 'Vrancea', **_NONE},
]
