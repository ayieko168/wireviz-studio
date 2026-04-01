"""Background render worker using QThread."""

from __future__ import annotations

from pathlib import Path

import yaml
from PySide6.QtCore import QThread, Signal

from wireviz_studio.core.exceptions import WireVizStudioError
from wireviz_studio.core.parser import parse_yaml


class RenderWorker(QThread):
	render_complete = Signal(str, list)
	render_error = Signal(str)

	def __init__(self, yaml_text: str, base_path: Path | None = None) -> None:
		super().__init__()
		self._yaml_text = yaml_text
		self._base_path = base_path

	def run(self) -> None:
		try:
			if self.isInterruptionRequested():
				return

			# Prefer C-accelerated loader when available for faster large document parsing.
			try:
				yaml_data = yaml.load(self._yaml_text, Loader=yaml.CSafeLoader)
			except AttributeError:
				yaml_data = yaml.safe_load(self._yaml_text)

			if not isinstance(yaml_data, dict):
				raise WireVizStudioError("Top-level YAML document must be a mapping.")

			if self.isInterruptionRequested():
				return

			image_paths = [self._base_path] if self._base_path else []
			harness = parse_yaml(yaml_data, image_paths=image_paths)
			svg_data = harness.render_svg()

			if self.isInterruptionRequested():
				return

			bom_rows = harness.bom()
			self.render_complete.emit(svg_data, bom_rows)
		except Exception as exc:
			self.render_error.emit(str(exc))
