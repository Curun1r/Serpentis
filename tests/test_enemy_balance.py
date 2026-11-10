"""Smaller standard aliens retain matching hitboxes and offer rarer bonuses."""

from unittest.mock import Mock

import pygame
import pytest

import alien as alien_module
import combat
from alien import Alien, ArmoredAlien, ShooterAlien, ZigzagAlien
from ball import Ball
from powerup import ShieldPowerUp, SlowTimePowerUp, TripleShotPowerUp


@pytest.mark.parametrize('scale', [.5, .65, 1.25])
def test_standard_alien_reduction_respects_configured_scale_and_hitbox(gameplay, monkeypatch, scale):
    raw = pygame.Surface((68, 52), pygame.SRCALPHA)
    raw.fill((150, 20, 160, 255))
    original = pygame.image.tobytes(raw, 'RGBA')
    monkeypatch.setattr(alien_module.Assets, 'get_image', lambda path: raw)
    monkeypatch.setattr(alien_module, 'ALIEN_SCALE', scale)
    enemy = Alien()
    expected = tuple(round(int(dimension * scale) * .8) for dimension in raw.get_size())
    assert enemy.image.get_size() == enemy.rect.size == expected
    assert (enemy.width, enemy.height) == expected
    enemy.take_hit()
    enemy.update(.01)
    assert enemy.image is enemy._img_flash
    assert enemy.image.get_size() == enemy.rect.size == expected
    assert pygame.image.tobytes(raw, 'RGBA') == original


@pytest.mark.parametrize(('enemy_type', 'size'), [(ArmoredAlien, (42, 42)),
                                                  (ZigzagAlien, (44, 40)),
                                                  (ShooterAlien, (42, 42))])
def test_special_enemy_models_and_hitboxes_keep_their_existing_size(gameplay, enemy_type, size):
    enemy = enemy_type()
    assert enemy.image.get_size() == enemy.rect.size == size
    enemy.take_hit()
    enemy.update(.01)
    assert enemy.image.get_size() == enemy.rect.size == size


@pytest.mark.parametrize('enemy_type', [Alien, ArmoredAlien, ZigzagAlien, ShooterAlien])
@pytest.mark.parametrize('roll', [.099, .10, .249, .25])
def test_enemy_drop_chance_thresholds(gameplay, monkeypatch, enemy_type, roll):
    draws = iter((roll, .5))
    monkeypatch.setattr(combat.random, 'random', lambda: next(draws))
    chance = .10 if enemy_type is Alien else .25
    gameplay._maybe_drop_powerup(250, 300, enemy_type.DROP_CHANCE)
    assert len(gameplay.powerups) == int(roll < chance)


@pytest.mark.parametrize(('roll', 'powerup_type'), [(0, TripleShotPowerUp), (.399, TripleShotPowerUp),
                                                   (.4, SlowTimePowerUp), (.719, SlowTimePowerUp),
                                                   (.72, ShieldPowerUp), (.999, ShieldPowerUp)])
def test_bonus_type_distribution_is_preserved_after_a_successful_drop(gameplay, monkeypatch, roll, powerup_type):
    draws = iter((0, roll))
    monkeypatch.setattr(combat.random, 'random', lambda: next(draws))
    gameplay._maybe_drop_powerup(250, 300, Alien.DROP_CHANCE)
    assert len(gameplay.powerups) == 1
    bonus = next(iter(gameplay.powerups))
    assert isinstance(bonus, powerup_type) and bonus.rect.midtop == (250, 300)


@pytest.mark.parametrize('enemy_type', [Alien, ArmoredAlien, ZigzagAlien, ShooterAlien])
def test_projectile_kill_uses_the_defeated_enemy_drop_chance(gameplay, monkeypatch, enemy_type):
    game = gameplay
    game.aliens.empty()
    enemy = enemy_type()
    enemy.hp = 1
    enemy.rect.center = (250, 200)
    game.aliens.add(enemy)
    bullet = Ball(game.fighter)
    bullet.rect.center = enemy.rect.center
    game.balls.add(bullet)
    game._ball_queue.append(bullet)
    # A 15% roll is above the standard's 10% chance and below the specials' 25%.
    monkeypatch.setattr(combat.random, 'random', lambda: .15)
    monkeypatch.setattr(game._effects, 'spawn_particles', Mock())
    combat._resolve_alien_hits(game)
    combat._resolve_alien_hits(game)
    assert not enemy.alive() and not bullet.alive()
    assert game.game_score == enemy.SCORE
    assert len(game.powerups) == (0 if enemy_type is Alien else 1)
