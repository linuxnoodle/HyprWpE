import os
import json
from typing import List, Optional
from data.models import Wallpaper

class WallpaperDataManager:
    def __init__(self, wallpaper_dir: str):
        self.wallpaper_dir = wallpaper_dir
        self.all_wallpapers: List[Wallpaper] = []
        self.filtered_wallpapers: List[Wallpaper] = []
        self.search_term = ""
        self.type_filters = {"video": True, "scene": True, "web": True}
    
    def load_wallpaper_data(self) -> List[Wallpaper]:
        """Load wallpaper metadata from the wallpaper directory"""
        print(f"Loading wallpaper data from: {self.wallpaper_dir}")
        
        self.all_wallpapers.clear()
        
        if not self.wallpaper_dir or not os.path.isdir(self.wallpaper_dir):
            print("Wallpaper directory not found or invalid")
            return []
            
        wallpaper_count = 0
        for wallpaper_id in os.listdir(self.wallpaper_dir):
            wallpaper_path = os.path.join(self.wallpaper_dir, wallpaper_id)
            project_json_path = os.path.join(wallpaper_path, "project.json")
            
            if os.path.isdir(wallpaper_path) and os.path.exists(project_json_path):
                try:
                    with open(project_json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    title = data.get('title', 'No Title')
                    wp_type = data.get('type', 'unknown').lower()
                    preview_file = data.get('preview', 'preview.gif')
                    
                    wallpaper_data = Wallpaper(
                        id=wallpaper_id,
                        title=title,
                        type=wp_type,
                        preview_path=os.path.join(wallpaper_path, preview_file),
                        title_lower=title.lower(),
                    )
                    
                    self.all_wallpapers.append(wallpaper_data)
                    wallpaper_count += 1
                    
                except Exception as e:
                    print(f"Could not parse project.json for {wallpaper_id}: {e}")
                    
        print(f"Successfully loaded {wallpaper_count} wallpapers")
        
        # Show some examples
        for i, wp in enumerate(self.all_wallpapers[:3]):
            print(f"  [{i+1}] ID: {wp.id}, Type: {wp.type}, Title: '{wp.title}'")
        
        return self.all_wallpapers

    def apply_filters(self, search_term: str, type_filters: dict) -> List[Wallpaper]:
        self.search_term = search_term
        self.type_filters = type_filters
        
        search_term_lower = self.search_term.lower()
        
        self.filtered_wallpapers = [
            wp for wp in self.all_wallpapers
            if (search_term_lower in wp.title_lower if search_term_lower else True) and \
               (self.type_filters.get(wp.type, False))
        ]
        
        return self.filtered_wallpapers

    def get_wallpaper_by_id(self, wallpaper_id: str) -> Optional[Wallpaper]:
        for wp in self.all_wallpapers:
            if wp.id == wallpaper_id:
                return wp
        return None

    def validate_wallpaper_directory(self) -> bool:
        return os.path.isdir(self.wallpaper_dir)
        
    def refresh_wallpapers(self) -> List[Wallpaper]:
        """Reload wallpaper data from disk"""
        print("Refreshing wallpaper data...")
        return self.load_wallpaper_data()
