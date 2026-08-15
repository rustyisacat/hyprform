from hyprform import discovery
from hyprform.hyprlang.writer import serialize as serialize_hyprlang
from hyprform.schema.binder import add_keybind, add_monitor, add_window_rule, list_monitors


def test_monitor_line_splits_into_editable_fields(tmp_path):
    conf = tmp_path / "hyprland.conf"
    conf.write_text("monitor=DP-1,1920x1080@144,0x0,1\n")
    tree = discovery.load(hypr_dir=str(tmp_path))

    items = list_monitors(tree)
    assert len(items) == 1
    labels = [f.label for f in items[0].fields]
    assert labels == ["Name", "Resolution", "Position", "Scale"]
    values = [f.value for f in items[0].fields]
    assert values == ["DP-1", "1920x1080@144", "0x0", "1"]


def test_editing_one_monitor_field_only_changes_that_field(tmp_path):
    conf = tmp_path / "hyprland.conf"
    conf.write_text("monitor=DP-1,1920x1080@144,0x0,1\n")
    tree = discovery.load(hypr_dir=str(tmp_path))

    items = list_monitors(tree)
    name_field, resolution_field, position_field, scale_field = items[0].fields
    resolution_field.set("2560x1440@165")

    doc = tree.hyprlang_docs[str(conf)]
    kv = doc.root.find_all("monitor")[0]
    assert kv.value == "DP-1,2560x1440@165,0x0,1"

    # a second edit on a different field must not clobber the first
    scale_field.set("1.5")
    kv = doc.root.find_all("monitor")[0]
    assert kv.value == "DP-1,2560x1440@165,0x0,1.5"


def test_monitor_with_missing_trailing_fields_defaults_to_empty(tmp_path):
    conf = tmp_path / "hyprland.conf"
    conf.write_text("monitor=,preferred,auto,1\n")
    tree = discovery.load(hypr_dir=str(tmp_path))

    items = list_monitors(tree)
    values = [f.value for f in items[0].fields]
    assert values == ["", "preferred", "auto", "1"]


def test_add_window_rule_hyprlang(tmp_path):
    conf = tmp_path / "hyprland.conf"
    conf.write_text("windowrulev2 = float,class:^(pavucontrol)$\n")
    tree = discovery.load(hypr_dir=str(tmp_path))

    ok, msg = add_window_rule(tree, "class", "kitty", "opacity", "0.9 0.8")
    assert ok, msg

    doc = tree.hyprlang_docs[str(conf)]
    text = serialize_hyprlang(doc)
    assert text.splitlines()[-1] == "windowrulev2 = opacity 0.9 0.8,class:^(kitty)$"


def test_add_window_rule_requires_match_value(tmp_path):
    conf = tmp_path / "hyprland.conf"
    conf.write_text("windowrulev2 = float,class:^(pavucontrol)$\n")
    tree = discovery.load(hypr_dir=str(tmp_path))

    ok, msg = add_window_rule(tree, "class", "  ", "float", "")
    assert not ok
    assert "match" in msg.lower()


def test_add_window_rule_lua_fails_honestly_instead_of_guessing(tmp_path):
    lua = tmp_path / "hyprland.lua"
    lua.write_text('hl.window_rule({ class = "kitty", rule = "float" })\n')
    tree = discovery.load(hypr_dir=str(tmp_path))

    ok, msg = add_window_rule(tree, "class", "kitty", "float", "")
    assert not ok
    assert "doesn't know" in msg.lower() or "won't guess" in msg.lower()


def test_add_keybind_hyprlang(tmp_path):
    conf = tmp_path / "hyprland.conf"
    conf.write_text("bind = SUPER, Q, exec, kitty\n")
    tree = discovery.load(hypr_dir=str(tmp_path))

    ok, msg = add_keybind(tree, "SUPER", "F", "fullscreen", "", False)
    assert ok, msg

    doc = tree.hyprlang_docs[str(conf)]
    text = serialize_hyprlang(doc)
    assert text.splitlines()[-1] == "bind = SUPER, F, fullscreen, "


def test_add_keybind_repeat_uses_binde(tmp_path):
    conf = tmp_path / "hyprland.conf"
    conf.write_text("bind = SUPER, Q, exec, kitty\n")
    tree = discovery.load(hypr_dir=str(tmp_path))

    ok, msg = add_keybind(tree, "SUPER", "L", "resizeactive", "20 0", True)
    assert ok, msg

    doc = tree.hyprlang_docs[str(conf)]
    text = serialize_hyprlang(doc)
    assert text.splitlines()[-1] == "binde = SUPER, L, resizeactive, 20 0"


def test_add_keybind_requires_key(tmp_path):
    conf = tmp_path / "hyprland.conf"
    conf.write_text("bind = SUPER, Q, exec, kitty\n")
    tree = discovery.load(hypr_dir=str(tmp_path))

    ok, msg = add_keybind(tree, "SUPER", "  ", "exec", "kitty", False)
    assert not ok
    assert "key" in msg.lower()


def test_add_keybind_lua_fails_honestly_instead_of_guessing(tmp_path):
    lua = tmp_path / "hyprland.lua"
    lua.write_text('hl.config({ general = { layout = "dwindle" } })\n')
    tree = discovery.load(hypr_dir=str(tmp_path))

    ok, msg = add_keybind(tree, "SUPER", "Q", "exec", "kitty", False)
    assert not ok
    assert "doesn't know" in msg.lower() or "won't guess" in msg.lower()


def test_add_monitor_hyprlang(tmp_path):
    conf = tmp_path / "hyprland.conf"
    conf.write_text("monitor=DP-1,1920x1080@144,0x0,1\n")
    tree = discovery.load(hypr_dir=str(tmp_path))

    ok, msg = add_monitor(tree, "HDMI-A-1", "1920x1080@60", "2560x0", "1")
    assert ok, msg

    doc = tree.hyprlang_docs[str(conf)]
    text = serialize_hyprlang(doc)
    assert text.splitlines()[-1] == "monitor = HDMI-A-1,1920x1080@60,2560x0,1"


def test_add_monitor_defaults_blank_fields(tmp_path):
    conf = tmp_path / "hyprland.conf"
    conf.write_text("monitor=DP-1,1920x1080@144,0x0,1\n")
    tree = discovery.load(hypr_dir=str(tmp_path))

    ok, msg = add_monitor(tree, "HDMI-A-1", "", "", "")
    assert ok, msg

    doc = tree.hyprlang_docs[str(conf)]
    text = serialize_hyprlang(doc)
    assert text.splitlines()[-1] == "monitor = HDMI-A-1,preferred,auto,1"


def test_add_monitor_lua_fails_honestly_instead_of_guessing(tmp_path):
    lua = tmp_path / "hyprland.lua"
    lua.write_text('hl.monitor({ name = "DP-1", width = 2560 })\n')
    tree = discovery.load(hypr_dir=str(tmp_path))

    ok, msg = add_monitor(tree, "HDMI-A-1", "1920x1080", "0x0", "1")
    assert not ok
    assert "doesn't know" in msg.lower() or "won't guess" in msg.lower()
