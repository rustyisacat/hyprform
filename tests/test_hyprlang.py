from pathlib import Path

from hyprform.hyprlang import parser, writer
from hyprform.hyprlang.model import KeyValue

FIXTURE = Path(__file__).parent / "fixtures" / "sample.conf"


def test_round_trip_is_byte_identical():
    original = FIXTURE.read_text()
    doc = parser.parse(original, path=str(FIXTURE))
    assert writer.serialize(doc) == original


def test_editing_one_value_only_changes_that_line():
    original = FIXTURE.read_text()
    doc = parser.parse(original, path=str(FIXTURE))

    general = doc.root.find_block("general")
    gaps = general.find_first("gaps_in")
    assert gaps.value == "5"
    gaps.touch("8")

    new_text = writer.serialize(doc)
    old_lines = original.splitlines()
    new_lines = new_text.splitlines()
    assert len(old_lines) == len(new_lines)
    changed = [i for i, (a, b) in enumerate(zip(old_lines, new_lines)) if a != b]
    assert changed == [old_lines.index("    gaps_in = 5")]
    assert "gaps_in = 8" in new_lines[changed[0]]


def test_repeatable_keys_all_preserved_in_order():
    doc = parser.parse(FIXTURE.read_text(), path=str(FIXTURE))
    binds = doc.root.find_all("bind")
    assert [b.value for b in binds] == [
        "SUPER, Q, exec, kitty",
        "SUPER, C, killactive,",
        "SUPER, M, exit,",
    ]


def test_new_keyvalue_can_be_appended():
    doc = parser.parse(FIXTURE.read_text(), path=str(FIXTURE))
    doc.root.children.append(KeyValue(key="exec-once", value="nm-applet"))
    new_text = writer.serialize(doc)
    assert new_text.splitlines()[-1] == "exec-once = nm-applet"
