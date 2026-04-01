"""Export dialog UI for selecting target format/options."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
	QComboBox,
	QDialog,
	QDialogButtonBox,
	QFileDialog,
	QFormLayout,
	QGroupBox,
	QHBoxLayout,
	QLineEdit,
	QPushButton,
	QRadioButton,
	QVBoxLayout,
)


@dataclass
class ExportSelection:
	format_name: str
	output_path: str
	pdf_mode: str


class ExportDialog(QDialog):
	def __init__(self, parent=None, default_path: str = "", default_format: str = "SVG") -> None:
		super().__init__(parent)
		self.setWindowTitle("Export")

		self.format_combo = QComboBox(self)
		self.format_combo.addItems(["PNG", "SVG", "PDF", "CSV"])
		self.format_combo.setCurrentText(default_format.upper())

		self.path_edit = QLineEdit(default_path, self)
		browse_button = QPushButton("Browse", self)
		browse_button.clicked.connect(self._browse)

		path_row = QHBoxLayout()
		path_row.addWidget(self.path_edit)
		path_row.addWidget(browse_button)

		self.pdf_group = QGroupBox("PDF options", self)
		pdf_layout = QVBoxLayout(self.pdf_group)
		self.pdf_diagram = QRadioButton("Diagram only", self.pdf_group)
		self.pdf_bom = QRadioButton("BOM only", self.pdf_group)
		self.pdf_both = QRadioButton("Diagram + BOM", self.pdf_group)
		self.pdf_diagram.setChecked(True)
		pdf_layout.addWidget(self.pdf_diagram)
		pdf_layout.addWidget(self.pdf_bom)
		pdf_layout.addWidget(self.pdf_both)

		form = QFormLayout()
		form.addRow("Format", self.format_combo)
		form.addRow("Output", path_row)

		buttons = QDialogButtonBox(
			QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
			parent=self,
		)
		buttons.accepted.connect(self.accept)
		buttons.rejected.connect(self.reject)

		root = QVBoxLayout(self)
		root.addLayout(form)
		root.addWidget(self.pdf_group)
		root.addWidget(buttons)

		self.format_combo.currentTextChanged.connect(self._update_pdf_visibility)
		self._update_pdf_visibility(self.format_combo.currentText())

	def _browse(self) -> None:
		path, _ = QFileDialog.getSaveFileName(self, "Export output")
		if path:
			self.path_edit.setText(path)

	def _update_pdf_visibility(self, format_name: str) -> None:
		self.pdf_group.setVisible(format_name.upper() == "PDF")

	def selection(self) -> ExportSelection:
		if self.pdf_bom.isChecked():
			pdf_mode = "bom"
		elif self.pdf_both.isChecked():
			pdf_mode = "both"
		else:
			pdf_mode = "diagram"

		return ExportSelection(
			format_name=self.format_combo.currentText().upper(),
			output_path=self.path_edit.text().strip(),
			pdf_mode=pdf_mode,
		)
