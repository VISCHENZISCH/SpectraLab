"""Icônes vectorielles (trait 24×24, style « line ») rendues en pixmaps haute densité."""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from . import theme

_PATHS: dict[str, str] = {
    "home": '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9v11a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1V9"/>',
    "tag": '<path d="M3 12V4a1 1 0 0 1 1-1h8l9 9-9 9z"/><circle cx="7.5" cy="7.5" r="1.5"/>',
    "image": '<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="9" cy="9" r="2"/><path d="m21 15-5-5L5 21"/>',
    "audio": '<path d="M2 10v4M6 7v10M10 4v16M14 8v8M18 6v12M22 10v4"/>',
    "video": '<rect x="2" y="6" width="14" height="12" rx="2"/><path d="m16 10 6-3.5v11L16 14"/>',
    "shield": '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z"/><path d="m9 12 2 2 4-4"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 16v-4M12 8h.01"/>',
    "upload": '<path d="M12 15V3M7 8l5-5 5 5"/><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "trash": '<path d="M3 6h18M8 6V4h8v2M6 6l1 14a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-14"/>',
    "x": '<path d="M18 6 6 18M6 6l12 12"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    "sparkles": '<path d="M11 3l1.8 4.7 4.7 1.8-4.7 1.8L11 16l-1.8-4.7L4.5 9.5l4.7-1.8z"/>'
    '<path d="M19 14l.8 2.2 2.2.8-2.2.8L19 20l-.8-2.2L16 17l2.2-.8z"/>',
    "eye": '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    "arrow": '<path d="M7 17 17 7M8 7h9v9"/>',
    "check": '<path d="m5 12 5 5L20 7"/>',
    "alert": '<path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17h.01"/>',
    "edit": '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="m13 7 4 4"/>',
    "folder": '<path d="M3 6a1 1 0 0 1 1-1h5l2 2h9a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/>',
    "lock": '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    "cpu": '<rect x="6" y="6" width="12" height="12" rx="2"/>'
    '<path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>',
    "chart": '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    "resize": '<path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>',
    "refresh": '<path d="M3 12a9 9 0 0 1 15.5-6.2L21 8M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15.5 6.2L3 16M3 21v-5h5"/>',
    "wave": '<path d="M2 12h3l2-6 3 12 3-9 2 6 2-3h5"/>',
    "play": '<path d="M7 4.5v15a.8.8 0 0 0 1.2.7l12-7.5a.8.8 0 0 0 0-1.4l-12-7.5A.8.8 0 0 0 7 4.5z"/>',
    "pause": '<rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/>',
    "stop": '<rect x="5" y="5" width="14" height="14" rx="2"/>',
    "download": '<path d="M12 3v12M7 10l5 5 5-5"/><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>',
    "copy": '<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/>',
    "fingerprint": '<path d="M12 11v3a8 8 0 0 1-2 5M8 11a4 4 0 0 1 8 0v2M5 9a7.5 7.5 0 0 1 14 0'
    'M4 15c.5-1.5 1-3 1-5M19 15c0 2-.5 3.5-1.2 5M15.5 16c-.2 1.8-.8 3.4-1.7 4.8"/>',
    "layers": '<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/>',
    "phase": '<path d="M2 12c2.5-6 5-6 7.5 0s5 6 7.5 0 4-4 5-2"/><path d="M2 12c2.5 6 5 6 7.5 0" opacity=".45"/>',
    "volume": '<path d="M4 9v6h4l5 4V5L8 9z"/><path d="M16.5 8.5a5 5 0 0 1 0 7M19 6a8.5 8.5 0 0 1 0 12"/>',
    "binary": '<rect x="4" y="3" width="5" height="8" rx="2.5"/><path d="M15 3v8M13 3h2M17 21v-8M15 13h2"/>'
    '<rect x="4" y="13" width="5" height="8" rx="2.5"/>',
}

LOGO_SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
<path d="M4 14V4h10M34 4h10v10M44 34v10H34M14 44H4V34" fill="none" stroke="{theme.TEXT}" stroke-width="2.5"/>
<circle cx="38.5" cy="9.5" r="2" fill="{theme.CORAL}"/>
<path d="M7 24C12 15.5 17.5 12 24 12s12 3.5 17 12c-5 8.5-10.5 12-17 12S12 32.5 7 24Z"
      fill="none" stroke="{theme.LIME}" stroke-width="2.5" stroke-linejoin="round"/>
<circle cx="24" cy="24" r="7.75" fill="{theme.BG}" stroke="{theme.VIOLET}" stroke-width="1.5"/>
<g fill="{theme.LIME}">
<rect x="18.2" y="22" width="1.6" height="4" rx="0.8"/><rect x="20.7" y="19.5" width="1.6" height="9" rx="0.8"/>
<rect x="23.2" y="18" width="1.6" height="12" rx="0.8"/><rect x="25.7" y="20.5" width="1.6" height="7" rx="0.8"/>
<rect x="28.2" y="22.5" width="1.6" height="3" rx="0.8"/>
</g></svg>"""

_RENDER_SCALE = 3  # rendu à 3× : net sur les écrans haute densité


def _render(svg: str, size: int) -> QPixmap:
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(size * _RENDER_SCALE, size * _RENDER_SCALE)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, pixmap.width(), pixmap.height()))
    painter.end()
    pixmap.setDevicePixelRatio(_RENDER_SCALE)
    return pixmap


@lru_cache(maxsize=256)
def pixmap(name: str, color: str = theme.TEXT, size: int = 20, stroke: float = 1.8) -> QPixmap:
    body = _PATHS[name]
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )
    return _render(svg, size)


def icon(name: str, color: str = theme.TEXT, size: int = 20) -> QIcon:
    return QIcon(pixmap(name, color, size))


@lru_cache(maxsize=8)
def logo_pixmap(size: int = 48) -> QPixmap:
    return _render(LOGO_SVG, size)
