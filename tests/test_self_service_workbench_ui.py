"""Online-only tools are reachable through the real Workbench without saved CSVs."""
from streamlit.testing.v1 import AppTest
import pytest


@pytest.mark.parametrize('reason', ['peer_subject_filing_version_differs_from_current_financials',
    'peer_subject_price_differs_from_current_prices','peer_subject_price_date_differs_from_current_prices',
    'latest_annual_filing_not_corroborated'])
def test_headline_peer_result_uses_shared_current_context_hold(reason):
    from src.online_research_tools_ui import qualify_peer_view
    original = dict(status='research_comparison',reason=None,subject={'eps':2,'multiple':30},
                    peers=[{'ticker':'FA'}],peer_count=3,peer_median=20,premium_fraction=.5)
    context = {'peer_read_through': {'status':'withheld','reason':reason}}
    held = qualify_peer_view(original,context)
    assert held['status'] == 'withheld' and held['reason'] == reason
    assert held['subject'] is None and held['peer_count'] == 0
    assert held['peer_median'] is None and held['premium_fraction'] is None
    assert original['subject']['eps'] == 2
    from src.online_peer_valuation_ui import _reason
    assert 'could not be verified. This input is withheld.' not in _reason(reason)


def test_monitor_handoff_retains_only_scoped_online_scenario_drafts():
    from src.company_workbench_ui import retain_saved_tool_inputs
    class TrackingState(dict):
        touched = set()
        def __setitem__(self,key,value):
            self.touched.add(key)
            super().__setitem__(key,value)
    key = 'online-scenario:personal:FICT:0000001234:input:revenue_growth'
    other = 'online-scenario:personal:FICT:0000009999:input:revenue_growth'
    state = TrackingState({key:22.,other:9.})
    retain_saved_tool_inputs(state,'personal','FICT',identity_scope='0000001234')
    assert key in state.touched and other not in state.touched


def test_personal_snapshot_ui_remains_held_in_commercial_mode(monkeypatch):
    monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE','1')
    app = AppTest.from_function(_app)
    app.query_params.update(section='notes')
    app.run()
    assert not app.exception
    assert not any(b.label == 'Save research snapshot' for b in app.button)
    assert any('unavailable in this workspace' in m.value for m in app.info)


@pytest.mark.parametrize('section',['overview','financials','valuation','notes','sources'])
def test_canonical_navigation_retains_exact_research_snapshot_scope(section):
    from src.dashboard_navigation import canonical_workspace_query
    query = dict(mode='research',page='company-workbench',ticker='FICT',section=section,
                 research_cik='0000001234',research_snapshot='a'*64)
    assert canonical_workspace_query('research','Company Workbench',query) == query


def test_monitor_reopens_selected_single_snapshot_when_a_newer_one_exists(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import Mock

    from src import online_research_context_store as store
    from src.dashboard_navigation import canonical_workspace_query
    from src.online_research_tools_ui import render_online_research_monitor
    from src.research_workspace import MonitorOrigin, return_to_research_workbench

    scope = dict(profile_key='private', ticker='FICT', sec_cik='0000001234')
    older_id, newer_id = 'a' * 64, 'b' * 64
    query = dict(mode='research', page='monitor', return_ticker=scope['ticker'],
                 return_research_cik=scope['sec_cik'], return_research_snapshot=older_id,
                 return_section='valuation')
    assert canonical_workspace_query('research', 'Monitor', query) == query
    saved = dict(snapshot_id=older_id, observed_at='2026-11-19T23:42:00Z', context={'gaps': ['held reason']})
    load = Mock(return_value=saved)
    list_latest = Mock(return_value=[{'snapshot_id': newer_id}, saved])
    monkeypatch.delenv('COMMERCIAL_RESEARCH_MODE', raising=False)
    monkeypatch.setattr(store, 'load_research_context', load)
    monkeypatch.setattr(store, 'list_research_contexts', list_latest)
    monkeypatch.setattr(store, 'list_research_context_scopes', lambda *a, **k: {'scopes': [scope]})
    st = SimpleNamespace(markdown=Mock(), caption=Mock(), write=Mock(), button=Mock(), warning=Mock(),
                         selectbox=Mock(return_value='FICT · CIK 0000001234'), query_params=query)
    origin = MonitorOrigin(scope['profile_key'], scope['ticker'], 'valuation', None,
                           research_cik=scope['sec_cik'], research_snapshot=older_id)

    render_online_research_monitor(st, profile_key=scope['profile_key'], monitor_origin=origin)

    assert load.call_args.args == (older_id,)
    assert {key: load.call_args.kwargs[key] for key in scope} == scope
    list_latest.assert_not_called()
    st.caption.assert_any_call('Selected observation: ' + saved['observed_at'])
    st.write.assert_called_once_with('held reason')
    assert st.button.call_args.args == ('Reopen exact saved research',)
    assert st.button.call_args.kwargs['on_click'] is return_to_research_workbench
    assert st.button.call_args.kwargs['args'] == (st, origin)
    st.warning.assert_not_called()


def test_new_filing_pending_never_labels_older_revenue_as_current():
    from src.online_research_tools_ui import qualify_current_answers
    answers = ({'key':'financial','value':'Revenue USD 150','context':'2025-12-31',
                'evidence':(), 'links':()},)
    context = {'filing_coverage': {'current': {'quarterly': {
        'status':'facts_pending','reason':'Structured facts not yet published',
        'anchor':{'period_end':'2026-09-30','source_url':'https://www.sec.gov/'}}}}}
    qualified = qualify_current_answers(answers, context)
    assert qualified[0]['value'] == 'New filing · financial facts pending'
    assert '2026-09-30' in qualified[0]['context']
    assert answers[0]['value'] == 'Revenue USD 150'


def test_exact_native_annual_answer_preserves_separate_quarter_pending_status():
    from src.online_research_tools_ui import qualify_current_answers
    answers = ({'key': 'financial', 'value': 'Revenue TWD 150', 'context': '2025-12-31',
                'headline': 'Revenue up 25.0%', 'headline_context': 'Year ended 2025-12-31',
                'native_archive_annual': True, 'evidence': ('Annual observation',), 'links': ()},)
    pending = {'status': 'facts_pending', 'anchor': {'period_end': '2026-09-30'}}
    context = {'filing_coverage': {'current': {'quarterly': pending}}}
    assert qualify_current_answers(answers, context) == answers
    context['filing_coverage']['current']['annual'] = pending
    held = qualify_current_answers(answers, context)[0]
    assert held['value'] == 'New filing · financial facts pending'
    assert held['headline'] is None and 'Annual observation' not in held['evidence']


def _app():
    import streamlit as st
    from src.company_workbench_ui import render_integrated_company
    render_integrated_company(st, 'FICT', profile_scope='synthetic', saved_available=False,
        online_candidate={'cik': '0000001234', 'title': 'Synthetic company'},
        render_saved=lambda section: (_ for _ in ()).throw(AssertionError('saved model required')),
        render_sources=lambda bundle: None, render_notes=lambda bundle: None,
        enable_online_tools=True)


def test_online_tools_reachable_without_local_company_inputs(tmp_path, monkeypatch):
    from src import company_research_notes
    monkeypatch.setattr(company_research_notes, 'PROJECT_ROOT', tmp_path)
    app = AppTest.from_function(_app).run()
    assert not app.exception
    assert app.button(key='company-refresh-all').label == 'Research company'
    app.radio[0].set_value('valuation').run()
    assert not app.exception
    assert any(e.label == 'Scenario Lab · explicit assumptions' for e in app.expander)
    app.radio[0].set_value('notes').run()
    assert not app.exception
    assert any(e.label == 'Forward View and Decision Lab' for e in app.expander)
    assert any(b.label == 'Save research snapshot' for b in app.button)
    assert not list(tmp_path.rglob('*.csv'))


def test_exact_quarter_action_refreshes_only_financials_and_reuses_the_attempt(monkeypatch):
    from src import company_workbench_ui, sec_annual_history

    attempts = []

    def refresh(ticker, **kwargs):
        attempts.append((ticker, kwargs))
        return {'status': 'unavailable', 'ticker': ticker, 'safe_to_apply': False}

    def passive(ticker, state, *, refresh_requested, **kwargs):
        assert refresh_requested is False
        return {'status': 'not_requested', 'ticker': ticker}

    monkeypatch.setenv('SEC_USER_AGENT', 'Synthetic contact')
    monkeypatch.setattr(sec_annual_history, 'fetch_sec_online_research_view', refresh)
    monkeypatch.setattr(company_workbench_ui, 'get_online_company_prices', passive)
    monkeypatch.setattr(company_workbench_ui, 'get_online_peer_valuation', passive)
    monkeypatch.setattr(company_workbench_ui, 'get_price_filing_association',
                        lambda ticker, identity, prices, state, **kwargs: passive(ticker, state, **kwargs))
    app = AppTest.from_function(_app).run()
    app.button(key='company-refresh-exact-quarter').click().run()
    app.radio[0].set_value('notes').run()
    assert not app.exception
    assert attempts == [('FICT', dict(user_agent='Synthetic contact', exact_quarter_requested=True,
                                     expected_cik='0000001234'))]


def test_online_only_scenario_snapshot_and_unchanged_replay_need_no_prepared_files(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    from tests.test_self_service_financial_refresh import _fetcher
    from src import company_research_notes, online_research_tools_ui, sec_annual_history, online_company_prices, company_workbench_ui
    from src.online_research_context_store import list_research_contexts
    original = sec_annual_history.fetch_sec_online_research_view
    calls, fetch = _fetcher()
    monkeypatch.setattr(company_research_notes, 'PROJECT_ROOT', tmp_path)
    monkeypatch.setattr(online_research_tools_ui, 'PROJECT_ROOT', tmp_path)
    monkeypatch.setenv('SEC_USER_AGENT', 'Synthetic contact')
    monkeypatch.setattr(sec_annual_history, 'fetch_sec_online_research_view',
        lambda ticker, **kwargs: original(ticker, **kwargs, source_fetcher=fetch,
                                         observed_at=datetime.now(timezone.utc)))
    monkeypatch.setattr(online_company_prices, 'fetch_online_company_prices',
        lambda ticker, **kwargs: {'ticker': ticker, 'status': 'unavailable', 'reason': 'synthetic_price_gap'})
    peer_calls = []
    def peers(ticker, state, **kwargs):
        if kwargs['refresh_requested']:peer_calls.append(ticker)
        return {'ticker': ticker, 'status': 'unavailable', 'reason': 'synthetic_peer_gap'}
    monkeypatch.setattr(company_workbench_ui, 'get_online_peer_valuation', peers)
    app = AppTest.from_function(_app).run()
    app.button(key='company-refresh-all').click().run()
    assert not app.exception and len(calls) == 3 and peer_calls == ['FICT']
    app.radio[0].set_value('valuation').run()
    next(b for b in app.button if b.label == 'Calculate hypothetical enterprise value').click().run()
    assert not app.exception
    value = next(m.value for m in app.metric if m.label == 'Hypothetical enterprise value')
    next(i for i in app.number_input if i.label == 'FCFF margin assumption (%)').set_value(25.).run()
    next(b for b in app.button if b.label == 'Calculate hypothetical enterprise value').click().run()
    assert not app.exception
    assert next(m.value for m in app.metric if m.label == 'Hypothetical enterprise value') != value
    app.radio[0].set_value('notes').run()
    app.button(key='online-research-save').click().run()
    assert not app.exception
    saved = list_research_contexts(profile_key='synthetic', ticker='FICT', sec_cik='0000001234', project_root=tmp_path)
    assert len(saved) == 1 and saved[0]['historical']
    assert any('Current versus latest saved: unchanged' in c.value for c in app.caption)
    app.button(key='online-research-save').click().run()
    assert len(list_research_contexts(profile_key='synthetic', ticker='FICT', sec_cik='0000001234', project_root=tmp_path)) == 1
    assert len(calls) == 3 and peer_calls == ['FICT']
    assert not list(tmp_path.rglob('*.csv'))
