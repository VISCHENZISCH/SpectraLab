"""Point d'entrée de l'application graphique."""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from spectralab import APP_NAME, __version__
from spectralab.core.activity import data_dir


def _configure_logging() -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    try:
        log_dir = data_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_dir / "spectralab.log", encoding="utf-8"))
    except OSError:
        pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s : %(message)s",
        handlers=handlers,
    )


def main() -> int:
    _configure_logging()
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("VISCHENZISCH")
    app.setDesktopFileName("spectralab")
    app.setStyle("Fusion")

    # Imports après la création de QApplication (polices, pixmaps).
    from spectralab.ui import theme
    from spectralab.ui.main_window import MainWindow

    app.setFont(theme.app_font())
    app.setStyleSheet(theme.stylesheet())

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
