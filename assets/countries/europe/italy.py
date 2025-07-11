# This module contains the terrain layer definitions and geographical bounds for Italy.

# Bounding box defines the geographical area for Italy.
# The format is [south_lat, west_lon], [north_lat, east_lon]
bounds = {
    "italy": [[35.5, 6.6], [47.1, 18.5]]
}

# Definitions for the terrain layers available for this country.
# --- FIX: Using the reliable terrestris.de WMS service ---
terrain_layers = {
    'it_dtm': {
        'url': 'https://ows.terrestris.de/osm/service?',
        'options': {
            'layers': 'SRTM30-Hillshade',
            'format': 'image/png',
            'transparent': True,
            'attribution': 'SRTM30-Hillshade &copy; terrestris',
            'version': '1.1.1',
            'srs': 'EPSG:3857'
        }
    }
}

# This dictionary defines which terrain layer to use based on the region and zoom level.
layer_logic = {
    "italy": {
        "0": 'it_dtm' # Use this layer at all zoom levels when inside the italy bounds
    }
}
