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

class DataExtractorThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    result_found = pyqtSignal(dict)
    finished_extraction = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, keyword1, keyword2, sources, max_results=100):
        super().__init__()
        self.keyword1 = keyword1
        self.keyword2 = keyword2
        self.sources = sources
        self.max_results = max_results
        self.results = []
        self.seen_hashes = set()
        
        # Wikipedia API setup
        self.wiki = wikipediaapi.Wikipedia(
            language='en',
            extract_format=wikipediaapi.ExtractFormat.WIKI,
            user_agent='TreasureHunter/1.0'
        )
        
    def run(self):
        try:
            total_tasks = len(self.sources)
            completed_tasks = 0
            
            if 'wikipedia' in self.sources:
                self.status.emit("Searching Wikipedia...")
                self.search_wikipedia()
                completed_tasks += 1
                self.progress.emit(int((completed_tasks / total_tasks) * 100))
                
            if 'archive' in self.sources:
                self.status.emit("Searching Internet Archive...")
                self.search_archive_org()
                completed_tasks += 1
                self.progress.emit(int((completed_tasks / total_tasks) * 100))
                
            self.finished_extraction.emit(self.results)
            
        except Exception as e:
            self.error.emit(f"Extraction error: {str(e)}")
    
    def extract_coordinates(self, text: str) -> List[Tuple[float, float]]:
        """Extract coordinates from text using various patterns"""
        coords = []
        
        # Pattern 1: Decimal degrees (48.1234, 11.5678)
        pattern1 = r'(-?\d{1,3}\.\d+)[,\s]+(-?\d{1,3}\.\d+)'
        
        # Try decimal degrees
        for match in re.finditer(pattern1, text):
            try:
                lat = float(match.group(1))
                lon = float(match.group(2))
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    coords.append((lat, lon))
            except:
                pass
                
        return coords
    
    def create_result_hash(self, result: dict) -> str:
        """Create a hash to identify duplicate results"""
        key_parts = [
            result.get('title', ''),
            result.get('description', '')[:100],
            str(result.get('coordinates', ''))
        ]
        return hashlib.md5(''.join(key_parts).encode()).hexdigest()
    
    def add_result(self, result: dict):
        """Add result if not duplicate"""
        result_hash = self.create_result_hash(result)
        if result_hash not in self.seen_hashes:
            self.seen_hashes.add(result_hash)
            self.results.append(result)
            self.result_found.emit(result)
            
            if len(self.results) >= self.max_results:
                return False
        return True
    
    def search_wikipedia(self):
        """Search Wikipedia for archaeological finds"""
        queries = [
            f"{self.keyword1} {self.keyword2} found",
            f"{self.keyword1} {self.keyword2} discovered",
            f"ancient {self.keyword1} {self.keyword2}"
        ]
        
        for query in queries:
            try:
                search_results = self.wiki.search(query, results=10)
                
                for title in search_results:
                    if len(self.results) >= self.max_results:
                        return
                        
                    page = self.wiki.page(title)
                    if page.exists():
                        text = page.text
                        
                        if self.keyword1.lower() in text.lower() and self.keyword2.lower() in text.lower():
                            coordinates = self.extract_coordinates(text)
                            
                            if coordinates:
                                result = {
                                    'title': title,
                                    'source': 'Wikipedia',
                                    'url': page.fullurl,
                                    'description': page.summary[:500] if hasattr(page, 'summary') else text[:500],
                                    'coordinates': coordinates[0] if coordinates else None,
                                    'keywords': [self.keyword1, self.keyword2],
                                    'timestamp': datetime.now().isoformat()
                                }
                                
                                if not self.add_result(result):
                                    return
                                    
            except Exception as e:
                self.status.emit(f"Wikipedia search error: {str(e)}")
    
    def search_archive_org(self):
        """Search Internet Archive for historical documents"""
        base_url = "https://archive.org/advancedsearch.php"
        
        query = f"{self.keyword1} {self.keyword2}"
        
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
                        
                    coordinates = self.extract_coordinates(description)
                    
                    if self.keyword1.lower() in description.lower() and self.keyword2.lower() in description.lower():
                        result = {
                            'title': doc.get('title', 'Unknown'),
                            'source': 'Internet Archive',
                            'url': f"https://archive.org/details/{doc.get('identifier', '')}",
                            'description': description[:500],
                            'coordinates': coordinates[0] if coordinates else None,
                            'keywords': [self.keyword1, self.keyword2],
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        if not self.add_result(result):
                            return
                            
        except Exception as e:
            self.status.emit(f"Archive.org search error: {str(e)}")


class TreasureDataExtractor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.extractor_thread = None
        self.results = []
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Treasure Hunter Data Extractor")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Header
        header_label = QLabel("Archaeological Find Data Extractor")
        header_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header_label)
        
        # Search parameters group
        search_group = QGroupBox("Search Parameters")
        search_layout = QGridLayout()
        
        # Keywords
        search_layout.addWidget(QLabel("Primary Keyword:"), 0, 0)
        self.keyword1_input = QLineEdit()
        self.keyword1_input.setPlaceholderText("e.g., Celtic, Roman, Viking")
        search_layout.addWidget(self.keyword1_input, 0, 1)
        
        search_layout.addWidget(QLabel("Secondary Keyword:"), 1, 0)
        self.keyword2_input = QLineEdit()
        self.keyword2_input.setPlaceholderText("e.g., coin, sword, jewelry")
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
        
        # Max results
        search_layout.addWidget(QLabel("Max Results:"), 3, 0)
        self.max_results_spin = QSpinBox()
        self.max_results_spin.setRange(10, 100)
        self.max_results_spin.setValue(50)
        search_layout.addWidget(self.max_results_spin, 3, 1)
        
        search_group.setLayout(search_layout)
        main_layout.addWidget(search_group)
        
        # Control buttons
        control_layout = QHBoxLayout()
        self.search_button = QPushButton("Start Search")
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
        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            "Title", "Source", "Coordinates", "Description", "URL"
        ])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setAlternatingRowColors(True)
        main_layout.addWidget(self.results_table)
        
        # Statistics
        self.stats_label = QLabel("Results: 0")
        main_layout.addWidget(self.stats_label)
        
    def start_search(self):
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
            
        # Disable controls during search
        self.search_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setValue(0)
        
        # Start extraction thread
        self.extractor_thread = DataExtractorThread(
            keyword1, keyword2, sources, self.max_results_spin.value()
        )
        self.extractor_thread.progress.connect(self.update_progress)
        self.extractor_thread.status.connect(self.update_status)
        self.extractor_thread.result_found.connect(self.add_result)
        self.extractor_thread.finished_extraction.connect(self.search_finished)
        self.extractor_thread.error.connect(self.handle_error)
        self.extractor_thread.start()
        
    def stop_search(self):
        if self.extractor_thread and self.extractor_thread.isRunning():
            self.extractor_thread.terminate()
            self.search_finished([])
            
    def update_progress(self, value):
        self.progress_bar.setValue(value)
        
    def update_status(self, message):
        self.status_label.setText(message)
        
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
        self.update_stats()
        
    def search_finished(self, results):
        self.search_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setValue(100)
        self.status_label.setText(f"Search completed. Found {len(self.results)} results.")
        
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
        default_filename = f"{keyword1}_{keyword2}_finds_{timestamp}.json"
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Results", default_filename, "JSON Files (*.json)"
        )
        
        if filename:
            try:
                # Prepare data for export
                export_data = {
                    'metadata': {
                        'search_keywords': [keyword1, keyword2],
                        'timestamp': datetime.now().isoformat(),
                        'total_results': len(self.results)
                    },
                    'results': self.results
                }
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                    
                QMessageBox.information(self, "Export Successful", f"Results saved to {filename}")
                
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export: {str(e)}")
                
    def clear_results(self):
        self.results.clear()
        self.results_table.setRowCount(0)
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready")
        self.update_stats()
        
    def update_stats(self):
        total = len(self.results)
        self.stats_label.setText(f"Results: {total}")
        

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = TreasureDataExtractor()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()