from wireviz_studio.core.bom import (
    bom_list,
    generate_bom,
    make_list,
    make_str,
    pn_info_string,
)
from wireviz_studio.core.harness import Harness
from wireviz_studio.core.models import Metadata, Options, Tweak


def _make_harness() -> Harness:
    return Harness(metadata=Metadata(), options=Options(), tweak=Tweak())


def test_make_list_and_make_str_helpers():
    assert make_list(None) == []
    assert make_list("X1") == ["X1"]
    assert make_list(["X1", "X2"]) == ["X1", "X2"]
    assert make_str([1, "X2"]) == "1, X2"
    assert make_str(None) == ""


def test_pn_info_string_formats_expected_variants():
    assert pn_info_string("P/N", "Acme", "123") == "Acme: 123"
    assert pn_info_string("P/N", None, "123") == "P/N: 123"
    assert pn_info_string("P/N", "Acme", None) == "Acme"
    assert pn_info_string("P/N", None, None) is None


def test_generate_bom_merges_identical_parts_and_collects_designators():
    harness = _make_harness()
    harness.add_connector("X2", pincount=2, type="Header")
    harness.add_connector("X1", pincount=2, type="Header")

    bom = generate_bom(harness)

    assert len(bom) == 1
    assert bom[0]["qty"] == 2
    assert bom[0]["designators"] == ["X1", "X2"]


def test_bom_list_includes_optional_columns_when_present():
    rows = bom_list([
        {
            "id": 1,
            "description": "Connector",
            "qty": 1,
            "unit": "",
            "designators": ["X1"],
            "pn": "ABC-123",
        }
    ])

    assert rows[0][:5] == ["Id", "Description", "Qty", "Unit", "Designators"]
    assert "P/N" in rows[0]
