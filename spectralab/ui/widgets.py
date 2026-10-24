"""Composants visuels réutilisables : cartes en verre, jauges, graphique, zone de dépôt…"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QFont,
    QKeyEvent,
    QLinearGradient,
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
    QAbstractItemView,
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableWidget,
    QTreeWidget,
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
        widget.setIcon(icons.icon(icon_name, theme.ON_ACCENT if variant == "primary" else theme.TEXT, 18))
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
    # Barres masquées : la molette et le pavé tactile suffisent.
    area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    return area


class Backdrop(QWidget):
    """Fond bleu nuit éclairé par des halos (mis en cache à chaque redimensionnement).

    Les cartes translucides posées dessus prennent la teinte des halos : c'est
    ce qui donne l'effet de verre.
    """

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


def rounded_pixmap(source: QPixmap, radius: float = theme.RADIUS_INNER) -> QPixmap:
    """Copie de l'image aux coins arrondis (rien n'est affiché avec des angles droits)."""
    if source.isNull():
        return source
    result = QPixmap(source.size())
    result.setDevicePixelRatio(source.devicePixelRatio())
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    ratio = source.devicePixelRatio()
    path.addRoundedRect(QRectF(0, 0, source.width() / ratio, source.height() / ratio), radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, source)
    painter.end()
    return result


def round_pen(color, width: float = 1.0) -> QPen:  # noqa: ANN001 - QColor, QGradient ou QBrush
    """Crayon aux extrémités et jonctions arrondies."""
    pen = QPen(color, width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def accent_gradient(x1: float, y1: float, x2: float, y2: float, alpha: int = 255) -> QLinearGradient:
    gradient = QLinearGradient(x1, y1, x2, y2)
    start, end = QColor(theme.ACCENT), QColor(theme.ACCENT_2)
    start.setAlpha(alpha)
    end.setAlpha(alpha)
    gradient.setColorAt(0, start)
    gradient.setColorAt(1, end)
    return gradient


class Card(QFrame):
    def __init__(self, variant: str = "glass", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("card", variant)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(theme.PAD, theme.PAD, theme.PAD, theme.PAD)
        self.body.setSpacing(theme.ROW)


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
        ink = color or (theme.ON_ACCENT if variant in ("accent", "pill-accent") else theme.TEXT)
        self.setPixmap(icons.pixmap(name, ink, round(size * 0.45)))


class LcdLabel(QWidget):
    """En-tête de carte : titre à gauche, mesure en direct dans une pastille à droite.

    La pastille est anis en temps normal ; elle prend la couleur d'alerte
    (ambre, rouge) passée à ``set_value``.
    """

    HEIGHT = 30

    def __init__(self, title: str, value: str = "", color: str = theme.LCD) -> None:
        super().__init__()
        self._title = title[:1].upper() + title[1:].lower() if title.isupper() else title
        self._value = value
        self._color = color
        self.setFixedHeight(self.HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_value(self, value: str, color: str | None = None) -> None:
        self._value = value
        self._color = color or theme.LCD
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        value_font = QFont(self.font())
        value_font.setPixelSize(11)
        value_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(value_font)
        pill_w = painter.fontMetrics().horizontalAdvance(self._value) + 20 if self._value else 0
        if self._value:
            pill = QRectF(rect.right() - pill_w, rect.center().y() - 11, pill_w, 22)
            painter.setPen(Qt.PenStyle.NoPen)
            if self._color == theme.LCD:
                painter.setBrush(accent_gradient(pill.left(), 0, pill.right(), 0))
            else:
                painter.setBrush(QColor(self._color))
            painter.drawRoundedRect(pill, 11, 11)
            color = QColor(self._color)
            luminance = 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()
            painter.setPen(QColor("#0B0F1C" if luminance > 165 else theme.ON_ACCENT))
            painter.drawText(pill, Qt.AlignmentFlag.AlignCenter, self._value)
        title_font = QFont(self.font())
        title_font.setPixelSize(14)
        title_font.setWeight(QFont.Weight.Medium)
        painter.setFont(title_font)
        room = max(0, int(rect.width() - pill_w - 12))
        title = painter.fontMetrics().elidedText(self._title, Qt.TextElideMode.ElideRight, room)
        painter.setPen(QColor(theme.TEXT))
        painter.drawText(rect.adjusted(2, 0, -pill_w - 12, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                         title)


class LedBar(QWidget):
    """Jauge arrondie : rail translucide, remplissage en dégradé, curseur lumineux en bout."""

    def __init__(self, segments: int = 0, *, color: str | None = None, height: int = 12) -> None:
        super().__init__()
        del segments  # conservé pour compatibilité : la jauge est continue
        self._ratio = 0.0
        self._color = color
        self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_ratio(self, ratio: float) -> None:
        self._ratio = max(0.0, min(1.0, ratio))
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = rect.height() / 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 20))
        painter.drawRoundedRect(rect, radius, radius)
        if self._ratio <= 0:
            return
        filled = QRectF(rect.left(), rect.top(), max(rect.height(), rect.width() * self._ratio), rect.height())
        painter.setBrush(QColor(self._color) if self._color else accent_gradient(rect.left(), 0, rect.right(), 0))
        painter.drawRoundedRect(filled, radius, radius)
        painter.setBrush(QColor(theme.TEXT))
        painter.drawEllipse(QPointF(filled.right() - radius, filled.center().y()), radius * 0.45, radius * 0.45)


class SectionRule(QLabel):
    """Titre de section discret."""

    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.setObjectName("Caption")
        self.setTextFormat(Qt.TextFormat.PlainText)

    def set_text(self, text: str) -> None:
        self.setText(text)


def smooth_path(points: Sequence[QPointF]) -> QPainterPath:
    """Courbe lissée passant par tous les points (Catmull-Rom → Bézier)."""
    path = QPainterPath(points[0])
    for i in range(len(points) - 1):
        p0 = points[max(0, i - 1)]
        p1, p2 = points[i], points[i + 1]
        p3 = points[min(len(points) - 1, i + 2)]
        c1 = QPointF(p1.x() + (p2.x() - p0.x()) / 6, p1.y() + (p2.y() - p0.y()) / 6)
        c2 = QPointF(p2.x() - (p3.x() - p1.x()) / 6, p2.y() - (p3.y() - p1.y()) / 6)
        path.cubicTo(c1, c2, p2)
    return path


class FlowChart(QWidget):
    """Évolution de deux flux : courbes lissées, aires en dégradé, point lumineux sur la dernière valeur.

    Fond arrondi, grille pointillée discrète, étiquettes de dates en dessous.
    """

    SERIES = (theme.ACCENT, theme.ACCENT_2)

    def __init__(self) -> None:
        super().__init__()
        self._labels: list[str] = []
        self._values: list[tuple[float, float]] = []
        self.setMinimumHeight(220)

    def set_data(self, labels: Sequence[str], values: Sequence[tuple[float, float]]) -> None:
        self._labels = list(labels)
        self._values = [(float(a), float(b)) for a, b in values]
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        frame = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(QPen(QColor(255, 255, 255, 18), 1))
        painter.setBrush(QColor(0, 0, 0, 60))
        painter.drawRoundedRect(frame, theme.RADIUS_INNER, theme.RADIUS_INNER)
        if len(self._values) < 2:
            return
        rect = frame.adjusted(44, 18, -18, -32)
        peak = max(max(a, b) for a, b in self._values) or 1.0
        font = QFont(self.font())
        font.setPixelSize(10)
        painter.setFont(font)
        for i in range(5):
            value = peak * (4 - i) / 4
            y = rect.top() + rect.height() * i / 4
            painter.setPen(QPen(QColor(255, 255, 255, 18), 1, Qt.PenStyle.DotLine))
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            painter.setPen(QColor(theme.TEXT_3))
            painter.drawText(QRectF(frame.left() + 6, y - 8, 30, 16),
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{value:.0f}")
        step = rect.width() / (len(self._values) - 1)
        for i, text in enumerate(self._labels):
            if not text:
                continue
            last = i == len(self._labels) - 1
            painter.setPen(QColor(theme.TEXT if last else theme.TEXT_3))
            painter.drawText(QRectF(rect.left() + i * step - 32, rect.bottom() + 10, 64, 16),
                             Qt.AlignmentFlag.AlignCenter, text)
        for series in (1, 0):  # la série principale passe devant
            color = QColor(self.SERIES[series])
            points = [QPointF(rect.left() + i * step, rect.bottom() - v[series] / peak * rect.height())
                      for i, v in enumerate(self._values)]
            line = smooth_path(points)
            area = QPainterPath(line)
            area.lineTo(points[-1].x(), rect.bottom())
            area.lineTo(points[0].x(), rect.bottom())
            area.closeSubpath()
            fill = QLinearGradient(0, rect.top(), 0, rect.bottom())
            top = QColor(color)
            top.setAlpha(90 if series == 0 else 60)
            fill.setColorAt(0, top)
            fill.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(fill)
            painter.drawPath(area)
            glow = QColor(color)
            glow.setAlpha(60)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(round_pen(glow, 6))
            painter.drawPath(line)
            painter.setPen(round_pen(color, 2.2))
            painter.drawPath(line)
            end = points[-1]
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow)
            painter.drawEllipse(end, 9, 9)
            painter.setBrush(QColor(theme.TEXT))
            painter.drawEllipse(end, 4, 4)


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
        layout.setContentsMargins(24, 32, 24, 32)
        layout.setSpacing(theme.ROW)
        layout.addStretch()
        chip = IconChip("upload", "accent", 52)
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
        layout.setSpacing(theme.TIGHT)
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

    def select(self, index: int) -> None:
        if button := self._group.button(index):
            button.setChecked(True)


class StatusLine(QLabel):
    """Message d'état coloré (succès, erreur, information)."""

    _COLORS = {"ok": theme.GOOD, "error": theme.CORAL, "info": theme.TEXT_2, "busy": theme.ACCENT}

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
    row.setSpacing(theme.ROW)
    texts = QVBoxLayout()
    texts.setSpacing(4)
    texts.addWidget(label(title, "PageTitle"))
    texts.addWidget(label(subtitle, "Subtitle", wrap=True))
    row.addLayout(texts, 1)
    for action in actions:
        row.addWidget(action, 0, Qt.AlignmentFlag.AlignTop)
    return header


# ── Listes et tableaux : une ligne = une seule pilule arrondie ─────────────

_ROW_SELECTED = QColor(255, 255, 255, 28)
_ROW_HOVER = QColor(255, 255, 255, 12)
_ROW_RADIUS = 10


def _row_background(state: QStyle.StateFlag, tint: QBrush | None) -> QColor | QBrush | None:
    if state & QStyle.StateFlag.State_Selected:
        return _ROW_SELECTED
    if tint is not None and tint.style() != Qt.BrushStyle.NoBrush:
        return tint
    if state & QStyle.StateFlag.State_MouseOver:
        return _ROW_HOVER
    return None


class RowDelegate(QStyledItemDelegate):
    """Dessine le fond d'une ligne de tableau comme une seule pilule.

    Qt arrondit chaque cellule séparément : une ligne sélectionnée devenait une
    suite de pastilles collées. Ici chaque cellule dessine sa portion d'un même
    rectangle arrondi qui couvre toute la ligne.
    """

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:  # noqa: ANN001 - QModelIndex
        view = self.parent()
        tint = index.siblingAtColumn(0).data(Qt.ItemDataRole.BackgroundRole)
        fill = _row_background(option.state, tint if isinstance(tint, QBrush) else None)
        if fill is not None and isinstance(view, QAbstractItemView):
            row = QRectF(4, option.rect.top() + 1, view.viewport().width() - 8, option.rect.height() - 2)
            painter.save()
            painter.setClipRect(option.rect)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(fill)
            painter.drawRoundedRect(row, _ROW_RADIUS, _ROW_RADIUS)
            painter.restore()
        plain = QStyleOptionViewItem(option)
        self.initStyleOption(plain, index)
        plain.state &= ~(QStyle.StateFlag.State_Selected | QStyle.StateFlag.State_HasFocus
                         | QStyle.StateFlag.State_MouseOver)
        plain.backgroundBrush = QBrush()
        style = view.style() if isinstance(view, QWidget) else None
        if style is not None:
            style.drawControl(QStyle.ControlElement.CE_ItemViewItem, plain, painter, view)
        else:
            super().paint(painter, plain, index)


def make_table(headers: Sequence[str]) -> QTableWidget:
    """Tableau en lecture seule, sélection par ligne, lignes en pilules arrondies."""
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(list(headers))
    table.verticalHeader().hide()
    table.verticalHeader().setDefaultSectionSize(34)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setShowGrid(False)
    table.setWordWrap(False)
    table.setMouseTracking(True)
    table.setItemDelegate(RowDelegate(table))
    header = table.horizontalHeader()
    header.setStretchLastSection(True)
    header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    header.setHighlightSections(False)
    return table


class RoundedTree(QTreeWidget):
    """Arbre dont chaque ligne (flèche de dépliage comprise) est une seule pilule arrondie."""

    def __init__(self) -> None:
        super().__init__()
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setItemDelegate(_TreeDelegate(self))

    def drawRow(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:  # noqa: ANN001
        state = option.state
        if self.selectionModel().isSelected(index):
            state |= QStyle.StateFlag.State_Selected
        fill = _row_background(state, None)
        if fill is not None:
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(fill)
            painter.drawRoundedRect(QRectF(4, option.rect.top() + 1, self.viewport().width() - 8,
                                           option.rect.height() - 2), _ROW_RADIUS, _ROW_RADIUS)
            painter.restore()
        super().drawRow(painter, option, index)


class _TreeDelegate(QStyledItemDelegate):
    """Cellules d'arbre sans fond propre : c'est la ligne entière qui est dessinée."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:  # noqa: ANN001
        plain = QStyleOptionViewItem(option)
        self.initStyleOption(plain, index)
        plain.state &= ~(QStyle.StateFlag.State_Selected | QStyle.StateFlag.State_HasFocus
                         | QStyle.StateFlag.State_MouseOver)
        view = self.parent()
        view.style().drawControl(QStyle.ControlElement.CE_ItemViewItem, plain, painter, view)
