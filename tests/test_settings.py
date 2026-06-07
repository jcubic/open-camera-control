from opencameracontrol.settings import SettingChoices

ISO_CHOICES = ["100", "200", "400", "800", "1600", "3200", "6400", "12800"]
APERTURE_CHOICES = ["f/1.4", "f/2", "f/2.8", "f/4", "f/5.6", "f/8", "f/11", "f/16", "f/22"]
SHUTTER_CHOICES = [
    "30",
    "15",
    "8",
    "4",
    "2",
    "1",
    "1/2",
    "1/4",
    "1/8",
    "1/15",
    "1/30",
    "1/60",
    "1/125",
    "1/250",
    "1/500",
    "1/1000",
    "1/2000",
    "1/4000",
    "1/8000",
]


class TestChoiceListParsing:
    def test_creates_from_list(self):
        sc = SettingChoices(ISO_CHOICES)
        assert sc.choices == ISO_CHOICES

    def test_count(self):
        sc = SettingChoices(ISO_CHOICES)
        assert sc.count == 8

    def test_empty_choices(self):
        sc = SettingChoices([])
        assert sc.count == 0


class TestSliderToValue:
    def test_first_position(self):
        sc = SettingChoices(ISO_CHOICES)
        assert sc.value_at(0) == "100"

    def test_last_position(self):
        sc = SettingChoices(ISO_CHOICES)
        assert sc.value_at(7) == "12800"

    def test_middle_position(self):
        sc = SettingChoices(ISO_CHOICES)
        assert sc.value_at(3) == "800"

    def test_clamps_negative(self):
        sc = SettingChoices(ISO_CHOICES)
        assert sc.value_at(-1) == "100"

    def test_clamps_overflow(self):
        sc = SettingChoices(ISO_CHOICES)
        assert sc.value_at(100) == "12800"

    def test_none_for_empty(self):
        sc = SettingChoices([])
        assert sc.value_at(0) is None


class TestValueToSlider:
    def test_exact_match(self):
        sc = SettingChoices(ISO_CHOICES)
        assert sc.index_of("400") == 2

    def test_first_value(self):
        sc = SettingChoices(ISO_CHOICES)
        assert sc.index_of("100") == 0

    def test_last_value(self):
        sc = SettingChoices(ISO_CHOICES)
        assert sc.index_of("12800") == 7

    def test_not_found_returns_none(self):
        sc = SettingChoices(ISO_CHOICES)
        assert sc.index_of("999") is None

    def test_empty_choices(self):
        sc = SettingChoices([])
        assert sc.index_of("100") is None


class TestValidation:
    def test_valid_value(self):
        sc = SettingChoices(ISO_CHOICES)
        assert sc.is_valid("400") is True

    def test_invalid_value(self):
        sc = SettingChoices(ISO_CHOICES)
        assert sc.is_valid("450") is False

    def test_case_sensitive(self):
        sc = SettingChoices(["Auto", "Daylight"])
        assert sc.is_valid("auto") is False
        assert sc.is_valid("Auto") is True


class TestClosestMatch:
    def test_exact_match(self):
        sc = SettingChoices(APERTURE_CHOICES)
        assert sc.find_closest("f/5.6") == "f/5.6"

    def test_partial_match_aperture(self):
        sc = SettingChoices(APERTURE_CHOICES)
        assert sc.find_closest("5.6") == "f/5.6"

    def test_partial_match_case_insensitive(self):
        sc = SettingChoices(["Auto", "Daylight", "Cloudy"])
        assert sc.find_closest("day") == "Daylight"

    def test_no_match_returns_none(self):
        sc = SettingChoices(ISO_CHOICES)
        assert sc.find_closest("xyz") is None

    def test_numeric_closest_iso(self):
        sc = SettingChoices(ISO_CHOICES)
        assert sc.find_closest("350") == "400"

    def test_numeric_closest_low(self):
        sc = SettingChoices(ISO_CHOICES)
        assert sc.find_closest("50") == "100"

    def test_numeric_closest_high(self):
        sc = SettingChoices(ISO_CHOICES)
        assert sc.find_closest("20000") == "12800"


class TestBoundaryHandling:
    def test_slider_min(self):
        sc = SettingChoices(SHUTTER_CHOICES)
        assert sc.value_at(0) == "30"

    def test_slider_max(self):
        sc = SettingChoices(SHUTTER_CHOICES)
        assert sc.value_at(sc.count - 1) == "1/8000"

    def test_slider_max_index(self):
        sc = SettingChoices(SHUTTER_CHOICES)
        assert sc.max_index == 18

    def test_single_choice(self):
        sc = SettingChoices(["Auto"])
        assert sc.value_at(0) == "Auto"
        assert sc.max_index == 0
        assert sc.index_of("Auto") == 0
