"""Connects the plain-English schema (and the list-shaped categories:
monitors, keybinds, autostart, environment, window rules) to whatever a real
config tree actually contains — hyprlang, Lua, or a mix of both.

Every bound item carries enough to both display *and* write back: a getter,
a setter, which file it lives in, and whether it's actually safe to edit
(``editable=False`` items are shown read-only with their raw source text —
see the module docstring in ``knurl.lua.parser`` for why that limit exists).

Lua setters are built from *locators* (``knurl.lua.locators``), not raw
spans — a span captured at bind time goes stale the moment any earlier edit
in the same file is applied, since every offset after it shifts. Locators
re-find the value fresh each time, so editing several fields from the same
file in one sitting (very common — e.g. gaps, border, and rounding all live
in the same ``variables.lua``) can't corrupt the file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from ..hyprlang.model import Block, KeyValue
from ..lua.locators import ArrayItem, CallArg, Locator, ReturnTableField, TableField, make_setter
from ..lua.values import ArrayValue, LiteralValue, OpaqueValue, TableValue
from ..lua.writer import format_literal
from .fields import FieldSpec

BIND_KEYS = {"bind", "binde", "bindm", "bindr", "bindl", "bindn", "bindt", "bindi", "binds"}


@dataclass
class BoundField:
    label: str
    description: str
    kind: str
    value: object
    source_file: str
    editable: bool
    choices: tuple[str, ...] = ()
    unit: str = ""
    _setter: Callable[[object], None] | None = None

    def set(self, new_value: object) -> None:
        if not self.editable or self._setter is None:
            raise ValueError(f"field {self.label!r} is not editable")
        self._setter(new_value)


@dataclass
class ListItem:
    summary: str
    fields: list[BoundField]
    source_file: str
    editable: bool
    raw: str = ""


@dataclass
class AddSpec:
    """Describes how to add a new entry to a list-shaped category.
    ``fields`` names the plain-text inputs the GUI should collect (e.g.
    ``["Command"]`` or ``["Name", "Value"]``); ``handler`` receives them in
    that order and returns (success, message).
    """

    fields: list[str]
    handler: Callable[..., tuple[bool, str]]


@dataclass
class Category:
    name: str
    scalar_fields: list[BoundField]
    list_items: list[ListItem]
    add_spec: AddSpec | None = None


# ---------------------------------------------------------------------------
# hyprlang <-> typed value bridging
# ---------------------------------------------------------------------------

_TRUE_WORDS = {"true", "yes", "on", "1"}


def _hyprlang_to_typed(kind: str, raw: str):
    raw = raw.strip()
    if kind == "bool":
        return raw.lower() in _TRUE_WORDS
    if kind == "number":
        try:
            return int(raw)
        except ValueError:
            return float(raw)
    if kind == "float":
        return float(raw)
    return raw


def _typed_to_hyprlang(kind: str, value) -> str:
    if kind == "bool":
        return "true" if value else "false"
    return str(value)


def _find_hyprlang_block(tree, section: str) -> Block | None:
    parts = section.split(".")
    for doc in tree.hyprlang_docs.values():
        block = doc.root.find_block(parts[0])
        for part in parts[1:]:
            if block is None:
                break
            block = block.find_block(part)
        if block is not None:
            return block
    return None


def _find_config_call(tree, section: str, key: str):
    """Locate the ``hl.config`` call (by module + call-index, for a stable
    locator) whose table contains the given dotted section path *and* the
    leaf key — matching on section alone isn't enough, since several files
    each define their own top-level section (general.lua's "general" table
    doesn't have every "general.*" key hyprlang supports).
    """
    parts = (*section.split("."), key)
    for path, module in tree.lua_modules.items():
        config_calls = [c for c in module.call_sites if c.dotted_name == "hl.config"]
        for call_index, call in enumerate(config_calls):
            if not call.args:
                continue
            node = call.args[0]
            for part in parts:
                if not isinstance(node, TableValue) or part not in node.fields:
                    node = None
                    break
                node = node.fields[part]
            if node is not None:
                return module, path, call_index
    return None, None, None


def bind_scalar(tree, spec: FieldSpec) -> BoundField | None:
    block = _find_hyprlang_block(tree, spec.section)
    if block is not None:
        kv = block.find_first(spec.key)
        if kv is not None:
            value = _hyprlang_to_typed(spec.kind, kv.value)

            def setter(new_value, kv=kv, kind=spec.kind):
                kv.touch(_typed_to_hyprlang(kind, new_value))

            return BoundField(spec.label, spec.description, spec.kind, value, block.name, True, spec.choices, spec.unit, setter)

    module, path, call_index = _find_config_call(tree, spec.section, spec.key)
    if module is not None:
        locator: Locator = TableField(CallArg("hl.config", call_index, 0), (*spec.section.split("."), spec.key))
        field_value = locator.get(module)
        if isinstance(field_value, LiteralValue):
            setter = make_setter(module, locator, field_value.kind)
            return BoundField(spec.label, spec.description, spec.kind, field_value.value, path, True, spec.choices, spec.unit, setter)
        if isinstance(field_value, OpaqueValue):
            deref = _deref_variable(tree, field_value.raw)
            if deref is not None:
                var_value, var_locator, var_module, var_path = deref
                description = f"{spec.description} (shared variable: {field_value.raw})"
                setter = make_setter(var_module, var_locator, var_value.kind)
                return BoundField(spec.label, description, spec.kind, var_value.value, var_path, True, spec.choices, spec.unit, setter)
            return BoundField(spec.label, spec.description, spec.kind, field_value.raw, path, False, spec.choices, spec.unit)

    return None


_VAR_REF_RE = re.compile(r"^(?:vars|variables)\.(\w+)$")


def _deref_variable(tree, raw_text: str):
    """If an opaque value is exactly a ``vars.name`` reference, look ``name``
    up in whichever loaded Lua module has a top-level ``return { name = ... }``
    (i.e. variables.lua). Returns (literal, locator, module, path).
    """
    m = _VAR_REF_RE.match(raw_text.strip())
    if not m:
        return None
    name = m.group(1)
    for path, module in tree.lua_modules.items():
        if module.return_table is not None and name in module.return_table.fields:
            value = module.return_table.fields[name]
            if isinstance(value, LiteralValue):
                return value, ReturnTableField(name), module, path
    return None


def build_scalar_categories(tree) -> dict[str, list[BoundField]]:
    from .fields import FIELDS

    out: dict[str, list[BoundField]] = {}
    for spec in FIELDS:
        bound = bind_scalar(tree, spec)
        if bound is not None:
            out.setdefault(spec.category, []).append(bound)
    return out


# ---------------------------------------------------------------------------
# List-shaped categories: monitors, autostart, environment, window rules
# ---------------------------------------------------------------------------


def list_autostart(tree) -> list[ListItem]:
    items: list[ListItem] = []
    for path, doc in tree.hyprlang_docs.items():
        for kv in doc.root.find_all("exec-once"):
            items.append(_hyprlang_string_item(kv, path))
    for path, module in tree.lua_modules.items():
        calls = [c for c in module.call_sites if c.dotted_name == "hl.exec_cmd"]
        for i, call in enumerate(calls):
            if not call.args:
                continue
            value = call.args[0]
            locator = CallArg("hl.exec_cmd", i, 0)
            items.append(_lua_single_item(value, locator, module, path, "Command"))
    return items


def list_environment(tree) -> list[ListItem]:
    items: list[ListItem] = []
    for path, doc in tree.hyprlang_docs.items():
        for kv in doc.root.find_all("env"):
            name, _, val = kv.value.partition(",")
            items.append(ListItem(summary=f"{name.strip()} = {val.strip()}", fields=[], source_file=path, editable=False, raw=kv.value))
    for path, module in tree.lua_modules.items():
        calls = [c for c in module.call_sites if c.dotted_name == "hl.env"]
        for i, call in enumerate(calls):
            if len(call.args) != 2:
                continue
            name_arg, val_arg = call.args
            name = name_arg.value if isinstance(name_arg, LiteralValue) else name_arg.raw
            if isinstance(val_arg, LiteralValue):
                locator = CallArg("hl.env", i, 1)
                field = _literal_field("Value", "", val_arg, locator, module, path)
                items.append(ListItem(summary=str(name), fields=[field], source_file=path, editable=True))
            else:
                items.append(ListItem(summary=f"{name} = {val_arg.raw}", fields=[], source_file=path, editable=False, raw=val_arg.raw))
    return items


def add_autostart(tree, command: str) -> tuple[bool, str]:
    command = command.strip()
    if not command:
        return False, "Enter a command first."

    if tree.hyprlang_docs:
        doc = max(tree.hyprlang_docs.values(), key=lambda d: len(d.root.find_all("exec-once")))
        doc.root.children.append(KeyValue(key="exec-once", value=command))
        return True, f"Added to {doc.path}"

    for module in tree.lua_modules.values():
        calls = [c for c in module.call_sites if c.dotted_name == "hl.exec_cmd"]
        if calls:
            module.insert_after_call(calls[-1], f"hl.exec_cmd({format_literal('string', command)})")
            return True, f"Added to {module.path}"

    return False, "No existing autostart entry found to add alongside — Knurl only adds new Lua statements next to a real existing one, to stay in the same scope."


def add_environment(tree, name: str, value: str) -> tuple[bool, str]:
    name = name.strip()
    value = value.strip()
    if not name:
        return False, "Enter a variable name first."

    if tree.hyprlang_docs:
        doc = max(tree.hyprlang_docs.values(), key=lambda d: len(d.root.find_all("env")))
        doc.root.children.append(KeyValue(key="env", value=f"{name},{value}"))
        return True, f"Added to {doc.path}"

    for module in tree.lua_modules.values():
        calls = [c for c in module.call_sites if c.dotted_name == "hl.env"]
        if calls:
            call_text = f"hl.env({format_literal('string', name)}, {format_literal('string', value)})"
            module.insert_after_call(calls[-1], call_text)
            return True, f"Added to {module.path}"

    return False, "No existing environment entry found to add alongside — Knurl only adds new Lua statements next to a real existing one, to stay in the same scope."


def list_monitors(tree) -> list[ListItem]:
    items: list[ListItem] = []
    for path, doc in tree.hyprlang_docs.items():
        for kv in doc.root.find_all("monitor"):
            items.append(ListItem(summary=kv.value, fields=[], source_file=path, editable=False, raw=kv.value))
    for path, module in tree.lua_modules.items():
        calls = [c for c in module.call_sites if c.dotted_name == "hl.monitor"]
        for i, call in enumerate(calls):
            if not call.args:
                continue
            table = call.args[0]
            if isinstance(table, TableValue):
                summary = ", ".join(f"{k}={v.value if isinstance(v, LiteralValue) else v.raw}" for k, v in table.fields.items())
                base = CallArg("hl.monitor", i, 0)
                fields = [
                    _literal_field(k, "", v, TableField(base, (k,)), module, path)
                    for k, v in table.fields.items()
                    if isinstance(v, LiteralValue)
                ]
                items.append(ListItem(summary=summary or "(monitor)", fields=fields, source_file=path, editable=bool(fields)))
    return items


def list_window_rules(tree) -> list[ListItem]:
    items: list[ListItem] = []
    for path, doc in tree.hyprlang_docs.items():
        for key in ("windowrule", "windowrulev2"):
            for kv in doc.root.find_all(key):
                items.append(_hyprlang_string_item(kv, path))
    for path, module in tree.lua_modules.items():
        for call in module.call_sites:
            if call.dotted_name != "hl.window_rule" or not call.args:
                continue
            table = call.args[0]
            if isinstance(table, TableValue):
                summary = "; ".join(f"{k}={_short(v)}" for k, v in table.fields.items())
                items.append(ListItem(summary=summary, fields=[], source_file=path, editable=False, raw=table.raw))
            else:
                items.append(ListItem(summary=table.raw if hasattr(table, "raw") else "(rule)", fields=[], source_file=path, editable=False))
    return items


_CAMEL_RE = re.compile(r"(?<!^)(?=[A-Z])")


def list_keybinds(tree) -> list[ListItem]:
    items: list[ListItem] = []
    for path, doc in tree.hyprlang_docs.items():
        for key in BIND_KEYS:
            for kv in doc.root.find_all(key):
                items.append(_hyprlang_string_item(kv, path, label=key))

    for path, module in tree.lua_modules.items():
        rt = module.return_table
        if rt is None:
            continue
        for name in rt.field_order:
            if not name.startswith("kb"):
                continue
            value = rt.fields[name]
            label = _CAMEL_RE.sub(" ", name[2:])
            if isinstance(value, LiteralValue):
                field = _literal_field(label, "Key combination for this action.", value, ReturnTableField(name), module, path)
                items.append(ListItem(summary=label, fields=[field], source_file=path, editable=True))
            elif isinstance(value, ArrayValue):
                base = ReturnTableField(name)
                fields = [
                    _literal_field(f"{label} (option {i + 1})", "", item, ArrayItem(base, i), module, path)
                    for i, item in enumerate(value.items)
                ]
                items.append(ListItem(summary=f"{label} ({len(value.items)} shortcuts)", fields=fields, source_file=path, editable=True))
    return items


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------


def _short(v) -> str:
    if isinstance(v, LiteralValue):
        return str(v.value)
    return getattr(v, "raw", str(v))


def _literal_field(label: str, description: str, value: LiteralValue, locator: Locator, module, path: str) -> BoundField:
    setter = make_setter(module, locator, value.kind)
    return BoundField(label, description, value.kind, value.value, path, True, (), "", setter)


def _hyprlang_string_item(kv: KeyValue, path: str, label: str | None = None) -> ListItem:
    def setter(new_value, kv=kv):
        kv.touch(str(new_value))

    field = BoundField(label or kv.key, "", "string", kv.value, path, True, (), "", setter)
    return ListItem(summary=kv.value, fields=[field], source_file=path, editable=True)


def _lua_single_item(value, locator: Locator, module, path: str, label: str) -> ListItem:
    if isinstance(value, LiteralValue):
        field = _literal_field(label, "", value, locator, module, path)
        return ListItem(summary=str(value.value), fields=[field], source_file=path, editable=True)
    return ListItem(summary=value.raw, fields=[], source_file=path, editable=False, raw=value.raw)


def build_categories(tree) -> list[Category]:
    scalars = build_scalar_categories(tree)
    categories = [Category(name, scalars.get(name, []), []) for name in ("Appearance", "Behavior", "Input")]
    categories.append(Category("Monitors", [], list_monitors(tree)))
    categories.append(Category("Keybinds", [], list_keybinds(tree)))
    categories.append(
        Category(
            "Autostart",
            [],
            list_autostart(tree),
            add_spec=AddSpec(["Command"], lambda cmd, tree=tree: add_autostart(tree, cmd)),
        )
    )
    categories.append(Category("Window Rules", [], list_window_rules(tree)))
    categories.append(
        Category(
            "Environment",
            [],
            list_environment(tree),
            add_spec=AddSpec(["Name", "Value"], lambda name, value, tree=tree: add_environment(tree, name, value)),
        )
    )
    return [c for c in categories if c.scalar_fields or c.list_items]
