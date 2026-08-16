"""Turns a BoundField / ListItem into an Adw row widget, without exposing
any hyprlang/Lua vocabulary to the user — labels and descriptions come
entirely from the schema, never from raw key names.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk  # noqa: E402

from .. import color  # noqa: E402
from ..schema.binder import BoundField, ListItem  # noqa: E402


def build_field_row(field: BoundField, on_changed) -> Adw.PreferencesRow:
    if not field.editable:
        row = Adw.ActionRow(title=field.label, subtitle=f"{field.description}\nLinked to: {field.value}" if field.description else f"Linked to: {field.value}")
        row.set_subtitle_lines(0)
        icon = Gtk.Image.new_from_icon_name("view-refresh-symbolic")
        icon.set_tooltip_text("This value is built by a script in your config, not a plain setting — Hyprform can't safely edit it. Change it directly in the config file if you need to.")
        row.add_suffix(icon)
        row.set_sensitive(False)
        return row

    subtitle = field.description or None

    if field.kind == "bool":
        row = Adw.SwitchRow(title=field.label, subtitle=subtitle)
        row.set_active(bool(field.value))
        row.connect("notify::active", lambda r, _p: on_changed(field, r.get_active()))
        return row

    if field.kind == "choice" and field.choices:
        row = Adw.ComboRow(title=field.label, subtitle=subtitle)
        model = Gtk.StringList.new(list(field.choices))
        row.set_model(model)
        try:
            row.set_selected(list(field.choices).index(str(field.value)))
        except ValueError:
            row.set_selected(0)
        row.connect("notify::selected", lambda r, _p: on_changed(field, field.choices[r.get_selected()]))
        return row

    if field.kind == "color":
        parsed = color.parse_color(str(field.value))
        if parsed is not None:
            row = Adw.ActionRow(title=field.label, subtitle=subtitle)
            button = Gtk.ColorDialogButton(dialog=Gtk.ColorDialog())
            button.set_valign(Gtk.Align.CENTER)
            rgba = Gdk.RGBA()
            rgba.red, rgba.green, rgba.blue, rgba.alpha = parsed.r, parsed.g, parsed.b, parsed.a
            button.set_rgba(rgba)

            def _on_color_changed(btn, _pspec, field=field, style=parsed.style):
                c = btn.get_rgba()
                new_value = color.format_color(c.red, c.green, c.blue, c.alpha, style)
                on_changed(field, new_value)

            button.connect("notify::rgba", _on_color_changed)
            row.add_suffix(button)
            row.set_activatable_widget(button)
            return row
        # Not a single flat color (e.g. a gradient with multiple stops) —
        # fall through to the plain text field below rather than risk
        # a picker that can only ever show/set one stop of it.

    if field.kind == "number":
        row = Adw.SpinRow.new_with_range(0, 100000, 1)
        row.set_title(field.label)
        if subtitle:
            row.set_subtitle(subtitle)
        row.set_value(float(field.value))
        row.connect("notify::value", lambda r, _p: on_changed(field, int(r.get_value())))
        return row

    if field.kind == "float":
        row = Adw.SpinRow.new_with_range(0, 100, 0.01)
        row.set_title(field.label)
        row.set_digits(2)
        if subtitle:
            row.set_subtitle(subtitle)
        row.set_value(float(field.value))
        row.connect("notify::value", lambda r, _p: on_changed(field, round(r.get_value(), 4)))
        return row

    row = Adw.EntryRow(title=field.label)
    row.set_text(str(field.value))
    row.connect("apply", lambda r: on_changed(field, r.get_text()))
    row.connect("entry-activated", lambda r: on_changed(field, r.get_text()))
    return row


def build_list_item_row(item: ListItem, on_changed) -> Adw.ExpanderRow:
    row = Adw.ExpanderRow(title=item.summary or "(empty)")
    if not item.editable:
        row.set_subtitle("Read-only — this value is built by a script, not a plain setting.")
        row.set_sensitive(False)
        return row
    for field in item.fields:
        row.add_row(build_field_row(field, on_changed))
    return row
