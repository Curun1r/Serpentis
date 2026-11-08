"""Mini-boss identities, dodge windows and movement remain stable at any FPS."""

import math
import random

import pygame
import pytest

import config
from mini_boss import MiniBoss
from settings_manager import Settings


@pytest.fixture(autouse=True)
def isolated_arena(pygame_context, monkeypatch, tmp_path):
    import settings_manager

    monkeypatch.setattr(config, 'SCREEN_WIDTH', 1280)
    monkeypatch.setattr(config, 'SCREEN_HEIGHT', 720)
    monkeypatch.setattr(settings_manager, 'SETTINGS_FILE', str(tmp_path / 'settings.json'))
    monkeypatch.setattr(Settings, '_instance', None)
    state = random.getstate()
    random.seed(42)
    yield
    random.setstate(state)


def entered(wave):
    enemy = MiniBoss(wave)
    enemy.update(1.0)
    assert not enemy._entering
    return enemy


@pytest.mark.parametrize(('wave', 'name'), [(3, 'RAIDER'), (8, 'HUNTER'), (13, 'WARDEN'), (18, 'RAIDER')])
def test_encounters_cycle_between_distinct_roles(wave, name):
    assert MiniBoss(wave).name == name
    assert MiniBoss.style_for_wave(wave).name == name


def test_roles_have_distinct_models_and_accents():
    enemies = [MiniBoss(wave) for wave in (3, 8, 13)]
    assert len({enemy.color for enemy in enemies}) == 3
    # Compare the source silhouettes independently of later-wave scaling.
    masks = [pygame.mask.from_surface(enemy.image).count() / (enemy.width * enemy.height) for enemy in enemies]
    assert len(set(masks)) == 3


@pytest.mark.parametrize('wave', [3, 8, 13])
def test_entrance_does_not_fire_or_spend_the_first_cooldown(wave):
    enemy = MiniBoss(wave)
    initial_x, cooldown = enemy.x, enemy._phase_left
    while enemy._entering:
        enemy.update(0.1, (100, 600))
        assert enemy.drain_shots() == []
        assert enemy.x == initial_x
        assert enemy._phase_left == cooldown
    assert enemy.y == enemy._rest_y
    enemy.update(0.3, (100, 600))
    assert enemy._phase_left == pytest.approx(cooldown - 0.3)


def test_raider_marks_a_dive_then_commits_and_retreats():
    enemy = entered(3)
    enemy._phase_left = 0.1
    enemy.update(0.1, (1050, 620))
    start = pygame.Vector2(enemy.x, enemy.y)
    marked = enemy.attack_target
    enemy.update(0.3, (100, 620))
    assert enemy.attack_warning > 0
    assert enemy.attack_target == marked
    assert (enemy.x, enemy.y) == tuple(start)
    assert enemy.drain_shots() == []
    enemy.update(0.35, (100, 620))
    assert len(enemy.drain_shots()) == 3
    enemy.update(0.48, (100, 620))
    assert enemy.y > start.y + 100
    assert enemy.rect.center == pytest.approx(marked, abs=1)
    assert enemy.hit_rect.center == enemy.rect.center
    dive_y = enemy.y
    enemy.update(0.8, (100, 620))
    assert enemy.y < dive_y


def test_hunter_tracks_player_before_locking_a_three_round_burst():
    enemy = entered(8)
    enemy._phase_left = 5
    origin = enemy.x
    enemy.update(0.8, (1100, 620))
    assert enemy.x > origin
    enemy.update(0.8, (100, 620))
    assert enemy.x < origin + 2

    enemy._phase_left = 0.1
    enemy.update(0.1, (100, 620))
    assert enemy.attack_target == (100, 620)
    enemy.update(enemy.style.windup, (1100, 620))
    shots = enemy.drain_shots()
    assert len(shots) == 1
    enemy.update(0.36, (1100, 620))
    shots += enemy.drain_shots()
    assert len(shots) == 3
    assert all(vx < 0 and vy > 0 for _, _, vx, vy in shots)
    assert enemy.drain_shots() == []


def test_warden_fan_leaves_a_gap_and_changes_it_on_the_next_volley():
    enemy = entered(13)
    volleys = []
    for _ in range(2):
        enemy._phase_left = 0.1
        enemy.update(0.1, (640, 620))
        assert enemy.attack_target is None
        enemy.update(enemy.style.windup, (640, 620))
        shots = enemy.drain_shots()
        assert len(shots) == 5
        angles = sorted(math.atan2(vx, vy) for _, _, vx, vy in shots)
        assert max(b - a for a, b in zip(angles, angles[1:])) == pytest.approx(0.76)
        assert all(vy > 0 for _, _, _, vy in shots)
        volleys.append(angles)
    assert volleys[0] != volleys[1]


@pytest.mark.parametrize('wave', [3, 8, 13])
@pytest.mark.parametrize('width', [960, 1152, 1280, 1680], ids=['4:3', '16:10', '16:9', '21:9'])
def test_long_encounters_stay_inside_the_arena(wave, width, monkeypatch):
    monkeypatch.setattr(config, 'SCREEN_WIDTH', width)
    enemy = entered(wave)
    for frame in range(1800):
        target = (width * (0.5 + 0.45 * math.sin(frame / 180)), 620)
        old = pygame.Vector2(enemy.x, enemy.y)
        enemy.update(1 / 60, target)
        assert 0 <= enemy.x <= width - enemy.width
        assert 22 <= enemy.y <= 720 - enemy.height
        assert enemy.hit_rect.center == enemy.rect.center
        # Even the dive is continuous: no visible teleports between phases.
        assert old.distance_to((enemy.x, enemy.y)) < width / 20
        assert all(math.isfinite(v) for shot in enemy.drain_shots() for v in shot)


@pytest.mark.parametrize('wave', [3, 8, 13])
def test_attack_timing_is_independent_of_fps_cap(wave):
    timelines = []
    for fps in (30, 60, 144):
        random.seed(15)
        enemy = entered(wave)
        timeline = []
        for frame in range(fps * 12):
            enemy.update(1 / fps, (1050, 620))
            timeline.extend([(frame + 1) / fps] * len(enemy.drain_shots()))
        timelines.append(timeline)
    for timeline in timelines[1:]:
        assert timeline == pytest.approx(timelines[0], abs=1 / 30)


@pytest.mark.parametrize('wave', [3, 8, 13])
def test_difficulty_and_low_health_change_tempo_without_removing_windup(wave):
    counts = []
    for difficulty, damaged in [('easy', False), ('normal', False), ('hard', False), ('hard', True)]:
        random.seed(10)
        Settings.get().difficulty = difficulty
        enemy = entered(wave)
        if damaged:
            enemy.take_hit(enemy.max_hp - 1)
        count = 0
        for _ in range(1200):
            enemy.update(1 / 60, (900, 620))
            count += len(enemy.drain_shots())
        counts.append(count)
        assert enemy.style.windup >= 0.6
    assert counts == sorted(counts)
    assert counts[0] < counts[-1]


def test_game_supplies_player_position_to_the_hunter(gameplay):
    game = gameplay
    game._start_wave(8)
    game._pending_boss_wave = 0
    game._boss_warning_timer = 0
    enemy = entered(8)
    enemy._phase_left = 0.1
    game.mini_boss = enemy
    game.fighter.rect.center = (1000, 620)
    game._update_mini_boss(0.1)
    assert enemy.attack_target == (1000, 620)
    game._update_mini_boss(enemy.style.windup)
    assert len(game.alien_bullets) == 1
    assert next(iter(game.alien_bullets)).vx > 0


@pytest.mark.parametrize('wave', [3, 8, 13])
def test_windup_and_named_health_bar_render_without_advancing_the_attack(gameplay, monkeypatch, wave):
    import rendering

    enemy = entered(wave)
    enemy._phase_left = 0.1
    enemy.update(0.3, (950, 620))
    assert enemy.attack_warning > 0
    gameplay.mini_boss = enemy
    gameplay.wave = wave
    monkeypatch.setattr(pygame.time, 'get_ticks', lambda: 10000)
    phase_left = enemy._phase_left
    rendering.draw_world(gameplay)
    pixels = pygame.image.tobytes(gameplay._canvas, 'RGB')
    rendering.draw_world(gameplay)
    assert pygame.image.tobytes(gameplay._canvas, 'RGB') == pixels
    assert enemy._phase_left == phase_left
    assert enemy.drain_shots() == []
    assert any(key[1].startswith(enemy.name) for key in gameplay._painter._labels)
