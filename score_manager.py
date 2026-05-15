import json
import os

# Store scores in a dedicated data folder, separate from source code
SCORES_FILE = 'data/scores.json'


class ScoreManager:
    """Handles saving and loading the best score between sessions.

    Uses JSON so the file is human-readable and easy to extend
    (e.g. add player name, date, or a full leaderboard later).
    """

    @staticmethod
    def load() -> int:
        """Read the best score from disk. Returns 0 if file doesn't exist yet."""
        if not os.path.exists(SCORES_FILE):
            return 0
        try:
            with open(SCORES_FILE, 'r') as f:
                data = json.load(f)
                return int(data.get('best_score', 0))
        except (json.JSONDecodeError, IOError, ValueError):
            # If the file is corrupted or unreadable, start fresh
            return 0

    @staticmethod
    def save(score: int) -> None:
        """Write the best score to disk, creating the data folder if needed."""
        os.makedirs(os.path.dirname(SCORES_FILE), exist_ok=True)
        with open(SCORES_FILE, 'w') as f:
            json.dump({'best_score': score}, f)
