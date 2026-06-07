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
