import sys
import json
import re
import os
import hashlib
from datetime import datetime
from typing import List, Dict, Tuple, Optional
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
import traceback

class DebugDataExtractorThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    result_found = pyqtSignal(dict)
    finished_extraction = pyqtSignal(list)
    error = pyqtSignal(str)
    debug_log = pyqtSignal(str)  # New debug signal
    
    def __init__(self, keyword1, keyword2, sources, max_results=100):
        super().__init__()
        self.keyword1 = keyword1
        self.keyword2 = keyword2
        self.sources = sources
        self.max_results = max_results
        self.results = []
        self.seen_hashes = set()
        
        # Wikipedia API setup with multiple languages
        self.wikis = {
            'en': wikipediaapi.Wikipedia(
                language='en',
                extract_format=wikipediaapi.ExtractFormat.WIKI,
                user_agent='TreasureHunter/1.0 (https://example.com/contact)'
            ),
            'de': wikipediaapi.Wikipedia(
                language='de',
                extract_format=wikipediaapi.ExtractFormat.WIKI,
                user_agent='TreasureHunter/1.0 (https://example.com/contact)'
            )
        }
        
    def log_debug(self, message):
        """Send debug message to GUI"""
        self.debug_log.emit(f"[DEBUG] {message}")
        print(f"[DEBUG] {message}")  # Also print to console
        
    def run(self):
        try:
            self.log_debug(f"Starting search for '{self.keyword1}' and '{self.keyword2}'")
            self.log_debug(f"Selected sources: {self.sources}")
            
            if 'wikipedia' in self.sources:
                self.status.emit("Searching Wikipedia...")
                self.search_wikipedia_debug()
                
            if 'archive' in self.sources:
                self.status.emit("Searching Internet Archive...")
                self.search_archive_debug()
                
            self.log_debug(f"Search completed. Total results: {len(self.results)}")
            self.finished_extraction.emit(self.results)
            
        except Exception as e:
            self.log_debug(f"Fatal error: {str(e)}")
            self.log_debug(f"Traceback: {traceback.format_exc()}")
            self.error.emit(f"Extraction error: {str(e)}")
    
    def search_wikipedia_debug(self):
        """Search Wikipedia with detailed debugging"""
        # Test both languages
        for lang, wiki in self.wikis.items():
            self.log_debug(f"\n=== Searching Wikipedia {lang.upper()} ===")
            
            # Generate search queries
            queries = [
                f"{self.keyword1} {self.keyword2}",
                f"{self.keyword2} {self.keyword1}",
            ]
            
            # Add German-specific queries
            if lang == 'de' and 'kelt' in self.keyword1.lower():
                queries.extend([
                    "keltische Siedlung",
                    "Keltensiedlung",
                    "keltisches Oppidum",
                    "Liste keltischer Oppida",
                    "Keltenstadt"
                ])
                
            self.log_debug(f"Search queries for {lang}: {queries}")
            
            for query in queries:
                try:
                    self.log_debug(f"\nSearching for: '{query}'")
                    
                    # Search Wikipedia
                    search_results = wiki.search(query, results=20)
                    self.log_debug(f"Found {len(search_results)} search results")
                    
                    if search_results:
                        self.log_debug(f"First 5 results: {search_results[:5]}")
                    
                    for i, title in enumerate(search_results[:10]):  # Process first 10
                        self.log_debug(f"\nProcessing result {i+1}: '{title}'")
                        
                        try:
                            page = wiki.page(title)
                            
                            if not page.exists():
                                self.log_debug(f"  Page does not exist")
                                continue
                                
                            self.log_debug(f"  Page exists, URL: {page.fullurl}")
                            
                            # Get page text
                            text = page.text[:5000]  # First 5000 chars
                            self.log_debug(f"  Text length: {len(page.text)} chars")
                            
                            # Check if keywords present
                            kw1_present = self.keyword1.lower() in text.lower()
                            kw2_present = self.keyword2.lower() in text.lower()
                            self.log_debug(f"  Keyword1 present: {kw1_present}, Keyword2 present: {kw2_present}")
                            
                            # Look for coordinates
                            coords = self.extract_coordinates_debug(text)
                            
                            if coords:
                                self.log_debug(f"  ✓ Found {len(coords)} coordinates!")
                                
                                result = {
                                    'title': title,
                                    'source': f'Wikipedia ({lang.upper()})',
                                    'url': page.fullurl,
                                    'description': page.summary[:500] if hasattr(page, 'summary') else text[:500],
                                    'coordinates': coords[0],
                                    'keywords': [self.keyword1, self.keyword2],
                                    'timestamp': datetime.now().isoformat()
                                }
                                
                                self.add_result(result)
                                self.result_found.emit(result)
                                self.log_debug(f"  ✓ Result added: {title} at {coords[0]}")
                            else:
                                self.log_debug(f"  No coordinates found")
                                
                        except Exception as e:
                            self.log_debug(f"  Error processing page: {str(e)}")
                            
                except Exception as e:
                    self.log_debug(f"Error in search: {str(e)}")
                    self.log_debug(f"Traceback: {traceback.format_exc()}")
        
        # Also try direct page access for known pages
        self.log_debug("\n=== Trying known Celtic settlement pages ===")
        known_pages = {
            'de': [
                'Heuneburg',
                'Manching',
                'Glauberg',
                'Liste_keltischer_Oppida',
                'Keltische_Siedlung',
                'Heidengraben'
            ],
            'en': [
                'List_of_Celtic_oppida',
                'Heuneburg',
                'Manching_oppidum',
                'Celtic_settlement'
            ]
        }
        
        for lang, pages in known_pages.items():
            wiki = self.wikis.get(lang)
            if wiki:
                for page_title in pages:
                    self.log_debug(f"\nTrying direct access: {page_title} ({lang})")
                    try:
                        page = wiki.page(page_title)
                        if page.exists():
                            self.log_debug(f"  ✓ Page exists!")
                            self.process_known_page(page, lang)
                        else:
                            self.log_debug(f"  Page not found")
                    except Exception as e:
                        self.log_debug(f"  Error: {str(e)}")
    
    def extract_coordinates_debug(self, text):
        """Extract coordinates with detailed debugging"""
        coords = []
        self.log_debug(f"  Searching for coordinates in text ({len(text)} chars)")
        
        # Pattern 1: Decimal degrees
        pattern1 = r'(-?\d{1,3}\.\d{2,10})[,\s]+(-?\d{1,3}\.\d{2,10})'
        matches1 = list(re.finditer(pattern1, text))
        self.log_debug(f"    Decimal pattern matches: {len(matches1)}")
        
        for match in matches1:
            try:
                lat = float(match.group(1))
                lon = float(match.group(2))
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    coords.append((lat, lon))
                    self.log_debug(f"    ✓ Valid coordinates: {lat}, {lon}")
                else:
                    self.log_debug(f"    Invalid range: {lat}, {lon}")
            except Exception as e:
                self.log_debug(f"    Parse error: {e}")
        
        # Pattern 2: DMS format
        pattern2 = r'(\d{1,3})°\s*(\d{1,2})[\′\']\s*(?:(\d{1,2}(?:\.\d+)?)[\″"]?)?\s*([NS])[,\s]+(\d{1,3})°\s*(\d{1,2})[\′\']\s*(?:(\d{1,2}(?:\.\d+)?)[\″"]?)?\s*([EW])'
        matches2 = list(re.finditer(pattern2, text))
        self.log_debug(f"    DMS pattern matches: {len(matches2)}")
        
        # Pattern 3: Coord template (Wikipedia specific)
        pattern3 = r'\{\{[Cc]oord\|([^}]+)\}\}'
        matches3 = list(re.finditer(pattern3, text))
        self.log_debug(f"    Coord template matches: {len(matches3)}")
        
        for match in matches3:
            coord_text = match.group(1)
            self.log_debug(f"    Parsing coord template: {coord_text}")
            parts = coord_text.split('|')
            if len(parts) >= 2:
                try:
                    lat = float(parts[0])
                    lon = float(parts[1])
                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                        coords.append((lat, lon))
                        self.log_debug(f"    ✓ Valid coordinates from template: {lat}, {lon}")
                except:
                    self.log_debug(f"    Failed to parse template")
        
        # Pattern 4: Look for "coordinates" in text
        if "coordinates:" in text.lower() or "koordinaten:" in text.lower():
            self.log_debug(f"    Found 'coordinates' keyword in text")
            
        return coords
    
    def process_known_page(self, page, lang):
        """Process a known page that should contain settlements"""
        try:
            text = page.text
            self.log_debug(f"  Processing page: {page.title}")
            
            # For list pages, look for table entries
            if "Liste" in page.title or "List" in page.title:
                self.log_debug(f"  This appears to be a list page")
                # In a real implementation, we would parse the HTML here
                # For now, just extract any coordinates
                
            coords = self.extract_coordinates_debug(text[:10000])  # Check first 10k chars
            
            if coords:
                for coord in coords[:5]:  # Max 5 per page to avoid duplicates
                    result = {
                        'title': page.title,
                        'source': f'Wikipedia ({lang.upper()}) - Direct',
                        'url': page.fullurl,
                        'description': f"From page: {page.title}",
                        'coordinates': coord,
                        'keywords': [self.keyword1, self.keyword2],
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    if self.add_result(result):
                        self.result_found.emit(result)
                        self.log_debug(f"  ✓ Added result from {page.title}")
                        
        except Exception as e:
            self.log_debug(f"  Error processing known page: {str(e)}")
    
    def search_archive_debug(self):
        """Search Internet Archive with debugging"""
        self.log_debug("\n=== Searching Internet Archive ===")
        base_url = "https://archive.org/advancedsearch.php"
        
        query = f"{self.keyword1} {self.keyword2}"
        self.log_debug(f"Archive.org query: '{query}'")
        
        try:
            params = {
                'q': query,
                'fl': 'identifier,title,description',
                'rows': '10',
                'output': 'json'
            }
            
            self.log_debug(f"Request params: {params}")
            response = requests.get(base_url, params=params, timeout=10)
            self.log_debug(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                num_found = data.get('response', {}).get('numFound', 0)
                self.log_debug(f"Total results found: {num_found}")
                
                docs = data.get('response', {}).get('docs', [])
                self.log_debug(f"Results returned: {len(docs)}")
                
                for i, doc in enumerate(docs[:5]):
                    self.log_debug(f"\nProcessing archive result {i+1}: {doc.get('title', 'Unknown')}")
                    
                    description = doc.get('description', '')
                    if isinstance(description, list):
                        description = ' '.join(description)
                    
                    self.log_debug(f"  Description length: {len(description)}")
                    
                    coords = self.extract_coordinates_debug(description)
                    
                    if coords:
                        result = {
                            'title': doc.get('title', 'Unknown'),
                            'source': 'Internet Archive',
                            'url': f"https://archive.org/details/{doc.get('identifier', '')}",
                            'description': description[:500],
                            'coordinates': coords[0],
                            'keywords': [self.keyword1, self.keyword2],
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        if self.add_result(result):
                            self.result_found.emit(result)
                            self.log_debug(f"  ✓ Added archive result with coordinates")
                            
        except Exception as e:
            self.log_debug(f"Archive.org error: {str(e)}")
            self.log_debug(f"Traceback: {traceback.format_exc()}")
    
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
        else:
            self.log_debug(f"  Duplicate result skipped: {result.get('title')}")
        return False


class DebugTreasureExtractor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.extractor_thread = None
        self.results = []
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Treasure Hunter Data Extractor - DEBUG MODE")
        self.setGeometry(100, 100, 1400, 900)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Header
        header_label = QLabel("Archaeological Find Data Extractor - DEBUG MODE")
        header_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_label.setStyleSheet("color: red;")
        main_layout.addWidget(header_label)
        
        # Search parameters group
        search_group = QGroupBox("Search Parameters")
        search_layout = QGridLayout()
        
        # Keywords
        search_layout.addWidget(QLabel("Primary Keyword:"), 0, 0)
        self.keyword1_input = QLineEdit()
        self.keyword1_input.setPlaceholderText("e.g., Celtic, Roman, Keltische")
        self.keyword1_input.setText("Keltische")  # Default
        search_layout.addWidget(self.keyword1_input, 0, 1)
        
        search_layout.addWidget(QLabel("Secondary Keyword:"), 1, 0)
        self.keyword2_input = QLineEdit()
        self.keyword2_input.setPlaceholderText("e.g., settlement, Siedlung, coin")
        self.keyword2_input.setText("Siedlung")  # Default
        search_layout.addWidget(self.keyword2_input, 1, 1)
        
        # Sources
        search_layout.addWidget(QLabel("Sources:"), 2, 0)
        sources_layout = QHBoxLayout()
        self.wiki_check = QCheckBox("Wikipedia")
        self.wiki_check.setChecked(True)
        self.archive_check = QCheckBox("Archive.org")
        self.archive_check.setChecked(True)
        sources_layout.addWidget(self.wiki_check)
        sources_layout.addWidget(self.archive_check)
        search_layout.addLayout(sources_layout, 2, 1)
        
        search_group.setLayout(search_layout)
        main_layout.addWidget(search_group)
        
        # Control buttons
        control_layout = QHBoxLayout()
        self.search_button = QPushButton("Start Search (Debug Mode)")
        self.search_button.clicked.connect(self.start_search)
        self.search_button.setStyleSheet("background-color: #ffcccc;")
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
        self.status_label = QLabel("Ready - Debug Mode Active")
        main_layout.addWidget(self.status_label)
        
        # Tab widget for results and debug log
        self.tabs = QTabWidget()
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            "Title", "Source", "Coordinates", "Description", "URL"
        ])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.tabs.addTab(self.results_table, "Results")
        
        # Debug log
        self.debug_log = QTextEdit()
        self.debug_log.setReadOnly(True)
        self.debug_log.setFont(QFont("Consolas", 9))
        self.tabs.addTab(self.debug_log, "Debug Log")
        
        main_layout.addWidget(self.tabs)
        
        # Switch to debug tab
        self.tabs.setCurrentIndex(1)
        
    def start_search(self):
        # Clear previous results
        self.results.clear()
        self.results_table.setRowCount(0)
        self.debug_log.clear()
        
        keyword1 = self.keyword1_input.text().strip()
        keyword2 = self.keyword2_input.text().strip()
        
        if not keyword1 or not keyword2:
            QMessageBox.warning(self, "Input Error", "Please enter both keywords")
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
            
        self.search_button.setEnabled(False)
        self.progress_bar.setValue(0)
        
        # Add initial debug info
        self.debug_log.append("=== STARTING DEBUG SEARCH ===")
        self.debug_log.append(f"Primary keyword: '{keyword1}'")
        self.debug_log.append(f"Secondary keyword: '{keyword2}'")
        self.debug_log.append(f"Selected sources: {sources}")
        self.debug_log.append(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.debug_log.append("=" * 50)
        
        # Start extraction thread
        self.extractor_thread = DebugDataExtractorThread(
            keyword1, keyword2, sources, max_results=50
        )
        
        # Connect signals
        self.extractor_thread.progress.connect(self.update_progress)
        self.extractor_thread.status.connect(self.update_status)
        self.extractor_thread.result_found.connect(self.add_result)
        self.extractor_thread.finished_extraction.connect(self.search_finished)
        self.extractor_thread.error.connect(self.handle_error)
        self.extractor_thread.debug_log.connect(self.add_debug_log)
        
        self.extractor_thread.start()
        
    def add_debug_log(self, message):
        """Add message to debug log"""
        self.debug_log.append(message)
        # Auto-scroll to bottom
        cursor = self.debug_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.debug_log.setTextCursor(cursor)
        
    def update_progress(self, value):
        self.progress_bar.setValue(value)
        
    def update_status(self, message):
        self.status_label.setText(message)
        self.add_debug_log(f"[STATUS] {message}")
        
    def add_result(self, result):
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        # Add data to table
        self.results_table.setItem(row, 0, QTableWidgetItem(result.get('title', '')))
        self.results_table.setItem(row, 1, QTableWidgetItem(result.get('source', '')))
        
        coords = result.get('coordinates')
        coord_text = f"{coords[0]:.6f}, {coords[1]:.6f}" if coords else "No coordinates"
        self.results_table.setItem(row, 2, QTableWidgetItem(coord_text))
        
        desc = result.get('description', '')
        self.results_table.setItem(row, 3, QTableWidgetItem(desc[:100] + '...' if len(desc) > 100 else desc))
        self.results_table.setItem(row, 4, QTableWidgetItem(result.get('url', '')))
        
        self.results.append(result)
        
    def search_finished(self, results):
        self.search_button.setEnabled(True)
        self.progress_bar.setValue(100)
        self.status_label.setText(f"Search completed. Found {len(results)} results.")
        self.add_debug_log(f"\n=== SEARCH COMPLETED ===")
        self.add_debug_log(f"Total results found: {len(results)}")
        
    def handle_error(self, error_message):
        QMessageBox.critical(self, "Error", error_message)
        self.search_button.setEnabled(True)
        self.add_debug_log(f"\n[ERROR] {error_message}")
        
    def export_results(self):
        if not self.results:
            QMessageBox.information(self, "No Data", "No results to export")
            return
            
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Results", "debug_results.json", "JSON Files (*.json)"
        )
        
        if filename:
            export_data = {
                'metadata': {
                    'search_keywords': [
                        self.keyword1_input.text(),
                        self.keyword2_input.text()
                    ],
                    'timestamp': datetime.now().isoformat(),
                    'total_results': len(self.results)
                },
                'results': self.results
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
                
            # Also save debug log
            debug_filename = filename.replace('.json', '_debug.txt')
            with open(debug_filename, 'w', encoding='utf-8') as f:
                f.write(self.debug_log.toPlainText())
                
            QMessageBox.information(self, "Export Complete", 
                f"Results saved to: {filename}\nDebug log saved to: {debug_filename}")
    
    def clear_all(self):
        self.results.clear()
        self.results_table.setRowCount(0)
        self.debug_log.clear()
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready - Debug Mode Active")


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = DebugTreasureExtractor()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()