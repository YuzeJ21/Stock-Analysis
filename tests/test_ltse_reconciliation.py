from datetime import datetime, timezone
import hashlib
import json
from urllib.error import HTTPError

import pytest

import src.ltse_reconciliation as ltse
from src.ltse_reconciliation import CASES, SESSION_KEY, check_ltse, get_ltse, ltse_html

NOW = datetime(2026, 11, 12, 23, tzinfo=timezone.utc)
LTSE = 'Long-Term Stock Exchange'
HEADERS = ('<tr><th>Title of each class</th><th>Trading Symbol(s)</th>'
           '<th>Name of each exchange on which registered</th></tr>')


def fixture_transport(fault=None):
    calls = []

    def fetch(url, _agent):
        calls.append(url)
        case = next(c for c in CASES if url in {c.filing.metadata_url, c.filing.source_url})
        filing = case.filing
        target = filing.symbol == 'ASAN'
        if url == filing.metadata_url:
            if target and fault == 'rate_limit':
                raise HTTPError(url, 429, 'Limited', {}, None)
            filed = '2026-11-13' if target and fault == 'future' else case.filed
            payload = {
                'cik': '1' if target and fault == 'wrong_cik' else filing.cik,
                'filings': {'recent': {
                    'accessionNumber': [filing.accession], 'form': [filing.form],
                    'primaryDocument': [filing.document], 'filingDate': [filed],
                    'reportDate': [case.report_date], 'acceptanceDateTime': [filed + 'T12:00:00Z'],
                }},
            }
            return json.dumps(payload).encode(), {}, url
        title = 'Class B common stock' if target and fault == 'wrong_class' else case.security_class
        ticker = filing.symbol + 'X' if target and fault == 'wrong_symbol' else filing.symbol
        primary = 'The Nasdaq Stock Market LLC' if case.primary_venue == 'Nasdaq' else 'New York Stock Exchange'
        if target and fault == 'wrong_venue':
            primary = 'NYSE American'
        continuation = f'<tr><td></td><td></td><td>{LTSE}</td></tr>'
        if target and fault == 'different_security':
            continuation = f'<tr><td>Warrants</td><td>ASANW</td><td>{LTSE}</td></tr>'
        if target and fault == 'hidden':
            continuation = f'<tr><td></td><td></td><td hidden="">{LTSE}</td></tr>'
        body = (f'<html><table>{HEADERS}<tr><td>{title}</td><td>{ticker}</td><td>{primary}</td></tr>'
                f'{continuation}</table></html>').encode()
        return body, {}, url + '.other' if target and fault == 'redirect' else url

    return fetch, calls


def test_ltse_confirms_exact_classes_and_keeps_the_spotlight_denominator_separate():
    fetch, calls = fixture_transport()
    state = {'canonical': {'kept': True}}
    assert get_ltse(state, refresh=False, user_agent='Test', fetcher=fetch)['status'] == 'not_requested'
    assert not calls
    result = get_ltse(state, refresh=True, user_agent='Test', fetcher=fetch, observed_at=NOW)
    assert result['sample_count'] == result['confirmed_count'] == result['security_identity_count'] == 3
    assert result['spotlight_observed_on'] == '2026-11-12'
    assert result['roster_status'] == 'withheld'
    assert all(row['current_listing_status'] == 'withheld' for row in result['rows'])
    assert [(r['symbol'], r['security_class'], r['exchanges']) for r in result['rows']] == [
        ('ASAN', 'Class A common stock', ('NYSE', LTSE)),
        ('TDUP', 'Class A common stock', ('Nasdaq', LTSE)),
        ('BLX', 'Class E common stock', ('NYSE', LTSE)),
    ]
    assert result['rows'][2]['filed'] == '2026-04-20'
    assert (result['rows'][0]['accession'], result['rows'][0]['filed'], result['rows'][0]['report_date']) == (
        '0001628280-26-072757', '2026-11-10', '2026-11-06')
    assert all(len(r['payload_sha256']) == len(r['metadata_sha256']) == 64 for r in result['rows'])
    assert set(state) == {'canonical', SESSION_KEY} and state['canonical'] == {'kept': True}
    assert get_ltse(state, refresh=False, user_agent='Test', fetcher=fetch) == result
    assert get_ltse(state, refresh=True, user_agent='Test', fetcher=fetch, workspace_mode='public')['status'] == 'withheld'
    assert len(calls) == 6 and all('sec.gov/' in url for url in calls)
    html = ltse_html(result)
    assert '3 of 3 LTSE dual listings confirmed as filed' in html
    assert 'Complete dated roster' in html and 'TWLO' in html and '2022-12-29' in html
    assert 'Class E common stock' in html and 'Form 20-F' in html


@pytest.mark.parametrize(('fault', 'reason', 'identity_count'), [
    ('wrong_symbol', 'cover_security_row_missing_or_ambiguous', 2),
    ('hidden', 'cover_security_row_missing_or_ambiguous', 2),
    ('wrong_class', 'security_class_mismatch', 2),
    ('different_security', 'ltse_missing_from_security_row', 3),
    ('wrong_venue', 'companion_exchange_mismatch', 3),
    ('wrong_cik', 'filing_metadata_mismatch', 2),
    ('future', 'filing_metadata_mismatch', 2),
    ('redirect', 'filing_response_unverified', 2),
])
def test_ltse_withholds_only_unsupported_rows(fault, reason, identity_count):
    fetch, calls = fixture_transport(fault)
    result = check_ltse(user_agent='Test', fetcher=fetch, observed_at=NOW)
    assert result['confirmed_count'] == 2 and result['sample_count'] == 3
    assert result['security_identity_count'] == identity_count
    assert result['rows'][0]['reason'] == reason
    if fault in {'wrong_cik', 'future'}:
        assert CASES[0].filing.source_url not in calls


def test_ltse_stops_after_sec_access_limit():
    fetch, calls = fixture_transport('rate_limit')
    result = check_ltse(user_agent='Test', fetcher=fetch, observed_at=NOW)
    assert calls == [CASES[0].filing.metadata_url]
    assert result['confirmed_count'] == 0
    assert [r['reason'] for r in result['rows']] == ['sec_access_paused'] * 3


@pytest.mark.parametrize('fault', [None, 'duplicate', 'bad_acceptance'])
def test_post_filing_screen_uses_acceptance_time_and_never_promotes_listing_status(fault):
    fetch, _ = fixture_transport()
    target = CASES[1].filing

    def transport(url, agent):
        raw, headers, final = fetch(url, agent)
        if url != target.metadata_url:
            return raw, headers, final
        body = json.loads(raw)
        recent = body['filings']['recent']
        rows = (
            ('0001484778-26-000034', '25-NSE', '2026-11-04', '2026-11-04T12:05:00Z'),
            ('0001484778-26-000035', 'CERT', '2026-11-13', '2026-11-13T12:00:00Z'),
            ('0001484778-26-000032', '25', '2026-11-04', '2026-11-04T11:59:59Z'),
        )
        for accession, form, filed, accepted in rows:
            recent['accessionNumber'].append(recent['accessionNumber'][-1] if fault == 'duplicate' else accession)
            recent['form'].append(form)
            recent['filingDate'].append(filed)
            recent['acceptanceDateTime'].append('invalid' if fault == 'bad_acceptance' else accepted)
            recent['primaryDocument'].append('synthetic.htm')
            recent['reportDate'].append('')
        return json.dumps(body).encode(), headers, final

    result = check_ltse(user_agent='Test', fetcher=transport, observed_at=NOW)
    row = result['rows'][1]
    assert row['current_listing_status'] == 'withheld'
    if fault == 'duplicate':
        assert row['confirmed'] is False
        assert 'post_filing_scan' not in row
    elif fault:
        assert row['confirmed'] is True
        assert row['post_filing_scan'] is None
    else:
        scan = row['post_filing_scan']
        assert scan['later_count'] == 1
        assert [event['form'] for event in scan['registration_candidates']] == ['25-NSE']
        assert 'Venue and share class require review' in ltse_html(result)


@pytest.mark.parametrize('changed', [False, True, 'empty_tail_script'])
def test_bladex_rename_is_exact_evidence_separate_from_membership(changed, monkeypatch):
    event = ltse.BLX_RENAME
    raw_notice = b'<html><body>Synthetic corporate name amendment</body></html>'
    monkeypatch.setattr(ltse, 'BLX_RENAME_SHA256', hashlib.sha256(raw_notice).hexdigest())
    fetch, calls = fixture_transport()

    def transport(url, agent):
        if url == event.source_url:
            calls.append(url)
            body = (raw_notice + b' changed' if changed is True else
                    raw_notice.replace(b'</body>', b'<script type="text/javascript" src="/sec/proxy"></script></body>')
                    if changed == 'empty_tail_script' else raw_notice)
            return body, {}, url
        raw, headers, final = fetch(url, agent)
        if url != event.metadata_url:
            return raw, headers, final
        body = json.loads(raw)
        recent = body['filings']['recent']
        for key, value in dict(accessionNumber=event.accession, form=event.form, primaryDocument=event.document,
                               filingDate='2026-06-08', reportDate='2026-06-04',
                               acceptanceDateTime='2026-06-06T00:40:20Z').items():
            recent[key].append(value)
        return json.dumps(body).encode(), headers, final

    result = check_ltse(user_agent='Test', fetcher=transport, observed_at=NOW)
    row = result['rows'][2]
    assert calls.count(event.source_url) == 1
    assert row['confirmed'] is True and row['current_listing_status'] == 'withheld'
    assert row['post_filing_scan']['registration_candidates'] == []
    if changed is True:
        assert row['issuer_change'] is None
        assert 'renamed Bladex, Inc.' not in ltse_html(result)
    else:
        assert row['issuer_change']['effective'] == '2026-06-04'
        assert row['issuer_change']['filed'] == '2026-06-08'
        assert 'renamed Bladex, Inc.' in ltse_html(result)
        if changed == 'empty_tail_script':
            assert row['issuer_change']['payload_sha256'] != row['issuer_change']['body_sha256']
