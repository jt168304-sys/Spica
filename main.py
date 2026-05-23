from kivy.config import Config
Config.set("graphics", "resizable", "1")
Config.set("graphics", "width", "400")
Config.set("graphics", "height", "700")
Config.set("kivy", "log_level", "warning")
Config.set("input", "mouse", "mouse,multitouch_on_demand")

import os, sys
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.core.app_manager import WindApp

if __name__ == "__main__":
    WindApp().run()
