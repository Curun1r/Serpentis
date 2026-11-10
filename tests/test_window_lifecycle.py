"""App switching must preserve the run, release input and require an explicit resume."""

from unittest.mock import Mock

import pygame
import pytest

import display_layout
from game import GameState
from music import MusicPlayer
from score_manager import ScoreManager
from settings_manager import Settings


def event(game, kind, **attributes):
    game._handle_event(pygame.event.Event(kind, **attributes))


@pytest.mark.parametrize('kind', [pygame.WINDOWFOCUSLOST, pygame.WINDOWMINIMIZED])
def test_switching_away_pauses_and_clears_movement_without_losing_the_run(gameplay, kind):
    game = gameplay
    game._fade_alpha, game._fade_dir = 0, 0
    game.game_score = game.best_score = 12
    game.fighter.move_left()
    game.fighter.move_up()
    game.fighter.dash()
    cooldown = game.fighter.dash_cooldown_ratio
    fighter = game.fighter
    position = fighter.rect.copy()
    remaining = game._damage_grace_remaining = .5
    event(game, kind)
    assert not game._has_focus
    assert game.state == GameState.PAUSED
    assert not any((fighter.is_moving_left, fighter.is_moving_right,
                    fighter.is_moving_up, fighter.is_moving_down, fighter.is_dashing))
    assert fighter.dash_cooldown_ratio == cooldown
    assert ScoreManager.load() == (12, [])
    event(game, pygame.WINDOWRESTORED)
    assert not game._has_focus  # Restoring a window does not necessarily give it keyboard focus.
    event(game, pygame.WINDOWFOCUSGAINED)
    game._advance_frame(.1)
    assert game._has_focus and game.state == GameState.PAUSED
    assert game.fighter is fighter and fighter.rect == position
    assert game.game_score == 12 and game._damage_grace_remaining == remaining
    game._music.resume.assert_not_called()
    event(game, pygame.KEYDOWN, key=pygame.K_RETURN)
    assert game.state == GameState.PLAYING
    fighter.update(.1)
    assert fighter.rect == position
    game._music.resume.assert_called_once()


def test_focus_loss_during_launch_cannot_start_a_background_flight(gameplay):
    game = gameplay
    game.state = GameState.SHIP_SELECT
    game._confirm_ship()
    assert game._fade_next_state == GameState.PLAYING
    event(game, pygame.WINDOWFOCUSLOST)
    assert game._fade_next_state == GameState.PAUSED
    event(game, pygame.WINDOWFOCUSGAINED)
    game._update_fade(1, game._menu_canvas)
    assert game.state == GameState.PAUSED and game._fade_next_state is None
    game._music.resume.assert_not_called()


@pytest.mark.parametrize('state', [GameState.START, GameState.SETTINGS, GameState.DYING, GameState.PAUSED])
def test_focus_events_preserve_other_screens_and_pause_music(gameplay, state):
    game = gameplay
    game.state = state
    event(game, pygame.WINDOWFOCUSLOST)
    game._music.pause.assert_called_once()
    event(game, pygame.WINDOWFOCUSGAINED)
    assert game.state == state
    assert game._music.resume.call_count == (0 if state == GameState.PAUSED else 1)


def test_focus_loss_finishes_slider_drags_and_ignores_background_input(gameplay):
    game = gameplay
    game._pause._vol_dragging = game._settings._vol_dragging = True
    event(game, pygame.WINDOWFOCUSLOST)
    assert not game._pause._vol_dragging and not game._settings._vol_dragging
    event(game, pygame.KEYDOWN, key=pygame.K_RETURN)
    event(game, pygame.MOUSEBUTTONDOWN, button=1, pos=(640, 360))
    assert game.state == GameState.PAUSED and not game.balls


@pytest.mark.parametrize(('platform', 'modifier'), [('darwin', pygame.KMOD_GUI),
                                                   ('win32', pygame.KMOD_ALT),
                                                   ('linux', pygame.KMOD_ALT)])
def test_platform_minimize_shortcut_preserves_settings(gameplay, monkeypatch, platform, modifier):
    import game as game_module

    game = gameplay
    settings = Settings.get()
    settings.fullscreen = True
    settings.fps_index = 0
    before = (settings.fullscreen, settings.fps_index, game.fighter, game.wave)
    monkeypatch.setattr(game_module.sys, 'platform', platform)
    iconify = Mock(return_value=True)
    monkeypatch.setattr(pygame.display, 'iconify', iconify)
    event(game, pygame.KEYDOWN, key=pygame.K_m, mod=modifier)
    assert game.state == GameState.PAUSED and not game._has_focus
    assert (settings.fullscreen, settings.fps_index, game.fighter, game.wave) == before
    iconify.assert_called_once()


@pytest.mark.parametrize('modifier', [pygame.KMOD_GUI, pygame.KMOD_ALT,
                                    pygame.KMOD_GUI | pygame.KMOD_SHIFT])
def test_system_tab_does_not_change_menu_focus_or_launch_actions(gameplay, modifier):
    game = gameplay
    game.state = GameState.START
    before = game._start_screen._focus.index
    event(game, pygame.KEYDOWN, key=pygame.K_TAB, mod=modifier)
    event(game, pygame.KEYDOWN, key=pygame.K_RETURN, mod=modifier)
    assert game._start_screen._focus.index == before and game._fade_next_state is None


@pytest.mark.parametrize('supported', [True, False])
def test_pause_menu_minimize_and_unsupported_window_manager(gameplay, monkeypatch, supported):
    game = gameplay
    game._pause_game()
    iconify = Mock(return_value=supported)
    monkeypatch.setattr(pygame.display, 'iconify', iconify)
    rect = game._pause._layout(game.screen_width, game.screen_height)['minimize_rect']
    action = game._pause.handle_click(rect.center, game)
    assert action == 'minimize'
    game._handle_screen_action(action)
    assert game.state == GameState.PAUSED and game._has_focus is not supported
    iconify.assert_called_once()


def test_async_fullscreen_resize_refreshes_surface_and_mouse_mapping(gameplay, monkeypatch):
    surface = pygame.Surface((1728, 1084))
    monkeypatch.setattr(pygame.display, 'get_surface', lambda: surface)
    Settings.get().fill_screen = True
    event(gameplay, pygame.WINDOWSIZECHANGED, x=1728, y=1084)
    assert gameplay.screen is surface
    assert (gameplay._disp_w, gameplay._disp_h) == surface.get_size()
    assert gameplay._lpos((864, 542)) == (gameplay.screen_width // 2, gameplay.screen_height // 2)


def test_background_loop_stops_rendering_simulation_and_transitions(gameplay, monkeypatch):
    game = gameplay
    caps = []
    batches = iter([[pygame.event.Event(pygame.WINDOWFOCUSLOST)], [],
                    [pygame.event.Event(pygame.WINDOWFOCUSGAINED)]])

    class Finished(Exception):
        pass

    def tick(cap):
        caps.append(cap)
        if len(caps) == 4:
            raise Finished
        return .02

    monkeypatch.setattr(game._frame_limiter, 'tick', tick)
    monkeypatch.setattr(pygame.event, 'get', lambda: next(batches))
    for method in ('_advance_frame', '_update_fade', '_present'):
        monkeypatch.setattr(game, method, Mock())
    with pytest.raises(Finished):
        game.run()
    assert caps == [Settings.get().fps, 15, 15, Settings.get().fps]
    game._advance_frame.assert_called_once()
    game._update_fade.assert_called_once()
    game._present.assert_called_once()
    assert game.state == GameState.PAUSED


@pytest.mark.parametrize('driver', ['cocoa', 'windows', 'x11', 'wayland'])
def test_desktop_fullscreen_without_exclusive_capture_or_extra_scaling(pygame_context, monkeypatch, driver):
    fullscreen = Mock(spec=pygame.Surface)
    fullscreen.get_flags.return_value = pygame.FULLSCREEN
    calls = []
    monkeypatch.setattr(pygame.display, 'get_driver', lambda: driver)
    monkeypatch.setattr(pygame.display, 'set_mode', lambda size, flags, **kw: calls.append((size, flags, kw)))
    monkeypatch.setattr(pygame.display, 'toggle_fullscreen', Mock())
    monkeypatch.setattr(pygame.display, 'get_surface', lambda: fullscreen)
    for method in ('set_grab', 'set_keyboard_grab'):
        monkeypatch.setattr(pygame.event, method, Mock())
    assert display_layout.open_window((1920, 1080), True, 1) is fullscreen
    assert calls == [((1920, 1080), 0, {'display': 1, 'vsync': 0})]
    pygame.display.toggle_fullscreen.assert_called_once()
    pygame.event.set_grab.assert_called_once_with(False)
    pygame.event.set_keyboard_grab.assert_called_once_with(False)


def test_window_manager_without_desktop_toggle_falls_back_safely(pygame_context, monkeypatch):
    calls = []
    monkeypatch.setattr(pygame.display, 'get_driver', lambda: 'x11')
    monkeypatch.setattr(pygame.display, 'set_mode', lambda size, flags, **kw: calls.append(flags) or pygame_context)
    monkeypatch.setattr(pygame.display, 'toggle_fullscreen', Mock(side_effect=pygame.error('unsupported')))
    display_layout.open_window((1920, 1080), True, 0)
    assert calls == [0, pygame.FULLSCREEN]


def test_pending_music_stays_paused_when_background_synthesis_finishes():
    # Model a track completing after the game has lost focus, without starting a thread.
    player = MusicPlayer.__new__(MusicPlayer)
    channel = Mock()
    sound = Mock()
    sound.play.return_value = channel
    player._channel = None
    player._volume = .4
    player._tracks = {'battle': sound}
    player.pause()
    player._switch('battle')
    channel.pause.assert_called_once()
    player.resume()
    channel.unpause.assert_called_once()


def test_returning_to_menu_resumes_its_music_after_a_pause(gameplay):
    gameplay._pause_game()
    gameplay._handle_screen_action('menu')
    gameplay._music.play_menu.assert_called()
    gameplay._music.resume.assert_called_once()
