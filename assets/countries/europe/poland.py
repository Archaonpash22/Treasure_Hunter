# This module contains the terrain layer definitions and geographical bounds for Poland.
# Checked 2026-10-19: GUGiK has a nationwide LiDAR terrain model NMT 1 m (ISOK and later flights). Mapterhorn
# holds the same NMT 1 m (source "pl1") and serves it from a CDN in ~0.2-0.5 s per tile; only about a quarter
# of Masovia (east and west of Warsaw) and small blocks (Lipno, Gorzów, Oborniki, Piła) are missing
# there. GUGiK's own hillshade WMS (NMT GRID1 ShadedRelief) covers everything, answers EPSG:3857 although it
# does not advertise it, but takes 1-5 s per tile (up to 16 s in parallel), shows occasional seam lines
# and forbids automatic harvesting; it is used only to fill the Masovian gap. Below 1 m: the 5 m NMT
# (source "pl5") via Mapterhorn as the base.
import json
import os

bounds = {
    "poland": [[49.0, 14.1], [54.85, 24.15]]
}

# Voivodeships (ISO 3166-2 PL-02 .. PL-32 = TERYT codes) and the national border as [lat, lon] rings
# (GUGiK PRG - Państwowy Rejestr Granic, WFS AdministrativeBoundaries layer A01_Granice_wojewodztw,
# version 14.10.2026, free of charge under Art. 40a Prawo geodezyjne i kartograficzne; voivodeships
# simplified to 50 m with shared borders, the national outline (their union) to 100 m).
with open(os.path.join(os.path.dirname(__file__), "poland_regions.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

REGIONS = ['PL-02', 'PL-04', 'PL-06', 'PL-08', 'PL-10', 'PL-12', 'PL-14', 'PL-16', 'PL-18', 'PL-20', 'PL-22',
           'PL-24', 'PL-26', 'PL-28', 'PL-30', 'PL-32']
_MT = 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp'

terrain_layers = {
    # NMT 1 m via Mapterhorn: grid-16 tiles (0.7 m/px) are native, grid 17 answers 404. In the gaps
    # (see above) grid 15/16 answer 404 and the GUGiK hillshade or the 5 m base shows.
    'pl_nmt1': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': REGIONS, 'transparentNoData': True, 'tileSize': 512, 'retryBlank': False,
            'zFactor': 2.0,   # mostly flat lowland: stronger relief, as for the Netherlands
            'maxZoom': 20, 'maxNativeZoom': 17,
            'attribution': 'NMT 1 m &copy; GUGiK (geoportal.gov.pl) via &copy; Mapterhorn (Schummerung berechnet)'
        }
    },
    # GUGiK hillshade of the same NMT 1 m, only for Masovia (fills the Mapterhorn gap under pl_nmt1).
    # Requested as opaque JPEG: as PNG the brightest slopes come back see-through. Outside Poland it
    # answers white (the page cuts it to the region).
    'pl_gugik': {
        'url': 'https://mapy.geoportal.gov.pl/wss/service/PZGIK/NMT/GRID1/WMS/ShadedRelief',
        'options': {
            'clipTo': ['PL-14'], 'layers': 'Raster', 'format': 'image/jpeg', 'transparent': False,
            'version': '1.3.0', 'tileSize': 512, 'retryBlank': False, 'maxZoom': 20, 'maxNativeZoom': 17,
            'attribution': 'NMT 1 m Cieniowanie &copy; GUGiK (geoportal.gov.pl)'
        }
    },
    # Base: NMT 5 m (and the 1 m model, resampled) via Mapterhorn, always underneath.
    'pl_base': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': ['poland'], 'fallbackFor': REGIONS, 'fallbackFrom': 99, 'tileSize': 512,
            'retryBlank': False, 'maxZoom': 20, 'maxNativeZoom': 15,
            'attribution': 'NMT 5 m / 1 m &copy; GUGiK via &copy; Mapterhorn (Schummerung berechnet)'
        }
    },
}

for _info in terrain_layers.values():
    _pts = [pt for code in _info['options']['clipTo'] for ring in outlines[code] for pt in ring]
    _info['options']['bounds'] = [[round(min(p[0] for p in _pts) - 0.01, 4), round(min(p[1] for p in _pts) - 0.01, 4)],
                                  [round(max(p[0] for p in _pts) + 0.01, 4), round(max(p[1] for p in _pts) + 0.01, 4)]]

layer_logic = {
    "poland": {
        "12": ['pl_nmt1', 'pl_gugik', 'pl_base'],
        "8": ['pl_nmt1', 'pl_base'],
        "0": ['pl_base'],
    }
}

country = {'id': 'PL', 'name': 'Polen'}
base_relief = {'layers': ['pl_base'], 'name': 'Grundrelief', 'resolution': '3 m', 'source': 'GUGiK NMT via Mapterhorn'}
_NMT = {'layers': ['pl_nmt1'], 'resolution': '1 m', 'source': 'GUGiK NMT 1 m (LiDAR) via Mapterhorn'}
regions = [
    {'id': 'PL-28', 'name': 'Ermland-Masuren', **_NMT},
    {'id': 'PL-30', 'name': 'Großpolen (Wielkopolska)', **_NMT,
     'source': 'GUGiK NMT 1 m via Mapterhorn; kleine Lücken (bei Oborniki und Piła) nur 3 m'},
    {'id': 'PL-26', 'name': 'Heiligkreuz (Świętokrzyskie)', **_NMT},
    {'id': 'PL-18', 'name': 'Karpatenvorland (Podkarpackie)', **_NMT},
    {'id': 'PL-12', 'name': 'Kleinpolen (Małopolska)', **_NMT},
    {'id': 'PL-04', 'name': 'Kujawien-Pommern', **_NMT,
     'source': 'GUGiK NMT 1 m via Mapterhorn; schmaler Streifen bei Lipno/Rypin nur 3 m'},
    {'id': 'PL-08', 'name': 'Lebus (Lubuskie)', **_NMT,
     'source': 'GUGiK NMT 1 m via Mapterhorn; Gorzów Wielkopolski selbst nur 3 m'},
    {'id': 'PL-10', 'name': 'Lodz (Łódzkie)', **_NMT},
    {'id': 'PL-06', 'name': 'Lublin (Lubelskie)', **_NMT},
    {'id': 'PL-14', 'name': 'Masowien (Mazowieckie)', 'layers': ['pl_nmt1', 'pl_gugik'], 'resolution': '1 m',
     'source': 'GUGiK NMT 1 m via Mapterhorn; Lücken (~1/4) aus dem GUGiK-Schummerungs-WMS (langsamer)'},
    {'id': 'PL-02', 'name': 'Niederschlesien', **_NMT},
    {'id': 'PL-16', 'name': 'Oppeln (Opolskie)', **_NMT},
    {'id': 'PL-20', 'name': 'Podlachien (Podlaskie)', **_NMT},
    {'id': 'PL-22', 'name': 'Pommern (Pomorskie)', **_NMT},
    {'id': 'PL-24', 'name': 'Schlesien (Śląskie)', **_NMT},
    {'id': 'PL-32', 'name': 'Westpommern', **_NMT},
]
