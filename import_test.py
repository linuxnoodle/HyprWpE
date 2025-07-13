print("Import Test: Starting...")
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('WebKit', '6.0')
gi.require_version('Gtk4LayerShell', '1.0')
from gi.repository import Gtk, WebKit, Gtk4LayerShell, Gdk, Gio
import sys

# Этот код идентичен рабочему gtk_test.py
class TestApp(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id="dev.gemini.importtest", **kwargs)
        self.win = None

    def do_activate(self):
        if not self.win:
            self.win = Gtk.ApplicationWindow(application=self)
            self.win.set_title("Import Test")
            self.win.set_default_size(300, 100)
            label = Gtk.Label(label="If you see this, the imports are NOT the problem.")
            self.win.set_child(label)
        
        self.win.present()

if __name__ == "__main__":
    app = TestApp()
    app.run(sys.argv)
