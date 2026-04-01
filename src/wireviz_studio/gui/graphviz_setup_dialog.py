"""GraphViz Setup dialog — shown on startup when no dot executable is found."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal, Optional

from PySide6.QtCore import QThread, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from wireviz_studio.graphviz_manager import resolve_dot_version
from wireviz_studio.graphviz_manager.bundled import platform_bundle_dir
from wireviz_studio.graphviz_manager.download import get_latest_version


def _parse_semver_tuple(text: str) -> Optional[tuple[int, int, int]]:
    """Extract ``(major, minor, patch)`` from a version-containing string."""
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", text)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def _bundled_install_dir() -> Path:
    """Return the ``bundled_graphviz/<platform>/`` directory inside the repo/app root."""
    # __file__: src/wireviz_studio/gui/graphviz_setup_dialog.py
    # parents: [gui/, wireviz_studio/, src/, <repo_root>]
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "bundled_graphviz" / platform_bundle_dir()


class _DownloadWorker(QThread):
    """Runs ``download_graphviz()`` on a background thread."""

    progress = Signal(int, int)   # (received_bytes, total_bytes)
    stage_changed = Signal(str)   # stage description
    finished_ok = Signal(dict)    # {zip_url, expected_digest, actual_digest}
    finished_err = Signal(str)    # error message

    def __init__(self, install_dir: Path) -> None:
        super().__init__()
        self._install_dir = install_dir

    def run(self) -> None:
        try:
            from wireviz_studio.graphviz_manager.download import download_graphviz

            result = download_graphviz(
                self._install_dir,
                progress_cb=self._report,
                stage_cb=self._stage_update,
            )
            self.finished_ok.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.finished_err.emit(str(exc))

    def _report(self, received: int, total: int) -> None:
        self.progress.emit(received, total)

    def _stage_update(self, stage: str) -> None:
        self.stage_changed.emit(stage)


class _CheckWorker(QThread):
    """Runs installed/latest version checks off the UI thread."""

    stage_changed = Signal(str)
    finished_ok = Signal(str, str)  # (installed_version, latest_version)
    finished_err = Signal(str)

    def run(self) -> None:
        try:
            self.stage_changed.emit("Checking installed GraphViz…")
            installed = resolve_dot_version() or ""
            self.stage_changed.emit("Checking latest available version…")
            latest = get_latest_version() or ""
            self.finished_ok.emit(installed, latest)
        except Exception as exc:  # noqa: BLE001
            self.finished_err.emit(str(exc))


class GraphVizSetupDialog(QDialog):
    """Modal dialog shown when GraphViz is not found at startup.

    Signals:
        graphviz_configured: Emitted when "Check Again" confirms dot is available.
    """

    graphviz_configured = Signal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        mode: Literal["setup_missing", "check_updates"] = "setup_missing",
    ) -> None:
        super().__init__(parent)
        self._mode: Literal["setup_missing", "check_updates"] = mode
        self.setWindowTitle("GraphViz Required" if mode == "setup_missing" else "GraphViz Updates")
        self.setMinimumWidth(540)
        self._install_dir = _bundled_install_dir()
        self._download_worker: Optional[_DownloadWorker] = None
        self._check_worker: Optional[_CheckWorker] = None
        self._build_ui()
        if self._mode == "check_updates":
            QTimer.singleShot(0, self._on_check_again)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)

        # Header
        if self._mode == "setup_missing":
            header_text = (
                "<b>GraphViz was not found on this system.</b><br><br>"
                "WireViz Studio needs the <code>dot</code> executable to render diagrams. "
                "Use one of the options below to install it."
            )
        else:
            header_text = (
                "<b>Check GraphViz installation and updates.</b><br><br>"
                "This screen shows your installed version and whether a newer release is available."
            )
        self._header = QLabel(header_text)
        self._header.setWordWrap(True)
        root.addWidget(self._header)

        # Auto-download button
        download_text = (
            "Download GraphViz Automatically"
            if self._mode == "setup_missing"
            else "Download or Update GraphViz Automatically"
        )
        self._btn_download = QPushButton(download_text)
        self._btn_download.setFixedHeight(34)
        self._btn_download.clicked.connect(self._on_download_clicked)
        root.addWidget(self._btn_download)

        # Stage label (e.g. "Downloading...")
        self._lbl_stage = QLabel("")
        self._lbl_stage.setStyleSheet("color: #0066cc; font-weight: bold;")
        self._lbl_stage.setFixedHeight(22)
        self._lbl_stage.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        root.addWidget(self._lbl_stage)

        # Progress bar (hidden until download starts)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(10)
        root.addWidget(self._progress_bar)

        # Download status label
        self._lbl_status = QLabel("")
        self._lbl_status.setWordWrap(True)
        self._lbl_status.setFixedHeight(22)
        self._lbl_status.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        root.addWidget(self._lbl_status)

        # Verification info label
        self._lbl_verify = QLabel("")
        self._lbl_verify.setWordWrap(True)
        self._lbl_verify.setFixedHeight(84)
        self._lbl_verify.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        root.addWidget(self._lbl_verify)

        # Collapsible manual section
        self._manual_widget = self._build_manual_section()
        self._manual_widget.setVisible(False)

        self._toggle_btn = QToolButton()
        self._toggle_btn.setText("▶  Manual Installation")
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setChecked(False)
        self._toggle_btn.setStyleSheet("QToolButton { border: none; font-weight: bold; }")
        self._toggle_btn.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._toggle_btn.toggled.connect(self._on_toggle_manual)
        root.addWidget(self._toggle_btn)
        root.addWidget(self._manual_widget)

        root.addStretch()

        # Button bar
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()

        self._btn_check = QPushButton(
            "Check Again" if self._mode == "setup_missing" else "Check for Updates"
        )
        self._btn_check.clicked.connect(self._on_check_again)
        btn_bar.addWidget(self._btn_check)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_bar.addWidget(btn_close)

        root.addLayout(btn_bar)

    def _build_manual_section(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 4, 0, 4)

        bin_path = self._install_dir / "bin"
        instructions = QLabel(
            "Place <code>dot.exe</code> and its companion DLLs into:<br>"
            f"<code>{bin_path}</code><br><br>"
            "Then click <b>Check Again</b> to verify."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        open_btn = QPushButton("Open Installation Folder")
        open_btn.clicked.connect(self._open_install_folder)
        layout.addWidget(open_btn)

        return widget

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    @Slot(bool)
    def _on_toggle_manual(self, checked: bool) -> None:
        arrow = "▼" if checked else "▶"
        self._toggle_btn.setText(f"{arrow}  Manual Installation")
        self._manual_widget.setVisible(checked)

        # Avoid forcing a shrink/relayout cycle that can produce noisy
        # setGeometry warnings on Windows. Only grow when expanded.
        layout = self.layout()
        if layout is not None:
            layout.activate()
        if checked:
            target_height = max(self.height(), self.sizeHint().height())
            self.resize(self.width(), target_height)

    @Slot()
    def _on_download_clicked(self) -> None:
        self._btn_download.setEnabled(False)
        self._btn_check.setEnabled(False)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._lbl_stage.setText("Preparing…")
        self._lbl_status.setText("")
        self._lbl_verify.setText("")

        self._download_worker = _DownloadWorker(self._install_dir)
        self._download_worker.progress.connect(self._on_progress)
        self._download_worker.stage_changed.connect(self._on_stage_changed)
        self._download_worker.finished_ok.connect(self._on_download_ok)
        self._download_worker.finished_err.connect(self._on_download_error)
        self._download_worker.start()

    @Slot(str)
    def _on_stage_changed(self, stage: str) -> None:
        self._lbl_stage.setText(stage)

    @Slot(int, int)
    def _on_progress(self, received: int, total: int) -> None:
        if total > 0:
            self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(int(received * 100 / total))
            size_text = f"{received / 1_048_576:.1f} MB / {total / 1_048_576:.1f} MB"
        else:
            self._progress_bar.setRange(0, 0)  # indeterminate
            size_text = f"{received / 1_048_576:.1f} MB"
        self._lbl_status.setText(f"{size_text}")

    @Slot(dict)
    def _on_download_ok(self, result: dict) -> None:
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(100)
        self._lbl_stage.setText("✓ Download complete")
        self._lbl_status.setText("")

        # Display verification info
        expected = result.get("expected_digest", "")[:16] + "…"
        actual = result.get("actual_digest", "")[:16] + "…"
        verify_text = (
            f"<b>SHA256 Verification:</b> ✓ Verified<br>"
            f"Expected: <code>{expected}</code><br>"
            f"Actual:   <code>{actual}</code>"
        )
        self._lbl_verify.setText(verify_text)

        # Get installed version
        version = resolve_dot_version()
        if version:
            verify_text += f"<br><b>Installed Version:</b> {version}"
            self._lbl_verify.setText(verify_text)

        self._btn_download.setEnabled(True)
        self._btn_check.setEnabled(True)

    @Slot(str)
    def _on_download_error(self, message: str) -> None:
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._lbl_stage.setText("✗ Download failed")
        self._lbl_status.setText(f"Error: {message}")
        self._lbl_verify.setText("")
        self._btn_download.setEnabled(True)
        self._btn_check.setEnabled(True)

    @Slot(str, str)
    def _on_check_done(self, installed_version: str, latest_version: str) -> None:
        self._btn_check.setEnabled(True)
        self._btn_download.setEnabled(True)

        if installed_version:
            installed_tuple = _parse_semver_tuple(installed_version)
            latest_tuple = _parse_semver_tuple(latest_version) if latest_version else None

            if latest_tuple and installed_tuple:
                if latest_tuple > installed_tuple:
                    status_line = f"Update available: {latest_version}"
                elif latest_tuple == installed_tuple:
                    status_line = "You are on the latest version."
                else:
                    status_line = "Installed version is newer than the website listing."
            else:
                status_line = "Could not compare versions online right now."

            details = [
                "<b>Status:</b> " + status_line,
                f"<b>Installed Version:</b> {installed_version}",
            ]
            if latest_version:
                details.append(f"<b>Latest Available:</b> {latest_version}")
            self._lbl_stage.setText("Installation detected")
            self._lbl_verify.setText("<br>".join(details))

            self.graphviz_configured.emit()
            if self._mode == "setup_missing":
                QMessageBox.information(
                    self,
                    "GraphViz Found",
                    f"GraphViz detected successfully.\nInstalled Version: {installed_version}",
                )
                self.accept()
            return

        self._lbl_stage.setText("GraphViz is not installed")
        if latest_version:
            self._lbl_verify.setText(
                "<b>Status:</b> Not installed.<br>"
                f"<b>Latest Available:</b> {latest_version}<br>"
                "Use automatic download or manual installation, then run the check again."
            )
        else:
            self._lbl_verify.setText(
                "<b>Status:</b> Not installed.<br>"
                "Use automatic download or manual installation, then run the check again."
            )

        if self._mode == "setup_missing":
            QMessageBox.warning(
                self,
                "GraphViz Not Found",
                "GraphViz dot still could not be found.\n\n"
                "Make sure dot.exe and its DLLs are placed in the installation folder, "
                "then click Check Again.",
            )

    @Slot(str)
    def _on_check_error(self, message: str) -> None:
        self._btn_check.setEnabled(True)
        self._btn_download.setEnabled(True)
        self._lbl_stage.setText("Version check failed")
        self._lbl_verify.setText(f"<b>Status:</b> {message}")

    @Slot()
    def _on_check_again(self) -> None:
        self._btn_check.setEnabled(False)
        self._btn_download.setEnabled(False)
        self._lbl_stage.setText("Checking GraphViz installation…")
        self._lbl_verify.setText("<b>Status:</b> Working…")

        self._check_worker = _CheckWorker()
        self._check_worker.stage_changed.connect(self._on_stage_changed)
        self._check_worker.finished_ok.connect(self._on_check_done)
        self._check_worker.finished_err.connect(self._on_check_error)
        self._check_worker.start()

    @Slot()
    def _open_install_folder(self) -> None:
        bin_dir = self._install_dir / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(bin_dir)))

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def closeEvent(self, event):  # type: ignore[override]
        if self._download_worker and self._download_worker.isRunning():
            self._download_worker.requestInterruption()
            self._download_worker.wait(3000)
        if self._check_worker and self._check_worker.isRunning():
            self._check_worker.requestInterruption()
            self._check_worker.wait(3000)
        super().closeEvent(event)
