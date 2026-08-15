# Hyprform

A GUI for editing Hyprland's config. No nano, no learning hyprlang or Lua syntax.

Hyprland configs come in two shapes these days: the classic `hyprland.conf`
(hyprlang: `key = value` and `block { ... }`), and, on newer installs
(Hyprland ≥0.55), a native Lua config
(`hyprland.lua` calling `hl.config({...})`, `hl.bind()`, `hl.env()`, etc.).
Hyprform reads both, follows `source =` / `require(...)` across however many
files your config is split into, and gives you plain-English forms instead
of either syntax.

## What it covers

- **Appearance** — gaps, border, rounding, blur, shadow, animations, layout
- **Behavior** — DPMS wake, splash/logo, VRR, misc toggles
- **Input** — keyboard layout, touchpad, gestures
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
synthetic plain hyprlang `.conf`. Run `pytest` for the automated test suite.

Not yet built: adding brand-new entries (keybinds, autostart commands,
window rules, env vars, monitors) from the GUI — today Hyprform edits every
value it discovers in your existing config, but doesn't yet offer an "add
new" flow for any category. A "reload Hyprland" confirmation beyond the
best-effort `hyprctl reload` on save is also still basic.

## License

AGPL-3.0-or-later — see [LICENSE](LICENSE).
