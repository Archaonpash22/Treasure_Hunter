# This module contains the terrain layer definitions and geographical bounds for Germany.
import json
import os

# Bounding boxes define the geographical areas for each region.
# The format is [south_lat, west_lon], [north_lat, east_lon]
bounds = {
    "germany": [[47.2, 5.8], [55.1, 15.1]]
}

# National territory incl. coastal waters ([lat, lon] rings from BKG VG250, simplified to 100 m;
# (c) BKG 2025, dl-de/by-2-0). The bounding box above also covers Salzburg, Basel, Strasbourg etc.;
# the outline keeps those views on their own country.
with open(os.path.join(os.path.dirname(__file__), "germany_outline.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

_MAPTERHORN = 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp'


def _mapterhorn(code, attribution):
    """Mapterhorn height tiles (the state's DGM1, ~1.2 m per pixel at its zoom 16 = app zoom 17), shaded locally."""
    return {
        'type': 'dem_terrarium',
        'url': _MAPTERHORN,
        'options': {
            'clipTo': [code],
            'tileSize': 512,
            'retryBlank': False,
            'maxZoom': 20,
            'maxNativeZoom': 17,
            'attribution': attribution + ' via &copy; Mapterhorn (Schummerung berechnet)'
        }
    }


# Definitions for the terrain layers available for this country.
# Each key corresponds to a layer that can be activated.
terrain_layers = {
    # Open data since 2024: hillshade of the 25 cm LiDAR terrain model (DGM025), all of BW.
    # Transparent outside BW, so other layers can sit underneath near the state border.
    'bw_dgm025': {
        'url': 'https://owsproxy.lgl-bw.de/owsproxy/ows/WMS_LGL-BW_ATKIS_DGM_025_Schummerung',
        'options': {
            'clipTo': ['DE-BW'],
            'layers': 'Schummerung_DGM_025_BW',
            'format': 'image/png',
            'transparent': True,
            'tileSize': 512,
            'retryBlank': False,
            'version': '1.3.0',
            'maxZoom': 20,
            'maxNativeZoom': 19,
            'attribution': 'LiDAR DGM 25 cm Schummerung &copy; LGL-BW (2026), dl-de/by-2-0'
        }
    },
    # NRW: 25 cm hillshade of the LiDAR DGM, open data (dl-de/zero-2-0).
    'nw_dgm025': {
        'url': 'https://www.wms.nrw.de/geobasis/wms_nw_dgm-schummerung',
        'options': {
            'clipTo': ['DE-NW'],
            'layers': 'nw_dgm-schummerung_pan',
            'format': 'image/png',
            'transparent': True,
            'tileSize': 512,
            'retryBlank': False,
            'version': '1.3.0',
            'maxZoom': 20,
            'maxNativeZoom': 19,
            'attribution': 'LiDAR DGM 25 cm Schummerung &copy; GeoBasis-DE / NRW, dl-de/zero-2-0'
        }
    },
    # Saarland: hillshade from the 2025 laser data (DGM1, rendered ~0.5 m). The URL is the
    # geoportal's public Mapbender proxy for "WMS SL Digitale Geländemodelle".
    'sl_dgm1': {
        'url': 'https://geoportal.saarland.de/owsproxy/00000000000000000000000000000000/f9406651c1de911d4ddf11f0d5abc43d',
        'options': {
            'clipTo': ['DE-SL'],
            'layers': 'sl_shaded_relief_2025',
            'preferPng': True,  # this server's JPEG is high quality and larger than its PNG
            'format': 'image/png',
            'transparent': True,
            'tileSize': 512,
            'retryBlank': False,
            'version': '1.1.1',
            'maxZoom': 20,
            'maxNativeZoom': 18,
            'attribution': 'LiDAR DGM Schummerung &copy; GeoBasis DE/LVGL-SL (2025), dl-de/by-2-0'
        }
    },
    'rp_dgm1': {
        'url': 'https://geo4.service24.rlp.de/wms/shade1m.fcgi',
        'options': {
            'clipTo': ['DE-RP'],
            'layers': 'rp_shade1m',
            'format': 'image/png',
            'transparent': True,
            'tileSize': 512,
            'retryBlank': False,
            'version': '1.3.0',
            'maxZoom': 20,
            'maxNativeZoom': 17,
            'attribution': 'LiDAR DGM 1 m Schummerung &copy; GeoBasis-DE / LVermGeoRP (2026), dl-de/by-2-0 [Daten bearbeitet]'
        }
    },
    # Sachsen: DGM1 hillshade, served at ~0.5 m per pixel.
    'sn_dgm1': {
        'url': 'https://geodienste.sachsen.de/wms_geosn_hoehe/guest',
        'options': {
            'clipTo': ['DE-SN'],
            'layers': 'relief_standard',
            'format': 'image/png',
            'transparent': True,
            'tileSize': 512,
            'retryBlank': False,
            'version': '1.3.0',
            'maxZoom': 20,
            'maxNativeZoom': 18,
            'attribution': 'LiDAR DGM Schummerung &copy; GeoSN, dl-de/by-2-0'
        }
    },
    # Brandenburg and Berlin in one service (LGB MapProxy cache), DGM 1 m.
    'bb_be_dgm1': {
        'url': 'https://isk.geobasis-bb.de/mapproxy/dgm/service/wms',
        'options': {
            'clipTo': ['DE-BB', 'DE-BE'],
            'layers': 'dgmshade',
            'format': 'image/png',
            'transparent': True,
            'tileSize': 512,
            'retryBlank': False,
            'version': '1.3.0',
            'maxZoom': 20,
            'maxNativeZoom': 17,
            'attribution': 'LiDAR DGM 1 m Schummerung &copy; GeoBasis-DE/LGB, GDI-BE, dl-de/by-2-0'
        }
    },
    'hh_dgm1': {
        # Buildings interpolated away (the older Schummerungskarte stamps them in as grey blocks).
        'url': 'https://geodienste.hamburg.de/wms_gelaendemodelle_schummerung',
        'options': {
            'clipTo': ['DE-HH'],
            'layers': 'gelaendemodelle_schummerung',
            'format': 'image/png',
            'transparent': True,
            'tileSize': 512,
            'retryBlank': False,
            'version': '1.3.0',
            'maxZoom': 20,
            'maxNativeZoom': 17,
            'attribution': 'LiDAR DGM 1 m Schummerung &copy; FHH, LGV, dl-de/by-2-0'
        }
    },
    # MV: heights from the WCS (the WMS burns a watermark into every image). Without bilinear
    # interpolation the server's resampling shows a moiré grid at zoom 17.
    'mv_dgm1': {
        'type': 'dem_wcs',
        'url': 'https://www.geodaten-mv.de/dienste/dgm_wcs?INTERPOLATION=BILINEAR',
        'options': {
            'clipTo': ['DE-MV'],
            'coverage': 'mv_dgm',
            'pyramid': {5: 'mv_dgm5', 25: 'mv_dgm25'},
            'subsetAxes': ['x', 'y'],
            'validRange': [-30, 200],
            'tileSize': 512,
            'retryBlank': False,
            'maxZoom': 20,
            'maxNativeZoom': 17,
            'attribution': 'DGM1 &copy; GeoBasis-DE/M-V 2025, CC BY 4.0 (Schummerung berechnet)'
        }
    },
    # Mapterhorn instead of the state services: TH only serves a 2 m hillshade, SH only a 20x exaggerated
    # one, Bremen nothing, and the NI WCS needs 5-13 s per tile (Mapterhorn 0.3-1 s, same DGM1).
    'th_dgm1': _mapterhorn('DE-TH', 'DGM1 &copy; GDI-Th, dl-de/by-2-0'),
    'sh_dgm1_mt': _mapterhorn('DE-SH', 'DGM1 &copy; GeoBasis-DE/LVermGeo SH, CC BY 4.0'),
    'hb_dgm1': _mapterhorn('DE-HB', 'DGM1 &copy; Landesamt GeoInformation Bremen, CC BY 4.0'),
    'ni_dgm1_mt': _mapterhorn('DE-NI', 'DGM1 &copy; LGLN (2026), CC BY 4.0'),
    # The next states publish their LiDAR DGM1 only as heights: the tile cache fetches them and
    # computes the hillshade itself (dem_shade.py). They therefore need the local tile cache.
    # Sachsen-Anhalt: WMS with a Float32 GeoTIFF format. Outside the state the TIFF holds junk
    # values, which validRange and the state mask take care of.
    'st_dgm1': {
        'type': 'dem_wms',
        'url': 'https://www.geodatenportal.sachsen-anhalt.de/ows_WMS_ST_DGM1',
        'options': {
            'clipTo': ['DE-ST'],
            'layers': 'ST_DGM1',
            'version': '1.3.0',
            'demFormat': 'image/tiff',
            'tileSize': 512,
            'retryBlank': False,
            'maxZoom': 20,
            'maxNativeZoom': 17,
            'attribution': 'DGM1 &copy; GeoBasis-DE / LVermGeo ST, dl-de/by-2-0 (Schummerung berechnet)'
        }
    },
    # Hessen: WCS (rasdaman) with coarser pyramid coverages for low zooms. Its answers are slightly
    # larger than requested; dem_shade resamples them onto the tile grid via the GeoTIFF tags.
    'he_dgm1': {
        'type': 'dem_wcs',
        'url': 'https://inspire-hessen.de/raster/dgm1/ows',
        'options': {
            'clipTo': ['DE-HE'],
            'coverage': 'he_dgm1',
            'pyramid': {2: 'he_dgm1_2', 4: 'he_dgm1_4', 8: 'he_dgm1_8', 16: 'he_dgm1_16', 32: 'he_dgm1_32'},
            'subsetAxes': ['E', 'N'],
            'oversample': 2,
            'scaleAxes': ['x', 'y'],
            'validRange': [-100, 1000],
            'tileSize': 512,
            'retryBlank': False,
            'maxZoom': 20,
            'maxNativeZoom': 17,
            'attribution': 'DGM1 &copy; HVBG, dl-de/zero-2-0 (Schummerung berechnet)'
        }
    },
    'de_gelaende': {
        'url': 'https://sgx.geodatenzentrum.de/wms_basemapde_schummerung',
        'options': {
            'clipTo': ['germany'],
            # Fills every state whose LiDAR is not shown (no service, or switched off in the
            # panel). From fallbackFrom on, the page clips it to exactly those states, so it never
            # loads unseen underneath opaque LiDAR.
            'fallbackFor': ['DE-BW', 'DE-BY', 'DE-BE', 'DE-BB', 'DE-HB', 'DE-HH', 'DE-HE', 'DE-MV',
                            'DE-NI', 'DE-NW', 'DE-RP', 'DE-SL', 'DE-SN', 'DE-ST', 'DE-SH', 'DE-TH'],
            'fallbackFrom': 14,
            'layers': 'de_basemapde_web_raster_hillshade',
            'format': 'image/png',
            'transparent': True,
            'tileSize': 512,
            'retryBlank': False,
            # Derived from the 5 m DGM: no more detail above zoom 16.
            'maxNativeZoom': 16,
            'attribution': 'Gelände &copy; GeoBasis-DE / BKG'
        }
    },
    'by_lidar_schraeglicht': {
        'url': 'https://geoservices.bayern.de/od/wms/dgm/v1/relief',
        'options': {
            'clipTo': ['DE-BY'],
            'layers': 'by_relief_schraeglicht',
            'format': 'image/png',
            'transparent': True,
            'tileSize': 512,
            'retryBlank': False,
            'attribution': 'Geländerelief &copy; LDBV',
            'version': '1.3.0',
            'maxZoom': 20,
            # Rendered from the 1 m DGM: fully resolved at zoom 17, enlarged client-side above.
            'maxNativeZoom': 17
        }
    },
    'by_lidar_kombiniert': {
        'url': 'https://geoservices.bayern.de/od/wms/dgm/v1/relief',
        'options': {
            'clipTo': ['DE-BY'],
            'layers': 'by_relief_kombiniert',
            'format': 'image/png',
            'transparent': True,
            'tileSize': 512,
            'retryBlank': False,
            'attribution': 'Geländerelief &copy; LDBV',
            'version': '1.3.0',
            'maxZoom': 20,
            # Rendered from the 1 m DGM: fully resolved at zoom 17, enlarged client-side above.
            'maxNativeZoom': 17
        }
    }
}

# State borders (BKG VG250 land areas incl. lagoons and mudflats, simplified to 5 m;
# (c) BKG 2025, dl-de/by-2-0). A layer with 'clipTo' is cut exactly at its state border in
# the page, tiles fully outside the state are never requested, and the offline downloader
# and the cache size estimate count only tiles that touch the state.
with open(os.path.join(os.path.dirname(__file__), "germany_states.json"), encoding="utf-8") as _f:
    _state_outlines = json.load(_f)

for _info in terrain_layers.values():
    _codes = _info['options'].get('clipTo')
    if not _codes:
        continue
    _pts = [pt for code in _codes for ring in (_state_outlines.get(code) or outlines[code]) for pt in ring]
    _info['options']['bounds'] = [[round(min(p[0] for p in _pts) - 0.01, 4), round(min(p[1] for p in _pts) - 0.01, 4)],
                                  [round(max(p[0] for p in _pts) + 0.01, 4), round(max(p[1] for p in _pts) + 0.01, 4)]]
    for _code in _codes:
        outlines.setdefault(_code, _state_outlines.get(_code))
    if not all(code.startswith('DE-') for code in _codes) or _info['options'].get('preferPng'):
        continue  # the national outline includes the sea, where the BKG relief stays transparent PNG
    # The mask replaces transparency, so the much smaller JPEG is enough: 4-10x less data per
    # tile, and the servers also render it faster (measured 2026-10-18, e.g. BW 1.2 s -> 0.25 s).
    _info['options']['format'] = 'image/jpeg'
    _info['options']['transparent'] = False

# Every state outline goes to the page: the base relief is clipped to whichever states it fills,
# and the terrain panel zooms to a state by its outline.
for _code, _rings in _state_outlines.items():
    outlines.setdefault(_code, _rings)


# The state LiDAR layers are clipped to their states, so they are stacked together for the whole
# country: whichever states are in view load tiles, and the nationwide BKG relief fills the rest.
# (layer key, first zoom it is shown at), finest data first.
state_lidar_layers = [
    ('bw_dgm025', 9),
    ('nw_dgm025', 9),
    ('sl_dgm1', 9),
    ('sn_dgm1', 9),
    ('bb_be_dgm1', 9),
    ('hh_dgm1', 9),
    ('rp_dgm1', 9),
    ('mv_dgm1', 9),    # shaded locally from WCS heights
    ('th_dgm1', 9),    # Mapterhorn
    ('sh_dgm1_mt', 9),
    ('hb_dgm1', 9),
    ('ni_dgm1_mt', 9),
    ('st_dgm1', 9),    # shaded locally from heights
    ('he_dgm1', 11),   # shaded locally; below zoom 11 the WCS takes far too long
]

# Bavaria switches between two renderings of the same data.
bavaria_by_zoom = {14: 'by_lidar_schraeglicht', 15: 'by_lidar_kombiniert'}


def _germany_logic():
    thresholds = sorted({0} | {z for _, z in state_lidar_layers} | set(bavaria_by_zoom))
    logic = {}
    for t in thresholds:
        stack = [key for key, min_zoom in state_lidar_layers if t >= min_zoom]
        by_zooms = [z for z in bavaria_by_zoom if t >= z]
        if by_zooms:
            stack.append(bavaria_by_zoom[max(by_zooms)])
        logic[str(t)] = stack + ['de_gelaende']
    return logic


# This dictionary defines which terrain layer to use based on the region and zoom level.
layer_logic = {
    "germany": _germany_logic()
}

# What the terrain panel lists: one entry per state, with the layers that draw it.
country = {'id': 'DE', 'name': 'Deutschland'}
base_relief = {'layers': ['de_gelaende'], 'name': 'Grundrelief', 'resolution': '5 m', 'source': 'BKG'}
regions = [
    {'id': 'DE-BW', 'name': 'Baden-Württemberg', 'layers': ['bw_dgm025'], 'resolution': '25 cm', 'source': 'LGL-BW'},
    {'id': 'DE-BY', 'name': 'Bayern', 'layers': ['by_lidar_schraeglicht', 'by_lidar_kombiniert'], 'resolution': '1 m', 'source': 'LDBV'},
    {'id': 'DE-BE', 'name': 'Berlin', 'layers': ['bb_be_dgm1'], 'resolution': '1 m', 'source': 'LGB'},
    {'id': 'DE-BB', 'name': 'Brandenburg', 'layers': ['bb_be_dgm1'], 'resolution': '1 m', 'source': 'LGB'},
    {'id': 'DE-HB', 'name': 'Bremen', 'layers': ['hb_dgm1'], 'resolution': '1 m', 'source': 'Mapterhorn (berechnet)'},
    {'id': 'DE-HH', 'name': 'Hamburg', 'layers': ['hh_dgm1'], 'resolution': '1 m', 'source': 'LGV'},
    {'id': 'DE-HE', 'name': 'Hessen', 'layers': ['he_dgm1'], 'resolution': '1 m', 'source': 'HVBG (berechnet)'},
    {'id': 'DE-MV', 'name': 'Mecklenburg-Vorpommern', 'layers': ['mv_dgm1'], 'resolution': '1 m', 'source': 'LAiV (berechnet)'},
    {'id': 'DE-NI', 'name': 'Niedersachsen', 'layers': ['ni_dgm1_mt'], 'resolution': '1 m', 'source': 'LGLN via Mapterhorn (berechnet)'},
    {'id': 'DE-NW', 'name': 'Nordrhein-Westfalen', 'layers': ['nw_dgm025'], 'resolution': '25 cm', 'source': 'Geobasis NRW'},
    {'id': 'DE-RP', 'name': 'Rheinland-Pfalz', 'layers': ['rp_dgm1'], 'resolution': '1 m', 'source': 'LVermGeo'},
    {'id': 'DE-SL', 'name': 'Saarland', 'layers': ['sl_dgm1'], 'resolution': '50 cm', 'source': 'LVGL'},
    {'id': 'DE-SN', 'name': 'Sachsen', 'layers': ['sn_dgm1'], 'resolution': '1 m', 'source': 'GeoSN'},
    {'id': 'DE-ST', 'name': 'Sachsen-Anhalt', 'layers': ['st_dgm1'], 'resolution': '1 m', 'source': 'LVermGeo (berechnet)'},
    {'id': 'DE-SH', 'name': 'Schleswig-Holstein', 'layers': ['sh_dgm1_mt'], 'resolution': '1 m', 'source': 'LVermGeo SH via Mapterhorn (berechnet)'},
    {'id': 'DE-TH', 'name': 'Thüringen', 'layers': ['th_dgm1'], 'resolution': '1 m', 'source': 'TLBG via Mapterhorn (berechnet)'},
]
