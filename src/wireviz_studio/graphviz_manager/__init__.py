"""GraphViz binary resolution for WireViz Studio.

Resolution order follows Phase 2 plan:
1) bundled binary
2) system-installed binary
3) error
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from wireviz_studio.graphviz_manager.bundled import configure_bundled_dot
from wireviz_studio.graphviz_manager.detect import configure_system_dot, dot_version


def resolve_dot_binary(app_root: Optional[Path] = None) -> Optional[Path]:
    """Resolve and configure GraphViz dot executable using bundled/system fallback.

    Returns the resolved :class:`~pathlib.Path` to the ``dot`` executable, or
    ``None`` when no executable can be found.  Callers that require ``dot`` (e.g.
    the render worker) must handle the ``None`` case themselves.
    """
    bundled_dot = configure_bundled_dot(app_root=app_root)
    if bundled_dot:
        return bundled_dot

    system_dot = configure_system_dot()
    if system_dot:
        return system_dot

    return None


def resolve_dot_version(app_root: Optional[Path] = None) -> Optional[str]:
    """Resolve dot and return version information when available."""
    dot_path = resolve_dot_binary(app_root=app_root)
    if dot_path is None:
        return None
    return dot_version(dot_path)
