from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from .. import discovery, save as save_mod  # noqa: E402
from ..schema.binder import build_categories  # noqa: E402
from .rows import build_field_row, build_list_item_row  # noqa: E402

CATEGORY_ICONS = {
    "Appearance": "applications-graphics-symbolic",
    "Behavior": "preferences-system-symbolic",
    "Input": "input-keyboard-symbolic",
    "Monitors": "video-display-symbolic",
    "Keybinds": "input-keyboard-symbolic",
    "Autostart": "system-run-symbolic",
    "Window Rules": "view-grid-symbolic",
    "Environment": "utilities-terminal-symbolic",
}


class KnurlWindow(Adw.ApplicationWindow):
    def __init__(self, app, hypr_dir: str):
        super().__init__(application=app, title="Knurl", default_width=980, default_height=680)
        self.hypr_dir = hypr_dir
        self.tree = None
        self.categories = []
        self.dirty = False
        self._current_category_name = None

        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        self.split_view = Adw.NavigationSplitView()
        self.toast_overlay.set_child(self.split_view)

        self._build_sidebar()
        self._build_content_placeholder()
        self._load()

    # -- chrome -------------------------------------------------------

    def _build_sidebar(self):
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title="Knurl", subtitle=self.hypr_dir))
        toolbar.add_top_bar(header)

        self.sidebar_list = Gtk.ListBox()
        self.sidebar_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.sidebar_list.add_css_class("navigation-sidebar")
        self.sidebar_list.connect("row-selected", self._on_category_selected)
        toolbar.set_content(Gtk.ScrolledWindow(child=self.sidebar_list, vexpand=True))

        page = Adw.NavigationPage(title="Knurl", child=toolbar)
        self.split_view.set_sidebar(page)

    def _build_content_placeholder(self):
        self.content_toolbar = Adw.ToolbarView()
        self.content_header = Adw.HeaderBar()
        self.save_button = Gtk.Button(label="Save")
        self.save_button.add_css_class("suggested-action")
        self.save_button.set_sensitive(False)
        self.save_button.connect("clicked", self._on_save_clicked)
        self.content_header.pack_end(self.save_button)
        self.content_toolbar.add_top_bar(self.content_header)

        self.content_scroller = Gtk.ScrolledWindow(vexpand=True)
        self.content_toolbar.set_content(self.content_scroller)

        self.content_page = Adw.NavigationPage(title="", child=self.content_toolbar)
        self.split_view.set_content(self.content_page)

    # -- data -----------------------------------------------------------

    def _load(self):
        try:
            self.tree = discovery.load(hypr_dir=self.hypr_dir)
        except FileNotFoundError as e:
            self._show_error(str(e))
            return
        self.categories = build_categories(self.tree)
        self._populate_sidebar()
        if self.categories:
            self.sidebar_list.select_row(self.sidebar_list.get_row_at_index(0))

    def _refresh_category_data(self):
        """Re-derive category/field data from the (edited) tree. Cheap and
        widget-free — safe to call after every edit without disturbing
        whatever row currently has focus. The widget tree for the visible
        category is only rebuilt on navigation, not on every keystroke.
        """
        self.categories = build_categories(self.tree)

    def _populate_sidebar(self):
        for cat in self.categories:
            row = Adw.ActionRow(title=cat.name)
            icon_name = CATEGORY_ICONS.get(cat.name, "preferences-other-symbolic")
            row.add_prefix(Gtk.Image.new_from_icon_name(icon_name))
            count = len(cat.scalar_fields) + len(cat.list_items)
            row.set_subtitle(f"{count} setting{'s' if count != 1 else ''}")
            row.knurl_category = cat.name  # type: ignore[attr-defined]
            self.sidebar_list.append(row)

    # -- rendering --------------------------------------------------------

    def _on_category_selected(self, _list, row):
        if row is None:
            return
        self._show_category(row.knurl_category)

    def _show_category(self, name: str):
        self._current_category_name = name
        cat = next((c for c in self.categories if c.name == name), None)
        self.content_page.set_title(name)
        if cat is None:
            return

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        page = Adw.PreferencesPage()
        outer.append(page)

        if cat.scalar_fields:
            group = Adw.PreferencesGroup(title=name)
            for field in cat.scalar_fields:
                group.add(build_field_row(field, self._on_field_changed))
            page.add(group)

        if cat.list_items:
            group = Adw.PreferencesGroup(title=name, description=f"{len(cat.list_items)} entries found in your config")
            for item in cat.list_items:
                group.add(build_list_item_row(item, self._on_field_changed))
            page.add(group)

        if cat.add_spec is not None:
            page.add(self._build_add_group(cat))

        self.content_scroller.set_child(outer)

    def _build_add_group(self, cat) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title=f"Add a new {cat.name.rstrip('s').lower()}")
        entries = [Adw.EntryRow(title=label) for label in cat.add_spec.fields]
        for entry in entries:
            group.add(entry)

        def on_add(_button, cat=cat, entries=entries):
            values = [e.get_text() for e in entries]
            success, message = cat.add_spec.handler(*values)
            self._toast(message)
            if success:
                for e in entries:
                    e.set_text("")
                self.dirty = True
                self.save_button.set_sensitive(True)
                self._refresh_category_data()
                self._show_category(cat.name)

        add_row = Adw.ActionRow(title="Add")
        button = Gtk.Button(icon_name="list-add-symbolic", valign=Gtk.Align.CENTER)
        button.add_css_class("suggested-action")
        button.connect("clicked", on_add)
        add_row.add_suffix(button)
        add_row.set_activatable_widget(button)
        group.add(add_row)
        return group

    # -- edits ------------------------------------------------------------

    def _on_field_changed(self, field, new_value):
        if field.value == new_value:
            return
        try:
            field.set(new_value)
        except Exception as e:  # noqa: BLE001
            self._toast(f"Couldn't apply that change: {e}")
            return
        self.dirty = True
        self.save_button.set_sensitive(True)
        self._refresh_category_data()

    def _on_save_clicked(self, _button):
        try:
            saved = save_mod.save(self.tree, reload_hyprland=self._is_hyprland_running())
        except Exception as e:  # noqa: BLE001
            self._toast(f"Save failed: {e}")
            return
        self.dirty = False
        self.save_button.set_sensitive(False)
        if not saved:
            self._toast("Nothing to save")
            return
        names = ", ".join(s.path.rsplit("/", 1)[-1] for s in saved)
        self._toast(f"Saved {len(saved)} file(s): {names} (backups kept alongside each)")

    @staticmethod
    def _is_hyprland_running() -> bool:
        import os

        return bool(os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"))

    # -- misc ---------------------------------------------------------------

    def _toast(self, message: str):
        self.toast_overlay.add_toast(Adw.Toast(title=message, timeout=4))

    def _show_error(self, message: str):
        status = Adw.StatusPage(
            title="No Hyprland config found",
            description=message,
            icon_name="dialog-warning-symbolic",
        )
        self.content_scroller.set_child(status)
