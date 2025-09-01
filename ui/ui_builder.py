import gi
from gi.repository import Gtk, Gdk

from config.constants import WALLPAPER_WIDGET_WIDTH, WALLPAPER_WIDGET_HEIGHT

class UIBuilder:
    def __init__(self, app_window: Gtk.ApplicationWindow, callbacks: dict, monitors: list):
        self.window = app_window
        self.callbacks = callbacks
        self.monitors = monitors
        self.filter_widgets = {}
        
    def build_main_ui(self) -> tuple:
        """Build the main UI and return (content_box, sidebar, prop_widgets_box, monitor_combo)"""
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.window.set_child(main_box)

        titlebar = self.build_header_bar()
        main_box.append(titlebar)

        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        content_box.set_vexpand(True)
        main_box.append(content_box)

        filter_sidebar = self.build_filter_sidebar()
        content_box.append(filter_sidebar)

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_hexpand(True)
        content_box.append(paned)

        scrolled_window = self.build_wallpaper_grid()
        paned.set_start_child(scrolled_window)

        sidebar, prop_widgets_box = self.build_properties_sidebar()
        sidebar.set_visible(False)
        paned.set_end_child(sidebar)
        
        # Store references for later use
        self.paned = paned
        self.sidebar = sidebar

        return content_box, sidebar, prop_widgets_box

    def build_header_bar(self) -> Gtk.Box:
        titlebar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6,
                           margin_start=6, margin_end=6, margin_top=6, margin_bottom=6)

        save_button = Gtk.Button(label="Save Setup")
        save_button.connect('clicked', self.callbacks['on_save_setup_clicked'])
        titlebar.append(save_button)

        offset_button = Gtk.Button(label="Configure Offset")
        offset_button.connect('clicked', self.callbacks['on_configure_offset_clicked'])
        titlebar.append(offset_button)
        
        refresh_button = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        refresh_button.set_tooltip_text("Refresh Wallpapers")
        refresh_button.connect('clicked', self.callbacks['on_refresh_clicked'])
        titlebar.append(refresh_button)

        search_entry = Gtk.SearchEntry(placeholder_text="Search wallpapers...")
        search_entry.connect("search-changed", self.callbacks['on_search_changed'])
        titlebar.append(search_entry)

        monitor_combo = Gtk.ComboBoxText()
        monitor_combo.append_text("All Monitors")
        for m in self.monitors:
            monitor_combo.append_text(m)
        monitor_combo.set_active(0)
        monitor_combo.connect("changed", self.callbacks['on_monitor_changed'])
        titlebar.append(monitor_combo)

        return titlebar

    def build_filter_sidebar(self) -> Gtk.Box:
        from ui.components import FilterComponents
        
        filter_sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                                 margin_top=10, margin_bottom=10,
                                 margin_start=10, margin_end=10, width_request=180)

        filter_sidebar.append(Gtk.Label(label="<big><b>Filter by Type</b></big>",
                                        use_markup=True, halign=Gtk.Align.START))

        video_check = FilterComponents.create_type_filter("video", True, self.callbacks['on_filter_toggled'])
        filter_sidebar.append(video_check)
        self.filter_widgets['video'] = video_check

        scene_check = FilterComponents.create_type_filter("scene", True, self.callbacks['on_filter_toggled'])
        filter_sidebar.append(scene_check)
        self.filter_widgets['scene'] = scene_check

        web_check = FilterComponents.create_type_filter("web", True, self.callbacks['on_filter_toggled'])
        filter_sidebar.append(web_check)
        self.filter_widgets['web'] = web_check

        return filter_sidebar

    def build_wallpaper_grid(self) -> Gtk.ScrolledWindow:
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

    def build_properties_sidebar(self) -> tuple:
        from ui.components import PropertyControls
        
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                          margin_top=10, margin_bottom=10,
                          margin_start=10, margin_end=10)

        sidebar_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        sidebar_title = Gtk.Label(label="<big><b>Properties</b></big>",
                                  use_markup=True, halign=Gtk.Align.START, hexpand=True)
        sidebar_header.append(sidebar_title)
        close_button = Gtk.Button.new_from_icon_name("window-close-symbolic")
        close_button.add_css_class("flat")
        close_button.connect('clicked', self.callbacks['hide_sidebar'])
        sidebar_header.append(close_button)
        sidebar.append(sidebar_header)

        sidebar_image = Gtk.Picture()
        sidebar_image.set_keep_aspect_ratio(True)
        sidebar_image.set_can_shrink(True)
        sidebar_image.set_margin_bottom(10)
        sidebar.append(sidebar_image)

        prop_widgets_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                                   sensitive=False)
        sidebar.append(prop_widgets_box)

        audio_check = PropertyControls.create_audio_toggle()
        prop_widgets_box.append(audio_check)

        speed_box = PropertyControls.create_speed_control()
        # Need to get the spin button from the box
        speed_spin = speed_box.get_last_child()  # Assuming spin button is the last child
        prop_widgets_box.append(speed_box)

        scale_box = PropertyControls.create_scale_selector()
        # Need to get the combo box from the box
        scale_combo = scale_box.get_last_child()  # Assuming combo box is the last child
        prop_widgets_box.append(scale_box)

        apply_button = Gtk.Button(label="Apply Changes", margin_top=10)
        apply_button.connect("clicked", self.callbacks['on_apply_changes_clicked'])
        prop_widgets_box.append(apply_button)
        
        # Store references to widgets that need to be accessed later
        self.sidebar_image = sidebar_image
        self.audio_check = audio_check
        self.speed_spin = speed_spin
        self.scale_combo = scale_combo
        self.prop_widgets_box = prop_widgets_box

        return sidebar, prop_widgets_box

    def setup_css_styling(self) -> None:
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

    def get_filter_states(self) -> dict:
        """Get the current states of all filter checkboxes"""
        return {
            'video': self.filter_widgets['video'].get_active(),
            'scene': self.filter_widgets['scene'].get_active(),
            'web': self.filter_widgets['web'].get_active()
        }

    def set_sidebar_visible(self, visible: bool) -> None:
        """Set the visibility of the properties sidebar"""
        if hasattr(self, 'sidebar'):
            self.sidebar.set_visible(visible)
            
    def set_paned_position(self, position: int) -> None:
        """Set the position of the paned container"""
        if hasattr(self, 'paned'):
            self.paned.set_position(position)

    def get_sidebar_widgets(self) -> dict:
        """Get references to the sidebar widgets"""
        return {
            'image': self.sidebar_image,
            'audio_check': self.audio_check,
            'speed_spin': self.speed_spin,
            'scale_combo': self.scale_combo,
            'prop_widgets_box': self.prop_widgets_box
        }

class GridManager:
    def __init__(self, flowbox: Gtk.FlowBox):
        self.flowbox = flowbox
        self.wallpaper_widgets = {}

    def populate_grid(self, wallpapers, on_wallpaper_clicked_callback) -> None:
        """Populate the flowbox with wallpaper widgets"""
        from ui.components import WallpaperWidget
        
        print(f"Populating grid with {len(wallpapers)} wallpapers...")
        
        # Clear existing widgets
        self.clear_grid()
        
        # Create widgets for all wallpapers
        for wp_data in wallpapers:
            widget = WallpaperWidget.create(wp_data, on_wallpaper_clicked_callback)
            
            # Store in our dictionary
            self.wallpaper_widgets[wp_data.id] = widget
            
            # Add to flowbox
            self.flowbox.append(widget)
            flowbox_child = widget.get_parent()
            if flowbox_child:
                flowbox_child.set_size_request(WALLPAPER_WIDGET_WIDTH, WALLPAPER_WIDGET_HEIGHT)
                flowbox_child.set_halign(Gtk.Align.START)
        
        print(f"Created {len(self.wallpaper_widgets)} wallpaper widgets")

    def clear_grid(self) -> None:
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

    def apply_filters(self, filtered_wallpapers) -> None:
        """Apply filters to show only relevant wallpapers"""
        # Remove all widgets from flowbox first
        child = self.flowbox.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.flowbox.remove(child)
            child = next_child
        
        # Re-add only the widgets that should be visible
        for wp_data in filtered_wallpapers:
            widget = self.wallpaper_widgets.get(wp_data.id)
            if not widget:
                continue
            
            self.flowbox.append(widget)
            
            # Set size on the FlowBoxChild after re-adding
            flowbox_child = widget.get_parent()
            if flowbox_child:
                flowbox_child.set_size_request(WALLPAPER_WIDGET_WIDTH, -1)
                flowbox_child.set_halign(Gtk.Align.START)
        
        print(f"Showing {len(filtered_wallpapers)} wallpapers")
