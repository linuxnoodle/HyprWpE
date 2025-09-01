import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

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
