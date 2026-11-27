"""Exercise the gate through real pytest subprocesses and installed metadata."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


def run_journey(tmp_path, source, *, required=('case.py::test_required',), targets=('case.py',), environment=None):
    (tmp_path / 'case.py').write_text(source, encoding='utf-8')
    program = (
        'from src.research_journey_gate import execute_journey\n'
        f'raise SystemExit(execute_journey({list(targets)!r}, required_cases={tuple(required)!r}))\n'
    )
    return subprocess.run([sys.executable, '-B', '-c', program], cwd=tmp_path,
        env={**os.environ, 'PYTHONPATH': str(ROOT), 'PYTHONDONTWRITEBYTECODE': '1',
             'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', **(environment or {})},
        capture_output=True, text=True, timeout=20)


def test_all_required_phases_pass_in_real_pytest(tmp_path):
    result = run_journey(tmp_path, 'def test_required():\n    assert 2 + 2 == 4\n')
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'research_journey: passed' in result.stdout
    assert 'mandatory_cases_passed: 1/1' in result.stdout


@pytest.mark.parametrize('source', [
    'import pytest\ndef test_required():\n    pytest.skip("missing browser")\n',
    'import pytest\ndef test_required():\n    pytest.xfail("known gap")\n',
    'import pytest\n@pytest.mark.xfail(reason="known gap")\ndef test_required():\n    pass\n',
    'import pytest\n@pytest.fixture\ndef resource():\n    raise RuntimeError("setup failed")\ndef test_required(resource):\n    pass\n',
    'import pytest\n@pytest.fixture\ndef resource():\n    yield\n    raise RuntimeError("teardown failed")\ndef test_required(resource):\n    pass\n',
], ids=['skipped', 'xfail', 'xpass', 'setup-error', 'teardown-error'])
def test_incomplete_required_evidence_never_passes(tmp_path, source):
    result = run_journey(tmp_path, source)
    assert result.returncode != 0
    assert 'research_journey: failed' in result.stdout
    assert 'research_journey: passed' not in result.stdout


def test_missing_required_case_cannot_pass_even_when_other_tests_pass(tmp_path):
    result = run_journey(tmp_path, 'def test_other():\n    pass\n')
    assert result.returncode != 0
    assert 'mandatory_cases_passed: 0/1' in result.stdout


def test_collect_only_is_not_completed_journey_evidence(tmp_path):
    result = run_journey(tmp_path, 'def test_required():\n    pass\n',
        targets=('--collect-only', 'case.py'))
    assert result.returncode != 0
    assert 'research_journey: failed' in result.stdout


def test_unrelated_failure_is_preserved_when_mandatory_case_passes(tmp_path):
    result = run_journey(tmp_path,
        'def test_required():\n    pass\ndef test_other():\n    assert False\n')
    assert result.returncode == 1
    assert 'mandatory_cases_passed: 1/1' in result.stdout
    assert 'research_journey: failed' in result.stdout


def test_supporting_skip_also_prevents_a_green_bundle(tmp_path):
    result = run_journey(tmp_path,
        'import pytest\ndef test_required():\n    pass\ndef test_other():\n    pytest.skip("missing dependency")\n')
    assert result.returncode != 0
    assert 'research_journey: failed' in result.stdout


def test_collection_error_stays_an_error(tmp_path):
    result = run_journey(tmp_path, 'this is invalid Python syntax !\n')
    assert result.returncode == 2
    assert 'research_journey: passed' not in result.stdout


def test_duplicate_required_collection_is_not_two_independent_successes(tmp_path):
    result = run_journey(tmp_path, 'def test_required():\n    pass\n',
        targets=('--keep-duplicates', 'case.py', 'case.py'))
    assert result.returncode != 0
    assert 'research_journey: failed' in result.stdout


@pytest.mark.parametrize(('requirements', 'expected'), [
    (['pytest>=0'], ()),
    (['pytest<0'], ('dependency_version_mismatch:pytest',)),
    (['nonexistent-stock-journey-dependency>=1'], ('dependency_missing:nonexistent-stock-journey-dependency',)),
])
def test_preflight_checks_real_installed_versions(tmp_path, requirements, expected):
    from src.research_journey_gate import check_runtime
    path = tmp_path / 'pyproject.toml'
    values = ', '.join('"' + value + '"' for value in requirements)
    path.write_text('[project]\nrequires-python = ">=3.10"\ndependencies = [' + values + ']\n')
    assert check_runtime(path) == expected


def test_preflight_includes_declared_dev_and_workspace_extras(tmp_path):
    from src.research_journey_gate import check_runtime
    path = tmp_path / 'pyproject.toml'
    path.write_text('[project]\nrequires-python = ">=3.10"\ndependencies = []\n'
        '[project.optional-dependencies]\ndev = ["pytest<0"]\n'
        'workspace = ["nonexistent-stock-workspace-dependency>=1"]\n')
    assert check_runtime(path) == (
        'dependency_version_mismatch:pytest',
        'dependency_missing:nonexistent-stock-workspace-dependency',
    )


def test_malformed_runtime_manifest_fails_closed(tmp_path):
    from src.research_journey_gate import check_runtime
    path = tmp_path / 'pyproject.toml'
    path.write_text('[project\n')
    assert check_runtime(path) == ('runtime_manifest_invalid',)


def test_an_empty_mandatory_set_is_rejected():
    from src.research_journey_gate import JourneyEvidence
    with pytest.raises(ValueError, match='mandatory'):
        JourneyEvidence(())


@pytest.mark.parametrize('missing', ['pytest', 'packaging'])
def test_unavailable_gate_dependency_is_blocked_without_an_import_traceback(tmp_path, missing):
    program = '''
import builtins, sys
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name == sys.argv[1] or name.startswith(sys.argv[1] + '.'):
        raise ImportError('Constructed unavailable dependency')
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
from pathlib import Path
from src.research_journey_gate import check_runtime, execute_journey
if sys.argv[1] == 'pytest':
    raise SystemExit(execute_journey([]))
print(check_runtime(Path(sys.argv[2])))
'''
    result = subprocess.run([sys.executable, '-B', '-c', program, missing,
        str(ROOT / 'pyproject.toml')], cwd=tmp_path,
        env={**os.environ, 'PYTHONPATH': str(ROOT)}, capture_output=True, text=True, timeout=10)
    assert result.returncode == (2 if missing == 'pytest' else 0)
    assert 'dependency_missing:' + missing in result.stdout
    assert 'Traceback' not in result.stderr


def test_support_module_collection_skip_prevents_success(tmp_path):
    (tmp_path / 'support.py').write_text('import pytest\npytest.skip("missing dependency", allow_module_level=True)\n')
    result = run_journey(tmp_path, 'def test_required():\n    pass\n',
        targets=('case.py', 'support.py'))
    assert result.returncode != 0
    assert 'research_journey: passed' not in result.stdout


@pytest.mark.parametrize('early', [False, True], ids=['failed-support', 'unexecuted-support'])
def test_explicit_zero_exit_cannot_hide_failed_or_unexecuted_support(tmp_path, early):
    stop = 'def test_stop():\n    pytest.exit("stop early", returncode=0)\n'
    fail = 'def test_bad():\n    assert False\n'
    source = 'import pytest\ndef test_required():\n    pass\n' + (stop + fail if early else fail + stop)
    result = run_journey(tmp_path, source)
    assert result.returncode != 0
    assert 'research_journey: passed' not in result.stdout


@pytest.mark.parametrize(('environment', 'source', 'blocker'), [
    ({'PYTEST_ADDOPTS': '-k required'},
        'def test_required():\n    pass\ndef test_support():\n    assert False\n',
        'inherited_pytest_options'),
    ({'PYTEST_ADDOPTS': '--runxfail'},
        'import pytest\n@pytest.mark.xfail(strict=True)\ndef test_required():\n    pass\n',
        'inherited_pytest_options'),
    ({'PYTHONOPTIMIZE': '1'}, 'def test_required():\n    pass\n', 'optimized_python'),
])
def test_ambient_options_cannot_weaken_release_evidence(tmp_path, environment, source, blocker):
    result = run_journey(tmp_path, source, environment=environment)
    assert result.returncode == 2
    assert 'blocker: ' + blocker in result.stdout


@pytest.mark.parametrize(('options', 'source'), [
    (('-k', 'required'), 'def test_required():\n    pass\ndef test_support():\n    assert False\n'),
    (('--runxfail',), 'import pytest\n@pytest.mark.xfail(strict=True)\ndef test_required():\n    pass\n'),
])
def test_explicit_deselection_and_xfail_override_cannot_pass(tmp_path, options, source):
    result = run_journey(tmp_path, source, targets=(*options, 'case.py'))
    assert result.returncode != 0
    assert 'research_journey: passed' not in result.stdout


def test_main_uses_preflight_browser_for_real_helper_and_restores_previous_value(tmp_path, monkeypatch):
    from src import research_journey_gate as gate
    from src.public_performance_gate import find_chrome_executable
    browser = tmp_path / 'cached-chromium'
    browser.write_text('#!/bin/sh\nexit 0\n')
    browser.chmod(0o700)
    monkeypatch.setenv('STOCK_RESEARCH_BROWSER_EXECUTABLE', '/previous/value')
    monkeypatch.setattr(gate, 'check_runtime', lambda path: ())
    monkeypatch.setattr(gate, 'check_browser_environment', lambda: (browser, ()))

    def execute(targets):
        assert find_chrome_executable() == browser
        return 0

    monkeypatch.setattr(gate, 'execute_journey', execute)
    assert gate.main([]) == 0
    assert os.environ['STOCK_RESEARCH_BROWSER_EXECUTABLE'] == '/previous/value'


def test_runtime_mismatch_stops_before_browser_or_pytest_execution(tmp_path, monkeypatch, capsys):
    from src import research_journey_gate as gate
    (tmp_path / 'pyproject.toml').write_text(
        '[project]\nrequires-python = ">=3.10"\ndependencies = ["pytest<0"]\n')
    monkeypatch.setattr(gate, 'ROOT', tmp_path)

    def unexpected():
        pytest.fail('Runtime mismatch must stop before browser access')

    monkeypatch.setattr(gate, 'check_browser_environment', unexpected)
    assert gate.main([]) == 2
    assert 'dependency_version_mismatch:pytest' in capsys.readouterr().out
