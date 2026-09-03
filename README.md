# Hyprform

![Platform](https://img.shields.io/badge/platform-Hyprland-58E1FF?logo=linux&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![GTK4](https://img.shields.io/badge/UI-GTK4%20%2B%20libadwaita-4A86CF?logo=gtk&logoColor=white)
![Version](https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2Frusty-workshop%2Fhyprform%2Fmaster%2Fpyproject.toml&query=%24.project.version&label=version)
![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)

🌐 **[Live site](https://hyprform.rusty.is-a.dev/)**

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
  animations. Border and shadow colors get a real color picker whenever the
  value is a single flat color (gradients stay as plain text — a picker
  can't represent multiple stops, so it doesn't pretend to)
- **Behavior** — DPMS wake, splash/logo, VRR, focus-on-activate, manual
  resize/drag animation, terminal swallowing, fullscreen handling, XWayland,
  and dwindle/master layout tuning (pseudotile, split behavior, master
  ratio)
- **Input** — keyboard layout/repeat, mouse sensitivity and acceleration,
  focus-follows-mouse, touchpad gestures and swipe tuning
- **Cursor** — hardware cursor mode, auto-hide on idle/typing/touch,
  per-monitor default, zoom
- **Monitors** — each entry's name, resolution, position, and scale are
  their own editable fields (not one raw line), with any trailing flags
  (transform, mirror, bitdepth, ...) preserved untouched
- **Keybinds, Autostart, Window Rules, Environment** — shown as lists, with
  an "add new" form for every one of them (see below)
- **Search** — a search bar in the sidebar filters every setting across
  every category at once, by name and description, so you don't have to
  know which category something lives in. Keybinds also gets its own
  search box right on the category page — since a real config can easily
  have 50+ of them — that filters live as you type by either the key/
  modifiers or the action (e.g. "SUPER" or "exec" both work)

## Adding new entries

Autostart, Environment, Window Rules, Keybinds, and Monitors all have an
"add a new one" form at the bottom of their category — no hyprlang/Lua
syntax involved:

- **Window Rules**: pick what to match (class/title/initialClass/
  initialTitle) and a value, pick a rule (float, workspace, opacity, size,
  ...) and its argument if it needs one. Hyprform builds the
  `windowrulev2` line and the exact-match regex for you.
- **Keybinds**: modifiers, key, an action from a curated list of common
  dispatchers, an optional argument, and a "repeat while held" toggle
  (`bind` vs `binde`).
- **Monitors**: name, resolution, position, scale.

All of these work for hyprlang configs. For Lua configs, Autostart and
Environment insert next to an existing sibling call at the same
indentation (not blindly appended at end-of-file, since real configs often
wrap calls in `hl.on("hyprland.start", function() ... end)`); Window Rules,
Keybinds, and Monitors are hyprlang-only for now — Hyprform doesn't have
confirmed knowledge of the exact argument shape `hl.window_rule()`/
`hl.bind()`/`hl.monitor()` expect in every real config, and would rather
say so than guess and silently write something wrong.

### Live Hyprland assists

If Hyprland is actually running while you use Hyprform (checked via
`hyprctl`, and never required — everything above still works from a plain
copy of your config), a few of these forms get real data instead of asking
you to already know Hyprland's own inspection commands:

- **Monitors**: a "Detect connected monitors" button lists your actually
  connected displays (via `hyprctl monitors`) so you can pick the real
  port name instead of guessing at "DP-1" vs "HDMI-A-1".
- **Window Rules**: a "Pick a running window" button lists your currently
  open windows (via `hyprctl clients`) and fills in the class name for
  you — no more opening a terminal to run `hyprctl clients` just to find
  out what an app calls itself.
- **Keybinds**: a "Listen for keypress" button captures your actual next
  key combo and fills in Modifiers/Key — no need to know Hyprland's key
  naming at all.

Saving also runs `hyprctl reload` when Hyprland is running, and reports
whether it actually succeeded (rather than the old silent best-effort).

## Reviewing changes before they're written

Clicking Save shows a real unified diff of every file about to change —
old lines and new lines, nothing hidden — before anything touches disk.
Added lines are highlighted green and removed lines red, same as a diff
viewer on GitHub, so a glance tells you what's about to happen. Confirming
still keeps the existing timestamped backup
(`<file>.hyprform-bak-<timestamp>`) alongside each touched file.

## Finding your way around

- The header bar's menu button opens **About** (version, license, links)
  and **Keyboard Shortcuts** (a full reference of everything below).
- If you have unsaved changes, the window's subtitle says so ("Unsaved
  changes") so it's always obvious whether Save has anything to do.
- Categories that start out empty (a fresh config with no window rules yet,
  say) show a plain-English hint and the add-new form instead of a blank
  page — there's always something to click.
- Hyprform remembers your window size (and whether it was maximized)
  between launches, like any other desktop app.
- The header bars and sidebar carry a faint purple-to-blue wash echoing the
  app icon — deliberately kept off every interactive element so it never
  fights whatever accent color you've set for your own GTK theme.

### Undo and redo

Every field edit (a toggled switch, a typed value, a moved slider, a picked
color) can be undone with `Ctrl+Z` and redone with `Ctrl+Shift+Z` — or with
the two arrow buttons next to Save. Undoing takes you right back to the
value the field had before, and making a new edit after an undo throws away
the old "redo" history, the same way any text editor's undo stack works.
Undo tracks *changes to existing fields* — adding a brand-new keybind,
window rule, etc. isn't undoable yet (there's no delete feature to pair it
with), so Hyprform is upfront about that rather than pretending an add can
be silently reversed.

### Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+S` | Save (opens the diff review) |
| `Ctrl+Z` | Undo the last field edit |
| `Ctrl+Shift+Z` | Redo |
| `Ctrl+F` | Jump to the sidebar search box |
| `Escape` | Clear whichever search box you're in |
| `Ctrl+Q` | Quit |
| `Ctrl+?` | Open the Keyboard Shortcuts window |

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
never move or reformat.

## Install

```
uv tool install --editable .
hyprform
```

To make it show up in your app launcher (wofi/rofi/fuzzel, GNOME/KDE menus,
anything that reads the freedesktop `.desktop` spec) with its own icon
instead of a generic gear:

```
mkdir -p ~/.local/share/applications ~/.local/share/icons/hicolor/scalable/apps
cp data/dev.rustyisacat.Hyprform.desktop ~/.local/share/applications/
cp data/icons/hicolor/scalable/apps/dev.rustyisacat.Hyprform.svg ~/.local/share/icons/hicolor/scalable/apps/
```

(Hyprform also finds this icon on its own for the About window and window
decorations — this step is only needed for icon *theme* integration, like
your launcher's app grid.)

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
(49 tests).

## Source

https://github.com/rusty-workshop/hyprform

## License

AGPL-3.0-or-later — see [LICENSE](LICENSE).
