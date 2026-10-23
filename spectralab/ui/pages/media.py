"""Audio et vidéo : informations techniques, flux et feuille de route des outils IA."""

from __future__ import annotations

from html import escape
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QStackedLayout, QVBoxLayout, QWidget

from spectralab.core import filetypes
from spectralab.core.activity import ActivityLog
from spectralab.core.media_info import MediaInfo, format_bitrate, format_duration, format_size, probe

from .. import jobs, theme
from ..widgets import Card, DropZone, IconChip, StatusLine, button, label, page_header

_KINDS = {
    "audio": {
        "title": "Studio audio",
        "subtitle": "Inspectez la structure de vos enregistrements avant de les restaurer.",
        "icon": "audio",
        "extensions": filetypes.AUDIO,
        "roadmap": (
            ("Restauration : débruitage, souffle, saturation", "Phase 3"),
            ("Séparation voix / musique", "Phase 3"),
            ("Transcription et identification des locuteurs", "Phase 3"),
            ("Reconstitution de passages manquants", "Phase 5"),
            ("Clonage de voix avec consentement et filigrane", "Phase 5"),
        ),
    },
    "video": {
        "title": "Studio vidéo",
        "subtitle": "Codecs, résolution et flux de vos vidéos, sans les envoyer nulle part.",
        "icon": "video",
        "extensions": filetypes.VIDEO,
        "roadmap": (
            ("Découpage et extraction d'images", "Phase 4"),
            ("Détection des changements de scène", "Phase 4"),
            ("Floutage automatique des visages", "Phase 4"),
            ("Analyse forensique image par image", "Phase 5"),
            ("Indices de deepfake", "Phase 5"),
        ),
    },
}


class _Stat(Card):
    def __init__(self, caption: str) -> None:
        super().__init__()
        self.body.addWidget(label(caption, "Caption"))
        self.value = label("—", "PageTitle")
        self.body.addWidget(self.value)


class MediaPage(QWidget):
    showMetadata = Signal(Path)

    def __init__(self, kind: str, activity: ActivityLog) -> None:
        super().__init__()
        spec = _KINDS[kind]
        self._activity = activity
        self._path: Path | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(16)
        choose = button("Choisir un fichier", icon_name="folder")
        self._meta_button = button("Voir les métadonnées", icon_name="tag")
        self._meta_button.setEnabled(False)
        self._meta_button.clicked.connect(lambda: self._path and self.showMetadata.emit(self._path))
        root.addWidget(page_header(spec["title"], spec["subtitle"], self._meta_button, choose))

        body = QHBoxLayout()
        body.setSpacing(16)
        root.addLayout(body, 1)

        main = QVBoxLayout()
        main.setSpacing(16)
        self._stack = QStackedLayout()
        self._drop = DropZone(
            "Déposez un fichier",
            ", ".join(sorted(e.lstrip(".").upper() for e in spec["extensions"])),
            spec["extensions"],
            filetypes.dialog_filter(spec["title"], spec["extensions"]),
        )
        self._drop.filesSelected.connect(lambda files: self.open_file(files[0]))
        choose.clicked.connect(self._drop.open_dialog)
        self._stack.addWidget(self._drop)

        details = QWidget()
        details_layout = QVBoxLayout(details)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(16)
        stats = QGridLayout()
        stats.setSpacing(16)
        self._stats = {key: _Stat(caption) for key, caption in (
            ("duration", "DURÉE"), ("size", "TAILLE"), ("bitrate", "DÉBIT"), ("streams", "FLUX"),
        )}
        for i, stat in enumerate(self._stats.values()):
            stats.addWidget(stat, 0, i)
        details_layout.addLayout(stats)

        streams_card = Card()
        head = QHBoxLayout()
        head.addWidget(IconChip(spec["icon"], "lime", 40))
        self._name = label("", "CardTitle")
        head.addWidget(self._name, 1)
        streams_card.body.addLayout(head)
        self._format = label("", "CardHint", wrap=True)
        streams_card.body.addWidget(self._format)
        self._streams = QVBoxLayout()
        self._streams.setSpacing(10)
        streams_card.body.addLayout(self._streams)
        streams_card.body.addStretch()
        details_layout.addWidget(streams_card, 1)
        self._stack.addWidget(details)

        main.addLayout(self._stack, 1)
        self._status = StatusLine()
        main.addWidget(self._status)
        body.addLayout(main, 1)

        roadmap = Card("violet")
        roadmap.setFixedWidth(320)
        roadmap.body.addWidget(label("Bientôt dans ce studio", "CardTitle"))
        roadmap.body.addWidget(label("Fonctions en préparation, traitées 100 % en local.", "CardHint", wrap=True))
        for text, phase in spec["roadmap"]:
            row = QHBoxLayout()
            row.addWidget(label(text, wrap=True), 1)
            row.addWidget(label(phase, "Badge"), 0, Qt.AlignmentFlag.AlignTop)
            roadmap.body.addLayout(row)
        roadmap.body.addStretch()
        body.addWidget(roadmap)

    def open_file(self, path: Path) -> None:
        self._status.show_message("Analyse…", "busy")
        jobs.submit(probe, path, on_success=self._show, on_error=lambda m: self._status.show_message(m, "error"))

    def _show(self, info: MediaInfo) -> None:
        self._path = info.path
        self._activity.record("analysis")
        self._meta_button.setEnabled(True)
        self._name.setText(info.path.name)
        self._format.setText(info.format_name)
        self._stats["duration"].value.setText(format_duration(info.duration))
        self._stats["size"].value.setText(format_size(info.size))
        self._stats["bitrate"].value.setText(format_bitrate(info.bit_rate))
        self._stats["streams"].value.setText(str(len(info.streams)))

        while (item := self._streams.takeAt(0)) is not None:
            if widget := item.widget():
                widget.deleteLater()
        for stream in info.streams:
            row = QWidget()
            line = QHBoxLayout(row)
            line.setContentsMargins(0, 0, 0, 0)
            kind = label(stream.kind.upper(), "Badge")
            kind.setFixedWidth(84)
            kind.setAlignment(Qt.AlignmentFlag.AlignCenter)
            line.addWidget(kind)
            # Rich text pour la mise en forme ; tout ce qui vient du fichier est échappé.
            text = QLabel(f"<b>{escape(stream.codec)}</b><br><span style='color:{theme.TEXT_2}'>{escape(stream.details)}</span>")
            text.setTextFormat(Qt.TextFormat.RichText)
            line.addWidget(text, 1)
            self._streams.addWidget(row)
        self._stack.setCurrentIndex(1)
        self._status.show_message("Analyse terminée.", "ok")
