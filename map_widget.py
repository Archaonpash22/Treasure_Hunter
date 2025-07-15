import os
import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QUrl, pyqtSlot, QObject, pyqtSignal

# Import asset modules
from assets import map_assets
from assets.countries.europe import germany as germany_assets
from assets.countries.europe import austria as austria_assets
from assets.countries.europe import switzerland as switzerland_assets
from assets.countries.europe import italy as italy_assets

# Define paths for local files
ROOT_DIR = os.path.dirname(__file__)
HTML_MAP_FILE = os.path.join(ROOT_DIR, "map.html")

class MapBridge(QObject):
    log_requested = pyqtSignal(str)
    map_ready = pyqtSignal()
    map_right_clicked = pyqtSignal(float, float)
    fetch_url_requested = pyqtSignal(str, str)

    @pyqtSlot(str)
    def log(self, message):
        self.log_requested.emit(message)

    @pyqtSlot()
    def onMapReady(self):
        self.map_ready.emit()

    @pyqtSlot(float, float)
    def onMapRightClicked(self, lat, lon):
        self.map_right_clicked.emit(lat, lon)
        
    @pyqtSlot(str, str)
    def fetchUrl(self, requestId, url):
        self.fetch_url_requested.emit(requestId, url)


class MapWidget(QWidget):
    def __init__(self, terrain_data, parent=None):
        super().__init__(parent)
        self.bridge = MapBridge()
        self.terrain_data = terrain_data
        self.init_ui()
        self.create_map_html_file()
        self.load_map()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.web_view = QWebEngineView()
        
        self.web_view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        
        self.channel = QWebChannel(self.web_view.page())
        self.web_view.page().setWebChannel(self.channel)
        self.channel.registerObject("bridge", self.bridge)
        layout.addWidget(self.web_view)

    def create_map_html_file(self):
        utfgrid_script_content = """
        L.Util.ajax=function(t,e){"use strict";if(void 0===window.XMLHttpRequest)window.XMLHttpRequest=function(){try{return new ActiveXObject("Microsoft.XMLHTTP.6.0")}catch(t){try{return new ActiveXObject("Microsoft.XMLHTTP.3.0")}catch(t){throw new Error("XMLHttpRequest is not supported")}}};var i=new window.XMLHttpRequest;i.open("GET",t),i.onreadystatechange=function(){4===i.readyState&&200===i.status&&(window.JSON?e(JSON.parse(i.responseText)):e(eval("("+i.responseText+")")))},i.send(null)};L.UtfGrid=(L.Layer||L.Class).extend({options:{subdomains:"abc",minZoom:0,maxZoom:18,tileSize:256,resolution:4,useJsonP:!0,pointerCursor:!0},_mouseOn:null,initialize:function(t,e){L.Util.setOptions(this,e),this._url=t,this._cache={},this.options.useJsonP&&(this._windowKey="_l_utfgrid_"+L.stamp(this),window[this._windowKey]={})},onAdd:function(t){this._map=t,this._container=this._map._container,this._update();var e=this._map.getZoom();this.options.minZoom<e&&this.options.maxZoom>e&&this._addEvents()},onRemove:function(){this._removeEvents(),this._mouseOn=null,this.options.useJsonP&&delete window[this._windowKey]},createTile:function(t){return this._loadTile(t),document.createElement("div")},_loadTile:function(t){var e=this.getTileUrl(t),i=this._tileCoordsToKey(t);this._cache[i]||(this.options.useJsonP?this._loadJsonP(e,i):L.Util.ajax(e,L.bind(function(t){this._cache[i]=t,this._update()},this)))},_loadJsonP:function(t,e){var i=document.getElementsByTagName("head")[0],s=document.createElement("script");return window[this._windowKey][e]=L.bind(function(t){this._cache[e]=t,delete window[this._windowKey][e],i.removeChild(s),this._update()},this),s.type="text/javascript",s.src=t,i.appendChild(s),s},_addEvents:function(){L.DomEvent.on(this._container,"mousemove",this._onMouseMove,this),L.DomEvent.on(this._map,"click",this._onClick,this),L.DomEvent.on(this._map,"zoomend",this._onZoom,this),L.DomEvent.on(this._map,"moveend",this._onMove,this)},_removeEvents:function(){L.DomEvent.off(this._container,"mousemove",this._onMouseMove,this),L.DomEvent.off(this._map,"click",this._onClick,this),L.DomEvent.off(this._map,"zoomend",this._onZoom,this),L.DomEvent.off(this._map,"moveend",this._onMove,this)},_onZoom:function(){this._cache={},this._update()},_onMove:function(){this._update()},_onMouseMove:function(t){var e=this._objectForEvent(t);e&&e.id!==(this._mouseOn&&this._mouseOn.id)?(this._fire("mouseover",this._mouseOn=e),this.options.pointerCursor&&(this._container.style.cursor="pointer")):e||!this._mouseOn||(this._fire("mouseout",this._mouseOn),this._mouseOn=null,this.options.pointerCursor&&(this._container.style.cursor=""))},_onClick:function(t){var e=this._objectForEvent(t);e&&this._fire("click",e)},_objectForEvent:function(t){var e=this._map.project(t.latlng),tile=this._getTile(e);if(!tile)return null;var i=Math.floor((e.x-tile.x)/this.options.resolution),s=Math.floor((e.y-tile.y)/this.options.resolution),o=tile.grid.length-1;if(i<0||i>o||s<0||s>o)return null;var n=this._utfDecode(tile.grid[s].charCodeAt(i)),r=tile.data[n];return r?L.Util.extend({latlng:t.latlng,id:n},r):null},_getTile:function(t){var e=this._getTileCoords(t),i=this._tileCoordsToKey(e),s=this._cache[i];return s?((s.x=this._getTilePoint(e).x),(s.y=this._getTilePoint(e).y)):this._loadTile(e),s},_getTileCoords:function(t){return{x:Math.floor(t.x/this.options.tileSize),y:Math.floor(t.y/this.options.tileSize),z:this._map.getZoom()}},_getTilePoint:function(t){return{x:t.x*this.options.tileSize,y:t.y*this.options.tileSize}},_tileCoordsToKey:function(t){return t.z+"/"+t.x+"/"+t.y},_update:function(){var t=this._map.getPixelBounds(),e=this._map.getZoom();if(!(e>this.options.maxZoom||e<this.options.minZoom)){var i=this._getTileCoords(t.min),s=this._getTileCoords(t.max);for(var o=i.x;o<=s.x;o++)for(var n=i.y;n<=s.y;n++)this._loadTile({x:o,y:n,z:e})}},_utfDecode:function(t){return t>=93&&t--,t>=35&&t--,t-32},getTileUrl:function(t){var e=L.Util.template(this._url,L.Util.extend({s:L.TileLayer.prototype._getSubdomain.call(this,t),z:t.z,x:t.x,y:t.y},this.options));return this.options.useJsonP?e+"?callback="+this._windowKey+"."+this._tileCoordsToKey(t):e},addLayer:function(){},removeLayer:function(){},_fire:L.Evented.prototype.fire});L.utfGrid=function(t,e){return new L.UtfGrid(t,e)};
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
            
            <script>
            {utfgrid_script_content}
            </script>
            
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

            function log(msg) {{ if(window.bridge) window.bridge.log(msg); }}

            document.addEventListener('DOMContentLoaded', () => {{
                new QWebChannel(qt.webChannelTransport, channel => {{
                    window.bridge = channel.objects.bridge;
                    initializeMap();
                }});
            }});

            function initializeMap() {{
                var requestCallbacks = {{}};
                L.Util.ajax = function(url, callback) {{
                    const requestId = 'req_' + Math.random().toString(36).substr(2, 9);
                    requestCallbacks[requestId] = callback;
                    window.bridge.fetchUrl(requestId, url);
                }};

                window.onDataFetched = function(requestId, data) {{
                    if (requestCallbacks[requestId]) {{
                        requestCallbacks[requestId](data);
                        delete requestCallbacks[requestId];
                    }}
                }};
                
                window.onDataFetchError = function(requestId, error) {{
                    log(`Fetch error for ${{requestId}}: ${{error}}`);
                    delete requestCallbacks[requestId];
                }};

                for (const key in icons_data) {{
                    if (icons_data.hasOwnProperty(key)) {{
                        icons[key] = L.icon(icons_data[key]);
                    }}
                }}
                
                map = L.map('map', {{ crs: L.CRS.EPSG3857, center: [49.5, 12.5], zoom: 6 }});
                
                baseLayers['OpenStreetMap'] = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '© OpenStreetMap contributors', maxZoom: 19
                }}).addTo(map);

                baseLayers['Satellit'] = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                    attribution: 'Tiles © Esri', maxZoom: 19
                }});

                baseLayers['Topographisch'] = L.tileLayer('https://{{s}}.tile.opentopomap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: 'Map data: © OpenStreetMap contributors, SRTM | Map style: © OpenTopoMap (CC-BY-SA)', maxZoom: 17
                }});
                
                baseLayers['Roman Empire'] = L.tileLayer('https://dh.gu.se/tiles/imperium/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '<a href="https://imperium.ahlfeldt.se/" target="_blank">DARE</a>',
                    maxNativeZoom: 11,
                    maxZoom: 19
                }});

                L.control.layers(baseLayers).addTo(map);
                
                var dareUtfGrid = L.utfGrid('https://dh.gu.se/tiles/pleiades/{{z}}/{{x}}/{{y}}.grid.json', {{
                    resolution: 4,
                    useJsonP: false
                }});

                dareUtfGrid.on('click', function (e) {{
                    if (e.data) {{
                        const key = Object.keys(e.data)[0];
                        if (key) {{
                            const placeInfo = e.data[key];
                            var content = `<b>${{placeInfo.name}}</b><br><a href="${{placeInfo.pleiades_url}}" target="_blank">Details auf Pleiades ansehen</a>`;
                            L.popup()
                                .setLatLng(e.latlng)
                                .setContent(content)
                                .openOn(map);
                        }}
                    }}
                }});
                dareUtfGrid.on('mouseover', function (e) {{ map.getContainer().style.cursor = 'pointer'; }});
                dareUtfGrid.on('mouseout', function (e) {{ map.getContainer().style.cursor = ''; }});

                map.on('baselayerchange', function (e) {{
                    if (e.name === 'Roman Empire') {{
                        map.addLayer(dareUtfGrid);
                    }} else {{
                        if (map.hasLayer(dareUtfGrid)) {{
                            map.removeLayer(dareUtfGrid);
                        }}
                    }}
                }});

                map.createPane('terrainPane').style.zIndex = 450;
                map.getPane('terrainPane').style.pointerEvents = 'none';
                map.createPane('borderPane').style.zIndex = 500;
                map.getPane('borderPane').style.pointerEvents = 'none';

                const paneOption = {{ pane: 'terrainPane' }};
                for (const countryName in terrainData) {{
                    const country = terrainData[countryName];
                    for (const layerKey in country.layers) {{
                        if (!terrainLayers[layerKey]) {{
                            const layerInfo = country.layers[layerKey];
                            let layerOptions = {{ ...layerInfo.options, ...paneOption }};
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
                borderLayers[4] = L.geoJSON(null, {{ ...{{ style: {{ color: '#0000FF', weight: 2, fillOpacity: 0.05, interactive: false }} }}, ...borderPaneOption }});

                map.on('contextmenu', e => window.bridge.onMapRightClicked(e.latlng.lat, e.latlng.lng));
                map.on('moveend zoomend', updateAutoTerrain);
                
                if(window.bridge) window.bridge.onMapReady();
            }}
            
            {self.get_full_js_functions()}
        </script>
        </html>
        """
        with open(HTML_MAP_FILE, "w", encoding="utf-8") as f:
            f.write(html_content)

    def get_full_js_functions(self):
        return """
            function updateAutoTerrain() {
                if (!isTerrainAutoMode) {
                    for (const key in terrainLayers) {
                        if (terrainLayers[key].setOpacity) terrainLayers[key].setOpacity(0);
                    }
                    map.getContainer().style.filter = 'none';
                    return;
                }
                
                const zoom = map.getZoom();
                const center = map.getCenter();
                let targetKey = null;

                if (terrainData.germany && terrainData.germany.bounds.bavaria && L.latLngBounds(terrainData.germany.bounds.bavaria).contains(center)) {
                    const logic = terrainData.germany.logic.bavaria;
                    if (zoom >= 15) { targetKey = logic['15']; } 
                    else if (zoom >= 14) { targetKey = logic['14']; } 
                    else { targetKey = logic['0']; }
                }
                else if (terrainData.austria && terrainData.austria.bounds.austria && L.latLngBounds(terrainData.austria.bounds.austria).contains(center)) {
                    targetKey = terrainData.austria.logic.austria['0'];
                }
                else if (terrainData.switzerland && terrainData.switzerland.bounds.switzerland && L.latLngBounds(terrainData.switzerland.bounds.switzerland).contains(center)) {
                    targetKey = terrainData.switzerland.logic.switzerland['0'];
                }
                else if (terrainData.italy && terrainData.italy.bounds.italy && L.latLngBounds(terrainData.italy.bounds.italy).contains(center)) {
                    targetKey = terrainData.italy.logic.italy['0'];
                }
                else if (terrainData.germany && terrainData.germany.bounds.germany && L.latLngBounds(terrainData.germany.bounds.germany).contains(center)) {
                    targetKey = terrainData.germany.logic.germany['0'];
                }

                for (const key in terrainLayers) {
                    terrainLayers[key].setOpacity(key === targetKey ? currentTerrainOpacity : 0);
                }
                
                const mapContainer = map.getContainer();
                let filterStyle = (zoom >= 15 && targetKey) ? 'brightness(70%) contrast(120%)' : 'none';
                mapContainer.style.filter = filterStyle;
            }

            window.updateBorderLayer = function(level, geoJsonData) {
                if (borderLayers[level]) {
                    borderLayers[level].clearLayers();
                    if (geoJsonData && geoJsonData.features) {
                        borderLayers[level].addData(geoJsonData);
                    }
                }
            };

            window.toggleBorderLayer = function(level, show) {
                const layer = borderLayers[level];
                if (layer) {
                    if (show && !map.hasLayer(layer)) {
                        map.addLayer(layer);
                    } else if (!show && map.hasLayer(layer)) {
                        map.removeLayer(layer);
                    }
                }
            };

            window.addCountryRegionsLayer = function(layerId, geoJsonData) {
                if (borderLayers[layerId]) {
                    map.removeLayer(borderLayers[layerId]);
                }
                borderLayers[layerId] = L.geoJSON(geoJsonData, {
                    style: { color: '#008000', weight: 2, fillOpacity: 0.05, interactive: false },
                    pane: 'borderPane'
                }).addTo(map);
            };

            window.removeBorderLayer = function(layerId) {
                if (borderLayers[layerId]) {
                    map.removeLayer(borderLayers[layerId]);
                    delete borderLayers[layerId];
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
                    const pathParts = layerKey.split('/');
                    const era = pathParts.length > 1 ? pathParts[0] : 'unknown';
                    let filename = pathParts.length > 1 ? pathParts[1] : pathParts[0];
                    let typeFromFilename = filename.replace(/\\.json$/, '');
                    
                    if (filename.includes('viereckschanze')) {
                        typeFromFilename = 'viereckschanze';
                    } else if (filename.includes('siedlung') || filename.includes('oppida')) {
                        typeFromFilename = 'siedlung';
                    } else {
                        typeFromFilename = typeFromFilename.split('_').slice(1).join('_');
                    }
                    
                    data.forEach(poi => {
                        if (poi && typeof poi.lat === 'number' && typeof poi.lon === 'number') {
                            let popupContent = `<div class="poi-popup-content"><b>${poi.name}</b>`;
                            if (poi.zusammenfassung) popupContent += `<br><p>${poi.zusammenfassung.substring(0, 200)}...</p>`;
                            if (poi.url) popupContent += `<br><a href="${poi.url}" target="_blank">Weitere Infos</a>`;
                            popupContent += `</div>`;
                            
                            let iconToUse = icons[typeFromFilename] || icons[era] || icons['punkt'];
                            L.marker([poi.lat, poi.lon], { icon: iconToUse }).bindPopup(popupContent).addTo(layer);
                        } else {
                            log(`[JS Warning] Skipping invalid POI object in ${layerKey}: ${JSON.stringify(poi)}`);
                        }
                    });
                    if (!map.hasLayer(layer)) map.addLayer(layer);
                } else {
                    if (map.hasLayer(layer)) map.removeLayer(layer);
                }
            };
            
            window.addPermanentMarker = function(data) {
                if(data && typeof data.lat === 'number' && typeof data.lon === 'number') {
                    const marker = L.marker([data.lat, data.lon], {icon: icons[data.icon] || icons['punkt']}).addTo(map).bindPopup(`<b>${data.comment}</b>`);
                    permanentMarkers[data.id] = marker;
                } else {
                    log(`[JS Warning] Skipping invalid permanent marker: ${JSON.stringify(data)}`);
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
            window.removePermanentMarker = (id) => { if(permanentMarkers[id]) { map.removeLayer(permanentMarkers[id]); delete permanentMarkers[id]; }};
            window.updateAllMarkers = (markers) => { 
                for(const id in permanentMarkers) { map.removeLayer(permanentMarkers[id]); } 
                permanentMarkers = {}; 
                markers.forEach(m => window.addPermanentMarker(m)); 
            };
            window.openMarkerPopup = (id) => { if(permanentMarkers[id]) permanentMarkers[id].openPopup(); };
            window.addSearchMarker = (lat, lon, popupText) => {
                if (searchMarker) { map.removeLayer(searchMarker); }
                searchMarker = L.marker([lat, lon], {icon: icons['start']}).addTo(map).bindPopup(popupText).openPopup();
            };
        """

    def load_map(self):
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