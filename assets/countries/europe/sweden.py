# This module contains the terrain layer definitions and geographical bounds for Sweden.
# Checked 2026-10-19: Lantmäteriet's national elevation model (Markhöjdmodell, 1 m grid from the national
# laser scanning, CC0 since 2025) has a hillshade view service, but it needs a Geotorget account (401).
# The internal proxy of Lantmäteriet's web map "Min karta" is not used: it is no public interface and
# would only sidestep that login. Mapterhorn holds the same model (source "se", Markhöjdmodell
# Nedladdning 1 m, CC0): grid 16 (~0.6 m/px) up to Jämtland/Västernorrland, in Västerbotten and
# Norrbotten only grid 15 (~0.6-0.8 m/px there). Its computed hillshade is a little softer than Lantmäteriet's.
import json
import os

bounds = {
    "sweden": [[55.3, 10.95], [69.1, 24.2]]
}

# Counties (län, ISO 3166-2 SE-AB .. SE-Z) and the national border as [lat, lon] rings (SCB DeSO 2025
# statistical areas, CC0, dissolved per county; the DeSO areas reach out to the territorial sea, so they
# were cut to the coastline of the OpenStreetMap land polygons (© OpenStreetMap contributors, ODbL);
# counties simplified to 100 m with shared borders, the national outline (their union) to 100 m;
# islands under 10 ha left out). The DeSO areas are generalised, inland borders are only accurate to
# some 100 m.
with open(os.path.join(os.path.dirname(__file__), "sweden_regions.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

REGIONS = ['SE-AB', 'SE-AC', 'SE-BD', 'SE-C', 'SE-D', 'SE-E', 'SE-F', 'SE-G', 'SE-H', 'SE-I', 'SE-K', 'SE-M',
           'SE-N', 'SE-O', 'SE-S', 'SE-T', 'SE-U', 'SE-W', 'SE-X', 'SE-Y', 'SE-Z']
_MT = 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp'

terrain_layers = {
    # Markhöjdmodell 1 m via Mapterhorn: grid-16 tiles are native; where grid 16 answers 404 (parts of the
    # north) the base shows.
    'se_mt': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': REGIONS, 'transparentNoData': True, 'tileSize': 512, 'retryBlank': False,
            'maxZoom': 20, 'maxNativeZoom': 17,
            'attribution': 'Markhöjdmodell 1 m &copy; Lantmäteriet (CC0) via &copy; Mapterhorn (Schummerung berechnet)'
        }
    },
    # Base: the same model via Mapterhorn up to grid 15 (= zoom 16), always underneath.
    'se_base': {
        'type': 'dem_terrarium',
        'url': _MT,
        'options': {
            'clipTo': ['sweden'], 'fallbackFor': REGIONS, 'fallbackFrom': 99, 'tileSize': 512,
            'retryBlank': False, 'maxZoom': 20, 'maxNativeZoom': 16,
            'attribution': 'Markhöjdmodell &copy; Lantmäteriet (CC0) via &copy; Mapterhorn (Schummerung berechnet)'
        }
    },
}

for _info in terrain_layers.values():
    _pts = [pt for code in _info['options']['clipTo'] for ring in outlines[code] for pt in ring]
    _info['options']['bounds'] = [[round(min(p[0] for p in _pts) - 0.01, 4), round(min(p[1] for p in _pts) - 0.01, 4)],
                                  [round(max(p[0] for p in _pts) + 0.01, 4), round(max(p[1] for p in _pts) + 0.01, 4)]]

layer_logic = {
    "sweden": {
        "8": ['se_mt', 'se_base'],
        "0": ['se_base'],
    }
}

country = {'id': 'SE', 'name': 'Schweden'}
base_relief = {'layers': ['se_base'], 'name': 'Grundrelief', 'resolution': '1 m', 'source': 'Lantmäteriet Markhöjdmodell via Mapterhorn'}
_LM = {'layers': ['se_mt'], 'resolution': '1 m', 'source': 'Lantmäteriet Markhöjdmodell 1 m (Laserscanning) via Mapterhorn'}
regions = [
    {'id': 'SE-K', 'name': 'Blekinge', **_LM},
    {'id': 'SE-W', 'name': 'Dalarna', **_LM},
    {'id': 'SE-X', 'name': 'Gävleborg', **_LM},
    {'id': 'SE-I', 'name': 'Gotland', **_LM},
    {'id': 'SE-N', 'name': 'Halland', **_LM},
    {'id': 'SE-Z', 'name': 'Jämtland', **_LM},
    {'id': 'SE-F', 'name': 'Jönköping', **_LM},
    {'id': 'SE-H', 'name': 'Kalmar', **_LM},
    {'id': 'SE-G', 'name': 'Kronoberg', **_LM},
    {'id': 'SE-BD', 'name': 'Norrbotten', **_LM},
    {'id': 'SE-T', 'name': 'Örebro', **_LM},
    {'id': 'SE-E', 'name': 'Östergötland', **_LM},
    {'id': 'SE-M', 'name': 'Schonen (Skåne)', **_LM},
    {'id': 'SE-D', 'name': 'Södermanland', **_LM},
    {'id': 'SE-AB', 'name': 'Stockholm', **_LM},
    {'id': 'SE-C', 'name': 'Uppsala', **_LM},
    {'id': 'SE-S', 'name': 'Värmland', **_LM},
    {'id': 'SE-AC', 'name': 'Västerbotten', **_LM},
    {'id': 'SE-Y', 'name': 'Västernorrland', **_LM},
    {'id': 'SE-U', 'name': 'Västmanland', **_LM},
    {'id': 'SE-O', 'name': 'Västra Götaland', **_LM},
]
