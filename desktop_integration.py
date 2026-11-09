"""Opt-in application-menu installation for the standalone Linux download."""

import os
from pathlib import Path
import shutil
import sys
import tempfile

from app_info import APP_NAME
from paths import resource_path

APP_ID = 'io.github.curun1r.serpentis'


class DesktopInstallError(RuntimeError):
    """The portable Linux application cannot install its menu entry."""


def _entry_string(value: str) -> str:
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise DesktopInstallError('The installation path contains unsupported control characters.')
    return value.replace('\\', '\\\\')


def _exec_argument(path: Path) -> str:
    """Apply Exec quoting, then the desktop-file string escaping layer."""
    value = str(path)
    if '=' in value:
        raise DesktopInstallError('Application-menu installation paths cannot contain an equals sign.')
    escaped = ''.join('\\' + character if character in '\\"`$' else character for character in value)
    return '"' + _entry_string(escaped.replace('%', '%%')) + '"'


def _atomic_install(destination: Path, source: Path | bytes, mode: int) -> None:
    """Replace files without truncating a currently running Linux executable."""
    if isinstance(source, Path) and source.resolve() == destination.resolve():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.serpentis-', delete=False) as output:
            temporary = Path(output.name)
            if isinstance(source, Path):
                with source.open('rb') as incoming:
                    shutil.copyfileobj(incoming, output)
            else:
                output.write(source)
            output.flush()
            os.fsync(output.fileno())
        temporary.chmod(mode)
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def install_desktop_entry() -> Path:
    """Install only this app and icon into the current user's XDG data folder."""
    if sys.platform != 'linux' or not getattr(sys, 'frozen', False):
        raise DesktopInstallError('Use --install-desktop with the standalone Linux download.')
    configured = os.environ.get('XDG_DATA_HOME', '')
    data_home = Path(configured) if configured and Path(configured).is_absolute() else Path.home() / '.local/share'
    executable = data_home / APP_NAME / 'app' / APP_NAME
    icon = data_home / 'icons/hicolor/512x512/apps' / f'{APP_ID}.png'
    desktop = data_home / 'applications' / f'{APP_ID}.desktop'
    # Validate/escape every generated value before modifying the installation.
    # GLib checks argv[0] exists before expanding desktop field codes. A literal
    # '%' in the app path is encoded as '%%', so use the stable env executable
    # as argv[0] and expand the quoted application path only as its argument.
    # env executes that absolute argument directly; no shell evaluates the path.
    command = '/usr/bin/env -- ' + _exec_argument(executable)
    icon_value = _entry_string(str(icon))
    entry = ('[Desktop Entry]\nVersion=1.0\nType=Application\n'
             f'Name={APP_NAME}\nComment=A Python space shooter\n'
             f'Exec={command}\nIcon={icon_value}\n'
             'Terminal=false\nStartupNotify=false\nCategories=Game;ArcadeGame;\n')
    source = Path(sys.executable).resolve()
    source_icon = Path(resource_path('image/serpentis-icon.png'))
    if not source.is_file() or not source_icon.is_file():
        raise DesktopInstallError('The Linux download is missing its executable or application icon.')
    _atomic_install(executable, source, 0o755)
    _atomic_install(icon, source_icon, 0o644)
    _atomic_install(desktop, entry.encode('utf-8'), 0o644)
    return desktop
