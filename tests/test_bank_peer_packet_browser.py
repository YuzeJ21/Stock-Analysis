"""Desktop/phone proof of lossless bank storage through the real dashboard."""
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from time import monotonic, sleep
from urllib.parse import urlsplit

import pytest

from src.public_performance_gate import _free_port, _wait_for_dom_stability, _wait_for_health, find_chrome_executable
from tests.bank_peer_packet_browser_fixture import BANKS
from tests.test_research_monitor_roundtrip_browser import assert_rendered_english


@pytest.fixture
def bank_peer_packet_server(tmp_path):
    project = Path(__file__).resolve().parents[1]
    script = tmp_path / 'bank_peer_packet_app.py'
    script.write_text('from pathlib import Path\n'
        'from tests.bank_peer_packet_browser_fixture import run_bank_peer_packet_fixture\n'
        'run_bank_peer_packet_fixture(Path(__file__).parent)\n', encoding='utf-8')
    url = f'http://127.0.0.1:{_free_port()}'
    environment = {**os.environ, 'PYTHONPATH': os.pathsep.join((str(project), str(project / 'tests'))),
        'PYTHONDONTWRITEBYTECODE': '1', 'STOCK_RESEARCH_DATA_PROFILE': 'demo',
        'SEC_USER_AGENT': 'Synthetic bank browser contact@example.com'}
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
def test_bank_packets_are_losslessly_retained_and_rechecked_without_promoting_pe(bank_peer_packet_server, tmp_path, width, height):
    chrome = find_chrome_executable()
    if chrome is None:
        pytest.skip('Chrome-compatible browser is unavailable')
    playwright = pytest.importorskip('playwright.sync_api')
    canonical = _canonical()
    destination = Path('/tmp/bank-peer-browser-proof') / str(width)
    destination.mkdir(parents=True, exist_ok=True)
    for previous in destination.glob('bank-peer-*'):
        if previous.is_file():
            previous.unlink()

    def read(name):
        return json.loads((tmp_path / name).read_text())

    def calls():
        path = tmp_path / 'provider-calls.txt'
        return path.read_text().splitlines() if path.exists() else []

    def retained_audit():
        audit = read('retention-audit.json')
        assert audit['classification_count'] == 1
        for ticker in BANKS:
            retained = audit['banks'][ticker]
            assert retained['stored_packet_bytes'] <= 8 * 1024 * 1024
            assert retained['expanded_peer_bytes'] > 8 * 1024 * 1024
            assert len(retained['documents']) == (4 if ticker == 'C' else 2)
            assert all(doc['exact_source_match'] and doc['sha256'] == doc['receipt_sha256']
                       for doc in retained['documents'])
            assert max(doc['bytes'] for doc in retained['documents']) > 6 * 1024 * 1024
        return audit

    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(executable_path=str(chrome), headless=True)
        page = browser.new_page(viewport={'width': width, 'height': height},
                                color_scheme='dark' if width < 640 else 'light')
        page.set_default_timeout(20_000)
        blocked, errors = [], []

        def local_only(route):
            if route.request.url.startswith(bank_peer_packet_server + '/'):
                route.continue_()
            else:
                blocked.append(route.request.url)
                route.abort()

        page.route('**/*', local_only)
        page.on('pageerror', lambda error: errors.append(str(error)))

        def settle():
            page.wait_for_function('''() => document.querySelector('[data-testid="stApp"]')
                ?.getAttribute('data-test-script-state') === 'notRunning' ''', timeout=20_000)
            _wait_for_dom_stability(page, timeout_seconds=8, stable_checks=2)

        def surface(name):
            settle()
            assert_rendered_english(page.locator('body'))
            assert page.locator('html').evaluate('element => element.scrollWidth') == width
            assert not page.get_by_test_id('stException').count()
            assert not blocked and not errors
            page.screenshot(path=str(tmp_path / f'bank-peer-{name}-{width}.png'), full_page=True)

        def expand(name):
            summary = page.locator('details > summary').filter(has=page.get_by_text(name, exact=True))
            playwright.expect(summary).to_have_count(1)
            if summary.locator('..').get_attribute('open') is None:
                summary.click()
            return summary.locator('..')

        def choose(ticker):
            radio = page.get_by_role('radio', name=ticker, exact=True)
            page.locator('.st-key-self-service-coverage-company label').filter(has=radio).click()
            playwright.expect(radio).to_be_checked()
            playwright.expect(page.get_by_role('heading', name=ticker + ' · Banks', exact=True)).to_be_visible()
            settle()

        try:
            page.goto(bank_peer_packet_server + '/?mode=research&page=discover')
            expand('Coverage studies')
            page.get_by_role('tab', name='Self-service', exact=True).click()
            region = page.get_by_role('region', name='Self-service research coverage', exact=True)
            playwright.expect(region).to_contain_text('Unattempted: 6 / 12.', timeout=30_000)
            settle()
            view = read('study-view.json')
            assert view['requested_count'] == 12 and view['attempted_count'] == view['pending_count'] == 6
            assert all(group['requested_count'] == 3 for group in view['by_group'])
            assert next(group for group in view['by_group'] if group['group'] == 'Banks')['counts']['attempted'] == 3
            assert view['counts']['peer_comparison'] == 0
            assert not view['user_notes_read'] and not view['user_store_written']
            assert view['saved_readiness_promoted'] is False and view['commercial_eligible'] is False
            retained_audit()
            first_calls = calls()
            listing_calls = [value for value in first_calls if value.endswith(('nasdaqlisted.txt', 'otherlisted.txt',
                              'company_tickers_exchange.json', 'company_tickers.json'))]
            assert len(listing_calls) == 4 and len(set(listing_calls)) == 4
            for ticker in BANKS:
                choose(ticker)
                selected = page.get_by_role('region', name='Selected company capabilities', exact=True)
                for label in ('SEC issuer match', 'Usable filing catalog', 'Current annual facts', 'Dated close'):
                    playwright.expect(selected.get_by_role('row').filter(has_text=label)).to_contain_text('Available')
                peer_row = selected.get_by_role('row').filter(has_text='Same-basis industry comparison')
                playwright.expect(peer_row).to_contain_text('Held')
                playwright.expect(peer_row).to_contain_text('EPS basis for the selected security remains unverified')
                playwright.expect(selected.get_by_role('row').filter(has_text='Hypothetical scenario eligibility')).to_contain_text('Excluded')
                retained = page.locator('[data-peer-evidence-retained="1"]')
                playwright.expect(retained).to_be_visible()
                playwright.expect(retained).to_contain_text('Full peer source evidence retained')
                playwright.expect(retained).to_contain_text('exact restoration verified')
                detail = expand('Reporting periods and original source receipts')
                playwright.expect(detail).to_contain_text('SHA-256')
                playwright.expect(detail).to_contain_text('Observed 2026-11-08')
                row = next(row for row in read('study-view.json')['rows'] if row['ticker'] == ticker)
                assert row['capabilities']['peer_comparison'] == dict(status='held', reason='multiple_issuer_share_classes_unresolved')
                assert row['capabilities']['scenario_eligibility']['reason'] == 'financial_sector_operating_company_dcf_excluded'
                storage = row['peer_storage']
                assert storage['status'] == 'retained' and storage['encoding'] == 'zlib+base64'
                assert storage['expanded_bytes'] > 8 * 1024 * 1024
                assert storage['source_evidence_unchanged'] is True
                storage_proof = detail.get_by_role('region', name='Peer source storage proof', exact=True)
                playwright.expect(storage_proof).to_contain_text('zlib+base64')
                playwright.expect(storage_proof).to_contain_text('Stored packet bytes')
                playwright.expect(storage_proof).to_contain_text('Restored source bytes')
                playwright.expect(storage_proof).to_contain_text('Original packet digest')
                playwright.expect(storage_proof).to_contain_text(f"{storage['stored_bytes']:,}")
                playwright.expect(storage_proof).to_contain_text(f"{storage['expanded_bytes']:,}")
                playwright.expect(storage_proof).to_contain_text(storage['packet_digest'])
                assert calls() == first_calls, 'Company selection/details must only read retained observations'
                surface(ticker.lower())
                storage_proof.scroll_into_view_if_needed()
                playwright.expect(storage_proof.get_by_text(f"{storage['expanded_bytes']:,}", exact=False)).to_be_visible()
                contrast = storage_proof.get_by_text('Restored source bytes', exact=True).evaluate('''element => {
                    const rgb = value => (value.match(/[\\d.]+/g) || []).map(Number);
                    const luminance = color => color.slice(0, 3).map(x => x / 255)
                        .map(x => x <= .04045 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4)
                        .reduce((sum, x, index) => sum + x * [.2126, .7152, .0722][index], 0);
                    const foreground = rgb(getComputedStyle(element).color);
                    let node = element, background = [255, 255, 255];
                    while (node) {
                        const candidate = rgb(getComputedStyle(node).backgroundColor);
                        if (candidate.length === 3 || candidate[3] === 1) { background = candidate; break; }
                        node = node.parentElement;
                    }
                    const values = [luminance(foreground), luminance(background)].sort((a, b) => b - a);
                    return (values[0] + .05) / (values[1] + .05);
                }''')
                assert contrast >= 4.5, 'Storage proof labels must remain readable in either color preference'
                page.screenshot(path=str(tmp_path / f'bank-peer-{ticker.lower()}-storage-{width}.png'), full_page=True)
            choose('JPM')
            before = calls()
            before_view = read('study-view.json')
            page.get_by_role('button', name='Recheck company', exact=True).click()
            deadline = monotonic() + 20
            while read('study-view.json')['source_request_count'] == before_view['source_request_count'] and monotonic() < deadline:
                sleep(0.05)
            settle()
            after = calls()
            assert len(after) > len(before)
            assert any(value.startswith('source:https://www.sec.gov/Archives/edgar/data/19617/') for value in after[len(before):])
            assert not any(value.endswith(('nasdaqlisted.txt', 'otherlisted.txt', 'company_tickers_exchange.json',
                           'company_tickers.json')) for value in after[len(before):])
            assert read('study-view.json')['attempted_count'] == 6
            assert read('study-view.json')['requested_count'] == 12
            assert retained_audit()['classification_count'] == 1
            # A real widget rerun calls the production getter's pure read path.
            choose('BAC')
            choose('JPM')
            assert calls() == after
            method = region.locator('summary').filter(has_text='All tool counts and method exclusions')
            method.click()
            playwright.expect(region).to_contain_text('at least three qualified references')
            playwright.expect(region).to_contain_text('3 excluded')
            surface('recheck-offline-read')
            assert not blocked and not errors and 'unexpected-external-request' not in calls()
            assert _canonical() == canonical and not (tmp_path / 'data').exists()
            assert not (tmp_path / 'outputs').exists()
            assert not list(tmp_path.rglob('research_thesis_journal.csv'))
        except Exception:
            page.screenshot(path=str(tmp_path / f'bank-peer-failure-{width}.png'), full_page=True)
            (tmp_path / f'bank-peer-failure-{width}.txt').write_text(page.url + '\n\n' + page.locator('body').inner_text(), encoding='utf-8')
            raise
        finally:
            browser.close()
            for path in tmp_path.iterdir():
                if path.suffix in {'.png', '.json', '.txt', '.log'}:
                    shutil.copy2(path, destination / path.name)
