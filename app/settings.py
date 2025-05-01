"""Application paths and common settings."""
import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

# Templates and static files
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Create directories if they don't exist
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# Visual assets directories
VISUALS_DIR = Path(os.environ.get("VISUALS_DIR", "data/visuals"))
CHARTS_DIR = VISUALS_DIR / "charts"
IMAGES_DIR = VISUALS_DIR / "images" 