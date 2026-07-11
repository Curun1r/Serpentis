"""Tests for config.json loading (config.py)."""
import json

import config


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
    with open('config.example.json') as f:
        example = json.load(f)
    assert set(example) <= {'screen', 'speeds', 'scales', 'gameplay'}
