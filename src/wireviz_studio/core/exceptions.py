"""Core exception hierarchy for WireViz Studio."""


class WireVizStudioError(Exception):
    """Base class for all WireViz Studio domain errors."""


class YAMLParseError(WireVizStudioError):
    """Raised when YAML input cannot be parsed or normalized."""


class ValidationError(WireVizStudioError):
    """Raised when parsed data violates structural rules."""


class RenderError(WireVizStudioError):
    """Raised when graph rendering fails."""


class GraphVizNotFoundError(RenderError):
    """Raised when the GraphViz dot executable is unavailable."""
