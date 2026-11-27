"""Desktop/phone source basis → save → Monitor reload → historical return."""
from urllib.parse import urlsplit
from urllib.parse import parse_qs

import pytest

from sap_depositary_fixtures import write_replay_app, research_context
from src.online_research_context_store import list_research_contexts, save_research_context
from src.public_performance_gate import _local_demo_server, find_chrome_executable


@pytest.mark.parametrize('width,height', [(1280, 900), (390, 844)], ids=['desktop', 'phone'])
def test_native_sap_basis_survives_save_monitor_reload_and_exact_return(tmp_path, width, height):
    from playwright.sync_api import sync_playwright, expect

    write_replay_app(tmp_path)
    browser_path = find_chrome_executable()
    assert browser_path is not None, 'The SAP release check requires installed Chromium'
    external = []
    errors = []
    with _local_demo_server(tmp_path, timeout_seconds=45) as base:
        with sync_playwright() as runtime:
            browser = runtime.chromium.launch(executable_path=str(browser_path), headless=True)
            page = browser.new_page(viewport={'width': width, 'height': height})
            page.on('pageerror', lambda error: errors.append(str(error)))

            def route(request_route):
                url = request_route.request.url
                if urlsplit(url).hostname in {'localhost', '127.0.0.1', '::1'}:
                    request_route.continue_()
                else:
                    external.append(url)
                    request_route.abort()

            page.route('**/*', route)
            page.goto(base, wait_until='domcontentloaded')
            expect(page.get_by_text('Reported annual diluted EPS (native currency)', exact=True).filter(visible=True)).to_have_count(1)
            expect(page.locator('p').filter(has_text='6.10 EUR/common share').filter(visible=True)).to_have_count(1)
            expect(page.locator('p').filter(has_text='2025-01-01 → 2025-12-31').filter(visible=True)).to_have_count(1)
            page.get_by_text('Saved online research · replay and compare', exact=True).click()
            page.get_by_role('button', name='Save research snapshot', exact=True).click()
            expect(page.get_by_text('Research snapshot saved:', exact=False)).to_be_visible()
            page.wait_for_function("""() => document.querySelector('[data-testid="stApp"]')
                ?.getAttribute('data-test-script-state') === 'notRunning'""")
            value = research_context()
            scope = {key:value[key] for key in ('profile_key','ticker','sec_cik')}
            first = list_research_contexts(**scope, project_root=tmp_path)[0]['snapshot_id']
            page.get_by_role('button', name='Open historical research snapshot', exact=True).click()
            page.wait_for_url('**research_snapshot=**')
            expect(page.get_by_role('heading', name='Valuation & Peers', exact=True)).to_be_visible()
            page.get_by_text('Data Sources', exact=True).click()
            expect(page.get_by_role('heading', name='Data Sources', exact=True)).to_be_visible()
            page.wait_for_function("""() => document.querySelector('[data-testid="stApp"]')
                ?.getAttribute('data-test-script-state') === 'notRunning'""")
            assert parse_qs(urlsplit(page.url).query)['research_snapshot'] == [first]
            assert parse_qs(urlsplit(page.url).query)['section'] == ['sources']
            decoy = research_context()
            decoy['observed_at'] = '2026-11-08T13:00:00Z'
            decoy['notes'] = {'thesis':'Newer decoy must not replace the pinned snapshot.'}
            second = save_research_context(decoy, **scope, project_root=tmp_path)
            assert second['snapshot_id'] != first
            page.get_by_role('button', name='Open Monitor', exact=True).click()
            page.wait_for_url('**page=monitor**')

            for reload in (False, True):
                if reload:
                    page.reload(wait_until='domcontentloaded')
                expect(page.get_by_role('heading', name='Saved online research updates', exact=True)).to_be_visible()
                page.wait_for_function("""() => document.querySelector('[data-testid="stApp"]')
                    ?.getAttribute('data-test-script-state') === 'notRunning'""")
                saved = page.get_by_role('region', name='Saved SAP filing evidence', exact=True)
                expect(saved).to_be_visible()
                expect(page.get_by_text('Snapshot ' + first[:12], exact=True)).to_be_visible()
                assert parse_qs(urlsplit(page.url).query)['return_research_snapshot'] == [first]
                summary = saved.locator('summary', has_text='Selected security and related issuer symbols')
                if summary.locator('..').get_attribute('open') is None:
                    summary.click()
                expect(saved.locator('p').filter(has_text='6.10 EUR/common share')).to_be_visible()
                expect(saved.locator('p').filter(has_text='1 ordinary shares/ADR')).to_be_visible()
                expect(saved.get_by_text('ADS valuation remains withheld.', exact=True)).to_be_visible()
                assert saved.locator('a[href*="otherlisted.txt"]').count() == 1
            page.get_by_role('button', name='Reopen exact saved research', exact=True).click()
            page.wait_for_url('**research_snapshot=**')
            page.wait_for_function("""() => document.querySelector('[data-testid="stApp"]')
                ?.getAttribute('data-test-script-state') === 'notRunning'""")
            saved = page.get_by_role('region', name='Saved SAP filing evidence', exact=True)
            expect(saved).to_be_visible()
            summary = saved.locator('summary', has_text='Selected security and related issuer symbols')
            if summary.locator('..').get_attribute('open') is None:
                summary.click()
            expect(saved.locator('p').filter(has_text='6.10 EUR/common share')).to_be_visible()
            assert parse_qs(urlsplit(page.url).query)['research_snapshot'] == [first]
            assert parse_qs(urlsplit(page.url).query)['section'] == ['sources']
            assert '6.10 USD' not in page.locator('body').inner_text()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
            browser.close()
    assert external == [] and errors == []
    assert not (tmp_path / 'server-provider-attempts.txt').exists()
