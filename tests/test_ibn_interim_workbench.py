"""Workbench keeps directly reported quarterly income and YTD cash in their own periods."""
from copy import deepcopy
from datetime import timedelta

import pytest

from src import sec_exact_filing_view
from src.company_answer_summary import build_company_answers
from src.company_workbench_presentation import workbench_metrics_html
from src.company_workbench_sections import workbench_projection
from src.online_filing_context import _digest
from src.online_research_context_store import compare_research_contexts, load_research_context, save_research_context
from test_ibn_workbench import SCOPE, _context
from test_sec_online_ibn_interim_evidence import OBSERVED, online


def _archive():
    source = 'https://www.sec.gov/Archives/edgar/data/1103838/000000123426000001/example.htm'
    end = '2026-09-30'

    def field(label, value):
        return dict(label=label, definition=label, value=value, unit='INR', reported_text=str(value // 10_000_000),
                    source_ref=source, table_index=1, row_index=2, column_span=[3, 4], period_evidence='Printed period')

    def period(kind, start, fields, withheld_fields):
        return dict(kind=kind, status='available', period_start=start, period_end=end, unit='INR',
                    fields=fields, withheld_fields=withheld_fields, unaudited=True)

    return dict(form='6-K', filed='2026-10-22', report_date='2026-10-19', accepted_at='2026-10-22T10:02:58Z',
                observed_at='2026-11-11T23:00:00Z', accession='0000001234-26-000001', source_url=source, unit='INR',
                source_receipts=[], accounting_basis='Indian GAAP (AS 25)',
                periods=[period('quarterly', '2026-07-01', {'net_profit_for_period': field('Net profit for the period', 220_000_000)},
                                {'cash_from_operations': 'direct_quarter_cash_statement_unavailable'}),
                         period('cumulative', '2026-04-01', {'net_profit_for_period': field('Net profit for the period', 410_000_000),
                                'cash_from_operations': field('Net operating cash flow', -90_000_000)}, {})])


def test_annual_bank_overview_defers_to_verified_direct_quarter_and_shows_cash_gap():
    archive = _archive()
    projection = dict(bank_annual={}, bank_interim=archive)
    answers = build_company_answers('IBN', projection, {}, {}, {}, {})
    financial = next(answer for answer in answers if answer['key'] == 'financial')
    assert 'Quarterly net profit INR 220.00M' == financial['value']
    assert '2026-09-30' in financial['context']
    assert ('Exact SEC 6-K', archive['source_url']) in financial['links']
    html = workbench_metrics_html('IBN', answers, {}, projection=projection)
    assert 'Quarterly operating cash flow needs verification' in html


def test_bank_interim_renderer_keeps_six_month_cash_out_of_direct_quarter():
    archive = _archive()
    html = sec_exact_filing_view.bank_interim_html(archive)
    quarter, ytd = html.split('Year to date', 1)
    assert 'Direct quarter' in quarter and '2026-07-01' in quarter
    assert 'Cash flow is reported for the six-month period only' in quarter
    assert '-90,000,000' not in quarter and '410,000,000' not in quarter
    assert '-90,000,000' in ytd and '2026-04-01' in ytd
    assert '2026-10-19' in ytd and archive['source_url'] in ytd


def test_exact_interim_save_and_replay_retain_periods_and_annual_evidence(tmp_path):
    financial = online()
    original = deepcopy(financial)
    context = _context(financial, as_of=OBSERVED)
    coverage = context['filing_coverage']['current']
    assert coverage['annual']['reason'] == 'exact_ibn_annual_table_and_filing'
    assert context['filing_coverage']['structured_annual']['status'] == 'withheld'
    for kind, start in (('quarterly', '2026-07-01'), ('interim', '2026-04-01')):
        state = coverage[kind]
        assert state['reason'] == 'exact_ibn_interim_table_and_filing'
        assert state['anchor']['period_start'] == start and state['anchor']['period_end'] == '2026-09-30'
        assert state['anchor']['report_date'] == '2026-10-19'
    trend = context['business_trend']
    quarter, year_to_date = trend['bank_interim']['periods']
    assert len(quarter['fields']) == 5 and len(year_to_date['fields']) == 7
    assert 'cash_from_operations' not in quarter['fields']
    assert year_to_date['fields']['cash_from_operations']['value'] == -35_000_000
    assert len(trend['bank_annual']['periods']) == 3 and not trend['periods']
    assert context['scenario_base']['status'] == 'excluded'
    projection = workbench_projection('IBN', financial, {}, expected_cik=SCOPE['sec_cik'], as_of=OBSERVED)
    assert (projection['quarter_count'], projection['annual_count'], projection['period_kind']) == (1, 3, 'quarterly')
    first = save_research_context(context, project_root=tmp_path, **SCOPE)
    reopened = load_research_context(first['snapshot_id'], project_root=tmp_path, **SCOPE)
    assert reopened == first and compare_research_contexts(first, reopened)['status'] == 'unchanged'
    assert financial == original and not (tmp_path / 'data').exists()


def test_same_interim_source_refreshed_later_changes_only_metadata():
    later = OBSERVED + timedelta(minutes=1)
    first = _context(online(), as_of=OBSERVED)
    second = _context(online(observed_at=later), as_of=later)
    assert first['business_trend']['bank_interim'] and second['business_trend']['bank_interim']
    comparison = compare_research_contexts(first, second)
    assert comparison['status'] == 'source_metadata_only' and not comparison['financial_changed']


def test_resealed_snapshot_cannot_move_six_month_cash_into_quarter(tmp_path):
    context = _context(online(), as_of=OBSERVED)
    interim = context['business_trend']['bank_interim']
    quarter, year_to_date = interim['periods']
    quarter['fields']['cash_from_operations'] = dict(year_to_date['fields']['cash_from_operations'],
                                                    period_start=quarter['period_start'])
    del quarter['withheld_fields']['cash_from_operations']
    interim['packet_digest'] = _digest({k: v for k, v in interim.items() if k != 'packet_digest'})
    with pytest.raises(ValueError, match='interim bank evidence'):
        save_research_context(context, project_root=tmp_path, **SCOPE)
    assert not list(tmp_path.iterdir())
