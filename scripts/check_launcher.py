"""Verify each platform's source launcher using a fresh copy and environment."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from launcher import MARKER_NAME
from scripts.verify_build import BuildVerificationError, validate_report

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class LauncherCheckError(RuntimeError):
    """A source launcher failed setup, validation, or environment reuse."""


def _invoke(project: Path, working_directory: Path, arguments: list[str], timeout: int) -> None:
    if sys.platform == 'win32':
        # cmd.exe is required for .bat files. All arguments are generated here,
        # and list2cmdline quotes the temporary paths containing spaces.
        command = subprocess.list2cmdline([str(project / 'run.bat'), *arguments])
        shell = True
    else:
        wrapper = 'run.command' if sys.platform == 'darwin' else 'run.sh'
        command = ['bash', str(project / wrapper), *arguments]
        shell = False
    try:
        result = subprocess.run(command, cwd=working_directory, shell=shell,
                                env=dict(os.environ, CI='true'), capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=timeout)
    except subprocess.TimeoutExpired as error:
        raise LauncherCheckError(f'Launcher {arguments[0]} exceeded {timeout} seconds') from error
    if result.returncode != 0:
        details = ((result.stderr or '') + '\n' + (result.stdout or '')).strip()[-3000:]
        raise LauncherCheckError(f'Launcher {arguments[0]} exited {result.returncode}: {details}')


def check_launcher(source: Path = PROJECT_ROOT) -> dict:
    """Exercise setup and repeat launches without touching a developer environment."""
    with tempfile.TemporaryDirectory(prefix='serpentis-launcher-check-') as folder:
        temporary = Path(folder)
        project = temporary / 'Serpentis source with spaces'
        shutil.copytree(source, project, ignore=shutil.ignore_patterns(
            '.git', '.venv', 'data', 'config.json', 'build', 'dist', '__pycache__',
            '.pytest_cache', '.ruff_cache', '.idea', '.DS_Store'))
        unrelated = temporary / 'Unrelated working directory'
        unrelated.mkdir()
        _invoke(project, unrelated, ['--setup'], timeout=120)
        marker = project / '.venv' / MARKER_NAME
        prepared_mtime = marker.stat().st_mtime_ns
        _invoke(project, unrelated, ['--check'], timeout=30)
        if marker.stat().st_mtime_ns != prepared_mtime:
            raise LauncherCheckError('Checking dependencies unexpectedly changed the setup marker')
        report_path = temporary / 'startup report.json'
        _invoke(project, unrelated, ['--smoke-test', '--smoke-report', str(report_path)], timeout=30)
        if marker.stat().st_mtime_ns != prepared_mtime:
            raise LauncherCheckError('Normal launch unexpectedly reinstalled dependencies')
        try:
            report = json.loads(report_path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as error:
            raise LauncherCheckError('Source launcher did not write a valid startup report') from error
        return validate_report(report)


def main() -> int:
    try:
        report = check_launcher()
    except (LauncherCheckError, BuildVerificationError, OSError) as error:
        print(f'Source launcher verification failed: {error}', file=sys.stderr)
        return 1
    print(f"Verified {report['application']} {report['version']} source launcher: "
          'fresh setup, dependency check, startup, and environment reuse.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
