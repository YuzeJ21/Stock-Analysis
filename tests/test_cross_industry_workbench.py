"""Native statements and exact filing qualification in the real tool builder."""
from copy import deepcopy
from datetime import datetime, timezone

from tests.test_sec_industry_financials import _foreign_view, _foreign_payload

NOW = datetime(2026, 10, 30, 18, tzinfo=timezone.utc)


def test_native_ifrs_history_is_not_replaced_by_convenience_usd_history():
    from tests.test_online_research_tools import financial
    from src.online_research_tools import build_online_research_context
    from src.online_filing_context import build_filing_inventory
    view = financial()
    native = _foreign_view()
    view['foreign_financials'] = native['foreign_financials']
    view['foreign_financials']['payload_sha256'] = view['companyfacts_identity']['payload_sha256']
    view['foreign_financials']['observed_at'] = view['companyfacts_identity']['observed_at']
    for kind in ('annual','quarterly','interim'):
        for row in view['foreign_financials'][kind]:
            for field in row['fields'].values():
                field['payload_sha256'] = view['companyfacts_identity']['payload_sha256']
                field['observed_at'] = view['companyfacts_identity']['observed_at']
    profile = dict(cik=1234,tickers=['FICT'],name='Synthetic foreign issuer',sic='3571',entityType='other',fiscalYearEnd='1231',
        filings={'recent':dict(form=['20-F','6-K'],reportDate=['2025-12-31','2026-08-01'],
            filingDate=['2026-03-01','2026-08-01'],accessionNumber=['0000001234-26-000001','0000001234-26-000002'],
            acceptanceDateTime=['2026-03-01T12:00:00Z','2026-08-01T12:00:00Z'],primaryDocument=['annual.htm','quarter.htm'])})
    view['filing_inventory'] = build_filing_inventory(dict(status='ready',payload=profile,
        source_url='https://data.sec.gov/submissions/CIK0000001234.json',observed_at=NOW.isoformat(),payload_sha256='d'*64),
        ticker='FICT',expected_cik='0000001234',as_of=NOW)
    original = deepcopy(view)
    result = build_online_research_context(view,{},ticker='FICT',profile_key='personal',as_of=NOW)
    annual = [row for row in result['business_trend']['periods'] if row['kind']=='annual']
    assert annual and {row['currency'] for row in annual} == {'EUR'}
    assert annual[-1]['fields']['revenue']['value'] == 100
    from src.company_workbench_sections import workbench_projection
    from src.company_answer_summary import _comparable_revenue
    projection = workbench_projection('FICT',view,{})
    assert projection['unit'] == 'EUR'
    assert _comparable_revenue(view,'2025-12-31','annual','EUR') is None
    assert result['scenario_base']['status'] != 'available'  # SEC entity type remains unqualified.
    assert view == original


def test_filing_status_uses_exact_fact_duration_not_event_report_date():
    from src.online_research_tools_ui import filing_status_html
    context = {'filing_coverage':{'current':{'interim':{'status':'withheld',
        'anchor':{'period_end':'2026-06-30','report_date':'2026-08-01'}}}}}
    html = filing_status_html(context)
    assert 'Interim 2026-06-30: withheld' in html and '2026-08-01' not in html


def test_unjoined_interim_statement_does_not_gain_usable_metrics():
    from src.online_research_tools import build_online_research_context
    view = _foreign_view()
    result = build_online_research_context(view,{},ticker='FICT',profile_key='personal',expected_cik='0000001234',as_of=NOW)
    interim = [row for row in result['business_trend']['metrics'] if row['period_kind']=='interim']
    assert interim and all(row['value'] is None for row in interim)


def test_historical_exact_filing_stays_historical_when_newer_period_is_known():
    from src.online_research_tools import _trend
    view = _foreign_view()
    rows = view['foreign_financials']['interim']
    assert rows
    end = rows[-1]['period_end']
    coverage = dict(periods={'interim':{end:{'status':'corroborated'}}},
        current={'interim':{'status':'withheld','reason':'newer_reporting_period_known',
            'anchor':{'period_end':end}}})
    trend = _trend([('interim', rows, 'EUR')], coverage)
    assert not any(row['current'] for row in trend['periods'])
    assert any(metric['status']=='calculated' for metric in trend['metrics'])


def test_missing_peer_attempt_is_distinct_from_failed_source():
    from tests.test_online_research_tools import financial
    from src.online_research_tools import build_online_research_context
    from src.online_peer_sources import _cache
    view = financial()
    missing = build_online_research_context(view,{},ticker='FICT',profile_key='personal',as_of=NOW)
    assert missing['peer_read_through']['status'] == 'not_requested'
    state = {}
    cache = _cache(state,'FICT',None,'vendor_context_source_unavailable',NOW)
    failed = build_online_research_context(view,{},cache,ticker='FICT',profile_key='personal',as_of=NOW)
    assert failed['peer_read_through']['reason'] == 'vendor_context_source_unavailable'
    altered = deepcopy(cache); altered['error'] = 'approved'
    rejected = build_online_research_context(view,{},altered,ticker='FICT',profile_key='personal',as_of=NOW)
    assert rejected['peer_read_through']['reason'] == 'cached_observation_changed'
