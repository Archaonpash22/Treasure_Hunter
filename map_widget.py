import os
import json
import webbrowser
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QUrl, pyqtSlot, QObject, pyqtSignal

# Import asset modules
from assets import map_assets

# Define paths for local files
ROOT_DIR = os.path.dirname(__file__)
HTML_MAP_FILE = os.path.join(ROOT_DIR, "map.html")

class MapBridge(QObject):
    log_requested = pyqtSignal(str)
    map_ready = pyqtSignal()
    map_right_clicked = pyqtSignal(float, float)
    fetch_url_requested = pyqtSignal(str, str)
    fetch_text_requested = pyqtSignal(str, str)
    view_changed = pyqtSignal(str)          # JSON: zoom, bounds, center, terrain source at the centre
    mouse_moved = pyqtSignal(float, float)
    terrain_loading = pyqtSignal(int)       # terrain tiles still loading

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

    @pyqtSlot(str, str)
    def fetchText(self, requestId, url):
        self.fetch_text_requested.emit(requestId, url)

    @pyqtSlot(str)
    def onViewChanged(self, payload):
        self.view_changed.emit(payload)

    @pyqtSlot(float, float)
    def onMouseMove(self, lat, lon):
        self.mouse_moved.emit(lat, lon)

    @pyqtSlot(int)
    def onTerrainLoading(self, pending):
        self.terrain_loading.emit(pending)


class _ExternalLinkPage(QWebEnginePage):
    """Opens links from popups (Denkmal-Atlas, Wikipedia, Pleiades) in the system browser."""

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        if nav_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked and url.scheme() in ('http', 'https'):
            webbrowser.open(url.toString())
            return False
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)

    def createWindow(self, _window_type):
        # target="_blank": hand the first navigation of the would-be window to the browser.
        page = QWebEnginePage(self)
        page.urlChanged.connect(lambda url: (webbrowser.open(url.toString()), page.deleteLater()))
        return page


class MapWidget(QWidget):
    def __init__(self, terrain_data, tile_proxy=None, parent=None):
        super().__init__(parent)
        self.bridge = MapBridge()
        self.terrain_data = terrain_data
        # Local tile cache proxy (tile_cache.py): {'host': '127.0.0.1', 'ports': [...]}.
        # None = fetch terrain tiles directly from the upstream services.
        self.tile_proxy = tile_proxy
        self.init_ui()
        self.create_map_html_file()
        self.load_map()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.web_view = QWebEngineView()
        self.web_view.setPage(_ExternalLinkPage(self.web_view))

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
        tile_proxy_json = json.dumps(self.tile_proxy)

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Treasure Hunter</title>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/qwebchannel/qwebchannel.js"></script>
            <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css"/>
            <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>

            <script>
            {utfgrid_script_content}
            </script>

            <style>
                html, body, #map {{ height: 100%; width: 100%; margin: 0; }}
                #map {{ background: #1a1d21; font: 13px 'Segoe UI', sans-serif; }}
                .leaflet-bar {{ border: 1px solid #2a2f36 !important; box-shadow: 0 1px 4px rgba(0,0,0,.35) !important; border-radius: 4px !important; }}
                .leaflet-bar a {{ background: #171a1e; color: #e6e1d6; border-bottom-color: #2a2f36; width: 30px; height: 30px; line-height: 30px; font-weight: 400; }}
                .leaflet-bar a:hover {{ background: #262b31; color: #fff; }}
                .leaflet-bar a.leaflet-disabled {{ background: #171a1e; color: #4b5159; }}
                .leaflet-control-attribution {{ background: rgba(17,19,22,.72) !important; color: #9198a1; font-size: 10px; }}
                .leaflet-control-attribution a {{ color: #c9a967; }}
                .leaflet-control-scale-line {{ background: rgba(17,19,22,.72); color: #e6e1d6; border-color: #9198a1; font-size: 10px; }}
                .leaflet-popup-content-wrapper, .leaflet-popup-tip {{ background: #171a1e; color: #e6e1d6; border-radius: 4px; box-shadow: 0 2px 10px rgba(0,0,0,.45); }}
                .leaflet-popup-content {{ font: 13px/1.45 'Segoe UI', sans-serif; margin: 10px 14px; }}
                .leaflet-container a.leaflet-popup-close-button {{ color: #9198a1; }}
                .poi-popup-content img {{ max-width: 100%; height: auto; border-radius: 3px; margin-bottom: 8px; }}
                .poi-popup-content p {{ margin: 6px 0; color: #b9b4aa; }}
                .leaflet-container .leaflet-popup-content a {{ color: #d4a24c; text-decoration: none; }}
                .leaflet-container .leaflet-popup-content a:hover {{ text-decoration: underline; }}
                .active-layers {{ display: flex; flex-direction: column; gap: 4px; margin-top: 6px !important; }}
                .active-chip {{
                    display: flex; align-items: center; gap: 6px; cursor: pointer; user-select: none; width: fit-content;
                    background: rgba(17, 19, 22, 0.88); border: 1px solid #2a2f36; border-radius: 4px;
                    padding: 3px 8px 3px 7px; color: #e6e1d6; font: 600 11px 'Segoe UI', sans-serif;
                    box-shadow: 0 1px 4px rgba(0,0,0,.35);
                }}
                .active-chip:hover {{ border-color: #d4a24c; }}
                .active-chip .dot {{ width: 8px; height: 8px; border-radius: 50%; flex: none; background: #6fbf73; }}
                .active-chip.wait .dot {{ background: #e0b23c; }}
                .active-chip.off {{ color: #8d939c; }}
                .active-chip.off .dot {{ background: #d0605a; }}
                .site-cluster {{
                    background: rgba(17, 19, 22, 0.82); border: 1.5px solid #d4a24c; border-radius: 50%;
                    color: #f0e3c4; font: 600 11px 'Segoe UI', sans-serif; display: flex; align-items: center; justify-content: center;
                }}
                .region-label {{
                    position: absolute; transform: translate(-50%, -50%); white-space: nowrap;
                    background: rgba(17, 19, 22, 0.78); border: 1px solid rgba(212, 162, 76, 0.7); border-radius: 3px;
                    padding: 1px 5px; font: 600 11px 'Bahnschrift', 'Segoe UI', sans-serif; letter-spacing: .5px; color: #f0e3c4;
                }}
            </style>
        </head>
        <body>
            <div id="map"></div>
        </body>
        <script>
            var map, searchMarker, currentBaseLayer, dareUtfGrid, monumentLayer;
            var analysisLayers = {{}};
            var activeLayersBox = null;
            const MONUMENT_WMS = 'https://geoservices.bayern.de/od/wms/gdi/v1/denkmal';
            var baseLayers = {{}};
            var terrainLayers = {{}};
            var poiLayers = {{}};
            var permanentMarkers = {{}};
            var isTerrainAutoMode = false;
            var currentTerrainOpacity = 0.7;
            var allPoiDataFromPython = {{}};
            var borderLayers = {{}};

            const terrainData = {terrain_data_json};
            const tileProxy = {tile_proxy_json};
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

                map = L.map('map', {{ crs: L.CRS.EPSG3857, center: [49.5, 12.5], zoom: 6, maxZoom: 20 }});
                L.control.scale({{ imperial: false, position: 'bottomleft' }}).addTo(map);

                baseLayers['OpenStreetMap'] = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '© OpenStreetMap contributors', maxNativeZoom: 19, maxZoom: 20
                }}).addTo(map);
                currentBaseLayer = baseLayers['OpenStreetMap'];

                baseLayers['Satellit'] = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                    attribution: 'Tiles © Esri', maxNativeZoom: 19, maxZoom: 20
                }});

                baseLayers['Topographisch'] = L.tileLayer('https://{{s}}.tile.opentopomap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: 'Map data: © OpenStreetMap contributors, SRTM | Map style: © OpenTopoMap (CC-BY-SA)', maxNativeZoom: 17, maxZoom: 20
                }});

                baseLayers['Roman Empire'] = L.tileLayer('https://dh.gu.se/tiles/imperium/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '<a href="https://imperium.ahlfeldt.se/" target="_blank">DARE</a>',
                    maxNativeZoom: 11,
                    maxZoom: 20
                }});

                dareUtfGrid = L.utfGrid('https://dh.gu.se/tiles/pleiades/{{z}}/{{x}}/{{y}}.grid.json', {{
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

                map.createPane('terrainPane').style.zIndex = 450;
                map.getPane('terrainPane').style.pointerEvents = 'none';
                map.createPane('analysisPane').style.zIndex = 460;
                map.getPane('analysisPane').style.pointerEvents = 'none';
                map.createPane('monumentPane').style.zIndex = 470;
                map.getPane('monumentPane').style.pointerEvents = 'none';
                map.createPane('borderPane').style.zIndex = 500;
                map.createPane('routePane').style.zIndex = 520;   // above terrain, monuments and borders
                map.getPane('routePane').style.pointerEvents = 'none';
                map.getPane('borderPane').style.pointerEvents = 'none';

                const paneOption = {{ pane: 'terrainPane' }};
                for (const countryName in terrainData) {{
                    const country = terrainData[countryName];
                    for (const layerKey in country.layers) {{
                        const layerInfo = country.layers[layerKey];
                        if (layerInfo.type === 'dem_analysis') {{
                            // Analysis views: own pane above the LiDAR, one at a time, only via the tile cache.
                            if (tileProxy && tileProxy.ports && tileProxy.ports.length) {{
                                analysisLayers[layerKey] = L.tileLayer('http://' + tileProxy.host + ':{{s}}/tile/' + layerKey + '/{{z}}/{{x}}/{{y}}.png',
                                    {{ ...layerInfo.options, subdomains: tileProxy.ports.map(String), pane: 'analysisPane', keepBuffer: 2 }});
                                analysisLayers[layerKey].on('tileloadstart tileload tileerror tileunload', scheduleLoadingReport);
                            }}
                            continue;
                        }}
                        if (!terrainLayers[layerKey]) {{
                            // Keep more off-screen tiles and skip the intermediate zoom levels while a zoom
                            // animation runs: the WMS servers are slow, so every saved request counts.
                            let layerOptions = {{ keepBuffer: 4, updateWhenZooming: false, ...layerInfo.options, ...paneOption }};
                            if (tileProxy && tileProxy.ports && tileProxy.ports.length) {{
                                // Local cache proxy builds the upstream request itself (see tile_cache.py).
                                // The ports act like tile-server subdomains to get around the browser's
                                // per-host connection limit.
                                const tileTemplate = 'http://' + tileProxy.host + ':{{s}}/tile/' + layerKey + '/{{z}}/{{x}}/{{y}}.png';
                                const proxyOptions = {{ ...layerOptions, subdomains: tileProxy.ports.map(String) }};
                                if (layerInfo.type === 'wms_crop' || layerInfo.options.clipTo) {{
                                    terrainLayers[layerKey] = L.gridLayer.wmsCropped(tileTemplate, {{ ...proxyOptions, tileTemplate: true }});
                                }} else {{
                                    terrainLayers[layerKey] = L.tileLayer(tileTemplate, proxyOptions);
                                }}
                            }} else if (['dem_wms', 'dem_wcs', 'arcgis_map'].includes(layerInfo.type)) {{
                                continue;  // only through the tile cache (it computes / converts these tiles)
                            }} else if (layerInfo.type === 'arcgis_image') {{
                                terrainLayers[layerKey] = L.tileLayer.arcgisImage(layerInfo.url, layerOptions);
                            }} else if (layerInfo.type === 'wms_crop' || layerInfo.options.clipTo) {{
                                terrainLayers[layerKey] = L.gridLayer.wmsCropped(layerInfo.url, layerOptions);
                            }} else if (layerInfo.url.includes('{{z}}')) {{
                                terrainLayers[layerKey] = L.tileLayer(layerInfo.url, layerOptions);
                            }} else {{
                                terrainLayers[layerKey] = L.tileLayer.wms(layerInfo.url, layerOptions);
                            }}
                            terrainLayers[layerKey]._clipAll = layerInfo.options.clipTo || null;
                            terrainLayers[layerKey].on('tileloadstart tileload tileerror tileunload', scheduleLoadingReport);
                            // Added to the map on demand by updateAutoTerrain().
                        }}
                    }}
                }}

                var borderPaneOption = {{ pane: 'borderPane' }};
                borderLayers[4] = L.geoJSON(null, {{ ...{{ style: {{ color: '#d4a24c', weight: 1.6, opacity: 0.9, fillOpacity: 0, interactive: false }} }}, ...borderPaneOption }});
                indexTerrainCatalog();

                // Under the zoom buttons: what is switched on, each line a quick hide/show toggle.
                const ActiveLayers = L.Control.extend({{
                    options: {{ position: 'topleft' }},
                    onAdd: function() {{
                        const div = L.DomUtil.create('div', 'active-layers');
                        L.DomEvent.disableClickPropagation(div);
                        L.DomEvent.disableScrollPropagation(div);
                        activeLayersBox = div;
                        return div;
                    }}
                }});
                new ActiveLayers().addTo(map);

                // Registered ground monuments of Bavaria (BLfD Denkmal-Atlas): metal detecting or digging
                // there needs a permit. Shown above the terrain; a click lists the monuments at that spot.
                monumentLayer = L.tileLayer.wms(MONUMENT_WMS, {{
                    layers: 'bodendenkmalO', format: 'image/png', transparent: true, version: '1.3.0',
                    tileSize: 512, opacity: 0.6, pane: 'monumentPane', maxZoom: 20,
                    bounds: [[47.2, 8.9], [50.6, 13.9]],
                    attribution: 'Bodendenkmäler &copy; Bayerisches Landesamt für Denkmalpflege'
                }});
                map.on('click', e => {{ if (map.hasLayer(monumentLayer)) queryMonuments(e); }});

                map.on('contextmenu', e => window.bridge.onMapRightClicked(e.latlng.lat, e.latlng.lng));
                map.on('moveend zoomend', updateAutoTerrain);
                map.on('moveend', reportView);
                let lastMouse = 0;
                map.on('mousemove', e => {{
                    const now = Date.now();
                    if (now - lastMouse < 50) return;
                    lastMouse = now;
                    window.bridge.onMouseMove(e.latlng.lat, e.latlng.lng);
                }});
                reportView();

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
            // Tile layer for ArcGIS Image Services (exportImage endpoint). Each Leaflet tile is
            // requested as a Web-Mercator bbox, optionally with a server-side renderingRule
            // (e.g. Hillshade), so DTM services can be shown as relief without local processing.
            L.TileLayer.ArcGISImage = L.TileLayer.extend({
                initialize: function(serviceUrl, options) {
                    options = options || {};
                    this._serviceUrl = serviceUrl.endsWith('/') ? serviceUrl.slice(0, -1) : serviceUrl;
                    this._renderingRule = options.renderingRule ? JSON.stringify(options.renderingRule) : null;
                    this._imageFormat = options.imageFormat || 'png';
                    L.TileLayer.prototype.initialize.call(this, serviceUrl, options);
                },
                getTileUrl: function(coords) {
                    const tileSize = this.getTileSize();
                    const nwPoint = coords.scaleBy(tileSize);
                    const sePoint = nwPoint.add(tileSize);
                    const nw = L.CRS.EPSG3857.project(this._map.unproject(nwPoint, coords.z));
                    const se = L.CRS.EPSG3857.project(this._map.unproject(sePoint, coords.z));
                    const params = {
                        f: 'image',
                        bbox: [nw.x, se.y, se.x, nw.y].join(','),
                        bboxSR: 3857,
                        imageSR: 3857,
                        size: tileSize.x + ',' + tileSize.y,
                        format: this._imageFormat,
                        transparent: true
                    };
                    if (this._renderingRule) params.renderingRule = this._renderingRule;
                    return this._serviceUrl + '/exportImage' + L.Util.getParamString(params);
                }
            });
            L.tileLayer.arcgisImage = (serviceUrl, options) => new L.TileLayer.ArcGISImage(serviceUrl, options);

            // State borders for layers with `clipTo`, projected once to zoom-0 world pixels and cut
            // into chunks of up to 128 edges with bounding boxes, so a tile can be classified as
            // inside / outside / on the border without walking every vertex.
            const clipShapes = {};
            function getClipShape(codes) {
                const id = codes.join('+');
                if (clipShapes[id]) return clipShapes[id];
                const rings = [], chunks = [];
                for (const code of codes) {
                    for (const countryName in terrainData) {
                        const rs = (terrainData[countryName].outlines || {})[code];
                        if (!rs) continue;
                        for (const r of rs) {
                            const pts = new Float64Array(r.length * 2);
                            r.forEach(([lat, lng], i) => {
                                const p = L.CRS.EPSG3857.latLngToPoint(L.latLng(lat, lng), 0);
                                pts[2 * i] = p.x; pts[2 * i + 1] = p.y;
                            });
                            rings.push(pts);
                            const n = r.length;
                            for (let a = 0; a < n; a += 128) {
                                const b = Math.min(a + 128, n);  // edges a..b-1, the last one closes the ring
                                let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
                                for (let i = a; i <= b; i++) {
                                    const j = (i % n) * 2;
                                    x0 = Math.min(x0, pts[j]); x1 = Math.max(x1, pts[j]);
                                    y0 = Math.min(y0, pts[j + 1]); y1 = Math.max(y1, pts[j + 1]);
                                }
                                chunks.push({ pts, n, a, b, x0, y0, x1, y1 });
                            }
                        }
                    }
                }
                return (clipShapes[id] = { rings, chunks });
            }

            // 'out', 'in' or 'border' for a rectangle in zoom-0 world pixels.
            function classifyRect(shape, x0, y0, x1, y1) {
                for (const c of shape.chunks) {
                    if (c.x1 < x0 || c.x0 > x1 || c.y1 < y0 || c.y0 > y1) continue;
                    for (let i = c.a; i < c.b; i++) {
                        const j = i * 2, k = ((i + 1) % c.n) * 2;
                        const ax = c.pts[j], ay = c.pts[j + 1], bx = c.pts[k], by = c.pts[k + 1];
                        if (Math.max(ax, bx) >= x0 && Math.min(ax, bx) <= x1 &&
                            Math.max(ay, by) >= y0 && Math.min(ay, by) <= y1) return 'border';
                    }
                }
                // No edge near the rectangle: it lies entirely on one side. Even-odd test of its centre.
                const px = (x0 + x1) / 2, py = (y0 + y1) / 2;
                let inside = false;
                for (const pts of shape.rings) {
                    const n = pts.length / 2;
                    for (let i = 0, j = n - 1; i < n; j = i++) {
                        const yi = pts[2 * i + 1], yj = pts[2 * j + 1];
                        if ((yi > py) !== (yj > py) &&
                            px < (pts[2 * j] - pts[2 * i]) * (py - yi) / (yj - yi) + pts[2 * i]) inside = !inside;
                    }
                }
                return inside ? 'in' : 'out';
            }

            // Canvas WMS layer, used for
            //  - `cropLeft`: each tile is requested that many pixels wider and drawn shifted left,
            //    cutting off a watermark some servers paint at the left edge (Regione Toscana, M-V);
            //  - `clipTo`: tiles outside the given state(s) are not requested at all and tiles on
            //    the border are masked to the state polygon, so neighbouring layers never overlap;
            //  - `whiteToAlpha`: white pixels become transparent (needs CORS, i.e. the tile proxy).
            L.GridLayer.WMSCropped = L.GridLayer.extend({
                initialize: function(url, options) {
                    options = options || {};
                    this._wmsUrl = url;
                    this._cropLeft = options.cropLeft || 0;
                    const version = options.version || '1.1.1';
                    this._wmsParams = {
                        service: 'WMS', request: 'GetMap', version: version,
                        layers: options.layers || '', styles: options.styles || '',
                        format: options.format || 'image/png', transparent: options.transparent !== false
                    };
                    this._wmsParams[version === '1.3.0' ? 'crs' : 'srs'] = 'EPSG:3857';
                    L.GridLayer.prototype.initialize.call(this, options);
                    // Cancel downloads of tiles that scrolled away, so visible tiles get the connections.
                    this.on('tileunload', e => { if (e.tile._img) e.tile._img.src = ''; });
                },
                createTile: function(coords, done) {
                    const tile = document.createElement('canvas');
                    const size = this.getTileSize();
                    tile.width = size.x; tile.height = size.y;
                    const crop = this._cropLeft;
                    const scale = Math.pow(2, coords.z);
                    const ox = coords.x * size.x, oy = coords.y * size.y;  // tile origin in pixels at coords.z
                    let clip = null;
                    if (this.options.clipTo) {
                        const shape = getClipShape(this.options.clipTo);
                        const where = classifyRect(shape, ox / scale, oy / scale, (ox + size.x) / scale, (oy + size.y) / scale);
                        if (where === 'out') {
                            setTimeout(() => done(null, tile), 0);  // nothing of the state here: no request
                            return tile;
                        }
                        if (where === 'border') clip = shape;
                    }
                    const nwPoint = coords.scaleBy(size).subtract([crop, 0]);
                    const sePoint = coords.scaleBy(size).add(size);
                    const nw = L.CRS.EPSG3857.project(this._map.unproject(nwPoint, coords.z));
                    const se = L.CRS.EPSG3857.project(this._map.unproject(sePoint, coords.z));
                    const params = { ...this._wmsParams, width: size.x + crop, height: size.y, bbox: [nw.x, se.y, se.x, nw.y].join(',') };
                    const img = new Image();
                    tile._img = img;
                    const whiteToAlpha = this.options.whiteToAlpha;
                    if (whiteToAlpha) img.crossOrigin = 'anonymous';
                    img.onload = () => {
                        tile._img = null;
                        const ctx = tile.getContext('2d');
                        ctx.drawImage(img, -crop, 0);
                        if (whiteToAlpha) {
                            try {
                                const data = ctx.getImageData(0, 0, tile.width, tile.height);
                                const px = data.data;
                                for (let i = 0; i < px.length; i += 4) {
                                    if (px[i] >= 254 && px[i + 1] >= 254 && px[i + 2] >= 254) px[i + 3] = 0;
                                }
                                ctx.putImageData(data, 0, 0);
                            } catch (e) { /* no CORS (direct mode): show the tile as it is */ }
                        }
                        if (clip) {
                            // Keep only the pixels inside the state.
                            ctx.globalCompositeOperation = 'destination-in';
                            ctx.beginPath();
                            for (const pts of clip.rings) {
                                for (let i = 0; i < pts.length; i += 2) {
                                    const x = pts[i] * scale - ox, y = pts[i + 1] * scale - oy;
                                    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
                                }
                                ctx.closePath();
                            }
                            ctx.fill('evenodd');
                            ctx.globalCompositeOperation = 'source-over';
                        }
                        done(null, tile);
                    };
                    img.onerror = () => { tile._img = null; done(new Error('tile load failed'), tile); };
                    if (this.options.tileTemplate) {
                        const subdomains = this.options.subdomains || [''];
                        const s = subdomains[Math.abs(coords.x + coords.y) % subdomains.length];
                        img.src = L.Util.template(this._wmsUrl, { s: s, z: coords.z, x: coords.x, y: coords.y });
                    } else {
                        img.src = this._wmsUrl + L.Util.getParamString(params, this._wmsUrl);
                    }
                    return tile;
                }
            });
            L.gridLayer.wmsCropped = (url, options) => new L.GridLayer.WMSCropped(url, options);

            // Regions are checked in this order; the first whose bounds contain the map centre wins.
            // Regions defined in the country modules but missing here are checked afterwards.
            const terrainRegionPriority = [
                ['germany', 'germany'],
                ['austria', 'austria'],
                ['switzerland', 'switzerland'],
                ['italy', 'elba'],
                ['italy', 'lunigiana'],
                ['italy', 'emilia_romagna'],
                ['italy', 'tuscany'],
                ['italy', 'italy']
            ];

            function pickLayerForZoom(logic, zoom) {
                if (!logic) return null;
                const thresholds = Object.keys(logic).map(Number).filter(n => !isNaN(n)).sort((a, b) => b - a);
                for (const t of thresholds) {
                    if (zoom >= t) return logic[String(t)];
                }
                return null;
            }

            // The region whose area contains the map centre provides the layer stack. A region with
            // an outline (Germany) clips all its layers to that outline, so near its border it is
            // also stacked on top of the neighbour's layers whenever it is in view: both sides of
            // the border get their own data, and they never overlap.
            function resolveTerrainLayerKey(center, zoom, view) {
                const candidates = terrainRegionPriority.slice();
                for (const countryName in terrainData) {
                    for (const regionName in (terrainData[countryName].bounds || {})) {
                        if (!candidates.some(c => c[0] === countryName && c[1] === regionName)) {
                            candidates.push([countryName, regionName]);
                        }
                    }
                }
                // The first region containing the centre provides the main stack; every other region with
                // an outline that is in view adds its (clipped) layers too, in front or behind alike.
                let main = null;
                const overlays = [];
                for (const [countryName, regionName] of candidates) {
                    const country = terrainData[countryName];
                    if (!country || !country.bounds || !country.bounds[regionName]) continue;
                    const box = L.latLngBounds(country.bounds[regionName]);
                    const outline = country.outlines && country.outlines[regionName];
                    const picked = pickLayerForZoom(country.logic && country.logic[regionName], zoom);
                    const keys = (Array.isArray(picked) ? picked : [picked]).filter(k => k && terrainLayers[k]);
                    if (!keys.length) continue;
                    if (!main && box.contains(center) && (!outline || pointInRings(center, outline))) {
                        main = keys;
                    } else if (outline && view && box.intersects(view)) {
                        overlays.push(...keys);
                    }
                }
                const stack = [...overlays, ...(main || [])];
                return stack.filter((k, i) => stack.indexOf(k) === i);
            }

            // Ray casting with the even-odd rule over all rings (holes included); rings of [lat, lon].
            function pointInRings(latlng, rings) {
                let inside = false;
                for (const ring of rings) {
                    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
                        const [yi, xi] = ring[i], [yj, xj] = ring[j];
                        if ((yi > latlng.lat) !== (yj > latlng.lat) &&
                            latlng.lng < (xj - xi) * (latlng.lat - yi) / (yj - yi) + xi) inside = !inside;
                    }
                }
                return inside;
            }

            // Region switches from the terrain panel. Each region lists the layers that draw it; a layer
            // clipped to several regions (Brandenburg + Berlin) is cut down to the regions still on.
            let disabledTerrain = new Set();
            const layerRegionIds = {};   // layer key -> region ids it draws
            const baseIdOfLayer = {};    // layer key -> 'DE:base' etc. for a country's base relief
            const regionIndex = [];      // [{country, region}] for the status line
            function indexTerrainCatalog() {
                for (const countryName in terrainData) {
                    const d = terrainData[countryName];
                    for (const r of d.regions || []) {
                        regionIndex.push({ country: d, region: r });
                        for (const k of r.layers || []) (layerRegionIds[k] = layerRegionIds[k] || []).push(r.id);
                    }
                    if (d.base) for (const k of d.base.layers) baseIdOfLayer[k] = d.country.id + ':base';
                }
            }

            // [{key, clip}] for a resolved stack: switched-off regions removed, and from `fallbackFrom` on
            // the base relief clipped to the regions that no LiDAR layer of this stack covers.
            function planTerrainStack(keys, zoom) {
                const plan = {}, covered = new Set();
                for (const key of keys) {
                    if (baseIdOfLayer[key]) continue;
                    const all = terrainLayers[key]._clipAll;
                    const regionIds = layerRegionIds[key];
                    if (!regionIds) { plan[key] = { key, clip: all }; continue; }
                    const on = regionIds.filter(id => !disabledTerrain.has(id));
                    if (!on.length) continue;
                    const clip = all ? all.filter(c => !regionIds.includes(c) || on.includes(c)) : null;
                    if (clip && !clip.length) continue;
                    (clip || on).forEach(c => covered.add(c));
                    plan[key] = { key, clip };
                }
                for (const key of keys) {
                    if (!baseIdOfLayer[key] || disabledTerrain.has(baseIdOfLayer[key])) continue;
                    const o = terrainLayers[key].options;
                    let clip = terrainLayers[key]._clipAll;
                    if (o.fallbackFor && zoom >= (o.fallbackFrom || 0)) {
                        clip = o.fallbackFor.filter(c => !covered.has(c));
                        if (!clip.length) continue;
                    }
                    plan[key] = { key, clip };
                }
                return keys.filter(k => plan[k]).map(k => plan[k]);
            }

            // New tiles use the new clip. When it changes without a zoom change (a region switched in the
            // panel), the tiles on screen are redrawn.
            function applyLayerClip(layer, clip, zoom) {
                const id = clip ? clip.join('+') : '';
                if (layer._clipId === undefined) layer._clipId = layer._clipAll ? layer._clipAll.join('+') : '';
                if (id === layer._clipId) { layer._clipZoom = zoom; return; }
                layer.options.clipTo = clip;
                layer._clipId = id;
                if (layer._clipZoom === zoom && map.hasLayer(layer)) layer.redraw();
                layer._clipZoom = zoom;
            }

            function updateAutoTerrain() {
                if (!isTerrainAutoMode) {
                    for (const key in terrainLayers) {
                        if (map.hasLayer(terrainLayers[key])) map.removeLayer(terrainLayers[key]);
                    }
                    map.getContainer().style.filter = 'none';
                    return;
                }

                const zoom = map.getZoom();
                const center = map.getCenter();
                // Ordered finest -> coarsest; coarser layers show through where finer ones are empty.
                // Layers whose coverage is out of view stay off the map (no requests, no attribution).
                const view = map.getBounds().pad(0.25);
                const plan = planTerrainStack(resolveTerrainLayerKey(center, zoom, view), zoom).filter(p => {
                    const b = terrainLayers[p.key].options.bounds;
                    return !b || L.latLngBounds(b).intersects(view);
                });
                plan.forEach(p => applyLayerClip(terrainLayers[p.key], p.clip, zoom));
                const targetKeys = plan.map(p => p.key);

                for (const key in terrainLayers) {
                    const layer = terrainLayers[key];
                    if (targetKeys.includes(key)) {
                        if (!map.hasLayer(layer)) layer.addTo(map);
                    } else if (map.hasLayer(layer)) {
                        map.removeLayer(layer);
                    }
                }
                // Stack order: bring the coarsest to the front first so the finest ends on top.
                for (let i = targetKeys.length - 1; i >= 0; i--) {
                    terrainLayers[targetKeys[i]].bringToFront();
                }
                // Opacity is applied once to the whole pane, so stacked layers composite exactly.
                map.getPane('terrainPane').style.opacity = currentTerrainOpacity;

                const mapContainer = map.getContainer();
                let filterStyle = (zoom >= 15 && targetKeys.length) ? 'brightness(70%) contrast(120%)' : 'none';
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
                const labels = L.layerGroup();
                const regions = L.geoJSON(geoJsonData, {
                    style: { color: '#e8dcc0', weight: 1.4, opacity: 0.85, dashArray: '5 4', fillOpacity: 0, interactive: false },
                    pane: 'borderPane',
                    renderer: borderRenderer || (borderRenderer = L.canvas({ pane: 'borderPane', padding: 0.5 })),
                    onEachFeature: (feature, layer) => {
                        const props = feature.properties || {};
                        const code = regionAbbreviation(props);
                        if (!code) return;
                        const id = props.id || props.iso_3166_2;
                        const pos = regionLabelPositions[id] || layer.getBounds().getCenter();
                        labels.addLayer(L.marker(pos, {
                            interactive: false, keyboard: false, pane: 'borderPane',
                            icon: L.divIcon({ className: '', html: '<span class="region-label">' + code + '</span>', iconSize: null })
                        }));
                    }
                });
                borderLayers[layerId] = L.layerGroup([regions, labels]).addTo(map);
            };

            // Detailed borders have hundreds of thousands of vertices; canvas draws them much
            // faster than SVG while panning and zooming. Created on first use (the pane must exist).
            let borderRenderer = null;

            // Short code for a region feature, e.g. "BW" from the ISO 3166-2 id "DE-BW".
            function regionAbbreviation(props) {
                const iso = props.id || props.iso_3166_2 || '';
                const m = /^[A-Z]{2}-([A-Z0-9]{1,3})$/.exec(iso);
                if (m) return m[1];
                return props.postal || props.abbreviation || '';
            }

            // Labels whose bbox centre would land on another region (Brandenburg -> Berlin).
            const regionLabelPositions = {
                'DE-BB': [52.0, 13.6]
            };

            window.removeBorderLayer = function(layerId) {
                if (borderLayers[layerId]) {
                    map.removeLayer(borderLayers[layerId]);
                    delete borderLayers[layerId];
                }
            };

            // Which terrain layers the current view would show at each zoom level (based on the
            // map centre and the region switches), plus the visible bbox. Used by the offline tile downloader.
            window.getTerrainPlanForView = function(minZoom, maxZoom) {
                const b = map.getBounds();
                const stacks = {};
                for (let z = minZoom; z <= maxZoom; z++) {
                    // [key, clip codes] when the layer is cut to fewer regions than its definition.
                    stacks[z] = planTerrainStack(resolveTerrainLayerKey(map.getCenter(), z, b), z)
                        .map(p => (p.clip || []).join('+') === (terrainLayers[p.key]._clipAll || []).join('+') ? p.key : [p.key, p.clip]);
                }
                return { bbox: [b.getSouth(), b.getWest(), b.getNorth(), b.getEast()], zoom: map.getZoom(), stacks: stacks };
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

            const markerKindNames = { start: 'Start', ziel: 'Ziel', punkt: 'Punkt', fund: 'Fund' };
            const escapeHtml = s => String(s || '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
            window.addPermanentMarker = function(data) {
                if(data && typeof data.lat === 'number' && typeof data.lon === 'number') {
                    const kind = data.kind || 'punkt';
                    const note = data.note ? `<div style="margin-top:4px;white-space:pre-wrap">${escapeHtml(data.note)}</div>` : '';
                    const date = data.created ? ' · ' + escapeHtml(data.created.slice(0, 10)) : '';
                    const html = `<b>${escapeHtml(data.title || data.comment)}</b><br>` +
                        `<span style="color:#9198a1">${markerKindNames[kind] || kind}${date} · ${data.lat.toFixed(5)}, ${data.lon.toFixed(5)}</span>${note}`;
                    const marker = L.marker([data.lat, data.lon], {icon: icons['mk_' + kind] || icons['punkt'], zIndexOffset: 500})
                        .addTo(map).bindPopup(html, { maxWidth: 320 });
                    permanentMarkers[data.id] = marker;
                } else {
                    log(`[JS Warning] Skipping invalid permanent marker: ${JSON.stringify(data)}`);
                }
            };

            window.setTerrainAutoMode = (enabled) => { isTerrainAutoMode = enabled; updateAutoTerrain(); reportView(); };
            window.setTerrainSelection = (disabledIds) => {
                disabledTerrain = new Set(disabledIds || []);
                if (map) { updateAutoTerrain(); reportView(); }
            };
            window.setBaseLayer = (name) => {
                const layer = baseLayers[name];
                if (!layer || layer === currentBaseLayer) return;
                if (currentBaseLayer) map.removeLayer(currentBaseLayer);
                layer.addTo(map);
                layer.bringToBack();
                currentBaseLayer = layer;
                if (name === 'Roman Empire') map.addLayer(dareUtfGrid);
                else if (map.hasLayer(dareUtfGrid)) map.removeLayer(dareUtfGrid);
            };
            // Lines of the active-layers box: LiDAR, analysis, monuments, sites. Hidden ones stay chosen in the
            // panels; only their pane is switched off until clicked again.
            const activeHidden = {};
            const activePanes = { lidar: 'terrainPane', analysis: 'analysisPane', monuments: 'monumentPane' };
            const activeKinds = { lidar: 'LiDAR', analysis: 'Analyse', monuments: 'Denkmäler', sites: 'Fundstellen' };
            function applyActiveVisibility(key) {
                const hidden = !!activeHidden[key];
                if (activePanes[key]) map.getPane(activePanes[key]).style.display = hidden ? 'none' : '';
                if (key === 'sites' && sitesLayer) {
                    if (hidden && map.hasLayer(sitesLayer)) map.removeLayer(sitesLayer);
                    if (!hidden && !map.hasLayer(sitesLayer)) sitesLayer.addTo(map);
                }
            }
            const activeChips = {};
            window.toggleActive = (key) => { if (activeChips[key]) activeChips[key].onclick(); };
            window.setActiveInfo = (info) => {
                if (!activeLayersBox) return;
                activeLayersBox.innerHTML = '';
                for (const k in activeChips) delete activeChips[k];
                for (const key of ['lidar', 'analysis', 'monuments', 'sites']) {
                    const what = info[key];
                    if (!what) {
                        if (activeHidden[key]) { activeHidden[key] = false; applyActiveVisibility(key); }
                        continue;
                    }
                    // Traffic light: green = shown, yellow = on but not visible at this zoom, red = hidden.
                    const wait = what.includes('ab Zoom');
                    const chip = L.DomUtil.create('div', 'active-chip' + (wait ? ' wait' : '') + (activeHidden[key] ? ' off' : ''), activeLayersBox);
                    const tip = () => what + '\\n' + (activeHidden[key] ? 'Ausgeblendet – klicken zum Einblenden' : 'Klicken zum Ausblenden');
                    chip.title = tip();
                    chip.innerHTML = `<span class="dot"></span><span>${activeKinds[key]}</span>`;
                    chip.onclick = () => {
                        activeHidden[key] = !activeHidden[key];
                        chip.classList.toggle('off', activeHidden[key]);
                        chip.title = tip();
                        applyActiveVisibility(key);
                    };
                    activeChips[key] = chip;
                }
            };

            window.setAnalysis = (key) => {
                for (const k in analysisLayers) {
                    if (k !== key && map.hasLayer(analysisLayers[k])) map.removeLayer(analysisLayers[k]);
                }
                if (key && analysisLayers[key] && !map.hasLayer(analysisLayers[key])) analysisLayers[key].addTo(map);
            };
            window.setAnalysisOpacity = (v) => { map.getPane('analysisPane').style.opacity = v; };

            window.setMonumentLayer = (on) => {
                if (on && !map.hasLayer(monumentLayer)) monumentLayer.addTo(map);
                if (!on && map.hasLayer(monumentLayer)) map.removeLayer(monumentLayer);
            };

            // GetFeatureInfo for the clicked point (text answer fetched by the Qt side: no CORS on the server).
            const textCallbacks = {};
            window.onTextFetched = (id, text) => { if (textCallbacks[id]) { textCallbacks[id](text); delete textCallbacks[id]; } };
            function queryMonuments(e) {
                const size = map.getSize(), b = map.getBounds();
                const sw = L.CRS.EPSG3857.project(b.getSouthWest()), ne = L.CRS.EPSG3857.project(b.getNorthEast());
                const p = map.latLngToContainerPoint(e.latlng).round();
                const params = { SERVICE: 'WMS', REQUEST: 'GetFeatureInfo', VERSION: '1.3.0', LAYERS: 'bodendenkmalO',
                                 QUERY_LAYERS: 'bodendenkmalO', STYLES: '', CRS: 'EPSG:3857',
                                 BBOX: [sw.x, sw.y, ne.x, ne.y].join(','), WIDTH: size.x, HEIGHT: size.y,
                                 I: p.x, J: p.y, INFO_FORMAT: 'text/plain', FEATURE_COUNT: 5 };
                const id = 'fi_' + Math.random().toString(36).slice(2);
                textCallbacks[id] = text => {
                    const items = [];
                    let cur = null;
                    for (const line of text.split(/\\r?\\n/)) {
                        const f = /Feature (\\d+)/.exec(line);
                        if (f) { cur = { koid: f[1] }; items.push(cur); continue; }
                        const kv = /^\\s*(\\w+) = '(.*)'\\s*$/.exec(line);
                        if (kv && cur) cur[kv[1]] = kv[2];
                    }
                    if (!items.length) return;
                    const esc = s => String(s || '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
                    const html = items.map(it => `<b>Bodendenkmal ${esc(it.aktennummer)}</b><br>${esc(it.beschreibung)}` +
                        `<br><span style="color:#9198a1">${esc(it.verfahrensstand)}</span>` +
                        `<br><a href="https://geoportal.bayern.de/denkmalatlas/searchResult.html?objtyp=boden&koid=${esc(it.koid)}" target="_blank">Im Denkmal-Atlas öffnen</a>`).join('<hr>');
                    L.popup({ maxWidth: 340 }).setLatLng(e.latlng)
                        .setContent(html + '<div style="margin-top:6px;color:#d0705f;font-size:12px">Geschützt: Graben und Sondengehen nur mit Erlaubnis.</div>')
                        .openOn(map);
                };
                window.bridge.fetchText(id, MONUMENT_WMS + L.Util.getParamString(params));
            }

            // Site catalogue: coloured dots by epoch, grouped into clusters while zoomed out.
            let sitesLayer = null;
            window.setSites = (items) => {
                if (sitesLayer) map.removeLayer(sitesLayer);
                sitesLayer = null;
                if (!items.length) return;
                sitesLayer = L.markerClusterGroup({
                    chunkedLoading: true, maxClusterRadius: 48, disableClusteringAtZoom: 14, showCoverageOnHover: false,
                    iconCreateFunction: c => {
                        const n = c.getChildCount(), size = n < 100 ? 30 : n < 1000 ? 36 : 42;
                        return L.divIcon({ html: `<div class="site-cluster" style="width:${size}px;height:${size}px">${n}</div>`,
                                           className: '', iconSize: [size, size] });
                    }
                });
                const markers = items.map(s => {
                    const html = `<b>${escapeHtml(s.n)}</b><br><span style="color:#9198a1">${escapeHtml(s.t)} · ${escapeHtml(s.e)}` +
                        (s.k ? ` · ${escapeHtml(s.k)}` : '') + `</span>` + (s.d ? `<div style="margin-top:4px">${escapeHtml(s.d)}</div>` : '') +
                        `<div style="margin-top:6px"><a href="${escapeHtml(s.u)}" target="_blank">${escapeHtml(s.s)}</a></div>`;
                    return L.circleMarker([s.la, s.lo], { radius: 6, color: '#111316', weight: 1.5, fillColor: s.c, fillOpacity: 0.95 })
                        .bindPopup(html, { maxWidth: 320 });
                });
                sitesLayer.addLayers(markers);
                if (!activeHidden.sites) sitesLayer.addTo(map);
            };

            window.fitBounds = (b, maxZoom) => map.fitBounds(b, { padding: [20, 20], maxZoom: maxZoom || 20 });

            // Terrain tiles still loading, reported to the status bar at most every 200 ms.
            let loadingTimer = null, lastPending = -1;
            function scheduleLoadingReport() {
                if (loadingTimer) return;
                loadingTimer = setTimeout(() => {
                    loadingTimer = null;
                    let pending = 0;
                    for (const layer of [...Object.values(terrainLayers), ...Object.values(analysisLayers)]) {
                        if (!map.hasLayer(layer)) continue;
                        for (const id in layer._tiles) {
                            const t = layer._tiles[id];
                            if (t.current && !t.loaded) pending++;
                        }
                    }
                    if (pending !== lastPending) { lastPending = pending; window.bridge.onTerrainLoading(pending); }
                }, 200);
            }

            // Which region the map centre is in and what terrain data shows there.
            function describeHere() {
                const c = map.getCenter();
                for (const { country, region } of regionIndex) {
                    const rings = country.outlines && country.outlines[region.id];
                    const inside = rings ? pointInRings(c, rings)
                                         : region.bounds && L.latLngBounds(region.bounds).contains(c);
                    if (!inside) continue;
                    if (!isTerrainAutoMode) return region.name;
                    const baseOn = country.base && !disabledTerrain.has(country.country.id + ':base');
                    const base = baseOn ? `Grundrelief ${country.base.resolution} (${country.base.source})` : 'kein Gelände gewählt';
                    if (!(region.layers || []).length) return `${region.name} · ${base}`;
                    if (disabledTerrain.has(region.id)) return `${region.name} · LiDAR aus · ${base}`;
                    const shown = region.layers.some(k => map.hasLayer(terrainLayers[k]));
                    return `${region.name} · ` + (shown ? `LiDAR ${region.resolution} (${region.source})` : `${base}, LiDAR ab höherem Zoom`);
                }
                for (const countryName in terrainData) {
                    const d = terrainData[countryName];
                    const outline = d.outlines && d.outlines[countryName];
                    const box = d.bounds && d.bounds[countryName];
                    if ((outline && pointInRings(c, outline)) || (!outline && box && L.latLngBounds(box).contains(c))) {
                        const baseOn = d.base && !disabledTerrain.has(d.country.id + ':base');
                        return d.country.name + (baseOn ? ` · Grundrelief ${d.base.resolution} (${d.base.source})` : '');
                    }
                }
                return '';
            }

            function reportView() {
                if (!map || !window.bridge) return;
                const b = map.getBounds(), c = map.getCenter();
                window.bridge.onViewChanged(JSON.stringify({
                    zoom: map.getZoom(),
                    center: [c.lat, c.lng],
                    bounds: [[b.getSouth(), b.getWest()], [b.getNorth(), b.getEast()]],
                    here: describeHere()
                }));
            }
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

            // Route of the navigator: dark casing under a brass line, fitted into view.
            let routeLayer = null;
            window.showRoute = (latlngs) => {
                window.clearRoute();
                routeLayer = L.layerGroup([
                    L.polyline(latlngs, { color: '#111316', weight: 8, opacity: 0.7, interactive: false, pane: 'routePane' }),
                    L.polyline(latlngs, { color: '#d4a24c', weight: 4.5, opacity: 0.95, interactive: false, pane: 'routePane' })
                ]).addTo(map);
                map.fitBounds(L.latLngBounds(latlngs), { padding: [40, 40] });
                map.attributionControl.addAttribution('Routing &copy; OpenStreetMap / FOSSGIS');
            };
            window.clearRoute = () => {
                if (routeLayer) { map.removeLayer(routeLayer); routeLayer = null; }
                map.attributionControl.removeAttribution('Routing &copy; OpenStreetMap / FOSSGIS');
            };
            window.addSearchMarker = (lat, lon, popupText) => {
                if (searchMarker) { map.removeLayer(searchMarker); }
                searchMarker = L.circleMarker([lat, lon], { radius: 7, color: '#111316', weight: 2, fillColor: '#e6e1d6', fillOpacity: 1 })
                    .addTo(map).bindPopup(popupText).openPopup();
            };
        """

    def load_map(self):
        self.web_view.setUrl(QUrl.fromLocalFile(os.path.abspath(HTML_MAP_FILE)))

    def run_js(self, script, callback=None):
        if callback:
            self.web_view.page().runJavaScript(script, callback)
        else:
            self.web_view.page().runJavaScript(script)

    def center_on_location(self, lat, lon, popup_text, zoom=13):
        self.run_js(f"window.setView({lat}, {lon}, {zoom});")
        self.run_js(f"window.addSearchMarker({lat}, {lon}, {json.dumps(popup_text.replace(chr(10), '<br>'))});")

    def add_permanent_marker(self, marker_data):
        self.run_js(f"window.addPermanentMarker({json.dumps(marker_data)});")

    def remove_permanent_marker(self, marker_id):
        self.run_js(f"window.removePermanentMarker('{marker_id}');")

    def update_all_markers(self, markers_list):
        self.run_js(f"window.updateAllMarkers({json.dumps(markers_list)});")

    def toggle_poi_layer(self, layer_key, is_visible):
        self.run_js(f"window.togglePoiLayerVisibility('{layer_key}', {str(is_visible).lower()});")