"""Transitions dim complete frames uniformly and reuse their render resources."""

import pygame
import pytest

from game import GameState
from settings_manager import Settings


@pytest.mark.parametrize("opacity", [32, 96, 160, 224, 255])
def test_fade_dims_text_and_background_uniformly_without_changing_alpha(gameplay, opacity):
    game = gameplay
    frame = pygame.Surface((420, 140), pygame.SRCALPHA, 32)
    frame.fill((40, 65, 95))
    frame.blit(game.game_font.render("PLAY / SETTINGS", True, (235, 241, 255)), (25, 35))
    before = pygame.surfarray.array3d(frame).astype(float)
    game._fade_alpha, game._fade_dir = opacity, 0
    game._update_fade(0, frame)
    after = pygame.surfarray.array3d(frame).astype(float)
    expected = before * (255 - opacity) / 255
    assert abs(after - expected).max() <= 1
    assert (pygame.surfarray.array_alpha(frame) == 255).all()


def test_fade_does_not_allocate_a_full_frame_surface(gameplay, monkeypatch):
    frame = pygame.Surface((1920, 1080), pygame.SRCALPHA, 32)
    frame.fill((40, 65, 95))
    gameplay._fade_alpha, gameplay._fade_dir = 128, 0

    def unexpected_allocation(*args, **kwargs):
        pytest.fail("Fade allocated a new full-frame surface")

    monkeypatch.setattr(pygame, "Surface", unexpected_allocation)
    gameplay._update_fade(0, frame)


def test_retry_reuses_hd_framebuffer_and_fonts_but_resets_run(gameplay):
    game = gameplay
    canvas, painter = game._canvas, game._painter
    fonts = dict(painter._fonts)
    game.game_score = 123
    game._init_game()
    assert game._canvas is canvas
    assert game._painter is painter
    assert painter._fonts == fonts
    assert game.game_score == 0
    Settings.get().resolution_index = 3
    game._configure_render_target()
    assert game._painter is not painter


@pytest.mark.parametrize("state", [GameState.START, GameState.PLAYING])
def test_present_reuses_opaque_scaling_buffer(gameplay, monkeypatch, state):
    game = gameplay
    game.state = state
    game.screen = pygame.Surface((1200, 800))
    game._disp_w, game._disp_h = game.screen.get_size()
    frame = game._menu_canvas if state == GameState.START else game._canvas
    frame.fill((235, 241, 255))
    monkeypatch.setattr(pygame.display, "update", lambda: None)
    game._present(frame)
    buffer = game._presentation_canvas
    game._present(frame)
    assert game._presentation_canvas is buffer
    assert buffer.get_alpha() is None
    assert frame.get_alpha() == 255
    assert min(game.screen.get_at(game._viewport.center)[:3]) > 225


def test_menu_frames_stay_opaque_through_a_complete_transition(gameplay):
    game = gameplay
    game.state = GameState.START
    game._fade_alpha = 0
    game._fade_to(GameState.SETTINGS)
    seen = set()
    for _ in range(80):
        frame = game._advance_frame(1 / 60)
        game._update_fade(1 / 60, frame)
        assert (pygame.surfarray.array_alpha(frame) == 255).all()
        seen.add(game.state)
    assert {GameState.START, GameState.SETTINGS} <= seen
