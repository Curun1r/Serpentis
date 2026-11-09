"""A physical hit provides recovery time; missed enemies remain separate penalties."""

import math

import pygame
import pytest

from alien import Alien
from alien_bullet import AlienBullet
from boss import Boss, MiniBoss
from combat import DAMAGE_GRACE_SECONDS
from game_state import GameState
import rendering


def calm_arena(game):
    game.aliens.empty()
    game.balls.empty()
    game.alien_bullets.empty()
    game._boss_warning_timer = 999.0
    game._pending_boss_wave = 0


@pytest.mark.parametrize('fps', [30, 60, 120, 144, 240])
def test_physical_hit_grace_expires_after_elapsed_game_time(gameplay, fps):
    game = gameplay
    calm_arena(game)
    game._take_damage()
    assert game.lives == 2
    for frame in range(1, math.ceil(DAMAGE_GRACE_SECONDS * fps) + 1):
        game._update(1 / fps)
        game._take_damage()
        expected = 2 if frame / fps < DAMAGE_GRACE_SECONDS - 1e-9 else 1
        assert game.lives == expected
    # The first post-expiry hit starts its own window in the same frame.
    game._take_damage()
    assert game.lives == 1


@pytest.mark.parametrize('mini', [False, True], ids=['boss', 'mini-boss'])
def test_sustained_boss_contact_cannot_drain_lives_every_frame(gameplay, monkeypatch, mini):
    game = gameplay
    calm_arena(game)
    enemy = MiniBoss(3) if mini else Boss(5)
    if mini:
        enemy.update(1.0)
        game.mini_boss = enemy
    else:
        game.boss = enemy
    monkeypatch.setattr(enemy, 'update', lambda *args: None)
    game.fighter.rect.center = enemy.rect.center
    game.fighter.x, game.fighter.y = game.fighter.rect.topleft
    game._update(0)
    for _ in range(60):
        game._update(1 / 120)
    assert game.lives == 2
    assert game.state == GameState.PLAYING
    for _ in range(24):
        game._update(1 / 120)
    assert game.lives == 1


@pytest.mark.parametrize('shield', [False, True])
def test_simultaneous_alien_contacts_consume_one_hit_or_shield(gameplay, shield):
    game = gameplay
    calm_arena(game)
    game._shield_active = shield
    for _ in range(3):
        alien = Alien()
        alien.rect.center = game.fighter.rect.center
        alien.x, alien.y = alien.rect.topleft
        game.aliens.add(alien)
    game._update(0)
    assert game.lives == (3 if shield else 2)
    assert not game._shield_active
    assert len(game.aliens) == 0


def test_shield_break_protects_against_the_next_frame_of_contact(gameplay):
    game = gameplay
    calm_arena(game)
    game._shield_active = True
    game.alien_bullets.add(AlienBullet(*game.fighter.rect.center))
    game._update(0)
    assert not game._shield_active
    assert game.lives == 3
    assert game._damage_grace_remaining == DAMAGE_GRACE_SECONDS
    game.alien_bullets.add(AlienBullet(*game.fighter.rect.center))
    game._update(1 / 120)
    assert game.lives == 3
    assert not game.alien_bullets


def test_a_new_shield_is_not_consumed_during_existing_hit_protection(gameplay):
    game = gameplay
    calm_arena(game)
    game._take_damage()
    game._shield_active = True
    game.alien_bullets.add(AlienBullet(*game.fighter.rect.center))
    game._update(0)
    assert game.lives == 2
    assert game._shield_active


def test_each_escaped_alien_costs_a_life_despite_grace_or_shield(gameplay):
    game = gameplay
    calm_arena(game)
    game.lives = 5
    game._damage_grace_remaining = 0.5
    game._shield_active = True
    for _ in range(2):
        alien = Alien()
        alien.y = game.screen_height + 10
        alien.rect.y = int(alien.y)
        game.aliens.add(alien)
    game._update(0)
    assert game.lives == 3
    assert game._shield_active
    assert not game.aliens


def test_pausing_freezes_grace_and_new_run_resets_it(gameplay):
    game = gameplay
    calm_arena(game)
    game._take_damage()
    game.state = GameState.PAUSED
    game._advance_frame(0.4)
    game._update(0.5)
    assert game._damage_grace_remaining == DAMAGE_GRACE_SECONDS
    game.state = GameState.PLAYING
    game._update(0.3)
    assert game._damage_grace_remaining == pytest.approx(0.4)
    game._init_game()
    assert game._damage_grace_remaining == 0
    game._take_damage()
    assert game.lives == 2


def test_hit_feedback_uses_game_time_and_never_mutates_shared_ship_art(gameplay, monkeypatch):
    game = gameplay
    monkeypatch.setattr(pygame.time, 'get_ticks', lambda: 10000)
    source = pygame.image.tobytes(game.fighter.image, 'RGBA')
    game._damage_grace_remaining = 0.6  # Dim phase of the protection blink.
    rendering.draw_world(game)
    dim = pygame.image.tobytes(game._canvas, 'RGB')
    rendering.draw_world(game)
    assert pygame.image.tobytes(game._canvas, 'RGB') == dim
    assert game._damage_grace_remaining == 0.6
    game._damage_grace_remaining = 0
    rendering.draw_world(game)
    assert pygame.image.tobytes(game._canvas, 'RGB') != dim
    assert pygame.image.tobytes(game.fighter.image, 'RGBA') == source
