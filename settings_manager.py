import json
import os

SETTINGS_FILE = 'data/settings.json'

RESOLUTIONS = [(1024, 768), (1280, 720), (1920, 1080)]

DIFFICULTY_CONFIG = {
    'easy':   {'alien_speed_mult': 0.65, 'alien_count': 2},
    'normal': {'alien_speed_mult': 1.0,  'alien_count': 3},
    'hard':   {'alien_speed_mult': 1.6,  'alien_count': 5},
}


class Settings:
    """Singleton that holds and persists user preferences (volume, resolution, difficulty)."""

    _instance: 'Settings | None' = None

    def __init__(self):
        self.volume: float = 0.3
        self.resolution_index: int = 0   # index into RESOLUTIONS
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
        except (json.JSONDecodeError, IOError, ValueError):
            pass

    def save(self) -> None:
        """Write current settings to disk, creating the data/ folder if needed."""
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, 'w') as f:
            json.dump({
                'volume': round(self.volume, 3),
                'resolution_index': self.resolution_index,
                'difficulty': self.difficulty,
                'fullscreen': self.fullscreen,
            }, f, indent=2)

    @property
    def resolution(self) -> tuple[int, int]:
        return RESOLUTIONS[self.resolution_index]

    @property
    def alien_speed_mult(self) -> float:
        return DIFFICULTY_CONFIG[self.difficulty]['alien_speed_mult']

    @property
    def alien_count(self) -> int:
        return DIFFICULTY_CONFIG[self.difficulty]['alien_count']
