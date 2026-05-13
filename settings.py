"""Application-wide constants for ImGui Forge Builder."""

from pathlib import Path


APP_NAME = "ImGui Forge Builder"
APP_VERSION = "0.1.0"

DEFAULT_WINDOW_WIDTH = 1280
DEFAULT_WINDOW_HEIGHT = 820

DEFAULT_MENU_WIDTH = 720
DEFAULT_MENU_HEIGHT = 500

MAX_UNDO_STATES = 60
DEFAULT_PROJECTS_DIR = Path("projects")
CUSTOM_PRESETS_PATH = DEFAULT_PROJECTS_DIR / "custom_presets.json"

SUPPORTED_NAV_POSITIONS = ["left", "right", "top", "bottom"]
SUPPORTED_NAV_STYLES = ["vertical sidebar", "top tabs", "pill tabs", "icon sidebar"]
SUPPORTED_LAYOUT_MODES = ["auto", "free"]

GRID_SIZES = [4, 8, 10, 12, 16, 20, 24, 32]

ANIMATION_TYPES = [
    "None",
    "Fade In",
    "Slide In Left",
    "Slide In Right",
    "Slide In Up",
    "Slide In Down",
    "Pulse Glow",
    "Hover Scale",
    "Hover Glow",
    "Border Glow",
    "Floating",
    "Shake Error",
    "Loading Dots",
    "Animated Gradient",
    "Particle Drift",
    "Scanline Sweep",
]

EASING_TYPES = ["linear", "ease in", "ease out", "ease in out"]

BACKGROUND_TYPES = [
    "Solid Color",
    "Linear Gradient Preview",
    "Animated Gradient",
    "Cyber Grid",
    "Floating Particles",
    "Glow Orbs",
    "Starfield",
    "Scanlines",
    "Glassmorphism Blur Preview",
    "Noise Texture Simulation",
]
