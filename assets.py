import pygame
import array
import math


class Assets:
    """Centralized asset loader and cache."""

    _images: dict = {}
    _sounds: dict = {}

    @classmethod
    def get_image(cls, path: str) -> pygame.Surface:
        if path not in cls._images:
            cls._images[path] = pygame.image.load(path).convert_alpha()
        return cls._images[path]

    @classmethod
    def get_sound(cls, key: str, frequency: float, duration: float,
                  volume: float = 0.3) -> pygame.mixer.Sound:
        """Sine wave tone (cached by key)."""
        if key not in cls._sounds:
            cls._sounds[key] = cls._make_sine(frequency, duration, volume)
        return cls._sounds[key]

    @classmethod
    def make_chirp(cls, key: str, f_start: float, f_end: float,
                   duration: float, volume: float = 0.4) -> pygame.mixer.Sound:
        """Frequency-sweep sound (laser / whoosh). Cached by key."""
        if key not in cls._sounds:
            cls._sounds[key] = cls._build_chirp(f_start, f_end, duration, volume)
        return cls._sounds[key]

    # ------------------------------------------------------------------

    @classmethod
    def _make_sine(cls, frequency: float, duration: float,
                   volume: float) -> pygame.mixer.Sound:
        sr     = 44100
        frames = int(duration * sr)
        buf    = array.array('h')
        for i in range(frames):
            v = int(volume * 32767 * math.sin(2 * math.pi * frequency * i / sr))
            buf.append(v); buf.append(v)
        return pygame.mixer.Sound(buffer=buf)

    @classmethod
    def _build_chirp(cls, f_start: float, f_end: float,
                     duration: float, volume: float) -> pygame.mixer.Sound:
        """Linear frequency sweep with smooth amplitude envelope."""
        sr     = 44100
        frames = int(duration * sr)
        buf    = array.array('h')
        phase  = 0.0
        for i in range(frames):
            t    = i / frames                          # 0 → 1
            freq = f_start + (f_end - f_start) * t
            # Envelope: quick attack, smooth decay
            amp  = min(t * 15.0, 1.0) * math.exp(-3.5 * t)
            phase += 2.0 * math.pi * freq / sr
            v    = int(volume * amp * 32767 * math.sin(phase))
            buf.append(v); buf.append(v)
        return pygame.mixer.Sound(buffer=buf)

    @classmethod
    def clear(cls):
        cls._images.clear()
        cls._sounds.clear()
