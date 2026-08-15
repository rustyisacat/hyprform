"""Stable ways to re-find a value inside a LuaModule after it's been edited.

A ``Span`` captured at bind time is only valid until the *next* edit
anywhere in that same file — editing shifts every character offset after
it, so a second field's stale span would silently corrupt the file. A
locator instead re-walks the module's current (freshly re-parsed) call
sites / return table each time, so it's always valid no matter how many
other edits happened first.

This relies on one invariant: editing a literal's own text never changes
how many calls or table fields exist, or their order — it only replaces
that one value's characters. So "the Nth call to hl.env" or "the table
field named X" still means the same logical site after a reparse.
"""

from __future__ import annotations

from dataclasses import dataclass

from .values import TableValue


@dataclass(frozen=True)
class ReturnTableField:
    """A field of the module's top-level ``return { ... }`` table."""

    key: str

    def get(self, module):
        rt = module.return_table
        if rt is None or self.key not in rt.fields:
            raise KeyError(f"{self.key!r} not found in return table")
        return rt.fields[self.key]


@dataclass(frozen=True)
class ArrayItem:
    base: "Locator"
    index: int

    def get(self, module):
        arr = self.base.get(module)
        return arr.items[self.index]


@dataclass(frozen=True)
class CallArg:
    """The Nth argument of the Kth call to ``dotted_name`` in this module."""

    dotted_name: str
    call_index: int
    arg_index: int = 0

    def get(self, module):
        matches = [c for c in module.call_sites if c.dotted_name == self.dotted_name]
        return matches[self.call_index].args[self.arg_index]


@dataclass(frozen=True)
class TableField:
    base: "Locator"
    path: tuple[str, ...]

    def get(self, module):
        node = self.base.get(module)
        for key in self.path:
            if not isinstance(node, TableValue) or key not in node.fields:
                raise KeyError(f"path {self.path!r} not found")
            node = node.fields[key]
        return node


Locator = ReturnTableField | ArrayItem | CallArg | TableField


def make_setter(module, locator: Locator, kind: str):
    from .writer import format_literal

    def setter(new_value):
        value = locator.get(module)
        module.apply_edit(value.span, format_literal(kind, new_value))

    return setter
