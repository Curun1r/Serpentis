"""Gameplay rules: movement, weapons, collisions, damage and rewards.

Functions operate on the active run owned by Game. Screen transitions and wave
creation stay with the controller; temporary visuals are owned by VisualEffects.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

import pygame

from alien import ShooterAlien
from alien_bullet import AlienBullet
from ball import Ball
from boss import Boss, MiniBoss
from explosion import Explosion
from game_state import GameState
from powerup import HeartPowerUp, ShieldPowerUp, SlowTimePowerUp, TripleShotPowerUp
from score_manager import ScoreManager
from settings_manager import Settings
from ui_fx import DamageNumber

if TYPE_CHECKING:
    from game import Game


def shoot(game: Game) -> None:
    ship = game._selected_ship
    if game._triple_shot_timer > 0:
        if ship.default_shots >= 2:
            # Heavy firepower ship: 4-shot spread
            angles = [-24, -8, 8, 24]
            limit = 12
        else:
            angles = [-18, 0, 18]
            limit = 9
    else:
        angles = [-10, 10] if ship.default_shots == 2 else [0]
        limit = ship.max_bullets

    while len(game._ball_queue) + len(angles) > limit:
        if game._ball_queue:
            game._ball_queue.pop(0).kill()
        else:
            break

    for ang in angles:
        ball = Ball(game.fighter, angle_deg=ang)
        game.balls.add(ball)
        game._ball_queue.append(ball)
    game.shoot_sound.play()


def remove_projectile(game: Game, ball: Ball) -> None:
    try:
        game._ball_queue.remove(ball)
    except ValueError:
        pass


def update(game: Game, dt: float) -> None:
    """Advance one active frame; stop immediately when lethal contact ends a run."""
    if game.state != GameState.PLAYING:
        return

    _advance_timers(game, dt)
    _move_actors(game, dt)
    for update_enemy in (update_boss, update_mini_boss):
        update_enemy(game, dt)
        if game.state != GameState.PLAYING:
            return

    _remove_offscreen_projectiles(game)
    _collect_powerups(game)
    _fire_alien_weapons(game)
    _resolve_alien_hits(game)
    _resolve_projectile_hits(game)
    if game.state != GameState.PLAYING:
        return
    _resolve_alien_contacts(game)
    if game.state == GameState.PLAYING:
        _advance_wave_if_cleared(game)


def _advance_timers(game: Game, dt: float) -> None:
    game._run_elapsed += dt
    if game._wave_banner_timer > 0:
        game._wave_banner_timer -= dt
    if game._triple_shot_timer > 0:
        game._triple_shot_timer -= dt
    if game._slow_time_timer > 0:
        game._slow_time_timer -= dt

    # Boss/mini-boss warning countdown
    if game._boss_warning_timer > 0:
        game._boss_warning_timer -= dt
        if game._boss_warning_timer <= 0:
            game._boss_warning_timer = 0.0
            pw = game._pending_boss_wave
            game._pending_boss_wave = 0
            if pw > 0:
                game.boss = Boss(pw)
            elif pw < 0:
                game.mini_boss = MiniBoss(-pw)


def _move_actors(game: Game, dt: float) -> None:
    slow = 0.30 if game._slow_time_timer > 0 else 1.0

    game.fighter.update(dt)
    game._effects.spawn_engine_trail(game.fighter, game._selected_ship)
    game._effects.update_engine_trail(dt)
    game.powerups.update(dt)
    game.aliens.update(dt * slow)
    game.balls.update(dt)
    game.explosions.update(dt)
    game.alien_bullets.update(dt * slow)
    game._effects.update(dt)


def _remove_offscreen_projectiles(game: Game) -> None:
    for ball in list(game.balls):
        if ball.is_out_of_screen():
            ball.kill()
            remove_projectile(game, ball)

    for ab in list(game.alien_bullets):
        if ab.is_off_screen():
            ab.kill()


def _collect_powerups(game: Game) -> None:
    for pu in list(game.powerups):
        if pu.is_off_screen():
            pu.kill()
            continue
        if pu.rect.colliderect(game.fighter.rect):
            apply_powerup(game, pu)
            pu.kill()


def _fire_alien_weapons(game: Game) -> None:
    for alien in game.aliens:
        if isinstance(alien, ShooterAlien):
            for cx, cy in alien.drain_shots():
                game.alien_bullets.add(AlienBullet(cx, cy))


def _resolve_alien_hits(game: Game) -> None:
    hits = pygame.sprite.groupcollide(game.balls, game.aliens, True, False)
    for ball in hits.keys():
        remove_projectile(game, ball)
    for aliens_hit in hits.values():
        for alien in aliens_hit:
            if not alien.alive():
                continue
            cx, cy = alien.rect.center
            if alien.take_hit():
                alien.kill()
                game.explosions.add(Explosion(cx, cy))
                game._effects.spawn_particles(cx, cy)
                game._maybe_drop_powerup(cx, cy)
                game.game_score += alien.SCORE
                if game.game_score > game.best_score:
                    game.best_score = game.game_score
                    ScoreManager.save(game.best_score)
                game._effects.spawn_damage_number(cx, cy, f"+{alien.SCORE}", DamageNumber.COLOR_SCORE, scale=1.05)
            else:
                game._effects.spawn_particles(cx, cy, count=5, colors=[(90, 140, 255), (160, 195, 255)])
                game._effects.spawn_damage_number(cx, cy, "HIT", DamageNumber.COLOR_HIT, scale=0.85, lifetime=0.55)
            game.hit_sound.play()


def _resolve_projectile_hits(game: Game) -> None:
    for ab in list(game.alien_bullets):
        if ab.rect.colliderect(game.fighter.rect):
            ab.kill()
            if game._shield_active:
                break_shield(game)
            else:
                game._take_damage()
            if game.state != GameState.PLAYING:
                return


def _resolve_alien_contacts(game: Game) -> None:
    for alien in list(game.aliens):
        reached = alien.has_reached_fighter(game.fighter)
        off = alien.is_off_screen()
        if reached or off:
            alien.kill()
            # Shield absorbs direct collision but NOT enemies that slip past
            if reached and game._shield_active:
                break_shield(game)
                game._effects.spawn_particles(
                    alien.rect.centerx, alien.rect.centery, count=10, colors=[(70, 150, 255), (180, 220, 255)]
                )
            else:
                game._take_damage()
            if game.state != GameState.PLAYING:
                return


def _advance_wave_if_cleared(game: Game) -> None:
    if (
        game.boss is None
        and game.mini_boss is None
        and len(game.aliens) == 0
        and game._pending_boss_wave == 0
        and game._boss_warning_timer <= 0
    ):
        game._start_wave(game.wave + 1)


def update_boss(game: Game, dt: float) -> None:
    if not game.boss:
        return

    game.boss.update(dt)

    for shot in game.boss.drain_shots():
        game.alien_bullets.add(AlienBullet(*shot))

    for ball in list(game.balls):
        if ball.rect.colliderect(game.boss.hit_rect):
            ball.kill()
            remove_projectile(game, ball)
            if game.boss.take_hit():
                defeat_boss(game, game.boss)
                return
            else:
                game._effects.spawn_damage_number(
                    ball.rect.centerx, ball.rect.centery, "HIT", DamageNumber.COLOR_BOSS, scale=0.9, lifetime=0.6
                )
                game.hit_sound.play()

    if game.boss and game.boss.rect.colliderect(game.fighter.rect):
        if game._shield_active:
            break_shield(game)
            # Shield rams the boss — deal damage to it
            if game.boss.take_hit(2):
                defeat_boss(game, game.boss)
        else:
            game._take_damage()


def update_mini_boss(game: Game, dt: float) -> None:
    if not game.mini_boss:
        return
    game.mini_boss.update(dt)

    for shot in game.mini_boss.drain_shots():
        game.alien_bullets.add(AlienBullet(*shot))

    for ball in list(game.balls):
        if ball.rect.colliderect(game.mini_boss.hit_rect):
            ball.kill()
            remove_projectile(game, ball)
            if game.mini_boss.take_hit():
                defeat_boss(game, game.mini_boss)
                return
            else:
                game._effects.spawn_damage_number(
                    ball.rect.centerx, ball.rect.centery, "HIT", (0, 220, 170), scale=0.9, lifetime=0.6
                )
                game.hit_sound.play()

    if game.mini_boss and game.mini_boss.rect.colliderect(game.fighter.rect):
        if game._shield_active:
            break_shield(game)
            if game.mini_boss.take_hit(2):
                defeat_boss(game, game.mini_boss)
        else:
            game._take_damage()


def defeat_boss(game: Game, enemy: Boss | MiniBoss) -> None:
    """Resolve a boss kill once, regardless of whether a bullet or shield hit it."""
    if enemy is not game.boss and enemy is not game.mini_boss:
        return
    mini = enemy is game.mini_boss
    cx, cy = enemy.rect.center
    spread = 35 if mini else 55
    for _ in range(4 if mini else 7):
        ox = random.randint(-spread, spread)
        oy = random.randint(-spread, spread)
        game.explosions.add(Explosion(cx + ox, cy + oy))
    colors = (
        [(0, 220, 170), (0, 180, 140), (255, 215, 0), (200, 255, 230)]
        if mini
        else [(255, 100, 255), (200, 50, 255), (255, 215, 0), (255, 80, 80)]
    )
    game._effects.spawn_particles(cx, cy, count=25 if mini else 40, colors=colors)
    game.game_score += enemy.SCORE
    if game.game_score > game.best_score:
        game.best_score = game.game_score
        ScoreManager.save(game.best_score)
    game._effects.spawn_damage_number(
        cx, cy, f"+{enemy.SCORE}", DamageNumber.COLOR_SCORE, scale=1.15 if mini else 1.3, lifetime=1.1 if mini else 1.2
    )
    game.hit_sound.play()
    game.powerups.add(HeartPowerUp(cx, cy))
    if mini:
        game.mini_boss = None
    else:
        game.boss = None
    game._start_wave(game.wave + 1, extra_delay=1.5 if mini else 2.0)


def maybe_drop_powerup(game: Game, cx: int, cy: int) -> None:
    if random.random() > 0.25:
        return
    roll = random.random()
    if roll < 0.40:
        pu = TripleShotPowerUp(cx, cy)
    elif roll < 0.72:
        pu = SlowTimePowerUp(cx, cy)
    else:
        pu = ShieldPowerUp(cx, cy)
    game.powerups.add(pu)


def apply_powerup(game: Game, pu: pygame.sprite.Sprite) -> None:
    if isinstance(pu, TripleShotPowerUp):
        game._triple_shot_timer = TripleShotPowerUp.DURATION
    elif isinstance(pu, ShieldPowerUp):
        game._shield_active = True
    elif isinstance(pu, SlowTimePowerUp):
        game._slow_time_timer = SlowTimePowerUp.DURATION
    elif isinstance(pu, HeartPowerUp):
        game.lives = min(game.lives + 1, Settings.get().starting_lives + 2)
    game.powerup_sound.play()


def take_damage(game: Game) -> None:
    if game.state != GameState.PLAYING:
        return
    if game._shield_active:
        break_shield(game)
        return
    game.lives -= 1
    game.flash_timer = 20
    game._effects.shake_frames = 5
    game.lose_life_sound.play()
    # Floating damage label above the ship
    fx, fy = game.fighter.rect.centerx, game.fighter.rect.top - 10
    game._effects.spawn_damage_number(fx, fy, "-1 LIFE", DamageNumber.COLOR_PLAYER, scale=1.1, lifetime=1.0)
    if game.lives <= 0:
        # Trigger death animation before showing game over
        cx, cy = game.fighter.rect.centerx, game.fighter.rect.centery
        for _ in range(10):
            ox = random.randint(-40, 40)
            oy = random.randint(-40, 40)
            game.explosions.add(Explosion(cx + ox, cy + oy))
        game._effects.spawn_particles(
            cx, cy, count=60, colors=[(255, 220, 50), (255, 120, 0), (255, 60, 0), (255, 255, 200)]
        )
        game._effects.shake_frames = 18
        game.state = GameState.DYING
        game._death_timer = 1.8
        game.score_entries = ScoreManager.add_entry(
            game.game_score,
            game.wave,
            game._selected_ship.name,
            Settings.get().difficulty,
            duration=game._run_elapsed,
            aspect_ratio=game._run_aspect,
        )
        game.best_score = max(game.best_score, game.game_score)


def break_shield(game: Game) -> None:
    """Deactivate shield, trigger flash/shake, and play the break sound."""
    game._shield_active = False
    game.flash_timer = 6
    game._effects.shake_frames = 2
    game.shield_break_sound.play()
