"""Startup must work outside the source folder and keep player data isolated."""
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import main

ROOT = Path(__file__).resolve().parents[1]


def test_help_works_without_site_packages_or_display(tmp_path):
    result = subprocess.run([sys.executable, '-S', '-B', str(ROOT / 'main.py'), '--help'],
                            cwd=tmp_path, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert '--smoke-test' in result.stdout
    assert not (tmp_path / 'data').exists()


def test_full_startup_check_outside_project_preserves_player_data(tmp_path):
    report = tmp_path / 'startup report.json'
    protected = tmp_path / 'player saves'
    protected.mkdir()
    scores = protected / 'scores.json'
    scores.write_text('{"best_score": 1000}')
    env = dict(os.environ, SERPENTIS_DATA_DIR=str(protected))
    result = subprocess.run([sys.executable, '-B', str(ROOT / 'main.py'), '--smoke-test',
                             '--smoke-report', str(report)], cwd=tmp_path, env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    data = json.loads(report.read_text())
    assert data['ok'] is True
    assert data['save_data'] == 'passed'
    assert data['sprite_sizes'] == {'alien': [44, 44], 'player_projectile': [9, 9]}
    assert data['mini_bosses'] == ['RAIDER', 'HUNTER', 'WARDEN']
    assert set(data['screens']) == {'menu', 'hangar', 'settings', 'controls',
                                    'loading', 'gameplay', 'pause', 'results', 'leaderboard'}
    assert scores.read_text() == '{"best_score": 1000}'
    assert not (protected / 'settings.json').exists()
    assert not (tmp_path / 'data').exists()


def test_missing_audio_device_falls_back_to_silent_driver(monkeypatch):
    pygame = Mock()
    pygame.error = RuntimeError
    pygame.mixer.get_init.return_value = None
    pygame.mixer.init.side_effect = [RuntimeError('No audio device'), None]
    monkeypatch.setenv('SDL_AUDIODRIVER', 'unavailable')
    main._initialize_pygame(pygame)
    assert os.environ['SDL_AUDIODRIVER'] == 'dummy'
    pygame.mixer.set_num_channels.assert_called_once_with(16)
    pygame.mixer.set_reserved.assert_called_once_with(2)


def test_startup_failure_returns_error_and_writes_diagnostics(tmp_path, monkeypatch):
    monkeypatch.setenv('SERPENTIS_DATA_DIR', str(tmp_path))
    def fail(smoke):
        raise ImportError('missing pygame')
    monkeypatch.setattr(main, '_run', fail)
    assert main.main([]) == 1
    assert 'missing pygame' in (tmp_path / 'startup.log').read_text()


def test_failed_smoke_keeps_report_and_restores_environment(tmp_path, monkeypatch):
    protected = tmp_path / 'player saves'
    monkeypatch.setenv('SERPENTIS_DATA_DIR', str(protected))
    monkeypatch.setenv('SDL_VIDEODRIVER', 'original-driver')
    def fail(smoke):
        raise RuntimeError('startup check failed')
    monkeypatch.setattr(main, '_run', fail)
    report = tmp_path / 'failure.json'
    assert main.main(['--smoke-test', '--smoke-report', str(report)]) == 1
    data = json.loads(report.read_text())
    assert data['ok'] is False
    assert 'startup check failed' in data['error']
    assert os.environ['SERPENTIS_DATA_DIR'] == str(protected)
    assert os.environ['SDL_VIDEODRIVER'] == 'original-driver'
    assert not protected.exists()
