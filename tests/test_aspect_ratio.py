"""Chosen proportions affect world bounds while menu/input layouts stay usable."""
import pygame
import pytest

import config
from display_layout import fit_viewport, game_canvas_size
from game import GameState
from settings_manager import Settings


@pytest.mark.parametrize(('aspect', 'width'), [('16:9', 1280), ('16:10', 1152),
                                             ('4:3', 960), ('21:9', 1680), ('auto', 1109)])
def test_new_round_applies_ratio_without_stretching_ship(gameplay, aspect, width):
    game = gameplay
    original_ship_size = game.fighter.image.get_size()
    game._native_mode = (3024, 1964)
    Settings.get().aspect_ratio = aspect
    assert game._canvas.get_size() == (1920, 1080)
    game._init_game()
    render_width, render_height = game._canvas.get_size()
    assert render_width >= 1920 and render_height >= 1080
    assert render_width / render_height == pytest.approx(width / 720, abs=.001)
    assert (config.SCREEN_WIDTH, config.SCREEN_HEIGHT) == (width, 720)
    assert game.fighter.image.get_size() == original_ship_size
    assert game.fighter.rect.centerx == pytest.approx(width / 2, abs=1)
    assert game._menu_canvas.get_size() == (1280, 720)
    assert game._menu_context.screen_width == 1280
    assert all(0 <= alien.rect.left < width for alien in game.aliens)


@pytest.mark.parametrize('aspect', ['4:3', '16:10', '21:9'])
def test_pointer_follows_world_and_menu_viewports(gameplay, aspect):
    game = gameplay
    Settings.get().aspect_ratio = aspect
    game._init_game()
    game._disp_w, game._disp_h = (1920, 1200)
    view = fit_viewport((1920, 1200), game._canvas.get_size())
    assert game._lpos(view.center) == pytest.approx((game.screen_width / 2, 360), abs=1)
    game.state = GameState.PAUSED
    assert game._lpos(view.center) == pytest.approx((game.screen_width / 2, 360), abs=1)
    game.state = GameState.SETTINGS
    view = fit_viewport((1920, 1200))
    assert game._lpos(view.center) == pytest.approx((640, 360), abs=1)
    assert game._lpos((view.centerx, view.top - 1)) == (-1, -1)


def test_auto_ratio_tracks_monitor_even_with_manual_window_size(gameplay, monkeypatch):
    import game as game_module
    game = gameplay
    settings = Settings.get()
    settings.auto_resolution = False
    settings.aspect_ratio = 'auto'
    monkeypatch.setattr(pygame.display, 'get_num_displays', lambda: 2)
    monkeypatch.setattr(game_module, 'get_native_resolution', lambda index: (3440, 1440))
    game._handle_event(pygame.event.Event(pygame.WINDOWDISPLAYCHANGED, display_index=1))
    game._init_game()
    assert (game.screen_width, game.screen_height) == (1720, 720)
    assert game._canvas.get_size() == (2580, 1080)


@pytest.mark.parametrize(('native', 'expected'), [((1080, 1920), (960, 720)),
                                                ((5120, 1440), (2560, 720))])
def test_unusual_auto_displays_keep_playfield_usable(native, expected):
    assert game_canvas_size('auto', native) == expected
