"""YAML syntax highlighter for editor tabs."""

from __future__ import annotations

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QColor, QTextCharFormat, QSyntaxHighlighter, QFont
from PySide6.QtWidgets import QApplication


def _fmt(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
	text_format = QTextCharFormat()
	text_format.setForeground(QColor(color))
	if bold:
		text_format.setFontWeight(QFont.Weight.Bold)
	text_format.setFontItalic(italic)
	return text_format


class YamlHighlighter(QSyntaxHighlighter):
	def __init__(self, parent) -> None:
		super().__init__(parent)

		self.rules = self._build_rules()

	def _build_rules(self):
		palette = QApplication.palette()
		is_dark = palette.base().color().lightness() < 128

		if is_dark:
			key_color = "#9CDCFE"
			section_color = "#DCDCAA"
			bool_color = "#569CD6"
			number_color = "#B5CEA8"
			string_color = "#CE9178"
			comment_color = "#6A9955"
		else:
			key_color = "#0451A5"
			section_color = "#795E26"
			bool_color = "#0000FF"
			number_color = "#098658"
			string_color = "#A31515"
			comment_color = "#008000"

		return [
			(QRegularExpression(r"^\s*[A-Za-z_][\w-]*\s*:(?=\s|$)"), _fmt(key_color, bold=True)),
			(QRegularExpression(r"\b(connectors|cables|connections|metadata|options|tweak)\b"), _fmt(section_color, bold=True)),
			(QRegularExpression(r"\b(true|false|null|yes|no|on|off)\b"), _fmt(bool_color)),
			(QRegularExpression(r"[-+]?\b\d+(?:\.\d+)?\b"), _fmt(number_color)),
			(QRegularExpression(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\""), _fmt(string_color)),
			(QRegularExpression(r"#.*$"), _fmt(comment_color, italic=True)),
		]

	def highlightBlock(self, text: str) -> None:
		for pattern, text_format in self.rules:
			iterator = pattern.globalMatch(text)
			while iterator.hasNext():
				match = iterator.next()
				self.setFormat(match.capturedStart(), match.capturedLength(), text_format)
