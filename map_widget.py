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
                .region-label {{
                    position: absolute; transform: translate(-50%, -50%); white-space: nowrap;
                    background: rgba(255, 255, 255, 0.75); border: 1px solid #008000; border-radius: 3px;
                    padding: 1px 4px; font: bold 12px sans-serif; color: #005000;
                }}
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
                            // Keep more off-screen tiles and skip the intermediate zoom levels while a zoom
                            // animation runs: the WMS servers are slow, so every saved request counts.
                            let layerOptions = {{ keepBuffer: 4, updateWhenZooming: false, ...layerInfo.options, ...paneOption }};
                            if (tileProxy && tileProxy.ports && tileProxy.ports.length) {{
                                // Local cache proxy builds the upstream request itself (see tile_cache.py).
                                // The ports act like tile-server subdomains to get around the browser's
                                // per-host connection limit.
                                const tileTemplate = 'http://' + tileProxy.host + ':{{s}}/tile/' + layerKey + '/{{z}}/{{x}}/{{y}}.png';
                                const proxyOptions = {{ ...layerOptions, subdomains: tileProxy.ports.map(String) }};
                                if (layerInfo.type === 'wms_crop') {{
                                    terrainLayers[layerKey] = L.gridLayer.wmsCropped(tileTemplate, {{ ...proxyOptions, tileTemplate: true }});
                                }} else {{
                                    terrainLayers[layerKey] = L.tileLayer(tileTemplate, proxyOptions);
                                }}
                            }} else if (layerInfo.type === 'arcgis_image') {{
                                terrainLayers[layerKey] = L.tileLayer.arcgisImage(layerInfo.url, layerOptions);
                            }} else if (layerInfo.type === 'wms_crop') {{
                                terrainLayers[layerKey] = L.gridLayer.wmsCropped(layerInfo.url, layerOptions);
                            }} else if (layerInfo.url.includes('{{z}}')) {{
                                terrainLayers[layerKey] = L.tileLayer(layerInfo.url, layerOptions);
                            }} else {{
                                terrainLayers[layerKey] = L.tileLayer.wms(layerInfo.url, layerOptions);
                            }}
                            // Added to the map on demand by updateAutoTerrain().
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

            // WMS layer that requests each tile `cropLeft` pixels wider than needed and draws it
            // shifted left onto a canvas, cutting off a watermark strip some servers paint along
            // the left edge of every image (e.g. Regione Toscana's Geoscopio WMS).
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
                },
                createTile: function(coords, done) {
                    const tile = document.createElement('canvas');
                    const size = this.getTileSize();
                    tile.width = size.x; tile.height = size.y;
                    const crop = this._cropLeft;
                    const nwPoint = coords.scaleBy(size).subtract([crop, 0]);
                    const sePoint = coords.scaleBy(size).add(size);
                    const nw = L.CRS.EPSG3857.project(this._map.unproject(nwPoint, coords.z));
                    const se = L.CRS.EPSG3857.project(this._map.unproject(sePoint, coords.z));
                    const params = { ...this._wmsParams, width: size.x + crop, height: size.y, bbox: [nw.x, se.y, se.x, nw.y].join(',') };
                    const img = new Image();
                    const whiteToAlpha = this.options.whiteToAlpha;
                    if (whiteToAlpha) img.crossOrigin = 'anonymous';
                    img.onload = () => {
                        const ctx = tile.getContext('2d');
                        ctx.drawImage(img, -crop, 0);
                        // Some services paint everything outside their state opaque white.
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
                        done(null, tile);
                    };
                    img.onerror = () => done(new Error('tile load failed'), tile);
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

            function resolveTerrainLayerKey(center, zoom) {
                const candidates = terrainRegionPriority.slice();
                for (const countryName in terrainData) {
                    for (const regionName in (terrainData[countryName].bounds || {})) {
                        if (!candidates.some(c => c[0] === countryName && c[1] === regionName)) {
                            candidates.push([countryName, regionName]);
                        }
                    }
                }
                for (const [countryName, regionName] of candidates) {
                    const country = terrainData[countryName];
                    if (!country || !country.bounds || !country.bounds[regionName]) continue;
                    if (!L.latLngBounds(country.bounds[regionName]).contains(center)) continue;
                    // Optional outline for regions a rectangle fits badly (Germany vs. its neighbours).
                    const outline = country.outlines && country.outlines[regionName];
                    if (outline && !outline.some(ring => pointInRing(center, ring))) continue;
                    const picked = pickLayerForZoom(country.logic && country.logic[regionName], zoom);
                    const keys = (Array.isArray(picked) ? picked : [picked]).filter(k => k && terrainLayers[k]);
                    if (keys.length) return keys;
                }
                return [];
            }

            // Ray casting; ring is a list of [lat, lon].
            function pointInRing(latlng, ring) {
                let inside = false;
                for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
                    const [yi, xi] = ring[i], [yj, xj] = ring[j];
                    if ((yi > latlng.lat) !== (yj > latlng.lat) &&
                        latlng.lng < (xj - xi) * (latlng.lat - yi) / (yj - yi) + xi) inside = !inside;
                }
                return inside;
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
                const targetKeys = resolveTerrainLayerKey(center, zoom).filter(k => {
                    const b = terrainLayers[k].options.bounds;
                    return !b || L.latLngBounds(b).intersects(view);
                });

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
                    style: { color: '#008000', weight: 2, fillOpacity: 0.05, interactive: false },
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
            // map centre), plus the visible bbox. Used by the offline tile downloader.
            window.getTerrainPlanForView = function(minZoom, maxZoom) {
                const b = map.getBounds();
                const stacks = {};
                for (let z = minZoom; z <= maxZoom; z++) {
                    stacks[z] = resolveTerrainLayerKey(map.getCenter(), z);
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