"""Verify a packaged game from an unrelated directory before it is published."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app_info import APP_NAME, APP_VERSION

EXPECTED_SCREENS = {'menu', 'hangar', 'settings', 'controls', 'loading', 'gameplay', 'pause', 'results', 'leaderboard'}
# Golden logical sizes from the game's intended default appearance.
EXPECTED_SPRITE_SIZES = {'alien': [44, 44], 'player_projectile': [9, 9]}


class BuildVerificationError(RuntimeError):
    """The executable did not complete its self-check successfully."""


def validate_report(report: dict) -> dict:
    """Require a complete report from this exact application version."""
    if not isinstance(report, dict) or report.get('ok') is not True:
        raise BuildVerificationError('Startup report did not indicate success')
    if report.get('application') != APP_NAME or report.get('version') != APP_VERSION:
        raise BuildVerificationError(f'Startup report must identify {APP_NAME} {APP_VERSION}')
    screens = report.get('screens')
    if (not isinstance(screens, list) or not all(isinstance(screen, str) for screen in screens)
            or len(screens) != len(EXPECTED_SCREENS) or set(screens) != EXPECTED_SCREENS):
        raise BuildVerificationError('Startup report did not cover all nine game screens')
    if report.get('save_data') != 'passed':
        raise BuildVerificationError('Startup report did not verify persistent save data')
    if report.get('sprite_sizes') != EXPECTED_SPRITE_SIZES:
        raise BuildVerificationError('Built sprites do not match the standard alien/projectile sizes')
    size = report.get('render_size')
    if (not isinstance(size, list) or len(size) != 2 or
            not all(isinstance(value, int) and value > 0 for value in size) or size[1] < 1080):
        raise BuildVerificationError('Built game did not render to an HD framebuffer')
    return report


def verify_build(executable: Path, timeout: float = 30) -> dict:
    """Run the actual binary; do not depend on stdout from a windowed Windows EXE."""
    executable = Path(executable).resolve()
    if not executable.is_file():
        raise BuildVerificationError(f'Executable not found: {executable}')
    with tempfile.TemporaryDirectory(prefix='serpentis-build-check-') as folder:
        report_path = Path(folder) / 'startup-report.json'
        command = [str(executable), '--smoke-test', '--smoke-report', str(report_path)]
        try:
            result = subprocess.run(command, cwd=folder, capture_output=True, text=True,
                                    encoding='utf-8', errors='replace', timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise BuildVerificationError(f'Executable did not finish its check within {timeout:g} seconds') from exc
        except OSError as exc:
            raise BuildVerificationError(f'Cannot start executable: {exc}') from exc
        if result.returncode != 0:
            details = ((result.stderr or '') + '\n' + (result.stdout or '')).strip()[-2000:]
            raise BuildVerificationError(f'Executable exited with code {result.returncode}: {details}')
        try:
            report = json.loads(report_path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            raise BuildVerificationError('Executable did not write a valid startup report') from exc
        return validate_report(report)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path, help='Path to the freshly built game executable')
    args = parser.parse_args()
    try:
        verify_build(args.executable)
    except BuildVerificationError as exc:
        parser.exit(1, f'Build verification failed: {exc}\n')
    print(f'Verified {APP_NAME} {APP_VERSION}: {args.executable}')


if __name__ == '__main__':
    main()
