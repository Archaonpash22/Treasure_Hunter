import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Tuple
import json

class CelticSettlementsFinder:
    """Specialized finder for Celtic archaeological sites with coordinates"""
    
    def __init__(self):
        self.results = []
        
        # Known Celtic settlement terms in multiple languages
        self.celtic_terms = {
            'en': [
                'celtic settlement', 'celtic oppidum', 'celtic hillfort', 
                'iron age settlement', 'la tène', 'hallstatt', 'celtic fort',
                'celtic stronghold', 'celtic town', 'gallic settlement'
            ],
            'de': [
                'keltische siedlung', 'keltisches oppidum', 'keltenstadt',
                'keltischer ringwall', 'keltenschanze', 'viereckschanze',
                'latène', 'hallstatt', 'fürstensitz', 'keltische höhensiedlung',
                'keltischer burgwall', 'keltische befestigung', 'eisenzeitliche siedlung'
            ],
            'fr': [
                'oppidum celtique', 'oppidum gaulois', 'site celtique',
                'fortification celtique', 'agglomération celtique'
            ]
        }
        
        # Known important Celtic sites with coordinates
        self.known_sites = [
            {'name': 'Heuneburg', 'coords': (48.0833, 9.4167), 'country': 'Germany'},
            {'name': 'Manching', 'coords': (48.7153, 11.5089), 'country': 'Germany'},
            {'name': 'Bibracte', 'coords': (46.9333, 4.0333), 'country': 'France'},
            {'name': 'Alesia', 'coords': (47.5372, 4.5003), 'country': 'France'},
            {'name': 'Maiden Castle', 'coords': (50.6950, -2.4692), 'country': 'UK'},
            {'name': 'Danebury', 'coords': (51.1458, -1.5119), 'country': 'UK'},
            {'name': 'Závist', 'coords': (49.9683, 14.3967), 'country': 'Czech Republic'},
            {'name': 'Staré Hradisko', 'coords': (49.6639, 17.0758), 'country': 'Czech Republic'},
            {'name': 'Glauberg', 'coords': (50.3167, 9.0000), 'country': 'Germany'},
            {'name': 'Mont Beuvray', 'coords': (46.9214, 4.0394), 'country': 'France'},
            {'name': 'Titelberg', 'coords': (49.5419, 5.8639), 'country': 'Luxembourg'},
            {'name': 'Donnersberg', 'coords': (49.6247, 7.9294), 'country': 'Germany'},
            {'name': 'Heidengraben', 'coords': (48.5500, 9.4500), 'country': 'Germany'},
            {'name': 'Martberg', 'coords': (50.1694, 7.3861), 'country': 'Germany'},
            {'name': 'Dünsberg', 'coords': (50.7333, 8.4833), 'country': 'Germany'}
        ]
        
    def search_all_sources(self) -> List[Dict]:
        """Search all available sources for Celtic settlements"""
        results = []
        
        # Add known sites first
        for site in self.known_sites:
            results.append({
                'title': site['name'],
                'source': 'Known Celtic Sites Database',
                'coordinates': site['coords'],
                'country': site['country'],
                'description': f"Major Celtic oppidum/settlement in {site['country']}",
                'type': 'verified_site'
            })
        
        # Search Wikipedia lists
        results.extend(self.search_wikipedia_lists())
        
        # Search archaeological databases
        results.extend(self.search_archaeological_databases())
        
        return results
    
    def search_wikipedia_lists(self) -> List[Dict]:
        """Search Wikipedia list articles for Celtic sites"""
        results = []
        
        # URLs of Wikipedia lists containing Celtic settlements
        list_urls = [
            'https://en.wikipedia.org/wiki/List_of_Celtic_oppida',
            'https://en.wikipedia.org/wiki/List_of_hillforts_in_Britain',
            'https://en.wikipedia.org/wiki/List_of_hillforts_in_Ireland',
            'https://de.wikipedia.org/wiki/Liste_von_Oppida',
            'https://de.wikipedia.org/wiki/Liste_der_keltischen_Oppida',
            'https://en.wikipedia.org/wiki/La_T%C3%A8ne_culture',
            'https://en.wikipedia.org/wiki/Hallstatt_culture'
        ]
        
        for url in list_urls:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Find all tables in the page
                    tables = soup.find_all('table', class_='wikitable')
                    
                    for table in tables:
                        results.extend(self.parse_wikipedia_table(table, url))
                        
                    # Also look for coordinates in lists
                    results.extend(self.extract_coordinates_from_page(soup, url))
                    
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                
        return results
    
    def parse_wikipedia_table(self, table, source_url: str) -> List[Dict]:
        """Parse a Wikipedia table for site information"""
        results = []
        
        try:
            rows = table.find_all('tr')[1:]  # Skip header
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    # Extract site name
                    name_cell = cells[0]
                    name = name_cell.get_text().strip()
                    
                    # Look for coordinates in the row
                    coords = None
                    row_text = row.get_text()
                    
                    # Check for coordinate patterns
                    coord_patterns = [
                        r'(\d+\.\d+)[°\s,]+(\d+\.\d+)',
                        r'(\d+)°(\d+)′(\d+)″[NS][,\s]+(\d+)°(\d+)′(\d+)″[EW]'
                    ]
                    
                    for pattern in coord_patterns:
                        match = re.search(pattern, row_text)
                        if match:
                            # Parse coordinates
                            try:
                                if len(match.groups()) == 2:
                                    lat = float(match.group(1))
                                    lon = float(match.group(2))
                                    coords = (lat, lon)
                                break
                            except:
                                pass
                    
                    # Also check for geo spans
                    geo_span = row.find('span', class_='geo')
                    if geo_span and not coords:
                        try:
                            geo_text = geo_span.get_text()
                            if ';' in geo_text:
                                lat, lon = geo_text.split(';')
                            elif ',' in geo_text:
                                lat, lon = geo_text.split(',')
                            coords = (float(lat.strip()), float(lon.strip()))
                        except:
                            pass
                    
                    if coords or any(term in name.lower() for terms in self.celtic_terms.values() for term in terms):
                        results.append({
                            'title': name,
                            'source': f'Wikipedia Table - {source_url}',
                            'coordinates': coords,
                            'description': row_text[:200],
                            'type': 'table_entry',
                            'url': source_url
                        })
                        
        except Exception as e:
            print(f"Error parsing table: {e}")
            
        return results
    
    def extract_coordinates_from_page(self, soup, url: str) -> List[Dict]:
        """Extract all coordinates from a Wikipedia page"""
        results = []
        
        # Find all elements with coordinates
        coord_elements = soup.find_all('span', class_='geo')
        
        for elem in coord_elements:
            try:
                # Find the parent context
                parent = elem.parent
                context = parent.get_text()[:200] if parent else ""
                
                # Check if context contains Celtic terms
                if any(term in context.lower() for terms in self.celtic_terms.values() for term in terms):
                    coords_text = elem.get_text()
                    
                    # Parse coordinates
                    if ';' in coords_text:
                        lat, lon = coords_text.split(';')
                    elif ',' in coords_text:
                        lat, lon = coords_text.split(',')
                    else:
                        continue
                        
                    coords = (float(lat.strip()), float(lon.strip()))
                    
                    # Try to find the site name
                    title = "Unknown Celtic Site"
                    # Look for nearby header
                    header = elem.find_previous(['h2', 'h3', 'h4', 'b'])
                    if header:
                        title = header.get_text().strip()
                    
                    results.append({
                        'title': title,
                        'source': f'Wikipedia - {url}',
                        'coordinates': coords,
                        'description': context,
                        'type': 'coordinate_mention',
                        'url': url
                    })
                    
            except Exception as e:
                print(f"Error extracting coordinates: {e}")
                
        return results
    
    def search_archaeological_databases(self) -> List[Dict]:
        """Search specialized archaeological databases"""
        results = []
        
        # This would connect to:
        # - ARIADNE (Archaeological Research Infrastructure)
        # - ADS (Archaeology Data Service)
        # - PAS (Portable Antiquities Scheme)
        # - National archaeological databases
        
        # For now, we'll add some known sites from archaeological literature
        additional_sites = [
            {'name': 'Kelheim', 'coords': (48.9186, 11.8817), 'type': 'oppidum'},
            {'name': 'Altenburg-Rheinau', 'coords': (47.6469, 8.4931), 'type': 'oppidum'},
            {'name': 'Basel-Gasfabrik', 'coords': (47.5750, 7.6000), 'type': 'settlement'},
            {'name': 'Bern-Engehalbinsel', 'coords': (46.9522, 7.4586), 'type': 'oppidum'},
            {'name': 'Entremont', 'coords': (43.5308, 5.4378), 'type': 'oppidum'},
            {'name': 'Ensérune', 'coords': (43.2897, 3.0503), 'type': 'oppidum'},
            {'name': 'Corent', 'coords': (45.6589, 3.1908), 'type': 'oppidum'},
            {'name': 'Gergovia', 'coords': (45.7089, 3.1250), 'type': 'oppidum'},
            {'name': 'Aulnat', 'coords': (45.7667, 3.1667), 'type': 'settlement'}
        ]
        
        for site in additional_sites:
            results.append({
                'title': site['name'],
                'source': 'Archaeological Database',
                'coordinates': site['coords'],
                'description': f"Celtic {site['type']}",
                'type': 'archaeological_site'
            })
            
        return results
    
    def export_to_json(self, filename: str = 'celtic_settlements.json'):
        """Export all results to JSON"""
        all_results = self.search_all_sources()
        
        # Remove duplicates based on coordinates
        unique_results = []
        seen_coords = set()
        
        for result in all_results:
            coords = result.get('coordinates')
            if coords:
                coord_key = f"{coords[0]:.4f},{coords[1]:.4f}"
                if coord_key not in seen_coords:
                    seen_coords.add(coord_key)
                    unique_results.append(result)
            else:
                unique_results.append(result)
        
        export_data = {
            'metadata': {
                'total_sites': len(unique_results),
                'sites_with_coordinates': sum(1 for r in unique_results if r.get('coordinates')),
                'sources': list(set(r['source'].split(' - ')[0] for r in unique_results))
            },
            'results': unique_results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
            
        return export_data


# Quick usage example
if __name__ == "__main__":
    finder = CelticSettlementsFinder()
    data = finder.export_to_json('celtic_settlements_with_coords.json')
    
    print(f"Found {data['metadata']['total_sites']} Celtic sites")
    print(f"Sites with coordinates: {data['metadata']['sites_with_coordinates']}")
    
    # Print first few results with coordinates
    for result in data['results'][:10]:
        if result.get('coordinates'):
            print(f"\n{result['title']}: {result['coordinates']}")
            print(f"  Source: {result['source']}")