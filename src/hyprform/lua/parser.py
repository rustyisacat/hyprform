"""Reads a Lua config file (Hyprland's native ``hl.*`` config style, or a
plain ``return { ... }`` module like ``variables.lua``) into the typed value
tree in :mod:`hyprform.lua.values`.

Only the safe, common subset is classified as editable: string/number/bool
literals, arrays of those, and tables of those (recursively). Everything
else — helper function definitions, loops, string concatenation, calls other
than the recognized ``hl.*`` ones — is left as an :class:`OpaqueValue` that
the GUI shows read-only. This is a deliberate scope limit: Hyprland's Lua
configs are full Lua, not a declarative format, so a tool that promised to
safely edit *any* construct would be lying.
"""

from __future__ import annotations

from luaparser import ast as last
from luaparser import astnodes as n

from .values import ArrayValue, CallSite, LiteralValue, OpaqueValue, Span, TableValue


def _span(node) -> Span:
    return Span(node._first_token.start, node._last_token.stop)


def _dotted_name(func_node) -> str | None:
    """``hl.config`` -> "hl.config"; a bare ``require`` -> "require"."""
    if isinstance(func_node, n.Name):
        return func_node.id
    if isinstance(func_node, n.Index) and func_node.notation == n.IndexNotation.DOT:
        base = _dotted_name(func_node.value)
        attr = func_node.idx.id if isinstance(func_node.idx, n.Name) else None
        if base is None or attr is None:
            return None
        return f"{base}.{attr}"
    return None


def classify(node, source: str):
    """Turn one piece of parsed Lua (a string, a number, a table, ...) into
    one of the typed values above, recursing into tables field by field.
    """
    if isinstance(node, n.String):
        raw_bytes = node.s
        text = raw_bytes.decode() if isinstance(raw_bytes, bytes) else raw_bytes
        return LiteralValue(kind="string", value=text, span=_span(node), raw=_span(node).slice(source))
    if isinstance(node, n.Number):
        return LiteralValue(kind="number", value=node.n, span=_span(node), raw=_span(node).slice(source))
    if isinstance(node, n.TrueExpr):
        return LiteralValue(kind="bool", value=True, span=_span(node), raw=_span(node).slice(source))
    if isinstance(node, n.FalseExpr):
        return LiteralValue(kind="bool", value=False, span=_span(node), raw=_span(node).slice(source))
    if isinstance(node, n.Table):
        return classify_table(node, source)
    return OpaqueValue(raw=_span(node).slice(source), span=_span(node))


def classify_table(node: n.Table, source: str):
    """A Table is an ArrayValue if every field is a plain literal with no
    explicit key (Lua array-style), otherwise a TableValue (dict-style),
    falling back to OpaqueValue per-field for anything unclassifiable.
    """
    fields = node.fields
    all_array_literals = fields and all(
        f.key is None and isinstance(classify(f.value, source), LiteralValue) for f in fields
    )
    if all_array_literals:
        items = [classify(f.value, source) for f in fields]
        return ArrayValue(items=items, span=_span(node), raw=_span(node).slice(source))

    table = TableValue(span=_span(node), raw=_span(node).slice(source))
    for f in fields:
        if f.key is None:
            key = f"[{len(table.field_order)}]"
        elif isinstance(f.key, n.Name):
            key = f.key.id
        elif isinstance(f.key, n.String):
            raw_bytes = f.key.s
            key = raw_bytes.decode() if isinstance(raw_bytes, bytes) else raw_bytes
        else:
            key = _span(f.key).slice(source)
        table.fields[key] = classify(f.value, source)
        table.field_order.append(key)
    return table


def find_call_sites(tree, source: str, names: set[str] | None = None) -> list[CallSite]:
    """Find every ``Call`` node in the tree, optionally filtered to a set of
    dotted names (e.g. ``{"hl.config", "hl.env"}``). Order matches source order.
    """
    sites: list[CallSite] = []

    def walk(node):
        # Recursively visits every node in the parsed file (function bodies,
        # table contents, if-blocks, everything) looking for Call nodes,
        # since a hl.config(...) call could be nested arbitrarily deep.
        if isinstance(node, n.Call):
            dotted = _dotted_name(node.func)
            if dotted is not None and (names is None or dotted in names):
                args = [classify(a, source) for a in node.args]
                sites.append(CallSite(dotted_name=dotted, args=args, span=_span(node), line=node.func._first_token.line))
        if hasattr(node, "__dict__"):
            for key, v in vars(node).items():
                if key.startswith("_") or key == "comments":
                    continue
                if isinstance(v, list):
                    for item in v:
                        if hasattr(item, "__dict__"):
                            walk(item)
                elif hasattr(v, "__dict__"):
                    walk(v)

    walk(tree)
    sites.sort(key=lambda c: c.span.start)
    return sites


def find_return_table(tree, source: str) -> TableValue | None:
    """For ``variables.lua``-style modules: the table in the file's top-level
    ``return { ... }`` statement, if any.
    """
    body = tree.body.body if hasattr(tree.body, "body") else tree.body
    for stmt in body:
        if isinstance(stmt, n.Return) and stmt.values:
            value = stmt.values[0]
            if isinstance(value, n.Table):
                return classify_table(value, source)
    return None


class LuaModule:
    """A parsed Lua file: source text + tree + the call sites and top-level
    return table hyprform knows how to edit.
    """

    RECOGNIZED_CALLS = {
        "hl.config",
        "hl.env",
        "hl.exec_cmd",
        "hl.window_rule",
        "hl.monitor",
        "hl.bind",
    }

    def __init__(self, source: str, path: str = "<memory>"):
        self.source = source
        self.path = path
        self.tree = last.parse(source)
        self.call_sites = find_call_sites(self.tree, source, self.RECOGNIZED_CALLS)
        self.return_table = find_return_table(self.tree, source)

    def apply_edit(self, span: Span, new_text: str) -> None:
        """Surgically replace one value's source range and re-parse, so
        subsequent spans stay valid for further edits in the same session.
        """
        self.source = self.source[: span.start] + new_text + self.source[span.stop + 1 :]
        self._reparse()

    def insert_after_call(self, call: CallSite, statement: str) -> None:
        """Insert a brand-new statement right after an existing call, at
        the same indentation. This is the only structurally safe way to add
        new Lua code without understanding arbitrary scoping: a new
        sibling statement next to a real existing one is guaranteed to run
        in the same context (e.g. inside the same ``hl.on(...)`` handler),
        which blindly appending at end-of-file is not.
        """
        line_start = self.source.rfind("\n", 0, call.span.start) + 1
        indent = self.source[line_start : call.span.start]
        indent = indent[: len(indent) - len(indent.lstrip())]
        insertion = f"\n{indent}{statement}"
        self.source = self.source[: call.span.stop + 1] + insertion + self.source[call.span.stop + 1 :]
        self._reparse()

    def _reparse(self) -> None:
        self.tree = last.parse(self.source)
        self.call_sites = find_call_sites(self.tree, self.source, self.RECOGNIZED_CALLS)
        self.return_table = find_return_table(self.tree, self.source)
