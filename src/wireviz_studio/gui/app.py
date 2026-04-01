"""Application bootstrap for WireViz Studio."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from wireviz_studio import APP_NAME
from wireviz_studio.gui.main_window import MainWindow
from wireviz_studio.gui.settings import AppSettings
from wireviz_studio.gui.theme_loader import apply_theme


def create_application() -> QApplication:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("WireViz Studio")
    app.setOrganizationDomain("wireviz.studio") # TODO: Update to actual domain when available or read from init file
    return app


def run() -> int:
    app = create_application()
    settings = AppSettings()
    apply_theme(app, settings)

    window = MainWindow(settings=settings, app=app)
    window.show()
    return app.exec()
