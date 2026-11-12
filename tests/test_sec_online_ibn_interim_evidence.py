from copy import deepcopy
from datetime import timedelta
import json
from urllib.error import HTTPError

from test_sec_html_bank import URL as ANNUAL_URL
from test_sec_online_ibn_evidence import CIK, FACTS, MAP, OBSERVED, SUB, TICKER, sources as annual_sources


def _add_event(values, sequence, *, filed='2026-10-22', report_date='2026-10-19', form='6-K', body):
    accession = f'0000004321-26-{sequence:06d}'
    filename = f'report{sequence}.htm'
    url = f'https://www.sec.gov/Archives/edgar/data/1103838/{accession.replace("-", "")}/{filename}'
    record = dict(accessionNumber=accession, form=form, filingDate=filed, reportDate=report_date,
                  acceptanceDateTime=filed + 'T12:00:00Z', primaryDocument=filename, isInlineXBRL=0, isXBRL=0)
    for key, entries in values[SUB]['filings']['recent'].items():
        entries.append(record[key])
    values[url] = body
    return url


def _notice(text, form='6-K'):
    return (f'<html><body><p>FORM {form}</p><p>ICICI Bank Limited</p><p>Table of Contents</p>'
            '<p>Items:</p><p>1. Other news</p><p>OTHER NEWS</p><p>Subject: Disclosure under Indian Listing Regulations</p>'
            f'<p>{text}</p></body></html>')


def sources():
    from test_sec_ibn_interim_tables import interim_html

    values = annual_sources()
    results = _add_event(values, 2, body=interim_html())
    latest = _add_event(values, 3, filed='2026-10-25', body=_notice(
        'The Goods and Services Tax department confirmed a penalty. The Bank received an Order in Appeal.'))
    return values, results, latest


def online(values=None, calls=None, *, observed_at=OBSERVED):
    from src.sec_annual_history import fetch_sec_online_research_view

    values = sources()[0] if values is None else values

    def fetch(url, agent):
        if calls is not None:
            calls.append(url)
        if url == FACTS:
            raise HTTPError(url, 404, 'Not Found', {}, None)
        value = values[url]
        raw = value if isinstance(value, bytes) else value.encode() if isinstance(value, str) else json.dumps(value).encode()
        return raw, {}, url

    return fetch_sec_online_research_view(TICKER, user_agent='Constructed research contact',
                                         source_fetcher=fetch, observed_at=observed_at)


def test_ibn_interim_reuses_annual_identity_and_keeps_event_date_separate():
    from src.sec_online_ibn_interim_evidence import validated_ibn_archive_interim

    values, results, latest = sources()
    calls = []
    financial = online(values, calls)
    prior = deepcopy(financial)
    packet = validated_ibn_archive_interim(financial, ticker=TICKER, expected_cik=CIK, as_of=OBSERVED)
    assert calls == [MAP, FACTS, SUB, ANNUAL_URL, latest, results]
    assert financial == prior and 'companyfacts_identity' not in financial
    assert packet['source_url'] == results and packet['unit'] == 'INR'
    assert packet['report_date'] == '2026-10-19' and packet['period_end'] == '2026-09-30'
    quarter, cumulative = packet['periods']
    assert (quarter['kind'], quarter['period_start']) == ('quarterly', '2026-07-01')
    assert (cumulative['kind'], cumulative['period_start']) == ('cumulative', '2026-04-01')
    assert quarter['period_end'] == cumulative['period_end'] == packet['period_end']
    assert packet['reviewed_preceding'][0]['reason'] == 'gst_tax_appeal'
    assert packet['archive_identity'] == financial['ibn_archive_annual']['archive_identity']
    assert packet['commercial_eligible'] is packet['financial_coverage_promoted'] is False
    assert validated_ibn_archive_interim(financial, as_of=OBSERVED + timedelta(hours=25)) is None


def test_newer_ambiguous_or_amended_6k_preserves_annual_and_does_not_fall_back():
    from src.sec_online_ibn_evidence import validated_ibn_archive_annual
    from src.sec_online_ibn_interim_evidence import validated_ibn_archive_interim

    for form, reason in [('6-K', 'ibn_interim_newer_filing_scope_unresolved'), ('6-K/A', 'ibn_interim_amendment_unresolved')]:
        values, results, latest = sources()
        unknown = _add_event(values, 4, form=form, filed='2026-10-27', body=_notice('Unknown report.', form=form))
        calls = []
        financial = online(values, calls)
        assert calls == [MAP, FACTS, SUB, ANNUAL_URL, unknown]
        assert results not in calls and latest not in calls
        assert financial['ibn_archive_interim']['reason'] == reason
        assert validated_ibn_archive_interim(financial, as_of=OBSERVED) is None
        assert validated_ibn_archive_annual(financial, as_of=OBSERVED)['period_end'] == '2026-03-31'


def test_interim_resealed_packet_rejects_a_foreign_duration_or_receipt():
    from src.online_filing_context import _digest
    from src.sec_online_ibn_interim_evidence import validated_ibn_archive_interim

    financial = online()
    for problem in ('duration', 'receipt', 'skip', 'rights', 'unknown_proof_key'):
        changed = deepcopy(financial)
        packet = changed['ibn_archive_interim']
        if problem == 'duration':
            packet['periods'][0]['period_start'] = '2026-04-01'
        elif problem == 'receipt':
            packet['source_receipts'][-1]['source_url'] = ANNUAL_URL
        elif problem == 'skip':
            packet['reviewed_preceding'].clear()
        elif problem == 'unknown_proof_key':
            packet['periods'][0]['fields']['total_income']['extra_proof'] = 'unsupported'
        else:
            packet['commercial_eligible'] = True
        packet['packet_digest'] = _digest({key: value for key, value in packet.items() if key != 'packet_digest'})
        assert validated_ibn_archive_interim(changed, as_of=OBSERVED) is None
