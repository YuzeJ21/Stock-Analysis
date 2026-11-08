"""Desktop and phone bank save/replay journeys over real constructed producers."""
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
from tests.bank_research_snapshot_browser_fixture import BANKS, CIKS
from tests.test_research_monitor_roundtrip_browser import assert_rendered_english


@pytest.fixture
def bank_snapshot_server(tmp_path):
    project = Path(__file__).resolve().parents[1]
    script = tmp_path / 'bank_snapshot_app.py'
    script.write_text('from pathlib import Path\n'
        'from tests.bank_research_snapshot_browser_fixture import run_bank_research_snapshot_fixture\n'
        'run_bank_research_snapshot_fixture(Path(__file__).parent)\n', encoding='utf-8')
    url = f'http://127.0.0.1:{_free_port()}'
    environment = {**os.environ, 'PYTHONPATH': os.pathsep.join((str(project), str(project / 'tests'))),
        'PYTHONDONTWRITEBYTECODE': '1', 'STOCK_RESEARCH_DATA_PROFILE': 'demo',
        'SEC_USER_AGENT': 'Synthetic bank snapshot contact@example.com'}
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


def _cover_evidence(context):
    peer = context['peer_read_through']
    assert peer['status'] == 'research_comparison' and peer['peer_count'] == 3
    assert len(peer['excluded']) == 1
    assert peer['excluded'][0]['ticker'] == 'GAP'
    assert peer['excluded'][0]['reason'] == 'selected_security_eps_conflict'
    assert context['scenario_base']['status'] == 'excluded'
    assert context['scenario_base']['reason'] == 'financial_sector_operating_company_dcf_excluded'
    assert context['commercial_eligible'] is False and context['saved_readiness_promoted'] is False
    result = []
    for row in [peer['subject'], *peer['peers']]:
        scope = row['selected_security_scope']
        assert scope['status'] == 'supported_common'
        assert scope['commercial_eligible'] is False and scope['alias_mappings_established'] is False
        assert scope['basis_refs'] and scope['original_eps']['proofs']
        for doc in scope['documents']:
            assert doc['source_ref'].startswith('https://www.sec.gov/Archives/edgar/data/')
            assert len(doc['payload_sha256']) == len(doc['body_sha256']) == 64
            if doc.get('parent_source_ref'):
                assert doc['parent_href'] and doc['role'].endswith('_companion')
                continue
            assert doc['cover_observation_schema'] == 'sec-cover-observations-v1'
            observations = doc['cover_observations']
            assert observations == [dict(trading_symbol=row['ticker'], title='Common Stock', exchange='Nasdaq', context_id='common'),
                dict(trading_symbol=row['ticker'] + '-P', title='Preferred Stock', exchange='Nasdaq', context_id='preferred')]
            assert 'raw_cover_observations' not in doc
            assert doc['selected_common']['fact_refs']
            result.append((row['ticker'], doc['role'], observations, doc['selected_common'], doc['payload_sha256']))
    return result


@pytest.mark.parametrize('width,height', [(1440, 1000), (390, 844)], ids=['desktop-light', 'phone-dark'])
def test_three_bank_snapshots_save_compare_replay_and_return_offline(bank_snapshot_server, tmp_path, width, height):
    chrome = find_chrome_executable()
    if chrome is None:
        pytest.skip('Chrome-compatible browser is unavailable')
    playwright = pytest.importorskip('playwright.sync_api')
    canonical = _canonical()
    destination = Path('/tmp/bank-research-snapshot-browser-proof') / str(width)
    destination.mkdir(parents=True, exist_ok=True)
    for previous in destination.iterdir():
        if previous.is_file():
            previous.unlink()
    metadata = dict(viewport=dict(width=width, height=height),
        color_scheme='dark' if width < 640 else 'light', banks={}, contrast={})

    def read(name):
        return json.loads((tmp_path / name).read_text())

    def calls():
        path = tmp_path / 'provider-calls.txt'
        return path.read_text().splitlines() if path.exists() else []

    def snapshots(ticker):
        return list((tmp_path / 'outputs/local/online-research-contexts').glob(f'*/{CIKS[ticker]}/{ticker}/*.json'))

    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(executable_path=str(chrome), headless=True)
        page = browser.new_page(viewport={'width': width, 'height': height}, color_scheme=metadata['color_scheme'])
        page.set_default_timeout(20_000)
        blocked, errors = [], []

        def local_only(route):
            if route.request.url.startswith(bank_snapshot_server + '/'):
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
            page.screenshot(path=str(tmp_path / f'bank-snapshot-{name}-{width}.png'), full_page=True)

        def expand(name, container=None, first=False):
            container = container if container is not None else page
            summary = container.locator('details > summary').filter(has=page.get_by_text(name, exact=True))
            if first:
                summary = summary.first
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
            for ticker in BANKS:
                page.goto(bank_snapshot_server + f'/?mode=research&page=company-workbench&ticker={ticker}&online=1')
                research = page.get_by_role('button', name='Research company', exact=True)
                playwright.expect(research).to_be_visible()
                research.click()
                playwright.expect(page.locator('[data-online-filing-status="1"]')).to_be_visible()
                settle()
                source_calls = calls()
                context = read('workbench-' + ticker + '.json')
                cover = _cover_evidence(context)
                peer = context['peer_read_through']
                expected_median = sorted(row['multiple'] for row in peer['peers'])[1]
                assert peer['peer_median'] == expected_median
                assert peer['premium_fraction'] == pytest.approx(peer['subject']['multiple'] / expected_median - 1)
                assert read('source-audit.json')['source_objects_unchanged'] is True
                surface(ticker.lower() + '-overview')

                section('Valuation & Peers')
                valuation = page.get_by_role('region', name='Online peer valuation', exact=True)
                playwright.expect(valuation).to_contain_text('3 companies')
                playwright.expect(valuation).to_contain_text('EPS YoY withheld.')
                excluded = expand('Excluded reference companies and reasons (1)', valuation)
                playwright.expect(excluded).to_contain_text('GAP')
                playwright.expect(excluded).to_contain_text('conflicts with the annual filing fact')
                sources = expand('View actual fiscal periods, prices, and sources', valuation)
                security = expand('Selected security and related issuer symbols', sources, first=True)
                playwright.expect(security).to_contain_text(f'{ticker}-P · Preferred Stock · Nasdaq · context preferred')
                playwright.expect(security.get_by_role('link', name='Cover trading symbol', exact=True).first).to_have_attribute('href', peer['subject']['selected_security_scope']['documents'][0]['selected_common']['fact_refs'][1])
                playwright.expect(security.get_by_role('link', name='Original EPS fact', exact=True).first).to_have_attribute('href', peer['subject']['selected_security_scope']['original_eps']['proofs'][0]['source_ref'])
                if ticker in {'JPM', 'C'}:
                    playwright.expect(security).to_contain_text('Companion exhibit in the same')
                    playwright.expect(security.get_by_role('link', name='Parent document reference', exact=True).first).to_be_visible()
                readable(ticker + '-cover-literal', security.get_by_text(f'{ticker}-P · Preferred Stock · Nasdaq · context preferred', exact=True).first)
                scenario = expand('Scenario Lab · explicit assumptions')
                scenario.get_by_role('button', name='Calculate hypothetical enterprise value', exact=True).click()
                playwright.expect(scenario).to_contain_text('financial sector operating company dcf excluded')
                playwright.expect(page.get_by_test_id('stMetric').filter(has_text='Hypothetical enterprise value')).to_have_count(0)
                assert calls() == source_calls
                surface(ticker.lower() + '-evidence')

                section('Research Notes')
                saved = expand('Saved online research · replay and compare')
                save = saved.get_by_role('button', name='Save research snapshot', exact=True)
                save.click()
                playwright.expect(saved).to_contain_text('Current versus latest saved: unchanged')
                settle()
                paths = snapshots(ticker)
                assert len(paths) == 1
                path, original_bytes = paths[0], paths[0].read_bytes()
                snapshot = json.loads(original_bytes)
                assert snapshot['context'] == read('workbench-' + ticker + '.json')
                assert _cover_evidence(snapshot['context']) == cover
                assert snapshot['historical'] is True and snapshot['current'] is False
                assert path.stat().st_size <= 512 * 1024
                save.click()
                playwright.expect(saved).to_contain_text('Current versus latest saved: unchanged')
                settle()
                assert snapshots(ticker) == paths and path.read_bytes() == original_bytes
                readable(ticker + '-save-action', save.get_by_text('Save research snapshot', exact=True))
                surface(ticker.lower() + '-saved')
                saved.get_by_role('button', name='Open historical research snapshot', exact=True).click()
                playwright.expect(saved).to_contain_text('Historical replay · ')
                settle()
                query = parse_qs(urlsplit(page.url).query)
                assert query['ticker'] == [ticker] and query['research_cik'] == [CIKS[ticker]]
                assert query['research_snapshot'] == [snapshot['snapshot_id']]
                assert calls() == source_calls and path.read_bytes() == original_bytes
                surface(ticker.lower() + '-historical')
                saved.get_by_role('button', name='Open Monitor', exact=True).click()
                heading = page.get_by_role('heading', name='Saved online research updates', exact=True)
                playwright.expect(heading).to_be_visible()
                settle()
                selector = page.get_by_test_id('stSelectbox').filter(has_text='Saved online research company')
                box = selector.get_by_role('combobox')
                company_label = f'{ticker} · CIK {CIKS[ticker]}'
                if width < 640:
                    # The phone control is an editable combobox. Its explicit
                    # Open button launches the option dialog; input clicks edit.
                    opener = selector.get_by_role('button', name='Open', exact=True)
                    playwright.expect(opener).to_be_visible()
                    opener.scroll_into_view_if_needed()
                    settle()
                    opener.press('Space')
                else:
                    box.press('ArrowDown')
                playwright.expect(box).to_have_attribute('aria-expanded', 'true')
                page.get_by_role('option', name=company_label, exact=True).click()
                settle()
                reopen = page.get_by_role('button', name='Reopen exact saved research', exact=True)
                playwright.expect(reopen).to_be_visible()
                readable(ticker + '-monitor-return', reopen.get_by_text('Reopen exact saved research', exact=True))
                surface(ticker.lower() + '-monitor')
                reopen.click()
                playwright.expect(page.get_by_text('Historical replay · ', exact=False)).to_be_visible()
                settle()
                route = parse_qs(urlsplit(page.url).query)
                assert {key: route.get(key) for key in ('ticker', 'section', 'research_cik', 'research_snapshot')} == dict(
                    ticker=[ticker], section=['notes'], research_cik=[CIKS[ticker]], research_snapshot=[snapshot['snapshot_id']])
                assert calls() == source_calls, 'Saving, replay, Monitor and exact return must stay offline'
                assert path.read_bytes() == original_bytes
                assert _cover_evidence(json.loads(path.read_bytes())['context']) == cover
                surface(ticker.lower() + '-monitor-return')
                metadata['banks'][ticker] = dict(snapshot_id=snapshot['snapshot_id'], snapshot_sha256=snapshot['snapshot_sha256'],
                    stored_bytes=len(original_bytes), repeated_save_preserved_bytes=True, comparison='unchanged',
                    qualified_references=peer['peer_count'], excluded_reference=peer['excluded'][0]['reason'],
                    normalized_cover_rows=sum(len(row[2]) for row in cover), source_calls_after_research=len(source_calls),
                    replay_and_return_source_calls=0, original_source_objects_unchanged=True,
                    scenario_status=context['scenario_base']['status'])
            assert _canonical() == canonical
            assert not (tmp_path / 'data').exists()
            assert not list(tmp_path.rglob('research_thesis_journal.csv'))
            assert not list((tmp_path / 'outputs').rglob('*notes*'))
            assert len(list((tmp_path / 'outputs/local/online-research-contexts').rglob('*.json'))) == 3
            assert not blocked and not errors and 'unexpected-external-request' not in calls()
            metadata.update(status='passed', external_browser_requests=blocked, browser_errors=errors,
                canonical_demo_unchanged=True, user_notes_written=False)
        except Exception:
            page.screenshot(path=str(tmp_path / f'bank-snapshot-failure-{width}.png'), full_page=True)
            (tmp_path / f'bank-snapshot-failure-{width}.txt').write_text(page.url + '\n\n' + page.locator('body').inner_text(), encoding='utf-8')
            (tmp_path / f'bank-snapshot-failure-{width}-aria.txt').write_text(page.locator('body').aria_snapshot(), encoding='utf-8')
            raise
        finally:
            browser.close()
            (tmp_path / 'browser-proof.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
            for path in tmp_path.iterdir():
                if path.suffix in {'.png', '.json', '.txt', '.log'}:
                    shutil.copy2(path, destination / path.name)
