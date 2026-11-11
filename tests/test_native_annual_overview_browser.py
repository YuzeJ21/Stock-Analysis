"""Desktop and phone proof of the native annual workflow from Discover."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from urllib.parse import urlsplit

import pytest

from src.public_performance_gate import _free_port, _wait_for_health, find_chrome_executable
from tests.test_research_monitor_roundtrip_browser import assert_rendered_english
from tests.test_self_service_research_browser import _demo_bytes


def run_native_annual_fixture(root):
    from src import company_research_notes, company_workbench_ui, dashboard
    from src import online_company_identity, online_company_prices, online_research_context_store
    from src import online_research_tools_ui, sec_annual_history, sec_research_review_ui
    from src.online_peer_sources import get_online_peer_valuation
    from src.providers.sec_company_discovery import SEC_COMPANY_DIRECTORY_URL, search_sec_company_candidates
    from tests.test_sec_online_annual_evidence import CIK, SOURCE, SUB, _sources

    def record(source):
        with (root / 'provider-calls.txt').open('a', encoding='utf-8') as handle:
            handle.write(source + '\n')

    def search_transport(url, _agent):
        assert url == SEC_COMPANY_DIRECTORY_URL
        record('search')
        return json.dumps(dict(fields=['cik', 'name', 'ticker', 'exchange'],
            data=[[1234, 'Constructed native annual issuer', 'FICT', 'Nasdaq']])).encode(), {}

    def search(query, *, user_agent):
        return search_sec_company_candidates(query, user_agent=user_agent, fetcher=search_transport)

    production_financial = sec_annual_history.fetch_sec_online_research_view

    def financial(ticker, *, user_agent, **kwargs):
        assert ticker == 'FICT'
        sources = _sources()
        recent = sources[SUB]['filings']['recent']
        prior = dict(accessionNumber='0000004321-25-000001', reportDate='2024-12-31',
            filingDate='2025-08-01', acceptanceDateTime='2025-08-01T12:00:00Z',
            form='20-F', primaryDocument='fict-20241231.htm', isInlineXBRL=1, isXBRL=1)
        for key, value in prior.items():
            recent[key].append(value)
        sources[SOURCE] = sources[SOURCE].replace('ifrs:RevenueFromContractsWithCustomers', 'ifrs:Revenue')

        def transport(url, _agent):
            record('sec:' + url)
            data = sources[url]
            return (data.encode() if isinstance(data, str) else json.dumps(data).encode()), {}, url

        return production_financial(ticker, user_agent=user_agent, source_fetcher=transport,
                                    observed_at=datetime.now(timezone.utc))

    def prices(ticker, **kwargs):
        assert ticker == 'FICT'
        record('prices-unavailable')
        return dict(ticker=ticker, status='unavailable', reason='daily_prices_unavailable')

    def profile(cik, **kwargs):
        assert cik == CIK
        record('listing-profile-unavailable')
        return dict(status='unavailable', reason='sec_profile_unavailable')

    def classification(**kwargs):
        record('classification-unavailable')
        return dict(status='unavailable', reason='source_unavailable')

    def peer(ticker, state, **kwargs):
        return get_online_peer_valuation(ticker, state,
            dependencies={'classification': classification}, **kwargs)

    def local_only(original):
        def connect(sock, address):
            if isinstance(address, tuple) and address[0] not in {'127.0.0.1', '::1', 'localhost'}:
                record('unexpected-external-request')
                raise AssertionError('Constructed native annual proof prohibits external providers.')
            return original(sock, address)
        return connect

    for module in (company_research_notes, online_research_context_store,
                   online_research_tools_ui, sec_research_review_ui):
        module.PROJECT_ROOT = root
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(socket.socket, 'connect', local_only(socket.socket.connect))
        patch.setattr(socket.socket, 'connect_ex', local_only(socket.socket.connect_ex))
        patch.setattr(dashboard, 'search_sec_company_candidates', search)
        patch.setattr(sec_annual_history, 'fetch_sec_online_research_view', financial)
        patch.setattr(online_company_prices, 'fetch_online_company_prices', prices)
        patch.setattr(online_company_identity, 'fetch_sec_company_profile', profile)
        patch.setattr(company_workbench_ui, 'get_online_peer_valuation', peer)
        dashboard.main()


@pytest.fixture
def native_annual_server(tmp_path):
    project = Path(__file__).resolve().parents[1]
    app = tmp_path / 'native_annual_app.py'
    app.write_text('from pathlib import Path\n'
        'from tests.test_native_annual_overview_browser import run_native_annual_fixture\n'
        'run_native_annual_fixture(Path(__file__).parent)\n', encoding='utf-8')
    url = f'http://127.0.0.1:{_free_port()}'
    environment = {**os.environ,
        'PYTHONPATH': os.pathsep.join((str(project), str(project / 'tests'))),
        'PYTHONDONTWRITEBYTECODE': '1', 'STOCK_RESEARCH_DATA_PROFILE': 'demo',
        'SEC_USER_AGENT': 'Constructed native annual browser research contact'}
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


@pytest.mark.parametrize('width,height', [(1440, 1000), (390, 844)], ids=['desktop', 'phone'])
def test_unfamiliar_company_overview_connects_native_filing_peer_hold_and_gaps(
    native_annual_server, tmp_path, width, height,
):
    from tests.test_sec_online_annual_evidence import FACTS, MAP, SOURCE, SUB

    chrome = find_chrome_executable()
    if chrome is None:
        pytest.skip('Chrome-compatible browser is unavailable')
    playwright = pytest.importorskip('playwright.sync_api')
    canonical = _demo_bytes()
    path = tmp_path / 'provider-calls.txt'

    def calls():
        return path.read_text().splitlines() if path.exists() else []

    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(executable_path=str(chrome), headless=True)
        try:
            page = browser.new_page(viewport={'width': width, 'height': height},
                                    color_scheme='dark' if width < 640 else 'light')
            page.set_default_timeout(12_000)
            blocked, errors = [], []

            def local_only(route):
                if route.request.url.startswith(native_annual_server + '/'):
                    route.continue_()
                else:
                    blocked.append(route.request.url)
                    route.abort()

            page.route('**/*', local_only)
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(native_annual_server + '/?mode=research&page=discover')
            search = page.get_by_role('textbox', name='Company name or ticker', exact=True)
            playwright.expect(search).to_be_visible()
            assert calls() == []
            search.fill('FICT')
            page.get_by_role('button', name='Search company', exact=True).click()
            results = page.get_by_role('region', name='SEC online company results', exact=True)
            playwright.expect(results).to_contain_text('No local ticker row')
            results.get_by_role('link', name='Open company evidence', exact=True).click()
            research = page.get_by_role('button', name='Research company', exact=True)
            playwright.expect(research).to_be_visible()
            assert calls() in (['search'], ['search', 'search'])
            research.click()

            financial = page.locator('[data-company-answer="financial"]')
            valuation = page.locator('[data-company-answer="valuation"]')
            gaps = page.locator('[aria-label="Research gaps"]')
            playwright.expect(financial).to_contain_text('What changed')
            playwright.expect(financial).to_contain_text('Revenue up 23.4%')
            playwright.expect(financial).to_contain_text('2025-12-31')
            playwright.expect(valuation).to_contain_text('Peer valuation')
            playwright.expect(valuation).to_contain_text('Peer comparison unavailable')
            playwright.expect(valuation).to_contain_text('Independent listing and security-type sources were unavailable.')
            playwright.expect(gaps).to_contain_text('Direct-quarter evidence needs verification')
            page.wait_for_function('''() => document.querySelector('[data-testid="stApp"]')
                ?.getAttribute('data-test-script-state') === 'notRunning' ''')
            baseline = calls()
            assert [call for call in baseline if call.startswith('sec:')] == [
                'sec:' + url for url in (MAP, FACTS, SUB, SOURCE)]
            assert baseline.count('classification-unavailable') == 1
            assert 'unexpected-external-request' not in baseline
            assert_rendered_english(page.locator('body'))
            assert page.locator('html').evaluate('node => node.scrollWidth') == width
            for card in (financial, valuation, gaps):
                box = card.bounding_box()
                assert box and box['width'] <= width
                assert box['y'] + box['height'] <= height
            page.screenshot(path=str(tmp_path / f'native-annual-overview-{width}.png'))

            financial.locator('summary[aria-label="View what changed evidence"]').click()
            playwright.expect(financial).to_contain_text('TWD 1,234,000,000')
            playwright.expect(financial).to_contain_text('TWD 1,000,000,000')
            fact_link = financial.get_by_role('link', name='Exact SEC filing fact', exact=True)
            playwright.expect(fact_link).to_have_attribute('href', SOURCE + '#revenue')
            page.screenshot(path=str(tmp_path / f'native-annual-evidence-{width}.png'), full_page=True)
            trends = page.get_by_role('radio', name='Financial Trends', exact=True)
            page.locator('label').filter(has=trends).click()
            playwright.expect(trends).to_be_checked()
            body = page.locator('.st-key-company-section-body')
            playwright.expect(body.get_by_role('heading', name='Financial Trends', exact=True)).to_be_visible()
            page.wait_for_function('''() => document.querySelector('[data-testid="stApp"]')
                ?.getAttribute('data-test-script-state') === 'notRunning' ''')
            sources = page.get_by_role('radio', name='Data Sources', exact=True)
            page.locator('label').filter(has=sources).click()
            playwright.expect(sources).to_be_checked()
            page.get_by_text('Exact SEC annual evidence', exact=True).click()
            source_link = page.get_by_role('link', name='Open exact SEC primary document', exact=True)
            playwright.expect(source_link).to_be_visible()
            playwright.expect(source_link).to_have_attribute('href', SOURCE)
            assert calls() == baseline
            assert not blocked and not errors
            assert not page.get_by_test_id('stException').count()
        finally:
            browser.close()
    assert _demo_bytes() == canonical
