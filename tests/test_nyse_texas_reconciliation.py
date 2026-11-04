from datetime import datetime, timezone
import json
from urllib.error import HTTPError

import pytest

from src.nyse_texas_reconciliation import (
    CASES, SESSION_KEY, check_nyse_texas, cover_registration, get_nyse_texas,
    reconciliation_html,
)

NOW = datetime(2026, 11, 4, 20, tzinfo=timezone.utc)
HEADER = ('<tr><th>Title of Each Class</th><th>Trading Symbol(s)</th>'
          '<th>Name of Each Exchange on Which Registered</th></tr>')


def document(symbol, exchange='New York Stock Exchange', continuation='', title='Common Stock'):
    return (f'<html><body><table>{HEADER}<tr><td>{title}</td><td>{symbol}</td>'
            f'<td>{exchange}</td></tr>{continuation}</table></body></html>').encode()


@pytest.mark.parametrize('raw', [
    document('DEMO', 'New York Stock Exchange<br/>NYSE Texas, Inc.'),
    document('DEMO', continuation='<tr><td></td><td></td><td>NYSE Texas</td></tr>'),
])
def test_resolves_the_same_security_across_two_explicit_venues(raw):
    assert cover_registration(raw, 'DEMO') == ('common_shares', ('NYSE', 'NYSE Texas'))


@pytest.mark.parametrize(('raw', 'expected'), [
    (document('DEMO', continuation='<tr><td>Warrant</td><td>DEMOW</td><td>NYSE Texas</td></tr>'),
     ('common_shares', ('NYSE',))),
    (document('DEMO', continuation='<tr><td></td><td></td><td hidden="">NYSE Texas</td></tr>'), None),
    (document('DEMO', continuation='<tr><td>Common Stock</td><td>DEMO</td><td>NYSE Texas</td></tr>'), None),
    (document('DEMO', continuation='<tr><td></td><td>NYSE Texas</td><td></td></tr>'), None),
    (document('DEMO', 'NYSE Texas (proposed)'), ('common_shares', ())),
    (document('DEMO', 'NYSE Texas', title='Warrants to purchase Common Stock'), (None, ('NYSE Texas',))),
    (document('DEMOX', 'NYSE Texas'), None),
    (b'<!DOCTYPE html>' + document('DEMO', 'NYSE Texas'), None),
])
def test_does_not_borrow_other_instruments_or_hidden_or_ambiguous_cells(raw, expected):
    assert cover_registration(raw, 'DEMO') == expected


def transport(*, wrong_document=False, future=False, redirected=False, single_venue=False):
    calls = []

    def fetch(url, user_agent):
        calls.append(url)
        case = next(c for c in CASES if url in {c.metadata_url, c.source_url})
        if url == case.metadata_url:
            payload = {
                'cik': int(case.cik),
                'filings': {'recent': {
                    'accessionNumber': [case.accession], 'form': ['8-K'],
                    'primaryDocument': ['wrong.htm' if wrong_document else case.document],
                    'filingDate': ['2026-11-05' if future else '2026-11-02'],
                    'reportDate': ['2026-11-01'],
                    'acceptanceDateTime': ['2026-11-05T16:00:00Z' if future else '2026-11-02T16:00:00Z'],
                }},
            }
            return json.dumps(payload).encode(), {}, url
        exchange = 'New York Stock Exchange' if single_venue else 'New York Stock Exchange<br/>NYSE Texas'
        return document(case.symbol, exchange), {}, url + '.bad' if redirected else url

    return fetch, calls


def test_filing_evidence_is_bounded_session_only_and_no_request_on_rerender():
    state = {'canonical': {'unchanged': True}}
    fetch, calls = transport()
    assert get_nyse_texas(state, refresh=False, user_agent='Test', fetcher=fetch)['status'] == 'not_requested'
    assert calls == []
    result = get_nyse_texas(state, refresh=True, user_agent='Test', fetcher=fetch, observed_at=NOW)
    assert set(state) == {'canonical', SESSION_KEY} and state['canonical'] == {'unchanged': True}
    assert result['confirmed_count'] == len(CASES) == result['security_identity_count']
    assert len(calls) == 2 * len(CASES)
    first = result['rows'][0]
    assert first['filed'] == '2026-11-02' and first['observed_at'] == '2026-11-04T20:00:00Z'
    assert len(first['payload_sha256']) == len(first['metadata_sha256']) == 64
    assert 'Current active status' in reconciliation_html(result)
    assert get_nyse_texas(state, refresh=False, user_agent='Test', fetcher=fetch) == result
    assert len(calls) == 2 * len(CASES)
    public = get_nyse_texas(state, refresh=True, user_agent='Test', fetcher=fetch, workspace_mode='public')
    assert public['status'] == 'withheld'
    assert len(calls) == 2 * len(CASES)


@pytest.mark.parametrize(('options', 'reason'), [
    ({'wrong_document': True}, 'filing_metadata_mismatch'),
    ({'future': True}, 'filing_metadata_mismatch'),
    ({'redirected': True}, 'filing_response_unverified'),
    ({'single_venue': True}, 'nyse_texas_missing_from_security_row'),
])
def test_failures_remain_in_denominator(options, reason):
    fetch, _ = transport(**options)
    result = check_nyse_texas(user_agent='Test', fetcher=fetch, observed_at=NOW)
    assert result['confirmed_count'] == 0 and result['sample_count'] == len(CASES)
    assert all(row['reason'] == reason for row in result['rows'])
    if options.get('single_venue'):
        assert result['security_identity_count'] == len(CASES)


def test_off_grid_exchange_and_hidden_cover_are_withheld():
    raw = document('DEMO', continuation='<tr><td colspan="2"></td><td></td><td>NYSE Texas</td></tr>')
    assert cover_registration(raw, 'DEMO') is None
    raw = document('DEMO', 'NYSE Texas').replace(b'<table>', b'<div hidden=""><table>').replace(b'</table>', b'</table></div>')
    assert cover_registration(raw, 'DEMO') is None


def test_sec_access_limit_pauses_remaining_candidates():
    calls = []

    def fetch(url, _agent):
        calls.append(url)
        raise HTTPError(url, 429, 'Limited', {}, None)

    result = check_nyse_texas(user_agent='Test', fetcher=fetch, observed_at=NOW)
    assert calls == [CASES[0].metadata_url]
    assert result['confirmed_count'] == 0
    assert [r['reason'] for r in result['rows']] == ['sec_access_paused'] * len(CASES)
