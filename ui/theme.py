"""Colours and the application stylesheet."""
import os
import tempfile

from . import icons

# Warm graphite with one brass accent; the map is the colourful part of the window.
BG_DEEP = '#111316'     # header, rail, status bar
BG_PANEL = '#171a1e'    # side panel
BG_FIELD = '#1f2328'    # inputs, lists
BG_HOVER = '#262b31'
LINE = '#2a2f36'
LINE_STRONG = '#3a4049'
TEXT = '#e6e1d6'
TEXT_MUTED = '#9198a1'
TEXT_FAINT = '#646b74'
ACCENT = '#d4a24c'
ACCENT_HOVER = '#e2b462'
ACCENT_SOFT = '#3b311f'
OK = '#7fb77e'
DANGER = '#d0705f'

TITLE_FONT = 'Bahnschrift'
UI_FONT = 'Segoe UI'
MONO_FONT = 'Cascadia Mono, Consolas'


def stylesheet():
    img = icons.write_svg_files(os.path.join(tempfile.gettempdir(), 'treasure_hunter_ui'), {
        'check': ('check', BG_DEEP, 2.6),
        'dash': ('dash', BG_DEEP, 2.6),
        'arrow_closed': ('chevron-right', TEXT_MUTED, 2.0),
        'arrow_open': ('chevron-down', TEXT_MUTED, 2.0),
        'combo_arrow': ('chevron-down', TEXT_MUTED, 2.0),
    })
    return f"""
* {{ font-family: '{UI_FONT}'; font-size: 13px; color: {TEXT}; outline: none; }}
QMainWindow, QDialog, QMessageBox {{ background: {BG_PANEL}; }}
QToolTip {{ background: {BG_FIELD}; color: {TEXT}; border: 1px solid {LINE_STRONG}; padding: 4px 6px; }}

/* header */
#header {{ background: {BG_DEEP}; border-bottom: 1px solid {LINE}; }}
#appTitle {{ font-family: '{TITLE_FONT}'; font-size: 17px; font-weight: 600; letter-spacing: 3px; color: {TEXT}; }}
QToolButton#monumentButton {{ background: transparent; border: 1px solid {LINE_STRONG}; border-radius: 4px;
    padding: 5px 10px; color: {TEXT_MUTED}; font-weight: 600; }}
QToolButton#monumentButton:hover {{ border-color: {DANGER}; color: {TEXT}; }}
QToolButton#monumentButton:checked {{ background: {DANGER}; border-color: {DANGER}; color: {BG_DEEP}; }}
QToolButton#kindButton {{ background: {BG_FIELD}; border: 1px solid {LINE}; border-radius: 4px; padding: 6px 4px; }}
QToolButton#kindButton:hover {{ border-color: {LINE_STRONG}; }}
QToolButton#kindButton:checked {{ border: 1px solid {ACCENT}; background: {ACCENT_SOFT}; }}
QLabel#findDetail {{ background: {BG_FIELD}; border: 1px solid {LINE}; border-radius: 4px; padding: 8px; }}
QPlainTextEdit {{ background: {BG_FIELD}; border: 1px solid {LINE}; border-radius: 4px; padding: 4px; }}
QPlainTextEdit:focus {{ border-color: {ACCENT}; }}
QToolButton#locateButton {{ background: {BG_FIELD}; border: 1px solid {LINE}; border-radius: 4px; padding: 6px 10px; }}
QToolButton#locateButton:hover {{ border-color: {ACCENT}; }}
#busyLabel {{ color: {ACCENT}; font-size: 12px; }}
#appSubtitle {{ color: {TEXT_FAINT}; font-size: 12px; }}
#searchBox {{ background: {BG_FIELD}; border: 1px solid {LINE}; border-radius: 4px; padding: 6px 10px 6px 30px; min-width: 320px; }}
#searchBox:focus {{ border-color: {ACCENT}; }}

/* rail */
#rail {{ background: {BG_DEEP}; border-right: 1px solid {LINE}; }}
#rail QToolButton {{ border: 1px solid transparent; border-radius: 5px; padding: 8px 2px; color: {TEXT_FAINT}; font-size: 11px; }}
#rail QToolButton:hover {{ background: {BG_PANEL}; color: {TEXT_MUTED}; }}
#rail QToolButton:checked {{ border: 1px solid {OK}; background: {BG_PANEL}; color: {TEXT}; }}

/* side panel */
#sidePanel {{ background: {BG_PANEL}; border-right: 1px solid {LINE}; }}
#sidePanel QScrollArea, #sidePanel QScrollArea > QWidget > QWidget {{ background: {BG_PANEL}; }}
#sidePanel QScrollArea > QScrollBar:vertical {{ width: 6px; margin: 4px 3px 4px 0; background: transparent; }}
#sidePanel QScrollArea > QScrollBar::handle:vertical {{ background: {LINE}; border-radius: 3px; margin: 0; }}
#sidePanel QScrollArea > QScrollBar::handle:vertical:hover {{ background: {LINE_STRONG}; }}
#panelTitle {{ font-family: '{TITLE_FONT}'; font-size: 15px; font-weight: 600; letter-spacing: 1px; }}
#panelHint {{ color: {TEXT_FAINT}; font-size: 12px; }}
#sectionLabel {{ font-family: '{TITLE_FONT}'; font-size: 11px; letter-spacing: 1.5px; color: {TEXT_MUTED}; padding-top: 6px; }}
QToolButton#sectionToggle {{ background: transparent; border: none; border-bottom: 1px solid {LINE};
    text-align: left; padding: 10px 0 5px 0; font-family: '{TITLE_FONT}'; font-size: 13px; font-weight: 600;
    letter-spacing: 1.5px; color: {ACCENT}; }}
QToolButton#sectionToggle:hover {{ color: {ACCENT_HOVER}; }}
#muted {{ color: {TEXT_MUTED}; }}
#valueLabel {{ color: {TEXT_MUTED}; font-family: {MONO_FONT}; font-size: 12px; }}
QFrame#divider {{ background: {LINE}; max-height: 1px; min-height: 1px; border: none; }}

QLineEdit, QComboBox, QSpinBox {{
    background: {BG_FIELD}; border: 1px solid {LINE}; border-radius: 4px; padding: 5px 8px;
    selection-background-color: {ACCENT_SOFT}; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow {{ image: url({img['combo_arrow']}); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{ background: {BG_FIELD}; border: 1px solid {LINE_STRONG}; selection-background-color: {BG_HOVER}; }}

QPushButton {{ background: {BG_FIELD}; border: 1px solid {LINE_STRONG}; border-radius: 4px; padding: 6px 12px; }}
QPushButton:hover {{ background: {BG_HOVER}; }}
QPushButton:pressed {{ background: {LINE}; }}
QPushButton:disabled {{ color: {TEXT_FAINT}; border-color: {LINE}; }}
QPushButton#primary {{ background: {ACCENT}; border-color: {ACCENT}; color: {BG_DEEP}; font-weight: 600; }}
QPushButton#primary:hover {{ background: {ACCENT_HOVER}; border-color: {ACCENT_HOVER}; }}
QPushButton#danger:hover {{ border-color: {DANGER}; color: {DANGER}; }}
QPushButton#link {{ background: transparent; border: none; color: {TEXT_MUTED}; padding: 2px 4px; }}
QPushButton#link:hover {{ color: {ACCENT}; }}
QToolButton#iconButton {{ background: transparent; border: none; border-radius: 4px; padding: 5px; }}
QToolButton#iconButton:hover {{ background: {BG_HOVER}; }}
QToolButton#iconButton:checked {{ background: {ACCENT_SOFT}; }}

QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator, QTreeView::indicator, QListView::indicator {{ width: 14px; height: 14px; border: 1px solid {LINE_STRONG}; border-radius: 3px; background: {BG_FIELD}; }}
QCheckBox::indicator:hover, QTreeView::indicator:hover, QListView::indicator:hover {{ border-color: {ACCENT}; }}
QCheckBox::indicator:checked, QTreeView::indicator:checked, QListView::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; image: url({img['check']}); }}
QTreeView::indicator:indeterminate {{ background: {ACCENT}; border-color: {ACCENT}; image: url({img['dash']}); }}
QTreeView::indicator:disabled {{ background: transparent; border-color: {LINE}; }}

QRadioButton {{ spacing: 8px; padding: 3px 0; }}
QRadioButton::indicator {{ width: 12px; height: 12px; border: 1px solid {LINE_STRONG}; border-radius: 7px; background: {BG_FIELD}; }}
QRadioButton::indicator:checked {{ border: 4px solid {ACCENT}; background: {BG_DEEP}; width: 6px; height: 6px; }}

QTreeView, QListView, QListWidget, QTreeWidget {{
    background: transparent; border: none; show-decoration-selected: 1; }}
QTreeView::item, QListWidget::item {{ padding: 4px 2px; border-radius: 3px; }}
QTreeView::item:hover, QListWidget::item:hover {{ background: {BG_HOVER}; }}
QTreeView::item:selected, QListWidget::item:selected {{ background: {ACCENT_SOFT}; color: {TEXT}; }}
QTreeView::branch {{ background: transparent; }}
QTreeView::branch:has-children:closed {{ image: url({img['arrow_closed']}); }}
QTreeView::branch:has-children:open {{ image: url({img['arrow_open']}); }}

QSlider::groove:horizontal {{ height: 3px; background: {LINE_STRONG}; border-radius: 1px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 1px; }}
QSlider::handle:horizontal {{ background: {TEXT}; width: 12px; height: 12px; margin: -5px 0; border-radius: 6px; }}
QSlider::handle:horizontal:hover {{ background: {ACCENT_HOVER}; }}

QScrollBar:vertical {{ background: transparent; width: 9px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {LINE_STRONG}; border-radius: 4px; min-height: 24px; margin: 2px; }}
QScrollBar::handle:vertical:hover {{ background: {TEXT_FAINT}; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ background: none; height: 0; width: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 9px; }}
QScrollBar::handle:horizontal {{ background: {LINE_STRONG}; border-radius: 4px; min-width: 24px; margin: 2px; }}

QProgressBar {{ background: {BG_FIELD}; border: none; border-radius: 2px; height: 4px; text-align: center; color: transparent; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 2px; }}

/* status bar and log */
QStatusBar {{ background: {BG_DEEP}; border-top: 1px solid {LINE}; color: {TEXT_MUTED}; }}
QStatusBar::item {{ border: none; }}
QStatusBar QLabel {{ color: {TEXT_MUTED}; font-size: 12px; padding: 0 8px; }}
QStatusBar QToolButton#coords {{ font-family: {MONO_FONT}; }}
QLabel#emptyHint {{ color: {ACCENT}; background: {ACCENT_SOFT}; border-radius: 4px; padding: 6px 8px; }}
QSplitter::handle:horizontal {{ background: {LINE}; }}
QSplitter::handle:horizontal:hover {{ background: {ACCENT}; }}
QStatusBar QToolButton {{ background: transparent; border: none; color: {TEXT_MUTED}; padding: 2px 8px; font-size: 12px; }}
QStatusBar QToolButton:hover, QStatusBar QToolButton:checked {{ color: {TEXT}; background: {BG_PANEL}; }}
#logPanel {{ background: {BG_DEEP}; border-top: 1px solid {LINE}; }}
QTextEdit#logConsole {{ background: {BG_DEEP}; border: none; color: {TEXT_MUTED}; font-family: {MONO_FONT}; font-size: 12px; padding: 4px 8px; }}
QSplitter::handle {{ background: {LINE}; }}

QMenu {{ background: {BG_FIELD}; border: 1px solid {LINE_STRONG}; padding: 4px; }}
QMenu::item {{ padding: 5px 18px; border-radius: 3px; }}
QMenu::item:selected {{ background: {BG_HOVER}; }}
QMenu::separator {{ height: 1px; background: {LINE}; margin: 4px 6px; }}
"""
