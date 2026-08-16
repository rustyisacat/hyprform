"""Parses and formats the color syntaxes Hyprland actually uses in its
config, so a color picker widget can round-trip a value without silently
changing its meaning.

Only single, flat colors are handled. Hyprland border colors are frequently
*gradients* (``rgba(...) rgba(...) 45deg``) — those are intentionally left
alone (``parse_color`` returns ``None``) so the GUI falls back to plain text
editing instead of a picker that would only ever show/set one stop of a
multi-stop gradient.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_RGBA_RE = re.compile(r"^rgba\(\s*([0-9a-fA-F]{8})\s*\)$")
_RGB_RE = re.compile(r"^rgb\(\s*([0-9a-fA-F]{6})\s*\)$")
_HEX0X_RE = re.compile(r"^0x([0-9a-fA-F]{8})$")
_HASH_RE = re.compile(r"^#([0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


@dataclass(frozen=True)
class ParsedColor:
    r: float
    g: float
    b: float
    a: float
    style: str  # "rgba" | "rgb" | "0x" | "hash6" | "hash8"


def parse_color(raw: str) -> ParsedColor | None:
    """Parses a *single* flat color. Returns None for anything else (a
    gradient, an unrecognized format, or extra surrounding text) so callers
    can fall back to a plain text field rather than risk misrepresenting it.
    """
    text = raw.strip()

    m = _RGBA_RE.match(text)
    if m:
        r, g, b, a = _split_hex(m.group(1), 4)
        return ParsedColor(r, g, b, a, "rgba")

    m = _RGB_RE.match(text)
    if m:
        r, g, b = _split_hex(m.group(1), 3)
        return ParsedColor(r, g, b, 1.0, "rgb")

    m = _HEX0X_RE.match(text)
    if m:
        # Unlike every other format here, Hyprland's 0x style puts the alpha
        # (transparency) digits *first*, e.g. 0xAARRGGBB, not last.
        a, r, g, b = _split_hex(m.group(1), 4)
        return ParsedColor(r, g, b, a, "0x")

    m = _HASH_RE.match(text)
    if m:
        digits = m.group(1)
        if len(digits) == 8:
            r, g, b, a = _split_hex(digits, 4)
            return ParsedColor(r, g, b, a, "hash8")
        r, g, b = _split_hex(digits, 3)
        return ParsedColor(r, g, b, 1.0, "hash6")

    return None


def format_color(r: float, g: float, b: float, a: float, style: str) -> str:
    """Writes back (r, g, b, a) in [0, 1] using the same syntax style the
    original value used, so editing a color never changes its notation.
    """
    rr, gg, bb, aa = (_to_hex(v) for v in (r, g, b, a))
    if style == "rgba":
        return f"rgba({rr}{gg}{bb}{aa})"
    if style == "rgb":
        return f"rgb({rr}{gg}{bb})"
    if style == "0x":
        return f"0x{aa}{rr}{gg}{bb}"
    if style == "hash8":
        return f"#{rr}{gg}{bb}{aa}"
    if style == "hash6":
        return f"#{rr}{gg}{bb}"
    raise ValueError(f"unknown color style: {style!r}")


def _split_hex(digits: str, channels: int) -> tuple[float, ...]:
    pairs = [digits[i : i + 2] for i in range(0, channels * 2, 2)]
    return tuple(int(p, 16) / 255 for p in pairs)


def _to_hex(value: float) -> str:
    clamped = max(0.0, min(1.0, value))
    return f"{round(clamped * 255):02x}"
