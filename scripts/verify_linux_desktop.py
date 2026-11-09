"""Check menu installation from the real Linux binary in disposable user data."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desktop_integration import APP_ID


def verify_linux_desktop(executable: Path) -> None:
    executable = executable.resolve()
    with tempfile.TemporaryDirectory(prefix='serpentis-menu-check-') as folder:
        data = Path(folder) / 'Application data'
        environment = dict(os.environ, XDG_DATA_HOME=str(data))
        result = subprocess.run([str(executable), '--install-desktop'], env=environment,
                                capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise RuntimeError(f'Menu installation failed: {result.stdout}\n{result.stderr}')
        installed = data / 'Serpentis/app/Serpentis'
        desktop = data / 'applications' / f'{APP_ID}.desktop'
        icon = data / 'icons/hicolor/512x512/apps' / f'{APP_ID}.png'
        if not installed.is_file() or not os.access(installed, os.X_OK) or not icon.is_file():
            raise RuntimeError('Menu installation did not copy its executable and icon')
        if str(installed) not in desktop.read_text(encoding='utf-8'):
            raise RuntimeError('Menu installation did not identify the installed executable')
        # Re-running from the installed copy must not truncate a running binary.
        subprocess.run([str(installed), '--install-desktop'], env=environment,
                       capture_output=True, check=True, timeout=30)
    print('Verified standalone Linux application-menu installation and update')


if __name__ == '__main__':
    verify_linux_desktop(Path(sys.argv[1]))
