from copy import deepcopy

import pytest

from src.sec_native_quarter_tables import parse_native_quarter_tables, valid_native_table_number


FISCAL_YEAR_END = '1231'


def parse(text, currency='TWD', fiscal_year_end=FISCAL_YEAR_END):
    return parse_native_quarter_tables(text.encode(), currency=currency, fiscal_year_end=fiscal_year_end)


def quarter_release():
    return '''<div>Example Group Reports September Quarter Results</div>
    <div>Example Group announced consolidated results for the third quarter ended September 30, 2026.</div>
    <div>Example Group’s 2026 third quarter consolidated results:</div>
    <div>(Unit: NT$ million, except for EPS)</div>
    <table>
      <tr><td colspan="2"></td><td colspan="2">3Q26<span>Amount</span><span>a</span></td>
          <td colspan="2">3Q25<span>Amount</span></td><td>YoY %</td></tr>
      <tr><td colspan="2">Net sales</td><td></td><td>1,234</td><td></td><td>800</td><td>54.2</td></tr>
      <tr><td colspan="2">Income from operations</td><td colspan="2">567</td><td colspan="2">300</td><td>89.0</td></tr>
      <tr><td colspan="2">Diluted EPS</td><td colspan="2">6.5</td><td colspan="2">5</td><td>30</td></tr>
    </table>
    <div>a: 3Q2026 figures have not been approved by Board of Directors</div>'''


def test_native_quarter_uses_reported_currency_dated_period_and_caveat():
    packet = parse(quarter_release())
    assert packet['status'] == 'inspection_only'
    quarter, = packet['periods']
    assert (quarter['kind'], quarter['period_start'], quarter['period_end'], quarter['unit']) == (
        'quarterly', '2026-07-01', '2026-09-30', 'TWD',
    )
    assert quarter['provisional'] is True
    assert set(quarter['fields']) == {'revenue', 'operating_income'}
    sales = quarter['fields']['revenue']
    assert (sales['value'], sales['reported_text'], sales['scale']) == (1_234_000_000, '1,234', 6)
    assert 'September 30, 2026' in sales['period_evidence']
    assert 'NT$ million' in sales['unit_evidence']
    assert valid_native_table_number(sales, fiscal_year_end=FISCAL_YEAR_END)
    assert set(quarter['withheld_fields']) >= {'cash_from_operations', 'capital_expenditures'}


def test_abbreviated_release_columns_have_separate_yoy_and_sequential_proof():
    document = quarter_release().replace('<td>YoY %</td>', '<td>2Q26<span>Amount</span></td>')
    packet = parse(document)
    quarter, = packet['periods']
    yoy, sequential = packet['comparative_periods']
    assert 'comparison_basis' not in quarter['fields']['revenue']
    assert yoy['comparison_basis'] == 'year_over_year' and sequential['comparison_basis'] == 'sequential'
    assert (yoy['period_start'], yoy['period_end']) == ('2025-07-01', '2025-09-30')
    assert (sequential['period_start'], sequential['period_end']) == ('2026-04-01', '2026-06-30')
    for row, value in ((yoy, 800_000_000), (sequential, 54_200_000)):
        sales = row['fields']['revenue']
        assert row['current_period_end'] == sales['current_period_end'] == quarter['period_end']
        assert sales['value'] == value and sales['column_index'] != quarter['fields']['revenue']['column_index']
        assert not row['provisional']
        assert valid_native_table_number(sales, fiscal_year_end=FISCAL_YEAR_END)
    forged = dict(yoy['fields']['revenue'], comparison_basis='sequential')
    assert not valid_native_table_number(forged, fiscal_year_end=FISCAL_YEAR_END)
    forged = dict(yoy['fields']['revenue'], current_period_end='2026-06-30')
    assert not valid_native_table_number(forged, fiscal_year_end=FISCAL_YEAR_END)
    forged = dict(yoy['fields']['revenue'], column_header='3Q25Amounta')
    assert not valid_native_table_number(forged, fiscal_year_end=FISCAL_YEAR_END)


def test_ambiguous_comparative_columns_do_not_replace_the_current_release():
    packet = parse(quarter_release().replace('<td>YoY %</td>', '<td>3Q25<span>Amount</span></td>'))
    assert packet['status'] == 'inspection_only'
    assert packet['periods'][0]['fields']['revenue']['value'] == 1_234_000_000
    assert packet['comparative_periods'] == []


def test_quarter_and_ytd_facts_keep_their_own_reported_periods():
    packet = parse('''<p>Condensed Consolidated Statements of Income</p>
    <table>
      <tr><td>(EUR in millions)</td><td colspan="2">Three months ended September 30,</td>
          <td colspan="2">Nine months ended September 30,</td></tr>
      <tr><td></td><td>2026</td><td>2025</td><td>2026</td><td>2025</td></tr>
      <tr><td>Revenue</td><td>3,400</td><td>3,000</td><td>11,000</td><td>10,000</td></tr>
      <tr><td>Operating income</td><td>(100)</td><td>110</td><td>500</td><td>490</td></tr>
    </table>
    <p>Condensed Consolidated Statements of Cash Flows</p>
    <p>(EUR in millions)</p>
    <table>
      <tr><td></td><td>Nine months ended September 30, 2026</td><td>Nine months ended September 30, 2025</td></tr>
      <tr><td>Net cash provided by operating activities</td><td>1,100</td><td>900</td></tr>
      <tr><td>Purchases of property, plant and equipment</td><td>(310)</td><td>(280)</td></tr>
    </table>''', currency='EUR')
    quarter, cumulative = packet['periods']
    assert quarter['period_start'] == '2026-07-01'
    assert cumulative['period_start'] == '2026-01-01'
    assert quarter['fields']['revenue']['value'] == 3_400_000_000
    assert quarter['fields']['operating_income']['value'] == -100_000_000
    assert cumulative['fields']['revenue']['value'] == 11_000_000_000
    assert cumulative['fields']['cash_from_operations']['value'] == 1_100_000_000
    assert cumulative['fields']['capital_expenditures']['value'] == -310_000_000
    assert 'cash_from_operations' in quarter['withheld_fields']
    assert 'capital_expenditures' in quarter['withheld_fields']


@pytest.mark.parametrize(('old', 'new'), [
    ('third quarter ended September 30, 2026', 'month ended September 30, 2026'),
    ('third quarter ended September 30, 2026', 'third quarter ended September 28, 2026'),
    ('third quarter ended September 30, 2026', 'third quarter ended September 30, 2025'),
    ('NT$ million', 'USD million'),
    ('NT$ million', '$ million'),
    ('NT$ million', 'NT$ million and USD million'),
    ('third quarter consolidated results', 'third quarter adjusted consolidated results'),
    ('3Q26<span>Amount</span>', '3Q26<span>Growth %</span>'),
    ('2026 third quarter consolidated results', '2026 full year consolidated results'),
    ('3Q26<span>Amount</span><span>a</span>', '3Q26<span>Amount</span><span>b</span>'),
    ('3Q2026 figures', '3Q2025 figures'),
])
def test_quarter_candidate_with_wrong_period_scope_or_currency_is_withheld(old, new):
    assert parse(quarter_release().replace(old, new))['status'] == 'withheld'


def test_fiscal_year_ends_and_invalid_evidence_do_not_get_guessed():
    assert parse(quarter_release(), fiscal_year_end='0331')['status'] == 'withheld'
    assert parse(quarter_release(), fiscal_year_end='1230')['status'] == 'withheld'
    valid = parse(quarter_release())['periods'][0]['fields']['revenue']
    for key, replacement in (
        ('value', 1), ('unit', 'USD'), ('scale', 3), ('sign', '-'),
        ('row_label', 'Adjusted sales'), ('period_start', '2026-01-01'), ('column_index', -1),
        ('column_header', '3Q25Amount'), ('reported_text', '1,23'),
    ):
        forged = deepcopy(valid)
        forged[key] = replacement
        assert not valid_native_table_number(forged, fiscal_year_end=FISCAL_YEAR_END)


def test_conflicting_duplicate_direct_row_is_withheld_without_discarding_siblings():
    conflicting = quarter_release().replace(
        '<tr><td colspan="2">Diluted EPS</td>', '<tr><td colspan="2">Net sales</td>',
    )
    quarter, = parse(conflicting)['periods']
    assert 'revenue' in quarter['withheld_fields']
    assert set(quarter['fields']) == {'operating_income'}


def test_hidden_reported_cell_is_withheld():
    quarter, = parse(quarter_release().replace('1,234', '<span hidden>1,234</span>'))['periods']
    assert 'revenue' in quarter['withheld_fields']
    assert set(quarter['fields']) == {'operating_income'}


def split_cash_table():
    return '''<p>Summary of Consolidated Statement of Cash Flow Data</p>
    <p>(In NT$ million)</p><p>(Unaudited)</p>
    <table>
      <tr><td></td><td colspan="2">For the three months ended</td>
          <td colspan="2">For the nine months ended</td></tr>
      <tr><td></td><td>Sep. 30 2026</td><td></td><td>Sep. 30 2026 (Retrospectively Adjusted)</td><td></td></tr>
      <tr><td>Cash Flows from Operating Activities</td><td></td><td></td><td></td><td></td></tr>
      <tr><td>Net cash generated from operating activities</td><td>54</td><td></td><td>137</td><td></td></tr>
      <tr><td>Net payments for property, plant and equipment</td><td>(100)</td><td></td><td>(201)</td><td></td></tr>
    </table>'''


def test_consolidated_cash_summary_preserves_reporting_caveats_and_net_capex_gap():
    quarter, cumulative = parse(split_cash_table())['periods']
    assert quarter['unaudited'] and cumulative['unaudited']
    assert quarter['fields']['cash_from_operations']['value'] == 54_000_000
    assert cumulative['fields']['cash_from_operations']['value'] == 137_000_000
    assert cumulative['fields']['cash_from_operations']['column_header'].endswith('(Retrospectively Adjusted)')
    assert all(row['withheld_fields']['capital_expenditures'] == 'non_equivalent_reported_component'
               for row in (quarter, cumulative))


def test_only_explicit_cumulative_duration_yields_only_cumulative_evidence():
    report = split_cash_table().replace('For the three months ended', '')
    cumulative, = parse(report)['periods']
    assert cumulative['kind'] == 'cumulative' and cumulative['period_start'] == '2026-01-01'


def test_dated_consolidated_columns_keep_restatement_labels_and_comparison_durations():
    result = parse('''<p>Summary of Consolidated Statement of Income Data</p><p>(In NT$ million)</p><p>(Unaudited)</p>
    <table>
      <tr><td></td><td colspan="3">For the three months ended</td><td colspan="2">For the nine months ended</td></tr>
      <tr><td></td><td>Sep. 30 2026</td><td>Jun. 30 2026 (Retrospectively Adjusted)</td><td>Sep. 30 2025</td>
          <td>Sep. 30 2026</td><td>Sep. 30 2025</td></tr>
      <tr><td>Total net revenues</td><td>240</td><td>220</td><td>180</td><td>600</td><td>450</td></tr>
    </table>''')
    assert [row['kind'] for row in result['periods']] == ['quarterly', 'cumulative']
    yoy, sequential = result['comparative_periods']
    assert yoy['fields']['revenue']['value'] == 180_000_000
    assert sequential['fields']['revenue']['value'] == 220_000_000
    assert sequential['unaudited'] and sequential['fields']['revenue']['column_header'].endswith('(Retrospectively Adjusted)')
    assert all(valid_native_table_number(row['fields']['revenue'], fiscal_year_end=FISCAL_YEAR_END)
               for row in result['comparative_periods'])


def test_historical_values_from_a_different_table_do_not_become_comparatives():
    packet = parse('''<p>Consolidated Statements of Income</p><p>(In NT$ million)</p>
    <table><tr><td></td><td>Three months ended September 30, 2026</td></tr>
    <tr><td>Net sales</td><td>5</td></tr></table>
    <p>Consolidated Statements of Income</p><p>(In NT$ million)</p>
    <table><tr><td></td><td>Three months ended September 30, 2025</td></tr>
    <tr><td>Net sales</td><td>2</td></tr></table>''')
    assert packet['status'] == 'inspection_only'
    assert packet['comparative_periods'] == []


@pytest.mark.parametrize(('old', 'new'), [
    ('Summary of Consolidated', 'Adjusted Summary of Consolidated'),
    ('Summary of Consolidated', 'Standalone Summary of Consolidated'),
    ('Summary of Consolidated', 'Summary of Segment'),
    ('<p>(Unaudited)</p>', '<p>(Unaudited)</p><p>Subsidiary data</p>'),
    ('<p>(Unaudited)</p>', '<p>(Unaudited)</p><p>Consolidated Statement of Cash Flows</p>'),
    ('<td>Sep. 30 2026</td><td></td>', '<td>Sep. 30 2026</td><td>EUR</td>'),
    ('<td>Sep. 30 2026</td><td></td>', '<td>Sep. 30 2026</td><td>Canadian dollars</td>'),
    ('<td>Sep. 30 2026</td><td></td>', '<td>For the nine months ended Sep. 30 2026</td><td></td>'),
    ('<td>Sep. 30 2026</td><td></td>', '<td>Sep. 30 2026</td><td>Sep. 30 2026</td>'),
    ('<td>Sep. 30 2026</td><td></td>', '<td>Sep. 30 2026</td><td>Year-to-date</td>'),
])
def test_scoped_cash_table_rejects_competing_evidence(old, new):
    assert parse(split_cash_table().replace(old, new))['status'] == 'withheld'
