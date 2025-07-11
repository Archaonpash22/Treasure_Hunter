# This module contains the terrain layer definitions and geographical bounds for Germany.

# Bounding boxes define the geographical areas for each region.
# The format is [south_lat, west_lon], [north_lat, east_lon]
bounds = {
    "bavaria": [[47.2, 8.9], [50.6, 13.9]],
    "germany": [[47.2, 5.8], [55.1, 15.1]]
}

# Definitions for the terrain layers available for this country.
# Each key corresponds to a layer that can be activated.
terrain_layers = {
    'de_gelaende': {
        'url': 'https://sgx.geodatenzentrum.de/wms_basemapde_schummerung',
        'options': {
            'layers': 'de_basemapde_web_raster_hillshade',
            'format': 'image/png',
            'transparent': True,
            'attribution': 'Gelände &copy; GeoBasis-DE / BKG'
        }
    },
    'by_lidar_schraeglicht': {
        'url': 'https://geoservices.bayern.de/od/wms/dgm/v1/relief',
        'options': {
            'layers': 'by_relief_schraeglicht',
            'format': 'image/png',
            'transparent': True,
            'attribution': 'Geländerelief &copy; LDBV',
            'version': '1.3.0',
            'maxZoom': 20
        }
    },
    'by_lidar_kombiniert': {
        'url': 'https://geoservices.bayern.de/od/wms/dgm/v1/relief',
        'options': {
            'layers': 'by_relief_kombiniert',
            'format': 'image/png',
            'transparent': True,
            'attribution': 'Geländerelief &copy; LDBV',
            'version': '1.3.0',
            'maxZoom': 20
        }
    }
}

# This dictionary defines which terrain layer to use based on the region and zoom level.
# It allows for dynamic selection of the best available map.
layer_logic = {
    "bavaria": {
        "15": 'by_lidar_kombiniert',
        "14": 'by_lidar_schraeglicht',
        "0": 'de_gelaende' # Default for lower zoom levels
    },
    "germany": {
        "0": 'de_gelaende'
    }
}
