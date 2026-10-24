"""Fenêtre principale : rail de navigation noir à gauche, pages empilées à droite."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, QThreadPool
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
)

from spectralab import APP_NAME, __version__
from spectralab.core import filetypes
from spectralab.core.activity import ActivityLog
from spectralab.core.tools import tool_version

from . import icons, jobs, theme
from .pages.compare import ComparePage
from .pages.dashboard import DashboardPage
from .pages.forensics import ForensicsPage
from .pages.image import ImagePage
from .pages.metadata import MetadataPage
from .pages.spectrum import SpectrumPage
from .pages.video import VideoPage
from .widgets import Backdrop

# (clé, icône, libellé) dans l'ordre du rail ; Ctrl+1… suit cet ordre.
_NAV = (
    ("home", "home", "Accueil"),
    ("spectrum", "wave", "Spectre"),
    ("video", "video", "Vidéo"),
    ("compare", "layers", "Comparer"),
    ("image", "image", "Image"),
    ("metadata", "tag", "Métadonnées"),
    ("forensics", "fingerprint", "Forensique"),
)
_ENGINES = ("exiftool", "ffmpeg")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(icons.logo_pixmap(64))
        self.setMinimumSize(1280, 800)
        self.resize(1480, 920)

        activity = ActivityLog()
        self._dashboard = DashboardPage(activity)
        self._spectrum = SpectrumPage(activity)
        self._video = VideoPage(activity)
        self._compare = ComparePage(activity)
        self._image = ImagePage(activity)
        self._metadata = MetadataPage(activity)
        self._forensics = ForensicsPage(activity)
        self._pages = {
            "home": self._dashboard,
            "spectrum": self._spectrum,
            "video": self._video,
            "compare": self._compare,
            "image": self._image,
            "metadata": self._metadata,
            "forensics": self._forensics,
        }

        self._stack = QStackedWidget()
        for page in self._pages.values():
            self._stack.addWidget(page)

        backdrop = Backdrop()
        layout = QHBoxLayout(backdrop)
        layout.setContentsMargins(theme.GAP, theme.GAP, theme.GUTTER, theme.GAP)
        layout.setSpacing(theme.GUTTER)
        layout.addWidget(self._build_rail())
        page_area = QVBoxLayout()
        page_area.setContentsMargins(0, theme.ROW, 0, 0)
        page_area.addWidget(self._stack)
        layout.addLayout(page_area, 1)
        self.setCentralWidget(backdrop)
        self._add_shortcuts()

        self._dashboard.navigate.connect(self.show_page)
        self._dashboard.openFile.connect(self.open_file)
        self._dashboard.reopen.connect(self._reopen)
        self._dashboard.aboutRequested.connect(self._about)
        self._spectrum.showMetadata.connect(self._show_metadata)
        self._video.openInSpectrum.connect(lambda p: self._reopen(p, "spectrum"))
        jobs.submit(lambda: {t: tool_version(t) for t in _ENGINES}, on_success=self._dashboard.set_engines)

    # ── Rail ──
    def _build_rail(self) -> QFrame:
        rail = QFrame()
        rail.setObjectName("Sidebar")
        rail.setFixedWidth(76)
        column = QVBoxLayout(rail)
        column.setContentsMargins(14, 16, 14, 16)
        column.setSpacing(10)

        logo = QLabel()
        logo.setPixmap(icons.logo_pixmap(46))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setToolTip(f"{APP_NAME} {__version__}")
        column.addWidget(logo)
        column.addSpacing(30)

        self._nav = QButtonGroup(self)
        self._nav.setExclusive(True)
        for key, icon_name, text in _NAV:
            nav_button = self._rail_button(icon_name, text)
            nav_button.setCheckable(True)
            nav_button.setProperty("page", key)
            nav_button.clicked.connect(lambda _=False, k=key: self.show_page(k))
            self._nav.addButton(nav_button)
            column.addWidget(nav_button, 0, Qt.AlignmentFlag.AlignHCenter)
        self._nav.buttons()[0].setChecked(True)

        column.addStretch()
        about = self._rail_button("info", "À propos")
        about.clicked.connect(self._about)
        column.addWidget(about, 0, Qt.AlignmentFlag.AlignHCenter)
        return rail

    @staticmethod
    def _rail_button(icon_name: str, text: str) -> QToolButton:
        rail_button = QToolButton()
        rail_button.setObjectName("NavButton")
        rail_button.setIcon(icons.icon(icon_name, theme.ON_DARK, 20))
        rail_button.setIconSize(QSize(20, 20))
        rail_button.setFixedSize(48, 48)
        rail_button.setToolTip(text)
        rail_button.setAccessibleName(text)
        rail_button.setCursor(Qt.CursorShape.PointingHandCursor)
        rail_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        return rail_button

    def _add_shortcuts(self) -> None:
        def action(shortcut: str, handler) -> None:  # noqa: ANN001 - appelable Qt
            item = QAction(self)
            item.setShortcut(QKeySequence(shortcut))
            item.triggered.connect(handler)
            self.addAction(item)

        action("Ctrl+O", self._choose_file)
        action("Ctrl+Shift+O", self._choose_forensics)
        action("Ctrl+Q", self.close)
        action("F11", lambda: self.showNormal() if self.isFullScreen() else self.showFullScreen())
        for index, (key, _, _) in enumerate(_NAV, start=1):
            action(f"Ctrl+{index}", lambda k=key: self.show_page(k))

    # ── Navigation ──
    def show_page(self, key: str) -> None:
        self._stack.setCurrentWidget(self._pages[key])
        for nav_button in self._nav.buttons():
            if nav_button.property("page") == key:
                nav_button.setChecked(True)

    def open_file(self, path: Path) -> None:
        kind = filetypes.kind_of(path)
        if kind == "image":
            self.show_page("image")
            self._image.open_image(path)
        elif kind == "audio":
            self._reopen(path, "spectrum")
        elif kind == "video":
            self.show_page("video")
            self._video.open_file(path)
        elif kind == "document":
            self._show_metadata(path)
        else:
            # Type inconnu (archive, exécutable, binaire…) : place à l'analyse forensique.
            self._reopen(path, "forensics")

    def _reopen(self, path: Path, tool: str) -> None:
        if not path.is_file():
            QMessageBox.information(self, APP_NAME, f"{path.name} n'existe plus.")
            return
        if tool == "forensics":
            self.show_page("forensics")
            self._forensics.open_file(path)
        elif tool == "spectrum":
            self.show_page("spectrum")
            self._spectrum.open_file(path)
        elif tool == "metadata":
            self._show_metadata(path)
        else:
            self.open_file(path)

    def _show_metadata(self, path: Path) -> None:
        self.show_page("metadata")
        self._metadata.add_files([path])

    def _choose_file(self) -> None:
        name, _ = QFileDialog.getOpenFileName(self, "Ouvrir un fichier", "", "Tous les fichiers (*)")
        if name:
            self.open_file(Path(name))

    def _choose_forensics(self) -> None:
        name, _ = QFileDialog.getOpenFileName(self, "Analyse forensique", "", "Tous les fichiers (*)")
        if name:
            self._reopen(Path(name), "forensics")

    def _about(self) -> None:
        QMessageBox.about(
            self,
            f"À propos de {APP_NAME}",
            f"{APP_NAME} {__version__}\n\n"
            "Studio d'analyse, d'expertise et de protection de médias.\n"
            "Tous les traitements s'exécutent localement.\n\n"
            "Raccourcis : Ctrl+O ouvrir · Ctrl+1 à Ctrl+7 pages · F11 plein écran.\n\n"
            "Moteurs : ExifTool (Phil Harvey), FFmpeg, NumPy, Pillow, Qt.\n"
            "Développé par VISCHENZISCH.",
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        # Les outils externes en cours sont tués et leurs fichiers temporaires
        # supprimés avant la sortie, plutôt qu'abandonnés en arrière-plan.
        jobs.cancel_all()
        QThreadPool.globalInstance().waitForDone(5000)
        super().closeEvent(event)
