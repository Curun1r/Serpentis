"""Tests for config.json loading (config.py)."""
import json
from pathlib import Path
import runpy

import config
import paths
from paths import resource_path


def test_load_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(config, '_CONFIG_FILE', str(tmp_path / 'missing.json'))
    assert config._load() == {}


def test_load_corrupt_file(tmp_path, monkeypatch):
    path = tmp_path / 'config.json'
    path.write_text('{broken')
    monkeypatch.setattr(config, '_CONFIG_FILE', str(path))
    assert config._load() == {}


def test_load_valid_file(tmp_path, monkeypatch):
    path = tmp_path / 'config.json'
    path.write_text(json.dumps({'screen': {'width': 800}}))
    monkeypatch.setattr(config, '_CONFIG_FILE', str(path))
    assert config._load() == {'screen': {'width': 800}}


def test_module_constants_have_sane_values():
    assert config.SCREEN_WIDTH > 0
    assert config.SCREEN_HEIGHT > 0
    assert isinstance(config.GAME_CAPTION, str) and config.GAME_CAPTION
    assert config.FIGHTER_SPEED > 0
    assert config.ALIEN_SPEED > 0
    assert config.BALL_SPEED > 0
    assert config.ALIEN_COUNT > 0
    assert config.STARTING_LIVES > 0


def test_example_config_matches_expected_schema():
    """config.example.json must stay parseable and use only known sections."""
    with open(resource_path('config.example.json')) as f:
        example = json.load(f)
    assert set(example) <= {'screen', 'speeds', 'scales', 'gameplay'}


def test_clean_release_defaults_match_the_documented_configuration(tmp_path, monkeypatch):
    """A private, ignored config.json must not hide different release defaults."""
    example = json.loads(Path(resource_path('config.example.json')).read_text())
    monkeypatch.setattr(paths, 'resource_path', lambda name: str(tmp_path / name))
    clean = runpy.run_path(config.__file__)
    for section, names in {
        'speeds': {'fighter': 'FIGHTER_SPEED', 'alien': 'ALIEN_SPEED', 'ball': 'BALL_SPEED'},
        'scales': {'fighter': 'FIGHTER_SCALE', 'alien': 'ALIEN_SCALE', 'ball': 'BALL_SCALE'},
        'gameplay': {'alien_count': 'ALIEN_COUNT', 'starting_lives': 'STARTING_LIVES',
                     'alien_stagger': 'ALIEN_STAGGER'},
    }.items():
        for key, constant in names.items():
            assert clean[constant] == example[section][key], constant


def test_explicit_local_sprite_scale_overrides_remain_supported(tmp_path, monkeypatch):
    (tmp_path / 'config.json').write_text(json.dumps({'scales': {'alien': .5, 'ball': .25}}))
    monkeypatch.setattr(paths, 'resource_path', lambda name: str(tmp_path / name))
    custom = runpy.run_path(config.__file__)
    assert custom['ALIEN_SCALE'] == .5
    assert custom['BALL_SCALE'] == .25
