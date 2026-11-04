"""Line icons (24x24, stroke only), tinted at runtime."""
from PyQt6.QtCore import QByteArray, QRectF, Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

_PATHS = {
    'terrain': '<path d="M2.5 19.5 9 8.5l3.6 6.1L15 10.5l6.5 9z"/><path d="M7.1 11.8 9 13l1.4-1"/>',
    'map': '<path d="M9 4.5 3.5 6.8v13l5.5-2.3 6 2.3 5.5-2.3v-13L15 6.8z"/><path d="M9 4.5v13M15 6.8v13"/>',
    'sites': '<path d="M3 20.5h18M5 17.5h14M6.5 17.5v-7M10 17.5v-7M14 17.5v-7M17.5 17.5v-7M4 10.5h16L12 4.5z"/>',
    'pin': '<path d="M12 21s-6.5-5.7-6.5-11a6.5 6.5 0 0 1 13 0c0 5.3-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.3"/>',
    'offline': '<path d="M12 3.5v10.5M7.5 9.5 12 14l4.5-4.5"/><path d="M4 15.5v3.5h16v-3.5"/>',
    'search': '<circle cx="10.8" cy="10.8" r="6.3"/><path d="m15.5 15.5 5 5"/>',
    'locate': '<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/>',
    'log': '<rect x="3.5" y="4.5" width="17" height="15" rx="1.5"/><path d="m7.5 9.5 3 2.5-3 2.5M12.5 15h4"/>',
    'check': '<path d="m5.5 12.5 4 4L18.5 7.5"/>',
    'dash': '<path d="M6.5 12h11"/>',
    'chevron-right': '<path d="m9.5 6 6 6-6 6"/>',
    'chevron-down': '<path d="m6 9.5 6 6 6-6"/>',
    'trash': '<path d="M4.5 6.5h15M9.5 6.5V4.5h5v2M6.5 6.5l1 13h9l1-13M10.5 10v6M13.5 10v6"/>',
    'route': '<path d="M3.5 11 20.5 3.5 13 20.5l-2-7.5z"/>',
    'focus': '<path d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5"/>',
    'folder': '<path d="M3.5 6.5v12h17v-10h-8l-2-2.5h-7z"/>',
    'info': '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5M12 7.8v.2"/>',
    'close': '<path d="m6.5 6.5 11 11M17.5 6.5l-11 11"/>',
    'layers': '<path d="m12 4 8.5 4.5L12 13 3.5 8.5z"/><path d="m3.5 12.5 8.5 4.5 8.5-4.5"/><path d="m3.5 16.5 8.5 4.5 8.5-4.5"/>',
    'monument': '<path d="M12 3 4.5 6v5.5c0 4.6 3.2 8.2 7.5 9.5 4.3-1.3 7.5-4.9 7.5-9.5V6z"/><path d="M12 8v5M12 16.2v.2"/>',
    'analysis': '<path d="M3.5 18.5c2.5 0 3-3 5.5-3s3 3 5.5 3 3-3 5.5-3"/><path d="M3.5 12.5c2.5 0 3-3 5.5-3s3 3 5.5 3 3-3 5.5-3"/><circle cx="16.5" cy="5.5" r="2"/>',
    'more': '<circle cx="5.5" cy="12" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="18.5" cy="12" r="1.2"/>',
    'compass': '<circle cx="12" cy="12" r="9"/><path d="m15.6 8.4-2.2 5-5 2.2 2.2-5z"/>',
}


def svg(name, color, stroke=1.7):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">'
            f'{_PATHS[name]}</svg>')


def pixmap(name, color, size=18, stroke=1.7, ratio=2.0):
    renderer = QSvgRenderer(QByteArray(svg(name, color, stroke).encode()))
    pm = QPixmap(int(size * ratio), int(size * ratio))
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    renderer.render(painter, QRectF(0, 0, pm.width(), pm.height()))
    painter.end()
    pm.setDevicePixelRatio(ratio)
    return pm


def icon(name, color, active_color=None, size=18, stroke=1.7):
    """Icon in `color`; `active_color` is used when the button is checked."""
    ic = QIcon()
    ic.addPixmap(pixmap(name, color, size, stroke), QIcon.Mode.Normal, QIcon.State.Off)
    ic.addPixmap(pixmap(name, active_color or color, size, stroke), QIcon.Mode.Normal, QIcon.State.On)
    return ic


def write_svg_files(folder, colors):
    """SVG files for stylesheet images (checkbox marks, tree arrows); returns {name: path}."""
    import os
    os.makedirs(folder, exist_ok=True)
    paths = {}
    for key, (name, color, stroke) in colors.items():
        path = os.path.join(folder, key + '.svg')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(svg(name, color, stroke))
        paths[key] = path.replace('\\', '/')
    return paths
