"""Constructed bank sources through production observation, proof and save paths."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import socket

import pytest


BANKS = ('JPM', 'BAC', 'C')
CIKS = dict(JPM='0000019617', BAC='0000070858', C='0000831001', WFC='0000072971', GAP='0000001009')
NOW = datetime(2026, 11, 8, 4, tzinfo=timezone.utc)


def snapshot_dependencies(record, now):
    """Approve only exact constructed source bytes, never a computed verdict."""
    from src.online_company_identity import fetch_sec_company_profile
    from src.online_company_prices import fetch_online_company_prices
    from src.online_peer_sec_history import fetch_vendor_history_match
    from src.online_peer_valuation import normalized_digest
    from src.online_sec_receipt import fetch_sec_json_receipt
    from src.sec_selected_security import fetch_selected_security_evidence, _url
    from src.security_classification import fetch_classification
    from tests.document_set_fixtures import document_set_fixture
    from tests.selected_security_fixtures import fixture
    from tests.test_online_peer_valuation import issuer
    from tests.test_online_us_universe import N_URL, O_URL, M_URL, E_URL
    from tests.test_sec_annual_history import _payload
    from tests.test_sec_quarterly_history import _quarter_payload

    bodies, policies, vendors, prices = {}, [], {}, {}
    symbols = {symbol: cik for ticker, cik in CIKS.items() for symbol in (ticker, ticker + '-P')}
    mapping = {str(index): dict(ticker=ticker, cik_str=int(cik), title='Constructed ' + ticker)
               for index, (ticker, cik) in enumerate(symbols.items())}
    bodies[M_URL] = json.dumps(mapping).encode()
    bodies[E_URL] = json.dumps(dict(fields=['cik', 'name', 'ticker', 'exchange'],
        data=[[row['cik_str'], row['title'], row['ticker'], 'Nasdaq'] for row in mapping.values()])).encode()
    nasdaq = 'Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares\n'
    nasdaq += ''.join(f'{ticker}|Constructed {ticker} - {"Preferred Stock" if ticker.endswith("-P") else "Common Stock"}|Q|N|N|100|N|N\n' for ticker in symbols)
    bodies[N_URL] = (nasdaq + 'File Creation Time: 1106202615:41|||||||\n').encode()
    bodies[O_URL] = ('ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol\n'
        'UNMAP|Constructed Unmapped - Common Stock|N|UNMAP|N|100|N|UNMAP\n'
        'File Creation Time: 1106202615:41|||||||\n').encode()
    source_documents = {}
    for index, (ticker, cik) in enumerate(CIKS.items()):
        policy, original, _, raw = (document_set_fixture('financial') if ticker == 'JPM' else
            document_set_fixture('cover') if ticker == 'C' else fixture())
        policy = json.loads(json.dumps(policy).replace('FICT', ticker).replace('0000001001', cik).replace('FP', ticker + '-P'))
        policy['policy_id'] = 'constructed-browser-' + ticker.lower() + '-v1'
        policy['issuer_symbols'] = sorted(policy['issuer_symbols'])
        for role, doc in policy['documents'].items():
            for companion in (False, True) if 'companion' in doc else (False,):
                target = doc['companion'] if companion else doc
                body = raw[role + '-companion' if companion else role].replace(b'FICT', ticker.encode()).replace(b'0000001001', cik.encode())
                if b'id="symbol"' in body:
                    # Preserve a literal non-common cover row as independent evidence.
                    end = doc['metadata']['reportDate']
                    extra = (f'<x:context id="preferred"><x:entity><x:identifier scheme="http://www.sec.gov/CIK">{cik}</x:identifier></x:entity>'
                        f'<x:period><x:startDate>{end}</x:startDate><x:endDate>{end}</x:endDate></x:period></x:context>'
                        f'<ix:nonNumeric id="preferred-title" name="dei:Security12bTitle" contextRef="preferred">Preferred Stock</ix:nonNumeric>'
                        f'<ix:nonNumeric id="preferred-symbol" name="dei:TradingSymbol" contextRef="preferred">{ticker}-P</ix:nonNumeric>'
                        '<ix:nonNumeric id="preferred-exchange" name="dei:SecurityExchangeName" contextRef="preferred">Nasdaq</ix:nonNumeric>').encode()
                    body = body.replace(b'</html>', extra + b'</html>')
                target['sha256'] = sha256(body).hexdigest()
                url = _url(cik, doc['metadata'])
                if companion:
                    url = url.rsplit('/', 1)[0] + '/' + target['primaryDocument']
                bodies[url] = source_documents[url] = body
        policies.append(policy)
        row = issuer(ticker, cik, (30, 20, 25, 40, 15)[index])
        profile = json.loads(json.dumps(original['profile']['payload']).replace('FICT', ticker).replace('0000001001', cik).replace('FP', ticker + '-P'))
        profile.update(cik=int(cik), name='Constructed ' + ticker, sic='6021', fiscalYearEnd='1231',
                       tickers=policy['issuer_symbols'], exchanges=['Nasdaq'] * len(policy['issuer_symbols']))
        bodies[f'https://data.sec.gov/submissions/CIK{cik}.json'] = json.dumps(profile).encode()
        annual = policy['documents']['annual']['metadata']
        facts = _payload()
        quarterly = _quarter_payload()
        for concept, fact in quarterly['facts']['us-gaap'].items():
            facts['facts']['us-gaap'][concept]['units']['USD'] += fact['units']['USD']
        facts['facts']['us-gaap']['RevenuesNetOfInterestExpense'] = facts['facts']['us-gaap'].pop('Revenues')
        facts.update(cik=int(cik), entityName='Constructed ' + ticker)
        for fact in facts['facts']['us-gaap'].values():
            for records in fact['units'].values():
                for value in records:
                    value['accn'] = value['accn'].replace('0000001234', cik)
                    if value['form'] == '10-K':
                        value.update(accn=annual['accessionNumber'], filed=annual['filingDate'])
        facts['facts']['us-gaap'].update(deepcopy(row['facts']['payload']['facts']['us-gaap']))
        if ticker == 'GAP':
            facts['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]['val'] = 2
        bodies[f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'] = json.dumps(facts).encode()
        vendor = row['vendor']
        vendor['observed_at'] = now.isoformat()
        vendor['payload']['info'].update(industryKey='banks-regional', sectorKey='financial-services',
            regularMarketTime=int(datetime(2026, 11, 6, 21, tzinfo=timezone.utc).timestamp()))
        vendor['normalized_sha256'] = normalized_digest(vendor['payload'])
        vendors[ticker] = vendor
        multiple = row['prices']['bars'][-1]['close']
        prices[ticker] = dict(chart=dict(error=None, result=[dict(meta=dict(symbol=ticker,
            currency='USD', instrumentType='EQUITY', exchangeName='NMS', fullExchangeName='NasdaqGS',
            exchangeTimezoneName='America/New_York'),
            timestamp=[int(datetime(2025, 10, 31, 14, tzinfo=timezone.utc).timestamp()),
                       int(datetime(2026, 11, 6, 14, tzinfo=timezone.utc).timestamp())],
            indicators=dict(quote=[dict(open=[multiple]*2, high=[multiple]*2, low=[multiple]*2,
                close=[multiple]*2, volume=[100]*2)]), events=dict(splits={}))]))

    original_sources = deepcopy(bodies)

    def transport(url, agent):
        assert 'Synthetic' in agent
        record('source:' + url)
        assert url in bodies, 'Unexpected constructed bank source: ' + url
        return bodies[url], {}, url

    def price(ticker, **kwargs):
        def fetch(url):
            record('prices:' + url)
            return json.dumps(prices[ticker]).encode(), url
        return fetch_online_company_prices(ticker, **{**kwargs, 'fetcher': fetch, 'observed_at': now})

    def vendor(ticker, **kwargs):
        record('vendor:' + ticker)
        return deepcopy(vendors[ticker])

    def industry(key, sector, **kwargs):
        record('industry:' + key)
        payload = dict(key=key, sector=sector, symbols=list(CIKS))
        return dict(status='observed', source_ref=f'https://finance.yahoo.com/sectors/{sector}/{key}/',
            observed_at=now.isoformat(), payload=payload, normalized_sha256=normalized_digest(payload))

    deps = dict(classification=lambda **kwargs: fetch_classification(**{**kwargs, 'fetcher': transport}),
        vendor=vendor, industry=industry, prices=price,
        sec=lambda *args, **kwargs: fetch_sec_json_receipt(*args, **{**kwargs, 'fetcher': transport}),
        security=lambda *args, **kwargs: fetch_selected_security_evidence(*args, **{**kwargs, 'fetcher': transport}),
        history=lambda *args, **kwargs: fetch_vendor_history_match(*args, **{**kwargs, 'fetcher': transport}))
    return dict(policies=policies, dependencies=deps, transport=transport, prices=price,
        profile=lambda *args, **kwargs: fetch_sec_company_profile(*args, **{**kwargs, 'fetcher': transport, 'observed_at': now}),
        documents=source_documents, sources_unchanged=lambda: bodies == original_sources)


def run_bank_research_snapshot_fixture(root):
    from src import company_research_notes, company_workbench_ui, dashboard, online_company_identity
    from src import online_company_prices, online_peer_sources, online_research_context_store, online_research_tools
    from src import online_research_tools_ui, sec_annual_history, sec_research_review_ui, sec_selected_security
    from src.providers.sec_company_discovery import search_sec_company_candidates

    def write_json(name, value):
        pending = root / (name + '.pending')
        pending.write_text(json.dumps(value), encoding='utf-8')
        pending.replace(root / name)

    def record(value):
        with (root / 'provider-calls.txt').open('a', encoding='utf-8') as handle:
            handle.write(value + '\n')

    # Freeze only the harness clock. Every source parser, eligibility check,
    # context producer and immutable store operation remains production code.
    now = NOW
    fixture = snapshot_dependencies(record, now)
    financial, prepare, peer = sec_annual_history.fetch_sec_online_research_view, online_research_tools_ui.prepare_online_tools, online_peer_sources.get_online_peer_valuation
    context_clock = online_research_tools._now

    def observed_prepare(ticker, bundle, state, **kwargs):
        original = deepcopy(state.get(online_peer_sources.SESSION_KEY))
        result = prepare(ticker, bundle, state, **kwargs)
        assert state.get(online_peer_sources.SESSION_KEY) == original
        assert fixture['sources_unchanged']()
        write_json('workbench-' + ticker + '.json', result)
        write_json('source-audit.json', dict(source_objects_unchanged=True,
            documents={url: sha256(body).hexdigest() for url, body in fixture['documents'].items()}))
        return result

    def observed_peer(ticker, state, **kwargs):
        result = peer(ticker, state, **{**kwargs, 'dependencies': fixture['dependencies'], 'as_of': now})
        write_json('peer-' + ticker + '.json', result)
        return result

    original_connect, original_connect_ex = socket.socket.connect, socket.socket.connect_ex

    def local(function):
        def connect(sock, address):
            if isinstance(address, tuple) and address[0] not in {'127.0.0.1', '::1', 'localhost'}:
                record('unexpected-external-request')
                raise AssertionError('Constructed bank research proof prohibits external requests')
            return function(sock, address)
        return connect

    for module in (company_research_notes, online_research_context_store, online_research_tools_ui, sec_research_review_ui):
        module.PROJECT_ROOT = root
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(socket.socket, 'connect', local(original_connect))
        patch.setattr(socket.socket, 'connect_ex', local(original_connect_ex))
        patch.setattr(sec_selected_security, 'POLICIES', tuple(fixture['policies']))
        patch.setattr(online_research_tools, '_now', lambda value=None: context_clock(now if value is None else value))
        patch.setattr(dashboard, 'search_sec_company_candidates', lambda query, **kwargs:
            search_sec_company_candidates(query, **{**kwargs,
                'fetcher': lambda url, agent: fixture['transport'](url, agent)[:2], 'observed_at': now}))
        patch.setattr(sec_annual_history, 'fetch_sec_online_research_view', lambda ticker, **kwargs:
            financial(ticker, **{**kwargs, 'source_fetcher': fixture['transport'], 'observed_at': now}))
        patch.setattr(online_company_prices, 'fetch_online_company_prices', fixture['prices'])
        patch.setattr(online_company_identity, 'fetch_sec_company_profile', fixture['profile'])
        patch.setattr(company_workbench_ui, 'get_online_peer_valuation', observed_peer)
        patch.setattr(online_research_tools_ui, 'prepare_online_tools', observed_prepare)
        dashboard.main()
