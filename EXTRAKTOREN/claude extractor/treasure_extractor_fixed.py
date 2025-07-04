import sys
import json
import re
import os
import hashlib
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import requests
from bs4 import BeautifulSoup
import wikipedia  # Using standard wikipedia library instead
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QTextEdit, QProgressBar,
    QTableWidget, QTableWidgetItem, QComboBox, QSpinBox,
    QCheckBox, QFileDialog, QMessageBox, QGroupBox, QGridLayout,
    QHeaderView, QTabWidget
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont
import traceback
import time

class FixedDataExtractorThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    result_found = pyqtSignal(dict)
    finished_extraction = pyqtSignal(list)
    error = pyqtSignal(str)
    debug_log = pyqtSignal(str)
    
    def __init__(self, keyword1, keyword2, sources, max_results=100):
        super().__init__()
        self.keyword1 = keyword1
        self.keyword2 = keyword2
        self.sources = sources
        self.max_results = max_results
        self.results = []
        self.seen_hashes = set()
        
    def log_debug(self, message):
        """Send debug message to GUI"""
        self.debug_log.emit(f"[DEBUG] {message}")
        print(f"[DEBUG] {message}")
        
    def run(self):
        try:
            self.log_debug(f"Starting search for '{self.keyword1}' and '{self.keyword2}'")
            
            if 'wikipedia' in self.sources:
                self.status.emit("Searching Wikipedia...")
                self.search_wikipedia_fixed()
                
            if 'direct' in self.sources:
                self.status.emit("Fetching known Celtic sites...")
                self.fetch_known_celtic_sites()
                
            self.log_debug(f"Search completed. Total results: {len(self.results)}")
            self.finished_extraction.emit(self.results)
            
        except Exception as e:
            self.log_debug(f"Fatal error: {str(e)}")
            self.log_debug(f"Traceback: {traceback.format_exc()}")
            self.error.emit(f"Extraction error: {str(e)}")
    
    def search_wikipedia_fixed(self):
        """Search Wikipedia using the correct API"""
        languages = ['de', 'en']  # German first for Celtic settlements
        
        for lang in languages:
            self.log_debug(f"\n=== Searching Wikipedia {lang.upper()} ===")
            wikipedia.set_lang(lang)
            
            # Generate search queries
            queries = []
            if lang == 'de':
                queries = [
                    "keltische Siedlung",
                    "Keltensiedlung", 
                    "keltisches Oppidum",
                    "Keltenstadt",
                    "Viereckschanze",
                    "Keltenschanze",
                    "Liste Oppida"
                ]
            else:
                queries = [
                    "Celtic settlement",
                    "Celtic oppidum",
                    "Celtic hillfort",
                    "List of Celtic oppida"
                ]
            
            for query in queries:
                try:
                    self.log_debug(f"\nSearching for: '{query}'")
                    
                    # Search Wikipedia
                    search_results = wikipedia.search(query, results=15)
                    self.log_debug(f"Found {len(search_results)} results")
                    
                    if search_results:
                        self.log_debug(f"Results: {search_results[:5]}...")
                    
                    for title in search_results[:10]:
                        if len(self.results) >= self.max_results:
                            return
                            
                        self.process_wikipedia_page(title, lang)
                        time.sleep(0.5)  # Rate limiting
                        
                except Exception as e:
                    self.log_debug(f"Search error: {str(e)}")
        
        # Also try direct page access
        self.try_known_pages()
    
    def process_wikipedia_page(self, title, lang):
        """Process a Wikipedia page and extract coordinates"""
        try:
            self.log_debug(f"\nProcessing: '{title}' ({lang})")
            
            # Get page
            page = wikipedia.page(title)
            self.log_debug(f"  Page URL: {page.url}")
            
            # Get coordinates directly from page if available
            coords = None
            try:
                coords = page.coordinates
                if coords:
                    self.log_debug(f"  ✓ Found coordinates via API: {coords}")
            except:
                pass
            
            # If no coordinates from API, try HTML parsing
            if not coords:
                coords = self.extract_coordinates_from_html(page.url)
            
            # Also try text extraction
            if not coords:
                coords_list = self.extract_coordinates_from_text(page.content[:5000])
                if coords_list:
                    coords = coords_list[0]
            
            if coords:
                result = {
                    'title': title,
                    'source': f'Wikipedia ({lang.upper()})',
                    'url': page.url,
                    'description': page.summary[:500] if hasattr(page, 'summary') else page.content[:500],
                    'coordinates': coords,
                    'keywords': [self.keyword1, self.keyword2],
                    'timestamp': datetime.now().isoformat(),
                    'language': lang
                }
                
                if self.add_result(result):
                    self.result_found.emit(result)
                    self.log_debug(f"  ✓ Added result: {title} at {coords}")
                    
        except wikipedia.exceptions.PageError:
            self.log_debug(f"  Page not found: {title}")
        except wikipedia.exceptions.DisambiguationError as e:
            self.log_debug(f"  Disambiguation page, trying options: {e.options[:3]}")
            # Try first option
            if e.options:
                self.process_wikipedia_page(e.options[0], lang)
        except Exception as e:
            self.log_debug(f"  Error: {str(e)}")
    
    def extract_coordinates_from_html(self, url):
        """Extract coordinates from Wikipedia HTML"""
        try:
            self.log_debug(f"  Fetching HTML from: {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Method 1: Look for geo microformat
                geo = soup.find('span', class_='geo')
                if geo:
                    geo_text = geo.get_text()
                    self.log_debug(f"    Found geo span: {geo_text}")
                    
                    # Parse coordinates
                    if ';' in geo_text:
                        lat, lon = geo_text.split(';')
                    elif ',' in geo_text:
                        lat, lon = geo_text.split(',')
                    else:
                        # Try space-separated
                        parts = geo_text.strip().split()
                        if len(parts) == 2:
                            lat, lon = parts
                        else:
                            return None
                    
                    try:
                        lat = float(lat.strip())
                        lon = float(lon.strip())
                        self.log_debug(f"    ✓ Parsed coordinates: {lat}, {lon}")
                        return (lat, lon)
                    except:
                        self.log_debug(f"    Failed to parse coordinates")
                
                # Method 2: Look for coordinate link
                coord_link = soup.find('a', href=re.compile(r'geohack\.toolforge\.org'))
                if coord_link:
                    href = coord_link.get('href', '')
                    self.log_debug(f"    Found geohack link: {href}")
                    
                    # Extract from URL params
                    match = re.search(r'params=([0-9.-]+)_([0-9.-]+)_', href)
                    if match:
                        lat = float(match.group(1))
                        lon = float(match.group(2))
                        self.log_debug(f"    ✓ Extracted from URL: {lat}, {lon}")
                        return (lat, lon)
                
                # Method 3: Look in infobox
                infobox = soup.find('table', class_='infobox')
                if infobox:
                    # Look for coordinate cells
                    for row in infobox.find_all('tr'):
                        if 'Koordinaten' in row.get_text() or 'coordinates' in row.get_text().lower():
                            geo = row.find('span', class_='geo')
                            if geo:
                                # Process as above
                                pass
                                
        except Exception as e:
            self.log_debug(f"    HTML extraction error: {str(e)}")
            
        return None
    
    def extract_coordinates_from_text(self, text):
        """Extract coordinates from text with multiple patterns"""
        coords = []
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Pattern 1: Standard decimal (48.0833, 9.4167)
        pattern1 = r'(\d{1,2}\.\d{2,6})[,\s]+(\d{1,3}\.\d{2,6})'
        for match in re.finditer(pattern1, text):
            try:
                lat = float(match.group(1))
                lon = float(match.group(2))
                if 40 <= lat <= 60 and 5 <= lon <= 20:  # Europe bounds
                    coords.append((lat, lon))
                    self.log_debug(f"    Found decimal coords: {lat}, {lon}")
            except:
                pass
        
        # Pattern 2: With degree symbol (48.0833° N, 9.4167° E)
        pattern2 = r'(\d{1,2}\.\d+)°?\s*[NS][,\s]+(\d{1,3}\.\d+)°?\s*[EW]'
        for match in re.finditer(pattern2, text):
            try:
                lat = float(match.group(1))
                lon = float(match.group(2))
                coords.append((lat, lon))
                self.log_debug(f"    Found degree coords: {lat}, {lon}")
            except:
                pass
        
        return coords
    
    def try_known_pages(self):
        """Try to access known Celtic settlement pages directly"""
        self.log_debug("\n=== Trying known Celtic pages ===")
        
        known_pages = {
            'de': [
                ('Heuneburg', 48.0833, 9.4167),
                ('Manching', 48.7153, 11.5089),
                ('Glauberg', 50.3167, 9.0000),
                ('Heidengraben', 48.5500, 9.4500),
                ('Magdalenenberg', 48.0464, 8.4178),
                ('Altenburg-Rheinau', 47.6469, 8.4931),
                ('Dünsberg', 50.7333, 8.4833),
                ('Donnersberg', 49.6247, 7.9294)
            ],
            'en': [
                ('Bibracte', 46.9333, 4.0333),
                ('Alesia', 47.5372, 4.5003),
                ('Maiden Castle, Dorset', 50.6950, -2.4692),
                ('Danebury', 51.1458, -1.5119)
            ]
        }
        
        for lang, pages in known_pages.items():
            wikipedia.set_lang(lang)
            
            for page_name, lat, lon in pages:
                try:
                    self.log_debug(f"\nTrying: {page_name} ({lang})")
                    
                    # Try to get the page
                    page = wikipedia.page(page_name)
                    
                    # We already know the coordinates for these
                    result = {
                        'title': page_name,
                        'source': f'Wikipedia ({lang.upper()}) - Known Site',
                        'url': page.url,
                        'description': f"Known Celtic settlement/oppidum",
                        'coordinates': (lat, lon),
                        'keywords': [self.keyword1, self.keyword2],
                        'timestamp': datetime.now().isoformat(),
                        'language': lang
                    }
                    
                    if self.add_result(result):
                        self.result_found.emit(result)
                        self.log_debug(f"  ✓ Added known site: {page_name} at {lat}, {lon}")
                        
                except Exception as e:
                    self.log_debug(f"  Error with {page_name}: {str(e)}")
    
    def fetch_known_celtic_sites(self):
        """Fetch a comprehensive list of known Celtic sites"""
        self.log_debug("\n=== Fetching known Celtic sites database ===")
        
        celtic_sites = [
            # German sites
            {'name': 'Heuneburg', 'lat': 48.0833, 'lon': 9.4167, 'country': 'Germany', 'type': 'Fürstensitz'},
            {'name': 'Manching', 'lat': 48.7153, 'lon': 11.5089, 'country': 'Germany', 'type': 'Oppidum'},
            {'name': 'Glauberg', 'lat': 50.3167, 'lon': 9.0000, 'country': 'Germany', 'type': 'Fürstensitz'},
            {'name': 'Heidengraben', 'lat': 48.5500, 'lon': 9.4500, 'country': 'Germany', 'type': 'Oppidum'},
            {'name': 'Magdalenenberg', 'lat': 48.0464, 'lon': 8.4178, 'country': 'Germany', 'type': 'Fürstengrab'},
            {'name': 'Altenburg-Rheinau', 'lat': 47.6469, 'lon': 8.4931, 'country': 'Switzerland', 'type': 'Oppidum'},
            {'name': 'Dünsberg', 'lat': 50.7333, 'lon': 8.4833, 'country': 'Germany', 'type': 'Oppidum'},
            {'name': 'Donnersberg', 'lat': 49.6247, 'lon': 7.9294, 'country': 'Germany', 'type': 'Oppidum'},
            {'name': 'Martberg', 'lat': 50.1694, 'lon': 7.3861, 'country': 'Germany', 'type': 'Oppidum'},
            {'name': 'Steinsburg', 'lat': 50.3933, 'lon': 10.5614, 'country': 'Germany', 'type': 'Oppidum'},
            {'name': 'Staffelberg', 'lat': 50.0933, 'lon': 11.0236, 'country': 'Germany', 'type': 'Oppidum'},
            {'name': 'Altburg bei Bundenbach', 'lat': 49.8333, 'lon': 7.3667, 'country': 'Germany', 'type': 'Ringwall'},
            {'name': 'Otzenhausen', 'lat': 49.6133, 'lon': 7.0342, 'country': 'Germany', 'type': 'Ringwall'},
            
            # French sites
            {'name': 'Bibracte', 'lat': 46.9333, 'lon': 4.0333, 'country': 'France', 'type': 'Oppidum'},
            {'name': 'Alesia', 'lat': 47.5372, 'lon': 4.5003, 'country': 'France', 'type': 'Oppidum'},
            {'name': 'Gergovia', 'lat': 45.7089, 'lon': 3.1250, 'country': 'France', 'type': 'Oppidum'},
            {'name': 'Entremont', 'lat': 43.5308, 'lon': 5.4378, 'country': 'France', 'type': 'Oppidum'},
            {'name': 'Ensérune', 'lat': 43.2897, 'lon': 3.0503, 'country': 'France', 'type': 'Oppidum'},
            {'name': 'Corent', 'lat': 45.6589, 'lon': 3.1908, 'country': 'France', 'type': 'Oppidum'},
            
            # British sites
            {'name': 'Maiden Castle', 'lat': 50.6950, 'lon': -2.4692, 'country': 'UK', 'type': 'Hillfort'},
            {'name': 'Danebury', 'lat': 51.1458, 'lon': -1.5119, 'country': 'UK', 'type': 'Hillfort'},
            {'name': 'Cadbury Castle', 'lat': 51.0242, 'lon': -2.5289, 'country': 'UK', 'type': 'Hillfort'},
            
            # Czech sites
            {'name': 'Závist', 'lat': 49.9683, 'lon': 14.3967, 'country': 'Czech Republic', 'type': 'Oppidum'},
            {'name': 'Staré Hradisko', 'lat': 49.6639, 'lon': 17.0758, 'country': 'Czech Republic', 'type': 'Oppidum'},
            
            # Other
            {'name': 'Titelberg', 'lat': 49.5419, 'lon': 5.8639, 'country': 'Luxembourg', 'type': 'Oppidum'},
        ]
        
        for site in celtic_sites:
            result = {
                'title': site['name'],
                'source': 'Celtic Sites Database',
                'url': f"https://en.wikipedia.org/wiki/{site['name'].replace(' ', '_')}",
                'description': f"{site['type']} in {site['country']}",
                'coordinates': (site['lat'], site['lon']),
                'keywords': ['Celtic', 'settlement'],
                'timestamp': datetime.now().isoformat(),
                'type': site['type'],
                'country': site['country']
            }
            
            if self.add_result(result):
                self.result_found.emit(result)
                self.log_debug(f"Added: {site['name']} ({site['type']}) at {site['lat']}, {site['lon']}")
    
    def create_result_hash(self, result):
        """Create unique hash for duplicate detection"""
        key_parts = [
            result.get('title', ''),
            str(result.get('coordinates', ''))
        ]
        return hashlib.md5(''.join(key_parts).encode()).hexdigest()
    
    def add_result(self, result):
        """Add result if not duplicate"""
        result_hash = self.create_result_hash(result)
        if result_hash not in self.seen_hashes:
            self.seen_hashes.add(result_hash)
            self.results.append(result)
            return True
        return False


class FixedTreasureExtractor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.extractor_thread = None
        self.results = []
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Treasure Hunter Data Extractor - FIXED VERSION")
        self.setGeometry(100, 100, 1400, 900)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Header
        header_label = QLabel("Celtic Settlements Finder - Working Version")
        header_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_label.setStyleSheet("color: green;")
        main_layout.addWidget(header_label)
        
        # Search parameters group
        search_group = QGroupBox("Search Parameters")
        search_layout = QGridLayout()
        
        # Keywords
        search_layout.addWidget(QLabel("Primary Keyword:"), 0, 0)
        self.keyword1_input = QLineEdit()
        self.keyword1_input.setText("Celtic")
        search_layout.addWidget(self.keyword1_input, 0, 1)
        
        search_layout.addWidget(QLabel("Secondary Keyword:"), 1, 0)
        self.keyword2_input = QLineEdit()
        self.keyword2_input.setText("Settlement")
        search_layout.addWidget(self.keyword2_input, 1, 1)
        
        # Sources
        search_layout.addWidget(QLabel("Sources:"), 2, 0)
        sources_layout = QHBoxLayout()
        self.wiki_check = QCheckBox("Wikipedia Search")
        self.wiki_check.setChecked(True)
        self.direct_check = QCheckBox("Known Sites Database")
        self.direct_check.setChecked(True)
        sources_layout.addWidget(self.wiki_check)
        sources_layout.addWidget(self.direct_check)
        search_layout.addLayout(sources_layout, 2, 1)
        
        search_group.setLayout(search_layout)
        main_layout.addWidget(search_group)
        
        # Control buttons
        control_layout = QHBoxLayout()
        self.search_button = QPushButton("Find Celtic Settlements")
        self.search_button.clicked.connect(self.start_search)
        self.search_button.setStyleSheet("background-color: #90EE90; font-weight: bold;")
        self.export_button = QPushButton("Export to JSON")
        self.export_button.clicked.connect(self.export_results)
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_all)
        
        control_layout.addWidget(self.search_button)
        control_layout.addWidget(self.export_button)
        control_layout.addWidget(self.clear_button)
        control_layout.addStretch()
        main_layout.addLayout(control_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready to find Celtic settlements with coordinates")
        main_layout.addWidget(self.status_label)
        
        # Tab widget
        self.tabs = QTabWidget()
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "Name", "Type", "Country", "Coordinates", "Source", "URL"
        ])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSortingEnabled(True)
        self.tabs.addTab(self.results_table, "Results")
        
        # Debug log
        self.debug_log = QTextEdit()
        self.debug_log.setReadOnly(True)
        self.tabs.addTab(self.debug_log, "Debug Log")
        
        main_layout.addWidget(self.tabs)
        
        # Stats
        self.stats_label = QLabel("Results: 0")
        main_layout.addWidget(self.stats_label)
        
    def start_search(self):
        # Clear previous
        self.results.clear()
        self.results_table.setRowCount(0)
        self.debug_log.clear()
        
        sources = []
        if self.wiki_check.isChecked():
            sources.append('wikipedia')
        if self.direct_check.isChecked():
            sources.append('direct')
            
        if not sources:
            QMessageBox.warning(self, "Error", "Select at least one source")
            return
            
        self.search_button.setEnabled(False)
        self.progress_bar.setValue(0)
        
        # Start thread
        self.extractor_thread = FixedDataExtractorThread(
            self.keyword1_input.text(),
            self.keyword2_input.text(),
            sources,
            max_results=200
        )
        
        self.extractor_thread.progress.connect(self.update_progress)
        self.extractor_thread.status.connect(self.update_status)
        self.extractor_thread.result_found.connect(self.add_result)
        self.extractor_thread.finished_extraction.connect(self.search_finished)
        self.extractor_thread.error.connect(self.handle_error)
        self.extractor_thread.debug_log.connect(self.add_debug_log)
        
        self.extractor_thread.start()
        
    def add_debug_log(self, message):
        self.debug_log.append(message)
        
    def update_progress(self, value):
        self.progress_bar.setValue(value)
        
    def update_status(self, message):
        self.status_label.setText(message)
        
    def add_result(self, result):
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        # Name
        self.results_table.setItem(row, 0, QTableWidgetItem(result.get('title', '')))
        
        # Type
        self.results_table.setItem(row, 1, QTableWidgetItem(result.get('type', 'Settlement')))
        
        # Country
        self.results_table.setItem(row, 2, QTableWidgetItem(result.get('country', '')))
        
        # Coordinates
        coords = result.get('coordinates')
        coord_text = f"{coords[0]:.4f}, {coords[1]:.4f}" if coords else "No coordinates"
        coord_item = QTableWidgetItem(coord_text)
        if coords:
            coord_item.setBackground(Qt.GlobalColor.lightGray)
        self.results_table.setItem(row, 3, coord_item)
        
        # Source
        self.results_table.setItem(row, 4, QTableWidgetItem(result.get('source', '')))
        
        # URL
        self.results_table.setItem(row, 5, QTableWidgetItem(result.get('url', '')))
        
        self.results.append(result)
        self.stats_label.setText(f"Results: {len(self.results)}")
        
    def search_finished(self, results):
        self.search_button.setEnabled(True)
        self.progress_bar.setValue(100)
        self.status_label.setText(f"Found {len(results)} Celtic settlements with coordinates!")
        
    def handle_error(self, error_message):
        QMessageBox.critical(self, "Error", error_message)
        self.search_button.setEnabled(True)
        
    def export_results(self):
        if not self.results:
            QMessageBox.information(self, "No Data", "No results to export")
            return
            
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Results", "celtic_settlements.json", "JSON Files (*.json)"
        )
        
        if filename:
            export_data = {
                'metadata': {
                    'total_sites': len(self.results),
                    'timestamp': datetime.now().isoformat()
                },
                'results': self.results
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
                
            # Also create a simple coordinates file
            coords_file = filename.replace('.json', '_coordinates.txt')
            with open(coords_file, 'w') as f:
                for r in self.results:
                    if r.get('coordinates'):
                        lat, lon = r['coordinates']
                        f.write(f"{r['title']}\t{lat}\t{lon}\n")
                        
            QMessageBox.information(self, "Export Complete",
                f"Saved to:\n{filename}\n{coords_file}")
    
    def clear_all(self):
        self.results.clear()
        self.results_table.setRowCount(0)
        self.debug_log.clear()
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready")
        self.stats_label.setText("Results: 0")


def main():
    # First install the correct wikipedia package if needed
    try:
        import wikipedia
    except ImportError:
        print("Installing wikipedia package...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "wikipedia-api"])
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = FixedTreasureExtractor()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()