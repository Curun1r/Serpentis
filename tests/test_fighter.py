"""Player movement and dash behavior, independent of display and sound."""
import math

import pytest

import config
from fighter import DASH_COOLDOWN, DASH_DURATION, DASH_MULTIPLIER, Fighter
from ship import SHIPS


@pytest.fixture(params=SHIPS, ids=lambda ship: ship.id)
def player(request, monkeypatch):
    monkeypatch.setattr(config, 'SCREEN_WIDTH', 1280)
    monkeypatch.setattr(config, 'SCREEN_HEIGHT', 720)
    fighter = Fighter(ship=request.param)
    fighter.x = 400.0
    fighter.y = 300.0
    return fighter, request.param


@pytest.mark.parametrize('fps', [30, 60, 120, 144])
def test_dash_recharges_and_can_be_used_again(player, fps):
    fighter, ship = player
    fighter.move_right()
    fighter.dash()
    assert fighter.is_dashing

    recharge_time = (DASH_DURATION * ship.dash_duration_mult
                     + DASH_COOLDOWN * ship.dash_cooldown_mult)
    for _ in range(math.ceil(recharge_time * fps) + 1):
        fighter.update(1 / fps)
        assert 0.0 <= fighter.dash_cooldown_ratio <= 1.0

    assert not fighter.is_dashing
    assert fighter.dash_cooldown_ratio == 0.0
    fighter.dash()
    assert fighter.is_dashing
    assert fighter.dash_cooldown_ratio == 1.0


def test_long_frame_does_not_extend_dash_distance(player):
    fighter, ship = player
    start_x = fighter.x
    dash_duration = DASH_DURATION * ship.dash_duration_mult
    normal_duration = 0.05
    fighter.move_right()
    fighter.dash()
    fighter.update(dash_duration + normal_duration)

    expected_distance = fighter.speed * (DASH_MULTIPLIER * dash_duration + normal_duration)
    assert fighter.x == pytest.approx(start_x + expected_distance)
    assert not fighter.is_dashing


@pytest.mark.parametrize('direction', ['left', 'right', 'up', 'down'])
def test_normal_movement_stays_inside_screen(player, direction):
    fighter, _ = player
    fighter.x = 1.0 if direction == 'left' else float(config.SCREEN_WIDTH - fighter.width - 1)
    fighter.y = 1.0 if direction == 'up' else float(config.SCREEN_HEIGHT - fighter.height - 1)
    getattr(fighter, f'move_{direction}')()
    fighter.update(1 / 30)

    assert 0.0 <= fighter.x <= config.SCREEN_WIDTH - fighter.width
    assert 0.0 <= fighter.y <= config.SCREEN_HEIGHT - fighter.height
    assert 0 <= fighter.rect.left <= fighter.rect.right <= config.SCREEN_WIDTH
    assert 0 <= fighter.rect.top <= fighter.rect.bottom <= config.SCREEN_HEIGHT


@pytest.mark.parametrize('direction', ['left', 'right', 'up', 'down'])
def test_dash_stays_inside_screen(player, direction):
    fighter, _ = player
    fighter.x = 1.0 if direction == 'left' else float(config.SCREEN_WIDTH - fighter.width - 1)
    fighter.y = 1.0 if direction == 'up' else float(config.SCREEN_HEIGHT - fighter.height - 1)
    getattr(fighter, f'move_{direction}')()
    fighter.dash()
    fighter.update(1 / 30)

    assert 0.0 <= fighter.x <= config.SCREEN_WIDTH - fighter.width
    assert 0.0 <= fighter.y <= config.SCREEN_HEIGHT - fighter.height


def test_opposite_movement_keys_cancel_each_other_at_edge(player):
    fighter, _ = player
    fighter.x = 0.0
    fighter.y = 0.0
    fighter.move_left()
    fighter.move_right()
    fighter.move_up()
    fighter.move_down()
    fighter.update(1 / 60)

    assert fighter.x == 0.0
    assert fighter.y == 0.0
