"""Tests for user preferences persistence (settings_manager.py)."""
import json

import pytest

import settings_manager
from settings_manager import ASPECT_RATIOS, DIFFICULTY_CONFIG, FRAMERATES, RESOLUTIONS, Settings


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
    assert s.resolution == (s.native_resolution if s.auto_resolution else RESOLUTIONS[s.resolution_index])
    assert s.fps == FRAMERATES[s.fps_index]


def test_get_returns_singleton():
    assert Settings.get() is Settings.get()


def test_save_load_roundtrip():
    s = Settings()
    s.volume = 0.75
    s.difficulty = 'hard'
    s.fullscreen = True
    s.resolution_index = 1
    s.auto_resolution = False
    s.fps_index = 2
    s.save()

    loaded = Settings()
    assert loaded.volume == 0.75
    assert loaded.difficulty == 'hard'
    assert loaded.fullscreen is True
    assert loaded.resolution_index == 1
    assert loaded.auto_resolution is False
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


@pytest.mark.parametrize(('platform', 'automatic'), [('darwin', True), ('linux', False), ('win32', False)])
def test_auto_resolution_platform_default(monkeypatch, platform, automatic):
    monkeypatch.setattr(settings_manager.sys, 'platform', platform)
    assert Settings().auto_resolution is automatic


def test_legacy_mac_settings_default_to_current_display(settings_file, monkeypatch):
    monkeypatch.setattr(settings_manager.sys, 'platform', 'darwin')
    monkeypatch.setattr(settings_manager, 'get_native_resolution', lambda: (3024, 1964))
    settings_file.write_text(json.dumps({'resolution_index': 2, 'fullscreen': False}))
    settings = Settings()
    assert settings.auto_resolution is True
    assert settings.resolution == (3024, 1964)
    assert settings.fullscreen is False


def test_manual_mac_resolution_override_is_persisted(monkeypatch):
    monkeypatch.setattr(settings_manager.sys, 'platform', 'darwin')
    settings = Settings()
    settings.auto_resolution = False
    settings.resolution_index = 1
    settings.save()
    assert Settings().resolution == (1280, 720)


def test_auto_resolution_follows_monitor_changes(monkeypatch):
    settings = Settings()
    settings.auto_resolution = True
    monkeypatch.setattr(settings_manager, 'get_native_resolution', lambda: (2560, 1440))
    assert settings.resolution == (2560, 1440)
    monkeypatch.setattr(settings_manager, 'get_native_resolution', lambda: (3440, 1440))
    assert settings.resolution == (3440, 1440)
    settings.save()
    assert Settings().auto_resolution is True


@pytest.mark.parametrize('aspect', ASPECT_RATIOS)
def test_aspect_ratio_roundtrip(aspect):
    settings = Settings()
    settings.aspect_ratio = aspect
    settings.save()
    assert Settings().aspect_ratio == aspect


@pytest.mark.parametrize('aspect', ['invalid', None, ['16:9']])
def test_unknown_aspect_uses_legacy_16_by_9(settings_file, aspect):
    settings_file.write_text(json.dumps({'aspect_ratio': aspect}))
    assert Settings().aspect_ratio == '16:9'


def test_legacy_settings_preserve_fps_and_gain_safe_defaults(settings_file):
    settings_file.write_text(json.dumps({'fps_index': 3, 'difficulty': 'hard',
                                         'volume': .6, 'fullscreen': True}))
    settings = Settings()
    assert settings.fps == 144
    assert settings.difficulty == 'hard'
    assert settings.volume == .6
    assert settings.fullscreen is True
    assert settings.aspect_ratio == '16:9'
    assert settings.show_fps is True


@pytest.mark.parametrize('cap', [240, 0])
def test_extended_fps_limits_roundtrip(cap):
    settings = Settings()
    settings.fps_index = FRAMERATES.index(cap)
    settings.save()
    assert Settings().fps == cap


def test_fps_counter_preference_roundtrip():
    settings = Settings()
    settings.show_fps = False
    settings.save()
    assert Settings().show_fps is False


@pytest.mark.parametrize('value', ['false', None, [], 0])
def test_bad_fps_counter_value_keeps_safe_default(settings_file, value):
    settings_file.write_text(json.dumps({'show_fps': value}))
    assert Settings().show_fps is True


def test_non_object_settings_file_is_ignored(settings_file):
    settings_file.write_text('[]')
    settings = Settings()
    assert settings.fps == 60
    assert settings.aspect_ratio == '16:9'


def test_aspect_selection_saves_and_requests_next_flight_update(gameplay):
    import pygame
    settings = Settings.get()
    screen = gameplay._settings
    screen.focus.select(screen._ROWS.index('aspect'))
    assert screen.handle_key(pygame.K_RIGHT, gameplay) == 'aspect'
    assert settings.aspect_ratio == '16:10'
    assert Settings().aspect_ratio == '16:10'


def test_clicking_extended_fps_option_changes_saved_cap(gameplay):
    screen = gameplay._settings
    rect = screen._layout(1280)['fps_rects'][FRAMERATES.index(240)]
    assert screen.handle_click(rect.center, gameplay) is None
    assert Settings.get().fps == 240
    assert Settings().fps == 240


def test_keyboard_toggles_fps_counter_and_persists(gameplay):
    import pygame
    screen = gameplay._settings
    screen.focus.select(screen._ROWS.index('show_fps'))
    assert screen.handle_key(pygame.K_RETURN, gameplay) is None
    assert Settings.get().show_fps is False
    assert Settings().show_fps is False
