"""Release verification fails closed for missing checks and incomplete downloads."""
import hashlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from app_info import APP_NAME, APP_VERSION
from scripts import checksums, verify_build


def complete_report():
    return {'ok': True, 'application': APP_NAME, 'version': APP_VERSION,
            'screens': sorted(verify_build.EXPECTED_SCREENS), 'save_data': 'passed',
            'sprite_sizes': {'alien': [44, 44], 'player_projectile': [9, 9]}}


@pytest.fixture
def executable(tmp_path):
    binary = tmp_path / 'Serpentis.exe'
    binary.write_bytes(b'fake executable used with a mocked child process')
    return binary


def test_packaged_verifier_uses_absolute_paths_and_unrelated_cwd(executable, monkeypatch):
    def child(command, **kwargs):
        assert Path(command[0]) == executable.resolve()
        assert Path(kwargs['cwd']) != executable.parent
        report = Path(command[command.index('--smoke-report') + 1])
        assert report.is_absolute() and report.parent == Path(kwargs['cwd'])
        assert '--smoke-test' in command
        assert kwargs['timeout'] == 30
        report.write_text(json.dumps(complete_report()), encoding='utf-8')
        # A --windowed Windows executable need not provide stdout.
        return SimpleNamespace(returncode=0, stdout='', stderr='')
    monkeypatch.setattr(verify_build.subprocess, 'run', child)
    assert verify_build.verify_build(executable)['ok'] is True


def test_packaged_verifier_rejects_nonzero_exit(executable, monkeypatch):
    monkeypatch.setattr(verify_build.subprocess, 'run',
                        lambda *a, **k: SimpleNamespace(returncode=139, stdout='', stderr='native failure'))
    with pytest.raises(verify_build.BuildVerificationError, match='code 139'):
        verify_build.verify_build(executable)


@pytest.mark.parametrize('report_text', [None, '{invalid'])
def test_packaged_verifier_rejects_missing_or_invalid_json(executable, monkeypatch, report_text):
    def child(command, **kwargs):
        if report_text is not None:
            Path(command[-1]).write_text(report_text, encoding='utf-8')
        return SimpleNamespace(returncode=0, stdout='', stderr='')
    monkeypatch.setattr(verify_build.subprocess, 'run', child)
    with pytest.raises(verify_build.BuildVerificationError, match='valid startup report'):
        verify_build.verify_build(executable)


@pytest.mark.parametrize(('field', 'value'), [
    ('ok', False), ('application', 'Other Game'), ('version', '0.0.0'),
    ('save_data', 'failed'), ('screens', ['menu']),
    ('screens', ['menu'] * 8), ('screens', None),
    ('sprite_sizes', None), ('sprite_sizes', {}),
    ('sprite_sizes', {'alien': [51, 51], 'player_projectile': [22, 22]}),
])
def test_report_requires_correct_identity_version_saves_and_screen_coverage(field, value):
    report = complete_report()
    report[field] = value
    with pytest.raises(verify_build.BuildVerificationError):
        verify_build.validate_report(report)


def test_packaged_verifier_bounds_hung_process(executable, monkeypatch):
    def hung(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs['timeout'])
    monkeypatch.setattr(verify_build.subprocess, 'run', hung)
    with pytest.raises(verify_build.BuildVerificationError, match='within 1 seconds'):
        verify_build.verify_build(executable, timeout=1)


def test_packaged_verifier_rejects_missing_executable(tmp_path):
    with pytest.raises(verify_build.BuildVerificationError, match='Executable not found'):
        verify_build.verify_build(tmp_path / 'not-built')


def test_checksums_include_all_three_downloads_with_bare_names(tmp_path):
    for name in checksums.ARTIFACT_NAMES:
        (tmp_path / name).write_bytes(name.encode('ascii'))
    output = checksums.write_checksums(tmp_path)
    expected = ''.join(f'{hashlib.sha256(name.encode("ascii")).hexdigest()}  {name}\n'
                       for name in sorted(checksums.ARTIFACT_NAMES))
    assert output.name == 'SHA256SUMS.txt'
    assert output.read_text(encoding='ascii') == expected
    # Regeneration must not hash the old manifest into itself.
    assert checksums.write_checksums(tmp_path).read_text(encoding='ascii') == expected


@pytest.mark.parametrize('empty', [False, True], ids=['missing', 'empty'])
def test_checksums_reject_incomplete_release_without_replacing_manifest(tmp_path, empty):
    missing = checksums.ARTIFACT_NAMES[-1]
    for name in checksums.ARTIFACT_NAMES[:-1]:
        (tmp_path / name).write_bytes(b'complete download')
    if empty:
        (tmp_path / missing).write_bytes(b'')
    output = tmp_path / 'SHA256SUMS.txt'
    output.write_text('previous complete manifest', encoding='ascii')
    with pytest.raises(ValueError, match=missing):
        checksums.write_checksums(tmp_path)
    assert output.read_text(encoding='ascii') == 'previous complete manifest'
