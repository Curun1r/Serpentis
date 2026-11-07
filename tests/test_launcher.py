"""Source bootstrap behavior without creating environments or using the network."""
import hashlib
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

import launcher


@pytest.fixture
def project(tmp_path, monkeypatch):
    root = tmp_path / 'project with spaces'
    root.mkdir()
    (root / 'requirements.txt').write_text('pygame>=2.5.0\nnumpy>=1.24.0\n')
    (root / 'main.py').write_text('')
    monkeypatch.setattr(launcher, 'PROJECT_ROOT', root)
    return root


def prepared(project, marker=True):
    environment = project / '.venv'
    python = launcher.environment_python(environment)
    python.parent.mkdir(parents=True)
    python.touch()
    (environment / 'pyvenv.cfg').write_text('home = /fake/python\n')
    if marker:
        digest = hashlib.sha256((project / 'requirements.txt').read_bytes()).hexdigest()
        (environment / launcher.MARKER_NAME).write_text(digest + '\n')
    return python


def test_ready_environment_reuses_dependencies_and_forwards_game_args(project, monkeypatch):
    python = prepared(project)
    monkeypatch.setattr(launcher, 'dependencies_import', lambda *args: True)
    run = Mock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(launcher.subprocess, 'run', run)
    assert launcher.main(['--smoke-test']) == 0
    run.assert_called_once()
    assert run.call_args.args[0] == [str(python), str(project / 'main.py'), '--smoke-test']
    assert run.call_args.kwargs['cwd'] == project


def test_check_ready_environment_never_installs_or_launches(project, monkeypatch):
    prepared(project)
    monkeypatch.setattr(launcher, 'dependencies_import', lambda *args: True)
    run = Mock()
    monkeypatch.setattr(launcher.subprocess, 'run', run)
    assert launcher.main(['--check']) == 0
    run.assert_not_called()


def test_missing_environment_check_is_nonmutating(project, monkeypatch):
    create = Mock()
    monkeypatch.setattr(launcher.venv, 'EnvBuilder', create)
    assert launcher.main(['--check']) == 1
    create.assert_not_called()
    assert not (project / '.venv').exists()


def test_incomplete_existing_environment_is_not_overwritten(project, monkeypatch):
    environment = project / '.venv'
    environment.mkdir()
    sentinel = environment / 'keep.txt'
    sentinel.write_text('existing files')
    create = Mock()
    monkeypatch.setattr(launcher.venv, 'EnvBuilder', create)
    assert launcher.main(['--setup']) == 1
    assert sentinel.read_text() == 'existing files'
    create.assert_not_called()


def test_existing_environment_symlink_is_reused(project, tmp_path, monkeypatch):
    if launcher.os.name == 'nt':
        pytest.skip('Symlink creation can require administrator privileges on Windows')
    python = prepared(project)
    real_env = tmp_path / 'existing virtual environment'
    (project / '.venv').rename(real_env)
    (project / '.venv').symlink_to(real_env, target_is_directory=True)
    monkeypatch.setattr(launcher, 'dependencies_import', lambda *args: True)
    assert launcher.prepare_environment(project) == python
    assert (project / '.venv').is_symlink()


@pytest.mark.parametrize('condition', ['changed', 'missing_import', 'missing_marker'])
def test_dependencies_repaired_only_when_needed(project, monkeypatch, condition):
    python = prepared(project, marker=condition != 'missing_marker')
    if condition == 'changed':
        with (project / 'requirements.txt').open('a') as stream:
            stream.write('# updated\n')
    probe = Mock(side_effect=[condition != 'missing_import', True])
    monkeypatch.setattr(launcher, 'dependencies_import', probe)
    run = Mock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(launcher.subprocess, 'run', run)
    assert launcher.main(['--setup']) == 0
    run.assert_called_once()
    command = run.call_args.args[0]
    assert command[:5] == [str(python), '-m', 'pip', '--isolated', 'install']
    assert command[-2:] == ['-r', str(project / 'requirements.txt')]
    assert (project / '.venv' / launcher.MARKER_NAME).read_text().strip() == hashlib.sha256(
        (project / 'requirements.txt').read_bytes()).hexdigest()


def test_missing_environment_is_created_with_pip(project, monkeypatch):
    builder = Mock()
    def create(path):
        prepared(project, marker=False)
    builder.create.side_effect = create
    factory = Mock(return_value=builder)
    monkeypatch.setattr(launcher.venv, 'EnvBuilder', factory)
    monkeypatch.setattr(launcher, 'dependencies_import', Mock(side_effect=[False, True]))
    monkeypatch.setattr(launcher.subprocess, 'run', Mock(return_value=subprocess.CompletedProcess([], 0)))
    assert launcher.main(['--setup']) == 0
    factory.assert_called_once_with(with_pip=True)
    builder.create.assert_called_once_with(project / '.venv')


def test_install_failure_does_not_record_success_or_start_game(project, monkeypatch):
    prepared(project, marker=False)
    monkeypatch.setattr(launcher, 'dependencies_import', lambda *args: False)
    run = Mock(return_value=subprocess.CompletedProcess([], 1))
    monkeypatch.setattr(launcher.subprocess, 'run', run)
    assert launcher.main([]) == 1
    run.assert_called_once()
    assert 'pip' in run.call_args.args[0]
    assert not (project / '.venv' / launcher.MARKER_NAME).exists()


def test_failed_import_after_install_is_not_marked_ready(project, monkeypatch):
    prepared(project, marker=False)
    monkeypatch.setattr(launcher, 'dependencies_import', lambda *args: False)
    monkeypatch.setattr(launcher.subprocess, 'run', Mock(return_value=subprocess.CompletedProcess([], 0)))
    assert launcher.main(['--setup']) == 1
    assert not (project / '.venv' / launcher.MARKER_NAME).exists()


def test_game_failure_preserves_exit_status(project, monkeypatch):
    prepared(project)
    monkeypatch.setattr(launcher, 'dependencies_import', lambda *args: True)
    monkeypatch.setattr(launcher.subprocess, 'run', Mock(return_value=subprocess.CompletedProcess([], 7)))
    assert launcher.main([]) == 7


def test_game_signal_exit_uses_shell_status(project, monkeypatch):
    prepared(project)
    monkeypatch.setattr(launcher, 'dependencies_import', lambda *args: True)
    monkeypatch.setattr(launcher.subprocess, 'run', Mock(return_value=subprocess.CompletedProcess([], -11)))
    assert launcher.main([]) == 139


def test_unsupported_bootstrap_python_reports_error(project, monkeypatch, capsys):
    monkeypatch.setattr(launcher.sys, 'version_info', (3, 9, 0))
    assert launcher.main(['--setup']) == 1
    assert 'Python 3.10' in capsys.readouterr().err
    assert not (project / '.venv').exists()


def test_child_probe_ignores_ambient_python_paths(project, monkeypatch):
    monkeypatch.setenv('PYTHONPATH', '/unrelated/packages')
    monkeypatch.setenv('PYTHONHOME', '/unrelated/python')
    run = Mock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(launcher.subprocess, 'run', run)
    assert launcher.dependencies_import(Path('/project/.venv/bin/python'), project)
    env = run.call_args.kwargs['env']
    assert 'PYTHONPATH' not in env
    assert 'PYTHONHOME' not in env


def test_check_changed_requirements_does_not_install(project, monkeypatch):
    prepared(project)
    (project / 'requirements.txt').write_text('pygame>=2.6.0\nnumpy>=1.24.0\n')
    monkeypatch.setattr(launcher, 'dependencies_import', lambda *args: True)
    run = Mock()
    monkeypatch.setattr(launcher.subprocess, 'run', run)
    assert launcher.main(['--check']) == 1
    run.assert_not_called()


def test_environment_creation_failure_stops_setup(project, monkeypatch):
    builder = Mock()
    builder.create.side_effect = OSError('permission denied')
    monkeypatch.setattr(launcher.venv, 'EnvBuilder', Mock(return_value=builder))
    run = Mock()
    monkeypatch.setattr(launcher.subprocess, 'run', run)
    assert launcher.main(['--setup']) == 1
    run.assert_not_called()


def test_missing_requirements_does_not_create_environment(project):
    (project / 'requirements.txt').unlink()
    assert launcher.main(['--setup']) == 1
    assert not (project / '.venv').exists()
