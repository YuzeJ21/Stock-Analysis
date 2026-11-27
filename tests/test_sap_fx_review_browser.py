"""Actual desktop/phone explicit FX action and public-only download; constructed source."""
import json
from urllib.parse import urlsplit
from zipfile import ZipFile

import pytest

from fx_reference_fixtures import write_fx_review_app, XML
from src.public_performance_gate import _local_demo_server, find_chrome_executable


@pytest.mark.parametrize('width,height', [(1280,900),(390,844)], ids=['desktop','phone'])
def test_fx_action_download_and_profile_scope(tmp_path, width, height):
    from playwright.sync_api import sync_playwright, expect
    write_fx_review_app(tmp_path)
    browser_path = find_chrome_executable()
    assert browser_path is not None, 'FX workflow requires installed Chromium'
    external, errors = [], []
    with _local_demo_server(tmp_path, timeout_seconds=45) as base:
        with sync_playwright() as runtime:
            browser = runtime.chromium.launch(executable_path=str(browser_path), headless=True)
            page = browser.new_page(viewport={'width':width,'height':height}, accept_downloads=True)
            page.on('pageerror', lambda error:errors.append(str(error)))
            def route(request_route):
                if urlsplit(request_route.request.url).hostname in {'localhost','127.0.0.1','::1'}:
                    request_route.continue_()
                else:
                    external.append(request_route.request.url)
                    request_route.abort()
            page.route('**/*', route)
            page.goto(base, wait_until='domcontentloaded')
            summary = page.locator('summary').filter(has_text='Currency conversion review')
            expect(summary).to_be_visible()
            assert not (tmp_path/'calls.txt').exists()
            if summary.locator('..').get_attribute('open') is None: summary.click()
            page.get_by_role('button', name='Fetch FX reference', exact=True).click()
            review = page.get_by_role('region', name='Historical currency translation', exact=True)
            expect(review).to_contain_text('7.625000 USD/ordinary share')
            expect(review).to_contain_text('point-in-time availability remain unverified')
            assert (tmp_path/'calls.txt').read_text().splitlines() == ['fetch']
            with page.expect_download() as download_info:
                page.get_by_role('button', name='Download currency review', exact=True).click()
            download = download_info.value
            archive_path = tmp_path/'review.zip'
            download.save_as(str(archive_path))
            with ZipFile(archive_path) as archive:
                assert set(archive.namelist()) == {'fx.xml','receipt.json','SOURCE.txt','review.json'}
                assert archive.read('fx.xml') == XML
                result = json.loads(archive.read('review.json'))
                assert result['derived_amount_decimal'] == '7.625000'
                assert result['valuation_eligible'] is False and result['point_in_time_eligible'] is False
                assert b'private-thesis-unique' not in archive.read('review.json')
            for destination in ('sources','saved valuation','saved sources'):
                page.get_by_role('combobox', name='View', exact=True).click()
                page.get_by_role('option', name=destination, exact=True).click()
                summary=page.locator('summary').filter(has_text='Currency conversion review')
                expect(summary).to_be_visible()
                if summary.locator('..').get_attribute('open') is None: summary.click()
                expect(review).to_be_visible()
                expect(review).to_contain_text('7.625000 USD/ordinary share')
                assert (tmp_path/'calls.txt').read_text().splitlines() == ['fetch']
            page.get_by_role('combobox', name='View', exact=True).click()
            page.get_by_role('option', name='monitor', exact=True).click()
            expect(page.get_by_role('heading',name='Saved online research updates',exact=True)).to_be_visible()
            expect(page.get_by_role('button',name='Fetch FX reference',exact=True)).to_have_count(0)
            expect(review).to_have_count(0)
            assert (tmp_path/'calls.txt').read_text().splitlines() == ['fetch']
            page.get_by_role('combobox', name='View', exact=True).click()
            page.get_by_role('option', name='sources', exact=True).click()
            summary=page.locator('summary').filter(has_text='Currency conversion review')
            expect(summary).to_be_visible()
            if summary.locator('..').get_attribute('open') is None: summary.click()
            expect(review).to_be_visible()
            expect(review).to_contain_text('7.625000 USD/ordinary share')
            page.get_by_role('combobox', name='Profile', exact=True).click()
            page.get_by_role('option', name='two', exact=True).click()
            expect(review).to_have_count(0)
            assert (tmp_path/'calls.txt').read_text().splitlines() == ['fetch']
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
            browser.close()
    assert external == [] and errors == []
    assert not (tmp_path/'server-provider-attempts.txt').exists()
