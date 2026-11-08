"""Constructed, unapproved bank documents through the real collection/storage path."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import base64
import json
import socket

import pytest


NOW = datetime(2026, 11, 8, 4, tzinfo=timezone.utc)
BANKS = ('JPM', 'BAC', 'C')


def bank_dependencies(record):
    """Use production receipt/classification/financial/security builders, offline."""
    from src import self_service_research_coverage as coverage
    from src.online_peer_valuation import normalized_digest
    from src.sec_selected_security import KEYS, _url
    from src.sec_selected_security_policies import POLICIES
    from src.sec_security_document_set import companion_source
    from tests.test_online_peer_valuation import issuer
    from tests.test_online_us_universe import N_URL, O_URL, M_URL, E_URL
    from tests.test_sec_annual_history import _payload
    from tests.test_sec_quarterly_history import _quarter_payload

    policies = {p['ticker']: p for p in POLICIES if p['ticker'] in BANKS}
    ciks = {ticker: policies[ticker]['sec_cik'] if ticker in policies else str(1001 + index).zfill(10)
            for index, ticker in enumerate(coverage.SAMPLE)}
    symbols = {ticker: ciks[ticker] for ticker in coverage.SAMPLE}
    for ticker, policy in policies.items():
        symbols.update({symbol: ciks[ticker] for symbol in policy['issuer_symbols']})
    mapping = {str(index): dict(ticker=ticker, cik_str=int(cik), title='Constructed ' + ticker)
               for index, (ticker, cik) in enumerate(symbols.items())}
    exchange = dict(fields=['cik', 'name', 'ticker', 'exchange'],
                    data=[[row['cik_str'], row['title'], row['ticker'], 'Nasdaq'] for row in mapping.values()])
    nasdaq = 'Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares\n'
    nasdaq += ''.join(f'{ticker}|Constructed {ticker} - {"Common Stock" if ticker in coverage.SAMPLE else "Preferred Stock"}|Q|N|N|100|N|N\n'
                      for ticker in symbols)
    nasdaq += 'File Creation Time: 1106202615:41|||||||\n'
    other = ('ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol\n'
             'UNMAP|Constructed Unmapped - Common Stock|N|UNMAP|N|100|N|UNMAP\n'
             'File Creation Time: 1106202615:41|||||||\n')
    bodies = {N_URL: nasdaq.encode(), O_URL: other.encode(), M_URL: json.dumps(mapping).encode(),
              E_URL: json.dumps(exchange).encode()}
    source_documents = {}
    profiles, vendors = {}, {}
    for ticker, cik in ciks.items():
        row = issuer(ticker, cik, 30)
        if ticker in policies:
            policy = policies[ticker]
            metadata = [deepcopy(doc['metadata']) for doc in policy['documents'].values()]
            profile = dict(cik=int(cik), name='Constructed ' + ticker, entityType='operating', sic='6021',
                           fiscalYearEnd='1231', tickers=policy['issuer_symbols'],
                           exchanges=['Nasdaq'] * len(policy['issuer_symbols']),
                           filings={'recent': {key: [meta[key] for meta in metadata] for key in KEYS}})
            # Actual captured document fields, not unrelated JSON padding. These
            # large source bodies deliberately fail the reviewed policy digests:
            # retaining them must never establish a literal-common/P/E verdict.
            for role, doc in policy['documents'].items():
                url = _url(cik, doc['metadata'])
                paragraph = f'<p>Constructed {ticker} {role} filing text; no approved security or EPS evidence.</p>'.encode()
                repeat = (7 * 1024 * 1024 // len(paragraph)) if role == 'annual' else 1
                raw = b'<html><body>' + paragraph * repeat + b'</body></html>'
                bodies[url] = raw
                source_documents[url] = raw
                companion = companion_source(doc, url)
                if companion:
                    _, companion_url = companion
                    raw = f'<html><body>Constructed {ticker} {role} companion; evidence remains unapproved.</body></html>'.encode()
                    bodies[companion_url] = raw
                    source_documents[companion_url] = raw
            annual = policy['documents']['annual']['metadata']
            vendor = row['vendor']
            filing = vendor['payload']['filings'][0]
            accession = annual['accessionNumber']
            filing.update(date=annual['filingDate'],
                          edgarUrl=f'https://finance.yahoo.com/sec-filing/{ticker}/{accession}_{int(cik)}',
                          exhibits={'10-K': f'https://cdn.yahoofinance.com/prod/sec-filings/{cik}/{accession.replace("-", "")}/{annual["primaryDocument"]}'})
        else:
            profile = row['profile']['payload']
            profile.update(name='Constructed ' + ticker, fiscalYearEnd='1231')
            profile['filings']['recent'].update(acceptanceDateTime=['2026-02-01T12:00:00Z'], isInlineXBRL=[1], isXBRL=[1])
            annual = {key: value[0] for key, value in profile['filings']['recent'].items()}
            vendor = row['vendor']
        vendor['observed_at'] = NOW.isoformat()
        vendor['payload']['info'].update(industryKey='banks-regional' if ticker in BANKS else 'semiconductors',
                                        sectorKey='financial-services' if ticker in BANKS else 'technology',
                                        regularMarketTime=int(datetime(2026, 11, 6, 21, tzinfo=timezone.utc).timestamp()))
        vendor['normalized_sha256'] = normalized_digest(vendor['payload'])
        vendors[ticker] = vendor
        profiles[ticker] = profile
        bodies[f'https://data.sec.gov/submissions/CIK{cik}.json'] = json.dumps(profile).encode()
        facts = _payload()
        quarterly = _quarter_payload()
        for concept, fact in quarterly['facts']['us-gaap'].items():
            facts['facts']['us-gaap'][concept]['units']['USD'] += fact['units']['USD']
        if ticker in BANKS:
            facts['facts']['us-gaap']['RevenuesNetOfInterestExpense'] = facts['facts']['us-gaap'].pop('Revenues')
        facts.update(cik=int(cik), entityName='Constructed ' + ticker)
        for fact in facts['facts']['us-gaap'].values():
            for records in fact['units'].values():
                for value in records:
                    value['accn'] = value['accn'].replace('0000001234', cik)
                    if value['form'] == '10-K':
                        value.update(accn=annual['accessionNumber'], filed=annual['filingDate'])
        facts['facts']['us-gaap'].update(row['facts']['payload']['facts']['us-gaap'])
        eps = facts['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]
        eps.update(accn=annual['accessionNumber'], filed=annual['filingDate'])
        bodies[f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'] = json.dumps(facts).encode()

    def transport(url, agent):
        assert 'Synthetic' in agent
        record('source:' + url)
        if url not in bodies:
            raise AssertionError('Unexpected constructed bank source URL: ' + url)
        return bodies[url], {}, url

    def prices(ticker, **kwargs):
        record('prices:' + ticker)
        result = issuer(ticker, ciks[ticker], 30)['prices']
        result.update(observed_at=NOW.isoformat(), instrument_type='EQUITY', last_price_date='2026-11-06')
        result['bars'][-1]['date'] = '2026-11-06'
        return result

    def vendor(ticker, **kwargs):
        record('vendor:' + ticker)
        return deepcopy(vendors[ticker])

    def industry(key, sector, **kwargs):
        record('industry:' + key)
        payload = dict(key=key, sector=sector, symbols=list(BANKS) if key == 'banks-regional' else [])
        return dict(status='observed', source_ref=f'https://finance.yahoo.com/sectors/{sector}/{key}/',
                    observed_at=NOW.isoformat(), payload=payload, normalized_sha256=normalized_digest(payload))

    return dict(source_fetcher=transport, prices=prices,
                peer_dependencies=dict(vendor=vendor, industry=industry)), source_documents


def run_bank_peer_packet_fixture(root):
    from src import company_research_notes, dashboard, online_research_context_store, online_research_tools_ui
    from src import sec_research_review_ui, self_service_research_coverage as coverage
    from src import self_service_research_coverage_ui as coverage_ui

    def record(value):
        with (root / 'provider-calls.txt').open('a', encoding='utf-8') as handle:
            handle.write(value + '\n')

    dependencies, documents = bank_dependencies(record)
    getter = coverage.get_self_service_coverage

    def write_json(name, value):
        pending = root / (name + '.pending')
        pending.write_text(json.dumps(value), encoding='utf-8')
        pending.replace(root / name)

    def write_audit(state):
        private = state.get(coverage.SESSION_KEY, {})
        audit = dict(classification_count=len(private.get('classifications', {})), banks={})
        for ticker in BANKS:
            packet = private.get('packets', {}).get(ticker)
            if not packet:
                continue
            expanded = coverage._expand_peer(packet.get('peer_packet'), private)
            bank = dict(stored_packet_bytes=len(coverage._bytes(packet)),
                        stored_peer_keys=sorted(packet.get('peer_packet') or {}), documents=[])
            if expanded and expanded.get('collection'):
                bank['expanded_peer_bytes'] = len(coverage._bytes(expanded))
                for issuer in expanded['collection']['issuers']:
                    security = issuer.get('selected_security_evidence') or {}
                    for role, doc in security.get('documents', {}).items():
                        for label, receipt in [(role, doc)] + ([(role + '_companion', doc['companion'])] if 'companion' in doc else []):
                            raw = base64.b64decode(receipt['payload_raw_base64'], validate=True)
                            original = documents[receipt['source_url']]
                            bank['documents'].append(dict(role=label, source_url=receipt['source_url'],
                                bytes=len(raw), exact_source_match=raw == original,
                                sha256=sha256(raw).hexdigest(), receipt_sha256=receipt['payload_sha256']))
            audit['banks'][ticker] = bank
        write_json('retention-audit.json', audit)

    def observed_getter(state, **kwargs):
        if coverage.SESSION_KEY not in state:
            # Public explicit actions only: preserve the canonical sample order
            # and its twelve-company denominator, with all three banks reached.
            for _ in range(6):
                getter(state, inspect_requested=True, user_agent='Synthetic bank contact@example.com',
                       dependencies=dependencies, as_of=NOW)
        result = getter(state, **{**kwargs, 'dependencies': dependencies, 'as_of': NOW})
        write_audit(state)
        write_json('study-view.json', result)
        return result

    original_connect, original_connect_ex = socket.socket.connect, socket.socket.connect_ex

    def local(function):
        def connect(sock, address):
            if isinstance(address, tuple) and address[0] not in {'127.0.0.1', '::1', 'localhost'}:
                record('unexpected-external-request')
                raise AssertionError('Constructed bank browser proof prohibits external requests')
            return function(sock, address)
        return connect

    for module in (company_research_notes, online_research_context_store, online_research_tools_ui, sec_research_review_ui):
        module.PROJECT_ROOT = root
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(socket.socket, 'connect', local(original_connect))
        patch.setattr(socket.socket, 'connect_ex', local(original_connect_ex))
        patch.setattr(coverage_ui, 'get_self_service_coverage', observed_getter)
        dashboard.main()
