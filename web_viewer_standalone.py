import gi
gi.require_version('Gtk', '4.0')
gi.require_version('WebKit', '6.0')
gi.require_version('Gtk4LayerShell', '1.0')
from gi.repository import Gtk, WebKit, Gtk4LayerShell, Gdk, Gio
import sys
import os

# --- ЖЕСТКО ЗАДАННЫЙ ПУТЬ ДЛЯ ОТЛАДКИ ---
HARDCODED_HTML_PATH = "/home/destinyrrj/.steam/steam/steamapps/workshop/content/431960/3518715742/dynamic_wallpaper.html"

class WebWallpaperWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("DEBUG: Окно создается...")
        
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
            print(f"ОШИБКА: Не найден файл для отладки: {HARDCODED_HTML_PATH}")
            return
        uri = Gio.File.new_for_path(HARDCODED_HTML_PATH).get_uri()
        print(f"DEBUG: Загрузка URI: {uri}")
        self.webview.load_uri(uri)

class WebWallpaperApp(Gtk.Application):
    def __init__(self, *args, **kwargs):
        # Используем новый, уникальный ID, чтобы избежать конфликтов
        super().__init__(*args, application_id="dev.gemini.hyprpaperwe.standalone.test", **kwargs)
        print("DEBUG: Приложение инициализировано.")
        self.win = None

    def do_activate(self):
        print("DEBUG: Приложение активируется (do_activate)...")
        if not self.win:
            self.win = WebWallpaperWindow(application=self)
        
        self.win.load_the_uri()
        self.win.present()
        print("DEBUG: Окно показано.")

if __name__ == "__main__":
    print("DEBUG: Запуск автономного скрипта...")
    app = WebWallpaperApp()
    # Используем sys.argv, как в рабочем gtk_test.py
    exit_status = app.run(sys.argv)
    print(f"DEBUG: Приложение завершилось с кодом {exit_status}")
    sys.exit(exit_status)
