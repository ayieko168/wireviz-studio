"""QSettings wrapper for persisted UI preferences."""

from __future__ import annotations

from typing import List

from PySide6.QtCore import QByteArray, QSettings


class AppSettings:
	def __init__(self) -> None:
		self._settings = QSettings()

	@property
	def theme(self) -> str:
		return str(self._settings.value("ui/theme", "light"))

	@theme.setter
	def theme(self, value: str) -> None:
		self._settings.setValue("ui/theme", value)

	@property
	def recent_files(self) -> List[str]:
		values = self._settings.value("files/recent", [])
		if isinstance(values, str):
			return [values]
		return [str(value) for value in values]

	@recent_files.setter
	def recent_files(self, value: List[str]) -> None:
		self._settings.setValue("files/recent", value[:10])

	@property
	def window_geometry(self) -> QByteArray | None:
		value = self._settings.value("ui/window_geometry")
		return value if isinstance(value, QByteArray) else None

	@window_geometry.setter
	def window_geometry(self, value: QByteArray) -> None:
		self._settings.setValue("ui/window_geometry", value)

	@property
	def window_state(self) -> QByteArray | None:
		value = self._settings.value("ui/window_state")
		return value if isinstance(value, QByteArray) else None

	@window_state.setter
	def window_state(self, value: QByteArray) -> None:
		self._settings.setValue("ui/window_state", value)

	@property
	def splitter_sizes(self) -> List[int] | None:
		raw = self._settings.value("ui/splitter_sizes")
		if not raw:
			return None
		return [int(v) for v in raw]

	@splitter_sizes.setter
	def splitter_sizes(self, value: List[int]) -> None:
		self._settings.setValue("ui/splitter_sizes", value)

	@property
	def last_export_dir(self) -> str:
		return str(self._settings.value("export/last_dir", ""))

	@last_export_dir.setter
	def last_export_dir(self, value: str) -> None:
		self._settings.setValue("export/last_dir", value)

	@property
	def last_export_format(self) -> str:
		return str(self._settings.value("export/last_format", "SVG"))

	@last_export_format.setter
	def last_export_format(self, value: str) -> None:
		self._settings.setValue("export/last_format", value)

	def sync(self) -> None:
		self._settings.sync()
