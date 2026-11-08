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


def test_add_entry_keeps_top_hundred_only():
    for score in range(1, 106):
        ScoreManager.add_entry(score, wave=1, ship='serpent')
    _, entries = ScoreManager.load()
    assert len(entries) == score_manager.MAX_ENTRIES
    assert [e['score'] for e in entries] == list(range(105, 5, -1))


def test_add_entry_updates_best_score():
    ScoreManager.add_entry(999, wave=12, ship='hydra', difficulty='hard')
    best, entries = ScoreManager.load()
    assert best == 999
    assert entries[0]['difficulty'] == 'hard'


def test_entry_contains_all_fields():
    ScoreManager.add_entry(42, wave=2, ship='viper')
    _, entries = ScoreManager.load()
    assert {'score', 'wave', 'ship', 'difficulty', 'date', 'duration', 'aspect_ratio',
            'id', 'timestamp'} <= set(entries[0])


def test_written_file_is_valid_json(scores_file):
    ScoreManager.add_entry(5, wave=1, ship='serpent')
    data = json.loads(scores_file.read_text())
    assert data['best_score'] == 5


def test_legacy_results_preserve_fields_and_higher_all_time_best(scores_file):
    legacy = {'score': 25, 'wave': 3, 'ship': 'Viper', 'date': '31.12.2025',
              'custom_note': 'old result'}
    scores_file.write_text(json.dumps({'best_score': 900, 'entries': [legacy]}))
    before = scores_file.read_text()
    best, entries = ScoreManager.load()
    assert best == 900
    assert all(entries[0][key] == value for key, value in legacy.items())
    assert entries[0]['difficulty'] == 'normal'
    assert entries[0]['duration'] == 0
    assert scores_file.read_text() == before  # Viewing records is not a migration write.
    ScoreManager.add_entry(30, 4, 'Serpent')
    assert ScoreManager.load()[0] == 900
    assert ScoreManager.load()[1][1]['custom_note'] == 'old result'


def test_result_stores_duration_ratio_and_unique_identity():
    first = ScoreManager.add_entry(50, 6, 'Hydra', 'hard', duration=123.75, aspect_ratio='21:9')
    second = ScoreManager.add_entry(49, 5, 'Hydra', 'hard', duration=61, aspect_ratio='16:10')
    assert first[0]['duration'] == 123.75
    assert first[0]['aspect_ratio'] == '21:9'
    assert second[0]['id'] != second[1]['id']
    assert second[0]['timestamp']


def test_oversized_legacy_duration_does_not_discard_valid_result(scores_file):
    scores_file.write_text(json.dumps({'entries': [
        {'score': 40, 'wave': 3, 'ship': 'Viper', 'duration': 10 ** 400},
    ]}))
    best, entries = ScoreManager.load()
    assert best == 40 and len(entries) == 1
    assert entries[0]['duration'] == 0.0


@pytest.mark.parametrize('data', [None, [], 'invalid', {'entries': None}, {'entries': 'invalid'}])
def test_loading_invalid_json_schema_returns_safe_defaults(scores_file, data):
    scores_file.write_text(json.dumps(data))
    assert ScoreManager.load() == (0, [])


def test_invalid_records_do_not_discard_other_valid_results(scores_file):
    entries = [None, [], {'score': 'oops', 'wave': 3, 'ship': 'Viper'},
               {'score': 9, 'wave': -1, 'ship': 'Hydra'},
               {'score': True, 'wave': 3, 'ship': 'Serpent'},
               {'score': 22, 'wave': 3, 'ship': 'Custom legacy ship', 'difficulty': {}, 'date': []}]
    scores_file.write_text(json.dumps({'best_score': 'bad', 'entries': entries}))
    best, loaded = ScoreManager.load()
    assert best == 22 and len(loaded) == 1
    assert loaded[0]['ship'] == 'Custom legacy ship'
    assert loaded[0]['difficulty'] == 'normal'
    assert loaded[0]['date'] == ''


def test_failed_atomic_replace_preserves_existing_file_and_removes_temp(scores_file, monkeypatch):
    ScoreManager.add_entry(10, 1, 'Serpent')
    before = scores_file.read_bytes()
    def fail(*args):
        raise OSError('cannot replace')
    monkeypatch.setattr(score_manager.os, 'replace', fail)
    with pytest.raises(OSError, match='cannot replace'):
        ScoreManager.add_entry(20, 2, 'Viper')
    assert scores_file.read_bytes() == before
    assert not list(scores_file.parent.glob('.scores-*.tmp'))


def test_query_filters_case_insensitively_without_mutating_input():
    entries = [{'score': 100, 'wave': 2, 'ship': 'viper', 'difficulty': 'hard'},
               {'score': 90, 'wave': 3, 'ship': 'Viper', 'difficulty': 'easy'},
               {'score': 80, 'wave': 4, 'ship': 'Hydra', 'difficulty': 'hard'}]
    before = json.loads(json.dumps(entries))
    result = ScoreManager.query(entries, ship='Viper', difficulty='hard')
    assert [entry['score'] for entry in result] == [100]
    result[0]['score'] = 1
    assert entries == before


def test_query_sorts_by_wave_and_actual_calendar_date():
    entries = [{'score': 90, 'wave': 4, 'ship': 'Serpent', 'date': '31.12.2025'},
               {'score': 30, 'wave': 8, 'ship': 'Viper', 'date': '01.01.2026'},
               {'score': 60, 'wave': 5, 'ship': 'Hydra', 'date': '15.03.2026'}]
    assert [entry['wave'] for entry in ScoreManager.query(entries, sort='wave')] == [8, 5, 4]
    assert [entry['score'] for entry in ScoreManager.query(entries, sort='date')] == [60, 30, 90]


def test_recent_results_use_timestamp_for_order_within_one_day():
    entries = [{'score': 90, 'wave': 4, 'ship': 'Serpent', 'date': '07.11.2026',
                'timestamp': '2026-11-07T09:00:00+00:00'},
               {'score': 30, 'wave': 8, 'ship': 'Viper', 'date': '07.11.2026',
                'timestamp': '2026-11-07T10:00:00+00:00'}]
    assert [entry['score'] for entry in ScoreManager.query(entries, sort='date')] == [30, 90]
