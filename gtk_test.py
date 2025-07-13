import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk
import sys

class TestApp(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id="dev.gemini.test", **kwargs)
        self.win = None

    def do_activate(self):
        if not self.win:
            self.win = Gtk.ApplicationWindow(application=self)
            self.win.set_title("GTK Test")
            self.win.set_default_size(200, 100)
            label = Gtk.Label(label="Hello, World!")
            self.win.set_child(label)
        
        self.win.present()

if __name__ == "__main__":
    app = TestApp()
    app.run(sys.argv)
