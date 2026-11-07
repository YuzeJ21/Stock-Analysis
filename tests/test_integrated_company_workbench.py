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


def _company_brief(at):
    return next(m.value for m in at.markdown if 'aria-label="Company Brief"' in m.value)


@pytest.mark.parametrize('section', ['overview','financials','valuation','notes','sources'])
def test_company_answer_cards_precede_controls_on_every_section(monkeypatch, section):
    calls=_sources(monkeypatch)
    at=AppTest.from_function(_app)
    at.query_params['section']=section
    at.run()

    assert not at.exception
    brief=_company_brief(at)
    assert brief.count('aria-label="Company research summary"')==1
    for answer in ('price','financial','valuation'):
        assert brief.count(f'data-company-answer="{answer}"')==1
    assert brief.index('</h1>') < brief.index('aria-label="Company research summary"')
    elements=list(at.main)
    header_index=next(i for i,el in enumerate(elements) if el.type=='markdown' and el.value==brief)
    update_index=next(i for i,el in enumerate(elements) if el.type=='button' and el.key=='company-refresh-all')
    section_index=next(i for i,el in enumerate(elements) if el.type=='radio' and el.label=='Company research sections')
    assert header_index < min(update_index,section_index)
    assert calls=={'financial':0,'prices':0}


def test_company_valuation_answer_updates_on_refresh_and_reuses_peer_cache_in_other_sections(monkeypatch):
    import src.online_peer_sources as sources
    from test_online_peer_valuation_ui import _setup

    calls,other=_setup(monkeypatch)
    at=AppTest.from_function(_app).run()
    at.radio[0].set_value('valuation').run()
    before=_company_brief(at)
    assert '2026-10-30' not in before and not calls

    next(button for button in at.button if button.label=='Refresh peer valuation').click().run()
    refreshed=_company_brief(at)
    assert '2026-10-30' in refreshed
    assert 'Annual P/E 20.0% above industry references' in text(at)
    observed_calls=list(calls)
    assert observed_calls

    for section in ('sources','financials','notes','overview'):
        at.radio[0].set_value(section).run()
        assert not at.exception
        assert '2026-10-30' in _company_brief(at)
    assert calls==observed_calls and other=={'financial':0,'prices':0}

    at.radio[0].set_value('valuation').run()
    monkeypatch.setattr(sources,'observe_vendor',lambda *a,**kw:(_ for _ in ()).throw(OSError('private exception')))
    next(button for button in at.button if button.label=='Refresh peer valuation').click().run()
    assert not at.exception
    assert '2026-10-30' not in _company_brief(at)
    assert 'Annual P/E 20.0% above industry references' not in text(at)


def test_five_sections_are_visible_without_loading_legacy_tools_or_fetching(monkeypatch):
    calls=_sources(monkeypatch)
    at=AppTest.from_function(_app).run()
    assert not at.exception
    assert 'section' not in at.query_params
    assert at.radio[0].options==['Overview','Financial Trends','Valuation & Peers','Research Notes','Data Sources']
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
    assert 'SAVED-TOOL-financials' in text(at)
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
    at.radio[0].set_value('financials').run()
    assert 'SAVED-TOOL' not in text(at)
    at.radio[0].set_value('valuation').run()
    assert 'SAVED-TOOL' not in text(at)
    assert 'No supported peer comparison yet' in text(at)
    at.radio[0].set_value('notes').run()
    assert 'SAVED-TOOL' not in text(at)
    assert 'identity' in text(at)
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
    nav=[r for r in at.radio if r.options==['Overview','Financial Trends','Valuation & Peers','Research Notes','Data Sources']]
    assert len(nav)==1
    nav[0].set_value('financials').run()
    assert not at.exception
    assert calls==[], 'Financial Trends must not require the saved quote-backed report'
    assert any(e.label=='Business Trend (saved evidence)' for e in at.expander)
    nav[0].set_value('valuation').run()
    assert not at.exception
    assert calls==['AMD']
    assert 'Scenario Lab' in text(at)
    assert any(e.label=='Peer Read-Through (saved evidence)' for e in at.expander)
    at.radio[0].set_value('notes').run()
    assert not at.exception
    assert calls==['AMD']
    assert any(e.label=='Research Decision Lab & History' for e in at.expander)
    assert any(e.label=='Forward View & Catalysts (saved evidence)' for e in at.expander)
    assert any(e.label=='Add a reviewed research record' for e in at.expander)
    assert any(e.label=='HTML Research Brief' for e in at.expander)


def test_saved_quarterly_trend_remains_visible_without_local_quote(tmp_path, monkeypatch):
    import pandas as pd
    from src import dashboard

    data_dir = tmp_path / 'data'
    (data_dir / 'earnings_nowcast').mkdir(parents=True)
    pd.DataFrame([{'ticker':'SYN1','name':'Sample Company','asset_type':'company'}]).to_csv(
        data_dir / 'universe_master.csv', index=False)
    pd.DataFrame([{
        'ticker':'SYN1','theme':'sample','default_purpose':'research',
        'market_cap_bucket':'unknown','notes':'Constructed test company',
    }]).to_csv(data_dir / 'universe.csv', index=False)
    rows = []
    for period, end, revenue, eps in (
        ('2024-Q1', '2024-03-31', 100.0, 1.0),
        ('2025-Q1', '2025-03-31', 150.0, 1.5),
    ):
        rows.append({
            'ticker':'SYN1','fiscal_period':period,'period_end_date':end,
            'reported_at':period[:4]+'-05-01T00:00:00Z',
            'revenue_actual':revenue,'eps_actual':eps,'source':'sec_companyfacts',
            'source_ref':'sec:SYN1:'+period,'retrieved_at':period[:4]+'-05-02T00:00:00Z',
            'revenue_currency':'USD','revenue_unit_scale':1.0,'revenue_basis':'gaap',
            'eps_currency':'USD','eps_basis':'gaap','eps_share_basis':'diluted',
            'eps_operations_basis':'continuing','split_adjustment_basis':'as_reported',
        })
    pd.DataFrame(rows).to_csv(data_dir / 'earnings_nowcast' / 'quarterly_actuals.csv', index=False)
    assert not (data_dir / 'prices.csv').exists()
    assert 'SYN1' in dashboard.build_provider('local', base_dir=tmp_path).list_local_tickers()
    monkeypatch.setattr(dashboard, 'DATA_DIR', data_dir)
    calls = []
    original = dashboard.build_stock_report
    def tracked(*args, **kwargs):
        calls.append(args[0])
        return original(*args, **kwargs)
    monkeypatch.setattr(dashboard, 'build_stock_report', tracked)

    at = AppTest.from_string(
        "from pathlib import Path\n"
        "from src import dashboard\n"
        f"root = Path({str(tmp_path)!r})\n"
        "context = dashboard.build_profile_context(project_root=root)\n"
        "provider = dashboard.build_provider('local', base_dir=root)\n"
        "dashboard.render_company_workbench(provider, context, {'queue': []}, None)\n",
        default_timeout=30,
    )
    at.query_params.update(mode='research', page='company-workbench', ticker='SYN1')
    at.run()
    at.radio[0].set_value('financials').run()

    assert not at.exception
    assert calls == []
    assert any(e.label == 'Business Trend (saved evidence)' for e in at.expander)
    trend = next(frame.value for frame in at.dataframe if 'Latest period' in frame.value.columns)
    revenue = trend.loc[trend['Metric'] == 'Revenue'].iloc[0]
    assert revenue['Latest period'] == '2025-Q1'
    assert float(revenue['Latest value']) == 150.0


def test_saved_scenario_assumptions_survive_section_roundtrip_without_cross_company_reuse(monkeypatch):
    from src import dashboard
    prepared=[];snapshots=[]
    prepare=dashboard.run_scenario_lab_from_state
    build=dashboard.build_company_workbench_html_snapshot
    def tracked_prepare(*args,**kwargs):
        session=prepare(*args,**kwargs);prepared.append(session);return session
    def tracked_build(inputs):
        snapshots.append(inputs);return build(inputs)
    monkeypatch.setattr(dashboard,'run_scenario_lab_from_state',tracked_prepare)
    monkeypatch.setattr(dashboard,'build_company_workbench_html_snapshot',tracked_build)
    at=AppTest.from_function(_dashboard_app,default_timeout=30)
    at.query_params.update(mode='research',page='company-workbench',ticker='NVDA')
    at.run();at.radio[0].set_value('valuation').run()
    next(s for s in at.slider if s.label=='WACC').set_value(.12).run()
    at.radio[0].set_value('notes').run()
    at.run()  # A second notes rerun must retain the scenario used by the exported snapshot.
    assert prepared[-1].parameters.wacc==pytest.approx(.12)
    assert snapshots[-1].scenario_lab_result is prepared[-1].result
    at.radio[0].set_value('financials').run()
    at.radio[0].set_value('valuation').run()
    assert not at.exception
    assert next(s for s in at.slider if s.label=='WACC').value==pytest.approx(.12)
    at.query_params['ticker']='AMD';at.run()
    at.radio[0].set_value('valuation').run()
    assert not at.exception
    assert next(s for s in at.slider if s.label=='WACC').value!=pytest.approx(.12)


def test_unsaved_research_draft_survives_section_roundtrip():
    at=AppTest.from_function(_dashboard_app,default_timeout=30)
    at.query_params.update(mode='research',page='company-workbench',ticker='NVDA')
    at.run();at.radio[0].set_value('notes').run()
    next(t for t in at.text_area if t.label=='Summary').input('Synthetic unsaved draft').run()
    at.radio[0].set_value('financials').run()
    at.radio[0].set_value('notes').run()
    assert not at.exception
    assert next(t for t in at.text_area if t.label=='Summary').value=='Synthetic unsaved draft'


def test_retention_touches_only_current_scope_editable_inputs():
    from src.company_workbench_ui import retain_saved_tool_inputs
    from src.scenario_lab_session import scenario_lab_widget_keys
    from src.research_record_authoring_ui import authoring_session_key
    touched=[]
    class State(dict):
        def __setitem__(self,key,value):
            touched.append(key);super().__setitem__(key,value)
    scenario=scenario_lab_widget_keys('default','FICT')['wacc']
    draft=authoring_session_key('default','FICT','field:thesis:summary')
    confirmed=authoring_session_key('default','FICT','confirmed')
    action=authoring_session_key('default','FICT','validate')
    other=scenario_lab_widget_keys('other-profile','FICT')['wacc']
    state=State({scenario:.12,draft:'Synthetic unsaved note',confirmed:True,action:True,other:.15})
    retain_saved_tool_inputs(state,'default','FICT')
    assert set(touched)=={scenario,draft}
