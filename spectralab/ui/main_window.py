"""Fenêtre principale : barre latérale + pages empilées."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
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

from . import icons, theme
from .pages.dashboard import DashboardPage
from .pages.image import ImagePage
from .pages.media import MediaPage
from .pages.metadata import MetadataPage
from .widgets import Backdrop

_NAV = (
    ("home", "home", "Accueil"),
    ("metadata", "tag", "Métadonnées"),
    ("image", "image", "Image"),
    ("audio", "audio", "Audio"),
    ("video", "video", "Vidéo"),
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(icons.logo_pixmap(64))
        self.setMinimumSize(1180, 760)
        self.resize(1440, 900)

        activity = ActivityLog()
        self._dashboard = DashboardPage(activity)
        self._metadata = MetadataPage(activity)
        self._image = ImagePage(activity)
        self._audio = MediaPage("audio", activity)
        self._video = MediaPage("video", activity)
        self._pages = {
            "home": self._dashboard,
            "metadata": self._metadata,
            "image": self._image,
            "audio": self._audio,
            "video": self._video,
        }

        self._stack = QStackedWidget()
        for page in self._pages.values():
            self._stack.addWidget(page)

        backdrop = Backdrop()
        layout = QHBoxLayout(backdrop)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(20)
        layout.addWidget(self._build_sidebar())
        layout.addWidget(self._stack, 1)
        self.setCentralWidget(backdrop)

        self._dashboard.navigate.connect(self.show_page)
        self._dashboard.openFile.connect(self.open_file)
        for media_page in (self._audio, self._video):
            media_page.showMetadata.connect(self._show_metadata)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(80)
        column = QVBoxLayout(sidebar)
        column.setContentsMargins(12, 16, 12, 16)
        column.setSpacing(8)

        logo = QLabel()
        logo.setPixmap(icons.logo_pixmap(44))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setToolTip(f"{APP_NAME} {__version__}")
        column.addWidget(logo)
        column.addSpacing(24)

        self._nav = QButtonGroup(self)
        self._nav.setExclusive(True)
        for key, icon_name, tooltip in _NAV:
            nav_button = QToolButton()
            nav_button.setObjectName("NavButton")
            nav_button.setCheckable(True)
            nav_button.setIcon(icons.icon(icon_name, theme.TEXT, 22))
            nav_button.setIconSize(QSize(22, 22))
            nav_button.setToolTip(tooltip)
            nav_button.setAccessibleName(tooltip)
            nav_button.setCursor(Qt.CursorShape.PointingHandCursor)
            nav_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            nav_button.clicked.connect(lambda _=False, k=key: self.show_page(k))
            self._nav.addButton(nav_button)
            nav_button.setProperty("page", key)
            column.addWidget(nav_button, 0, Qt.AlignmentFlag.AlignHCenter)
        self._nav.buttons()[0].setChecked(True)

        column.addStretch()
        about = QToolButton()
        about.setObjectName("NavButton")
        about.setIcon(icons.icon("info", theme.TEXT_2, 22))
        about.setIconSize(QSize(22, 22))
        about.setToolTip("À propos")
        about.setAccessibleName("À propos")
        about.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        about.clicked.connect(self._about)
        column.addWidget(about, 0, Qt.AlignmentFlag.AlignHCenter)
        return sidebar

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
        elif kind in ("audio", "video"):
            self.show_page(kind)
            self._pages[kind].open_file(path)
        else:
            self._show_metadata(path)

    def _show_metadata(self, path: Path) -> None:
        self.show_page("metadata")
        self._metadata.add_files([path])

    def _about(self) -> None:
        QMessageBox.about(
            self,
            f"À propos de {APP_NAME}",
            f"{APP_NAME} {__version__}\n\n"
            "Studio d'analyse, de restauration et de protection de médias.\n"
            "Tous les traitements s'exécutent localement.\n\n"
            "Moteurs : ExifTool (Phil Harvey), FFmpeg, Pillow, Qt.\n"
            "Développé par VISCHENZISCH.",
        )
