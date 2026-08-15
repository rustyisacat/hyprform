"""Plain-English metadata for the common hyprlang scalar settings.

Hyprland's own Lua config API (``hl.config({ general = {...}, ... })``)
deliberately mirrors hyprlang's section/key structure, so a single
``(section, key)`` schema works for both formats — the binder just looks the
pair up in whichever representation the user's config actually uses.

This is not an exhaustive mirror of every hyprlang option (there are
hundreds); it covers what people actually reach for when tweaking the look
and feel of their setup. Anything not listed here still shows up in the
"Advanced" raw view, untouched.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldSpec:
    section: str
    key: str
    label: str
    description: str
    kind: str  # "bool" | "number" | "float" | "string" | "choice"
    category: str
    choices: tuple[str, ...] = ()
    unit: str = ""


FIELDS: list[FieldSpec] = [
    # --- Appearance: spacing & borders ---
    FieldSpec("general", "gaps_in", "Gap between windows", "Space left between windows that are next to each other.", "number", "Appearance", unit="px"),
    FieldSpec("general", "gaps_out", "Gap around screen edge", "Space left between windows and the edge of the screen.", "number", "Appearance", unit="px"),
    FieldSpec("general", "border_size", "Border thickness", "Thickness of the colored line drawn around each window.", "number", "Appearance", unit="px"),
    FieldSpec("general", "layout", "Window layout style", "How new windows are automatically arranged on screen.", "choice", "Appearance", choices=("dwindle", "master")),
    FieldSpec("general", "resize_on_border", "Resize by dragging window edges", "Lets you resize a window by clicking and dragging near its edge, not just the border line.", "bool", "Appearance"),
    FieldSpec("general", "allow_tearing", "Allow screen tearing", "Lets fullscreen apps (mainly games) skip a sync step for lower input lag, at the cost of possible visual tearing.", "bool", "Appearance"),
    # --- Appearance: decoration ---
    FieldSpec("decoration", "rounding", "Rounded corners", "How rounded window corners are.", "number", "Appearance", unit="px"),
    FieldSpec("decoration", "active_opacity", "Focused window opacity", "How see-through the currently focused window is.", "float", "Appearance"),
    FieldSpec("decoration", "inactive_opacity", "Unfocused window opacity", "How see-through windows are when they're not focused.", "float", "Appearance"),
    FieldSpec("decoration.blur", "enabled", "Background blur", "Blurs whatever is behind transparent windows and panels.", "bool", "Appearance"),
    FieldSpec("decoration.blur", "size", "Blur strength", "How strong the background blur effect is.", "number", "Appearance"),
    FieldSpec("decoration.blur", "passes", "Blur quality passes", "How many times the blur is applied — higher looks smoother but costs more performance.", "number", "Appearance"),
    FieldSpec("decoration.shadow", "enabled", "Window drop shadow", "Draws a soft shadow behind each window.", "bool", "Appearance"),
    FieldSpec("decoration.shadow", "range", "Shadow size", "How far the drop shadow spreads out from the window.", "number", "Appearance", unit="px"),
    # --- Appearance: animations ---
    FieldSpec("animations", "enabled", "Enable animations", "Turns on smooth motion for opening/closing/moving windows and workspaces.", "bool", "Appearance"),
    # --- Behavior: general ---
    FieldSpec("general", "no_focus_fallback", "Don't refocus when a window closes", "Normally Hyprland focuses another window automatically when the focused one closes; this turns that off.", "bool", "Behavior"),
    FieldSpec("misc", "disable_hyprland_logo", "Hide Hyprland logo on empty workspace", "Removes the background logo shown when a workspace has no windows.", "bool", "Behavior"),
    FieldSpec("misc", "disable_splash_rendering", "Hide startup splash text", "Removes the small splash text shown alongside the logo.", "bool", "Behavior"),
    FieldSpec("misc", "mouse_move_enables_dpms", "Wake screen on mouse move", "Turns the display back on when you move the mouse, if it was asleep.", "bool", "Behavior"),
    FieldSpec("misc", "key_press_enables_dpms", "Wake screen on key press", "Turns the display back on when you press a key, if it was asleep.", "bool", "Behavior"),
    FieldSpec("misc", "vfr", "Variable refresh rate (power saving)", "Reduces GPU work when nothing on screen is changing. Recommended on.", "bool", "Behavior"),
    FieldSpec("misc", "vrr", "Adaptive sync (VRR)", "Lets your monitor's refresh rate match the frame rate to reduce stutter, if your display supports it.", "choice", "Behavior", choices=("0", "1", "2")),
    # --- Input ---
    FieldSpec("input", "kb_layout", "Keyboard layout", "Which keyboard layout to use (e.g. 'us', 'gb', 'de').", "string", "Input"),
    FieldSpec("input", "numlock_by_default", "Turn on Num Lock at startup", "Enables the numeric keypad automatically when you log in.", "bool", "Input"),
    FieldSpec("input", "repeat_rate", "Key repeat speed", "How many times per second a held-down key repeats.", "number", "Input"),
    FieldSpec("input", "repeat_delay", "Key repeat delay", "How long a key must be held before it starts repeating.", "number", "Input", unit="ms"),
    FieldSpec("input.touchpad", "natural_scroll", "Natural (reversed) scrolling", "Makes touchpad scrolling move content the same direction as your fingers, like on a phone.", "bool", "Input"),
    FieldSpec("input.touchpad", "disable_while_typing", "Disable touchpad while typing", "Ignores touchpad input for a moment after you press a key, to prevent accidental taps.", "bool", "Input"),
    FieldSpec("input.touchpad", "tap-to-click", "Tap to click", "Lets you tap the touchpad instead of pressing it down to click.", "bool", "Input"),
    FieldSpec("input.touchpad", "scroll_factor", "Touchpad scroll speed", "Multiplier for how fast touchpad scrolling moves.", "float", "Input"),
    FieldSpec("gestures", "workspace_swipe", "Swipe between workspaces", "Lets you switch workspaces by swiping on the touchpad.", "bool", "Input"),
    FieldSpec("gestures", "workspace_swipe_fingers", "Fingers needed to swipe workspaces", "Number of fingers required for the workspace-switch swipe gesture.", "number", "Input"),
]


def lookup(section: str, key: str) -> FieldSpec | None:
    for spec in FIELDS:
        if spec.section == section and spec.key == key:
            return spec
    return None


CATEGORIES = ["Appearance", "Behavior", "Input"]
