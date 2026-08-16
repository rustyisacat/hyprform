"""Best-effort live introspection of a *running* Hyprland session via
``hyprctl -j``. Every function here degrades to ``None``/an empty result
instead of raising — hyprctl might not be installed, Hyprland might not be
running (e.g. testing against a copied config), or it might just be slow.
None of this is required for Hyprform to work; it only makes a few "add
new" flows nicer by pre-filling real values (connected monitor names,
currently running app classes) instead of asking the user to already know
Hyprland's own inspection commands.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess

_TIMEOUT = 2.0


def is_available() -> bool:
    """True if we're actually running inside a live Hyprland session with
    the ``hyprctl`` command available to talk to it. HYPRLAND_INSTANCE_SIGNATURE
    is an environment variable Hyprland itself sets for every process running
    under it — its presence is the standard way to detect "am I on Hyprland
    right now?" rather than, say, testing against a copied config on some
    other desktop.
    """
    return bool(os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")) and shutil.which("hyprctl") is not None


def _run_json(args: list[str]):
    """Runs ``hyprctl -j <args>`` and parses its JSON output (the ``-j`` flag
    is hyprctl's own "give me machine-readable output" option). Returns None
    on literally any failure — not running, not installed, bad output,
    taking too long — so callers never need their own try/except.
    """
    if not is_available():
        return None
    try:
        result = subprocess.run(
            ["hyprctl", "-j", *args],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def list_monitors() -> list[dict] | None:
    """Currently connected monitors, e.g. [{"name": "DP-1", "width": 2560, ...}]."""
    return _run_json(["monitors"])


def list_clients() -> list[dict] | None:
    """Currently open windows, e.g. [{"class": "kitty", "title": "...", ...}]."""
    return _run_json(["clients"])


def reload() -> tuple[bool, str]:
    """Best-effort ``hyprctl reload``. Never raises — returns (ok, message)."""
    if not is_available():
        return False, "Hyprland doesn't appear to be running — skipped reload."
    try:
        result = subprocess.run(
            ["hyprctl", "reload"],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
        if result.returncode == 0:
            return True, "Reloaded Hyprland."
        detail = (result.stderr or result.stdout).strip()
        return False, f"hyprctl reload failed: {detail}" if detail else "hyprctl reload failed."
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        return False, f"Couldn't reload Hyprland: {e}"
