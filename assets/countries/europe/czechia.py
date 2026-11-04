# This module contains the terrain layer definitions and geographical bounds for Czechia.
# Checked 2026-10-19: ČÚZK serves its LiDAR terrain model DMR 5G (flown 2009-13, 2 m grid in the image
# service) for the whole country as a hillshade WMS (raster function GrayscaleHillshade). Mapterhorn only
# holds the coarser DMR 4G (5 m, up to Mapterhorn zoom 14), which stays underneath as the base.
import json
import os

bounds = {
    "czechia": [[48.5, 12.0], [51.1, 18.9]]
}

# Regions (kraje, ISO 3166-2 CZ-10 .. CZ-80) and the national border as [lat, lon] rings (ČÚZK RÚIAN,
# MapServer layers VÚSC and Stát, 19.10.2026, open data; regions simplified to 25 m with shared borders,
# the national outline to 100 m; Prague is a hole ring in Central Bohemia).
with open(os.path.join(os.path.dirname(__file__), "czechia_regions.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

REGIONS = ['CZ-10', 'CZ-20', 'CZ-31', 'CZ-32', 'CZ-41', 'CZ-42', 'CZ-51', 'CZ-52', 'CZ-53', 'CZ-63', 'CZ-64',
           'CZ-71', 'CZ-72', 'CZ-80']

terrain_layers = {
    # Transparent outside the data (the image service's NoData), no watermark; about 1.2-1.5 s per tile.
    # The grid is 2 m: zoom 18 only shows enlarged pixels, so the server is asked up to zoom 17.
    'cz_dmr5g': {
        'url': 'https://ags.cuzk.cz/arcgis2/services/dmr5g/ImageServer/WMSServer',
        'options': {
            'clipTo': REGIONS,
            'layers': 'dmr5g:GrayscaleHillshade',
            'format': 'image/png',
            'transparent': True,
            'version': '1.3.0',
            'tileSize': 512,
            'retryBlank': False,
            'maxZoom': 20,
            'maxNativeZoom': 17,
            'attribution': 'DMR 5G LiDAR 2009-2013 &copy; ČÚZK (geoportal.cuzk.gov.cz), CC BY 4.0'
        }
    },
    # Base: DMR 4G (5 m) via Mapterhorn, always under DMR 5G.
    'cz_dmr4g': {
        'type': 'dem_terrarium',
        'url': 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp',
        'options': {
            'clipTo': ['czechia'],
            'fallbackFor': REGIONS,
            'fallbackFrom': 99,
            'tileSize': 512,
            'retryBlank': False,
            'maxZoom': 20,
            'maxNativeZoom': 15,
            'attribution': 'DMR 4G &copy; ČÚZK, CC BY 4.0 via &copy; Mapterhorn (Schummerung berechnet)'
        }
    },
}

for _info in terrain_layers.values():
    _pts = [pt for code in _info['options']['clipTo'] for ring in outlines[code] for pt in ring]
    _info['options']['bounds'] = [[round(min(p[0] for p in _pts) - 0.01, 4), round(min(p[1] for p in _pts) - 0.01, 4)],
                                  [round(max(p[0] for p in _pts) + 0.01, 4), round(max(p[1] for p in _pts) + 0.01, 4)]]

layer_logic = {
    "czechia": {
        "8": ['cz_dmr5g', 'cz_dmr4g'],
        "0": ['cz_dmr4g'],
    }
}

country = {'id': 'CZ', 'name': 'Tschechien'}
base_relief = {'layers': ['cz_dmr4g'], 'name': 'Grundrelief', 'resolution': '5 m', 'source': 'ČÚZK DMR 4G via Mapterhorn'}
_DMR = {'layers': ['cz_dmr5g'], 'resolution': '2 m', 'source': 'ČÚZK DMR 5G (LiDAR 2009-13)'}
regions = [
    {'id': 'CZ-42', 'name': 'Aussig', **_DMR},
    {'id': 'CZ-63', 'name': 'Hochland (Vysočina)', **_DMR},
    {'id': 'CZ-41', 'name': 'Karlsbad', **_DMR},
    {'id': 'CZ-52', 'name': 'Königgrätz', **_DMR},
    {'id': 'CZ-80', 'name': 'Mährisch-Schlesien', **_DMR},
    {'id': 'CZ-20', 'name': 'Mittelböhmen', **_DMR},
    {'id': 'CZ-71', 'name': 'Olmütz', **_DMR},
    {'id': 'CZ-53', 'name': 'Pardubitz', **_DMR},
    {'id': 'CZ-32', 'name': 'Pilsen', **_DMR},
    {'id': 'CZ-10', 'name': 'Prag', **_DMR},
    {'id': 'CZ-51', 'name': 'Reichenberg', **_DMR},
    {'id': 'CZ-31', 'name': 'Südböhmen', **_DMR},
    {'id': 'CZ-64', 'name': 'Südmähren', **_DMR},
    {'id': 'CZ-72', 'name': 'Zlín', **_DMR},
]
