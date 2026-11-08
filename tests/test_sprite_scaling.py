"""Objects share one world-to-display scale, independent of aspect and resolution."""
import pygame
import pytest

from alien import Alien, ArmoredAlien, ZigzagAlien, ShooterAlien
from alien_bullet import AlienBullet
from ball import Ball
from settings_manager import Settings
from ship import SHIPS


def sprites(game):
    return [Alien(), ArmoredAlien(), ZigzagAlien(), ShooterAlien(),
            Ball(game.fighter), AlienBullet(500, 200)]


@pytest.mark.parametrize('aspect', ['auto', '16:9', '16:10', '4:3', '21:9'])
@pytest.mark.parametrize('display', [(1024, 768), (1280, 720), (1920, 1080),
                                   (2560, 1440), (3456, 2234), (3440, 1440)])
def test_sprite_sizes_and_hitboxes_survive_display_and_aspect_changes(gameplay, monkeypatch, aspect, display):
    game = gameplay
    baseline = [sprite.image.get_size() for sprite in sprites(game)]
    assert baseline[0] == (44, 44)
    assert baseline[4] == (9, 9)
    Settings.get().aspect_ratio = aspect
    game._native_mode = (3456, 2234)
    game._init_game()
    objects = sprites(game)
    assert [sprite.image.get_size() for sprite in objects] == baseline

    # Exercise the real presentation path, including repeated window changes.
    # Present the actual object images with their matching collision footprints.
    monkeypatch.setattr(pygame.display, 'update', lambda: None)
    for size in (display, (1280, 720), display):
        game.screen = pygame.Surface(size)
        game._disp_w, game._disp_h = size
        game._canvas.fill((0, 0, 0))
        for i, sprite in enumerate(objects):
            assert sprite.rect.size == sprite.image.get_size() == baseline[i]
            game._canvas.blit(sprite.image, (100 + i * 120, 240))
        game._present()
        view = game._viewport
        assert pygame.Rect((0, 0), size).contains(view)
        # Rounding the viewport may introduce less than one physical pixel of
        # difference between its two scale factors, never independent stretching.
        sx, sy = view.w / game.screen_width, view.h / game.screen_height
        assert abs(sx - sy) <= 1 / min(game.screen_width, game.screen_height)
        assert [sprite.image.get_size() for sprite in objects] == baseline

    # Future spawns and ship choices keep the same relative world sizes too.
    for ship in SHIPS:
        game._selected_ship = ship
        game._init_game()
        shot = Ball(game.fighter)
        assert shot.rect.size == (9, 9)
        assert shot.rect.centerx == pytest.approx(game.fighter.rect.centerx, abs=1)
        assert shot.height / game.screen_height == pytest.approx(9 / 720)
