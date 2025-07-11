import requests
import json

def overpass_to_geojson(overpass_json):
    """
    Converts the JSON output from the Overpass API to a standard GeoJSON
    FeatureCollection that Leaflet can understand.
    """
    features = []
    for element in overpass_json.get('elements', []):
        # Ensure the element has geometry data to draw
        if 'geometry' not in element:
            continue

        # Convert Overpass geometry (a list of {lat, lon} dicts) 
        # to GeoJSON coordinates (a list of [lon, lat] lists)
        coords = [[pt['lon'], pt['lat']] for pt in element['geometry']]

        # Create the GeoJSON Feature
        feature = {
            'type': 'Feature',
            'properties': element.get('tags', {}),
            'geometry': {
                # Boundaries are typically polygons.
                'type': 'Polygon',
                # GeoJSON polygons require an extra level of nesting for their coordinates
                'coordinates': [coords] 
            }
        }
        features.append(feature)

    return {
        'type': 'FeatureCollection',
        'features': features
    }


def get_admin_borders(bbox, admin_level):
    """
    Fetches administrative boundaries from the Overpass API for a given bounding box and admin level.
    The fetched data is then converted to GeoJSON.
    """
    # Overpass API endpoint
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    # The Overpass QL query to find administrative boundaries within the bbox
    query = f"""
    [out:json][timeout:30];
    (
      relation["boundary"="administrative"]["admin_level"="{admin_level}"]({bbox});
    );
    out geom;
    """
    
    try:
        # Make the request to the API
        response = requests.get(overpass_url, params={'data': query})
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        
        # ** THE FIX IS HERE: Convert the raw data to GeoJSON before returning **
        overpass_data = response.json()
        return overpass_to_geojson(overpass_data)

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching data from Overpass API: {e}")
        # Return an empty GeoJSON feature collection on error
        return {"type": "FeatureCollection", "features": []}
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from Overpass API: {e}")
        return {"type": "FeatureCollection", "features": []}

