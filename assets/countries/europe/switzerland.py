# This module contains the terrain layer definitions and geographical bounds for Switzerland.

# Bounding box defines the geographical area for Switzerland.
# The format is [south_lat, west_lon], [north_lat, east_lon]
bounds = {
    "switzerland": [[45.8, 5.9], [47.8, 10.5]]
}

# Definitions for the terrain layers available for Switzerland.
terrain_layers = {
    'ch_dtm': {
        'url': 'https://wms.geo.admin.ch/',
        'options': {
            'layers': 'ch.swisstopo.swissalti3d-reliefschattierung',
            'format': 'image/png',
            'transparent': True,
            'attribution': 'Relief © swisstopo',
            # --- FIX: Added the required WMS version parameter ---
            'version': '1.3.0' 
        }
    }
}

# This dictionary defines which terrain layer to use based on the region and zoom level.
layer_logic = {
    "switzerland": {
        "0": 'ch_dtm' # Use this layer at all zoom levels when inside the switzerland bounds
    }
}
