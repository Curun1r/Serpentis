"""Native fullscreen output, fill/input mapping, and actual HD drawing."""

import pygame
import pytest

from display_layout import fit_viewport, render_canvas_size
from game import GameState
from settings_manager import Settings


@pytest.mark.parametrize("native", [(3024, 1964), (3456, 2234), (3440, 1440)])
def test_fullscreen_always_uses_desktop_framebuffer_without_sdl_scaling(gameplay, monkeypatch, native):
    import game as game_module

    settings = Settings.get()
    settings.fullscreen = True
    settings.auto_resolution = False
    settings.resolution_index = 1
    monkeypatch.setattr(game_module, "get_native_resolution", lambda index: native)
    calls = []

    def set_mode(size, flags, **kwargs):
        calls.append((size, flags))
        return pygame.Surface(size)

    monkeypatch.setattr(pygame.display, "set_mode", set_mode)
    gameplay._apply_resolution()
    assert calls == [(native, pygame.FULLSCREEN)]
    assert gameplay.screen.get_size() == native
    assert gameplay._canvas.get_width() >= 1920
    assert gameplay._canvas.get_height() >= 1080


@pytest.mark.parametrize("state", [GameState.PLAYING, GameState.PAUSED, GameState.START, GameState.SETTINGS])
def test_fill_covers_every_pixel_and_mouse_uses_logical_coordinates(gameplay, monkeypatch, state):
    game = gameplay
    settings = Settings.get()
    settings.aspect_ratio = "16:10"
    settings.fill_screen = True
    game._init_game()
    game.state = state
    game.screen = pygame.Surface((1200, 800))
    game._disp_w, game._disp_h = game.screen.get_size()
    frame = game._canvas if state in (GameState.PLAYING, GameState.PAUSED) else game._menu_canvas
    frame.fill((255, 255, 255))
    monkeypatch.setattr(pygame.display, "update", lambda: None)
    game._present(frame)
    assert game._viewport == game.screen.get_rect()
    for point in ((0, 0), (1199, 0), (0, 799), (1199, 799)):
        # SDL's integer smoothscaler may round white down by one or two units.
        assert min(game.screen.get_at(point)[:3]) > 245
    width = 1152 if state in (GameState.PLAYING, GameState.PAUSED) else 1280
    assert game._lpos((600, 400)) == (width // 2, 360)
    assert game._lpos((1199, 799))[0] >= width - 2


def test_hd_resolution_changes_preserve_run_and_hitboxes(gameplay):
    game = gameplay
    game.game_score = 125
    fighter = game.fighter
    bounds = fighter.rect.copy()
    alien_sizes = [alien.image.get_size() for alien in game.aliens]
    Settings.get().resolution_index = 3  # 2560x1440
    game._configure_render_target()
    game._draw()
    assert game._canvas.get_size() == (2560, 1440)
    assert game.game_score == 125
    assert game.fighter is fighter and fighter.rect == bounds
    assert [alien.image.get_size() for alien in game.aliens] == alien_sizes
    assert game._painter._fonts[game.game_font].get_height() > game.game_font.get_height()


def test_fill_preference_can_switch_back_to_fit_and_persists(gameplay):
    settings = Settings.get()
    settings.fill_screen = True
    screen = gameplay._settings
    screen.handle_click(screen._layout(1280)["fill_rect"].center, gameplay)
    assert settings.fill_screen is False
    assert Settings().fill_screen is False
    assert fit_viewport((1200, 800), (1280, 720), fill=True) == pygame.Rect(0, 0, 1200, 800)
    assert fit_viewport((1200, 800), (1280, 720)).h < 800


@pytest.mark.parametrize(
    ("world", "resolution", "render"),
    [
        ((1280, 720), (1280, 720), (1920, 1080)),
        ((1152, 720), (1920, 1080), (1920, 1200)),
        ((960, 720), (1920, 1080), (1920, 1440)),
        ((1280, 720), (2560, 1440), (2560, 1440)),
    ],
)
def test_hd_framebuffer_keeps_world_ratio_and_covers_selected_resolution(world, resolution, render):
    assert render_canvas_size(world, resolution) == render


def test_fading_text_does_not_change_the_cached_opaque_label(gameplay):
    painter = gameplay._painter
    args = (gameplay.game_font, "OPAQUE", (255, 255, 255), (200, 200))
    painter.surface.fill((0, 0, 0))
    painter.text(*args, alpha=40)
    faded = pygame.image.tobytes(painter.surface, "RGB")
    painter.surface.fill((0, 0, 0))
    painter.text(*args)
    opaque = pygame.image.tobytes(painter.surface, "RGB")
    assert opaque != faded
    assert all(label.get_alpha() in (None, 255) for label in painter._labels.values())
