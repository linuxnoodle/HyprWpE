#!/bin/bash

# This script is executed on system startup to restore the last wallpaper.

# --- Configuration ---
# Directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
# Path to the main wallpaper script
HYPRPAPER_SCRIPT="$SCRIPT_DIR/hyprpaper-we.sh"
# Path to the configuration file
CONFIG_FILE="$HOME/.config/hyprpaper-we/state.json"

# --- Logic ---
# Check if the configuration file exists
if [ -f "$CONFIG_FILE" ]; then
    # Read the last used wallpaper ID from the config file
    WALLPAPER_ID=$(jq -r '.last_wallpaper_id' "$CONFIG_FILE")

    # If a wallpaper ID was found, launch the wallpaper
    if [ -n "$WALLPAPER_ID" ] && [ "$WALLPAPER_ID" != "null" ]; then
        echo "Autostarting wallpaper ID: $WALLPAPER_ID"
        "$HYPRPAPER_SCRIPT" "$WALLPAPER_ID"
    else
        echo "No last wallpaper ID found in config file."
    fi
else
    echo "Config file not found: $CONFIG_FILE"
fi
