"""Exact native annual evidence across research, projection and private replay."""
from copy import deepcopy
import json

import pytest

from test_sec_online_annual_evidence import _online, _sources, OBSERVED, CIK


def _view():
    return _online(_sources(unit='TWD'))


def test_native_archive_annual_keeps_structured_hold_and_replays_full_evidence(tmp_path):
    from src.online_research_context_store import load_research_context, save_research_context
    from src.online_research_tools import build_online_research_context

    view = _view()
    scope = dict(ticker=view['ticker'], profile_key='personal', sec_cik=CIK)
    result = build_online_research_context(view, {}, ticker=scope['ticker'], profile_key=scope['profile_key'],
                                           expected_cik=CIK, as_of=OBSERVED)
    coverage = result['filing_coverage']
    assert coverage['current']['annual']['reason'] == 'exact_archive_annual_and_filing'
    assert coverage['structured_annual']['status'] == 'facts_pending'
    current = next(r for r in result['business_trend']['periods'] if r['kind'] == 'annual' and r['current'])
    assert current['currency'] == 'TWD' and current['status'] == 'available'
    assert current['fields']['revenue']['reported_numeric_schema'] == 'sec-reported-numeric-v1'
    assert current['fields']['revenue']['rights_status'] == 'unregistered_sec_archive_personal_inspection_only'
    assert result['scenario_base']['status'] != 'available'
    assert result['peer_read_through']['status'] != 'research_comparison'
    assert any(r['source'] == 'exact_annual_receipt' for r in result['source_receipts'])
    assert 'source_packet' not in json.dumps(result)
    saved = save_research_context(result, project_root=tmp_path, **scope)
    assert load_research_context(saved['snapshot_id'], project_root=tmp_path, **scope)['context'] == result

    altered = deepcopy(result)
    row = next(r for r in altered['business_trend']['periods'] if r['kind'] == 'annual' and r['current'])
    row['fields']['revenue']['unit'] = 'USD'
    with pytest.raises(ValueError, match='reported numeric proof'):
        save_research_context(altered, project_root=tmp_path, **scope)


def test_native_annual_projection_uses_exact_filing_and_exposes_missing_comparison():
    from src.company_workbench_sections import workbench_projection

    view = _view()
    projection = workbench_projection(view['ticker'], view, {}, expected_cik=CIK, as_of=OBSERVED)
    assert projection['period_kind'] == 'annual' and projection['unit'] == 'TWD'
    assert projection['annual_archive']['period_end'] == projection['period_end']
    assert projection['facts']['revenue']['source_ref'].startswith('https://www.sec.gov/Archives/')


def test_new_qualified_structured_annual_retains_precedence_over_cached_archive():
    from src.online_research_tools import build_online_research_context

    structured = _online(_sources(unit='TWD', covered=True))
    structured['archive_annual'] = _view()['archive_annual']
    result = build_online_research_context(structured, {}, ticker=structured['ticker'],
                                           profile_key='personal', expected_cik=CIK, as_of=OBSERVED)
    assert 'structured_annual' not in result['filing_coverage']
    current = next(row for row in result['business_trend']['periods'] if row['kind'] == 'annual' and row['current'])
    assert current['fields']['revenue']['source_ref'].startswith('https://data.sec.gov/')
    assert 'reported_text' not in current['fields']['revenue']


def test_archive_corroboration_cannot_unlock_peer_valuation(monkeypatch):
    from src import online_peer_sources
    from src.online_filing_context import corroborate_online_financials
    from src.online_research_tools import _peer_context

    view = _view()
    coverage = corroborate_online_financials(view, view['filing_inventory'], as_of=OBSERVED)
    anchor = coverage['current']['annual']['anchor']
    subject = {key: anchor[key] for key in ('period_end', 'accession', 'form', 'filed')}
    subject.update(price_date='2026-10-29', price=12)
    monkeypatch.setattr(online_peer_sources, '_read', lambda *_: dict(
        status='research_comparison', subject=subject, peer_median=10, premium_fraction=.2))
    qualified = _peer_context({'packet_digest': 'constructed'}, ticker=view['ticker'], cik=CIK,
                              now=OBSERVED, coverage=coverage,
                              prices=dict(status='inspection_only', last_price_date='2026-10-29', close=12))
    assert qualified['status'] == 'withheld'
    assert qualified['reason'] == 'latest_annual_filing_not_corroborated'
    assert qualified['peer_median'] is None


def test_native_annual_comparison_requires_matching_concept_currency_and_duration():
    from src.sec_native_annual_history import native_annual_comparison

    def row(start, end, revenue_concept):
        return dict(period_start=start, period_end=end, status='available', fields={
            'revenue': dict(taxonomy='ifrs-full', concept=revenue_concept, unit='TWD', value=100,
                            source_ref='https://data.sec.gov/qualified-source'),
            'operating_income': dict(taxonomy='ifrs-full', concept='ProfitLossFromOperatingActivities',
                                     unit='TWD', value=30, source_ref='https://data.sec.gov/qualified-source'),
        })
    prior = row('2024-01-01', '2024-12-31', 'Revenue')
    current = row('2025-01-01', '2025-12-31', 'RevenueFromContractsWithCustomers')
    current['fields']['operating_income']['value'] = 42
    coverage = {'periods': {'annual': {'2024-12-31': {'status': 'corroborated'}}}}
    comparison = native_annual_comparison(current, [prior], coverage)
    assert comparison['field'] == 'operating_income'
    assert (comparison['value'], comparison['current_value']) == (30, 42)
    assert native_annual_comparison(current, [prior], {}) is None
    assert native_annual_comparison(current, [prior, deepcopy(prior)], coverage) is None
    prior['fields']['operating_income']['unit'] = 'EUR'
    assert native_annual_comparison(current, [prior], coverage) is None
