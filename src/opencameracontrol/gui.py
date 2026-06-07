# Copyright (C) 2026 Jakub T. Jankiewicz <https://jakub.jankiewicz.org/>
#
# This file is part of Open Camera Control.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import os
import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk

from opencameracontrol.camera import CameraBackend, CameraError, detect_cameras
from opencameracontrol.config import find_closest_wb, lookup_wb_kelvin
from opencameracontrol.settings import SettingChoices

CSS = b"""
.connect-btn {
    background-image: none;
    background-color: #4e9a06;
    color: white;
    border-color: #3d7c05;
}
.connect-btn:hover {
    background-color: #73d216;
    border-color: #4e9a06;
}
.connect-btn.disconnecting {
    background-color: #cc0000;
    border-color: #a40000;
}
.connect-btn.disconnecting:hover {
    background-color: #ef2929;
    border-color: #cc0000;
}
.connect-progress progress {
    background-image: repeating-linear-gradient(
        45deg,
        rgba(255,255,255,0.15),
        rgba(255,255,255,0.15) 10px,
        transparent 10px,
        transparent 20px
    );
    background-color: #4e9a06;
    border-radius: 0;
    min-height: 4px;
}
.connect-progress trough {
    min-height: 4px;
    background-color: #d3d7cf;
    border-radius: 0;
}
"""


class SettingRow(Gtk.Box):
    def __init__(self, label, choices):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._choices = SettingChoices(choices)
        self._updating = False
        self._initial_value = None

        header = Gtk.Label(label=label, xalign=0)
        header.get_style_context().add_class("setting-label")
        self.pack_start(header, False, False, 0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.pack_start(hbox, False, False, 0)

        adj = Gtk.Adjustment(
            value=0,
            lower=0,
            upper=max(0, self._choices.max_index),
            step_increment=1,
            page_increment=1,
        )
        self._scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        self._scale.set_draw_value(False)
        self._scale.set_digits(0)
        self._scale.set_hexpand(True)
        self._scale.connect("value-changed", self._on_slider_changed)
        hbox.pack_start(self._scale, True, True, 0)

        self._entry = Gtk.Entry()
        self._entry.set_width_chars(8)
        self._entry.connect("activate", self._on_entry_activate)
        hbox.pack_start(self._entry, False, False, 0)

        self.set_margin_bottom(8)

    def get_current_value(self):
        return self._entry.get_text().strip()

    def is_changed(self):
        return self.get_current_value() != self._initial_value

    def mark_applied(self):
        self._initial_value = self.get_current_value()

    def set_value(self, value):
        idx = self._choices.index_of(value)
        if idx is not None:
            self._updating = True
            self._scale.set_value(idx)
            self._entry.set_text(value)
            self._initial_value = value
            self._updating = False

    def _on_slider_changed(self, scale):
        if self._updating:
            return
        idx = int(scale.get_value())
        value = self._choices.value_at(idx)
        if value is not None:
            self._updating = True
            self._entry.set_text(value)
            self._updating = False

    def _on_entry_activate(self, entry):
        text = entry.get_text().strip()
        match = self._choices.find_closest(text)
        if match:
            idx = self._choices.index_of(match)
            self._updating = True
            self._entry.set_text(match)
            if idx is not None:
                self._scale.set_value(idx)
            self._updating = False


class WhiteBalanceRow(Gtk.Box):
    def __init__(self, presets, kelvin_range, camera_choices=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._presets = presets
        self._kelvin_min = kelvin_range["min"]
        self._kelvin_max = kelvin_range["max"]
        self._kelvin_step = kelvin_range["step"]
        self._updating = False
        self._initial_preset = None
        self._initial_kelvin = None

        header = Gtk.Label(label="White Balance", xalign=0)
        header.get_style_context().add_class("setting-label")
        self.pack_start(header, False, False, 0)

        self._combo = Gtk.ComboBoxText()
        if camera_choices:
            self._preset_names = list(camera_choices)
        else:
            self._preset_names = list(presets.keys())
        for name in self._preset_names:
            self._combo.append_text(name)
        self._combo.set_active(0)
        self._combo.connect("changed", self._on_combo_changed)
        self.pack_start(self._combo, False, False, 0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.pack_start(hbox, False, False, 0)

        adj = Gtk.Adjustment(
            value=self._kelvin_min,
            lower=self._kelvin_min,
            upper=self._kelvin_max,
            step_increment=self._kelvin_step,
            page_increment=self._kelvin_step * 5,
        )
        self._scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        self._scale.set_draw_value(False)
        self._scale.set_digits(0)
        self._scale.set_hexpand(True)
        self._scale.connect("value-changed", self._on_slider_changed)
        hbox.pack_start(self._scale, True, True, 0)

        self._entry = Gtk.Entry()
        self._entry.set_width_chars(8)
        self._entry.set_text(str(self._kelvin_min))
        self._entry.connect("activate", self._on_entry_activate)
        hbox.pack_start(self._entry, False, False, 0)

        kelvin_label = Gtk.Label(label="K")
        hbox.pack_start(kelvin_label, False, False, 0)

        self.set_margin_bottom(8)

    def get_wb_value(self):
        return self._combo.get_active_text()

    def get_kelvin(self):
        return int(self._scale.get_value())

    def is_changed(self):
        return (
            self.get_wb_value() != self._initial_preset or self.get_kelvin() != self._initial_kelvin
        )

    def mark_applied(self):
        self._initial_preset = self.get_wb_value()
        self._initial_kelvin = self.get_kelvin()

    def set_active_mode(self, mode_name):
        if mode_name in self._preset_names:
            idx = self._preset_names.index(mode_name)
            self._updating = True
            self._combo.set_active(idx)
            kelvin = self._lookup_kelvin(mode_name)
            if kelvin is not None:
                self._scale.set_value(kelvin)
                self._entry.set_text(str(kelvin))
            self._initial_preset = mode_name
            self._initial_kelvin = self.get_kelvin()
            self._updating = False

    def _lookup_kelvin(self, name):
        return lookup_wb_kelvin(name, self._presets)

    def _on_combo_changed(self, combo):
        if self._updating:
            return
        name = combo.get_active_text()
        if not name:
            return
        kelvin = self._lookup_kelvin(name)
        if kelvin is not None:
            self._updating = True
            self._scale.set_value(kelvin)
            self._entry.set_text(str(kelvin))
            self._updating = False

    def _on_slider_changed(self, scale):
        if self._updating:
            return
        kelvin = int(scale.get_value())
        self._updating = True
        self._entry.set_text(str(kelvin))
        closest = find_closest_wb(kelvin, self._preset_names, self._presets)
        if closest and closest in self._preset_names:
            self._combo.set_active(self._preset_names.index(closest))
        self._updating = False

    def _on_entry_activate(self, entry):
        text = entry.get_text().strip()
        try:
            kelvin = int(text)
        except ValueError:
            return
        kelvin = max(self._kelvin_min, min(kelvin, self._kelvin_max))
        self._updating = True
        self._scale.set_value(kelvin)
        self._entry.set_text(str(kelvin))
        closest = find_closest_wb(kelvin, self._preset_names, self._presets)
        if closest and closest in self._preset_names:
            self._combo.set_active(self._preset_names.index(closest))
        self._updating = False


class CameraControlWindow(Gtk.Window):
    def __init__(self, config):
        super().__init__(title="Open Camera Control")
        self.set_default_size(450, 500)
        self._camera = CameraBackend()
        self._config = config
        self._tabs = {}
        self._cameras = []
        self._pulse_timer = None

        self.connect("destroy", self._on_destroy)

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox)

        toolbar = self._build_toolbar()
        vbox.pack_start(toolbar, False, False, 0)

        self._progress = Gtk.ProgressBar()
        self._progress.get_style_context().add_class("connect-progress")
        self._progress.set_no_show_all(True)
        vbox.pack_start(self._progress, False, False, 0)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(sep, False, False, 0)

        self._notebook = Gtk.Notebook()
        self._notebook.set_sensitive(False)
        vbox.pack_start(self._notebook, True, True, 0)

        self._refresh_camera_list()

    def _build_toolbar(self):
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hbox.set_margin_start(8)
        hbox.set_margin_end(8)
        hbox.set_margin_top(6)
        hbox.set_margin_bottom(6)

        self._camera_combo = Gtk.ComboBoxText()
        self._camera_combo.set_hexpand(True)
        hbox.pack_start(self._camera_combo, True, True, 0)

        refresh_btn = Gtk.Button()
        refresh_icon = Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        refresh_btn.set_image(refresh_icon)
        refresh_btn.set_tooltip_text("Refresh camera list")
        refresh_btn.connect("clicked", self._on_refresh)
        hbox.pack_start(refresh_btn, False, False, 0)

        self._connect_btn = Gtk.Button(label="Connect")
        self._connect_btn.get_style_context().add_class("connect-btn")
        self._connect_btn.connect("clicked", self._on_connect_toggle)
        hbox.pack_start(self._connect_btn, False, False, 0)

        return hbox

    def _refresh_camera_list(self):
        self._cameras = detect_cameras()
        self._camera_combo.remove_all()
        for name, port in self._cameras:
            self._camera_combo.append_text(f"{name} ({port})")
        if self._cameras:
            self._camera_combo.set_active(0)
            self._connect_btn.set_sensitive(True)
        else:
            self._camera_combo.append_text("No cameras detected")
            self._camera_combo.set_active(0)
            self._camera_combo.set_sensitive(False)
            self._connect_btn.set_sensitive(False)

    def _on_refresh(self, _button):
        if self._camera.connected:
            return
        self._camera_combo.set_sensitive(True)
        self._refresh_camera_list()

    def _on_connect_toggle(self, _button):
        if self._camera.connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        idx = self._camera_combo.get_active()
        if idx < 0 or idx >= len(self._cameras):
            return

        _name, port = self._cameras[idx]

        self._connect_btn.set_label("Connecting…")
        self._connect_btn.set_sensitive(False)
        self._camera_combo.set_sensitive(False)
        self._start_pulse()

        thread = threading.Thread(target=self._connect_worker, args=(port,), daemon=True)
        thread.start()

    def _connect_worker(self, port):
        try:
            self._camera.connect(port=port)
            GLib.idle_add(self._on_connected)
        except CameraError as e:
            GLib.idle_add(self._on_connect_error, str(e))

    def _on_connected(self):
        self._stop_pulse()
        self._connect_btn.set_label("Disconnect")
        self._connect_btn.get_style_context().add_class("disconnecting")
        self._connect_btn.set_sensitive(True)

        self._build_tabs()
        self._notebook.set_sensitive(True)
        self._notebook.show_all()

    def _on_connect_error(self, message):
        self._stop_pulse()
        self._connect_btn.set_label("Connect")
        self._connect_btn.set_sensitive(True)
        self._camera_combo.set_sensitive(True)
        self._show_error(message)

    def _disconnect(self):
        self._camera.release()

        self._connect_btn.set_label("Connect")
        self._connect_btn.get_style_context().remove_class("disconnecting")
        self._camera_combo.set_sensitive(True)

        self._clear_tabs()
        self._notebook.set_sensitive(False)

    def _build_tabs(self):
        self._clear_tabs()
        for mode in ("Photo", "Video"):
            tab = self._build_tab(mode)
            self._notebook.append_page(tab, Gtk.Label(label=mode))

    def _clear_tabs(self):
        self._tabs.clear()
        while self._notebook.get_n_pages() > 0:
            self._notebook.remove_page(0)

    def _build_tab(self, mode):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        vbox.set_margin_start(12)
        vbox.set_margin_end(12)
        vbox.set_margin_top(12)
        vbox.set_margin_bottom(12)

        rows = {}
        settings = [
            ("Aperture", "aperture"),
            ("Shutter Speed", "shutterspeed"),
            ("ISO", "iso"),
        ]

        for label, setting_name in settings:
            try:
                choices = self._camera.get_choices(setting_name, mode)
                current = self._camera.get_value(setting_name, mode)
                readonly = self._camera.is_readonly(setting_name, mode)
            except Exception:
                choices = []
                current = None
                readonly = True

            row = SettingRow(label, choices)
            if current:
                row.set_value(current)
            if readonly:
                row.set_sensitive(False)
            rows[setting_name] = row
            vbox.pack_start(row, False, False, 0)

        wb_presets = self._config["white_balance_presets"]
        kelvin_range = self._config["kelvin_range"]

        try:
            wb_choices = self._camera.get_choices("whitebalance", mode)
            current_wb = self._camera.get_value("whitebalance", mode)
        except Exception:
            wb_choices = list(wb_presets.keys())
            current_wb = None

        wb_row = WhiteBalanceRow(wb_presets, kelvin_range, wb_choices)

        if current_wb:
            wb_row.set_active_mode(current_wb)

        rows["whitebalance"] = wb_row
        vbox.pack_start(wb_row, False, False, 0)

        self._tabs[mode] = rows

        apply_btn = Gtk.Button(label="Apply")
        apply_btn.get_style_context().add_class("suggested-action")
        apply_btn.connect("clicked", self._on_apply, mode)
        vbox.pack_end(apply_btn, False, False, 8)

        return vbox

    def _on_apply(self, _button, mode):
        rows = self._tabs[mode]
        errors = []
        changed = False

        for setting_name in ("iso", "aperture", "shutterspeed"):
            row = rows[setting_name]
            if not row.is_changed():
                continue
            value = row.get_current_value()
            if value:
                try:
                    self._camera.set_value(setting_name, value, mode)
                    changed = True
                except Exception as e:
                    errors.append(str(e))

        wb_row = rows["whitebalance"]
        if wb_row.is_changed():
            wb_value = wb_row.get_wb_value()
            if wb_value:
                try:
                    self._camera.set_value("whitebalance", wb_value, mode)
                    changed = True
                except Exception as e:
                    errors.append(str(e))

        if changed:
            try:
                self._camera.apply()
                for row in rows.values():
                    row.mark_applied()
            except Exception as e:
                errors.append(str(e))

        if errors:
            self._show_error("\n".join(errors))

    def _start_pulse(self):
        self._progress.show()
        self._pulse_timer = GLib.timeout_add(80, self._pulse_tick)

    def _pulse_tick(self):
        self._progress.pulse()
        return True

    def _stop_pulse(self):
        if self._pulse_timer is not None:
            GLib.source_remove(self._pulse_timer)
            self._pulse_timer = None
        self._progress.set_fraction(0)
        self._progress.hide()

    def _on_destroy(self, _widget):
        self._camera.release()
        os._exit(0)

    def _show_error(self, message):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=message,
        )
        dialog.run()
        dialog.destroy()
