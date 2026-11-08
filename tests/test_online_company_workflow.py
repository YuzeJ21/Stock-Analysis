from pathlib import Path

from streamlit.testing.v1 import AppTest


def _dashboard_app():
    import os
    from pathlib import Path
    import pytest
    from src import company_research_notes
    from tests.test_research_monitor_roundtrip_browser import run_browser_fixture
    root = Path(os.environ['ONLINE_WORKFLOW_FIXTURE_DIR'])
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(company_research_notes,'PROJECT_ROOT',root)
        run_browser_fixture(root)


def _app(tmp_path, monkeypatch):
    from src import company_research_notes, sec_research_review_ui
    # Widget callbacks run before the next script body; isolate the store for
    # their full lifetime, not only inside the script's patch context.
    monkeypatch.setattr(company_research_notes,'PROJECT_ROOT',tmp_path)
    monkeypatch.setattr(sec_research_review_ui,'PROJECT_ROOT',tmp_path)
    monkeypatch.setenv('ONLINE_WORKFLOW_FIXTURE_DIR',str(tmp_path))
    monkeypatch.setenv('STOCK_RESEARCH_DATA_PROFILE','demo')
    app = AppTest.from_function(_dashboard_app)
    app.query_params.update(mode='research',page='company-workbench',ticker='FICT',online='1',section='notes')
    return app.run(timeout=30)


def test_production_online_notes_route_has_authoring_and_sec_controls_without_company_csv(tmp_path,monkeypatch):
    app = _app(tmp_path,monkeypatch)
    assert not app.exception
    assert any(b.label == 'Validate and preview' for b in app.button)
    assert any(b.label == 'Save current SEC evidence' for b in app.button)
    assert not any('saved report unavailable' in str(m.value).lower() for m in app.markdown)
    assert not list(tmp_path.rglob('*.csv'))


def test_production_notes_only_route_reopens_without_local_company_or_sec_receipt(tmp_path,monkeypatch):
    from src.company_research_notes import CompanyNotesScope,notes_paths
    from src.research_thesis_journal import append_journal_entry
    from tests.test_company_research_notes import entry
    scope = CompanyNotesScope('demo','FICT','0000001234')
    append_journal_entry(notes_paths(scope,project_root=tmp_path).journal,entry())
    app = _app(tmp_path,monkeypatch)
    app.query_params.clear()
    app.query_params.update(mode='research',page='company-workbench',ticker='FICT',notes_cik=scope.sec_cik,section='notes')
    app.run(timeout=30)
    assert not app.exception
    assert any(b.label == 'Validate and preview' for b in app.button)
    assert 'Check the next reported cash-flow period.' in '\n'.join(str(m.value) for m in app.text)
    summary=next(field for field in app.text_area if field.label=='Summary')
    summary.set_value('Synthetic unsaved journal-only draft').run()
    app.radio[0].set_value('financials').run()
    app.radio[0].set_value('notes').run()
    assert next(field for field in app.text_area if field.label=='Summary').value=='Synthetic unsaved journal-only draft'
    assert not any('No registered saved company matches' in str(m.value) for m in app.markdown)


def test_unavailable_saved_note_identity_cannot_fall_back_to_another_scope(tmp_path,monkeypatch):
    app = _app(tmp_path,monkeypatch)
    app.query_params.clear()
    app.query_params.update(mode='research',page='company-workbench',ticker='FICT',notes_cik='0000009999',section='notes')
    app.run(timeout=30)
    assert not app.exception
    assert not any(b.label == 'Validate and preview' for b in app.button)


def test_snapshot_only_company_keeps_identity_through_sections_and_monitor(tmp_path,monkeypatch):
    from src import online_research_context_store,online_research_tools_ui
    from tests.test_online_research_context_store import context
    from src.online_research_context_store import save_research_context
    monkeypatch.setattr(online_research_context_store,'PROJECT_ROOT',tmp_path)
    monkeypatch.setattr(online_research_tools_ui,'PROJECT_ROOT',tmp_path)
    saved=save_research_context(context(profile_key='demo'),profile_key='demo',ticker='FICT',
        sec_cik='0000001234',project_root=tmp_path)
    app=_app(tmp_path,monkeypatch)
    app.query_params.clear()
    app.query_params.update(mode='research',page='company-workbench',ticker='FICT',section='notes',
        research_cik='0000001234',research_snapshot=saved['snapshot_id'])
    app.run(timeout=30)
    assert not app.exception
    app.radio[0].set_value('valuation').run()
    next(field for field in app.number_input if field.label=='Revenue growth assumption (%)').set_value(22.).run()
    assert not app.exception
    assert app.query_params['research_snapshot']==[saved['snapshot_id']]
    app.button(key='research-nav-monitor').click().run(timeout=30)
    app.button(key='monitor-return-to-workbench').click().run(timeout=30)
    assert not app.exception
    assert app.query_params['research_snapshot']==[saved['snapshot_id']]
    assert next(field for field in app.number_input if field.label=='Revenue growth assumption (%)').value==22.


def _legacy_journal_app():
    import os
    from pathlib import Path
    import streamlit as st
    from src import dashboard
    root=Path(os.environ['ONLINE_WORKFLOW_FIXTURE_DIR'])
    context=dashboard.build_profile_context(project_root=root)
    class EmptyProvider:
        def list_local_tickers(self):return []
    dashboard.render_company_workbench(EmptyProvider(),context,{'queue':[]},None)


def test_legacy_journal_only_issuer_remains_accessible_without_local_universe_or_prices(tmp_path,monkeypatch):
    from src import dashboard
    from src.research_thesis_journal import append_journal_entry
    from tests.test_company_research_notes import entry
    monkeypatch.setenv('ONLINE_WORKFLOW_FIXTURE_DIR',str(tmp_path))
    monkeypatch.setenv('STOCK_RESEARCH_DATA_PROFILE','demo')
    context=dashboard.build_profile_context(project_root=tmp_path)
    append_journal_entry(context.data_dir/'research_thesis_journal.csv',entry(profile=context.profile_key))
    app=AppTest.from_function(_legacy_journal_app)
    app.query_params.update(mode='research',page='company-workbench',ticker='FICT',section='notes')
    app.run(timeout=30)
    assert not app.exception
    assert any(b.label=='Validate and preview' for b in app.button)
    assert 'Check the next reported cash-flow period.' in '\n'.join(str(m.value) for m in app.text)
    next(field for field in app.text_area if field.label=='Summary').set_value('Synthetic unsaved journal-only draft').run()
    app.radio[0].set_value('financials').run()
    app.radio[0].set_value('notes').run()
    assert next(field for field in app.text_area if field.label=='Summary').value=='Synthetic unsaved journal-only draft'


def test_sec_only_entry_retains_inferred_issuer_draft_through_sections_and_monitor(tmp_path,monkeypatch):
    from src.sec_research_review import capture_review,save_review
    from tests.test_multi_company_sec_review import issuer_view
    save_review(capture_review(issuer_view('FICT','0000001234'),profile_key='demo',saved_at='2026-11-07T12:00:00Z'),tmp_path)
    app=_app(tmp_path,monkeypatch)
    app.query_params.clear()
    app.query_params.update(mode='research',page='company-workbench',ticker='FICT',section='notes')
    app.run(timeout=30)
    next(field for field in app.text_area if field.label=='Summary').set_value('Synthetic SEC-only draft').run()
    app.radio[0].set_value('financials').run()
    app.radio[0].set_value('notes').run()
    assert next(field for field in app.text_area if field.label=='Summary').value=='Synthetic SEC-only draft'
    assert app.query_params['notes_cik']==['0000001234']
    app.button(key='research-nav-monitor').click().run(timeout=30)
    assert app.query_params['return_notes_cik']==['0000001234']
    app.button(key='monitor-return-to-workbench').click().run(timeout=30)
    assert not app.exception
    assert next(field for field in app.text_area if field.label=='Summary').value=='Synthetic SEC-only draft'
