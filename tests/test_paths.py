"""Tests for save-data directory resolution (paths.py)."""
import paths


def _no_makedirs(monkeypatch):
    monkeypatch.setattr(paths.os, 'makedirs', lambda *a, **k: None)


def test_source_run_uses_local_data_dir(monkeypatch):
    _no_makedirs(monkeypatch)
    monkeypatch.delattr(paths.sys, 'frozen', raising=False)
    assert paths.user_data_dir() == 'data'


def test_frozen_macos(monkeypatch):
    _no_makedirs(monkeypatch)
    monkeypatch.setattr(paths.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(paths.sys, 'platform', 'darwin')
    assert paths.user_data_dir().endswith('Application Support/Serpentis')


def test_frozen_windows(monkeypatch):
    _no_makedirs(monkeypatch)
    monkeypatch.setattr(paths.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(paths.sys, 'platform', 'win32')
    monkeypatch.setenv('APPDATA', '/fake/appdata')
    assert paths.user_data_dir() == '/fake/appdata/Serpentis'


def test_frozen_linux_xdg(monkeypatch):
    _no_makedirs(monkeypatch)
    monkeypatch.setattr(paths.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(paths.sys, 'platform', 'linux')
    monkeypatch.setenv('XDG_DATA_HOME', '/fake/xdg')
    assert paths.user_data_dir() == '/fake/xdg/Serpentis'
