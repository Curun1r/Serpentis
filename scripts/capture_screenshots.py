"""Render README previews with isolated demonstration data, without a window.

Run from any directory: python /path/to/Serpentis/scripts/capture_screenshots.py
"""

import os
from pathlib import Path
import random
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _demo_records():
    return [dict(score=score, wave=wave, ship=ship, difficulty=mode,
                 date='08.11.2026', duration=duration, aspect_ratio='16:10')
            for score, wave, ship, mode, duration in [
                (128, 16, 'Viper', 'normal', 724), (112, 15, 'Serpent', 'hard', 680),
                (97, 13, 'Hydra', 'normal', 592), (86, 11, 'Viper', 'hard', 520),
                (72, 10, 'Serpent', 'normal', 475), (61, 8, 'Hydra', 'easy', 408),
                (48, 7, 'Viper', 'normal', 354), (35, 5, 'Serpent', 'easy', 282),
                (24, 4, 'Hydra', 'normal', 190), (16, 3, 'Viper', 'normal', 142),
            ]]


def _capture(game, state, filename, output):
    import pygame

    game.state = state
    frame = game._advance_frame(0)
    game._present(frame)
    pygame.image.save(game.screen, str(output / filename))


def _gameplay_scene(game):
    import pygame
    from alien import Alien, ArmoredAlien, ShooterAlien, ZigzagAlien
    from ball import Ball
    from ship import SHIPS

    game._selected_ship = SHIPS[1]
    game._init_game()
    game.wave, game.game_score, game.lives = 4, 24, 3
    game._wave_banner_timer = 0
    game.fighter.x, game.fighter.y = game.screen_width * 0.58, 570
    game.fighter.rect.topleft = round(game.fighter.x), round(game.fighter.y)
    enemies = [Alien(), ArmoredAlien(), ZigzagAlien(), ShooterAlien(), Alien(), ArmoredAlien()]
    for i, enemy in enumerate(enemies):
        enemy.x, enemy.y = game.screen_width * (0.12 + i * 0.14), 145 + i % 3 * 85
        enemy.rect.topleft = round(enemy.x), round(enemy.y)
    game.aliens = pygame.sprite.Group(*enemies)
    for y in (275, 390, 505):
        bullet = Ball(game.fighter)
        bullet.y = y
        bullet.rect.y = y
        game.balls.add(bullet)
    for _ in range(25):
        game.fighter.is_moving_up = True
        game._effects.spawn_engine_trail(game.fighter, game._selected_ship)
        game._effects.update_engine_trail(1 / 60)
    game.fighter.is_moving_up = False


def capture(output: Path) -> None:
    os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy',
                      SDL_RENDER_DRIVER='software', PYGAME_HIDE_SUPPORT_PROMPT='1')
    with tempfile.TemporaryDirectory(prefix='serpentis-preview-') as folder:
        os.environ['SERPENTIS_DATA_DIR'] = folder
        import pygame
        from app_info import APP_VERSION
        from boss import Boss
        from game import Game, GameState
        from main import _initialize_pygame
        from mini_boss import MiniBoss
        from alien_bullet import AlienBullet
        from settings_manager import Settings

        random.seed(17)
        _initialize_pygame(pygame)
        settings = Settings.get()
        settings.fullscreen, settings.auto_resolution = False, True
        settings.aspect_ratio, settings.fill_screen = '16:10', True
        settings.show_fps, settings.fps_index = False, 2
        settings.difficulty = 'normal'
        settings.volume = 0.65
        with patch('game.MusicPlayer'):
            game = Game()
        try:
            output.mkdir(parents=True, exist_ok=True)
            game.screen = pygame.Surface((1600, 1000))
            game._disp_w, game._disp_h = game.screen.get_size()
            game._lmouse = lambda: (-1, -1)
            game._fade_alpha = 0
            game.score_entries = _demo_records()
            game.best_score = game.score_entries[0]['score']
            game._menu_background.update(2.0)
            settings.fullscreen = True
            for state, filename in [(GameState.START, 'menu.png'), (GameState.SHIP_SELECT, 'ship_select.png'),
                                    (GameState.SETTINGS, 'settings.png'), (GameState.CONTROLS, 'controls.png'),
                                    (GameState.LEADERBOARD, 'leaderboard.png')]:
                _capture(game, state, filename, output)

            _gameplay_scene(game)
            _capture(game, GameState.PLAYING, 'gameplay.png', output)
            _capture(game, GameState.PAUSED, 'pause.png', output)

            game.aliens.empty()
            game.wave, game.game_score = 10, 72
            game.boss = Boss(10)
            game.boss.hp = round(game.boss.max_hp * 0.6)
            game.boss.update(0.5)
            for age in (1.3, 0.65):
                game.boss._queue_shots()
                for shot in game.boss.drain_shots():
                    bullet = AlienBullet(*shot)
                    bullet.update(age)
                    game.alien_bullets.add(bullet)
            _capture(game, GameState.PLAYING, 'boss.png', output)

            game.boss = None
            game.alien_bullets.empty()
            game.wave, game.game_score = 13, 97
            enemy = game.mini_boss = MiniBoss(13)
            enemy.update(1.0)
            for _ in range(240):
                enemy.update(1 / 60, game.fighter.rect.center)
                game.alien_bullets.update(1 / 60)
                game.alien_bullets.add(*(AlienBullet(*shot) for shot in enemy.drain_shots()))
            _capture(game, GameState.PLAYING, 'mini_boss.png', output)
            game.mini_boss = None
            _capture(game, GameState.GAME_OVER, 'game_over.png', output)
            print(f'Rendered 10 Serpentis {APP_VERSION} previews at 1600 x 1000 in {output}')
        finally:
            game._music.close()
            pygame.quit()


if __name__ == '__main__':
    capture(ROOT / 'screenshots')
