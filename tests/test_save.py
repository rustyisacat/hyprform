from hyprform import discovery, save


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
