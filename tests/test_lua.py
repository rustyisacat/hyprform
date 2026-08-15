from pathlib import Path

from knurl.lua.locators import ArrayItem, CallArg, ReturnTableField, TableField, make_setter
from knurl.lua.parser import LuaModule
from knurl.lua.values import ArrayValue, LiteralValue, OpaqueValue, TableValue

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> LuaModule:
    return LuaModule((FIXTURES / name).read_text(), path=name)


def test_hl_config_table_is_classified_correctly():
    m = load("sample_config.lua")
    call = next(c for c in m.call_sites if c.dotted_name == "hl.config")
    table = call.args[0]
    assert isinstance(table, TableValue)
    general = table.fields["general"]
    assert isinstance(general.fields["layout"], LiteralValue)
    assert general.fields["layout"].value == "dwindle"
    assert isinstance(general.fields["border_size"], LiteralValue)
    assert general.fields["border_size"].value == 2
    # a reference to another module's variable is not a literal
    assert isinstance(general.fields["gaps_in"], OpaqueValue)
    assert general.fields["gaps_in"].raw == "vars.gapsIn"


def test_return_table_has_literals_and_arrays():
    m = load("sample_variables.lua")
    rt = m.return_table
    assert isinstance(rt.fields["gapsIn"], LiteralValue)
    assert rt.fields["gapsIn"].value == 5
    assert isinstance(rt.fields["kbMoveToWs"], ArrayValue)
    assert [i.value for i in rt.fields["kbMoveToWs"].items] == [
        "SUPER + ALT + S",
        "CTRL + SUPER + SHIFT + Up",
    ]


def test_editing_via_locator_survives_a_prior_edit_in_the_same_file():
    """Regression test: a span captured before another edit in the same file
    must not be used directly — locators re-resolve fresh every time.
    """
    m = load("sample_variables.lua")

    gaps_locator = ReturnTableField("gapsIn")
    cursor_locator = ReturnTableField("cursorTheme")

    gaps_setter = make_setter(m, gaps_locator, "number")
    cursor_setter = make_setter(m, cursor_locator, "string")

    gaps_setter(9)  # shifts every offset after it in the file
    cursor_setter("Breeze")  # must not corrupt the file despite the shift

    assert m.return_table.fields["gapsIn"].value == 9
    assert m.return_table.fields["cursorTheme"].value == "Breeze"


def test_array_item_and_call_arg_locators():
    m = load("sample_variables.lua")
    base = ReturnTableField("kbMoveToWs")
    item0 = ArrayItem(base, 0)
    setter = make_setter(m, item0, "string")
    setter("SUPER + ALT + T")
    assert m.return_table.fields["kbMoveToWs"].items[0].value == "SUPER + ALT + T"

    m2 = load("sample_config.lua")
    monitor_locator = TableField(CallArg("hl.monitor", 0, 0), ("scale",))
    setter2 = make_setter(m2, monitor_locator, "number")
    setter2(2)
    call = next(c for c in m2.call_sites if c.dotted_name == "hl.monitor")
    assert call.args[0].fields["scale"].value == 2


def test_exec_cmd_calls_found_in_source_order():
    m = load("sample_config.lua")
    calls = [c for c in m.call_sites if c.dotted_name == "hl.exec_cmd"]
    assert [c.args[0].value for c in calls] == ["waybar", "hyprpaper"]
