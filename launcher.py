"""Prepare a project-local Python environment and start Serpentis."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import venv

PROJECT_ROOT = Path(__file__).resolve().parent
MIN_PYTHON = (3, 10)
MARKER_NAME = '.serpentis-requirements.sha256'

# Run inside the selected virtual environment, after setup if necessary.
# packaging evaluates standard PEP 508 markers without consulting the network.
_DEPENDENCY_PROBE = '''
import sys
from pathlib import Path
from importlib.metadata import version

try:
    assert sys.prefix != sys.base_prefix, 'A virtual environment is required'
    assert sys.version_info >= (3, 10), 'Python 3.10 or newer is required'
    from packaging.requirements import Requirement
    for line in (Path(sys.argv[1]) / 'requirements.txt').read_text().splitlines():
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        requirement = Requirement(line)
        if requirement.marker and not requirement.marker.evaluate():
            continue
        installed = version(requirement.name)
        if not requirement.specifier.contains(installed, prereleases=True):
            raise RuntimeError(f'Required {requirement}; installed {installed}')
    import pygame
    import numpy
except Exception as error:
    raise SystemExit(str(error))
'''


class LauncherError(Exception):
    """A setup problem that should be shown without a Python traceback."""


def environment_python(environment: Path) -> Path:
    return environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def child_environment() -> dict:
    """Keep Python and pip pointed at the selected environment."""
    environment = os.environ.copy()
    environment.pop('PYTHONHOME', None)
    environment.pop('PYTHONPATH', None)
    environment['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
    return environment


def dependencies_import(python: Path, root: Path) -> bool:
    # A child process also catches broken native extension installations.
    result = subprocess.run(
        [str(python), '-c', _DEPENDENCY_PROBE, str(root)],
        cwd=root, env=child_environment(), capture_output=True, text=True,
    )
    return result.returncode == 0


def prepare_environment(root: Path, check_only: bool = False) -> Path:
    environment = root / '.venv'
    python = environment_python(environment)
    requirements = root / 'requirements.txt'
    if not requirements.is_file():
        raise LauncherError(f'Missing dependency list: {requirements}')
    digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
    marker = environment / MARKER_NAME

    if not python.is_file() or not (environment / 'pyvenv.cfg').is_file():
        if environment.exists() or environment.is_symlink():
            raise LauncherError('The existing .venv is incomplete. Repair it or move it aside, then retry.')
        if check_only:
            raise LauncherError('No project environment yet. Run the launcher with --setup first.')
        print('Creating the Serpentis environment...', flush=True)
        venv.EnvBuilder(with_pip=True).create(environment)

    recorded = marker.read_text().strip() if marker.is_file() else ''
    usable = dependencies_import(python, root)
    if recorded == digest and usable:
        return python
    if check_only:
        raise LauncherError('Dependencies are missing or have different versions. Run the launcher with --setup.')

    print('Preparing Serpentis dependencies...', flush=True)
    result = subprocess.run(
        [str(python), '-m', 'pip', '--isolated', 'install', '--disable-pip-version-check',
         '-r', str(requirements)],
        cwd=root, env=child_environment(),
    )
    if result.returncode:
        raise LauncherError('Dependency installation failed. Check the messages above and your connection, then retry.')
    if not dependencies_import(python, root):
        raise LauncherError('Dependencies could not be loaded after installation. Repair .venv, then retry.')
    marker.write_text(digest + '\n')
    return python


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--setup', action='store_true', help='prepare dependencies without opening the game')
    mode.add_argument('--check', action='store_true', help='check prepared dependencies without changing anything')
    options, game_arguments = parser.parse_known_args(argv)
    if (options.setup or options.check) and game_arguments:
        parser.error('Game arguments cannot be combined with --setup or --check')
    if sys.version_info < MIN_PYTHON:
        print('Serpentis requires Python 3.10 or newer. Install it, then run this launcher again.', file=sys.stderr)
        return 1
    try:
        python = prepare_environment(PROJECT_ROOT, check_only=options.check)
        if options.setup or options.check:
            print('Serpentis environment is ready.')
            return 0
        result = subprocess.run([str(python), str(PROJECT_ROOT / 'main.py'), *game_arguments],
                                cwd=PROJECT_ROOT, env=child_environment())
        return result.returncode if result.returncode >= 0 else 128 - result.returncode
    except (LauncherError, OSError, subprocess.SubprocessError) as error:
        print(f'Serpentis could not start: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
