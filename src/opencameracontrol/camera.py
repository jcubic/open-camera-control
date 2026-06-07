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

import json
import multiprocessing
import os
import re
import signal
from importlib import resources

import gphoto2 as gp

from opencameracontrol.config import CONFIG_DIR


class CameraError(Exception):
    pass


DEFAULT_PHOTO_SETTINGS = {
    "iso": "iso",
    "aperture": "f-number",
    "shutterspeed": "shutterspeed",
    "whitebalance": "whitebalance",
}

DEFAULT_VIDEO_PREFIX = "movie"


def _normalize_model_name(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _build_video_defaults():
    return {
        "iso": DEFAULT_VIDEO_PREFIX + DEFAULT_PHOTO_SETTINGS["iso"],
        "aperture": DEFAULT_VIDEO_PREFIX + DEFAULT_PHOTO_SETTINGS["aperture"],
        "shutterspeed": DEFAULT_VIDEO_PREFIX + DEFAULT_PHOTO_SETTINGS["shutterspeed"],
        "whitebalance": DEFAULT_PHOTO_SETTINGS["whitebalance"],
    }


def _resolve_model(raw_data):
    if "settings" in raw_data:
        settings = raw_data["settings"]
        return {"photo": dict(settings), "video": dict(settings)}

    if "photo" in raw_data and "video" in raw_data:
        return {"photo": raw_data["photo"], "video": raw_data["video"]}

    photo_overrides = raw_data.get("photo", {})
    photo = {**DEFAULT_PHOTO_SETTINGS, **photo_overrides}

    video_widgets = raw_data.get("video_widgets", False)
    if video_widgets:
        video_defaults = _build_video_defaults()
        video_overrides = raw_data.get("video", {})
        video = {**video_defaults, **video_overrides}
    else:
        video = dict(photo)

    return {"photo": photo, "video": video}


def _load_model_data(model_name, config_dir=None):
    if config_dir is None:
        config_dir = CONFIG_DIR

    config_path = os.path.join(config_dir, "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                user_config = json.load(f)
            models = user_config.get("models", {})
            if model_name in models:
                return _resolve_model(models[model_name])
        except (json.JSONDecodeError, OSError):
            pass

    normalized = _normalize_model_name(model_name)
    models_pkg = resources.files("opencameracontrol") / "models"
    model_file = models_pkg / f"{normalized}.json"
    try:
        data = json.loads(model_file.read_text(encoding="utf-8"))
        return _resolve_model(data)
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        pass

    return None


def _find_child(widget, name):
    for i in range(widget.count_children()):
        child = widget.get_child(i)
        if child.get_name() == name:
            return child
        found = _find_child(child, name)
        if found is not None:
            return found
    return None


def _camera_worker(req_q, resp_q, port, config_dir):
    os.environ["LC_ALL"] = "C"
    camera = gp.Camera()
    if port:
        port_info_list = gp.PortInfoList()
        port_info_list.load()
        idx = port_info_list.lookup_path(port)
        camera.set_port_info(port_info_list[idx])
    try:
        camera.init()
    except gp.GPhoto2Error as e:
        resp_q.put(("error", f"Failed to connect to camera: {e}"))
        return

    model_name = camera.get_abilities().model
    model_data = _load_model_data(model_name, config_dir)
    if model_data is None:
        normalized = _normalize_model_name(model_name)
        resp_q.put(
            (
                "error",
                f"No widget mapping found for camera model '{model_name}'.\n"
                f"Run: camera-control-detect\n"
                f"Then copy the output to:\n"
                f"  src/opencameracontrol/models/{normalized}.json (to contribute)\n"
                f"  OR ~/.open-camera-control/config.json under "
                f'"models"."{model_name}" (for personal use)',
            )
        )
        return

    config = camera.get_config()
    resp_q.put(("ok", model_name))

    def get_widget(setting_name, mode):
        settings = model_data.get(mode.lower())
        if not settings:
            return None
        widget_name = settings.get(setting_name)
        if not widget_name:
            return None
        return _find_child(config, widget_name)

    while True:
        try:
            cmd = req_q.get()
        except (EOFError, OSError):
            break

        action = cmd[0]
        try:
            if action == "get_choices":
                widget = get_widget(cmd[1], cmd[2])
                if widget is None:
                    resp_q.put(("ok", []))
                    continue
                try:
                    choices = [widget.get_choice(i) for i in range(widget.count_choices())]
                except gp.GPhoto2Error:
                    choices = []
                resp_q.put(("ok", choices))

            elif action == "get_value":
                widget = get_widget(cmd[1], cmd[2])
                if widget is None:
                    resp_q.put(("error", f"Widget not found for {cmd[1]}"))
                    continue
                resp_q.put(("ok", widget.get_value()))

            elif action == "is_readonly":
                widget = get_widget(cmd[1], cmd[2])
                resp_q.put(
                    (
                        "ok",
                        True if widget is None else bool(widget.get_readonly()),
                    )
                )

            elif action == "set_value":
                setting_name, value, mode = cmd[1], cmd[2], cmd[3]
                widget = get_widget(setting_name, mode)
                if widget is None:
                    resp_q.put(("error", f"Unknown setting: {setting_name}"))
                elif widget.get_readonly():
                    resp_q.put(
                        (
                            "error",
                            f"{setting_name} is read-only in {mode} mode",
                        )
                    )
                else:
                    widget.set_value(value)
                    resp_q.put(("ok", None))

            elif action == "apply":
                camera.set_config(config)
                config = camera.get_config()
                resp_q.put(("ok", None))

        except gp.GPhoto2Error as e:
            resp_q.put(("error", str(e)))
        except Exception as e:
            resp_q.put(("error", str(e)))


def detect_cameras():
    try:
        return list(gp.Camera.autodetect())
    except gp.GPhoto2Error:
        return []


class CameraBackend:
    def __init__(self):
        self._process = None
        self._req_q = None
        self._resp_q = None
        self._model_name = None

    def connect(self, port=None, config_dir=None):
        self._kill_worker()
        self._req_q = multiprocessing.Queue()
        self._resp_q = multiprocessing.Queue()
        self._process = multiprocessing.Process(
            target=_camera_worker,
            args=(self._req_q, self._resp_q, port, config_dir),
            daemon=True,
        )
        self._process.start()

        try:
            status, payload = self._resp_q.get(timeout=15)
        except Exception:
            self._kill_worker()
            raise CameraError("Timeout connecting to camera")

        if status == "error":
            self._process.join(timeout=2)
            self._process = None
            self._req_q = None
            self._resp_q = None
            raise CameraError(payload)

        self._model_name = payload

    @property
    def model_name(self):
        return self._model_name

    def _call(self, *args):
        if not self.connected:
            raise CameraError("Not connected")
        self._req_q.put(args)
        try:
            status, payload = self._resp_q.get(timeout=10)
        except Exception:
            raise CameraError("Camera not responding")
        if status == "error":
            raise CameraError(payload)
        return payload

    def get_choices(self, setting_name, mode="photo"):
        return self._call("get_choices", setting_name, mode)

    def get_value(self, setting_name, mode="photo"):
        return self._call("get_value", setting_name, mode)

    def is_readonly(self, setting_name, mode="photo"):
        return self._call("is_readonly", setting_name, mode)

    def set_value(self, setting_name, value, mode="photo"):
        self._call("set_value", setting_name, value, mode)

    def apply(self):
        self._call("apply")

    @property
    def connected(self):
        return self._process is not None and self._process.is_alive()

    def release(self):
        self._kill_worker()

    def _kill_worker(self):
        if self._process and self._process.is_alive():
            os.kill(self._process.pid, signal.SIGKILL)
            self._process.join(timeout=2)
        self._process = None
        self._req_q = None
        self._resp_q = None
        self._model_name = None
