"""Desktop and phone replay of a large, constructed foreign issuer context."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from urllib.parse import parse_qs, urlsplit

import pytest

from src.public_performance_gate import _free_port, _wait_for_health, find_chrome_executable


SCOPE = dict(profile_key='personal/large-snapshot-test', ticker='TSM', sec_cik='0001046179')
NOW = datetime(2026, 11, 7, 12, tzinfo=timezone.utc)


def _large_context():
    """Produce normalized history from synthetic submissions and native IFRS data."""
    from src.online_filing_context import build_filing_inventory
    from src.online_research_tools import build_online_research_context
    from src.sec_foreign_financials import build_sec_foreign_financials

    ticker, cik = SCOPE['ticker'], SCOPE['sec_cik']
    observed = NOW.isoformat()
    profile_url = f'https://data.sec.gov/submissions/CIK{cik}.json'
    facts_url = f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'
    fields = ('accessionNumber', 'form', 'reportDate', 'filingDate', 'acceptanceDateTime', 'primaryDocument')
    annual = [
        (cik + '-25-000001', '20-F', '2024-12-31', '2025-04-16', '2025-04-16T12:00:00Z', 'annual-2024.htm'),
        (cik + '-26-000001', '20-F', '2025-12-31', '2026-04-16', '2026-04-16T12:00:00Z', 'annual-2025.htm'),
    ]
    events = []
    for index in range(650):
        day = NOW.date() - timedelta(days=index + 1)
        event = day.isoformat()
        events.append((f'{cik}-{day.year % 100:02d}-{index + 100:06d}', '6-K', event, event,
                       event + 'T12:00:00Z', f'current-report-{index:04d}.htm'))
    submissions = dict(cik=int(cik), tickers=[ticker], name='Constructed foreign issuer', sic='3674',
                       entityType='operating', fiscalYearEnd='1231',
                       filings={'recent': {key: list(values) for key, values in zip(fields, zip(*annual, *events))}})
    receipt = dict(status='ready', source_url=profile_url, observed_at=observed, source_last_modified=None,
                   payload_sha256=sha256(json.dumps(submissions).encode()).hexdigest(), payload=submissions)
    inventory = build_filing_inventory(receipt, ticker=ticker, expected_cik=cik, as_of=NOW)
    assert len(inventory['earnings_reports']) == len(events)

    # A newer annual filing exists. Only the historical annual TWD amount has
    # compatible structured evidence. The 6-K report dates carry no durations.
    facts = dict(cik=int(cik), entityName='Constructed foreign issuer', facts={'ifrs-full': {
        'Revenue': {'units': {'TWD': [dict(start='2024-01-01', end=annual[0][2], filed=annual[0][3],
                                          form='20-F', accn=annual[0][0], val=123_000)]}},
    }})
    digest = sha256(json.dumps(facts).encode()).hexdigest()
    identity = dict(status='source_matched', ticker=ticker, sec_cik=cik, source_url=facts_url,
                    observed_at=observed, payload_sha256=digest,
                    association_source_url='https://www.sec.gov/files/company_tickers.json',
                    association_observed_at=observed, association_payload_sha256='a' * 64)
    foreign = build_sec_foreign_financials(ticker, facts, expected_cik=cik, observed_at=observed,
                                          source_url=facts_url, payload_sha256=digest)
    financial = dict(ticker=ticker, sec_cik=cik, status='unavailable', companyfacts_identity=identity,
                     foreign_financials=foreign, filing_inventory=inventory)
    return build_online_research_context(financial, {}, ticker=ticker, profile_key=SCOPE['profile_key'],
                                         expected_cik=cik, as_of=NOW), financial


def _run_app(root):
    """Provide a deterministic context to the normal research Notes and Monitor components."""
    import streamlit as st
    from src import online_research_context_store, online_research_tools_ui

    def local_only(function):
        def connect(sock, address):
            if isinstance(address, tuple) and address[0] not in {'127.0.0.1', '::1', 'localhost'}:
                (root / 'external-request.txt').write_text(repr(address), encoding='utf-8')
                raise AssertionError('Constructed replay test attempted external transport')
            return function(sock, address)
        return connect

    st.set_page_config(page_title='Research snapshot browser test', layout='wide')
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(online_research_context_store, 'PROJECT_ROOT', root)
        patch.setattr(online_research_tools_ui, 'PROJECT_ROOT', root)
        patch.setattr(socket.socket, 'connect', local_only(socket.socket.connect))
        patch.setattr(socket.socket, 'connect_ex', local_only(socket.socket.connect_ex))
        if st.query_params.get('page') == 'monitor':
            online_research_tools_ui.render_online_research_monitor(st, profile_key=SCOPE['profile_key'])
        else:
            if 'large-snapshot-test-context' not in st.session_state:
                st.session_state['large-snapshot-test-context'] = _large_context()
            context, financial = st.session_state['large-snapshot-test-context']
            st.markdown('### Research Notes')
            online_research_tools_ui.render_online_tools(st, 'notes', dict(research_context=context, financial=financial))


@pytest.fixture
def large_snapshot_server(tmp_path):
    project = Path(__file__).resolve().parents[1]
    script = tmp_path / 'app.py'
    script.write_text('from pathlib import Path\n'
                      'from tests.test_large_research_snapshot_browser import _run_app\n'
                      '_run_app(Path(__file__).parent)\n', encoding='utf-8')
    port = _free_port()
    url = f'http://127.0.0.1:{port}'
    environment = {**os.environ, 'PYTHONPATH': str(project), 'PYTHONDONTWRITEBYTECODE': '1'}
    environment.pop('COMMERCIAL_RESEARCH_MODE', None)
    with (tmp_path / 'streamlit.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, '-m', 'streamlit', 'run', str(script),
            '--server.address', '127.0.0.1', '--server.port', str(port), '--server.headless', 'true',
            '--server.fileWatcherType', 'none', '--browser.gatherUsageStats', 'false'], cwd=project,
            env=environment, stdout=log, stderr=subprocess.STDOUT)
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


@pytest.mark.parametrize('width,height', [(1440, 1000), (390, 844)], ids=['desktop', 'phone'])
def test_large_foreign_snapshot_saves_and_reopens_exactly_from_monitor(large_snapshot_server, tmp_path, width, height):
    from src.online_research_context_store import list_research_contexts, load_research_context

    chrome = find_chrome_executable()
    if chrome is None:
        pytest.skip('Chrome-compatible browser is unavailable')
    playwright = pytest.importorskip('playwright.sync_api')
    original, _ = _large_context()
    size = len(json.dumps(original, separators=(',', ':'), allow_nan=False).encode())
    assert 512 * 1024 < size < 1024 * 1024
    assert original['business_trend']['periods'][0]['currency'] == 'TWD'
    assert original['filing_coverage']['current']['annual']['status'] == 'facts_pending'
    assert original['filing_coverage']['current']['quarterly']['status'] == 'withheld'
    assert original['scenario_base']['status'] == 'withheld'
    assert original['peer_read_through']['status'] != 'research_comparison'

    blocked, errors = [], []
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(executable_path=str(chrome), headless=True)
        page = browser.new_page(viewport={'width': width, 'height': height}, color_scheme='dark' if width < 640 else 'light')
        page.set_default_timeout(15_000)

        def local_only(route):
            if route.request.url.startswith(large_snapshot_server + '/'):
                route.continue_()
            else:
                blocked.append(route.request.url)
                route.abort()

        def verify_surface():
            page.wait_for_function('''() => document.querySelector('[data-testid="stApp"]')
                ?.getAttribute('data-test-script-state') === 'notRunning' ''')
            assert page.locator('html').evaluate('element => element.scrollWidth') == width
            assert not page.get_by_test_id('stException').count()

        page.route('**/*', local_only)
        page.on('pageerror', lambda error: errors.append(str(error)))
        try:
            page.goto(large_snapshot_server + '/?mode=research&page=company-workbench&ticker=TSM&section=notes')
            saved = page.locator('details').filter(has=page.get_by_text('Saved online research · replay and compare', exact=True))
            saved.locator('summary').click()
            save = saved.get_by_role('button', name='Save research snapshot', exact=True)
            save.click()
            unchanged = saved.get_by_text('Current versus latest saved: unchanged', exact=True)
            playwright.expect(unchanged).to_be_visible()
            verify_surface()
            snapshots = list_research_contexts(**SCOPE, project_root=tmp_path)
            assert len(snapshots) == 1
            snapshot = snapshots[0]
            assert snapshot['context'] == original
            assert snapshot['historical'] is True and snapshot['current'] is False
            paths = list((tmp_path / 'outputs/local/online-research-contexts').rglob('*.json'))
            assert len(paths) == 1
            original_bytes = paths[0].read_bytes()

            save.click()
            playwright.expect(unchanged).to_be_visible()
            verify_surface()
            assert list_research_contexts(**SCOPE, project_root=tmp_path) == snapshots
            assert paths[0].read_bytes() == original_bytes

            saved.get_by_role('button', name='Open Monitor', exact=True).click()
            playwright.expect(page.get_by_role('heading', name='Saved online research updates', exact=True)).to_be_visible()
            playwright.expect(page.get_by_text('validated current annual revenue required', exact=True)).to_be_visible()
            verify_surface()
            page.screenshot(path=str(tmp_path / 'monitor.png'), full_page=True)

            page.get_by_role('button', name='Reopen exact saved research', exact=True).click()
            playwright.expect(saved.get_by_text('Historical replay · ', exact=False)).to_be_visible()
            playwright.expect(unchanged).to_be_visible()
            verify_surface()
            route = parse_qs(urlsplit(page.url).query)
            assert route == dict(mode=['research'], page=['company-workbench'], ticker=['TSM'], section=['notes'],
                                 research_cik=[SCOPE['sec_cik']], research_snapshot=[snapshot['snapshot_id']])
            assert load_research_context(snapshot['snapshot_id'], **SCOPE, project_root=tmp_path) == snapshot
            assert paths[0].read_bytes() == original_bytes
            assert not (tmp_path / 'external-request.txt').exists()
            assert not blocked and not errors
            page.screenshot(path=str(tmp_path / 'historical-return.png'), full_page=True)
        finally:
            browser.close()
