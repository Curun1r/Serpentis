"""Records and pause navigation remain usable across world/menu proportions."""
import pygame
import pytest

from display_layout import fit_viewport
from game import GameState
from score_manager import ScoreManager
from settings_manager import Settings


def display_position(game, logical_pos, logical_size):
    view = fit_viewport((game._disp_w, game._disp_h), logical_size)
    return (view.x + round(logical_pos[0] * view.w / logical_size[0]),
            view.y + round(logical_pos[1] * view.h / logical_size[1]))


def click(game, pos):
    game._handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def test_pause_resume_click_uses_the_narrow_world_viewport(gameplay):
    game = gameplay
    Settings.get().aspect_ratio = '4:3'
    game._init_game()
    game._disp_w, game._disp_h = (1920, 1080)
    game._handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert game.state == GameState.PAUSED

    resume = game._pause._layout(960, 720)['resume_rect']
    # The right edge maps outside the button if input incorrectly uses 1280x720.
    pos = display_position(game, (resume.right - 12, resume.centery), (960, 720))
    click(game, pos)

    assert game.state == GameState.PLAYING
    game._music.resume.assert_called_once()


@pytest.mark.parametrize('origin', [GameState.START, GameState.GAME_OVER])
@pytest.mark.parametrize('return_input', ['escape', 'button'])
def test_records_return_to_the_menu_that_opened_them(gameplay, origin, return_input):
    game = gameplay
    Settings.get().aspect_ratio = '4:3'
    game._init_game()
    game._disp_w, game._disp_h = (1920, 1080)
    game.state = origin
    game.game_score = 73
    screen = game._start_screen if origin == GameState.START else game._gameover
    click(game, display_position(game, screen.leaderboard_rect.center, (1280, 720)))
    assert game._fade_next_state == GameState.LEADERBOARD

    # Complete the fade so the next input reaches the records screen.
    game.state = GameState.LEADERBOARD
    game._fade_next_state = None
    if return_input == 'escape':
        game._handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    else:
        click(game, display_position(game, game._leaderboard.back_rect.center, (1280, 720)))

    assert game._fade_next_state == origin
    assert game.game_score == 73


def test_fatal_run_records_active_time_and_its_chosen_ratio(gameplay):
    game = gameplay
    settings = Settings.get()
    settings.aspect_ratio = '4:3'
    settings.difficulty = 'hard'
    game._init_game()
    game._update(.25)
    game.state = GameState.PAUSED
    game._update(20)
    game.state = GameState.PLAYING
    game._update(.5)
    game.game_score, game.wave, game.lives = 123, 4, 1
    game._take_damage()

    best, records = ScoreManager.load()
    assert game.state == GameState.DYING
    assert best == 123
    assert len(records) == 1
    assert records[0]['duration'] == pytest.approx(.75)
    assert records[0]['aspect_ratio'] == '4:3'
    assert records[0]['difficulty'] == 'hard'
    assert (records[0]['score'], records[0]['wave'], records[0]['ship']) == (123, 4, 'Serpent')
    game._init_game()
    assert game._run_elapsed == 0
    assert ScoreManager.load()[1] == records


@pytest.mark.parametrize(('score', 'best', 'label'), [
    (400, 500, 'PERSONAL LEADERBOARD'),
    (400, 400, 'PERSONAL BEST - A FLIGHT TO REMEMBER'),
    (0, 0, 'PERSONAL LEADERBOARD'),
])
def test_results_respect_a_higher_best_from_an_unfinished_run(gameplay, monkeypatch, score, best, label):
    import screens.game_over as results_module
    game = gameplay
    game.state = GameState.GAME_OVER
    game.game_score, game.best_score = score, best
    game.score_entries = [{'score': score, 'wave': game.wave, 'ship': game._selected_ship.name}]
    labels = []
    monkeypatch.setattr(results_module, 'text', lambda surface, font, value, *args, **kwargs: labels.append(value))
    game._gameover.draw(game._menu_canvas, game._menu_context)
    assert label in labels
