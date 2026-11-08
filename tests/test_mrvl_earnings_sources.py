"""Constructed HTTP sources for the bounded, independent MRVL annual review."""

import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json

import pytest


NOW = datetime(2026, 11, 7, 12, tzinfo=timezone.utc)
MRVL_FACTS = 'https://data.sec.gov/api/xbrl/companyfacts/CIK0001835632.json'
MRVL_PROFILE = 'https://data.sec.gov/submissions/CIK0001835632.json'
AVGO_PROFILE = 'https://data.sec.gov/submissions/CIK0001730168.json'
MRVL_DOCUMENT = 'https://www.sec.gov/Archives/edgar/data/1835632/000183563226000011/mrvl-20260131.htm'
AVGO_DOCUMENT = 'https://www.sec.gov/Archives/edgar/data/1730168/000173016825000121/avgo-20251102.htm'
CONCEPTS = (
    'EarningsPerShareDiluted', 'NetIncomeLoss',
    'NetCashProvidedByUsedInOperatingActivities',
    'PaymentsToAcquirePropertyPlantAndEquipment', 'ShareBasedCompensation',
    'AmortizationOfIntangibleAssets', 'GainLossOnSaleOfBusiness',
)


def _facts_payload():
    fields = {}
    for name, value in zip(CONCEPTS + ('Revenues', 'OperatingIncomeLoss'), (2, 200, 300, 40, 30, 20, 90, 1000, 150)):
        unit = 'USD/shares' if name == 'EarningsPerShareDiluted' else 'USD'
        fields[name] = {'units': {unit: [{
            'start': '2025-02-02', 'end': '2026-01-31', 'val': value,
            'filed': '2026-03-11', 'form': '10-K',
            'accn': '0001835632-26-000011', 'fy': 2026, 'fp': 'FY',
        }]}}
    return {'cik': 1835632, 'entityName': 'Constructed Marvell', 'facts': {'us-gaap': fields}}


def _facts_receipt():
    payload = _facts_payload()
    raw = json.dumps(payload, indent=2).encode()
    return {'status': 'ready', 'source_url': MRVL_FACTS,
            'observed_at': '2026-11-07T12:00:00Z', 'source_last_modified': None,
            'payload_sha256': hashlib.sha256(raw).hexdigest(), 'payload': payload}


def _profile(ticker):
    mrvl = ticker == 'MRVL'
    return {'cik': '0001835632' if mrvl else '0001730168', 'tickers': [ticker],
            'name': 'Constructed ' + ticker, 'filings': {'recent': {
                'accessionNumber': ['0001835632-26-000011' if mrvl else '0001730168-25-000121'],
                'reportDate': ['2026-01-31' if mrvl else '2025-11-02'],
                'filingDate': ['2026-03-11' if mrvl else '2025-12-18'],
                'acceptanceDateTime': ['2026-03-11T12:00:00Z' if mrvl else '2025-12-18T12:00:00Z'],
                'form': ['10-K'], 'primaryDocument': ['mrvl-20260131.htm' if mrvl else 'avgo-20251102.htm'],
                'isInlineXBRL': [1], 'isXBRL': [1],
            }}}


def _document(ticker):
    mrvl = ticker == 'MRVL'
    cik, end = ('1835632', '2026-01-31') if mrvl else ('1730168', '2025-11-02')
    start = '2025-02-02' if mrvl else '2024-11-04'
    business = ('Companies that compete directly with our businesses include Broadcom.' if mrvl else
                'We have two reportable segments: semiconductor solutions and infrastructure software.')
    return ('<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" '
            'xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:dei="http://xbrl.sec.gov/dei/2025"><body>'
            f'<xbrli:context id="annual"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">{cik}</xbrli:identifier></xbrli:entity>'
            f'<xbrli:period><xbrli:startDate>{start}</xbrli:startDate><xbrli:endDate>{end}</xbrli:endDate></xbrli:period></xbrli:context>'
            f'<ix:nonNumeric name="dei:EntityCentralIndexKey" contextRef="annual">{cik}</ix:nonNumeric>'
            '<ix:nonNumeric name="dei:DocumentType" contextRef="annual">10-K</ix:nonNumeric>'
            f'<ix:nonNumeric name="dei:DocumentPeriodEndDate" contextRef="annual">{end}</ix:nonNumeric>'
            f'<p>{business}</p></body></html>').encode()


def _sources():
    return {MRVL_PROFILE: _profile('MRVL'), AVGO_PROFILE: _profile('AVGO'),
            MRVL_DOCUMENT: _document('MRVL'), AVGO_DOCUMENT: _document('AVGO')}


def _fetcher(sources, calls):
    def fetch(url, agent):
        calls.append(url)
        assert agent == 'Research contact@example.com'
        source = sources[url]
        if isinstance(source, Exception):
            raise source
        raw = json.dumps(source, indent=2).encode() if isinstance(source, dict) else source
        return raw, {}, url
    return fetch


def _collect(receipt=None, **kwargs):
    from src.mrvl_earnings_sources import fetch_mrvl_earnings_review
    return fetch_mrvl_earnings_review(
        _facts_receipt() if receipt is None else receipt,
        ticker='MRVL', expected_cik='0001835632',
        user_agent='Research contact@example.com', observed_at=NOW, **kwargs,
    )


def test_collection_uses_existing_facts_and_only_two_profiles_two_exact_documents(monkeypatch):
    monkeypatch.delenv('COMMERCIAL_RESEARCH_MODE', raising=False)
    calls = []
    receipt = _facts_receipt()
    before = deepcopy(receipt)
    packet = _collect(receipt, source_fetcher=_fetcher(_sources(), calls))
    assert calls == [MRVL_PROFILE, MRVL_DOCUMENT, AVGO_PROFILE, AVGO_DOCUMENT]
    assert packet['schema_version'] == 'mrvl-earnings-review-v1'
    assert packet['ticker'] == 'MRVL' and packet['sec_cik'] == '0001835632'
    assert packet['facts']['payload_sha256'] == receipt['payload_sha256']
    assert packet['facts']['normalized_sha256'] != receipt['payload_sha256']
    assert set(packet['facts']['payload']['facts']['us-gaap']) == set(CONCEPTS)
    assert set(packet['profiles']) == set(packet['documents']) == {'MRVL', 'AVGO'}
    for ticker, url in [('MRVL', MRVL_DOCUMENT), ('AVGO', AVGO_DOCUMENT)]:
        document = packet['documents'][ticker]
        raw = base64.b64decode(document['payload_raw_base64'], validate=True)
        assert raw == _document(ticker)
        assert document['payload_sha256'] == hashlib.sha256(raw).hexdigest()
        assert document['source_url'] == url
    assert len(packet['packet_digest']) == 64
    assert receipt == before
    from src.mrvl_earnings_review import build_mrvl_earnings_review
    review = build_mrvl_earnings_review(packet, expected_cik='0001835632', as_of=NOW)
    assert review['quality']['status'] == 'inspection_only'
    assert review['peer_context']['relationship_supported'] is True
    assert review['peer_context']['period_end_gap_days'] == 90


@pytest.mark.parametrize('age_seconds', [-1, 86401])
def test_future_or_more_than_one_day_old_facts_prevent_additional_sources(monkeypatch, age_seconds):
    monkeypatch.delenv('COMMERCIAL_RESEARCH_MODE', raising=False)
    receipt = _facts_receipt()
    receipt['observed_at'] = (NOW - timedelta(seconds=age_seconds)).strftime('%Y-%m-%dT%H:%M:%SZ')
    calls = []
    packet = _collect(receipt, source_fetcher=_fetcher(_sources(), calls))
    assert calls == []
    assert packet['reason'] == 'review_companyfacts_observation_unavailable'


def test_exactly_one_day_old_facts_keep_the_existing_freshness_boundary(monkeypatch):
    monkeypatch.delenv('COMMERCIAL_RESEARCH_MODE', raising=False)
    receipt = _facts_receipt()
    receipt['observed_at'] = '2026-11-06T12:00:00Z'
    calls = []
    packet = _collect(receipt, source_fetcher=_fetcher(_sources(), calls))
    assert len(calls) == 4
    assert packet['facts']['status'] == 'ready'


def test_unfixed_collection_observes_each_response_then_seals_at_batch_completion(monkeypatch):
    from src import mrvl_earnings_sources, online_sec_receipt

    monkeypatch.delenv('COMMERCIAL_RESEARCH_MODE', raising=False)
    clock = {'current': NOW}
    class SourceClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls.fromtimestamp(clock['current'].timestamp(), tz)
    monkeypatch.setattr(mrvl_earnings_sources, 'datetime', SourceClock)
    monkeypatch.setattr(online_sec_receipt, 'datetime', SourceClock)
    calls = []
    base = _fetcher(_sources(), calls)
    times = {MRVL_PROFILE: 1, MRVL_DOCUMENT: 2, AVGO_PROFILE: 3, AVGO_DOCUMENT: 4}
    def fetch(url, agent):
        result = base(url, agent)
        clock['current'] = NOW + timedelta(seconds=times[url])
        return result
    packet = mrvl_earnings_sources.fetch_mrvl_earnings_review(
        _facts_receipt(), ticker='MRVL', expected_cik='0001835632',
        user_agent='Research contact@example.com', source_fetcher=fetch,
    )
    assert calls == [MRVL_PROFILE, MRVL_DOCUMENT, AVGO_PROFILE, AVGO_DOCUMENT]
    assert packet['profiles']['MRVL']['observed_at'] == '2026-11-07T12:00:01Z'
    assert packet['documents']['MRVL']['observed_at'] == '2026-11-07T12:00:02Z'
    assert packet['profiles']['AVGO']['observed_at'] == '2026-11-07T12:00:03Z'
    assert packet['documents']['AVGO']['observed_at'] == packet['observed_at'] == '2026-11-07T12:00:04Z'


def test_explicit_observation_remains_deterministic_for_all_sources(monkeypatch):
    monkeypatch.delenv('COMMERCIAL_RESEARCH_MODE', raising=False)
    packet = _collect(source_fetcher=_fetcher(_sources(), []))
    stamps = [packet['observed_at']] + [packet[k][ticker]['observed_at']
        for k in ('profiles', 'documents') for ticker in ('MRVL', 'AVGO')]
    assert stamps == ['2026-11-07T12:00:00Z'] * 5


@pytest.mark.parametrize('change', ['ticker', 'expected_cik', 'body_cik', 'url', 'status', 'digest', 'observation', 'user_agent'])
def test_invalid_identity_or_transport_configuration_prevents_new_requests(monkeypatch, change):
    monkeypatch.delenv('COMMERCIAL_RESEARCH_MODE', raising=False)
    from src.mrvl_earnings_sources import fetch_mrvl_earnings_review
    receipt = _facts_receipt()
    options = dict(ticker='MRVL', expected_cik='0001835632', user_agent='Research contact@example.com', observed_at=NOW)
    if change == 'ticker': options['ticker'] = 'AVGO'
    elif change == 'expected_cik': options['expected_cik'] = '0001730168'
    elif change == 'body_cik': receipt['payload']['cik'] = 1730168
    elif change == 'url': receipt['source_url'] = 'https://example.com/facts.json'
    elif change == 'status': receipt['status'] = 'unavailable'
    elif change == 'digest': receipt['payload_sha256'] = 'not-a-digest'
    elif change == 'observation': options['observed_at'] = datetime(2026, 11, 7)
    else: options['user_agent'] = 'Research\r\nInjected: true'
    calls = []
    packet = fetch_mrvl_earnings_review(receipt, source_fetcher=_fetcher(_sources(), calls), **options)
    assert calls == []
    assert packet.get('reason')


@pytest.mark.parametrize('mode', ['1', 'invalid'])
def test_commercial_or_invalid_mode_prevents_new_requests(monkeypatch, mode):
    monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE', mode)
    calls = []
    packet = _collect(source_fetcher=_fetcher(_sources(), calls))
    assert calls == []
    assert packet.get('reason')


@pytest.mark.parametrize('ticker', ['MRVL', 'AVGO'])
@pytest.mark.parametrize('change', ['amendment', 'new_period', 'identity', 'document_path'])
def test_current_scope_must_match_policy_without_fetching_older_document(monkeypatch, ticker, change):
    monkeypatch.delenv('COMMERCIAL_RESEARCH_MODE', raising=False)
    sources = _sources()
    url = MRVL_PROFILE if ticker == 'MRVL' else AVGO_PROFILE
    profile = sources[url]
    recent = profile['filings']['recent']
    if change in {'amendment', 'new_period'}:
        for key in recent:
            recent[key].insert(0, recent[key][0])
        recent['filingDate'][0] = '2026-10-01'
        recent['acceptanceDateTime'][0] = '2026-10-01T12:00:00Z'
        recent['accessionNumber'][0] = profile['cik'] + '-26-000099'
        if change == 'amendment': recent['form'][0] = '10-K/A'
        else: recent['reportDate'][0] = '2026-09-01'
    elif change == 'identity': profile['cik'] = '0000009999'
    else: recent['primaryDocument'][0] = 'other.htm'
    calls = []
    packet = _collect(source_fetcher=_fetcher(sources, calls))
    assert (MRVL_DOCUMENT if ticker == 'MRVL' else AVGO_DOCUMENT) not in calls
    assert len(calls) == 3
    assert packet['documents'][ticker]['status'] == 'unavailable'
    assert packet['documents'][ticker]['reason']
    other = 'AVGO' if ticker == 'MRVL' else 'MRVL'
    assert packet['documents'][other]['status'] == 'ready'
    assert packet['facts']['status'] == 'ready'


@pytest.mark.parametrize('url', [MRVL_PROFILE, AVGO_PROFILE, MRVL_DOCUMENT, AVGO_DOCUMENT])
def test_failed_sources_remain_independent_without_retry_or_exception_disclosure(monkeypatch, url):
    monkeypatch.delenv('COMMERCIAL_RESEARCH_MODE', raising=False)
    sources = _sources()
    sources[url] = OSError('sensitive internal detail https://example.com/?secret=private')
    calls = []
    packet = _collect(source_fetcher=_fetcher(sources, calls))
    assert len(calls) == (3 if url in {MRVL_PROFILE, AVGO_PROFILE} else 4)
    assert calls.count(url) == 1
    assert packet['facts']['status'] == 'ready'
    other = 'AVGO' if url in {MRVL_PROFILE, MRVL_DOCUMENT} else 'MRVL'
    assert packet['documents'][other]['status'] == 'ready'
    assert 'sensitive internal detail' not in json.dumps(packet)
    assert 'example.com' not in json.dumps(packet)
    if url != MRVL_PROFILE:
        from src.mrvl_earnings_review import build_mrvl_earnings_review
        review = build_mrvl_earnings_review(packet, expected_cik='0001835632', as_of=NOW)
        assert review['quality']['status'] == 'inspection_only'
        assert sum(row['status'] == 'available' for row in review['quality']['fields']) == 7


@pytest.mark.parametrize('change', ['redirect', 'oversize', 'not_bytes', 'empty'])
def test_html_response_guards_hold_each_document_without_poisoning_facts(monkeypatch, change):
    monkeypatch.delenv('COMMERCIAL_RESEARCH_MODE', raising=False)
    from src.sec_exact_filing import MAX_FILING_BYTES
    sources = _sources()
    calls = []
    base = _fetcher(sources, calls)
    def fetch(url, agent):
        raw, headers, final = base(url, agent)
        if url == MRVL_DOCUMENT:
            if change == 'redirect': final = 'https://example.com/filing.htm'
            elif change == 'oversize': raw = b'x' * (MAX_FILING_BYTES + 1)
            elif change == 'not_bytes': raw = raw.decode()
            else: raw = b''
        return raw, headers, final
    packet = _collect(source_fetcher=fetch)
    assert len(calls) == 4
    assert packet['facts']['status'] == packet['documents']['AVGO']['status'] == 'ready'
    assert packet['documents']['MRVL']['status'] == 'unavailable'
    assert 'payload_raw_base64' not in packet['documents']['MRVL']
