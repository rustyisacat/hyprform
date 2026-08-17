"""Hyprform's main window: a sidebar of categories (Appearance, Keybinds,
...) on the left and that category's settings on the right — the standard
libadwaita "preferences" layout (``Adw.NavigationSplitView``). Clicking a
sidebar row calls ``_show_category``, which asks ``schema.binder`` for that
category's data and hands each field to ``ui.rows`` to turn into an actual
GTK widget. Nothing in this file knows about hyprlang or Lua syntax —
that's the whole point of the schema/binder split.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Pango", "1.0")
from gi.repository import Adw, Gdk, Gio, Gtk, Pango  # noqa: E402

from .. import discovery, hyprctl, save as save_mod  # noqa: E402
from ..schema.binder import build_categories  # noqa: E402
from .rows import build_field_row, build_list_item_row  # noqa: E402

_MODIFIER_KEYVALS = {
    Gdk.KEY_Shift_L, Gdk.KEY_Shift_R,
    Gdk.KEY_Control_L, Gdk.KEY_Control_R,
    Gdk.KEY_Alt_L, Gdk.KEY_Alt_R,
    Gdk.KEY_Super_L, Gdk.KEY_Super_R,
    Gdk.KEY_Meta_L, Gdk.KEY_Meta_R,
    Gdk.KEY_Hyper_L, Gdk.KEY_Hyper_R,
    Gdk.KEY_Caps_Lock, Gdk.KEY_ISO_Level3_Shift,
}


def translate_keypress(keyval: int, state) -> tuple[str, str] | None:
    """Turns a captured GTK keypress into (modifiers, key) in Hyprland's own
    naming convention (e.g. ("SUPER SHIFT", "Q")), so the Keybinds "add new"
    form can be filled from an actual keypress instead of requiring the user
    to already know X11 keysym names. Returns None for a bare modifier
    keypress (Shift/Ctrl/etc. alone) — those should keep listening rather
    than being captured as "the key".
    """
    if keyval in _MODIFIER_KEYVALS:
        return None
    mods = []
    if state & Gdk.ModifierType.SUPER_MASK:
        mods.append("SUPER")
    if state & Gdk.ModifierType.CONTROL_MASK:
        mods.append("CTRL")
    if state & Gdk.ModifierType.ALT_MASK:
        mods.append("ALT")
    if state & Gdk.ModifierType.SHIFT_MASK:
        mods.append("SHIFT")
    name = Gdk.keyval_name(keyval) or ""
    if len(name) == 1:
        name = name.upper()
    return " ".join(mods), name


def monitor_picker_rows(monitors: list[dict]) -> list[tuple[str, str, str]]:
    """(primary, secondary, value) rows for a hyprctl monitors -j result."""
    return [
        (m.get("name", "?"), f"{m.get('width', '?')}x{m.get('height', '?')} @ {m.get('refreshRate', '?')}Hz", m.get("name", ""))
        for m in monitors
    ]


def client_picker_rows(clients: list[dict]) -> list[tuple[str, str, str]]:
    """(primary, secondary, value) rows for a hyprctl clients -j result."""
    return [(c.get("title") or "(untitled)", c.get("class", "?"), c.get("class", "")) for c in clients]


def keybind_search_text(item) -> str:
    """All the text worth matching a Keybinds search query against — the
    summary line plus every field's label and current value — so searching
    finds a match whether it's a modifier, a key, or an action/command.
    hyprlang binds keep everything in one summary string (e.g. "SUPER, Q,
    exec, kitty"); Lua-defined binds split the action name into the field
    label and the key combo into the field value, so both need checking.
    """
    parts = [item.summary]
    for field in item.fields:
        parts.append(field.label)
        parts.append(str(field.value))
    return " ".join(parts).lower()

def _apply_diff_coloring(buffer: Gtk.TextBuffer, text: str) -> None:
    """Colors a unified diff the way every other diff viewer does: added
    lines green, removed lines red, file/hunk headers muted — so a save
    with several changed lines is scannable at a glance instead of being a
    wall of identical-looking monospace text.
    """
    buffer.set_text(text)
    added = buffer.create_tag("diff-added", foreground="#26a269")
    removed = buffer.create_tag("diff-removed", foreground="#c01c28")
    header = buffer.create_tag("diff-header", foreground="#1c71d8", weight=Pango.Weight.BOLD)
    hunk = buffer.create_tag("diff-hunk", foreground="#9a9996", style=Pango.Style.ITALIC)

    for line_no in range(buffer.get_line_count()):
        _found, start = buffer.get_iter_at_line(line_no)
        end = start.copy()
        end.forward_to_line_end()
        line_text = buffer.get_text(start, end, False)
        if line_text.startswith("+++") or line_text.startswith("---"):
            buffer.apply_tag(header, start, end)
        elif line_text.startswith("@@"):
            buffer.apply_tag(hunk, start, end)
        elif line_text.startswith("+"):
            buffer.apply_tag(added, start, end)
        elif line_text.startswith("-"):
            buffer.apply_tag(removed, start, end)


def build_shortcuts_window(parent) -> Gtk.ShortcutsWindow:
    window = Gtk.ShortcutsWindow(transient_for=parent, modal=True)
    section = Gtk.ShortcutsSection(section_name="main")
    group = Gtk.ShortcutsGroup(title="General")
    group.append(Gtk.ShortcutsShortcut(title="Save changes", accelerator="<Primary>s"))
    group.append(Gtk.ShortcutsShortcut(title="Search all settings", accelerator="<Primary>f"))
    group.append(Gtk.ShortcutsShortcut(title="Clear the current search", accelerator="Escape"))
    group.append(Gtk.ShortcutsShortcut(title="Show this window", accelerator="<Primary>question"))
    group.append(Gtk.ShortcutsShortcut(title="Quit Hyprform", accelerator="<Primary>q"))
    section.add_group(group)
    window.add_section(section)
    return window


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
        self._build_actions()
        self._load()

    # -- chrome -------------------------------------------------------

    def _build_actions(self):
        save_action = Gio.SimpleAction.new("save", None)
        save_action.connect("activate", lambda *_a: self._on_save_clicked(None))
        self.add_action(save_action)

        focus_search_action = Gio.SimpleAction.new("focus-search", None)
        focus_search_action.connect("activate", lambda *_a: self.search_entry.grab_focus())
        self.add_action(focus_search_action)

    def _build_sidebar(self):
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        self._base_subtitle = self.hypr_dir
        self.window_title = Adw.WindowTitle(title="Hyprform", subtitle=self._base_subtitle)
        header.set_title_widget(self.window_title)

        menu = Gio.Menu()
        menu.append("Keyboard Shortcuts", "app.shortcuts")
        menu.append("About Hyprform", "app.about")
        menu_button = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu, primary=True, tooltip_text="Main Menu")
        header.pack_end(menu_button)
        toolbar.add_top_bar(header)

        self.search_entry = Gtk.SearchEntry(placeholder_text="Search all settings…")
        self.search_entry.set_margin_start(8)
        self.search_entry.set_margin_end(8)
        self.search_entry.set_margin_top(8)
        self.search_entry.set_margin_bottom(4)
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("stop-search", lambda entry: entry.set_text(""))
        toolbar.add_top_bar(self.search_entry)

        self.sidebar_list = Gtk.ListBox()
        self.sidebar_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.sidebar_list.add_css_class("navigation-sidebar")
        self.sidebar_list.connect("row-selected", self._on_category_selected)
        toolbar.set_content(Gtk.ScrolledWindow(child=self.sidebar_list, vexpand=True))

        page = Adw.NavigationPage(title="Hyprform", child=toolbar)
        self.split_view.set_sidebar(page)

    def _update_window_title(self):
        subtitle = self._base_subtitle
        if self.dirty:
            subtitle += " • Unsaved changes"
        self.window_title.set_subtitle(subtitle)

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

        if cat.list_items and name == "Keybinds":
            self._build_keybinds_list_group(page, cat)
        elif cat.list_items:
            group = Adw.PreferencesGroup(title=name, description=f"{len(cat.list_items)} entries found in your config")
            for item in cat.list_items:
                group.add(build_list_item_row(item, self._on_field_changed))
            page.add(group)
        elif cat.add_spec is not None:
            # A list-shaped category with nothing in it yet — say so, rather
            # than just silently showing the add-a-new-one form with no
            # context for why the rest of the page looks empty.
            kind = cat.name.rstrip("s").lower()
            page.add(Adw.PreferencesGroup(description=f"No {kind}s in your config yet — add one below."))

        if cat.add_spec is not None:
            page.add(self._build_add_group(cat))

        self.content_scroller.set_child(outer)

    def _build_keybinds_list_group(self, page, cat):
        """Keybinds gets its own search box (unlike the other list
        categories) since a real config can easily have 50+ of them —
        filters live as you type, by key/modifier or by action, without
        rebuilding the search box itself (which would steal keyboard focus
        mid-keystroke).
        """
        search_group = Adw.PreferencesGroup()
        search_entry = Gtk.SearchEntry(placeholder_text="Search by key or action (e.g. “SUPER” or “exec”)…")
        search_group.add(search_entry)
        search_entry.connect("stop-search", lambda entry: entry.set_text(""))
        page.add(search_group)

        list_group = Adw.PreferencesGroup(title="Keybinds")
        page.add(list_group)

        rows: list[Gtk.Widget] = []

        def populate(query: str):
            for row in rows:
                list_group.remove(row)
            rows.clear()
            q = query.strip().lower()
            matched = [item for item in cat.list_items if not q or q in keybind_search_text(item)]
            total = len(cat.list_items)
            if matched:
                for item in matched:
                    row = build_list_item_row(item, self._on_field_changed)
                    list_group.add(row)
                    rows.append(row)
            else:
                empty_row = Adw.ActionRow(title=f"No keybinds match “{query}”", sensitive=False)
                list_group.add(empty_row)
                rows.append(empty_row)
            list_group.set_description(f"{len(matched)} of {total} entries match" if q else f"{total} entries found in your config")

        search_entry.connect("search-changed", lambda entry: populate(entry.get_text()))
        populate("")

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

        self._add_live_lookup_row(cat, group, widgets)

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
                self._update_window_title()
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

    def _add_live_lookup_row(self, cat, group, widgets):
        """A few "add new" forms are much friendlier with a live-Hyprland
        assist — picking a connected monitor, a running window's class, or
        an actual keypress — instead of requiring the user to already know
        Hyprland's own inspection commands. All of these degrade to a toast
        explaining why, rather than silently doing nothing, if Hyprland
        isn't reachable.
        """
        if cat.name == "Monitors":
            name_row = next(row for spec, row in widgets if spec.label.startswith("Name"))
            row = Adw.ActionRow(title="Detect connected monitors", subtitle="Requires Hyprland to be running")
            button = Gtk.Button(icon_name="view-refresh-symbolic", valign=Gtk.Align.CENTER)

            def on_detect(_button, name_row=name_row):
                monitors = hyprctl.list_monitors()
                if not monitors:
                    self._toast("Couldn't detect monitors — is Hyprland running?")
                    return
                self._show_picker_dialog("Pick a monitor", monitor_picker_rows(monitors), name_row.set_text)

            button.connect("clicked", on_detect)
            row.add_suffix(button)
            row.set_activatable_widget(button)
            group.add(row)

        elif cat.name == "Keybinds":
            mods_row = next(row for spec, row in widgets if spec.label.startswith("Modifiers"))
            key_row = next(row for spec, row in widgets if spec.label.startswith("Key"))
            row = Adw.ActionRow(title="Or press the actual key combo", subtitle="Fills in Modifiers and Key for you")
            button = Gtk.Button(label="Listen for keypress", valign=Gtk.Align.CENTER)
            button.connect("clicked", lambda _b, mods_row=mods_row, key_row=key_row: self._show_key_capture_dialog(mods_row, key_row))
            row.add_suffix(button)
            row.set_activatable_widget(button)
            group.add(row)

        elif cat.name == "Window Rules":
            match_by_row = next(row for spec, row in widgets if spec.label == "Match by")
            match_value_row = next(row for spec, row in widgets if spec.label.startswith("Match value"))
            row = Adw.ActionRow(title="Or pick a running window", subtitle="Requires Hyprland to be running")
            button = Gtk.Button(label="Pick a window…", valign=Gtk.Align.CENTER)

            def on_pick(_button, match_by_row=match_by_row, match_value_row=match_value_row):
                clients = hyprctl.list_clients()
                if not clients:
                    self._toast("Couldn't list windows — is Hyprland running?")
                    return

                def apply_pick(value, match_by_row=match_by_row, match_value_row=match_value_row):
                    match_by_row.set_selected(0)  # "class" — first in WINDOW_RULE_MATCH_CHOICES
                    match_value_row.set_text(value)

                self._show_picker_dialog("Pick a running window", client_picker_rows(clients), apply_pick)

            button.connect("clicked", on_pick)
            row.add_suffix(button)
            row.set_activatable_widget(button)
            group.add(row)

    def _show_picker_dialog(self, title: str, rows_data: list[tuple[str, str, str]], on_pick):
        dialog = Adw.Dialog()
        dialog.set_title(title)
        dialog.set_content_width(480)
        dialog.set_content_height(420)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.connect("clicked", lambda _b, d=dialog: d.close())
        header.pack_start(cancel_button)
        toolbar.add_top_bar(header)

        listbox = Gtk.ListBox()
        listbox.add_css_class("boxed-list")
        listbox.set_margin_start(12)
        listbox.set_margin_end(12)
        listbox.set_margin_top(12)
        listbox.set_margin_bottom(12)
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)

        for primary, secondary, value in rows_data:
            row = Adw.ActionRow(title=primary or "?", subtitle=secondary, activatable=True)
            row.hyprform_value = value  # type: ignore[attr-defined]
            listbox.append(row)

        def on_row_activated(_list, row, dialog=dialog, on_pick=on_pick):
            on_pick(row.hyprform_value)
            dialog.close()

        listbox.connect("row-activated", on_row_activated)
        scroller = Gtk.ScrolledWindow(child=listbox, vexpand=True)
        toolbar.set_content(scroller)

        dialog.set_child(toolbar)
        dialog.present(self)

    def _show_key_capture_dialog(self, mods_row, key_row):
        dialog = Adw.Dialog()
        dialog.set_title("Press a key combo")
        dialog.set_content_width(380)
        dialog.set_content_height(180)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.connect("clicked", lambda _b, d=dialog: d.close())
        header.pack_start(cancel_button)
        toolbar.add_top_bar(header)

        status = Adw.StatusPage(
            title="Press your key combo now…",
            description="Modifier keys alone won't be captured — press the actual key too.",
            icon_name="input-keyboard-symbolic",
        )
        toolbar.set_content(status)

        def on_key_pressed(_controller, keyval, _keycode, state, dialog=dialog, mods_row=mods_row, key_row=key_row):
            translated = translate_keypress(keyval, state)
            if translated is None:
                return False
            mods, key = translated
            mods_row.set_text(mods)
            key_row.set_text(key)
            dialog.close()
            return True

        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", on_key_pressed)
        dialog.add_controller(controller)

        dialog.set_child(toolbar)
        dialog.present(self)

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
        self._update_window_title()
        self._refresh_category_data()

    def _on_save_clicked(self, _button):
        if not self.dirty:
            self._toast("Nothing to save")
            return
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
        _apply_diff_coloring(text_view.get_buffer(), combined)
        scroller = Gtk.ScrolledWindow(child=text_view, vexpand=True, hexpand=True)
        toolbar.set_content(scroller)

        dialog.set_child(toolbar)
        dialog.present(self)

    def _confirm_save(self, dialog):
        dialog.close()
        try:
            saved, reload_message = save_mod.save(self.tree, reload_hyprland=hyprctl.is_available())
        except Exception as e:  # noqa: BLE001
            self._toast(f"Save failed: {e}")
            return
        self.dirty = False
        self.save_button.set_sensitive(False)
        self._update_window_title()
        if not saved:
            self._toast("Nothing to save")
            return
        names = ", ".join(s.path.rsplit("/", 1)[-1] for s in saved)
        message = f"Saved {len(saved)} file(s): {names} (backups kept alongside each)"
        if reload_message:
            message += f" — {reload_message}"
        self._toast(message)

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
