import os
import yaml
from config.constants import CONFIG_DIR, YAML_FILE, PROPERTIES_FILE, DEFAULT_WALLPAPER_DIR

class ConfigManager:
    def __init__(self):
        self.config = {}
        self.properties = {}
    
    def ensure_config_dir(self) -> None:
        os.makedirs(CONFIG_DIR, exist_ok=True)

    def load_config(self) -> dict:
        config = {}
        needs_save = False
        if os.path.exists(YAML_FILE):
            try:
                with open(YAML_FILE, 'r') as f:
                    config = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Error loading YAML wallpapers, creating new one: {e}")
                config = {}
        
        if 'wallpaper_dir' not in config or not config['wallpaper_dir']:
            config['wallpaper_dir'] = DEFAULT_WALLPAPER_DIR
            needs_save = True
        if 'wallpapers' not in config:
            config['wallpapers'] = {}
            needs_save = True
        if needs_save:
            self.save_config(config)
        self.config = config
        return self.config

    def save_config(self, config_data: dict) -> None:
        try:
            with open(YAML_FILE, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
            print(f"Initialized or updated config file at {YAML_FILE}")
        except Exception as e:
            print(f"Error saving initial config: {e}")

    def load_properties(self) -> dict:
        props = {}
        needs_save = False
        if os.path.exists(PROPERTIES_FILE):
            try:
                with open(PROPERTIES_FILE, 'r') as f:
                    props = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Error loading properties YAML, creating new one: {e}")
                props = {}
        if 'panel_margins' not in props:
            props['panel_margins'] = {'top': 0, 'bottom': 0, 'left': 0, 'right': 0}
            needs_save = True
        if needs_save:
            self.save_properties(props)
        self.properties = props
        return self.properties

    def save_properties(self, properties: dict) -> None:
        try:
            with open(PROPERTIES_FILE, 'w') as f:
                yaml.dump(properties, f, default_flow_style=False)
            print(f"Initialized panel_margins in {PROPERTIES_FILE}")
        except Exception as e:
            print(f"Error saving properties: {e}")

    def validate_config(self, config_data: dict) -> bool:
        # Basic validation, can be expanded
        if 'wallpaper_dir' not in config_data or 'wallpapers' not in config_data:
            return False
        return True
