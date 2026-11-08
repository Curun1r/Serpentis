"""Component boundaries preserve run state, visual lifetime and transitions."""
from copy import deepcopy

import pygame

from game import GameState
import rendering


def test_new_round_clears_all_transient_effects(gameplay):
    game = gameplay
    effects = game._effects
    effects.spawn_particles(300, 300)
    effects.spawn_damage_number(300, 300, '+10', (255, 215, 50))
    game.fighter.move_left()
    effects.spawn_engine_trail(game.fighter, game._selected_ship)
    effects.shake_frames = 5
    assert effects.particles and effects.damage_numbers and effects.engine_particles

    game._init_game()

    assert effects.particles == effects.damage_numbers == effects.engine_particles == []
    assert effects.advance_shake() == (0, 0)


def test_effect_updates_expire_particles_trails_and_labels(gameplay):
    effects = gameplay._effects
    effects.spawn_particles(300, 300)
    effects.spawn_damage_number(300, 300, 'HIT', (255, 255, 255))
    gameplay.fighter.move_up()
    effects.spawn_engine_trail(gameplay.fighter, gameplay._selected_ship)
    effects.update(1.0)
    effects.update_engine_trail(1.0)
    assert effects.particles == effects.damage_numbers == effects.engine_particles == []


def test_drawing_world_does_not_advance_simulation_or_visual_timers(gameplay, monkeypatch):
    game = gameplay
    monkeypatch.setattr(pygame.time, 'get_ticks', lambda: 12345)
    game.flash_timer = 6
    game._effects.shake_frames = 2
    game._effects.spawn_particles(400, 400)
    before = deepcopy(game._effects.particles)
    fighter_before = game.fighter.rect.copy()

    rendering.draw_world(game)
    first_frame = pygame.image.tobytes(game._canvas, 'RGB')
    rendering.draw_world(game)

    assert pygame.image.tobytes(game._canvas, 'RGB') == first_frame
    assert game._effects.particles == before
    assert game.fighter.rect == fighter_before
    assert (game.flash_timer, game._effects.shake_frames) == (6, 2)


def test_controller_advances_visual_frame_counters_after_drawing(gameplay):
    game = gameplay
    game.flash_timer = 2
    game._effects.shake_frames = 2
    game._draw()
    assert (game.flash_timer, game._effects.shake_frames) == (1, 1)
    game._draw()
    assert (game.flash_timer, game._effects.shake_frames) == (0, 0)
    game._draw()
    assert (game._shake_ox, game._shake_oy) == (0, 0)


def test_loading_switch_and_fade_keep_their_frame_order(gameplay):
    game = gameplay
    game.state = GameState.LOADING
    game._loading_timer = .01
    frame = game._advance_frame(.02)
    assert game.state == GameState.START
    assert frame is game._menu_canvas

    game._fade_next_state = None
    game._fade_alpha = 254
    game._fade_to(GameState.SHIP_SELECT)
    game._update_fade(.02, frame)
    assert game.state == GameState.SHIP_SELECT
    assert game._fade_next_state is None
    assert game._fade_dir == -1
    assert frame.get_at(frame.get_rect().center)[:3] == (0, 0, 0)
