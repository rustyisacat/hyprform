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
    "Cursor": "input-mouse-symbolic",
    "Monitors": "video-display-symbolic",
    "Keybinds": "input-keyboard-symbolic",
    "Autostart": "system-run-symbolic",
    "Window Rules": "view-grid-symbolic",
    "Environment": "utilities-terminal-symbolic",
}


class HyprformWindow(Adw.ApplicationWindow):
    def __init__(self, app, hypr_dir: str):
        super().__init__(application=app, title="Hyprform", default_width=980, default_height=680)
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
        header.set_title_widget(Adw.WindowTitle(title="Hyprform", subtitle=self.hypr_dir))
        toolbar.add_top_bar(header)

        self.search_entry = Gtk.SearchEntry(placeholder_text="Search all settings…")
        self.search_entry.set_margin_start(8)
        self.search_entry.set_margin_end(8)
        self.search_entry.set_margin_top(8)
        self.search_entry.set_margin_bottom(4)
        self.search_entry.connect("search-changed", self._on_search_changed)
        toolbar.add_top_bar(self.search_entry)

        self.sidebar_list = Gtk.ListBox()
        self.sidebar_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.sidebar_list.add_css_class("navigation-sidebar")
        self.sidebar_list.connect("row-selected", self._on_category_selected)
        toolbar.set_content(Gtk.ScrolledWindow(child=self.sidebar_list, vexpand=True))

        page = Adw.NavigationPage(title="Hyprform", child=toolbar)
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
            row.hyprform_category = cat.name  # type: ignore[attr-defined]
            self.sidebar_list.append(row)

    # -- rendering --------------------------------------------------------

    def _on_category_selected(self, _list, row):
        if row is None:
            return
        self._show_category(row.hyprform_category)

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

    def _on_search_changed(self, entry):
        query = entry.get_text().strip()
        if not query:
            if self._current_category_name:
                self._show_category(self._current_category_name)
            return
        self._show_search_results(query)

    def _show_search_results(self, query: str):
        q = query.lower()
        by_category: dict[str, list[tuple[str, object]]] = {}
        for cat in self.categories:
            for field in cat.scalar_fields:
                haystack = f"{field.label} {field.description}".lower()
                if q in haystack:
                    by_category.setdefault(cat.name, []).append(("field", field))
            for item in cat.list_items:
                if q in item.summary.lower():
                    by_category.setdefault(cat.name, []).append(("item", item))

        self.content_page.set_title(f"Search: {query}")

        if not by_category:
            status = Adw.StatusPage(
                title="No matches",
                description=f"Nothing found for “{query}”.",
                icon_name="edit-find-symbolic",
            )
            self.content_scroller.set_child(status)
            return

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        page = Adw.PreferencesPage()
        outer.append(page)

        for cat_name, entries in by_category.items():
            group = Adw.PreferencesGroup(title=cat_name)
            for kind, obj in entries:
                if kind == "field":
                    group.add(build_field_row(obj, self._on_field_changed))
                else:
                    group.add(build_list_item_row(obj, self._on_field_changed))
            page.add(group)

        self.content_scroller.set_child(outer)

    def _build_add_group(self, cat) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title=f"Add a new {cat.name.rstrip('s').lower()}")
        widgets = []
        for spec in cat.add_spec.fields:
            if spec.kind == "choice":
                row = Adw.ComboRow(title=spec.label)
                row.set_model(Gtk.StringList.new(list(spec.choices)))
            elif spec.kind == "bool":
                row = Adw.SwitchRow(title=spec.label)
            else:
                row = Adw.EntryRow(title=spec.label)
            widgets.append((spec, row))
            group.add(row)

        def on_add(_button, cat=cat, widgets=widgets):
            values = []
            for spec, row in widgets:
                if spec.kind == "choice":
                    values.append(spec.choices[row.get_selected()])
                elif spec.kind == "bool":
                    values.append(row.get_active())
                else:
                    values.append(row.get_text())
            success, message = cat.add_spec.handler(*values)
            self._toast(message)
            if success:
                for spec, row in widgets:
                    if spec.kind == "choice":
                        row.set_selected(0)
                    elif spec.kind == "bool":
                        row.set_active(False)
                    else:
                        row.set_text("")
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
        diffs = save_mod.unified_diffs(self.tree)
        if not diffs:
            self._toast("Nothing to save")
            return
        self._show_diff_dialog(diffs)

    def _show_diff_dialog(self, diffs: dict[str, str]):
        dialog = Adw.Dialog()
        dialog.set_title("Review changes")
        dialog.set_content_width(720)
        dialog.set_content_height(560)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)

        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.connect("clicked", lambda _b, d=dialog: d.close())
        header.pack_start(cancel_button)

        save_button = Gtk.Button(label=f"Save {len(diffs)} file{'s' if len(diffs) != 1 else ''}")
        save_button.add_css_class("suggested-action")
        save_button.connect("clicked", lambda _b, d=dialog: self._confirm_save(d))
        header.pack_end(save_button)
        toolbar.add_top_bar(header)

        text_view = Gtk.TextView(editable=False, monospace=True, wrap_mode=Gtk.WrapMode.NONE, top_margin=8, bottom_margin=8, left_margin=8, right_margin=8)
        combined = "\n".join(diffs.values())
        text_view.get_buffer().set_text(combined)
        scroller = Gtk.ScrolledWindow(child=text_view, vexpand=True, hexpand=True)
        toolbar.set_content(scroller)

        dialog.set_child(toolbar)
        dialog.present(self)

    def _confirm_save(self, dialog):
        dialog.close()
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
