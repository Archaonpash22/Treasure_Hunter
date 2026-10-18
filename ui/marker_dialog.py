"""Dialog for a new or edited marker: kind (start, destination, point, find), title and note."""
import os

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QButtonGroup, QDialog, QDialogButtonBox, QGridLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPlainTextEdit, QToolButton, QVBoxLayout)

from .widgets import hint

MARKER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'vectors', 'markers')

# kind -> (label, explanation)
MARKER_KINDS = {
    'start': ('Start', 'Startpunkt für den Navigator. Ersetzt einen vorhandenen Start.'),
    'ziel': ('Ziel', 'Ziel für den Navigator. Ersetzt ein vorhandenes Ziel.'),
    'punkt': ('Punkt', 'Merkpunkt, z. B. Parkplatz oder Verdachtsstelle; im Navigator als Zwischenstopp nutzbar.'),
    'fund': ('Fund', 'Etwas, das du gefunden hast. Erscheint unter „Meine Funde“.'),
}


def marker_icon(kind):
    return QIcon(os.path.join(MARKER_DIR, f'{kind}.svg'))


class MarkerDialog(QDialog):
    def __init__(self, lat, lon, marker=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Marker bearbeiten' if marker else 'Neuer Marker')
        self.setModal(True)
        self.setMinimumWidth(420)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 14)
        lay.setSpacing(10)

        pos = QLabel(f'{lat:.5f}, {lon:.5f}')
        pos.setObjectName('valueLabel')
        lay.addWidget(pos)

        grid = QGridLayout()
        grid.setSpacing(6)
        self.kinds = QButtonGroup(self)
        current = (marker or {}).get('kind', 'punkt')
        for i, (kind, (label, tip)) in enumerate(MARKER_KINDS.items()):
            btn = QToolButton()
            btn.setObjectName('kindButton')
            btn.setText(label)
            btn.setIcon(marker_icon(kind))
            btn.setIconSize(QSize(24, 32))
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            btn.setCheckable(True)
            btn.setToolTip(tip)
            btn.setMinimumWidth(86)
            btn.setProperty('kind', kind)
            btn.setChecked(kind == current)
            self.kinds.addButton(btn)
            grid.addWidget(btn, 0, i)
        lay.addLayout(grid)
        self.kind_hint = hint('')
        lay.addWidget(self.kind_hint)
        self.kinds.buttonToggled.connect(self._update_hint)

        lay.addWidget(QLabel('Titel'))
        self.title = QLineEdit((marker or {}).get('title', ''))
        self.title.setPlaceholderText('z. B. Parkplatz Waldrand, Bronzefibel, Hügel am Bach …')
        lay.addWidget(self.title)
        lay.addWidget(QLabel('Notiz'))
        self.note = QPlainTextEdit((marker or {}).get('note', ''))
        self.note.setPlaceholderText('Beschreibung, Tiefe, Bodenart, Fundumstände, Ansprechpartner …')
        self.note.setFixedHeight(110)
        lay.addWidget(self.note)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok = buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok.setText('Speichern')
        ok.setObjectName('primary')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Abbrechen')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)
        self._update_hint()
        self.title.setFocus()

    def _update_hint(self, *_):
        btn = self.kinds.checkedButton()
        self.kind_hint.setText(MARKER_KINDS[btn.property('kind')][1] if btn else '')

    def get_data(self):
        kind = self.kinds.checkedButton().property('kind')
        return {
            'kind': kind,
            'title': self.title.text().strip() or MARKER_KINDS[kind][0],
            'note': self.note.toPlainText().strip(),
        }
