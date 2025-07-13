#!/bin/bash

# --- Configuration ---
# Path to the Wallpaper Engine workshop content folder
WALLPAPER_DIR="~/.steam/steam/steamapps/workshop/content/431960"
# Your monitor name (find with `hyprctl monitors`)
MONITOR="DP-1"
# Temporary directory for unpacking
TMP_DIR="/tmp/hyprpaper-we"

# Temporary file to store the PID
PID_FILE="/tmp/hyprpaper-we.pid"

# --- Functions ---

# Function to stop the current wallpaper
stop_wallpaper() {
    if [ -f "$PID_FILE" ]; then
        local pid_to_kill=$(cat "$PID_FILE")
        if ps -p $pid_to_kill > /dev/null; then
            echo "Stopping wallpaper process with PID: $pid_to_kill"
            kill $pid_to_kill
            rm "$PID_FILE"
        else
            echo "Process with PID $pid_to_kill not found. Removing stale PID file."
            rm "$PID_FILE"
        fi
    else
        echo "No active wallpaper to stop (PID file not found)."
    fi
}

# Function to set a new wallpaper
set_wallpaper() {
    # First, stop any previously running wallpaper
    stop_wallpaper

    local wallpaper_id=$1
    local wallpaper_path="$(eval echo $WALLPAPER_DIR)/$wallpaper_id"
    local pkg_file=""

    local project_json_path="$wallpaper_path/project.json"
    if [ ! -f "$project_json_path" ]; then
        echo "Error: project.json not found in $wallpaper_path"
        return 1
    fi

    # Get basic info from project.json
    local type=$(jq -r '.type' "$project_json_path")
    local file=$(jq -r '.file' "$project_json_path")
    echo "Detected wallpaper type: $type, main file: $file"

    # --- Logic to determine content source ---
    local content_root=""
    local properties_source_json=""

    # Check if the files are unpacked
    if [ -f "$wallpaper_path/$file" ]; then
        echo "Found unpacked wallpaper."
        content_root="$wallpaper_path"
        properties_source_json="$project_json_path" # Use the external project.json
    else
        # If not, look for a .pkg file to unpack
        echo "Wallpaper is packed. Searching for .pkg file..."
        local pkg_file=""
        if [ -f "$wallpaper_path/project.pkg" ]; then
            pkg_file="$wallpaper_path/project.pkg"
        elif [ -f "$wallpaper_path/preview.pkg" ]; then
            pkg_file="$wallpaper_path/preview.pkg"
        else
            echo "Error: .pkg file not found and main file '$file' is missing."
            return 1
        fi
        
        echo "Found PKG file: $pkg_file"
        content_root="$TMP_DIR/$wallpaper_id"
        properties_source_json="$content_root/project.json" # Use the internal project.json
        
        python "$(dirname "$0")/unpacker.py" "$pkg_file" "$content_root"
        if [ ! -f "$properties_source_json" ]; then
            echo "Error: Could not unpack or find the internal project.json"
            return 1
        fi
    fi
    # --- End of content source logic ---

    # --- Start the player based on type ---
    if [ "$type" == "video" ]; then
        local video_path="$content_root/$file"
        if [ -f "$video_path" ]; then
            echo "Launching mpvpaper for $video_path"
            mpvpaper -o "--loop-file=inf --no-audio" "$MONITOR" "$video_path" &
            LAST_PID=$!
            echo $LAST_PID > "$PID_FILE"
            echo "New PID: $LAST_PID"
        else
            echo "Error: Video file not found at $video_path"
        fi

    elif [ "$type" == "web" ]; then
        local html_path="$content_root/$file"
        if [ -f "$html_path" ]; then
            echo "Launching web_viewer for $html_path"
            # Launch the player in the background. Hyprland rules will handle the rest.
            LD_PRELOAD=/usr/lib/libgtk4-layer-shell.so python "$(dirname "$0")/web_viewer.py" "$html_path" &
            LAST_PID=$!
            echo $LAST_PID > "$PID_FILE"
            echo "New PID: $LAST_PID"
        else
            echo "Error: HTML file not found at $html_path"
        fi

    elif [ "$type" == "scene" ]; then
        echo "Error: 'scene' type wallpapers are not supported yet."
        return 1
    else
        echo "Unsupported wallpaper type: $type"
        return 1
    fi
}

# --- Main Logic ---

# Argument Handling
case "$1" in
    stop)
        stop_wallpaper
        exit 0
        ;;
    ""|--help|-h)
        echo "Usage: ./hyprpaper-we.sh <WALLPAPER_ID> | stop"
        echo "Example: ./hyprpaper-we.sh 123456789"
        echo "         ./hyprpaper-we.sh stop"
        exit 0
        ;;
    *)
        # Check if jq and python are installed
        if ! command -v jq &> /dev/null || ! command -v python &> /dev/null; then
            echo "Error: jq and/or python are not installed. Please install them."
            exit 1
        fi
        set_wallpaper "$1"
        ;;
esac
