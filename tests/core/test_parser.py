import yaml
import pytest
from pathlib import Path

from wireviz_studio.core.exceptions import GraphVizNotFoundError, ValidationError, YAMLParseError
from wireviz_studio.graphviz_manager import resolve_dot_binary
from wireviz_studio.core.harness import Harness
from wireviz_studio.core.parser import parse_yaml


def test_parse_yaml_returns_harness_instance():
    data = yaml.safe_load(
        """
connectors:
  X1:
    pincount: 2
  X2:
    pincount: 2
cables:
  W1:
    wirecount: 2
connections:
  - [X1, W1, X2]
"""
    )

    result = parse_yaml(data)

    assert isinstance(result, Harness)


def test_parse_yaml_produces_svg():
    data = yaml.safe_load(
        """
connectors:
  X1:
    pincount: 1
  X2:
    pincount: 1
cables:
  W1:
    wirecount: 1
connections:
  - [X1, W1, X2]
"""
    )

    harness = parse_yaml(data)

    try:
      resolve_dot_binary()
    except FileNotFoundError:
      with pytest.raises(GraphVizNotFoundError):
        harness.render_svg()
      return

    svg = harness.render_svg()
    assert "<svg" in svg


def test_parse_yaml_rejects_non_dict_payload():
    with pytest.raises(YAMLParseError):
        parse_yaml(["not", "a", "dict"])


def test_parse_yaml_rejects_mismatched_connection_set_lengths():
    data = yaml.safe_load(
        """
connectors:
  X1:
    pincount: 2
  X2:
    pincount: 2
cables:
  W1:
    wirecount: 2
connections:
  - [X1, [1, 2], W1, [1], X2, [1, 2]]
"""
    )

    with pytest.raises(ValidationError, match="same number of connections"):
        parse_yaml(data)


def test_parse_yaml_rejects_invalid_arrow_position_sequence():
    data = yaml.safe_load(
        """
connectors:
  X1:
    pincount: 1
  X2:
    pincount: 1
connections:
  - ["<-", X1, X2]
"""
    )

    with pytest.raises(ValidationError, match="Expected cable/arrow"):
        parse_yaml(data)


def test_parse_yaml_supports_fixture_driven_example():
    fixture_path = Path(__file__).resolve().parents[2] / "examples" / "ex01.yml"
    data = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))

    harness = parse_yaml(data)

    assert isinstance(harness, Harness)
    assert harness.connectors
    assert harness.cables
