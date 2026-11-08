"""Desktop/phone proof of real self-service tools using disposable SEC observations."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
from urllib.parse import parse_qs, urlsplit

import pytest

from src.public_performance_gate import _free_port, _wait_for_health, find_chrome_executable
from tests.test_research_monitor_roundtrip_browser import assert_rendered_english


CIK = '0000001234'


def run_self_service_fixture(root):
    """Run production collection/calculations; replace only external transports."""
    from src import company_research_notes, company_workbench_ui, dashboard
    from src import online_company_identity, online_company_prices, online_research_context_store
    from src import online_research_tools_ui, sec_annual_history, sec_research_review_ui
    from src.online_peer_sources import SESSION_KEY
    from tests.test_online_company_search_view import _result
    from tests.test_self_service_financial_refresh import _fetcher

    calls_path = root / 'provider-calls.txt'

    def record(source):
        with calls_path.open('a', encoding='utf-8') as handle:
            handle.write(source + '\n')

    def search(query, *, user_agent):
        assert query == 'FICT' and 'Synthetic' in user_agent
        record('search')
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        return {**_result(), 'query': query, 'observed_at': now, 'source_last_modified': now}

    production_financial = sec_annual_history.fetch_sec_online_research_view

    def financial(ticker, *, user_agent, **kwargs):
        assert ticker == 'FICT' and 'Synthetic' in user_agent
        record('financial-refresh')
        _calls, source_fetcher = _fetcher()
        def transport(url, agent):
            record('sec:' + url)
            return source_fetcher(url, agent)
        return production_financial(ticker, user_agent=user_agent,
            source_fetcher=transport, observed_at=datetime.now(timezone.utc))

    def prices(ticker, **kwargs):
        assert ticker == 'FICT'
        record('prices-unavailable')
        return dict(ticker=ticker, status='unavailable', reason='daily_prices_unavailable')

    def profile(cik, **kwargs):
        assert cik == CIK
        record('listing-profile-unavailable')
        return dict(status='unavailable', reason='sec_profile_unavailable')

    def peer(ticker, state, *, refresh_requested, expected_cik, **kwargs):
        if refresh_requested:
            assert (ticker, expected_cik) == ('FICT', CIK)
            record('peer-refresh-held')
            state[SESSION_KEY] = dict(ticker=ticker, sec_cik=CIK, status='withheld',
                reason='same_day_completed_price_and_three_references_required', peer_count=0)
        return state.get(SESSION_KEY, {'status': 'not_requested'})

    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def local_connect(sock, address):
        if isinstance(address, tuple) and address[0] not in {'127.0.0.1', '::1', 'localhost'}:
            record('unexpected-external-request')
            raise AssertionError('Self-service browser proof prohibits external providers.')
        return original_connect(sock, address)

    def local_connect_ex(sock, address):
        if isinstance(address, tuple) and address[0] not in {'127.0.0.1', '::1', 'localhost'}:
            record('unexpected-external-request')
            raise AssertionError('Self-service browser proof prohibits external providers.')
        return original_connect_ex(sock, address)

    # Persist through Streamlit reruns and isolate every private receipt/note path.
    for module in (company_research_notes, online_research_context_store,
                   online_research_tools_ui, sec_research_review_ui):
        module.PROJECT_ROOT = root
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(socket.socket, 'connect', local_connect)
        patch.setattr(socket.socket, 'connect_ex', local_connect_ex)
        patch.setattr(dashboard, 'search_sec_company_candidates', search)
        patch.setattr(sec_annual_history, 'fetch_sec_online_research_view', financial)
        patch.setattr(online_company_prices, 'fetch_online_company_prices', prices)
        patch.setattr(online_company_identity, 'fetch_sec_company_profile', profile)
        patch.setattr(company_workbench_ui, 'get_online_peer_valuation', peer)
        dashboard.main()


@pytest.fixture
def self_service_server(tmp_path):
    project = Path(__file__).resolve().parents[1]
    app = tmp_path / 'self_service_app.py'
    app.write_text('from pathlib import Path\n'
        'from tests.test_self_service_research_browser import run_self_service_fixture\n'
        'run_self_service_fixture(Path(__file__).parent)\n', encoding='utf-8')
    url = f'http://127.0.0.1:{_free_port()}'
    environment = {**os.environ, 'PYTHONPATH': str(project), 'PYTHONDONTWRITEBYTECODE': '1',
        'STOCK_RESEARCH_DATA_PROFILE': 'demo', 'SEC_USER_AGENT': 'Synthetic research contact@example.com'}
    environment.pop('COMMERCIAL_RESEARCH_MODE', None)
    with (tmp_path / 'streamlit.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, '-m', 'streamlit', 'run', str(app),
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


def _demo_bytes():
    directory = Path(__file__).resolve().parents[1] / 'data/demo'
    return {str(path.relative_to(directory)): sha256(path.read_bytes()).hexdigest()
        for path in directory.rglob('*') if path.is_file()}


@pytest.mark.parametrize('width,height', [(1440, 1000), (390, 844)], ids=['desktop', 'phone'])
def test_online_only_company_reaches_trend_scenario_notes_snapshot_and_monitor(
    self_service_server, tmp_path, width, height,
):
    """Actual browser inputs save real private records with no company CSV or network."""
    chrome = find_chrome_executable()
    if chrome is None:
        pytest.skip('Chrome-compatible browser is unavailable')
    playwright = pytest.importorskip('playwright.sync_api')
    from src.company_research_notes import CompanyNotesScope, load_company_notes
    from src.online_research_context_store import list_research_contexts
    from src.sec_research_review import review_queue
    canonical_before = _demo_bytes()
    scope = dict(profile_key='demo', ticker='FICT', sec_cik=CIK)
    summary = 'Synthetic owner hypothesis: inspect cash conversion with the next reported period.'

    def calls():
        path = tmp_path / 'provider-calls.txt'
        return path.read_text().splitlines() if path.exists() else []

    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(executable_path=str(chrome), headless=True)
        try:
            page = browser.new_page(viewport={'width': width, 'height': height},
                color_scheme='dark' if width < 640 else 'light')
            page.set_default_timeout(12_000)
            blocked, errors = [], []
            def local_only(route):
                if route.request.url.startswith(self_service_server + '/'):
                    route.continue_()
                else:
                    blocked.append(route.request.url)
                    route.abort()
            page.route('**/*', local_only)
            page.on('pageerror', lambda error: errors.append(str(error)))

            def settle():
                page.wait_for_function('''() => document.querySelector('[data-testid="stApp"]')
                    ?.getAttribute('data-test-script-state') === 'notRunning' ''', timeout=12_000)

            def surface(label):
                settle()
                assert_rendered_english(page.locator('body'))
                assert page.locator('html').evaluate('node => node.scrollWidth') == width
                assert not page.get_by_test_id('stException').count()
                assert not errors
                page.screenshot(path=str(tmp_path / f'self-service-{label}-{width}.png'), full_page=True)

            def expander(label):
                summary_node = page.locator('details > summary').filter(has=page.get_by_text(label, exact=True))
                playwright.expect(summary_node).to_have_count(1)
                if summary_node.locator('..').get_attribute('open') is None:
                    summary_node.click()
                return summary_node.last.locator('..')

            def section(label):
                radio = page.get_by_role('radio', name=label, exact=True)
                page.locator('label').filter(has=radio).click()
                playwright.expect(radio).to_be_checked()
                playwright.expect(page.locator('.st-key-company-section-body').get_by_role('heading', name=label, exact=True)).to_be_visible()
                settle()

            page.goto(self_service_server + '/?mode=research&page=research-desk')
            query = page.get_by_role('textbox', name='Company name or ticker', exact=True)
            playwright.expect(query).to_be_visible()
            assert calls() == []
            query.fill('FICT')
            page.get_by_role('button', name='Search company', exact=True).click()
            results = page.get_by_role('region', name='SEC online company results', exact=True)
            playwright.expect(results).to_contain_text('No local ticker row')
            results.get_by_role('link', name='Open company evidence', exact=True).click()
            research = page.get_by_role('button', name='Research company', exact=True)
            playwright.expect(research).to_be_visible()
            # The result link can open a fresh app session, which verifies the
            # directory identity again before any company observations exist.
            assert calls() in (['search'], ['search', 'search'])
            research.click()
            playwright.expect(page.locator('[data-online-filing-status="1"]')).to_contain_text('Annual 2025-12-31: corroborated')
            # Source failures are independent: current SEC revenue is still useful.
            playwright.expect(page.get_by_role('region', name='Company Brief', exact=True)).to_contain_text('FICT')
            original_calls = calls()
            assert original_calls.count('financial-refresh') == 1
            assert sum(call.startswith('sec:') for call in original_calls) == 3
            assert original_calls.count('peer-refresh-held') == 1
            assert original_calls.count('prices-unavailable') == 1
            assert 'unexpected-external-request' not in original_calls
            surface('researched')

            section('Financial Trends')
            trend = expander('Business Trend · online reported periods')
            playwright.expect(trend).to_contain_text('25.0%')
            playwright.expect(trend).to_contain_text('23.00 USD')
            playwright.expect(trend).to_contain_text('not issuer-defined free cash flow or FCFF')
            surface('trend')

            section('Valuation & Peers')
            scenario = expander('Scenario Lab · explicit assumptions')
            run = scenario.get_by_role('button', name='Calculate hypothetical enterprise value', exact=True)
            run.click()
            metric = page.get_by_test_id('stMetric').filter(has_text='Hypothetical enterprise value')
            playwright.expect(metric).to_have_count(1)
            before = metric.get_by_test_id('stMetricValue').inner_text()
            margin = page.get_by_role('spinbutton', name='FCFF margin assumption (%)', exact=True)
            margin.fill('25')
            margin.press('Enter')
            run.click()
            playwright.expect(metric.get_by_test_id('stMetricValue')).not_to_have_text(before)
            after = metric.get_by_test_id('stMetricValue').inner_text()
            assert float(after.removeprefix('USD ').replace(',', '')) > float(before.removeprefix('USD ').replace(',', ''))
            growth = page.get_by_role('spinbutton', name='Revenue growth assumption (%)', exact=True)
            growth.fill('22')
            growth.press('Enter')
            run.click()
            playwright.expect(metric.get_by_test_id('stMetricValue')).not_to_have_text(after)
            playwright.expect(scenario).to_contain_text('not a price target')
            assert calls() == original_calls
            surface('scenario')

            section('Research Notes')
            author = expander('Add a reviewed research record')
            now = datetime.now(timezone.utc)
            values = {'Thesis Id': 'self-service-browser-thesis', 'Summary': summary,
                'Effective At': (now - timedelta(hours=1)).isoformat(), 'Reviewer': 'Synthetic browser owner',
                'Confidence': '0.50', 'Review Due Date': (now + timedelta(days=28)).date().isoformat()}
            for label, value in values.items():
                author.get_by_role('textbox', name=label, exact=True).fill(value)
            author.get_by_role('button', name='Validate and preview', exact=True).click()
            playwright.expect(author.get_by_role('heading', name='Exact append-only preview', exact=True)).to_be_visible()
            assert not list(tmp_path.rglob('research_thesis_journal.csv')), 'Preview must not save a record'
            confirmation = author.get_by_role('checkbox', name='I reviewed this exact record and its source evidence', exact=True)
            confirmation.focus()
            page.keyboard.press('Space')
            playwright.expect(confirmation).to_be_checked()
            author.get_by_role('button', name='Confirm and save', exact=True).click()
            playwright.expect(page.get_by_text('Record saved', exact=True)).to_be_visible()
            settle()
            playwright.expect(page.get_by_text(summary, exact=True).first).to_be_visible()
            notes = load_company_notes(CompanyNotesScope(**scope), project_root=tmp_path)
            assert len(notes.journal) == 1 and notes.journal[0].summary == summary
            assert (notes.scope.profile_key, notes.scope.ticker, notes.scope.sec_cik) == ('demo', 'FICT', CIK)
            forward = expander('Forward View and Decision Lab')
            playwright.expect(forward).to_contain_text('Next research action')
            surface('notes')

            snapshots = expander('Saved online research · replay and compare')
            page.get_by_role('button', name='Save research snapshot', exact=True).click()
            playwright.expect(snapshots).to_contain_text('Current versus latest saved: unchanged')
            settle()
            first = list_research_contexts(**scope, project_root=tmp_path)
            assert len(first) == 1
            saved = first[0]
            assert saved['context']['scenario']['assumptions']['fcf_margin'] == 0.25
            assert saved['context']['scenario']['assumptions']['revenue_growth'] == 0.22
            assert saved['context']['notes']['journal'][0]['summary'] == summary
            assert saved['historical'] and not saved['current']
            expander('Saved online research · replay and compare')
            page.get_by_role('button', name='Save research snapshot', exact=True).click()
            playwright.expect(snapshots).to_contain_text('Current versus latest saved: unchanged')
            settle()
            assert list_research_contexts(**scope, project_root=tmp_path) == first
            assert not list((tmp_path / 'outputs/local/sec-research-reviews').rglob('*.json'))
            surface('saved')
            snapshots.get_by_role('button', name='Open Monitor', exact=True).click()
            playwright.expect(page.get_by_role('heading', name='Monitor', exact=True)).to_be_visible()
            playwright.expect(page.get_by_role('heading', name='Saved online research updates', exact=True)).to_be_visible()
            playwright.expect(page.get_by_role('heading', name='Saved SEC evidence review queue', exact=True)).to_have_count(0)
            assert review_queue(tmp_path, 'demo')['companies'] == 0
            playwright.expect(page.get_by_role('combobox', name='Saved online research company', exact=True)).to_have_value('FICT · CIK ' + CIK)
            assert calls() == original_calls
            surface('monitor')
            page.get_by_role('button', name='Reopen exact saved research', exact=True).click()
            playwright.expect(page.get_by_text(re.compile(r'^Historical replay · '))).to_be_visible()
            route = parse_qs(urlsplit(page.url).query)
            assert route['ticker'] == ['FICT'] and route['research_cik'] == [CIK]
            assert route['research_snapshot'] == [saved['snapshot_id']] and route['section'] == ['notes']
            playwright.expect(page.get_by_text(summary, exact=True).first).to_be_visible()
            assert calls() == original_calls, 'Historical return must not fetch source observations'
            assert list_research_contexts(**scope, project_root=tmp_path) == first
            surface('historical-return')
            section('Valuation & Peers')
            expander('Scenario Lab · explicit assumptions')
            playwright.expect(page.get_by_role('spinbutton', name='Revenue growth assumption (%)', exact=True)).to_have_value(re.compile(r'^22(?:\.0+)?$'))
            assert calls() == original_calls, 'Draft controls must survive the exact issuer return without another source request'
            surface('retained-assumptions')
            assert not blocked and not errors
        except Exception:
            page.screenshot(path=str(tmp_path / f'self-service-failure-{width}.png'), full_page=True)
            (tmp_path / f'self-service-failure-{width}.txt').write_text(page.url + '\n\n' + page.locator('body').inner_text(), encoding='utf-8')
            raise
        finally:
            browser.close()
    assert _demo_bytes() == canonical_before
    assert not (tmp_path / 'data').exists(), 'The online workflow must not prepare company CSV inputs'
