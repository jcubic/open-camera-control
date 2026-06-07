import json
import os

from opencameracontrol.camera import (
    DEFAULT_PHOTO_SETTINGS,
    DEFAULT_VIDEO_PREFIX,
    _load_model_data,
    _normalize_model_name,
)


def test_normalize_model_name():
    assert _normalize_model_name("Nikon DSC D780") == "nikon_dsc_d780"
    assert _normalize_model_name("Fuji Fujifilm X-Pro3") == "fuji_fujifilm_x_pro3"


def test_default_photo_settings_keys():
    assert set(DEFAULT_PHOTO_SETTINGS.keys()) == {
        "iso",
        "aperture",
        "shutterspeed",
        "whitebalance",
    }


def test_default_video_prefix():
    assert DEFAULT_VIDEO_PREFIX == "movie"


class TestLoadModelData:
    def _write_model_file(self, tmpdir, filename, data):
        os.makedirs(tmpdir, exist_ok=True)
        path = os.path.join(tmpdir, filename)
        with open(path, "w") as f:
            json.dump(data, f)
        return path

    def test_full_photo_video_format(self, tmp_path):
        config_dir = str(tmp_path / "config")
        os.makedirs(config_dir)
        config_path = os.path.join(config_dir, "config.json")
        with open(config_path, "w") as f:
            json.dump(
                {
                    "models": {
                        "Test Camera": {
                            "photo": {
                                "iso": "custom-iso",
                                "aperture": "custom-aperture",
                                "shutterspeed": "custom-ss",
                                "whitebalance": "custom-wb",
                            },
                            "video": {
                                "iso": "vid-iso",
                                "aperture": "vid-aperture",
                                "shutterspeed": "vid-ss",
                                "whitebalance": "vid-wb",
                            },
                        }
                    }
                },
                f,
            )
        result = _load_model_data("Test Camera", config_dir)
        assert result["photo"]["iso"] == "custom-iso"
        assert result["video"]["iso"] == "vid-iso"

    def test_bundled_model_with_video_widgets_true(self):
        result = _load_model_data("Nikon DSC D780")
        assert result is not None
        assert result["photo"]["shutterspeed"] == "shutterspeed2"
        assert result["video"]["iso"] == "movieiso"
        assert result["video"]["aperture"] == "movief-number"
        assert result["video"]["shutterspeed"] == "movieshutterspeed"
        assert result["video"]["whitebalance"] == "whitebalance"

    def test_bundled_model_with_video_widgets_false(self):
        result = _load_model_data("Fuji Fujifilm X-Pro3")
        assert result is not None
        assert result["photo"]["iso"] == "iso"
        assert result["video"]["iso"] == "iso"
        assert result["video"]["aperture"] == "f-number"
        assert result["photo"] == result["video"]

    def test_defaults_applied_when_no_overrides(self):
        result = _load_model_data("Fuji Fujifilm X-Pro3")
        assert result["photo"]["iso"] == DEFAULT_PHOTO_SETTINGS["iso"]
        assert result["photo"]["aperture"] == DEFAULT_PHOTO_SETTINGS["aperture"]
        assert result["photo"]["shutterspeed"] == DEFAULT_PHOTO_SETTINGS["shutterspeed"]
        assert result["photo"]["whitebalance"] == DEFAULT_PHOTO_SETTINGS["whitebalance"]

    def test_overrides_merged_with_defaults(self):
        result = _load_model_data("Nikon DSC D780")
        assert result["photo"]["iso"] == "iso"
        assert result["photo"]["shutterspeed"] == "shutterspeed2"
        assert result["photo"]["aperture"] == "f-number"

    def test_unknown_model_returns_none(self):
        result = _load_model_data("Nonexistent Camera XYZ")
        assert result is None

    def test_user_config_overrides_bundled(self, tmp_path):
        config_dir = str(tmp_path / "config")
        os.makedirs(config_dir)
        config_path = os.path.join(config_dir, "config.json")
        with open(config_path, "w") as f:
            json.dump(
                {
                    "models": {
                        "Nikon DSC D780": {
                            "photo": {"shutterspeed": "custom-ss"},
                            "video": {"iso": "custom-video-iso"},
                        }
                    }
                },
                f,
            )
        result = _load_model_data("Nikon DSC D780", config_dir)
        assert result["photo"]["shutterspeed"] == "custom-ss"
        assert result["video"]["iso"] == "custom-video-iso"

    def test_old_settings_format_still_works(self, tmp_path):
        config_dir = str(tmp_path / "config")
        os.makedirs(config_dir)
        config_path = os.path.join(config_dir, "config.json")
        with open(config_path, "w") as f:
            json.dump(
                {
                    "models": {
                        "Old Camera": {
                            "settings": {
                                "iso": "old-iso",
                                "aperture": "old-aperture",
                                "shutterspeed": "old-ss",
                                "whitebalance": "old-wb",
                            }
                        }
                    }
                },
                f,
            )
        result = _load_model_data("Old Camera", config_dir)
        assert result["photo"]["iso"] == "old-iso"
        assert result["video"]["iso"] == "old-iso"

    def test_video_widgets_flag_generates_movie_prefixed(self):
        result = _load_model_data("Nikon DSC D780")
        assert result["video"]["iso"] == "movieiso"
        assert result["video"]["aperture"] == "movief-number"

    def test_video_widgets_false_copies_photo_settings(self):
        result = _load_model_data("Fuji Fujifilm X-Pro3")
        for key in ("iso", "aperture", "shutterspeed", "whitebalance"):
            assert result["video"][key] == result["photo"][key]
