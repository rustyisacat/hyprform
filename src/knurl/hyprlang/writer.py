"""Serializes a hyprlang Document back to text.

Any node that still has its original ``raw_line``/``raw_header``/
``raw_footer`` is emitted verbatim. Edited or newly-added nodes are
regenerated from their structured fields — so a diff against the original
file only ever touches the lines that actually changed.
"""

from __future__ import annotations

from .model import Blank, Block, Comment, Document, KeyValue

DEFAULT_INDENT = "    "


def _emit_kv(kv: KeyValue) -> str:
    if kv.raw_line is not None:
        return kv.raw_line
    return f"{kv.indent}{kv.key} = {kv.value}"


def _emit_block(block: Block, depth: int) -> list[str]:
    lines: list[str] = []
    indent = block.indent or (DEFAULT_INDENT * depth if depth else "")

    if block.name != "<root>":
        lines.append(block.raw_header if block.raw_header is not None else f"{indent}{block.name} {{")

    child_indent_hint = "" if block.name == "<root>" else DEFAULT_INDENT * (depth + 1)
    for child in block.children:
        if isinstance(child, Blank):
            lines.append("")
        elif isinstance(child, Comment):
            lines.append(child.raw_line if child.raw_line is not None else f"{child_indent_hint}# {child.text}")
        elif isinstance(child, KeyValue):
            if child.raw_line is None and not child.indent:
                child.indent = child_indent_hint
            lines.append(_emit_kv(child))
        elif isinstance(child, Block):
            lines.extend(_emit_block(child, depth + 1))
        else:  # pragma: no cover - defensive
            raise TypeError(f"unknown node type: {type(child)!r}")

    if block.name != "<root>":
        lines.append(block.raw_footer if block.raw_footer is not None else f"{indent}}}")

    return lines


def serialize(doc: Document) -> str:
    lines = _emit_block(doc.root, depth=0)
    text = "\n".join(lines)
    trailing_newline = getattr(doc, "trailing_newline", True)
    return text + ("\n" if trailing_newline and not text.endswith("\n") else "")
