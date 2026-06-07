import json
import os
import tempfile

import pytest

from opencameracontrol.config import (
    DEFAULT_CONFIG,
    WB_KELVIN,
    find_closest_wb,
    find_color_temp_choice,
    load_config,
    lookup_wb_kelvin,
)


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


class TestWBKelvin:
    def test_all_values_are_ints(self):
        for name, kelvin in WB_KELVIN.items():
            assert isinstance(kelvin, int), f"{name} should map to an int"

    def test_all_keys_are_strings(self):
        for name in WB_KELVIN:
            assert isinstance(name, str)

    def test_standard_modes_present(self):
        standard = ["Daylight", "Cloudy", "Shade", "Tungsten", "Flash", "Fluorescent"]
        for name in standard:
            assert name in WB_KELVIN, f"{name} should be in WB_KELVIN"

    def test_standard_values(self):
        assert WB_KELVIN["Daylight"] == 5600
        assert WB_KELVIN["Cloudy"] == 6500
        assert WB_KELVIN["Shade"] == 7500
        assert WB_KELVIN["Tungsten"] == 3200
        assert WB_KELVIN["Flash"] == 5400
        assert WB_KELVIN["Fluorescent"] == 4000

    def test_fluorescent_variants_present(self):
        variants = [
            "Fluorescent Lamp 1",
            "Fluorescent Lamp 2",
            "Fluorescent Lamp 3",
            "Fluorescent Lamp 4",
            "Fluorescent Lamp 5",
            "Fluorescent H",
            "Fluorescent: Cold White",
            "Fluorescent: Day White",
            "Fluorescent: Daylight",
            "Fluorescent: Tungsten",
            "Fluorescent: Warm White",
            "Fluorescent: White",
        ]
        for name in variants:
            assert name in WB_KELVIN, f"{name} should be in WB_KELVIN"

    def test_fluorescent_lamp_ordering(self):
        assert WB_KELVIN["Fluorescent Lamp 1"] < WB_KELVIN["Fluorescent Lamp 5"]

    def test_special_modes_present(self):
        assert "Underwater" in WB_KELVIN
        assert "Tungsten 2" in WB_KELVIN

    def test_values_in_valid_range(self):
        for name, kelvin in WB_KELVIN.items():
            assert 1500 <= kelvin <= 10000, f"{name}: {kelvin}K out of range"


class TestLookupWBKelvin:
    def test_exact_match(self):
        assert lookup_wb_kelvin("Daylight") == 5600

    def test_case_insensitive_match(self):
        assert lookup_wb_kelvin("daylight") == 5600
        assert lookup_wb_kelvin("CLOUDY") == 6500

    def test_user_presets_override(self):
        assert lookup_wb_kelvin("Daylight", {"Daylight": 5500}) == 5500

    def test_user_presets_add_new(self):
        assert lookup_wb_kelvin("My Custom", {"My Custom": 4200}) == 4200

    def test_unknown_returns_none(self):
        assert lookup_wb_kelvin("Something Unknown") is None

    def test_auto_returns_none(self):
        assert lookup_wb_kelvin("Auto") is None

    def test_custom_preset_returns_none(self):
        assert lookup_wb_kelvin("Preset Custom 1") is None

    def test_user_presets_case_insensitive(self):
        assert lookup_wb_kelvin("my preset", {"My Preset": 3800}) == 3800


class TestFindClosestWB:
    def test_exact_match(self):
        choices = ["Auto", "Daylight", "Cloudy", "Shade", "Tungsten"]
        assert find_closest_wb(5600, choices) == "Daylight"

    def test_closest_lower(self):
        choices = ["Auto", "Daylight", "Cloudy", "Tungsten"]
        assert find_closest_wb(3000, choices) == "Tungsten"

    def test_closest_higher(self):
        choices = ["Auto", "Daylight", "Cloudy", "Tungsten"]
        assert find_closest_wb(8000, choices) == "Cloudy"

    def test_midpoint_picks_one(self):
        choices = ["Daylight", "Flash"]
        result = find_closest_wb(5500, choices)
        assert result in ("Daylight", "Flash")

    def test_skips_unmapped_choices(self):
        choices = ["Auto", "Preset Custom 1", "Daylight"]
        assert find_closest_wb(5600, choices) == "Daylight"

    def test_all_unmapped_returns_none(self):
        choices = ["Auto", "Preset Custom 1"]
        assert find_closest_wb(5600, choices) is None

    def test_empty_choices_returns_none(self):
        assert find_closest_wb(5600, []) is None

    def test_user_presets_used(self):
        choices = ["Auto", "My Mode"]
        assert find_closest_wb(4100, choices, {"My Mode": 4000}) == "My Mode"

    def test_single_mapped_choice(self):
        choices = ["Auto", "Tungsten"]
        assert find_closest_wb(9000, choices) == "Tungsten"


class TestFindColorTempChoice:
    def test_standard_name(self):
        choices = ["Auto", "Daylight", "Color Temperature", "Flash"]
        assert find_color_temp_choice(choices) == "Color Temperature"

    def test_sony_name(self):
        choices = ["Auto", "Daylight", "Choose Color Temperature", "Flash"]
        assert find_color_temp_choice(choices) == "Choose Color Temperature"

    def test_case_insensitive(self):
        choices = ["Auto", "color temperature"]
        assert find_color_temp_choice(choices) == "color temperature"

    def test_not_present(self):
        choices = ["Auto", "Daylight", "Cloudy", "Tungsten"]
        assert find_color_temp_choice(choices) is None

    def test_empty_choices(self):
        assert find_color_temp_choice([]) is None

    def test_does_not_match_partial(self):
        choices = ["Auto", "Temperature"]
        assert find_color_temp_choice(choices) is None
