#!/usr/bin/env bash
# niri-cheatsheet-toggle.sh
# Use this script as your Niri keybind action.
# It starts the daemon if not running, then toggles visibility.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WIDGET="$SCRIPT_DIR/niri-cheatsheet.py"
SOCKET="/tmp/niri-cheatsheet.sock"
PID_FILE="/tmp/niri-cheatsheet.pid"

is_running() {
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        kill -0 "$pid" 2>/dev/null && return 0
    fi
    return 1
}

if is_running; then
    python3 "$WIDGET" --toggle
else
    python3 "$WIDGET" &
    echo $! > "$PID_FILE"
fi
