import sys
import io
import re
import urllib.parse
import json
import os
import uuid
import webbrowser
import datetime
import requests

# This must be set before the QApplication is instantiated.
os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "8888"

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QLabel, QMessageBox, QStatusBar, QTextEdit, QComboBox,
    QDialog, QDialogButtonBox, QFormLayout, QMenu, QSpinBox, QProgressDialog, QFileDialog,
    QStackedWidget, QToolButton, QSplitter, QButtonGroup, QScrollArea
)
from PyQt6.QtGui import QCursor, QFont, QKeySequence, QPixmap, QShortcut
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QSettings, QSize, QTimer


# Local Imports
from map_widget import MapWidget
from assets import border_fetcher
from assets.countries.europe import germany as germany_assets
from assets.countries.europe import austria as austria_assets
from assets.countries.europe import switzerland as switzerland_assets
from assets.countries.europe import italy as italy_assets
import process_guard
import dem_analysis
from tile_cache import TileCacheServer, TileDownloadThread, plan_download
from ui import icons, theme
from ui.panels import COUNTRY_NAMES_DE, AnalysisPanel, FindsPanel, LidarSection, MapPanel, NavigatorPanel, OfflinePanel, SitesPanel
from ui.marker_dialog import MARKER_KINDS, MarkerDialog, marker_icon
from ui.widgets import BusyIndicator, icon_button
from ui.workers import GeocodeThread, Locator, RouteThread
from ui import sites as site_catalogue

COUNTRY_MODULES = {
    'germany': germany_assets,
    'austria': austria_assets,
    'switzerland': switzerland_assets,
    'italy': italy_assets,
}


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


class HeightThread(QThread):
    """Terrain height at one point from the cached height tiles (zoom 15, ~2.4 m pixels)."""
    ready = pyqtSignal(object)   # float metres or None

    def __init__(self, source, lat, lon):
        super().__init__()
        self.source, self.lat, self.lon = source, lat, lon

    def run(self):
        import math
        try:
            z = 15
            n = 2 ** z
            fx = (self.lon + 180) / 360 * n
            fy = (1 - math.asinh(math.tan(math.radians(self.lat))) / math.pi) / 2 * n
            tile = self.source.tile(z, int(fx), int(fy))
            if tile is None:
                self.ready.emit(None)
                return
            size = tile.shape[0]
            h = float(tile[min(int((fy % 1) * size), size - 1), min(int((fx % 1) * size), size - 1)])
            self.ready.emit(h if -500 < h < 9000 else None)
        except Exception:
            self.ready.emit(None)


class TextFetcherThread(QThread):
    """Plain-text GET for the page (e.g. WMS GetFeatureInfo of servers without CORS)."""
    done = pyqtSignal(str, str)  # request_id, text ('' on error)

    def __init__(self, request_id, url):
        super().__init__()
        self.request_id = request_id
        self.url = url

    def run(self):
        try:
            r = requests.get(self.url, timeout=15)
            r.raise_for_status()
            try:
                text = r.content.decode('utf-8')
            except UnicodeDecodeError:
                text = r.content.decode('cp1252', errors='replace')
        except requests.RequestException:
            text = ''
        self.done.emit(self.request_id, text)


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
            if self.is_running: self.data_ready.emit(self.admin_level, self.country_name or '', data)
        except Exception as e:
            if self.is_running: self.error.emit(str(e))

    def stop(self):
        self.is_running = False


class CacheStatsThread(QThread):
    """Walks the tile cache folder (can take a while once it holds many tiles)."""
    ready = pyqtSignal(dict)

    def __init__(self, cache):
        super().__init__()
        self.cache = cache

    def run(self):
        self.ready.emit(self.cache.summary())


def _rings_bounds(rings):
    lats = [p[0] for r in rings for p in r]
    lons = [p[1] for r in rings for p in r]
    return [[min(lats), min(lons)], [max(lats), max(lons)]]


def build_terrain_data():
    """Terrain layers, regions and outlines of every country module, for the page and the cache."""
    data = {}
    for key, module in COUNTRY_MODULES.items():
        data[key] = {
            'layers': module.terrain_layers,
            'bounds': module.bounds,
            'logic': module.layer_logic,
            'outlines': getattr(module, 'outlines', {}),
            'country': getattr(module, 'country', {'id': key, 'name': key.title()}),
            'regions': getattr(module, 'regions', []),
            'base': getattr(module, 'base_relief', None),
        }
    data['analysis'] = {'layers': ANALYSIS_LAYERS, 'bounds': {}, 'logic': {}, 'outlines': {},
                        'country': {'id': 'ANALYSIS', 'name': 'Analyse'}, 'regions': [], 'base': None}
    return data


# Analysis views (Analyse tab), computed locally from Mapterhorn height tiles. 512 px tiles from zoom 13;
# the heights end at their zoom 16 (= app zoom 17), above that the map enlarges.
ANALYSIS_LAYERS = {
    f'ana_{kind}': {
        'type': 'dem_analysis',
        'url': 'https://tiles.mapterhorn.com/{z}/{x}/{y}.webp',
        'options': {'analysis': kind, 'tileSize': 512, 'minZoom': 13, 'maxZoom': 20, 'maxNativeZoom': 17,
                    'attribution': 'Höhen &copy; Mapterhorn (amtliche DGM), Analyse berechnet'}
    } for kind in ('combo', 'lrm', 'multi', 'svf', 'slope')
}


def build_terrain_catalog(terrain_data):
    """Countries and regions for the terrain panel, each with a bounding box."""
    catalog = []
    for key, d in terrain_data.items():
        if key == 'analysis':
            continue
        outlines = d['outlines']
        regions = []
        for r in d['regions']:
            bounds = r.get('bounds') or (_rings_bounds(outlines[r['id']]) if r['id'] in outlines else None)
            regions.append({**r, 'bounds': bounds})
        country_bounds = (_rings_bounds(outlines[key]) if key in outlines
                          else d['bounds'].get(key) or next(iter(d['bounds'].values()), None))
        catalog.append({'key': key, 'id': d['country']['id'], 'name': d['country']['name'],
                        'bounds': country_bounds, 'base': d['base'], 'regions': regions})
    return catalog


class TreasureHunterApp(QMainWindow):
    """
    Main application window for the Treasure Hunter app.
    """
    request_add_marker_dialog = pyqtSignal(float, float)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Treasure Hunter")
        self.setWindowIcon(icons.icon('compass', theme.ACCENT, size=32))
        self.setGeometry(100, 100, 1400, 900)
        # TREASURE_HUNTER_SETTINGS lets test runs keep their own settings instead of the user's.
        self.settings = QSettings(os.environ.get("TREASURE_HUNTER_SETTINGS", "TreasureHunter"), "TreasureHunter")
        self.geocode_thread = None
        self.locator = None
        self.markers = {}
        self.markers_file = os.environ.get("TREASURE_HUNTER_MARKERS", "markers.json")  # tests use their own file
        self.current_location = None       # (lat, lon, label) from the search or own position
        self.route_thread = None
        self.last_route = None             # {'mode', 'points', 'line', 'distance', 'duration'}
        self.border_fetcher_threads = []
        self.url_fetcher_threads = {}
        self.tile_cache_server = None
        self.tile_download_thread = None
        self.download_progress = None
        self.cache_stats_thread = None

        self.init_ui()
        self.request_add_marker_dialog.connect(self.show_add_marker_dialog)
        self.add_log("Anwendung gestartet.")
        self.add_log("Entwicklerkonsole aktiv auf http://localhost:8888")
        self.load_markers()

    # ------------------------------------------------------------------ layout

    def init_ui(self):
        # The log exists first: starting the tile cache already writes to it.
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setObjectName("logConsole")

        terrain_data = build_terrain_data()
        # Local tile cache: all terrain tiles are fetched through it and kept on disk
        # (tile_cache/), so visited areas also work offline.
        tile_proxy = None
        try:
            cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tile_cache")
            self.tile_cache_server = TileCacheServer(terrain_data, cache_dir)
            self.tile_cache_server.start()
            tile_proxy = self.tile_cache_server.proxy_info
            self.add_log(f"Gelände-Kachel-Cache aktiv (Ports {', '.join(map(str, tile_proxy['ports']))}, Ordner: {cache_dir})")
        except Exception as e:
            self.tile_cache_server = None
            self.add_log(f"Kachel-Cache konnte nicht gestartet werden, Kacheln werden direkt geladen: {e}")
        self.map_widget = MapWidget(terrain_data, tile_proxy=tile_proxy)
        self.map_widget.bridge.log_requested.connect(self.add_log)
        self.map_widget.bridge.map_ready.connect(self.on_map_ready)
        self.map_widget.bridge.map_right_clicked.connect(self.handle_map_right_click)
        self.map_widget.bridge.fetch_url_requested.connect(self.fetch_url_from_js)
        self.map_widget.bridge.fetch_text_requested.connect(self.fetch_text_from_js)
        self.map_widget.bridge.view_changed.connect(self.on_view_changed)
        self.map_widget.bridge.mouse_moved.connect(self.on_mouse_moved)
        self.map_widget.bridge.terrain_loading.connect(self.on_terrain_loading)

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self.create_header())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        outer.addLayout(body, 1)

        catalog = build_terrain_catalog(terrain_data)
        s = self.settings
        self.terrain_panel = LidarSection(
            catalog,
            enabled_ids=json.loads(s.value("terrain/enabled_ids", "[]")),
            opacity=int(s.value("terrain/opacity", 100)))
        self.terrain_panel.opacity_changed.connect(self.set_terrain_opacity)
        self.terrain_panel.selection_changed.connect(self.set_terrain_selection)
        self.terrain_panel.zoom_requested.connect(
            lambda b: self.map_widget.run_js(f"window.fitBounds({json.dumps(b)});"))

        self.map_panel = MapPanel(border_fetcher.get_country_list(), self.terrain_panel,
                                  base_map=s.value("map/base", "OpenStreetMap"),
                                  favorites=json.loads(s.value("borders/favorites", "[]")))
        self.map_panel.favorites_changed.connect(lambda favs: self.settings.setValue("borders/favorites", json.dumps(favs)))
        self.map_panel.base_map_changed.connect(self.set_base_map)
        self.map_panel.countries_toggled.connect(self.toggle_country_borders)
        self.map_panel.region_borders_toggled.connect(self.toggle_region_borders)

        self.sites_panel = SitesPanel(monuments_on=s.value("map/monuments", "false") == "true")
        self.sites_panel.monuments_toggled.connect(self.set_monuments)
        self.sites, per_source = site_catalogue.load_sites()
        self.sites_panel.set_catalogue(site_catalogue.counts(self.sites), site_catalogue.EPOCHS, site_catalogue.TYPES,
                                       site_catalogue.CULTURES, per_source, site_catalogue.EPOCH_COLORS)
        # Typing in the search or ticking several boxes quickly sends one update, not one per change.
        self.sites_timer = QTimer(self)
        self.sites_timer.setSingleShot(True)
        self.sites_timer.setInterval(250)
        self.sites_timer.timeout.connect(self.update_sites_on_map)
        self.sites_panel.filter_changed.connect(self.sites_timer.start)

        self.finds_panel = FindsPanel()
        self.navigator_panel = NavigatorPanel(s.value("nav/mode", "foot"))
        for panel in (self.finds_panel, self.navigator_panel):
            panel.center_requested.connect(self.center_on_marker)
            panel.edit_requested.connect(self.edit_marker)
            panel.delete_requested.connect(self.delete_marker)
        self.navigator_panel.route_requested.connect(self.compute_route)
        self.navigator_panel.phone_requested.connect(self.send_route_to_phone)
        self.navigator_panel.google_requested.connect(lambda mode, via: self._open_google(mode, via))
        self.navigator_panel.gpx_requested.connect(self.save_route_gpx)
        self.navigator_panel.clear_requested.connect(self.clear_route)

        self.analysis_panel = AnalysisPanel(int(s.value("analysis/opacity", 85)), self.terrain_panel.opacity.value(),
                                            view=s.value("analysis/view", ""))
        self.analysis_panel.view_changed.connect(self.set_analysis_view)
        self.analysis_panel.opacity_changed.connect(self.set_analysis_opacity)
        # LiDAR mirror in the analysis tab: ticks and opacity go to the main list, and back.
        self.analysis_panel.lidar.toggled.connect(self._toggle_lidar_from_analysis)
        self.analysis_panel.lidar.opacity_changed.connect(self.terrain_panel.opacity.setValue)
        self.terrain_panel.opacity.valueChanged.connect(self.analysis_panel.lidar.set_opacity)
        self._view_bounds = None

        self.offline_panel = OfflinePanel()
        self.offline_panel.download_requested.connect(self.start_tile_download_dialog)
        self.offline_panel.offline_toggled.connect(self.toggle_offline_mode)
        self.offline_panel.open_folder_requested.connect(self.open_cache_folder)
        self.offline_panel.details_requested.connect(self.show_cache_info)
        self.offline_panel.refresh_requested.connect(self.refresh_cache_stats)

        self.panel_stack = QStackedWidget()
        self.panel_stack.setObjectName("sidePanel")
        self.panel_stack.setMinimumWidth(300)
        self.panel_stack.setMaximumWidth(640)
        panels = [('map', 'Karte', self.map_panel),
                  ('sites', 'Fundstellen', self.sites_panel), ('pin', 'Meine Funde', self.finds_panel),
                  ('route', 'Navigator', self.navigator_panel), ('analysis', 'Analyse', self.analysis_panel),
                  ('offline', 'Offline', self.offline_panel)]
        body.addWidget(self.create_rail(panels))
        for _icon, _label, panel in panels:
            # Scrolls when the window is too low for all sections (the borders sit below the LiDAR list).
            scroll = QScrollArea()
            scroll.setWidget(panel)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.panel_stack.addWidget(scroll)

        self.log_panel = QWidget()
        self.log_panel.setObjectName("logPanel")
        log_layout = QVBoxLayout(self.log_panel)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.addWidget(self.log_console)
        self.log_panel.hide()
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(1)
        splitter.addWidget(self.map_widget)
        splitter.addWidget(self.log_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setSizes([700, 170])
        # The side panel can be dragged wider (handle between panel and map); the width is remembered.
        self.main_split = QSplitter(Qt.Orientation.Horizontal)
        self.main_split.setHandleWidth(4)
        self.main_split.setChildrenCollapsible(False)
        self.main_split.addWidget(self.panel_stack)
        self.main_split.addWidget(splitter)
        self.main_split.setStretchFactor(1, 1)
        width = int(self.settings.value("ui/panel_width", 330))
        self.main_split.setSizes([width, 1200])
        self.main_split.splitterMoved.connect(
            lambda *_: self.settings.setValue("ui/panel_width", self.panel_stack.width()) if self.panel_stack.isVisible() else None)
        body.addWidget(self.main_split, 1)

        self.create_status_bar()
        self.rail_group.buttons()[0].setChecked(True)
        self.create_shortcuts()

    def create_header(self):
        header = QWidget()
        header.setObjectName("header")
        header.setFixedHeight(52)
        lay = QHBoxLayout(header)
        lay.setContentsMargins(16, 0, 12, 0)
        lay.setSpacing(10)
        mark = QLabel()
        mark.setPixmap(icons.pixmap('compass', theme.ACCENT, 24, 1.6))
        lay.addWidget(mark)
        title = QLabel("TREASURE HUNTER")
        title.setObjectName("appTitle")
        lay.addWidget(title)
        lay.addSpacing(28)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchBox")
        self.search_input.setPlaceholderText("Ort, Adresse oder Koordinaten (48.40, 9.99)")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.addAction(icons.icon('search', theme.TEXT_FAINT, size=15), QLineEdit.ActionPosition.LeadingPosition)
        self.search_input.returnPressed.connect(self.search_location)
        self.search_input.setMaximumWidth(460)
        lay.addWidget(self.search_input, 1)
        locate = QToolButton()
        locate.setObjectName("locateButton")
        locate.setText("Mein Standort")
        locate.setIcon(icons.icon('locate', theme.TEXT, size=16))
        locate.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        locate.setCursor(Qt.CursorShape.PointingHandCursor)
        locate.setToolTip("Eigenen Standort ermitteln und dorthin springen (Windows-Ortung, sonst ungefähr per IP)")
        locate.clicked.connect(self.determine_current_location)
        lay.addWidget(locate)
        lay.addSpacing(16)
        self.busy = BusyIndicator()
        lay.addWidget(self.busy)
        lay.addStretch()

        more = icon_button('more', "Mehr")
        more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        more.setStyleSheet("QToolButton::menu-indicator { image: none; }")
        menu = QMenu(more)
        menu.addAction("Log anzeigen", lambda: self.log_button.toggle())
        menu.addAction("Entwicklerwerkzeuge der Karte öffnen", self.open_remote_debugger)
        more.setMenu(menu)
        lay.addWidget(more)
        return header

    def create_rail(self, panels):
        rail = QWidget()
        rail.setObjectName("rail")
        rail.setFixedWidth(82)
        lay = QVBoxLayout(rail)
        lay.setContentsMargins(5, 6, 6, 6)   # selected button keeps clear of the separator line
        lay.setSpacing(3)
        self.rail_group = QButtonGroup(self)
        self.rail_group.setExclusive(False)
        for index, (icon_name, label, _panel) in enumerate(panels):
            btn = QToolButton()
            btn.setText(label)
            btn.setIcon(icons.icon(icon_name, theme.TEXT_FAINT, theme.ACCENT, 22))
            btn.setIconSize(QSize(22, 22))
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            btn.setCheckable(True)
            btn.setFixedWidth(71)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, i=index: self.on_rail_clicked(i, checked))
            self.rail_group.addButton(btn, index)
            lay.addWidget(btn)
        lay.addStretch()
        return rail

    def create_shortcuts(self):
        """Alt+1..6 tabs, Alt+L / Alt+A / Alt+D hide or show LiDAR / analysis / monuments, Ctrl+F search."""
        for i, btn in enumerate(self.rail_group.buttons()):
            btn.setToolTip(f"{btn.text()}  (Alt+{i + 1})")
            QShortcut(QKeySequence(f"Alt+{i + 1}"), self, activated=lambda i=i: self.rail_group.button(i).click())
        for key, layer in (("Alt+L", "lidar"), ("Alt+A", "analysis"), ("Alt+D", "monuments"), ("Alt+F", "sites")):
            QShortcut(QKeySequence(key), self, activated=lambda l=layer: self.map_widget.run_js(f"window.toggleActive('{l}');"))
        QShortcut(QKeySequence("Ctrl+F"), self, activated=lambda: (self.search_input.setFocus(), self.search_input.selectAll()))

    def on_rail_clicked(self, index, checked):
        # Clicking the open panel's button again collapses the side panel (more room for the map).
        for i, btn in enumerate(self.rail_group.buttons()):
            if i != index:
                btn.setChecked(False)
        self.panel_stack.setVisible(checked)
        if checked:
            self.panel_stack.setCurrentIndex(index)
            if self.panel_stack.currentWidget().widget() is self.offline_panel:
                self.refresh_cache_stats()

    def create_status_bar(self):
        bar = QStatusBar(self)
        bar.setSizeGripEnabled(False)
        self.setStatusBar(bar)
        self.coords_label = QToolButton()
        self.coords_label.setText("–")
        self.coords_label.setObjectName("coords")
        self.coords_label.setToolTip("Position unter dem Mauszeiger – klicken zum Kopieren")
        self.coords_label.clicked.connect(self.copy_cursor_coordinates)
        self.height_label = QLabel("")
        self.height_label.setToolTip("Geländehöhe unter dem Mauszeiger (Mapterhorn, amtliche DGM)")
        self._cursor = None
        self._heights = None
        self._height_thread = None
        self.height_timer = QTimer(self)
        self.height_timer.setSingleShot(True)
        self.height_timer.setInterval(250)
        self.height_timer.timeout.connect(self.lookup_height)
        self.zoom_label = QLabel("Zoom –")
        self.here_label = QLabel("")
        self.here_label.setToolTip("Gelände-Datenquelle in der Kartenmitte")
        self.loading_label = QLabel("")
        bar.addWidget(self.coords_label)
        bar.addWidget(self.height_label)
        bar.addWidget(self.zoom_label)
        bar.addWidget(self.here_label, 1)
        bar.addPermanentWidget(self.loading_label)
        self.log_button = QToolButton()
        self.log_button.setText("Log")
        self.log_button.setIcon(icons.icon('log', theme.TEXT_MUTED, theme.TEXT, 14))
        self.log_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.log_button.setCheckable(True)
        self.log_button.toggled.connect(self.log_panel.setVisible)
        bar.addPermanentWidget(self.log_button)

    # ------------------------------------------------------------------ map events

    def on_map_ready(self):
        self.add_log("[JS] Karte ist bereit.")
        s = self.settings
        view = s.value("map/view")
        if view:
            try:
                lat, lon, zoom = json.loads(view)
                self.map_widget.run_js(f"window.setView({lat}, {lon}, {zoom});")
            except (ValueError, TypeError):
                pass
        self.set_base_map(s.value("map/base", "OpenStreetMap"))
        self.draw_all_markers_on_map()
        self.map_widget.run_js(f"window.setTerrainSelection({json.dumps(self.terrain_panel.disabled_ids())});")
        self.set_terrain_opacity(self.terrain_panel.opacity.value())
        self.set_analysis_opacity(self.analysis_panel.opacity.value())
        if self.analysis_panel.current_view():
            self.set_analysis_view(self.analysis_panel.current_view())
        self.update_active_info()
        if self.sites_panel.monuments.isChecked():
            self.set_monuments(True)
        # The overlay is always on; which layers it shows is decided only by the LiDAR selection.
        self.map_widget.run_js("window.setTerrainAutoMode(true);")

    def on_view_changed(self, payload):
        try:
            view = json.loads(payload)
        except ValueError:
            return
        self.zoom_label.setText(f"Zoom {view['zoom']}")
        if getattr(self, '_zoom', None) != view['zoom']:
            self._zoom = view['zoom']
            self.update_active_info()
        self.here_label.setText(view.get('here') or '')
        self.terrain_panel.set_view_bounds(view['bounds'])
        self._view_bounds = view['bounds']
        self.update_lidar_here()
        lat, lon = view['center']
        self.settings.setValue("map/view", json.dumps([round(lat, 5), round(lon, 5), view['zoom']]))

    def on_mouse_moved(self, lat, lon):
        self._cursor = (lat, lon)
        self.coords_label.setText(f"{lat:.5f}, {lon:.5f}")
        self.height_timer.start()   # looked up once the mouse rests

    def copy_cursor_coordinates(self):
        if self._cursor:
            text = f"{self._cursor[0]:.6f}, {self._cursor[1]:.6f}"
            QApplication.clipboard().setText(text)
            self.statusBar().showMessage(f"Koordinaten kopiert: {text}", 4000)

    def lookup_height(self):
        if not self._cursor or (self._height_thread and self._height_thread.isRunning()):
            return
        if self._heights is None:
            self._heights = dem_analysis.HeightSource(
                ANALYSIS_LAYERS['ana_combo']['url'],
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "tile_cache", "_heights"), requests.Session())
        self._height_thread = HeightThread(self._heights, *self._cursor)
        self._height_thread.ready.connect(
            lambda h: self.height_label.setText(f"Höhe {h:,.0f} m".replace(',', '.') if h is not None else ""))
        self._height_thread.start()

    def on_terrain_loading(self, pending):
        if pending > 0:
            self.busy.start('tiles', f"Gelände lädt ({pending} Kacheln)")
        else:
            self.busy.stop('tiles')

    # ------------------------------------------------------------------ terrain


    def set_terrain_opacity(self, value):
        self.settings.setValue("terrain/opacity", value)
        self.map_widget.run_js(f"window.setTerrainOpacity({value / 100.0});")

    def update_lidar_here(self):
        """Rows of the LiDAR mirror in the analysis tab: the regions (and base reliefs) in view."""
        view = self._view_bounds
        rows = []
        for item in self.terrain_panel._checkable_items():
            b = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if view and b and (b[0][0] > view[1][0] or b[1][0] < view[0][0] or b[0][1] > view[1][1] or b[1][1] < view[0][1]):
                continue
            rid = item.data(0, Qt.ItemDataRole.UserRole)
            label = f"Grundrelief {item.parent().text(0)}" if rid.endswith(':base') else item.text(0)
            rows.append((rid, label, item.text(1), item.foreground(1).color().name(),
                         item.checkState(0) == Qt.CheckState.Checked))
        self.analysis_panel.lidar.set_rows(rows)

    def _toggle_lidar_from_analysis(self, rid, on):
        for item in self.terrain_panel._checkable_items():
            if item.data(0, Qt.ItemDataRole.UserRole) == rid:
                item.setCheckState(0, Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)

    def update_active_info(self):
        """Lines of the box under the zoom buttons: what is switched on right now."""
        names = []
        for item in self.terrain_panel._checkable_items():
            if item.checkState(0) == Qt.CheckState.Checked:
                parent = item.parent().text(0)
                names.append(f"Grundrelief {parent}" if item.data(0, Qt.ItemDataRole.UserRole).endswith(':base')
                             else item.text(0))
        lidar = ', '.join(names) if len(names) <= 3 else f"{len(names)} Regionen ({', '.join(names[:2])} …)"
        btn = self.analysis_panel.group.checkedButton()
        analysis = btn.text() if btn and btn.property('view') else ''
        shown = self.sites_panel.shown.text()
        zoom = getattr(self, '_zoom', 20)
        if lidar and zoom < 9:
            lidar += ' – ab Zoom 9 sichtbar'
        analysis = analysis.replace(' (empfohlen)', '')
        if analysis and zoom < 13:
            analysis += ' – ab Zoom 13 sichtbar'
        info = {'lidar': lidar, 'analysis': analysis,
                'monuments': 'Bodendenkmäler Bayern' if self.sites_panel.monuments.isChecked() else '',
                'sites': shown.replace(' auf der Karte', '') if shown else ''}
        self.map_widget.run_js(f"window.setActiveInfo({json.dumps(info, ensure_ascii=False)});")

    def set_terrain_selection(self, enabled_ids):
        self.settings.setValue("terrain/enabled_ids", json.dumps(enabled_ids))
        self.update_active_info()
        # Deferred: the change may come from a tick in the mirror list itself, which must not be rebuilt
        # while Qt is still inside that item's change signal.
        QTimer.singleShot(0, self.update_lidar_here)
        # The page works with the switched-off ids: layers it does not know from the panel stay on.
        self.map_widget.run_js(f"window.setTerrainSelection({json.dumps(self.terrain_panel.disabled_ids())});")

    def set_monuments(self, on):
        self.settings.setValue("map/monuments", "true" if on else "false")
        self.map_widget.run_js(f"window.setMonumentLayer({str(on).lower()});")
        self.update_active_info()

    def set_analysis_view(self, kind):
        self.settings.setValue("analysis/view", kind)
        self.map_widget.run_js(f"window.setAnalysis({json.dumps('ana_' + kind if kind else None)});")
        self.update_active_info()

    def set_analysis_opacity(self, value):
        self.settings.setValue("analysis/opacity", value)
        self.map_widget.run_js(f"window.setAnalysisOpacity({value / 100.0});")

    def update_sites_on_map(self):
        chosen = site_catalogue.select(self.sites, self.sites_panel.selected_pairs(),
                                       self.sites_panel.culture_key(), self.sites_panel.search.text())
        self.sites_panel.set_shown(len(chosen))
        self.map_widget.run_js(f"window.setSites({json.dumps(site_catalogue.for_map(chosen), ensure_ascii=False)});")
        self.update_active_info()

    def set_base_map(self, name):
        self.settings.setValue("map/base", name)
        self.map_widget.run_js(f"window.setBaseLayer({json.dumps(name)});")

    # ------------------------------------------------------------------ borders

    def toggle_country_borders(self, is_checked):
        if not is_checked:
            self.map_widget.run_js("window.toggleBorderLayer(4, false);")
            return
        self.add_log("Lade Staatsgrenzen...")
        thread = BorderFetcherThread(4)
        thread.data_ready.connect(lambda lvl, name, data: self.on_border_data_ready(lvl, data))
        thread.error.connect(lambda msg: self.on_border_fetch_error(msg, lambda: self.map_panel.countries.setChecked(False)))
        self._start_border_thread(thread, "Staatsgrenzen werden geladen")

    def toggle_region_borders(self, country_name, is_checked):
        layer_id = f"regions_{country_name}".replace(" ", "_")
        if not is_checked:
            self.map_widget.run_js(f"window.removeBorderLayer('{layer_id}');")
            return
        self.add_log(f"Lade Regionsgrenzen für {country_name}...")
        thread = BorderFetcherThread(6, country_name)
        thread.data_ready.connect(lambda level, name, data, lid=layer_id: self.on_country_regions_data_ready(lid, data))
        thread.error.connect(lambda msg, n=country_name: self.on_border_fetch_error(msg, lambda: self.map_panel.uncheck_region(n)))
        label = 'Europa' if country_name == 'ALL' else COUNTRY_NAMES_DE.get(country_name, country_name)
        self._start_border_thread(thread, f"Regionsgrenzen {label} werden geladen")

    def _start_border_thread(self, thread, busy_text):
        self.border_fetcher_threads = [t for t in self.border_fetcher_threads if t.isRunning()]
        self.border_fetcher_threads.append(thread)
        key = f"borders{id(thread)}"
        self.busy.start(key, busy_text)
        thread.finished.connect(lambda: self.busy.stop(key))
        thread.start()

    def on_country_regions_data_ready(self, layer_id, data):
        self.add_log(f"Regionsgrenzen {layer_id} geladen.")
        self.map_widget.run_js(f"window.addCountryRegionsLayer('{layer_id}', {json.dumps(data)});")

    def on_border_data_ready(self, level, data):
        self.add_log(f"Grenzen (Ebene {level}) geladen.")
        self.map_widget.run_js(f"window.updateBorderLayer({level}, {json.dumps(data)});")
        self.map_widget.run_js(f"window.toggleBorderLayer({level}, true);")

    def on_border_fetch_error(self, error_message, undo):
        self.add_log(f"Fehler beim Laden der Grenzen: {error_message}")
        QMessageBox.warning(self, "Netzwerkfehler", f"Grenzdaten konnten nicht geladen werden:\n{error_message}")
        undo()

    # ------------------------------------------------------------------ misc

    def open_remote_debugger(self):
        webbrowser.open("http://localhost:8888")

    def fetch_url_from_js(self, request_id, url):
        thread = UrlFetcherThread(request_id, url)
        thread.data_ready.connect(self.on_url_data_ready)
        thread.error.connect(self.on_url_fetch_error)
        self.url_fetcher_threads[request_id] = thread
        thread.start()

    def fetch_text_from_js(self, request_id, url):
        thread = TextFetcherThread(request_id, url)
        thread.done.connect(lambda rid, text: self.map_widget.run_js(f"window.onTextFetched('{rid}', {json.dumps(text)});"))
        thread.finished.connect(lambda: self.url_fetcher_threads.pop(request_id, None))
        self.url_fetcher_threads[request_id] = thread
        thread.start()

    def on_url_data_ready(self, request_id, data):
        self.map_widget.run_js(f"window.onDataFetched('{request_id}', {json.dumps(data)});")
        if request_id in self.url_fetcher_threads:
            del self.url_fetcher_threads[request_id]

    def on_url_fetch_error(self, request_id, error_msg):
        self.add_log(f"Proxy Error for request {request_id}: {error_msg}")
        self.map_widget.run_js(f"window.onDataFetchError('{request_id}', {json.dumps(error_msg)});")
        if request_id in self.url_fetcher_threads:
            del self.url_fetcher_threads[request_id]

    def add_log(self, message):
        self.log_console.append(message)
        self.log_console.verticalScrollBar().setValue(self.log_console.verticalScrollBar().maximum())

    # ------------------------------------------------------------------ search and location

    def set_start_location(self, lat, lon, name):
        self.current_location = (lat, lon, name)
        self.update_navigator_endpoints()
        self.add_log(f"Standort für den Navigator: '{name}'.")

    def search_location(self):
        query = self.search_input.text().strip()
        if not query:
            return
        numbers = re.findall(r"[-+]?\d+(?:[.,]\d+)?", query)
        if len(numbers) == 2 and all(re.fullmatch(r"[-+]?\d+[.,]\d+", n) for n in numbers):
            lat, lon = (float(n.replace(',', '.')) for n in numbers)
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                self.set_start_location(lat, lon, f"{lat:.5f}, {lon:.5f}")
                self.map_widget.center_on_location(lat, lon, f"Koordinaten: {lat:.5f}, {lon:.5f}", 16)
                return
        if self.geocode_thread and self.geocode_thread.isRunning():
            return
        self.busy.start('search', f"suche „{query}“")
        self.geocode_thread = GeocodeThread(query)
        self.geocode_thread.found.connect(self.on_search_found)
        self.geocode_thread.failed.connect(lambda msg, q=query: self.on_search_failed(q, msg))
        self.geocode_thread.finished.connect(lambda: self.busy.stop('search'))
        self.geocode_thread.start()

    def on_search_found(self, results):
        self.go_to_search_result(results[0])
        if len(results) > 1:
            # Jump to the best hit right away; the other hits are offered below the search box.
            menu = QMenu(self)
            menu.addSection("Weitere Treffer")
            for r in results[1:]:
                menu.addAction(r['label'][:110], lambda r=r: self.go_to_search_result(r))
            menu.popup(self.search_input.mapToGlobal(self.search_input.rect().bottomLeft()))

    def go_to_search_result(self, r):
        self.set_start_location(r['lat'], r['lon'], r['label'].split(',')[0])
        self.map_widget.center_on_location(r['lat'], r['lon'], r['label'])
        if r.get('bbox'):
            self.map_widget.run_js(f"window.fitBounds({json.dumps(r['bbox'])}, 17);")
        self.add_log(f"Gefunden: {r['label']}")

    def on_search_failed(self, query, message):
        self.add_log(f"Suche nach '{query}' ohne Ergebnis: {message}")
        QMessageBox.information(self, "Suche", f"„{query}“ wurde nicht gefunden.\n\n"
                                              "Tipp: Straße, Hausnummer und Ort, z. B. „Hauptstraße 33, Pietling“, "
                                              "oder Koordinaten wie „48.0140, 12.8046“.")

    def determine_current_location(self):
        if self.locator is None:
            self.locator = Locator(self)
            self.locator.located.connect(self.on_located)
            self.locator.failed.connect(self.on_locate_failed)
        self.busy.start('locate', "Standort wird ermittelt")
        self.locator.locate()

    def on_located(self, lat, lon, how):
        self.busy.stop('locate')
        self.set_start_location(lat, lon, f"Eigener Standort ({how})")
        self.map_widget.center_on_location(lat, lon, f"Eigener Standort<br>{how}", 16)

    def on_locate_failed(self, message):
        self.busy.stop('locate')
        self.add_log(f"Standort nicht ermittelbar: {message}")
        QMessageBox.information(self, "Standort", "Der eigene Standort konnte nicht ermittelt werden.\n"
                                                  "Ist die Windows-Ortung aktiv (Einstellungen > Datenschutz > Position)?")

    # ------------------------------------------------------------------ markers

    def handle_map_right_click(self, lat, lon):
        menu = QMenu(self)
        title = menu.addAction(f"{lat:.5f}, {lon:.5f}")
        title.setEnabled(False)
        menu.addSeparator()
        menu.addAction(marker_icon('punkt'), "Neuer Marker hier …", lambda: self.show_add_marker_dialog(lat, lon))
        menu.addAction(marker_icon('ziel'), "Route hierher", lambda: self.route_to_point(lat, lon))
        menu.addAction(icons.icon('analysis', theme.TEXT_MUTED), "Analyse hier ansehen", lambda: self.analyse_here(lat, lon))
        menu.addSeparator()
        menu.addAction("Koordinaten kopieren",
                       lambda: (QApplication.clipboard().setText(f"{lat:.6f}, {lon:.6f}"),
                                self.statusBar().showMessage(f"Koordinaten kopiert: {lat:.6f}, {lon:.6f}", 4000)))
        menu.addAction("In Google Maps öffnen", lambda: webbrowser.open(f"https://www.google.com/maps?q={lat:.6f},{lon:.6f}"))
        menu.popup(QCursor.pos())

    def route_to_point(self, lat, lon):
        """Make this point the destination and route there from the start (marker, own position or search)."""
        marker = {"id": str(uuid.uuid4()), "lat": lat, "lon": lon, "kind": "ziel", "title": f"Ziel {lat:.4f}, {lon:.4f}",
                  "note": "", "created": datetime.datetime.now().isoformat(timespec='seconds')}
        self._replace_unique(marker)
        self.markers[marker['id']] = marker
        self._markers_changed()
        self.rail_group.button(3).setChecked(False)
        self.rail_group.button(3).click()   # open the navigator
        self.compute_route(self.navigator_panel.mode(), self.navigator_panel.via_ids())

    def analyse_here(self, lat, lon):
        if not self.analysis_panel.current_view():
            self.analysis_panel.set_view('combo')
        self.map_widget.run_js(f"window.setView({lat}, {lon}, Math.max(map.getZoom(), 16));")
        if self.panel_stack.currentWidget().widget() is not self.analysis_panel or not self.panel_stack.isVisible():
            self.rail_group.button(4).setChecked(False)
            self.rail_group.button(4).click()

    def show_add_marker_dialog(self, lat, lon):
        dialog = MarkerDialog(lat, lon, parent=self)
        if not dialog.exec():
            return
        data = dialog.get_data()
        marker = {"id": str(uuid.uuid4()), "lat": lat, "lon": lon, **data,
                  "created": datetime.datetime.now().isoformat(timespec='seconds')}
        self._replace_unique(marker)
        self.markers[marker['id']] = marker
        self._markers_changed()
        self.add_log(f"{MARKER_KINDS[marker['kind']][0]} '{marker['title']}' gesetzt.")

    def edit_marker(self, marker_id):
        marker = self.markers.get(marker_id)
        if not marker:
            return
        dialog = MarkerDialog(marker['lat'], marker['lon'], marker, parent=self)
        if not dialog.exec():
            return
        marker.update(dialog.get_data())
        self._replace_unique(marker)
        self._markers_changed()

    def _replace_unique(self, marker):
        """There is one start and one destination: a new one replaces the old."""
        if marker['kind'] in ('start', 'ziel'):
            for mid in [m['id'] for m in self.markers.values()
                        if m['kind'] == marker['kind'] and m['id'] != marker['id']]:
                del self.markers[mid]

    def _markers_changed(self):
        self.save_markers()
        self.update_marker_list_ui()
        self.draw_all_markers_on_map()

    def update_marker_list_ui(self):
        markers = list(self.markers.values())
        self.finds_panel.set_markers(markers, marker_icon('fund'))
        self.navigator_panel.set_markers(markers, marker_icon('punkt'))
        self.update_navigator_endpoints()

    def center_on_marker(self, marker_id):
        if marker_id in self.markers:
            marker = self.markers[marker_id]
            self.map_widget.run_js(f"window.setView({marker['lat']}, {marker['lon']}, 16);")
            self.map_widget.run_js(f"window.openMarkerPopup('{marker_id}');")

    def delete_marker(self, marker_id):
        marker = self.markers.get(marker_id)
        if not marker:
            return
        kind = MARKER_KINDS[marker['kind']][0]
        answer = QMessageBox.question(self, f"{kind} löschen", f"„{marker['title']}“ wirklich löschen?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        del self.markers[marker_id]
        self._markers_changed()
        self.add_log(f"{kind} '{marker['title']}' gelöscht.")

    def save_markers(self):
        try:
            with open(self.markers_file, 'w', encoding='utf-8') as f:
                json.dump(self.markers, f, indent=4, ensure_ascii=False)
        except IOError as e:
            QMessageBox.critical(self, "Speicherfehler", f"Fehler beim Speichern der Marker: {e}")

    @staticmethod
    def _migrate_marker(m):
        """Markers from before the kinds (comment + icon) become point/start/destination/find."""
        if 'kind' in m:
            return m
        icon = (m.get('icon') or '').lower()
        kind = ('start' if icon == 'start' else 'ziel' if icon == 'ziel' else
                'fund' if icon in ('münze', 'coin', 'treasure') else 'punkt')
        return {'id': m['id'], 'lat': m['lat'], 'lon': m['lon'], 'kind': kind,
                'title': m.get('comment') or MARKER_KINDS[kind][0], 'note': '', 'created': ''}

    def load_markers(self):
        if os.path.exists(self.markers_file):
            try:
                with open(self.markers_file, 'r', encoding='utf-8') as f:
                    self.markers = {k: self._migrate_marker(v) for k, v in json.load(f).items()}
                self.add_log(f"{len(self.markers)} Marker geladen.")
            except Exception as e:
                QMessageBox.critical(self, "Ladefehler", f"Fehler beim Laden der Marker-Datei: {e}.")
                self.markers = {}
        self.update_marker_list_ui()

    def draw_all_markers_on_map(self):
        self.map_widget.update_all_markers(list(self.markers.values()))

    # ------------------------------------------------------------------ navigator

    def _marker_of_kind(self, kind):
        return next((m for m in self.markers.values() if m['kind'] == kind), None)

    def update_navigator_endpoints(self):
        start = self._marker_of_kind('start')
        ziel = self._marker_of_kind('ziel')
        start_text = start['title'] if start else (self.current_location[2] if self.current_location else None)
        self.navigator_panel.set_endpoints(start_text, ziel['title'] if ziel else None)

    def _route_points(self, via_ids):
        """[(lat, lon, label)] start, via points, destination; None (with a message) if incomplete."""
        start = self._marker_of_kind('start')
        ziel = self._marker_of_kind('ziel')
        if start:
            first = (start['lat'], start['lon'], start['title'])
        elif self.current_location:
            first = self.current_location
        else:
            QMessageBox.information(self, "Navigator", "Es fehlt ein Start: Rechtsklick auf die Karte → Start, "
                                                       "oder oben den eigenen Standort ermitteln bzw. einen Ort suchen.")
            return None
        if not ziel:
            QMessageBox.information(self, "Navigator", "Es fehlt ein Ziel: Rechtsklick auf die Karte → Ziel.")
            return None
        via = [(m['lat'], m['lon'], m['title']) for m in (self.markers.get(i) for i in via_ids) if m]
        return [first] + via + [(ziel['lat'], ziel['lon'], ziel['title'])]

    def compute_route(self, mode, via_ids):
        self.settings.setValue("nav/mode", mode)
        points = self._route_points(via_ids)
        if not points or (self.route_thread and self.route_thread.isRunning()):
            return
        self.busy.start('route', "Route wird berechnet")
        self.navigator_panel.set_result("")
        self.route_thread = RouteThread([(p[0], p[1]) for p in points], mode)
        self.route_thread.found.connect(lambda dist, dur, line, m=mode, pts=points: self.on_route(m, pts, dist, dur, line))
        self.route_thread.failed.connect(self.on_route_failed)
        self.route_thread.finished.connect(lambda: self.busy.stop('route'))
        self.route_thread.start()

    def on_route(self, mode, points, distance, duration, line):
        self.last_route = {'mode': mode, 'points': points, 'line': line, 'distance': distance, 'duration': duration}
        h, m = divmod(round(duration / 60), 60)
        text = f"{distance / 1000:.1f} km · {f'{h} h ' if h else ''}{m} min".replace('.', ',')
        self.navigator_panel.set_result(text + "\nRouting: OpenStreetMap / FOSSGIS")
        self.map_widget.run_js(f"window.showRoute({json.dumps(line)});")

    def on_route_failed(self, message):
        self.navigator_panel.set_result("")
        self.add_log(f"Route nicht berechenbar: {message}")
        QMessageBox.information(self, "Navigator", f"Die Route konnte nicht berechnet werden:\n{message}")

    def clear_route(self):
        self.last_route = None
        self.navigator_panel.set_result("")
        self.map_widget.run_js("window.clearRoute();")

    GOOGLE_MODES = {'foot': 'walking', 'bike': 'bicycling', 'car': 'driving'}

    def _google_url(self, mode, points):
        """Google Maps URL (the documented 'Maps URLs' API: no key, allowed to link to)."""
        params = {'api': '1', 'origin': f"{points[0][0]:.6f},{points[0][1]:.6f}",
                  'destination': f"{points[-1][0]:.6f},{points[-1][1]:.6f}",
                  'travelmode': self.GOOGLE_MODES[mode]}
        if len(points) > 2:
            params['waypoints'] = '|'.join(f"{p[0]:.6f},{p[1]:.6f}" for p in points[1:-1])
        return 'https://www.google.com/maps/dir/?' + urllib.parse.urlencode(params, safe=',|')

    def _open_google(self, mode, via_ids):
        points = self._route_points(via_ids)
        if points:
            webbrowser.open(self._google_url(mode, points))

    def send_route_to_phone(self, mode, via_ids):
        points = self._route_points(via_ids)
        if not points:
            return
        url = self._google_url(mode, points)
        try:
            import segno
        except ImportError:
            QMessageBox.information(self, "Navigator", "Für den QR-Code fehlt das Paket 'segno' "
                                                       "(pip install -r requirements.txt).\n\n" + url)
            return
        buf = io.BytesIO()
        segno.make(url, error='m').save(buf, kind='png', scale=7, border=3, dark='#111316', light='#ffffff')
        pixmap = QPixmap()
        pixmap.loadFromData(buf.getvalue(), 'PNG')
        dialog = QDialog(self)
        dialog.setWindowTitle("Route aufs Handy")
        lay = QVBoxLayout(dialog)
        lay.setContentsMargins(20, 18, 20, 16)
        lay.setSpacing(10)
        title = QLabel("Mit der Handykamera scannen")
        title.setObjectName("panelTitle")
        lay.addWidget(title)
        info = QLabel(f"Die Route öffnet sich in Google Maps auf dem Handy ({len(points)} Punkte, "
                      f"{ {'foot': 'zu Fuß', 'bike': 'Fahrrad', 'car': 'Auto'}[mode] }).")
        info.setWordWrap(True)
        lay.addWidget(info)
        if len(points) > 5:
            warn = QLabel("Hinweis: Google Maps zeigt auf dem Handy höchstens 3 Zwischenstopps.")
            warn.setObjectName("panelHint")
            warn.setWordWrap(True)
            lay.addWidget(warn)
        code = QLabel()
        code.setPixmap(pixmap)
        code.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(code)
        buttons = QDialogButtonBox()
        copy_btn = buttons.addButton("Link kopieren", QDialogButtonBox.ButtonRole.ActionRole)
        copy_btn.clicked.connect(lambda: (QApplication.clipboard().setText(url), copy_btn.setText("Kopiert")))
        open_btn = buttons.addButton("Im Browser öffnen", QDialogButtonBox.ButtonRole.ActionRole)
        open_btn.clicked.connect(lambda: webbrowser.open(url))
        close_btn = buttons.addButton("Schließen", QDialogButtonBox.ButtonRole.RejectRole)
        close_btn.setObjectName("primary")
        buttons.rejected.connect(dialog.reject)
        lay.addWidget(buttons)
        dialog.exec()

    def save_route_gpx(self, mode, via_ids):
        points = self._route_points(via_ids)
        if not points:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Route als GPX speichern", "treasure_hunter_route.gpx", "GPX (*.gpx)")
        if not path:
            return
        esc = lambda t: str(t).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        names = ['Start'] + [f'Stopp {i}' for i in range(1, len(points) - 1)] + ['Ziel']
        wpts = ''.join(f'  <wpt lat="{p[0]:.6f}" lon="{p[1]:.6f}"><name>{esc(n)}: {esc(p[2])}</name></wpt>\n'
                       for p, n in zip(points, names))
        route = self.last_route if self.last_route and self.last_route['points'] == points else None
        track = ''
        if route:
            seg = ''.join(f'      <trkpt lat="{lat:.6f}" lon="{lon:.6f}"/>\n' for lat, lon in route['line'])
            track = f'  <trk><name>Route ({esc(mode)})</name>\n    <trkseg>\n{seg}    </trkseg>\n  </trk>\n'
        gpx = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<gpx version="1.1" creator="Treasure Hunter" xmlns="http://www.topografix.com/GPX/1/1">\n'
               f'{wpts}{track}</gpx>\n')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(gpx)
        self.add_log(f"GPX gespeichert: {path}" + ("" if route else " (nur Punkte; erst 'Route berechnen' für die Strecke)"))
        self.statusBar().showMessage(f"GPX gespeichert: {path}", 8000)

    # ------------------------------------------------------------- terrain tile cache

    def toggle_offline_mode(self, is_checked):
        if not self.tile_cache_server:
            return
        self.tile_cache_server.cache.offline = is_checked
        self.loading_label.setText("Offline" if is_checked else "")
        self.add_log("Offline-Modus aktiv: nur gespeicherte Gelände-Kacheln werden angezeigt."
                     if is_checked else "Offline-Modus aus: fehlende Kacheln werden wieder aus dem Internet geladen.")

    def refresh_cache_stats(self):
        if not self.tile_cache_server or (self.cache_stats_thread and self.cache_stats_thread.isRunning()):
            return
        self.offline_panel.stats.setText("zähle …")
        self.cache_stats_thread = CacheStatsThread(self.tile_cache_server.cache)
        self.cache_stats_thread.ready.connect(
            lambda info: self.offline_panel.set_stats(info['tiles'], info['bytes'], info['layers']))
        self.cache_stats_thread.start()

    def show_cache_info(self):
        if not self.tile_cache_server:
            QMessageBox.information(self, "Gelände-Cache", "Der Kachel-Cache ist nicht aktiv.")
            return
        info = self.tile_cache_server.cache.summary()
        lines = [f"Ordner: {info['cache_dir']}",
                 f"Gesamt: {info['tiles']} Kacheln, {info['bytes'] / 1_000_000:.1f} MB", ""]
        for key, data in sorted(info['layers'].items()):
            lines.append(f"{key}: {data['tiles']} Kacheln, {data['bytes'] / 1_000_000:.1f} MB")
        session = info['session']
        lines += ["", f"Diese Sitzung: {session['hits']} aus Cache, {session['network']} geladen, {session['errors']} Fehler"]
        if info.get('last_errors'):
            lines += ["", "Letzte Fehler:"] + info['last_errors'][-5:]
        QMessageBox.information(self, "Gelände-Cache", "\n".join(lines))

    def open_cache_folder(self):
        if not self.tile_cache_server:
            return
        folder = self.tile_cache_server.cache.cache_dir
        os.makedirs(folder, exist_ok=True)
        try:
            os.startfile(folder)
        except OSError as e:
            QMessageBox.warning(self, "Gelände-Cache", f"Ordner konnte nicht geöffnet werden: {e}")

    def start_tile_download_dialog(self):
        if not self.tile_cache_server:
            QMessageBox.information(self, "Gelände-Cache", "Der Kachel-Cache ist nicht aktiv.")
            return
        if self.tile_download_thread and self.tile_download_thread.isRunning():
            QMessageBox.information(self, "Gelände-Cache", "Es läuft bereits ein Download.")
            return
        self.map_widget.run_js("window.getTerrainPlanForView(0, 20);", self._show_download_dialog)

    def _show_download_dialog(self, plan):
        if not plan or not plan.get('stacks'):
            QMessageBox.warning(self, "Gelände-Cache", "Kartenausschnitt konnte nicht ermittelt werden.")
            return
        cache = self.tile_cache_server.cache
        bbox = tuple(plan['bbox'])
        stacks = plan['stacks']
        current_zoom = int(plan.get('zoom', 13))
        if not any(stacks.get(str(z)) or stacks.get(z) for z in range(0, 21)):
            QMessageBox.information(self, "Gelände-Cache",
                                    "Für diesen Kartenausschnitt ist keine Gelände-Überlagerung aktiv.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Ausschnitt herunterladen")
        dialog.setMinimumWidth(400)
        form = QFormLayout(dialog)
        form.setContentsMargins(18, 16, 18, 14)
        form.setSpacing(10)
        info_label = QLabel("Lädt alle Gelände-Kacheln des sichtbaren Kartenausschnitts für den "
                            "gewählten Zoombereich in den lokalen Speicher. Nur die eingeschalteten "
                            "Regionen werden berücksichtigt.")
        info_label.setWordWrap(True)
        form.addRow(info_label)
        min_spin = QSpinBox(); min_spin.setRange(0, 20); min_spin.setValue(max(10, min(current_zoom, 17)))
        max_spin = QSpinBox(); max_spin.setRange(0, 20); max_spin.setValue(max(min_spin.value(), min(17, current_zoom + 3)))
        form.addRow("Von Zoom:", min_spin)
        form.addRow("Bis Zoom:", max_spin)
        estimate_label = QLabel()
        estimate_label.setObjectName("valueLabel")
        form.addRow("Umfang:", estimate_label)

        def update_estimate():
            lo, hi = min_spin.value(), max_spin.value()
            if lo > hi:
                estimate_label.setText("Ungültiger Bereich")
                return
            jobs = plan_download(cache, bbox, stacks, lo, hi)
            cached = sum(1 for j in jobs if cache.has(*j))
            estimate_label.setText(f"{len(jobs)} Kacheln, davon {cached} schon gespeichert\n"
                                   f"ca. {max(len(jobs) - cached, 0) * 0.08:.0f} MB neu")
        min_spin.valueChanged.connect(update_estimate)
        max_spin.valueChanged.connect(update_estimate)
        update_estimate()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Herunterladen")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setObjectName("primary")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if not dialog.exec():
            return

        jobs = plan_download(cache, bbox, stacks, min_spin.value(), max_spin.value())
        if not jobs:
            QMessageBox.information(self, "Gelände-Cache", "Keine Kacheln zu laden.")
            return
        if len(jobs) > 20000:
            answer = QMessageBox.question(self, "Gelände-Cache",
                                          f"{len(jobs)} Kacheln sind sehr viele. Trotzdem starten?")
            if answer != QMessageBox.StandardButton.Yes:
                return

        self.download_progress = QProgressDialog("Lade Gelände-Kacheln...", "Abbrechen", 0, len(jobs), self)
        self.download_progress.setWindowTitle("Gelände-Cache")
        self.download_progress.setMinimumDuration(0)
        self.download_progress.setValue(0)
        self.tile_download_thread = TileDownloadThread(cache, jobs)
        self.tile_download_thread.progress.connect(self._on_download_progress)
        self.tile_download_thread.finished_summary.connect(self._on_download_finished)
        self.download_progress.canceled.connect(self.tile_download_thread.stop)
        self.add_log(f"Starte Download von {len(jobs)} Gelände-Kacheln (Zoom {min_spin.value()}-{max_spin.value()}).")
        self.tile_download_thread.start()

    def _on_download_progress(self, done, total, failed):
        if self.download_progress:
            self.download_progress.setLabelText(f"Lade Gelände-Kacheln... {done}/{total} ({failed} Fehler)")
            self.download_progress.setValue(done)

    def _on_download_finished(self, summary):
        if self.download_progress:
            self.download_progress.reset()
            self.download_progress = None
        self.add_log(summary)
        self.statusBar().showMessage(summary, 10000)
        self.refresh_cache_stats()

    def closeEvent(self, event):
        """ Handles the window close event to ensure clean shutdown of threads. """
        self.add_log("Anwendung wird beendet... Warte auf Threads.")

        for thread in self.border_fetcher_threads:
            if thread.isRunning():
                thread.stop()
                thread.wait()

        # Stop all URL fetcher threads
        for request_id, thread in list(self.url_fetcher_threads.items()):
            if thread.isRunning():
                thread.stop()
                thread.wait()

        if self.tile_download_thread and self.tile_download_thread.isRunning():
            self.tile_download_thread.stop()
            self.tile_download_thread.wait()
        if self.cache_stats_thread and self.cache_stats_thread.isRunning():
            self.cache_stats_thread.wait()
        if self.tile_cache_server:
            self.tile_cache_server.stop()

        self.add_log("Alle Threads beendet. Anwendung wird geschlossen.")
        event.accept()


def main():
    # Leftovers of a crashed or hung run would keep the cache ports and the DevTools port busy.
    closed = process_guard.close_other_instances()
    app = QApplication(sys.argv)
    app.setApplicationName("Treasure Hunter")
    app.setFont(QFont(theme.UI_FONT, 10))
    app.setStyleSheet(theme.stylesheet())
    window = TreasureHunterApp()
    if closed:
        window.add_log(f"{closed} hängende Treasure-Hunter-Prozesse beendet.")
    # Maximised, so the window always fits the screen (a fixed 900 px height ran off 1536x864 laptops).
    window.showMaximized()
    code = app.exec()
    # Hard exit: lingering worker threads (downloads, slow tile requests) must not keep a zombie alive.
    process_guard.end_own_children()
    os._exit(code)


if __name__ == "__main__":
    main()
