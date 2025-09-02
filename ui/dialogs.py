import os
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

# CSS for styling
css = """
.no-wallpaper-box {
    background-color: #333;
    border: 1px solid #555;
}
.selected-monitor {
    border: 2px solid #4e9af1;
    border-radius: 4px;
}
"""

class OffsetDialog(Gtk.Dialog):
    """A dialog window for configuring panel margins, updated for modern GTK4."""
    def __init__(self, parent, current_margins):
        super().__init__(title="Configure Panel Margins", transient_for=parent, modal=True)
        self.current_margins = current_margins
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_margin_top(10)
        main_box.set_margin_bottom(10)
        main_box.set_margin_start(10)
        main_box.set_margin_end(10)
        self.get_content_area().append(main_box)
        
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
        
        self.top_spin.set_value(self.current_margins.get("top", 0))
        self.bottom_spin.set_value(self.current_margins.get("bottom", 0))
        self.left_spin.set_value(self.current_margins.get("left", 0))
        self.right_spin.set_value(self.current_margins.get("right", 0))
        
        grid.attach(Gtk.Label(label="Top:"), 0, 0, 1, 1)
        grid.attach(self.top_spin, 1, 0, 1, 1)
        grid.attach(Gtk.Label(label="Bottom:"), 0, 1, 1, 1)
        grid.attach(self.bottom_spin, 1, 1, 1, 1)
        grid.attach(Gtk.Label(label="Left:"), 0, 2, 1, 1)
        grid.attach(self.left_spin, 1, 2, 1, 1)
        grid.attach(Gtk.Label(label="Right:"), 0, 3, 1, 1)
        grid.attach(self.right_spin, 1, 3, 1, 1)
        
        self.add_button("_Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("_Save", Gtk.ResponseType.OK)
        

class MonitorSelectionDialog(Gtk.Dialog):
    """Dialog for selecting monitors with live previews"""
    def __init__(self, parent, monitor_manager, wallpaper_data, wallpaper_id):
        super().__init__(title="Select Monitors", transient_for=parent, modal=True)
        self.monitor_manager = monitor_manager
        self.wallpaper_data = wallpaper_data
        self.wallpaper_id = wallpaper_id
        self.selected_monitors = set()
        
        # Apply CSS styling
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css, -1)
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        # Main content area
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.set_margin_top(10)
        content.set_margin_bottom(10)
        content.set_margin_start(10)
        content.set_margin_end(10)
        self.get_content_area().append(content)
        
        # Create monitor grid - scaled down to 1/15 of actual size
        self.monitor_grid = Gtk.Grid()
        self.monitor_grid.set_column_homogeneous(False)
        self.monitor_grid.set_row_homogeneous(False)
        content.append(self.monitor_grid)
        
        # Add scrollable container
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_child(self.monitor_grid)
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        content.append(scrolled_window)
        
        # Action buttons
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        apply_button = self.add_button("Apply", Gtk.ResponseType.OK)
        apply_button.connect("clicked", self.on_apply_clicked)
        
        # Populate monitors
        self.populate_monitor_grid()
        
    def on_apply_clicked(self, button):
        """Handle Apply button click to apply wallpapers to selected monitors"""
        if self.selected_monitors:
            self.apply_wallpapers(self.wallpaper_id)
            self.response(Gtk.ResponseType.OK)
        else:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                modal=True,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK,
                text="No monitors selected"
            )
            dialog.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
            dialog.run()
            dialog.destroy()

    def populate_monitor_grid(self):
        """Populate the grid with monitor representations scaled down"""
        monitors = self.monitor_manager.get_detailed_monitors()
        
        # Find max dimensions to determine scaling factor
        max_width = max(monitor['width'] for monitor in monitors) if monitors else 1920
        scale_factor = max(15, max_width // 200)  # Scale to 1/15 to 1/20 of actual size
        
        for monitor in monitors:
            frame = Gtk.Frame()
            frame.set_css_classes(["monitor-frame"])
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            frame.set_child(box)
            
            # Monitor name
            label = Gtk.Label(label=monitor['name'])
            box.append(label)
            
            # Wallpaper preview or default box
            preview_box = Gtk.Box()
            preview_box.set_size_request(
                monitor['width'] // scale_factor,
                monitor['height'] // scale_factor
            )
            
            if monitor['wallpaper_id']:
                wallpaper = self.wallpaper_data.get_wallpaper_by_id(str(monitor['wallpaper_id']))
                if wallpaper and os.path.exists(wallpaper.preview_path):
                    picture = Gtk.Picture.new_for_filename(wallpaper.preview_path)
                    picture.set_content_fit(Gtk.ContentFit.SCALE_DOWN)
                    picture.set_size_request(
                        monitor['width'] // scale_factor,
                        monitor['height'] // scale_factor
                    )
                    preview_box.append(picture)
                else:
                    preview_box.set_css_classes(["no-wallpaper-box"])
            else:
                preview_box.set_css_classes(["no-wallpaper-box"])
            
            box.append(preview_box)
            
            # Make selectable
            gesture = Gtk.GestureClick()
            gesture.connect("pressed", self.on_monitor_clicked, monitor['name'], frame)
            frame.add_controller(gesture)
            
            # Position in grid based on scaled monitor coordinates
            self.monitor_grid.attach(
                frame, 
                monitor['x'] // scale_factor, 
                monitor['y'] // scale_factor, 
                1, 
                1
            )

    def on_monitor_clicked(self, gesture, n_press, x, y, monitor_name, frame):
        """Handle monitor selection"""
        if monitor_name in self.selected_monitors:
            self.selected_monitors.remove(monitor_name)
            frame.remove_css_class("selected-monitor")
        else:
            self.selected_monitors.add(monitor_name)
            frame.add_css_class("selected-monitor")
            
    def get_selected_monitors(self):
        """Return the list of selected monitor names."""
        return list(self.selected_monitors)
        
    def apply_wallpapers(self, wallpaper_id):
        """Apply wallpaper to all selected monitors."""
        # Use the existing monitor_manager and wallpaper_data instances
        if wallpaper_id:
            for monitor_name in self.selected_monitors:
                monitor = self.monitor_manager.get_monitor_by_name(monitor_name)
                if monitor:
                    self.wallpaper_data.set_wallpaper_for_monitor(monitor['id'], wallpaper_id)
                    self.monitor_manager.apply_wallpaper(monitor['id'], wallpaper_id)
                    
            self.wallpaper_data.save()
            self.monitor_manager.save_config()
        else:
            print("No wallpaper selected to apply")
