"""Writes back whatever changed in a ConfigTree — one backup per touched
file, then only the files whose serialized text actually differs from what
was loaded. Nothing is ever regenerated wholesale; every diff should be as
small as the edits that were actually made in the GUI.
"""

from __future__ import annotations

import datetime
import difflib
import shutil
from dataclasses import dataclass

from . import hyprctl
from .hyprlang.writer import serialize as serialize_hyprlang


@dataclass
class SavedFile:
    path: str
    backup_path: str
    diff_lines_changed: int


def pending_changes(tree) -> dict[str, str]:
    """path -> new text, for every file whose content actually changed."""
    changed = {}
    for path, doc in tree.hyprlang_docs.items():
        new_text = serialize_hyprlang(doc)
        if new_text != tree.original_text.get(path):
            changed[path] = new_text
    for path, module in tree.lua_modules.items():
        if module.source != tree.original_text.get(path):
            changed[path] = module.source
    return changed


def unified_diffs(tree) -> dict[str, str]:
    """path -> diff text, for every file with pending changes — so the GUI
    can show exactly what's about to be written before Save actually
    touches disk. "Unified diff" is the standard +/- line-by-line format
    (removed lines prefixed with "-", added lines with "+") that tools like
    ``git diff`` and ``diff -u`` also use.
    """
    diffs = {}
    for path, new_text in pending_changes(tree).items():
        old_text = tree.original_text.get(path, "")
        diff = difflib.unified_diff(
            old_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=f"{path} (before)",
            tofile=f"{path} (after)",
        )
        diffs[path] = "".join(diff)
    return diffs


def save(tree, reload_hyprland: bool = False) -> tuple[list[SavedFile], str | None]:
    """Writes every pending change to disk. Returns the list of files
    actually written, plus a human-readable reload status message (None if
    a reload wasn't requested at all).
    """
    changed = pending_changes(tree)
    saved: list[SavedFile] = []
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    for path, new_text in changed.items():
        backup_path = f"{path}.hyprform-bak-{timestamp}"
        shutil.copy2(path, backup_path)
        with open(path, "w") as f:
            f.write(new_text)
        old_lines = tree.original_text[path].splitlines()
        new_lines = new_text.splitlines()
        changed_count = sum(1 for a, b in zip(old_lines, new_lines) if a != b) + abs(len(old_lines) - len(new_lines))
        saved.append(SavedFile(path=path, backup_path=backup_path, diff_lines_changed=changed_count))
        tree.original_text[path] = new_text

    reload_message = None
    if saved and reload_hyprland:
        _ok, reload_message = hyprctl.reload()

    return saved, reload_message
