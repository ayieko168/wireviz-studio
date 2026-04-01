from wireviz_studio.core.models import Cable, Connector, Options, Side


def test_options_default_background_chain_uses_bgcolor():
    options = Options(bgcolor="BK", bgcolor_node=None, bgcolor_connector=None, bgcolor_cable=None)

    assert options.bgcolor_node == "BK"
    assert options.bgcolor_connector == "BK"
    assert options.bgcolor_cable == "BK"
    assert options.bgcolor_bundle == "BK"


def test_connector_qty_multiplier_counts_populated_and_unpopulated():
    connector = Connector(name="X1", pincount=3)
    connector.activate_pin(1, Side.LEFT)
    connector.activate_pin(2, Side.RIGHT)

    assert connector.get_qty_multiplier("pincount") == 3
    assert connector.get_qty_multiplier("populated") == 2
    assert connector.get_qty_multiplier("unpopulated") == 1


def test_cable_parses_text_length_and_defaults_unit():
    cable = Cable(name="W1", wirecount=2, colors=["RD", "BK"], length="2.5 m")

    assert cable.length == 2.5
    assert cable.length_unit == "m"


def test_cable_qty_multiplier_terminations_and_total_length():
    cable = Cable(name="W2", wirecount=2, colors=["RD", "BK"], length=3)
    cable.connect("X1", (1, 2), (1, 2), "X2", (1, 2))

    assert cable.get_qty_multiplier("wirecount") == 2
    assert cable.get_qty_multiplier("terminations") == 2
    assert cable.get_qty_multiplier("total_length") == 6
