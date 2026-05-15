import json
import os

_CONFIG_FILE = 'config.json'


def _load() -> dict:
    """Load config.json if it exists, otherwise return an empty dict.

    The empty dict triggers all .get() calls below to fall back to defaults,
    so the game works even if the config file is missing or partially edited.
    """
    if not os.path.exists(_CONFIG_FILE):
        return {}
    try:
        with open(_CONFIG_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


_cfg = _load()

# --- Screen ---
SCREEN_WIDTH: int   = _cfg.get('screen', {}).get('width',   1200)
SCREEN_HEIGHT: int  = _cfg.get('screen', {}).get('height',  750)
GAME_CAPTION: str   = _cfg.get('screen', {}).get('caption', 'Awesome Shooter Game')

# --- Speeds (pixels per second, used with delta time) ---
FIGHTER_SPEED: float = _cfg.get('speeds', {}).get('fighter', 230)
ALIEN_SPEED: float   = _cfg.get('speeds', {}).get('alien',   48)
BALL_SPEED: float    = _cfg.get('speeds', {}).get('ball',    264)

# --- Sprite scale multipliers ---
FIGHTER_SCALE: float = _cfg.get('scales', {}).get('fighter', 1.5)
ALIEN_SCALE: float   = _cfg.get('scales', {}).get('alien',   1.2)
BALL_SCALE: float    = _cfg.get('scales', {}).get('ball',    1.0)

# --- Gameplay ---
ALIEN_COUNT: int     = _cfg.get('gameplay', {}).get('alien_count',    3)
STARTING_LIVES: int  = _cfg.get('gameplay', {}).get('starting_lives', 3)
ALIEN_STAGGER: int   = _cfg.get('gameplay', {}).get('alien_stagger',  250)
