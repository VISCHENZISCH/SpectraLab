"""Icônes de SpectraLab, dessinées pour l'application (grille 24×24).

Style « trait » : un seul tracé de 1,5 px, arrondi, d'une seule couleur.
Les détails (``accent``) sont dessinés dans la même couleur ; l'aplat
(``fill``) n'est utilisé que pour les symboles pleins (lecture, pause).
"""

from __future__ import annotations

from functools import lru_cache
from typing import NamedTuple

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from . import theme


class _Glyph(NamedTuple):
    stroke: str
    fill: str = ""
    accent: str = ""


_GLYPHS: dict[str, _Glyph] = {
    "home": _Glyph(
        '<path d="M4 10.5 12 4l8 6.5V19a1 1 0 0 1-1 1h-4.5v-5h-5v5H5a1 1 0 0 1-1-1z"/>',
        '<path d="M4 10.5 12 4l8 6.5V19a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1z"/>',
        '<circle cx="12" cy="10.2" r="1.5"/>',
    ),
    "tag": _Glyph(
        '<path d="M3.5 12.2V5A1.5 1.5 0 0 1 5 3.5h7.2l8.3 8.3-8.7 8.7z"/>',
        '<path d="M3.5 12.2V5A1.5 1.5 0 0 1 5 3.5h7.2l8.3 8.3-8.7 8.7z"/>',
        '<circle cx="8.2" cy="8.2" r="1.7"/>',
    ),
    "image": _Glyph(
        '<rect x="3.5" y="4.5" width="17" height="15" rx="3"/><path d="m3.8 16.5 4.7-4.3 4 3.5 2.8-2.3 4.9 4"/>',
        '<path d="m3.8 16.5 4.7-4.3 4 3.5 2.8-2.3 4.9 4v.1a2.5 2.5 0 0 1-2.5 2H6.3a2.5 2.5 0 0 1-2.5-2z"/>',
        '<circle cx="15.8" cy="9.2" r="1.7"/>',
    ),
    "audio": _Glyph(
        '<path d="M4 10.5v3M8 7.5v9M16 8.5v7M20 10.5v3"/>',
        "",
        '<path d="M12 4.5v15" fill="none"/>',
    ),
    "video": _Glyph(
        '<rect x="3" y="6.5" width="13" height="11" rx="2.5"/>'
        '<path d="m16 10.4 4.3-2.5a.6.6 0 0 1 .9.5v7.2a.6.6 0 0 1-.9.5L16 13.6"/>',
        '<rect x="3" y="6.5" width="13" height="11" rx="2.5"/>',
        '<circle cx="7" cy="10.2" r="1.4"/>',
    ),
    "shield": _Glyph(
        '<path d="M12 3.5 5 6.2v5.6c0 4.3 2.9 7.4 7 8.7 4.1-1.3 7-4.4 7-8.7V6.2z"/>',
        '<path d="M12 3.5 5 6.2v5.6c0 4.3 2.9 7.4 7 8.7 4.1-1.3 7-4.4 7-8.7V6.2z"/>',
        '<path d="m9.2 12.2 2 2 3.6-3.8" fill="none"/>',
    ),
    "info": _Glyph(
        '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5"/>',
        '<circle cx="12" cy="12" r="8.5"/>',
        '<circle cx="12" cy="7.9" r="1.2"/>',
    ),
    "upload": _Glyph(
        '<path d="M12 14.5V4.5M7.8 8.7 12 4.5l4.2 4.2"/><path d="M4 14.5V18a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3.5"/>',
        '<path d="M4 14.5V18a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3.5z"/>',
        '<circle cx="12" cy="17.3" r="1.2"/>',
    ),
    "plus": _Glyph('<path d="M12 5.5v13M5.5 12h13"/>'),
    "trash": _Glyph(
        '<path d="M4 7h16M9.5 7V4.5h5V7"/>'
        '<path d="m6.5 7 .9 12a1.5 1.5 0 0 0 1.5 1.4h6.2a1.5 1.5 0 0 0 1.5-1.4l.9-12"/>',
        '<path d="m6.5 7 .9 12a1.5 1.5 0 0 0 1.5 1.4h6.2a1.5 1.5 0 0 0 1.5-1.4l.9-12z"/>',
        '<path d="M10.5 11v5.5M13.5 11v5.5" fill="none"/>',
    ),
    "x": _Glyph('<path d="M17 7 7 17M7 7l10 10"/>'),
    "search": _Glyph(
        '<circle cx="10.5" cy="10.5" r="6.2"/><path d="m15.2 15.2 4.8 4.8"/>',
        '<circle cx="10.5" cy="10.5" r="6.2"/>',
        '<path d="M7.6 9.6a3.2 3.2 0 0 1 2.4-2.3" fill="none"/>',
    ),
    "sparkles": _Glyph(
        '<path d="m10 3.5 1.7 4.6 4.6 1.7-4.6 1.7L10 16.1l-1.7-4.6-4.6-1.7 4.6-1.7z"/>',
        '<path d="m10 3.5 1.7 4.6 4.6 1.7-4.6 1.7L10 16.1l-1.7-4.6-4.6-1.7 4.6-1.7z"/>',
        '<path d="m18 14 .8 2.2 2.2.8-2.2.8L18 20l-.8-2.2-2.2-.8 2.2-.8z"/>',
    ),
    "eye": _Glyph(
        '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/>'
        '<circle cx="12" cy="12" r="3"/>',
        '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/>',
        '<circle cx="12" cy="12" r="1.3"/>',
    ),
    "arrow": _Glyph('<path d="M7 17 17 7M9 7h8v8"/>'),
    "check": _Glyph('<path d="m5 12.5 4.5 4.5L19 7.5"/>'),
    "alert": _Glyph(
        '<path d="M10.3 4.2 2.9 17.5a2 2 0 0 0 1.7 3h14.8a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0z"/>'
        '<path d="M12 9.5V14"/>',
        '<path d="M10.3 4.2 2.9 17.5a2 2 0 0 0 1.7 3h14.8a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0z"/>',
        '<circle cx="12" cy="17" r="1.1"/>',
    ),
    "edit": _Glyph(
        '<path d="M4 20h4.2L19 9.2a2.1 2.1 0 0 0 0-3L17.8 5a2.1 2.1 0 0 0-3 0L4 15.8z"/>',
        '<path d="M4 20h4.2L19 9.2a2.1 2.1 0 0 0 0-3L17.8 5a2.1 2.1 0 0 0-3 0L4 15.8z"/>',
        '<path d="m13.5 6.5 4 4" fill="none"/>',
    ),
    "folder": _Glyph(
        '<path d="M3.5 7A1.5 1.5 0 0 1 5 5.5h4.4l2 2H19a1.5 1.5 0 0 1 1.5 1.5v8.5A1.5 1.5 0 0 1 19 19H5'
        'a1.5 1.5 0 0 1-1.5-1.5z"/>',
        '<path d="M3.5 10.5h17v7A1.5 1.5 0 0 1 19 19H5a1.5 1.5 0 0 1-1.5-1.5z"/>',
        '<path d="M3.5 10.5h17" fill="none"/>',
    ),
    "lock": _Glyph(
        '<rect x="5" y="10.5" width="14" height="10" rx="2.5"/><path d="M8 10.5v-3a4 4 0 0 1 8 0v3"/>',
        '<rect x="5" y="10.5" width="14" height="10" rx="2.5"/>',
        '<circle cx="12" cy="15.5" r="1.6"/>',
    ),
    "cpu": _Glyph(
        '<rect x="6.5" y="6.5" width="11" height="11" rx="2"/>'
        '<path d="M9.5 3v3.5M14.5 3v3.5M9.5 17.5V21M14.5 17.5V21M3 9.5h3.5M3 14.5h3.5M17.5 9.5H21M17.5 14.5H21"/>',
        '<rect x="6.5" y="6.5" width="11" height="11" rx="2"/>',
        '<rect x="10" y="10" width="4" height="4" rx="1"/>',
    ),
    "chart": _Glyph(
        '<path d="M4 4v15a1 1 0 0 0 1 1h15"/><path d="m7.5 14.5 3.5-4 3 2.5 4.5-6"/>',
        '<path d="m7.5 14.5 3.5-4 3 2.5 4.5-6V17h-11z"/>',
        '<circle cx="18.5" cy="7" r="1.6"/>',
    ),
    "resize": _Glyph('<path d="M14 4h6v6M10 20H4v-6M20 4l-6.5 6.5M4 20l6.5-6.5"/>'),
    "refresh": _Glyph(
        '<path d="M4.5 12a7.5 7.5 0 0 1 13-5.1l2 2.1M19.5 4.5V9H15"/>'
        '<path d="M19.5 12a7.5 7.5 0 0 1-13 5.1l-2-2.1M4.5 19.5V15H9"/>',
        "",
        '<circle cx="12" cy="12" r="1.6"/>',
    ),
    "wave": _Glyph(
        '<path d="M2.5 12h3l2.2-5.5 3.3 11 3-8 2 4.5 1.5-2h2"/>',
        "",
        '<circle cx="20.3" cy="12" r="1.6"/>',
    ),
    "play": _Glyph(
        '<path d="M8 5.3v13.4a.9.9 0 0 0 1.4.8l10.3-6.7a.9.9 0 0 0 0-1.5L9.4 4.5A.9.9 0 0 0 8 5.3z"/>',
        '<path fill-opacity="1" d="M8 5.3v13.4a.9.9 0 0 0 1.4.8l10.3-6.7a.9.9 0 0 0 0-1.5L9.4 4.5A.9.9 0 0 0 8 5.3z"/>',
    ),
    "pause": _Glyph(
        '<rect x="6.5" y="5" width="3.5" height="14" rx="1.2"/><rect x="14" y="5" width="3.5" height="14" rx="1.2"/>',
        '<g fill-opacity="1"><rect x="6.5" y="5" width="3.5" height="14" rx="1.2"/>'
        '<rect x="14" y="5" width="3.5" height="14" rx="1.2"/></g>',
    ),
    "step-back": _Glyph('<path d="M6.5 5.5v13"/><path d="M18 6.3v11.4a.8.8 0 0 1-1.2.7L9.6 12.7a.8.8 0 0 1 0-1.4l7.2-5.7a.8.8 0 0 1 1.2.7z"/>'),
    "step-forward": _Glyph('<path d="M17.5 5.5v13"/><path d="M6 6.3v11.4a.8.8 0 0 0 1.2.7l7.2-5.7a.8.8 0 0 0 0-1.4L7.2 5.6A.8.8 0 0 0 6 6.3z"/>'),
    "stop": _Glyph(
        '<rect x="6" y="6" width="12" height="12" rx="2.5"/>',
        '<rect x="6" y="6" width="12" height="12" rx="2.5"/>',
    ),
    "download": _Glyph(
        '<path d="M12 4v10.5M7.8 10.3 12 14.5l4.2-4.2"/><path d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>',
        '<path d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3z"/>',
    ),
    "copy": _Glyph(
        '<rect x="8.5" y="8.5" width="12" height="12" rx="2.5"/>'
        '<path d="M15.5 8.5V6A2.5 2.5 0 0 0 13 3.5H6A2.5 2.5 0 0 0 3.5 6v7A2.5 2.5 0 0 0 6 15.5h2.5"/>',
        '<rect x="8.5" y="8.5" width="12" height="12" rx="2.5"/>',
    ),
    "fingerprint": _Glyph(
        '<path d="M8 11a4 4 0 0 1 8 0v2M5 9a7.5 7.5 0 0 1 14 0M4 15c.5-1.5 1-3 1-5M19 15c0 2-.5 3.5-1.2 5'
        'M15.5 16c-.2 1.8-.8 3.4-1.7 4.8M12 14a8 8 0 0 1-2 5"/>',
        "",
        '<path d="M12 10.5V14" fill="none"/>',
    ),
    "layers": _Glyph(
        '<path d="m12 3.5 8.5 4.5-8.5 4.5L3.5 8z"/><path d="m3.5 12.5 8.5 4.5 8.5-4.5"/>'
        '<path d="m3.5 16.5 8.5 4.5 8.5-4.5"/>',
        '<path d="m12 3.5 8.5 4.5-8.5 4.5L3.5 8z"/>',
        '<circle cx="12" cy="8" r="1.3"/>',
    ),
    "volume": _Glyph(
        '<path d="M4 9.5v5h3.5l4.5 4v-13l-4.5 4z"/><path d="M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11"/>',
        '<path d="M4 9.5v5h3.5l4.5 4v-13l-4.5 4z"/>',
    ),
    "binary": _Glyph(
        '<rect x="4" y="3.5" width="5" height="7.5" rx="2.5"/><rect x="4" y="13" width="5" height="7.5" rx="2.5"/>'
        '<path d="M15 3.5v7.5M13.5 3.5H15M17 13v7.5M15.5 13H17"/>',
        '<rect x="4" y="3.5" width="5" height="7.5" rx="2.5"/>',
        '<circle cx="6.5" cy="16.8" r="1.1"/>',
    ),
}

LOGO_SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="{theme.ACCENT}"/><stop offset="1" stop-color="{theme.ACCENT_2}"/>
</linearGradient></defs>
<circle cx="24" cy="24" r="22.5" fill="#0D1222" stroke="url(#g)" stroke-width="2.4"/>
<path d="M11 24c3.4-5.6 7.7-8.4 13-8.4s9.6 2.8 13 8.4c-3.4 5.6-7.7 8.4-13 8.4S14.4 29.6 11 24Z"
      fill="none" stroke="{theme.TEXT}" stroke-width="2" stroke-linejoin="round"/>
<g fill="url(#g)">
<rect x="18.4" y="22.4" width="1.8" height="3.2" rx=".9"/><rect x="21.2" y="20" width="1.8" height="8" rx=".9"/>
<rect x="24" y="18.6" width="1.8" height="10.8" rx=".9"/><rect x="26.8" y="21" width="1.8" height="6" rx=".9"/>
<rect x="29.6" y="22.8" width="1.8" height="2.4" rx=".9"/>
</g>
<circle cx="35.5" cy="13" r="2.6" fill="{theme.ACCENT_2}"/>
</svg>"""

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


def svg(name: str, color: str = theme.TEXT, accent: str | None = None, stroke: float = 1.5) -> str:
    glyph = _GLYPHS[name]
    accent = accent or color
    # Seuls les aplats pleins (fill-opacity="1") sont gardés : le style est au trait.
    solid = glyph.fill if 'fill-opacity="1"' in glyph.fill else ""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        'stroke-linecap="round" stroke-linejoin="round">'
        f'<g fill="{color}" stroke="none">{solid}</g>'
        f'<g fill="none" stroke="{color}" stroke-width="{stroke}">{glyph.stroke}</g>'
        f'<g fill="none" stroke="{accent}" stroke-width="{stroke}">{glyph.accent}</g>'
        "</svg>"
    )


@lru_cache(maxsize=512)
def pixmap(name: str, color: str = theme.TEXT, size: int = 20, accent: str | None = None) -> QPixmap:
    return _render(svg(name, color, accent), size)


def icon(name: str, color: str = theme.TEXT, size: int = 20, accent: str | None = None) -> QIcon:
    return QIcon(pixmap(name, color, size, accent))


def names() -> list[str]:
    return sorted(_GLYPHS)


@lru_cache(maxsize=8)
def logo_pixmap(size: int = 48) -> QPixmap:
    return _render(LOGO_SVG, size)
