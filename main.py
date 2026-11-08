"""Application entry point and bounded startup check for desktop builds."""
import argparse
from contextlib import nullcontext
import json
import os
from pathlib import Path
import sys
import tempfile
import traceback

from app_info import APP_NAME, APP_VERSION


def _initialize_pygame(pygame):
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    if pygame.mixer.get_init() is None:
        # A missing audio device should not prevent playing the game.
        try:
            pygame.mixer.init()
        except pygame.error:
            pygame.mixer.quit()
            os.environ['SDL_AUDIODRIVER'] = 'dummy'
            pygame.mixer.init()
    pygame.mixer.set_num_channels(16)
    pygame.mixer.set_reserved(2)


def _smoke_test(game):
    """Exercise bundled images, menus, gameplay, audio, and writable save data."""
    import pygame
    from game import GameState
    from score_manager import ScoreManager
    from settings_manager import Settings

    game._lmouse = lambda: (-1, -1)
    rendered = []
    for name, screen in [('menu', game._start_screen), ('hangar', game._ship_screen),
                         ('settings', game._settings), ('controls', game._controls)]:
        game.background.draw(game._canvas)
        screen.draw(game._canvas, game)
        rendered.append(name)
    game._draw_loading()
    rendered.append('loading')
    game.state = GameState.PLAYING
    game._music.play_battle()
    game._shoot()
    # Report real asset dimensions so release checks catch different defaults
    # in a frozen build that does not include a developer's config.json.
    sprite_sizes = {'alien': list(next(iter(game.aliens)).image.get_size()),
                    'player_projectile': list(next(iter(game.balls)).image.get_size())}
    for _ in range(12):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise RuntimeError('Window closed during startup check')
            game._handle_event(event)
        game._update(1 / 60)
        game._draw()
        game._present()
    rendered.append('gameplay')
    game._pause.draw(game._canvas, game)
    rendered.append('pause')
    Settings.get().save()
    ScoreManager.add_entry(1, game.wave, game._selected_ship.name)
    best, game.score_entries = ScoreManager.load()
    if best != 1 or len(game.score_entries) != 1:
        raise RuntimeError('Save-data check failed')
    game.game_score = 1
    game._gameover.draw(game._canvas, game)
    rendered.append('results')
    game._leaderboard.draw(game._menu_canvas, game._menu_context)
    rendered.append('leaderboard')
    return {'ok': True, 'application': APP_NAME, 'version': APP_VERSION,
            'screens': rendered, 'save_data': 'passed', 'sprite_sizes': sprite_sizes}


def _run(smoke):
    import pygame
    game = None
    try:
        _initialize_pygame(pygame)
        from game import Game
        if smoke:
            from settings_manager import Settings
            settings = Settings.get()
            settings.auto_resolution = False
            settings.resolution_index = 1  # deterministic 1280x720 headless display
            settings.fullscreen = False
        game = Game()
        if smoke:
            return _smoke_test(game)
        game.run()
        return {'ok': True}
    finally:
        try:
            if game is not None:
                game._music.close()
        finally:
            pygame.quit()


def _startup_error(details):
    from paths import user_data_dir
    try:
        log = Path(user_data_dir()) / 'startup.log'
        log.write_text(details, encoding='utf-8')
        message = f'Could not start {APP_NAME}. Details: {log}'
    except OSError:
        message = f'Could not start {APP_NAME}.\n{details}'
    if sys.stderr is not None:
        print(message, file=sys.stderr)


def main(argv=None):
    parser = argparse.ArgumentParser(description=f'{APP_NAME} space shooter')
    parser.add_argument('--smoke-test', action='store_true', help='Check startup without opening a visible window')
    parser.add_argument('--smoke-report', type=Path, help='Write the startup-check result as JSON')
    args = parser.parse_args(argv)
    if args.smoke_report and not args.smoke_test:
        parser.error('--smoke-report requires --smoke-test')
    previous_env = {key: os.environ.get(key) for key in (
        'SDL_VIDEODRIVER', 'SDL_AUDIODRIVER', 'SDL_RENDER_DRIVER', 'SERPENTIS_DATA_DIR')}
    context = tempfile.TemporaryDirectory(prefix='serpentis-smoke-') if args.smoke_test else nullcontext()
    result = {'ok': False, 'application': APP_NAME, 'version': APP_VERSION}
    try:
        with context as save_dir:
            if args.smoke_test:
                os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy',
                                  SDL_RENDER_DRIVER='software', SERPENTIS_DATA_DIR=save_dir)
            try:
                result = _run(args.smoke_test)
            except Exception:
                result['error'] = traceback.format_exc()
                _startup_error(result['error'])
    finally:
        if args.smoke_test:
            for key, value in previous_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
    if args.smoke_report:
        args.smoke_report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    if args.smoke_test and sys.stdout is not None:
        print(json.dumps(result))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
