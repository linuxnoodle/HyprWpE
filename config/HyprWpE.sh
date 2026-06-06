#!/bin/bash

# --- Configuration ---
# Path to the Wallpaper Engine workshop content folder
WALLPAPER_DIR="~/.steam/steam/steamapps/workshop/content/431960"
# Default monitor (overridden if user passes second argument)
DEFAULT_MONITOR="DP-1"
# YAML config file for saved monitor setups
YAML_FILE="~/.config/HyprWpE/wallpapers.yaml"
# YAML config file for per-wallpaper properties
PROPERTIES_FILE="~/.config/HyprWpE/properties.yaml"
# Temporary directory for unpacking
TMP_DIR="/tmp/HyprWpE"

# Use argument for monitor if provided, else default
MONITOR="${2:-$DEFAULT_MONITOR}"

# Temporary file to store the PID, now monitor-specific
PID_FILE="/tmp/HyprWpE-${MONITOR}.pid"
# Lock file to prevent race conditions, now monitor-specific
LOCK_FILE="/tmp/HyprWpE-${MONITOR}.lock"


# --- Functions ---

write_pid() {
    ( flock -x 200; echo "$1" > "$PID_FILE"; ) 200>"$LOCK_FILE"
}

read_pid() {
    [ -f "$PID_FILE" ] && ( flock -s 200; cat "$PID_FILE" 2>/dev/null; ) 200>"$LOCK_FILE"
}

stop_wallpaper() {
    if [ -f "$PID_FILE" ]; then
        local pid_to_kill=$(read_pid)
        if [ -n "$pid_to_kill" ] && kill -0 "$pid_to_kill" 2>/dev/null; then
            kill -9 "$pid_to_kill"
        fi
        rm -f "$PID_FILE" "$LOCK_FILE"
    fi
    local lingering_pids=$(pgrep -f "(mpvpaper|web_viewer.py|linux-wallpaperengine).*$MONITOR")
    [ -n "$lingering_pids" ] && kill -9 $lingering_pids
}

stop_all_wallpapers() {
    echo "Stopping all wallpaper processes..."
    pkill -f "mpvpaper"
    pkill -f "web_viewer.py"
    pkill -f "linux-wallpaperengine"
    rm -f /tmp/HyprWpE-*
    echo "All active wallpapers have been stopped."
}

set_wallpaper() {
    stop_wallpaper
    local wallpaper_id=$1

    # --- The Fix: Read wallpaper_dir from the config file ---
    # This ensures the script uses the same directory as the GUI.
    local wallpaper_dir=$(yq -r '.wallpaper_dir' "$(eval echo $YAML_FILE)")
    if [ -z "$wallpaper_dir" ] || [ "$wallpaper_dir" = "null" ]; then
        echo "Error: 'wallpaper_dir' not found in $YAML_FILE. Please run the GUI once to configure it."
        return 1
    fi
    
    local wallpaper_path="$wallpaper_dir/$wallpaper_id"
    local project_json_path="$wallpaper_path/project.json"
    if [ ! -f "$project_json_path" ]; then echo "Error: project.json not found in $wallpaper_path"; return 1; fi

    local type=$(jq -r '.type | ascii_downcase' "$project_json_path")
    local file=$(jq -r '.file' "$project_json_path")
    local content_root="$wallpaper_path"

    # --- The Fix: Load properties for the wallpaper regardless of type ---
    # This logic now runs for every wallpaper, preparing the options if they are needed.
    local extra_opts=""
    if [ -n "$MPV_EXTRA_OPTS" ]; then
        echo "[$MONITOR] Using live options from GUI."
        extra_opts="$MPV_EXTRA_OPTS"
    else
        local props_file="$(eval echo $PROPERTIES_FILE)"
        if [ -f "$props_file" ]; then
            local raw_audio=$(yq -r ".[\"$wallpaper_id\"].audio" "$props_file")
            local raw_speed=$(yq -r ".[\"$wallpaper_id\"].speed" "$props_file")
            local raw_scale=$(yq -r ".[\"$wallpaper_id\"].scale" "$props_file")

            local audio=${raw_audio:-false}; [ "$audio" = "null" ] && audio="false"
            local speed=${raw_speed:-1.0}; [ "$speed" = "null" ] && speed="1.0"
            local scale=${raw_scale:-Cover}; [ "$scale" = "null" ] && scale="Cover"

            local opts_array=("--speed=$speed")
            if [ "$audio" != "true" ]; then opts_array+=("--no-audio"); fi
            
            scale=$(echo "$scale" | tr '[:upper:]' '[:lower:]')
            
            # For mpvpaper
            if [ "$scale" = "cover" ]; then opts_array+=("--panscan=1.0"); fi
            if [ "$scale" = "fill" ]; then opts_array+=("--video-aspect-method=stretch"); fi
            
            extra_opts=$(IFS=' '; echo "${opts_array[*]}")
            
            # For linux-wallpaperengine
            local we_scale="fill"
            if [ "$scale" = "cover" ]; then we_scale="fill"; fi
            if [ "$scale" = "contain" ]; then we_scale="fit"; fi
            if [ "$scale" = "fill" ]; then we_scale="stretch"; fi
        else
            # Fallback if properties file doesn't exist
            extra_opts="--no-audio --speed=1.0"
        fi
    fi

    # Unpacking logic (for video/web)
    if [ "$type" != "scene" ] && [ ! -f "$wallpaper_path/$file" ]; then
        local pkg_file=$(find "$wallpaper_path" -name "*.pkg" -print -quit)
        if [ -n "$pkg_file" ]; then
            content_root="$TMP_DIR/$wallpaper_id"
            python "$(dirname "$0")/unpacker.py" "$pkg_file" "$content_root"
            # Copy project.json if it was not in the archive
            if [ ! -f "$content_root/project.json" ] && [ -f "$wallpaper_path/project.json" ]; then
                cp "$wallpaper_path/project.json" "$content_root/"
            fi
            if [ ! -f "$content_root/project.json" ] && [ ! -f "$content_root/$file" ]; then
                echo "Error: Unpack failed"; return 1;
            fi
        fi
    fi

    if [ "$type" == "video" ]; then
        local video_path="$content_root/$file"
        local base_opts="--loop-file=inf"
        echo "[$MONITOR] Launching mpvpaper with options: $base_opts $extra_opts"
        mpvpaper -o "$base_opts $extra_opts" "$MONITOR" "$video_path" &
        write_pid $!

    elif [ "$type" == "web" ]; then
        local html_path="$content_root/$file"
        echo "[$MONITOR] Launching web_viewer as a layer-shell surface."
        LD_PRELOAD=/usr/lib/libgtk4-layer-shell.so python "$(dirname "$0")/web_viewer.py" "$html_path" "$MONITOR" &
        write_pid $!

    elif [ "$type" == "scene" ]; then
        echo "[$MONITOR] Launching linux-wallpaperengine for $content_root"
        
        export HYPRWPE_OFFSET_X=$(hyprctl monitors -j | jq -r ".[] | select(.name==\"$MONITOR\") | .x")
        export HYPRWPE_OFFSET_Y=$(hyprctl monitors -j | jq -r ".[] | select(.name==\"$MONITOR\") | .y")
        
        local silent_arg="--silent"
        if [ "$audio" == "true" ]; then silent_arg=""; fi
        
        local scene_opts_array=()
        local props_file="$(eval echo $PROPERTIES_FILE)"
        if [ -f "$props_file" ]; then
            echo "[$MONITOR] Parsing scene properties from $props_file for $wallpaper_id"
            local scene_keys=$(yq -r ".[\"$wallpaper_id\"].scene_props | keys | .[]" "$props_file" 2>/dev/null)
            echo "[$MONITOR] Extracted scene keys: $scene_keys"
            if [ -n "$scene_keys" ] && [ "$scene_keys" != "null" ]; then
                for k in $scene_keys; do
                    local v=$(yq -r ".[\"$wallpaper_id\"].scene_props.[\"$k\"]" "$props_file" 2>/dev/null)
                    # Convert json true/false to 1/0 that linux-wallpaperengine JS expects
                    if [ "$v" = "true" ]; then v="1"; fi
                    if [ "$v" = "false" ]; then v="0"; fi
                    scene_opts_array+=("--set-property" "$k=$v")
                done
            fi
        fi
        
        local span_arg="--screen-root \"$MONITOR\""
        if [[ "$MONITOR" == *","* ]]; then
            span_arg="--screen-span \"$MONITOR\""
        fi
        
        # If we_scale isn't set (e.g. fallback), default to fill
        we_scale=${we_scale:-fill}
        
        local engine_bin="$(dirname "$(dirname "$0")")/linux-wallpaperengine/build/output/linux-wallpaperengine"
        echo "Running with: $engine_bin $span_arg --scaling $we_scale --bg $content_root --fps 60 --no-fullscreen-pause $silent_arg ${scene_opts_array[*]}"
        eval "$engine_bin $span_arg --scaling $we_scale --bg \"$content_root\" --fps 60 --no-fullscreen-pause $silent_arg \"\${scene_opts_array[@]}\" >> \"$HOME/.config/HyprWpE/we_${MONITOR}.log\" 2>&1 &"
        write_pid $!
    else
        echo "[$MONITOR] Unsupported wallpaper type: $type"
    fi
}

load_config() {
    local config_file="${1:-$(eval echo $YAML_FILE)}"
    if [ ! -f "$config_file" ]; then echo "Error: Config file not found"; exit 1; fi
    stop_all_wallpapers; sleep 0.5

    local monitors=$(yq -r '.wallpapers | keys | .[]' "$config_file")
    for monitor in $monitors; do
        local wallpaper_id=$(yq -r ".wallpapers[\"$monitor\"]" "$config_file")
        if [[ "$wallpaper_id" =~ ^[0-9]+$ ]]; then
            "$0" "$wallpaper_id" "$monitor" &
        fi
    done
}

# --- Main Logic ---
# Trap Ctrl+C (INT) and termination (TERM) signals to run cleanup.
trap 'echo -e "\nSignal received. Stopping all wallpapers..."; stop_all_wallpapers; exit 130' INT TERM

# Check for dependencies needed for any YAML parsing
check_yq() {
    if ! command -v yq &> /dev/null; then
        echo "Error: 'yq' (python-yq) is not installed. Please install it to use YAML features."
        exit 1
    fi
}

case "$1" in
    --load-config)
        check_yq; load_config "$2"; exit 0 ;;
    stop)
        stop_all_wallpapers; exit 0 ;;
    ""|--help|-h)
        echo "Usage: $0 <ID> [MONITOR] | stop | --load-config [FILE]"
        echo "No args given, loading default config from $YAML_FILE..."
        check_yq; load_config; exit 0 ;;
    *)
        if ! [[ "$1" =~ ^[0-9]+$ ]]; then echo "Error: Invalid wallpaper ID '$1'"; exit 1; fi
        if ! command -v jq &> /dev/null; then echo "Error: 'jq' not installed."; exit 1; fi
        check_yq
        set_wallpaper "$1" ;;
esac
