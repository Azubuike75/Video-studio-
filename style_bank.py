"""
Style bank: everything that gets randomly combined per video —
background palettes, fonts, text colors, animation presets, music moods.
All local, all offline.
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS_DIR = os.path.join(BASE_DIR, "assets", "fonts")
MUSIC_DIR = os.path.join(BASE_DIR, "assets", "music")

FONTS = [
    {"name": "Poppins Bold", "file": "Poppins-Bold.ttf"},
    {"name": "Poppins Medium", "file": "Poppins-Medium.ttf"},
    {"name": "DejaVu Serif Bold", "file": "DejaVuSerif-Bold.ttf"},
    {"name": "DejaVu Sans Bold", "file": "DejaVuSans-Bold.ttf"},
    {"name": "Liberation Sans Bold", "file": "LiberationSans-Bold.ttf"},
    {"name": "Free Sans Bold", "file": "FreeSansBold.ttf"},
    {"name": "Lora", "file": "Lora-Variable.ttf"},
    {"name": "Lora Italic", "file": "Lora-Italic-Variable.ttf"},
]

def font_path(fname):
    return os.path.join(FONTS_DIR, fname)

# Each palette: gradient from color A -> color B, plus a matching text color
# and accent color. Picked to be legible and social-media friendly.
PALETTES = [
    {"name": "Midnight Violet", "bg1": (25, 20, 55), "bg2": (70, 40, 110), "text": (255, 255, 255), "accent": (255, 209, 102)},
    {"name": "Sunset Coral", "bg1": (255, 94, 98), "bg2": (255, 154, 90), "text": (255, 255, 255), "accent": (32, 32, 32)},
    {"name": "Ocean Teal", "bg1": (0, 78, 100), "bg2": (0, 150, 160), "text": (255, 255, 255), "accent": (255, 220, 130)},
    {"name": "Forest Calm", "bg1": (18, 60, 40), "bg2": (60, 120, 70), "text": (245, 245, 235), "accent": (255, 200, 87)},
    {"name": "Charcoal Minimal", "bg1": (28, 28, 30), "bg2": (55, 55, 60), "text": (255, 255, 255), "accent": (0, 200, 180)},
    {"name": "Rose Gold", "bg1": (75, 30, 45), "bg2": (190, 100, 100), "text": (255, 250, 245), "accent": (255, 224, 178)},
    {"name": "Electric Blue", "bg1": (10, 20, 70), "bg2": (30, 100, 220), "text": (255, 255, 255), "accent": (0, 255, 200)},
    {"name": "Warm Cream", "bg1": (235, 220, 195), "bg2": (250, 240, 220), "text": (40, 30, 20), "accent": (200, 90, 60)},
    {"name": "Cyberpunk", "bg1": (15, 5, 35), "bg2": (255, 0, 130), "text": (255, 255, 255), "accent": (0, 255, 255)},
    {"name": "Peach Soft", "bg1": (255, 200, 170), "bg2": (255, 230, 200), "text": (60, 30, 20), "accent": (220, 90, 60)},
]

# Animation presets translate to ffmpeg filter parameters (see video_gen.py)
ANIMATIONS = [
    "zoom_in",       # slow Ken Burns zoom in on background
    "zoom_out",      # slow Ken Burns zoom out
    "pan_left",      # background pans left to right
    "pan_right",     # background pans right to left
    "fade_pulse",    # background gently pulses opacity/brightness
    "static_fade",   # no movement, just fade in/out of text
]

TEXT_ANIMATIONS = [
    "fade_in",       # text fades in and stays
    "slide_up",      # text slides up into place
    "typewriter",    # text appears progressively (word by word)
    "pop_in",        # text scales in with a little bounce feel
]

MUSIC_MOODS = ["uplifting", "chill", "dramatic", "playful", "ambient"]

CATEGORY_MOOD_BIAS = {
    "quotes": ["uplifting", "ambient", "dramatic"],
    "facts": ["chill", "playful", "ambient"],
    "tips": ["uplifting", "chill"],
    "stories": ["dramatic", "ambient"],
    "jokes": ["playful"],
    "riddles": ["dramatic", "ambient"],
}

ASPECT_RATIOS = {
    "vertical": (1080, 1920),   # 9:16
    "square": (1080, 1080),     # 1:1
    "horizontal": (1920, 1080), # 16:9
}


def music_file_for_mood(mood):
    return os.path.join(MUSIC_DIR, f"{mood}.mp3")
