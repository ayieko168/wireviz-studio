"""Multi-tab YAML editor widgets with line numbers and dirty state."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QTextFormat
from PySide6.QtWidgets import QPlainTextEdit, QTabBar, QTabWidget, QTextEdit, QToolButton, QWidget

from wireviz_studio.gui.highlighter import YamlHighlighter


class _LineNumberArea(QWidget):
	def __init__(self, editor: "CodeEditor") -> None:
		super().__init__(editor)
		self._editor = editor

	def sizeHint(self) -> QSize:
		return QSize(self._editor.line_number_area_width(), 0)

	def paintEvent(self, event) -> None:
		self._editor.paint_line_numbers(event)


class CodeEditor(QPlainTextEdit):
	modifiedChanged = Signal(bool)

	def __init__(self, parent=None) -> None:
		super().__init__(parent)
		self.file_path: Path | None = None
		self._line_number_area = _LineNumberArea(self)

		self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
		self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
		self.setFont(QFont("Consolas", 10))
		YamlHighlighter(self.document())

		self.blockCountChanged.connect(self._update_line_number_area_width)
		self.updateRequest.connect(self._update_line_number_area)
		self.cursorPositionChanged.connect(self._highlight_current_line)
		self.document().modificationChanged.connect(self.modifiedChanged.emit)

		self._update_line_number_area_width(0)
		self._highlight_current_line()

	def line_number_area_width(self) -> int:
		digits = len(str(max(1, self.blockCount())))
		return 12 + self.fontMetrics().horizontalAdvance("9") * digits

	def _update_line_number_area_width(self, _new_block_count: int) -> None:
		self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

	def _update_line_number_area(self, rect: QRect, dy: int) -> None:
		if dy:
			self._line_number_area.scroll(0, dy)
		else:
			self._line_number_area.update(
				0, rect.y(), self._line_number_area.width(), rect.height()
			)

	def resizeEvent(self, event) -> None:
		super().resizeEvent(event)
		cr = self.contentsRect()
		self._line_number_area.setGeometry(
			QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
		)

	def paint_line_numbers(self, event) -> None:
		painter = QPainter(self._line_number_area)
		palette = self.palette()
		base = palette.base().color()
		if base.lightness() < 128:
			gutter_bg = QColor("#252526")
			number_fg = QColor("#858585")
		else:
			gutter_bg = QColor("#f3f3f3")
			number_fg = QColor("#8a8a8a")

		painter.fillRect(event.rect(), gutter_bg)

		block = self.firstVisibleBlock()
		block_number = block.blockNumber()
		top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
		bottom = top + self.blockBoundingRect(block).height()

		while block.isValid() and top <= event.rect().bottom():
			if block.isVisible() and bottom >= event.rect().top():
				number_text = str(block_number + 1)
				painter.setPen(number_fg)
				painter.drawText(
					0,
					int(top),
					self._line_number_area.width() - 6,
					self.fontMetrics().height(),
					Qt.AlignmentFlag.AlignRight,
					number_text,
				)

			block = block.next()
			top = bottom
			bottom = top + self.blockBoundingRect(block).height()
			block_number += 1

	def _highlight_current_line(self) -> None:
		if self.isReadOnly():
			self.setExtraSelections([])
			return

		selection = QTextEdit.ExtraSelection()
		base = self.palette().base().color()
		if base.lightness() < 128:
			line_bg = QColor("#2a2d2e")
		else:
			line_bg = QColor("#f5f9ff")
		selection.format.setBackground(line_bg)
		selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
		selection.cursor = self.textCursor()
		selection.cursor.clearSelection()
		self.setExtraSelections([selection])


class EditorTabs(QTabWidget):
	currentFilePathChanged = Signal(str)
	currentContentChanged = Signal()

	def __init__(self, parent=None) -> None:
		super().__init__(parent)
		self.setObjectName("editor_tabs")
		self.setTabsClosable(True)
		self.setMovable(True)
		self.tabCloseRequested.connect(self.close_tab)
		self.currentChanged.connect(self._on_current_changed)

	def _make_close_button(self) -> QToolButton:
		button = QToolButton(self)
		button.setObjectName("editor_tab_close")
		button.setText("×")
		button.setToolTip("Close tab")
		button.setAutoRaise(True)
		button.setCursor(Qt.CursorShape.PointingHandCursor)
		button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
		button.setFixedSize(18, 18)
		button.clicked.connect(lambda _checked=False, b=button: self._close_by_button(b))
		return button

	def _install_close_button(self, index: int) -> None:
		if index < 0:
			return
		button = self._make_close_button()
		self.tabBar().setTabButton(index, QTabBar.ButtonPosition.RightSide, button)

	def _close_by_button(self, button: QToolButton) -> None:
		for index in range(self.count()):
			if self.tabBar().tabButton(index, QTabBar.ButtonPosition.RightSide) is button:
				self.close_tab(index)
				return

	def new_tab(self, text: str = "", file_path: Path | None = None) -> int:
		editor = CodeEditor(self)
		editor.setPlainText(text)
		editor.document().setModified(False)
		editor.file_path = file_path

		editor.modifiedChanged.connect(lambda _: self._refresh_current_tab_title())
		editor.textChanged.connect(self.currentContentChanged.emit)

		title = file_path.name if file_path else "untitled.yml"
		index = self.addTab(editor, title)
		self._install_close_button(index)
		self.setCurrentIndex(index)
		self._refresh_tab_title(index)
		self._on_current_changed(index)
		return index

	def current_editor(self) -> CodeEditor | None:
		widget = self.currentWidget()
		return widget if isinstance(widget, CodeEditor) else None

	def _refresh_tab_title(self, index: int) -> None:
		editor = self.widget(index)
		if not isinstance(editor, CodeEditor):
			return
		title = editor.file_path.name if editor.file_path else "untitled.yml"
		if editor.document().isModified():
			title += "*"
		self.setTabText(index, title)

	def _refresh_current_tab_title(self) -> None:
		self._refresh_tab_title(self.currentIndex())

	def _on_current_changed(self, index: int) -> None:
		editor = self.widget(index)
		if not isinstance(editor, CodeEditor):
			self.currentFilePathChanged.emit("")
			return
		self.currentFilePathChanged.emit(str(editor.file_path) if editor.file_path else "")

	def open_file(self, file_path: Path) -> None:
		for index in range(self.count()):
			editor = self.widget(index)
			if isinstance(editor, CodeEditor) and editor.file_path == file_path:
				self.setCurrentIndex(index)
				return
		self.new_tab(text=file_path.read_text(encoding="utf-8"), file_path=file_path)

	def save_current(self, target_path: Path | None = None) -> Path | None:
		editor = self.current_editor()
		if editor is None:
			return None
		path = target_path or editor.file_path
		if path is None:
			return None
		path.write_text(editor.toPlainText(), encoding="utf-8")
		editor.file_path = path
		editor.document().setModified(False)
		self._refresh_current_tab_title()
		self.currentFilePathChanged.emit(str(path))
		return path

	def close_tab(self, index: int) -> None:
		self.removeTab(index)
		if self.count() == 0:
			self.new_tab()
