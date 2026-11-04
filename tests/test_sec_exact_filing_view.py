from copy import deepcopy

import pytest

from test_sec_inline_filing import _extract,OBSERVED
from test_sec_exact_filing import _fetch


def test_filing_action_is_company_period_scoped_and_rerenders_reuse_without_network():
    from src.sec_exact_filing import get_company_filing_preview
    state={};calls=[];options=dict(period_kind='quarterly',user_agent='Research',fetcher=_fetch(calls),observed_at=OBSERVED)
    assert get_company_filing_preview('FICT',state,refresh_requested=False,**options)['status']=='not_requested'
    assert calls==[]
    first=get_company_filing_preview('FICT',state,refresh_requested=True,**options)
    assert first['status']=='inspection_only' and len(calls)==3
    cached=get_company_filing_preview('FICT',state,refresh_requested=False,**options)
    assert cached==first and len(calls)==3
    assert get_company_filing_preview('OTHER',state,refresh_requested=False,**options)['status']=='not_requested'
    assert get_company_filing_preview('FICT',state,refresh_requested=False,**{**options,'period_kind':'annual'})['status']=='not_requested'
    assert get_company_filing_preview('FICT',state,refresh_requested=False,expected_cik='0000009999',**options)['status']=='withheld'


def test_exact_filing_view_labels_direct_and_cumulative_periods_and_personal_archive_rights():
    from src.sec_exact_filing_view import filing_preview_html
    html=filing_preview_html(_extract(),'FICT','quarterly')
    assert 'Exact SEC filing' in html and '2026-04-01' in html and '2026-01-01' in html
    assert 'Cumulative' in html and 'not a single quarter' in html
    assert 'Regulated and unregulated operating revenue' in html
    assert '0000004321-26-000001' in html and '#revenue' in html
    assert 'Archive source rights' in html and 'personal inspection' in html.lower()
    assert 'Companyfacts coverage' in html and 'SHA-256' in html
    annual=filing_preview_html(_extract(kind='annual'),'FICT','annual')
    assert 'TWD' in annual and 'Revenue · customer contracts' in annual
    assert 'RevenueFromContractsWithCustomers' in annual


def test_invalid_or_commercial_cached_filing_cannot_display_amounts(monkeypatch):
    from src.sec_exact_filing_view import filing_preview_html
    from src.sec_exact_filing import get_company_filing_preview,SESSION_KEY
    packet=_extract();bad=deepcopy(packet);bad['periods'][0]['fields']['revenue']['value']=999
    assert '<article' not in filing_preview_html(bad,'FICT','quarterly')
    assert '<article' not in filing_preview_html(packet,'OTHER','quarterly')
    monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE','1')
    state={SESSION_KEY:dict(ticker='FICT',period_kind='quarterly',packet=packet)}
    assert get_company_filing_preview('FICT',state,period_kind='quarterly',refresh_requested=False,user_agent='Research')['status']=='withheld'
    assert '<article' not in filing_preview_html(packet,'FICT','quarterly')


def test_exact_filing_cards_reflow_in_real_streamlit_browser(tmp_path):
    from playwright.sync_api import sync_playwright
    from src.public_performance_gate import _local_demo_server
    from src.sec_exact_filing_view import filing_preview_html
    html=filing_preview_html(_extract(),'FICT','quarterly')+filing_preview_html(_extract(kind='annual'),'FICT','annual')
    (tmp_path/'src').mkdir()
    (tmp_path/'src/dashboard.py').write_text('import streamlit as st\nst.markdown('+repr(html)+',unsafe_allow_html=True)\n')
    with _local_demo_server(tmp_path,timeout_seconds=30) as base:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True);page=browser.new_page()
            page.goto(base,wait_until='domcontentloaded')
            page.get_by_role('region',name='Exact SEC filing',exact=True).first.wait_for(timeout=15000)
            for width,height in [(1280,900),(390,844),(195,422)]:
                page.set_viewport_size({'width':width,'height':height})
                assert page.get_by_role('region',name='Exact SEC filing',exact=True).count()==2
                geometry=page.evaluate("() => [...document.querySelectorAll('.exact-sec-filing,.exact-sec-filing article')].map(x=>[x.clientWidth,x.scrollWidth])")
                assert all(a==b for a,b in geometry)
            browser.close()


def test_workbench_direct_period_choice_passes_annual_action_and_expected_issuer(monkeypatch):
    from types import SimpleNamespace
    from src import dashboard
    class Panel:
        def __enter__(self):return self
        def __exit__(self,*args):return False
    calls=[];rendered=[]
    monkeypatch.setattr(dashboard,'st',SimpleNamespace(session_state={},expander=lambda *a,**kw:Panel(),
        radio=lambda label,options,**kw:'annual',button=lambda *a,**kw:True,markdown=lambda value,**kw:rendered.append(value)))
    monkeypatch.setattr(dashboard,'get_company_filing_preview',lambda ticker,state,**kw:calls.append((ticker,kw['period_kind'],kw['expected_cik'],kw['refresh_requested'])) or _extract(kind='annual'))
    dashboard.render_company_sec_filing_check('FICT',expected_cik='0000001234')
    assert calls==[('FICT','annual','0000001234',True)]
    assert 'TWD' in ''.join(rendered) and '2025-12-31' in ''.join(rendered)
