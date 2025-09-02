import subprocess
import json
import os
from typing import List
from config.constants import SCRIPT_PATH

class MonitorManager:
    def __init__(self):
        self.monitors: List[str] = []
        self.current_wallpapers: dict = {}
    
    def detect_monitors(self) -> List[str]:
        try:
            result = subprocess.run(["hyprctl", "monitors", "-j"], capture_output=True, text=True, check=True)
            monitor_data = json.loads(result.stdout)
            self.monitors = [m['name'] for m in monitor_data]
            return self.monitors
        except Exception as e:
            print(f"Could not detect monitors: {e}")
            return []

    def get_monitor_by_name(self, name: str) -> dict:
        """Get monitor details by name"""
        monitors = self.get_detailed_monitors()
        for monitor in monitors:
            if monitor['name'] == name:
                return monitor
        return None

    def get_detailed_monitors(self) -> List[dict]:
        """Get detailed monitor information including position and size"""
        try:
            result = subprocess.run(["hyprctl", "monitors", "-j"], capture_output=True, text=True, check=True)
            monitors = json.loads(result.stdout)
            
            # Add current wallpaper ID for each monitor
            for monitor in monitors:
                monitor['wallpaper_id'] = self.current_wallpapers.get(monitor['name'])
                
            return monitors
        except Exception as e:
            print(f"Error getting detailed monitor info: {e}")
            return []

    def apply_wallpaper(self, wallpaper_id: str, monitor: str, properties: dict, wallpaper_type: str) -> None:
        audio = properties.get('audio', False)
        speed = properties.get('speed', 1.0)
        scale = properties.get('scale', 'Cover').lower()
        mpv_opts = [f"--speed={speed}"]
        if not audio: mpv_opts.append("--no-audio")
        if scale == 'cover': mpv_opts.append("--panscan=1.0")
        elif scale == 'fill': mpv_opts.append("--video-aspect-method=stretch")
        env = os.environ.copy()
        env['MPV_EXTRA_OPTS'] = " ".join(mpv_opts)
        try:
            print(f"Applying '{wallpaper_type}' wallpaper ID: {wallpaper_id} to monitor: {monitor}")
            # For web wallpapers, pass monitor name as an additional argument
            if wallpaper_type == "web":
                subprocess.Popen([SCRIPT_PATH, str(wallpaper_id), monitor, monitor], env=env)
            else:
                subprocess.Popen([SCRIPT_PATH, str(wallpaper_id), monitor], env=env)
            self.current_wallpapers[monitor] = int(wallpaper_id)
        except Exception as e:
            print(f"Error launching wallpaper script: {e}")

    def stop_all_wallpapers(self) -> None:
        print("Stopping all wallpapers...")
        try:
            subprocess.run([SCRIPT_PATH, "stop"], check=True, timeout=5, capture_output=True, text=True)
            self.current_wallpapers.clear()
            print("All instances stopped and in-memory state cleared.")
        except Exception as e:
            if isinstance(e, subprocess.TimeoutExpired) or (hasattr(e, 'stderr') and e.stderr):
                 print(f"Error sending stop command: {e}")

    def get_monitor_list(self) -> List[str]:
        return self.monitors
