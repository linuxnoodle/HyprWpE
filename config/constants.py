import os

# Constants that will be moved here:
DEFAULT_WALLPAPER_DIR = os.path.expanduser("~/.steam/steam/steamapps/workshop/content/431960")
SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hyprpaper-we.sh")
CONFIG_DIR = os.path.expanduser("~/.config/hyprpaper-we")
YAML_FILE = os.path.join(CONFIG_DIR, "wallpapers.yaml")
PROPERTIES_FILE = os.path.join(CONFIG_DIR, "properties.yaml")

# New constants to add:
WALLPAPER_WIDGET_WIDTH = 160
WALLPAPER_WIDGET_HEIGHT = 180
IMAGE_FRAME_WIDTH = 150
IMAGE_FRAME_HEIGHT = 100
