"""Sanity checks for ship definitions (ship.py)."""
from ship import SHIPS


def test_ship_ids_are_unique():
    ids = [s.id for s in SHIPS]
    assert len(ids) == len(set(ids))


def test_stat_bars_in_display_range():
    for s in SHIPS:
        assert 0 <= s.stat_speed <= 10, s.id
        assert 0 <= s.stat_fire <= 10, s.id
        assert 0 <= s.stat_dash <= 10, s.id


def test_multipliers_are_positive():
    for s in SHIPS:
        assert s.speed_mult > 0, s.id
        assert s.dash_cooldown_mult > 0, s.id
        assert s.dash_duration_mult > 0, s.id


def test_shooting_limits_are_valid():
    for s in SHIPS:
        assert s.default_shots >= 1, s.id
        assert s.max_bullets >= s.default_shots, s.id


def test_colors_are_valid_rgb():
    for s in SHIPS:
        assert len(s.color) == 3, s.id
        assert all(0 <= c <= 255 for c in s.color), s.id


def test_configs_are_frozen():
    import dataclasses
    import pytest
    with pytest.raises(dataclasses.FrozenInstanceError):
        SHIPS[0].name = 'Hacked'
