"""Tests for the persistent leaderboard (score_manager.py)."""
import json

import pytest

import score_manager
from score_manager import ScoreManager


@pytest.fixture(autouse=True)
def scores_file(tmp_path, monkeypatch):
    """Redirect the scores file into a temp dir for every test."""
    path = tmp_path / 'scores.json'
    monkeypatch.setattr(score_manager, 'SCORES_FILE', str(path))
    return path


def test_load_missing_file_returns_defaults():
    assert ScoreManager.load() == (0, [])


def test_load_corrupt_file_returns_defaults(scores_file):
    scores_file.write_text('{not valid json')
    assert ScoreManager.load() == (0, [])


def test_save_persists_new_best(scores_file):
    ScoreManager.save(120)
    best, entries = ScoreManager.load()
    assert best == 120
    assert entries == []


def test_save_ignores_lower_score(scores_file):
    ScoreManager.save(120)
    ScoreManager.save(50)
    best, _ = ScoreManager.load()
    assert best == 120


def test_add_entry_sorted_descending():
    ScoreManager.add_entry(100, wave=3, ship='serpent')
    ScoreManager.add_entry(300, wave=7, ship='viper')
    ScoreManager.add_entry(200, wave=5, ship='hydra')
    _, entries = ScoreManager.load()
    assert [e['score'] for e in entries] == [300, 200, 100]


def test_add_entry_keeps_top_five_only():
    for score in [10, 20, 30, 40, 50, 60, 70]:
        ScoreManager.add_entry(score, wave=1, ship='serpent')
    _, entries = ScoreManager.load()
    assert len(entries) == score_manager.MAX_ENTRIES
    assert [e['score'] for e in entries] == [70, 60, 50, 40, 30]


def test_add_entry_updates_best_score():
    ScoreManager.add_entry(999, wave=12, ship='hydra', difficulty='hard')
    best, entries = ScoreManager.load()
    assert best == 999
    assert entries[0]['difficulty'] == 'hard'


def test_entry_contains_all_fields():
    ScoreManager.add_entry(42, wave=2, ship='viper')
    _, entries = ScoreManager.load()
    assert set(entries[0]) == {'score', 'wave', 'ship', 'difficulty', 'date'}


def test_written_file_is_valid_json(scores_file):
    ScoreManager.add_entry(5, wave=1, ship='serpent')
    data = json.loads(scores_file.read_text())
    assert data['best_score'] == 5
