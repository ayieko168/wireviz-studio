"""Theme loading helpers shared by app bootstrap and main window."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from wireviz_studio.gui.settings import AppSettings


def _theme_path(theme_name: str) -> Path:
    return Path(__file__).resolve().parent / "themes" / f"{theme_name}.qss"


def apply_theme(app: QApplication, settings: AppSettings) -> None:
    theme_name = settings.theme
    qss_path = _theme_path(theme_name)
    if not qss_path.exists():
        theme_name = "light"
        qss_path = _theme_path(theme_name)
        settings.theme = theme_name

    app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
