import requests
import json

# URL for high-resolution country borders - RESTORED TO WORKING VERSION
COUNTRIES_URL = "https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson"

# URLs for specific, high-quality GeoJSON data for major European countries
COUNTRY_SPECIFIC_REGIONS = {
    "Germany": "https://raw.githubusercontent.com/isellsoap/deutschlandGeoJSON/main/2_bundeslaender/1_sehr_hoch.geo.json",
    "Italy": "https://raw.githubusercontent.com/openpolis/geojson-italy/master/geojson/limits_IT_regions.geojson",
    "France": "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/regions.geojson",
    "Spain": "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/spain-communities.geojson",
    "Austria": "https://raw.githubusercontent.com/codeforgermany/click_that_hood/master/public/data/austria-states.geojson",
    "Switzerland": "https://raw.githubusercontent.com/ginseng666/GeoJSON-TopoJSON-Switzerland/master/2021/simplified-geojson/cantons_95_geo.json"
}

# Fallback URL for other countries' regions from Natural Earth
GENERAL_REGIONS_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_1_states_provinces.geojson"

# A specific list of European countries to keep the menu clean and fast
EUROPEAN_COUNTRIES = [
    "Albania", "Andorra", "Austria", "Belarus", "Belgium", "Bosnia and Herzegovina",
    "Bulgaria", "Croatia", "Cyprus", "Czechia", "Denmark", "Estonia", "Finland",
    "France", "Germany", "Greece", "Hungary", "Iceland", "Ireland", "Italy",
    "Kosovo", "Latvia", "Liechtenstein", "Lithuania", "Luxembourg", "Malta",
    "Moldova", "Monaco", "Montenegro", "Netherlands", "North Macedonia", "Norway",
    "Poland", "Portugal", "Romania", "Russia", "San Marino", "Serbia", "Slovakia",
    "Slovenia", "Spain", "Sweden", "Switzerland", "Ukraine", "United Kingdom", "Vatican City"
]

def get_geojson_from_url(url):
    """
    Fetches GeoJSON data from a given URL.
    """
    try:
        response = requests.get(url, timeout=30) # Increased timeout for larger files
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from {url}: {e}")
        raise
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {url}")
        raise

def get_admin_borders(admin_level, country_name=None):
    """
    Returns GeoJSON data for a given administrative level.
    """
    if admin_level == 4:  # All Countries
        print("Fetching all country borders...")
        return get_geojson_from_url(COUNTRIES_URL)
    elif admin_level == 6:  # Regions
        if country_name == "ALL":
             print("Fetching all European regions...")
             return get_geojson_from_url(GENERAL_REGIONS_URL)
        if country_name in COUNTRY_SPECIFIC_REGIONS:
            print(f"Fetching specific regions for {country_name}...")
            return get_geojson_from_url(COUNTRY_SPECIFIC_REGIONS[country_name])
        elif country_name:
             # Fallback to the general regions file for other countries
            print(f"Fetching regions for {country_name} from general source...")
            all_regions = get_geojson_from_url(GENERAL_REGIONS_URL)
            country_features = [
                f for f in all_regions.get('features', [])
                if f.get('properties', {}).get('admin') == country_name
            ]
            return {"type": "FeatureCollection", "features": country_features}
        else:
             return {"type": "FeatureCollection", "features": []}
    else:
        return {"type": "FeatureCollection", "features": []}

def get_country_list():
    """
    Returns the hardcoded list of European countries.
    """
    return EUROPEAN_COUNTRIES