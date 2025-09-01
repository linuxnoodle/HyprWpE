import gi
gi.require_version('Gtk', '4.0')
gi.require_version('WebKit', '6.0')
gi.require_version('Gtk4LayerShell', '1.0')
from gi.repository import Gtk, WebKit, Gtk4LayerShell, Gdk, Gio
import sys
import os
import yaml

CONFIG_DIR = os.path.expanduser("~/.config/HyprWpE")
PROPERTIES_FILE = os.path.join(CONFIG_DIR, "properties.yaml")

def load_properties():
    if os.path.exists(PROPERTIES_FILE):
        try:
            with open(PROPERTIES_FILE, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception:
            pass
    return {}

class WebWallpaperWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, monitor_name=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.set_decorated(False)
        self.webview = WebKit.WebView()
        settings = self.webview.get_settings()
        
        try:
            settings.set_property("media-playback-allows-inline", True)
            settings.set_property("autoplay-policy", WebKit.AutoplayPolicy.ALLOW)
        except Exception:
            print("Warning: Could not set all media properties. Autoplay may not work.")

        self.set_child(self.webview)
        
        Gtk4LayerShell.init_for_window(self)

        if monitor_name:
            display = Gdk.Display.get_default()
            monitors = display.get_monitors()
            for monitor in monitors:
                if monitor.get_connector() == monitor_name:
                    Gtk4LayerShell.set_monitor(self, monitor)
                    break
        
        Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.BACKGROUND)
        Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.ON_DEMAND)
        
        # Load margins from the config file and apply them
        props = load_properties()
        margins = props.get("panel_margins", {})
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.TOP, margins.get("top", 0))
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.BOTTOM, margins.get("bottom", 0))
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.LEFT, margins.get("left", 0))
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.RIGHT, margins.get("right", 0))

        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.TOP, True)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.BOTTOM, True)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.LEFT, True)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.RIGHT, True)

    def load_uri(self, uri):
        self.webview.load_uri(uri)

class WebWallpaperApp(Gtk.Application):
    def __init__(self, uri, monitor_name, *args, **kwargs):
        # Use a static ID so it can be targeted by a layerrule for effects if desired
        super().__init__(*args, application_id="dev.gemini.hyprpaperwe.viewer", **kwargs)
        self.uri = uri
        self.monitor_name = monitor_name
        self.win = None

    def do_activate(self):
        if not self.win:
            self.win = WebWallpaperWindow(application=self, monitor_name=self.monitor_name)
        self.win.load_uri(self.uri)
        self.win.present()

if __name__ == "__main__":
    if not (2 <= len(sys.argv) <= 3):
        print(f"Usage: {sys.argv[0]} <html_file_path> [monitor_name]", file=sys.stderr)
        sys.exit(1)

    html_path = sys.argv[1]
    monitor_name = sys.argv[2] if len(sys.argv) == 3 else None
    
    uri = Gio.File.new_for_path(html_path).get_uri()
    app = WebWallpaperApp(uri, monitor_name)
    app.run(None)
