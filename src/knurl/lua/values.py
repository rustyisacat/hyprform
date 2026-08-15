"""Typed, editable representations of values found inside a parsed Lua file.

Every value knows the exact (start, stop) character range it occupies in the
original source (inclusive, from luaparser's antlr tokens), so an edit can be
applied as a surgical substring replacement instead of a full regeneration —
anything the classifier doesn't understand is left completely untouched.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Span:
    start: int
    stop: int  # inclusive

    def slice(self, source: str) -> str:
        return source[self.start : self.stop + 1]


@dataclass
class LiteralValue:
    """A string, number, or boolean literal — safe to edit via a form field."""

    kind: str  # "string" | "number" | "bool"
    value: object
    span: Span
    raw: str


@dataclass
class ArrayValue:
    """A ``{ "a", "b" }`` style array of literals — safe to edit as a list."""

    items: list[LiteralValue]
    span: Span
    raw: str


@dataclass
class TableValue:
    """A ``{ key = value, ... }`` table — fields recurse, in source order."""

    fields: dict[str, "AnyValue"] = field(default_factory=dict)
    field_order: list[str] = field(default_factory=list)
    span: Span | None = None
    raw: str = ""


@dataclass
class OpaqueValue:
    """Anything not classified above: a Name/Index reference (``vars.foo``),
    a string concatenation, a function call, etc. Shown read-only in the GUI
    with its source text — never edited via a form, only via the raw view.
    """

    raw: str
    span: Span
    reason: str = "expression"


AnyValue = LiteralValue | ArrayValue | TableValue | OpaqueValue


@dataclass
class CallSite:
    """A recognized ``hl.xxx(...)`` (or bare ``xxx(...)``) call."""

    dotted_name: str
    args: list[AnyValue]
    span: Span
    line: int
