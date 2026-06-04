# Niri Hotkey Cheatsheet Widget

A transparent, always-on-top floating widget that shows your Niri keybindings.
Toggle it open/closed with a hotkey. Press Esc or click ✕ to dismiss.

## Requirements

```bash
# Debian/Ubuntu
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0

# Arch
sudo pacman -S python-gobject gtk3

# Fedora
sudo dnf install python3-gobject gtk3
```

A compositor with RGBA support is required for transparency.
Niri handles this natively — no extra setup needed.

## Installation

1. Copy files to your Niri config directory:

```bash
mkdir -p ~/.config/niri
cp niri-cheatsheet.py ~/.config/niri/
cp niri-cheatsheet-toggle.sh ~/.config/niri/
chmod +x ~/.config/niri/niri-cheatsheet.py
chmod +x ~/.config/niri/niri-cheatsheet-toggle.sh
```

2. Add a keybind in `~/.config/niri/config.kdl`:

```kdl
binds {
    // ... your existing binds ...

    // Toggle cheatsheet with Super + /
    Mod+Slash { spawn "bash" "-c" "~/.config/niri/niri-cheatsheet-toggle.sh"; }
}
```

You can use any key combo you like. `Super+Slash` or `Super+F1` are common choices.

3. (Optional) Auto-start via systemd user service:

```bash
# Edit the service file to point to the right path, then:
cp niri-cheatsheet.service ~/.config/systemd/user/
systemctl --user enable --now niri-cheatsheet.service
```

If using the service, update your keybind to just send the toggle signal:
```kdl
Mod+Slash { spawn "python3" "-c"
    "import socket; s=socket.socket(socket.AF_UNIX); s.connect('/tmp/niri-cheatsheet.sock'); s.close()"; }
```

## Usage

| Action            | How                          |
|-------------------|------------------------------|
| Open/close widget | Your keybind (e.g. Super+/)  |
| Close             | Esc key or ✕ button          |
| Scroll            | Mouse wheel (if content tall)|

## Customization

Edit `niri-cheatsheet.py` to:

- **Add/change keybinds**: Edit the `HOTKEYS` dict at the top of the file.
  Each section is a key with a list of `(key, description)` tuples.

- **Change position**: Find `self.move(...)` and adjust the coordinates.
  `(geom.x + geom.width - 500, geom.y + 40)` = top-right by default.

- **Change opacity**: In the CSS, change `rgba(10, 10, 14, 0.88)` —
  the last value is opacity (0.0 = fully transparent, 1.0 = solid).

- **Change colors**: Edit the CSS block at the top of the script.
  `#a78bfa` = purple accent, `#e2dfe8` = text color.

- **Change size**: Edit `self.set_default_size(480, -1)` for width,
  and `scrolled.set_max_content_height(700)` for max height.

## Troubleshooting

**Widget is not transparent:**
- Make sure a Wayland compositor is running (Niri itself provides this)
- If using X11 fallback, install `picom` or another compositor

**Script doesn't start:**
- Check Python GTK bindings: `python3 -c "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk; print('OK')`

**Font looks wrong:**
- Install JetBrains Mono or Fira Code, or change the font in the CSS `font-family` line
