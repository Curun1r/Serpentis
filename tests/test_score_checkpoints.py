"""Accumulate high scores during play and save only at explicit checkpoints."""

from unittest.mock import Mock

import pygame
import pytest

import combat
import main
from alien import Alien
from ball import Ball
from game import GameState
from score_manager import ScoreManager


def earn_points(game, count):
    """Resolve actual kill rewards without advancing to the next wave."""
    for _ in range(count):
        alien = Alien()
        alien.rect.center = (350, 200)
        bullet = Ball(game.fighter)
        bullet.rect.center = alien.rect.center
        game.aliens.add(alien)
        game.balls.add(bullet)
        game._ball_queue.append(bullet)
        combat._resolve_alien_hits(game)


def test_many_kills_update_hud_record_without_disk_writes(gameplay, monkeypatch):
    game = gameplay
    writes = Mock(wraps=ScoreManager._write)
    monkeypatch.setattr(ScoreManager, '_write', writes)
    earn_points(game, 30)
    assert game.game_score == game.best_score == 30
    assert ScoreManager.load() == (0, [])
    writes.assert_not_called()
    game._flush_best_score()
    assert ScoreManager.load() == (30, [])
    assert writes.call_count == 1
    game._flush_best_score()
    game._start_wave(2)
    assert writes.call_count == 1


def test_wave_checkpoint_saves_best_without_creating_a_completed_run(gameplay, monkeypatch):
    writes = Mock(wraps=ScoreManager._write)
    monkeypatch.setattr(ScoreManager, '_write', writes)
    earn_points(gameplay, 4)
    gameplay._start_wave(2)
    assert ScoreManager.load() == (4, [])
    assert writes.call_count == 1


def test_checkpoint_preserves_existing_run_metadata(gameplay):
    game = gameplay
    ScoreManager.add_entry(5, 2, 'Viper', 'hard', duration=123.75, aspect_ratio='21:9')
    game.best_score, game.score_entries = ScoreManager.load()
    game._saved_best_score = game.best_score
    original = list(game.score_entries)
    earn_points(game, 8)
    game._flush_best_score()
    assert ScoreManager.load() == (8, original)


@pytest.mark.parametrize('key', [pygame.K_p, pygame.K_ESCAPE])
def test_pausing_saves_pending_best_once(gameplay, monkeypatch, key):
    game = gameplay
    writes = Mock(wraps=ScoreManager._write)
    monkeypatch.setattr(ScoreManager, '_write', writes)
    earn_points(game, 3)
    game._handle_keydown(key)
    assert game.state == GameState.PAUSED
    assert ScoreManager.load() == (3, [])
    assert writes.call_count == 1
    game._handle_screen_action('resume')
    game._handle_keydown(key)
    assert writes.call_count == 1


@pytest.mark.parametrize('action', ['restart', 'menu'])
def test_abandoning_a_paused_run_preserves_best_without_fabricating_a_result(gameplay, action):
    game = gameplay
    earn_points(game, 6)
    game.state = GameState.PAUSED
    game._handle_screen_action(action)
    assert game.game_score == 0
    assert game.best_score == 6
    assert ScoreManager.load() == (6, [])


def test_new_round_preserves_pending_best_before_resetting_score(gameplay):
    game = gameplay
    earn_points(game, 7)
    game._init_game()
    assert game.game_score == 0
    assert game.best_score == 7
    assert ScoreManager.load() == (7, [])


@pytest.mark.parametrize('route', ['window', 'quit-action', 'interrupted-loop'])
def test_normal_exit_routes_flush_pending_record(gameplay, monkeypatch, route):
    game = gameplay
    earn_points(game, 9)
    writes = Mock(wraps=ScoreManager._write)
    monkeypatch.setattr(ScoreManager, '_write', writes)
    with pytest.raises(SystemExit):
        if route == 'window':
            monkeypatch.setattr(pygame.event, 'get', lambda: [pygame.event.Event(pygame.QUIT)])
            game._process_events()
        elif route == 'quit-action':
            game._handle_screen_action('quit')
        else:
            monkeypatch.setattr(game, '_process_events', Mock(side_effect=SystemExit))
            game.run()
    assert ScoreManager.load() == (9, [])
    assert writes.call_count == 1


def test_game_over_writes_one_final_result_and_shutdown_does_not_write_again(gameplay, monkeypatch):
    game = gameplay
    earn_points(game, 11)
    game.lives = 1
    writes = Mock(wraps=ScoreManager._write)
    monkeypatch.setattr(ScoreManager, '_write', writes)
    game._take_damage()
    best, entries = ScoreManager.load()
    assert game.state == GameState.DYING
    assert best == 11
    assert len(entries) == 1 and entries[0]['score'] == 11
    assert writes.call_count == 1
    game._flush_best_score()
    game._init_game()
    assert writes.call_count == 1


def test_final_result_keeps_a_higher_pending_best_in_the_same_write(gameplay, monkeypatch):
    game = gameplay
    # A pending all-time best must survive even when the current result is lower.
    game.best_score, game.game_score = 100, 20
    game.lives = 1
    writes = Mock(wraps=ScoreManager._write)
    monkeypatch.setattr(ScoreManager, '_write', writes)
    game._take_damage()
    best, entries = ScoreManager.load()
    assert best == 100 and entries[0]['score'] == 20
    game._flush_best_score()
    assert writes.call_count == 1


def test_failed_checkpoint_remains_pending_and_can_be_retried(gameplay, monkeypatch):
    game = gameplay
    earn_points(game, 3)
    saved = ScoreManager.save
    save = Mock(side_effect=[OSError('storage unavailable'), None])
    monkeypatch.setattr(ScoreManager, 'save', save)
    with pytest.raises(OSError, match='storage unavailable'):
        game._flush_best_score()
    assert game._saved_best_score == 0
    monkeypatch.setattr(ScoreManager, 'save', saved)
    game._flush_best_score()
    assert ScoreManager.load() == (3, [])
    assert game._saved_best_score == 3


def test_main_cleanup_closes_audio_even_when_score_checkpoint_fails(gameplay, monkeypatch):
    import game as game_module

    game = gameplay
    earn_points(game, 2)
    monkeypatch.setattr(game_module, 'Game', lambda: game)
    monkeypatch.setattr(main, '_initialize_pygame', lambda module: None)
    monkeypatch.setattr(game, 'run', Mock())
    monkeypatch.setattr(ScoreManager, 'save', Mock(side_effect=OSError('storage unavailable')))
    quit_pygame = Mock()
    monkeypatch.setattr(pygame, 'quit', quit_pygame)
    with pytest.raises(OSError, match='storage unavailable'):
        main._run(False)
    game._music.close.assert_called_once()
    quit_pygame.assert_called_once()
    assert game._saved_best_score == 0
