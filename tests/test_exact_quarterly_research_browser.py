"""Two viewport exact SEC quarter journeys over constructed source bytes."""
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import parse_qs, urlsplit

import pytest

from src.public_performance_gate import _free_port, _wait_for_dom_stability, _wait_for_health, find_chrome_executable
from tests.exact_quarterly_browser_fixture import CIKS, END, NOW, TICKERS, VALUES, accession, source_url
from tests.test_research_monitor_roundtrip_browser import assert_rendered_english


@pytest.fixture
def exact_quarter_server(tmp_path):
    project = Path(__file__).resolve().parents[1]
    script = tmp_path / 'exact_quarter_app.py'
    script.write_text('from pathlib import Path\n'
        'from tests.exact_quarterly_browser_fixture import run_exact_quarterly_fixture\n'
        'run_exact_quarterly_fixture(Path(__file__).parent)\n', encoding='utf-8')
    url = f'http://127.0.0.1:{_free_port()}'
    environment = {**os.environ, 'PYTHONPATH': os.pathsep.join((str(project), str(project / 'tests'))),
        'PYTHONDONTWRITEBYTECODE': '1', 'STOCK_RESEARCH_DATA_PROFILE': 'demo',
        'SEC_USER_AGENT': 'Synthetic exact quarter browser contact@example.com'}
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


def _protected_files():
    project = Path(__file__).resolve().parents[1]
    roots = [project / 'data/demo', project / 'outputs/local/company-research-notes',
             project / 'outputs/local/online-research-contexts']
    return {str(path): sha256(path.read_bytes()).hexdigest()
            for root in roots if root.exists() for path in root.rglob('*') if path.is_file()}


def _quarter_proof(financial):
    from src.online_filing_context import corroborate_online_financials
    from src.sec_online_quarter_evidence import validated_archive_quarter
    ticker = financial['ticker']
    view = validated_archive_quarter(financial, as_of=NOW)
    assert view is not None and view['status'] == 'inspection_only'
    assert view['ticker'] == ticker and view['sec_cik'] == CIKS[ticker]
    assert view['accession'] == accession(ticker) and view['source_url'] == source_url(ticker)
    assert view['rights_status'] == 'unregistered_sec_archive_personal_inspection_only'
    assert view['commercial_eligible'] is False and view['saved_readiness_promoted'] is False
    coverage = corroborate_online_financials(financial, financial['filing_inventory'], as_of=NOW)
    assert coverage['current']['quarterly']['status'] == 'corroborated'
    assert coverage['current']['quarterly']['reason'] == 'exact_archive_quarter_and_filing'
    assert coverage['structured_quarterly']['status'] == 'facts_pending'
    assert max(row['period_end'] for row in financial['quarterly_history']['periods']) == '2026-06-30'
    quarter = next(row for row in view['periods'] if row['kind'] == 'quarterly')
    ytd = next(row for row in view['periods'] if row['kind'] == 'cumulative')
    assert (quarter['period_start'], quarter['period_end']) == ('2026-07-01', END)
    assert (ytd['period_start'], ytd['period_end']) == ('2026-01-01', END)
    assert 'cash_from_operations' not in quarter['fields']
    assert 'capital_expenditures' not in quarter['fields']
    assert ytd['fields']['cash_from_operations']['value'] == VALUES[ticker]['cash_from_operations'] * 1_000_000
    for name, expected in VALUES[ticker].items():
        period = ytd if name in {'cash_from_operations', 'capital_expenditures'} else quarter
        field = period['fields'][name]
        assert field['value'] == expected * 1_000_000
        assert field['context_id'] == ('ytd' if period is ytd else 'parent-quarter')
        assert field['unit'] == 'USD' and field['unit_id'] == 'money'
        assert field['source_ref'] == source_url(ticker) + '#' + name
        assert field['reported_text'] == f'{expected:,}'
        assert field['reported_numeric_schema'] == 'sec-reported-numeric-v1'
        assert field['scale'] == 6 and field['decimals'] == '-6'
    if ticker == 'C':
        assert 'operating_income' not in quarter['fields']
        assert quarter['withheld_fields']['operating_income']
        assert quarter['fields']['revenue']['concept'] == 'RevenuesNetOfInterestExpense'
        assert {'net_interest_income', 'noninterest_income'} <= set(quarter['fields'])
    if ticker == 'NEE':
        assert 'capital_expenditures' not in ytd['fields']
        assert ytd['withheld_fields']['capital_expenditures']
    encoded = json.dumps(view)
    assert not any(key in encoded for key in ('"raw_text":', '"source_packet":', 'payload_raw_base64'))
    return view


@pytest.mark.parametrize('width,height', [(1440, 1000), (390, 844)], ids=['desktop-light', 'phone-dark'])
def test_exact_quarter_company_discover_and_offline_snapshot_journey(exact_quarter_server, tmp_path, width, height):
    chrome = find_chrome_executable()
    if chrome is None:
        pytest.skip('Chrome-compatible browser is unavailable')
    playwright = pytest.importorskip('playwright.sync_api')
    protected = _protected_files()
    destination = Path('/tmp/exact-quarter-browser-proof') / str(width)
    destination.mkdir(parents=True, exist_ok=True)
    metadata = dict(viewport=dict(width=width, height=height),
        color_scheme='dark' if width < 640 else 'light', companies={}, contrast={})

    def read(name):
        return json.loads((tmp_path / name).read_text())

    def calls():
        path = tmp_path / 'provider-calls.txt'
        return path.read_text().splitlines() if path.exists() else []

    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(executable_path=str(chrome), headless=True)
        page = browser.new_page(viewport={'width': width, 'height': height}, color_scheme=metadata['color_scheme'])
        page.set_default_timeout(20_000)
        blocked, errors = [], []

        def local_only(route):
            if route.request.url.startswith(exact_quarter_server + '/'):
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
            page.screenshot(path=str(tmp_path / f'exact-quarter-{name}-{width}.png'), full_page=True)

        def expand(name, container=None):
            container = container if container is not None else page
            summary = container.locator('details > summary').filter(has=page.get_by_text(name, exact=True))
            playwright.expect(summary).to_have_count(1)
            if summary.locator('..').get_attribute('open') is None:
                summary.click()
            return summary.locator('..')

        def section(name):
            radio = page.get_by_role('radio', name=name, exact=True)
            page.locator('label').filter(has=radio).click()
            playwright.expect(radio).to_be_checked()
            playwright.expect(page.locator('.st-key-company-section-body').get_by_role('heading', name=name, exact=True)).to_be_visible()
            settle()

        def readable(label, locator):
            proof = locator.evaluate(r'''element => {
                const rgb = value => (value.match(/[\d.]+/g) || []).map(Number);
                const luminance = color => color.slice(0, 3).map(x => x / 255)
                    .map(x => x <= .04045 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4)
                    .reduce((sum, x, index) => sum + x * [.2126, .7152, .0722][index], 0);
                const foreground = getComputedStyle(element).color;
                let node = element, background = 'rgb(255, 255, 255)';
                while (node) {
                    const value = getComputedStyle(node).backgroundColor, candidate = rgb(value);
                    if (candidate.length === 3 || candidate[3] === 1) { background = value; break; }
                    node = node.parentElement;
                }
                const values = [luminance(rgb(foreground)), luminance(rgb(background))].sort((a, b) => b - a);
                return {foreground, background, ratio: (values[0] + .05) / (values[1] + .05)};
            }''')
            assert proof['ratio'] >= 4.5, f'{label} must remain readable: {proof}'
            metadata['contrast'][label] = proof

        try:
            for ticker in TICKERS:
                page.goto(exact_quarter_server + f'/?mode=research&page=company-workbench&ticker={ticker}&online=1')
                research = page.get_by_role('button', name='Research company', exact=True)
                playwright.expect(research).to_be_visible()
                settle()
                before = calls()
                research.click()
                playwright.expect(page.locator('[data-online-filing-status="1"]')).to_be_visible()
                settle()
                surface(ticker.lower() + '-overview')
                section('Financial Trends')
                quarterly = page.get_by_role('radio', name='Quarterly', exact=True)
                page.locator('label').filter(has=quarterly).click()
                playwright.expect(quarterly).to_be_checked()
                settle()
                archive = page.locator('.company-archive-quarter')
                playwright.expect(archive.get_by_role('heading', name='Exact SEC quarter', exact=True)).to_be_visible()
                settle()
                financial = read('financial-' + ticker + '.json')
                evidence = _quarter_proof(financial)
                context = read('workbench-' + ticker + '.json')
                source_calls = calls()
                assert source_calls[len(before):].count('sec:' + source_url(ticker)) == 1
                assert read('source-audit.json')['source_objects_unchanged'] is True
                playwright.expect(archive).to_contain_text(END)
                playwright.expect(archive).to_contain_text('2026-07-01')
                playwright.expect(archive).to_contain_text('2026-01-01')
                playwright.expect(archive).to_contain_text('Withheld')
                playwright.expect(archive).to_contain_text('USD')
                for name, expected in VALUES[ticker].items():
                    table = archive.locator('table').nth(1 if name in {'cash_from_operations', 'capital_expenditures'} else 0)
                    playwright.expect(table).to_contain_text(f'USD {expected * 1_000_000:,}')
                financial_table = page.get_by_role('region', name='Financial table', exact=True)
                latest_row = financial_table.get_by_role('row').filter(has=page.get_by_role('rowheader', name=END, exact=True))
                playwright.expect(latest_row).to_have_count(1)
                playwright.expect(latest_row).to_contain_text(f"{VALUES[ticker]['revenue']:,.1f}")
                period_evidence = expand('Period evidence and gaps')
                playwright.expect(period_evidence).to_contain_text('Exact SEC filing')
                assert source_url(ticker) + '#revenue' in period_evidence.get_by_role('link').evaluate_all('nodes => nodes.map(node => node.href)')
                readable(ticker + '-quarter-heading', archive.get_by_role('heading', name='Exact SEC quarter', exact=True))
                surface(ticker.lower() + '-financial-quarter')

                basis = expand('Source and reporting basis', archive)
                playwright.expect(archive).to_contain_text(accession(ticker))
                playwright.expect(basis).to_contain_text('2026-11-02')
                playwright.expect(basis).to_contain_text('2026-11-08')
                playwright.expect(basis).to_contain_text('SHA-256')
                playwright.expect(basis).to_contain_text('Personal inspection')
                assert source_url(ticker) in basis.get_by_role('link').evaluate_all('nodes => nodes.map(node => node.href)')
                assert calls() == source_calls
                surface(ticker.lower() + '-source-proof')

                section('Financial Trends')
                trend = expand('Business Trend · online reported periods')
                current = read('workbench-' + ticker + '.json')
                latest = [row for row in current['business_trend']['periods']
                          if row['kind'] == 'quarterly' and row['period_end'] == END]
                assert len(latest) == 1
                assert latest[0]['fields']['revenue']['value'] == VALUES[ticker]['revenue'] * 1_000_000
                assert 'cash_from_operations' not in latest[0]['fields']
                direct_cash = [row for row in current['business_trend']['metrics']
                               if row['period_kind'] == 'quarterly' and row['period_end'] == END
                               and row['key'] == 'cfo_less_ppe']
                assert direct_cash and all(row['value'] is None for row in direct_cash)
                if ticker == 'NEE':
                    assert not any(row['value'] is not None for row in current['business_trend']['metrics']
                        if row['period_kind'] == 'cumulative' and row['period_end'] == END and row['key'] == 'cfo_less_ppe')
                playwright.expect(trend).to_contain_text('Year-to-date cash flow stays separate')
                playwright.expect(page.locator('.company-archive-quarter')).to_contain_text(END)
                surface(ticker.lower() + '-trends')
                section('Data Sources')
                playwright.expect(page.locator('.company-archive-quarter')).to_contain_text(END)
                surface(ticker.lower() + '-data-sources')
                assert calls() == source_calls, 'Read-only section changes must reuse exact source observations'

                if ticker == 'DUK':
                    section('Research Notes')
                    saved = expand('Saved online research · replay and compare')
                    saved.get_by_role('button', name='Save research snapshot', exact=True).click()
                    playwright.expect(saved).to_contain_text('Current versus latest saved: unchanged')
                    settle()
                    paths = list((tmp_path / 'outputs/local/online-research-contexts').glob(f'*/{CIKS[ticker]}/{ticker}/*.json'))
                    assert len(paths) == 1
                    path, original_bytes = paths[0], paths[0].read_bytes()
                    snapshot = json.loads(original_bytes)
                    assert snapshot['context'] == read('workbench-' + ticker + '.json')
                    assert snapshot['historical'] is True and snapshot['current'] is False
                    assert snapshot['context']['commercial_eligible'] is False
                    surface('duk-saved')
                    saved.get_by_role('button', name='Open historical research snapshot', exact=True).click()
                    playwright.expect(saved).to_contain_text('Historical replay · ')
                    settle()
                    assert calls() == source_calls
                    surface('duk-historical')
                    saved.get_by_role('button', name='Open Monitor', exact=True).click()
                    playwright.expect(page.get_by_role('heading', name='Saved online research updates', exact=True)).to_be_visible()
                    settle()
                    reopen = page.get_by_role('button', name='Reopen exact saved research', exact=True)
                    playwright.expect(reopen).to_be_visible()
                    surface('duk-monitor')
                    reopen.click()
                    playwright.expect(page.get_by_text('Historical replay · ', exact=False)).to_be_visible()
                    settle()
                    query = parse_qs(urlsplit(page.url).query)
                    assert {key: query.get(key) for key in ('ticker', 'section', 'research_cik', 'research_snapshot')} == dict(
                        ticker=[ticker], section=['notes'], research_cik=[CIKS[ticker]], research_snapshot=[snapshot['snapshot_id']])
                    assert path.read_bytes() == original_bytes
                    assert calls() == source_calls, 'Saving, Monitor, replay and exact return must remain offline'
                    surface('duk-monitor-return')
                    metadata['snapshot'] = dict(snapshot_id=snapshot['snapshot_id'],
                        snapshot_sha256=snapshot['snapshot_sha256'], stored_bytes=len(original_bytes),
                        exact_context=True, immutable_bytes=True, later_transport_calls=0)
                metadata['companies'][ticker] = dict(accession=evidence['accession'], source_url=evidence['source_url'],
                    direct_fields=sorted(evidence['periods'][0]['fields']),
                    source_requests=sum(value.startswith('sec:') for value in source_calls[len(before):]), later_transport_calls=0,
                    rights_status=evidence['rights_status'], commercial_eligible=False,
                    companyfacts_latest='2026-06-30', archive_latest=END)

            page.goto(exact_quarter_server + '/?mode=research&page=discover')
            expand('Coverage studies')
            page.get_by_role('tab', name='Self-service', exact=True).click()
            region = page.get_by_role('region', name='Self-service research coverage', exact=True)
            playwright.expect(region).to_contain_text('Unattempted: 12 / 12.')
            for attempted in range(1, 13):
                page.get_by_role('button', name='Inspect next company', exact=True).click()
                playwright.expect(region).to_contain_text(f'Unattempted: {12-attempted} / 12.')
                settle()
            study = read('study-view.json')
            assert study['attempted_count'] == study['requested_count'] == 12
            assert study['counts']['dated_price'] == study['counts']['peer_comparison'] == 0
            assert study['user_store_written'] is False and study['canonical_changed'] is False
            assert study['commercial_eligible'] is False and study['saved_readiness_promoted'] is False
            by_ticker = {row['ticker']: row for row in study['rows']}
            before_details = calls()
            for ticker in TICKERS:
                radio = page.get_by_role('radio', name=ticker, exact=True)
                page.locator('.st-key-self-service-coverage-company label').filter(has=radio).click()
                playwright.expect(radio).to_be_checked()
                settle()
                selected = page.get_by_role('region', name='Selected company capabilities', exact=True)
                playwright.expect(selected).to_contain_text('Current direct-quarter facts')
                assert by_ticker[ticker]['capabilities']['direct_quarter']['status'] == 'available'
                detail = expand('Reporting periods and original source receipts')
                playwright.expect(detail).to_contain_text('2026-11-08')
                assert source_url(ticker) in detail.get_by_role('link').evaluate_all('nodes => nodes.map(node => node.href)')
                surface('discover-' + ticker.lower())
            assert calls() == before_details, 'Discover selection and source inspection must remain offline'
            assert len(list((tmp_path / 'outputs/local/online-research-contexts').rglob('*.json'))) == 1
            assert not (tmp_path / 'data').exists()
            assert not list(tmp_path.rglob('research_thesis_journal.csv'))
            assert not (tmp_path / 'outputs/local/company-research-notes').exists()
            assert _protected_files() == protected
            assert not blocked and not errors and 'unexpected-external-request' not in calls()
            metadata.update(status='passed', study_count=study['attempted_count'],
                external_browser_requests=blocked, browser_errors=errors,
                canonical_and_user_store_unchanged=True, financial_csv_written=False)
        except Exception:
            page.screenshot(path=str(tmp_path / f'exact-quarter-failure-{width}.png'), full_page=True)
            (tmp_path / f'exact-quarter-failure-{width}.txt').write_text(page.url + '\n\n' + page.locator('body').inner_text(), encoding='utf-8')
            (tmp_path / f'exact-quarter-failure-{width}-aria.txt').write_text(page.locator('body').aria_snapshot(), encoding='utf-8')
            raise
        finally:
            browser.close()
            (tmp_path / 'browser-proof.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
            for path in tmp_path.iterdir():
                if path.suffix in {'.png', '.json', '.txt', '.log'}:
                    shutil.copy2(path, destination / path.name)
            report = Path('/tmp/exact-quarter-browser-report.md')
            entries = []
            for proof in sorted(Path('/tmp/exact-quarter-browser-proof').glob('*/browser-proof.json')):
                result = json.loads(proof.read_text())
                entries.append(f"- {result['viewport']['width']} × {result['viewport']['height']} {result['color_scheme']}: {result.get('status', 'failed')}.")
            report.write_text('# Constructed exact-quarter browser proof\n\n' + '\n'.join(entries)
                + '\n\nEvidence: /tmp/exact-quarter-browser-proof. These checks use constructed SEC bytes through production parsers, coverage, trends and snapshot paths; they do not establish live SEC or human validation.\n', encoding='utf-8')
