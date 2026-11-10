"""Menu pointers preserve click coordinates and disappear throughout combat."""

from unittest.mock import Mock

import pygame
import pytest

from game_cursor import GameCursor, build_cursor
from game_state import GameState


@pytest.mark.parametrize('native', [True, False])
@pytest.mark.parametrize(('state', 'show'), [(GameState.LOADING, True), (GameState.START, True),
    (GameState.PAUSED, True), (GameState.GAME_OVER, True), (GameState.PLAYING, False), (GameState.DYING, False)])
def test_cursor_visibility_follows_the_screen(pygame_context, monkeypatch, native, state, show):
    setter = Mock(side_effect=None if native else pygame.error('unsupported'))
    visible = Mock()
    monkeypatch.setattr(pygame.mouse, 'set_cursor', setter)
    monkeypatch.setattr(pygame.mouse, 'set_visible', visible)
    cursor = GameCursor()
    assert cursor.update(state, True) is show
    visible.assert_called_once_with(show and native)
    cursor.update(state, True)
    assert visible.call_count == 1  # No repeated OS calls while a screen stays active.
    cursor.update(state, False)
    assert visible.call_args.args == (True,)
    cursor.close()


def test_software_fallback_uses_the_same_click_hotspot(pygame_context, monkeypatch):
    monkeypatch.setattr(pygame.mouse, 'set_cursor', Mock(side_effect=pygame.error('unsupported')))
    monkeypatch.setattr(pygame.mouse, 'get_focused', lambda: True)
    monkeypatch.setattr(pygame.mouse, 'get_pos', lambda: (100, 100))
    cursor = GameCursor()
    surface = pygame.Surface((200, 200))
    surface.fill((0, 0, 0))
    cursor.draw(surface, GameState.PAUSED, True)
    assert surface.get_at((100, 100))[:3] == cursor.image.get_at(cursor.HOTSPOT)[:3]
    assert surface.get_at((100, 100))[:3] != (0, 0, 0)
    for state, focused in ((GameState.PLAYING, True), (GameState.DYING, True), (GameState.PAUSED, False)):
        surface.fill((0, 0, 0))
        cursor.draw(surface, state, focused)
        assert pygame.image.tobytes(surface, 'RGB') == bytes(200 * 200 * 3)
    cursor.close()


def test_native_cursor_restores_the_previous_pointer_on_exit(pygame_context, monkeypatch):
    previous = pygame.mouse.get_cursor()
    setter, visible = Mock(), Mock()
    monkeypatch.setattr(pygame.mouse, 'set_cursor', setter)
    monkeypatch.setattr(pygame.mouse, 'set_visible', visible)
    cursor = GameCursor()
    cursor.update(GameState.PLAYING, True)
    cursor.close()
    cursor.close()
    assert setter.call_args.args == (previous,)
    assert setter.call_count == 2
    assert visible.call_args.args == (True,)


def test_game_hides_cursor_on_launch_and_returns_it_on_pause(gameplay, monkeypatch):
    cursor = Mock(wraps=gameplay._cursor)
    monkeypatch.setattr(gameplay, '_cursor', cursor)
    monkeypatch.setattr(pygame.display, 'update', lambda: None)
    gameplay.state = GameState.SHIP_SELECT
    gameplay._fade_alpha = 255
    gameplay._fade_to(GameState.PLAYING)
    gameplay._update_fade(.1, gameplay._menu_canvas)
    gameplay._present()
    assert cursor.draw.call_args.args[1:] == (GameState.PLAYING, True)
    gameplay._handle_keydown(pygame.K_ESCAPE)
    gameplay._present()
    assert cursor.draw.call_args.args[1:] == (GameState.PAUSED, True)
    gameplay._lose_focus()
    assert cursor.update.call_args.args == (GameState.PAUSED, False)


def test_cursor_artwork_has_transparent_margins_and_a_visible_tip(pygame_context):
    image = build_cursor()
    assert image.get_size() == (32, 32)
    assert image.get_at((0, 0)).a == 0
    assert image.get_at(GameCursor.HOTSPOT).a == 255
