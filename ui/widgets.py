"""Small building blocks shared by the panels."""
from PyQt6.QtCore import QPropertyAnimation, QRectF, QSize, Qt, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (QAbstractButton, QFrame, QHBoxLayout, QLabel, QLineEdit, QSizePolicy,
                             QToolButton, QVBoxLayout, QWidget)

from . import icons, theme


class ToggleSwitch(QAbstractButton):
    """Compact on/off switch."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pos = 0.0
        self._anim = QPropertyAnimation(self, b'knob', self)
        self._anim.setDuration(120)
        self.toggled.connect(self._animate)

    def sizeHint(self):
        return QSize(34, 18)

    def _animate(self, on):
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def setChecked(self, on):
        super().setChecked(on)
        self._anim.stop()
        self._pos = 1.0 if on else 0.0
        self.update()

    def _get_knob(self):
        return self._pos

    def _set_knob(self, value):
        self._pos = value
        self.update()

    knob = pyqtProperty(float, _get_knob, _set_knob)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        off, on = QColor(theme.LINE_STRONG), QColor(theme.ACCENT)
        track = QColor(int(off.red() + (on.red() - off.red()) * self._pos),
                       int(off.green() + (on.green() - off.green()) * self._pos),
                       int(off.blue() + (on.blue() - off.blue()) * self._pos))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        d = r.height() - 4
        x = r.left() + 2 + (r.width() - d - 4) * self._pos
        p.setBrush(QColor(theme.BG_DEEP if self.isChecked() else theme.TEXT))
        p.drawEllipse(QRectF(x, r.top() + 2, d, d))


def divider():
    line = QFrame()
    line.setObjectName('divider')
    return line


def section(text):
    label = QLabel(text.upper())
    label.setObjectName('sectionLabel')
    return label


def hint(text):
    label = QLabel(text)
    label.setObjectName('panelHint')
    label.setWordWrap(True)
    return label


def icon_button(name, tooltip, checkable=False, size=18):
    btn = QToolButton()
    btn.setObjectName('iconButton')
    btn.setIcon(icons.icon(name, theme.TEXT_MUTED, theme.ACCENT if checkable else theme.TEXT, size))
    btn.setIconSize(QSize(size, size))
    btn.setToolTip(tooltip)
    btn.setCheckable(checkable)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def search_field(placeholder):
    field = QLineEdit()
    field.setPlaceholderText(placeholder)
    field.setClearButtonEnabled(True)
    field.addAction(icons.icon('search', theme.TEXT_FAINT, size=14), QLineEdit.ActionPosition.LeadingPosition)
    return field


def title_row(title, right_widget=None):
    row = QWidget()
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 0, 0, 0)
    label = QLabel(title)
    label.setObjectName('panelTitle')
    lay.addWidget(label)
    lay.addStretch()
    if right_widget is not None:
        lay.addWidget(right_widget)
    return row


class BusyIndicator(QWidget):
    """'Bitte warten' with a running bar while any background job is busy. Jobs register by key."""

    def __init__(self, parent=None):
        super().__init__(parent)
        from PyQt6.QtWidgets import QProgressBar
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.bar = QProgressBar()
        self.bar.setRange(0, 0)
        self.bar.setFixedSize(90, 3)
        self.label = QLabel()
        self.label.setObjectName('busyLabel')
        lay.addWidget(self.bar)
        lay.addWidget(self.label)
        self._jobs = {}
        self.hide()

    def start(self, key, text):
        self._jobs.pop(key, None)
        self._jobs[key] = text   # newest job is shown
        self._refresh()

    def stop(self, key):
        if self._jobs.pop(key, None) is not None:
            self._refresh()

    def _refresh(self):
        if not self._jobs:
            self.hide()
            return
        self.label.setText('Bitte warten – ' + list(self._jobs.values())[-1])
        self.show()


class Collapsible(QWidget):
    """Section with a clickable header that shows or hides its content."""
    toggled = pyqtSignal(bool)

    def __init__(self, title, content, expanded=True, grow=False, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.button = QToolButton()
        self.button.setObjectName('sectionToggle')
        self.button.setText(title.upper())
        self.button.setCheckable(True)
        self.button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.button.setIconSize(QSize(12, 12))
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        lay.addWidget(self.button)
        self.content = content
        lay.addWidget(content, 1)
        self._grow = grow
        self.button.setChecked(expanded)
        self._apply(expanded)
        self.button.toggled.connect(self._on_toggled)

    def _on_toggled(self, on):
        self._apply(on)
        self.toggled.emit(on)

    def _apply(self, on):
        self.content.setVisible(on)
        self.button.setIcon(icons.icon('chevron-down' if on else 'chevron-right', theme.ACCENT, size=12, stroke=2.4))
        # Only an open section with a list may take the free height; closed ones shrink to the header.
        v = QSizePolicy.Policy.Expanding if (on and self._grow) else QSizePolicy.Policy.Maximum
        self.setSizePolicy(QSizePolicy.Policy.Preferred, v)
