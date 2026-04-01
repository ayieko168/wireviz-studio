import pytest

from wireviz_studio.core.exceptions import GraphVizNotFoundError, RenderError
from wireviz_studio.core.harness import Harness
from wireviz_studio.core.models import Metadata, Options, Tweak


def _make_harness() -> Harness:
    return Harness(metadata=Metadata(), options=Options(), tweak=Tweak())


def test_bom_is_cached(monkeypatch):
    harness = _make_harness()
    calls = {"count": 0}

    def fake_generate_bom(_):
        calls["count"] += 1
        return [{"id": 1, "description": "stub"}]

    monkeypatch.setattr("wireviz_studio.core.harness.generate_bom", fake_generate_bom)

    first = harness.bom()
    second = harness.bom()

    assert first == second
    assert calls["count"] == 1


def test_render_svg_maps_missing_dot_to_graphviz_error(monkeypatch):
    harness = _make_harness()

    def fail_resolve():
        raise FileNotFoundError("dot not found")

    monkeypatch.setattr("wireviz_studio.core.harness.resolve_dot_binary", fail_resolve)

    with pytest.raises(GraphVizNotFoundError):
        harness.render_svg()


def test_render_svg_maps_unexpected_failures_to_render_error(monkeypatch):
    harness = _make_harness()

    monkeypatch.setattr("wireviz_studio.core.harness.resolve_dot_binary", lambda: None)

    def broken_svg(_self):
        raise RuntimeError("render pipeline failed")

    monkeypatch.setattr(Harness, "svg", property(broken_svg))

    with pytest.raises(RenderError):
        harness.render_svg()
