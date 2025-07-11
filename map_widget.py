import os
import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QUrl, pyqtSlot, QObject, pyqtSignal

# Import asset modules
from assets import map_assets
from assets.countries.europe import germany as germany_assets
from assets.countries.europe import austria as austria_assets
from assets.countries.europe import switzerland as switzerland_assets
from assets.countries.europe import italy as italy_assets

# Define the HTML file path for the Leaflet map
HTML_MAP_FILE = os.path.join(os.path.dirname(__file__), "map.html")

class MapBridge(QObject):
    """
    A bridge class to facilitate communication between Python (PyQt) and JavaScript
    within the QWebEngineView.
    """
    log_requested = pyqtSignal(str)
    map_ready = pyqtSignal()
    map_right_clicked = pyqtSignal(float, float)

    @pyqtSlot(str)
    def log(self, message):
        self.log_requested.emit(message)

    @pyqtSlot()
    def onMapReady(self):
        self.map_ready.emit()

    @pyqtSlot(float, float)
    def onMapRightClicked(self, lat, lon):
        self.map_right_clicked.emit(lat, lon)

class MapWidget(QWidget):
    """
    A PyQt widget that embeds a web engine view to display an interactive Leaflet map.
    """
    def __init__(self, terrain_data, parent=None):
        super().__init__(parent)
        self.bridge = MapBridge()
        self.terrain_data = terrain_data
        self.init_ui()
        self.create_map_html()
        self.load_map()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        self.web_view = QWebEngineView()
        self.web_view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        self.channel = QWebChannel(self.web_view.page())
        self.web_view.page().setWebChannel(self.channel)
        self.channel.registerObject("bridge", self.bridge)
        layout.addWidget(self.web_view)

    def create_map_html(self):
        """
        Generates the HTML content for the map, injecting assets from the modules.
        """
        icons_json = json.dumps(map_assets.icons)
        colors_json = json.dumps(map_assets.culture_colors)
        terrain_data_json = json.dumps(self.terrain_data)

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Karte</title>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/qwebchannel/qwebchannel.js"></script>
            <style>
                html, body, #map {{ height: 100%; width: 100%; margin: 0; }}
                .leaflet-popup-content-wrapper {{ border-radius: 8px; }}
                .poi-popup-content img {{ max-width: 100%; height: auto; border-radius: 4px; margin-bottom: 8px; }}
                .poi-popup-content a {{ color: #007bff; text-decoration: none; }}
                .poi-popup-content a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <div id="map"></div>
        </body>
        <script>
            var map, searchMarker;
            var baseLayers = {{}};
            var terrainLayers = {{}};
            var poiLayers = {{}};
            var permanentMarkers = {{}};
            var isTerrainAutoMode = false;
            var currentTerrainOpacity = 0.7;
            var allPoiDataFromPython = {{}};
            var borderLayers = {{}};
            
            const terrainData = {terrain_data_json};

            const icons_data = {icons_json};
            const cultureColors = {colors_json};
            const icons = {{}};
            for (const key in icons_data) {{
                if (icons_data.hasOwnProperty(key)) {{
                    icons[key] = L.icon(icons_data[key]);
                }}
            }}

            function log(msg) {{ if(window.bridge) window.bridge.log(msg); }}

            document.addEventListener('DOMContentLoaded', () => {{
                new QWebChannel(qt.webChannelTransport, channel => {{
                    window.bridge = channel.objects.bridge;
                    initializeMap();
                }});
            }});

            function initializeMap() {{
                map = L.map('map', {{ crs: L.CRS.EPSG3857, center: [49.5, 12.5], zoom: 6 }});
                
                map.createPane('terrainPane').style.zIndex = 450;
                map.getPane('terrainPane').style.pointerEvents = 'none';
                map.createPane('borderPane').style.zIndex = 500;
                map.getPane('borderPane').style.pointerEvents = 'none';

                baseLayers['Standard'] = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{ attribution: '&copy; OpenStreetMap', maxZoom: 19 }}).addTo(map);
                
                const paneOption = {{ pane: 'terrainPane' }};
                for (const countryName in terrainData) {{
                    const country = terrainData[countryName];
                    for (const layerKey in country.layers) {{
                        if (!terrainLayers[layerKey]) {{
                            const layerInfo = country.layers[layerKey];
                            let layerOptions = {{ ...layerInfo.options, ...paneOption }};

                            // --- FIX: Handle both 'crs' and 'srs' parameters ---
                            let crs_string = layerOptions.crs || layerOptions.srs;
                            if (crs_string && typeof crs_string === 'string') {{
                                if (crs_string === 'EPSG:3857') {{
                                    // Set the CRS object that Leaflet understands
                                    layerOptions.crs = L.CRS.EPSG3857;
                                }}
                            }}

                            if (layerInfo.url.includes('{{z}}')) {{
                                terrainLayers[layerKey] = L.tileLayer(layerInfo.url, layerOptions);
                            }} else {{
                                terrainLayers[layerKey] = L.tileLayer.wms(layerInfo.url, layerOptions);
                            }}
                            terrainLayers[layerKey].setOpacity(0).addTo(map);
                        }}
                    }}
                }}
                
                var borderPaneOption = {{ pane: 'borderPane' }};
                borderLayers[4] = L.geoJSON(null, {{ ...{{ style: {{ color: '#006400', weight: 3, fillOpacity: 0.05, interactive: false }} }}, ...borderPaneOption }});
                borderLayers[6] = L.geoJSON(null, {{ ...{{ style: {{ color: '#0000CD', weight: 2, fillOpacity: 0.05, interactive: false }} }}, ...borderPaneOption }});
                borderLayers[8] = L.geoJSON(null, {{ ...{{ style: {{ color: '#FF4500', weight: 1, fillOpacity: 0.05, interactive: false }} }}, ...borderPaneOption }});

                map.on('contextmenu', e => window.bridge.onMapRightClicked(e.latlng.lat, e.latlng.lng));
                map.on('moveend zoomend', updateAutoTerrain);
                
                if(window.bridge) window.bridge.onMapReady();
            }}
            
            function updateAutoTerrain() {{
                if (!isTerrainAutoMode) {{
                    for (const key in terrainLayers) {{
                        if (terrainLayers[key].setOpacity) terrainLayers[key].setOpacity(0);
                    }}
                    map.getContainer().style.filter = 'none';
                    return;
                }}
                
                const zoom = map.getZoom();
                const center = map.getCenter();
                let targetKey = null;

                if (terrainData.germany && terrainData.germany.bounds.bavaria && L.latLngBounds(terrainData.germany.bounds.bavaria).contains(center)) {{
                    const logic = terrainData.germany.logic.bavaria;
                    if (zoom >= 15) {{ targetKey = logic['15']; }} 
                    else if (zoom >= 14) {{ targetKey = logic['14']; }} 
                    else {{ targetKey = logic['0']; }}
                }}
                else if (terrainData.austria && terrainData.austria.bounds.austria && L.latLngBounds(terrainData.austria.bounds.austria).contains(center)) {{
                    targetKey = terrainData.austria.logic.austria['0'];
                }}
                else if (terrainData.switzerland && terrainData.switzerland.bounds.switzerland && L.latLngBounds(terrainData.switzerland.bounds.switzerland).contains(center)) {{
                    targetKey = terrainData.switzerland.logic.switzerland['0'];
                }}
                else if (terrainData.italy && terrainData.italy.bounds.italy && L.latLngBounds(terrainData.italy.bounds.italy).contains(center)) {{
                    targetKey = terrainData.italy.logic.italy['0'];
                }}
                else if (terrainData.germany && terrainData.germany.bounds.germany && L.latLngBounds(terrainData.germany.bounds.germany).contains(center)) {{
                    targetKey = terrainData.germany.logic.germany['0'];
                }}

                for (const key in terrainLayers) {{
                    terrainLayers[key].setOpacity(key === targetKey ? currentTerrainOpacity : 0);
                }}
                
                const mapContainer = map.getContainer();
                let filterStyle = (zoom >= 15 && targetKey) ? 'brightness(70%) contrast(120%)' : 'none';
                mapContainer.style.filter = filterStyle;
            }}
            
            // ... (All other JS functions remain the same)
        </script>
        </html>
        """.replace("// ... (All other JS functions remain the same)", self.get_full_js_functions())
        with open(HTML_MAP_FILE, "w", encoding="utf-8") as f:
            f.write(html_content)

    def get_full_js_functions(self):
        """
        Returns the string of all other JS functions that were omitted for brevity.
        """
        return """
            window.updateBorderLayer = function(level, geoJsonData) {
                if (borderLayers[level]) {
                    borderLayers[level].clearLayers();
                    if (geoJsonData && geoJsonData.features) {
                        borderLayers[level].addData(geoJsonData);
                    }
                }
            };

            window.toggleBorderLayer = function(level, show) {
                if (borderLayers[level]) {
                    if (show && !map.hasLayer(borderLayers[level])) {
                        map.addLayer(borderLayers[level]);
                    } else if (!show && map.hasLayer(borderLayers[level])) {
                        map.removeLayer(borderLayers[level]);
                    }
                }
            };

            window.getMapState = function() {
                return {
                    bbox: map.getBounds().toBBoxString(),
                    zoom: map.getZoom()
                };
            };
            
            window.setInitialPoiData = function(data) {
                allPoiDataFromPython = data;
                for (const layerKey in allPoiDataFromPython) {
                    if (allPoiDataFromPython.hasOwnProperty(layerKey)) {
                        if (!poiLayers[layerKey]) {
                            poiLayers[layerKey] = L.layerGroup();
                        }
                    }
                }
            };

            window.togglePoiLayerVisibility = function(layerKey, show) {
                const layer = poiLayers[layerKey];
                const data = allPoiDataFromPython[layerKey];
                if (!layer || !data) return;

                if (show) {
                    layer.clearLayers();
                    const era = layerKey.split('_')[0]; 
                    const typeFromFilename = layerKey.replace(/\\.json$/, '').split('_').slice(1).join('_');

                    data.forEach(poi => {
                        if (typeof poi.lat !== 'number' || typeof poi.lon !== 'number' || isNaN(poi.lat) || isNaN(poi.lon)) return;
                        let popupContent = `<div class="poi-popup-content"><b>${poi.name}</b>`;
                        if (poi.image_url) popupContent += `<br><img src="${poi.image_url}" alt="${poi.name}" onerror="this.style.display='none';">`;
                        if (poi.url) popupContent += `<br><a href="${poi.url}" target="_blank">Wikipedia-Eintrag</a>`;
                        popupContent += `</div>`;
                        
                        let iconToUse = icons[typeFromFilename] || icons[era] || icons['punkt'];
                        let finalIconUrl = iconToUse.options.iconUrl;
                        const eraColor = cultureColors[era];
                        
                        if (eraColor && finalIconUrl.startsWith('data:image/svg+xml;base64,')) {
                            let svgBase64 = finalIconUrl.substring('data:image/svg+xml;base64,'.length);
                            let svgString = atob(svgBase64); 
                            svgString = svgString.replace(/stroke="#000000"/g, `stroke="${eraColor}"`);
                            svgString = svgString.replace(/fill="#000000"/g, `fill="${eraColor}"`);
                            finalIconUrl = 'data:image/svg+xml;base64,' + btoa(svgString);
                            iconToUse = L.icon({ iconUrl: finalIconUrl, iconSize: iconToUse.options.iconSize });
                        }
                        L.marker([poi.lat, poi.lon], { icon: iconToUse }).bindPopup(popupContent).addTo(layer);
                    });
                    if (!map.hasLayer(layer)) map.addLayer(layer);
                } else {
                    if (map.hasLayer(layer)) map.removeLayer(layer);
                }
            };

            window.setTerrainAutoMode = (enabled) => { isTerrainAutoMode = enabled; updateAutoTerrain(); };
            window.setTerrainOpacity = (opacity) => { currentTerrainOpacity = opacity; updateAutoTerrain(); };
            window.setTerrainEnhancement = function(value) {
                const pane = map.getPane('terrainPane');
                if (!pane) return;
                if (value === 0) { pane.style.filter = 'none'; return; }
                const contrast = 100 + value * 2;
                const brightness = 100 - (value / 5);
                const saturate = 100 - (value / 1.5);
                pane.style.filter = `contrast(${contrast}%) brightness(${brightness}%) saturate(${saturate}%)`;
            };
            window.setView = (lat, lon, zoom = 13) => map.setView([lat, lon], zoom);
            window.addPermanentMarker = (data) => {
                const marker = L.marker([data.lat, data.lon], {icon: icons[data.icon] || icons['punkt']}).addTo(map).bindPopup(`<b>${data.comment}</b>`);
                permanentMarkers[data.id] = marker;
            };
            window.removePermanentMarker = (id) => {
                if(permanentMarkers[id]) { map.removeLayer(permanentMarkers[id]); delete permanentMarkers[id]; }
            };
            window.updateAllMarkers = (markers) => {
                for(const id in permanentMarkers) { map.removeLayer(permanentMarkers[id]); }
                permanentMarkers = {};
                markers.forEach(m => window.addPermanentMarker(m));
            };
            window.openMarkerPopup = (id) => { if(permanentMarkers[id]) permanentMarkers[id].openPopup(); };
            window.addSearchMarker = (lat, lon, popupText) => {
                if (searchMarker) { map.removeLayer(searchMarker); }
                searchMarker = L.marker([lat, lon], {icon: icons['ziel']}).addTo(map).bindPopup(popupText).openPopup();
            };
        """

    def load_map(self):
        profile = QWebEngineProfile.defaultProfile()
        profile.clearHttpCache()
        self.web_view.setUrl(QUrl.fromLocalFile(os.path.abspath(HTML_MAP_FILE)))

    def run_js(self, script, callback=None):
        if callback:
            self.web_view.page().runJavaScript(script, callback)
        else:
            self.web_view.page().runJavaScript(script)

    def center_on_location(self, lat, lon, popup_text):
        js_popup_text = popup_text.replace("'", "\\'").replace("\n", "<br>")
        self.run_js(f"window.setView({lat}, {lon});")
        self.run_js(f"window.addSearchMarker({lat}, {lon}, '{js_popup_text}');")

    def add_permanent_marker(self, marker_data):
        self.run_js(f"window.addPermanentMarker({json.dumps(marker_data)});")

    def remove_permanent_marker(self, marker_id):
        self.run_js(f"window.removePermanentMarker('{marker_id}');")
        
    def update_all_markers(self, markers_list):
        self.run_js(f"window.updateAllMarkers({json.dumps(markers_list)});")

    def toggle_poi_layer(self, layer_key, is_visible):
        self.run_js(f"window.togglePoiLayerVisibility('{layer_key}', {str(is_visible).lower()});")
