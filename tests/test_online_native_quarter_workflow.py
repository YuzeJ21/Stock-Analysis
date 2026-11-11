"""Separate native 6-K durations survive the Workbench and private replay."""
from copy import deepcopy

import pytest

from src.company_answer_summary import build_company_answers
from src.company_workbench_sections import workbench_projection
from src.online_research_context_store import compare_research_contexts, load_research_context, save_research_context
from src.online_research_tools import build_online_research_context
from src.sec_online_quarter_view import native_quarter_html
from test_sec_inline_filing import OBSERVED
from test_sec_online_annual_evidence import CIK, FACTS, _online
from test_sec_online_native_quarter_evidence import _quarter_sources


SCOPE = dict(ticker='FICT', sec_cik=CIK, profile_key='personal/demo')


def _context(financial):
    return build_online_research_context(financial, {}, ticker=SCOPE['ticker'], expected_cik=CIK,
                                         profile_key=SCOPE['profile_key'], as_of=OBSERVED)


def _native_periods(context):
    return {row['kind']: row for row in context['business_trend']['periods'] if row.get('period_basis')}


def test_exact_native_quarter_and_ytd_replay_their_own_fields(tmp_path):
    sources, _, _, exhibit = _quarter_sources()
    financial = _online(sources)
    original = deepcopy(financial)
    context = _context(financial)
    periods = _native_periods(context)
    assert set(periods) == {'quarterly', 'interim'}
    for kind, basis, start, revenue in (
        ('quarterly', 'direct_quarter', '2026-07-01', 1_234_000_000),
        ('interim', 'year_to_date', '2026-01-01', 3_456_000_000),
    ):
        row = periods[kind]
        assert row['period_basis'] == basis and row['period_start'] == start
        assert row['period_end'] == '2026-09-30' and row['current']
        assert row['fields']['revenue']['value'] == revenue
        assert row['fields']['revenue']['source_ref'] == exhibit and row['currency'] == 'TWD'
        assert row['cumulative_fields'] == {} and 'cash_from_operations' in row['withheld_fields']
    assert context['scenario_base']['status'] == 'withheld'
    assert context['peer_read_through']['status'] == 'not_requested'
    assert context['saved_readiness_promoted'] is context['commercial_eligible'] is False
    projection = workbench_projection('FICT', financial, {}, expected_cik=CIK, as_of=OBSERVED)
    assert projection['native_quarter_selected'] and not projection['native_ytd_missing']
    assert projection['facts']['revenue']['value'] == periods['quarterly']['fields']['revenue']['value']
    assert projection['facts']['revenue']['unit'] == 'TWD'
    html = native_quarter_html(projection['native_quarter_archive'])
    assert html.index('Direct quarter') < html.index('TWD 1,234,000,000') < html.index('Year to date')
    assert 'TWD 3,456,000,000' in html and exhibit in html
    first = save_research_context(context, project_root=tmp_path, **SCOPE)
    second = load_research_context(first['snapshot_id'], project_root=tmp_path, **SCOPE)
    assert second == first and second['historical'] and not second['current']
    assert compare_research_contexts(first, second)['status'] == 'unchanged'
    assert financial == original


@pytest.mark.parametrize('change', ['period', 'unit', 'source', 'literal', 'year_to_date_copy'])
def test_native_snapshot_rejects_cross_scope_numeric_proof(tmp_path, change):
    context = _context(_online(_quarter_sources()[0]))
    periods = _native_periods(context)
    field = periods['quarterly']['fields']['revenue']
    if change == 'period':
        field['period_start'] = '2026-01-01'
    elif change == 'unit':
        field['unit'] = 'USD'
    elif change == 'source':
        field['source_ref'] = 'https://www.sec.gov/Archives/edgar/data/999/not-the-filing.htm'
    elif change == 'literal':
        field['value'] += 1
    else:
        periods['quarterly']['fields']['revenue'] = periods['interim']['fields']['revenue']
    with pytest.raises(ValueError, match='reported numeric proof'):
        save_research_context(context, project_root=tmp_path, **SCOPE)
    assert not list(tmp_path.iterdir())


def test_missing_ytd_and_yoy_remain_visible_with_supported_sequential_change():
    sources, _, _, exhibit = _quarter_sources()
    sources[exhibit] = _comparative_exhibit().replace(
        '<th>Three Months Ended September 30, 2025</th>', '<th>Nine Months Ended September 30, 2025</th>')
    financial = _online(sources)
    projection = workbench_projection('FICT', financial, {}, expected_cik=CIK, as_of=OBSERVED)
    assert projection['native_ytd_missing']
    html = native_quarter_html(projection['native_quarter_archive'])
    assert 'Year-to-date values are unavailable in this results document.' in html
    financial_answer = next(a for a in build_company_answers('FICT', projection, financial, {}, {}, {})
                            if a['key'] == 'financial')
    assert ('Exact SEC results document', exhibit) in financial_answer['links']
    assert financial_answer['headline'] == 'Revenue up 25.0%'
    assert 'Quarter over quarter' in financial_answer['headline_context']
    assert financial_answer['native_comparison_gaps'] == ['Same quarter last year revenue needs verification']


def _comparative_exhibit():
    return '''<h2>Consolidated Statements of Income</h2><p>(TWD in millions)</p>
    <table><tr><th></th><th>Three Months Ended September 30, 2026</th>
    <th>Three Months Ended June 30, 2026 (Retrospectively Adjusted)</th>
    <th>Three Months Ended September 30, 2025</th></tr>
    <tr><td>Revenue</td><td>125</td><td>100</td><td>80</td></tr>
    <tr><td>Operating income</td><td>14</td><td>0</td><td>7</td></tr></table>'''


def test_same_filing_quarter_comparisons_reach_overview_trends_and_replay(tmp_path):
    sources, _, _, exhibit = _quarter_sources()
    sources[exhibit] = _comparative_exhibit()
    financial = _online(sources)
    projection = workbench_projection('FICT', financial, {}, expected_cik=CIK, as_of=OBSERVED)
    summary = next(a for a in build_company_answers('FICT', projection, financial, {}, {}, {})
                   if a['key'] == 'financial')
    assert summary['headline'] == 'Revenue up 56.2%'
    assert 'Year over year' in summary['headline_context']
    assert ('Exact SEC results document', exhibit) in summary['links']
    html = native_quarter_html(projection['native_quarter_archive'])
    assert 'Quarter comparisons' in html and 'Previous quarter' in html and '+25.0%' in html
    assert 'Retrospectively adjusted' in html and 'Prior value must be positive' in html
    assert 'Year-to-date values are unavailable' in html
    context = _context(financial)
    trend = context['business_trend']
    assert [row['comparison_basis'] for row in trend['comparative_periods']] == ['year_over_year', 'sequential']
    assert all(row['kind'] == 'quarterly' for row in trend['comparative_periods'])
    growth = {m['key']: m for m in trend['metrics'] if m['period_end'] == '2026-09-30'}
    assert growth['revenue_yoy']['value'] == pytest.approx(0.5625)
    assert growth['revenue_qoq']['value'] == pytest.approx(0.25)
    assert growth['revenue_yoy']['from_period_end'] == '2025-09-30'
    first = save_research_context(context, project_root=tmp_path, **SCOPE)
    reopened = load_research_context(first['snapshot_id'], project_root=tmp_path, **SCOPE)
    assert reopened == first and compare_research_contexts(first, reopened)['status'] == 'unchanged'


@pytest.mark.parametrize('tamper', ['value', 'source', 'unit', 'period', 'strip_proof', 'duplicate_basis'])
def test_comparative_snapshot_rejects_unqualified_or_relabelled_values(tmp_path, tamper):
    sources, _, _, exhibit = _quarter_sources()
    sources[exhibit] = _comparative_exhibit()
    context = _context(_online(sources))
    rows = context['business_trend']['comparative_periods']
    proof = rows[0]['fields']['revenue']
    if tamper == 'value':
        proof['value'] += 1
    elif tamper == 'source':
        proof['source_ref'] = exhibit + '?changed=1'
    elif tamper == 'unit':
        proof['unit'] = 'USD'
    elif tamper == 'period':
        proof['period_start'] = '2025-01-01'
    elif tamper == 'strip_proof':
        del proof['reported_numeric_schema']
        del proof['reported_text']
    else:
        rows[1] = deepcopy(rows[0])
    with pytest.raises(ValueError, match='reported numeric proof|native quarter comparison'):
        save_research_context(context, project_root=tmp_path, **SCOPE)
    assert not list(tmp_path.iterdir())


def test_current_structured_ytd_keeps_its_source_when_exact_quarter_fills_a_gap():
    sources, _, _, _ = _quarter_sources()
    rows = sources[FACTS]['facts']['ifrs-full']['Revenue']['units']['TWD']
    rows.append(dict(start='2026-01-01', end='2026-09-30', filed='2026-10-15', form='6-K',
                     accn='0000001234-26-000002', val=3_410_000_000))
    financial = _online(sources)
    coverage = _context(financial)['filing_coverage']['current']
    assert coverage['quarterly']['reason'] == 'exact_native_quarter_table_and_filing'
    assert coverage['interim']['reason'] == 'exact_structured_duration_and_filing'
    projection = workbench_projection('FICT', financial, {}, expected_cik=CIK, as_of=OBSERVED)
    html = native_quarter_html(projection['native_quarter_archive'])
    assert projection['native_quarter_selected'] and not projection['native_ytd_missing']
    assert '3,456,000,000' not in html
    assert 'Check filing coverage for the current evidence on this reporting basis.' in html
