from hyprform import discovery, hyprctl, save


def test_unified_diffs_empty_when_nothing_changed(tmp_path):
    conf = tmp_path / "hyprland.conf"
    conf.write_text("general {\n    gaps_in = 5\n}\n")
    tree = discovery.load(hypr_dir=str(tmp_path))

    assert save.unified_diffs(tree) == {}


def test_unified_diffs_shows_the_actual_line_change(tmp_path):
    conf = tmp_path / "hyprland.conf"
    conf.write_text("general {\n    gaps_in = 5\n}\n")
    tree = discovery.load(hypr_dir=str(tmp_path))

    doc = tree.hyprlang_docs[str(conf)]
    doc.root.find_block("general").find_first("gaps_in").touch("8")

    diffs = save.unified_diffs(tree)
    assert list(diffs.keys()) == [str(conf)]
    diff_text = diffs[str(conf)]
    assert "-    gaps_in = 5" in diff_text
    assert "+    gaps_in = 8" in diff_text


def test_unified_diffs_does_not_touch_disk(tmp_path):
    conf = tmp_path / "hyprland.conf"
    conf.write_text("general {\n    gaps_in = 5\n}\n")
    tree = discovery.load(hypr_dir=str(tmp_path))

    doc = tree.hyprlang_docs[str(conf)]
    doc.root.find_block("general").find_first("gaps_in").touch("8")

    save.unified_diffs(tree)
    assert conf.read_text() == "general {\n    gaps_in = 5\n}\n"


def test_save_with_no_changes_writes_nothing(tmp_path):
    conf = tmp_path / "hyprland.conf"
    conf.write_text("general {\n    gaps_in = 5\n}\n")
    tree = discovery.load(hypr_dir=str(tmp_path))

    saved, reload_message = save.save(tree)
    assert saved == []
    assert reload_message is None


def test_save_writes_changed_file_with_backup(tmp_path):
    conf = tmp_path / "hyprland.conf"
    conf.write_text("general {\n    gaps_in = 5\n}\n")
    tree = discovery.load(hypr_dir=str(tmp_path))

    doc = tree.hyprlang_docs[str(conf)]
    doc.root.find_block("general").find_first("gaps_in").touch("8")

    saved, reload_message = save.save(tree)
    assert len(saved) == 1
    assert reload_message is None  # reload not requested
    assert "gaps_in = 8" in conf.read_text()
    assert list(tmp_path.glob("hyprland.conf.hyprform-bak-*"))


def test_save_reload_requested_uses_hyprctl_and_surfaces_message(tmp_path, monkeypatch):
    """Never let this hit a real hyprctl — pytest may well be running
    inside a live Hyprland session, and a test triggering a real reload as
    a side effect would be a surprising, disruptive bug in the test itself.
    """
    conf = tmp_path / "hyprland.conf"
    conf.write_text("general {\n    gaps_in = 5\n}\n")
    tree = discovery.load(hypr_dir=str(tmp_path))
    doc = tree.hyprlang_docs[str(conf)]
    doc.root.find_block("general").find_first("gaps_in").touch("8")

    monkeypatch.setattr(hyprctl, "reload", lambda: (True, "Reloaded Hyprland."))
    saved, reload_message = save.save(tree, reload_hyprland=True)
    assert len(saved) == 1
    assert reload_message == "Reloaded Hyprland."
