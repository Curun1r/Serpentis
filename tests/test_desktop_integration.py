"""Optional Linux installation is explicit, portable and safe for user paths."""

import configparser
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time

import pytest

import desktop_integration as desktop
import main


@pytest.fixture
def linux_download(tmp_path, monkeypatch):
    source = tmp_path / 'portable download' / 'Serpentis'
    source.parent.mkdir()
    source.write_bytes(b'portable executable')
    icon = source.parent / 'icon.png'
    icon.write_bytes(b'icon contents')
    data = tmp_path / 'Application data'
    monkeypatch.setattr(desktop.sys, 'platform', 'linux')
    monkeypatch.setattr(desktop.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(desktop.sys, 'executable', str(source))
    monkeypatch.setattr(desktop, 'resource_path', lambda name: str(icon))
    monkeypatch.setenv('XDG_DATA_HOME', str(data))
    return source, icon, data


def decode_exec_argument(value):
    """Read the two escaping layers required by the Desktop Entry specification."""
    value = value.replace('\\\\', '\\')
    assert value.startswith('"') and value.endswith('"')
    value = value[1:-1]
    decoded = []
    index = 0
    while index < len(value):
        character = value[index]
        if character == '\\':
            index += 1
            assert value[index] in '\\"`$'
            character = value[index]
        decoded.append(character)
        index += 1
    return ''.join(decoded).replace('%%', '%')


def test_install_copies_app_icon_and_menu_entry_without_changing_player_data(linux_download):
    source, icon, data = linux_download
    saves = data / 'Serpentis'
    saves.mkdir(parents=True)
    (saves / 'scores.json').write_text('{"best_score":100}')
    (saves / 'settings.json').write_text('{"volume":0.5}')
    entry_path = desktop.install_desktop_entry()
    installed = saves / 'app/Serpentis'
    assert installed.read_bytes() == source.read_bytes()
    assert os.access(installed, os.X_OK)
    installed_icon = data / 'icons/hicolor/512x512/apps' / f'{desktop.APP_ID}.png'
    assert installed_icon.read_bytes() == icon.read_bytes()
    document = configparser.ConfigParser(interpolation=None)
    document.read(entry_path, encoding='utf-8')
    entry = document['Desktop Entry']
    assert entry['Name'] == 'Serpentis'
    assert entry['Type'] == 'Application'
    assert entry['Terminal'] == 'false'
    command, separator, argument = entry['Exec'].split(' ', 2)
    assert command == '/usr/bin/env'
    assert separator == '--'
    assert decode_exec_argument(argument) == str(installed)
    assert entry['Icon'] == str(installed_icon).replace('\\', '\\\\')
    assert (saves / 'scores.json').read_text() == '{"best_score":100}'
    assert (saves / 'settings.json').read_text() == '{"volume":0.5}'


def test_download_update_and_same_path_reinstall_keep_the_executable_intact(linux_download, monkeypatch):
    source, _, data = linux_download
    desktop.install_desktop_entry()
    installed = data / 'Serpentis/app/Serpentis'
    source.write_bytes(b'new portable executable')
    desktop.install_desktop_entry()
    assert installed.read_bytes() == b'new portable executable'
    before = installed.stat().st_mtime_ns
    monkeypatch.setattr(desktop.sys, 'executable', str(installed))
    desktop.install_desktop_entry()
    assert installed.read_bytes() == b'new portable executable'
    assert installed.stat().st_mtime_ns == before


@pytest.mark.skipif(os.name != 'posix', reason='POSIX permits atomic replacement of open executable files')
def test_update_atomically_replaces_an_open_installed_file(linux_download):
    source, _, data = linux_download
    desktop.install_desktop_entry()
    installed = data / 'Serpentis/app/Serpentis'
    with installed.open('rb') as running:
        source.write_bytes(b'updated executable')
        desktop.install_desktop_entry()
        assert running.read() == b'portable executable'
    assert installed.read_bytes() == b'updated executable'


def test_relative_xdg_path_uses_the_standard_home_fallback(linux_download, monkeypatch, tmp_path):
    monkeypatch.setenv('XDG_DATA_HOME', 'relative-folder')
    monkeypatch.setattr(desktop.Path, 'home', lambda: tmp_path / 'Home')
    installed = desktop.install_desktop_entry()
    assert installed == tmp_path / 'Home/.local/share/applications' / f'{desktop.APP_ID}.desktop'


@pytest.mark.parametrize('value', ['/tmp/space folder/Serpentis', '/tmp/$HOME/Serpentis',
                                  '/tmp/quote"and`tick/Serpentis', '/tmp/back\\slash/Serpentis',
                                  '/tmp/100%/Serpentis', '/tmp/Корабель/Serpentis'])
def test_desktop_exec_preserves_reserved_characters_without_shell_expansion(value):
    path = Path(value)
    assert decode_exec_argument(desktop._exec_argument(path)) == str(path)


@pytest.mark.parametrize('value', ['bad\npath', 'bad\rpath', 'bad\tpath', 'bad=path'])
def test_invalid_menu_paths_are_rejected_before_any_installation(linux_download, monkeypatch, tmp_path, value):
    data = tmp_path / value
    monkeypatch.setenv('XDG_DATA_HOME', str(data))
    with pytest.raises(desktop.DesktopInstallError):
        desktop.install_desktop_entry()
    assert not (tmp_path / 'Application data').exists()


def test_source_cli_rejects_installation_without_starting_pygame(monkeypatch, capsys):
    monkeypatch.setattr(desktop.sys, 'frozen', False, raising=False)
    monkeypatch.setattr(main, '_run', lambda smoke: pytest.fail('Installer started the game'))
    assert main.main(['--install-desktop']) == 1
    assert 'standalone Linux download' in capsys.readouterr().err


def test_installation_cli_succeeds_without_starting_pygame(linux_download, monkeypatch, capsys):
    monkeypatch.setattr(main, '_run', lambda smoke: pytest.fail('Installer started the game'))
    assert main.main(['--install-desktop']) == 0
    assert 'application menu' in capsys.readouterr().out


def test_menu_installation_cannot_be_combined_with_smoke_mode(monkeypatch):
    monkeypatch.setattr(main, '_run', lambda smoke: pytest.fail('Installer started the game'))
    with pytest.raises(SystemExit) as result:
        main.main(['--install-desktop', '--smoke-test'])
    assert result.value.code == 2


@pytest.mark.skipif(sys.platform != 'linux' or shutil.which('gio') is None,
                    reason='Desktop-entry launch verification uses Linux GIO when available')
@pytest.mark.parametrize('directory', ['normal', 'Application data', '$HOME', '100%', '"quoted"',
                                     'back\\slash', '`ticks`', 'Корабель',
                                     'Data $HOME 100% "quoted" back\\slash `ticks`'])
def test_real_desktop_parser_launches_literal_special_character_paths(
        linux_download, monkeypatch, tmp_path, directory):
    source, _, _ = linux_download
    launched = tmp_path / 'launched.txt'
    source.write_text('#!/bin/sh\nprintf launched > ' + shlex.quote(str(launched)) + '\n')
    data = tmp_path / directory
    monkeypatch.setenv('XDG_DATA_HOME', str(data))
    entry = desktop.install_desktop_entry()
    result = subprocess.run(['gio', 'launch', str(entry)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    deadline = time.monotonic() + 3
    while not launched.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert launched.read_text() == 'launched'
