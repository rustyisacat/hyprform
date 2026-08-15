# Hyprform

![Platform](https://img.shields.io/badge/platform-Hyprland-58E1FF?logo=linux&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![GTK4](https://img.shields.io/badge/UI-GTK4%20%2B%20libadwaita-4A86CF?logo=gtk&logoColor=white)
![Version](https://img.shields.io/badge/version-0.1.0-blue)
![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)

A GUI for editing Hyprland's config. No nano, no learning hyprlang or Lua syntax.

Hyprland configs come in two shapes these days: the classic `hyprland.conf`
(hyprlang: `key = value` and `block { ... }`), and, on newer installs
(Hyprland ≥0.55), a native Lua config
(`hyprland.lua` calling `hl.config({...})`, `hl.bind()`, `hl.env()`, etc.).
Hyprform reads both, follows `source =` / `require(...)` across however many
files your config is split into, and gives you plain-English forms instead
of either syntax.

## What it covers

- **Appearance** — gaps, border thickness and color, snap-to-edge, rounding,
  opacity, dimming, full blur tuning (strength, passes, contrast,
  brightness, vibrancy, noise, xray), shadow (size, softness, color),
  animations
- **Behavior** — DPMS wake, splash/logo, VRR, focus-on-activate, manual
  resize/drag animation, terminal swallowing, fullscreen handling, XWayland,
  and dwindle/master layout tuning (pseudotile, split behavior, master
  ratio)
- **Input** — keyboard layout/repeat, mouse sensitivity and acceleration,
  focus-follows-mouse, touchpad gestures and swipe tuning
- **Cursor** — hardware cursor mode, auto-hide on idle/typing/touch,
  per-monitor default, zoom
- **Monitors, Keybinds, Autostart, Window Rules, Environment** — the
  repeatable-entry parts of your config, shown as lists

## What it deliberately doesn't try to do

Hyprland's Lua config is *real Lua* — full programs, not just settings.
Hyprform only edits values it can prove are safe: plain literals (strings,
numbers, booleans) and arrays/tables of those. Anything built by a loop,
helper function, or string concatenation is shown read-only with its actual
source text, not silently guessed at. A field that's a reference to a shared
variable (e.g. `vars.windowGapsIn`) is resolved and edited at its real
source — most Caelestia-style setups keep the actual tunable values in one
`variables.lua`, so this is what makes editing those configs useful at all.

Every edit is a surgical text replacement — untouched lines in your config
never move or reformat. Every save writes a timestamped backup
(`<file>.hyprform-bak-<timestamp>`) alongside the original before touching it.

## Install

```
uv tool install --editable .
hyprform
```

To make it show up in your app launcher (wofi/rofi/fuzzel, GNOME/KDE menus,
anything that reads the freedesktop `.desktop` spec):

```
mkdir -p ~/.local/share/applications
cp data/dev.rustyisacat.Hyprform.desktop ~/.local/share/applications/
```

Or point it at a specific config directory (useful for testing against a
copy before trusting it with your real one):

```
hyprform --hypr-dir ~/some/other/hypr/config
```

## Requirements

- Python 3.11+
- GTK4 + libadwaita (`gtk4`, `libadwaita` — already present on most
  Hyprland desktops via Qt/GTK app dependencies; on Arch: `pacman -S gtk4
  libadwaita python-gobject`)

## Status

Early but functional — the parsers, the Lua-editing engine, and the GUI
have all been tested against a real hybrid hyprlang+Lua Caelestia config
(69 keybinds, 13 autostart entries, 14 env vars, 7 window rules all
discovered and correctly classified editable/read-only) as well as a
synthetic plain hyprlang `.conf`. Run `pytest` for the automated test suite
(13 tests).

Adding brand-new entries from the GUI is supported for **Autostart** and
**Environment** in both config formats — for Lua configs, new entries are
inserted next to an existing sibling call at the same indentation (not
blindly appended at end-of-file, since real configs often wrap calls in
`hl.on("hyprland.start", function() ... end)`). Not yet built: adding new
Keybinds, Window Rules, or Monitors from the GUI — those don't have a safe
universal single-anchor pattern the same way, so they're left read-only
rather than guessed at. A "reload Hyprland" confirmation beyond the
best-effort `hyprctl reload` on save is also still basic.

## Source

https://github.com/rustyisacat/hyprform

## License

AGPL-3.0-or-later — see [LICENSE](LICENSE).
