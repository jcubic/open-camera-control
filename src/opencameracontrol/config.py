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
import os
from copy import deepcopy

DEFAULT_CONFIG = {
    "white_balance_presets": {
        "Daylight": 5600,
        "Cloudy": 6500,
        "Shade": 7500,
        "Tungsten": 3200,
        "Fluorescent": 4000,
        "Flash": 5400,
    },
    "kelvin_range": {
        "min": 2500,
        "max": 10000,
        "step": 100,
    },
}

CONFIG_DIR = os.path.expanduser("~/.open-camera-control")

WB_KELVIN = {
    "Daylight": 5600,
    "Direct Sunlight": 5600,
    "Cloudy": 6500,
    "Shade": 7500,
    "Tungsten": 3200,
    "Tungsten 2": 3200,
    "Flash": 5400,
    "Standard Flash": 5400,
    "Fluorescent": 4000,
    "Fluorescent Lamp 1": 2700,
    "Fluorescent Lamp 2": 3000,
    "Fluorescent Lamp 3": 3700,
    "Fluorescent Lamp 4": 4200,
    "Fluorescent Lamp 5": 5000,
    "Fluorescent H": 3700,
    "Fluorescent: Cold White": 4200,
    "Fluorescent: Day White": 5000,
    "Fluorescent: Daylight": 6500,
    "Fluorescent: Tungsten": 3000,
    "Fluorescent: Warm White": 3000,
    "Fluorescent: White": 3700,
    "Underwater": 5000,
    "Natural Light Auto": 5500,
    "Automatic Cool": 5000,
    "Automatic Warm": 6000,
}


def lookup_wb_kelvin(name, user_presets=None):
    if user_presets:
        if name in user_presets:
            return user_presets[name]
        name_lower = name.lower()
        for preset_name, kelvin in user_presets.items():
            if preset_name.lower() == name_lower:
                return kelvin

    if name in WB_KELVIN:
        return WB_KELVIN[name]

    name_lower = name.lower()
    for wb_name, kelvin in WB_KELVIN.items():
        if wb_name.lower() == name_lower:
            return kelvin

    return None


def find_color_temp_choice(choices):
    for name in choices:
        if "color" in name.lower() and "temperature" in name.lower():
            return name
    return None


def find_closest_wb(kelvin, choices, user_presets=None):
    best_name = None
    best_diff = None
    for name in choices:
        k = lookup_wb_kelvin(name, user_presets)
        if k is None:
            continue
        diff = abs(k - kelvin)
        if best_diff is None or diff < best_diff:
            best_diff = diff
            best_name = name
    return best_name


def load_config(config_dir=None):
    if config_dir is None:
        config_dir = CONFIG_DIR

    os.makedirs(config_dir, exist_ok=True)

    config_path = os.path.join(config_dir, "config.json")
    config = deepcopy(DEFAULT_CONFIG)

    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                user_config = json.load(f)
        except (json.JSONDecodeError, OSError):
            return config

        for key in user_config:
            if key in config:
                config[key] = user_config[key]

    return config
