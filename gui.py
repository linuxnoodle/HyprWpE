import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio, Gdk

import os
import json
import subprocess
import sys

WALLPAPER_DIR = os.path.expanduser("~/.steam/steam/steamapps/workshop/content/431960")
SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hyprpaper-we.sh")
AUTOSTART_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "autostart.sh")
CONFIG_DIR = os.path.expanduser("~/.config/hyprpaper-we")
CONFIG_FILE = os.path.join(CONFIG_DIR, "state.json")
AUTOSTART_DESKTOP_FILE = os.path.expanduser("~/.config/autostart/hyprpaper-we.desktop")

class WallpaperSelectorApp(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id="dev.gemini.hyprpaperwe.gui", **kwargs)
        self.win = None
        self.ensure_config_dir()
        self.load_state()

    def ensure_config_dir(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)

    def load_state(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                self.state = json.load(f)
        else:
            self.state = {'last_wallpaper_id': None}

    def save_state(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.state, f, indent=4)

    def do_activate(self):
        if not self.win:
            settings = Gtk.Settings.get_default()
            is_dark_theme = settings.get_property("gtk-application-prefer-dark-theme")

            if is_dark_theme:
                card_bg_color = "rgba(255, 255, 255, 0.07)"
                card_hover_bg_color = "rgba(255, 255, 255, 0.12)"
                shadow_color = "rgba(0, 0, 0, 0.3)"
            else:
                card_bg_color = "rgba(0, 0, 0, 0.05)"
                card_hover_bg_color = "rgba(0, 0, 0, 0.09)"
                shadow_color = "rgba(0, 0, 0, 0.15)"

            css_provider = Gtk.CssProvider()
            css_provider.load_from_data(
                f"""
                .wallpaper-card {{
                    border-radius: 8px;
                    background-color: {card_bg_color};
                    margin: 6px;
                    transition: all 0.2s ease-in-out;
                }}
                .wallpaper-card:hover {{
                    background-color: {card_hover_bg_color};
                    box-shadow: 0 4px 8px {shadow_color};
                }}
                flowbox > .wallpaper-card {{
                    padding: 8px;
                }}
                """.encode()
            )
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

            self.win = Gtk.ApplicationWindow(application=self)
            self.win.set_title("HyprPaper-WE Selector")
            self.win.set_default_size(800, 600)
            self.win.set_decorated(False)
            self.win.set_opacity(0.95)

            self.build_ui()
        self.win.present()

    def build_ui(self):
        titlebar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        titlebar.add_css_class("titlebar")

        stop_button = Gtk.Button(label="Stop Wallpaper")
        stop_button.connect('clicked', self.on_stop_clicked)
        titlebar.append(stop_button)

        self.autostart_button = Gtk.Button()
        self.autostart_button.connect('clicked', self.on_autostart_toggle)
        titlebar.append(self.autostart_button)
        self.update_autostart_button_label()

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.append(titlebar)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_vexpand(True)
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        main_box.append(scrolled_window)

        self.win.set_child(main_box)

        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(5)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flowbox.set_margin_top(10)
        self.flowbox.set_margin_bottom(10)
        self.flowbox.set_margin_start(10)
        self.flowbox.set_margin_end(10)
        scrolled_window.set_child(self.flowbox)

        self.load_wallpapers()

    def load_wallpapers(self):
        print(f"Scanning for wallpapers in: {WALLPAPER_DIR}")
        if not os.path.isdir(WALLPAPER_DIR):
            print("Error: Wallpaper directory not found!")
            return

        for wallpaper_id in os.listdir(WALLPAPER_DIR):
            wallpaper_path = os.path.join(WALLPAPER_DIR, wallpaper_id)
            project_json_path = os.path.join(wallpaper_path, "project.json")

            if os.path.isdir(wallpaper_path) and os.path.exists(project_json_path):
                try:
                    with open(project_json_path, 'r') as f:
                        data = json.load(f)
                    
                    if data.get('type') == 'scene':
                        continue

                    title = data.get('title', 'No Title')
                    preview_file = data.get('preview', 'preview.gif')
                    preview_path = os.path.join(wallpaper_path, preview_file)
                    wallpaper_type = data.get('type', 'unknown')

                    widget = self.create_wallpaper_widget(wallpaper_id, title, preview_path, wallpaper_type)
                    self.flowbox.append(widget)

                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Could not parse project.json for {wallpaper_id}: {e}")

    def create_wallpaper_widget(self, wallpaper_id, title, preview_path, wallpaper_type):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_size_request(150, 180)

        image = Gtk.Image()
        if os.path.exists(preview_path):
            image.set_from_file(preview_path)
        else:
            image.set_from_icon_name("image-missing", Gtk.IconSize.LARGE)
        image.set_pixel_size(120)
        box.append(image)

        title_label = Gtk.Label(label=title)
        title_label.set_wrap(True)
        title_label.set_justify(Gtk.Justification.CENTER)
        box.append(title_label)

        type_label = Gtk.Label()
        type_label.set_markup(f"<small><i>{wallpaper_type.capitalize()}</i></small>")
        box.append(type_label)

        button = Gtk.Button()
        button.set_child(box)
        button.connect('clicked', self.on_wallpaper_selected, wallpaper_id)
        button.add_css_class("wallpaper-card")
        return button

    def on_wallpaper_selected(self, button, wallpaper_id):
        print(f"Selected wallpaper ID: {wallpaper_id}")
        try:
            subprocess.run([SCRIPT_PATH, wallpaper_id], check=True)
            self.state['last_wallpaper_id'] = wallpaper_id
            self.save_state()
            print("Successfully launched wallpaper and saved state.")
        except subprocess.CalledProcessError as e:
            print(f"Error launching wallpaper script: {e}")
        except FileNotFoundError:
            print(f"Error: Script not found at {SCRIPT_PATH}")

    def on_stop_clicked(self, button):
        print("Stop button clicked.")
        try:
            result = subprocess.run([SCRIPT_PATH, "stop"], check=True, capture_output=True, text=True)
            self.state['last_wallpaper_id'] = None
            self.save_state()
            print(result.stdout.strip())
        except subprocess.CalledProcessError as e:
            print(f"Error sending stop command: {e}")
        except FileNotFoundError:
            print(f"Error: Script not found at {SCRIPT_PATH}")

    def on_autostart_toggle(self, button):
        if os.path.exists(AUTOSTART_DESKTOP_FILE):
            self.disable_autostart()
        else:
            self.enable_autostart()
        self.update_autostart_button_label()

    def update_autostart_button_label(self):
        if os.path.exists(AUTOSTART_DESKTOP_FILE):
            self.autostart_button.set_label("Disable Autostart")
        else:
            self.autostart_button.set_label("Enable Autostart")

    def enable_autostart(self):
        desktop_entry = f"""[Desktop Entry]
Type=Application
Name=HyprPaper-WE
Exec={AUTOSTART_SCRIPT_PATH}
StartupNotify=false
Terminal=false
"""
        os.makedirs(os.path.dirname(AUTOSTART_DESKTOP_FILE), exist_ok=True)
        with open(AUTOSTART_DESKTOP_FILE, 'w') as f:
            f.write(desktop_entry)
        print("Autostart enabled.")

    def disable_autostart(self):
        if os.path.exists(AUTOSTART_DESKTOP_FILE):
            os.remove(AUTOSTART_DESKTOP_FILE)
            print("Autostart disabled.")

if __name__ == "__main__":
    app = WallpaperSelectorApp()
    app.run(sys.argv)