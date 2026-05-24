"""Persistent top-5 leaderboard stored as JSON."""
import json
import os
from datetime import datetime

SCORES_FILE  = 'data/scores.json'
MAX_ENTRIES  = 5


class ScoreManager:

    @staticmethod
    def load() -> tuple[int, list[dict]]:
        """Return (best_score, entries) from disk.

        *entries* is a list of dicts sorted by score descending:
            {'score': int, 'wave': int, 'ship': str, 'date': str}

        Falls back to (0, []) if the file is missing or corrupted.
        """
        if not os.path.exists(SCORES_FILE):
            return 0, []
        try:
            with open(SCORES_FILE, 'r') as f:
                data = json.load(f)
            entries = data.get('entries', [])
            best    = data.get('best_score',
                               max((e['score'] for e in entries), default=0))
            return int(best), entries
        except (json.JSONDecodeError, IOError, ValueError):
            return 0, []

    @staticmethod
    def save(score: int) -> None:
        """Update only the best-score field (called frequently during gameplay)."""
        best, entries = ScoreManager.load()
        if score <= best:
            return
        os.makedirs(os.path.dirname(SCORES_FILE), exist_ok=True)
        with open(SCORES_FILE, 'w') as f:
            json.dump({'best_score': score, 'entries': entries}, f, indent=2)

    @staticmethod
    def add_entry(score: int, wave: int, ship: str) -> list[dict]:
        """Insert a new entry, keep the top-MAX_ENTRIES, return the updated list.

        Call this exactly once per game session, at Game-Over.
        """
        _, entries = ScoreManager.load()
        entries.append({
            'score': score,
            'wave':  wave,
            'ship':  ship,
            'date':  datetime.now().strftime('%d.%m.%Y'),
        })
        entries.sort(key=lambda e: e['score'], reverse=True)
        entries = entries[:MAX_ENTRIES]
        best = entries[0]['score'] if entries else 0
        os.makedirs(os.path.dirname(SCORES_FILE), exist_ok=True)
        with open(SCORES_FILE, 'w') as f:
            json.dump({'best_score': best, 'entries': entries}, f, indent=2)
        return entries
