from copy import deepcopy

import pytest

from test_online_us_universe import _inventory, _fetch, OBSERVED
from test_sec_industry_financials import _foreign_view


def test_inventory_actions_are_explicit_and_cache_read_is_recomputed_without_fetches():
    from src.online_us_universe import get_online_us_universe
    calls = []; session = {}; options = dict(user_agent='Research', source_fetcher=_fetch(calls), observed_at=OBSERVED)
    assert get_online_us_universe(session, **options)['status'] == 'not_requested'
    assert calls == []
    state = get_online_us_universe(session, load_requested=True, **options)
    assert state['coverage']['issuer_denominator'] == 3 and state['coverage']['unprobed_issuer_count'] == 3
    assert len(calls) == 4
    state = get_online_us_universe(session, inspect_requested=True, batch_size=1, **options)
    assert state['coverage']['attempted_issuer_count'] == 1
    count = len(calls)
    cached = get_online_us_universe(session, **options)
    assert cached['coverage'] == state['coverage'] and len(calls) == count
    reset = get_online_us_universe(session, load_requested=True, **options)
    assert reset['coverage']['attempted_issuer_count'] == 0


def test_foreign_view_retains_units_periods_sources_and_separates_interim():
    from src.online_us_universe_view import foreign_financials_html
    html = foreign_financials_html(_foreign_view())
    assert 'IFRS financials' in html and 'EUR' in html
    assert 'Cumulative / interim' in html and 'not a single quarter' in html
    assert '2026-04-01' in html and '2026-01-01' in html
    assert '0000001234-26-000002' in html and '2026-08-01' in html
    assert 'ifrs-full:Revenue' in html and 'SHA-256' in html
    assert 'No FX conversion' in html
    broken = _foreign_view(); broken['foreign_financials']['annual'][0]['fields']['revenue']['unit'] = 'USD'
    assert '<article' not in foreign_financials_html(broken)


def test_full_inventory_ui_has_separate_listing_and_issuer_denominators_with_gaps():
    from src.online_us_universe_view import universe_coverage_html
    state = dict(inventory=_inventory(), observations=[])
    html = universe_coverage_html(state)
    assert '6 observed listings' in html and '3 issuer candidates' in html
    assert '3 unprobed' in html and '1 known ETF' in html
    assert 'LTSE' in html and 'GIX' in html
    assert 'not yet established' in html and 'domicile' in html
    assert 'WUT' in html
    broken = deepcopy(state); broken['inventory']['rows'][0]['symbol'] = '<script>alert(1)</script>'
    assert '<script>' not in universe_coverage_html(broken)
    assert '6 observed listings' not in universe_coverage_html(broken)


def test_commercial_mode_cannot_reuse_or_render_personal_universe_or_foreign_cache(monkeypatch):
    from src.online_us_universe import get_online_us_universe, SESSION_KEY
    from src.online_us_universe_view import universe_coverage_html, foreign_financials_html
    state = dict(inventory=_inventory(), observations=[]); session = {SESSION_KEY: state}
    monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE', '1')
    assert get_online_us_universe(session, user_agent='Research')['status'] == 'unavailable'
    assert '6 observed listings' not in universe_coverage_html(state)
    assert '<article' not in foreign_financials_html(_foreign_view())


def test_inventory_and_foreign_cards_reflow_in_real_browser(tmp_path):
    from playwright.sync_api import sync_playwright
    from src.public_performance_gate import _local_demo_server
    from src.online_us_universe_view import universe_coverage_html, foreign_financials_html
    html = universe_coverage_html(dict(inventory=_inventory(), observations=[])) + foreign_financials_html(_foreign_view())
    (tmp_path/'src').mkdir()
    (tmp_path/'src/dashboard.py').write_text('import streamlit as st\nst.markdown('+repr(html)+',unsafe_allow_html=True)\n')
    with _local_demo_server(tmp_path, timeout_seconds=30) as base:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True); page=browser.new_page()
            page.goto(base,wait_until='domcontentloaded')
            page.get_by_role('region',name='U.S. listing coverage',exact=True).wait_for(timeout=15000)
            for width,height in [(1280,900),(390,844),(195,422)]:
                page.set_viewport_size({'width':width,'height':height})
                assert page.get_by_role('region',name='IFRS financials',exact=True).count()==1
                sizes=page.evaluate("() => [...document.querySelectorAll('.online-universe,.online-foreign,.online-foreign article')].map(x=>[x.clientWidth,x.scrollWidth])")
                assert all(a==b for a,b in sizes)
            browser.close()
