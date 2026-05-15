import pygame
import array
import math


class Assets:
    """Centralized asset loader and cache.

    Images and sounds are loaded/generated once on first request
    and reused on all subsequent calls — avoids redundant disk reads
    when multiple sprites share the same asset.
    """

    _images: dict = {}
    _sounds: dict = {}

    @classmethod
    def get_image(cls, path: str) -> pygame.Surface:
        """Return a surface for the given path, loading from disk only once."""
        if path not in cls._images:
            cls._images[path] = pygame.image.load(path).convert_alpha()
        return cls._images[path]

    @classmethod
    def get_sound(cls, key: str, frequency: float, duration: float, volume: float = 0.3) -> pygame.mixer.Sound:
        """Return a generated sine wave sound, creating it only once per key."""
        if key not in cls._sounds:
            cls._sounds[key] = cls._make_sine(frequency, duration, volume)
        return cls._sounds[key]

    @classmethod
    def _make_sine(cls, frequency: float, duration: float, volume: float) -> pygame.mixer.Sound:
        """Generate a sine wave sound buffer from scratch — no audio files needed."""
        sample_rate = 44100
        frames = int(duration * sample_rate)
        wave_data = array.array('h')
        for i in range(frames):
            value = int(volume * 32767 * math.sin(2 * math.pi * frequency * i / sample_rate))
            wave_data.append(value)
            wave_data.append(value)  # stereo — same value for both channels
        return pygame.mixer.Sound(buffer=wave_data)

    @classmethod
    def clear(cls):
        """Release all cached assets — useful for testing or freeing memory."""
        cls._images.clear()
        cls._sounds.clear()
