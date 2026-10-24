"""Image : aperçu, conversion de format et redimensionnement."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImageReader, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QSpinBox,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from spectralab.core import filetypes, image_ops
from spectralab.core.activity import ActivityLog
from spectralab.core.image_ops import ImageResult
from spectralab.core.media_info import format_size

from .. import jobs, session, theme
from ..widgets import Card, DropZone, IconChip, StatusLine, button, label, page_header, rounded_pixmap

# Plafond mémoire du décodage de l'aperçu (Mo) : protège contre les images géantes.
QImageReader.setAllocationLimit(512)


class _Preview(QLabel):
    def __init__(self) -> None:
        super().__init__()
        self._source = QPixmap()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(200, 200)

    def set_source(self, pixmap: QPixmap) -> None:
        self._source = pixmap
        self._fit()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._fit()

    def _fit(self) -> None:
        if self._source.isNull():
            self.clear()
            return
        ratio = self.devicePixelRatioF()
        scaled = self._source.scaled(
            self.size() * ratio, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        scaled.setDevicePixelRatio(ratio)
        self.setPixmap(rounded_pixmap(scaled))


class ImagePage(QWidget):
    def __init__(self, activity: ActivityLog) -> None:
        super().__init__()
        self._activity = activity
        self._path: Path | None = None
        self._size = QSize()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(theme.GAP)
        change = button("Choisir une image", icon_name="folder")
        root.addWidget(page_header("Image", "Convertissez et redimensionnez sans perte de contrôle sur vos métadonnées.", change))

        body = QHBoxLayout()
        body.setSpacing(theme.GAP)
        root.addLayout(body, 1)

        # ── Aperçu ──
        preview_card = Card()
        self._stack = QStackedLayout()
        self._drop = DropZone(
            "Déposez une image",
            "PNG, JPEG, WEBP, TIFF, HEIC… ou cliquez pour parcourir",
            filetypes.IMAGE,
            filetypes.dialog_filter("Images", filetypes.IMAGE),
        )
        self._drop.filesSelected.connect(lambda files: self.open_image(files[0]))
        change.clicked.connect(self._drop.open_dialog)
        self._preview = _Preview()
        self._stack.addWidget(self._drop)
        self._stack.addWidget(self._preview)
        preview_card.body.addLayout(self._stack, 1)
        self._info = label("", "CardHint")
        preview_card.body.addWidget(self._info)
        body.addWidget(preview_card, 1)

        # ── Réglages ──
        side = QVBoxLayout()
        side.setSpacing(theme.GAP)

        convert = Card()
        convert.setFixedWidth(340)
        head = QHBoxLayout()
        head.addWidget(IconChip("refresh", "accent", 40))
        head.addWidget(label("Conversion", "CardTitle"), 1)
        convert.body.addLayout(head)
        self._format = QComboBox()
        self._format.addItems(image_ops.available_formats())
        convert.body.addWidget(label("FORMAT DE SORTIE", "Caption"))
        convert.body.addWidget(self._format)
        convert.body.addWidget(label("QUALITÉ (JPEG, WEBP, AVIF)", "Caption"))
        quality_row = QHBoxLayout()
        self._quality = QSlider(Qt.Orientation.Horizontal)
        self._quality.setRange(40, 100)
        self._quality.setValue(90)
        quality_value = label("90", "Mono")
        self._quality.valueChanged.connect(lambda v: quality_value.setText(str(v)))
        quality_row.addWidget(self._quality, 1)
        quality_row.addWidget(quality_value)
        convert.body.addLayout(quality_row)
        self._convert = button("Convertir", "primary", "refresh")
        self._convert.clicked.connect(self._on_convert)
        convert.body.addWidget(self._convert)
        side.addWidget(convert)

        resize = Card()
        resize.setFixedWidth(340)
        head = QHBoxLayout()
        head.addWidget(IconChip("resize", "violet", 40))
        head.addWidget(label("Redimensionnement", "CardTitle"), 1)
        resize.body.addLayout(head)
        dims = QGridLayout()
        dims.setHorizontalSpacing(10)
        self._width = QSpinBox()
        self._height = QSpinBox()
        for spin in (self._width, self._height):
            spin.setRange(1, image_ops.MAX_DIMENSION)
            spin.setSuffix(" px")
            spin.lineEdit().setTextMargins(10, 0, 0, 0)  # Qt ignore le padding CSS ici
        dims.addWidget(label("LARGEUR", "Caption"), 0, 0)
        dims.addWidget(label("HAUTEUR", "Caption"), 0, 1)
        dims.addWidget(self._width, 1, 0)
        dims.addWidget(self._height, 1, 1)
        resize.body.addLayout(dims)
        self._ratio = QCheckBox("Conserver les proportions")
        self._ratio.setChecked(True)
        self._ratio.toggled.connect(self._height.setDisabled)
        self._height.setDisabled(True)
        self._width.valueChanged.connect(self._sync_height)
        resize.body.addWidget(self._ratio)
        self._resize = button("Redimensionner", icon_name="resize")
        self._resize.clicked.connect(self._on_resize)
        resize.body.addWidget(self._resize)
        side.addWidget(resize)

        output = Card()
        output.setFixedWidth(340)
        self._keep_meta = QCheckBox("Recopier les métadonnées EXIF")
        self._keep_meta.setToolTip("Désactivé par défaut : les fichiers produits ne contiennent ni GPS ni appareil.")
        output.body.addWidget(self._keep_meta)
        self._status = StatusLine()
        output.body.addWidget(self._status)
        side.addWidget(output)
        side.addStretch()
        body.addLayout(side)

        self._set_enabled(False)

    def open_image(self, path: Path) -> None:
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            self._status.show_message(f"Image illisible : {reader.errorString()}", "error")
            return
        self._path = path
        self._size = image.size()
        self._preview.set_source(QPixmap.fromImage(image))
        self._stack.setCurrentWidget(self._preview)
        self._info.setText(f"{path.name} · {image.width()}×{image.height()} px · {format_size(path.stat().st_size)}")
        self._width.blockSignals(True)
        self._width.setValue(image.width())
        self._width.blockSignals(False)
        self._height.setValue(image.height())
        self._activity.record("analysis")
        session.recent.add(path, "image")
        self._status.show_message("Image chargée.", "info")
        self._set_enabled(True)

    def _sync_height(self, width: int) -> None:
        if self._ratio.isChecked() and self._size.width() > 0:
            self._height.setValue(max(1, round(self._size.height() * width / self._size.width())))

    def _set_enabled(self, enabled: bool) -> None:
        for widget in (self._convert, self._resize):
            widget.setEnabled(enabled)

    def _done(self, result: ImageResult) -> None:
        self._activity.record("convert")
        self._set_enabled(True)
        w, h = result.dimensions
        self._status.show_message(
            f"Créé : {result.path.name}\n{w}×{h} px · {format_size(result.size_before)} → {format_size(result.size_after)}",
            "ok",
        )

    def _fail(self, message: str) -> None:
        self._set_enabled(True)
        self._status.show_message(message, "error")

    def _on_convert(self) -> None:
        if self._path is None:
            return
        self._set_enabled(False)
        self._status.show_message("Conversion…", "busy")
        jobs.submit(
            image_ops.convert_image,
            self._path,
            self._format.currentText(),
            quality=self._quality.value(),
            keep_metadata=self._keep_meta.isChecked(),
            on_success=self._done,
            on_error=self._fail,
        )

    def _on_resize(self) -> None:
        if self._path is None:
            return
        self._set_enabled(False)
        self._status.show_message("Redimensionnement…", "busy")
        jobs.submit(
            image_ops.resize_image,
            self._path,
            self._width.value(),
            None if self._ratio.isChecked() else self._height.value(),
            keep_metadata=self._keep_meta.isChecked(),
            on_success=self._done,
            on_error=self._fail,
        )
