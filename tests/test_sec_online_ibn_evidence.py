from copy import deepcopy
from datetime import timedelta
import json
import re
from urllib.error import HTTPError

import pytest

from test_sec_exact_filing import MAP, _submission
from test_sec_html_bank import URL, html
from test_sec_inline_filing import OBSERVED


TICKER = 'IBN'
CIK = '0001103838'
SUB = 'https://data.sec.gov/submissions/CIK0001103838.json'
FACTS = 'https://data.sec.gov/api/xbrl/companyfacts/CIK0001103838.json'


def sources():
    profile = _submission()
    profile.update(cik=1103838, name='ICICI BANK LTD', sic='6029', fiscalYearEnd='0331',
                   tickers=['IBN'], exchanges=['NYSE'], entityType='other')
    profile['filings']['recent'].update(form=['20-F'], reportDate=['2026-03-31'],
                                        isInlineXBRL=[0], isXBRL=[0])
    return {MAP: {'0': {'ticker': 'IBN', 'cik_str': 1103838}}, SUB: profile, URL: html()}


def online(values=None, calls=None):
    from src.sec_annual_history import fetch_sec_online_research_view

    values = sources() if values is None else values

    def fetch(url, agent):
        if calls is not None:
            calls.append(url)
        if url == FACTS:
            raise HTTPError(url, 404, 'Not Found', {}, None)
        value = values[url]
        raw = value.encode() if isinstance(value, str) else json.dumps(value).encode()
        return raw, {}, url

    return fetch_sec_online_research_view(TICKER, user_agent='Constructed research contact',
                                         source_fetcher=fetch, observed_at=OBSERVED)


def test_missing_companyfacts_keeps_qualified_ibn_annual_evidence_online():
    from src.sec_online_ibn_evidence import validated_ibn_archive_annual

    calls = []
    financial = online(calls=calls)
    original = deepcopy(financial)
    archive = validated_ibn_archive_annual(financial, ticker=TICKER, expected_cik=CIK, as_of=OBSERVED)
    assert calls == [MAP, FACTS, SUB, URL]
    assert financial.get('companyfacts_identity') is None
    assert financial.get('status') != 'inspection_only'
    assert archive['archive_identity']['kind'] == 'sec_ticker_map_and_submissions'
    assert archive['form'] == '20-F' and archive['unit'] == 'INR' and archive['accounting_basis'] == 'Indian GAAP'
    assert [row['period_end'] for row in archive['periods']] == ['2026-03-31', '2025-03-31', '2024-03-31']
    assert archive['commercial_eligible'] is archive['saved_readiness_promoted'] is False
    assert archive['financial_coverage_promoted'] is False
    row = archive['periods'][0]
    assert row['kind'] == 'annual' and row['status'] == 'available' and row['period_start'] == '2025-04-01'
    assert row['fields']['total_income']['value'] == 120_000
    assert row['fields']['total_income']['source_ref'] == URL + '#f_003'
    purchases = row['fields']['fixed_asset_purchases']
    assert purchases['reported_numeric_schema'] == 'sec-ibn-bank-number-v1'
    assert (purchases['reported_text'], purchases['value']) == ('(4)', -4000)
    assert set(archive['withheld_fields']) >= {'revenue', 'operating_income', 'free_cash_flow', 'valuation'}
    assert 'raw_text' not in json.dumps(archive) and 'raw_cover' not in json.dumps(archive)
    assert financial == original
    assert validated_ibn_archive_annual(financial, as_of=OBSERVED + timedelta(hours=25)) is None


@pytest.mark.parametrize('problem', ['inline', 'xbrl', 'missing_document', 'unsupported_bank_scope'])
def test_unqualified_latest_filing_does_not_request_or_fall_back(problem):
    from src.sec_online_ibn_evidence import validated_ibn_archive_annual

    values = sources()
    profile = values[SUB]
    rows = profile['filings']['recent']
    if problem == 'unsupported_bank_scope':
        profile['sic'] = '3674'
    else:
        for cells in rows.values():
            cells.append(cells[0])
        rows['accessionNumber'][-1] = '0000004321-26-000002'
        rows['form'][-1] = '20-F/A'
        rows['filingDate'][-1] = '2026-09-01'
        rows['acceptanceDateTime'][-1] = '2026-09-01T12:00:00Z'
        rows['primaryDocument'][-1] = '' if problem == 'missing_document' else 'newer-amendment.htm'
        rows['isInlineXBRL'][-1] = int(problem == 'inline')
        rows['isXBRL'][-1] = int(problem in {'inline', 'xbrl'})
    calls = []
    financial = online(values, calls)
    assert calls == [MAP, FACTS, SUB]
    assert validated_ibn_archive_annual(financial, as_of=OBSERVED) is None
    assert financial['ibn_archive_annual']['status'] == 'withheld'


def test_validated_ibn_archive_rejects_resealed_identity_or_latest_accession_substitutions():
    from src.online_filing_context import _digest
    from src.sec_online_ibn_evidence import validated_ibn_archive_annual

    base = online()
    for problem in ('issuer', 'accession', 'receipt', 'rights'):
        financial = deepcopy(base)
        wrapper = financial['ibn_archive_annual']
        if problem == 'issuer':
            wrapper['archive_identity']['sec_cik'] = '0000000001'
        elif problem == 'accession':
            source = wrapper['source_packet']
            source['accession'] = '0000004321-26-000002'
            source['packet_digest'] = _digest({k: v for k, v in source.items() if k != 'packet_digest'})
        elif problem == 'receipt':
            wrapper['archive_identity']['submissions_receipt']['payload_sha256'] = 'a' * 64
        else:
            wrapper['commercial_eligible'] = True
        wrapper['packet_digest'] = _digest({k: v for k, v in wrapper.items() if k != 'packet_digest'})
        assert validated_ibn_archive_annual(financial, as_of=OBSERVED) is None


def test_latest_ibn_annual_requires_at_least_one_qualified_current_field():
    from src.sec_html_bank import DEFINITIONS
    from src.sec_online_ibn_evidence import validated_ibn_archive_annual

    values = sources()
    for name, (_, label, _) in DEFINITIONS.items():
        if name != 'total_income':
            values[URL] = re.sub(r'(<tr><td>' + re.escape(label) + r'</td><td colspan="3">)[^<]+',
                                 r'\g<1>nil', values[URL])
    partial = validated_ibn_archive_annual(online(values), as_of=OBSERVED)
    assert set(partial['periods'][0]['fields']) == {'total_income'}
    values[URL] = values[URL].replace('>120</td>', '>nil</td>')
    financial = online(values)
    assert financial['ibn_archive_annual']['reason'] == 'ibn_annual_current_fields_unavailable'
    assert validated_ibn_archive_annual(financial, as_of=OBSERVED) is None
