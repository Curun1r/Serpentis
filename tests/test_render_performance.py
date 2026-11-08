"""Render caches stay bounded and preserve alpha, tints and interactive controls."""

import pygame
import pytest

from background import StarBackground
from settings_manager import Settings
from world_painter import WorldPainter


def fail_allocation(*args, **kwargs):
    pytest.fail('Steady-state drawing allocated another surface')


@pytest.mark.parametrize('hd', [False, True])
def test_background_reuses_cloud_artwork_and_remains_opaque(gameplay, monkeypatch, hd):
    game = gameplay
    background = game.background if hd else game._menu_background
    canvas = game._canvas if hd else game._menu_canvas
    def draw():
        if hd:
            background.draw_scaled(game._painter)
        else:
            background.draw(canvas)
    draw()
    images = dict(background._cloud_images)
    assert 0 < len(images) <= 8
    before = pygame.image.tobytes(canvas, 'RGB')
    monkeypatch.setattr(pygame, 'Surface', fail_allocation)
    background.update(0.15)
    draw()
    assert background._cloud_images == images
    assert pygame.image.tobytes(canvas, 'RGB') != before
    assert (pygame.surfarray.array_alpha(canvas) == 255).all()


def test_resolution_change_replaces_cloud_cache_instead_of_accumulating_it(gameplay):
    background = gameplay.background
    background.draw_scaled(gameplay._painter)
    old_images = list(background._cloud_images.values())
    Settings.get().resolution_index = 3
    gameplay._configure_render_target()
    background.draw_scaled(gameplay._painter)
    assert 0 < len(background._cloud_images) <= 8
    assert all(image not in old_images for image in background._cloud_images.values())


def test_precomposed_nebula_matches_separately_blended_rings(pygame_context):
    background = StarBackground(400, 300)
    background._stars = []
    background._nebulae = [[200, 150, (80, 30, 140, 14), 100, 5]]
    actual = pygame.Surface((800, 600), pygame.SRCALPHA, 32)
    expected = actual.copy()
    painter = WorldPainter(actual, (400, 300), {})
    reference = WorldPainter(expected, (400, 300), {})
    background.draw_scaled(painter)
    expected.fill((5, 5, 16))
    for step in range(4, 0, -1):
        fraction = step / 4
        reference.circle((80, 30, 140, int(14 * fraction * fraction)), (200, 150), int(100 * fraction))
    difference = abs(pygame.surfarray.array3d(actual).astype(int) - pygame.surfarray.array3d(expected).astype(int))
    # Precomposition/RLE use integer alpha approximations; keep the same subtle glow.
    assert difference.max() <= 3
    assert difference.mean() < 0.3


def test_warning_strips_match_full_frame_border_without_allocating_per_frame(gameplay, monkeypatch):
    painter = gameplay._painter
    expected = painter.surface.copy()
    color = (255, 20, 20, 83)
    layer = pygame.Surface(expected.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(layer, color, layer.get_rect(), round(18 * painter.scale))
    expected.fill((5, 5, 16))
    expected.blit(layer, (0, 0))
    painter.surface.fill((5, 5, 16))
    painter.border(color, 18)
    assert pygame.image.tobytes(painter.surface, 'RGBA') == pygame.image.tobytes(expected, 'RGBA')
    monkeypatch.setattr(pygame, 'Surface', fail_allocation)
    painter.border((255, 20, 20, 43), 18)


@pytest.mark.parametrize('color', [(25, 45, 180, 22), (255, 0, 0, 90), (30, 100, 200, 0), (30, 100, 200, 255)])
def test_tint_preserves_blending_and_alpha_without_allocating_a_frame(gameplay, monkeypatch, color):
    painter = gameplay._painter
    painter.surface.fill((93, 147, 203))
    expected = painter.surface.copy()
    layer = pygame.Surface(expected.get_size(), pygame.SRCALPHA)
    layer.fill(color)
    expected.blit(layer, (0, 0))
    monkeypatch.setattr(pygame, 'Surface', fail_allocation)
    painter.tint(color)
    difference = abs(pygame.surfarray.array3d(painter.surface).astype(int)
                     - pygame.surfarray.array3d(expected).astype(int))
    assert difference.max() <= 1
    assert (pygame.surfarray.array_alpha(painter.surface) == 255).all()


def test_pause_cache_tracks_volume_focus_hover_and_run_state(gameplay):
    game = gameplay
    game._lmouse = lambda: (-1, -1)
    pause = game._pause
    first = pause.surface(game)
    assert pause.surface(game) is first
    Settings.get().volume = 0.75
    changed = pause.surface(game)
    assert changed is not first
    assert pygame.image.tobytes(changed, 'RGBA') != pygame.image.tobytes(first, 'RGBA')
    pause.focus.select(3)
    focused = pause.surface(game)
    assert focused is not changed
    game._lmouse = lambda: pause._layout(game.screen_width, game.screen_height)['resume_rect'].center
    hovered = pause.surface(game)
    assert hovered is not focused
    game.game_score += 1
    assert pause.surface(game) is not hovered


def test_accelerated_scaled_image_preserves_its_existing_opacity(gameplay):
    painter = gameplay._painter
    image = pygame.Surface((20, 20), pygame.SRCALPHA)
    image.fill((255, 255, 255))
    image.set_alpha(60)
    painter.surface.fill((0, 0, 0))
    painter.blit(image, (100, 100))
    assert image.get_alpha() == 60
    assert painter._images[image].get_alpha() == 60
    assert 55 <= painter.surface.get_at(painter.point((105, 105))).r <= 65
