# This module contains the terrain layer definitions and geographical bounds for Germany.
import json
import os

# Bounding boxes define the geographical areas for each region.
# The format is [south_lat, west_lon], [north_lat, east_lon]
bounds = {
    "germany": [[47.2, 5.8], [55.1, 15.1]]
}

# Simplified national border ([lat, lon] rings, ~500 m accuracy). The bounding box above also
# covers Salzburg, Basel, Strasbourg etc.; the outline keeps those views on their own country.
with open(os.path.join(os.path.dirname(__file__), "germany_outline.json"), encoding="utf-8") as _f:
    outlines = json.load(_f)

# Definitions for the terrain layers available for this country.
# Each key corresponds to a layer that can be activated.
terrain_layers = {
    # Open data since 2024: hillshade of the 25 cm LiDAR terrain model (DGM025), all of BW.
    # Transparent outside BW, so other layers can sit underneath near the state border.
    'bw_dgm025': {
        'url': 'https://owsproxy.lgl-bw.de/owsproxy/ows/WMS_LGL-BW_ATKIS_DGM_025_Schummerung',
        'options': {
            'layers': 'Schummerung_DGM_025_BW',
            'format': 'image/png',
            'transparent': True,
            'tileSize': 512,
            'retryBlank': False,
            'version': '1.3.0',
            'maxZoom': 20,
            'maxNativeZoom': 19,
            'bounds': [[47.5, 7.5], [49.85, 10.55]],
            'attribution': 'LiDAR DGM 25 cm Schummerung &copy; LGL-BW (2026), dl-de/by-2-0'
        }
    },
    # NRW: 25 cm hillshade of the LiDAR DGM, open data (dl-de/zero-2-0).
    'nw_dgm025': {
        'url': 'https://www.wms.nrw.de/geobasis/wms_nw_dgm-schummerung',
        'options': {
            'layers': 'nw_dgm-schummerung_pan',
            'format': 'image/png',
            'transparent': True,
            'tileSize': 512,
            'retryBlank': False,
            'version': '1.3.0',
            'maxZoom': 20,
            'maxNativeZoom': 19,
            'bounds': [[50.32, 5.86], [52.53, 9.46]],
            'attribution': 'LiDAR DGM 25 cm Schummerung &copy; GeoBasis-DE / NRW, dl-de/zero-2-0'
        }
    },
    # Saarland: hillshade from the 2025 laser data (DGM1, rendered ~0.5 m). The URL is the
    # geoportal's public Mapbender proxy for "WMS SL Digitale Geländemodelle".
    'sl_dgm1': {
        'url': 'https://geoportal.saarland.de/owsproxy/00000000000000000000000000000000/f9406651c1de911d4ddf11f0d5abc43d',
        'options': {
            'layers': 'sl_shaded_relief_2025',
            'format': 'image/png',
            'transparent': True,
            'tileSize': 512,
            'retryBlank': False,
            'version': '1.1.1',
            'maxZoom': 20,
            'maxNativeZoom': 18,
            'bounds': [[49.10, 6.35], [49.65, 7.41]],
            'attribution': 'LiDAR DGM Schummerung &copy; GeoBasis DE/LVGL-SL (2025), dl-de/by-2-0'
        }
    },
    'rp_dgm1': {
        'url': 'https://geo4.service24.rlp.de/wms/shade1m.fcgi',
        'options': {
            'layers': 'rp_shade1m',
            'format': 'image/png',
            'transparent': True,
            'tileSize': 512,
            'retryBlank': False,
            'version': '1.3.0',
            'maxZoom': 20,
            'maxNativeZoom': 17,
            'bounds': [[48.96, 6.11], [50.95, 8.51]],
            'attribution': 'LiDAR DGM 1 m Schummerung &copy; GeoBasis-DE / LVermGeoRP (2026), dl-de/by-2-0 [Daten bearbeitet]'
        }
    },
    # Thüringen: DGM2 (2 m) hillshade. The service paints the rest of its bbox opaque white,
    # so white is made transparent in the page. Nothing is drawn below zoom 10.
    'th_dgm2': {
        'type': 'wms_crop',
        'url': 'https://www.geoproxy.geoportal-th.de/geoproxy/services/DGM',
        'options': {
            'layers': 'DGM2',
            'format': 'image/png',
            'transparent': True,
            'tileSize': 512,
            'retryBlank': False,
            'whiteToAlpha': True,
            'version': '1.3.0',
            'maxZoom': 20,
            'maxNativeZoom': 16,
            'bounds': [[50.20, 9.87], [51.65, 12.66]],
            'attribution': 'DGM 2 m Schummerung &copy; GDI-Th, CC BY 4.0'
        }
    },
    # Sachsen: DGM1 hillshade, served at ~0.5 m per pixel.
    'sn_dgm1': {
        'url': 'https://geodienste.sachsen.de/wms_geosn_hoehe/guest',
        'options': {
            'layers': 'relief_standard',
            'format': 'image/png',
            'transparent': True,
            'tileSize': 512,
            'retryBlank': False,
            'version': '1.3.0',
            'maxZoom': 20,
            'maxNativeZoom': 18,
            'bounds': [[50.17, 11.87], [51.69, 15.04]],
            'attribution': 'LiDAR DGM Schummerung &copy; GeoSN, dl-de/by-2-0'
        }
    },
    # Brandenburg and Berlin in one service (LGB MapProxy cache), DGM 1 m.
    'bb_be_dgm1': {
        'url': 'https://isk.geobasis-bb.de/mapproxy/dgm/service/wms',
        'options': {
            'layers': 'dgmshade',
            'format': 'image/png',
            'transparent': True,
            'tileSize': 512,
            'retryBlank': False,
            'version': '1.3.0',
            'maxZoom': 20,
            'maxNativeZoom': 17,
            'bounds': [[51.36, 11.26], [53.56, 14.77]],
            'attribution': 'LiDAR DGM 1 m Schummerung &copy; GeoBasis-DE/LGB, GDI-BE, dl-de/by-2-0'
        }
    },
    'hh_dgm1': {
        'url': 'https://geodienste.hamburg.de/HH_WMS_Digitales_Hoehenmodel_Hamburg_Schummerungskarte_Gelaenderelief',
        'options': {
            'layers': 'dgm_schummerung',
            'format': 'image/png',
            'transparent': True,
            'tileSize': 512,
            'retryBlank': False,
            'version': '1.3.0',
            'maxZoom': 20,
            'maxNativeZoom': 17,
            'bounds': [[53.39, 9.72], [53.75, 10.34]],
            'attribution': 'LiDAR DGM 1 m Schummerung &copy; FHH, LGV, dl-de/by-2-0'
        }
    },
    # GDI-SH service without licence metadata; the DGM1 itself is CC BY 4.0 open data.
    # Layer "4" = DGM1 hillshade, 20x vertically exaggerated.
    'sh_dgm1': {
        'url': 'https://service.gdi-sh.de/WMS_SH_DGM',
        'options': {
            'layers': '4',
            'format': 'image/png',
            'transparent': True,
            'tileSize': 512,
            'retryBlank': False,
            'version': '1.3.0',
            'maxZoom': 20,
            'maxNativeZoom': 17,
            'bounds': [[53.36, 7.86], [55.06, 11.32]],
            'attribution': 'LiDAR DGM 1 m Schummerung &copy; GeoBasis-DE/LVermGeo SH, CC BY 4.0'
        }
    },
    # MV burns "(c) GeoBasis-DE/M-V" into the top-left corner of every image: request a strip
    # more to the west and crop it away (the attribution is shown in the map footer instead).
    'mv_dgm1': {
        'type': 'wms_crop',
        'url': 'https://www.geodaten-mv.de/dienste/dgm_wms',
        'options': {
            'layers': 'schummerung_NW',
            'format': 'image/png',
            'transparent': True,
            'tileSize': 512,
            'retryBlank': False,
            'cropLeft': 140,
            'maxZoom': 20,
            'maxNativeZoom': 17,
            'bounds': [[53.10, 10.59], [54.69, 14.42]],
            'attribution': 'LiDAR DGM 1 m Schummerung &copy; GeoBasis-DE/M-V 2025, CC BY 4.0'
        }
    },
    'de_gelaende': {
        'url': 'https://sgx.geodatenzentrum.de/wms_basemapde_schummerung',
        'options': {
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
            'layers': 'by_relief_schraeglicht',
            'format': 'image/png',
            'transparent': True,
            'tileSize': 512,
            'retryBlank': False,
            'bounds': [[47.2, 8.9], [50.6, 13.9]],
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
            'layers': 'by_relief_kombiniert',
            'format': 'image/png',
            'transparent': True,
            'tileSize': 512,
            'retryBlank': False,
            'bounds': [[47.2, 8.9], [50.6, 13.9]],
            'attribution': 'Geländerelief &copy; LDBV',
            'version': '1.3.0',
            'maxZoom': 20,
            # Rendered from the 1 m DGM: fully resolved at zoom 17, enlarged client-side above.
            'maxNativeZoom': 17
        }
    }
}

# The state LiDAR layers are all transparent outside their state and clipped to their own
# bounds, so they are stacked together for the whole country: whichever states are in view
# load tiles, and the nationwide BKG hillshade shows through everywhere else.
# (layer key, first zoom it is shown at), finest data first.
state_lidar_layers = [
    ('bw_dgm025', 9),
    ('nw_dgm025', 9),
    ('sl_dgm1', 9),
    ('sn_dgm1', 9),
    ('bb_be_dgm1', 9),
    ('hh_dgm1', 9),
    ('sh_dgm1', 9),
    ('rp_dgm1', 9),
    ('mv_dgm1', 10),   # the service draws nothing below zoom 10
    ('th_dgm2', 10),   # likewise
]
# No open LiDAR hillshade (checked 2026-10-18), the BKG relief covers them:
# Hessen (only a colour DGM), Niedersachsen (LGLN hillshade needs a contract), Bremen (only DGM colour / DOM),
# Sachsen-Anhalt (only a 5 m DGM relief, no better than BKG).

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
