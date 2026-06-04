#!/usr/bin/env python3
"""
Niri Hotkey Cheatsheet Widget
Transparent, always-on-top floating overlay for Wayland/Niri.
Toggle with: niri-cheatsheet.py --toggle
"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import sys
import os
import socket
import threading

# Local helper: loads TallBF.txt and returns colored Pango markup.
from ascii_art import load_flower

#Socket is a communication channel, when a hotkey is pressed it runs the script and connects to the socket.
#this is the location of the socket
SOCKET_PATH = "/tmp/niri-cheatsheet.sock"

#Hotkeys for Niri
HOTKEYS = {
    "Navigation": [
        ("Super + H/L",         "Focus window left/right"),
        ("Super + J/K",         "Focus window down/up"),
        ("Super + Shift + H/L", "Move window left/right"),
        ("Super + Shift + J/K", "Move window down/up"),
        ("Super + Tab",         "Switch to next workspace"),
        ("Super + Shift + Tab", "Switch to prev workspace"),
        ("Super + 1-9",         "Go to workspace N"),
        ("Super + Shift + 1-9", "Move window to workspace N"),
    ],
    "Windows": [
        ("Super + Q",           "Close focused window"),
        ("Super + F",           "Toggle fullscreen"),
        ("Super + Shift + F",   "Toggle floating"),
        ("Super + M",           "Maximize window"),
        ("Super + R",           "Enter resize mode"),
        ("Super + ,",           "Consume into column"),
        ("Super + .",           "Expel from column"),
        ("Super + W",           "Switch preset column widths"),
    ],
    "Workspaces": [
        ("Super + U",           "Focus monitor left"),
        ("Super + I",           "Focus monitor right"),
        ("Super + Shift + U",   "Move window to monitor left"),
        ("Super + Shift + I",   "Move window to monitor right"),
        ("Super + Ctrl + Up",   "Move workspace up"),
        ("Super + Ctrl + Down", "Move workspace down"),
    ],
    "Apps & System": [
        ("Super + Return",      "Open terminal"),
        ("Super + Space",       "Open app launcher"),
        ("Super + E",           "Open file manager"),
        ("Super + B",           "Open browser"),
        ("Super + L",           "Lock screen"),
        ("Super + Shift + E",   "Exit niri"),
        ("Super + Shift + R",   "Reload config"),
        ("PrtSc",               "Screenshot"),
        ("Super + PrtSc",       "Screenshot region"),
    ],
    "Layout": [
        ("Super + Shift + H/L", "Shift column left/right"),
        ("Super + Ctrl + H/L",  "Resize column left/right"),
        ("Super + Ctrl + J/K",  "Resize window down/up"),
        ("Super + Plus/Minus",  "Change gap size"),
    ],
}

CSS = b"""
/* Catppuccin Mocha palette with teal accents. */
window {
    background-color: rgba(24, 24, 37, 0.78);
    border-radius: 12px;
}
* {
    color: #cdd6f4; /* Mocha Text */
    font-family: 'JetBrains Mono', 'Fira Code', 'Monospace';
}
#header {
    font-size: 13px;
    font-weight: bold;
    color: #94e2d5; /* Mocha Teal */
    letter-spacing: 2px;
    padding: 14px 18px 6px 18px;
    border-bottom: 1px solid rgba(148, 226, 213, 0.25);
}
#hint {
    font-size: 10px;
    color: rgba(166, 173, 200, 0.55); /* dimmed Subtext0 */
    padding: 4px 18px 0 18px;
}
.section-label {
    font-size: 10px;
    font-weight: bold;
    color: #89dceb; /* Mocha Sky */
    letter-spacing: 1.5px;
    padding: 10px 18px 3px 18px;
}
.keybind-row {
    padding: 2px 18px;
}
.key {
    font-size: 11px;
    color: #94e2d5; /* Mocha Teal */
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    min-width: 190px;
}
.desc {
    font-size: 11px;
    color: rgba(186, 194, 222, 0.85); /* Mocha Subtext1 */
}
#close-btn {
    padding: 0;
    margin: 0;
    background: transparent;
    border: none;
    color: rgba(108, 112, 134, 0.6); /* Mocha Overlay0 */
    font-size: 14px;
    min-width: 24px;
    min-height: 24px;
}
#close-btn:hover {
    color: #94e2d5; /* Mocha Teal */
}
#scrolled {
    background: transparent;
}
#bg-art {
    /* Background Braille flower behind the keybindings.
       Opacity is set programmatically via set_opacity() so this rule only
       handles font-related styling. Monospace is required so columns align. */
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 14px;
}
"""

#the Widget itself, inherits from Gtk.Window which is just a basic Window object
class NiriCheatsheet(Gtk.Window):
    def __init__(self):
        # initializes Gtk.Window, it is type of TOPLEVEL (normal window managed by compositor, can be moved, focused, stacked.)
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        # takes CSS string and loads it into the GTK style engine, this affects fonts, colors, padding.
        self._apply_style()
        # building the main ui (box with header, hints, and scroll area)
        self._build_ui()
        # configures behavior, keeps it above other windows, hides it form taskbar, positions it in the top right
        self._setup_window()
        # listens for the toggle hotkey signal
        self._start_socket_listener()

    def _apply_style(self):
        # object implements GtkStyleProvider interface, parses CSS input to style widgets
        provider = Gtk.CssProvider()
        # loads CSS to provider
        provider.load_from_data(CSS)
        # object that stores styling information affecting widget.
        Gtk.StyleContext.add_provider_for_screen(
            # Gets current screen ( gets display)
            Gdk.Screen.get_default(),
            # Gtk.CssProvider with CSS loaded up
            provider,
            # Priority is app level which is high enough to override default GTK theme but below anything marked as user override.
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            # "Take this CSS, attach it to the default screen at application priority so it overrides the default theme."
        )

    def _setup_window(self):
        # set up basic rules for the Window
        self.set_title("Niri Cheatsheet")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_accept_focus(True)
        self.set_default_size(480, -1)

        # Get screen window is on
        screen = self.get_screen()
        # RGBA visual allows for transparency (A is alpha channel)
        visual = screen.get_rgba_visual()
        # checks if get_rgba_visual() returns None, (no compositor support). if so, it goes solid rather than transparent
        if visual:
            self.set_visual(visual)
        self.set_app_paintable(True)

        # GTK's way of wiring up event handlers
        # Widgets emit signals when things happen to them, connect subscribes a function to the signal.
        # Draw fires everytime GTK needs to repaint the window (starup, hidden, when another window moves over it)
        self.connect("draw", self._on_draw)
        # fires whenever key is pressed while window has focus.
        self.connect("key-press-event", self._on_key_press)
        # fires when something tries to close the window (close button ,Alt+F4)
        self.connect("delete-event", self._on_delete)

        # Position: top-right corner
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        #gets size/position of monitor
        geom = monitor.get_geometry()
        self.move(geom.x + geom.width - 500, geom.y + 40)

    def _on_draw(self, widget, cr):
        # cr = Cairo, 2D graphics library that GTK uses for rendering.
        # With set_app_paintable(True), GTK skips drawing the window's CSS
        # background, so we paint it ourselves here. This is required under
        # Niri, where a fully-transparent surface gets filled with the
        # compositor's focus color and washes the widget out when focused.
        #
        # First clear the surface so prior frames don't bleed through, then
        # paint our warm-charcoal background with controlled alpha.
        cr.set_operator(1)  # CLEAR
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()

        cr.set_operator(2)  # OVER
        # Catppuccin Mocha "Mantle" #181825 (matches CSS window {} rule).
        # Alpha here is the single source of truth for widget opacity.
        cr.set_source_rgba(24 / 255, 24 / 255, 37 / 255, 0.78)
        cr.paint()
        return False

    # Escape Key hides
    def _on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.hide()
            return True
        return False

    def _on_delete(self, *args):
        self.hide()
        return True  # Don't destroy, just hide

    def _on_header_press(self, widget, event):
        # Left-click on the header initiates a compositor-driven window move.
        # Under Wayland/Niri this issues an xdg-toplevel move request, which
        # Niri honors for floating windows. The drag continues until the
        # user releases the button, no separate motion/release handling needed.
        if event.button == 1:
            self.begin_move_drag(
                event.button,
                int(event.x_root),
                int(event.y_root),
                event.time,
            )
            return True
        return False

    # ui is oriented vertical
    def _build_ui(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(outer)

        # Header row — wrapped in an EventBox so left-click + drag on the
        # title bar moves the window. Gtk.Window doesn't receive button
        # events directly when children sit on top, so we need a real input
        # widget here. The close button still consumes its own clicks.
        header_event = Gtk.EventBox()
        header_event.connect("button-press-event", self._on_header_press)

        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header_box.set_hexpand(True)

        header = Gtk.Label(label="NIRI  KEYBINDINGS")
        header.set_name("header")
        header.set_halign(Gtk.Align.START)
        header.set_hexpand(True)
        header_box.pack_start(header, True, True, 0)

        # Button to close the widget
        close_btn = Gtk.Button(label="✕")
        close_btn.set_name("close-btn")
        close_btn.set_valign(Gtk.Align.CENTER)
        close_btn.connect("clicked", lambda _: self.hide())
        header_box.pack_end(close_btn, False, False, 8)

        header_event.add(header_box)

        # header_event contains the draggable header row + close button.
        # Keep the height natural (first False) since expand is False second fill feature is False
        # no extra padding on top of what CSS provides
        outer.pack_start(header_event, False, False, 0)

        # hint feature
        hint = Gtk.Label(label="Press Esc to dismiss")
        hint.set_name("hint")
        hint.set_halign(Gtk.Align.START)
        outer.pack_start(hint, False, False, 0)

        # Scrollable content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_name("scrolled")
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_max_content_height(700)
        scrolled.set_propagate_natural_height(True)

        # content box is set vertically
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content.set_margin_bottom(14)

        # iterates over each section in the dictionary (HOTKEYS Navigation, Windows, Workspaces, Apps & Systems, Layout)
        for section, keys in HOTKEYS.items():
            # For each one it creates a second label, styles it with section-label CSS class (makes it purple and uppercase)
            label = Gtk.Label(label=section.upper())
            label.set_name("section-label")
            label.set_halign(Gtk.Align.START)
            content.pack_start(label, False, False, 0)

            # Iteraties over key, description tuple inside the section
            for key, desc in keys:
                # For each keybind it builds horizontal row with key_lbl, key combo, styled with key CSS class
                # sep dot (.) separator in the middle
                # desc_lbl with desc style
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
                row.get_style_context().add_class("keybind-row")

                key_lbl = Gtk.Label(label=key)
                key_lbl.get_style_context().add_class("key")
                key_lbl.set_halign(Gtk.Align.START)
                key_lbl.set_xalign(0)

                desc_lbl = Gtk.Label(label=desc)
                desc_lbl.get_style_context().add_class("desc")
                desc_lbl.set_halign(Gtk.Align.START)
                desc_lbl.set_xalign(0)

                sep = Gtk.Label(label="·")
                sep.set_margin_start(8)
                sep.set_margin_end(8)
                sep.get_style_context().add_class("desc")

                row.pack_start(key_lbl, False, False, 0)
                row.pack_start(sep, False, False, 0)
                row.pack_start(desc_lbl, True, True, 0)
                content.pack_start(row, False, False, 0)

        # Flower art appended at the very bottom of the scrollable content.
        # Because it lives INSIDE the ScrolledWindow (and the keybindings
        # already fill the visible height), it stays hidden until the user
        # scrolls past the last section.
        flower = Gtk.Label()
        flower.set_name("bg-art")
        flower.set_use_markup(True)
        flower.set_markup(load_flower())
        flower.set_halign(Gtk.Align.CENTER)
        flower.set_margin_top(24)
        # Nudge ~2px to the left for visual centering. With halign=CENTER,
        # a margin on one side shrinks the centering region and pulls the
        # label toward the opposite side: 4px of right margin -> ~2px shift left.
        flower.set_margin_end(12)
        content.pack_start(flower, False, False, 0)

        # places content box inside the ScrolledWindow, ScrolledWindow is a container that clips what is inside it to its visible area and
        # adds scroll bar
        scrolled.add(content)
        # adds scrolled area into main vertical box, scrolled ares will expand to fill remaining vertical space after header and hint have
        # taken their natural height. (This is what False, False is for.)
        outer.pack_start(scrolled, True, True, 0)

    # public facing method that the socket listener calls. schedules _do_toggle() to run through GLib.idle_add()
    def toggle(self):
        GLib.idle_add(self._do_toggle)
    # toggle logic, checks get_visible and hides or shows window. show_all is used to recursively show window and all child widgets.
    # present brings it to the front and gives it keyboard focus
    # Returning False tells GLib to run it once and remove it from Queue, True would have it called repeatedly.
    def _do_toggle(self):
        if self.get_visible():
            self.hide()
        else:
            self.show_all()
            self.present()
        return False

    # sets up the socket widget listens on.
    def _start_socket_listener(self):
        # checks if socket path exists from a previous run (crashed run)
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(SOCKET_PATH)
        server.listen(1)

        def listen():
            # infinite loop that blocks on server.accept(), waits for a connection.
            # connection closes when anything connects and calls toggle.
            while True:
                try:
                    conn, _ = server.accept()
                    conn.close()
                    self.toggle()
                except Exception:
                    pass

        t = threading.Thread(target=listen, daemon=True)
        t.start()


def send_toggle():
    """Send toggle signal to running instance."""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(SOCKET_PATH)
        sock.close()
        return True
    except Exception:
        return False


if __name__ == "__main__":
    if "--toggle" in sys.argv:
        if not send_toggle():
            print("No running instance found. Start the widget first.")
        sys.exit(0)

    # Check for compositor support
    screen = Gdk.Screen.get_default()
    if not screen.is_composited():
        print("Warning: compositor not detected, transparency may not work.")

    app = NiriCheatsheet()
    app.show_all()
    Gtk.main()
