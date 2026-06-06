import gi
import os
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gdk, GdkPixbuf
from config.constants import WALLPAPER_WIDGET_WIDTH, WALLPAPER_WIDGET_HEIGHT, IMAGE_FRAME_WIDTH, IMAGE_FRAME_HEIGHT

class WallpaperWidget:
    @staticmethod
    def create(wallpaper, on_click_callback):
        """Create a properly sized wallpaper widget for horizontal flow"""
        # Main container with consistent sizing
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        main_box.set_size_request(WALLPAPER_WIDGET_WIDTH, WALLPAPER_WIDGET_HEIGHT)
        main_box.set_halign(Gtk.Align.START)
        main_box.set_hexpand(False)

        # Image container with proper sizing
        image_frame = Gtk.Frame()
        image_frame.set_size_request(IMAGE_FRAME_WIDTH, IMAGE_FRAME_HEIGHT)
        image_frame.set_halign(Gtk.Align.CENTER)
        image_frame.set_margin_top(15)
        
        image = Gtk.Image()
        image.set_pixel_size(120)
        image.set_halign(Gtk.Align.CENTER)
        image.set_valign(Gtk.Align.CENTER)
        
        if os.path.exists(wallpaper.preview_path):
            try:
                # Check if file is a GIF and handle it as animation
                if wallpaper.preview_path.lower().endswith('.gif'):
                    try:
                        pixbuf_animation = GdkPixbuf.PixbufAnimation.new_from_file(wallpaper.preview_path)
                        # Try different methods for different GTK versions
                        if hasattr(image, 'set_from_animation'):
                            image.set_from_animation(pixbuf_animation)
                        elif hasattr(image, 'set_pixbuf_animation'):
                            image.set_pixbuf_animation(pixbuf_animation)
                        else:
                            # Fallback: get first frame as static pixbuf
                            pixbuf = pixbuf_animation.get_static_image()
                            image.set_from_pixbuf(pixbuf)
                    except Exception:
                        # Fallback to static image
                        image.set_from_file(wallpaper.preview_path)
                else:
                    image.set_from_file(wallpaper.preview_path)
            except Exception:
                WallpaperWidget._set_missing_image(image)
        else:
            # Check for preview.gif as fallback for scene wallpapers
            preview_gif_path = os.path.join(os.path.dirname(wallpaper.preview_path), "preview.gif")
            if wallpaper.type.lower() == "scene" and os.path.exists(preview_gif_path):
                try:
                    # Handle preview.gif as animation
                    if preview_gif_path.lower().endswith('.gif'):
                        try:
                            pixbuf_animation = GdkPixbuf.PixbufAnimation.new_from_file(preview_gif_path)
                            # Try different methods for different GTK versions
                            if hasattr(image, 'set_from_animation'):
                                image.set_from_animation(pixbuf_animation)
                            elif hasattr(image, 'set_pixbuf_animation'):
                                image.set_pixbuf_animation(pixbuf_animation)
                            else:
                                # Fallback: get first frame as static pixbuf
                                pixbuf = pixbuf_animation.get_static_image()
                                image.set_from_pixbuf(pixbuf)
                        except Exception:
                            # Fallback to static image
                            image.set_from_file(preview_gif_path)
                    else:
                        image.set_from_file(preview_gif_path)
                except Exception:
                    WallpaperWidget._set_missing_image(image)
            else:
                WallpaperWidget._set_missing_image(image)
        
        image_frame.set_child(image)
        main_box.append(image_frame)
        
        # Title with proper wrapping
        title_label = Gtk.Label(label=wallpaper.title)
        title_label.set_wrap(False)
        title_label.set_justify(Gtk.Justification.CENTER)
        title_label.set_max_width_chars(18)
        title_label.set_lines(2)
        title_label.set_ellipsize(3)  # END
        title_label.set_halign(Gtk.Align.CENTER)
        title_label.set_size_request(IMAGE_FRAME_WIDTH, 35)
        main_box.append(title_label)
        
        # Type badge
        type_label = Gtk.Label()
        type_color = WallpaperWidget._get_type_color(wallpaper.type)
        type_label.set_markup(f"<span size='x-small' color='{type_color}'><b>{wallpaper.type.upper()}</b></span>")
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
        
        button.connect('clicked', on_click_callback, wallpaper.id)
        
        return button

    @staticmethod
    def _set_missing_image(image: Gtk.Image):
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

    @staticmethod
    def _get_type_color(wallpaper_type):
        """Get color for wallpaper type badge"""
        colors = {
            'video': '#3498db',
            'scene': '#2ecc71', 
            'web': '#e74c3c'
        }
        return colors.get(wallpaper_type.lower(), '#95a5a6')


class FilterComponents:
    @staticmethod
    def create_type_filter(filter_type: str, active: bool, callback) -> Gtk.CheckButton:
        checkbox = Gtk.CheckButton(label=filter_type.capitalize())
        checkbox.set_active(active)
        checkbox.connect("toggled", callback, filter_type.lower())
        return checkbox


class PropertyControls:
    @staticmethod
    def create_audio_toggle() -> Gtk.CheckButton:
        return Gtk.CheckButton(label="Enable Audio")

    @staticmethod
    def create_speed_control() -> Gtk.Box:
        speed_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, valign=Gtk.Align.CENTER)
        speed_box.append(Gtk.Label(label="Speed:"))
        speed_spin = Gtk.SpinButton.new_with_range(0.1, 4.0, 0.05)
        speed_spin.set_hexpand(True)
        speed_box.append(speed_spin)
        return speed_box

    @staticmethod
    def create_scale_selector() -> Gtk.Box:
        scale_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, valign=Gtk.Align.CENTER)
        scale_box.append(Gtk.Label(label="Scale Mode:"))
        scale_combo = Gtk.ComboBoxText()
        scale_combo.append_text("Cover")
        scale_combo.append_text("Contain")
        scale_combo.append_text("Fill")
        scale_combo.set_hexpand(True)
        scale_box.append(scale_combo)
        return scale_box

    @staticmethod
    def create_dynamic_bool(label_text: str, default_value: bool) -> Gtk.CheckButton:
        checkbox = Gtk.CheckButton(label=label_text)
        checkbox.set_active(default_value)
        return checkbox

    @staticmethod
    def create_dynamic_slider(label_text: str, min_val: float, max_val: float, step: float, default_value: float) -> tuple:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, valign=Gtk.Align.CENTER)
        label = Gtk.Label(label=label_text)
        label.set_xalign(0)
        box.append(label)
        
        # Determine digits based on step
        digits = 0
        if step < 1:
            digits = len(str(step).split('.')[-1])
            
        adjustment = Gtk.Adjustment(value=default_value, lower=min_val, upper=max_val, step_increment=step, page_increment=step * 10)
        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adjustment)
        scale.set_digits(digits)
        scale.set_draw_value(True)
        scale.set_hexpand(True)
        box.append(scale)
        return box, scale

    @staticmethod
    def create_dynamic_combo(label_text: str, options: list, default_value: str) -> tuple:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, valign=Gtk.Align.CENTER)
        label = Gtk.Label(label=label_text)
        label.set_xalign(0)
        box.append(label)
        
        combo = Gtk.ComboBoxText()
        active_index = 0
        for i, opt in enumerate(options):
            combo.append(opt['value'], opt['label'])
            if str(opt['value']) == str(default_value):
                active_index = i
                
        combo.set_active(active_index)
        combo.set_hexpand(True)
        box.append(combo)
        return box, combo

    @staticmethod
    def create_dynamic_color(label_text: str, default_rgb_str: str) -> tuple:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, valign=Gtk.Align.CENTER)
        label = Gtk.Label(label=label_text)
        label.set_xalign(0)
        box.append(label)
        
        color_btn = Gtk.ColorButton()
        # default_rgb_str is typically "r g b" like "1 1 1" or "0.5 0.5 0.5"
        try:
            r, g, b = map(float, default_rgb_str.split())
            rgba = Gdk.RGBA()
            rgba.red = r
            rgba.green = g
            rgba.blue = b
            rgba.alpha = 1.0
            color_btn.set_rgba(rgba)
        except Exception:
            pass
            
        color_btn.set_hexpand(True)
        box.append(color_btn)
        return box, color_btn
