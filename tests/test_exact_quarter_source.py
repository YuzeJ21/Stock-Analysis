"""Exact filing metadata scale and original-byte bank classification proofs."""
import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import zlib

import pytest

from test_sec_exact_filing import MAP, SUB, URL, _submission
from test_sec_inline_filing import _xml
from src.online_sec_receipt import fetch_sec_json_receipt
from src.sec_exact_filing import fetch_sec_filing_preview, select_sec_filing, valid_bank_scope, validated_filing_preview

OBSERVED = datetime(2026, 10, 30, 21, tzinfo=timezone.utc)


def receipt(body, *, url=SUB, observed='2026-10-30T20:00:00Z', retain=True):
    raw = json.dumps(body, separators=(',', ':')).encode()
    result = dict(status='ready', payload=body, source_url=url, observed_at=observed,
                  payload_sha256=hashlib.sha256(raw).hexdigest())
    if retain:
        result['payload_raw_base64'] = base64.b64encode(raw).decode()
    return result


def many_rows(count=13000):
    body = _submission()
    rows = body['filings']['recent']
    for key, values in rows.items():
        values.extend([values[0]] * (count - 1))
    rows['form'][1:] = ['4'] * (count - 1)
    return body


def large_bank_receipt():
    body = many_rows()
    body['sic'] = '6022'
    body['original_profile_detail'] = 'A' * (2 * 1024 * 1024)
    return receipt(body)


def test_selects_financial_form_from_large_aligned_unfiltered_profile():
    result = select_sec_filing('FICT', '0000001234', receipt(many_rows()), period_kind='quarterly')
    assert result['status'] == 'selected'
    assert result['source_url'] == URL


@pytest.mark.parametrize('problem', ['raw_rows', 'financial_rows', 'alignment'])
def test_metadata_scale_limits_still_hold(problem):
    body = many_rows(100001 if problem == 'raw_rows' else 13000)
    if problem == 'financial_rows':
        body['filings']['recent']['form'][:2001] = ['10-Q'] * 2001
    if problem == 'alignment':
        body['filings']['recent']['isXBRL'].pop()
    result = select_sec_filing('FICT', '0000001234', receipt(body), period_kind='quarterly')
    assert result['status'] == 'withheld'
    assert result['reason'] == 'filing_metadata_schema_invalid'


@pytest.mark.parametrize('problem', ['document', 'inline', 'accession', 'report_date', 'accepted'])
def test_large_profile_does_not_fall_back_from_malformed_latest_amendment(problem):
    body = many_rows()
    rows = body['filings']['recent']
    rows['form'][1] = '10-Q/A'
    rows['filingDate'][1] = '2026-09-01'
    rows['acceptanceDateTime'][1] = '2026-09-01T12:00:00Z'
    rows['accessionNumber'][1] = '0000004321-26-000002'
    key, value = {'document': ('primaryDocument', '../escape.htm'), 'inline': ('isInlineXBRL', False),
                  'accession': ('accessionNumber', 'bad'), 'report_date': ('reportDate', 'bad'),
                  'accepted': ('acceptanceDateTime', 'bad')}[problem]
    rows[key][1] = value
    assert select_sec_filing('FICT', '0000001234', receipt(body), period_kind='quarterly')['status'] == 'withheld'


def test_opted_in_raw_retention_preserves_large_original_bytes_and_digest():
    raw = json.dumps({'cik': 1234, 'padding': 'a' * (2 * 1024 * 1024)}).encode()
    fetch = lambda url, agent: (raw, {}, url)
    default = fetch_sec_json_receipt(SUB, user_agent='Synthetic', fetcher=fetch, retain_raw=True)
    result = fetch_sec_json_receipt(SUB, user_agent='Synthetic', fetcher=fetch, retain_raw=True,
                                   max_retained_raw_bytes=4 * 1024 * 1024)
    assert default['status'] == 'ready' and 'payload_raw_base64' not in default
    assert base64.b64decode(result['payload_raw_base64'], validate=True) == raw
    assert result['payload_sha256'] == hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize('limit', [True, 0, -1, 4 * 1024 * 1024 + 1, 16 * 1024 * 1024, 1.5, '4000000'])
def test_invalid_retention_limit_fails_before_request(limit):
    result = fetch_sec_json_receipt(SUB, user_agent='Synthetic', retain_raw=True,
        max_retained_raw_bytes=limit, fetcher=lambda *_: pytest.fail('invalid retention requested source'))
    assert result['status'] == 'unavailable' and result['reason'] == 'invalid_retention_request'


def test_bank_scope_compresses_larger_original_profile_losslessly_and_keeps_receipt():
    original = large_bank_receipt()
    result = select_sec_filing('FICT', '0000001234', original, period_kind='quarterly')
    assert result['status'] == 'selected'
    scope = result['bank_scope']
    assert scope['schema_version'] == 'sec-bank-scope-v2'
    original_bytes = base64.b64decode(original['payload_raw_base64'], validate=True)
    restored = zlib.decompress(base64.b64decode(scope['submissions_zlib_base64'], validate=True))
    assert restored == original_bytes
    assert scope['submissions_raw_bytes'] == len(original_bytes)
    assert len(json.dumps(scope)) < 256000
    assert scope['source_receipt']['payload_sha256'] == hashlib.sha256(original_bytes).hexdigest()
    assert valid_bank_scope(scope, '0000001234', result['source_receipts'])


@pytest.mark.parametrize('problem', ['trailing', 'concatenated', 'corrupt', 'bomb', 'size', 'hash', 'cik', 'sic', 'extra'])
def test_compressed_bank_scope_rejects_nonexact_or_unbounded_proof(problem):
    original = large_bank_receipt()
    result = select_sec_filing('FICT', '0000001234', original, period_kind='quarterly')
    assert result['status'] == 'selected'
    scope = deepcopy(result['bank_scope'])
    packed = base64.b64decode(scope['submissions_zlib_base64'], validate=True)
    if problem == 'trailing': packed += b'unobserved'
    elif problem == 'concatenated': packed += zlib.compress(b'{}')
    elif problem == 'corrupt': packed = packed[:len(packed)//2] + b'bad'
    elif problem == 'bomb': packed = zlib.compress(b'x' * (4 * 1024 * 1024 + 1))
    elif problem == 'size': scope['submissions_raw_bytes'] += 1
    elif problem == 'hash': scope['source_receipt']['payload_sha256'] = 'f' * 64
    elif problem == 'cik': scope['sec_cik'] = '0000009999'
    elif problem == 'sic': scope['sic'] = '3571'
    else: scope['unexpected'] = True
    scope['submissions_zlib_base64'] = base64.b64encode(packed).decode()
    assert not valid_bank_scope(scope, '0000001234', result['source_receipts'])


def supplied_receipts():
    return (receipt({'0': {'ticker': 'FICT', 'cik_str': 1234}}, url=MAP,
                    observed='2026-10-30T19:00:00Z', retain=False), receipt(_submission()))


def test_preview_reuses_supplied_original_receipts_without_json_requests():
    mapping, submissions = supplied_receipts()
    calls = []
    def fetch(url, agent):
        calls.append(url)
        assert url == URL
        return _xml().encode(), {}, url
    result = fetch_sec_filing_preview('FICT', period_kind='quarterly', user_agent='Synthetic',
        fetcher=fetch, observed_at=OBSERVED, ticker_map_receipt=mapping, submissions_receipt=submissions)
    assert result['status'] == 'inspection_only' and calls == [URL]
    assert result['source_receipts'][:2] == [{k: r[k] for k in ('source_url', 'observed_at', 'payload_sha256')}
                                          for r in (mapping, submissions)]
    assert validated_filing_preview(result, 'FICT', 'quarterly') == result


@pytest.mark.parametrize('problem', ['map_url', 'map_time', 'map_hash', 'map_status', 'submissions_url', 'cik', 'receipt_order'])
def test_bad_supplied_receipts_are_held_without_fetch_fallback(problem):
    mapping, submissions = supplied_receipts()
    if problem == 'map_url': mapping['source_url'] = 'https://example.invalid/map'
    elif problem == 'map_time': mapping['observed_at'] = 'bad'
    elif problem == 'map_hash': mapping['payload_sha256'] = 'bad'
    elif problem == 'map_status': mapping['status'] = 'unavailable'
    elif problem == 'submissions_url': submissions['source_url'] = 'https://data.sec.gov/submissions/CIK0000009999.json'
    elif problem == 'cik': submissions['payload']['cik'] = 9999
    else: mapping['observed_at'] = '2026-10-30T20:30:00Z'
    result = fetch_sec_filing_preview('FICT', period_kind='quarterly', user_agent='Synthetic', observed_at=OBSERVED,
        ticker_map_receipt=mapping, submissions_receipt=submissions,
        fetcher=lambda *_: pytest.fail('invalid supplied receipts requested another source'))
    assert result['status'] == 'withheld'


@pytest.mark.parametrize('missing', ['source_receipt', 'submissions_zlib_base64', 'submissions_raw_bytes', 'schema_version'])
def test_incomplete_compressed_scope_is_held_without_throwing(missing):
    original = large_bank_receipt()
    result = select_sec_filing('FICT', '0000001234', original, period_kind='quarterly')
    scope = deepcopy(result['bank_scope'])
    scope.pop(missing)
    assert not valid_bank_scope(scope, '0000001234', result['source_receipts'])
