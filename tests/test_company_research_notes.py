from dataclasses import replace
from pathlib import Path

import pytest

from src.research_thesis_journal import JournalEntry, append_journal_entry


def entry(profile='demo', ticker='FICT'):
    return JournalEntry('research-thesis-journal-v1', 'entry-one', profile, ticker,
        'thesis-one', 'thesis', '2026-11-07T12:00:00Z', '2026-11-07T11:00:00Z',
        'Synthetic browser', 'Check the next reported cash-flow period.', '', '', '', '',
        '0.50', '2026-12-01', '')


def test_note_paths_and_empty_reads_do_not_prepare_any_files(tmp_path):
    from src.company_research_notes import CompanyNotesScope, notes_paths, load_company_notes, notes_index
    scope = CompanyNotesScope('demo', 'FICT', '0000001234')
    paths = notes_paths(scope, project_root=tmp_path)
    assert paths.journal.name == 'research_thesis_journal.csv'
    assert paths.journal.parent.parts[-2:] == ('0000001234', 'FICT')
    assert load_company_notes(scope, project_root=tmp_path).record_count == 0
    assert notes_index('demo', project_root=tmp_path).scopes == ()
    assert list(tmp_path.iterdir()) == []


def test_existing_append_engine_saves_and_reopens_without_company_inputs(tmp_path):
    from src.company_research_notes import CompanyNotesScope, notes_paths, load_company_notes, saved_notes_scope
    scope = CompanyNotesScope('demo', 'FICT', '0000001234')
    append_journal_entry(notes_paths(scope, project_root=tmp_path).journal, entry())
    loaded = load_company_notes(scope, project_root=tmp_path)
    assert loaded.record_count == 1 and loaded.journal == (entry(),)
    assert saved_notes_scope('FICT', 'demo', sec_cik='0000001234', project_root=tmp_path) == scope
    assert not (tmp_path / 'data').exists()


def test_same_ticker_other_issuer_or_profile_cannot_reuse_notes(tmp_path):
    from src.company_research_notes import CompanyNotesScope, notes_paths, load_company_notes, saved_notes_scope
    scope = CompanyNotesScope('demo', 'FICT', '0000001234')
    append_journal_entry(notes_paths(scope, project_root=tmp_path).journal, entry())
    assert load_company_notes(replace(scope, sec_cik='0000005678'), project_root=tmp_path).record_count == 0
    assert saved_notes_scope('FICT', 'other', project_root=tmp_path) is None
    assert saved_notes_scope('FICT', 'demo', sec_cik='0000005678', project_root=tmp_path) is None
    other = replace(scope, sec_cik='0000005678')
    append_journal_entry(notes_paths(other, project_root=tmp_path).journal, entry())
    assert saved_notes_scope('FICT', 'demo', project_root=tmp_path) is None
    assert saved_notes_scope('FICT', 'demo', sec_cik=scope.sec_cik, project_root=tmp_path) == scope


@pytest.mark.parametrize('profile,ticker,cik', [('', 'FICT','0000001234'), ('demo','../FICT','0000001234'),
    ('demo','FICT','0000000000'), ('demo','FICT','1234'), ('demo','FICT','../../file'),
    ('demo','FICT','１２３４５６７８９０')])
def test_invalid_note_scope_is_rejected_without_writes(tmp_path, profile, ticker, cik):
    from src.company_research_notes import CompanyNotesScope, notes_paths
    with pytest.raises(ValueError):
        notes_paths(CompanyNotesScope(profile, ticker, cik), project_root=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_corrupt_or_cross_scope_records_are_excluded_with_a_gap(tmp_path):
    from src.company_research_notes import CompanyNotesScope, notes_paths, notes_index, load_company_notes
    good = CompanyNotesScope('demo','FICT','0000001234')
    bad = CompanyNotesScope('demo','OTHER','0000005678')
    append_journal_entry(notes_paths(good, project_root=tmp_path).journal, entry())
    append_journal_entry(notes_paths(bad, project_root=tmp_path).journal, entry())
    with pytest.raises(ValueError, match='scope'):
        load_company_notes(bad, project_root=tmp_path)
    index = notes_index('demo', project_root=tmp_path)
    assert index.scopes == (good,) and len(index.errors) == 1


def test_symlinked_note_store_and_oversize_files_fail_closed(tmp_path):
    from src.company_research_notes import CompanyNotesScope, notes_paths, load_company_notes, MAX_NOTE_BYTES
    scope = CompanyNotesScope('demo','FICT','0000001234')
    paths = notes_paths(scope, project_root=tmp_path)
    paths.journal.parent.mkdir(parents=True)
    outside = tmp_path / 'outside.csv'
    outside.write_text('private unrelated input')
    paths.journal.symlink_to(outside)
    with pytest.raises(ValueError, match='symlink'):
        load_company_notes(scope, project_root=tmp_path)
    paths.journal.unlink()
    paths.journal.write_bytes(b'x' * (MAX_NOTE_BYTES + 1))
    with pytest.raises(ValueError, match='limit'):
        load_company_notes(scope, project_root=tmp_path)
    assert outside.read_text() == 'private unrelated input'


def test_saved_note_link_is_an_explicit_offline_scope_not_live_listing_claim(tmp_path):
    from src.company_research_notes import CompanyNotesScope, notes_query
    query = notes_query(CompanyNotesScope('demo','FICT','0000001234'))
    assert query == {'mode':'research', 'page':'company-workbench', 'ticker':'FICT',
                     'section':'notes', 'notes_cik':'0000001234'}
    assert 'online' not in query and 'sec_pair' not in query


def test_notes_only_monitor_return_preserves_exact_saved_issuer_and_loaded_state(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from src import company_research_notes, research_workspace
    from src.company_research_notes import CompanyNotesScope, notes_paths, notes_query
    monkeypatch.setattr(company_research_notes, 'PROJECT_ROOT', tmp_path)
    scope = CompanyNotesScope('demo','FICT','0000001234')
    append_journal_entry(notes_paths(scope).journal, entry())
    class Query(dict):
        def from_dict(self, values):
            self.clear(); self.update(values)
    query = Query(notes_query(scope))
    key = 'company-section:demo:FICT:notes:0000001234'
    state = {key:'notes', 'online-observations':{'retained':True}}
    app = SimpleNamespace(query_params=query, session_state=state)
    research_workspace.open_research_monitor(app,'FICT','demo')
    assert query.get('return_notes_cik') == scope.sec_cik
    origin = research_workspace.research_monitor_origin(state,'demo','FICT')
    assert origin.notes_cik == scope.sec_cik and origin.online_cik is None
    assert research_workspace.research_monitor_origin(state,'different','FICT') is None
    query['return_notes_cik'] = '0000005678'
    research_workspace.return_to_research_workbench(app,origin)
    assert query['page'] == 'monitor'
    query['return_notes_cik'] = scope.sec_cik
    research_workspace.return_to_research_workbench(app,origin)
    assert query['notes_cik'] == scope.sec_cik and query['section'] == 'notes'
    assert 'online' not in query and state['online-observations'] == {'retained':True}


def test_deleted_saved_scope_cannot_regain_monitor_origin(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from src import company_research_notes, research_workspace
    from src.company_research_notes import CompanyNotesScope, notes_paths, notes_query
    monkeypatch.setattr(company_research_notes,'PROJECT_ROOT',tmp_path)
    scope = CompanyNotesScope('demo','FICT','0000001234')
    path = notes_paths(scope).journal
    append_journal_entry(path,entry())
    class Query(dict):
        def from_dict(self, values):
            self.clear(); self.update(values)
    app = SimpleNamespace(query_params=Query(notes_query(scope)),session_state={})
    research_workspace.open_research_monitor(app,'FICT','demo')
    path.unlink()
    assert research_workspace.research_monitor_origin(app.session_state,'demo','FICT') is None


def test_csv_parser_failure_is_a_scope_gap_not_a_route_crash(tmp_path):
    import csv
    from src.company_research_notes import CompanyNotesScope,notes_paths,notes_index,saved_notes_scope
    from src.catalyst_evidence_timeline import FIELDS
    scope=CompanyNotesScope('demo','FICT','0000001234')
    paths=notes_paths(scope,project_root=tmp_path)
    paths.catalysts.parent.mkdir(parents=True)
    with paths.catalysts.open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(FIELDS)
        writer.writerow(['x' * (csv.field_size_limit()+1)] + ['x']*(len(FIELDS)-1))
    assert notes_index('demo',project_root=tmp_path).errors
    assert saved_notes_scope('FICT','demo',sec_cik=scope.sec_cik,project_root=tmp_path) is None


def test_overflow_index_keeps_existing_exact_routes_available(tmp_path):
    from src.company_research_notes import CompanyNotesScope,notes_paths,notes_index,saved_notes_scope,MAX_NOTE_SCOPES
    for index in range(1,MAX_NOTE_SCOPES+2):
        scope=CompanyNotesScope('demo','FICT',str(index).zfill(10))
        append_journal_entry(notes_paths(scope,project_root=tmp_path).journal,entry())
    first=CompanyNotesScope('demo','FICT','0000000001')
    assert saved_notes_scope('FICT','demo',sec_cik=first.sec_cik,project_root=tmp_path) == first
    index=notes_index('demo',project_root=tmp_path)
    assert len(index.scopes)<=MAX_NOTE_SCOPES and index.errors


def test_legacy_note_lookup_needs_no_registered_ticker_and_keeps_profiles_separate(tmp_path):
    from src.company_research_notes import legacy_notes_available,legacy_note_tickers
    from src.research_record_authoring import AuthoringPaths
    paths=AuthoringPaths(tmp_path/'journal.csv',tmp_path/'catalysts.csv',tmp_path/'outcomes.csv')
    append_journal_entry(paths.journal,entry())
    assert legacy_notes_available('FICT','demo',paths)
    assert legacy_note_tickers(paths,'demo') == ('FICT',)
    assert not legacy_notes_available('FICT','other',paths)
    assert not legacy_notes_available('OTHER','demo',paths)


def test_pinned_pair_monitor_canonicalization_preserves_saved_note_issuer_return(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from src import company_research_notes,research_workspace
    from src.dashboard_navigation import canonical_workspace_query
    from src.sec_research_review import capture_review,save_review
    from tests.test_multi_company_sec_review import issuer_view
    monkeypatch.setattr(company_research_notes,'PROJECT_ROOT',tmp_path)
    pair=[capture_review(issuer_view('AMD','0000002488'),profile_key='demo',saved_at=f'2026-11-07T12:0{i}:00Z') for i in range(2)]
    for packet in pair:save_review(packet,tmp_path)
    class Query(dict):
        def from_dict(self,values):self.clear();self.update(values)
    query=Query(mode='research',page='company-workbench',ticker='AMD',section='notes',notes_cik='0000002488',sec_pair='.'.join(p['receipt_id'] for p in pair))
    app=SimpleNamespace(query_params=query,session_state={})
    research_workspace.open_research_monitor(app,'AMD','demo')
    query.from_dict(canonical_workspace_query('research','Monitor',query))
    assert query['return_notes_cik']=='0000002488'
    origin=research_workspace.research_monitor_origin(app.session_state,'demo','AMD')
    research_workspace.return_to_research_workbench(app,origin)
    assert query['page']=='company-workbench' and query['notes_cik']=='0000002488'
