from copy import deepcopy

import pytest

from src.sec_ibn_interim_tables import parse_ibn_interim_tables, valid_ibn_interim_number


END = '2026-09-30'


def _row(*cells):
    return '<tr>' + ''.join(f'<td>{cell}</td>' for cell in cells) + '</tr>'


def interim_html():
    dates = ('September 30, 2026', 'June 30, 2026', 'September 30, 2025',
             'September 30, 2026', 'September 30, 2025', 'March 31, 2026')
    labels = ('(Q2-2027)', '(Q1-2027)', '(Q2-2026)', '(H1-2027)', '(H1-2026)', '(FY2026)')
    audit = ('(Unaudited)',) * 5 + ('(Audited)',)
    report = '''<html><body><p>FORM 6-K</p><p>ICICI Bank Limited</p>
    <p>(Translation of registrant’s name into English)</p>
    <p>Unaudited financial results (standalone and consolidated) for the quarter and six months ended September 30, 2026</p>
    <p>CONSOLIDATED FINANCIAL RESULTS</p><p>(₹ in crore)</p>
    <table><tr><th rowspan="4">Sr. No.</th><th rowspan="4" colspan="2">Particulars</th>
    <th colspan="3">Three months ended</th><th colspan="2">Six months ended</th><th>Year ended</th></tr>'''
    report += _row(*dates) + _row(*labels) + _row(*audit)
    for ordinal, name, current, cumulative in (
        ('1', 'Interest earned (a)+(b)+(c)+(d)', '100.30', '197.61'),
        ('2', 'Other income (e)+(f)', '14.05', '27.09'),
        ('3', 'TOTAL INCOME (1)+(2)', '114.35', '224.70'),
        ('4', 'Interest expended', '40.00', '79.12'),
        ('17', 'NET PROFIT FOR THE PERIOD (15)–(16)', '20.15', '37.31'),
    ):
        report += (f'<tr><td>{ordinal}</td><td colspan="2">{name}</td><td>{current}</td>'
                   f'<td>90.00</td><td>80.00</td><td>{cumulative}</td><td>150.00</td><td>350.00</td></tr>')
    report += '''</table><p>CONSOLIDATED CASH FLOW STATEMENTS</p><p>(₹ in crore)</p>
    <table><tr><th rowspan="4">Particulars</th><th rowspan="4"></th><th colspan="3">Period ended</th></tr>'''
    report += _row(dates[0], dates[5], dates[2]) + _row(labels[3], labels[5], labels[4])
    report += _row('(Unaudited)', '(Audited)', '(Unaudited)')
    report += _row('Net cash flow from/(used in) operating activities (i)+(ii)+(iii)', '(A)', '(3.50)', '7.10', '(2.25)')
    report += _row('Purchase of fixed assets', '', '(1.10)', '(2.20)', '(0.90)')
    report += '''</table><p>Notes on consolidated financial results:</p><table>
    <tr><td>2.</td><td>The consolidated financial results have been prepared in accordance with the recognition
    and measurement principles laid down in Accounting Standards 25 “Interim Financial Reporting” (‘AS 25’),
    the relevant Indian banking provisions and other accounting principles generally accepted in India.</td></tr>
    </table></body></html>'''
    return report.encode()


def june_html():
    report = '''<html><body><p>FORM 6-K</p><p>ICICI Bank Limited</p>
    <p>(Translation of registrant’s name into English)</p>
    <p>Unaudited financial results (standalone and consolidated) for the quarter ended June 30, 2026</p>
    <p>CONSOLIDATED FINANCIAL RESULTS</p><p>(Rs. in crore)</p>
    <table><tr><th rowspan="4">Sr. No.</th><th rowspan="4" colspan="2">Particulars</th>
    <th colspan="3">Three months ended</th><th>Year ended</th></tr>'''
    report += _row('June 30, 2026', 'March 31, 2026', 'June 30, 2025', 'March 31, 2026')
    report += _row('(Q1-2027)', '(Q4-2026)', '(Q1-2026)', '(FY2026)')
    report += _row('(Unaudited)', '(Audited) <sup>8</sup>', '(Unaudited)', '(Audited)')
    for ordinal, name, current in (
        ('1', 'Interest earned (a)+(b)+(c)+(d)', '83.30'),
        ('2', 'Other income (e)+(f)', '14.95'),
        ('3', 'TOTAL INCOME (1)+(2)', '98.25'),
        ('4', 'Interest expended', '38.25'),
        ('17', 'NET PROFIT FOR THE PERIOD (15)–(16)', '16.10'),
    ):
        report += (f'<tr><td>{ordinal}</td><td colspan="2">{name}</td><td>{current}</td>'
                   '<td>90.00</td><td>80.00</td><td>350.00</td></tr>')
    report += '''</table><p>Notes on consolidated financial results:</p><table>
    <tr><td>2.</td><td>The consolidated financial results have been prepared in accordance with the recognition
    and measurement principles laid down in Accounting Standards 25 “Interim Financial Reporting” (‘AS 25’),
    the relevant Indian banking provisions and other accounting principles generally accepted in India.</td></tr>
    </table></body></html>'''
    return report.encode()


def test_june_disclosure_has_only_the_direct_quarter_and_its_own_rupee_evidence():
    packet = parse_ibn_interim_tables(june_html(), period_end='2026-06-30')
    assert packet['status'] == 'inspection_only'
    quarter, = packet['periods']
    assert (quarter['kind'], quarter['period_start'], quarter['period_end']) == (
        'quarterly', '2026-04-01', '2026-06-30',
    )
    assert len(quarter['fields']) == 5 and quarter['fields']['net_profit_for_period']['value'] == 161_000_000
    assert quarter['withheld_fields'] == dict.fromkeys(('cash_from_operations', 'fixed_asset_purchases'),
                                                     'direct_quarter_cash_statement_unavailable')
    for field in quarter['fields'].values():
        assert field['unit_evidence'] == '(Rs. in crore)' and field['column_span'] == [3, 4]
        assert valid_ibn_interim_number(field)


@pytest.mark.parametrize(('old', 'new'), [
    ('quarter ended June 30', 'quarter and six months ended June 30'),
    ('(Rs. in crore)', '(USD in crore)'),
    ('(Q1-2027)', '(Q2-2027)'),
    ('<td>(Unaudited)</td>', '<td><span hidden>(Unaudited)</span></td>'),
    ('<td>June 30, 2026</td>', '<td>September 30, 2026</td>'),
])
def test_june_rejects_wrong_period_unit_or_unreadable_selected_header(old, new):
    assert parse_ibn_interim_tables(june_html().decode().replace(old, new, 1).encode())['status'] == 'withheld'


def test_extracts_only_separate_current_periods_and_signed_native_crore_fields():
    packet = parse_ibn_interim_tables(interim_html(), period_end=END)
    assert packet['status'] == 'inspection_only'
    assert packet['accounting_basis'] == 'Indian GAAP (AS 25)'
    quarter, ytd = packet['periods']
    assert (quarter['kind'], quarter['period_start'], quarter['period_end']) == ('quarterly', '2026-07-01', END)
    assert (ytd['kind'], ytd['period_start'], ytd['period_end']) == ('cumulative', '2026-04-01', END)
    assert quarter['unaudited'] and ytd['unaudited']
    assert quarter['fields']['total_income']['value'] == 1_143_500_000
    assert ytd['fields']['total_income']['value'] == 2_247_000_000
    assert quarter['fields']['net_profit_for_period']['value'] == 201_500_000
    assert 'profit_attributable_to_group' not in quarter['fields']
    for key, value in (('cash_from_operations', -35_000_000), ('fixed_asset_purchases', -11_000_000)):
        assert quarter['withheld_fields'][key] == 'direct_quarter_cash_statement_unavailable'
        assert key not in quarter['fields']
        assert ytd['fields'][key]['value'] == value and ytd['fields'][key]['sign'] == '-'
    assert all(valid_ibn_interim_number(field) for row in (quarter, ytd) for field in row['fields'].values())


@pytest.mark.parametrize(('old', 'new'), [
    ('CONSOLIDATED FINANCIAL RESULTS', 'STANDALONE FINANCIAL RESULTS'),
    ('Notes on consolidated financial results:', 'Notes on standalone financial results:'),
    ('The consolidated financial results have been prepared', 'The standalone financial results have been prepared'),
    ('Accounting Standards 25', 'Accounting Standards 26'),
    ('the relevant Indian banking provisions', 'IFRS amendments'),
    ('generally accepted in India', 'generally accepted in another jurisdiction'),
    ('quarter and six months ended September 30, 2026', 'quarter and six months ended October 22, 2026'),
    ('<p>CONSOLIDATED FINANCIAL RESULTS</p><p>(₹ in crore)</p>',
     '<p>CONSOLIDATED FINANCIAL RESULTS</p><p>(USD in crore)</p>'),
    ('<th colspan="3">Three months ended</th>', '<th colspan="3">Six months ended</th>'),
    ('<th rowspan="4">Sr. No.</th>', '<th rowspan="5">Sr. No.</th>'),
    ('<th colspan="3">Three months ended</th>', '<th colspan="1" colspan="3">Three months ended</th>'),
    ('(Q2-2027)', '(H1-2027)'),
    ('<td>(Unaudited)</td><td>(Unaudited)</td>', '<td>(Audited)</td><td>(Unaudited)</td>'),
])
def test_rejects_ambiguous_issuer_period_accounting_basis_or_unit(old, new):
    assert parse_ibn_interim_tables(interim_html().decode().replace(old, new, 1).encode())['status'] == 'withheld'


def test_source_event_date_does_not_replace_reported_end():
    assert parse_ibn_interim_tables(interim_html(), period_end='2026-10-22')['status'] == 'withheld'


def test_invalid_or_standalone_cash_does_not_change_verified_income():
    document = interim_html().decode().replace('CONSOLIDATED CASH FLOW STATEMENTS', 'STANDALONE CASH FLOW STATEMENTS')
    quarter, ytd = parse_ibn_interim_tables(document.encode())['periods']
    assert quarter['fields']['total_income']['value'] == 1_143_500_000
    assert 'cash_from_operations' not in ytd['fields']
    assert ytd['withheld_fields']['cash_from_operations'] == 'cumulative_cash_statement_unavailable'


def test_hidden_numeric_and_duplicate_reported_rows_remain_withheld_by_field():
    document = interim_html().decode().replace('<td>114.35</td>', '<td><span hidden>114.35</span></td>')
    quarter, ytd = parse_ibn_interim_tables(document.encode())['periods']
    assert quarter['withheld_fields']['total_income'] == 'direct_numeric_cell_unavailable'
    assert ytd['fields']['total_income']['value'] == 2_247_000_000
    document = interim_html().decode().replace('<td>4</td><td colspan="2">Interest expended</td>',
                                               '<td>3</td><td colspan="2">TOTAL INCOME (1)+(2)</td>')
    quarter, _ = parse_ibn_interim_tables(document.encode())['periods']
    assert quarter['withheld_fields']['total_income'] == 'conflicting_reported_rows'


def test_typed_interim_numeric_proof_rejects_tampered_fields_and_mixed_cash_period():
    quarter, ytd = parse_ibn_interim_tables(interim_html())['periods']
    field = ytd['fields']['cash_from_operations']
    for key, value in (('value', -1), ('scale', 1000), ('sign', ''), ('column_span', [3, 4]),
                       ('period_start', quarter['period_start']), ('unit', 'USD'),
                       ('table_caption', 'STANDALONE CASH FLOW STATEMENTS'), ('label', 'Operating income'),
                       ('period_evidence', quarter['fields']['total_income']['period_evidence'])):
        forged = deepcopy(field)
        forged[key] = value
        assert not valid_ibn_interim_number(forged)
