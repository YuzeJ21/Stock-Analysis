"""A normal SEC filing refresh needs no company policy or prepared input file."""
import json
from datetime import datetime, timezone

from tests.test_sec_annual_history import _payload


NOW = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)
PROFILE = 'https://data.sec.gov/submissions/CIK0000001234.json'


def _profile():
    return {'cik': '0000001234', 'name': 'Fictional Company', 'sic': '3674',
            'entityType': 'operating', 'fiscalYearEnd': '1231', 'tickers': ['FICT'],
            'filings': {'recent': {
                'accessionNumber': ['0000001234-26-000001'], 'form': ['10-K'],
                'reportDate': ['2025-12-31'], 'filingDate': ['2026-03-01'],
                'acceptanceDateTime': ['2026-03-01T16:00:00Z'],
                'primaryDocument': ['fict-20251231.htm'],
            }}}


def _fetcher(*, profile_failure=False):
    calls = []
    def fetch(url, _agent):
        calls.append(url)
        if url == PROFILE:
            if profile_failure:
                raise TimeoutError('Constructed independent source failure')
            body = _profile()
        elif 'companyfacts/' in url:
            body = _payload()
        else:
            body = {'0': {'ticker': 'FICT', 'cik_str': 1234}}
        return json.dumps(body).encode(), {}, url
    return calls, fetch


def test_generic_refresh_independently_checks_latest_filing_without_csv(monkeypatch):
    from src.sec_annual_history import fetch_sec_online_research_view
    import pandas as pd
    monkeypatch.setattr(pd, 'read_csv', lambda *_a, **_k: (_ for _ in ()).throw(AssertionError('CSV read')))
    calls, fetch = _fetcher()
    view = fetch_sec_online_research_view('FICT', user_agent='Synthetic contact',
                                        source_fetcher=fetch, observed_at=NOW)
    assert calls.count(PROFILE) == 1
    assert len(calls) == 3
    assert view['filing_inventory']['latest']['annual']['accession'] == '0000001234-26-000001'
    assert view['filing_coverage']['current']['annual']['status'] == 'corroborated'
    assert view['annual_history']['periods'][-1]['revenue'] == 150
    assert view['earnings_components']['status'] != 'approved'


def test_profile_outage_keeps_observed_financial_history_but_withholds_current_claim():
    from src.sec_annual_history import fetch_sec_online_research_view
    calls, fetch = _fetcher(profile_failure=True)
    view = fetch_sec_online_research_view('FICT', user_agent='Synthetic contact',
                                        source_fetcher=fetch, observed_at=NOW)
    assert calls.count(PROFILE) == 1
    assert view['annual_history']['periods'][-1]['revenue'] == 150
    assert view['filing_inventory']['status'] == 'withheld'
    assert view['filing_coverage']['current']['annual']['status'] == 'withheld'


def test_companyfacts_outage_still_detects_independent_latest_filing():
    from src.sec_annual_history import fetch_sec_online_research_view
    calls = []
    def fetch(url, _agent):
        calls.append(url)
        if 'companyfacts/' in url:raise TimeoutError('Constructed facts outage')
        body = _profile() if url == PROFILE else {'0':{'ticker':'FICT','cik_str':1234}}
        return json.dumps(body).encode(), {}, url
    view = fetch_sec_online_research_view('FICT',user_agent='Synthetic contact',source_fetcher=fetch,observed_at=NOW)
    assert calls.count(PROFILE) == 1
    assert view['filing_inventory']['latest']['annual']['period_end'] == '2025-12-31'
    assert view['filing_coverage']['current']['annual']['status'] != 'corroborated'
    assert view['earnings_components']['status'] == 'withheld'


def test_later_structured_facts_unlock_new_filing_without_company_specific_policy():
    from copy import deepcopy
    from src.sec_annual_history import fetch_sec_online_research_view
    from src.online_research_tools import build_online_research_context, run_online_scenario
    payload = _payload()
    pending = deepcopy(payload)
    for fact in pending['facts']['us-gaap'].values():
        fact['units']['USD'] = [row for row in fact['units']['USD'] if row['end'] != '2025-12-31']
    active = {'payload':pending}
    def fetch(url, _agent):
        body = _profile() if url == PROFILE else active['payload'] if 'companyfacts/' in url else {'0':{'ticker':'FICT','cik_str':1234}}
        return json.dumps(body).encode(), {}, url
    def refresh():
        view = fetch_sec_online_research_view('FICT',user_agent='Synthetic contact',source_fetcher=fetch,observed_at=NOW)
        return build_online_research_context(view,{},ticker='FICT',profile_key='synthetic',as_of=NOW)
    before = refresh()
    assert before['filing_coverage']['current']['annual']['status'] == 'facts_pending'
    assert before['scenario_base']['revenue'] is None
    active['payload'] = payload
    after = refresh()
    assert after['filing_coverage']['current']['annual']['status'] == 'corroborated'
    assert after['scenario_base']['revenue'] == 150
    assert after['source_revision'] != before['source_revision']
    result = run_online_scenario(after,dict(revenue_growth=.08,fcf_margin=.15,wacc=.10,terminal_growth=.02,forecast_years=5))
    assert result['status'] == 'calculated'
    assert after['saved_readiness_promoted'] is False
