"""Keep SDL native-event processing in a child process to catch fatal crashes."""
import os
from pathlib import Path
import subprocess
import sys
import textwrap


def test_settings_survives_real_sdl_events_and_clean_shutdown(tmp_path):
    script = textwrap.dedent('''
        import sys
        from unittest.mock import Mock
        import pygame
        import paths
        paths.user_data_dir = lambda: sys.argv[1]
        pygame.init()
        pygame.mixer.set_num_channels(16)
        pygame.mixer.set_reserved(2)
        import game
        from settings_manager import Settings
        Settings.get().auto_resolution = False
        Settings.get().resolution_index = 1
        game.MusicPlayer = Mock
        instance = game.Game()
        for _ in range(60):
            instance.state = game.GameState.SETTINGS
            instance._settings.draw(instance._menu_canvas, instance._menu_context)
            pygame.event.pump()
            for event in pygame.event.get():
                if event.type != pygame.QUIT:
                    instance._handle_event(event)
            instance._present(instance._menu_canvas)
            instance.state = game.GameState.START
            instance._start_screen.draw(instance._menu_canvas, instance._menu_context)
            instance._present(instance._menu_canvas)
        pygame.quit()
        print('clean shutdown')
    ''')
    env = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy',
               SDL_RENDER_DRIVER='software', PYGAME_HIDE_SUPPORT_PROMPT='1')
    result = subprocess.run([sys.executable, '-B', '-c', script, str(tmp_path)],
                            cwd=Path(__file__).resolve().parents[1], env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, f'SDL process exited {result.returncode}: {result.stderr}'
    assert 'clean shutdown' in result.stdout
