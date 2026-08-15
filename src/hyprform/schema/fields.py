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
    FieldSpec("general", "no_border_on_floating", "No border on floating windows", "Hides the colored border outline specifically on floating (non-tiled) windows.", "bool", "Appearance"),
    FieldSpec("general", "col.active_border", "Focused window border color", "Color (or gradient) of the border around the currently focused window.", "string", "Appearance"),
    FieldSpec("general", "col.inactive_border", "Unfocused window border color", "Color of the border around windows that aren't focused.", "string", "Appearance"),
    FieldSpec("general.snap", "enabled", "Snap windows to edges", "Lets floating windows snap into place near screen edges and other windows while dragging.", "bool", "Appearance"),
    FieldSpec("general.snap", "window_gap", "Snap distance", "How close a window's edge has to get to another before it snaps.", "number", "Appearance", unit="px"),
    # --- Appearance: decoration ---
    FieldSpec("decoration", "rounding", "Rounded corners", "How rounded window corners are.", "number", "Appearance", unit="px"),
    FieldSpec("decoration", "active_opacity", "Focused window opacity", "How see-through the currently focused window is.", "float", "Appearance"),
    FieldSpec("decoration", "inactive_opacity", "Unfocused window opacity", "How see-through windows are when they're not focused.", "float", "Appearance"),
    FieldSpec("decoration", "dim_inactive", "Dim unfocused windows", "Darkens windows that aren't currently focused, to make the active one stand out.", "bool", "Appearance"),
    FieldSpec("decoration", "dim_strength", "Dim strength", "How much unfocused windows are darkened, from 0 (none) to 1 (fully dark).", "float", "Appearance"),
    FieldSpec("decoration.blur", "enabled", "Background blur", "Blurs whatever is behind transparent windows and panels.", "bool", "Appearance"),
    FieldSpec("decoration.blur", "size", "Blur strength", "How strong the background blur effect is.", "number", "Appearance"),
    FieldSpec("decoration.blur", "passes", "Blur quality passes", "How many times the blur is applied — higher looks smoother but costs more performance.", "number", "Appearance"),
    FieldSpec("decoration.blur", "contrast", "Blur contrast", "Adjusts contrast in the blurred area.", "float", "Appearance"),
    FieldSpec("decoration.blur", "brightness", "Blur brightness", "Adjusts brightness in the blurred area.", "float", "Appearance"),
    FieldSpec("decoration.blur", "vibrancy", "Blur vibrancy", "Boosts color saturation in the blurred area.", "float", "Appearance"),
    FieldSpec("decoration.blur", "noise", "Blur noise", "Adds a subtle grain to the blur to reduce color banding.", "float", "Appearance"),
    FieldSpec("decoration.blur", "xray", "Blur through all layers at once", "Blurs straight through to the desktop background instead of layering blur between each window.", "bool", "Appearance"),
    FieldSpec("decoration.shadow", "enabled", "Window drop shadow", "Draws a soft shadow behind each window.", "bool", "Appearance"),
    FieldSpec("decoration.shadow", "range", "Shadow size", "How far the drop shadow spreads out from the window.", "number", "Appearance", unit="px"),
    FieldSpec("decoration.shadow", "render_power", "Shadow softness", "How soft/feathered the shadow's edge looks, from 1 (sharp) to 4 (very soft).", "number", "Appearance"),
    FieldSpec("decoration.shadow", "color", "Shadow color", "Color of the drop shadow, as a hex value (e.g. 0xee1a1a1a).", "string", "Appearance"),
    # --- Appearance: animations ---
    FieldSpec("animations", "enabled", "Enable animations", "Turns on smooth motion for opening/closing/moving windows and workspaces.", "bool", "Appearance"),
    FieldSpec("animations", "first_launch_animation", "Startup animation", "Plays an animation the very first time Hyprland's desktop appears after login.", "bool", "Appearance"),
    # --- Behavior: general ---
    FieldSpec("general", "no_focus_fallback", "Don't refocus when a window closes", "Normally Hyprland focuses another window automatically when the focused one closes; this turns that off.", "bool", "Behavior"),
    FieldSpec("misc", "disable_hyprland_logo", "Hide Hyprland logo on empty workspace", "Removes the background logo shown when a workspace has no windows.", "bool", "Behavior"),
    FieldSpec("misc", "disable_splash_rendering", "Hide startup splash text", "Removes the small splash text shown alongside the logo.", "bool", "Behavior"),
    FieldSpec("misc", "mouse_move_enables_dpms", "Wake screen on mouse move", "Turns the display back on when you move the mouse, if it was asleep.", "bool", "Behavior"),
    FieldSpec("misc", "key_press_enables_dpms", "Wake screen on key press", "Turns the display back on when you press a key, if it was asleep.", "bool", "Behavior"),
    FieldSpec("misc", "vfr", "Variable refresh rate (power saving)", "Reduces GPU work when nothing on screen is changing. Recommended on.", "bool", "Behavior"),
    FieldSpec("misc", "vrr", "Adaptive sync (VRR)", "Lets your monitor's refresh rate match the frame rate to reduce stutter, if your display supports it.", "choice", "Behavior", choices=("0", "1", "2")),
    FieldSpec("misc", "focus_on_activate", "Focus windows that request attention", "Switches focus to a window automatically when it asks for it (e.g. a finished download), instead of just flashing an indicator.", "bool", "Behavior"),
    FieldSpec("misc", "animate_manual_resizes", "Animate manual resizing", "Smoothly animates a window while you're actively dragging its edge to resize it.", "bool", "Behavior"),
    FieldSpec("misc", "animate_mouse_windowdragging", "Animate window dragging", "Smoothly animates a window while you're dragging it around with the mouse.", "bool", "Behavior"),
    FieldSpec("misc", "enable_swallow", "Enable terminal swallowing", "Hides a terminal window behind the app you launch from it (e.g. launching an image viewer from a file manager run in-terminal).", "bool", "Behavior"),
    FieldSpec("misc", "new_window_takes_over_fullscreen", "New window vs. fullscreen window", "What happens when a new window opens while another is fullscreen: 0 keeps focus, 1 takes over, 2 opens behind it.", "choice", "Behavior", choices=("0", "1", "2")),
    FieldSpec("misc", "close_special_on_empty", "Close special workspace when emptied", "Automatically closes a special (scratchpad-style) workspace once its last window is gone.", "bool", "Behavior"),
    FieldSpec("misc", "exit_window_retains_fullscreen", "Keep next window fullscreen after closing one", "If a fullscreen window closes, the next window that gets focus stays fullscreen instead of exiting it.", "bool", "Behavior"),
    FieldSpec("xwayland", "enabled", "Enable X11 app support (XWayland)", "Lets older X11-only apps run alongside native Wayland ones. Turning this off saves resources if you never run X11 apps.", "bool", "Behavior"),
    FieldSpec("xwayland", "force_zero_scaling", "Force X11 apps to 1x scaling", "Stops XWayland apps from being scaled by the compositor, useful if X11 apps look blurry on HiDPI screens.", "bool", "Behavior"),
    # --- Behavior: window arrangement (dwindle / master layouts) ---
    FieldSpec("dwindle", "pseudotile", "Allow pseudo-tiling", "Lets a tiled window keep its natural size within its tile instead of being stretched to fill it exactly.", "bool", "Behavior"),
    FieldSpec("dwindle", "preserve_split", "Preserve split direction", "Keeps the dwindle layout's split direction fixed instead of recalculating it every time a window opens/closes.", "bool", "Behavior"),
    FieldSpec("dwindle", "force_split", "Force split side", "Forces new windows to always split to one side: 0 follows the cursor, 1 always left/top, 2 always right/bottom.", "choice", "Behavior", choices=("0", "1", "2")),
    FieldSpec("dwindle", "smart_split", "Smart split", "Changes the split direction based on where you drop the window relative to its neighbor.", "bool", "Behavior"),
    FieldSpec("dwindle", "smart_resizing", "Smart resizing", "Resizing a window resizes just that window's side of the split rather than the whole layout.", "bool", "Behavior"),
    FieldSpec("master", "new_status", "New window role in master layout", "Whether a newly opened window becomes the master window, a slave, or inherits the role of the window it split from.", "choice", "Behavior", choices=("master", "slave", "inherit")),
    FieldSpec("master", "new_on_top", "Add new windows above master", "Puts newly opened windows at the top of the stack instead of the bottom.", "bool", "Behavior"),
    FieldSpec("master", "mfact", "Master area size", "How much of the screen the master window takes up, from 0 to 1.", "float", "Behavior"),
    # --- Input ---
    FieldSpec("input", "kb_layout", "Keyboard layout", "Which keyboard layout to use (e.g. 'us', 'gb', 'de').", "string", "Input"),
    FieldSpec("input", "numlock_by_default", "Turn on Num Lock at startup", "Enables the numeric keypad automatically when you log in.", "bool", "Input"),
    FieldSpec("input", "repeat_rate", "Key repeat speed", "How many times per second a held-down key repeats.", "number", "Input"),
    FieldSpec("input", "repeat_delay", "Key repeat delay", "How long a key must be held before it starts repeating.", "number", "Input", unit="ms"),
    FieldSpec("input", "sensitivity", "Mouse sensitivity", "Adjusts pointer speed, from -1 (slowest) to 1 (fastest). 0 is the default speed.", "float", "Input"),
    FieldSpec("input", "accel_profile", "Mouse acceleration profile", "How pointer speed scales with how fast you physically move the mouse ('flat' or 'adaptive'). Leave blank for the driver default.", "string", "Input"),
    FieldSpec("input", "follow_mouse", "Focus follows mouse", "Whether moving the mouse over a window focuses it: 0 always, 1 only if it changes window, 2 only when clicked, 3 never.", "choice", "Input", choices=("0", "1", "2", "3")),
    FieldSpec("input", "float_switch_override_focus", "Floating window click-through focus", "Whether clicking a tiled window through a floating one changes focus: 0 never, 1 always, 2 only if the floating window isn't hovered.", "choice", "Input", choices=("0", "1", "2")),
    FieldSpec("input.touchpad", "natural_scroll", "Natural (reversed) scrolling", "Makes touchpad scrolling move content the same direction as your fingers, like on a phone.", "bool", "Input"),
    FieldSpec("input.touchpad", "disable_while_typing", "Disable touchpad while typing", "Ignores touchpad input for a moment after you press a key, to prevent accidental taps.", "bool", "Input"),
    FieldSpec("input.touchpad", "tap-to-click", "Tap to click", "Lets you tap the touchpad instead of pressing it down to click.", "bool", "Input"),
    FieldSpec("input.touchpad", "scroll_factor", "Touchpad scroll speed", "Multiplier for how fast touchpad scrolling moves.", "float", "Input"),
    FieldSpec("input.touchpad", "middle_button_emulation", "Middle-click via two-finger tap", "Emulates a middle mouse button click when you tap the touchpad with two fingers.", "bool", "Input"),
    FieldSpec("gestures", "workspace_swipe", "Swipe between workspaces", "Lets you switch workspaces by swiping on the touchpad.", "bool", "Input"),
    FieldSpec("gestures", "workspace_swipe_fingers", "Fingers needed to swipe workspaces", "Number of fingers required for the workspace-switch swipe gesture.", "number", "Input"),
    FieldSpec("gestures", "workspace_swipe_distance", "Swipe distance", "How far you need to swipe (in pixels) to complete a workspace switch.", "number", "Input", unit="px"),
    FieldSpec("gestures", "workspace_swipe_invert", "Invert swipe direction", "Reverses which way you swipe to move to the next/previous workspace.", "bool", "Input"),
    FieldSpec("gestures", "workspace_swipe_min_speed_to_force", "Minimum flick speed to force-switch", "A fast enough swipe below the full distance still completes the switch if it's at least this speed.", "number", "Input"),
    # --- Cursor ---
    FieldSpec("cursor", "no_hardware_cursors", "Hardware cursor mode", "Whether the cursor is drawn by the GPU's hardware cursor plane. Auto works for most setups; force off/on if the cursor flickers or disappears.", "choice", "Cursor", choices=("-1", "0", "1")),
    FieldSpec("cursor", "inactive_timeout", "Hide cursor after inactivity", "Hides the cursor after this many seconds of no mouse movement. 0 disables auto-hide.", "float", "Cursor", unit="s"),
    FieldSpec("cursor", "hide_on_key_press", "Hide cursor while typing", "Hides the cursor as soon as you press a key, until you move the mouse again.", "bool", "Cursor"),
    FieldSpec("cursor", "hide_on_touch", "Hide cursor on touchscreen input", "Hides the mouse cursor when you use a touchscreen instead.", "bool", "Cursor"),
    FieldSpec("cursor", "default_monitor", "Cursor's home monitor", "Which monitor the cursor starts on at launch. Leave blank to let Hyprland decide.", "string", "Cursor"),
    FieldSpec("cursor", "zoom_factor", "Cursor zoom", "Magnifies everything around the cursor by this factor. 1 is normal size.", "float", "Cursor"),
]


def lookup(section: str, key: str) -> FieldSpec | None:
    for spec in FIELDS:
        if spec.section == section and spec.key == key:
            return spec
    return None


CATEGORIES = ["Appearance", "Behavior", "Input", "Cursor"]
