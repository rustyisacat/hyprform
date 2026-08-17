"""Hyprform's entry point: parses command-line args and starts the GTK app.

This is the file `hyprform` on the command line actually runs.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import os
import pathlib
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, Gtk  # noqa: E402

from .window import HyprformWindow, build_shortcuts_window  # noqa: E402

APP_ID = "dev.rustyisacat.Hyprform"


def _version() -> str:
    try:
        return importlib.metadata.version("hyprform")
    except importlib.metadata.PackageNotFoundError:
        # Not installed as a package (e.g. running straight from source) —
        # a missing version shouldn't be a crash, just a blank field.
        return "dev"


def _register_app_icon() -> None:
    """Points GTK's icon lookup at this repo's bundled icon, so the About
    window shows Hyprform's real icon instead of a generic gear even before
    anyone's copied it into their system icon theme (see README's install
    steps for the app-launcher/taskbar version of the same icon). Best
    effort only — a missing icon is cosmetic, never worth crashing over.
    """
    try:
        repo_root = pathlib.Path(__file__).resolve().parents[3]
        icons_dir = repo_root / "data" / "icons"
        if not icons_dir.is_dir():
            return
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.IconTheme.get_for_display(display).add_search_path(str(icons_dir))
    except Exception:  # noqa: BLE001
        pass


class HyprformApplication(Adw.Application):
    def __init__(self, hypr_dir: str):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.hypr_dir = hypr_dir
        self.window = None

    def do_startup(self):
        Adw.Application.do_startup(self)
        _register_app_icon()

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)

        shortcuts_action = Gio.SimpleAction.new("shortcuts", None)
        shortcuts_action.connect("activate", self._on_shortcuts)
        self.add_action(shortcuts_action)

        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_a: self.quit())
        self.add_action(quit_action)

        self.set_accels_for_action("app.quit", ["<Primary>q"])
        self.set_accels_for_action("app.shortcuts", ["<Primary>question"])
        self.set_accels_for_action("win.save", ["<Primary>s"])
        self.set_accels_for_action("win.focus-search", ["<Primary>f"])
        self.set_accels_for_action("win.undo", ["<Primary>z"])
        self.set_accels_for_action("win.redo", ["<Primary><Shift>z", "<Primary>y"])

    def do_activate(self):
        # GTK calls this automatically once the app has finished starting up
        # (via app.run() below) — it's where we actually create and show the
        # window, rather than in __init__, which runs too early for that.
        if self.window is None:
            self.window = HyprformWindow(self, self.hypr_dir)
        self.window.present()

    def _on_about(self, _action, _param):
        about = Adw.AboutWindow(
            transient_for=self.window,
            application_name="Hyprform",
            application_icon=APP_ID,
            version=_version(),
            developer_name="rustyisacat",
            license_type=Gtk.License.AGPL_3_0,
            comments="A GUI for editing Hyprland's config — no nano, no lingo.",
            website="https://github.com/rustyisacat/hyprform",
            issue_url="https://github.com/rustyisacat/hyprform/issues",
        )
        about.present()

    def _on_shortcuts(self, _action, _param):
        build_shortcuts_window(self.window).present()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hyprform", description="A GUI for editing Hyprland's config — no nano, no lingo.")
    parser.add_argument(
        "--hypr-dir",
        default=os.environ.get("HYPRFORM_HYPR_DIR", os.path.expanduser("~/.config/hypr")),
        help="Path to the Hyprland config directory (default: ~/.config/hypr)",
    )
    args = parser.parse_args(argv)

    app = HyprformApplication(hypr_dir=args.hypr_dir)
    return app.run(sys.argv[:1])


if __name__ == "__main__":
    raise SystemExit(main())
