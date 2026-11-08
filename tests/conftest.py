"""Run gameplay regressions without a window, audio hardware, or player saves."""
import os
from unittest.mock import Mock

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('SDL_RENDER_DRIVER', 'software')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame
import pytest


@pytest.fixture(scope='session')
def pygame_context():
    pygame.init()
    pygame.mixer.set_num_channels(16)
    pygame.mixer.set_reserved(2)
    yield pygame.display.set_mode((1280, 720))
    pygame.quit()


@pytest.fixture
def gameplay(pygame_context, tmp_path, monkeypatch):
    import game
    import score_manager
    import settings_manager

    monkeypatch.setattr(settings_manager, 'SETTINGS_FILE', str(tmp_path / 'settings.json'))
    monkeypatch.setattr(score_manager, 'SCORES_FILE', str(tmp_path / 'scores.json'))
    monkeypatch.setattr(settings_manager.Settings, '_instance', None)
    settings_manager.Settings.get().resolution_index = 1
    settings_manager.Settings.get().auto_resolution = False
    # Legacy geometry regressions exercise FIT; fill behavior has separate cases.
    settings_manager.Settings.get().fill_screen = False
    # Reuse a headless surface: SDL's dummy driver cannot recreate SCALED renderers.
    monkeypatch.setattr(pygame.display, 'set_mode', lambda *args, **kwargs: pygame_context)
    # Music synthesis is unrelated to gameplay; avoid starting background threads.
    monkeypatch.setattr(game, 'MusicPlayer', Mock)
    instance = game.Game()
    instance.state = game.GameState.PLAYING
    return instance
