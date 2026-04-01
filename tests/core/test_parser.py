import shutil

import yaml
import pytest

from wireviz_studio.core.exceptions import GraphVizNotFoundError
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

    if shutil.which("dot") is None:
        with pytest.raises(GraphVizNotFoundError):
            harness.render_svg()
        return

    svg = harness.render_svg()

    assert "<svg" in svg
