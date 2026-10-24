"""Accueil : statistiques de la semaine, analyse rapide, moteurs et fichiers récents."""

from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QPainter, QPaintEvent, QShowEvent
from PySide6.QtWidgets import QFileDialog, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from spectralab.core.activity import ActivityLog

from .. import icons, session, theme
from ..widgets import (
    Card,
    ClickableCard,
    FlowChart,
    IconChip,
    LedBar,
    PillBar,
    accent_gradient,
    button,
    round_pen,
    label,
    scrollable,
)

_MONTHS = ("janv", "févr", "mars", "avr", "mai", "juin", "juil", "août", "sept", "oct", "nov", "déc")

# Onglets de raccourci : (clé de page, libellé).
_SHORTCUTS = (
    ("home", "Vue d'ensemble"), ("spectrum", "Spectre"), ("video", "Vidéo"), ("compare", "Comparer"),
    ("forensics", "Forensique"), ("metadata", "Métadonnées"), ("image", "Image"),
)
_TOOLS = (
    ("video", "video", "Expertise vidéo", "Plans, images dupliquées, coupures, synchronisation."),
    ("compare", "layers", "Comparer deux sons", "Alignement automatique et différences."),
    ("forensics", "fingerprint", "Forensique", "Bruit, copier-coller, miniature, cohérence EXIF."),
    ("spectrum", "wave", "Spectre", "ENF, parole, sonie, ruptures et voix claire."),
)


def _hero_chip(name: str, accent: bool = False) -> QLabel:
    chip = QLabel()
    chip.setProperty("chip", "pill-accent" if accent else "pill")
    chip.setFixedSize(58, 44)
    chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
    chip.setPixmap(icons.pixmap(name, theme.ON_ACCENT if accent else theme.TEXT, 20))
    return chip


def _hero_line(*parts: QWidget) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(14)
    for part in parts:
        row.addWidget(part, 0, Qt.AlignmentFlag.AlignVCenter)
    row.addStretch()
    return row


class _StatCard(Card):
    """Statistique sur 7 jours, rapportée aux 14 derniers jours."""

    openRequested = Signal()

    def __init__(self, title: str, icon_name: str, variant: str = "glass") -> None:
        super().__init__(variant)
        self.body.setSpacing(theme.ROW)
        head = QHBoxLayout()
        head.setSpacing(theme.ROW)
        head.addWidget(IconChip(icon_name, "glass", 38))
        head.addWidget(label(title, "CardTitle"), 1)
        more = button("⋮", "ghost")
        more.setToolTip("Ouvrir l'outil")
        more.clicked.connect(self.openRequested)
        head.addWidget(more)
        self.body.addLayout(head)
        self.body.addSpacing(6)
        numbers = QHBoxLayout()
        numbers.setSpacing(theme.TIGHT)
        self.value = label("0", "BigNumber")
        numbers.addWidget(self.value, 0, Qt.AlignmentFlag.AlignBottom)
        side = QVBoxLayout()
        side.setSpacing(4)
        self.badge = label("0 %", "AccentBadge" if variant == "glass" else "Badge")
        self.badge.setFixedHeight(22)
        side.addStretch()
        side.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignLeft)
        self.total = label("/ 0", "Unit")
        side.addWidget(self.total)
        numbers.addLayout(side)
        numbers.addStretch()
        self.body.addLayout(numbers)
        self.meter = LedBar(8)
        self.body.addWidget(self.meter)

    def set_data(self, week: int, fortnight: int) -> None:
        share = week / fortnight if fortnight else 0.0
        self.value.setText(str(week))
        self.total.setText(f"/ {fortnight} sur 14 j")
        self.badge.setText(f"{share:.0%}")
        self.meter.set_ratio(share)


class _SpectrumArt(QWidget):
    """Illustration de la carte sombre : un spectre stylisé en gélules."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(110, 130)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        count, gap = 9, 6
        width = (self.width() - gap * (count - 1)) / count
        for i in range(count):
            level = 0.25 + 0.7 * abs(math.sin(i * 0.9 + 0.6)) * (1 - abs(i - 4) / 7)
            height = self.height() * level
            rect = QRectF(i * (width + gap), (self.height() - height) / 2, width, height)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(accent_gradient(0, rect.top(), 0, rect.bottom()) if i in (3, 4)
                             else QColor(255, 255, 255, 30 + i * 10))
            painter.drawRoundedRect(rect, width / 2, width / 2)
        painter.setPen(round_pen(QColor(theme.ACCENT_2), 1.6))
        painter.drawLine(QPointF(self.width() - 18, 10), QPointF(self.width() - 6, 2))
        painter.drawLine(QPointF(self.width() - 12, 2), QPointF(self.width() - 6, 2))
        painter.drawLine(QPointF(self.width() - 6, 2), QPointF(self.width() - 6, 8))


class _QuickCard(Card):
    """Carte sombre d'appel à l'action ; on peut aussi y déposer un fichier."""

    fileDropped = Signal(Path)

    def __init__(self) -> None:
        super().__init__("dark")
        self.setAcceptDrops(True)
        top = QHBoxLayout()
        texts = QVBoxLayout()
        title = label("Analysez un fichier en un geste", wrap=True)
        title.setStyleSheet("font-size: 22px; font-weight: 400;")
        texts.addWidget(title)
        texts.addWidget(label("Déposez-le ici : SpectraLab choisit l'outil adapté.", "CardHint", wrap=True))
        texts.addStretch()
        top.addLayout(texts, 3)
        top.addWidget(_SpectrumArt(), 2)
        self.body.addLayout(top, 1)
        self.open = button("Ouvrir un fichier  ▷", "light")
        self.body.addWidget(self.open)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if any(u.isLocalFile() for u in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        files = [Path(u.toLocalFile()) for u in event.mimeData().urls() if u.isLocalFile()]
        files = [f for f in files if f.is_file()]
        if files:
            event.acceptProposedAction()
            self.fileDropped.emit(files[0])


class _MiniCard(Card):
    """Petite carte carrée : icône, nom et état d'un moteur."""

    def __init__(self, icon_name: str, title: str) -> None:
        super().__init__()
        self.body.setContentsMargins(18, 18, 18, 18)
        self.body.addWidget(IconChip(icon_name, "glass", 38), 0, Qt.AlignmentFlag.AlignHCenter)
        name = label(title, "CardTitle")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body.addWidget(name)
        self.state = label("…", "CardHint")
        self.state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body.addWidget(self.state)


class _LinkCard(ClickableCard):
    """Carte de liste : icône, titre, description, flèche."""

    def __init__(self, icon_name: str, title: str, hint: str) -> None:
        super().__init__()
        self.body.setContentsMargins(18, 16, 18, 16)
        self.body.setSpacing(10)
        top = QHBoxLayout()
        top.addWidget(IconChip(icon_name, "glass", 38))
        top.addStretch()
        arrow = QLabel()
        arrow.setPixmap(icons.pixmap("arrow", theme.TEXT, 18))
        top.addWidget(arrow, 0, Qt.AlignmentFlag.AlignTop)
        self.body.addLayout(top)
        self.body.addWidget(label(title, "CardTitle"))
        self.body.addWidget(label(hint, "CardHint", wrap=True))


class DashboardPage(QWidget):
    navigate = Signal(str)
    openFile = Signal(Path)
    reopen = Signal(Path, str)
    aboutRequested = Signal()

    def __init__(self, activity: ActivityLog) -> None:
        super().__init__()
        self._activity = activity

        content = QWidget()
        grid = QGridLayout(content)
        grid.setContentsMargins(0, 0, 0, theme.GAP)
        grid.setHorizontalSpacing(theme.GAP)
        grid.setVerticalSpacing(theme.GAP)

        hero = QVBoxLayout()
        hero.setSpacing(2)
        hero.addLayout(_hero_line(label("Analysez", "HeroTitle"), _hero_chip("eye"), label("vos médias", "HeroTitle")))
        hero.addLayout(_hero_line(label("et", "HeroTitle"), _hero_chip("sparkles", True),
                                  label("protégez-les", "HeroTitle")))
        grid.addLayout(hero, 0, 0, 1, 3)

        actions = QHBoxLayout()
        actions.setSpacing(theme.ROW)
        actions.addStretch()
        about = button("", "icon", "info")
        about.setToolTip("À propos de SpectraLab")
        about.clicked.connect(self.aboutRequested)
        actions.addWidget(about)
        open_button = button("Ouvrir un fichier", "primary", "plus")
        open_button.clicked.connect(self._choose_file)
        actions.addWidget(open_button)
        grid.addLayout(actions, 0, 3, Qt.AlignmentFlag.AlignTop)

        tabs = PillBar([text for _, text in _SHORTCUTS])
        tabs.changed.connect(self._on_tab)
        self._tabs = tabs
        grid.addWidget(tabs, 1, 0, 1, 3)

        self._analyses = _StatCard("Analyses", "chart")
        self._cleans = _StatCard("Nettoyages", "shield", "accent")
        self._analyses.openRequested.connect(lambda: self.navigate.emit("forensics"))
        self._cleans.openRequested.connect(lambda: self.navigate.emit("metadata"))
        grid.addWidget(self._analyses, 2, 0)
        grid.addWidget(self._cleans, 2, 1)
        quick = _QuickCard()
        quick.open.clicked.connect(self._choose_file)
        quick.fileDropped.connect(self.openFile)
        grid.addWidget(quick, 2, 2)

        stats = Card()
        head = QHBoxLayout()
        head.setSpacing(theme.ROW)
        head.addWidget(IconChip("chart", "glass", 42))
        title = label("Statistiques")
        title.setStyleSheet("font-size: 24px; font-weight: 400;")
        head.addWidget(title)
        head.addSpacing(theme.GAP)
        for color, text in ((theme.ACCENT, "Analyses"), (theme.ACCENT_2, "Nettoyages et conversions")):
            dot = label("●")
            dot.setStyleSheet(f"color: {color}; font-size: 14px;")
            head.addWidget(dot)
            head.addWidget(label(text, "CardHint"))
        head.addStretch()
        self._period = label("", "Badge")
        head.addWidget(self._period)
        stats.body.addLayout(head)
        self._chart = FlowChart()
        stats.body.addWidget(self._chart, 1)
        grid.addWidget(stats, 3, 0, 1, 3)

        side = QVBoxLayout()
        side.setSpacing(theme.GAP)
        engines = QHBoxLayout()
        engines.setSpacing(theme.GAP)
        self._engines = {"exiftool": _MiniCard("tag", "ExifTool"), "ffmpeg": _MiniCard("video", "FFmpeg")}
        for card in self._engines.values():
            engines.addWidget(card)
        side.addLayout(engines)
        self._links = QVBoxLayout()
        self._links.setSpacing(theme.GAP)
        side.addLayout(self._links)
        side.addStretch()
        grid.addLayout(side, 1, 3, 3, 1)

        for column, stretch in enumerate((3, 3, 3, 2)):
            grid.setColumnStretch(column, stretch)
        grid.setColumnMinimumWidth(3, 300)
        grid.setRowStretch(3, 1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scrollable(content))
        session.recent.changed.connect(self._refresh_links)
        self._refresh_links()

    def _on_tab(self, index: int) -> None:
        if index:
            self.navigate.emit(_SHORTCUTS[index][0])
            self._tabs.select(0)  # l'accueil reste sélectionné quand on y revient

    # ── Données ──
    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        days = self._activity.last_days(14)
        for kind, card in (("analysis", self._analyses), ("clean", self._cleans)):
            counts = [c.get(kind, 0) for _, c in days]
            card.set_data(sum(counts[7:]), sum(counts))
        self._chart.set_data(
            [f"{d.day} {_MONTHS[d.month - 1]}" if i % 2 == 0 or i == len(days) - 1 else ""
             for i, (d, _) in enumerate(days)],
            [(c.get("analysis", 0), c.get("clean", 0) + c.get("convert", 0)) for _, c in days],
        )
        first, last = days[0][0], days[-1][0]
        self._period.setText(f"{first.day} {_MONTHS[first.month - 1]} – {last.day} {_MONTHS[last.month - 1]}")

    def set_engines(self, versions: dict[str, str | None]) -> None:
        for tool, card in self._engines.items():
            version = versions.get(tool)
            card.state.setText(f"✓ {version}" if version else "✕ absent")
            card.state.setStyleSheet(f"color: {theme.GOOD if version else theme.CORAL};")

    def _refresh_links(self) -> None:
        while (item := self._links.takeAt(0)) is not None:
            if widget := item.widget():
                widget.deleteLater()
        recent = session.recent.items()[:4]
        if recent:
            self._links.addWidget(label("Fichiers récents", "Caption"))
            for path, tool in recent:
                card = _LinkCard(session.recent.icon_for(path), path.name, "Rouvrir dans l'outil utilisé")
                card.clicked.connect(lambda p=path, t=tool: self.reopen.emit(p, t))
                self._links.addWidget(card)
            return
        for key, icon_name, title, hint in _TOOLS:
            card = _LinkCard(icon_name, title, hint)
            card.clicked.connect(lambda k=key: self.navigate.emit(k))
            self._links.addWidget(card)

    def _choose_file(self) -> None:
        name, _ = QFileDialog.getOpenFileName(self, "Analyser un fichier", "", "Tous les fichiers (*)")
        if name:
            self.openFile.emit(Path(name))
