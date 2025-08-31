import gi
import os
import json
import subprocess
import sys
import yaml
import argparse
import signal

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio, Gdk, GLib

DEFAULT_WALLPAPER_DIR = os.path.expanduser("~/.steam/steam/steamapps/workshop/content/431960")
SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hyprpaper-we.sh")
CONFIG_DIR = os.path.expanduser("~/.config/hyprpaper-we")
YAML_FILE = os.path.join(CONFIG_DIR, "wallpapers.yaml")
PROPERTIES_FILE = os.path.join(CONFIG_DIR, "properties.yaml")

class OffsetDialog(Gtk.Dialog):
    """A dialog window for configuring panel margins, updated for modern GTK4."""
    def __init__(self, parent, current_margins):
        super().__init__(title="Configure Panel Margins", transient_for=parent, modal=True)

        # The main content area of a dialog is now managed by setting a child widget.
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_margin_top(10); main_box.set_margin_bottom(10); main_box.set_margin_start(10); main_box.set_margin_end(10)
        self.set_child(main_box)

        description = Gtk.Label(
            label="Set margins (in pixels) to prevent Web and Scene wallpapers from drawing under panels like Waybar.",
            wrap=True,
            justify=Gtk.Justification.CENTER
        )
        main_box.append(description)

        grid = Gtk.Grid(column_spacing=10, row_spacing=10, margin_top=15, halign=Gtk.Align.CENTER)
        main_box.append(grid)
        
        self.top_spin = Gtk.SpinButton.new_with_range(0, 1000, 1)
        self.bottom_spin = Gtk.SpinButton.new_with_range(0, 1000, 1)
        self.left_spin = Gtk.SpinButton.new_with_range(0, 1000, 1)
        self.right_spin = Gtk.SpinButton.new_with_range(0, 1000, 1)
        
        self.top_spin.set_value(current_margins.get("top", 0))
        self.bottom_spin.set_value(current_margins.get("bottom", 0))
        self.left_spin.set_value(current_margins.get("left", 0))
        self.right_spin.set_value(current_margins.get("right", 0))

        grid.attach(Gtk.Label(label="Top:"), 0, 0, 1, 1)
        grid.attach(self.top_spin, 1, 0, 1, 1)
        grid.attach(Gtk.Label(label="Bottom:"), 0, 1, 1, 1)
        grid.attach(self.bottom_spin, 1, 1, 1, 1)
        grid.attach(Gtk.Label(label="Left:"), 0, 2, 1, 1)
        grid.attach(self.left_spin, 1, 2, 1, 1)
        grid.attach(Gtk.Label(label="Right:"), 0, 3, 1, 1)
        grid.attach(self.right_spin, 1, 3, 1, 1)

        # Use add_action_widget for modern GTK4 dialogs
        self.add_action_widget(Gtk.Button(label="_Cancel"), Gtk.ResponseType.CANCEL)
        self.add_action_widget(Gtk.Button(label="_Save"), Gtk.ResponseType.OK)


    def get_values(self):
        return {
            "top": int(self.top_spin.get_value()),
            "bottom": int(self.bottom_spin.get_value()),
            "left": int(self.left_spin.get_value()),
            "right": int(self.right_spin.get_value()),
        }

class WallpaperSelectorApp(Gtk.Application):
    def __init__(self, *args, config_file_to_load=None, **kwargs):
        super().__init__(*args, application_id="wallpaper_app", **kwargs)
        self.win = None
        self.paned = None 
        self.config_to_load_on_startup = config_file_to_load
        
        self.ensure_config_dir()
        self.config = self.load_or_initialize_config()
        self.wallpaper_dir = self.config.get('wallpaper_dir', DEFAULT_WALLPAPER_DIR)
        self.current_wallpapers = self.config.get("wallpapers", {})

        self.monitors = self.detect_monitors()
        self.wallpaper_properties = self.load_properties()
        
        self.all_wallpapers = []
        self.search_term = ""
        self.type_filters = {"video": True, "scene": True, "web": True}
        
        self.current_monitor = "All Monitors"
        self.selected_wallpaper_id = None
        self.property_signal_handlers = {}
        self.setup_signal_handlers()

        self.wallpaper_widgets = {}
        self.filtered_wallpapers = []
        self.last_allocated_width = 0
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path("style.css")

        # Apply CSS provider to the default display
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def ensure_config_dir(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)

    def load_or_initialize_config(self):
        config = {}
        needs_save = False
        if os.path.exists(YAML_FILE):
            try:
                with open(YAML_FILE, 'r') as f:
                    config = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Error loading YAML wallpapers, creating new one: {e}")
                config = {}
        
        if 'wallpaper_dir' not in config or not config['wallpaper_dir']:
            config['wallpaper_dir'] = DEFAULT_WALLPAPER_DIR
            needs_save = True
        if 'wallpapers' not in config:
            config['wallpapers'] = {}
            needs_save = True
        if needs_save:
            try:
                with open(YAML_FILE, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False, sort_keys=False)
                print(f"Initialized or updated config file at {YAML_FILE}")
            except Exception as e:
                print(f"Error saving initial config: {e}")
        return config

    def clear_wallpaper_grid(self):
        """Remove all wallpaper widgets from the flowbox"""
        print("Clearing wallpaper grid...")
        
        # Remove all children from flowbox
        child = self.flowbox.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.flowbox.remove(child)
            child = next_child
        
        # Clear our tracking dictionary
        self.wallpaper_widgets.clear()

    def apply_filters(self):
        """Apply search and type filters to wallpapers by removing/adding widgets"""
        search_term = self.search_term.lower()
        visible_count = 0
        
        print(f"Applying filters - Search: '{search_term}', Types: {self.type_filters}")
        
        # Remove all widgets from flowbox first
        child = self.flowbox.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.flowbox.remove(child)
            child = next_child
        
        # Re-add only the widgets that should be visible
        for wp_data in self.all_wallpapers:
            widget = self.wallpaper_widgets.get(wp_data['id'])
            if not widget:
                continue
                
            # Check if matches search
            title_matches = search_term in wp_data['title_lower'] if search_term else True
            
            # Check if type is enabled
            type_matches = self.type_filters.get(wp_data['type'], False)
            
            # Add back to flowbox if it should be visible
            if title_matches and type_matches:
                self.flowbox.append(widget)
                
                # Set size on the FlowBoxChild after re-adding
                flowbox_child = widget.get_parent()
                if flowbox_child:
                    flowbox_child.set_size_request(160, -1)
                    flowbox_child.set_halign(Gtk.Align.START)
                
                visible_count += 1
        
        print(f"Showing {visible_count} out of {len(self.all_wallpapers)} wallpapers")

    def populate_wallpaper_grid(self):
        """Populate the flowbox with all wallpapers"""
        print(f"Populating grid with {len(self.all_wallpapers)} wallpapers...")
        
        # Clear existing widgets
        self.clear_wallpaper_grid()
        
        # Create widgets for all wallpapers
        #for idx, wp_data in enumerate(self.all_wallpapers):
        for wp_data in self.all_wallpapers:
            widget = self.create_wallpaper_widget(
                wp_data['id'], 
                wp_data['title'], 
                wp_data['preview_path'], 
                wp_data['type']
            )
            
            # Store in our dictionary
            self.wallpaper_widgets[wp_data['id']] = widget
            
            # Add to flowbox
            self.flowbox.append(widget)
            #self.flowbox.get_child_at_index(idx).add_css_class("flowbox-item")
            flowbox_child = widget.get_parent()
            if flowbox_child:
                flowbox_child.set_size_request(160, -1)  # Fixed width, natural height
                flowbox_child.set_halign(Gtk.Align.START)
        
        print(f"Created {len(self.wallpaper_widgets)} wallpaper widgets")
        
        # Apply initial filtering
        self.apply_filters()

    def load_properties(self):
        props = {}
        needs_save = False
        if os.path.exists(PROPERTIES_FILE):
            try:
                with open(PROPERTIES_FILE, 'r') as f:
                    props = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Error loading properties YAML, creating new one: {e}")
                props = {}
        if 'panel_margins' not in props:
            props['panel_margins'] = {'top': 0, 'bottom': 0, 'left': 0, 'right': 0}
            needs_save = True
        if needs_save:
            try:
                with open(PROPERTIES_FILE, 'w') as f:
                    yaml.dump(props, f, default_flow_style=False)
                print(f"Initialized panel_margins in {PROPERTIES_FILE}")
            except Exception as e:
                print(f"Error saving initial properties: {e}")
        return props

    def save_properties(self):
        try:
            with open(PROPERTIES_FILE, 'w') as f:
                yaml.dump(self.wallpaper_properties, f, default_flow_style=False)
        except Exception as e:
            print(f"Error saving properties: {e}")

    def detect_monitors(self):
        try:
            result = subprocess.run(["hyprctl", "monitors", "-j"], capture_output=True, text=True, check=True)
            return [m['name'] for m in json.loads(result.stdout)]
        except Exception as e:
            print(f"Could not detect monitors: {e}")
            return []

    def setup_signal_handlers(self):
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, self.shutdown)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, self.shutdown)

    def shutdown(self, *args):
        print("\nShutdown signal received. Stopping all wallpapers.")
        self.on_stop_clicked(None)
        self.quit()
        return True

    def do_activate(self):
        if not self.win:
            self.win = Gtk.ApplicationWindow(application=self)
            self.win.set_title("mpvpaper-WE Selector")
            self.win.set_default_size(1200, 700)
            self.win.set_decorated(False)
            self.win.set_opacity(0.95)
            self.build_ui()
            self.apply_config_from_file(self.config_to_load_on_startup or YAML_FILE)
        self.win.present()

    def build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_child(main_box)

        titlebar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6,
                           margin_start=6, margin_end=6, margin_top=6, margin_bottom=6)
        main_box.append(titlebar)

        save_button = Gtk.Button(label="Save Setup")
        save_button.connect('clicked', self.on_save_setup_clicked)
        titlebar.append(save_button)

        offset_button = Gtk.Button(label="Configure Offset")
        offset_button.connect('clicked', self.on_configure_offset_clicked)
        titlebar.append(offset_button)

        search_entry = Gtk.SearchEntry(placeholder_text="Search wallpapers...")
        search_entry.connect("search-changed", self.on_search_changed)
        titlebar.append(search_entry)

        self.monitor_combo = Gtk.ComboBoxText()
        self.monitor_combo.append_text("All Monitors")
        for m in self.monitors:
            self.monitor_combo.append_text(m)
        self.monitor_combo.set_active(0)
        self.monitor_combo.connect("changed", self.on_monitor_changed)
        titlebar.append(self.monitor_combo)

        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        content_box.set_vexpand(True)
        main_box.append(content_box)

        filter_sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                                 margin_top=10, margin_bottom=10,
                                 margin_start=10, margin_end=10, width_request=180)
        content_box.append(filter_sidebar)

        filter_sidebar.append(Gtk.Label(label="<big><b>Filter by Type</b></big>",
                                        use_markup=True, halign=Gtk.Align.START))

        video_check = Gtk.CheckButton(label="Video")
        video_check.set_active(True)
        video_check.connect("toggled", self.on_filter_toggled, "video")
        filter_sidebar.append(video_check)

        scene_check = Gtk.CheckButton(label="Scene")
        scene_check.set_active(True)
        scene_check.connect("toggled", self.on_filter_toggled, "scene")
        filter_sidebar.append(scene_check)

        web_check = Gtk.CheckButton(label="Web")
        web_check.set_active(True)
        web_check.connect("toggled", self.on_filter_toggled, "web")
        filter_sidebar.append(web_check)

        self.paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.paned.set_hexpand(True)
        content_box.append(self.paned)

        scrolled_window = self.build_wallpaper_grid_section()
        self.paned.set_start_child(scrolled_window)

        self.sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                               margin_top=10, margin_bottom=10,
                               margin_start=10, margin_end=10)
        self.sidebar.set_visible(False)
        self.paned.set_end_child(self.sidebar)

        sidebar_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        sidebar_title = Gtk.Label(label="<big><b>Properties</b></big>",
                                  use_markup=True, halign=Gtk.Align.START, hexpand=True)
        sidebar_header.append(sidebar_title)
        close_button = Gtk.Button.new_from_icon_name("window-close-symbolic")
        close_button.add_css_class("flat")
        close_button.connect('clicked', self.hide_sidebar)
        sidebar_header.append(close_button)
        self.sidebar.append(sidebar_header)

        self.sidebar_image = Gtk.Picture()
        self.sidebar_image.set_keep_aspect_ratio(True)
        self.sidebar_image.set_can_shrink(True)
        self.sidebar_image.set_margin_bottom(10)
        self.sidebar.append(self.sidebar_image)

        self.prop_widgets_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                                        sensitive=False)
        self.sidebar.append(self.prop_widgets_box)

        self.audio_check = Gtk.CheckButton(label="Enable Audio")
        self.prop_widgets_box.append(self.audio_check)

        speed_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, valign=Gtk.Align.CENTER)
        speed_box.append(Gtk.Label(label="Speed:"))
        self.speed_spin = Gtk.SpinButton.new_with_range(0.1, 4.0, 0.05)
        self.speed_spin.set_hexpand(True)
        speed_box.append(self.speed_spin)
        self.prop_widgets_box.append(speed_box)

        scale_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, valign=Gtk.Align.CENTER)
        scale_box.append(Gtk.Label(label="Scale Mode:"))
        self.scale_combo = Gtk.ComboBoxText()
        self.scale_combo.append_text("Cover")
        self.scale_combo.append_text("Contain")
        self.scale_combo.append_text("Fill")
        self.scale_combo.set_hexpand(True)
        scale_box.append(self.scale_combo)
        self.prop_widgets_box.append(scale_box)

        apply_button = Gtk.Button(label="Apply Changes", margin_top=10)
        apply_button.connect("clicked", self.on_apply_changes_clicked)
        self.prop_widgets_box.append(apply_button)

        self.property_signal_handlers['audio'] = self.audio_check.connect('toggled', self.on_property_changed)
        self.property_signal_handlers['speed'] = self.speed_spin.connect('value-changed', self.on_property_changed)
        self.property_signal_handlers['scale'] = self.scale_combo.connect('changed', self.on_property_changed)

        self.load_wallpaper_data()

    def load_wallpaper_data(self):
        """Load wallpaper metadata from the wallpaper directory"""
        print(f"Loading wallpaper data from: {self.wallpaper_dir}")
        
        self.all_wallpapers.clear()
        
        if not self.wallpaper_dir or not os.path.isdir(self.wallpaper_dir):
            print("Wallpaper directory not found or invalid")
            return
            
        wallpaper_count = 0
        for wallpaper_id in os.listdir(self.wallpaper_dir):
            wallpaper_path = os.path.join(self.wallpaper_dir, wallpaper_id)
            project_json_path = os.path.join(wallpaper_path, "project.json")
            
            if os.path.isdir(wallpaper_path) and os.path.exists(project_json_path):
                try:
                    with open(project_json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    title = data.get('title', 'No Title')
                    wp_type = data.get('type', 'unknown').lower()
                    preview_file = data.get('preview', 'preview.gif')
                    
                    wallpaper_data = {
                        'id': wallpaper_id,
                        'title': title,
                        'type': wp_type,
                        'preview_path': os.path.join(wallpaper_path, preview_file),
                        'title_lower': title.lower(),
                    }
                    
                    self.all_wallpapers.append(wallpaper_data)
                    wallpaper_count += 1
                    
                except Exception as e:
                    print(f"Could not parse project.json for {wallpaper_id}: {e}")
                    
        print(f"Successfully loaded {wallpaper_count} wallpapers")
        
        # Show some examples
        for i, wp in enumerate(self.all_wallpapers[:3]):
            print(f"  [{i+1}] ID: {wp['id']}, Type: {wp['type']}, Title: '{wp['title']}'")
        
        # Populate the grid
        self.populate_wallpaper_grid()

    def clear_flowbox(self):
        """Clear all children from the flowbox"""
        child = self.flowbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.flowbox.remove(child)
            child = next_child
        self.wallpaper_widgets.clear()

    def on_search_changed(self, search_entry):
        """Handle search text changes"""
        self.search_term = search_entry.get_text()
        print(f"Search changed to: '{self.search_term}'")
        self.apply_filters()

    def on_filter_toggled(self, checkbox, type_name):
        """Handle type filter changes"""
        self.type_filters[type_name] = checkbox.get_active()
        print(f"Filter '{type_name}' set to: {self.type_filters[type_name]}")
        self.apply_filters()

    def on_configure_offset_clicked(self, button):
        current_margins = self.wallpaper_properties.get("panel_margins", {})
        dialog = OffsetDialog(self.win, current_margins)
        dialog.connect("response", self.on_offset_dialog_response)
        dialog.present()
        
    def on_offset_dialog_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.OK:
            new_margins = dialog.get_values()
            self.wallpaper_properties["panel_margins"] = new_margins
            self.save_properties()
            print("Panel margins saved. Relaunch any active Web or Scene wallpapers to see changes.")
        dialog.destroy()

    def hide_sidebar(self, button):
        self.sidebar.set_visible(False)

    def populate_sidebar_values(self):
        if not self.selected_wallpaper_id: return
        preview_path = next((wp['preview_path'] for wp in self.all_wallpapers if wp['id'] == self.selected_wallpaper_id), None)
        if preview_path and os.path.exists(preview_path):
            self.sidebar_image.set_filename(preview_path)
        else:
            icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
            paintable = icon_theme.lookup_icon("image-missing-symbolic", None, 128, 1, Gtk.TextDirection.NONE, None)
            self.sidebar_image.set_paintable(paintable)
        self.audio_check.handler_block(self.property_signal_handlers['audio'])
        self.speed_spin.handler_block(self.property_signal_handlers['speed'])
        self.scale_combo.handler_block(self.property_signal_handlers['scale'])
        props = self.wallpaper_properties.get(self.selected_wallpaper_id, {})
        self.prop_widgets_box.set_sensitive(True)
        self.audio_check.set_active(props.get('audio', False))
        self.speed_spin.set_value(props.get('speed', 1.0))
        self.scale_combo.set_active(["Cover", "Contain", "Fill"].index(props.get('scale', 'Cover')))
        self.audio_check.handler_unblock(self.property_signal_handlers['audio'])
        self.speed_spin.handler_unblock(self.property_signal_handlers['speed'])
        self.scale_combo.handler_unblock(self.property_signal_handlers['scale'])

    # --- Performance Fix: Only save properties, don't apply them ---
    def on_property_changed(self, widget, *args):
        wid = self.selected_wallpaper_id
        if not wid: return
        if wid not in self.wallpaper_properties: self.wallpaper_properties[wid] = {}
        if isinstance(widget, Gtk.CheckButton): self.wallpaper_properties[wid]['audio'] = widget.get_active()
        elif isinstance(widget, Gtk.SpinButton): self.wallpaper_properties[wid]['speed'] = widget.get_value()
        elif isinstance(widget, Gtk.ComboBoxText): self.wallpaper_properties[wid]['scale'] = widget.get_active_text()
        self.save_properties()

    # --- Performance Fix: New handler for the "Apply" button ---
    def on_apply_changes_clicked(self, button):
        print("Applying property changes...")
        self.apply_wallpaper()

    def apply_wallpaper(self, wallpaper_id=None, monitor=None):
        wid_to_apply = wallpaper_id or self.selected_wallpaper_id
        monitor_to_apply = monitor or self.current_monitor
        if not wid_to_apply: return
        props = self.wallpaper_properties.get(str(wid_to_apply), {})
        audio = props.get('audio', False)
        speed = props.get('speed', 1.0)
        scale = props.get('scale', 'Cover').lower()
        mpv_opts = [f"--speed={speed}"]
        if not audio: mpv_opts.append("--no-audio")
        if scale == 'cover': mpv_opts.append("--panscan=1.0")
        elif scale == 'fill': mpv_opts.append("--video-aspect-method=stretch")
        env = os.environ.copy()
        env['MPV_EXTRA_OPTS'] = " ".join(mpv_opts)
        try:
            targets = self.monitors if monitor_to_apply == "All Monitors" else [monitor_to_apply]
            for m in targets:
                # Find wallpaper type for the selected ID
                wp_data = next((wp for wp in self.all_wallpapers if wp['id'] == str(wid_to_apply)), None)
                if wp_data:
                    print(f"Applying '{wp_data['type']}' wallpaper ID: {wid_to_apply} to monitor: {m}")
                    subprocess.Popen([SCRIPT_PATH, str(wid_to_apply), m], env=env)
                    self.current_wallpapers[m] = int(wid_to_apply)
        except Exception as e:
            print(f"Error launching wallpaper script: {e}")

    def on_wallpaper_clicked(self, button, wallpaper_id):
        """Handle wallpaper selection"""
        print(f"Wallpaper clicked: {wallpaper_id}")
        self.selected_wallpaper_id = wallpaper_id
        
        self.sidebar.set_visible(True)
        current_width = self.win.get_allocated_width()
        initial_position = int(current_width * 3 / 4)
        self.paned.set_position(initial_position)
        
        self.populate_sidebar_values()
        self.apply_wallpaper()

    def on_save_setup_clicked(self, button):
        config_to_save = {'wallpaper_dir': self.wallpaper_dir, 'wallpapers': self.current_wallpapers}
        try:
            with open(YAML_FILE, 'w') as f:
                yaml.dump(config_to_save, f, default_flow_style=False, sort_keys=False)
            print(f"Wallpaper setup saved to {YAML_FILE}")
        except Exception as e:
            print(f"Error saving wallpaper setup: {e}")
        print("Updating and saving properties for all active wallpapers...")
        for wallpaper_id in self.current_wallpapers.values():
            str_wallpaper_id = str(wallpaper_id)
            if str_wallpaper_id not in self.wallpaper_properties:
                print(f"Adding default properties for newly active wallpaper: {str_wallpaper_id}")
                self.wallpaper_properties[str_wallpaper_id] = {'audio': False, 'speed': 1.0, 'scale': 'Cover'}
        self.save_properties()
            
    def apply_config_from_file(self, config_path):
        self.on_stop_clicked(None)
        import time; time.sleep(0.5)
        if not os.path.exists(config_path): return
        config_data = {}
        try:
            with open(config_path, 'r') as f: config_data = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Error loading config for applying: {e}")
        wallpapers_to_apply = config_data.get("wallpapers", {})
        for monitor, wid in wallpapers_to_apply.items():
            if monitor in self.monitors:
                self.apply_wallpaper(wallpaper_id=str(wid), monitor=monitor)

    def on_monitor_changed(self, combo):
        self.current_monitor = combo.get_active_text()
        
    def on_stop_clicked(self, button):
        print("Stopping all wallpapers...")
        try:
            subprocess.run([SCRIPT_PATH, "stop"], check=True, timeout=5, capture_output=True, text=True)
            self.current_wallpapers.clear()
            print("All instances stopped and in-memory state cleared.")
        except Exception as e:
            if isinstance(e, subprocess.TimeoutExpired) or (hasattr(e, 'stderr') and e.stderr):
                 print(f"Error sending stop command: {e}")

    """
    def build_wallpaper_grid_section(self):
        # Create scrolled window
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_vexpand(True)
        scrolled_window.set_hexpand(True)
        #scrolled_window.set_valign(Gtk.Align.FILL)

        # Create FlowBox with proper settings for horizontal flow
        self.flowbox = Gtk.FlowBox()
        self.flowbox.add_css_class("highlight")
        
        # Orientation and selection settings
        self.flowbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        
        # Layout settings
        self.flowbox.set_homogeneous(False)
        self.flowbox.set_halign(Gtk.Align.FILL)
        self.flowbox.set_hexpand(True)
        self.flowbox.set_valign(Gtk.Align.START)
        
        # Spacing settings
        self.flowbox.set_column_spacing(15)
        self.flowbox.set_row_spacing(15)
        
        # Set margins
        self.flowbox.set_margin_top(15)
        self.flowbox.set_margin_bottom(15)
        self.flowbox.set_margin_start(15)
        self.flowbox.set_margin_end(15)

        # Put flowbox directly in scrolled window
        self.flowbox.add_css_class("flowbox-item")
        scrolled_window.set_child(self.flowbox)
        
        return scrolled_window
    """

    def build_wallpaper_grid_section(self):
        """Build the wallpaper grid section with proper horizontal layout"""
        # Create scrolled window
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_vexpand(True)
        scrolled_window.set_hexpand(True)

        # Create FlowBox with proper settings for horizontal flow
        self.flowbox = Gtk.FlowBox()
        self.flowbox.add_css_class("highlight")
        
        # Orientation and selection settings
        self.flowbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        
        # Layout settings
        self.flowbox.set_homogeneous(True)  # Change to True for consistent sizing
        self.flowbox.set_halign(Gtk.Align.START)  # Align to start instead of FILL
        self.flowbox.set_hexpand(True)
        self.flowbox.set_valign(Gtk.Align.START)
        
        # Spacing settings - reduce if needed
        self.flowbox.set_column_spacing(10)  # Reduced from 15
        self.flowbox.set_row_spacing(10)     # Reduced from 15
        
        # Set min/max children per line to control wrapping behavior
        self.flowbox.set_min_children_per_line(1)
        self.flowbox.set_max_children_per_line(30)  # Allow many items per line
        
        # Set margins
        self.flowbox.set_margin_top(15)
        self.flowbox.set_margin_bottom(15)
        self.flowbox.set_margin_start(15)
        self.flowbox.set_margin_end(15)

        scrolled_window.set_child(self.flowbox)
        
        return scrolled_window

    def create_wallpaper_widget(self, wallpaper_id, title, preview_path, wallpaper_type):
        """Create a properly sized wallpaper widget for horizontal flow"""
        # Main container with consistent sizing
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        main_box.set_size_request(160, 180)  # Fixed width, natural height
        main_box.set_halign(Gtk.Align.START)
        main_box.set_hexpand(False)

        # Image container with proper sizing
        image_frame = Gtk.Frame()
        image_frame.set_size_request(150, 100)  # Consistent image size
        image_frame.set_halign(Gtk.Align.CENTER)
        
        image = Gtk.Image()
        image.set_pixel_size(120)

        image.set_halign(Gtk.Align.CENTER)
        image.set_valign(Gtk.Align.CENTER)
        
        if os.path.exists(preview_path):
            try:
                image.set_from_file(preview_path)
            except Exception as e:
                print(f"Error loading image {preview_path}: {e}")
                self._set_missing_image(image)
        else:
            self._set_missing_image(image)
        
        image_frame.set_child(image)
        main_box.append(image_frame)
        
        # Title with proper wrapping
        title_label = Gtk.Label(label=title)
        title_label.set_wrap(False)
        #title_label.set_wrap_mode(2)  # WORD_CHAR
        title_label.set_justify(Gtk.Justification.CENTER)
        title_label.set_max_width_chars(18)
        title_label.set_lines(2)
        title_label.set_ellipsize(3)  # END
        title_label.set_halign(Gtk.Align.CENTER)
        title_label.set_size_request(150, 35)  # Fixed height for consistency
        main_box.append(title_label)
        
        # Type badge
        type_label = Gtk.Label()
        type_color = self._get_type_color(wallpaper_type)
        type_label.set_markup(f"<span size='x-small' color='{type_color}'><b>{wallpaper_type.upper()}</b></span>")
        type_label.set_halign(Gtk.Align.CENTER)
        main_box.append(type_label)
        
        # Button wrapper
        button = Gtk.Button()
        button.set_child(main_box)
        button.add_css_class("highlight")
        
        # Let the button size naturally based on content
        button.set_hexpand(False)
        button.set_vexpand(False)
        button.set_halign(Gtk.Align.START)
        
        button.connect('clicked', self.on_wallpaper_clicked, wallpaper_id)
        
        # Store data
        button.wallpaper_id = wallpaper_id
        button.wallpaper_type = wallpaper_type
        button.wallpaper_title = title
        
        return button

    def _set_missing_image(self, image: Gtk.Image):
        """Helper method to set missing image icon using Gtk.Image"""
        icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        # Lookup the icon as a Gdk.Paintable
        icon = icon_theme.lookup_icon(
            "image-missing", 100,  # size in pixels
            0  # flags
        )
        if icon:
            image.set_from_paintable(icon.load_icon())  # convert GIcon/Gdk.Paintable to set_from_paintable
        else:
            image.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)


    def _get_type_color(self, wallpaper_type):
        """Get color for wallpaper type badge"""
        colors = {
            'video': '#3498db',
            'scene': '#2ecc71', 
            'web': '#e74c3c'
        }
        return colors.get(wallpaper_type.lower(), '#95a5a6')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A GTK selector for mpvpaper-WE.")
    parser.add_argument('--load-config', dest='config_file', metavar='FILE_PATH', help='Load and apply a specific config YAML on startup.')
    args = parser.parse_args()
    app = WallpaperSelectorApp(config_file_to_load=args.config_file)
    app.run(sys.argv)

