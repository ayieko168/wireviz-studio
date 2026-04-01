"""Main window implementation for WireViz Studio."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QSizePolicy,
    QWidget,
)

from wireviz_studio import APP_NAME
from wireviz_studio.graphviz_manager import resolve_dot_version
from wireviz_studio.gui.editor import EditorTabs
from wireviz_studio.gui.export import ExportDialog
from wireviz_studio.gui.preview import PreviewPanel
from wireviz_studio.gui.graphviz_setup_dialog import GraphVizSetupDialog
from wireviz_studio.gui.settings import AppSettings
from wireviz_studio.gui.theme_loader import apply_theme
from wireviz_studio.gui.worker import RenderWorker


class MainWindow(QMainWindow):
    def __init__(self, settings: AppSettings, app: QApplication) -> None:
        super().__init__()
        self._settings = settings
        self._app = app
        self._render_worker: RenderWorker | None = None

        self.setWindowTitle(APP_NAME)
        self.resize(1360, 820)

        self.editor_tabs = EditorTabs(self)
        self.preview_panel = PreviewPanel(self)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(self.editor_tabs)
        splitter.addWidget(self.preview_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        self._splitter = splitter
        self.setCentralWidget(splitter)

        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self._build_statusbar()

        self.editor_tabs.new_tab()
        self.editor_tabs.currentFilePathChanged.connect(self._on_current_file_changed)
        self.editor_tabs.currentContentChanged.connect(self._on_content_changed)

        self._restore_window_state()
        graphviz_found = self._update_graphviz_status()
        self._refresh_recent_files_menu()

        if not graphviz_found:
            QTimer.singleShot(0, self._show_graphviz_setup_dialog)

    def _build_actions(self) -> None:
        self.act_new = QAction("New", self)
        self.act_new.setShortcut(QKeySequence.StandardKey.New)
        self.act_new.triggered.connect(lambda: self.editor_tabs.new_tab())

        self.act_open = QAction("Open", self)
        self.act_open.setShortcut(QKeySequence.StandardKey.Open)
        self.act_open.triggered.connect(self._open_file_dialog)

        self.act_save = QAction("Save", self)
        self.act_save.setShortcut(QKeySequence.StandardKey.Save)
        self.act_save.triggered.connect(self._save_current)

        self.act_save_as = QAction("Save As", self)
        self.act_save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.act_save_as.triggered.connect(self._save_current_as)

        self.act_close_tab = QAction("Close Tab", self)
        self.act_close_tab.setShortcut(QKeySequence("Ctrl+W"))
        self.act_close_tab.triggered.connect(
            lambda: self.editor_tabs.close_tab(self.editor_tabs.currentIndex())
        )

        self.act_render = QAction("Render", self)
        self.act_render.setShortcut(QKeySequence("F5"))
        self.act_render.triggered.connect(self._render_current)

        self.act_export = QAction("Export", self)
        self.act_export.triggered.connect(self._show_export_dialog)

        self.act_fit = QAction("Fit Diagram", self)
        self.act_fit.triggered.connect(self.preview_panel.diagram_view.fit_diagram)

        self.act_theme = QAction("Dark Theme", self)
        self.act_theme.setCheckable(True)
        self.act_theme.setChecked(self._settings.theme == "dark")
        self.act_theme.triggered.connect(self._toggle_theme)

        self.act_check_graphviz = QAction("Check for GraphViz Updates", self)
        self.act_check_graphviz.triggered.connect(self._show_graphviz_check_dialog)

        self.act_about = QAction("About", self)
        self.act_about.triggered.connect(self._show_about)

        self.recent_file_actions = []

    def _build_menus(self) -> None:
        menu_file = self.menuBar().addMenu("File")
        menu_file.addAction(self.act_new)
        menu_file.addAction(self.act_open)
        menu_file.addAction(self.act_save)
        menu_file.addAction(self.act_save_as)

        self.menu_recent = menu_file.addMenu("Recent Files")
        menu_file.addSeparator()
        menu_file.addAction(self.act_close_tab)
        menu_file.addSeparator()
        menu_file.addAction("Exit", self.close)

        menu_view = self.menuBar().addMenu("View")
        menu_view.addAction(self.act_theme)
        menu_view.addAction(self.act_fit)

        menu_tools = self.menuBar().addMenu("Tools")
        menu_tools.addAction(self.act_render)
        menu_tools.addAction(self.act_export)
        menu_tools.addSeparator()
        menu_tools.addAction(self.act_check_graphviz)

        menu_help = self.menuBar().addMenu("Help")
        menu_help.addAction(self.act_about)

    def _build_toolbar(self) -> None:
        toolbar = self.addToolBar("Main")
        toolbar.setObjectName("main_toolbar")
        toolbar.setMovable(False)
        toolbar.addAction(self.act_new)
        toolbar.addAction(self.act_open)
        toolbar.addAction(self.act_save)

        spacer = QWidget(self)
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        toolbar.addSeparator()
        toolbar.addAction(self.act_render)
        toolbar.addAction(self.act_export)

    def _build_statusbar(self) -> None:
        status = QStatusBar(self)
        self.setStatusBar(status)
        self._status_render = "Ready"
        self._status_graphviz = "GraphViz: unknown"
        self._status_file = ""
        self._refresh_statusbar()

    def _refresh_statusbar(self) -> None:
        self.statusBar().showMessage(
            f"{self._status_render} | {self._status_graphviz} | {self._status_file}"
        )

    def _set_render_status(self, text: str) -> None:
        self._status_render = text
        self._refresh_statusbar()

    @Slot(str)
    def _on_current_file_changed(self, file_path: str) -> None:
        self._status_file = file_path
        self._refresh_statusbar()

    @Slot()
    def _on_content_changed(self) -> None:
        editor = self.editor_tabs.current_editor()
        if editor and editor.document().isModified():
            self._set_render_status("Modified")

    def _open_file_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open YAML", filter="YAML (*.yml *.yaml)")
        if not path:
            return
        file_path = Path(path)
        self.editor_tabs.open_file(file_path)
        self._push_recent_file(file_path)

    def _save_current(self) -> None:
        editor = self.editor_tabs.current_editor()
        if not editor:
            return
        if editor.file_path is None:
            self._save_current_as()
            return
        saved = self.editor_tabs.save_current()
        if saved:
            self._push_recent_file(saved)
            self._set_render_status(f"Saved: {saved.name}")

    def _save_current_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save YAML", filter="YAML (*.yml *.yaml)")
        if not path:
            return
        saved = self.editor_tabs.save_current(Path(path))
        if saved:
            self._push_recent_file(saved)
            self._set_render_status(f"Saved: {saved.name}")

    def _render_current(self) -> None:
        editor = self.editor_tabs.current_editor()
        if not editor:
            return

        if self._render_worker and self._render_worker.isRunning():
            self._set_render_status("Render already in progress")
            return

        base_path = editor.file_path.parent if editor.file_path else None
        self._render_worker = RenderWorker(editor.toPlainText(), base_path)
        self._render_worker.render_complete.connect(self._on_render_complete)
        self._render_worker.render_error.connect(self._on_render_error)
        self._render_worker.finished.connect(self._on_render_finished)
        self._set_render_status("Rendering...")
        self.act_render.setEnabled(False)
        self._render_worker.start()

    @Slot(str, list)
    def _on_render_complete(self, svg_data: str, bom_rows: list) -> None:
        self.preview_panel.set_svg(svg_data)
        self.preview_panel.set_bom(bom_rows)
        self._set_render_status("Rendered successfully")

    @Slot(str)
    def _on_render_error(self, message: str) -> None:
        self._set_render_status(f"Render failed: {message}")
        QMessageBox.critical(self, "Render Error", message)

    @Slot()
    def _on_render_finished(self) -> None:
        self.act_render.setEnabled(True)
        if self._render_worker is not None:
            self._render_worker.deleteLater()
            self._render_worker = None

    def _show_export_dialog(self) -> None:
        dialog = ExportDialog(
            self,
            default_path=self._settings.last_export_path or self._settings.last_export_dir,
            default_format=self._settings.last_export_format,
            default_pdf_mode=self._settings.last_export_pdf_mode,
        )
        if self._settings.export_dialog_size:
            dialog.resize(self._settings.export_dialog_size)

        if dialog.exec() != dialog.DialogCode.Accepted:
            self._settings.export_dialog_size = dialog.size()
            return

        selection = dialog.selection()
        self._settings.last_export_format = selection.format_name
        self._settings.last_export_pdf_mode = selection.pdf_mode
        self._settings.last_export_path = selection.output_path
        self._settings.export_dialog_size = dialog.size()
        if selection.output_path:
            self._settings.last_export_dir = str(Path(selection.output_path).parent)
        QMessageBox.information(
            self,
            "Export",
            "Export processing will be implemented in the export layer in a subsequent phase.",
        )

    def _toggle_theme(self, checked: bool) -> None:
        self._settings.theme = "dark" if checked else "light"
        apply_theme(self._app, self._settings)

    def _show_about(self) -> None:
        QMessageBox.information(
            self,
            "About",
            f"{APP_NAME}\n\nPhase 3 shell is active: editor, render preview, BOM tab, and settings persistence.",
        )

    def _push_recent_file(self, file_path: Path) -> None:
        items = [str(file_path)] + [item for item in self._settings.recent_files if item != str(file_path)]
        self._settings.recent_files = items[:10]
        self._refresh_recent_files_menu()

    def _refresh_recent_files_menu(self) -> None:
        self.menu_recent.clear()
        recent = self._settings.recent_files
        if not recent:
            self.menu_recent.addAction("(empty)").setEnabled(False)
            return
        for file_name in recent:
            action = self.menu_recent.addAction(file_name)
            action.triggered.connect(lambda _checked=False, p=file_name: self._open_recent(Path(p)))

    def _open_recent(self, file_path: Path) -> None:
        if not file_path.exists():
            QMessageBox.warning(self, "Missing File", f"File no longer exists:\n{file_path}")
            return
        self.editor_tabs.open_file(file_path)
        self._push_recent_file(file_path)

    def _update_graphviz_status(self) -> bool:
        """Refresh GraphViz status bar entry and return True when dot is found."""
        version = resolve_dot_version()
        self._status_graphviz = f"GraphViz: {version}" if version else "GraphViz: not found"
        self._refresh_statusbar()
        return version is not None

    def _show_graphviz_setup_dialog(self) -> None:
        dialog = GraphVizSetupDialog(self, mode="setup_missing")
        dialog.graphviz_configured.connect(self._update_graphviz_status)
        dialog.exec()

    def _show_graphviz_check_dialog(self) -> None:
        """Show the GraphViz setup dialog for manual checking/updating."""
        dialog = GraphVizSetupDialog(self, mode="check_updates")
        dialog.graphviz_configured.connect(self._update_graphviz_status)
        dialog.exec()

    def _restore_window_state(self) -> None:
        if self._settings.window_geometry:
            self.restoreGeometry(self._settings.window_geometry)
        if self._settings.window_state:
            self.restoreState(self._settings.window_state)
        if self._settings.splitter_sizes:
            self._splitter.setSizes(self._settings.splitter_sizes)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._render_worker and self._render_worker.isRunning():
            self._render_worker.requestInterruption()
            self._render_worker.wait(2000)
        self._settings.window_geometry = self.saveGeometry()
        self._settings.window_state = self.saveState()
        self._settings.splitter_sizes = self._splitter.sizes()
        self._settings.sync()
        super().closeEvent(event)
