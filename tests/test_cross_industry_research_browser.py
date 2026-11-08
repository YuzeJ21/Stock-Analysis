"""Real dashboard checks across the fixed sample with no external transport."""
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from time import monotonic, sleep
from urllib.parse import parse_qs, urlsplit

import pytest

from src.public_performance_gate import _free_port, _wait_for_health, _wait_for_dom_stability, find_chrome_executable
from tests.test_research_monitor_roundtrip_browser import assert_rendered_english


@pytest.fixture
def cross_industry_server(tmp_path):
    project = Path(__file__).resolve().parents[1]
    script = tmp_path / 'cross_industry_app.py'
    script.write_text('from pathlib import Path\n'
        'from tests.cross_industry_browser_fixture import run_cross_industry_fixture\n'
        'run_cross_industry_fixture(Path(__file__).parent)\n', encoding='utf-8')
    url = f'http://127.0.0.1:{_free_port()}'
    environment = {**os.environ, 'PYTHONPATH': os.pathsep.join((str(project), str(project / 'tests'))),
        'PYTHONDONTWRITEBYTECODE': '1', 'STOCK_RESEARCH_DATA_PROFILE': 'demo',
        'SEC_USER_AGENT': 'Synthetic research browser contact@example.com'}
    environment.pop('COMMERCIAL_RESEARCH_MODE', None)
    with (tmp_path / 'streamlit.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, '-m', 'streamlit', 'run', str(script),
            '--server.address', '127.0.0.1', '--server.port', str(urlsplit(url).port),
            '--server.headless', 'true', '--server.fileWatcherType', 'none',
            '--browser.gatherUsageStats', 'false'], cwd=project, env=environment,
            stdout=log, stderr=subprocess.STDOUT)
        try:
            _wait_for_health(url, timeout_seconds=20)
            yield url
        finally:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def _canonical():
    root = Path(__file__).resolve().parents[1] / 'data/demo'
    return {str(path.relative_to(root)): sha256(path.read_bytes()).hexdigest()
        for path in root.rglob('*') if path.is_file()}


@pytest.mark.parametrize('width,height', [(1440, 1000), (390, 844)], ids=['desktop', 'phone'])
def test_failure_inclusive_study_and_four_company_workflows(cross_industry_server, tmp_path, width, height):
    chrome = find_chrome_executable()
    if chrome is None:
        pytest.skip('Chrome-compatible browser is unavailable')
    playwright = pytest.importorskip('playwright.sync_api')
    canonical = _canonical()
    def calls():
        path = tmp_path / 'provider-calls.txt'
        return path.read_text().splitlines() if path.exists() else []
    def study():
        return json.loads((tmp_path / 'study-view.json').read_text())
    def context(ticker):
        return json.loads((tmp_path / ('workbench-' + ticker + '.json')).read_text())

    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(executable_path=str(chrome), headless=True)
        page = browser.new_page(viewport={'width': width, 'height': height},
            color_scheme='dark' if width < 640 else 'light')
        page.set_default_timeout(12_000)
        blocked, errors = [], []
        def local_only(route):
            if route.request.url.startswith(cross_industry_server + '/'):
                route.continue_()
            else:
                blocked.append(route.request.url)
                route.abort()
        page.route('**/*', local_only)
        page.on('pageerror', lambda error: errors.append(str(error)))
        def settle():
            page.wait_for_function('''() => document.querySelector('[data-testid="stApp"]')
                ?.getAttribute('data-test-script-state') === 'notRunning' ''', timeout=12_000)
        def surface(name):
            settle()
            assert_rendered_english(page.locator('body'))
            assert page.locator('html').evaluate('element => element.scrollWidth') == width
            assert not page.get_by_test_id('stException').count()
            assert not blocked and not errors
            page.screenshot(path=str(tmp_path / f'cross-industry-{name}-{width}.png'), full_page=True)
        def expand(name):
            summary = page.locator('details > summary').filter(has=page.get_by_text(name, exact=True))
            playwright.expect(summary).to_have_count(1)
            if summary.locator('..').get_attribute('open') is None:
                summary.click()
            return summary.last.locator('..')
        def choose_company(value):
            _wait_for_dom_stability(page, timeout_seconds=8, stable_checks=2)
            radio = page.get_by_role('radio', name=value, exact=True)
            page.locator('.st-key-self-service-coverage-company label').filter(has=radio).click()
            playwright.expect(radio).to_be_checked()
            settle()
        def section(name):
            radio = page.get_by_role('radio', name=name, exact=True)
            page.locator('label').filter(has=radio).click()
            playwright.expect(radio).to_be_checked()
            playwright.expect(page.locator('.st-key-company-section-body').get_by_role('heading', name=name, exact=True)).to_be_visible()
            settle()
        try:
            page.goto(cross_industry_server + '/?mode=research&page=discover')
            expand('Coverage studies')
            page.get_by_role('tab', name='Self-service', exact=True).click()
            region = page.get_by_role('region', name='Self-service research coverage', exact=True)
            playwright.expect(region).to_contain_text('Unattempted: 12 / 12.')
            settle()
            assert calls() == []
            view = study()
            assert view['requested_count'] == view['pending_count'] == 12 and view['attempted_count'] == 0
            assert [group['requested_count'] for group in view['by_group']] == [3, 3, 3, 3]
            assert all(row['status'] == 'unattempted' for row in view['rows'])
            surface('unattempted')
            page.get_by_role('button', name='Inspect next company', exact=True).click()
            playwright.expect(region).to_contain_text('Unattempted: 11 / 12.')
            settle()
            assert study()['attempted_count'] == 1 and study()['requested_count'] == 12
            first_calls = calls()
            choose_company('JPM')
            playwright.expect(page.get_by_role('region', name='Selected company capabilities', exact=True)).to_contain_text('Unattempted')
            assert calls() == first_calls, 'Selecting an unattempted company must not request sources'
            for attempted in range(2, 13):
                page.get_by_role('button', name='Inspect next company', exact=True).click()
                playwright.expect(region).to_contain_text(f'Unattempted: {12-attempted} / 12.')
                settle()
                assert study()['attempted_count'] == attempted and study()['requested_count'] == 12
            playwright.expect(page.get_by_role('radio', name='JPM', exact=True)).to_be_checked()
            playwright.expect(page.get_by_role('heading', name='JPM · Banks', exact=True)).to_be_visible()
            final_study = study()
            assert final_study['capability_status_counts']['scenario_eligibility']['excluded'] == 3
            assert final_study['capability_status_counts']['matched_identity']['failed'] == 1
            assert final_study['counts']['dated_price'] == final_study['counts']['peer_comparison'] == 0
            assert not final_study['user_notes_read'] and not final_study['user_store_written']
            assert final_study['saved_readiness_promoted'] is False and final_study['commercial_eligible'] is False
            assert not (tmp_path / 'outputs').exists(), 'Study probes must not save into the app user store'
            (tmp_path / 'study-complete.json').write_text(json.dumps(final_study, indent=2), encoding='utf-8')
            before_details = calls()
            selected = page.get_by_role('region', name='Selected company capabilities', exact=True)
            playwright.expect(selected).to_contain_text('Excluded')
            playwright.expect(selected).to_contain_text('financial sector operating company dcf excluded')
            detail = expand('Reporting periods and original source receipts')
            playwright.expect(detail).to_contain_text('Observed 2026-')
            playwright.expect(detail).to_contain_text('SHA-256')
            playwright.expect(detail.get_by_role('link', name='Original source', exact=True).first).to_have_attribute('href', 'https://data.sec.gov/api/xbrl/companyfacts/CIK0000001004.json')
            method = region.locator('summary').filter(has_text='All tool counts and method exclusions')
            method.click()
            playwright.expect(region).to_contain_text('3 excluded')
            assert calls() == before_details
            surface('complete-bank-exclusion')
            previous_requests = study()['source_request_count']
            page.get_by_role('button', name='Recheck company', exact=True).click()
            deadline = monotonic() + 12
            while study()['source_request_count'] == previous_requests and monotonic() < deadline:
                sleep(0.05)
            assert study()['source_request_count'] > previous_requests
            _wait_for_dom_stability(page, timeout_seconds=8, stable_checks=2)
            settle()
            # Fresh source metadata, unchanged 12-company denominator.
            playwright.expect(region).to_contain_text('Unattempted: 0 / 12.')
            assert study()['attempted_count'] == 12 and len(calls()) > len(before_details)
            assert 'sec:https://data.sec.gov/api/xbrl/companyfacts/CIK0000001004.json' in calls()[len(before_details):]
            before_reset = calls()
            page.get_by_role('button', name='Restart study', exact=True).click()
            playwright.expect(region).to_contain_text('Unattempted: 12 / 12.')
            settle()
            assert study()['attempted_count'] == 0 and calls() == before_reset
            surface('restart')

            for ticker in ('NVDA', 'JPM', 'DUK', 'SAP'):
                page.goto(cross_industry_server + f'/?mode=research&page=company-workbench&ticker={ticker}&online=1')
                research = page.get_by_role('button', name='Research company', exact=True)
                playwright.expect(research).to_be_visible()
                research.click()
                playwright.expect(page.locator('[data-online-filing-status="1"]')).to_be_visible()
                settle()
                source_calls = calls()
                actual = context(ticker)
                if ticker == 'DUK':
                    playwright.expect(page.locator('[data-online-filing-status="1"]')).to_contain_text('Quarterly 2026-09-30: facts pending')
                    assert actual['filing_coverage']['current']['quarterly']['status'] == 'facts_pending'
                    section('Financial Trends')
                    expand('Business Trend · online reported periods')
                    assert all(not row['current'] for row in context(ticker)['business_trend']['periods'] if row['kind'] == 'quarterly')
                elif ticker == 'SAP':
                    section('Financial Trends')
                    trend = expand('Business Trend · online reported periods')
                    playwright.expect(trend).to_contain_text('EUR')
                    annual = [row for row in actual['business_trend']['periods'] if row['kind'] == 'annual']
                    assert annual and {row['currency'] for row in annual} == {'EUR'}
                    assert annual[-1]['fields']['revenue']['value'] == 100
                    section('Valuation & Peers')
                    scenario = expand('Scenario Lab · explicit assumptions')
                    scenario.get_by_role('button', name='Calculate hypothetical enterprise value', exact=True).click()
                    playwright.expect(scenario.get_by_text('Scenario unavailable:', exact=False)).to_be_visible()
                    playwright.expect(scenario).to_contain_text('operating company classification required')
                    assert context(ticker)['scenario_base']['status'] == 'withheld'
                    playwright.expect(page.get_by_test_id('stMetric').filter(has_text='Hypothetical enterprise value')).to_have_count(0)
                else:
                    section('Valuation & Peers')
                    scenario = expand('Scenario Lab · explicit assumptions')
                    scenario.get_by_role('button', name='Calculate hypothetical enterprise value', exact=True).click()
                    if ticker == 'JPM':
                        playwright.expect(scenario.get_by_text('Scenario unavailable:', exact=False)).to_be_visible()
                        playwright.expect(scenario).to_contain_text('financial sector operating company dcf excluded')
                        assert context(ticker)['scenario_base']['status'] == 'excluded'
                        playwright.expect(page.get_by_test_id('stMetric').filter(has_text='Hypothetical enterprise value')).to_have_count(0)
                    else:
                        metric = page.get_by_test_id('stMetric').filter(has_text='Hypothetical enterprise value')
                        playwright.expect(metric).to_contain_text('USD')
                        assert context(ticker)['scenario']['status'] == 'calculated'
                surface(ticker.lower())
                assert calls() == source_calls, 'Workbench tools and holds must reuse current observations'
                if ticker == 'NVDA':
                    section('Research Notes')
                    snapshot = expand('Saved online research · replay and compare')
                    snapshot.get_by_role('button', name='Save research snapshot', exact=True).click()
                    playwright.expect(snapshot).to_contain_text('Current versus latest saved: unchanged')
                    settle()
                    snapshot.get_by_role('button', name='Open Monitor', exact=True).click()
                    playwright.expect(page.get_by_role('heading', name='Saved online research updates', exact=True)).to_be_visible()
                    page.get_by_role('button', name='Reopen exact saved research', exact=True).click()
                    historical = page.get_by_text('Historical replay · ', exact=False)
                    playwright.expect(historical).to_be_visible()
                    historical.scroll_into_view_if_needed()
                    query = parse_qs(urlsplit(page.url).query)
                    assert query['ticker'] == ['NVDA'] and len(query['research_snapshot'][0]) == 64
                    assert calls() == source_calls
                    surface('nvda-replay')
            assert not blocked and not errors and 'unexpected-external-request' not in calls()
        except Exception:
            page.screenshot(path=str(tmp_path / f'cross-industry-failure-{width}.png'), full_page=True)
            (tmp_path / f'cross-industry-failure-{width}.txt').write_text(page.url + '\n\n' + page.locator('body').inner_text(), encoding='utf-8')
            raise
        finally:
            browser.close()
    assert _canonical() == canonical and not (tmp_path / 'data').exists()
    assert not list(tmp_path.rglob('research_thesis_journal.csv'))
    destination = Path('/tmp/cross-industry-browser-proof') / str(width)
    destination.mkdir(parents=True, exist_ok=True)
    for path in tmp_path.glob('cross-industry-*.png'):
        shutil.copy2(path, destination / path.name)
    for name in ('study-complete.json', 'provider-calls.txt', 'streamlit.log', 'radio-events.jsonl'):
        shutil.copy2(tmp_path / name, destination / name)
    for ticker in ('NVDA', 'JPM', 'DUK', 'SAP'):
        shutil.copy2(tmp_path / ('workbench-' + ticker + '.json'), destination / ('workbench-' + ticker + '.json'))
