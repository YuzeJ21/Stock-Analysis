"""Actual Workbench navigation with disposable, constructed SEC HTTP responses."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from urllib.parse import parse_qs, urlsplit

import pytest

from src.public_performance_gate import _free_port, _wait_for_health, find_chrome_executable
from tests.test_research_monitor_roundtrip_browser import assert_rendered_english


def run_mrvl_fixture(root):
    from datetime import datetime, timezone
    from src import company_research_notes, dashboard, sec_research_review_ui
    from tests.test_mrvl_workbench import install_sources
    from tests.test_online_company_search_view import _result
    import pytest

    class Calls(list):
        def append(self, value):
            super().append(value)
            with (root/'source-calls.txt').open('a') as output:
                output.write(value+'\n')

    def search(query, **kwargs):
        assert query == 'MRVL'
        return {**_result(candidates=[dict(ticker='MRVL',cik='0001835632',title='Constructed MRVL browser case',
                                          exchange='Nasdaq',ambiguous=False)]),
                'query':'MRVL','observed_at':datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}

    original_connect = socket.socket.connect
    def local_only(sock, address):
        if isinstance(address, tuple) and str(address[0]) not in {'127.0.0.1','localhost','::1'}:
            raise AssertionError('Constructed browser checks must not reach outside providers')
        return original_connect(sock, address)

    # This is a dedicated app process; all private stores remain disposable.
    company_research_notes.PROJECT_ROOT = root
    sec_research_review_ui.PROJECT_ROOT = root
    with pytest.MonkeyPatch.context() as patch:
        failure = ('after_tax_exhibit' if (root/'fail-after-tax-exhibit').exists() else
                   'peer_document' if (root/'fail-peer-document').exists() else None)
        install_sources(patch, failure=failure, calls=Calls(), after_tax=True)
        patch.setattr(dashboard, 'search_sec_company_candidates', search)
        patch.setattr(socket.socket, 'connect', local_only)
        dashboard.main()


@pytest.fixture
def mrvl_browser_server(tmp_path):
    script = tmp_path/'mrvl_app.py'
    script.write_text('from pathlib import Path\nfrom tests.test_mrvl_earnings_browser import run_mrvl_fixture\nrun_mrvl_fixture(Path(__file__).parent)\n')
    root = Path(__file__).resolve().parents[1]
    base = f'http://127.0.0.1:{_free_port()}'
    env = {**os.environ,'PYTHONPATH':str(root),'PYTHONDONTWRITEBYTECODE':'1',
           'STOCK_RESEARCH_DATA_PROFILE':'demo','SEC_USER_AGENT':'Synthetic research contact@example.com'}
    env.pop('COMMERCIAL_RESEARCH_MODE', None)
    with (tmp_path/'streamlit.log').open('w') as log:
        process = subprocess.Popen([sys.executable,'-m','streamlit','run',str(script),
            '--server.address','127.0.0.1','--server.port',urlsplit(base).port.__str__(),
            '--server.headless','true','--server.fileWatcherType','none','--browser.gatherUsageStats','false'],
            cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            _wait_for_health(base, timeout_seconds=20)
            yield base
        finally:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=5)


def _calls(root):
    path = root/'source-calls.txt'
    return path.read_text().splitlines() if path.exists() else []


def _section(page, label):
    radio = page.get_by_role('radio',name=label,exact=True)
    page.locator('label').filter(has=radio).click()


def _details(scope, title):
    summary = scope.locator('summary').filter(has_text=title)
    assert summary.count() == 1
    assert summary.bounding_box()['height'] >= 44
    summary.click()


@pytest.mark.parametrize('width,height',[(1440,1000),(390,844)],ids=['desktop','phone'])
def test_mrvl_annual_explanation_sources_monitor_and_failed_retry_keep_their_boundaries(
    mrvl_browser_server,tmp_path,width,height,
):
    chrome = find_chrome_executable()
    if chrome is None:
        pytest.skip('Chrome-compatible browser is unavailable')
    playwright = pytest.importorskip('playwright.sync_api')
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(executable_path=str(chrome),headless=True)
        page = browser.new_page(viewport={'width':width,'height':height})
        page.set_default_timeout(15000)
        errors, external = [], []
        page.on('pageerror',lambda error:errors.append(str(error)))
        def local_only(route):
            if route.request.url.startswith(mrvl_browser_server+'/'):
                route.continue_()
            else:
                external.append(route.request.url); route.abort()
        page.route('**/*',local_only)
        expect = playwright.expect
        try:
            page.goto(mrvl_browser_server+'/?mode=research&page=company-workbench&ticker=MRVL&online=1&section=valuation')
            expect(page.get_by_role('heading',name='MRVL Company Brief',exact=True)).to_be_visible()
            assert _calls(tmp_path) == []
            refresh = page.get_by_role('button',name='Refresh financials and prices',exact=True)
            assert refresh.bounding_box()['height'] >= 44
            refresh.click()
            review = page.get_by_role('region',name='MRVL earnings and peer context',exact=True)
            expect(review.get_by_role('heading',name='Earnings quality behind annual P/E',exact=True)).to_be_visible()
            expect(review).to_contain_text('business-sale gain')
            expect(review).to_contain_text('direct competitor')
            assert len(_calls(tmp_path)) == 8
            basis_link = page.get_by_role('link',name='View earnings basis',exact=True)
            assert basis_link.bounding_box()['height'] >= 44
            basis_link.click()
            assert review.bounding_box()['y'] < height
            assert len(_calls(tmp_path)) == 8
            _details(review,'Inspect annual earnings and cash-flow evidence')
            caption = review.locator('caption').filter(has_text='Annual observations; rounded display values.')
            caption_box = caption.bounding_box()
            assert caption_box['width'] >= review.bounding_box()['width']*.7
            assert caption_box['height'] <= 150
            expect(review.locator('td[data-label="Reported item"]').filter(has_text='Operating cash flow')).to_be_visible()
            field_row = review.locator('tr').filter(has_text='Reported business-sale gain')
            expect(field_row).to_have_count(1)
            _details(field_row,'Field evidence')
            expect(field_row).to_contain_text('us-gaap:GainLossOnSaleOfBusiness')
            expect(field_row).to_contain_text('2025-02-02 to 2026-01-31')
            expect(field_row).to_contain_text('2026-03-11')
            assert field_row.get_by_role('link',name='SEC Companyfacts',exact=True).get_attribute('href').endswith('CIK0001835632.json')
            _details(review,'Issuer after-tax reconciliation — verified')
            reconciliation = review.locator('details.mrvl-after-tax')
            expect(reconciliation).to_contain_text('USD 176.0M')
            expect(reconciliation).to_contain_text('USD 1.76')
            expect(reconciliation).to_contain_text('100.0M shares')
            expect(reconciliation).to_contain_text('not recurring or normalized earnings')
            expect(reconciliation).to_contain_text('gain alone')
            expect(reconciliation).to_contain_text('furnished under Item 2.02')
            assert reconciliation.get_by_role('link',name='SEC earnings report',exact=True).get_attribute('href').endswith('mrvl-20260305.htm')
            assert reconciliation.get_by_role('link',name='SEC reconciliation exhibit',exact=True).get_attribute('href').endswith('q426_8kx1312026ex-991.htm')
            share_row = reconciliation.locator('tr').filter(has_text='Non-GAAP weighted-average shares')
            _details(share_row,'Source observation')
            expect(share_row).to_contain_text('source scale 1000000')
            expect(share_row).to_contain_text('source column span [24, 27]')
            assert reconciliation.locator('caption').bounding_box()['width'] >= review.bounding_box()['width']*.7
            _details(review,'Why consider AVGO, and why is the annual comparison held?')
            expect(review).to_contain_text('90 days apart')
            expect(review).to_contain_text('35-day window')
            expect(review).to_contain_text('does not admit AVGO')
            expect(review).to_contain_text('infrastructure software')
            assert_rendered_english(page.locator('body'))
            assert page.locator('html').evaluate('node=>node.scrollWidth') <= width+1
            _section(page,'Data Sources')
            expect(page.get_by_role('heading',name='MRVL earnings review sources',exact=True)).to_be_visible()
            assert len(_calls(tmp_path)) == 8
            nav = page.get_by_role('navigation',name='Personal research workflow',exact=True)
            nav.get_by_role('link',name='Monitor',exact=True).click()
            back = page.get_by_role('button',name='Return to MRVL Company Workbench',exact=True)
            expect(back).to_be_visible()
            assert back.bounding_box()['height'] >= 44
            back.click()
            expect(page.get_by_role('heading',name='MRVL earnings review sources',exact=True)).to_be_visible()
            assert parse_qs(urlsplit(page.url).query)['section'] == ['sources']
            assert len(_calls(tmp_path)) == 8
            expect(page.get_by_text('Issuer after-tax reconciliation — verified',exact=True)).to_be_visible()
            _section(page,'Overview')
            expect(page.get_by_role('heading',name='Earnings quality behind annual P/E',exact=True)).to_have_count(0)
            _section(page,'Valuation & Peers')
            expect(page.get_by_role('heading',name='Earnings quality behind annual P/E',exact=True)).to_be_visible()
            assert len(_calls(tmp_path)) == 8
            (tmp_path/'fail-peer-document').write_text('Constructed retry failure')
            refresh.click()
            expect(review).to_contain_text('AVGO comparison context remains incomplete')
            expect(review).to_contain_text('business-sale gain')
            expect(review).not_to_contain_text('direct competitor')
            assert len(_calls(tmp_path)) == 16
            expect(review).to_contain_text('Issuer after-tax reconciliation — verified')
            (tmp_path/'fail-peer-document').unlink()
            (tmp_path/'fail-after-tax-exhibit').write_text('Constructed earnings source failure')
            refresh.click()
            expect(review).to_contain_text('Issuer after-tax reconciliation — withheld')
            _details(review,'Issuer after-tax reconciliation — withheld')
            expect(review).to_contain_text('earnings exhibit was unavailable')
            expect(review).not_to_contain_text('USD 176.0M')
            expect(review).to_contain_text('direct competitor')
            expect(review).to_contain_text('business-sale gain')
            assert len(_calls(tmp_path)) == 24
            assert page.locator('html').evaluate('node=>node.scrollWidth') <= width+1
            assert not page.get_by_test_id('stException').count()
            assert_rendered_english(page.locator('body'))
            assert not errors and not external
            assert not (tmp_path/'data').exists()
            assert not list((tmp_path/'outputs/local').rglob('*.csv'))
        finally:
            browser.close()
