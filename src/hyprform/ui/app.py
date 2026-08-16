"""Hyprform's entry point: parses command-line args and starts the GTK app.

This is the file `hyprform` on the command line actually runs.
"""

from __future__ import annotations

import argparse
import os
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio  # noqa: E402

from .window import HyprformWindow  # noqa: E402

APP_ID = "dev.rustyisacat.Hyprform"


class HyprformApplication(Adw.Application):
    def __init__(self, hypr_dir: str):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.hypr_dir = hypr_dir
        self.window = None

    def do_activate(self):
        # GTK calls this automatically once the app has finished starting up
        # (via app.run() below) — it's where we actually create and show the
        # window, rather than in __init__, which runs too early for that.
        if self.window is None:
            self.window = HyprformWindow(self, self.hypr_dir)
        self.window.present()


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
