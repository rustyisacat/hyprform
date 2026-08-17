"""Remembers the window's size across restarts, the same way any well
behaved desktop app does — so Hyprform doesn't reopen at a fixed default
size every time once you've resized it to fit your screen.
"""

from __future__ import annotations

import json
import os


def _state_path() -> str:
    config_home = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(config_home, "hyprform", "window-state.json")


def load() -> dict:
    """Returns whatever was last saved, or an empty dict if there's nothing
    yet (first run) or the file is missing/corrupt — either way, the window
    just falls back to its built-in default size rather than failing.
    """
    try:
        with open(_state_path()) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save(width: int, height: int, maximized: bool) -> None:
    path = _state_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump({"width": width, "height": height, "maximized": maximized}, f)
    except OSError:
        pass  # remembering the window size is a nicety, never worth a crash
