"""Tests for save-data directory resolution (paths.py)."""
import paths


def _no_makedirs(monkeypatch):
    monkeypatch.setattr(paths.os, 'makedirs', lambda *a, **k: None)


def test_source_run_uses_local_data_dir(monkeypatch):
    _no_makedirs(monkeypatch)
    monkeypatch.delattr(paths.sys, 'frozen', raising=False)
    assert paths.user_data_dir() == paths.os.path.join(paths.PROJECT_ROOT, 'data')


def test_frozen_macos(monkeypatch):
    _no_makedirs(monkeypatch)
    monkeypatch.setattr(paths.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(paths.sys, 'platform', 'darwin')
    assert paths.user_data_dir().endswith(paths.os.path.join('Application Support', 'Serpentis'))


def test_frozen_windows(monkeypatch):
    _no_makedirs(monkeypatch)
    monkeypatch.setattr(paths.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(paths.sys, 'platform', 'win32')
    monkeypatch.setenv('APPDATA', '/fake/appdata')
    assert paths.user_data_dir() == paths.os.path.join('/fake/appdata', 'Serpentis')


def test_frozen_linux_xdg(monkeypatch):
    _no_makedirs(monkeypatch)
    monkeypatch.setattr(paths.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(paths.sys, 'platform', 'linux')
    monkeypatch.setenv('XDG_DATA_HOME', '/fake/xdg')
    assert paths.user_data_dir() == paths.os.path.join('/fake/xdg', 'Serpentis')


def test_source_data_is_project_relative_from_another_working_folder(tmp_path, monkeypatch):
    project = tmp_path / 'project with spaces'
    monkeypatch.setattr(paths, 'PROJECT_ROOT', str(project))
    monkeypatch.delattr(paths.sys, 'frozen', raising=False)
    monkeypatch.delenv('SERPENTIS_DATA_DIR', raising=False)
    monkeypatch.chdir(tmp_path)
    directory = paths.user_data_dir()
    assert directory == str(project / 'data')
    assert (project / 'data').is_dir()
    assert not (tmp_path / 'data').exists()


def test_resource_path_uses_source_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, 'PROJECT_ROOT', str(tmp_path / 'source'))
    monkeypatch.delattr(paths.sys, 'frozen', raising=False)
    monkeypatch.chdir(tmp_path)
    assert paths.resource_path('image/heart.png') == str(tmp_path / 'source' / 'image/heart.png')


def test_frozen_resources_use_extracted_bundle(tmp_path, monkeypatch):
    monkeypatch.setattr(paths.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(paths.sys, '_MEIPASS', str(tmp_path / 'bundle'), raising=False)
    assert paths.resource_path('image/heart.png') == str(tmp_path / 'bundle' / 'image/heart.png')


def test_explicit_data_directory_overrides_source_and_bundle(tmp_path, monkeypatch):
    monkeypatch.setenv('SERPENTIS_DATA_DIR', str(tmp_path / 'isolated saves'))
    monkeypatch.setattr(paths.sys, 'frozen', True, raising=False)
    assert paths.user_data_dir() == str(tmp_path / 'isolated saves')
    assert (tmp_path / 'isolated saves').is_dir()
