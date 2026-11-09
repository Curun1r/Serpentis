"""Persistent top-100 leaderboard with safe legacy loading and atomic updates."""
from datetime import datetime
from copy import deepcopy
import json
import math
import os
import tempfile
from uuid import uuid4

from paths import user_data_dir

SCORES_FILE = os.path.join(user_data_dir(), 'scores.json')
MAX_ENTRIES = 100
_DIFFICULTIES = {'easy', 'normal', 'hard'}


def _nonnegative_int(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if not math.isfinite(value) or value < 0 or int(value) != value:
        return None
    return int(value)


def _duration(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0
    try:
        duration = float(value)
    except (OverflowError, ValueError):
        return 0.0
    return duration if math.isfinite(duration) and duration >= 0 else 0.0


def _entry(value):
    """Preserve legacy metadata while normalizing values used by the UI."""
    if not isinstance(value, dict):
        return None
    score = _nonnegative_int(value.get('score'))
    wave = _nonnegative_int(value.get('wave'))
    ship = value.get('ship')
    if score is None or wave is None or not isinstance(ship, str) or not ship.strip():
        return None
    entry = deepcopy(value)
    entry.update(score=score, wave=wave)
    difficulty = value.get('difficulty', 'normal')
    entry['difficulty'] = difficulty.lower() if isinstance(difficulty, str) and difficulty.lower() in _DIFFICULTIES else 'normal'
    entry['date'] = value.get('date', '') if isinstance(value.get('date', ''), str) else ''
    entry['duration'] = _duration(value.get('duration', 0))
    aspect = value.get('aspect_ratio', '16:9')
    entry['aspect_ratio'] = aspect if isinstance(aspect, str) and aspect else '16:9'
    return entry


def _date_key(entry):
    timestamp = entry.get('timestamp')
    if isinstance(timestamp, str):
        try:
            return datetime.fromisoformat(timestamp).timestamp()
        except (ValueError, OverflowError, OSError):
            pass
    try:
        return datetime.strptime(entry.get('date', ''), '%d.%m.%Y').timestamp()
    except (ValueError, TypeError, OverflowError, OSError):
        return float('-inf')


class ScoreManager:
    @staticmethod
    def load() -> tuple[int, list[dict]]:
        """Read and validate scores without rewriting or dropping legacy metadata."""
        try:
            with open(SCORES_FILE, encoding='utf-8') as source:
                data = json.load(source)
            if not isinstance(data, dict):
                return 0, []
            raw_entries = data.get('entries', [])
            entries = []
            if isinstance(raw_entries, list):
                entries = [entry for value in raw_entries if (entry := _entry(value)) is not None]
            entries.sort(key=lambda entry: entry['score'], reverse=True)
            entries = entries[:MAX_ENTRIES]
            best = _nonnegative_int(data.get('best_score', 0)) or 0
            return max(best, entries[0]['score'] if entries else 0), entries
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            return 0, []

    @staticmethod
    def _write(best: int, entries: list[dict]) -> None:
        directory = os.path.dirname(os.path.abspath(SCORES_FILE))
        os.makedirs(directory, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=directory,
                                             prefix='.scores-', suffix='.tmp', delete=False) as output:
                temporary = output.name
                json.dump({'best_score': best, 'entries': entries}, output, indent=2, ensure_ascii=False)
                output.write('\n')
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, SCORES_FILE)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)

    @staticmethod
    def save(score: int) -> None:
        """Update the all-time best without changing stored session results."""
        score = _nonnegative_int(score)
        if score is None:
            raise ValueError('Score must be a nonnegative integer')
        best, entries = ScoreManager.load()
        if score > best:
            ScoreManager._write(score, entries)

    @staticmethod
    def add_entry(score: int, wave: int, ship: str, difficulty: str = 'normal',
                  duration: float = 0.0, aspect_ratio: str = '16:9', *,
                  best_score: int | None = None) -> list[dict]:
        """Record one completed run, retaining the top 100 and any higher saved best."""
        now = datetime.now().astimezone()
        entry = _entry({'score': score, 'wave': wave, 'ship': ship,
                        'difficulty': difficulty, 'date': now.strftime('%d.%m.%Y'),
                        'timestamp': now.isoformat(timespec='seconds'), 'id': uuid4().hex,
                        'duration': duration, 'aspect_ratio': aspect_ratio})
        if entry is None:
            raise ValueError('A result requires a nonnegative score/wave and a ship name')
        pending_best = entry['score'] if best_score is None else _nonnegative_int(best_score)
        if pending_best is None:
            raise ValueError('Best score must be a nonnegative integer')
        best, entries = ScoreManager.load()
        entries.append(entry)
        entries.sort(key=lambda value: value['score'], reverse=True)
        entries = entries[:MAX_ENTRIES]
        ScoreManager._write(max(best, pending_best, entry['score']), entries)
        return entries

    @staticmethod
    def query(entries, ship='all', difficulty='all', sort='score') -> list[dict]:
        """Filter and rank a copy; never mutate the original records or their order."""
        records = [record for value in entries if (record := _entry(value)) is not None]
        if ship.lower() != 'all':
            records = [entry for entry in records if entry['ship'].casefold() == ship.casefold()]
        if difficulty.lower() != 'all':
            records = [entry for entry in records if entry['difficulty'] == difficulty.lower()]
        if sort == 'wave':
            return sorted(records, key=lambda entry: (entry['wave'], entry['score']), reverse=True)
        if sort == 'date':
            return sorted(records, key=lambda entry: (_date_key(entry), entry['score']), reverse=True)
        return sorted(records, key=lambda entry: entry['score'], reverse=True)
