from datetime import datetime, timezone
import hashlib
import json
from urllib.error import HTTPError

import pytest

import src.nyse_texas_reconciliation as audit
import src.sec_exact_filing as exact_filing
from src.nyse_texas_reconciliation import (
    CASES, SESSION_KEY, check_nyse_texas, cover_registration, get_nyse_texas,
    reconciliation_html,
)

NOW = datetime(2026, 11, 12, 20, tzinfo=timezone.utc)
HEADER = ('<tr><th>Title of Each Class</th><th>Trading Symbol(s)</th>'
          '<th>Name of Each Exchange on Which Registered</th></tr>')


def test_archive_transport_accepts_bounded_pdf_without_changing_default_callers(monkeypatch):
    seen = {}

    class Response:
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def read(self, size):
            seen['read_size'] = size
            return b'%PDF'

        def geturl(self):
            return 'https://www.sec.gov/example.pdf'

    def fake_open(request, timeout):
        seen['accept'] = request.get_header('Accept')
        return Response()

    monkeypatch.setattr(exact_filing, 'urlopen', fake_open)
    monkeypatch.setattr(exact_filing.time, 'sleep', lambda *_: None)

    raw, _, final = exact_filing._fetch_html('https://www.sec.gov/example.pdf', 'Agent', max_bytes=20,
                                              accept='application/pdf')
    assert (raw, final) == (b'%PDF', 'https://www.sec.gov/example.pdf')
    assert seen == {'read_size': 21, 'accept': 'application/pdf'}


def document(symbol, exchange='New York Stock Exchange', continuation='', title='Common Stock'):
    return (f'<html><body><table>{HEADER}<tr><td>{title}</td><td>{symbol}</td>'
            f'<td>{exchange}</td></tr>{continuation}</table></body></html>').encode()


@pytest.mark.parametrize('raw', [
    document('DEMO', 'New York Stock Exchange<br/>NYSE Texas, Inc.'),
    document('DEMO', continuation='<tr><td></td><td></td><td>NYSE Texas</td></tr>'),
])
def test_resolves_the_same_security_across_two_explicit_venues(raw):
    assert cover_registration(raw, 'DEMO') == ('common_shares', ('NYSE', 'NYSE Texas'))


def test_whole_cell_zero_width_placeholders_are_empty_but_symbol_text_is_exact():
    blank = '\u200b'
    cover = (f'<html><body><table><tr><td>{blank}</td><td>{blank}</td><td>{blank}</td></tr>'
             f'{HEADER}<tr><td>Common Stock, $0.01 Par Value</td><td>DIT</td><td>NYSE American</td></tr>'
             f'<tr><td>{blank}</td><td>{blank}</td><td>NYSE Texas</td></tr></table></body></html>').encode()
    assert cover_registration(cover, 'DIT') == ('common_shares', ('NYSE American', 'NYSE Texas'))
    assert cover_registration(cover.replace(b'>DIT<', 'D\u200bIT'.encode().join((b'>', b'<'))), 'DIT') is None
    decorated = cover.replace(f'<td>{blank}</td>'.encode(),
                              f'<td><span style="visibility:hidden;">{blank}</span></td>'.encode())
    assert cover_registration(decorated, 'DIT') == ('common_shares', ('NYSE American', 'NYSE Texas'))


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
        if url == audit.DIT_FILINGS[0].metadata_url:
            raise OSError('Registration pair unavailable for the cover-only fixture')
        case = next(c for c in CASES if url in {c.metadata_url, c.source_url})
        if url == case.metadata_url:
            payload = {
                'cik': int(case.cik),
                'filings': {'recent': {
                    'accessionNumber': [case.accession], 'form': ['8-K'],
                    'primaryDocument': ['wrong.htm' if wrong_document else case.document],
                    'filingDate': ['2026-11-13' if future else '2026-11-02'],
                    'reportDate': ['2026-11-01'],
                    'acceptanceDateTime': ['2026-11-13T16:00:00Z' if future else '2026-11-02T16:00:00Z'],
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
    assert len(calls) == 2 * len(CASES) + 1
    first = result['rows'][0]
    assert first['filed'] == '2026-11-02' and first['observed_at'] == '2026-11-12T20:00:00Z'
    assert len(first['payload_sha256']) == len(first['metadata_sha256']) == 64
    assert 'Current active status' in reconciliation_html(result)
    assert get_nyse_texas(state, refresh=False, user_agent='Test', fetcher=fetch) == result
    assert len(calls) == 2 * len(CASES) + 1
    public = get_nyse_texas(state, refresh=True, user_agent='Test', fetcher=fetch, workspace_mode='public')
    assert public['status'] == 'withheld'
    assert len(calls) == 2 * len(CASES) + 1


@pytest.mark.parametrize(('options', 'reason'), [
    ({'wrong_document': True}, 'filing_metadata_mismatch'),
    ({'future': True}, 'filing_metadata_mismatch'),
    ({'redirected': True}, 'filing_response_unverified'),
    ({'single_venue': True}, 'nyse_texas_missing_from_security_row'),
])
def test_failures_remain_in_denominator(options, reason):
    fetch, _ = transport(**options)
    result = check_nyse_texas(user_agent='Test', fetcher=fetch, observed_at=NOW)
    assert result['confirmed_count'] == 0 and result['sample_count'] == len(CASES) + 1
    assert all(row['reason'] == reason for row in result['rows'][:-1])
    assert result['rows'][-1]['reason'] == 'filing_metadata_unavailable'
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
    assert [r['reason'] for r in result['rows']] == ['sec_access_paused'] * (len(CASES) + 1)


@pytest.mark.parametrize(('fault', 'reason', 'identity_count'), [
    (None, None, 5),
    ('form_bytes', 'form_8a_digest_mismatch', 4),
    ('certificate_bytes', 'certificate_digest_mismatch', 5),
    ('certificate_redirect', 'certificate_response_unverified', 5),
    ('certificate_type', 'certificate_metadata_mismatch', 5),
    ('certificate_date', 'certificate_metadata_mismatch', 5),
    ('wrong_cik', 'form_8a_metadata_mismatch', 4),
    ('certificate_access', 'sec_access_paused', 5),
    ('notice_bytes', None, 5),
    ('notice_access', None, 5),
    ('notice_metadata', None, 5),
    ('past_directory_cutoff', None, 5),
])
def test_dit_requires_reviewed_registration_and_certificate(fault, reason, identity_count, monkeypatch):
    form, certificate = audit.DIT_FILINGS
    notice = audit.DIT_NOTICE
    form_body = b'<html>Synthetic Form 8-A</html>'
    certificate_body = b'%PDF-1.7 synthetic certificate'
    notice_body = b'<html>Synthetic issuer listing announcement</html>'
    monkeypatch.setattr(audit, 'DIT_REVIEWED_DIGESTS', {
        form.form: hashlib.sha256(form_body).hexdigest(),
        certificate.form: hashlib.sha256(certificate_body).hexdigest(),
        notice.form: hashlib.sha256(notice_body).hexdigest(),
    })
    fetch_base, calls = transport()

    def fetch(url, agent):
        if url not in {form.metadata_url, form.source_url, certificate.source_url, notice.source_url}:
            return fetch_base(url, agent)
        calls.append(url)
        if url == form.metadata_url:
            return json.dumps({
                'cik': '0000000001' if fault == 'wrong_cik' else form.cik,
                'filings': {'recent': {
                    'accessionNumber': [form.accession, certificate.accession, notice.accession],
                    'form': [form.form, '8-K' if fault == 'certificate_type' else certificate.form, notice.form],
                    'primaryDocument': [form.document, certificate.document,
                                        'other.htm' if fault == 'notice_metadata' else notice.document],
                    'filingDate': ['2026-08-12', '2026-08-13' if fault == 'certificate_date' else '2026-08-12',
                                   '2026-08-12'],
                    'reportDate': ['', '', '2026-08-06'],
                    'acceptanceDateTime': ['2026-08-12T11:20:19Z', '2026-08-12T12:47:49Z',
                                           '2026-08-12T11:16:28Z'],
                }},
            }).encode(), {}, url
        if url == form.source_url:
            return (form_body + b' changed' if fault == 'form_bytes' else form_body), {}, url
        if url == notice.source_url:
            if fault == 'notice_access':
                raise HTTPError(url, 429, 'Limited', {}, None)
            return (notice_body + b' changed' if fault == 'notice_bytes' else notice_body), {}, url
        if fault == 'certificate_access':
            raise HTTPError(url, 429, 'Limited', {}, None)
        return ((certificate_body + b' changed' if fault == 'certificate_bytes' else certificate_body), {},
                form.source_url if fault == 'certificate_redirect' else url)

    cutoff = NOW.replace(day=3) if fault == 'past_directory_cutoff' else NOW
    result = check_nyse_texas(user_agent='Test', fetcher=fetch, observed_at=cutoff)
    dit = result['rows'][-1]
    assert dit['symbol'] == 'DIT'
    assert dit['reason'] == reason
    assert result['sample_count'] == 5
    assert result['security_identity_count'] == identity_count
    assert result['confirmed_count'] == (5 if reason is None else 4)
    assert calls.count(form.metadata_url) == 1
    if fault in {'form_bytes', 'certificate_type', 'certificate_date', 'wrong_cik'}:
        assert certificate.source_url not in calls
    if fault is None:
        assert dit['exchanges'] == ('NYSE American', 'NYSE Texas')
        assert [filing['filed'] for filing in dit['filings']] == ['2026-08-12', '2026-08-12']
        assert [filing['report_date'] for filing in dit['filings']] == [None, None]
        assert [filing['payload_sha256'] for filing in dit['filings']] == [audit.DIT_REVIEWED_DIGESTS[c.form] for c in (form, certificate)]
        html = reconciliation_html(result)
        assert 'Form 8-A' in html and 'Exchange certification' in html and 'USD 0.01 per share' in html
        assert '5 of 5 dual registrations confirmed as filed' in html
    elif identity_count == 5:
        assert dit['exchanges'] == (('NYSE American', 'NYSE Texas') if reason is None else ('NYSE American',))

    assert dit['first_trade_date'] is None
    assert dit['directory_observed_on'] == (None if fault == 'past_directory_cutoff' else '2026-11-12')
    notice_failures = {'notice_bytes': 'digest_mismatch', 'notice_metadata': 'metadata_mismatch',
                       'notice_access': 'sec_access_paused', 'certificate_access': 'sec_access_paused',
                       'wrong_cik': 'metadata_mismatch'}
    assert dit['announcement_reason'] == notice_failures.get(fault)
    if fault in notice_failures:
        assert dit['announced_effective_date'] is None
    else:
        assert dit['announced_effective_date'] == '2026-08-13'
        assert dit['announcement']['filed'] == '2026-08-12'
    html = reconciliation_html(result)
    assert 'Actual first trade</strong> · Withheld' in html
    assert ('Present when reviewed on 2026-11-12' in html) == (fault != 'past_directory_cutoff')
    assert 'First trade confirmed' not in html
    if fault == 'past_directory_cutoff':
        assert dit['first_trade_reviewed_on'] is None
        assert 'First-trade sources checked' not in html
    else:
        assert dit['first_trade_reviewed_on'] == '2026-11-12'
        assert 'First-trade sources checked · 2026-11-12' in html
        assert 'July 1–2, 2026' in html
        assert 'NYSE Texas can trade securities listed elsewhere' in html
        assert 'Rule 605' in html and 'limited monthly' in html
        for url in (audit.DIT_TAQ_URL, audit.DIT_TAQ_SAMPLE_URL, audit.DIT_TRADER_UPDATES_URL,
                    audit.DIT_SHORT_VOLUME_URL, audit.DIT_UTP_NOTICE_URL):
            assert f'href="{url}"' in html
            assert url not in calls


def test_dit_latest_10k_is_independent_dated_corroboration_without_first_trade(monkeypatch):
    form, certificate = audit.DIT_FILINGS
    notice, annual = audit.DIT_NOTICE, audit.DIT_LATEST_ANNUAL
    blank = '\u200b'
    annual_body = (f'<html><body><table><tr><td>{blank}</td><td>{blank}</td><td>{blank}</td></tr>'
                   f'{HEADER}<tr><td>Common Stock, $0.01 Par Value</td><td>DIT</td><td>NYSE American</td></tr>'
                   f'<tr><td>{blank}</td><td>{blank}</td><td>NYSE Texas</td></tr></table></body></html>').encode()
    bodies = {form.source_url: b'<html>Reviewed Form 8-A</html>',
              certificate.source_url: b'%PDF Reviewed exchange certificate',
              notice.source_url: b'<html>Reviewed Form 8-K</html>', annual.source_url: annual_body}
    monkeypatch.setattr(audit, 'DIT_REVIEWED_DIGESTS',
                        {case.form: hashlib.sha256(bodies[case.source_url]).hexdigest()
                         for case in (form, certificate, notice, annual)})
    metadata = {'cik': form.cik, 'filings': {'recent': {
        'accessionNumber': [case.accession for case in (form, certificate, notice, annual)],
        'form': [case.form for case in (form, certificate, notice, annual)],
        'primaryDocument': [case.document for case in (form, certificate, notice, annual)],
        'filingDate': ['2026-08-12', '2026-08-12', '2026-08-12', '2026-11-09'],
        'reportDate': ['', '', '2026-08-06', '2026-09-30'],
        'acceptanceDateTime': ['2026-08-12T11:20:19Z', '2026-08-12T12:47:49Z',
                               '2026-08-12T11:16:28Z', '2026-11-09T21:20:42Z'],
    }}}

    def fetch(url, _agent):
        if url == form.metadata_url:
            return json.dumps(metadata).encode(), {}, url
        return bodies[url], {}, url

    dit = audit._check_dit('Agent', fetch, NOW, access_paused=lambda: False)
    annual_review = dit['annual_corroboration']
    assert dit['confirmed'] is True and dit['first_trade_date'] is None
    assert annual_review['confirmed'] is True
    assert annual_review['filed'] == '2026-11-09' and annual_review['report_date'] == '2026-09-30'
    assert annual_review['exchanges'] == ('NYSE American', 'NYSE Texas')
    html = reconciliation_html(dict(status='inspection_only', rows=[dit], sample_count=1,
                                    confirmed_count=1, security_identity_count=1))
    assert 'Dated annual cover' in html and annual.accession in html
    assert 'Actual first trade</strong> · Withheld' in html
