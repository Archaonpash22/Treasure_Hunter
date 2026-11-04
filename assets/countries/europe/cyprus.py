# This module contains the terrain layer definitions and geographical bounds for Cyprus.
# Checked 2026-10-19: the Department of Lands and Surveys (DLS) publishes no live elevation or LiDAR
# hillshade service: its only hillshade (eservices.dls.moi.gov.cy BASEMAPS/Imagery_HillShade_1993) is a
# coarse TIN of the 1993 DTM, blank from zoom 17 on and coarser than Copernicus GLO-30. Mapterhorn holds the
# DLS "Cyprus DTM 2019" 1 m (CC BY 4.0) for the area controlled by the Republic plus the plain north of
# Nicosia up to the Kyrenia range (Lefkosia ~92 %, Lemesos, Larnaka and Pafos completely, Ammochostos
# ~18 % around Ayia Napa/Paralimni). Its grid-17 tiles exist (finest level, ~0.5 m/px); a faint square grid
# pattern of the source shows from zoom 17. North of the Green Line the model is noticeably smoother. The
# north beyond (Kyrenia district, most of Ammochostos, Morphou) shows only GLO-30 (30 m, a surface model).
import json
import os

bounds = {
    "cyprus": [[34.55, 32.25], [35.72, 34.62]]
}

# The six districts (ISO 3166-2 CY-01 .. CY-06, boundaries as defined by the Republic of Cyprus, including
# the north) and the outline of the island as [lat, lon] rings (DLS INSPIRE Administrative Units, 2nd order,
# eservices.dls.moi.gov.cy; districts simplified to 50 m with shared borders, islets below 2 ha left out,
# the national outline (their union) to 100 m). The British Sovereign Base Areas are not cut out.
with open(os.path.join(os.path.dirname(__file__), "cyprus_regions.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

REGIONS = ['CY-01', 'CY-02', 'CY-03', 'CY-04', 'CY-05', 'CY-06']
_MT = 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp'

terrain_layers = {
    # DLS DTM 2019 1 m via Mapterhorn, 0.2-1.3 s per tile; outside it the tiles answer 404 and GLO-30 shows.
    'cy_dtm': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': ['CY-01', 'CY-02', 'CY-03', 'CY-04', 'CY-05'], 'transparentNoData': True, 'tileSize': 512,
            'retryBlank': False, 'maxZoom': 20, 'maxNativeZoom': 18,
            'attribution': 'Cyprus DTM 2019 &copy; Τμήμα Κτηματολογίου και Χωρομετρίας (DLS), CC BY 4.0 via &copy; Mapterhorn '
                           '(Schummerung berechnet)'
        }
    },
    # Base: Copernicus GLO-30 (30 m) via Mapterhorn, up to grid 12 (= zoom 13), always underneath.
    'cy_glo30': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': ['cyprus'], 'fallbackFor': REGIONS, 'fallbackFrom': 99, 'tileSize': 512,
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
    "cyprus": {
        "8": ['cy_dtm', 'cy_glo30'],
        "0": ['cy_glo30'],
    }
}

country = {'id': 'CY', 'name': 'Zypern'}
base_relief = {'layers': ['cy_glo30'], 'name': 'Grundrelief', 'resolution': '30 m', 'source': 'Copernicus via Mapterhorn'}
_DTM = {'layers': ['cy_dtm'], 'resolution': '1 m', 'source': 'DLS Cyprus DTM 2019 1 m via Mapterhorn'}
regions = [
    {'id': 'CY-04', 'name': 'Famagusta (Ammochostos)', 'layers': ['cy_dtm'], 'resolution': '30 m',
     'source': 'GLO-30; DTM 2019 1 m nur im freien Süden um Ayia Napa/Paralimni (~1/5)'},
    {'id': 'CY-06', 'name': 'Kyrenia (Keryneia)', 'layers': [], 'resolution': '30 m', 'source': 'nur Copernicus GLO-30',
     'note': 'de facto nicht unter Kontrolle der Republik; kein offenes Geländemodell'},
    {'id': 'CY-03', 'name': 'Larnaka', **_DTM},
    {'id': 'CY-02', 'name': 'Limassol (Lemesos)', **_DTM},
    {'id': 'CY-01', 'name': 'Nikosia (Lefkosia)', **_DTM,
     'source': 'DLS Cyprus DTM 2019 1 m via Mapterhorn (~92 %, nördlich der Grünen Linie glatter); Westen um Morphou nur GLO-30'},
    {'id': 'CY-05', 'name': 'Paphos (Pafos)', **_DTM},
]
