# This module contains the terrain layer definitions and geographical bounds for Austria.

# Bounding box defines the geographical area for Austria.
# The format is [south_lat, west_lon], [north_lat, east_lon]
bounds = {
    "austria": [[46.3, 9.5], [49.1, 17.2]]
}

# Definitions for the terrain layers available for Austria.
# --- FIX: Using the correct WMTS service URL without subdomains ---
terrain_layers = {
    'at_dtm': {
        'url': 'https://maps.wien.gv.at/basemap/bmapgelaende/grau/google3857/{z}/{y}/{x}.jpeg',
        'options': {
            'attribution': 'Geländedarstellung aus Digitalem Geländemodell (DGM) | Datenquelle: basemap.at'
        }
    }
}

# This dictionary defines which terrain layer to use based on the region and zoom level.
layer_logic = {
    "austria": {
        "0": 'at_dtm' # Use this layer at all zoom levels when inside the austria bounds
    }
}
