"""Regressions for input, damage, and rewards across game-state transitions."""
import pygame
import pytest

from alien import Alien
from alien_bullet import AlienBullet
from ball import Ball
from boss import Boss, MiniBoss
from game import GameState
from powerup import HeartPowerUp, ShieldPowerUp
from score_manager import ScoreManager


def spawn_boss(game, mini):
    game._start_wave(3 if mini else 5)
    game._boss_warning_timer = 0
    game._pending_boss_wave = 0
    enemy = MiniBoss(game.wave) if mini else Boss(game.wave)
    if mini:
        enemy.update(1.0)  # Finish its slide-in before testing combat collisions.
        game.mini_boss = enemy
    else:
        game.boss = enemy
    return enemy


@pytest.mark.parametrize('key', [
    pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d,
    pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s,
])
def test_releasing_movement_while_paused_stops_ship(gameplay, key):
    game = gameplay
    game.fighter.y = 300
    game._handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))
    game._handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p))
    game._handle_event(pygame.event.Event(pygame.KEYUP, key=key))
    game._handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p))
    before = game.fighter.x, game.fighter.y
    game.fighter.update(1 / 60)
    assert game.state == GameState.PLAYING
    assert (game.fighter.x, game.fighter.y) == before


def test_two_lethal_bullets_record_one_result_and_stop_the_frame(gameplay):
    game = gameplay
    game.lives = 1
    game.alien_bullets.add(*(AlienBullet(*game.fighter.rect.center) for _ in range(2)))
    game._update(0)

    assert game.state == GameState.DYING
    assert game.lives == 0
    assert game.wave == 1
    _, entries = ScoreManager.load()
    assert len(entries) == 1
    assert entries[0]['wave'] == 1
    assert len(game.alien_bullets) == 1
    game._take_damage()
    game._update(0)
    assert game.lives == 0
    assert len(ScoreManager.load()[1]) == 1


@pytest.mark.parametrize('state', [GameState.PAUSED, GameState.DYING, GameState.GAME_OVER])
def test_damage_outside_play_does_not_change_lives_or_record_results(gameplay, state):
    game = gameplay
    game.lives = 1
    game.state = state
    game._take_damage()
    assert game.lives == 1
    assert game.state == state
    assert ScoreManager.load() == (0, [])


@pytest.mark.parametrize('mini', [False, True], ids=['boss', 'mini-boss'])
def test_fatal_boss_contact_cannot_collect_a_heart(gameplay, mini):
    game = gameplay
    enemy = spawn_boss(game, mini)
    game.lives = 1
    game.fighter.rect.center = enemy.rect.center
    game.fighter.x, game.fighter.y = game.fighter.rect.topleft
    heart = HeartPowerUp(*game.fighter.rect.center)
    game.powerups.add(heart)
    wave = game.wave
    game._update(0)

    assert game.state == GameState.DYING
    assert game.lives == 0
    assert heart in game.powerups
    assert game.wave == wave
    assert ScoreManager.load()[1][0]['wave'] == wave


def test_fatal_last_escaping_enemy_does_not_advance_wave(gameplay):
    game = gameplay
    game.aliens.empty()
    alien = Alien(index=0)
    alien.y = game.screen_height + alien.rect.height
    alien.rect.y = int(alien.y)
    game.aliens.add(alien)
    game.lives = 1
    game._update(0)
    assert game.state == GameState.DYING
    assert game.wave == 1
    assert ScoreManager.load()[1][0]['wave'] == 1


@pytest.mark.parametrize('mini', [False, True], ids=['boss', 'mini-boss'])
@pytest.mark.parametrize('weapon', ['bullet', 'shield'])
def test_boss_defeat_awards_score_and_collectible_heart_once(gameplay, mini, weapon):
    game = gameplay
    enemy = spawn_boss(game, mini)
    enemy.hp = 1
    wave = game.wave
    if weapon == 'bullet':
        bullet = Ball(game.fighter)
        bullet.rect.center = enemy.hit_rect.center
        game.balls.add(bullet)
        game._ball_queue.append(bullet)
    else:
        game._shield_active = True
        game.fighter.rect.center = enemy.rect.center
        game.fighter.x, game.fighter.y = game.fighter.rect.topleft

    update = game._update_mini_boss if mini else game._update_boss
    update(0)
    update(0)

    assert game.boss is None and game.mini_boss is None
    assert game.wave == wave + 1
    assert game.game_score == enemy.SCORE
    assert ScoreManager.load()[0] == enemy.SCORE
    hearts = [pu for pu in game.powerups if isinstance(pu, HeartPowerUp)]
    assert len(hearts) == 1
    game.lives = 1
    game.fighter.rect.center = (game.screen_width // 2, game.screen_height - 100)
    game.fighter.x, game.fighter.y = game.fighter.rect.topleft
    hearts[0].rect.center = game.fighter.rect.center
    hearts[0].y = float(hearts[0].rect.y)
    game._update(0)
    assert game.lives == 2
    assert hearts[0] not in game.powerups


def test_last_enemy_drop_survives_wave_and_new_game_clears_it(gameplay, monkeypatch):
    game = gameplay
    game.aliens.empty()
    alien = Alien(index=0)
    alien.y = 200
    alien.rect.y = 200
    game.aliens.add(alien)
    bullet = Ball(game.fighter)
    bullet.rect.center = alien.rect.center
    bullet.x, bullet.y = bullet.rect.topleft
    game.balls.add(bullet)
    drop = ShieldPowerUp(*alien.rect.center)
    monkeypatch.setattr(game, '_maybe_drop_powerup', lambda *args: game.powerups.add(drop))
    game._update(0)
    assert game.wave == 2
    assert drop in game.powerups
    game._init_game()
    assert len(game.powerups) == 0


@pytest.mark.parametrize(('shield', 'expected_lives'), [(False, 1), (True, 2)])
def test_nonlethal_hits_and_single_use_shield_keep_their_behavior(gameplay, shield, expected_lives):
    game = gameplay
    game.lives = 3
    game._shield_active = shield
    game.alien_bullets.add(*(AlienBullet(*game.fighter.rect.center) for _ in range(2)))
    game._update(0)
    assert game.state == GameState.PLAYING
    assert game.lives == expected_lives
    assert not game._shield_active
    assert ScoreManager.load() == (0, [])
