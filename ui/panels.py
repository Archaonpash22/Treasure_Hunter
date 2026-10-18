"""The side panels: map (base map, LiDAR per country and region, borders), sites, finds, offline."""
import os

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton,
    QRadioButton, QSlider, QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator, QVBoxLayout, QWidget
)

from . import theme
from .widgets import Collapsible, ToggleSwitch, divider, hint, search_field, section, title_row

ROLE_ID = Qt.ItemDataRole.UserRole
ROLE_BOUNDS = Qt.ItemDataRole.UserRole + 1
ROLE_SEARCH = Qt.ItemDataRole.UserRole + 2


class Panel(QWidget):
    def __init__(self, title, header_widget=None, description=None):
        super().__init__()
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(16, 14, 12, 12)
        self.layout_.setSpacing(8)
        self.layout_.addWidget(title_row(title, header_widget))
        if description:
            self.layout_.addWidget(hint(description))

    def add(self, widget, stretch=0):
        self.layout_.addWidget(widget, stretch)
        return widget


def _bounds_intersect(a, b):
    (as_, aw), (an, ae) = a
    (bs, bw), (bn, be) = b
    return not (as_ > bn or an < bs or aw > be or ae < bw)


def _resolution_rank(text):
    """Sort key / colour class for a resolution like '25 cm' or '2 m'."""
    if not text:
        return 99.0
    value, unit = text.split()
    value = float(value.replace(',', '.'))
    return value / 100 if unit == 'cm' else value


class LidarSection(QWidget):
    """Opacity and a tree of countries > regions; every LiDAR layer and base relief is picked by hand."""
    opacity_changed = pyqtSignal(int)
    selection_changed = pyqtSignal(list)   # ids switched on, e.g. ['DE-BW', 'DE:base']
    zoom_requested = pyqtSignal(list)      # [[south, west], [north, east]]

    def __init__(self, catalog, enabled_ids=None, opacity=100):
        super().__init__()
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self.layout_.setSpacing(6)

        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 2, 0, 2)
        lay.addWidget(QLabel('Deckkraft'))
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(10, 100)
        self.opacity.setValue(opacity)
        lay.addWidget(self.opacity, 1)
        self.opacity_value = QLabel(f'{opacity} %')
        self.opacity_value.setObjectName('valueLabel')
        self.opacity_value.setFixedWidth(40)
        self.opacity_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(self.opacity_value)
        self.opacity.valueChanged.connect(self._on_opacity)
        self.add(row)

        self.empty_hint = self.add(hint('Noch nichts gewählt: ein Land aufklappen und Regionen anhaken. '
                                        'Gold = 50 cm oder feiner. Das Grundrelief füllt den Rest des Landes.'))
        self.empty_hint.setObjectName('emptyHint')
        self.filter = self.add(search_field('Land oder Region suchen'))
        self.filter.textChanged.connect(self._apply_filter)
        self.in_view = self.add(QCheckBox('Nur was im Kartenausschnitt liegt'))
        self.in_view.toggled.connect(self._apply_filter)
        self._view_bounds = None

        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(14)
        self.tree.setUniformRowHeights(True)
        self.tree.setRootIsDecorated(True)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, self.tree.header().ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, self.tree.header().ResizeMode.ResizeToContents)
        self.tree.itemDoubleClicked.connect(self._on_double_click)
        self.tree.itemExpanded.connect(self._fit_tree)
        self.tree.itemCollapsed.connect(self._fit_tree)
        self.add(self.tree)

        footer = QWidget()
        f = QHBoxLayout(footer)
        f.setContentsMargins(0, 0, 0, 0)
        all_on = QPushButton('Alle an')
        all_on.setObjectName('link')
        all_on.clicked.connect(lambda: self._set_all(True))
        all_off = QPushButton('Alle aus')
        all_off.setObjectName('link')
        all_off.clicked.connect(lambda: self._set_all(False))
        f.addWidget(all_on)
        f.addWidget(all_off)
        f.addStretch()
        legend = QLabel(f'<span style="color:{theme.ACCENT}">●</span> ≤ 50 cm &nbsp; '
                        f'<span style="color:{theme.TEXT}">●</span> 1–2 m &nbsp; '
                        f'<span style="color:{theme.TEXT_FAINT}">●</span> gröber')
        legend.setObjectName('panelHint')
        f.addWidget(legend)
        self.add(footer)
        self.tree.setToolTip('Alles ist anfangs aus: Regionen und Grundrelief einzeln anklicken. '
                             'Doppelklick zoomt zur Region.')

        self._building = True
        self._build(catalog, set(enabled_ids or []))
        self._building = False
        self._fit_tree()
        self.selection_changed.connect(lambda ids: self.empty_hint.setVisible(not ids))
        self.empty_hint.setVisible(not self.enabled_ids())
        self.tree.itemChanged.connect(self._on_item_changed)

    # ----------------------------------------------------------------- tree
    def _build(self, catalog, enabled):
        bold = QFont(theme.UI_FONT)
        bold.setWeight(QFont.Weight.DemiBold)
        italic = QFont(theme.UI_FONT)
        italic.setItalic(True)
        for country in sorted(catalog, key=lambda c: c['name']):
            top = QTreeWidgetItem([country['name'], ''])
            top.setFont(0, bold)
            top.setData(0, ROLE_ID, country['id'])
            top.setData(0, ROLE_BOUNDS, country.get('bounds'))
            top.setData(0, ROLE_SEARCH, country['name'].lower())
            # Tristate is kept by hand (_sync_country): Qt's automatic tristate gives up as soon as
            # one child has no checkbox, and regions without LiDAR have none.
            top.setFlags(top.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            self.tree.addTopLevelItem(top)
            fine = sum(1 for r in country['regions'] if r.get('layers'))
            top.setText(1, f"{fine}/{len(country['regions'])}" if country['regions'] else '')
            top.setForeground(1, QBrush(QColor(theme.TEXT_FAINT)))
            top.setToolTip(1, f'{fine} von {len(country["regions"])} Regionen mit LiDAR')
            base = country.get('base')
            if base:
                item = QTreeWidgetItem([base['name'], base.get('resolution', '')])
                item.setFont(0, italic)
                bid = country['id'] + ':base'
                item.setData(0, ROLE_ID, bid)
                item.setData(0, ROLE_BOUNDS, country.get('bounds'))
                item.setData(0, ROLE_SEARCH, (country['name'] + ' ' + base['name']).lower())
                item.setToolTip(0, f"Flächendeckendes Relief {base.get('resolution', '')} ({base.get('source', '')}), "
                                   'liegt unter den Regionen und füllt Lücken')
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(0, Qt.CheckState.Checked if bid in enabled else Qt.CheckState.Unchecked)
                self._style_resolution(item, base.get('resolution'))
                top.addChild(item)
            for region in country['regions']:
                res = region.get('resolution')
                item = QTreeWidgetItem([region['name'], res or '—'])
                item.setData(0, ROLE_ID, region['id'])
                item.setData(0, ROLE_BOUNDS, region.get('bounds'))
                item.setData(0, ROLE_SEARCH, (country['name'] + ' ' + region['name'] + ' ' + region['id']).lower())
                if region.get('layers'):
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(0, Qt.CheckState.Checked if region['id'] in enabled else Qt.CheckState.Unchecked)
                    item.setToolTip(0, f"LiDAR {res} · {region.get('source', '')}")
                    self._style_resolution(item, res)
                else:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
                    item.setForeground(0, QBrush(QColor(theme.TEXT_FAINT)))
                    item.setForeground(1, QBrush(QColor(theme.TEXT_FAINT)))
                    item.setToolTip(0, (region.get('note') or 'kein LiDAR') + ' – das Grundrelief deckt die Region ab')
                top.addChild(item)
            if not self._sync_country(top):
                top.setFlags(top.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
        self.tree.resizeColumnToContents(1)

    @staticmethod
    def _checkable_children(top):
        return [top.child(i) for i in range(top.childCount())
                if top.child(i).flags() & Qt.ItemFlag.ItemIsUserCheckable]

    def _sync_country(self, top):
        """Set a country's box from its regions; False if it has nothing switchable."""
        states = [c.checkState(0) for c in self._checkable_children(top)]
        if not states:
            return False
        if all(s == Qt.CheckState.Checked for s in states):
            state = Qt.CheckState.Checked
        elif all(s == Qt.CheckState.Unchecked for s in states):
            state = Qt.CheckState.Unchecked
        else:
            state = Qt.CheckState.PartiallyChecked
        # An item without check data reports Unchecked but draws no box, so set it the first time too.
        if top.data(0, Qt.ItemDataRole.CheckStateRole) is None or top.checkState(0) != state:
            top.setCheckState(0, state)
        return True

    @staticmethod
    def _style_resolution(item, res):
        rank = _resolution_rank(res)
        color = theme.ACCENT if rank <= 0.5 else theme.TEXT if rank <= 2 else theme.TEXT_FAINT
        item.setForeground(1, QBrush(QColor(color)))

    def _checkable_items(self):
        it = QTreeWidgetItemIterator(self.tree)
        while it.value():
            item = it.value()
            if item.parent() is not None and item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                yield item
            it += 1

    def disabled_ids(self):
        return [i.data(0, ROLE_ID) for i in self._checkable_items() if i.checkState(0) == Qt.CheckState.Unchecked]

    def enabled_ids(self):
        return [i.data(0, ROLE_ID) for i in self._checkable_items() if i.checkState(0) == Qt.CheckState.Checked]

    def _on_item_changed(self, item, column):
        if self._building or column != 0:
            return
        self._building = True
        if item.parent() is None:
            state = item.checkState(0)
            if state != Qt.CheckState.PartiallyChecked:
                for child in self._checkable_children(item):
                    child.setCheckState(0, state)
        else:
            self._sync_country(item.parent())
        self._building = False
        self.selection_changed.emit(self.enabled_ids())

    def _set_all(self, on):
        self._building = True
        state = Qt.CheckState.Checked if on else Qt.CheckState.Unchecked
        for item in self._checkable_items():
            item.setCheckState(0, state)
        for i in range(self.tree.topLevelItemCount()):
            self._sync_country(self.tree.topLevelItem(i))
        self._building = False
        self.selection_changed.emit(self.enabled_ids())

    def _on_double_click(self, item, _column):
        bounds = item.data(0, ROLE_BOUNDS)
        if bounds:
            self.zoom_requested.emit(bounds)

    def _on_opacity(self, value):
        self.opacity_value.setText(f'{value} %')
        self.opacity_changed.emit(value)

    # ----------------------------------------------------------------- filtering
    def set_view_bounds(self, bounds):
        self._view_bounds = bounds
        if self.in_view.isChecked():
            self._apply_filter()

    def add(self, widget, stretch=0):
        self.layout_.addWidget(widget, stretch)
        return widget

    def _fit_tree(self, *_):
        """As tall as the visible rows (up to 9, the list scrolls beyond), so the borders section follows
        right below and stays on screen even on 1366x768 laptops."""
        rows = 0
        it = QTreeWidgetItemIterator(self.tree, QTreeWidgetItemIterator.IteratorFlag.NotHidden)
        while it.value():
            item = it.value()
            parent = item.parent()
            if parent is None or parent.isExpanded():
                rows += 1
            it += 1
        row_h = self.tree.sizeHintForRow(0) if self.tree.topLevelItemCount() else 28
        self.tree.setFixedHeight(min(max(rows, 3), 9) * max(row_h, 20) + 6)

    def _apply_filter(self, *_):
        text = self.filter.text().strip().lower()
        view = self._view_bounds if self.in_view.isChecked() else None
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            top_match = bool(text) and text in top.data(0, ROLE_SEARCH)
            any_child = False
            for j in range(top.childCount()):
                child = top.child(j)
                ok = (not text or top_match or text in child.data(0, ROLE_SEARCH))
                b = child.data(0, ROLE_BOUNDS)
                if view and b and not _bounds_intersect(b, view):
                    ok = False
                child.setHidden(not ok)
                any_child |= ok
            top_bounds = top.data(0, ROLE_BOUNDS)
            hidden = not any_child or (view and top_bounds and not _bounds_intersect(top_bounds, view))
            top.setHidden(bool(hidden))
            if (text or view) and not hidden:
                top.setExpanded(True)
        self._fit_tree()


COUNTRY_NAMES_DE = {
    'Albania': 'Albanien', 'Andorra': 'Andorra', 'Austria': 'Österreich', 'Belarus': 'Belarus',
    'Belgium': 'Belgien', 'Bosnia and Herzegovina': 'Bosnien und Herzegowina', 'Bulgaria': 'Bulgarien',
    'Croatia': 'Kroatien', 'Cyprus': 'Zypern', 'Czechia': 'Tschechien', 'Denmark': 'Dänemark',
    'Estonia': 'Estland', 'Finland': 'Finnland', 'France': 'Frankreich', 'Germany': 'Deutschland',
    'Greece': 'Griechenland', 'Hungary': 'Ungarn', 'Iceland': 'Island', 'Ireland': 'Irland',
    'Italy': 'Italien', 'Kosovo': 'Kosovo', 'Latvia': 'Lettland', 'Liechtenstein': 'Liechtenstein',
    'Lithuania': 'Litauen', 'Luxembourg': 'Luxemburg', 'Malta': 'Malta', 'Moldova': 'Moldau',
    'Monaco': 'Monaco', 'Montenegro': 'Montenegro', 'Netherlands': 'Niederlande',
    'North Macedonia': 'Nordmazedonien', 'Norway': 'Norwegen', 'Poland': 'Polen', 'Portugal': 'Portugal',
    'Romania': 'Rumänien', 'Russia': 'Russland', 'San Marino': 'San Marino', 'Serbia': 'Serbien',
    'Slovakia': 'Slowakei', 'Slovenia': 'Slowenien', 'Spain': 'Spanien', 'Sweden': 'Schweden',
    'Switzerland': 'Schweiz', 'Ukraine': 'Ukraine', 'United Kingdom': 'Vereinigtes Königreich',
    'Vatican City': 'Vatikanstadt',
}

_UMLAUT_SORT = str.maketrans('ÄÖÜäöü', 'AOUaou')

CULTURE_NAMES_DE = {'celts': 'Kelten', 'romans': 'Römer', 'medieval': 'Mittelalter', 'modern': 'Neuzeit'}

BASE_MAPS = [
    ('OpenStreetMap', 'OpenStreetMap'),
    ('Topographisch', 'OpenTopoMap, Höhenlinien'),
    ('Satellit', 'Esri World Imagery'),
    ('Roman Empire', 'Römisches Reich (DARE), Orte anklickbar'),
]


class MapPanel(Panel):
    """Base map, LiDAR and borders as collapsible sections. Countries for region borders can be
    starred; favourites stay at the top of the list."""
    base_map_changed = pyqtSignal(str)
    countries_toggled = pyqtSignal(bool)
    region_borders_toggled = pyqtSignal(str, bool)
    favorites_changed = pyqtSignal(list)

    def __init__(self, country_names, lidar, base_map='OpenStreetMap', favorites=()):
        super().__init__('Karte')
        self.lidar = lidar

        base = QWidget()
        bl = QVBoxLayout(base)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)
        self.group = QButtonGroup(self)
        names = [n for n, _ in BASE_MAPS]
        base_map = base_map if base_map in names else 'OpenStreetMap'
        for name, desc in BASE_MAPS:
            rb = QRadioButton(name if name != 'Roman Empire' else 'Römisches Reich')
            rb.setToolTip(desc)
            rb.setProperty('base', name)
            rb.setChecked(name == base_map)
            self.group.addButton(rb)
            bl.addWidget(rb)
        self.group.buttonToggled.connect(lambda b, on: on and self.base_map_changed.emit(b.property('base')))

        borders = QWidget()
        gl = QVBoxLayout(borders)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.setSpacing(6)
        self.countries = QCheckBox('Staatsgrenzen (ganz Europa)')
        self.countries.toggled.connect(self.countries_toggled)
        gl.addWidget(self.countries)
        gl.addWidget(hint('Regionsgrenzen mit Kürzeln: Land einzeln wählen. Stern = Favorit, steht oben.'))
        self.filter = search_field('Land suchen')
        gl.addWidget(self.filter)
        self.favorites = set(favorites)
        self.list = QTreeWidget()
        self.list.setColumnCount(2)
        self.list.setHeaderHidden(True)
        self.list.setRootIsDecorated(False)
        self.list.setIndentation(0)
        self.list.setUniformRowHeights(True)
        self.list.header().setStretchLastSection(False)
        self.list.header().setSectionResizeMode(0, self.list.header().ResizeMode.Stretch)
        self.list.header().setSectionResizeMode(1, self.list.header().ResizeMode.Fixed)
        self.list.header().resizeSection(1, 28)
        entries = sorted(((n, COUNTRY_NAMES_DE.get(n, n)) for n in country_names),
                         key=lambda e: e[1].translate(_UMLAUT_SORT))
        for order, (key, label) in enumerate(entries):
            item = QTreeWidgetItem([label, ''])
            item.setData(0, ROLE_ID, key)
            item.setData(0, ROLE_SEARCH, order)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, Qt.CheckState.Unchecked)
            item.setTextAlignment(1, Qt.AlignmentFlag.AlignCenter)
            item.setToolTip(1, 'Als Favorit markieren')
            self.list.addTopLevelItem(item)
        self._sort()
        self.list.itemChanged.connect(self._on_changed)
        self.list.itemClicked.connect(self._on_clicked)
        self.filter.textChanged.connect(self._filter)
        self.list.setMinimumHeight(180)
        gl.addWidget(self.list, 1)

        # Every start: LiDAR open, borders closed.
        for title, widget, expanded, grow in (('Hintergrund', base, True, False),
                                              ('LiDAR', lidar, True, False),
                                              ('Grenzen', borders, False, True)):
            self.add(Collapsible(title, widget, expanded=expanded, grow=grow), 1 if grow else 0)
        self.layout_.addStretch(0)

    def _items(self):
        return [self.list.topLevelItem(i) for i in range(self.list.topLevelItemCount())]

    def _sort(self):
        """Favourites first (in list order), then the rest; stars drawn in the second column."""
        self.list.blockSignals(True)
        items = [self.list.takeTopLevelItem(0) for _ in range(self.list.topLevelItemCount())]
        items.sort(key=lambda it: (it.data(0, ROLE_ID) not in self.favorites, it.data(0, ROLE_SEARCH)))
        for it in items:
            fav = it.data(0, ROLE_ID) in self.favorites
            it.setText(1, '★' if fav else '☆')
            it.setForeground(1, QBrush(QColor(theme.ACCENT if fav else theme.TEXT_FAINT)))
            self.list.addTopLevelItem(it)
        self.list.blockSignals(False)

    def _on_clicked(self, item, column):
        if column != 1:
            return
        self.favorites.symmetric_difference_update({item.data(0, ROLE_ID)})
        self._sort()
        self.list.setCurrentItem(item)
        self.favorites_changed.emit(sorted(self.favorites))

    def _on_changed(self, item, column):
        if column == 0:
            self.region_borders_toggled.emit(item.data(0, ROLE_ID), item.checkState(0) == Qt.CheckState.Checked)

    def uncheck_region(self, key):
        for item in self._items():
            if item.data(0, ROLE_ID) == key:
                item.setCheckState(0, Qt.CheckState.Unchecked)

    def _filter(self, text):
        text = text.strip().lower()
        for item in self._items():
            item.setHidden(bool(text) and text not in item.text(0).lower())


class SitesPanel(Panel):
    """Ground monuments (Bavaria) and the site catalogue: coins and hoards, then epoch > type, culture filter."""
    monuments_toggled = pyqtSignal(bool)
    filter_changed = pyqtSignal()           # selection, culture or search text changed

    def __init__(self, monuments_on=False):
        super().__init__('Fundstellen')

        mon = QWidget()
        ml = QVBoxLayout(mon)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(6)
        self.monuments = QCheckBox('Amtliche Bodendenkmal-Flächen (rot)')
        self.monuments.setChecked(monuments_on)
        self.monuments.toggled.connect(self.monuments_toggled)
        ml.addWidget(self.monuments)
        note = hint('Nur Bayern (Bayerisches Landesamt für Denkmalpflege). Dort sind Graben und Sondengehen '
                    'ohne Erlaubnis verboten. Klick auf eine Fläche zeigt Aktennummer und Beschreibung. '
                    'Andere Länder folgen.')
        ml.addWidget(note)

        sites = QWidget()
        sl = QVBoxLayout(sites)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(6)
        self.search = search_field('Name oder Beschreibung')
        self.search.textChanged.connect(lambda _t: self.filter_changed.emit())
        sl.addWidget(self.search)
        self.culture = QComboBox()
        self.culture.addItem('Alle Völker und Kulturen', None)
        self.culture.currentIndexChanged.connect(lambda _i: self.filter_changed.emit())
        sl.addWidget(self.culture)
        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(14)
        self.tree.setUniformRowHeights(True)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, self.tree.header().ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, self.tree.header().ResizeMode.ResizeToContents)
        self.tree.setMinimumHeight(220)
        self.tree.itemChanged.connect(self._on_changed)
        sl.addWidget(self.tree, 1)
        foot = QWidget()
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(0, 0, 0, 0)
        off = QPushButton('Alle aus')
        off.setObjectName('link')
        off.clicked.connect(self._all_off)
        fl.addWidget(off)
        fl.addStretch()
        self.shown = QLabel('')
        self.shown.setObjectName('panelHint')
        fl.addWidget(self.shown)
        sl.addWidget(foot)
        self.sources = hint('')
        sl.addWidget(self.sources)

        self.add(Collapsible('Bodendenkmäler – nur Bayern', mon, expanded=True))
        self.add(Collapsible('Fundstellen nach Zeitalter', sites, expanded=True, grow=True), 1)
        self.layout_.addStretch(0)
        self._building = False

    # ----------------------------------------------------------------- catalogue
    def set_catalogue(self, counts, epochs, types, cultures, per_source, colors):
        """counts: {epoch: {type: n}}; epochs/types/cultures: key -> label (epochs: (label, colour group))."""
        self._building = True
        self.tree.clear()
        bold = QFont(theme.UI_FONT)
        bold.setWeight(QFont.Weight.DemiBold)
        # Coins and hoards first, as one group over all epochs (children: epochs).
        coin_types = ('hoard', 'coin_find')
        coin_rows = [(ep, label, [(ep, t) for t in coin_types if counts.get(ep, {}).get(t)],
                      sum(counts.get(ep, {}).get(t, 0) for t in coin_types)) for ep, (label, _g) in epochs.items()]
        coin_rows = [r for r in coin_rows if r[3]]
        if coin_rows:
            top = QTreeWidgetItem(['Münzen und Horte', str(sum(r[3] for r in coin_rows))])
            top.setFont(0, bold)
            top.setForeground(0, QBrush(QColor(theme.ACCENT)))
            top.setForeground(1, QBrush(QColor(theme.TEXT_FAINT)))
            top.setFlags(top.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            top.setToolTip(0, 'Münzfunde und Hortfunde (Depotfunde) aller Zeiten; Horte von Nomisma nur auf Ortsebene genau')
            for ep, label, pairs, n in coin_rows:
                child = QTreeWidgetItem([label, str(n)])
                child.setData(0, ROLE_ID, pairs)
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Unchecked)
                child.setForeground(1, QBrush(QColor(theme.TEXT_FAINT)))
                top.addChild(child)
            top.setCheckState(0, Qt.CheckState.Unchecked)
            self.tree.addTopLevelItem(top)
        for ep, (label, group) in epochs.items():
            per_type = {t: n for t, n in (counts.get(ep) or {}).items() if t not in coin_types}
            if not per_type:
                continue
            top = QTreeWidgetItem([label, str(sum(per_type.values()))])
            top.setFont(0, bold)
            top.setForeground(0, QBrush(QColor(colors[group])))
            top.setForeground(1, QBrush(QColor(theme.TEXT_FAINT)))
            top.setFlags(top.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            for typ, n in sorted(per_type.items(), key=lambda kv: -kv[1]):
                child = QTreeWidgetItem([types[typ], str(n)])
                child.setData(0, ROLE_ID, [(ep, typ)])
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Unchecked)
                child.setForeground(1, QBrush(QColor(theme.TEXT_FAINT)))
                top.addChild(child)
            top.setCheckState(0, Qt.CheckState.Unchecked)
            self.tree.addTopLevelItem(top)
        self.culture.blockSignals(True)
        while self.culture.count() > 1:
            self.culture.removeItem(1)
        for key, label in cultures.items():
            self.culture.addItem(label, key)
        self.culture.blockSignals(False)
        total = sum(per_source.values())
        self.sources.setText(f'{total:,}'.replace(',', '.') + ' Fundstellen in DE, AT, CH, IT. Quellen: ' +
                             ', '.join(f'{k} ({v:,})'.replace(',', '.') for k, v in per_source.items()) +
                             '. Bayerische Bodendenkmäler stehen nicht doppelt hier, sondern oben als Flächen.'
                             if total else 'Noch kein Katalog: python tools/build_sites.py ausführen.')
        self._building = False

    def selected_pairs(self):
        pairs = set()
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            for j in range(top.childCount()):
                child = top.child(j)
                if child.checkState(0) == Qt.CheckState.Checked:
                    pairs.update(tuple(p) for p in child.data(0, ROLE_ID))
        return pairs

    def culture_key(self):
        return self.culture.currentData()

    def set_shown(self, n):
        self.shown.setText(f'{n:,} auf der Karte'.replace(',', '.') if n else '')

    def _on_changed(self, item, column):
        if self._building or column != 0:
            return
        self._building = True
        if item.parent() is None:
            state = item.checkState(0)
            if state != Qt.CheckState.PartiallyChecked:
                for j in range(item.childCount()):
                    item.child(j).setCheckState(0, state)
        else:
            top = item.parent()
            states = {top.child(j).checkState(0) for j in range(top.childCount())}
            top.setCheckState(0, states.pop() if len(states) == 1 else Qt.CheckState.PartiallyChecked)
        self._building = False
        self.filter_changed.emit()

    def _all_off(self):
        self._building = True
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            top.setCheckState(0, Qt.CheckState.Unchecked)
            for j in range(top.childCount()):
                top.child(j).setCheckState(0, Qt.CheckState.Unchecked)
        self._building = False
        self.filter_changed.emit()


class MarkerListMixin:
    """Common bits of the lists of the user's markers."""

    def _make_list(self):
        lst = QListWidget()
        lst.setIconSize(QSize(18, 24))
        lst.itemDoubleClicked.connect(lambda item: self.center_requested.emit(item.data(ROLE_ID)))
        return lst

    @staticmethod
    def _current_id(lst):
        item = lst.currentItem()
        return item.data(ROLE_ID) if item else None


class FindsPanel(Panel, MarkerListMixin):
    """Everything the user has found (markers of kind 'fund'), with notes."""
    center_requested = pyqtSignal(str)
    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__('Meine Funde', description='Rechtsklick auf die Karte → „Neuer Marker“ → Fund. '
                                                    'Doppelklick zeigt den Fund auf der Karte.')
        self.filter = self.add(search_field('Fund suchen (Titel oder Notiz)'))
        self.filter.textChanged.connect(self._filter)
        self.count = self.add(QLabel())
        self.count.setObjectName('panelHint')
        self.list = self._make_list()
        self.list.currentItemChanged.connect(self._show_current)
        self.add(self.list, 1)
        self.empty = self.add(hint('Noch keine Funde gespeichert.'))
        self.detail = self.add(QLabel())
        self.detail.setWordWrap(True)
        self.detail.setObjectName('findDetail')
        self.detail.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        self.edit_btn = QPushButton('Bearbeiten')
        self.edit_btn.clicked.connect(lambda: self._emit(self.edit_requested))
        self.delete_btn = QPushButton('Löschen')
        self.delete_btn.setObjectName('danger')
        self.delete_btn.clicked.connect(lambda: self._emit(self.delete_requested))
        lay.addWidget(self.edit_btn, 1)
        lay.addWidget(self.delete_btn, 1)
        self.add(row)
        self._finds = {}
        self._show_current()

    def set_markers(self, markers, icon):
        finds = sorted((m for m in markers if m.get('kind') == 'fund'), key=lambda m: m.get('created', ''), reverse=True)
        self._finds = {m['id']: m for m in finds}
        current = self._current_id(self.list)
        self.list.clear()
        for m in finds:
            item = QListWidgetItem(icon, m['title'])
            item.setData(ROLE_ID, m['id'])
            item.setData(ROLE_SEARCH, (m['title'] + ' ' + m.get('note', '')).lower())
            item.setToolTip(m.get('note') or '')
            self.list.addItem(item)
            if m['id'] == current:
                self.list.setCurrentItem(item)
        self.empty.setVisible(not finds)
        self.count.setText(f'{len(finds)} Funde' if finds else '')
        self._filter(self.filter.text())
        self._show_current()

    def _show_current(self, *_):
        m = self._finds.get(self._current_id(self.list))
        self.edit_btn.setEnabled(m is not None)
        self.delete_btn.setEnabled(m is not None)
        if not m:
            self.detail.setText('')
            self.detail.hide()
            return
        date = (m.get('created') or '')[:10]
        note = m.get('note') or '<i>keine Notiz</i>'
        self.detail.setText(f"<b>{_esc(m['title'])}</b><br><span style='color:{theme.TEXT_FAINT}'>{date} · "
                            f"{m['lat']:.5f}, {m['lon']:.5f}</span><br>{_esc(note).replace(chr(10), '<br>') if m.get('note') else note}")
        self.detail.show()

    def _emit(self, signal):
        mid = self._current_id(self.list)
        if mid:
            signal.emit(mid)

    def _filter(self, text):
        text = text.strip().lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(bool(text) and text not in item.data(ROLE_SEARCH))


def _esc(text):
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


TRAVEL_MODES = [('foot', 'Zu Fuß'), ('bike', 'Fahrrad'), ('car', 'Auto')]


class NavigatorPanel(Panel, MarkerListMixin):
    """Route from the start over chosen points to the destination: shown in the app (OpenStreetMap
    routing) and handed to the phone as a Google Maps link (QR code), or saved as GPX."""
    center_requested = pyqtSignal(str)
    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    route_requested = pyqtSignal(str, list)      # travel mode, ids of the via points in order
    phone_requested = pyqtSignal(str, list)
    google_requested = pyqtSignal(str, list)
    gpx_requested = pyqtSignal(str, list)
    clear_requested = pyqtSignal()

    def __init__(self, travel_mode='foot'):
        super().__init__('Navigator', description='Start und Ziel per Rechtsklick auf die Karte. Ohne Start gilt '
                                                  'dein Standort bzw. das letzte Suchergebnis.')
        self.start_label = self.add(QLabel())
        self.ziel_label = self.add(QLabel())
        for lbl in (self.start_label, self.ziel_label):
            lbl.setWordWrap(True)
        self.add(section('Zwischenstopps'))
        self.list = self._make_list()
        self.list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.list.currentItemChanged.connect(self._update_buttons)
        self.list.setMinimumHeight(70)
        self.list.setToolTip('Häkchen = auf der Route. Reihenfolge per Ziehen ändern.')
        self.add(self.list, 1)
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        self.edit_btn = QPushButton('Bearbeiten')
        self.edit_btn.clicked.connect(lambda: self._emit_current(self.edit_requested))
        self.delete_btn = QPushButton('Löschen')
        self.delete_btn.setObjectName('danger')
        self.delete_btn.clicked.connect(lambda: self._emit_current(self.delete_requested))
        lay.addWidget(self.edit_btn, 1)
        lay.addWidget(self.delete_btn, 1)
        self.add(row)

        self.add(section('Fortbewegung'))
        modes = QWidget()
        ml = QHBoxLayout(modes)
        ml.setContentsMargins(0, 0, 0, 0)
        self.mode_group = QButtonGroup(self)
        for key, label in TRAVEL_MODES:
            rb = QRadioButton(label)
            rb.setProperty('mode', key)
            rb.setChecked(key == travel_mode)
            self.mode_group.addButton(rb)
            ml.addWidget(rb)
        ml.addStretch()
        self.add(modes)

        go = QPushButton('Route berechnen')
        go.setObjectName('primary')
        go.clicked.connect(lambda: self.route_requested.emit(self.mode(), self.via_ids()))
        self.add(go)
        self.result = self.add(QLabel(''))
        self.result.setObjectName('valueLabel')
        self.result.setWordWrap(True)
        self.add(divider())
        self.add(section('Aufs Handy'))
        phone = QPushButton('QR-Code für Google Maps')
        phone.setToolTip('Mit der Handykamera scannen: die Route öffnet sich in Google Maps auf dem Handy')
        phone.clicked.connect(lambda: self.phone_requested.emit(self.mode(), self.via_ids()))
        self.add(phone)
        row2 = QWidget()
        l2 = QHBoxLayout(row2)
        l2.setContentsMargins(0, 0, 0, 0)
        google = QPushButton('In Google Maps')
        google.setToolTip('Route im Browser in Google Maps öffnen')
        google.clicked.connect(lambda: self.google_requested.emit(self.mode(), self.via_ids()))
        gpx = QPushButton('GPX speichern')
        gpx.setToolTip('Für GPS-Geräte und Apps wie OsmAnd, Komoot oder Garmin')
        gpx.clicked.connect(lambda: self.gpx_requested.emit(self.mode(), self.via_ids()))
        l2.addWidget(google, 1)
        l2.addWidget(gpx, 1)
        self.add(row2)
        clear = QPushButton('Route von der Karte entfernen')
        clear.setObjectName('link')
        clear.clicked.connect(self.clear_requested)
        self.add(clear)
        self.set_endpoints(None, None)
        self._update_buttons()

    def mode(self):
        return self.mode_group.checkedButton().property('mode')

    def via_ids(self):
        return [self.list.item(i).data(ROLE_ID) for i in range(self.list.count())
                if self.list.item(i).checkState() == Qt.CheckState.Checked]

    def set_markers(self, markers, icon):
        order = [self.list.item(i).data(ROLE_ID) for i in range(self.list.count())]
        checked = set(self.via_ids())
        points = [m for m in markers if m.get('kind') == 'punkt']
        points.sort(key=lambda m: (order.index(m['id']) if m['id'] in order else len(order), m.get('created', '')))
        self.list.clear()
        for m in points:
            item = QListWidgetItem(icon, m['title'])
            item.setData(ROLE_ID, m['id'])
            item.setToolTip(m.get('note') or '')
            item.setFlags((item.flags() | Qt.ItemFlag.ItemIsUserCheckable) & ~Qt.ItemFlag.ItemIsDropEnabled)
            item.setCheckState(Qt.CheckState.Checked if m['id'] in checked else Qt.CheckState.Unchecked)
            self.list.addItem(item)
        self._update_buttons()

    def set_endpoints(self, start_text, ziel_text):
        green, red = '#7fb77e', theme.DANGER
        self.start_label.setText(f"<span style='color:{green}'>●</span> <b>Start:</b> " +
                                 (_esc(start_text) if start_text else f"<span style='color:{theme.TEXT_FAINT}'>noch keiner</span>"))
        self.ziel_label.setText(f"<span style='color:{red}'>●</span> <b>Ziel:</b> " +
                                (_esc(ziel_text) if ziel_text else f"<span style='color:{theme.TEXT_FAINT}'>noch keins</span>"))

    def set_result(self, text):
        self.result.setText(text)

    def _emit_current(self, signal):
        mid = self._current_id(self.list)
        if mid:
            signal.emit(mid)

    def _update_buttons(self, *_):
        has = self.list.currentItem() is not None
        self.edit_btn.setEnabled(has)
        self.delete_btn.setEnabled(has)


ANALYSIS_VIEWS = [
    ('', 'Aus', ''),
    ('combo', 'Kombiniert (empfohlen)',
     'Alle Verfahren in einem Bild, ähnlich der archäologischen VAT-Darstellung: Schummerung aus 8 Richtungen, '
     'Sky-View-Factor und Hangneigung als Graubild, eingefärbt mit dem Lokalen Relief – rötlich höher '
     '(Grabhügel, Wälle), bläulich tiefer (Gräben, Hohlwege, Gruben).'),
    ('lrm', 'Lokales Relief (LRM)',
     'Gelände minus geglättetes Gelände: Erhöhungen rot, Vertiefungen blau. Grabhügel, Wälle, Gräben und '
     'Ackerbeete von wenigen Dezimetern werden sichtbar, Berg und Tal verschwinden.'),
    ('multi', 'Schummerung aus 8 Richtungen',
     'Mittel aus acht Lichtrichtungen: nichts verschwindet, nur weil es parallel zum Licht verläuft.'),
    ('svf', 'Sky-View-Factor',
     'Wie viel Himmel von jedem Punkt sichtbar ist: Gräben, Hohlwege und Gruben dunkel, Wälle und Kuppen hell. '
     'Unabhängig von jeder Lichtrichtung.'),
    ('slope', 'Hangneigung',
     'Steile Kanten dunkel: Böschungen von Wällen, Terrassen und Gräben.'),
]


class LidarHere(QWidget):
    """The LiDAR choice for what is on screen now: a mirror of the full list in the map tab."""
    toggled = pyqtSignal(str, bool)       # region or base id, on
    opacity_changed = pyqtSignal(int)

    def __init__(self, opacity=100):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(QLabel('Deckkraft'))
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(10, 100)
        self.opacity.setValue(opacity)
        rl.addWidget(self.opacity, 1)
        self.value = QLabel(f'{opacity} %')
        self.value.setObjectName('valueLabel')
        self.value.setFixedWidth(40)
        rl.addWidget(self.value)
        self.opacity.valueChanged.connect(self._on_opacity)
        lay.addWidget(row)
        self.list = QTreeWidget()
        self.list.setColumnCount(2)
        self.list.setHeaderHidden(True)
        self.list.setRootIsDecorated(False)
        self.list.setIndentation(0)
        self.list.setUniformRowHeights(True)
        self.list.header().setStretchLastSection(False)
        self.list.header().setSectionResizeMode(0, self.list.header().ResizeMode.Stretch)
        self.list.header().setSectionResizeMode(1, self.list.header().ResizeMode.ResizeToContents)
        self.list.itemChanged.connect(self._on_changed)
        lay.addWidget(self.list)
        self.empty = hint('Hier gibt es kein LiDAR.')
        lay.addWidget(self.empty)
        self._filling = False

    def set_rows(self, rows):
        """rows: [(id, label, resolution, colour, checked)] for the regions in view."""
        self._filling = True
        self.list.clear()
        for rid, label, res, colour, checked in rows:
            item = QTreeWidgetItem([label, res])
            item.setData(0, ROLE_ID, rid)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            item.setForeground(1, QBrush(QColor(colour)))
            self.list.addTopLevelItem(item)
        row_h = self.list.sizeHintForRow(0) if rows else 28
        self.list.setFixedHeight(min(max(len(rows), 1), 8) * max(row_h, 20) + 6)
        self.list.setVisible(bool(rows))
        self.empty.setVisible(not rows)
        self._filling = False

    def set_opacity(self, value):
        self.opacity.blockSignals(True)
        self.opacity.setValue(value)
        self.value.setText(f'{value} %')
        self.opacity.blockSignals(False)

    def _on_opacity(self, value):
        self.value.setText(f'{value} %')
        self.opacity_changed.emit(value)

    def _on_changed(self, item, column):
        if not self._filling and column == 0:
            self.toggled.emit(item.data(0, ROLE_ID), item.checkState(0) == Qt.CheckState.Checked)


class AnalysisPanel(Panel):
    """Archaeological visualisations of the terrain, computed locally from the height data."""
    view_changed = pyqtSignal(str)       # '' = off
    opacity_changed = pyqtSignal(int)

    def __init__(self, opacity=85, lidar_opacity=100, view=''):
        super().__init__('Analyse', description='Spezial-Darstellungen, mit denen Archäologen Bodendenkmäler '
                                                'im LiDAR erkennen. Lokal berechnet, ohne KI. Ab Zoom 13.')
        views = QWidget()
        vl = QVBoxLayout(views)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(6)
        self.layout_views = vl
        self.group = QButtonGroup(self)
        self.explain = None
        for key, label, text in ANALYSIS_VIEWS:
            rb = QRadioButton(label)
            rb.setProperty('view', key)
            rb.setToolTip(text)
            rb.setChecked(key == (view if view in [k for k, _l, _t in ANALYSIS_VIEWS] else ''))
            self.group.addButton(rb)
            vl.addWidget(rb)
        self.explain = hint('')
        vl.addWidget(self.explain)
        self.legend = QLabel(
            "<span style='color:#2152a0'>■</span> tiefer &nbsp; "
            "<span style='color:#f6f4ee'>■</span> eben &nbsp; "
            "<span style='color:#962d19'>■</span> höher")
        self.legend.setObjectName('panelHint')
        vl.addWidget(self.legend)
        self.group.buttonToggled.connect(self._on_toggled)
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 6, 0, 0)
        lay.addWidget(QLabel('Deckkraft'))
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(20, 100)
        self.opacity.setValue(opacity)
        lay.addWidget(self.opacity, 1)
        value = QLabel(f'{opacity} %')
        value.setObjectName('valueLabel')
        value.setFixedWidth(40)
        self.opacity.valueChanged.connect(lambda v: (value.setText(f'{v} %'), self.opacity_changed.emit(v)))
        lay.addWidget(value)
        vl.addWidget(row)
        self.add(Collapsible('Analyse-Ansicht', views, expanded=True))

        # The LiDAR of the current view, coupled to the list in the map tab (same ticks, same opacity).
        self.lidar = LidarHere(lidar_opacity)
        self.add(Collapsible('LiDAR im Kartenausschnitt', self.lidar, expanded=True))
        self.add(hint('Höhendaten der Analyse: Mapterhorn (amtliche Geländemodelle, in Deutschland 1 m). Die '
                      'Analyse liegt über dem LiDAR; mit beiden Deckkraft-Reglern lassen sie sich mischen. '
                      'Auffälligkeiten sind kein Freibrief: Bodendenkmäler können auch unkartiert sein.'))
        self.layout_.addStretch()
        self._on_toggled()

    def current_view(self):
        btn = self.group.checkedButton()
        return btn.property('view') if btn else ''

    def set_view(self, key):
        for btn in self.group.buttons():
            if btn.property('view') == key:
                btn.setChecked(True)

    def _on_toggled(self, *_):
        btn = self.group.checkedButton()
        key = btn.property('view') if btn else ''
        self.explain.setText(next(t for k, _l, t in ANALYSIS_VIEWS if k == key))
        self.explain.setVisible(bool(key))
        self.legend.setVisible(key in ('lrm', 'combo'))
        if _:
            self.view_changed.emit(key)


class OfflinePanel(Panel):
    download_requested = pyqtSignal()
    offline_toggled = pyqtSignal(bool)
    open_folder_requested = pyqtSignal()
    details_requested = pyqtSignal()
    refresh_requested = pyqtSignal()

    def __init__(self):
        self.switch = ToggleSwitch()
        super().__init__('Offline', self.switch,
                         'Jede angesehene Geländekachel wird lokal gespeichert. Mit dem Schalter '
                         'zeigt die Karte nur noch Gespeichertes.')
        self.switch.setToolTip('Offline-Modus: nur gespeicherte Kacheln verwenden')
        self.switch.toggled.connect(self.offline_toggled)
        self.add(divider())
        self.add(section('Speicher'))
        self.stats = self.add(QLabel('–'))
        self.stats.setObjectName('valueLabel')
        self.stats.setWordWrap(True)
        refresh = QPushButton('Neu zählen')
        refresh.setObjectName('link')
        refresh.clicked.connect(self.refresh_requested)
        self.add(refresh)
        self.add(divider())
        self.add(section('Gebiet herunterladen'))
        self.add(hint('Lädt die Gelände-Kacheln des aktuellen Kartenausschnitts für einen '
                      'Zoombereich, z. B. vor einer Begehung ohne Netz. Größenordnung: '
                      '100 km² in 1 m ≈ 12 MB, in 25 cm ≈ 330 MB.'))
        dl = QPushButton('Ausschnitt herunterladen …')
        dl.setObjectName('primary')
        dl.clicked.connect(self.download_requested)
        self.add(dl)
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        folder = QPushButton('Ordner öffnen')
        folder.clicked.connect(self.open_folder_requested)
        details = QPushButton('Details')
        details.clicked.connect(self.details_requested)
        lay.addWidget(folder, 1)
        lay.addWidget(details, 1)
        self.add(row)
        self.layout_.addStretch()

    def set_stats(self, tiles, size_bytes, layers):
        merged = {}
        for key, v in layers.items():   # 256 and 512 px tiles of the same layer
            m = merged.setdefault(key.split('@')[0], {'bytes': 0})
            m['bytes'] += v['bytes']
        top = sorted(merged.items(), key=lambda kv: -kv[1]['bytes'])[:6]
        lines = [f'{tiles:,} Kacheln · {size_bytes / 1e9:.2f} GB'.replace(',', '.')]
        lines += [f'{k:<22}{v["bytes"] / 1e6:>8.0f} MB' for k, v in top]
        self.stats.setText('\n'.join(lines))
