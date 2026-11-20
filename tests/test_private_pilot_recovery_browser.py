"""Provider outage and recovery through Workbench with an immutable saved baseline."""
from functools import lru_cache
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest

from src.public_performance_gate import _free_port, _wait_for_dom_stability, _wait_for_health, find_chrome_executable
from tests.test_research_monitor_roundtrip_browser import assert_rendered_english


@lru_cache(maxsize=1)
def _recovery_fixture(root):
    from tests import bank_research_snapshot_browser_fixture as fixture

    build_dependencies = fixture.snapshot_dependencies

    def dependencies(record, now):
        result = build_dependencies(record, now)
        vendor = result['dependencies']['vendor']

        def observed_vendor(*args, **kwargs):
            if (root / 'provider-outage').exists():
                record('injected-provider-timeout')
                raise TimeoutError('Synthetic private diagnostic must stay private')
            return vendor(*args, **kwargs)

        result['dependencies']['vendor'] = observed_vendor
        return result

    fixture.snapshot_dependencies = dependencies
    return fixture.run_bank_research_snapshot_fixture


def run_recovery_fixture(root):
    _recovery_fixture(root)(root)


@pytest.fixture
def recovery_server(tmp_path):
    project = Path(__file__).resolve().parents[1]
    script = tmp_path / 'recovery_app.py'
    script.write_text('from pathlib import Path\n'
        'from tests.test_private_pilot_recovery_browser import run_recovery_fixture\n'
        'run_recovery_fixture(Path(__file__).parent)\n', encoding='utf-8')
    address = f'http://127.0.0.1:{_free_port()}'
    environment = {**os.environ, 'PYTHONPATH': os.pathsep.join((str(project), str(project / 'tests'))),
        'PYTHONDONTWRITEBYTECODE': '1', 'STOCK_RESEARCH_DATA_PROFILE': 'demo',
        'SEC_USER_AGENT': 'Synthetic recovery rehearsal contact@example.com'}
    environment.pop('COMMERCIAL_RESEARCH_MODE', None)
    with (tmp_path / 'streamlit.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, '-m', 'streamlit', 'run', str(script),
            '--server.address', '127.0.0.1', '--server.port', str(urlsplit(address).port),
            '--server.headless', 'true', '--server.fileWatcherType', 'none',
            '--browser.gatherUsageStats', 'false'], cwd=project, env=environment,
            stdout=log, stderr=subprocess.STDOUT)
        try:
            _wait_for_health(address, timeout_seconds=40)
            yield address
        finally:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


@pytest.mark.parametrize('width,height', [(1440, 1000), (390, 844)], ids=['desktop', 'phone'])
def test_private_rehearsal_provider_recovery_and_saved_monitor_replay(recovery_server, tmp_path, width, height):
    chrome = find_chrome_executable()
    if not chrome:
        pytest.skip('Chrome-compatible browser is unavailable')
    playwright = pytest.importorskip('playwright.sync_api')
    with playwright.sync_playwright() as engine:
        browser = engine.chromium.launch(executable_path=str(chrome), headless=True)
        browser_context = browser.new_context(viewport=dict(width=width, height=height),
            color_scheme='dark' if width < 640 else 'light')
        page = browser_context.new_page()
        page.set_default_timeout(30_000)
        failures, errors = [], []

        def local_only(route):
            if route.request.url.startswith(recovery_server + '/'):
                route.continue_()
            else:
                failures.append(route.request.url)
                route.abort()

        page.route('**/*', local_only)
        page.on('pageerror', lambda error: errors.append(str(error)))

        def settle():
            page.wait_for_function("""() => document.querySelector('[data-testid="stApp"]')
                ?.getAttribute('data-test-script-state') === 'notRunning'""")
            _wait_for_dom_stability(page, timeout_seconds=12, stable_checks=2)
            assert not page.get_by_test_id('stException').count()
            assert page.locator('html').evaluate('element => element.scrollWidth') == width

        def section(name):
            radio = page.get_by_role('radio', name=name, exact=True)
            page.locator('label').filter(has=radio).click()
            playwright.expect(radio).to_be_checked()
            playwright.expect(page.get_by_role('heading', name=name, exact=True)).to_be_visible(timeout=30_000)
            settle()

        def calls():
            return (tmp_path / 'provider-calls.txt').read_text().splitlines()

        def peer():
            return json.loads((tmp_path / 'peer-JPM.json').read_text())

        try:
            page.goto(recovery_server + '/?mode=research&page=company-workbench&ticker=JPM&online=1')
            research = page.get_by_role('button', name='Research company', exact=True)
            playwright.expect(research).to_be_visible(timeout=30_000)
            settle()
            research.click()
            playwright.expect(page.locator('[data-online-filing-status="1"]')).to_be_visible(timeout=30_000)
            settle()
            section('Valuation & Peers')
            valuation = page.get_by_role('region', name='Online peer valuation', exact=True)
            playwright.expect(valuation).to_contain_text('3 companies', timeout=30_000)
            accepted = peer()
            assert accepted['status'] == 'research_comparison'
            section('Research Notes')
            page.get_by_text('Saved online research · replay and compare', exact=True).click()
            page.get_by_role('button', name='Save research snapshot', exact=True).click()
            playwright.expect(page.get_by_text('Current versus latest saved: unchanged', exact=False)).to_be_visible(timeout=30_000)
            settle()
            snapshot_path, = (tmp_path / 'outputs/local/online-research-contexts').rglob('*.json')
            original_bytes = snapshot_path.read_bytes()
            snapshot = json.loads(original_bytes)
            assert snapshot['context']['peer_read_through']['status'] == 'research_comparison'

            section('Valuation & Peers')
            outage = tmp_path / 'provider-outage'
            outage.touch()
            page.get_by_role('button', name='Refresh peer valuation', exact=True).click()
            playwright.expect(valuation.get_by_role('heading', name='Relative valuation withheld', exact=True)).to_be_visible(timeout=30_000)
            settle()
            held = peer()
            assert held['status'] == 'withheld' and held['subject'] is None
            assert held['peer_median'] is held['premium_fraction'] is None
            assert 'private diagnostic' not in page.locator('body').inner_text()
            page.screenshot(path=str(tmp_path / 'provider-held.png'), full_page=True)
            before = calls()
            section('Data Sources')
            section('Valuation & Peers')
            assert calls() == before
            assert snapshot_path.read_bytes() == original_bytes
            outage.unlink()
            page.get_by_role('button', name='Refresh peer valuation', exact=True).click()
            playwright.expect(valuation).to_contain_text('3 companies', timeout=30_000)
            settle()
            recovered = peer()
            assert recovered['status'] == 'research_comparison'
            for key in ('subject', 'peers', 'excluded', 'peer_median', 'premium_fraction'):
                assert recovered[key] == accepted[key]
            page.screenshot(path=str(tmp_path / 'provider-recovered.png'), full_page=True)

            outage.touch()
            before = calls()
            query = dict(mode='research', page='monitor', return_ticker='JPM', return_section='valuation',
                return_research_cik=snapshot['sec_cik'], return_research_snapshot=snapshot['snapshot_id'])
            page.goto(recovery_server + '/?' + urlencode(query))
            playwright.expect(page.get_by_text('Snapshot ' + snapshot['snapshot_id'][:12], exact=True)).to_be_visible(timeout=30_000)
            page.get_by_role('button', name='Reopen exact saved research', exact=True).click()
            marker = 'Snapshot ' + snapshot['snapshot_id'][:12] + ' · SEC CIK ' + snapshot['sec_cik']
            playwright.expect(page.get_by_text(marker, exact=True)).to_be_visible(timeout=30_000)
            playwright.expect(valuation).to_contain_text('3 companies')
            settle()
            assert parse_qs(urlsplit(page.url).query)['research_snapshot'] == [snapshot['snapshot_id']]
            assert calls() == before and snapshot_path.read_bytes() == original_bytes
            assert_rendered_english(page.locator('body'))
            assert not failures and not errors and 'unexpected-external-request' not in calls()
            page.screenshot(path=str(tmp_path / 'outage-saved-replay.png'), full_page=True)
            (tmp_path / 'browser-proof.json').write_text(json.dumps(dict(status='passed',
                viewport=[width, height], initial='research_comparison', during_outage='withheld',
                after_retry='research_comparison', saved_snapshot=snapshot['snapshot_id'],
                immutable_saved_bytes=True, passive_provider_requests=0,
                external_browser_requests=failures, browser_errors=errors)), encoding='utf-8')
        finally:
            browser_context.close()
