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

import signal

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from opencameracontrol.config import load_config
from opencameracontrol.gui import CameraControlWindow


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    config = load_config()
    win = CameraControlWindow(config)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
