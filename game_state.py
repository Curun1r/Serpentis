"""Shared screen states, independent of the application controller."""

from enum import Enum


class GameState(Enum):
    LOADING = "loading"
    START = "start"
    SHIP_SELECT = "ship_select"
    PLAYING = "playing"
    PAUSED = "paused"
    DYING = "dying"  # death animation before game over
    GAME_OVER = "game_over"
    SETTINGS = "settings"
    CONTROLS = "controls"
    LEADERBOARD = "leaderboard"
