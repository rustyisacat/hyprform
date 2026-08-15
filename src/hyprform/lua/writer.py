"""Formats a Python value back into Lua source syntax for a surgical edit."""

from __future__ import annotations


def format_literal(kind: str, value: object) -> str:
    if kind == "bool":
        return "true" if value else "false"
    if kind == "number":
        if isinstance(value, float) and value.is_integer():
            return repr(value)  # Lua distinguishes 5 from 5.0; keep the float form
        return repr(value) if isinstance(value, float) else str(value)
    if kind == "string":
        escaped = str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'
    raise ValueError(f"unknown literal kind: {kind!r}")
