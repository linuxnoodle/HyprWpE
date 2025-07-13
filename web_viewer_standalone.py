import gi
gi.require_version('Gtk', '4.0')
gi.require_version('WebKit', '6.0')
gi.require_version('Gtk4LayerShell', '1.0')
from gi.repository import Gtk, WebKit, Gtk4LayerShell, Gdk, Gio
import sys
import os

# --- HARDCODED PATH FOR DEBUGGING ---
HARDCODED_HTML_PATH = "/home/destinyrrj/.steam/steam/steamapps/workshop/content/431960/3518715742/dynamic_wallpaper.html"

class WebWallpaperWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("DEBUG: Window is being created...")
        
        self.webview = WebKit.WebView()
        self.set_child(self.webview)
        
        Gtk4LayerShell.init_for_window(self)
        Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.BACKGROUND)
        Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.NONE)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.TOP, True)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.BOTTOM, True)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.LEFT, True)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.RIGHT, True)

    def load_the_uri(self):
        if not os.path.exists(HARDCODED_HTML_PATH):
            print(f"ERROR: Debug file not found: {HARDCODED_HTML_PATH}")
            return
        uri = Gio.File.new_for_path(HARDCODED_HTML_PATH).get_uri()
        print(f"DEBUG: Loading URI: {uri}")
        self.webview.load_uri(uri)

class WebWallpaperApp(Gtk.Application):
    def __init__(self, *args, **kwargs):
        # Use a new, unique ID to avoid conflicts
        super().__init__(*args, application_id="dev.gemini.hyprpaperwe.standalone.test", **kwargs)
        print("DEBUG: Application initialized.")
        self.win = None

    def do_activate(self):
        print("DEBUG: Application is activating (do_activate)...")
        if not self.win:
            self.win = WebWallpaperWindow(application=self)
        
        self.win.load_the_uri()
        self.win.present()
        print("DEBUG: Window presented.")

if __name__ == "__main__":
    print("DEBUG: Running standalone script...")
    app = WebWallpaperApp()
    # Use sys.argv, like in the working gtk_test.py
    exit_status = app.run(sys.argv)
    print(f"DEBUG: Application finished with exit code {exit_status}")
    sys.exit(exit_status)