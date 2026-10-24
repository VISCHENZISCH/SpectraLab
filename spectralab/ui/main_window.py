"""Fenêtre principale : barre latérale + pages empilées."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, QThreadPool
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
)

from spectralab import APP_NAME, __version__
from spectralab.core import filetypes
from spectralab.core.activity import ActivityLog

from . import icons, jobs, theme
from .pages.dashboard import DashboardPage
from .pages.forensics import ForensicsPage
from .pages.image import ImagePage
from .pages.metadata import MetadataPage
from .pages.spectrum import SpectrumPage
from .widgets import Backdrop, label

# (section, [(clé, icône, libellé)]) ; une section vide n'a pas de titre.
_NAV = (
    ("", (("home", "home", "Accueil"),)),
    ("ANALYSE", (
        ("spectrum", "wave", "Spectre"),
        ("image", "image", "Image"),
        ("metadata", "tag", "Métadonnées"),
    )),
    ("SÉCURITÉ", (
        ("forensics", "fingerprint", "Forensique"),
    )),
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(icons.logo_pixmap(64))
        self.setMinimumSize(1280, 800)
        self.resize(1440, 900)

        activity = ActivityLog()
        self._dashboard = DashboardPage(activity)
        self._metadata = MetadataPage(activity)
        self._image = ImagePage(activity)
        self._spectrum = SpectrumPage(activity)
        self._forensics = ForensicsPage(activity)
        self._pages = {
            "home": self._dashboard,
            "spectrum": self._spectrum,
            "image": self._image,
            "metadata": self._metadata,
            "forensics": self._forensics,
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
        self._spectrum.showMetadata.connect(self._show_metadata)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        column = QVBoxLayout(sidebar)
        column.setContentsMargins(14, 18, 14, 16)
        column.setSpacing(4)

        brand = QHBoxLayout()
        brand.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(icons.logo_pixmap(40))
        logo.setToolTip(f"{APP_NAME} {__version__}")
        brand.addWidget(logo)
        names = QVBoxLayout()
        names.setSpacing(0)
        names.addWidget(label(APP_NAME, "Brand"))
        names.addWidget(label("STUDIO FORENSIQUE", "BrandSub"))
        brand.addLayout(names, 1)
        column.addLayout(brand)
        column.addSpacing(18)

        self._nav = QButtonGroup(self)
        self._nav.setExclusive(True)
        for section, entries in _NAV:
            if section:
                column.addWidget(label(section, "NavSection"))
            for key, icon_name, text in entries:
                nav_button = QToolButton()
                nav_button.setObjectName("NavButton")
                nav_button.setCheckable(True)
                nav_button.setText(text)
                nav_button.setIcon(icons.icon(icon_name, theme.TEXT, 20))
                nav_button.setIconSize(QSize(20, 20))
                nav_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
                nav_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                nav_button.setAccessibleName(text)
                nav_button.setCursor(Qt.CursorShape.PointingHandCursor)
                nav_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
                nav_button.clicked.connect(lambda _=False, k=key: self.show_page(k))
                nav_button.setProperty("page", key)
                self._nav.addButton(nav_button)
                column.addWidget(nav_button)
        self._nav.buttons()[0].setChecked(True)

        column.addStretch()
        local = label("● Traitement 100 % local", "CardHint")
        local.setStyleSheet(f"color: {theme.LIME}; padding: 0 14px 8px;")
        column.addWidget(local)
        about = QToolButton()
        about.setObjectName("NavButton")
        about.setText("À propos")
        about.setIcon(icons.icon("info", theme.TEXT_2, 20))
        about.setIconSize(QSize(20, 20))
        about.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        about.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        about.setAccessibleName("À propos")
        about.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        about.clicked.connect(self._about)
        column.addWidget(about)
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
            self.show_page("spectrum")
            self._spectrum.open_file(path)
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
            "Moteurs : ExifTool (Phil Harvey), FFmpeg, NumPy, Pillow, Qt.\n"
            "Développé par VISCHENZISCH.",
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        # Les outils externes en cours sont tués et leurs fichiers temporaires
        # supprimés avant la sortie, plutôt qu'abandonnés en arrière-plan.
        jobs.cancel_all()
        QThreadPool.globalInstance().waitForDone(5000)
        super().closeEvent(event)
