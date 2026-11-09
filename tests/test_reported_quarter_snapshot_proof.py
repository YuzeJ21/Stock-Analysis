"""Only typed, issuer-bound numeric literals may enter historical snapshots."""
from copy import deepcopy
from datetime import timedelta
import json

import pytest

from test_online_research_context_store import context, save, snapshot_path, SCOPE
from test_sec_online_quarter_evidence import _financial, _wrapper
from test_sec_inline_filing import OBSERVED


def _reported_context():
    from src.sec_online_quarter_evidence import validated_archive_quarter
    from src.sec_online_quarter_view import merge_archive_quarter
    from src.online_research_tools import _trend
    financial = _financial(); financial['archive_quarterly'] = _wrapper(financial)
    archive = validated_archive_quarter(financial, as_of=OBSERVED)
    trend = _trend([('quarterly', merge_archive_quarter([], archive), 'USD')], financial['filing_coverage'])
    return context(observed_at=OBSERVED.isoformat(), business_trend=trend)


def _field(value, name='revenue', cumulative=False):
    return value['business_trend']['periods'][0]['cumulative_fields' if cumulative else 'fields'][name]


def _resign(snapshot):
    from src.online_research_context_store import _digest, _identity
    snapshot['snapshot_id'] = _digest(_identity(snapshot['context']))
    snapshot['snapshot_sha256'] = _digest({k: v for k, v in snapshot.items() if k != 'snapshot_sha256'})


def test_exact_quarter_and_cumulative_literal_proof_roundtrip_without_dropping_metadata(tmp_path):
    from src.online_research_context_store import load_research_context
    value = _reported_context(); before = deepcopy(value)
    first = save(value, tmp_path)
    loaded = load_research_context(first['snapshot_id'], project_root=tmp_path, **SCOPE)
    assert loaded['context'] == before and value == before
    assert _field(loaded['context'])['reported_text'] == '1,234'
    assert _field(loaded['context'], 'cash_from_operations', cumulative=True)['value'] == 500000000
    assert loaded['historical'] is True and loaded['current'] is False
    assert loaded['context']['saved_readiness_promoted'] is False


@pytest.mark.parametrize('problem', ['value', 'text', 'html', 'oversize', 'marker', 'missing_marker',
    'missing_text', 'unit', 'taxonomy', 'namespace', 'concept', 'field_name', 'issuer', 'ticker',
    'accession', 'form', 'filed', 'start', 'end', 'source_cik', 'source_accession', 'source_fact',
    'source_document', 'rights', 'source_id', 'fact_id', 'context_id', 'unit_id', 'receipt_digest',
    'future_observation', 'accepted', 'extra_payload', 'fixed_zero_body'])
def test_invalid_or_rebound_reported_proof_is_rejected_before_save(tmp_path, problem):
    value = _reported_context(); field = _field(value)
    if problem == 'value': field['value'] += 1
    elif problem == 'text': field['reported_text'] = '9999'
    elif problem == 'html': field['reported_text'] = '<div>1,234</div>'
    elif problem == 'oversize': field['reported_text'] = '1' * 101
    elif problem == 'marker': field['reported_numeric_schema'] = 'new-unreviewed-v2'
    elif problem == 'missing_marker': field.pop('reported_numeric_schema')
    elif problem == 'missing_text': field.pop('reported_text')
    elif problem == 'unit': field['unit'] = 'EUR'
    elif problem == 'taxonomy': field['taxonomy'] = 'unreviewed'
    elif problem == 'namespace': field['namespace_uri'] = 'https://example.invalid/us-gaap/2026'
    elif problem == 'concept': field['concept'] = 'CustomRevenue'
    elif problem == 'field_name': field['field'] = 'operating_income'
    elif problem == 'issuer': field['sec_cik'] = '0000009999'
    elif problem == 'ticker': field['ticker'] = 'OTHER'
    elif problem == 'accession': field['accession'] = '0000004321-26-000002'
    elif problem == 'form': field['form'] = '10-Q/A'
    elif problem == 'filed': field['filed'] = '2026-08-02'
    elif problem == 'start': field['period_start'] = '2026-01-01'
    elif problem == 'end': field['period_end'] = '2026-09-30'
    elif problem == 'source_cik':
        field['source_url'] = field['source_url'].replace('/1234/', '/9999/'); field['source_ref'] = field['source_url'] + '#' + field['fact_id']
    elif problem == 'source_accession':
        field['source_url'] = field['source_url'].replace('000000432126000001', '000000432126000002'); field['source_ref'] = field['source_url'] + '#' + field['fact_id']
    elif problem == 'source_fact': field['source_ref'] = field['source_url'] + '#other'
    elif problem == 'source_document': field['primary_document'] = 'different.htm'
    elif problem == 'rights': field['rights_status'] = 'approved'
    elif problem == 'source_id': field['source_id'] = 'sec_companyfacts'
    elif problem == 'fact_id': field['fact_id'] = '../escape'
    elif problem == 'context_id': field['context_id'] = '<context>'
    elif problem == 'unit_id': field['unit_id'] = ['USD']
    elif problem == 'receipt_digest': field['payload_sha256'] = 'unverified'
    elif problem == 'future_observation': field['observed_at'] = (OBSERVED + timedelta(seconds=1)).isoformat()
    elif problem == 'accepted': field['accepted_at'] = (OBSERVED + timedelta(seconds=1)).isoformat()
    elif problem == 'extra_payload': field['unrecognized_source_text'] = 'untyped body'
    else:
        field.update(value=0, transformation='fixed-zero', reported_text='<html>not a numeric literal</html>')
    with pytest.raises(ValueError, match='reported|numeric|normalized'):
        save(value, tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('location', ['notes', 'metrics', 'nested', 'annual', 'field_alias', 'cumulative_quarter_start'])
def test_reported_numeric_tokens_require_the_exact_typed_quarter_field_path(tmp_path, location):
    value = _reported_context(); field = deepcopy(_field(value))
    if location == 'notes': value['notes']['proof'] = field
    elif location == 'metrics': value['business_trend']['metrics'].append(field)
    elif location == 'nested': _field(value)['nested'] = {'proof': field}
    elif location == 'annual': value['business_trend']['periods'][0]['kind'] = 'annual'
    elif location == 'field_alias': value['business_trend']['periods'][0]['fields']['made_up_revenue'] = field
    else: _field(value, 'cash_from_operations', cumulative=True)['period_start'] = value['business_trend']['periods'][0]['period_start']
    with pytest.raises(ValueError, match='reported|numeric|normalized'):
        save(value, tmp_path)


@pytest.mark.parametrize('problem', ['value', 'issuer', 'cumulative_start', 'renamed_body'])
def test_recomputed_snapshot_checksums_do_not_bypass_reported_proof_replay(tmp_path, problem):
    from src.online_research_context_store import load_research_context
    original = save(_reported_context(), tmp_path)
    path = snapshot_path(tmp_path, original); forged = json.loads(path.read_text())
    value = forged['context']
    if problem == 'value': _field(value)['value'] += 1
    elif problem == 'issuer': _field(value)['sec_cik'] = '0000009999'
    elif problem == 'cumulative_start': _field(value, 'capital_expenditures', cumulative=True)['period_start'] = '2025-01-01'
    else: _field(value)['reported_text'] = '<html>renamed source body</html>'
    _resign(forged); replacement = path.with_name(forged['snapshot_id'] + '.json'); path.unlink()
    replacement.write_text(json.dumps(forged))
    with pytest.raises(ValueError, match='reported|numeric|normalized'):
        load_research_context(forged['snapshot_id'], project_root=tmp_path, **SCOPE)


def test_historical_literals_need_no_current_freshness_or_source_requests(tmp_path, monkeypatch):
    from src.online_research_context_store import load_research_context
    from src import sec_exact_filing
    value = _reported_context(); value['observed_at'] = '2030-01-01T00:00:00Z'
    monkeypatch.setattr(sec_exact_filing, 'fetch_sec_filing_preview', lambda *a, **k: pytest.fail('snapshot requested a source'))
    first = save(value, tmp_path)
    loaded = load_research_context(first['snapshot_id'], project_root=tmp_path, **SCOPE)
    assert loaded['context'] == value and loaded['current'] is False


@pytest.mark.parametrize('literal', ['-', '\u2013', '\u2014', '0', '0.00'])
def test_fixed_zero_literal_is_bounded_and_rederived(tmp_path, literal):
    value = _reported_context(); field = _field(value)
    field.update(value=0, reported_text=literal, transformation='fixed-zero')
    first = save(value, tmp_path)
    assert _field(first['context'])['reported_text'] == literal
