import sys
import re
import json
import os
import uuid
import webbrowser
import http.server
import socketserver
import threading
import requests

# This must be set before the QApplication is instantiated.
os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "8888"

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QMessageBox, QStatusBar, QSlider,
    QTextEdit, QComboBox, QListWidget, QListWidgetItem, QDialog,
    QDialogButtonBox, QFormLayout, QCheckBox, QFrame, QMenu
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QFile, QTextStream, Qt, pyqtSignal, QThread

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

# Local Imports
from map_widget import MapWidget
from assets import border_fetcher
from assets.countries.europe import germany as germany_assets
from assets.countries.europe import austria as austria_assets
from assets.countries.europe import switzerland as switzerland_assets
from assets.countries.europe import italy as italy_assets

class UrlFetcherThread(QThread):
    """ A QThread to fetch data from a URL in the background without freezing the UI. """
    data_ready = pyqtSignal(str, object) # request_id, data
    error = pyqtSignal(str, str) # request_id, error_message

    def __init__(self, request_id, url):
        super().__init__()
        self.request_id = request_id
        self.url = url
        self.is_running = True

    def run(self):
        try:
            if not self.is_running: return
            response = requests.get(self.url, timeout=10)
            if not self.is_running: return
            response.raise_for_status()
            self.data_ready.emit(self.request_id, response.json())
        except requests.exceptions.RequestException as e:
            if self.is_running: self.error.emit(self.request_id, str(e))
        except json.JSONDecodeError:
            if self.is_running: self.error.emit(self.request_id, "Invalid JSON response")

    def stop(self):
        self.is_running = False


class BorderFetcherThread(QThread):
    """
    A QThread to fetch border data in the background to avoid freezing the UI.
    """
    data_ready = pyqtSignal(int, str, dict)
    error = pyqtSignal(str)
    
    def __init__(self, admin_level, country_name=None):
        super().__init__()
        self.admin_level = admin_level
        self.country_name = country_name
        self.is_running = True

    def run(self):
        try:
            if not self.is_running: return
            data = border_fetcher.get_admin_borders(self.admin_level, self.country_name)
            if self.is_running: self.data_ready.emit(self.admin_level, self.country_name, data)
        except Exception as e:
            if self.is_running: self.error.emit(str(e))
            
    def stop(self):
        self.is_running = False


class AddMarkerDialog(QDialog):
    """
    Dialog for adding a new marker to the map.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Neuen Marker hinzufügen")
        self.setModal(True)
        self.layout = QFormLayout(self)
        self.comment_input = QLineEdit()
        self.comment_input.setPlaceholderText("z.B. Keltenschanze, Römische Münze...")
        self.layout.addRow("Kommentar:", self.comment_input)
        self.icon_selector = QComboBox()
        self.icon_selector.addItems(["Start", "Punkt", "Münze", "Ziel", "Viereckschanze", "Kastell", "Siedlung", "Coin", "Treasure", "Modern"])
        self.layout.addRow("Icon:", self.icon_selector)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addRow(self.button_box)

    def get_data(self):
        return {
            "comment": self.comment_input.text() or "Unbenannter Marker",
            "icon": self.icon_selector.currentText().lower()
        }

class TreasureHunterApp(QMainWindow):
    """
    Main application window for the Treasure Hunter app.
    """
    request_add_marker_dialog = pyqtSignal(float, float)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Treasure Hunter")
        self.setGeometry(100, 100, 1300, 850)
        self.geolocator = Nominatim(user_agent="treasure_hunter_app_v40")
        self.markers = {}
        self.markers_file = "markers.json"
        self.poi_data = {}
        self.current_location = None
        self.border_fetcher_thread = None
        self.url_fetcher_threads = {}
        
        self.init_ui()
        self.setStatusBar(QStatusBar(self))
        self.request_add_marker_dialog.connect(self.show_add_marker_dialog)
        self.add_log("Anwendung gestartet.")
        self.add_log("Entwicklerkonsole aktiv auf http://localhost:8888")
        self.load_markers()
        self.load_all_poi_data()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.init_menu()

        control_panel = QWidget()
        control_panel.setFixedWidth(350)
        control_panel.setObjectName("controlPanel")
        control_layout = QVBoxLayout(control_panel)
        control_layout.setContentsMargins(15, 15, 15, 10)
        control_layout.setSpacing(8)

        # UI sections...
        navigation_label = QLabel("Navigation & Suche")
        navigation_label.setObjectName("titleLabel")
        control_layout.addWidget(navigation_label)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Ort suchen oder 'lat, lon'...")
        self.search_input.returnPressed.connect(self.search_location)
        control_layout.addWidget(self.search_input)
        search_button = QPushButton("Ort suchen")
        search_button.clicked.connect(self.search_location)
        control_layout.addWidget(search_button)
        my_location_button = QPushButton("Eigenen Standort ermitteln")
        my_location_button.setObjectName("locationButton")
        my_location_button.clicked.connect(self.determine_current_location)
        control_layout.addWidget(my_location_button)
        self.current_location_label = QLabel("Start: Standort unbekannt")
        control_layout.addWidget(self.current_location_label)
        ziel_label = QLabel("Ziel (aus Fundorten):")
        control_layout.addWidget(ziel_label)
        self.destination_selector = QComboBox()
        self.destination_selector.setToolTip("Wählen Sie einen gespeicherten Fundort als Ziel")
        control_layout.addWidget(self.destination_selector)
        navigate_button = QPushButton("Route starten")
        navigate_button.clicked.connect(self.navigate_to_destination)
        control_layout.addWidget(navigate_button)
        control_layout.addWidget(self.create_separator())
        layer_label = QLabel("Karten-Layer")
        layer_label.setObjectName("titleLabel")
        control_layout.addWidget(layer_label)
        
        overlay_sublabel = QLabel("Hintergrund-Überlagerung")
        overlay_sublabel.setObjectName("subTitleLabel")
        control_layout.addWidget(overlay_sublabel)
        self.terrain_checkbox = QCheckBox("Gelände-Überlagerung (Auto)")
        self.terrain_checkbox.stateChanged.connect(self.toggle_terrain_layer)
        control_layout.addWidget(self.terrain_checkbox)
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self.set_terrain_opacity)
        control_layout.addWidget(self.opacity_slider)
        
        control_layout.addWidget(self.create_separator())
        marker_label = QLabel("Meine Fundorte")
        marker_label.setObjectName("titleLabel")
        control_layout.addWidget(marker_label)
        self.marker_list_widget = QListWidget()
        self.marker_list_widget.setObjectName("markerList")
        self.marker_list_widget.itemDoubleClicked.connect(self.center_on_marker)
        control_layout.addWidget(self.marker_list_widget)
        delete_marker_button = QPushButton("Ausgewählten Marker löschen")
        delete_marker_button.clicked.connect(self.delete_selected_marker)
        control_layout.addWidget(delete_marker_button)
        control_layout.addStretch()
        log_label = QLabel("Log")
        log_label.setObjectName("subTitleLabel")
        control_layout.addWidget(log_label)
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setObjectName("logConsole")
        self.log_console.setFixedHeight(120)
        control_layout.addWidget(self.log_console)

        terrain_data = {
            'germany': {
                'layers': germany_assets.terrain_layers,
                'bounds': germany_assets.bounds,
                'logic': germany_assets.layer_logic
            },
            'austria': {
                'layers': austria_assets.terrain_layers,
                'bounds': austria_assets.bounds,
                'logic': austria_assets.layer_logic
            },
            'switzerland': {
                'layers': switzerland_assets.terrain_layers,
                'bounds': switzerland_assets.bounds,
                'logic': switzerland_assets.layer_logic
            },
            'italy': {
                'layers': italy_assets.terrain_layers,
                'bounds': italy_assets.bounds,
                'logic': italy_assets.layer_logic
            }
        }
        self.map_widget = MapWidget(terrain_data)
        
        self.map_widget.bridge.log_requested.connect(self.add_log)
        self.map_widget.bridge.map_ready.connect(self.on_map_ready)
        self.map_widget.bridge.map_right_clicked.connect(self.handle_map_right_click)
        self.map_widget.bridge.fetch_url_requested.connect(self.fetch_url_from_js)
        
        main_layout.addWidget(control_panel)
        main_layout.addWidget(self.map_widget)

    def init_menu(self):
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet("""
            QMenuBar {
                background-color: #2c3e50;
                color: white;
                border-bottom: 1px solid #34495e;
            }
            QMenuBar::item:selected {
                background-color: #34495e;
            }
            QMenu {
                background-color: #2c3e50;
                color: white;
                border: 1px solid #34495e;
            }
            QMenu::item:selected {
                background-color: #34495e;
            }
        """)
        self.poi_menu = menu_bar.addMenu("&POI Layers")
        self.poi_menu.aboutToShow.connect(self.handle_menu_show)
        self.poi_menu.aboutToHide.connect(self.handle_menu_hide)

        border_menu = menu_bar.addMenu("&Administrative Borders")
        border_menu.aboutToShow.connect(self.handle_menu_show)
        border_menu.aboutToHide.connect(self.handle_menu_hide)

        # Countries
        countries_action = QAction("Countries", self, checkable=True)
        countries_action.setData(4)
        countries_action.toggled.connect(self.handle_border_toggle)
        border_menu.addAction(countries_action)
        
        # Regions
        self.regions_menu = border_menu.addMenu("Regions")
        self.populate_regions_menu()
        
        debug_menu = menu_bar.addMenu("&Debug")
        dev_tools_action = QAction("Open Remote Debugger", self)
        dev_tools_action.triggered.connect(self.open_remote_debugger)
        debug_menu.addAction(dev_tools_action)

    def handle_menu_show(self):
        self.sender().menuAction().setProperty("mouse-over", True)

    def handle_menu_hide(self):
        self.sender().menuAction().setProperty("mouse-over", False)


    def populate_regions_menu(self):
        try:
            # Add "Show All" option first
            all_action = QAction("Show All", self, checkable=True)
            all_action.setData("ALL")
            all_action.toggled.connect(self.toggle_all_regions_for_country)
            self.regions_menu.addAction(all_action)
            self.regions_menu.addSeparator()

            country_names = sorted(border_fetcher.get_country_list())
            for name in country_names:
                # A single, checkable action for each country to show all its regions
                country_action = QAction(name, self, checkable=True)
                country_action.setData(name)
                country_action.toggled.connect(self.toggle_all_regions_for_country)
                self.regions_menu.addAction(country_action)
        except Exception as e:
            self.add_log(f"Failed to populate regions menu: {e}")
            error_action = QAction("Error loading countries", self)
            error_action.setEnabled(False)
            self.regions_menu.addAction(error_action)
            
    def toggle_all_regions_for_country(self, is_checked):
        action = self.sender()
        if not action: return
        
        country_name = action.data()
        layer_id = f"regions_{country_name}".replace(" ", "_")

        if is_checked:
            self.add_log(f"Fetching regions for {country_name}...")
            self.border_fetcher_thread = BorderFetcherThread(6, country_name)
            self.border_fetcher_thread.data_ready.connect(
                lambda level, name, data, lid=layer_id: self.on_country_regions_data_ready(lid, data)
            )
            self.border_fetcher_thread.error.connect(lambda msg: self.add_log(f"Failed to fetch regions: {msg}"))
            self.border_fetcher_thread.start()
        else:
            self.map_widget.run_js(f"window.removeBorderLayer('{layer_id}');")

    def on_country_regions_data_ready(self, layer_id, data):
        self.add_log(f"Region data for {layer_id} has been successfully loaded.")
        feature_collection_json = json.dumps(data)
        self.map_widget.run_js(f"window.addCountryRegionsLayer('{layer_id}', {feature_collection_json});")
        
    def open_remote_debugger(self):
        webbrowser.open("http://localhost:8888")

    def fetch_url_from_js(self, request_id, url):
        thread = UrlFetcherThread(request_id, url)
        thread.data_ready.connect(self.on_url_data_ready)
        thread.error.connect(self.on_url_fetch_error)
        self.url_fetcher_threads[request_id] = thread
        thread.start()

    def on_url_data_ready(self, request_id, data):
        self.map_widget.run_js(f"window.onDataFetched('{request_id}', {json.dumps(data)});")
        if request_id in self.url_fetcher_threads:
            del self.url_fetcher_threads[request_id]

    def on_url_fetch_error(self, request_id, error_msg):
        self.add_log(f"Proxy Error for request {request_id}: {error_msg}")
        self.map_widget.run_js(f"window.onDataFetchError('{request_id}', '{error_msg}');")
        if request_id in self.url_fetcher_threads:
            del self.url_fetcher_threads[request_id]

    def on_map_ready(self):
        self.add_log("[JS] Karte ist bereit.")
        self.draw_all_markers_on_map()
        self.set_terrain_opacity(self.opacity_slider.value())
        self.map_widget.run_js(f"window.setInitialPoiData({json.dumps(self.poi_data)});")
        for key in self.poi_data:
            self.map_widget.toggle_poi_layer(key, False) 

    def create_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #555; margin-top: 5px; margin-bottom: 5px;")
        return line

    def add_log(self, message):
        self.log_console.append(message)
        self.log_console.verticalScrollBar().setValue(self.log_console.verticalScrollBar().maximum())

    def handle_border_toggle(self, is_checked):
        action = self.sender()
        if not action: return
        level = action.data()
        
        if is_checked:
            self.start_border_fetch(level, action)
        else:
            self.map_widget.run_js(f"window.toggleBorderLayer({level}, false);")

    def start_border_fetch(self, level, action_to_update):
        self.add_log(f"Fetching global borders for level {level}...")
        # Pass None for country_name when fetching all countries
        self.border_fetcher_thread = BorderFetcherThread(level)
        self.border_fetcher_thread.data_ready.connect(
            lambda lvl, name, data: self.on_border_data_ready(lvl, data)
        )
        self.border_fetcher_thread.error.connect(lambda msg: self.on_border_fetch_error(msg, action_to_update))
        self.border_fetcher_thread.start()

    def on_border_data_ready(self, level, data):
        self.add_log(f"Border data received for level {level}. Updating map.")
        json_data_str = json.dumps(data)
        self.map_widget.run_js(f"window.updateBorderLayer({level}, {json_data_str});")
        self.map_widget.run_js(f"window.toggleBorderLayer({level}, true);")

    def on_border_fetch_error(self, error_message, action_to_update):
        self.add_log(f"Error fetching border data: {error_message}")
        QMessageBox.warning(self, "Network Error", f"Could not fetch border data: {error_message}")
        if action_to_update:
            action_to_update.setChecked(False)

    def toggle_terrain_layer(self, state):
        is_visible = state == Qt.CheckState.Checked.value
        self.map_widget.run_js(f"window.setTerrainAutoMode({str(is_visible).lower()});")

    def set_terrain_opacity(self, value):
        self.map_widget.run_js(f"window.setTerrainOpacity({value / 100.0});")

    def set_terrain_enhancement(self, value):
        self.map_widget.run_js(f"window.setTerrainEnhancement({value});")

    def populate_poi_menu(self):
        self.poi_menu.clear()
        tree_structure = {}
        for file_key in sorted(self.poi_data.keys()):
            if '/' in file_key:
                category, _ = file_key.split('/', 1)
                if category not in tree_structure:
                    tree_structure[category] = []
                tree_structure[category].append(file_key)
            else:
                self.add_log(f"Info: Datei '{file_key}' im Hauptverzeichnis von 'poi_data' wird ignoriert.")

        for category in sorted(tree_structure.keys()):
            category_name = category.replace('_', ' ').title()
            category_menu = self.poi_menu.addMenu(category_name)
            
            show_all_action = QAction(f"Alle '{category_name}' anzeigen", self)
            show_all_action.triggered.connect(lambda checked=False, menu=category_menu, state=True: self.toggle_category_actions(menu, state))
            category_menu.addAction(show_all_action)
            
            hide_all_action = QAction(f"Alle '{category_name}' ausblenden", self)
            hide_all_action.triggered.connect(lambda checked=False, menu=category_menu, state=False: self.toggle_category_actions(menu, state))
            category_menu.addAction(hide_all_action)
            
            category_menu.addSeparator()
            
            for file_key in sorted(tree_structure[category]):
                filename = file_key.split('/')[-1]
                display_name = os.path.splitext(filename)[0].replace('_', ' ').title()
                
                action = QAction(display_name, self, checkable=True)
                action.setData(file_key)
                action.toggled.connect(self.handle_poi_action_toggle)
                category_menu.addAction(action)

    def load_all_poi_data(self):
        poi_folder = "poi_data"
        self.add_log(f"Suche nach POI-Daten im Ordner '{poi_folder}'...")
        self.poi_data.clear()

        if not os.path.exists(poi_folder):
            os.makedirs(poi_folder)
            self.add_log(f"Ordner '{poi_folder}' wurde erstellt.")
            for subfolder in ["celts", "romans", "medieval", "modern"]:
                os.makedirs(os.path.join(poi_folder, subfolder), exist_ok=True)
            self.populate_poi_menu()
            return

        for dirpath, _, filenames in os.walk(poi_folder):
            for filename in filenames:
                if filename.endswith('.json'):
                    filepath = os.path.join(dirpath, filename)
                    relative_path = os.path.relpath(filepath, poi_folder)
                    file_key = relative_path.replace('\\', '/')

                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                self.poi_data[file_key] = data
                                self.add_log(f"'{file_key}' geladen: {len(data)} Einträge.")
                            else:
                                self.add_log(f"Warnung: '{file_key}' ist keine Liste.")
                    except Exception as e:
                        self.add_log(f"Fehler beim Laden von '{file_key}': {e}")
        
        self.add_log("POI-Daten laden abgeschlossen.")
        self.populate_poi_menu()

    def handle_poi_action_toggle(self, is_checked):
        action = self.sender()
        if action:
            file_key = action.data()
            if file_key:
                self.map_widget.toggle_poi_layer(file_key, is_checked)

    def toggle_category_actions(self, menu, state):
        for action in menu.actions():
            if action.isCheckable():
                action.setChecked(state)

    def set_start_location(self, lat, lon, name):
        self.current_location = (lat, lon)
        self.current_location_label.setText(f"Start: {name}")
        self.add_log(f"Startpunkt auf '{name}' gesetzt.")

    def search_location(self):
        query = self.search_input.text().strip()
        if not query: return

        try:
            numbers = re.findall(r"[-+]?\d*\.\d+|\d+", query.replace(',', '.'))
            if len(numbers) == 2:
                lat, lon = float(numbers[0]), float(numbers[1])
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    self.set_start_location(lat, lon, f"{lat:.4f}, {lon:.4f}")
                    self.map_widget.center_on_location(lat, lon, f"Koordinaten: {lat:.4f}, {lon:.4f}")
                    return
        except (ValueError, IndexError):
            pass

        try:
            location = self.geolocator.geocode(query, timeout=10)
            if location:
                self.set_start_location(location.latitude, location.longitude, location.address.split(',')[0])
                self.map_widget.center_on_location(location.latitude, location.longitude, location.address)
            else:
                QMessageBox.information(self, "Suche", f"Der Ort '{query}' konnte nicht gefunden werden.")
        except Exception as e:
            self.add_log(f"Fehler bei der Suche: {e}")
            QMessageBox.critical(self, "Fehler", f"Ein unerwarteter Fehler bei der Suche ist aufgetreten: {e}")

    def determine_current_location(self):
        try:
            location = self.geolocator.geocode("me", timeout=10)
            if location:
                self.set_start_location(location.latitude, location.longitude, "Eigener Standort")
                self.map_widget.run_js(f"window.setView({location.latitude}, {location.longitude}, 14);")
            else:
                QMessageBox.information(self, "Standort", "Konnte den eigenen Standort nicht ermitteln.")
        except Exception as e:
            self.add_log(f"Fehler bei der Standortermittlung: {e}")
            QMessageBox.critical(self, "Standort Fehler", f"Ein unerwarteter Fehler ist aufgetreten: {e}")

    def navigate_to_destination(self):
        if not self.current_location:
            QMessageBox.warning(self, "Navigation", "Bitte ermitteln Sie zuerst Ihren Startpunkt.")
            return
        marker_id = self.destination_selector.currentData()
        if not marker_id:
            QMessageBox.information(self, "Navigation", "Bitte wählen Sie ein Ziel aus.")
            return
        if marker_id in self.markers:
            marker = self.markers[marker_id]
            url = f"https://www.google.com/maps/dir/{self.current_location[0]},{self.current_location[1]}/{marker['lat']},{marker['lon']}"
            webbrowser.open(url)
        else:
            QMessageBox.critical(self, "Navigation Fehler", "Das ausgewählte Ziel konnte nicht gefunden werden.")

    def handle_map_right_click(self, lat, lon):
        self.request_add_marker_dialog.emit(lat, lon)

    def show_add_marker_dialog(self, lat, lon):
        dialog = AddMarkerDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            marker_id = str(uuid.uuid4())
            new_marker = {"id": marker_id, "lat": lat, "lon": lon, **data}
            self.markers[marker_id] = new_marker
            self.update_marker_list_ui()
            self.map_widget.add_permanent_marker(new_marker)
            self.save_markers()

    def update_marker_list_ui(self):
        self.marker_list_widget.clear()
        self.destination_selector.clear()
        self.destination_selector.addItem("Ziel auswählen...", None)
        sorted_markers = sorted(self.markers.values(), key=lambda m: m['comment'])
        for marker in sorted_markers:
            item = QListWidgetItem(f"{marker['comment']} ({marker['icon']})")
            item.setData(Qt.ItemDataRole.UserRole, marker['id'])
            self.marker_list_widget.addItem(item)
            self.destination_selector.addItem(marker['comment'], marker['id'])

    def center_on_marker(self, item):
        marker_id = item.data(Qt.ItemDataRole.UserRole)
        if marker_id in self.markers:
            marker = self.markers[marker_id]
            self.map_widget.run_js(f"window.setView({marker['lat']}, {marker['lon']}, 15);")
            self.map_widget.run_js(f"window.openMarkerPopup('{marker_id}');")

    def delete_selected_marker(self):
        selected_items = self.marker_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Löschen", "Bitte wählen Sie einen Marker zum Löschen aus.")
            return
        marker_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        if marker_id in self.markers:
            del self.markers[marker_id]
            self.save_markers()
            self.update_marker_list_ui()
            self.map_widget.remove_permanent_marker(marker_id)
            self.add_log(f"Marker '{marker_id}' gelöscht.")

    def save_markers(self):
        try:
            with open(self.markers_file, 'w', encoding='utf-8') as f:
                json.dump(self.markers, f, indent=4)
            self.add_log("Marker gespeichert.")
        except IOError as e:
            QMessageBox.critical(self, "Speicherfehler", f"Fehler beim Speichern der Marker: {e}")

    def load_markers(self):
        if not os.path.exists(self.markers_file):
            return
        try:
            with open(self.markers_file, 'r', encoding='utf-8') as f:
                self.markers = json.load(f)
            self.add_log("Marker geladen.")
            self.update_marker_list_ui()
        except Exception as e:
            QMessageBox.critical(self, "Ladefehler", f"Fehler beim Laden der Marker-Datei: {e}.")
            self.markers = {}

    def draw_all_markers_on_map(self):
        if self.markers:
            self.map_widget.update_all_markers(list(self.markers.values()))

    def closeEvent(self, event):
        """ Handles the window close event to ensure clean shutdown of threads. """
        self.add_log("Anwendung wird beendet... Warte auf Threads.")
        
        # Stop border fetcher thread if it's running
        if self.border_fetcher_thread and self.border_fetcher_thread.isRunning():
            self.border_fetcher_thread.stop()
            self.border_fetcher_thread.wait() # Wait for it to finish

        # Stop all URL fetcher threads
        for request_id, thread in list(self.url_fetcher_threads.items()):
            if thread.isRunning():
                thread.stop()
                thread.wait()

        self.add_log("Alle Threads beendet. Anwendung wird geschlossen.")
        event.accept()


def main():
    # The local server is not needed with the Python proxy approach
    app = QApplication(sys.argv)
    
    # Lade das Stylesheet
    qss_file = QFile("dark_theme.qss")
    if qss_file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text):
        stream = QTextStream(qss_file)
        app.setStyleSheet(stream.readAll())
    else:
        print("Warnung: dark_theme.qss nicht gefunden oder konnte nicht geöffnet werden.")
        
    window = TreasureHunterApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()