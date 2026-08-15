from __future__ import annotations

import argparse
import os
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio  # noqa: E402

from .window import KnurlWindow  # noqa: E402

APP_ID = "dev.rustyisacat.Knurl"


class KnurlApplication(Adw.Application):
    def __init__(self, hypr_dir: str):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.hypr_dir = hypr_dir
        self.window = None

    def do_activate(self):
        if self.window is None:
            self.window = KnurlWindow(self, self.hypr_dir)
        self.window.present()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="knurl", description="A GUI for editing Hyprland's config — no nano, no lingo.")
    parser.add_argument(
        "--hypr-dir",
        default=os.environ.get("KNURL_HYPR_DIR", os.path.expanduser("~/.config/hypr")),
        help="Path to the Hyprland config directory (default: ~/.config/hypr)",
    )
    args = parser.parse_args(argv)

    app = KnurlApplication(hypr_dir=args.hypr_dir)
    return app.run(sys.argv[:1])


if __name__ == "__main__":
    raise SystemExit(main())
