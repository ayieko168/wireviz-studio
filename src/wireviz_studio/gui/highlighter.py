"""YAML syntax highlighter for editor tabs."""

from __future__ import annotations

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QColor, QTextCharFormat, QSyntaxHighlighter, QFont


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

		self.rules = [
            # Keys: Match lines that start with optional whitespace, followed by a valid YAML key (alphanumeric, underscores, or hyphens), and a colon. The lookahead ensures the colon is followed by whitespace or end of line.
			(QRegularExpression(r"^\s*[A-Za-z_][\w-]*\s*:(?=\s|$)"), _fmt("#2f6f9f", bold=True)),
   
            # Values: Match common YAML values like booleans, nulls, numbers, and strings. The patterns cover unquoted values (true, false, null, yes, no, on, off), numeric values (integers and floats), quoted strings (single or double), and comments (starting with #).
			(QRegularExpression(r"\b(connectors|cables|connections|metadata|options|tweak)\b"), _fmt("#8a4f00", bold=True)),
   
            # Booleans and nulls: Match unquoted YAML values that represent booleans (true, false) and null (null), as well as common yes/no and on/off values. The word boundaries ensure we only match these as standalone values.
			(QRegularExpression(r"\b(true|false|null|yes|no|on|off)\b"), _fmt("#7b2cbf")),
   
            # Numbers: Match integers and floating-point numbers, including optional signs. The pattern looks for word boundaries to ensure we match whole numbers and not parts of words.
			(QRegularExpression(r"[-+]?\b\d+(?:\.\d+)?\b"), _fmt("#0b7a75")),
   
            # Strings: Match both single-quoted and double-quoted strings, allowing for escaped characters within the quotes. The patterns ensure we capture the entire string, including any escaped quotes.
			(QRegularExpression(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\""), _fmt("#a3333d")),
   
            # Comments: Match comments that start with a # and continue to the end of the line. This pattern captures the entire comment, allowing for any characters after the #.
			(QRegularExpression(r"#.*$"), _fmt("#6a737d", italic=True)),
		]

	def highlightBlock(self, text: str) -> None:
		for pattern, text_format in self.rules:
			iterator = pattern.globalMatch(text)
			while iterator.hasNext():
				match = iterator.next()
				self.setFormat(match.capturedStart(), match.capturedLength(), text_format)
