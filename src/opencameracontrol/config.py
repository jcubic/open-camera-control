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
