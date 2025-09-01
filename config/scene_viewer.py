import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gtk4LayerShell', '1.0')
from gi.repository import Gtk, Gdk, GLib, Gtk4LayerShell
import pyglet
pyglet.options['headless'] = True # Prevent pyglet from creating its own window
from pyglet.gl import *
import sys
import os
import json
import math
import yaml

# --- Added configuration paths ---
CONFIG_DIR = os.path.expanduser("~/.config/HyprWpE")
PROPERTIES_FILE = os.path.join(CONFIG_DIR, "properties.yaml")

def load_properties():
    """Loads the properties.yaml file."""
    if os.path.exists(PROPERTIES_FILE):
        try:
            with open(PROPERTIES_FILE, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception:
            pass
    return {}

class Scene:
    """A class to load and parse a Wallpaper Engine scene file."""
    def __init__(self, scene_dir):
        self.directory = scene_dir
        self.objects = []
        self.assets = {}
        self.general_info = {}

        project_file = os.path.join(self.directory, 'project.json')
        if not os.path.exists(project_file):
            raise FileNotFoundError("project.json not found")

        with open(project_file, 'r') as f:
            project_data = json.load(f)

        if project_data.get("type", "").lower() != "scene":
            raise ValueError("This is not a scene wallpaper.")

        scene_file_name = project_data.get("file", "scene.json")
        scene_file_path = os.path.join(self.directory, scene_file_name)
        if not os.path.exists(scene_file_path):
            raise FileNotFoundError(f"{scene_file_name} not found")
            
        with open(scene_file_path, 'r') as f:
            scene_data = json.load(f)
        
        self.general_info = scene_data.get("general", {})
        self.objects = scene_data.get("objects", [])
        self.assets = {asset['name']: os.path.join(self.directory, asset['file']) for asset in scene_data.get("assets", [])}

class SceneViewerWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, scene_dir=None, monitor_name=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.scene_dir = scene_dir
        self.monitor_name = monitor_name
        self.scene = None
        self.textures = {}
        self.animation_time = 0.0

        self.set_decorated(False)
        
        self.gl_area = Gtk.GLArea()
        self.gl_area.set_required_version(3, 3)
        self.set_child(self.gl_area)

        self.gl_area.connect("realize", self.on_realize)
        self.gl_area.connect("render", self.on_render)

        self.setup_layer_shell()
        
        try:
            self.scene = Scene(self.scene_dir)
        except Exception as e:
            print(f"Error loading scene: {e}")
            self.close()

    def setup_layer_shell(self):
        Gtk4LayerShell.init_for_window(self)
        if self.monitor_name:
            display = Gdk.Display.get_default()
            monitors = display.get_monitors()
            for monitor in monitors:
                if monitor.get_connector() == self.monitor_name:
                    Gtk4LayerShell.set_monitor(self, monitor)
                    break
        Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.BACKGROUND)
        Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.NONE)

        # --- The Fix: Load and apply panel margins from the config file ---
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

    def on_realize(self, area):
        area.make_current()
        self.load_textures()
        GLib.timeout_add(16, self.tick) # ~60 FPS

    def load_textures(self):
        if not self.scene: return
        for name, path in self.scene.assets.items():
            if os.path.exists(path) and path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                try:
                    image = pyglet.image.load(path)
                    self.textures[name] = image.get_texture()
                except Exception as e:
                    print(f"Failed to load texture {name}: {e}")

    def tick(self):
        self.animation_time += 0.016
        self.gl_area.queue_draw()
        return True # Keep the timeout running

    def on_render(self, area, ctx):
        if not self.scene: return
        width = self.get_width()
        height = self.get_height()

        glViewport(0, 0, width, height)
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, width, 0, height, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        for obj in self.scene.objects:
            if obj.get("type") == "imagelayer":
                self.render_image_layer(obj, width, height)
                
        return True

    def render_image_layer(self, layer_obj, width, height):
        asset_name = layer_obj.get("asset")
        if not asset_name or asset_name not in self.textures:
            return

        texture = self.textures[asset_name]
        
        pos = layer_obj.get("pos", "0 0 0").split()
        x, y = float(pos[0]), float(pos[1])
        scale = layer_obj.get("scale", "1 1 1").split()
        sx, sy = float(scale[0]), float(scale[1])
        angle_deg = float(layer_obj.get("angle", 0))

        draw_width = texture.width * sx
        draw_height = texture.height * sy
        draw_x = (width / 2) + x - (draw_width / 2)
        draw_y = (height / 2) - y - (draw_height / 2) # Y is inverted

        glPushMatrix()
        glTranslatef(draw_x + draw_width/2, draw_y + draw_height/2, 0)
        glRotatef(angle_deg, 0, 0, 1)
        glTranslatef(-(draw_x + draw_width/2), -(draw_y + draw_height/2), 0)
        
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, texture.id)
        glColor4f(1.0, 1.0, 1.0, 1.0)
        
        pyglet.graphics.draw(4, GL_QUADS,
            ('v2f', [draw_x, draw_y,
                     draw_x + draw_width, draw_y,
                     draw_x + draw_width, draw_y + draw_height,
                     draw_x, draw_y + draw_height]),
            ('t2f', [0, 0, 1, 0, 1, 1, 0, 1])
        )
        
        glDisable(GL_TEXTURE_2D)
        glPopMatrix()

class SceneViewerApp(Gtk.Application):
    def __init__(self, scene_dir, monitor_name, *args, **kwargs):
        clean_id = ''.join(filter(str.isalnum, os.path.basename(scene_dir)))
        super().__init__(*args, application_id=f"dev.gemini.hyprpaperwe.scene.{clean_id}", **kwargs)
        self.scene_dir = scene_dir
        self.monitor_name = monitor_name
        self.win = None

    def do_activate(self):
        if not self.win:
            self.win = SceneViewerWindow(application=self, scene_dir=self.scene_dir, monitor_name=self.monitor_name)
        self.win.present()

if __name__ == "__main__":
    if not (2 <= len(sys.argv) <= 3):
        print(f"Usage: {sys.argv[0]} <path_to_scene_directory> [monitor_name]", file=sys.stderr)
        sys.exit(1)

    scene_dir = sys.argv[1]
    monitor_name = sys.argv[2] if len(sys.argv) == 3 else None
    
    if not os.path.isdir(scene_dir):
        print(f"Error: Directory not found at {scene_dir}", file=sys.stderr)
        sys.exit(1)

    app = SceneViewerApp(scene_dir, monitor_name)
    app.run(None)


