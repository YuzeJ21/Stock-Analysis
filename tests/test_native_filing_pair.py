from copy import deepcopy

import pytest

from test_sec_inline_filing import OBSERVED
from test_sec_online_annual_evidence import _online
from test_sec_online_native_quarter_evidence import _add, _quarter_sources, _results


def _contexts(*, operating_income='123,164', unit='thousands'):
    from src.online_research_tools import build_online_research_context

    sources, _, _, _ = _quarter_sources()
    baseline = build_online_research_context(_online(sources), {}, ticker='FICT',
                                             profile_key='personal', as_of=OBSERVED)
    later = _results().replace('<body>', '<body>FORM 6-K ').replace('(TWD in millions)', f'(TWD in {unit})')
    later = later.replace('>123<', f'>{operating_income}<').replace('>Revenue<', '>Net revenue<')
    if unit == 'thousands':
        later = later.replace('1,234', '1,234,284')
    _add(sources, 4, filed='2026-10-22', content=later)
    current = build_online_research_context(_online(sources), {}, ticker='FICT',
                                            profile_key='personal', as_of=OBSERVED)
    return baseline, current


def test_same_quarter_pair_keeps_precision_and_definition_independent():
    from src.online_research_context_store import compare_native_filing_pair

    baseline, current = _contexts()
    result = compare_native_filing_pair(baseline, current)
    assert result['status'] == 'available'
    assert result['fields']['operating_income']['status'] == 'agrees_at_baseline_precision'
    assert result['fields']['revenue']['reason'] == 'Filing field definitions differ'
    assert result['fields']['cash_from_operations']['status'] == 'withheld'
    assert result['fields']['capital_expenditures']['status'] == 'withheld'
    assert result['period_start'] == '2026-07-01' and result['period_end'] == '2026-09-30'
    assert result['baseline']['source_url'] != result['current']['source_url']
    assert compare_native_filing_pair(current, current)['status'] == 'same_filing'
    assert compare_native_filing_pair(current, baseline)['status'] == 'withheld'


def test_same_quarter_pair_keeps_scope_and_numeric_proof(tmp_path):
    from src.online_research_context_store import compare_native_filing_pair, save_research_context, load_research_context

    baseline, current = _contexts()
    scope = {key: baseline[key] for key in ('ticker', 'sec_cik', 'profile_key')}
    older = save_research_context(baseline, **scope, project_root=tmp_path)
    newer = save_research_context(current, **scope, project_root=tmp_path)
    paths = list(tmp_path.rglob('*.json'))
    original = [path.read_bytes() for path in paths]
    reopened = [load_research_context(item['snapshot_id'], **scope, project_root=tmp_path) for item in (older, newer)]
    assert compare_native_filing_pair(*reopened) == compare_native_filing_pair(baseline, current)
    assert [path.read_bytes() for path in paths] == original
    wrong_scope = {**current, 'profile_key': 'another-profile'}
    with pytest.raises(ValueError, match='scope'):
        compare_native_filing_pair(baseline, wrong_scope)
    altered = deepcopy(current)
    quarter = next(p for p in altered['business_trend']['periods'] if p.get('period_basis') == 'direct_quarter')
    quarter['fields']['operating_income']['value'] += 1
    with pytest.raises(ValueError, match='reported numeric'):
        compare_native_filing_pair(baseline, altered)


def test_same_quarter_pair_distinguishes_changes_from_lower_precision():
    from src.online_research_context_store import compare_native_filing_pair

    baseline, current = _contexts(operating_income='123,500')
    assert compare_native_filing_pair(baseline, current)['fields']['operating_income']['status'] == 'differs_at_baseline_precision'
    baseline, current = _contexts(operating_income='1', unit='billions')
    comparison = compare_native_filing_pair(baseline, current)['fields']['operating_income']
    assert comparison['status'] == 'withheld'
    assert comparison['reason'] == 'Later filing reports at lower precision'


def test_reviewed_tsm_revenue_definition_applies_only_to_the_exact_two_lines():
    from src.sec_native_quarter_comparisons import reviewed_filing_revenue_definition

    archive = 'https://www.sec.gov/Archives/edgar/data/1046179/'
    scope = dict(field='revenue', ticker='TSM', sec_cik='0001046179', form='6-K', unit='TWD',
                 period_start='2026-07-01', period_end='2026-09-30')
    baseline = dict(scope, accession='0001046179-26-000726', concept='reported_net_sales', row_label='Net sales',
                    source_url=archive + '000104617926000726/a3q26e_withguidancexfinal.htm')
    current = dict(scope, accession='0001046179-26-000801', concept='reported_net_revenue',
                   row_label='NET REVENUE (Notes 20, 31 and 37)',
                   source_url=archive + '000104617926000801/a2026q3consolidatedreport-.htm')

    evidence = reviewed_filing_revenue_definition(baseline, current)
    assert evidence['source_url'] == archive + '000104617926000726/a3q26presentatione.htm'
    assert 'Note 20' in evidence['explanation']
    assert reviewed_filing_revenue_definition(current, baseline) is None
    for key, substitute in [('source_url', baseline['source_url']), ('sec_cik', '0000000123'),
                            ('accession', '0001046179-26-000802'), ('form', '6-K/A'),
                            ('period_start', '2026-01-01'), ('unit', 'USD'),
                            ('row_label', 'Related-party net revenue'), ('field', 'cash_from_operations')]:
        assert reviewed_filing_revenue_definition(baseline, {**current, key: substitute}) is None
