"""One research journey, lazy sections, explicit transport and identity isolation."""
from copy import deepcopy

import pytest
from streamlit.testing.v1 import AppTest

from tests.test_company_workbench_sections import financial_view
from tests.test_online_company_prices import _fetch


def _sources(monkeypatch, *, financial_failure=False):
    import src.sec_annual_history as annual
    import src.online_company_prices as prices
    calls={'financial':0,'prices':0}
    def facts(*args,**kwargs):
        calls['financial']+=1
        if financial_failure:raise TimeoutError('Synthetic source timeout')
        return financial_view()
    raw=_fetch()
    def price(url):
        calls['prices']+=1
        return raw(url)
    monkeypatch.setattr(annual,'fetch_sec_online_research_view',facts)
    monkeypatch.setattr(prices,'_raw_fetch',price)
    monkeypatch.setenv('SEC_USER_AGENT','Synthetic research contact@example.com')
    return calls


def _app():
    import streamlit as st
    from src.company_workbench_ui import render_integrated_company
    ticker=st.query_params.get('ticker','FICT')
    candidate={'cik':'0000001234','title':'Synthetic online company'} if st.query_params.get('online')=='1' else None
    def saved(section):st.markdown('SAVED-TOOL-'+section)
    def sources(bundle):st.markdown('SOURCE-PROOF-'+str(bundle['financial'].get('status')))
    render_integrated_company(st,ticker,profile_scope='synthetic',saved_available=True,
                              online_candidate=candidate,render_saved=saved,render_sources=sources)


def text(at):return '\n'.join(m.value for m in at.markdown)


def test_five_sections_are_visible_without_loading_legacy_tools_or_fetching(monkeypatch):
    calls=_sources(monkeypatch)
    at=AppTest.from_function(_app).run()
    assert not at.exception
    assert 'section' not in at.query_params
    assert at.radio[0].options==['概览','财务趋势','估值与同行','研究记录','数据来源']
    assert text(at).count('<h1')==1
    assert 'SAVED-TOOL' not in text(at)
    assert 'Open evidence and analysis modules' not in text(at)
    assert calls=={'financial':0,'prices':0}


def test_combined_update_loads_once_and_pane_changes_reuse_same_source_attempts(monkeypatch):
    calls=_sources(monkeypatch)
    at=AppTest.from_function(_app).run()
    at.button(key='company-refresh-all').click().run()
    assert not at.exception
    assert calls=={'financial':1,'prices':1}
    assert '150' in text(at) and '2025-12-31' in text(at)
    at.radio[0].set_value('financials').run()
    assert 'Historical annual financials' in text(at)
    assert 'No source-backed quarterly actual is available' not in text(at)
    assert 'SAVED-TOOL' not in text(at)
    at.radio[0].set_value('valuation').run()
    assert 'SAVED-TOOL-valuation' in text(at)
    at.radio[0].set_value('notes').run()
    assert 'SAVED-TOOL-notes' in text(at)
    at.radio[0].set_value('sources').run()
    assert 'SOURCE-PROOF-inspection_only' in text(at)
    assert calls=={'financial':1,'prices':1}
    assert not at.exception


def test_financial_timeout_keeps_price_chart_and_does_not_retry_on_switch(monkeypatch):
    calls=_sources(monkeypatch,financial_failure=True)
    at=AppTest.from_function(_app).run()
    at.button(key='company-refresh-all').click().run()
    assert 'Daily price history' in text(at)
    at.radio[0].set_value('financials').run()
    at.radio[0].set_value('overview').run()
    assert calls=={'financial':1,'prices':1}
    assert 'Daily price history' in text(at)
    assert not at.exception


def test_online_identity_cannot_open_same_symbol_saved_models_or_authoring(monkeypatch):
    calls=_sources(monkeypatch)
    at=AppTest.from_function(_app)
    at.query_params['online']='1';at.run()
    at.radio[0].set_value('valuation').run()
    assert 'SAVED-TOOL' not in text(at)
    assert 'No supported peer comparison yet' in text(at)
    at.radio[0].set_value('notes').run()
    assert 'SAVED-TOOL' not in text(at)
    assert '身份' in text(at)
    assert calls=={'financial':0,'prices':0}
    assert not at.exception


def test_online_valuation_reuses_verified_instrument_path_without_fetch(monkeypatch):
    from tests.test_company_research_scope import context
    from src.security_classification import SESSION_KEY
    calls=_sources(monkeypatch)
    at=AppTest.from_function(_app)
    at.session_state[SESSION_KEY]=context('',entity='investment-company',forms=['N-CSR'])
    at.query_params['online']='1'
    at.run()
    at.radio[0].set_value('valuation').run()
    assert not at.exception
    assert 'Use the instrument-specific research path first' in text(at)
    assert 'SAVED-TOOL' not in text(at)
    assert calls=={'financial':0,'prices':0}


def test_ticker_switch_cannot_render_prior_company_cache(monkeypatch):
    calls=_sources(monkeypatch)
    at=AppTest.from_function(_app).run()
    at.button(key='company-refresh-all').click().run()
    at.query_params['ticker']='OTHER';at.run()
    assert 'OTHER Company Brief' in text(at)
    assert 'USD 11' not in text(at)
    assert '2025-12-31' not in text(at)
    assert calls=={'financial':1,'prices':1}
    assert not at.exception


def test_known_online_identity_conflict_never_exposes_numerical_source_rows(monkeypatch):
    from src.company_workbench_ui import load_workbench_observations
    calls=_sources(monkeypatch)
    result=load_workbench_observations('FICT',{},refresh_financials=True,refresh_prices=True,
                                     expected_cik='0000009999',user_agent='Test contact@example.com')
    assert result['projection']['identity_conflict'] is True
    assert result['financial']['status']=='unavailable'
    assert result['prices']['status']=='unavailable'
    assert result['projection']['facts']=={}
    assert calls=={'financial':1,'prices':1}


def _dashboard_app():
    from src.dashboard import main
    main()


def test_real_workbench_route_is_lazy_and_reuses_saved_tools_when_requested(monkeypatch):
    from src import dashboard
    calls=[];original=dashboard.build_stock_report
    def tracked(*args,**kwargs):
        calls.append(args[0]);return original(*args,**kwargs)
    monkeypatch.setattr(dashboard,'build_stock_report',tracked)
    at=AppTest.from_function(_dashboard_app,default_timeout=30)
    at.query_params.update({'mode':'research','page':'company-workbench','ticker':'AMD'})
    at.run()
    assert not at.exception
    assert calls==[], 'Overview must not build the saved DCF report'
    nav=[r for r in at.radio if r.options==['概览','财务趋势','估值与同行','研究记录','数据来源']]
    assert len(nav)==1
    nav[0].set_value('valuation').run()
    assert not at.exception
    assert calls==['AMD']
    assert 'Scenario Lab' in text(at)
    at.radio[0].set_value('notes').run()
    assert not at.exception
    assert calls==['AMD']
    assert 'Research Decision Lab' in text(at)
    assert any(e.label=='Add a reviewed research record' for e in at.expander)
    assert any(e.label=='HTML Research Brief' for e in at.expander)
