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

import re


class SettingChoices:
    def __init__(self, choices):
        self._choices = list(choices)

    @property
    def choices(self):
        return list(self._choices)

    @property
    def count(self):
        return len(self._choices)

    @property
    def max_index(self):
        return max(0, len(self._choices) - 1)

    def value_at(self, index):
        if not self._choices:
            return None
        index = max(0, min(index, len(self._choices) - 1))
        return self._choices[index]

    def index_of(self, value):
        try:
            return self._choices.index(value)
        except ValueError:
            return None

    def is_valid(self, value):
        return value in self._choices

    def find_closest(self, text):
        if not self._choices:
            return None

        if text in self._choices:
            return text

        lower = text.lower()
        for choice in self._choices:
            if lower in choice.lower():
                return choice

        input_num = _parse_number(text)
        if input_num is not None:
            best = None
            best_dist = float("inf")
            for choice in self._choices:
                choice_num = _parse_number(choice)
                if choice_num is not None:
                    dist = abs(choice_num - input_num)
                    if dist < best_dist:
                        best_dist = dist
                        best = choice
            if best is not None:
                return best

        return None


def _parse_number(text):
    cleaned = re.sub(r"[a-zA-Z/]*", "", text, count=1)
    if "/" in text:
        parts = text.split("/")
        try:
            return float(parts[0]) / float(parts[1])
        except (ValueError, ZeroDivisionError):
            pass
    try:
        return float(cleaned)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return None
