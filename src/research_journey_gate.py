"""Run the existing research journey without accepting incomplete test evidence."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from importlib import metadata
import os
from pathlib import Path
import platform
import socket
import sys

ROOT = Path(__file__).resolve().parents[1]
_BROWSER_TARGETS = (
    'tests/test_self_service_research_browser.py::test_online_only_company_reaches_trend_scenario_notes_snapshot_and_monitor',
    'tests/test_research_monitor_roundtrip_browser.py::test_online_research_round_trip_keeps_section_and_evidence',
    'tests/test_private_pilot_recovery_browser.py::test_private_rehearsal_provider_recovery_and_saved_monitor_replay',
)
MANDATORY_CASES = (
    *(_BROWSER_TARGETS[0] + '[' + viewport + ']' for viewport in ('desktop', 'phone')),
    *(_BROWSER_TARGETS[1] + '[' + viewport + ']' for viewport in ('desktop-valuation', 'phone-sec-receipt')),
    *(_BROWSER_TARGETS[2] + '[' + viewport + ']' for viewport in ('desktop', 'phone')),
)
TARGETS = (*_BROWSER_TARGETS,
    'tests/test_self_service_financial_refresh.py',
    'tests/test_online_peer_sources.py',
    'tests/test_online_research_context_store.py',
    'tests/test_company_research_notes.py',
    'tests/test_self_service_workbench_ui.py',
)


class JourneyEvidence:
    """Observe actual collection and setup/call/teardown results, including skips."""

    def __init__(self, required_cases):
        self.required = tuple(required_cases)
        if not self.required or len(set(self.required)) != len(self.required):
            raise ValueError('A unique nonempty mandatory case set is required')
        self.collected = Counter()
        self.phases = defaultdict(lambda: defaultdict(list))
        self.incomplete = set()
        self.finished = False
        self.exit_status = None

    def pytest_collection_finish(self, session):
        self.collected.update(item.nodeid for item in session.items)

    def pytest_configure(self, config):
        if config.getoption('runxfail', default=False):
            self.incomplete.add('xfail_override')

    def pytest_collectreport(self, report):
        if report.skipped or report.failed:
            self.incomplete.add('collection:' + report.nodeid)

    def pytest_deselected(self, items):
        self.incomplete.update('deselected:' + item.nodeid for item in items)

    def pytest_runtest_logreport(self, report):
        self.phases[report.nodeid][report.when].append(report.outcome)
        if report.skipped or hasattr(report, 'wasxfail'):
            self.incomplete.add(report.nodeid)

    def _case_passed(self, nodeid):
        return (self.collected[nodeid] == 1 and nodeid not in self.incomplete
            and all(self.phases[nodeid].get(phase) == ['passed']
                    for phase in ('setup', 'call', 'teardown')))

    @property
    def passed_cases(self):
        return sum(self._case_passed(nodeid) for nodeid in self.required)

    @property
    def passed(self):
        return (self.finished and self.exit_status == 0 and not self.incomplete
            and self.passed_cases == len(self.required)
            and all(self._case_passed(nodeid) for nodeid in self.collected))

    def pytest_sessionfinish(self, session, exitstatus):
        self.finished = True
        self.exit_status = int(exitstatus)
        if self.exit_status == 0 and not self.passed:
            session.exitstatus = self.exit_status = 1


def check_runtime(pyproject_path: Path) -> tuple[str, ...]:
    """Check actual installed distributions against this checkout's declarations."""
    try:
        from packaging.requirements import InvalidRequirement, Requirement
        from packaging.specifiers import InvalidSpecifier, SpecifierSet
    except ImportError:
        return ('dependency_missing:packaging',)
    try:
        import tomllib
    except ImportError:
        return ('release_verifier_requires_python_3_11_or_newer',)
    try:
        document = tomllib.loads(Path(pyproject_path).read_text(encoding='utf-8'))
        project = document['project']
        requirements = project['dependencies']
        optional = project.get('optional-dependencies', {})
        if not isinstance(requirements, list) or not isinstance(optional, dict):
            raise ValueError('Invalid runtime requirements')
        requirements = requirements + optional.get('dev', []) + optional.get('workspace', [])
        problems = []
        if not SpecifierSet(project['requires-python']).contains(platform.python_version()):
            problems.append('python_version_mismatch')
        for text in dict.fromkeys(requirements):
            requirement = Requirement(text)
            if requirement.marker and not requirement.marker.evaluate():
                continue
            try:
                installed = metadata.version(requirement.name)
            except metadata.PackageNotFoundError:
                problems.append('dependency_missing:' + requirement.name)
                continue
            if not requirement.specifier.contains(installed, prereleases=True):
                problems.append('dependency_version_mismatch:' + requirement.name)
        return tuple(problems)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, InvalidRequirement, InvalidSpecifier):
        return ('runtime_manifest_invalid',)


def check_browser_environment() -> tuple[Path | None, tuple[str, ...]]:
    """Check capability, without launching an app or contacting any provider."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as runtime:
            browser = Path(runtime.chromium.executable_path).resolve()
            if not browser.is_file() or not os.access(browser, os.X_OK):
                return None, ('playwright_chromium_unavailable',)
    except Exception:
        return None, ('playwright_runtime_unavailable',)
    try:
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
    except OSError:
        return None, ('localhost_server_unavailable',)
    return browser, ()


def execute_journey(targets, *, required_cases=MANDATORY_CASES) -> int:
    """Execute pytest and require complete evidence; preserve existing errors."""
    unsafe = ('optimized_python' if sys.flags.optimize or
        os.environ.get('PYTHONOPTIMIZE', '').strip() not in {'', '0'} else
        'inherited_pytest_options' if os.environ.get('PYTEST_ADDOPTS', '').strip() else None)
    if unsafe:
        print('research_journey: blocked')
        print('blocker: ' + unsafe)
        return 2
    try:
        import pytest
    except ImportError:
        print('research_journey: blocked')
        print('blocker: dependency_missing:pytest')
        return 2
    evidence = JourneyEvidence(required_cases)
    result = int(pytest.main(['-q', '-p', 'no:cacheprovider', *targets], plugins=[evidence]))
    passed = result == 0 and evidence.passed
    print('research_journey: ' + ('passed' if passed else 'failed'))
    print(f'mandatory_cases_passed: {evidence.passed_cases}/{len(evidence.required)}')
    if not passed:
        for nodeid in evidence.required:
            if not evidence._case_passed(nodeid):
                print('incomplete_mandatory_case: ' + nodeid)
        if evidence.incomplete:
            print(f'skipped_or_expected_failure_cases: {len(evidence.incomplete)}')
    return result if result else (0 if passed else 1)


def main(argv=None) -> int:
    argparse.ArgumentParser(description='Verify the fixed constructed-source research journey.').parse_args(argv)
    print('Research Journey Release Check')
    print('Constructed sources and disposable stores; this does not verify actual users, source rights or hosting.')
    problems = check_runtime(ROOT / 'pyproject.toml')
    browser = None
    if not problems:
        browser, problems = check_browser_environment()
    if problems:
        print('research_journey: blocked')
        for problem in problems:
            print('blocker: ' + problem)
        return 2
    from src.public_performance_gate import RESEARCH_BROWSER_EXECUTABLE_ENV
    previous = os.environ.get(RESEARCH_BROWSER_EXECUTABLE_ENV)
    os.environ[RESEARCH_BROWSER_EXECUTABLE_ENV] = str(browser)
    try:
        return execute_journey(TARGETS)
    finally:
        if previous is None:
            os.environ.pop(RESEARCH_BROWSER_EXECUTABLE_ENV, None)
        else:
            os.environ[RESEARCH_BROWSER_EXECUTABLE_ENV] = previous


if __name__ == '__main__':
    raise SystemExit(main())
