"""Métadonnées : lecture, rapport de confidentialité, modification et nettoyage."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from spectralab.core import filetypes, metadata
from spectralab.core.activity import ActivityLog
from spectralab.core.cancel import CancelToken
from spectralab.core.metadata import FileMetadata, Severity
from spectralab.core.paths import derived_path

from .. import jobs, session, theme
from ..widgets import Card, DropZone, IconChip, PillBar, RoundedTree, StatusLine, button, label, page_header

_MAX_SHOWN_VALUE = 400
_MAX_TOOLTIP = 4000
_RISK_TEXT = {
    Severity.HIGH: "Risque élevé",
    Severity.MEDIUM: "Risque modéré",
    Severity.LOW: "Risque faible",
}
_PRESET_TAGS = (
    "Artist",
    "Copyright",
    "ImageDescription",
    "XMP-dc:Creator",
    "XMP-dc:Rights",
    "XMP-dc:Subject",
    "Comment",
    "Title",
)
_MODE_EMBEDDED, _MODE_SENSITIVE, _MODE_ALL = range(3)


def _dot(color: str, size: int = 10) -> QIcon:
    pixmap = QPixmap(size * 3, size * 3)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color))
    painter.drawEllipse(0, 0, pixmap.width(), pixmap.height())
    painter.end()
    pixmap.setDevicePixelRatio(3)
    return QIcon(pixmap)


def _clear(layout: QLayout) -> None:
    while (item := layout.takeAt(0)) is not None:
        if widget := item.widget():
            widget.deleteLater()
        elif child := item.layout():
            _clear(child)


def _clean_many(
    paths: list[Path], keep_technical: bool, cancel: CancelToken | None = None
) -> tuple[list[Path], list[str]]:
    outputs, errors = [], []
    for path in paths:
        try:
            outputs.append(metadata.clean_copy(path, keep_technical=keep_technical, cancel=cancel))
        except (metadata.ToolError, ValueError, OSError) as exc:
            errors.append(f"{path.name} : {exc}")
    return outputs, errors


class TagDialog(QDialog):
    """Saisie d'un champ à écrire ; le nom est validé avant d'activer « Écrire »."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Modifier un champ")
        self.setMinimumWidth(420)
        form = QFormLayout(self)
        form.setSpacing(theme.ROW)
        form.setContentsMargins(24, 24, 24, 24)

        self.tag = QComboBox()
        self.tag.setEditable(True)
        self.tag.addItems(_PRESET_TAGS)
        self.value = QLineEdit()
        self.value.setPlaceholderText("Laisser vide pour supprimer le champ")
        self.value.setMaxLength(2000)
        self.in_place = QCheckBox("Modifier le fichier original (sinon : une copie)")
        self.error = label("", "CardHint")
        self.error.setStyleSheet(f"color: {theme.CORAL};")

        form.addRow("Champ", self.tag)
        form.addRow("Valeur", self.value)
        form.addRow(self.in_place)
        form.addRow(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Écrire")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setProperty("variant", "primary")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        self._ok = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.tag.currentTextChanged.connect(self._validate)
        self._validate(self.tag.currentText())

    def _validate(self, text: str) -> None:
        try:
            metadata.validate_tag(text)
        except ValueError as exc:
            self.error.setText(str(exc))
            self._ok.setEnabled(False)
        else:
            self.error.setText("")
            self._ok.setEnabled(True)


class MetadataPage(QWidget):
    def __init__(self, activity: ActivityLog) -> None:
        super().__init__()
        self._activity = activity
        self._meta: dict[Path, FileMetadata] = {}
        self._busy = False

        add = button("Ajouter des fichiers", "primary", "plus")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(theme.GAP)
        root.addWidget(
            page_header(
                "Métadonnées",
                "Voyez ce que vos fichiers révèlent, puis modifiez ou supprimez ces informations.",
                add,
            )
        )

        body = QHBoxLayout()
        body.setSpacing(theme.GAP)
        root.addLayout(body, 1)

        # ── Fichiers ──
        files_card = Card()
        files_card.setFixedWidth(300)
        files_card.body.addWidget(label("FICHIERS", "Caption"))
        self._drop = DropZone(
            "Déposez vos fichiers",
            "Images, audio, vidéo, PDF",
            filetypes.ALL,
            filetypes.dialog_filter("Médias", filetypes.ALL),
        )
        self._drop.setFixedHeight(170)
        self._drop.filesSelected.connect(self.add_files)
        add.clicked.connect(self._drop.open_dialog)
        files_card.body.addWidget(self._drop)
        self._list = QListWidget()
        self._list.setIconSize(QSize(10, 10))
        self._list.currentItemChanged.connect(lambda *_: self._render())
        files_card.body.addWidget(self._list, 1)
        remove = button("Retirer de la liste", icon_name="x")
        remove.clicked.connect(self._remove_current)
        files_card.body.addWidget(remove)
        body.addWidget(files_card)

        # ── Champs ──
        fields_card = Card()
        top = QHBoxLayout()
        self._pills = PillBar(["Intégrées", "Sensibles", "Tout"])
        self._pills.changed.connect(lambda _: self._render())
        top.addWidget(self._pills, 1)
        self._search = QLineEdit()
        self._search.setPlaceholderText("Rechercher un champ ou une valeur…")
        self._search.setClearButtonEnabled(True)
        self._search.setMaximumWidth(280)
        self._search.textChanged.connect(lambda _: self._render())
        top.addWidget(self._search)
        fields_card.body.addLayout(top)
        self._tree = RoundedTree()
        self._tree.setHeaderLabels(["CHAMP", "VALEUR"])
        self._tree.setColumnWidth(0, 230)
        self._tree.setUniformRowHeights(True)
        self._tree.setIndentation(14)
        self._tree.setWordWrap(False)
        fields_card.body.addWidget(self._tree, 1)
        self._empty = label("Ajoutez un fichier pour afficher ses métadonnées.", "CardHint")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fields_card.body.addWidget(self._empty)
        body.addWidget(fields_card, 1)

        # ── Confidentialité et actions ──
        side = QVBoxLayout()
        side.setSpacing(theme.GAP)
        privacy = Card()
        privacy.setFixedWidth(320)
        head = QHBoxLayout()
        head.addWidget(IconChip("shield", "violet", 40))
        head.addWidget(label("Confidentialité", "CardTitle"), 1)
        privacy.body.addLayout(head)
        self._risk = label("—", "PageTitle")
        self._risk_hint = label("", "CardHint", wrap=True)
        privacy.body.addWidget(self._risk)
        privacy.body.addWidget(self._risk_hint)
        self._findings = QVBoxLayout()
        self._findings.setSpacing(8)
        privacy.body.addLayout(self._findings)
        privacy.body.addStretch()
        side.addWidget(privacy, 1)

        actions = Card()
        actions.setFixedWidth(320)
        self._keep = QCheckBox("Conserver orientation et profil couleur")
        self._keep.setChecked(True)
        self._keep.setToolTip("Ces champs techniques ne révèlent rien mais changent l'affichage s'ils disparaissent.")
        actions.body.addWidget(self._keep)
        self._clean_copy = button("Nettoyer une copie", "primary", "sparkles")
        self._clean_all = button("Nettoyer toute la liste", icon_name="refresh")
        self._edit = button("Modifier un champ…", icon_name="edit")
        self._clean_original = button("Nettoyer l'original", "danger", "alert")
        for widget, slot in (
            (self._clean_copy, self._on_clean_copy),
            (self._clean_all, self._on_clean_all),
            (self._edit, self._on_edit),
            (self._clean_original, self._on_clean_original),
        ):
            widget.clicked.connect(slot)
            actions.body.addWidget(widget)
        self._status = StatusLine()
        actions.body.addWidget(self._status)
        side.addWidget(actions)
        body.addLayout(side)

        self._render()

    # ── Fichiers ──

    def add_files(self, paths: Iterable[Path], then: Callable[[], None] | None = None) -> None:
        known = {self._list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self._list.count())}
        new = [p.resolve() for p in paths if p.resolve() not in known]
        if not new:
            if then:
                then()
            return
        for path in new:
            item = QListWidgetItem(_dot(theme.TEXT_3), path.name)
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setToolTip(str(path))
            self._list.addItem(item)
        self._list.setCurrentRow(self._list.count() - len(new))
        self._read(new, then)

    def _read(self, paths: list[Path], then: Callable[[], None] | None = None) -> None:
        self._set_busy(True, f"Lecture de {len(paths)} fichier(s)…")

        def done(results: list[FileMetadata]) -> None:
            for meta in results:
                self._meta[meta.path] = meta
                if not meta.error:
                    session.recent.add(meta.path, "metadata")
            self._activity.record("analysis", sum(1 for m in results if not m.error))
            self._refresh_items()
            self._set_busy(False)
            self._render()
            if then:
                then()
            else:
                self._status.show_message(f"{len(results)} fichier(s) analysé(s).", "ok")

        jobs.submit(metadata.read_metadata, paths, on_success=done, on_error=self._fail)

    def _refresh_items(self) -> None:
        for i in range(self._list.count()):
            item = self._list.item(i)
            meta = self._meta.get(item.data(Qt.ItemDataRole.UserRole))
            if meta is None:
                continue
            if meta.error:
                item.setIcon(_dot(theme.CORAL))
                item.setToolTip(f"{meta.path}\n{meta.error}")
            else:
                level = metadata.risk_level(meta.findings())
                item.setIcon(_dot(theme.SEVERITY_COLORS[level] if level else theme.ACCENT))

    def _remove_current(self) -> None:
        row = self._list.currentRow()
        if row < 0:
            return
        item = self._list.takeItem(row)
        self._meta.pop(item.data(Qt.ItemDataRole.UserRole), None)
        self._render()

    def _current(self) -> FileMetadata | None:
        item = self._list.currentItem()
        return self._meta.get(item.data(Qt.ItemDataRole.UserRole)) if item else None

    # ── Affichage ──

    def _render(self) -> None:
        meta = self._current()
        self._tree.setUpdatesEnabled(False)
        self._tree.clear()
        has_file = meta is not None
        self._tree.setVisible(has_file)
        self._empty.setVisible(not has_file)
        self._empty.setText("Ajoutez un fichier pour afficher ses métadonnées.")
        self._render_privacy(meta)
        self._update_buttons()
        if meta is None:
            self._tree.setUpdatesEnabled(True)
            return

        severity = {entry: f.severity for f in meta.findings() for entry in f.entries}
        mode = self._pills.current()
        needle = self._search.text().strip().lower()
        groups: dict[str, QTreeWidgetItem] = {}
        bold = QFont(self._tree.font())
        bold.setBold(True)
        for entry in meta.entries:
            if mode == _MODE_EMBEDDED and not entry.embedded:
                continue
            if mode == _MODE_SENSITIVE and entry not in severity:
                continue
            if needle and needle not in entry.tag.lower() and needle not in entry.value.lower():
                continue
            parent = groups.get(entry.group)
            if parent is None:
                parent = QTreeWidgetItem(self._tree, [entry.group or "—"])
                parent.setFont(0, bold)
                parent.setForeground(0, QColor(theme.VIOLET))
                parent.setFirstColumnSpanned(True)
                parent.setExpanded(True)
                groups[entry.group] = parent
            shown = entry.value if len(entry.value) <= _MAX_SHOWN_VALUE else entry.value[:_MAX_SHOWN_VALUE] + "…"
            child = QTreeWidgetItem(parent, [entry.tag, shown])
            child.setToolTip(1, entry.value[:_MAX_TOOLTIP])
            if level := severity.get(entry):
                child.setForeground(0, QColor(theme.SEVERITY_COLORS[level]))
        self._tree.setUpdatesEnabled(True)
        if not groups:
            self._tree.setVisible(False)
            self._empty.setVisible(True)
            self._empty.setText(meta.error or ("Aucun résultat pour cette recherche." if needle else "Aucune métadonnée à afficher ici."))

    def _render_privacy(self, meta: FileMetadata | None) -> None:
        _clear(self._findings)
        if meta is None or meta.error:
            self._risk.setText("—")
            self._risk.setStyleSheet("")
            self._risk_hint.setText("Le rapport apparaît après l'analyse d'un fichier.")
            return
        findings = meta.findings()
        level = metadata.risk_level(findings)
        if level is None:
            self._risk.setText("Aucun risque")
            self._risk.setStyleSheet(f"color: {theme.ACCENT};")
            self._risk_hint.setText(f"{len(meta.embedded)} champ(s) intégré(s), aucun jugé sensible.")
            return
        self._risk.setText(_RISK_TEXT[level])
        self._risk.setStyleSheet(f"color: {theme.SEVERITY_COLORS[level]};")
        count = sum(len(f.entries) for f in findings)
        self._risk_hint.setText(f"{count} champ(s) sensible(s) sur {len(meta.embedded)} intégré(s).")
        for finding in findings:
            row = QHBoxLayout()
            row.addWidget(label(finding.label), 1)
            row.addWidget(label(str(len(finding.entries)), "Badge"))
            self._findings.addLayout(row)

    def _update_buttons(self) -> None:
        meta = self._current()
        usable = meta is not None and not meta.error and not self._busy
        for widget in (self._clean_copy, self._edit, self._clean_original):
            widget.setEnabled(usable)
        self._clean_all.setEnabled(not self._busy and self._list.count() > 0)

    def _set_busy(self, busy: bool, message: str = "") -> None:
        self._busy = busy
        if message:
            self._status.show_message(message, "busy")
        self._update_buttons()

    def _fail(self, message: str) -> None:
        self._set_busy(False)
        self._status.show_message(message, "error")

    # ── Actions ──

    def _keep_technical(self) -> bool:
        return self._keep.isChecked()

    def _on_clean_copy(self) -> None:
        meta = self._current()
        if meta is None:
            return
        self._set_busy(True, "Nettoyage en cours…")

        def done(output: Path) -> None:
            self._activity.record("clean")
            self._set_busy(False)
            self.add_files([output], lambda: self._status.show_message(f"Copie nettoyée : {output.name}", "ok"))

        jobs.submit(metadata.clean_copy, meta.path, keep_technical=self._keep_technical(), on_success=done, on_error=self._fail)

    def _on_clean_all(self) -> None:
        paths = [self._list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self._list.count())]
        paths = [p for p in paths if (m := self._meta.get(p)) and not m.error]
        if not paths:
            return
        self._set_busy(True, f"Nettoyage de {len(paths)} fichier(s)…")

        def done(result: tuple[list[Path], list[str]]) -> None:
            outputs, errors = result
            self._activity.record("clean", len(outputs))
            self._set_busy(False)

            def report() -> None:
                if errors:
                    summary = f"{len(outputs)} copie(s) créée(s), {len(errors)} échec(s) :\n" + "\n".join(errors)
                    self._status.show_message(summary, "error")
                else:
                    self._status.show_message(f"{len(outputs)} copie(s) nettoyée(s) créée(s).", "ok")

            self.add_files(outputs, report)

        jobs.submit(_clean_many, paths, self._keep_technical(), on_success=done, on_error=self._fail)

    def _on_clean_original(self) -> None:
        meta = self._current()
        if meta is None:
            return
        answer = QMessageBox.warning(
            self,
            "Nettoyer l'original",
            f"Les métadonnées de « {meta.path.name} » seront supprimées définitivement.\n\n"
            "Cette opération ne peut pas être annulée. Continuer ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._set_busy(True, "Nettoyage de l'original…")

        def done(path: Path) -> None:
            self._activity.record("clean")
            self._read([path], lambda: self._status.show_message(f"Original nettoyé : {path.name}", "ok"))

        jobs.submit(
            metadata.strip_metadata,
            meta.path,
            output=None,
            keep_technical=self._keep_technical(),
            on_success=done,
            on_error=self._fail,
        )

    def _on_edit(self) -> None:
        meta = self._current()
        if meta is None:
            return
        dialog = TagDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        tag, value = dialog.tag.currentText().strip(), dialog.value.text()
        output = None if dialog.in_place.isChecked() else derived_path(meta.path, "_modifie")
        self._set_busy(True, "Écriture du champ…")

        def done(path: Path) -> None:
            if output is None:
                self._read([path], lambda: self._status.show_message(f"« {tag} » écrit dans l'original.", "ok"))
            else:
                self._set_busy(False)
                self.add_files([path], lambda: self._status.show_message(f"« {tag} » écrit dans {path.name}.", "ok"))

        jobs.submit(metadata.write_tags, meta.path, {tag: value}, output=output, on_success=done, on_error=self._fail)
