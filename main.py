import sys
import re
import json
import os
import uuid
import webbrowser
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QMessageBox, QStatusBar, QSlider,
    QTextEdit, QComboBox, QListWidget, QListWidgetItem, QDialog,
    QDialogButtonBox, QFormLayout, QCheckBox, QFrame, QTreeWidget, QTreeWidgetItem
)
from PyQt6.QtCore import QFile, QTextStream, Qt, pyqtSignal
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

from map_widget import MapWidget

class AddMarkerDialog(QDialog):
    """
    Dialog for adding a new marker to the map.
    Allows users to input a comment and select an icon for the marker.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Neuen Marker hinzufügen")
        self.setModal(True) # Make the dialog modal (blocks parent window)

        self.layout = QFormLayout(self)

        self.comment_input = QLineEdit()
        self.comment_input.setPlaceholderText("z.B. Keltenschanze, Römische Münze...")
        self.layout.addRow("Kommentar:", self.comment_input)

        self.icon_selector = QComboBox()
        # Available icons for markers. These correspond to icon definitions in map.html.
        self.icon_selector.addItems(["Punkt", "Münze", "Ziel"])
        self.layout.addRow("Icon:", self.icon_selector)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept) # Connect OK button to accept the dialog
        self.button_box.rejected.connect(self.reject) # Connect Cancel button to reject the dialog
        self.layout.addRow(self.button_box)

    def get_data(self):
        """
        Retrieves the data entered by the user in the dialog.
        Returns a dictionary with 'comment' and 'icon'.
        """
        return {
            "comment": self.comment_input.text() or "Unbenannter Marker", # Default comment if empty
            "icon": self.icon_selector.currentText().lower() # Get selected icon in lowercase
        }

class TreasureHunterApp(QMainWindow):
    """
    Main application window for the Treasure Hunter app.
    Manages UI, map interactions, marker management, and POI display.
    """
    # Signal emitted when a right-click on the map requests adding a marker
    request_add_marker_dialog = pyqtSignal(float, float)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Treasure Hunter")
        self.setGeometry(100, 100, 1300, 850) # Set initial window size and position
        self.geolocator = Nominatim(user_agent="treasure_hunter_app_v26") # Geocoding service
        
        self.markers = {} # Dictionary to store user-added markers
        self.markers_file = "markers.json" # File to save/load markers
        self.poi_data = {} # Dictionary to store Points of Interest data
        self.current_location = None # Stores the user's current or searched location
        
        self.init_ui() # Initialize the user interface
        self.setStatusBar(QStatusBar(self)) # Add a status bar at the bottom
        
        # Connect the custom signal to the dialog display method
        self.request_add_marker_dialog.connect(self.show_add_marker_dialog)
        self.add_log("Anwendung gestartet.") # Log application start
        self.load_markers() # Load previously saved markers
        self.load_all_poi_data() # Load all predefined POI data

    def init_ui(self):
        """
        Initializes the main user interface components and layout.
        """
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Control panel on the left side
        control_panel = QWidget()
        control_panel.setFixedWidth(350)
        control_panel.setObjectName("controlPanel") # For CSS styling
        control_layout = QVBoxLayout(control_panel)
        control_layout.setContentsMargins(15, 15, 15, 10)
        control_layout.setSpacing(8)

        # --- Navigation & Search Section ---
        navigation_label = QLabel("Navigation & Suche")
        navigation_label.setObjectName("titleLabel")
        control_layout.addWidget(navigation_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Ort suchen oder 'lat, lon'...")
        self.search_input.returnPressed.connect(self.search_location) # Trigger search on Enter key
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

        # --- Map Layers Section ---
        control_layout.addWidget(self.create_separator()) # Visual separator
        layer_label = QLabel("Karten-Layer")
        layer_label.setObjectName("titleLabel")
        control_layout.addWidget(layer_label)
        
        # Background Overlay (Terrain)
        overlay_sublabel = QLabel("Hintergrund-Überlagerung")
        overlay_sublabel.setObjectName("subTitleLabel")
        control_layout.addWidget(overlay_sublabel)

        self.terrain_checkbox = QCheckBox("Gelände-Überlagerung (Auto)")
        self.terrain_checkbox.stateChanged.connect(self.toggle_terrain_layer)
        control_layout.addWidget(self.terrain_checkbox)

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100) # 0% to 100% opacity
        self.opacity_slider.setValue(70) # Default opacity
        self.opacity_slider.valueChanged.connect(self.set_terrain_opacity)
        control_layout.addWidget(self.opacity_slider)

        enhancement_label = QLabel("Konturenschärfe:")
        control_layout.addWidget(enhancement_label)
        self.enhancement_slider = QSlider(Qt.Orientation.Horizontal)
        self.enhancement_slider.setRange(0, 100) # Adjustment range for enhancement
        self.enhancement_slider.setValue(0) # Default no enhancement
        self.enhancement_slider.valueChanged.connect(self.set_terrain_enhancement)
        control_layout.addWidget(self.enhancement_slider)

        # Points of Interest (POI)
        poi_sublabel = QLabel("Interessante Orte")
        poi_sublabel.setObjectName("subTitleLabel")
        control_layout.addWidget(poi_sublabel)

        self.poi_tree = QTreeWidget()
        self.poi_tree.setHeaderHidden(True) # Hide the header for the tree widget
        self.poi_tree.setObjectName("poiTree")
        control_layout.addWidget(self.poi_tree)
        # populate_poi_tree wird erst nach load_all_poi_data aufgerufen,
        # um sicherzustellen, dass alle Daten geladen sind.
        # self.populate_poi_tree() # Removed from here
        self.poi_tree.itemChanged.connect(self.handle_poi_toggle) # Handle checkbox changes

        # --- My Markers Section ---
        control_layout.addWidget(self.create_separator())
        marker_label = QLabel("Meine Fundorte")
        marker_label.setObjectName("titleLabel")
        control_layout.addWidget(marker_label)

        self.marker_list_widget = QListWidget()
        self.marker_list_widget.setObjectName("markerList")
        self.marker_list_widget.itemDoubleClicked.connect(self.center_on_marker) # Center map on double click
        control_layout.addWidget(self.marker_list_widget)

        delete_marker_button = QPushButton("Ausgewählten Marker löschen")
        delete_marker_button.clicked.connect(self.delete_selected_marker)
        control_layout.addWidget(delete_marker_button)
        
        control_layout.addStretch() # Pushes content to the top

        # --- Log Console ---
        log_label = QLabel("Log")
        log_label.setObjectName("subTitleLabel")
        control_layout.addWidget(log_label)

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True) # Make log console read-only
        self.log_console.setObjectName("logConsole")
        self.log_console.setFixedHeight(120)
        control_layout.addWidget(self.log_console)

        # Map widget on the right side
        self.map_widget = MapWidget()
        self.map_widget.bridge.log_requested.connect(self.add_log) # Connect JS logs to Python log console
        self.map_widget.bridge.map_ready.connect(self.on_map_ready) # Signal when map is initialized in JS
        self.map_widget.bridge.map_right_clicked.connect(self.handle_map_right_click) # Handle right-clicks on map
        
        main_layout.addWidget(control_panel)
        main_layout.addWidget(self.map_widget)

    def on_map_ready(self):
        """
        Callback function executed when the JavaScript map reports itself as ready.
        Draws all existing markers and sets initial terrain layer state.
        """
        self.add_log("[JS] Karte ist bereit.")
        self.draw_all_markers_on_map()
        self.toggle_terrain_layer(self.terrain_checkbox.checkState().value)
        
        # NEU: Sende ALLE POI-Daten an JavaScript, sobald die Karte bereit ist
        self.map_widget.run_js(f"window.setInitialPoiData({json.dumps(self.poi_data)});")

        # Initialisiere die POI-Layer-Sichtbarkeit in JS (alle aus)
        for key in self.poi_data:
            # Das 'data'-Argument ist hier nicht mehr nötig, da die Daten bereits in JS sind
            self.map_widget.toggle_poi_layer(key, False, []) 

    def create_separator(self):
        """
        Creates a horizontal line separator for UI organization.
        """
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #555; margin-top: 5px; margin-bottom: 5px;")
        return line

    def add_log(self, message):
        """
        Appends a message to the log console and scrolls to the bottom.
        """
        self.log_console.append(message)
        self.log_console.verticalScrollBar().setValue(self.log_console.verticalScrollBar().maximum())

    def toggle_terrain_layer(self, state):
        """
        Toggles the visibility of the terrain overlay on the map.
        """
        is_visible = state == Qt.CheckState.Checked.value
        self.map_widget.run_js(f"window.setTerrainAutoMode({str(is_visible).lower()});")
        if is_visible:
            # If enabled, apply current opacity and enhancement settings
            self.set_terrain_opacity(self.opacity_slider.value())
            self.set_terrain_enhancement(self.enhancement_slider.value())

    def set_terrain_opacity(self, value):
        """
        Sets the opacity of the terrain layer on the map.
        Value is converted from 0-100 to 0.0-1.0 for JavaScript.
        """
        self.map_widget.run_js(f"window.setTerrainOpacity({value / 100});")

    def set_terrain_enhancement(self, value):
        """
        Sets the visual enhancement (contrast, brightness, saturation) of the terrain layer.
        """
        self.map_widget.run_js(f"window.setTerrainEnhancement({value});")

    def populate_poi_tree(self):
        """
        Populates the QTreeWidget with POI categories and their respective files.
        This method is now more dynamic, building the tree based on loaded data.
        """
        self.poi_tree.clear() # Clear existing items before repopulating
        
        # Group files by culture
        culture_groups = {}
        for filename in self.poi_data.keys():
            try:
                # Expected format: "culture_type.json"
                parts = filename.split('_', 1)
                if len(parts) == 2:
                    culture_raw = parts[0]
                    # Capitalize first letter for display
                    culture_display = culture_raw.capitalize()
                    
                    if culture_display not in culture_groups:
                        culture_groups[culture_display] = []
                    culture_groups[culture_display].append(filename)
                else:
                    self.add_log(f"Warnung: Dateiname '{filename}' passt nicht zum erwarteten Format 'kultur_typ.json'.")
            except Exception as e:
                self.add_log(f"Fehler beim Parsen des Dateinamens '{filename}': {e}")


        # Sort cultures alphabetically
        sorted_cultures = sorted(culture_groups.keys())

        for culture_display in sorted_cultures:
            era_item = QTreeWidgetItem(self.poi_tree)
            era_item.setText(0, culture_display)
            era_item.setFlags(era_item.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)
            era_item.setCheckState(0, Qt.CheckState.Unchecked)
            
            # Sort files within each culture
            sorted_files = sorted(culture_groups[culture_display])

            for file in sorted_files:
                # Extract typ from filename for display
                typus = os.path.splitext(file)[0].split('_', 1)[-1].replace('_', ' ').title()
                file_item = QTreeWidgetItem(era_item)
                file_item.setText(0, typus)
                file_item.setData(0, Qt.ItemDataRole.UserRole, file) # Store filename as user data
                file_item.setFlags(file_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                file_item.setCheckState(0, Qt.CheckState.Unchecked)

    def load_all_poi_data(self):
        """
        Loads all predefined Points of Interest data from JSON files.
        It now scans the current directory for JSON files matching the pattern.
        """
        # Define a list of potential POI files that *could* exist.
        # This list can be dynamically built or manually maintained.
        # For a truly dynamic approach, you'd scan the directory.
        # For now, let's include common ones and dynamically find others.
        potential_poi_files = [
            "kelten_viereckschanzen.json", "kelten_oppida.json", "kelten_schatzfunde.json",
            "kelten_siedlung.json", # Updated from _siedlungen.json to _siedlung.json
            "kelten_schatz.json", # New from extractor
            "kelten_münze.json", # New from extractor
            "roemer_kastell.json", # Updated from _kastelle.json
            "mittelalter_burg.json", # Updated from _burgen.json
            "weltkriege_bunker.json"
        ]

        # Additionally, scan the current directory for any other *.json files
        # that might have been created by the extractor.
        for f in os.listdir('.'):
            if f.endswith('.json') and f not in potential_poi_files and f != self.markers_file:
                potential_poi_files.append(f)

        self.add_log("Starte Laden der POI-Daten...")
        for file in sorted(potential_poi_files): # Sort for consistent logging
            if file == self.markers_file:
                continue # Skip the markers file

            try:
                if os.path.exists(file):
                    with open(file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list): # Ensure it's a list of POIs
                            self.poi_data[file] = data
                            self.add_log(f"'{file}' geladen. Enthält {len(data)} Einträge.")
                        else:
                            self.add_log(f"Warnung: '{file}' ist keine Liste von POIs. Überspringe. Inhaltstyp: {type(data)}")
                            self.poi_data[file] = [] # Initialize as empty list
                else:
                    self.add_log(f"Info: '{file}' nicht gefunden. Wird übersprungen.")
                    self.poi_data[file] = [] # Initialize as empty list if file doesn't exist
            except json.JSONDecodeError as e:
                self.poi_data[file] = []
                self.add_log(f"Fehler: '{file}' ist keine gültige JSON-Datei. Fehler: {e}")
            except Exception as e:
                self.poi_data[file] = []
                self.add_log(f"Unerwarteter Fehler beim Laden von '{file}': {e}")
        
        self.add_log("POI-Daten laden abgeschlossen. Aktualisiere POI-Baum.")
        self.populate_poi_tree() # Populate the tree AFTER all data is loaded

    def handle_poi_toggle(self, item, column):
        """
        Handles the toggling of POI layers based on the QTreeWidget checkbox state.
        Communicates the state change and data to the JavaScript map.
        """
        # Only process if it's a child item (a specific POI file)
        # Check if item has a parent (i.e., it's not a top-level culture item)
        if item.parent():
            file_key = item.data(0, Qt.ItemDataRole.UserRole)
            if file_key:
                is_checked = item.checkState(0) == Qt.CheckState.Checked
                # Das 'data'-Argument ist hier nicht mehr nötig, da die Daten bereits in JS sind
                self.map_widget.toggle_poi_layer(file_key, is_checked, []) 
        # If it's a parent item, its children's states will trigger this method individually.
        # Qt's ItemIsAutoTristate handles the visual state of the parent.

    def set_start_location(self, lat, lon, name):
        """
        Sets the current starting location for navigation.
        """
        self.current_location = (lat, lon)
        self.current_location_label.setText(f"Start: {name}")
        self.add_log(f"Startpunkt auf '{name}' gesetzt.")

    def search_location(self):
        """
        Searches for a location based on user input (address or coordinates).
        Updates the map and sets the current start location.
        """
        query = self.search_input.text().strip()
        if not query: return # Do nothing if search input is empty

        # Try to parse as coordinates (lat, lon)
        try:
            normalized_query = query.replace(',', '.') # Handle comma as decimal separator
            numbers = re.findall(r"[-+]?\d*\.\d+|\d+", normalized_query)
            if len(numbers) == 2:
                lat, lon = float(numbers[0]), float(numbers[1])
                # Basic validation for latitude and longitude ranges
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    self.set_start_location(lat, lon, f"{lat:.4f}, {lon:.4f}")
                    self.map_widget.center_on_location(lat, lon, f"Koordinaten: {lat:.4f}, {lon:.4f}")
                    return # Exit if coordinates were successfully processed
        except (ValueError, IndexError):
            pass # Not a valid coordinate pair, proceed to geocoding

        # If not coordinates, try to geocode as an address
        try:
            location = self.geolocator.geocode(query, timeout=10) # 10-second timeout
            if location:
                # Use the first part of the address for display
                self.set_start_location(location.latitude, location.longitude, location.address.split(',')[0])
                self.map_widget.center_on_location(location.latitude, location.longitude, location.address)
            else:
                QMessageBox.information(self, "Suche", f"Der Ort '{query}' konnte nicht gefunden werden.")
        except (GeocoderTimedOut, GeocoderUnavailable) as e:
            self.add_log(f"Geocoding-Fehler: {e}. Bitte Internetverbindung prüfen oder später versuchen.")
            QMessageBox.warning(self, "Geocoding Fehler", f"Konnte Ort nicht finden: {e}. Bitte Internetverbindung prüfen oder später versuchen.")
        except Exception as e:
            self.add_log(f"Ein unerwarteter Fehler bei der Suche ist aufgetreten: {e}")
            QMessageBox.critical(self, "Fehler", f"Ein unerwarteter Fehler bei der Suche ist aufgetreten: {e}")

    def determine_current_location(self):
        """
        Attempts to determine the user's current location using geocoding.
        Note: This relies on the Nominatim service's ability to guess "me", which is not always precise.
        """
        try:
            location = self.geolocator.geocode("me", timeout=10)
            if location:
                self.set_start_location(location.latitude, location.longitude, "Eigener Standort")
                self.map_widget.run_js(f"window.setView({location.latitude}, {location.longitude}, 14);")
            else:
                QMessageBox.information(self, "Standort", "Konnte den eigenen Standort nicht ermitteln.")
        except (GeocoderTimedOut, GeocoderUnavailable) as e:
            self.add_log(f"Standort-Fehler: {e}. Bitte Internetverbindung prüfen oder später versuchen.")
            QMessageBox.warning(self, "Standort Fehler", f"Konnte Standort nicht ermitteln: {e}. Bitte Internetverbindung prüfen oder später versuchen.")
        except Exception as e:
            self.add_log(f"Ein unerwarteter Fehler bei der Standortermittlung ist aufgetreten: {e}")
            QMessageBox.critical(self, "Standort Fehler", f"Ein unerwarteter Fehler ist aufgetreten: {e}")

    def navigate_to_destination(self):
        """
        Opens Google Maps in a web browser to navigate from the current start location
        to a selected marker destination.
        """
        if not self.current_location:
            QMessageBox.warning(self, "Navigation", "Bitte ermitteln Sie zuerst Ihren Startpunkt.")
            return

        marker_id = self.destination_selector.currentData()
        if not marker_id:
            QMessageBox.information(self, "Navigation", "Bitte wählen Sie ein Ziel aus.")
            return

        if marker_id in self.markers:
            marker = self.markers[marker_id]
            # Construct Google Maps directions URL
            url = f"https://www.google.com/maps/dir/{self.current_location[0]},{self.current_location[1]}/{marker['lat']},{marker['lon']}"
            webbrowser.open(url) # Open URL in default web browser
        else:
            self.add_log(f"Fehler: Zielmarker mit ID '{marker_id}' nicht gefunden.")
            QMessageBox.critical(self, "Navigation Fehler", "Das ausgewählte Ziel konnte nicht gefunden werden.")


    def handle_map_right_click(self, lat, lon):
        """
        Handles a right-click event on the map by emitting a signal
        to show the Add Marker dialog at the clicked coordinates.
        """
        self.request_add_marker_dialog.emit(lat, lon)

    def show_add_marker_dialog(self, lat, lon):
        """
        Displays the Add Marker dialog and processes the new marker data
        if the dialog is accepted.
        """
        dialog = AddMarkerDialog(self)
        if dialog.exec(): # Show dialog and wait for user interaction
            data = dialog.get_data()
            marker_id = str(uuid.uuid4()) # Generate a unique ID for the new marker
            new_marker = {
                "id": marker_id,
                "lat": lat,
                "lon": lon,
                "comment": data["comment"],
                "icon": data["icon"]
            }
            self.markers[marker_id] = new_marker # Add new marker to dictionary
            self.update_marker_list_ui() # Update UI lists
            self.map_widget.add_permanent_marker(new_marker) # Add marker to map
            self.save_markers() # Save markers to file

    def update_marker_list_ui(self):
        """
        Clears and repopulates the marker list widget and destination selector
        with current markers.
        """
        self.marker_list_widget.clear()
        self.destination_selector.clear()
        self.destination_selector.addItem("Ziel auswählen...", None) # Default empty item

        if not self.markers: return # No markers to display

        # Sort markers alphabetically by comment for better readability
        sorted_markers = sorted(self.markers.values(), key=lambda m: m['comment'])
        for marker in sorted_markers:
            item = QListWidgetItem(f"{marker['comment']} ({marker['icon']})")
            item.setData(Qt.ItemDataRole.UserRole, marker['id']) # Store marker ID in item data
            self.marker_list_widget.addItem(item)
            self.destination_selector.addItem(marker['comment'], marker['id']) # Add to destination selector

    def center_on_marker(self, item):
        """
        Centers the map on a selected marker and opens its popup.
        """
        marker_id = item.data(Qt.ItemDataRole.UserRole) # Retrieve marker ID from list item
        if marker_id in self.markers:
            # Set map view to marker's coordinates with a zoom level of 15
            self.map_widget.run_js(f"window.setView({self.markers[marker_id]['lat']}, {self.markers[marker_id]['lon']}, 15);")
            # Open the marker's popup
            self.map_widget.run_js(f"window.openMarkerPopup('{marker_id}');")

    def delete_selected_marker(self):
        """
        Deletes the currently selected marker from the list, map, and saved data.
        """
        selected_items = self.marker_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Löschen", "Bitte wählen Sie einen Marker zum Löschen aus.")
            return

        # Get the ID of the first selected item
        marker_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        if marker_id in self.markers:
            del self.markers[marker_id] # Remove from internal dictionary
            self.save_markers() # Save changes to file
            self.update_marker_list_ui() # Update UI
            self.map_widget.remove_permanent_marker(marker_id) # Remove from map
            self.add_log(f"Marker '{marker_id}' gelöscht.")
        else:
            self.add_log(f"Fehler: Marker mit ID '{marker_id}' nicht gefunden.")


    def save_markers(self):
        """
        Saves the current markers dictionary to a JSON file.
        """
        try:
            with open(self.markers_file, 'w', encoding='utf-8') as f:
                json.dump(self.markers, f, indent=4) # Pretty print JSON
            self.add_log("Marker gespeichert.")
        except IOError as e:
            self.add_log(f"Fehler beim Speichern der Marker: {e}")
            QMessageBox.critical(self, "Speicherfehler", f"Fehler beim Speichern der Marker: {e}")

    def load_markers(self):
        """
        Loads markers from the JSON file into the application.
        """
        if not os.path.exists(self.markers_file):
            self.add_log("Keine Marker-Datei gefunden. Starte mit leeren Markern.")
            return # No file, nothing to load

        try:
            with open(self.markers_file, 'r', encoding='utf-8') as f:
                self.markers = json.load(f)
            self.add_log("Marker geladen.")
            self.update_marker_list_ui() # Update UI after loading
        except json.JSONDecodeError as e:
            self.add_log(f"Fehler beim Laden der Marker-Datei (JSON-Formatfehler): {e}")
            QMessageBox.critical(self, "Ladefehler", f"Fehler beim Laden der Marker-Datei: {e}. Die Datei ist möglicherweise beschädigt.")
            self.markers = {} # Reset markers if file is corrupted
        except Exception as e:
            self.add_log(f"Ein unerwarteter Fehler beim Laden der Marker ist aufgetreten: {e}")
            QMessageBox.critical(self, "Ladefehler", f"Ein unerwarteter Fehler ist aufgetreten: {e}")

    def draw_all_markers_on_map(self):
        """
        Sends all currently loaded markers to the map widget for display.
        """
        if self.markers:
            # Convert dictionary values to a list for JSON serialization
            self.map_widget.update_all_markers(list(self.markers.values()))
            self.add_log(f"Alle {len(self.markers)} Marker auf der Karte aktualisiert.")
        else:
            self.add_log("Keine Marker zum Zeichnen auf der Karte vorhanden.")


def main():
    """
    Main entry point for the application.
    Initializes the QApplication, loads a stylesheet, and starts the main window.
    """
    app = QApplication(sys.argv)
    
    # Load custom dark theme stylesheet
    qss_file = QFile("dark_theme.qss")
    if qss_file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text):
        stream = QTextStream(qss_file)
        app.setStyleSheet(stream.readAll())
    else:
        print("Warning: dark_theme.qss not found or could not be opened.")

    window = TreasureHunterApp()
    window.show() # Display the main application window
    sys.exit(app.exec()) # Start the Qt event loop

if __name__ == "__main__":
    main()

