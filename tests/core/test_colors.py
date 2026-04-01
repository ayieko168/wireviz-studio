import pytest

from wireviz_studio.core.colors import get_color_hex, translate_color


def test_get_color_hex_for_two_colors_adds_third_segment_for_stripe_style():
    colors = get_color_hex("RDBK")

    assert len(colors) == 3
    assert colors[0] == "#ff0000"
    assert colors[1] == "#000000"
    assert colors[2] == "#ff0000"


def test_get_color_hex_pad_repeats_single_color():
    colors = get_color_hex("RD", pad=True)

    assert colors == ["#ff0000", "#ff0000", "#ff0000"]


def test_translate_color_supports_modes_and_capitalization():
    assert translate_color("RDBK", "SHORT") == "RDBK"
    assert translate_color("RDBK", "short") == "rdbk"
    assert translate_color("RDBK", "hex").startswith("#")
    assert "red" in translate_color("RD", "full")


@pytest.mark.parametrize("mode", ["HeX", "ShOrT"])
def test_translate_color_rejects_mixed_case_mode(mode):
    with pytest.raises(Exception, match="capitalization"):
        translate_color("RD", mode)
