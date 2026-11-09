"""Constructed SEC bytes through the real exact-quarter production workflow.

Amounts are synthetic. Only transports and the harness clock are substituted;
identity, filing selection, inline parsing, archive validation, coverage, trends,
and immutable research snapshots remain production code.
"""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import socket

import pytest


TICKERS = ('C', 'DUK', 'SO', 'NEE')
CIKS = dict(C='0000831001', DUK='0001326160', SO='0000092122', NEE='0000753308')
NOW = datetime(2026, 11, 8, 4, tzinfo=timezone.utc)
END = '2026-09-30'
QUARTER_START = '2026-07-01'
YTD_START = '2026-01-01'
MAPPING = 'https://www.sec.gov/files/company_tickers.json'
VALUES = {
    'C': dict(revenue=23845, net_interest_income=16982, noninterest_income=6863, cash_from_operations=9000),
    'DUK': dict(revenue=8500, operating_income=2100, cash_from_operations=9000, capital_expenditures=7000),
    'SO': dict(revenue=7800, operating_income=2300, cash_from_operations=8200, capital_expenditures=6200),
    'NEE': dict(revenue=7200, operating_income=1900, cash_from_operations=7600),
}


def accession(ticker, *, annual=False):
    return CIKS[ticker] + ('-26-000001' if annual else '-26-000003')


def source_url(ticker):
    return (f'https://www.sec.gov/Archives/edgar/data/{int(CIKS[ticker])}/'
            f'{accession(ticker).replace("-", "")}/{ticker.lower()}-20260930.htm')


def _profile(ticker):
    rows = [
        ('10-Q', END, '2026-11-02', accession(ticker), ticker.lower() + '-20260930.htm'),
        ('10-Q', '2026-06-30', '2026-08-03', CIKS[ticker] + '-26-000002', ticker.lower() + '-20260630.htm'),
        ('10-K', '2025-12-31', '2026-02-02', accession(ticker, annual=True), ticker.lower() + '-20251231.htm'),
    ]
    keys = ('form', 'reportDate', 'filingDate', 'accessionNumber', 'primaryDocument')
    recent = {key: [row[index] for row in rows] for index, key in enumerate(keys)}
    recent.update(acceptanceDateTime=[row[2] + 'T12:00:00Z' for row in rows],
                  isInlineXBRL=[1] * len(rows), isXBRL=[1] * len(rows))
    return dict(cik=int(CIKS[ticker]), name='Constructed exact-quarter ' + ticker,
                tickers=[ticker], exchanges=['NYSE'], sic='6021' if ticker == 'C' else '4911',
                entityType='operating', fiscalYearEnd='1231', filings={'recent': recent})


def _facts(ticker):
    """Companyfacts has Q2, while submissions independently reports Q3."""
    revenue = 'RevenuesNetOfInterestExpense' if ticker == 'C' else 'RegulatedAndUnregulatedOperatingRevenue'
    concepts = {revenue: (10000, 12000, 15000), 'OperatingIncomeLoss': (1000, 1200, 1500),
                'NetCashProvidedByUsedInOperatingActivities': (2500, 3000, 4000),
                'PaymentsToAcquirePropertyPlantAndEquipment': (1500, 1800, 2200)}
    facts = {}
    for concept, values in concepts.items():
        records = [dict(start=f'{year}-01-01', end=f'{year}-12-31', val=value * 1_000_000,
                        filed='2026-02-02', form='10-K', accn=accession(ticker, annual=True), fy=2025, fp='FY')
                   for year, value in zip((2023, 2024, 2025), values)]
        for year, quarters in ((2025, (1, 2, 3)), (2026, (1, 2))):
            for quarter in quarters:
                month = quarter * 3
                end = f'{year}-{month:02d}-' + ('31' if month == 3 else '30')
                start = f'{year}-{month - 2:02d}-01'
                # Q2/Q3 cash flow is cumulative and never converted to a quarter.
                if concept.startswith(('NetCash', 'Payments')):
                    start = f'{year}-01-01'
                records.append(dict(start=start, end=end, val=(values[-1] + quarter * 100) * 1_000_000,
                    filed=f'{year}-' + ('05-04' if quarter == 1 else '08-03' if quarter == 2 else '11-03'),
                    form='10-Q', accn=CIKS[ticker] + f'-{str(year)[2:]}-{quarter + 10:06d}', fy=year, fp=f'Q{quarter}'))
        facts[concept] = {'units': {'USD': records}}
    return dict(cik=int(CIKS[ticker]), entityName='Constructed exact-quarter ' + ticker,
                facts={'us-gaap': facts})


def _document(ticker):
    cik = CIKS[ticker]

    def context(identity, start, entity=cik, *, dimensional=False):
        segment = ('<x:segment><dim:explicitMember dimension="g:LegalEntityAxis">'
                   'g:SubsidiaryMember</dim:explicitMember></x:segment>') if dimensional else ''
        return (f'<x:context id="{identity}"><x:entity><x:identifier scheme="http://www.sec.gov/CIK">'
                f'{entity}</x:identifier>{segment}</x:entity><x:period><x:startDate>{start}</x:startDate>'
                f'<x:endDate>{END}</x:endDate></x:period></x:context>')

    tags = dict(revenue='RevenuesNetOfInterestExpense' if ticker == 'C' else 'RegulatedAndUnregulatedOperatingRevenue', operating_income='OperatingIncomeLoss',
                cash_from_operations='NetCashProvidedByUsedInOperatingActivities',
                capital_expenditures='PaymentsToAcquirePropertyPlantAndEquipment',
                net_interest_income='InterestIncomeExpenseNet', noninterest_income='NoninterestIncome')

    def fact(field, value, ctx, *, suffix='', unit='money'):
        return (f'<ix:nonFraction name="g:{tags[field]}" contextRef="{ctx}" unitRef="{unit}" '
                f'scale="6" decimals="-6" format="ixt:num-dot-decimal" id="{field}{suffix}">'
                f'{value:,}</ix:nonFraction>')

    amounts = []
    for field, value in VALUES[ticker].items():
        ctx = 'ytd' if field in {'cash_from_operations', 'capital_expenditures'} else 'parent-quarter'
        amounts.append(fact(field, value, ctx))
    # These plausible larger values must never overwrite the parent facts or
    # fill a missing parent field. They exercise actual context/unit filtering.
    for field in tags:
        for ctx in ('subsidiary-quarter', 'segment-quarter'):
            amounts.append(fact(field, 999999, ctx, suffix='-' + ctx))
    amounts.append(fact('capital_expenditures', 888888, 'parent-quarter', suffix='-wrong-unit', unit='shares'))
    return f'''<html xmlns="http://www.w3.org/1999/xhtml" xmlns:x="http://www.xbrl.org/2003/instance"
      xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" xmlns:ixt="http://www.xbrl.org/inlineXBRL/transformation/2020-02-12"
      xmlns:dei="http://xbrl.sec.gov/dei/2026" xmlns:g="http://fasb.org/us-gaap/2026"
      xmlns:iso="http://www.xbrl.org/2003/iso4217" xmlns:dim="http://xbrl.org/2006/xbrldi">
      <head>{context('parent-quarter', QUARTER_START)}{context('ytd', YTD_START)}
      {context('subsidiary-quarter', QUARTER_START, '0000009999')}
      {context('segment-quarter', QUARTER_START, dimensional=True)}
      <x:unit id="money"><x:measure>iso:USD</x:measure></x:unit>
      <x:unit id="shares"><x:measure>x:shares</x:measure></x:unit></head><body>
      <h1>Constructed exact-quarter {ticker} source</h1>
      <ix:nonNumeric name="dei:EntityCentralIndexKey" contextRef="parent-quarter" id="dei-cik">{cik}</ix:nonNumeric>
      <ix:nonNumeric name="dei:DocumentType" contextRef="parent-quarter" id="dei-form">10-Q</ix:nonNumeric>
      <ix:nonNumeric name="dei:DocumentPeriodEndDate" contextRef="parent-quarter" id="dei-end">{END}</ix:nonNumeric>
      <ix:nonNumeric name="dei:AmendmentFlag" contextRef="parent-quarter" id="dei-amend">false</ix:nonNumeric>
      {''.join(amounts)}</body></html>'''.encode()


def exact_quarterly_dependencies(record):
    """Return raw constructed observations, never a parsed financial verdict."""
    mapping = {str(index): dict(ticker=ticker, cik_str=int(CIKS[ticker]),
                               title='Constructed exact-quarter ' + ticker)
               for index, ticker in enumerate(TICKERS)}
    bodies = {MAPPING: json.dumps(mapping).encode(),
              'https://www.sec.gov/files/company_tickers_exchange.json': json.dumps(
                  dict(fields=['cik', 'name', 'ticker', 'exchange'],
                       data=[[row['cik_str'], row['title'], row['ticker'], 'NYSE']
                             for row in mapping.values()])).encode()}
    for ticker in TICKERS:
        cik = CIKS[ticker]
        bodies[f'https://data.sec.gov/submissions/CIK{cik}.json'] = json.dumps(_profile(ticker)).encode()
        bodies[f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'] = json.dumps(_facts(ticker)).encode()
        bodies[source_url(ticker)] = _document(ticker)
    original = deepcopy(bodies)

    def transport(url, agent):
        assert 'Synthetic' in agent
        record('sec:' + url)
        assert url in bodies, 'Unexpected exact-quarter constructed URL: ' + url
        return bodies[url], {}, url

    def held_prices(ticker, **kwargs):
        record('prices-held:' + ticker)
        return dict(ticker=ticker, status='unavailable', reason='daily_prices_unavailable')

    def held_peer_source(*args, **kwargs):
        record('peer-source-held')
        return dict(status='unavailable', reason='constructed_industry_sources_held')

    return dict(transport=transport, prices=held_prices,
                peers={name: held_peer_source for name in ('classification', 'vendor', 'industry')},
                documents={source_url(ticker): bodies[source_url(ticker)] for ticker in TICKERS},
                source_objects_unchanged=lambda: bodies == original)


def run_exact_quarterly_fixture(root):
    from src import company_research_notes, company_workbench_ui, dashboard, online_company_identity
    from src import online_company_prices, online_peer_sources, online_research_context_store
    from src import online_research_tools, online_research_tools_ui, sec_annual_history, sec_research_review_ui
    from src import online_filing_context, sec_online_quarter_evidence
    from src import self_service_research_coverage as coverage, self_service_research_coverage_ui as coverage_ui
    from src.providers.sec_company_discovery import search_sec_company_candidates

    def write_json(name, value):
        pending = root / (name + '.pending')
        pending.write_text(json.dumps(value), encoding='utf-8')
        pending.replace(root / name)

    def record(value):
        with (root / 'provider-calls.txt').open('a', encoding='utf-8') as handle:
            handle.write(value + '\n')

    fixture = exact_quarterly_dependencies(record)
    financial = sec_annual_history.fetch_sec_online_research_view
    prepare = online_research_tools_ui.prepare_online_tools
    peer = online_peer_sources.get_online_peer_valuation
    getter = coverage.get_self_service_coverage
    context_clock, coverage_clock = online_research_tools._now, coverage._now
    filing_clock = online_filing_context._now
    deps = dict(financial=financial, prices=fixture['prices'], source_fetcher=fixture['transport'],
                peer_dependencies=fixture['peers'])

    def observed_financial(ticker, **kwargs):
        result = financial(ticker, **{**kwargs, 'source_fetcher': fixture['transport'], 'observed_at': NOW})
        write_json('financial-' + ticker + '.json', result)
        return result

    def observed_prepare(ticker, bundle, state, **kwargs):
        result = prepare(ticker, bundle, state, **kwargs)
        assert fixture['source_objects_unchanged']()
        write_json('workbench-' + ticker + '.json', result)
        write_json('source-audit.json', dict(source_objects_unchanged=True,
            documents={url: sha256(body).hexdigest() for url, body in fixture['documents'].items()}))
        return result

    def observed_coverage(*args, **kwargs):
        result = getter(*args, **{**kwargs, 'as_of': NOW})
        write_json('study-view.json', result)
        return result

    def observed_peer(ticker, state, **kwargs):
        return peer(ticker, state, **{**kwargs, 'dependencies': fixture['peers'], 'as_of': NOW})

    original_connect, original_connect_ex = socket.socket.connect, socket.socket.connect_ex

    def local(function):
        def connect(sock, address):
            if isinstance(address, tuple) and address[0] not in {'127.0.0.1', '::1', 'localhost'}:
                record('unexpected-external-request')
                raise AssertionError('Constructed exact-quarter browser proof prohibits external requests')
            return function(sock, address)
        return connect

    for module in (company_research_notes, online_research_context_store, online_research_tools_ui, sec_research_review_ui):
        module.PROJECT_ROOT = root
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(socket.socket, 'connect', local(original_connect))
        patch.setattr(socket.socket, 'connect_ex', local(original_connect_ex))
        patch.setattr(online_research_tools, '_now', lambda value=None: context_clock(NOW if value is None else value))
        patch.setattr(coverage, '_now', lambda value=None: coverage_clock(NOW if value is None else value))
        patch.setattr(online_filing_context, '_now', lambda value=None: filing_clock(NOW if value is None else value))
        patch.setattr(sec_online_quarter_evidence, '_now', lambda value=None: filing_clock(NOW if value is None else value))
        patch.setattr(coverage, 'default_dependencies', lambda: deps)
        patch.setattr(coverage_ui, 'get_self_service_coverage', observed_coverage)
        patch.setattr(dashboard, 'search_sec_company_candidates', lambda query, **kwargs:
            search_sec_company_candidates(query, **{**kwargs,
                'fetcher': lambda url, agent: fixture['transport'](url, agent)[:2], 'observed_at': NOW}))
        patch.setattr(sec_annual_history, 'fetch_sec_online_research_view', observed_financial)
        patch.setattr(online_company_prices, 'fetch_online_company_prices', fixture['prices'])
        patch.setattr(online_company_identity, 'fetch_sec_company_profile', lambda *args, **kwargs:
            dict(status='unavailable', reason='constructed_listing_profile_held'))
        patch.setattr(company_workbench_ui, 'get_online_peer_valuation', observed_peer)
        patch.setattr(online_research_tools_ui, 'prepare_online_tools', observed_prepare)
        dashboard.main()
