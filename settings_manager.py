import json
import os

SETTINGS_FILE = 'data/settings.json'

RESOLUTIONS  = [(1024, 768), (1280, 720), (1920, 1080), (2560, 1440)]
FRAMERATES   = [30, 60, 120, 144]

DIFFICULTY_CONFIG = {
    #                speed   count  starting_lives  boss_hp_mult  shooter_interval_mult
    'easy':   {'alien_speed_mult': 0.40, 'alien_count': 2,
               'starting_lives': 5, 'boss_hp_mult': 0.65, 'shooter_interval_mult': 1.8},
    'normal': {'alien_speed_mult': 1.0,  'alien_count': 3,
               'starting_lives': 3, 'boss_hp_mult': 1.0,  'shooter_interval_mult': 1.0},
    'hard':   {'alien_speed_mult': 2.1,  'alien_count': 7,
               'starting_lives': 2, 'boss_hp_mult': 1.5,  'shooter_interval_mult': 0.6},
}


class Settings:
    """Singleton that holds and persists user preferences (volume, resolution, difficulty)."""

    _instance: 'Settings | None' = None

    def __init__(self):
        self.volume: float = 0.3
        self.resolution_index: int = 2   # index into RESOLUTIONS  (default: 1920×1080)
        self.fps_index: int = 1          # index into FRAMERATES   (default: 60 fps)
        self.difficulty: str = 'normal'
        self.fullscreen: bool = False
        self.load()

    @classmethod
    def get(cls) -> 'Settings':
        if cls._instance is None:
            cls._instance = Settings()
        return cls._instance

    def load(self) -> None:
        """Read saved settings from disk; silently keeps defaults if file is missing/corrupt."""
        if not os.path.exists(SETTINGS_FILE):
            return
        try:
            with open(SETTINGS_FILE) as f:
                data = json.load(f)
            self.volume = max(0.0, min(1.0, float(data.get('volume', 0.3))))
            ri = int(data.get('resolution_index', 0))
            self.resolution_index = ri if 0 <= ri < len(RESOLUTIONS) else 0
            d = data.get('difficulty', 'normal')
            self.difficulty = d if d in DIFFICULTY_CONFIG else 'normal'
            self.fullscreen = bool(data.get('fullscreen', False))
            fi = int(data.get('fps_index', 1))
            self.fps_index = fi if 0 <= fi < len(FRAMERATES) else 1
        except (json.JSONDecodeError, IOError, ValueError):
            pass

    def save(self) -> None:
        """Write current settings to disk, creating the data/ folder if needed."""
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, 'w') as f:
            json.dump({
                'volume': round(self.volume, 3),
                'resolution_index': self.resolution_index,
                'fps_index': self.fps_index,
                'difficulty': self.difficulty,
                'fullscreen': self.fullscreen,
            }, f, indent=2)

    @property
    def resolution(self) -> tuple[int, int]:
        return RESOLUTIONS[self.resolution_index]

    @property
    def fps(self) -> int:
        return FRAMERATES[self.fps_index]

    @property
    def alien_speed_mult(self) -> float:
        return DIFFICULTY_CONFIG[self.difficulty]['alien_speed_mult']

    @property
    def alien_count(self) -> int:
        return DIFFICULTY_CONFIG[self.difficulty]['alien_count']

    @property
    def starting_lives(self) -> int:
        return DIFFICULTY_CONFIG[self.difficulty]['starting_lives']

    @property
    def boss_hp_mult(self) -> float:
        return DIFFICULTY_CONFIG[self.difficulty]['boss_hp_mult']

    @property
    def shooter_interval_mult(self) -> float:
        return DIFFICULTY_CONFIG[self.difficulty]['shooter_interval_mult']
