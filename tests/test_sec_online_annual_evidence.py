"""Exact annual archive fallback for foreign issuers."""
from copy import deepcopy
from datetime import timedelta
import json

import pytest

from test_sec_inline_filing import OBSERVED, _xml
from test_sec_exact_filing import MAP, SUB
from test_sec_online_quarter_evidence import CIK, FACTS, _seal

CONTACT = 'Constructed research contact'
ACCESSION = '0000004321-26-000001'
SOURCE = 'https://www.sec.gov/Archives/edgar/data/1234/000000432126000001/fict-20251231.htm'


def _sources(*, unit='TWD', history_unit=None, covered=False, form='20-F', inline=True):
    metadata = dict(cik=1234, name='Constructed foreign issuer', tickers=['FICT'],
        entityType='operating', fiscalYearEnd='1231',
        filings={'recent': dict(accessionNumber=[ACCESSION], reportDate=['2025-12-31'],
            filingDate=['2026-08-01'], acceptanceDateTime=['2026-08-01T12:00:00Z'],
            form=[form], primaryDocument=['fict-20251231.htm'], isInlineXBRL=[int(inline)], isXBRL=[1])})
    year = '2025' if covered else '2024'
    data = dict(start=year + '-01-01', end=year + '-12-31', filed='2026-08-01' if covered else '2025-08-01',
        form='20-F', accn=ACCESSION if covered else '0000004321-25-000001', val=1_000_000_000)
    facts = dict(cik=1234, entityName='Constructed foreign issuer', facts={'ifrs-full': {
        'Revenue': {'units': {history_unit or unit: [data]}}
    }})
    document = _xml(annual=True).replace('iso:TWD', 'iso:' + unit)
    return {MAP: {'0': {'ticker': 'FICT', 'cik_str': 1234}}, SUB: metadata, FACTS: facts, SOURCE: document}


def _fetch(sources, calls):
    def fetch(url, agent):
        assert agent == CONTACT
        calls.append(url)
        value = sources[url]
        return (value.encode() if isinstance(value, str) else json.dumps(value).encode()), {}, url
    return fetch


def _online(sources=None, calls=None, when=OBSERVED):
    from src.sec_annual_history import fetch_sec_online_research_view
    return fetch_sec_online_research_view('FICT', user_agent=CONTACT, observed_at=when,
        source_fetcher=_fetch(_sources() if sources is None else sources, [] if calls is None else calls))


@pytest.mark.parametrize('currency', ['TWD', 'MXN'])
def test_loader_fetches_one_latest_annual_and_preserves_original_receipts_and_literals(currency):
    from src.sec_online_annual_evidence import validated_archive_annual
    calls = []
    financial = _online(_sources(unit=currency), calls)
    assert calls == [MAP, FACTS, SUB, SOURCE]
    before = deepcopy(financial)
    result = validated_archive_annual(financial, ticker='FICT', expected_cik=CIK, as_of=OBSERVED)
    assert result['unit'] == currency and result['taxonomy'] == 'ifrs-full'
    assert result['period_kind'] == 'annual' and result['form'] == '20-F'
    assert result['accession'] == ACCESSION and result['source_url'] == SOURCE
    assert [r['source_url'] for r in result['source_receipts']] == [MAP, SUB, SOURCE]
    assert result['rights_status'] == 'unregistered_sec_archive_personal_inspection_only'
    assert result['commercial_eligible'] is False and result['saved_readiness_promoted'] is False
    annual, = result['periods']
    assert annual['kind'] == 'annual' and annual['status'] == 'available'
    assert (annual['period_start'], annual['period_end']) == ('2025-01-01', '2025-12-31')
    assert set(annual['fields']) == {'revenue', 'operating_income', 'cash_from_operations', 'capital_expenditures'}
    assert annual['fields']['revenue']['reported_text'] == '1,234'
    assert annual['fields']['revenue']['value'] == 1_234_000_000
    assert not any(key in json.dumps(result) for key in ('"raw_text"', '"source_packet"', '"bank_scope"', 'base64'))
    assert financial['foreign_financials']['annual'][-1]['period_end'] == '2024-12-31'
    assert financial == before and calls == [MAP, FACTS, SUB, SOURCE]


@pytest.mark.parametrize('kwargs', [dict(covered=True), dict(form='10-K'), dict(inline=False)])
def test_supported_structured_annual_or_ineligible_form_skips_archive_document(kwargs):
    calls = []
    financial = _online(_sources(**kwargs), calls)
    assert calls == [MAP, FACTS, SUB]
    assert financial['archive_annual']['status'] == 'withheld'


@pytest.mark.parametrize('kwargs,reason', [
    (dict(unit='USD'), 'archive_annual_native_ifrs_required'),
    (dict(unit='TWD', history_unit='EUR'), 'archive_annual_reporting_currency_conflict'),
])
def test_usd_and_known_reporting_currency_conflicts_remain_held(kwargs, reason):
    from src.sec_online_annual_evidence import validated_archive_annual
    financial = _online(_sources(**kwargs))
    assert financial['archive_annual']['reason'] == reason
    assert validated_archive_annual(financial, as_of=OBSERVED) is None


@pytest.mark.parametrize('problem', ['literal', 'receipt', 'accession', 'form', 'currency', 'commercial', 'stale'])
def test_annual_read_revalidates_original_filing_and_scope(problem):
    from src.sec_online_annual_evidence import validated_archive_annual
    financial = _online()
    wrapper = financial['archive_annual']
    packet = wrapper['source_packet']
    if problem == 'literal':
        packet['periods'][0]['fields']['revenue']['value'] += 1
    elif problem == 'receipt':
        packet['source_receipts'][1]['payload_sha256'] = 'e' * 64
    elif problem == 'accession':
        packet['accession'] = '0000004321-26-000003'
    elif problem == 'form':
        packet['form'] = '20-F/A'
    elif problem == 'currency':
        packet['unit'] = 'USD'
        for field in packet['periods'][0]['fields'].values():
            field['unit'] = 'USD'
    elif problem == 'commercial':
        packet['commercial_eligible'] = True
    _seal(packet)
    wrapper['source_packet_digest'] = packet['packet_digest']
    _seal(wrapper)
    as_of = OBSERVED + timedelta(hours=25) if problem == 'stale' else OBSERVED
    assert validated_archive_annual(financial, as_of=as_of) is None


def test_unusable_latest_amendment_does_not_fetch_original_document():
    calls = []
    sources = _sources()
    recent = sources[SUB]['filings']['recent']
    for column in recent.values():
        column.append(column[0])
    recent['accessionNumber'][1] = '0000004321-26-000002'
    recent['form'][1] = '20-F/A'
    recent['filingDate'][1] = '2026-09-01'
    recent['acceptanceDateTime'][1] = '2026-09-01T12:00:00Z'
    recent['primaryDocument'][1] = 'latest-amendment.htm'
    recent['isInlineXBRL'][1] = 0
    financial = _online(sources, calls)
    assert calls == [MAP, FACTS, SUB]
    assert financial['archive_annual']['status'] == 'withheld'


@pytest.mark.parametrize('change', ['later_period', 'later_same_period_version'])
def test_newer_structured_annual_evidence_blocks_filing_request(change):
    calls = []
    sources = _sources()
    start, end = ('2025-07-01', '2026-06-30') if change == 'later_period' else ('2025-01-01', '2025-12-31')
    rows = sources[FACTS]['facts']['ifrs-full']['Revenue']['units']['TWD']
    rows.append(dict(start=start, end=end, filed='2026-09-01', form='20-F/A',
                     accn='0000004321-26-000002', val=1_500_000_000))
    financial = _online(sources, calls)
    assert calls == [MAP, FACTS, SUB]
    assert financial['archive_annual']['reason'] == 'archive_annual_newer_structured_period_or_version'
