import sys
import json
import re
import os
import hashlib
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Set
import requests
from bs4 import BeautifulSoup
import wikipediaapi
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QTextEdit, QProgressBar,
    QTableWidget, QTableWidgetItem, QComboBox, QSpinBox,
    QCheckBox, QFileDialog, QMessageBox, QGroupBox, QGridLayout,
    QHeaderView, QTabWidget
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont
import time
from urllib.parse import unquote
from concurrent.futures import ThreadPoolExecutor, as_completed

class DeepSearchExtractor(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    result_found = pyqtSignal(dict)
    finished_extraction = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, keyword1, keyword2, sources, max_results=100, languages=['en', 'de']):
        super().__init__()
        self.keyword1 = keyword1
        self.keyword2 = keyword2
        self.sources = sources
        self.max_results = max_results
        self.languages = languages
        self.results = []
        self.seen_hashes = set()
        self.processed_pages = set()
        
        # Wikipedia APIs for multiple languages
        self.wikis = {}
        for lang in languages:
            self.wikis[lang] = wikipediaapi.Wikipedia(
                language=lang,
                extract_format=wikipediaapi.ExtractFormat.WIKI,
                user_agent='TreasureHunter/2.0 Deep Search'
            )
        
    def run(self):
        try:
            if 'wikipedia' in self.sources:
                self.deep_wikipedia_search()
                
            if 'archive' in self.sources:
                self.search_archive_org()
                
            self.finished_extraction.emit(self.results)
            
        except Exception as e:
            self.error.emit(f"Extraction error: {str(e)}")
    
    def deep_wikipedia_search(self):
        """Perform deep Wikipedia search across multiple languages"""
        # Generate search variations
        search_variations = self.generate_search_variations()
        
        total_searches = len(search_variations) * len(self.languages)
        current_search = 0
        
        for lang in self.languages:
            wiki = self.wikis[lang]
            self.status.emit(f"Searching Wikipedia ({lang.upper()})...")
            
            for query in search_variations:
                current_search += 1
                self.progress.emit(int((current_search / total_searches) * 50))
                
                try:
                    # Search Wikipedia
                    search_results = wiki.search(query, results=30)
                    
                    for title in search_results:
                        if len(self.results) >= self.max_results:
                            return
                            
                        if title not in self.processed_pages:
                            self.process_wikipedia_page(wiki, title, lang)
                            
                    # Also search categories
                    self.search_wikipedia_categories(wiki, query, lang)
                    
                except Exception as e:
                    self.status.emit(f"Search error ({lang}): {str(e)}")
                    
                time.sleep(0.5)  # Rate limiting
    
    def generate_search_variations(self):
        """Generate multiple search query variations"""
        variations = []
        
        # Basic combinations
        variations.append(f"{self.keyword1} {self.keyword2}")
        variations.append(f"{self.keyword2} {self.keyword1}")
        
        # With additional context
        contexts = ["found", "discovered", "excavated", "site", "archaeological", "ancient", "historic"]
        for context in contexts:
            variations.append(f"{self.keyword1} {self.keyword2} {context}")
            variations.append(f"{context} {self.keyword1} {self.keyword2}")
        
        # German specific (if searching for Celtic settlements)
        if "kelt" in self.keyword1.lower() or "celt" in self.keyword1.lower():
            variations.extend([
                "keltische Siedlung",
                "Keltenstadt",
                "Oppidum",
                "Latène",
                "Hallstatt",
                "keltischer Ringwall",
                "Keltenschanze",
                "Viereckschanze"
            ])
            
        if "sied" in self.keyword2.lower() or "settl" in self.keyword2.lower():
            variations.extend([
                "Celtic settlement",
                "Celtic oppidum",
                "Celtic hillfort",
                "Iron Age settlement",
                "La Tène settlement"
            ])
            
        return list(set(variations))  # Remove duplicates
    
    def search_wikipedia_categories(self, wiki, query, lang):
        """Search Wikipedia categories for more results"""
        category_terms = {
            'en': ['Category:Celtic_sites', 'Category:Archaeological_sites', 
                   'Category:Iron_Age_sites', 'Category:Oppida'],
            'de': ['Kategorie:Archäologischer_Fundplatz', 'Kategorie:Keltische_Siedlung',
                   'Kategorie:Oppidum', 'Kategorie:Latènezeit']
        }
        
        if lang in category_terms:
            for category in category_terms[lang]:
                try:
                    cat_page = wiki.page(category)
                    if cat_page.exists():
                        # Get all pages in category
                        self.process_category_members(wiki, cat_page, lang)
                except:
                    pass
    
    def process_category_members(self, wiki, category_page, lang):
        """Process all members of a category"""
        try:
            # This would require additional API calls to get category members
            # For now, we'll process the category page itself
            self.process_wikipedia_page(wiki, category_page.title, lang)
        except:
            pass
    
    def process_wikipedia_page(self, wiki, title, lang):
        """Process a single Wikipedia page and extract data"""
        if title in self.processed_pages:
            return
            
        self.processed_pages.add(title)
        
        try:
            page = wiki.page(title)
            if not page.exists():
                return
                
            text = page.text
            
            # Check if page is relevant
            if not self.is_page_relevant(text):
                return
                
            # Extract all coordinates from the page
            all_coordinates = self.extract_all_coordinates(text)
            
            # Also try to get coordinates from infobox
            infobox_coords = self.extract_infobox_coordinates(page, lang)
            if infobox_coords:
                all_coordinates.extend(infobox_coords)
            
            # Get coordinates from the page HTML (more reliable)
            html_coords = self.extract_coordinates_from_html(page.fullurl)
            if html_coords:
                all_coordinates.extend(html_coords)
            
            if all_coordinates:
                # Remove duplicates
                unique_coords = list(set(all_coordinates))
                
                for coords in unique_coords:
                    result = {
                        'title': title,
                        'source': f'Wikipedia ({lang.upper()})',
                        'url': page.fullurl,
                        'description': self.extract_relevant_description(text, coords),
                        'coordinates': coords,
                        'keywords': [self.keyword1, self.keyword2],
                        'timestamp': datetime.now().isoformat(),
                        'language': lang
                    }
                    
                    if self.add_result(result):
                        self.result_found.emit(result)
                        
            # Follow links to related pages
            if len(self.results) < self.max_results:
                self.follow_relevant_links(wiki, page, lang)
                
        except Exception as e:
            self.status.emit(f"Error processing {title}: {str(e)}")
    
    def is_page_relevant(self, text):
        """Check if page content is relevant to search"""
        text_lower = text.lower()
        
        # Check for primary keywords
        keyword1_variations = [self.keyword1.lower()]
        keyword2_variations = [self.keyword2.lower()]
        
        # Add variations
        if "celt" in self.keyword1.lower():
            keyword1_variations.extend(["kelt", "gallic", "gaul", "iron age", "la tène", "hallstatt"])
        if "settl" in self.keyword2.lower():
            keyword2_variations.extend(["sied", "oppidum", "hillfort", "stadt", "site", "fundplatz"])
            
        # Check if any variation of both keywords present
        has_keyword1 = any(var in text_lower for var in keyword1_variations)
        has_keyword2 = any(var in text_lower for var in keyword2_variations)
        
        return has_keyword1 or has_keyword2  # More lenient matching
    
    def extract_all_coordinates(self, text):
        """Extract all coordinate patterns from text"""
        coords = []
        
        # Pattern 1: Decimal degrees
        decimal_pattern = r'(-?\d{1,3}\.\d{2,10})[,\s]+(-?\d{1,3}\.\d{2,10})'
        
        # Pattern 2: Degrees minutes seconds
        dms_pattern = r'(\d{1,3})°\s*(\d{1,2})[\′\']\s*(\d{1,2}(?:\.\d+)?)?[\″"]?\s*([NS])[,\s]+(\d{1,3})°\s*(\d{1,2})[\′\']\s*(\d{1,2}(?:\.\d+)?)?[\″"]?\s*([EW])'
        
        # Pattern 3: Coordinates with pipes (common in Wikipedia)
        pipe_pattern = r'(\d{1,3}\.\d+)\|(\d{1,3}\.\d+)'
        
        # Pattern 4: Coord template
        coord_template = r'[Cc]oord\|([^}]+)\}'
        
        # Extract decimal coordinates
        for match in re.finditer(decimal_pattern, text):
            try:
                lat = float(match.group(1))
                lon = float(match.group(2))
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    coords.append((lat, lon))
            except:
                pass
        
        # Extract DMS coordinates
        for match in re.finditer(dms_pattern, text):
            try:
                lat = self.dms_to_decimal(match.group(1), match.group(2), match.group(3), match.group(4))
                lon = self.dms_to_decimal(match.group(5), match.group(6), match.group(7), match.group(8))
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    coords.append((lat, lon))
            except:
                pass
                
        # Extract pipe-separated coordinates
        for match in re.finditer(pipe_pattern, text):
            try:
                lat = float(match.group(1))
                lon = float(match.group(2))
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    coords.append((lat, lon))
            except:
                pass
                
        # Extract from coord templates
        for match in re.finditer(coord_template, text):
            coord_text = match.group(1)
            # Parse coord template parameters
            parts = coord_text.split('|')
            try:
                if len(parts) >= 2:
                    lat = float(parts[0])
                    lon = float(parts[1])
                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                        coords.append((lat, lon))
            except:
                pass
                
        return coords
    
    def dms_to_decimal(self, deg, min, sec, direction):
        """Convert degrees, minutes, seconds to decimal"""
        decimal = float(deg) + float(min)/60 + (float(sec) if sec else 0)/3600
        if direction in ['S', 'W']:
            decimal = -decimal
        return decimal
    
    def extract_infobox_coordinates(self, page, lang):
        """Try to extract coordinates from Wikipedia infobox"""
        coords = []
        
        # Common coordinate parameter names in different languages
        coord_params = {
            'en': ['coordinates', 'coords', 'latd', 'longd', 'lat_deg', 'lon_deg'],
            'de': ['koordinaten', 'coord', 'breitengrad', 'längengrad']
        }
        
        # This would require parsing the wiki markup
        # For now, we'll rely on text extraction
        
        return coords
    
    def extract_coordinates_from_html(self, url):
        """Extract coordinates from the HTML page (more reliable)"""
        coords = []
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for coordinate spans
                geo_spans = soup.find_all('span', class_='geo')
                for span in geo_spans:
                    try:
                        coords_text = span.get_text()
                        # Parse different formats
                        if ';' in coords_text:
                            lat, lon = coords_text.split(';')
                        elif ',' in coords_text:
                            lat, lon = coords_text.split(',')
                        else:
                            continue
                            
                        lat = float(lat.strip())
                        lon = float(lon.strip())
                        
                        if -90 <= lat <= 90 and -180 <= lon <= 180:
                            coords.append((lat, lon))
                    except:
                        pass
                        
                # Look for geo microformat
                geo_tags = soup.find_all(class_='geo-dec')
                for tag in geo_tags:
                    try:
                        coords_text = tag.get_text()
                        if ',' in coords_text:
                            lat, lon = coords_text.split(',')
                            lat = float(lat.strip().rstrip('°'))
                            lon = float(lon.strip().rstrip('°'))
                            
                            if -90 <= lat <= 90 and -180 <= lon <= 180:
                                coords.append((lat, lon))
                    except:
                        pass
                        
        except Exception as e:
            self.status.emit(f"HTML extraction error: {str(e)}")
            
        return coords
    
    def extract_relevant_description(self, text, coords):
        """Extract description around coordinate mention"""
        # Find text around coordinates
        coord_str = f"{coords[0]:.4f}"
        
        # Find position of coordinates in text
        pos = text.find(coord_str)
        if pos == -1:
            # If exact match not found, return first 500 chars
            return text[:500].strip()
            
        # Extract surrounding context
        start = max(0, pos - 200)
        end = min(len(text), pos + 300)
        
        description = text[start:end].strip()
        
        # Clean up
        description = re.sub(r'\s+', ' ', description)
        description = re.sub(r'\[\d+\]', '', description)  # Remove references
        
        return description
    
    def follow_relevant_links(self, wiki, page, lang):
        """Follow links to related pages"""
        try:
            links = page.links
            relevant_keywords = [
                'archaeological', 'excavation', 'settlement', 'oppidum', 
                'hillfort', 'site', 'fundplatz', 'ausgrabung', 'siedlung'
            ]
            
            for link_title in links:
                if len(self.results) >= self.max_results:
                    break
                    
                # Check if link might be relevant
                if any(keyword in link_title.lower() for keyword in relevant_keywords):
                    if link_title not in self.processed_pages:
                        self.process_wikipedia_page(wiki, link_title, lang)
                        
        except:
            pass
    
    def extract_coordinates(self, text):
        """Legacy method for compatibility"""
        return self.extract_all_coordinates(text)
    
    def create_result_hash(self, result):
        """Create unique hash for duplicate detection"""
        key_parts = [
            result.get('title', ''),
            str(result.get('coordinates', '')),
            result.get('language', '')
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
    
    def search_archive_org(self):
        """Search Internet Archive"""
        # Similar to simple version but with more variations
        base_url = "https://archive.org/advancedsearch.php"
        
        queries = self.generate_search_variations()
        
        for query in queries[:5]:  # Limit archive.org searches
            try:
                params = {
                    'q': query,
                    'fl': 'identifier,title,description',
                    'rows': '20',
                    'output': 'json'
                }
                
                response = requests.get(base_url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    
                    for doc in data.get('response', {}).get('docs', []):
                        if len(self.results) >= self.max_results:
                            return
                            
                        description = doc.get('description', '')
                        if isinstance(description, list):
                            description = ' '.join(description)
                            
                        coords = self.extract_coordinates(description)
                        
                        if coords or self.is_page_relevant(description):
                            result = {
                                'title': doc.get('title', 'Unknown'),
                                'source': 'Internet Archive',
                                'url': f"https://archive.org/details/{doc.get('identifier', '')}",
                                'description': description[:500],
                                'coordinates': coords[0] if coords else None,
                                'keywords': [self.keyword1, self.keyword2],
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            if self.add_result(result):
                                self.result_found.emit(result)
                                
                time.sleep(1)  # Rate limiting
                                
            except Exception as e:
                self.status.emit(f"Archive.org error: {str(e)}")


class DeepSearchTreasureExtractor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.extractor_thread = None
        self.results = []
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Treasure Hunter Deep Search Extractor")
        self.setGeometry(100, 100, 1400, 900)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Header
        header_label = QLabel("Archaeological Find Deep Search Extractor")
        header_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header_label)
        
        # Search parameters group
        search_group = QGroupBox("Search Parameters")
        search_layout = QGridLayout()
        
        # Keywords
        search_layout.addWidget(QLabel("Primary Keyword:"), 0, 0)
        self.keyword1_input = QLineEdit()
        self.keyword1_input.setPlaceholderText("e.g., Celtic, Roman, Keltische")
        self.keyword1_input.setText("Keltische")  # Default for your search
        search_layout.addWidget(self.keyword1_input, 0, 1)
        
        search_layout.addWidget(QLabel("Secondary Keyword:"), 1, 0)
        self.keyword2_input = QLineEdit()
        self.keyword2_input.setPlaceholderText("e.g., settlement, Siedlung, coin")
        self.keyword2_input.setText("Siedlung")  # Default for your search
        search_layout.addWidget(self.keyword2_input, 1, 1)
        
        # Languages
        search_layout.addWidget(QLabel("Languages:"), 2, 0)
        lang_layout = QHBoxLayout()
        self.lang_en = QCheckBox("English")
        self.lang_en.setChecked(True)
        self.lang_de = QCheckBox("German")
        self.lang_de.setChecked(True)
        self.lang_fr = QCheckBox("French")
        lang_layout.addWidget(self.lang_en)
        lang_layout.addWidget(self.lang_de)
        lang_layout.addWidget(self.lang_fr)
        search_layout.addLayout(lang_layout, 2, 1)
        
        # Sources
        search_layout.addWidget(QLabel("Sources:"), 3, 0)
        sources_layout = QHBoxLayout()
        self.wiki_check = QCheckBox("Wikipedia (Deep)")
        self.wiki_check.setChecked(True)
        self.archive_check = QCheckBox("Archive.org")
        self.archive_check.setChecked(True)
        sources_layout.addWidget(self.wiki_check)
        sources_layout.addWidget(self.archive_check)
        search_layout.addLayout(sources_layout, 3, 1)
        
        # Max results
        search_layout.addWidget(QLabel("Max Results:"), 4, 0)
        self.max_results_spin = QSpinBox()
        self.max_results_spin.setRange(10, 500)
        self.max_results_spin.setValue(100)
        search_layout.addWidget(self.max_results_spin, 4, 1)
        
        search_group.setLayout(search_layout)
        main_layout.addWidget(search_group)
        
        # Control buttons
        control_layout = QHBoxLayout()
        self.search_button = QPushButton("Start Deep Search")
        self.search_button.clicked.connect(self.start_search)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_search)
        self.stop_button.setEnabled(False)
        self.export_button = QPushButton("Export to JSON")
        self.export_button.clicked.connect(self.export_results)
        self.clear_button = QPushButton("Clear Results")
        self.clear_button.clicked.connect(self.clear_results)
        
        control_layout.addWidget(self.search_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.export_button)
        control_layout.addWidget(self.clear_button)
        control_layout.addStretch()
        main_layout.addLayout(control_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready for deep search")
        main_layout.addWidget(self.status_label)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "Title", "Language", "Source", "Coordinates", "Description", "URL"
        ])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSortingEnabled(True)
        main_layout.addWidget(self.results_table)
        
        # Statistics
        self.stats_label = QLabel("Results: 0 | Pages processed: 0")
        main_layout.addWidget(self.stats_label)
        
    def start_search(self):
        keyword1 = self.keyword1_input.text().strip()
        keyword2 = self.keyword2_input.text().strip()
        
        if not keyword1 or not keyword2:
            QMessageBox.warning(self, "Input Error", "Please enter both keywords")
            return
            
        # Get selected languages
        languages = []
        if self.lang_en.isChecked():
            languages.append('en')
        if self.lang_de.isChecked():
            languages.append('de')
        if self.lang_fr.isChecked():
            languages.append('fr')
            
        if not languages:
            QMessageBox.warning(self, "Input Error", "Please select at least one language")
            return
            
        # Get selected sources
        sources = []
        if self.wiki_check.isChecked():
            sources.append('wikipedia')
        if self.archive_check.isChecked():
            sources.append('archive')
            
        if not sources:
            QMessageBox.warning(self, "Input Error", "Please select at least one source")
            return
            
        # Clear previous results
        self.results.clear()
        self.results_table.setRowCount(0)
        
        # Disable controls during search
        self.search_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setValue(0)
        
        # Start extraction thread
        self.extractor_thread = DeepSearchExtractor(
            keyword1, keyword2, sources, self.max_results_spin.value(), languages
        )
        self.extractor_thread.progress.connect(self.update_progress)
        self.extractor_thread.status.connect(self.update_status)
        self.extractor_thread.result_found.connect(self.add_result)
        self.extractor_thread.finished_extraction.connect(self.search_finished)
        self.extractor_thread.error.connect(self.handle_error)
        self.extractor_thread.start()
        
        self.status_label.setText(f"Starting deep search for '{keyword1} {keyword2}'...")
        
    def stop_search(self):
        if self.extractor_thread and self.extractor_thread.isRunning():
            self.extractor_thread.terminate()
            self.search_finished([])
            self.status_label.setText("Search stopped by user")
            
    def update_progress(self, value):
        self.progress_bar.setValue(value)
        
    def update_status(self, message):
        self.status_label.setText(message)
        # Update stats
        if self.extractor_thread:
            pages = len(self.extractor_thread.processed_pages)
            self.stats_label.setText(f"Results: {len(self.results)} | Pages processed: {pages}")
        
    def add_result(self, result):
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        # Add data to table
        self.results_table.setItem(row, 0, QTableWidgetItem(result.get('title', '')))
        self.results_table.setItem(row, 1, QTableWidgetItem(result.get('language', '').upper()))
        self.results_table.setItem(row, 2, QTableWidgetItem(result.get('source', '')))
        
        coords = result.get('coordinates')
        coord_text = f"{coords[0]:.6f}, {coords[1]:.6f}" if coords else "No coordinates"
        coord_item = QTableWidgetItem(coord_text)
        if coords:
            coord_item.setBackground(Qt.GlobalColor.lightGray)
        self.results_table.setItem(row, 3, coord_item)
        
        desc = result.get('description', '')
        self.results_table.setItem(row, 4, QTableWidgetItem(desc[:150] + '...' if len(desc) > 150 else desc))
        self.results_table.setItem(row, 5, QTableWidgetItem(result.get('url', '')))
        
        self.results.append(result)
        self.update_stats()
        
    def search_finished(self, results):
        self.search_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setValue(100)
        
        # Show summary
        with_coords = sum(1 for r in self.results if r.get('coordinates'))
        self.status_label.setText(
            f"Search completed. Found {len(self.results)} results ({with_coords} with coordinates)"
        )
        
    def handle_error(self, error_message):
        QMessageBox.critical(self, "Error", error_message)
        self.search_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
    def export_results(self):
        if not self.results:
            QMessageBox.information(self, "No Data", "No results to export")
            return
            
        # Generate filename
        keyword1 = self.keyword1_input.text().strip()
        keyword2 = self.keyword2_input.text().strip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"{keyword1}_{keyword2}_deep_search_{timestamp}.json"
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Results", default_filename, "JSON Files (*.json)"
        )
        
        if filename:
            try:
                # Prepare data for export
                export_data = {
                    'metadata': {
                        'search_keywords': [keyword1, keyword2],
                        'languages': [],
                        'timestamp': datetime.now().isoformat(),
                        'total_results': len(self.results),
                        'results_with_coordinates': sum(1 for r in self.results if r.get('coordinates')),
                        'pages_processed': len(self.extractor_thread.processed_pages) if self.extractor_thread else 0
                    },
                    'results': self.results
                }
                
                # Add selected languages
                if self.lang_en.isChecked():
                    export_data['metadata']['languages'].append('en')
                if self.lang_de.isChecked():
                    export_data['metadata']['languages'].append('de')
                if self.lang_fr.isChecked():
                    export_data['metadata']['languages'].append('fr')
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                    
                QMessageBox.information(self, "Export Successful", 
                    f"Results saved to {filename}\n"
                    f"Total results: {len(self.results)}\n"
                    f"With coordinates: {export_data['metadata']['results_with_coordinates']}")
                
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export: {str(e)}")
                
    def clear_results(self):
        self.results.clear()
        self.results_table.setRowCount(0)
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready for deep search")
        self.update_stats()
        
    def update_stats(self):
        total = len(self.results)
        with_coords = sum(1 for r in self.results if r.get('coordinates'))
        pages = len(self.extractor_thread.processed_pages) if self.extractor_thread else 0
        self.stats_label.setText(f"Results: {total} ({with_coords} with coords) | Pages processed: {pages}")
        

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = DeepSearchTreasureExtractor()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()