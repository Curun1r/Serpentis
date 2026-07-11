"""Tests for user preferences persistence (settings_manager.py)."""
import json

import pytest

import settings_manager
from settings_manager import DIFFICULTY_CONFIG, FRAMERATES, RESOLUTIONS, Settings


@pytest.fixture(autouse=True)
def settings_file(tmp_path, monkeypatch):
    """Redirect the settings file into a temp dir and reset the singleton."""
    path = tmp_path / 'settings.json'
    monkeypatch.setattr(settings_manager, 'SETTINGS_FILE', str(path))
    monkeypatch.setattr(Settings, '_instance', None)
    return path


def test_defaults_when_no_file():
    s = Settings()
    assert s.volume == 0.3
    assert s.difficulty == 'normal'
    assert s.fullscreen is False
    assert s.resolution == RESOLUTIONS[s.resolution_index]
    assert s.fps == FRAMERATES[s.fps_index]


def test_get_returns_singleton():
    assert Settings.get() is Settings.get()


def test_save_load_roundtrip():
    s = Settings()
    s.volume = 0.75
    s.difficulty = 'hard'
    s.fullscreen = True
    s.resolution_index = 1
    s.fps_index = 2
    s.save()

    loaded = Settings()
    assert loaded.volume == 0.75
    assert loaded.difficulty == 'hard'
    assert loaded.fullscreen is True
    assert loaded.resolution_index == 1
    assert loaded.fps_index == 2


def test_load_clamps_volume(settings_file):
    settings_file.write_text(json.dumps({'volume': 5.0}))
    assert Settings().volume == 1.0
    settings_file.write_text(json.dumps({'volume': -1.0}))
    assert Settings().volume == 0.0


def test_load_rejects_bad_indices(settings_file):
    settings_file.write_text(json.dumps({'resolution_index': 99, 'fps_index': -3}))
    s = Settings()
    assert 0 <= s.resolution_index < len(RESOLUTIONS)
    assert 0 <= s.fps_index < len(FRAMERATES)


def test_load_rejects_unknown_difficulty(settings_file):
    settings_file.write_text(json.dumps({'difficulty': 'nightmare'}))
    assert Settings().difficulty == 'normal'


def test_load_survives_corrupt_file(settings_file):
    settings_file.write_text('{oops')
    s = Settings()
    assert s.difficulty == 'normal'


def test_difficulty_properties_match_config():
    s = Settings()
    for name in DIFFICULTY_CONFIG:
        s.difficulty = name
        cfg = DIFFICULTY_CONFIG[name]
        assert s.alien_speed_mult == cfg['alien_speed_mult']
        assert s.alien_count == cfg['alien_count']
        assert s.starting_lives == cfg['starting_lives']
        assert s.boss_hp_mult == cfg['boss_hp_mult']
        assert s.shooter_interval_mult == cfg['shooter_interval_mult']


def test_difficulty_config_is_consistent():
    required = {'alien_speed_mult', 'alien_count', 'starting_lives',
                'boss_hp_mult', 'shooter_interval_mult'}
    for name, cfg in DIFFICULTY_CONFIG.items():
        assert set(cfg) == required, name
        assert cfg['alien_count'] > 0
        assert cfg['starting_lives'] > 0
