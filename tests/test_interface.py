"""Menu navigation and display/input behavior through the game controller."""
import pygame
import pytest

from display_layout import fit_viewport
from game import GameState
from settings_manager import Settings


def key(game, value):
    game._handle_event(pygame.event.Event(pygame.KEYDOWN, key=value))


@pytest.mark.parametrize(('steps', 'target'), [(1, GameState.SHIP_SELECT),
                                              (2, GameState.SETTINGS), (3, GameState.CONTROLS)])
def test_main_menu_keyboard_actions(gameplay, steps, target):
    game = gameplay
    game.state = GameState.START
    for _ in range(steps):
        key(game, pygame.K_DOWN)
    key(game, pygame.K_RETURN)
    assert game._fade_next_state == target


def test_controls_return_to_menu(gameplay):
    gameplay.state = GameState.CONTROLS
    key(gameplay, pygame.K_ESCAPE)
    assert gameplay._fade_next_state == GameState.START


def test_ship_selection_keyboard_browse_and_launch(gameplay):
    game = gameplay
    game.state = GameState.SHIP_SELECT
    key(game, pygame.K_RIGHT)
    key(game, pygame.K_RETURN)
    assert game._selected_ship.id == 'viper'
    assert game._fade_next_state == GameState.PLAYING


def test_pause_keyboard_restart_and_resume(gameplay):
    game = gameplay
    key(game, pygame.K_ESCAPE)
    key(game, pygame.K_RETURN)
    assert game.state == GameState.PLAYING
    key(game, pygame.K_ESCAPE)
    game._music.reset_mock()
    game.game_score = 90
    key(game, pygame.K_DOWN)
    key(game, pygame.K_RETURN)
    assert game.game_score == 0
    assert game._fade_next_state == GameState.PLAYING
    game._music.resume.assert_called_once()


def test_results_keyboard_retry(gameplay):
    game = gameplay
    game.state = GameState.GAME_OVER
    game.game_score = 90
    key(game, pygame.K_RETURN)
    assert game.game_score == 0
    assert game._fade_next_state == GameState.PLAYING


def test_settings_keyboard_volume_and_display_choices(gameplay, monkeypatch):
    game = gameplay
    game.state = GameState.SETTINGS
    settings = Settings.get()
    key(game, pygame.K_DOWN)
    key(game, pygame.K_RIGHT)
    assert settings.volume == pytest.approx(.35)
    key(game, pygame.K_DOWN)
    calls = []
    monkeypatch.setattr(game, '_apply_resolution', lambda: calls.append(settings.auto_resolution))
    settings.auto_resolution = True
    key(game, pygame.K_RIGHT)
    assert not settings.auto_resolution and settings.resolution_index == 0
    assert calls == [False]
    key(game, pygame.K_LEFT)
    assert settings.auto_resolution
    assert calls == [False, True]


def test_right_mouse_button_does_not_activate_menu(gameplay):
    game = gameplay
    game.state = GameState.START
    game._handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3,
                                         pos=game._start_screen.play_rect.center))
    assert game._fade_next_state is None


@pytest.mark.parametrize('size', [(1024, 768), (3024, 1964), (3440, 1440)])
def test_mouse_mapping_accounts_for_letterboxing_and_ignores_bars(gameplay, size):
    game = gameplay
    game._viewport = fit_viewport(size)
    game._disp_w, game._disp_h = size
    view = game._viewport
    assert game._lpos(view.center) == pytest.approx((640, 360), abs=1)
    assert game._lpos(view.topleft) == (0, 0)
    assert game._lpos((view.right, view.bottom)) == (-1, -1)
    assert game._lpos((view.left - 1, view.centery)) == (-1, -1)
    assert game._lpos((view.centerx, view.top - 1)) == (-1, -1)


def test_letterbox_click_does_not_shoot(gameplay):
    gameplay._viewport = fit_viewport((1024, 768))
    gameplay._disp_w, gameplay._disp_h = (1024, 768)
    gameplay._handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(512, 10)))
    assert len(gameplay.balls) == 0


@pytest.mark.parametrize('fullscreen', [False, True])
def test_auto_display_uses_current_monitor_and_keeps_desktop_mode(gameplay, monkeypatch, fullscreen):
    import game as game_module
    game = gameplay
    settings = Settings.get()
    settings.auto_resolution = True
    settings.fullscreen = fullscreen
    monkeypatch.setattr(game_module, 'get_native_resolution', lambda index: (3024, 1964))
    monkeypatch.setattr(pygame.display, 'get_num_displays', lambda: 2)
    calls = []
    def set_mode(size, flags, **kwargs):
        calls.append((size, flags, kwargs['display']))
        return pygame.Surface(size)
    monkeypatch.setattr(pygame.display, 'set_mode', set_mode)
    game._apply_resolution(1)
    assert calls[0][0] == ((3024, 1964) if fullscreen else (2944, 1844))
    assert calls[0][2] == 1
    assert bool(calls[0][1] & pygame.FULLSCREEN) == fullscreen
    assert pygame.Rect((0, 0), game.screen.get_size()).contains(game._viewport)


def test_removed_monitor_falls_back_to_primary_display(gameplay, monkeypatch):
    game = gameplay
    monkeypatch.setattr(pygame.display, 'get_num_displays', lambda: 1)
    calls = []
    def set_mode(size, flags, **kwargs):
        calls.append(kwargs['display'])
        return pygame.Surface(size)
    monkeypatch.setattr(pygame.display, 'set_mode', set_mode)
    game._apply_resolution(4)
    assert calls == [0]


def test_auto_display_follows_monitor_change_once(gameplay, monkeypatch):
    import game as game_module
    game = gameplay
    Settings.get().auto_resolution = True
    monkeypatch.setattr(pygame.display, 'get_num_displays', lambda: 2)
    monkeypatch.setattr(game_module, 'get_native_resolution', lambda index: (2560, 1440))
    calls = []
    def apply(index):
        calls.append(index)
        game._display_index = index
        game._native_mode = (2560, 1440)
    monkeypatch.setattr(game, '_apply_resolution', apply)
    event = pygame.event.Event(pygame.WINDOWDISPLAYCHANGED, display_index=1)
    game._handle_event(event)
    game._handle_event(event)
    assert calls == [1]


def test_present_keeps_bars_black_during_camera_shake(gameplay, monkeypatch):
    game = gameplay
    game.screen = pygame.Surface((1024, 768))
    game._disp_w, game._disp_h = game.screen.get_size()
    game._viewport = fit_viewport(game.screen.get_size())
    game._canvas.fill((255, 255, 255))
    game._shake_ox, game._shake_oy = 10, -10
    monkeypatch.setattr(pygame.display, 'update', lambda: None)
    game._present()
    assert game.screen.get_at((512, 95))[:3] == (0, 0, 0)
    assert game.screen.get_at((512, 672))[:3] == (0, 0, 0)
    assert min(game.screen.get_at((512, 360))[:3]) > 245
