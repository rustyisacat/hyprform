from knurl import discovery
from knurl.hyprlang.writer import serialize as serialize_hyprlang
from knurl.schema.binder import add_autostart, add_environment


def test_add_autostart_hyprlang(tmp_path):
    conf = tmp_path / "hyprland.conf"
    conf.write_text("exec-once = waybar\n")
    tree = discovery.load(hypr_dir=str(tmp_path))

    ok, msg = add_autostart(tree, "nm-applet")
    assert ok, msg

    doc = tree.hyprlang_docs[str(conf)]
    text = serialize_hyprlang(doc)
    assert text == "exec-once = waybar\nexec-once = nm-applet\n"


def test_add_environment_hyprlang(tmp_path):
    conf = tmp_path / "hyprland.conf"
    conf.write_text("env = XCURSOR_SIZE,24\n")
    tree = discovery.load(hypr_dir=str(tmp_path))

    ok, msg = add_environment(tree, "MOZ_ENABLE_WAYLAND", "1")
    assert ok, msg

    doc = tree.hyprlang_docs[str(conf)]
    text = serialize_hyprlang(doc)
    assert text == "env = XCURSOR_SIZE,24\nenv = MOZ_ENABLE_WAYLAND,1\n"


def test_add_autostart_lua_inserts_beside_existing_call_not_at_eof(tmp_path):
    lua = tmp_path / "hyprland.lua"
    lua.write_text(
        'hl.on("hyprland.start", function()\n'
        '    hl.exec_cmd("waybar")\n'
        "end)\n"
    )
    tree = discovery.load(hypr_dir=str(tmp_path))

    ok, msg = add_autostart(tree, "nm-applet")
    assert ok, msg

    module = tree.lua_modules[str(lua)]
    lines = module.source.splitlines()
    # the new call must land *inside* the hl.on(...) closure, not after "end)"
    assert lines == [
        'hl.on("hyprland.start", function()',
        '    hl.exec_cmd("waybar")',
        '    hl.exec_cmd("nm-applet")',
        "end)",
    ]

    # and the module must still parse cleanly with both calls discoverable
    calls = [c for c in module.call_sites if c.dotted_name == "hl.exec_cmd"]
    assert [c.args[0].value for c in calls] == ["waybar", "nm-applet"]


def test_add_environment_lua_no_anchor_fails_safely(tmp_path):
    lua = tmp_path / "hyprland.lua"
    lua.write_text("hl.config({ general = { layout = \"dwindle\" } })\n")
    tree = discovery.load(hypr_dir=str(tmp_path))

    ok, msg = add_environment(tree, "FOO", "bar")
    assert not ok
    assert "no existing" in msg.lower()
