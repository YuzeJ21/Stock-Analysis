from copy import deepcopy
import hashlib
import re

import pytest

from src.sec_inline_filing import extract_inline_filing
from test_sec_inline_filing import _selection, _xml


SOURCE = 'https://www.sec.gov/Archives/edgar/data/753308/000075330826000081/nee-20260930.htm'


def _fact(concept, fact_id, text):
    return (f'<ix:nonFraction name="{concept}" contextRef="c-1" unitRef="usd" scale="6" decimals="-6" '
            f'format="ixt:num-dot-decimal" id="{fact_id}">{text}</ix:nonFraction>')


def _cash_rows():
    rows = '''<tr><td colspan="6"></td><td colspan="9">Nine Months Ended September 30,</td></tr>
    <tr><td colspan="6"></td><td colspan="3">2026</td><td colspan="3"></td><td colspan="3">2025</td></tr>
    <tr><td colspan="3">CASH FLOWS FROM INVESTING ACTIVITIES</td><td colspan="12"></td></tr>'''
    for concept, fact_id, label, amount in (
        ('nee:CapitalExpendituresOfFPL', 'f-347', 'Capital expenditures of FPL', '8'),
        ('nee:IndependentPowerInvestments', 'f-349', 'Independent power and other investments of NEER', '19'),
        ('g:PaymentsForProceedsFromNuclearFuel', 'f-351', 'Nuclear fuel purchases', '3'),
        ('nee:ProceedsPaymentsFromOtherCapitalExpenditures', 'f-353', 'Other capital expenditures', '1'),
    ):
        rows += (f'<tr><td colspan="3">{label}</td><td colspan="3"></td><td colspan="2">('
                 f'{_fact(concept, fact_id, amount)})</td><td colspan="7"></td></tr>')
    return rows


def _segment_rows():
    total = _fact('nee:CapitalExpendituresIndependentPowerInvestmentsAndNuclearFuelPurchases', 'f-2280', '31')
    return f'''<tr><td colspan="27"></td><td colspan="3">Total Consolidated</td></tr>
    <tr><td colspan="3"></td><td colspan="27">(millions)</td></tr>
    <tr><td colspan="30">Three Months Ended September 30, 2026</td></tr>
    <tr><td colspan="30">Nine Months Ended September 30, 2026</td></tr>
    <tr><td colspan="3">Capital expenditures, independent power and other investments and nuclear fuel purchases</td>
    <td colspan="24"></td><td>$</td><td>{total}</td><td></td></tr>'''


def nee_filing():
    selection = _selection()
    selection.update(ticker='NEE', sec_cik='0000753308', accession='0000753308-26-000081',
                     primary_document='nee-20260930.htm', source_url=SOURCE, period_end='2026-09-30',
                     filed='2026-10-21', accepted_at='2026-10-21T12:00:00Z')
    selection['source_receipts'][1]['source_url'] = 'https://data.sec.gov/submissions/CIK0000753308.json'
    xml = _xml().replace('0000001234', '0000753308').replace('2026-06-30', '2026-09-30').replace(
        '2026-04-01', '2026-07-01').replace('id="cum"', 'id="c-1"').replace('contextRef="cum"', 'contextRef="c-1"').replace(
        'id="money"', 'id="usd"').replace('unitRef="money"', 'unitRef="usd"').replace(
        '<html ', '<html xmlns:nee="http://www.nexteraenergy.com/20260930" ', 1)
    xml = re.sub(r'\(<ix:nonFraction[^>]+ id="capex">[^<]+</ix:nonFraction>\)', '', xml)
    tables = f'''<div>NEXTERA ENERGY, INC.</div><div>CONDENSED CONSOLIDATED STATEMENTS OF CASH FLOWS</div>
    <div>(millions)</div><div>(unaudited)</div><div><table>{_cash_rows()}</table></div>
    <div><table>{_segment_rows()}</table></div>'''
    raw = xml.replace('</body>', tables + '</body>').encode()
    receipt = dict(status='ready', source_url=SOURCE, observed_at='2026-10-30T21:00:00Z',
                   payload_sha256=hashlib.sha256(raw).hexdigest())
    return raw, selection, receipt


def _extract(changed=None):
    raw, selection, receipt = nee_filing()
    if changed:
        raw = changed(raw, selection)
        receipt['payload_sha256'] = hashlib.sha256(raw).hexdigest()
    return extract_inline_filing(raw, selection, receipt)


def test_exact_nee_capital_purchase_evidence_is_separate_from_ppe_and_cash_generation():
    from src.sec_inline_filing import valid_nee_capital_purchase_evidence

    result = _extract()
    assert result['status'] == 'inspection_only'
    assert all('capital_expenditures' not in row['fields'] for row in result['periods'])
    evidence = result['capital_purchase_evidence']
    assert valid_nee_capital_purchase_evidence(evidence, source_url=SOURCE)
    assert evidence['capital_expenditures_equivalent'] is evidence['cash_generation_eligible'] is False
    assert evidence['period_kind'] == 'cumulative' and evidence['period_start'] == '2026-01-01'
    assert evidence['fields']['reported_capital_investment_total']['value'] == 31_000_000
    assert evidence['fields']['fpl_capital_expenditures']['presentation'] == 'cash_outflow'
    assert evidence['fields']['fpl_capital_expenditures']['presentation_evidence'] == '(8)'
    assert evidence['fields']['nuclear_fuel_purchases']['taxonomy'] == 'us-gaap'


@pytest.mark.parametrize(('old', 'new'), [
    ('Nine Months Ended September 30, 2026', 'Three Months Ended September 30, 2026'),
    ('Total Consolidated', 'Reportable Segments'),
    ('<td colspan="27">(millions)</td>', '<td colspan="27">(thousands)</td>'),
    ('<tr><td colspan="30">Nine Months', '<tr hidden="hidden"><td colspan="30">Nine Months'),
    ('Capital expenditures, independent power and other investments and nuclear fuel purchases', 'Capital expenditures'),
    ('CONDENSED CONSOLIDATED STATEMENTS OF CASH FLOWS', 'STANDALONE CASH FLOWS'),
    ('NEXTERA ENERGY, INC.', 'FLORIDA POWER &amp; LIGHT COMPANY'),
    ('http://www.nexteraenergy.com/20260930', 'https://example.invalid/20260930'),
    ('id="f-347">8</ix:nonFraction>)', 'id="f-347">8</ix:nonFraction>'),
    ('id="f-2280">31', 'id="f-2280">32'),
    ('<div><table><tr><td colspan="27">', '<div hidden="hidden"><table><tr><td colspan="27">'),
])
def test_mismatched_source_definitions_remain_withheld(old, new):
    result = _extract(lambda raw, _: raw.replace(old.encode(), new.encode(), 1))
    assert result['status'] == 'inspection_only' and 'capital_purchase_evidence' not in result
    assert all('capital_expenditures' not in row['fields'] for row in result['periods'])


def test_nee_evidence_validation_rejects_tampered_numeric_or_definition():
    from src.sec_inline_filing import valid_nee_capital_purchase_evidence

    original = _extract()['capital_purchase_evidence']
    for key, value in (('value', 1), ('source_ref', SOURCE + '#f-748'), ('period_start', '2026-07-01'),
                       ('label', 'Property, plant and equipment'), ('presentation', 'reported_total')):
        invalid = deepcopy(original)
        invalid['fields']['fpl_capital_expenditures'][key] = value
        assert not valid_nee_capital_purchase_evidence(invalid, source_url=SOURCE)


def nee_cfo_filing(period_end):
    raw, selection, receipt = nee_filing()
    xml = re.sub(r'<ix:nonFraction[^>]+ id="cfo">[^<]+</ix:nonFraction>', '', raw.decode())
    row = ('<tr><td colspan="3">CASH FLOWS FROM OPERATING ACTIVITIES</td><td colspan="12"></td></tr>'
           '<tr><td colspan="3">Net cash provided by operating activities</td><td colspan="3"></td>'
           '<td colspan="2">' + _fact('g:NetCashProvidedByUsedInOperatingActivities', 'f-345', '626')
           + '</td><td colspan="7"></td></tr>')
    xml = xml.replace('<tr><td colspan="3">CASH FLOWS FROM INVESTING ACTIVITIES', row
                      + '<tr><td colspan="3">CASH FLOWS FROM INVESTING ACTIVITIES', 1)
    if period_end == '2026-06-30':
        source = 'https://www.sec.gov/Archives/edgar/data/753308/000075330826000060/nee-20260630.htm'
        selection.update(accession='0000753308-26-000060', period_end=period_end,
                         source_url=source, primary_document='nee-20260630.htm',
                         filed='2026-07-24', accepted_at='2026-07-24T12:00:00Z')
        receipt['source_url'] = source
        xml = xml.replace('2026-09-30', period_end).replace('2026-07-01', '2026-04-01')
        xml = xml.replace('Nine Months Ended September 30,', 'Six Months Ended June 30,', 1)
    return xml.encode(), selection, receipt


@pytest.mark.parametrize('period_end', ['2026-06-30', '2026-09-30'])
def test_nee_cumulative_cfo_is_verified_in_visible_parent_statement(period_end):
    raw, selection, receipt = nee_cfo_filing(period_end)
    receipt['payload_sha256'] = hashlib.sha256(raw).hexdigest()
    result = extract_inline_filing(raw, selection, receipt)
    assert result['nee_cumulative_cfo_verified'] is True
    cumulative = next(row for row in result['periods'] if row['kind'] == 'cumulative')
    assert cumulative['fields']['cash_from_operations']['value'] == 626_000_000
    assert cumulative['fields']['cash_from_operations']['fact_id'] == 'f-345'


@pytest.mark.parametrize(('old', 'new'), [
    ('NEXTERA ENERGY, INC.', 'FLORIDA POWER &amp; LIGHT COMPANY'),
    ('<div>(millions)</div>', '<div>(thousands)</div>'),
    ('Nine Months Ended September 30,', 'Three Months Ended September 30,'),
    ('<td colspan="3">2026</td>', '<td colspan="3">2025</td>'),
    ('CASH FLOWS FROM OPERATING ACTIVITIES', 'CASH FLOWS FROM FINANCING ACTIVITIES'),
    ('Net cash provided by operating activities</td>', 'Other cash flow</td>'),
    ('<tr><td colspan="3">Net cash provided', '<tr hidden="hidden"><td colspan="3">Net cash provided'),
    ('<td colspan="2"><ix:nonFraction name="g:NetCashProvidedByUsedInOperatingActivities"',
     '<td colspan="3"><ix:nonFraction name="g:NetCashProvidedByUsedInOperatingActivities"'),
    ('id="f-345">626', 'sign="-" id="f-345">626'),
    ('format="ixt:num-dot-decimal" id="f-345"', 'id="f-345"'),
])
def test_nee_cumulative_cfo_leaves_generic_evidence_when_presentation_does_not_match(old, new):
    raw, selection, receipt = nee_cfo_filing('2026-09-30')
    assert old.encode() in raw
    raw = raw.replace(old.encode(), new.encode(), 1)
    receipt['payload_sha256'] = hashlib.sha256(raw).hexdigest()
    result = extract_inline_filing(raw, selection, receipt)
    assert result['status'] == 'inspection_only' and 'nee_cumulative_cfo_verified' not in result
    cumulative = next(row for row in result['periods'] if row['kind'] == 'cumulative')
    assert cumulative['fields']['cash_from_operations']['fact_id'] == 'f-345'


def test_nee_cumulative_cfo_does_not_inherit_proof_from_selection():
    raw, selection, receipt = nee_filing()
    selection['nee_cumulative_cfo_verified'] = True
    result = extract_inline_filing(raw, selection, receipt)
    assert result['status'] == 'inspection_only' and 'nee_cumulative_cfo_verified' not in result
