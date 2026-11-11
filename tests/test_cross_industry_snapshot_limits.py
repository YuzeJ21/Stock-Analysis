"""Private snapshots preserve full historical context within both size bounds."""
from base64 import b64decode, b64encode
from copy import deepcopy
from hashlib import sha256
import json
from random import Random
import zlib

import pytest

from src import online_research_context_store as store
from test_online_research_context_store import context, snapshot_path, SCOPE


def _historical_context(report_count):
    reports=[]
    for index in range(report_count):
        accession=f'0000001234-25-{index:06d}'
        reports.append(dict(accession=accession,form='6-K',period_end=None,report_date='2025-06-30',
            filed='2025-08-01',accepted_at='2025-08-01T12:00:00Z',primary_document=f'event-{index}.htm',
            source_url=f'https://www.sec.gov/Archives/edgar/data/1234/{accession.replace("-", "")}/event-{index}.htm',
            amendment=False))
    triggers=[dict(trigger_type='current_report_filing',anchor=report) for report in reports]
    value=context(scenario=None,notes=None,
        filing_inventory=dict(earnings_reports=reports,review_triggers=triggers),
        filing_coverage=dict(current={'annual':dict(status='facts_pending',reason='new_filing_structured_facts_pending'),
            'interim':dict(status='withheld',reason='newer_reporting_period_known')}),
        scenario_base=dict(status='withheld',reason='validated_current_annual_revenue_required',revenue=None),
        business_trend=dict(periods=[dict(kind='interim',period_start='2021-01-01',period_end='2021-06-30',
            status='available',current=False,currency='TWD',fields={'revenue':dict(value=100,unit='TWD')})],
            metrics=[]),forward_view=dict(review_triggers=triggers),
        gaps=['Latest annual facts are pending; the interim observation remains dated history.'])
    return value


def _compact_bytes(value):
    return json.dumps(value, ensure_ascii=True, separators=(',', ':'), sort_keys=True,
        allow_nan=False).encode('ascii')


def _digest(value):
    return sha256(_compact_bytes(value)).hexdigest()


def _assert_unchanged_historical_replay(value, before, reopened):
    assert reopened['context'] == before and value == before
    assert store.compare_research_contexts(value, reopened)['status'] == 'unchanged'
    assert reopened['historical'] is True and reopened['current'] is False
    assert reopened['context']['filing_coverage']['current']['annual']['status'] == 'facts_pending'
    assert reopened['context']['scenario_base']['status'] == 'withheld'
    assert reopened['context']['business_trend']['periods'][0]['current'] is False


def test_legitimate_dated_native_history_replays_exactly_with_current_model_holds(tmp_path):
    value=_historical_context(100); before=deepcopy(value)
    saved=store.save_research_context(value,**SCOPE,project_root=tmp_path)
    assert json.loads(snapshot_path(tmp_path, saved).read_bytes()) == saved
    reopened=store.load_research_context(saved['snapshot_id'],**SCOPE,project_root=tmp_path)
    _assert_unchanged_historical_replay(value, before, reopened)


def test_large_event_catalog_replays_exactly_with_original_snapshot_identity(tmp_path):
    from src.self_service_research_coverage import _replay_probe

    value = _historical_context(650)
    before = deepcopy(value)
    assert len(_compact_bytes(value)) > store.MAX_SNAPSHOT_BYTES
    saved = store.save_research_context(value, **SCOPE, project_root=tmp_path)
    path = snapshot_path(tmp_path, saved)
    original = path.read_bytes()
    assert len(original) <= store.MAX_SNAPSHOT_BYTES
    envelope = json.loads(original)
    assert set(envelope) == {'schema_version', 'expanded_bytes', 'payload_base64'}
    assert envelope['schema_version'] == 'online-research-snapshot-zlib-v1'
    assert store.MAX_SNAPSHOT_BYTES < envelope['expanded_bytes'] <= store.MAX_EXPANDED_SNAPSHOT_BYTES
    expanded = zlib.decompress(b64decode(envelope['payload_base64'], validate=True))
    assert len(expanded) == envelope['expanded_bytes']
    assert json.loads(expanded) == saved
    assert saved['schema_version'] == 'online-research-snapshot-v1'
    assert saved['snapshot_id'] == _digest(dict(schema_version=saved['schema_version'], **SCOPE, context=value))
    assert store.save_research_context(value, **SCOPE, project_root=tmp_path) == saved
    assert path.read_bytes() == original
    reopened = store.load_research_context(saved['snapshot_id'], **SCOPE, project_root=tmp_path)
    _assert_unchanged_historical_replay(value, before, reopened)
    assert store.list_research_contexts(**SCOPE, project_root=tmp_path) == [reopened]
    proof = _replay_probe(value, True)
    assert proof['status'] == 'available' and proof['exact_context_match'] is True
    assert proof['comparison_status'] == 'unchanged'
    assert proof['snapshot_id'] == saved['snapshot_id']
    assert proof['disposable_store'] is True and proof['user_store_written'] is False


def test_catalog_over_expanded_limit_is_held_without_truncation_or_write(tmp_path):
    value=_historical_context(1100); before=deepcopy(value)
    assert len(_compact_bytes(value)) > store.MAX_EXPANDED_SNAPSHOT_BYTES
    with pytest.raises(store.ResearchSnapshotSizeError,match='Research snapshot size limit exceeded') as failure:
        store.save_research_context(value,**SCOPE,project_root=tmp_path)
    assert failure.value.limit_kind == 'expanded'
    assert value==before
    assert list(tmp_path.iterdir())==[]


def test_catalog_within_expanded_limit_stays_held_if_encoding_exceeds_stored_limit(tmp_path):
    from src.self_service_research_coverage import _replay_probe

    sample = Random(471).randbytes(480_000).hex()
    value = context(notes={'first': sample[:480_000], 'second': sample[480_000:]})
    raw = _compact_bytes(value)
    assert len(raw) < store.MAX_EXPANDED_SNAPSHOT_BYTES
    assert len(b64encode(zlib.compress(raw))) > store.MAX_SNAPSHOT_BYTES
    with pytest.raises(store.ResearchSnapshotSizeError, match='Research snapshot size limit exceeded') as failure:
        store.save_research_context(value, **SCOPE, project_root=tmp_path)
    assert failure.value.limit_kind == 'stored'
    assert list(tmp_path.iterdir()) == []
    proof = _replay_probe(value, True)
    assert proof['status'] == 'held' and proof['reason'] == 'research_snapshot_size_limit'
    assert proof['limit_kind'] == 'stored' and proof['context_bytes'] == len(raw)
    assert proof['max_context_bytes'] == store.MAX_EXPANDED_SNAPSHOT_BYTES
    assert proof['max_stored_bytes'] == store.MAX_SNAPSHOT_BYTES
    assert proof['disposable_store'] is True and proof['user_store_written'] is False


@pytest.mark.parametrize('damage', ('extra_key', 'invalid_base64', 'length_bool', 'length_low',
    'length_high', 'expanded_over_limit', 'truncated', 'trailing_bytes', 'concatenated'))
def test_compressed_snapshot_rejects_damaged_storage(tmp_path, damage):
    saved = store.save_research_context(_historical_context(650), **SCOPE, project_root=tmp_path)
    path = snapshot_path(tmp_path, saved)
    envelope = json.loads(path.read_bytes())
    payload = b64decode(envelope['payload_base64'], validate=True)
    if damage == 'extra_key':
        envelope['encoding'] = 'zlib'
    elif damage == 'invalid_base64':
        envelope['payload_base64'] = '!' + envelope['payload_base64'][1:]
    elif damage == 'length_bool':
        envelope['expanded_bytes'] = True
    elif damage == 'length_low':
        envelope['expanded_bytes'] -= 1
    elif damage == 'length_high':
        envelope['expanded_bytes'] += 1
    elif damage == 'expanded_over_limit':
        payload = zlib.compress(b' ' * (store.MAX_EXPANDED_SNAPSHOT_BYTES + 1))
        envelope['payload_base64'] = b64encode(payload).decode('ascii')
        envelope['expanded_bytes'] = store.MAX_EXPANDED_SNAPSHOT_BYTES
    else:
        if damage == 'truncated':
            payload = payload[:-1]
        elif damage == 'trailing_bytes':
            payload += b'trailing bytes'
        elif damage == 'concatenated':
            payload += zlib.compress(b'{}')
        envelope['payload_base64'] = b64encode(payload).decode('ascii')
    path.write_bytes(_compact_bytes(envelope))
    with pytest.raises(ValueError):
        store.load_research_context(saved['snapshot_id'], **SCOPE, project_root=tmp_path)


def _replace_inner(path, snapshot):
    raw = _compact_bytes(snapshot) + b'\n'
    envelope = dict(schema_version='online-research-snapshot-zlib-v1', expanded_bytes=len(raw),
        payload_base64=b64encode(zlib.compress(raw)).decode('ascii'))
    path.write_bytes(_compact_bytes(envelope))


def test_compressed_snapshot_still_verifies_original_checksum(tmp_path):
    saved = store.save_research_context(_historical_context(650), **SCOPE, project_root=tmp_path)
    path = snapshot_path(tmp_path, saved)
    changed = dict(saved, saved_at='2026-10-01T12:00:00Z')
    _replace_inner(path, changed)
    with pytest.raises(ValueError, match='checksum'):
        store.load_research_context(saved['snapshot_id'], **SCOPE, project_root=tmp_path)


def test_compressed_snapshot_revalidates_normalized_context_after_decode(tmp_path):
    saved = store.save_research_context(_historical_context(650), **SCOPE, project_root=tmp_path)
    path = snapshot_path(tmp_path, saved)
    context_with_body = deepcopy(saved['context'])
    context_with_body['source_receipts']['financial']['raw_body'] = 'filing body'
    changed = dict(saved, context=context_with_body)
    changed['snapshot_id'] = _digest(dict(schema_version=changed['schema_version'], **SCOPE,
        context=context_with_body))
    del changed['snapshot_sha256']
    changed['snapshot_sha256'] = _digest(changed)
    _replace_inner(path.with_name(changed['snapshot_id'] + '.json'), changed)
    with pytest.raises(ValueError, match='normalized observations'):
        store.load_research_context(changed['snapshot_id'], **SCOPE, project_root=tmp_path)
