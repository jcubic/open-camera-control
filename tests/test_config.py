import json
import os
import tempfile

import pytest

from opencameracontrol.config import DEFAULT_CONFIG, load_config


@pytest.fixture
def config_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestDefaultConfig:
    def test_returns_default_when_no_file(self, config_dir):
        config = load_config(config_dir)
        assert config == DEFAULT_CONFIG

    def test_default_has_white_balance_presets(self):
        assert "white_balance_presets" in DEFAULT_CONFIG
        presets = DEFAULT_CONFIG["white_balance_presets"]
        assert "Daylight" in presets
        assert "Cloudy" in presets
        assert "Shade" in presets
        assert "Tungsten" in presets
        assert "Fluorescent" in presets
        assert "Flash" in presets

    def test_default_preset_values_are_ints(self):
        for name, kelvin in DEFAULT_CONFIG["white_balance_presets"].items():
            assert isinstance(kelvin, int), f"{name} should map to an int"

    def test_default_has_kelvin_range(self):
        kr = DEFAULT_CONFIG["kelvin_range"]
        assert kr["min"] < kr["max"]
        assert kr["step"] > 0

    def test_default_kelvin_range_values(self):
        kr = DEFAULT_CONFIG["kelvin_range"]
        assert kr["min"] == 2500
        assert kr["max"] == 10000
        assert kr["step"] == 100


class TestConfigLoading:
    def test_loads_valid_config(self, config_dir):
        custom = {
            "white_balance_presets": {
                "Daylight": 5500,
                "Overcast": 6200,
            },
            "kelvin_range": {"min": 2000, "max": 12000, "step": 50},
        }
        with open(os.path.join(config_dir, "config.json"), "w") as f:
            json.dump(custom, f)

        config = load_config(config_dir)
        assert config["white_balance_presets"]["Daylight"] == 5500
        assert config["white_balance_presets"]["Overcast"] == 6200
        assert config["kelvin_range"]["min"] == 2000

    def test_partial_config_merges_with_defaults(self, config_dir):
        partial = {"white_balance_presets": {"MyPreset": 4200}}
        with open(os.path.join(config_dir, "config.json"), "w") as f:
            json.dump(partial, f)

        config = load_config(config_dir)
        assert config["white_balance_presets"] == {"MyPreset": 4200}
        assert config["kelvin_range"] == DEFAULT_CONFIG["kelvin_range"]

    def test_invalid_json_returns_defaults(self, config_dir):
        with open(os.path.join(config_dir, "config.json"), "w") as f:
            f.write("not valid json {{{")

        config = load_config(config_dir)
        assert config == DEFAULT_CONFIG

    def test_creates_config_dir_if_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = os.path.join(tmpdir, "subdir", "config")
            config = load_config(nested)
            assert config == DEFAULT_CONFIG
            assert os.path.isdir(nested)


class TestPresetLookup:
    def test_preset_kelvin_values(self):
        presets = DEFAULT_CONFIG["white_balance_presets"]
        assert presets["Daylight"] == 5600
        assert presets["Tungsten"] == 3200

    def test_preset_names_are_strings(self):
        for name in DEFAULT_CONFIG["white_balance_presets"]:
            assert isinstance(name, str)
