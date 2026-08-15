"""Parser for Hyprland's hyprlang (.conf) format.

Handles: blank lines, ``# comment`` lines, ``key = value`` pairs (including
repeatable keys like ``bind``/``monitor``/``exec-once``/``env``/``source``),
and ``name {`` ... ``}`` blocks (which may nest, e.g. ``decoration { blur {`` ).

This is intentionally line-oriented rather than a full hyprlang-grammar
parser: hyprlang itself has no expressions, just line-shaped statements, and
staying line-oriented is what lets untouched lines round-trip exactly.
"""

from __future__ import annotations

import re

from .model import Blank, Block, Comment, Document, KeyValue

_BLOCK_OPEN_RE = re.compile(r"^(?P<indent>\s*)(?P<name>[A-Za-z0-9_.:]+)\s*\{\s*$")
_BLOCK_CLOSE_RE = re.compile(r"^(?P<indent>\s*)\}\s*$")
_COMMENT_RE = re.compile(r"^\s*#")
_KV_RE = re.compile(r"^(?P<indent>\s*)(?P<key>[A-Za-z0-9_.:\-]+)\s*=\s*(?P<value>.*)$")


class HyprlangParseError(ValueError):
    def __init__(self, line_no: int, line: str, message: str):
        super().__init__(f"line {line_no}: {message}: {line!r}")
        self.line_no = line_no
        self.line = line


def parse(text: str, path: str = "<memory>") -> Document:
    lines = text.split("\n")
    # split() on the final newline leaves a trailing "" element; drop it so we
    # don't synthesize a phantom blank line, but remember whether it was there
    # so the writer can restore it.
    trailing_newline = text.endswith("\n")
    if trailing_newline and lines and lines[-1] == "":
        lines = lines[:-1]

    root = Block(name="<root>")
    stack: list[Block] = [root]

    for line_no, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()

        if stripped == "":
            stack[-1].children.append(Blank())
            continue

        if _COMMENT_RE.match(raw_line):
            stack[-1].children.append(Comment(text=stripped.lstrip("#").strip(), raw_line=raw_line))
            continue

        m = _BLOCK_CLOSE_RE.match(raw_line)
        if m:
            if len(stack) == 1:
                raise HyprlangParseError(line_no, raw_line, "unmatched closing brace")
            closed = stack.pop()
            closed.raw_footer = raw_line
            continue

        m = _BLOCK_OPEN_RE.match(raw_line)
        if m:
            block = Block(name=m.group("name"), indent=m.group("indent"), raw_header=raw_line)
            stack[-1].children.append(block)
            stack.append(block)
            continue

        m = _KV_RE.match(raw_line)
        if m:
            kv = KeyValue(
                key=m.group("key"),
                value=m.group("value").rstrip(),
                indent=m.group("indent"),
                raw_line=raw_line,
            )
            stack[-1].children.append(kv)
            continue

        raise HyprlangParseError(line_no, raw_line, "unrecognized line")

    if len(stack) != 1:
        raise HyprlangParseError(len(lines), lines[-1] if lines else "", "unclosed block(s) at end of file")

    doc = Document(path=path, root=root)
    doc.trailing_newline = trailing_newline  # type: ignore[attr-defined]
    return doc
