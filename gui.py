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

from config.constants import *
from config.config_manager import ConfigManager
from data.wallpaper_data import WallpaperDataManager
from managers.monitor_manager import MonitorManager
from ui.ui_builder import UIBuilder, GridManager

from ui.dialogs import OffsetDialog
class WallpaperSelectorApp(Gtk.Application):
    def __init__(self, *args, config_file_to_load=None, **kwargs):
        super().__init__(*args, application_id="wallpaper_app", **kwargs)
        self.win = None
        self.paned = None
        self.config_to_load_on_startup = config_file_to_load

        self.config_manager = ConfigManager()
        self.config_manager.ensure_config_dir()
        self.config = self.config_manager.load_config()
        self.wallpaper_dir = self.config.get('wallpaper_dir', DEFAULT_WALLPAPER_DIR)
        # self.current_wallpapers will now be managed by MonitorManager
        # self.current_wallpapers = self.config.get("wallpapers", {})

        self.monitor_manager = MonitorManager()
        self.monitors = self.monitor_manager.detect_monitors()
        self.wallpaper_properties = self.config_manager.load_properties()

        self.data_manager = WallpaperDataManager(self.wallpaper_dir)
        self.all_wallpapers = []
        self.search_term = ""
        self.type_filters = {"video": True, "scene": True, "web": True}
        
        self.current_monitor = "All Monitors"
        self.selected_wallpaper_id = None
        self.property_signal_handlers = {}
        self.setup_signal_handlers()

        # Initialize UI Builder and Grid Manager
        self.ui_builder = None
        self.grid_manager = None
        
        # Setup CSS
        self.setup_css()

    def setup_css(self):
        css_provider = Gtk.CssProvider()
        try:
            css_provider.load_from_path("style.css")
            # Apply CSS provider to the default display
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        except Exception as e:
            print(f"Could not load CSS file: {e}")

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
        # Define callbacks for the UI builder
        callbacks = {
            'on_save_setup_clicked': self.on_save_setup_clicked,
            'on_configure_offset_clicked': self.on_configure_offset_clicked,
            'on_refresh_clicked': self.on_refresh_clicked,
            'on_search_changed': self.on_search_changed,
            'on_monitor_changed': self.on_monitor_changed,
            'on_filter_toggled': self.on_filter_toggled,
            'hide_sidebar': self.hide_sidebar,
            'on_apply_changes_clicked': self.on_apply_changes_clicked
        }
        
        # Create UI Builder and build the main UI
        self.ui_builder = UIBuilder(self.win, callbacks, self.monitors)
        content_box, sidebar, prop_widgets_box = self.ui_builder.build_main_ui()
        
        # Get references to important widgets
        self.sidebar = sidebar
        self.prop_widgets_box = prop_widgets_box
        self.monitor_combo = self.ui_builder.build_header_bar().get_last_child()  # Assuming monitor combo is the last child
        
        # Get sidebar widgets
        sidebar_widgets = self.ui_builder.get_sidebar_widgets()
        self.sidebar_image = sidebar_widgets['image']
        self.audio_check = sidebar_widgets['audio_check']
        self.speed_spin = sidebar_widgets['speed_spin']
        self.scale_combo = sidebar_widgets['scale_combo']
        
        # Setup property signal handlers
        self.property_signal_handlers = {}
        self.property_signal_handlers['audio'] = self.audio_check.connect('toggled', self.on_property_changed)
        self.property_signal_handlers['speed'] = self.speed_spin.connect('value-changed', self.on_property_changed)
        self.property_signal_handlers['scale'] = self.scale_combo.connect('changed', self.on_property_changed)
        
        # Initialize Grid Manager
        self.grid_manager = GridManager(self.ui_builder.flowbox)
        
        # Load data and populate grid
        self.all_wallpapers = self.data_manager.load_wallpaper_data()
        # Initialize current_wallpapers from config
        self.monitor_manager.current_wallpapers = self.config.get("wallpapers", {})
        self.grid_manager.populate_grid(self.all_wallpapers, self.on_wallpaper_clicked)
        
        # Apply initial filtering
        self.type_filters = self.ui_builder.get_filter_states()
        self.apply_filters()

    def apply_filters(self):
        """Apply search and type filters to wallpapers"""
        # Get current filter states from UI Builder
        self.type_filters = self.ui_builder.get_filter_states()
        self.filtered_wallpapers = self.data_manager.apply_filters(self.search_term, self.type_filters)
        self.grid_manager.apply_filters(self.filtered_wallpapers)

    def populate_sidebar_values(self):
        if not self.selected_wallpaper_id: return
        wp_data = self.data_manager.get_wallpaper_by_id(self.selected_wallpaper_id)
        if not wp_data: return

        if os.path.exists(wp_data.preview_path):
            self.sidebar_image.set_filename(wp_data.preview_path)
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

    def on_wallpaper_clicked(self, button, wallpaper_id):
        """Handle wallpaper selection"""
        print(f"Wallpaper clicked: {wallpaper_id}")
        self.selected_wallpaper_id = wallpaper_id
        
        self.sidebar.set_visible(True)
        current_width = self.win.get_allocated_width()
        initial_position = int(current_width * 3 / 4)
        self.ui_builder.set_paned_position(initial_position)
        
        self.populate_sidebar_values()
        self.apply_wallpaper()

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
            self.config_manager.save_properties(self.wallpaper_properties)
            print("Panel margins saved. Relaunch any active Web or Scene wallpapers to see changes.")
        dialog.destroy()

    def hide_sidebar(self, button):
        self.sidebar.set_visible(False)

    def populate_sidebar_values(self):
        if not self.selected_wallpaper_id: return
        wp_data = self.data_manager.get_wallpaper_by_id(self.selected_wallpaper_id)
        if not wp_data: return

        if os.path.exists(wp_data.preview_path):
            self.sidebar_image.set_filename(wp_data.preview_path)
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
        self.config_manager.save_properties(self.wallpaper_properties)

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
            wp_data = self.data_manager.get_wallpaper_by_id(str(wid_to_apply))
            if wp_data:
                self.monitor_manager.apply_wallpaper(
                    str(wid_to_apply), 
                    monitor_to_apply, 
                    props, 
                    wp_data.type
                )
        except Exception as e:
            print(f"Error launching wallpaper script: {e}")


    def on_save_setup_clicked(self, button):
        self.current_wallpapers = self.monitor_manager.current_wallpapers
        config_to_save = {'wallpaper_dir': self.wallpaper_dir, 'wallpapers': self.current_wallpapers}
        self.config_manager.save_config(config_to_save)
        print(f"Wallpaper setup saved to {YAML_FILE}")
        print("Updating and saving properties for all active wallpapers...")
        for wallpaper_id in self.current_wallpapers.values():
            str_wallpaper_id = str(wallpaper_id)
            if str_wallpaper_id not in self.wallpaper_properties:
                print(f"Adding default properties for newly active wallpaper: {str_wallpaper_id}")
                self.wallpaper_properties[str_wallpaper_id] = {'audio': False, 'speed': 1.0, 'scale': 'Cover'}
        self.config_manager.save_properties(self.wallpaper_properties)

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
        # Update MonitorManager's current_wallpapers
        self.monitor_manager.current_wallpapers = wallpapers_to_apply.copy()
        for monitor, wid in wallpapers_to_apply.items():
            if monitor in self.monitors:
                self.apply_wallpaper(wallpaper_id=str(wid), monitor=monitor)

    def on_monitor_changed(self, combo):
        self.current_monitor = combo.get_active_text()
        
    def on_refresh_clicked(self, button):
        """Handle refresh button click: reload wallpapers and update grid"""
        print("Refreshing wallpapers...")
        # Refresh the data
        self.all_wallpapers = self.data_manager.refresh_wallpapers()
        # Repopulate the grid with the new data
        self.grid_manager.populate_grid(self.all_wallpapers, self.on_wallpaper_clicked)
        # Re-apply the current filters to update the grid view
        self.apply_filters()
        print("Wallpapers refreshed.")
        
    def on_stop_clicked(self, button):
        self.monitor_manager.stop_all_wallpapers()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A GTK selector for mpvpaper-WE.")
    parser.add_argument('--load-config', dest='config_file', metavar='FILE_PATH', help='Load and apply a specific config YAML on startup.')
    args = parser.parse_args()
    app = WallpaperSelectorApp(config_file_to_load=args.config_file)
    app.run(sys.argv)


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
