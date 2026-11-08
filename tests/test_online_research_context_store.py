"""Private snapshot behavior: replay and comparison never turn observations live."""
from copy import deepcopy
import json

import pytest


SCOPE = dict(profile_key='personal/demo', ticker='FICT', sec_cik='0000001234')


def context(**changes):
    result = dict(schema_version='online-company-research-v1', **SCOPE,
        status='inspection_only', observed_at='2026-11-07T12:00:00Z', source_revision='a' * 64,
        source_receipts={'financial': {'source_url': 'https://data.sec.gov/api/xbrl/companyfacts/CIK0000001234.json',
            'observed_at': '2026-11-07T12:00:00Z', 'payload_sha256': 'b' * 64}},
        filing_inventory={'latest': {'annual': {'accession': '0000001234-26-000001', 'period_end': '2026-06-30'}},
            'observed_at': '2026-11-07T12:00:00Z', 'payload_sha256': 'b' * 64},
        filing_coverage={'status': 'corroborated'},
        earnings_components={'net_income': {'value': 20, 'unit': 'USD'}},
        business_trend={'metrics': [{'key': 'revenue_yoy', 'value': 0.1}]},
        peer_read_through={'status': 'withheld', 'reason': 'minimum_three_required'},
        forward_view={'status': 'inspection_only'}, decision_lab={'status': 'research_work_remaining'},
        gaps=['No reviewed forecast.'], notes={'thesis': 'Check cash conversion.'},
        scenario={'growth_rate': 0.05, 'fcf_margin': 0.1, 'wacc': 0.1,
            'terminal_growth_rate': 0.02, 'projection_years': 5},
        saved_readiness_promoted=False, commercial_eligible=False)
    result.update(changes)
    return result


def save(value, root, **scope):
    from src.online_research_context_store import save_research_context
    return save_research_context(value, project_root=root, **(scope or SCOPE))


def snapshot_path(root, snapshot):
    return next(root.rglob(snapshot['snapshot_id'] + '.json'))


def test_save_replay_is_private_immutable_and_explicitly_historical(tmp_path):
    from src.online_research_context_store import load_research_context, list_research_contexts
    value = context()
    original = deepcopy(value)
    first = save(value, tmp_path)
    assert first['historical'] is True and first['current'] is False
    assert first['context'] == original and value == original
    assert first['context']['saved_readiness_promoted'] is False
    assert first['context']['commercial_eligible'] is False
    assert 'refresh' in first['replay_notice'].lower()
    assert len(first['snapshot_id']) == 64
    path = snapshot_path(tmp_path, first)
    assert path.is_relative_to(tmp_path / 'outputs/local/online-research-contexts')
    assert not (tmp_path / 'data').exists()
    assert load_research_context(first['snapshot_id'], project_root=tmp_path, **SCOPE) == first
    assert save(value, tmp_path) == first
    assert list_research_contexts(project_root=tmp_path, **SCOPE) == [first]
    value['business_trend']['metrics'][0]['value'] = 99
    assert load_research_context(first['snapshot_id'], project_root=tmp_path, **SCOPE)['context']['business_trend']['metrics'][0]['value'] == 0.1


def test_empty_reads_make_no_directories_and_unknown_snapshot_is_not_current(tmp_path):
    from src.online_research_context_store import list_research_contexts, list_research_context_scopes, load_research_context
    assert list_research_contexts(project_root=tmp_path, **SCOPE) == []
    assert list_research_context_scopes(SCOPE['profile_key'], project_root=tmp_path) == {'scopes': [], 'errors': []}
    with pytest.raises(ValueError):
        load_research_context('a' * 64, project_root=tmp_path, **SCOPE)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('scope', [dict(SCOPE, profile_key='other'), dict(SCOPE, ticker='OTHER'),
    dict(SCOPE, sec_cik='0000005678')])
def test_context_and_replay_require_exact_profile_ticker_cik(tmp_path, scope):
    from src.online_research_context_store import load_research_context
    first = save(context(), tmp_path)
    with pytest.raises(ValueError, match='scope'):
        save(context(), tmp_path, **scope)
    with pytest.raises(ValueError):
        load_research_context(first['snapshot_id'], project_root=tmp_path, **scope)


@pytest.mark.parametrize('scope', [dict(SCOPE, profile_key=''), dict(SCOPE, ticker='../FICT'),
    dict(SCOPE, sec_cik='1234'), dict(SCOPE, sec_cik='0000000000'),
    dict(SCOPE, sec_cik='１２３４５６７８９０')])
def test_invalid_scope_rejected_before_any_write(tmp_path, scope):
    with pytest.raises(ValueError):
        save(context(), tmp_path, **scope)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('changes', [dict(schema_version='unrecognized'), dict(observed_at='yesterday'),
    dict(source_revision=''), dict(saved_readiness_promoted=True), dict(commercial_eligible=True),
    dict(saved_readiness_promoted=0), dict(gaps=[float('nan')]), dict(gaps=[float('inf')])])
def test_invalid_context_or_promoted_rights_are_not_persisted(tmp_path, changes):
    with pytest.raises(ValueError):
        save(context(**changes), tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('field', ['raw_body', 'body', 'raw_payload', 'raw_response', 'base64', 'archive', 'archive_body'])
def test_raw_transport_and_archive_fields_are_rejected_even_when_nested(tmp_path, field):
    value = context()
    value['source_receipts']['financial'][field] = 'not a normalized observation'
    with pytest.raises(ValueError, match='normalized'):
        save(value, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_oversized_and_deep_contexts_rejected_before_serialization_or_write(tmp_path):
    from src.online_research_context_store import MAX_SNAPSHOT_BYTES
    with pytest.raises(ValueError, match='limit|large'):
        save(context(notes={'text': 'x' * (MAX_SNAPSHOT_BYTES + 1)}), tmp_path)
    value = context()
    cursor = value['notes']
    for _ in range(80):
        cursor['nested'] = {}
        cursor = cursor['nested']
    with pytest.raises(ValueError, match='depth|limit'):
        save(value, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_changed_values_create_new_snapshot_and_comparison_separates_user_edits(tmp_path):
    from src.online_research_context_store import compare_research_contexts, list_research_contexts
    first = save(context(), tmp_path)
    changed = context(source_revision='c' * 64)
    changed['business_trend']['metrics'][0]['value'] = 0.2
    second = save(changed, tmp_path)
    assert first['snapshot_id'] != second['snapshot_id']
    result = compare_research_contexts(first, second)
    assert result['status'] == 'changed'
    assert result['source_changed'] and result['financial_changed']
    assert not result['filing_changed'] and not result['assumptions_changed'] and not result['notes_changed']
    assert {row['snapshot_id'] for row in list_research_contexts(project_root=tmp_path, **SCOPE)} == {first['snapshot_id'], second['snapshot_id']}
    edited = deepcopy(changed)
    edited['scenario']['fcf_margin'] = 0.2
    edited['notes']['thesis'] = 'Review cash conversion next quarter.'
    result = compare_research_contexts(changed, edited)
    assert result['status'] == 'user_inputs_changed'
    assert result['assumptions_changed'] and result['notes_changed']
    assert not result['source_changed'] and not result['source_metadata_changed']


def test_source_metadata_only_changes_do_not_become_financial_or_filing_revisions(tmp_path):
    from src.online_research_context_store import compare_research_contexts
    left = context()
    right = deepcopy(left)
    right['observed_at'] = '2026-11-08T12:00:00Z'
    right['source_receipts']['financial'].update(observed_at=right['observed_at'], payload_sha256='c' * 64)
    right['filing_inventory'].update(observed_at=right['observed_at'], payload_sha256='c' * 64)
    result = compare_research_contexts(save(left, tmp_path), save(right, tmp_path))
    assert result['status'] == 'source_metadata_only'
    assert result['source_metadata_changed']
    assert not result['source_changed'] and not result['financial_changed'] and not result['filing_changed']
    assert compare_research_contexts(left, left)['status'] == 'unchanged'


def test_filing_and_peer_revisions_and_baseline_are_explicit():
    from src.online_research_context_store import compare_research_contexts
    left = context()
    right = deepcopy(left)
    right['source_revision'] = 'd' * 64
    right['filing_inventory']['latest']['annual']['accession'] = '0000001234-26-000002'
    right['peer_read_through']['status'] = 'eligible_observed_references'
    result = compare_research_contexts(left, right)
    assert result['filing_changed'] and result['source_changed']
    assert {'filing_inventory', 'peer_read_through'} <= set(result['changed_sections'])
    assert compare_research_contexts(None, left)['status'] == 'baseline_missing'
    with pytest.raises(ValueError, match='scope'):
        compare_research_contexts(left, context(sec_cik='0000005678'))


def test_tampered_content_saved_at_or_filename_and_duplicate_json_are_rejected(tmp_path):
    from src.online_research_context_store import load_research_context, list_research_contexts
    first = save(context(), tmp_path)
    path = snapshot_path(tmp_path, first)
    original = path.read_bytes()
    changed = json.loads(original)
    changed['context']['business_trend']['metrics'][0]['value'] = 10
    path.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match='digest|checksum'):
        load_research_context(first['snapshot_id'], project_root=tmp_path, **SCOPE)
    with pytest.raises(ValueError):
        save(context(), tmp_path)
    changed = json.loads(original)
    changed['saved_at'] = '2026-10-01T12:00:00Z'
    path.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match='digest|checksum'):
        load_research_context(first['snapshot_id'], project_root=tmp_path, **SCOPE)
    path.write_bytes(original[:-2] + b',"ticker":"OTHER"}\n')
    with pytest.raises(ValueError, match='duplicate'):
        load_research_context(first['snapshot_id'], project_root=tmp_path, **SCOPE)
    path.write_bytes(original)
    path.rename(path.with_name('f' * 64 + '.json'))
    with pytest.raises(ValueError, match='identity|digest'):
        list_research_contexts(project_root=tmp_path, **SCOPE)


def test_snapshot_identifier_cannot_escape_scope_or_accept_path_components(tmp_path):
    from src.online_research_context_store import load_research_context
    for snapshot_id in ('../private', '/tmp/private.json', 'x' * 64, 'A' * 64):
        with pytest.raises(ValueError):
            load_research_context(snapshot_id, project_root=tmp_path, **SCOPE)
    assert list(tmp_path.iterdir()) == []


def test_symlinked_snapshot_or_store_is_rejected_and_external_file_untouched(tmp_path):
    from src.online_research_context_store import load_research_context, list_research_contexts
    first = save(context(), tmp_path)
    path = snapshot_path(tmp_path, first)
    raw = path.read_bytes()
    outside = tmp_path / 'outside.json'
    outside.write_bytes(raw)
    path.unlink()
    path.symlink_to(outside)
    with pytest.raises(ValueError, match='symlink'):
        load_research_context(first['snapshot_id'], project_root=tmp_path, **SCOPE)
    with pytest.raises(ValueError, match='symlink'):
        list_research_contexts(project_root=tmp_path, **SCOPE)
    assert outside.read_bytes() == raw
    path.unlink()
    directory = tmp_path / 'outputs/local/online-research-contexts'
    original_directory = directory.with_name('moved-store')
    directory.rename(original_directory)
    directory.symlink_to(original_directory, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        save(context(), tmp_path)


def test_bounded_read_does_not_trust_an_oversized_file(tmp_path):
    from src.online_research_context_store import load_research_context, MAX_SNAPSHOT_BYTES
    first = save(context(), tmp_path)
    path = snapshot_path(tmp_path, first)
    path.write_bytes(b' ' * (MAX_SNAPSHOT_BYTES + 1))
    with pytest.raises(ValueError, match='limit|size|large'):
        load_research_context(first['snapshot_id'], project_root=tmp_path, **SCOPE)


def test_monitor_lists_exact_scopes_and_keeps_valid_company_when_another_is_tampered(tmp_path):
    from src.online_research_context_store import list_research_context_scopes
    first = save(context(), tmp_path)
    other_scope = dict(SCOPE, ticker='OTHER', sec_cik='0000005678')
    second = save(context(**other_scope), tmp_path, **other_scope)
    snapshot_path(tmp_path, second).write_text('{}')
    result = list_research_context_scopes(SCOPE['profile_key'], project_root=tmp_path)
    assert len(result['scopes']) == 1 and result['errors']
    row = result['scopes'][0]
    assert (row['ticker'], row['sec_cik'], row['latest_snapshot_id'], row['snapshot_count']) == ('FICT', '0000001234', first['snapshot_id'], 1)
    assert list_research_context_scopes('other', project_root=tmp_path) == {'scopes': [], 'errors': []}


def test_history_and_monitor_limits_are_bounded_and_exact_lookup_stays_available(tmp_path, monkeypatch):
    from src import online_research_context_store as store
    monkeypatch.setattr(store, 'MAX_SNAPSHOTS_PER_SCOPE', 2)
    first = save(context(), tmp_path)
    save(context(notes={'thesis': 'second'}), tmp_path)
    with pytest.raises(ValueError, match='limit'):
        save(context(notes={'thesis': 'third'}), tmp_path)
    assert store.load_research_context(first['snapshot_id'], project_root=tmp_path, **SCOPE) == first
    for number in (5678, 9999):
        scope = dict(SCOPE, ticker=f'F{number}', sec_cik=str(number).zfill(10))
        save(context(**scope), tmp_path, **scope)
    result = store.list_research_context_scopes(SCOPE['profile_key'], project_root=tmp_path, limit=1)
    assert len(result['scopes']) == 1 and result['errors']


def test_default_project_root_can_be_scoped_without_changing_canonical_inputs(tmp_path, monkeypatch):
    from src import online_research_context_store as store
    monkeypatch.setattr(store, 'PROJECT_ROOT', tmp_path)
    first = store.save_research_context(context(), **SCOPE)
    assert store.load_research_context(first['snapshot_id'], **SCOPE) == first
    assert not (tmp_path / 'data').exists()


def test_actual_online_tools_context_scenario_and_notes_roundtrip_as_historical(tmp_path):
    from test_online_research_tools import financial, context as build_context, parameters, CIK
    from src.company_research_notes import CompanyNotes, CompanyNotesScope
    from src.research_thesis_journal import JOURNAL_COLUMNS, JOURNAL_SCHEMA_VERSION, JournalEntry
    from src.online_research_tools import run_online_scenario
    from src.online_research_context_store import load_research_context, compare_research_contexts
    view = financial()
    baseline = build_context(view)
    result = run_online_scenario(baseline, parameters())
    assert result['status'] == 'calculated'
    entry = JournalEntry(**{**dict.fromkeys(JOURNAL_COLUMNS, ''), 'schema_version': JOURNAL_SCHEMA_VERSION,
        'entry_id': 'one', 'profile_key': 'personal', 'ticker': 'FICT', 'thesis_id': 'thesis', 'entry_type': 'thesis',
        'recorded_at': '2026-10-29T12:00:00Z', 'effective_at': '2026-10-29T12:00:00Z',
        'reviewer': 'Owner', 'summary': 'Check cash conversion.', 'review_due_date': '2026-11-10'})
    notes = CompanyNotes(CompanyNotesScope('personal', 'FICT', CIK), (entry,), (), ())
    populated = build_context(view, scenario=result, notes=notes)
    own_scope = dict(profile_key='personal', ticker='FICT', sec_cik=CIK)
    snapshot = save(populated, tmp_path, **own_scope)
    reopened = load_research_context(snapshot['snapshot_id'], project_root=tmp_path, **own_scope)
    assert reopened['context'] == populated
    assert reopened['historical'] and not reopened['current']
    assert reopened['context']['notes']['journal'][0]['summary'] == 'Check cash conversion.'
    assert reopened['context']['scenario']['enterprise_value'] > 0
    comparison = compare_research_contexts(baseline, reopened)
    assert comparison['status'] == 'user_inputs_changed'
    assert comparison['notes_changed'] and comparison['assumptions_changed']
    assert not comparison['source_changed'] and not comparison['financial_changed'] and not comparison['filing_changed']


def test_actual_online_tools_metadata_revision_does_not_report_filing_change():
    from test_online_research_tools import context as build_context, financial
    from src.online_research_context_store import compare_research_contexts
    baseline = build_context()
    view = financial()
    view['companyfacts_identity']['payload_sha256'] = 'c' * 64
    view['quarterly_history']['payload_sha256'] = 'c' * 64
    refreshed = build_context(view)
    result = compare_research_contexts(baseline, refreshed)
    assert result['status'] == 'source_metadata_only'
    assert result['source_metadata_changed'] and not result['source_changed']
    assert not result['financial_changed'] and not result['filing_changed']


def test_metadata_signatures_never_become_filing_revisions():
    from src.online_research_context_store import compare_research_contexts
    baseline = context()
    baseline['filing_inventory'].update(inventory_sha256='b' * 64, normalized_sha256='c' * 64)
    refreshed = deepcopy(baseline)
    refreshed['filing_inventory'].update(inventory_sha256='d' * 64, normalized_sha256='e' * 64)
    result = compare_research_contexts(baseline, refreshed)
    assert result['status'] == 'source_metadata_only'
    assert result['source_metadata_changed'] and not result['filing_changed']


def test_replay_rejects_fifo_without_blocking(tmp_path):
    import os
    import subprocess
    import sys
    snapshot = save(context(), tmp_path)
    path = snapshot_path(tmp_path, snapshot)
    path.unlink()
    os.mkfifo(path)
    code = ("from src.online_research_context_store import load_research_context\n"
        "try:\n"
        f"    load_research_context({snapshot['snapshot_id']!r}, project_root={str(tmp_path)!r}, **{SCOPE!r})\n"
        "except ValueError:\n"
        "    pass\n"
        "else:\n"
        "    raise AssertionError('A FIFO was accepted as a saved snapshot')\n")
    subprocess.run([sys.executable, '-c', code], timeout=2, check=True, capture_output=True)


def test_changed_source_values_do_not_report_unchanged_user_assumptions_as_edits():
    from src.online_research_context_store import compare_research_contexts
    baseline = context(assumptions={'revenue_growth': 0.1, 'fcf_margin': 0.2, 'source_revenue': 100,
        'source_period_end': '2025-12-31'}, scenario={'status': 'calculated', 'enterprise_value': 1000})
    refreshed = deepcopy(baseline)
    refreshed['source_revision'] = 'c' * 64
    refreshed['assumptions'].update(source_revenue=110, source_period_end='2026-12-31')
    refreshed['scenario']['enterprise_value'] = 1100
    result = compare_research_contexts(baseline, refreshed)
    assert result['source_changed'] and not result['assumptions_changed']
