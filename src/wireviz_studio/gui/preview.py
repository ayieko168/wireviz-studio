"""Diagram/BOM preview widgets."""

from __future__ import annotations

from typing import Iterable

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from PySide6.QtWidgets import (
	QGraphicsScene,
	QGraphicsView,
	QHeaderView,
	QPushButton,
	QTableWidget,
	QTableWidgetItem,
	QTabWidget,
	QVBoxLayout,
	QWidget,
)


class DiagramView(QGraphicsView):
	def __init__(self, parent=None) -> None:
		super().__init__(parent)
		self.setScene(QGraphicsScene(self))
		self.setCacheMode(QGraphicsView.CacheModeFlag.CacheBackground)
		self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
		self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontSavePainterState, True)
		self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
		self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
		self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
		self._zoom = 1.0
		self._svg_renderer: QSvgRenderer | None = None

	def wheelEvent(self, event) -> None:
		factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
		self.scale(factor, factor)
		self._zoom *= factor

	def fit_diagram(self) -> None:
		if self.scene() and self.scene().items():
			self.fitInView(self.scene().itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
			self._zoom = 1.0

	def set_svg(self, svg_text: str) -> None:
		scene = self.scene()
		scene.clear()
		renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")), self)
		self._svg_renderer = renderer
		svg_item = QGraphicsSvgItem()
		svg_item.setSharedRenderer(renderer)
		scene.addItem(svg_item)
		self.fit_diagram()


class PreviewPanel(QWidget):
	def __init__(self, parent=None) -> None:
		super().__init__(parent)

		self.tabs = QTabWidget(self)

		self.diagram_view = DiagramView(self)
		self.fit_button = QPushButton("Fit", self)
		self.fit_button.clicked.connect(self.diagram_view.fit_diagram)
		diagram_container = QWidget(self)
		diagram_layout = QVBoxLayout(diagram_container)
		diagram_layout.setContentsMargins(0, 0, 0, 0)
		diagram_layout.addWidget(self.diagram_view)
		diagram_layout.addWidget(self.fit_button, alignment=Qt.AlignmentFlag.AlignRight)

		self.bom_table = QTableWidget(self)
		self.bom_table.setSortingEnabled(True)
		self.bom_table.setAlternatingRowColors(True)
		self.bom_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

		self.tabs.addTab(diagram_container, "Diagram")
		self.tabs.addTab(self.bom_table, "BOM")

		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.addWidget(self.tabs)

	def set_svg(self, svg_text: str) -> None:
		self.diagram_view.set_svg(svg_text)

	def set_bom(self, rows: Iterable[dict]) -> None:
		rows = list(rows)
		if not rows:
			self.bom_table.clear()
			self.bom_table.setRowCount(0)
			self.bom_table.setColumnCount(0)
			return

		self.bom_table.setSortingEnabled(False)
		columns = list(rows[0].keys())
		self.bom_table.setColumnCount(len(columns))
		self.bom_table.setHorizontalHeaderLabels(columns)
		self.bom_table.setRowCount(len(rows))

		for row_index, row in enumerate(rows):
			for column_index, column_name in enumerate(columns):
				value = row.get(column_name, "")
				if isinstance(value, list):
					value = ", ".join(str(item) for item in value)
				item = QTableWidgetItem(str(value))
				self.bom_table.setItem(row_index, column_index, item)
		self.bom_table.setSortingEnabled(True)
