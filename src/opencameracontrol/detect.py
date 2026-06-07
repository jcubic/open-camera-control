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
import re
import sys

import gphoto2 as gp

from opencameracontrol.camera import DEFAULT_PHOTO_SETTINGS, DEFAULT_VIDEO_PREFIX

WIDGET_TYPES = {
    0: "window",
    1: "section",
    2: "text",
    3: "range",
    4: "toggle",
    5: "radio",
    6: "menu",
    7: "button",
    8: "date",
}

SETTING_KEYWORDS = {
    "iso": ["iso"],
    "aperture": ["f-number", "aperture"],
    "shutterspeed": ["shutter speed", "shutterspeed", "exposure time"],
    "whitebalance": ["whitebalance", "white balance"],
}

VIDEO_KEYWORDS = {
    "iso": ["movieiso", "videoiso"],
    "aperture": ["movief-number", "movieaperture", "videoaperture"],
    "shutterspeed": ["movieshutterspeed", "videoshutterspeed"],
    "whitebalance": ["moviewhitebalance", "videowhitebalance"],
}


def _normalize_model_name(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _walk_config(widget, depth=0):
    results = []
    for i in range(widget.count_children()):
        child = widget.get_child(i)
        wtype = child.get_type()
        if wtype in (0, 1):
            results.extend(_walk_config(child, depth + 1))
        else:
            info = {
                "name": child.get_name(),
                "label": child.get_label(),
                "type": WIDGET_TYPES.get(wtype, str(wtype)),
                "readonly": bool(child.get_readonly()),
                "value": child.get_value(),
            }
            try:
                n = child.count_choices()
                if n > 0:
                    info["choices"] = [child.get_choice(j) for j in range(n)]
            except gp.GPhoto2Error:
                pass
            results.append(info)
    return results


def _suggest_settings(widgets):
    suggestions = {}
    for setting, keywords in SETTING_KEYWORDS.items():
        candidates = []
        for w in widgets:
            label_lower = w["label"].lower()
            name_lower = w["name"].lower()
            for kw in keywords:
                if kw in label_lower or kw in name_lower:
                    candidates.append(w)
                    break

        writable = [c for c in candidates if not c["readonly"]]
        if writable:
            suggestions[setting] = writable[0]["name"]
        elif candidates:
            suggestions[setting] = candidates[0]["name"]

    return suggestions


def _suggest_video_settings(widgets):
    suggestions = {}
    for setting, keywords in VIDEO_KEYWORDS.items():
        for w in widgets:
            name_lower = w["name"].lower()
            for kw in keywords:
                if kw in name_lower:
                    suggestions[setting] = w["name"]
                    break
            if setting in suggestions:
                break

    return suggestions


def main():
    camera = gp.Camera()
    try:
        camera.init()
    except gp.GPhoto2Error as e:
        print(f"Error: Failed to connect to camera: {e}", file=sys.stderr)
        sys.exit(1)

    model = camera.get_abilities().model
    normalized = _normalize_model_name(model)
    print(f"Camera model: {model}")
    print(f"Model file:   {normalized}.json")
    print()

    config = camera.get_config()
    widgets = _walk_config(config)

    suggestions = _suggest_settings(widgets)

    print("--- All widgets ---")
    for w in widgets:
        ro = " (readonly)" if w["readonly"] else ""
        choices = f" [{len(w.get('choices', []))} choices]" if "choices" in w else ""
        print(f"  {w['name']:30s} {w['label']:30s} {w['type']:6s}{ro}{choices}")
    print()

    video_suggestions = _suggest_video_settings(widgets)

    print("--- Suggested photo mapping ---")
    for setting in ("iso", "aperture", "shutterspeed", "whitebalance"):
        name = suggestions.get(setting, "???")
        is_default = name == DEFAULT_PHOTO_SETTINGS.get(setting)
        marker = " (default)" if is_default else ""
        print(f"  {setting:15s} -> {name}{marker}")
    print()

    has_video_widgets = bool(video_suggestions)

    print("--- Suggested video mapping ---")
    if has_video_widgets:
        print("  (camera has separate video widgets)")
    else:
        print("  (same as photo)")
    for setting in ("iso", "aperture", "shutterspeed", "whitebalance"):
        name = video_suggestions.get(setting, suggestions.get(setting, "???"))
        print(f"  {setting:15s} -> {name}")
    print()

    photo_overrides = {}
    for setting in ("iso", "aperture", "shutterspeed", "whitebalance"):
        detected = suggestions.get(setting, "")
        if detected and detected != DEFAULT_PHOTO_SETTINGS.get(setting):
            photo_overrides[setting] = detected

    model_data = {"model": model}

    if has_video_widgets:
        model_data["video_widgets"] = True

    if photo_overrides:
        model_data["photo"] = photo_overrides

    if has_video_widgets:
        video_defaults = {
            "iso": DEFAULT_VIDEO_PREFIX + DEFAULT_PHOTO_SETTINGS["iso"],
            "aperture": DEFAULT_VIDEO_PREFIX + DEFAULT_PHOTO_SETTINGS["aperture"],
            "shutterspeed": DEFAULT_VIDEO_PREFIX + DEFAULT_PHOTO_SETTINGS["shutterspeed"],
            "whitebalance": DEFAULT_PHOTO_SETTINGS["whitebalance"],
        }
        video_overrides = {}
        for setting in ("iso", "aperture", "shutterspeed", "whitebalance"):
            detected = video_suggestions.get(setting, "")
            if detected and detected != video_defaults.get(setting):
                video_overrides[setting] = detected
        if video_overrides:
            model_data["video"] = video_overrides

    filename = f"{normalized}.json"
    print(f"--- Model file content ({filename}) ---")
    print(json.dumps(model_data, indent=4))
    print()
    print("To contribute this model, save the JSON above as:")
    print(f"  src/opencameracontrol/models/{filename}")
    print()
    print("Or add to your ~/.open-camera-control/config.json:")
    user_config_example = {"models": {model: {k: v for k, v in model_data.items() if k != "model"}}}
    print(json.dumps(user_config_example, indent=4))

    camera = None


if __name__ == "__main__":
    main()
