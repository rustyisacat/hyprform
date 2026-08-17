from hyprform.ui import window_state


def test_load_returns_empty_dict_when_nothing_saved_yet(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert window_state.load() == {}


def test_save_then_load_round_trips(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    window_state.save(1200, 800, False)
    assert window_state.load() == {"width": 1200, "height": 800, "maximized": False}


def test_load_ignores_corrupt_file(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    state_dir = tmp_path / "hyprform"
    state_dir.mkdir()
    (state_dir / "window-state.json").write_text("not json{{{")
    assert window_state.load() == {}


def test_load_ignores_non_dict_json(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    state_dir = tmp_path / "hyprform"
    state_dir.mkdir()
    (state_dir / "window-state.json").write_text("[1, 2, 3]")
    assert window_state.load() == {}
