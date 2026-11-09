"""Set the running window's identity before creating its first display."""

import pygame
import pytest

from game import Game


def test_runtime_icon_is_loaded_before_the_first_display(gameplay, monkeypatch):
    calls = []
    original = Game._open_display

    def icon(surface):
        calls.append('icon')
        assert surface.get_size() == (128, 128)
        assert surface.get_at((0, 0)).a == 0

    def display(self, *args, **kwargs):
        calls.append('display')
        return original(self, *args, **kwargs)

    monkeypatch.setattr(pygame.display, 'set_icon', icon)
    monkeypatch.setattr(Game, '_open_display', display)
    instance = Game()
    assert calls == ['icon', 'display']
    assert instance._window_icon.get_size() == (128, 128)


@pytest.mark.parametrize(('platform', 'frozen', 'expected'), [
    ('darwin', True, False), ('darwin', False, True), ('linux', True, True), ('win32', True, True),
])
def test_mac_bundle_preserves_its_native_icon_while_other_runs_set_the_window_icon(
        gameplay, monkeypatch, platform, frozen, expected):
    import game as game_module

    calls = []
    monkeypatch.setattr(game_module.sys, 'platform', platform)
    monkeypatch.setattr(game_module.sys, 'frozen', frozen, raising=False)
    monkeypatch.setattr(pygame.display, 'set_icon', lambda surface: calls.append(surface))
    instance = Game()
    assert bool(calls) is expected
    assert instance._window_icon.get_size() == (128, 128)
