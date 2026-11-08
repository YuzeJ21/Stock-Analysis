"""Constructed SEC transports for cross-industry dashboard browser evidence."""
from datetime import datetime, timezone
import json
import socket

import pytest


def run_cross_industry_fixture(root):
    from src import company_research_notes, company_workbench_ui, dashboard, online_company_identity
    from src import online_company_prices, online_research_context_store, online_research_tools_ui
    from src import sec_annual_history, sec_research_review_ui, self_service_research_coverage as coverage
    from src import self_service_research_coverage_ui as coverage_ui
    from src.online_peer_sources import SESSION_KEY as PEER_KEY
    from tests.test_online_company_search_view import _result
    from tests.test_sec_annual_history import _payload
    from tests.test_sec_quarterly_history import _quarter_payload
    from tests.test_sec_industry_financials import _foreign_payload

    ciks = {ticker: str(1001 + index).zfill(10) for index, ticker in enumerate(coverage.SAMPLE)}
    by_cik = {value: ticker for ticker, value in ciks.items()}
    banks, utilities = {'JPM', 'BAC', 'C'}, {'DUK', 'SO', 'NEE'}

    def record(value):
        with (root / 'provider-calls.txt').open('a', encoding='utf-8') as handle:
            handle.write(value + '\n')

    def profile(ticker):
        cik = ciks[ticker]
        if ticker == 'SAP':
            rows = [('20-F', '2025-12-31', '2026-03-01', cik + '-26-000001'),
                    ('6-K', '2026-08-01', '2026-08-01', cik + '-26-000002')]
        else:
            rows = [('10-K', '2025-12-31', '2026-02-01', cik + '-26-000001')]
            rows += [('10-Q', end, filed, cik + f'-25-00000{index+1}') for index, (end, filed) in enumerate([
                ('2025-03-31', '2025-05-01'), ('2025-06-30', '2025-08-01'), ('2025-09-30', '2025-11-01')])]
            if ticker == 'DUK':
                rows.append(('10-Q', '2026-09-30', '2026-11-01', cik + '-26-000002'))
        keys = ('form', 'reportDate', 'filingDate', 'accessionNumber', 'acceptanceDateTime', 'primaryDocument')
        values = [(*row, row[2] + 'T12:00:00Z', 'annual.htm' if row[0] in {'10-K', '20-F'} else 'quarter.htm') for row in rows]
        return dict(cik=int(cik), name='Constructed ' + ticker, tickers=[ticker], exchanges=['Nasdaq'],
            sic='6021' if ticker in banks else '4911' if ticker in utilities else '7372' if ticker == 'SAP' else '3674',
            entityType='other' if ticker == 'SAP' else 'operating', fiscalYearEnd='1231',
            filings={'recent': {key: [row[index] for row in values] for index, key in enumerate(keys)}})

    def facts(ticker):
        cik = ciks[ticker]
        if ticker == 'SAP':
            body = _foreign_payload()
        else:
            body = _payload()
            quarterly = _quarter_payload()
            for concept, fact in quarterly['facts']['us-gaap'].items():
                body['facts']['us-gaap'][concept]['units']['USD'] += fact['units']['USD']
            revenue = 'RevenuesNetOfInterestExpense' if ticker in banks else 'RegulatedAndUnregulatedOperatingRevenue' if ticker in utilities else None
            if revenue:
                body['facts']['us-gaap'][revenue] = body['facts']['us-gaap'].pop('Revenues')
        body['cik'] = int(cik)
        body['entityName'] = 'Constructed ' + ticker
        for taxonomy in body['facts'].values():
            for fact in taxonomy.values():
                for rows in fact['units'].values():
                    for row in rows:
                        row['accn'] = row['accn'].replace('0000001234', cik)
                        if row['form'] == '10-K':
                            row['filed'] = '2026-02-01'
        return body

    def transport(url, agent):
        assert 'Synthetic' in agent
        record('sec:' + url)
        if url == 'https://www.sec.gov/files/company_tickers.json':
            body = {str(index): dict(ticker=ticker, cik_str=int(ciks[ticker]), title='Constructed ' + ticker)
                    for index, ticker in enumerate(coverage.SAMPLE)}
        else:
            cik = next((cik for cik in by_cik if 'CIK' + cik in url), None)
            if cik is None:
                raise AssertionError('Unexpected constructed source URL: ' + url)
            ticker = by_cik[cik]
            if url == f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json':
                if ticker == 'QCOM':
                    raise OSError('Constructed independent Companyfacts source outage')
                body = facts(ticker)
            elif url == f'https://data.sec.gov/submissions/CIK{cik}.json':
                body = profile(ticker)
            else:
                raise AssertionError('Unexpected constructed source URL: ' + url)
        return json.dumps(body).encode(), {}, url

    def held_prices(ticker, **kwargs):
        record('prices-held:' + ticker)
        return dict(ticker=ticker, status='unavailable', reason='daily_prices_unavailable')

    def peer_dependency(*args, **kwargs):
        record('study-peer-held')
        return dict(status='unavailable', reason='constructed_industry_sources_held')

    production_financial = sec_annual_history.fetch_sec_online_research_view
    deps = dict(financial=production_financial, prices=held_prices, source_fetcher=transport,
                peer_dependencies={'classification': peer_dependency, 'vendor': peer_dependency,
                                   'industry': peer_dependency})

    def workbench_financial(ticker, *, user_agent, **kwargs):
        record('workbench-financial:' + ticker)
        return production_financial(ticker, user_agent=user_agent, source_fetcher=transport,
                                    observed_at=datetime.now(timezone.utc))

    def search(query, *, user_agent):
        assert query in ciks
        record('search:' + query)
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        return {**_result(candidates=[dict(ticker=query, cik=ciks[query], title='Constructed ' + query,
                                         exchange='Nasdaq', ambiguous=False)]),
                'query': query, 'observed_at': now, 'source_last_modified': now}

    def held_profile(cik, **kwargs):
        record('listing-profile-held:' + cik)
        return dict(status='unavailable', reason='sec_profile_unavailable')

    def held_workbench_peer(ticker, state, *, refresh_requested, expected_cik, **kwargs):
        if refresh_requested:
            record('workbench-peer-held:' + ticker)
            state[PEER_KEY] = dict(ticker=ticker, sec_cik=expected_cik, status='withheld',
                reason='same_day_completed_price_and_three_references_required', peer_count=0)
        return state.get(PEER_KEY, {'status': 'not_requested'})

    getter, prepare = coverage.get_self_service_coverage, online_research_tools_ui.prepare_online_tools
    original_radio = dashboard.st.radio

    def observed_radio(*args, **kwargs):
        result = original_radio(*args, **kwargs)
        if kwargs.get('key') == 'self-service-coverage-company':
            from streamlit.elements.lib.form_utils import current_form_id
            with (root / 'radio-events.jsonl').open('a', encoding='utf-8') as handle:
                handle.write(json.dumps(dict(returned=result,
                    state=dashboard.st.session_state.get('self-service-coverage-company'),
                    form_id=current_form_id(dashboard.st._main),
                    at=datetime.now(timezone.utc).isoformat())) + '\n')
        return result

    def observed_getter(*args, **kwargs):
        result = getter(*args, **kwargs)
        (root / 'study-view.json').write_text(json.dumps(result), encoding='utf-8')
        return result

    def observed_prepare(ticker, *args, **kwargs):
        result = prepare(ticker, *args, **kwargs)
        (root / ('workbench-' + ticker + '.json')).write_text(json.dumps(result), encoding='utf-8')
        return result

    original_connect, original_connect_ex = socket.socket.connect, socket.socket.connect_ex
    def local(function):
        def connect(sock, address):
            if isinstance(address, tuple) and address[0] not in {'127.0.0.1', '::1', 'localhost'}:
                record('unexpected-external-request')
                raise AssertionError('Constructed browser proof prohibits external source requests')
            return function(sock, address)
        return connect

    for module in (company_research_notes, online_research_context_store, online_research_tools_ui, sec_research_review_ui):
        module.PROJECT_ROOT = root
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(socket.socket, 'connect', local(original_connect))
        patch.setattr(socket.socket, 'connect_ex', local(original_connect_ex))
        patch.setattr(coverage, 'default_dependencies', lambda: deps)
        patch.setattr(coverage_ui, 'get_self_service_coverage', observed_getter)
        patch.setattr(dashboard.st, 'radio', observed_radio)
        patch.setattr(dashboard, 'search_sec_company_candidates', search)
        patch.setattr(sec_annual_history, 'fetch_sec_online_research_view', workbench_financial)
        patch.setattr(online_company_prices, 'fetch_online_company_prices', held_prices)
        patch.setattr(online_company_identity, 'fetch_sec_company_profile', held_profile)
        patch.setattr(company_workbench_ui, 'get_online_peer_valuation', held_workbench_peer)
        patch.setattr(online_research_tools_ui, 'prepare_online_tools', observed_prepare)
        dashboard.main()
