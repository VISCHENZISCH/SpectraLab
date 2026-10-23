"""Accueil : activité de la semaine, moteurs installés, accès rapides."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QShowEvent
from PySide6.QtWidgets import QFileDialog, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from spectralab.core import filetypes
from spectralab.core.activity import ActivityLog
from spectralab.core.tools import tool_version

from .. import jobs, theme
from ..widgets import (
    Card,
    CapsuleChart,
    ClickableCard,
    IconChip,
    SegmentMeter,
    button,
    label,
    scrollable,
)

_WEEKDAYS = ("lun", "mar", "mer", "jeu", "ven", "sam", "dim")


def _hero_line(*parts: QWidget) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(12)
    for part in parts:
        row.addWidget(part, 0, Qt.AlignmentFlag.AlignVCenter)
    row.addStretch()
    return row


class _StatCard(Card):
    def __init__(self, title: str, icon_name: str, variant: str) -> None:
        super().__init__(variant)
        lime = variant == "lime"
        head = QHBoxLayout()
        head.setSpacing(12)
        head.addWidget(IconChip(icon_name, "light" if lime else "glass", 40))
        head.addWidget(label(title, "CardTitle"), 1)
        self.body.addLayout(head)

        numbers = QHBoxLayout()
        numbers.setSpacing(8)
        self.value = label("0", "BigNumber")
        self.unit = label("", "Unit")
        self.badge = label("", "Badge")
        numbers.addWidget(self.value, 0, Qt.AlignmentFlag.AlignBottom)
        side = QVBoxLayout()
        side.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignLeft)
        side.addWidget(self.unit)
        numbers.addLayout(side)
        numbers.addStretch()
        self.body.addLayout(numbers)

        ink = QColor(theme.INK) if lime else QColor(theme.TEXT)
        outline = QColor(11, 12, 16, 110) if lime else QColor(255, 255, 255, 80)
        self.meter = SegmentMeter(7 if not lime else 8, ink, outline)
        self.body.addWidget(self.meter)


class _ShortcutCard(ClickableCard):
    def __init__(self, icon_name: str, title: str, hint: str, compact: bool = False) -> None:
        super().__init__()
        top = QHBoxLayout()
        top.addWidget(IconChip(icon_name, "glass", 38))
        top.addStretch()
        if not compact:
            top.addWidget(IconChip("arrow", "glass", 30), 0, Qt.AlignmentFlag.AlignTop)
        self.body.addLayout(top)
        self.body.addWidget(label(title, "CardTitle"))
        if hint:
            hint_label = label(hint, "CardHint", wrap=True)
            self.body.addWidget(hint_label)


class DashboardPage(QWidget):
    navigate = Signal(str)
    openFile = Signal(Path)

    def __init__(self, activity: ActivityLog) -> None:
        super().__init__()
        self._activity = activity
        self._tools_checked = False

        content = QWidget()
        grid = QGridLayout(content)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)

        # ── Titre « héros » avec pastilles, à la manière d'un magazine ──
        hero = QVBoxLayout()
        hero.setSpacing(6)
        hero.addLayout(_hero_line(label("Analysez", "HeroTitle"), IconChip("eye", "glass", 46), label("vos médias", "HeroTitle")))
        hero.addLayout(_hero_line(label("et", "HeroTitle"), IconChip("sparkles", "lime", 46), label("protégez-les", "HeroTitle")))
        grid.addLayout(hero, 0, 0, 1, 3)

        actions = QHBoxLayout()
        actions.addStretch()
        open_button = button("Analyser un fichier", "primary", "plus")
        open_button.clicked.connect(self._choose_file)
        actions.addWidget(open_button)
        grid.addLayout(actions, 0, 3, Qt.AlignmentFlag.AlignTop)

        # ── Cartes de statistiques ──
        self._analyses = _StatCard("Analyses", "chart", "glass")
        self._cleans = _StatCard("Nettoyages", "lock", "lime")
        grid.addWidget(self._analyses, 1, 0)
        grid.addWidget(self._cleans, 1, 1)
        grid.addWidget(self._engines_card(), 1, 2)

        # ── Graphique d'activité ──
        chart_card = Card()
        head = QHBoxLayout()
        head.setSpacing(12)
        head.addWidget(IconChip("chart", "glass", 40))
        head.addWidget(label("Activité", "PageTitle"))
        head.addSpacing(16)
        for color, text in ((theme.TEXT, "Analyses"), (theme.LIME, "Nettoyages")):
            dot = label("●")
            dot.setStyleSheet(f"color: {color};")
            head.addWidget(dot)
            head.addWidget(label(text, "CardHint"))
        head.addStretch()
        head.addWidget(label("7 derniers jours", "Badge"))
        chart_card.body.addLayout(head)
        self._chart = CapsuleChart()
        chart_card.body.addWidget(self._chart, 1)
        grid.addWidget(chart_card, 2, 0, 1, 3)

        # ── Colonne de raccourcis ──
        shortcuts = QVBoxLayout()
        shortcuts.setSpacing(16)
        pair = QHBoxLayout()
        pair.setSpacing(16)
        for icon_name, title, key in (("tag", "Métadonnées", "metadata"), ("image", "Image", "image")):
            card = _ShortcutCard(icon_name, title, "", compact=True)
            card.clicked.connect(lambda k=key: self.navigate.emit(k))
            pair.addWidget(card)
        shortcuts.addLayout(pair)
        for icon_name, title, hint, key in (
            ("audio", "Studio audio", "Formats, pistes, débit et métadonnées.", "audio"),
            ("video", "Studio vidéo", "Codecs, résolution, flux et métadonnées.", "video"),
            ("shield", "Confidentialité", "Repérez GPS, numéros de série et auteurs.", "metadata"),
        ):
            card = _ShortcutCard(icon_name, title, hint)
            card.clicked.connect(lambda k=key: self.navigate.emit(k))
            shortcuts.addWidget(card)
        shortcuts.addStretch()
        grid.addLayout(shortcuts, 1, 3, 2, 1)

        for column, stretch in enumerate((3, 3, 3, 2)):
            grid.setColumnStretch(column, stretch)
        grid.setRowStretch(2, 1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scrollable(content))

    def _engines_card(self) -> Card:
        card = Card("violet")
        card.body.addWidget(label("Moteurs locaux", "CardTitle"))
        pitch = label("100 % hors ligne : vos fichiers ne quittent jamais votre machine.", "CardHint", wrap=True)
        card.body.addWidget(pitch)
        card.body.addStretch()
        self._engine_status: dict[str, QLabel] = {}
        for tool, name in (("exiftool", "ExifTool"), ("ffmpeg", "FFmpeg")):
            row = QHBoxLayout()
            row.addWidget(label(name, "CardTitle"))
            row.addStretch()
            status = label("vérification…", "Mono")
            row.addWidget(status)
            self._engine_status[tool] = status
            card.body.addLayout(row)
        return card

    # ── Données ──

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.refresh()
        if not self._tools_checked:
            self._tools_checked = True
            jobs.submit(
                lambda: {t: tool_version(t) for t in ("exiftool", "ffmpeg")},
                on_success=self._show_tools,
            )

    def _show_tools(self, versions: dict[str, str | None]) -> None:
        for tool, version in versions.items():
            status = self._engine_status[tool]
            if version:
                status.setText(f"✓ {version}")
                status.setStyleSheet(f"color: {theme.LIME};")
            else:
                status.setText("✕ absent")
                status.setStyleSheet(f"color: {theme.CORAL};")

    def refresh(self) -> None:
        days = self._activity.last_days(7)
        analyses = sum(c.get("analysis", 0) for _, c in days)
        cleans = sum(c.get("clean", 0) for _, c in days)
        active_days = sum(1 for _, c in days if c)

        self._analyses.value.setText(str(analyses))
        self._analyses.unit.setText("fichiers en 7 jours")
        self._analyses.badge.setText(f"{active_days}/7 jours actifs")
        self._analyses.meter.set_ratio(active_days / 7)

        share = cleans / analyses if analyses else 0.0
        self._cleans.value.setText(str(cleans))
        self._cleans.unit.setText("fichiers nettoyés")
        self._cleans.badge.setText(f"{share:.0%} des analyses")
        self._cleans.meter.set_ratio(share)

        self._chart.set_data(
            [(f"{_WEEKDAYS[d.weekday()]} {d.day}", c.get("analysis", 0), c.get("clean", 0)) for d, c in days]
        )

    def _choose_file(self) -> None:
        name, _ = QFileDialog.getOpenFileName(
            self, "Analyser un fichier", "", filetypes.dialog_filter("Médias", filetypes.ALL)
        )
        if name:
            self.openFile.emit(Path(name))
