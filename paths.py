"""Resolve a writable directory for save data (scores, settings).

Works the same whether the game runs from source or from a standalone
executable built with PyInstaller.
"""
import os
import sys

from app_info import APP_NAME

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def resource_path(relative_path: str) -> str:
    """Resolve a bundled asset or source file independently of the working folder."""
    base = getattr(sys, '_MEIPASS', PROJECT_ROOT) if getattr(sys, 'frozen', False) else PROJECT_ROOT
    return os.path.normpath(os.path.join(base, relative_path))


def user_data_dir() -> str:
    """Return (and create) a writable folder for persistent save data.

    - Running from source: keep everything inside the project's own
      ``data/`` folder, exactly like before — handy for development.
    - Running from a frozen executable (PyInstaller ``--onefile`` /
      ``--onedir``): the bundle's folder is read-only or temporary and
      gets wiped on every relaunch, so scores/settings would vanish.
      Instead we redirect to the OS's standard per-user app-data
      location, which persists across runs and updates.
    """
    override = os.environ.get('SERPENTIS_DATA_DIR')
    if override:
        path = os.path.abspath(os.path.expanduser(override))
    elif getattr(sys, 'frozen', False):
        if sys.platform == 'darwin':
            base = os.path.expanduser('~/Library/Application Support')
        elif sys.platform == 'win32':
            base = os.environ.get('APPDATA', os.path.expanduser('~'))
        else:
            base = os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share'))
        path = os.path.join(base, APP_NAME)
    else:
        path = os.path.join(PROJECT_ROOT, 'data')

    os.makedirs(path, exist_ok=True)
    return path
