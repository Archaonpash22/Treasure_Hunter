# This module contains the terrain layer definitions and geographical bounds for Italy.

# Bounding boxes define the geographical areas for each region.
# The format is [south_lat, west_lon], [north_lat, east_lon]
# Region priority (which box wins when several contain the map centre) is defined
# in map_widget.py (terrainRegionPriority); more specific regions come first.
bounds = {
    "lunigiana": [[44.05, 9.65], [44.55, 10.25]],
    "elba": [[42.70, 10.05], [42.90, 10.50]],
    "emilia_romagna": [[43.7, 9.1], [45.2, 12.85]],
    "tuscany": [[42.2, 9.6], [44.5, 12.45]],
    "italy": [[35.5, 6.6], [47.1, 18.5]]
}

_ER_BOX = [[43.7, 9.1], [45.2, 12.85]]
_TOSCANA_BOX = [[42.2, 9.6], [44.5, 12.45]]

# Regione Emilia-Romagna publishes its LiDAR-derived DTMs as ArcGIS Image Services.
# The hillshade is rendered on the server via a "renderingRule" on the exportImage
# endpoint, which is handled by the 'arcgis_image' layer type in map_widget.py.
_ER_IMAGE_SERVICES = 'https://servizigis.regione.emilia-romagna.it/arcgis/rest/services/public/'

# Regione Toscana "Geoscopio" morphology WMS (1 m LiDAR hillshade, 2019-2021 flights by
# Italian Remote Sensing, CC BY-NC-SA). Every image carries a vertical source-credit
# watermark along its left edge, so these layers use the 'wms_crop' type which requests
# a slightly wider image and crops that strip away.
_TOSCANA_WMS = 'https://www502.regione.toscana.it/wmsraster/com.rt.wms.RTmap/wms?map=wmsmorfologia'

# Ministry of the Environment (MASE / PST-A) LiDAR WMS, one map file per region.
_MASE_LIDAR_WMS = 'http://wms.pcn.minambiente.it/ogc?map=/ms_ogc/WMS_v1.3/servizi-LiDAR/LIDAR_{}.map'

# maxNativeZoom is the zoom whose pixel size matches the data (about 0.85 m per pixel at
# zoom 17 at this latitude, so 17 for 1 m data). Above it Leaflet just enlarges those tiles:
# finer tiles would show nothing new and only cost requests and cache space.
#
# Layer definitions. Keys listed later in this dict are drawn above earlier ones when
# several layers are stacked, so put fallbacks first and the finest data last.
terrain_layers = {
    # Country-wide fallback: TINITALY 10 m DEM hillshade (INGV, CC BY 4.0). Not LiDAR,
    # but far better than SRTM and it covers every island.
    'it_dtm': {
        'url': 'https://tinitaly.pi.ingv.it/TINItaly_1_1/wms?',
        'options': {
            'layers': 'tinitaly_hshd',
            'format': 'image/png',
            'transparent': True,
            'version': '1.3.0',
            'maxZoom': 20,
            'maxNativeZoom': 14,
            'bounds': [[35.5, 6.6], [47.1, 18.5]],
            'attribution': 'TINITALY 10 m &copy; INGV (CC BY 4.0)'
        }
    },
    # Emilia-Romagna 5 m DTM ("ultima edizione", built from the RER LiDAR flights),
    # rendered as a classic single-light hillshade. Covers the whole region.
    'er_dtm5m': {
        'type': 'arcgis_image',
        'url': _ER_IMAGE_SERVICES + 'Dtm5x5/ImageServer',
        'options': {
            'renderingRule': {
                'rasterFunction': 'Hillshade',
                'rasterFunctionArguments': {'Azimuth': 315, 'Altitude': 45, 'ZFactor': 1}
            },
            'imageFormat': 'png',
            'bounds': _ER_BOX,
            'maxZoom': 20,
            'maxNativeZoom': 15,
            'attribution': 'DTM 5 m &copy; Regione Emilia-Romagna (CC BY 4.0)'
        }
    },
    # Ministry of the Environment (MASE / PST-A) 2 m LiDAR DTM for Tuscany, served as a
    # tinted shaded relief. Covers coasts and river corridors only (e.g. a ring around
    # Elba), so it is always stacked on top of a full-coverage fallback.
    'tos_mase_2m': {
        'url': 'http://wms.pcn.minambiente.it/ogc?map=/ms_ogc/WMS_v1.3/servizi-LiDAR/LIDAR_TOSCANA.map',
        'options': {
            'layers': 'EL.LIDAR.TOSCANA.2x2.DTM',
            'format': 'image/png',
            'transparent': True,
            'version': '1.1.1',
            'maxZoom': 20,
            'maxNativeZoom': 16,
            'bounds': _TOSCANA_BOX,
            'attribution': 'LiDAR DTM 2 m &copy; MASE - Geoportale Nazionale'
        }
    },
    # MASE 1 m LiDAR DTM for Tuscany (2008-2010 flights along the main rivers), tinted
    # shaded relief. In Lunigiana it covers the whole Magra / Verde / Aulella valley floor
    # from above Pontremoli down to Sarzana, which the regional 1 m LiDAR does not.
    'tos_mase_1m': {
        'url': _MASE_LIDAR_WMS.format('TOSCANA'),
        'options': {
            'layers': 'EL.LIDAR.TOSCANA.1x1.DTM',
            'format': 'image/png',
            'transparent': True,
            'version': '1.1.1',
            'maxZoom': 20,
            'maxNativeZoom': 17,
            'bounds': _TOSCANA_BOX,
            'attribution': 'LiDAR DTM 1 m &copy; MASE - Geoportale Nazionale (CC BY 4.0)'
        }
    },
    # Regione Toscana 1 m DSM 2021 hillshade (photogrammetric surface model, not LiDAR:
    # it shows tree canopy and buildings). Covers all of Tuscany including Elba.
    'tos_dsm_1m': {
        'type': 'wms_crop',
        'url': _TOSCANA_WMS,
        'options': {
            'layers': 'rt_morfologia.iddsm2021.1m.hs.rt',
            'cropLeft': 32,
            'maxZoom': 20,
            'maxNativeZoom': 17,
            'bounds': _TOSCANA_BOX,
            'attribution': 'DSM 1 m 2021 &copy; Regione Toscana'
        }
    },
    # Regione Toscana 1 m LiDAR DTM hillshade (2019-2021). Covers mainland Tuscany;
    # the islands (Elba etc.) are not included. Only served at scales below 1:75,000,
    # i.e. from about zoom 13 upwards.
    'tos_lidar_1m': {
        'type': 'wms_crop',
        'url': _TOSCANA_WMS,
        'options': {
            'layers': 'rt_morfologia.iddtm.1m.hs.irs',
            'cropLeft': 32,
            'maxZoom': 20,
            'maxNativeZoom': 17,
            'bounds': _TOSCANA_BOX,
            'attribution': 'LiDAR DTM 1 m &copy; Regione Toscana / IRS (CC BY-NC-SA)'
        }
    },
    # Emilia-Romagna 0.5 m LiDAR DTM (RER 2023-24 flights), multidirectional hillshade.
    # Covers Sasso Marconi and most of the Bologna Apennines; the Bologna municipality
    # itself was flown separately and is not part of this service.
    'er_lidar_05m': {
        'type': 'arcgis_image',
        'url': _ER_IMAGE_SERVICES + 'DtmRER2023_24/ImageServer',
        'options': {
            'renderingRule': {
                'rasterFunction': 'Hillshade',
                'rasterFunctionArguments': {'HillshadeType': 1, 'ZFactor': 1}
            },
            'imageFormat': 'png',
            'bounds': _ER_BOX,
            'maxZoom': 20,
            'maxNativeZoom': 18,
            'attribution': 'LiDAR DTM 0,5 m RER 2023-24 &copy; Regione Emilia-Romagna (CC BY 4.0)'
        }
    }
}

# This dictionary defines which terrain layer(s) to use based on the region and zoom level.
# Keys are minimum zoom levels; the highest key <= current zoom wins. A value may be a
# single layer key or a list [finest, ..., coarsest]: all are shown, stacked in that
# order, so coarser data shows through wherever the finer service has no coverage.
layer_logic = {
    # Lunigiana (Mulazzo, Pontremoli, Villafranca, Aulla, Fivizzano). No single LiDAR
    # survey covers it: the regional 1 m LiDAR only reaches the Apuan side in the
    # south-east, MASE 1 m covers the Magra valley floor.
    # The hillsides in between (Mulazzo village itself) have no public LiDAR, so the
    # 1 m DSM 2021 (shows trees and buildings) is the finest fill there.
    # The MASE Liguria LiDAR WMS (LIDAR_LIGURIA.map) is deliberately not used: its 1 m
    # data only covers the Vara corridor and the coast, and for most tiles at zoom 13+
    # it returns flat colour without relief, which would hide the layers below.
    "lunigiana": {
        # The DSM is only added from zoom 15: below that the server's downsampling turns
        # it into noise and the 10 m TINITALY relief reads better.
        "15": ['tos_lidar_1m', 'tos_mase_1m', 'tos_dsm_1m', 'it_dtm'],
        "13": ['tos_lidar_1m', 'tos_mase_1m', 'it_dtm'],
        "11": ['tos_mase_1m', 'it_dtm'],
        "0": 'it_dtm'
    },
    # Elba: no complete LiDAR exists. The MASE 2 m LiDAR covers the coastal ring and the
    # 1 m DSM fills the rest of the island. Above zoom 16 the MASE service degrades to flat
    # opaque colour that would hide the DSM, so only the DSM is shown there.
    "elba": {
        "17": ['tos_dsm_1m'],
        "13": ['tos_mase_2m', 'tos_dsm_1m'],
        "0": 'it_dtm'
    },
    # The ER box reaches south over the Apennine ridge into northern Tuscany
    # (Florence, Pisa, Lucca), so the Tuscan LiDAR is kept in the stack as fallback.
    "emilia_romagna": {
        "14": ['er_lidar_05m', 'tos_lidar_1m', 'it_dtm'],
        "13": ['er_dtm5m', 'tos_lidar_1m', 'it_dtm'],
        "10": ['er_dtm5m', 'it_dtm'],
        "0": 'it_dtm'
    },
    "tuscany": {
        "13": ['tos_lidar_1m', 'it_dtm'],
        "0": 'it_dtm'
    },
    "italy": {
        "0": 'it_dtm'
    }
}
