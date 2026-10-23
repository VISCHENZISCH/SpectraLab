"""Composants visuels réutilisables : cartes en verre, jauges, graphique, zone de dépôt…"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QFont,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QPixmap,
    QRadialGradient,
    QResizeEvent,
)
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from . import icons, theme


def label(text: str = "", name: str | None = None, *, wrap: bool = False) -> QLabel:
    widget = QLabel(text)
    # Texte brut : un nom de fichier ou une valeur de métadonnée ne doit jamais
    # être interprété comme du HTML.
    widget.setTextFormat(Qt.TextFormat.PlainText)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(wrap)
    return widget


def button(text: str, variant: str | None = None, icon_name: str | None = None) -> QPushButton:
    widget = QPushButton(text)
    if variant:
        widget.setProperty("variant", variant)
    if icon_name:
        widget.setIcon(icons.icon(icon_name, theme.INK if variant == "primary" else theme.TEXT, 18))
        widget.setIconSize(QSize(18, 18))
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    return widget


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def scrollable(content: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidget(content)
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.viewport().setAutoFillBackground(False)
    return area


class Backdrop(QWidget):
    """Fond sombre éclairé par des halos colorés (mis en cache à chaque redimensionnement)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cache: QPixmap | None = None

    def resizeEvent(self, event: QResizeEvent) -> None:
        self._cache = None
        super().resizeEvent(event)

    def _render(self) -> QPixmap:
        ratio = self.devicePixelRatioF()
        pixmap = QPixmap(self.size() * ratio)
        pixmap.setDevicePixelRatio(ratio)
        pixmap.fill(QColor(theme.BG))
        painter = QPainter(pixmap)
        w, h = self.width(), self.height()
        for x, y, radius, color in theme.GLOWS:
            gradient = QRadialGradient(QPointF(w * x, h * y), max(w, h) * radius)
            gradient.setColorAt(0, color)
            gradient.setColorAt(1, QColor(0, 0, 0, 0))
            painter.fillRect(self.rect(), gradient)
        painter.end()
        return pixmap

    def paintEvent(self, event: QPaintEvent) -> None:
        if self._cache is None:
            self._cache = self._render()
        QPainter(self).drawPixmap(0, 0, self._cache)


class Card(QFrame):
    def __init__(self, variant: str = "glass", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("card", variant)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(22, 20, 22, 20)
        self.body.setSpacing(12)


class ClickableCard(Card):
    clicked = Signal()

    def __init__(self, variant: str = "glass", parent: QWidget | None = None) -> None:
        super().__init__(variant, parent)
        self.setProperty("clickable", "true")
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit()
        else:
            super().keyPressEvent(event)


class IconChip(QLabel):
    def __init__(self, name: str, variant: str = "glass", size: int = 42, color: str | None = None) -> None:
        super().__init__()
        self.setProperty("chip", variant)
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ink = color or (theme.INK if variant in ("light", "lime") else theme.TEXT)
        self.setPixmap(icons.pixmap(name, ink, round(size * 0.45)))


class SegmentMeter(QWidget):
    """Jauge en gélules : pleines jusqu'au ratio, puis contours pointillés."""

    def __init__(
        self,
        segments: int = 8,
        fill: QColor = QColor(theme.TEXT),
        outline: QColor = QColor(255, 255, 255, 90),
    ) -> None:
        super().__init__()
        self._segments = segments
        self._ratio = 0.0
        self._fill = fill
        self._outline = outline
        self.setMinimumHeight(46)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_ratio(self, ratio: float) -> None:
        self._ratio = max(0.0, min(1.0, ratio))
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        gap = 6
        width = (self.width() - gap * (self._segments - 1)) / self._segments
        filled = round(self._ratio * self._segments)
        dashed = QPen(self._outline, 1.2, Qt.PenStyle.DashLine)
        for i in range(self._segments):
            rect = QRectF(i * (width + gap) + 0.5, 0.5, width - 1, self.height() - 1)
            radius = min(width, rect.height()) / 2
            if i < filled:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(self._fill)
            else:
                painter.setPen(dashed)
                painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect, radius, radius)


class CapsuleChart(QWidget):
    """Colonnes en gélules à deux séries (ex. analyses / nettoyages par jour)."""

    def __init__(self) -> None:
        super().__init__()
        self._data: list[tuple[str, int, int]] = []
        self.setMinimumHeight(220)

    def set_data(self, data: Sequence[tuple[str, int, int]]) -> None:
        self._data = list(data)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        if not self._data:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        label_height = 26
        top = 26
        plot_h = self.height() - label_height - top
        peak = max(max(a, b) for _, a, b in self._data) or 1
        slot = self.width() / len(self._data)
        width = min(34.0, slot * 0.5)

        grid = QPen(QColor(255, 255, 255, 14), 1)
        for i in range(5):
            y = top + plot_h * i / 4
            painter.setPen(grid)
            painter.drawLine(QPointF(0, y), QPointF(self.width(), y))

        small = QFont(self.font())
        small.setPointSizeF(8.5)
        painter.setFont(small)
        for i, (text, first, second) in enumerate(self._data):
            cx = slot * i + slot / 2
            x = cx - width / 2
            bottom = top + plot_h
            if first == 0 and second == 0:
                painter.setPen(QPen(QColor(255, 255, 255, 60), 1.2, Qt.PenStyle.DashLine))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(QRectF(x, top + plot_h * 0.25, width, plot_h * 0.75), width / 2, width / 2)
            else:
                back_h = max(width, plot_h * max(first, second) / peak)
                self._capsule(painter, x, bottom - back_h, width, back_h, QColor(theme.TEXT), QColor(theme.INK))
                painter.setPen(QColor(theme.TEXT))
                painter.drawText(QRectF(cx - 30, bottom - back_h - 22, 60, 18), Qt.AlignmentFlag.AlignCenter, str(first))
                if second:
                    front_h = max(width, plot_h * second / peak)
                    self._capsule(painter, x, bottom - front_h, width, front_h, QColor(theme.LIME), QColor(theme.INK))
            painter.setPen(QColor(theme.TEXT_2))
            painter.drawText(
                QRectF(slot * i, self.height() - label_height + 6, slot, 18), Qt.AlignmentFlag.AlignCenter, text
            )

    @staticmethod
    def _capsule(painter: QPainter, x: float, y: float, w: float, h: float, fill: QColor, dot: QColor) -> None:
        path = QPainterPath()
        path.addRoundedRect(QRectF(x, y, w, h), w / 2, w / 2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fill)
        painter.drawPath(path)
        painter.setBrush(dot)
        painter.drawEllipse(QPointF(x + w / 2, y + w / 2), w * 0.16, w * 0.16)


class DropZone(QFrame):
    """Zone où déposer des fichiers (glisser-déposer ou clic → sélecteur)."""

    filesSelected = Signal(list)

    def __init__(self, title: str, hint: str, extensions: Iterable[str], dialog_filter: str) -> None:
        super().__init__()
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._extensions = {e.lower() for e in extensions}
        self._filter = dialog_filter

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 28, 24, 28)
        layout.setSpacing(10)
        layout.addStretch()
        chip = IconChip("upload", "lime", 52)
        layout.addWidget(chip, 0, Qt.AlignmentFlag.AlignHCenter)
        title_label = label(title, "CardTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_label = label(hint, "CardHint", wrap=True)
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        layout.addWidget(hint_label)
        layout.addStretch()

    def _accepted(self, paths: Iterable[Path]) -> list[Path]:
        return [p for p in paths if p.is_file() and (not self._extensions or p.suffix.lower() in self._extensions)]

    def _set_dragging(self, value: bool) -> None:
        self.setProperty("dragging", "true" if value else "false")
        repolish(self)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        urls = event.mimeData().urls()
        if urls and any(u.isLocalFile() for u in urls):
            event.acceptProposedAction()
            self._set_dragging(True)

    def dragLeaveEvent(self, event) -> None:  # noqa: ANN001 - signature Qt
        self._set_dragging(False)

    def dropEvent(self, event: QDropEvent) -> None:
        self._set_dragging(False)
        files = self._accepted(Path(u.toLocalFile()) for u in event.mimeData().urls() if u.isLocalFile())
        if files:
            event.acceptProposedAction()
            self.filesSelected.emit(files)

    def open_dialog(self) -> None:
        names, _ = QFileDialog.getOpenFileNames(self, "Choisir des fichiers", "", self._filter)
        files = self._accepted(Path(n) for n in names)
        if files:
            self.filesSelected.emit(files)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_dialog()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.open_dialog()
        else:
            super().keyPressEvent(event)


class PillBar(QWidget):
    changed = Signal(int)

    def __init__(self, labels: Sequence[str]) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self._group = QButtonGroup(self)
        for i, text in enumerate(labels):
            pill = button(text, "pill")
            pill.setCheckable(True)
            pill.setChecked(i == 0)
            self._group.addButton(pill, i)
            layout.addWidget(pill)
        layout.addStretch()
        self._group.idClicked.connect(self.changed)

    def current(self) -> int:
        return self._group.checkedId()


class StatusLine(QLabel):
    """Message d'état coloré (succès, erreur, information)."""

    _COLORS = {"ok": theme.LIME, "error": theme.CORAL, "info": theme.TEXT_2, "busy": theme.VIOLET}

    def __init__(self) -> None:
        super().__init__()
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setWordWrap(True)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

    def show_message(self, text: str, kind: str = "info") -> None:
        self.setStyleSheet(f"color: {self._COLORS.get(kind, theme.TEXT_2)};")
        self.setText(text)


def page_header(title: str, subtitle: str, *actions: QWidget) -> QWidget:
    header = QWidget()
    row = QHBoxLayout(header)
    row.setContentsMargins(0, 0, 0, 0)
    texts = QVBoxLayout()
    texts.setSpacing(4)
    texts.addWidget(label(title, "PageTitle"))
    texts.addWidget(label(subtitle, "Subtitle", wrap=True))
    row.addLayout(texts, 1)
    for action in actions:
        row.addWidget(action, 0, Qt.AlignmentFlag.AlignTop)
    return header
