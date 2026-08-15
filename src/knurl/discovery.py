"""Finds a Hyprland config's entrypoint and follows its includes
(``source =`` for hyprlang, ``require(...)`` for Lua) into a full graph of
every file that's actually part of the live config — across both formats,
since a real install (e.g. Caelestia's) can mix them.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from .hyprlang.model import Document
from .hyprlang.parser import HyprlangParseError, parse as parse_hyprlang
from .lua.parser import LuaModule

DEFAULT_HYPR_DIR = os.path.expanduser("~/.config/hypr")

_REQUIRE_RE = re.compile(r"""require\s*\(\s*["']([^"']+)["']\s*\)""")


@dataclass
class ConfigTree:
    root_dir: str
    entrypoint: str
    hyprlang_docs: dict[str, Document] = field(default_factory=dict)
    lua_modules: dict[str, LuaModule] = field(default_factory=dict)
    unresolved: list[str] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)
    original_text: dict[str, str] = field(default_factory=dict)

    def all_paths(self) -> list[str]:
        return sorted({*self.hyprlang_docs, *self.lua_modules})


def find_entrypoint(hypr_dir: str = DEFAULT_HYPR_DIR) -> str | None:
    """Hyprland tries hyprland.conf first; a Lua-based install (Caelestia and
    similar) replaces it with hyprland.lua and leaves a stub .conf (or none).
    """
    lua_entry = os.path.join(hypr_dir, "hyprland.lua")
    conf_entry = os.path.join(hypr_dir, "hyprland.conf")
    if os.path.isfile(lua_entry):
        return lua_entry
    if os.path.isfile(conf_entry):
        return conf_entry
    return None


def _resolve_source_path(raw: str, root_dir: str, from_dir: str) -> str:
    expanded = os.path.expanduser(raw.strip())
    if os.path.isabs(expanded):
        return expanded
    candidate = os.path.join(from_dir, expanded)
    if os.path.isfile(candidate):
        return candidate
    return os.path.join(root_dir, expanded)


def _resolve_require(name: str, root_dir: str) -> str | None:
    rel = name.replace(".", os.sep)
    for candidate in (f"{rel}.lua", os.path.join(rel, "init.lua")):
        path = os.path.join(root_dir, candidate)
        if os.path.isfile(path):
            return path
    return None


def load(hypr_dir: str = DEFAULT_HYPR_DIR, entrypoint: str | None = None) -> ConfigTree:
    entry = entrypoint or find_entrypoint(hypr_dir)
    if entry is None:
        raise FileNotFoundError(f"no hyprland.conf or hyprland.lua found under {hypr_dir}")

    tree = ConfigTree(root_dir=hypr_dir, entrypoint=entry)
    seen: set[str] = set()

    def load_hyprlang(path: str) -> None:
        if path in seen or not os.path.isfile(path):
            if not os.path.isfile(path):
                tree.unresolved.append(path)
            return
        seen.add(path)
        try:
            text = open(path).read()
            doc = parse_hyprlang(text, path=path)
        except HyprlangParseError as e:
            tree.errors[path] = str(e)
            return
        tree.hyprlang_docs[path] = doc
        tree.original_text[path] = text
        for kv in _iter_all_keyvalues(doc.root):
            if kv.key == "source":
                load_hyprlang(_resolve_source_path(kv.value, tree.root_dir, os.path.dirname(path)))

    def load_lua(path: str) -> None:
        if path in seen or not os.path.isfile(path):
            if not os.path.isfile(path):
                tree.unresolved.append(path)
            return
        seen.add(path)
        text = open(path).read()
        try:
            module = LuaModule(text, path=path)
        except Exception as e:  # pragma: no cover - malformed/dynamic Lua we can't parse
            tree.errors[path] = str(e)
            return
        tree.lua_modules[path] = module
        tree.original_text[path] = text
        for match in _REQUIRE_RE.finditer(text):
            resolved = _resolve_require(match.group(1), tree.root_dir)
            if resolved is not None:
                load_lua(resolved)
            else:
                tree.unresolved.append(match.group(1))

    if entry.endswith(".lua"):
        load_lua(entry)
    else:
        load_hyprlang(entry)

    return tree


def _iter_all_keyvalues(block):
    from .hyprlang.model import Block, KeyValue

    for child in block.children:
        if isinstance(child, KeyValue):
            yield child
        elif isinstance(child, Block):
            yield from _iter_all_keyvalues(child)
