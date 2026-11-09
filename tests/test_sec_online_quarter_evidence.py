"""The archive quarter remains a separate, exact-source personal lane."""
from copy import deepcopy
from datetime import timedelta
import hashlib
import json

import pytest

from test_sec_inline_filing import _extract, _xml, OBSERVED, SOURCE
from test_sec_exact_filing import _submission, MAP, SUB
from src.online_filing_context import build_filing_inventory, corroborate_online_financials

CIK = '0000001234'
FACTS = f'https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json'


def _profile_receipt():
    return dict(status='ready', payload=_submission(), source_url=SUB,
                observed_at='2026-10-30T21:00:00Z', source_last_modified=None,
                payload_sha256='c' * 64)


def _financial():
    identity = dict(status='source_matched', ticker='FICT', sec_cik=CIK,
        source_url=FACTS, observed_at='2026-10-30T21:00:00Z', source_last_modified=None,
        payload_sha256='d' * 64, association_source_url=MAP,
        association_payload_sha256='b' * 64, association_observed_at='2026-10-30T21:00:00Z')
    inventory = build_filing_inventory(_profile_receipt(), ticker='FICT', expected_cik=CIK, as_of=OBSERVED)
    result = dict(ticker='FICT', sec_cik=CIK, companyfacts_identity=identity,
                  quarterly_history={'status': 'withheld', 'periods': []}, filing_inventory=inventory)
    result['filing_coverage'] = corroborate_online_financials(result, inventory, as_of=OBSERVED)
    return result


def _wrapper(financial=None, packet=None):
    from src.sec_online_quarter_evidence import build_archive_quarter
    financial = _financial() if financial is None else financial
    return build_archive_quarter(financial, _extract() if packet is None else packet, as_of=OBSERVED)


def _seal(packet):
    packet['packet_digest'] = hashlib.sha256(json.dumps(
        {k: v for k, v in packet.items() if k != 'packet_digest'},
        sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def test_separate_exact_archive_quarter_retains_source_and_preserves_cumulative_gap():
    from src.sec_online_quarter_evidence import validated_archive_quarter
    financial = _financial(); before = deepcopy(financial)
    financial['archive_quarterly'] = _wrapper(financial)
    result = validated_archive_quarter(financial, as_of=OBSERVED)
    assert result is not None and result['status'] == 'inspection_only'
    assert financial['quarterly_history'] == before['quarterly_history']
    assert financial['archive_quarterly']['source_packet'] == _extract()
    quarter = next(r for r in result['periods'] if r['kind'] == 'quarterly')
    cumulative = next(r for r in result['periods'] if r['kind'] == 'cumulative')
    assert quarter['status'] == 'available' and quarter['fields']['revenue']['value'] == 1234000000
    assert 'cash_from_operations' not in quarter['fields']
    assert cumulative['fields']['cash_from_operations']['value'] == 500000000
    assert cumulative['period_start'] == '2026-01-01'
    assert result['source_id'] == 'sec_archive_inline'
    assert result['rights_status'] == 'unregistered_sec_archive_personal_inspection_only'
    assert result['commercial_eligible'] is False and result['saved_readiness_promoted'] is False
    assert quarter['accession'] == result['accession'] and quarter['source_url'] == SOURCE


def test_normalized_dto_keeps_numeric_proof_without_raw_body_fields():
    from src.sec_online_quarter_evidence import validated_archive_quarter
    financial = _financial(); financial['archive_quarterly'] = _wrapper(financial)
    result = validated_archive_quarter(financial, as_of=OBSERVED)
    literal = result['periods'][0]['fields']['revenue']
    assert literal['reported_numeric_schema'] == 'sec-reported-numeric-v1'
    assert literal['reported_text'] == '1,234'
    for key in ('value', 'scale', 'sign', 'decimals', 'transformation', 'context_id',
                'unit_id', 'fact_id', 'source_ref', 'namespace_uri'):
        assert literal[key] == _extract()['periods'][0]['fields']['revenue'][key]
    encoded = json.dumps(result)
    assert not any(key in encoded for key in ('"raw_text"', '"source_packet"', '"bank_scope"', 'base64'))
    assert financial['archive_quarterly']['source_packet']['periods'][0]['fields']['revenue']['raw_text'] == '1,234'


@pytest.mark.parametrize('problem', ['number', 'raw_text', 'profile_digest', 'map_digest',
    'accession', 'accepted', 'amendment', 'period', 'old_observation', 'future_observation',
    'identity', 'commercial', 'missing_profile', 'wrapper_digest'])
def test_resigned_or_stale_evidence_cannot_escape_source_or_numeric_gates(problem):
    from src.sec_online_quarter_evidence import validated_archive_quarter
    financial = _financial(); financial['archive_quarterly'] = _wrapper(financial)
    wrapper = financial['archive_quarterly']; packet = wrapper['source_packet']
    if problem == 'number': packet['periods'][0]['fields']['revenue']['value'] += 1
    elif problem == 'raw_text': packet['periods'][0]['fields']['revenue']['raw_text'] = '9,999'
    elif problem == 'profile_digest': packet['source_receipts'][1]['payload_sha256'] = 'e' * 64
    elif problem == 'map_digest': packet['source_receipts'][0]['payload_sha256'] = 'e' * 64
    elif problem == 'accession': packet['accession'] = '0000004321-26-000002'
    elif problem == 'accepted': packet['accepted_at'] = '2026-08-01T13:00:00Z'
    elif problem == 'amendment': packet['form'] = '10-Q/A'
    elif problem == 'period': packet['period_end'] = '2026-09-30'
    elif problem == 'identity': financial['companyfacts_identity']['sec_cik'] = '0000009999'
    elif problem == 'commercial': packet['commercial_eligible'] = True
    elif problem == 'missing_profile': packet['source_receipts'].pop(1)
    elif problem == 'wrapper_digest': wrapper['packet_digest'] = 'e' * 64
    _seal(packet)
    wrapper['source_packet_digest'] = packet['packet_digest']
    if problem != 'wrapper_digest': _seal(wrapper)
    now = OBSERVED + timedelta(hours=25) if problem == 'old_observation' else OBSERVED - timedelta(seconds=1) if problem == 'future_observation' else OBSERVED
    assert validated_archive_quarter(financial, as_of=now) is None


def test_latest_amendment_cannot_borrow_original_or_older_period():
    from src.sec_online_quarter_evidence import validated_archive_quarter
    financial = _financial(); financial['archive_quarterly'] = _wrapper(financial)
    profile = _profile_receipt(); recent = profile['payload']['filings']['recent']
    for values in recent.values(): values.append(values[0])
    recent['form'][1] = '10-Q/A'; recent['accessionNumber'][1] = '0000004321-26-000002'
    recent['filingDate'][1] = '2026-09-01'; recent['acceptanceDateTime'][1] = '2026-09-01T12:00:00Z'
    financial['filing_inventory'] = build_filing_inventory(profile, ticker='FICT', expected_cik=CIK, as_of=OBSERVED)
    assert validated_archive_quarter(financial, as_of=OBSERVED) is None


def test_conflicting_revenue_remains_withheld_even_when_operating_income_is_reported():
    from src.sec_online_quarter_evidence import validated_archive_quarter
    xml = _xml().replace('</body>', '<ix:nonFraction name="g:RegulatedAndUnregulatedOperatingRevenue" contextRef="cur" unitRef="money" scale="6" decimals="-6" format="ixt:num-dot-decimal" id="conflict">9,999</ix:nonFraction></body>')
    financial = _financial(); financial['archive_quarterly'] = _wrapper(financial, _extract(xml))
    result = validated_archive_quarter(financial, as_of=OBSERVED)
    quarter = result['periods'][0]
    assert quarter['status'] == 'withheld'
    assert 'revenue' not in quarter['fields'] and quarter['withheld_fields']['revenue'] == 'conflicting_direct_facts'
    assert quarter['fields']['operating_income']['value'] == -12300


def test_validation_is_read_only_and_performs_no_source_requests(monkeypatch):
    from src.sec_online_quarter_evidence import validated_archive_quarter
    from src import sec_exact_filing
    financial = _financial(); financial['archive_quarterly'] = _wrapper(financial)
    before = deepcopy(financial)
    monkeypatch.setattr(sec_exact_filing, 'fetch_sec_filing_preview', lambda *a, **k: pytest.fail('read requested a source'))
    assert validated_archive_quarter(financial, as_of=OBSERVED) is not None
    assert financial == before


def _transport():
    mapping = {'0': {'ticker': 'FICT', 'cik_str': 1234}}
    profile = _submission()
    sources = {MAP: mapping, SUB: profile, SOURCE: _xml()}
    calls = []
    def fetch(url, agent):
        calls.append(url)
        assert agent == 'Constructed research contact'
        value = sources[url]
        return (value.encode() if isinstance(value, str) else json.dumps(value).encode()), {}, url
    from src.online_sec_receipt import fetch_sec_json_receipt
    map_receipt = fetch_sec_json_receipt(MAP, user_agent='Constructed research contact', fetcher=fetch, observed_at=OBSERVED)
    profile_receipt = fetch_sec_json_receipt(SUB, user_agent='Constructed research contact', fetcher=fetch, observed_at=OBSERVED, retain_raw=True)
    financial = _financial()
    identity = financial['companyfacts_identity']
    identity['association_payload_sha256'] = map_receipt['payload_sha256']
    financial['filing_inventory'] = build_filing_inventory(profile_receipt, ticker='FICT', expected_cik=CIK, as_of=OBSERVED)
    financial['filing_coverage'] = corroborate_online_financials(financial, financial['filing_inventory'], as_of=OBSERVED)
    calls.clear()
    return financial, map_receipt, profile_receipt, fetch, calls


def test_acquisition_reuses_original_map_and_profile_and_fetches_only_exact_document():
    from src.sec_online_quarter_evidence import fetch_archive_quarter, validated_archive_quarter
    financial, mapping, profile, fetch, calls = _transport()
    financial['archive_quarterly'] = fetch_archive_quarter(financial,
        user_agent='Constructed research contact', ticker_map_receipt=mapping,
        submissions_receipt=profile, source_fetcher=fetch, observed_at=OBSERVED)
    assert financial['archive_quarterly']['status'] == 'inspection_only'
    assert calls == [SOURCE]
    assert validated_archive_quarter(financial, as_of=OBSERVED)['periods'][0]['status'] == 'available'


@pytest.mark.parametrize('problem', ['stale', 'wrong_cik', 'commercial', 'covered', 'missing_inventory', 'wrong_map', 'wrong_profile'])
def test_acquisition_with_no_current_gap_or_current_identity_performs_no_archive_request(problem, monkeypatch):
    from src.sec_online_quarter_evidence import fetch_archive_quarter
    financial, mapping, profile, fetch, calls = _transport()
    when = OBSERVED
    if problem == 'stale': when += timedelta(hours=25)
    elif problem == 'wrong_cik': financial['companyfacts_identity']['sec_cik'] = '0000009999'
    elif problem == 'commercial': monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE', '1')
    elif problem == 'missing_inventory': financial.pop('filing_inventory')
    elif problem == 'wrong_map': mapping['payload_sha256'] = 'e' * 64
    elif problem == 'wrong_profile': profile['payload_sha256'] = 'e' * 64
    else:
        # One validated structured quarter is enough to avoid refreshing other fields.
        from src.sec_quarterly_history import build_sec_quarterly_history
        payload = dict(cik=1234, facts={'us-gaap': {'Revenues': {'units': {'USD': [dict(
            start='2026-04-01', end='2026-06-30', filed='2026-08-01',
            accn='0000004321-26-000001', form='10-Q', val=1234000000)]}}}})
        financial['quarterly_history'] = build_sec_quarterly_history('FICT', payload,
            expected_cik=CIK, observed_at=financial['companyfacts_identity']['observed_at'],
            source_url=FACTS, payload_sha256=financial['companyfacts_identity']['payload_sha256'])
    result = fetch_archive_quarter(financial, user_agent='Constructed research contact',
        ticker_map_receipt=mapping, submissions_receipt=profile, source_fetcher=fetch, observed_at=when)
    assert result['status'] == 'withheld'
    assert calls == []


def test_loader_adds_only_latest_archive_document_to_existing_source_requests():
    from src.sec_annual_history import fetch_sec_online_research_view
    financial, mapping, profile, fetch, calls = _transport()
    facts = dict(cik=1234, facts={'us-gaap': {'Revenues': {'units': {'USD': [dict(
        start='2025-01-01', end='2025-12-31', filed='2026-02-01',
        accn='0000004321-26-000000', form='10-K', val=1000)]}}}})
    def loader_fetch(url, agent):
        if url == FACTS:
            calls.append(url)
            return json.dumps(facts).encode(), {}, url
        return fetch(url, agent)
    view = fetch_sec_online_research_view('FICT', user_agent='Constructed research contact',
        ticker_map_receipt=mapping, source_fetcher=loader_fetch, observed_at=OBSERVED)
    assert calls == [FACTS, SUB, SOURCE]
    assert view['archive_quarterly']['status'] == 'inspection_only'
    assert view['quarterly_history']['status'] == 'withheld'


def _bank_financial():
    from test_sec_inline_bank_context import bank_input
    from src.sec_exact_filing import select_sec_filing
    from src.sec_inline_filing import extract_inline_filing
    import base64
    financial = _financial(); profile = _profile_receipt()
    profile['payload']['sic'] = '6022'
    raw_profile = json.dumps(profile['payload']).encode()
    profile['payload_sha256'] = hashlib.sha256(raw_profile).hexdigest()
    profile['payload_raw_base64'] = base64.b64encode(raw_profile).decode()
    financial['filing_inventory'] = build_filing_inventory(profile, ticker='FICT', expected_cik=CIK, as_of=OBSERVED)
    selection = select_sec_filing('FICT', CIK, profile, period_kind='quarterly')
    selection['source_receipts'].insert(0, dict(source_url=MAP, observed_at='2026-10-30T21:00:00Z', payload_sha256='b' * 64))
    xml, _ = bank_input(); raw = xml.encode()
    packet = extract_inline_filing(raw, selection, dict(status='ready', source_url=SOURCE,
        observed_at='2026-10-30T21:00:00Z', payload_sha256=hashlib.sha256(raw).hexdigest()))
    financial['archive_quarterly'] = _wrapper(financial, packet)
    return financial


def test_bank_components_remain_partial_without_inventing_quarter_revenue():
    from src.sec_online_quarter_evidence import validated_archive_quarter
    financial = _bank_financial()
    assert 'bank_scope' in financial['archive_quarterly']['source_packet']
    result = validated_archive_quarter(financial, as_of=OBSERVED)
    quarter = result['periods'][0]
    assert quarter['status'] == 'withheld' and 'revenue' not in quarter['fields']
    assert quarter['fields']['net_interest_income']['value'] == 50000000
    assert quarter['fields']['noninterest_income']['value'] == 20000000
    assert result['source_id'] == 'sec_archive_inline_bank'
    assert 'bank_scope' not in json.dumps(result) and 'base64' not in json.dumps(result)


def test_bank_classification_raw_proof_is_rechecked_on_every_cached_read():
    from src.sec_online_quarter_evidence import validated_archive_quarter
    financial = _bank_financial()
    wrapper = financial['archive_quarterly']; packet = wrapper['source_packet']
    packet['bank_scope']['sic'] = '3571'
    _seal(packet); wrapper['source_packet_digest'] = packet['packet_digest']; _seal(wrapper)
    assert validated_archive_quarter(financial, as_of=OBSERVED) is None


@pytest.mark.parametrize('field', ['revenue', 'operating_income', 'cash_from_operations', 'capital_expenditures'])
def test_every_nonbank_numeric_proof_is_rechecked_after_cache_resigning(field):
    from src.sec_online_quarter_evidence import validated_archive_quarter
    financial = _financial(); financial['archive_quarterly'] = _wrapper(financial)
    wrapper = financial['archive_quarterly']; packet = wrapper['source_packet']
    value = next(row['fields'][field] for row in packet['periods'] if field in row['fields'])
    value['value'] += 1
    _seal(packet); wrapper['source_packet_digest'] = packet['packet_digest']; _seal(wrapper)
    assert validated_archive_quarter(financial, as_of=OBSERVED) is None


def test_unrecognized_field_payload_cannot_enter_a_snapshot_dto():
    from src.sec_online_quarter_evidence import validated_archive_quarter
    financial = _financial(); financial['archive_quarterly'] = _wrapper(financial)
    wrapper = financial['archive_quarterly']; packet = wrapper['source_packet']
    packet['periods'][0]['fields']['revenue']['raw_html'] = '<script>untrusted source body</script>'
    _seal(packet); wrapper['source_packet_digest'] = packet['packet_digest']; _seal(wrapper)
    assert validated_archive_quarter(financial, as_of=OBSERVED) is None
