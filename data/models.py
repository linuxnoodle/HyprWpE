from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

@dataclass
class Wallpaper:
    id: str
    title: str
    type: str
    preview_path: str
    title_lower: str
    properties: dict = field(default_factory=dict)

@dataclass
class WallpaperProperties:
    audio: bool = False
    speed: float = 1.0
    scale: str = "Cover"

@dataclass
class PanelMargins:
    top: int = 0
    bottom: int = 0
    left: int = 0
    right: int = 0

class WallpaperType(Enum):
    VIDEO = "video"
    SCENE = "scene"
    WEB = "web"

class ScaleMode(Enum):
    COVER = "Cover"
    CONTAIN = "Contain"
    FILL = "Fill"
