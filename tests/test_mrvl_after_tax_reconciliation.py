"""Constructed issuer receipts only; no live financial data or source snippets."""
import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib

import pytest

NOW = datetime(2026, 11, 7, 15, tzinfo=timezone.utc)
STAMP = '2026-11-07T15:00:00Z'
BASE = 'https://www.sec.gov/Archives/edgar/data/1835632/000183563226000006/'
PRIMARY_URL = BASE + 'mrvl-20260305.htm'
EXHIBIT_URL = BASE + 'q426_8kx1312026ex-991.htm'
LABELS = [
    ('GAAP net income (loss)', '160.0'),
    ('Stock-based compensation', '10.0'),
    ('Amortization of acquired intangible assets', '8.2'),
    ('Restructuring related charges (a)', '—'),
    ('Other cost of goods sold (b)', '0.0'),
    ('Gain on sale of business', '(4.4)'),
    ('Other (c)', '6.2'),
    ('Pre-tax total special items', '20.0'),
    ('Other income tax effects and adjustments (d)', '(4.0)'),
    ('Non-GAAP net income', '176.0'),
    ('GAAP weighted-average shares — basic', '100.0'),
    ('GAAP weighted-average shares — diluted', '100.0'),
    ('Non-GAAP weighted-average shares — diluted (e)', '100.0'),
    ('GAAP diluted net income (loss) per share', '1.60'),
    ('Non-GAAP diluted net income per share', '1.76'),
]


def _raw(url, html):
    raw = html.encode()
    return dict(status='ready', source_url=url, observed_at=STAMP,
                payload_sha256=hashlib.sha256(raw).hexdigest(),
                payload_raw_base64=base64.b64encode(raw).decode())


def _primary():
    return _raw(PRIMARY_URL, '''<html><body>
    <ix:nonNumeric name="dei:EntityCentralIndexKey">0001835632</ix:nonNumeric>
    <ix:nonNumeric name="dei:DocumentType">8-K</ix:nonNumeric>
    <ix:nonNumeric name="dei:DocumentPeriodEndDate">2026-03-05</ix:nonNumeric>
    <h1>MARVELL TECHNOLOGY, INC.</h1><p>FORM 8-K</p><p>Date of Report: March 5, 2026</p>
    <h2>Item 2.02 Results of Operations and Financial Condition.</h2>
    <p>The information in Item 2.02, including accompanying Exhibit 99.1, is being furnished and shall not be deemed filed.</p>
    <p>Marvell issued fiscal year results for January 31, 2026.</p>
    <h2>Item 9.01 Financial Statements and Exhibits.</h2>
    <table><tr><td>99.1</td><td><a href="q426_8kx1312026ex-991.htm">Press release March 5, 2026</a></td></tr></table>
    </body></html>''')


def _exhibit():
    # Real shape: 33 physical columns; three quarter dates precede the annual date.
    def cell(text='', span=3):
        return f'<td colspan="{span}">{text}</td>'
    def row(label, value, *, currency=False):
        cells = cell(label) + cell()
        for index in range(5):
            amount = value if index == 3 else '9.0'
            cells += cell('$', 1) + cell(amount, 1) + cell('', 1) if currency else cell(amount, 2) + cell('', 1)
            if index != 4:
                cells += cell()
        return '<tr>' + cells + '</tr>'
    header = ''.join('<tr>'+cell(t, 33)+'</tr>' for t in (
        'Marvell Technology, Inc.', 'Reconciliations from GAAP to Non-GAAP (Unaudited)',
        '(In millions, except per share amounts)'))
    header += '<tr>'+cell()+cell()+cell('Three Months Ended',15)+cell()+cell('Year Ended',9)+'</tr>'
    header += '<tr>'+cell()+cell()+cell('January 31,<br/>2026')+cell()+cell('November 1,<br/>2025')+cell()+cell('February 1,<br/>2025')+cell()+cell('January 31,<br/>2026')+cell()+cell('February 1,<br/>2025')+'</tr>'
    earlier = row('GAAP interest and other income (loss), net', '1.0', currency=True)
    earlier += row('Gain on sale of business', '(1.0)')
    body = ''
    for i, (label, value) in enumerate(LABELS):
        body += row(label, value, currency=i in {0,9,13,14})
        if i == 0:
            body += '<tr>'+cell('Special items - expenses (income):')+cell('',30)+'</tr>'
    return _raw(EXHIBIT_URL, '<html><body><table>'+header+earlier+body+'</table></body></html>')


def _profile_receipt():
    from src.mrvl_earnings_review import normalize_review_profile
    row = dict(form='8-K', reportDate='2026-03-05', filingDate='2026-03-05',
               accessionNumber='0001835632-26-000006', primaryDocument='mrvl-20260305.htm')
    body = dict(cik=1835632, tickers=['MRVL'], filings={'recent': {k: [v] for k,v in row.items()}})
    receipt = dict(status='ready', source_url='https://data.sec.gov/submissions/CIK0001835632.json',
                   observed_at=STAMP, payload_sha256='1'*64, payload=body)
    return normalize_review_profile(receipt)


def _annual_filing():
    from src.mrvl_earnings_review import MRVL
    return deepcopy(MRVL)


def _annual_fields():
    filing = _annual_filing()
    return [dict(field=f, concept=c, status='available', reason=None, value=v, unit=u,
                 source_ref='https://data.sec.gov/api/xbrl/companyfacts/CIK0001835632.json',
                 observed_at=STAMP, payload_sha256='2'*64,
                 **{k: filing[k] for k in ('accession','form','filed','period_start','period_end')})
            for f,c,v,u in [('net_income','NetIncomeLoss',160000000,'USD'),
                            ('diluted_eps','EarningsPerShareDiluted',1.60,'USD/shares')]]


def _evidence():
    return dict(schema_version='mrvl-after-tax-reconciliation-v1', primary=_primary(), exhibit=_exhibit())


def _replace(receipt, before, after):
    text = base64.b64decode(receipt['payload_raw_base64']).decode()
    assert before in text
    return _raw(receipt['source_url'], text.replace(before, after))


def _build(evidence=None, **kwargs):
    from src.mrvl_after_tax_reconciliation import build_mrvl_after_tax_reconciliation
    options = dict(profile_receipt=_profile_receipt(), annual_fields=_annual_fields(),
                   annual_filing=_annual_filing(), as_of=NOW)
    options.update(kwargs)
    return build_mrvl_after_tax_reconciliation(_evidence() if evidence is None else evidence, **options)


def test_exact_annual_bridge_selects_fourth_column_and_keeps_independent_gaps():
    e = _evidence(); before = deepcopy(e)
    result = _build(e)
    assert result['status'] == 'verified_issuer_reconciliation'
    assert result['reason'] is None
    assert result['basis'] == 'issuer_reported_non_gaap'
    assert result['normalized_earnings'] is False and result['valuation_denominator_eligible'] is False
    assert result['rights_status'] == 'personal_research_only_commercial_and_redistribution_unverified'
    rows = {r['field']:r for r in result['components']}
    assert len(rows) == 15
    assert rows['gaap_net_income']['value'] == 160000000
    assert rows['gain_on_sale_of_business']['value'] == -4400000
    assert rows['issuer_non_gaap_net_income']['value'] == 176000000
    assert rows['issuer_non_gaap_diluted_eps']['value'] == 1.76
    assert rows['gaap_diluted_shares']['unit'] == 'shares'
    assert rows['gaap_diluted_shares']['value'] == 100000000
    assert rows['gaap_diluted_shares']['scale'] == rows['gaap_net_income']['scale'] == 1_000_000
    assert rows['issuer_non_gaap_diluted_eps']['scale'] == 1
    assert rows['gaap_net_income']['source_value'] == '160.0'
    assert rows['gain_on_sale_of_business']['raw_text'] == '(4.4)'
    assert rows['gaap_net_income']['column_span'] == [24,27]
    assert result['annual_period']['period_start'] == '2025-02-02'
    assert result['annual_period']['period_start_source'] == 'independently_verified_10_k'
    assert result['checks']['pretax_components_residual_usd'] == 0
    assert result['checks']['net_income_residual_usd'] == 0
    assert result['checks']['gaap_eps']['passed'] is True
    assert result['checks']['issuer_non_gaap_eps']['passed'] is True
    assert set(result['gaps']) == {'sale_specific_tax_allocation_unavailable','item_specific_after_tax_eps_unavailable',
                                  'normalized_earnings_not_qualified','adjusted_valuation_denominator_not_qualified'}
    assert len(result['source_refs']) >= 3 and e == before


def test_exact_source_policy_and_selection():
    from src.mrvl_after_tax_reconciliation import RECONCILIATION_POLICY, select_mrvl_after_tax_source
    result = select_mrvl_after_tax_source(_profile_receipt(), as_of=NOW)
    assert result['status'] == 'selected'
    assert result['primary_url'] == RECONCILIATION_POLICY['primary_url'] == PRIMARY_URL
    assert result['exhibit_url'] == EXHIBIT_URL
    assert result['accession'] == '0001835632-26-000006'


@pytest.mark.parametrize('heading', [
    '(In thousands, except per share amounts)',
    'Three Months Ended January 31, 2026',
    'Amounts in CAD millions',
    'Amounts in billions',
])
def test_conflicting_section_context_cannot_override_global_table_headers(heading):
    evidence = _evidence()
    anchor = '<tr><td colspan="3">GAAP net income (loss)</td>'
    evidence['exhibit'] = _replace(evidence['exhibit'], anchor,
        '<tr><td colspan="33">'+heading+'</td></tr>'+anchor)
    result = _build(evidence)
    assert result['status'] == 'withheld'


@pytest.mark.parametrize('component,before,after', [
    ('exhibit','Year Ended','Three Months Ended'),
    ('exhibit','(In millions, except per share amounts)','(In thousands, except per share amounts)'),
    ('exhibit','Marvell Technology, Inc.','Another Issuer'),
    ('exhibit','Reconciliations from GAAP to Non-GAAP (Unaudited)','Some table'),
    ('exhibit','<td colspan="2">20.0</td>','<td colspan="2">21.0</td>'),
    ('exhibit','<td colspan="1">176.0</td>','<td colspan="1">177.0</td>'),
    ('exhibit','<td colspan="1">1.76</td>','<td colspan="1">1.77</td>'),
    ('exhibit','<td colspan="2">100.0</td>','<td colspan="2">99.0</td>'),
    ('exhibit','<td colspan="2">8.2</td>','<td colspan="4">8.2</td>'),
    ('exhibit','Stock-based compensation','<span hidden="hidden">Stock-based compensation</span>'),
    ('exhibit','Other (c)','Unexpected adjustment'),
    ('primary','>8-K<','>8-K/A<'),
    ('primary','>0001835632<','>0001730168<'),
    ('primary','>2026-03-05<','>2026-03-06<'),
    ('primary','is being furnished','is being filed'),
    ('primary','href="q426_8kx1312026ex-991.htm"','href="unrelated.htm"'),
    ('primary','Item 2.02 Results','Item 7.01 Results'),
])
def test_source_and_table_failures_withhold_locally(component, before, after):
    e = _evidence(); e[component] = _replace(e[component], before, after)
    result = _build(e)
    assert result['status'] == 'withheld' and result['reason']
    assert result['components'] == []


@pytest.mark.parametrize('change', ['raw_digest','future','stale','oversize','schema','missing','url'])
def test_receipt_failure_is_local(change):
    e = _evidence()
    if change == 'raw_digest': e['exhibit']['payload_sha256'] = '0'*64
    elif change == 'future': e['primary']['observed_at'] = '2026-11-07T15:00:01Z'
    elif change == 'stale': e['primary']['observed_at'] = '2026-11-06T14:59:59Z'
    elif change == 'oversize': e['primary']['payload_raw_base64'] = 'A' * 24000000
    elif change == 'schema': e['schema_version'] = 'other'
    elif change == 'missing': del e['primary']
    elif change == 'url': e['exhibit']['source_url'] = PRIMARY_URL
    assert _build(e)['status'] == 'withheld'


@pytest.mark.parametrize('change', ['value','unit','period_start','period_end','accession','status','duplicate','filing','stale'])
def test_independent_annual_anchor_must_match_exactly(change):
    fields = _annual_fields(); filing = _annual_filing(); before = deepcopy(fields)
    if change == 'value': fields[0]['value'] += 1
    elif change == 'unit': fields[0]['unit'] = 'CAD'
    elif change in {'period_start','period_end','accession','status'}: fields[0][change] = 'changed'
    elif change == 'duplicate': fields.append(deepcopy(fields[0]))
    elif change == 'filing': filing['period_start'] = '2025-02-01'
    elif change == 'stale': fields[0]['observed_at'] = '2026-11-06T14:59:59Z'
    changed = deepcopy(fields)
    assert _build(annual_fields=fields, annual_filing=filing)['status'] == 'withheld'
    assert fields == changed


def test_duplicate_and_extra_adjustment_rows_fail_closed():
    e = _evidence()
    row = '<tr><td colspan="3">Unmapped adjustment</td><td colspan="30">0</td></tr>'
    e['exhibit'] = _replace(e['exhibit'], '<tr><td colspan="3">Other (c)</td>', row+'<tr><td colspan="3">Other (c)</td>')
    assert _build(e)['status'] == 'withheld'
    e = _evidence()
    e['exhibit'] = _replace(e['exhibit'], '<tr><td colspan="3">Other (c)</td>', '<tr><td colspan="3">Stock-based compensation</td>')
    assert _build(e)['status'] == 'withheld'


@pytest.mark.parametrize('change', ['amendment','duplicate','identity','digest','future','stale','commercial'])
def test_profile_scope_and_personal_research_guard(change, monkeypatch):
    from src.mrvl_earnings_review import normalize_review_profile
    p = _profile_receipt()
    if change == 'identity': p['payload']['tickers'] = ['OTHER']
    elif change == 'digest': p['normalized_sha256'] = '0'*64
    elif change == 'future': p['observed_at'] = '2026-11-07T15:00:01Z'
    elif change == 'stale': p['observed_at'] = '2026-11-06T14:59:59Z'
    elif change == 'commercial': monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE','true')
    else:
        for key, values in p['payload']['filings']['recent'].items():
            values.append('8-K/A' if key == 'form' and change == 'amendment' else values[0])
        p.pop('normalized_sha256'); p = normalize_review_profile(p)
    assert _build(profile_receipt=p)['status'] == 'withheld'


def test_visible_exhibit_list_div_binds_designation_and_exact_link():
    e = _evidence()
    e['primary'] = _replace(e['primary'],
        '<table><tr><td>99.1</td><td><a href="q426_8kx1312026ex-991.htm">Press release March 5, 2026</a></td></tr></table>',
        '<div>99.1 <span><a href="q426_8kx1312026ex-991.htm">Press release March 5, 2026</a></span></div>')
    assert _build(e)['status'] == 'verified_issuer_reconciliation'


def test_non_gaap_eps_uses_its_own_separate_disclosed_share_count():
    e = _evidence()
    # NI176M /110M shares ->1.60. GAAP remains160M /100M ->1.60.
    raw = base64.b64decode(e['exhibit']['payload_raw_base64']).decode()
    label = 'Non-GAAP weighted-average shares — diluted (e)'
    first, rest = raw.split(label)
    rest = rest.replace('>100.0<', '>110.0<', 1)
    e['exhibit'] = _raw(EXHIBIT_URL, first+label+rest)
    e['exhibit'] = _replace(e['exhibit'], '>1.76<', '>1.60<')
    result = _build(e)
    assert result['status'] == 'verified_issuer_reconciliation'
    check = result['checks']['issuer_non_gaap_eps']
    assert check['denominator_field'] == 'issuer_non_gaap_diluted_shares'


def test_positive_plus_sign_and_source_precision_are_retained():
    e = _evidence(); e['exhibit'] = _replace(e['exhibit'], '>10.0<', '>+10.0<')
    result = _build(e)
    assert result['status'] == 'verified_issuer_reconciliation'
    row = next(r for r in result['components'] if r['field'] == 'stock_based_compensation')
    assert row['source_value'] == '10.0' and row['raw_text'] == '+10.0'


@pytest.mark.parametrize('style', ['display:none','visibility:hidden','opacity:0','font-size:0px'])
def test_hidden_ancestor_or_value_does_not_supply_observation(style):
    e = _evidence()
    e['exhibit'] = _replace(e['exhibit'], '>160.0<', f'><span style="{style}">160.0</span><')
    assert _build(e)['status'] == 'withheld'


def test_duplicate_qualified_reconciliation_tables_are_ambiguous():
    e = _evidence(); raw = base64.b64decode(e['exhibit']['payload_raw_base64']).decode()
    table = raw[raw.index('<table>'):raw.index('</table>')+8]
    e['exhibit'] = _raw(EXHIBIT_URL, raw.replace('</body>',table+'</body>'))
    assert _build(e)['status'] == 'withheld'


def test_small_arithmetic_residual_is_permitted_only_at_source_precision():
    e = _evidence()
    e['exhibit'] = _replace(e['exhibit'], '>20.0<', '>20.1<')
    result = _build(e)
    assert result['status'] == 'verified_issuer_reconciliation'
    assert result['checks']['pretax_components_residual_usd'] == -100000
    e['exhibit'] = _replace(e['exhibit'], '>20.1<', '>20.9<')
    assert _build(e)['status'] == 'withheld'


def test_exact_sec_exhibit_sgml_envelope_preserves_original_raw_digest():
    e = _evidence()
    raw = base64.b64decode(e['exhibit']['payload_raw_base64']).decode()
    wrapped = '<DOCUMENT>\n<TYPE>EX-99.1\n<SEQUENCE>2\n<FILENAME>q426_8kx1312026ex-991.htm\n<DESCRIPTION>EXHIBIT 99.1\n<TEXT>\n'+raw+'\n</TEXT>\n</DOCUMENT>'
    e['exhibit'] = _raw(EXHIBIT_URL, wrapped)
    result = _build(e)
    assert result['status'] == 'verified_issuer_reconciliation'
    assert all(r['payload_sha256'] == e['exhibit']['payload_sha256'] for r in result['components'])
    e['exhibit'] = _replace(e['exhibit'], '<TYPE>EX-99.1', '<TYPE>EX-99.2')
    assert _build(e)['status'] == 'withheld'


def test_entirely_empty_hidden_spacer_row_is_not_financial_evidence():
    e = _evidence()
    spacer = '<tr>'+('<td colspan="3" style="display:none"></td>'*11)+'</tr>'
    e['exhibit'] = _replace(e['exhibit'], '<tr><td colspan="3">Stock-based compensation</td>',
        spacer+'<tr><td colspan="3">Stock-based compensation</td>')
    assert _build(e)['status'] == 'verified_issuer_reconciliation'
    e['exhibit'] = _replace(e['exhibit'], 'style="display:none"></td>', 'style="display:none">0</td>')
    assert _build(e)['status'] == 'withheld'


@pytest.mark.parametrize('component', ['primary','exhibit'])
def test_external_or_embedded_stylesheets_make_visibility_unreviewed(component):
    e = _evidence()
    e[component] = _replace(e[component], '<body>', '<head><style>td { display:none }</style></head><body>')
    assert _build(e)['status'] == 'withheld'


def test_conflicting_additional_unit_heading_withholds():
    e = _evidence()
    e['exhibit'] = _replace(e['exhibit'], '<table>', '<table><tr><td colspan="33">(In thousands, except per share amounts)</td></tr>')
    assert _build(e)['status'] == 'withheld'


def test_numeric_values_split_across_cells_are_ambiguous():
    e = _evidence()
    e['exhibit'] = _replace(e['exhibit'], '<td colspan="2">10.0</td><td colspan="1"></td>',
        '<td colspan="1">10</td><td colspan="1">.0</td><td colspan="1"></td>')
    assert _build(e)['status'] == 'withheld'


def test_reported_precision_controls_residual_not_float_roundoff():
    e = _evidence()
    e['exhibit'] = _replace(e['exhibit'], '>20.0<', '>20.1000<')
    e['exhibit'] = _replace(e['exhibit'], '>176.0<', '>176.1000<')
    # NI anchor is160M; net income still reconciles exactly. Pretax residual
    # remains explainable at the six components' disclosed precision.
    result = _build(e)
    assert result['status'] == 'verified_issuer_reconciliation'
    row = next(r for r in result['components'] if r['field'] == 'pretax_special_items_total')
    assert row['source_value'] == '20.1000'
    assert result['checks']['pretax_components_residual_usd'] == -100000


def test_dash_zero_does_not_invent_a_half_million_rounding_allowance():
    e = _evidence()
    e['exhibit'] = _replace(e['exhibit'], '>20.0<', '>20.4<')
    e['exhibit'] = _replace(e['exhibit'], '>176.0<', '>176.4<')
    # The nil restructuring entry is zero, not a number disclosed with integer
    # precision. Five1-decimal components plus the subtotal permit at most0.3M.
    assert _build(e)['status'] == 'withheld'


def _profile_with_amendment(*, same_report):
    from src.mrvl_earnings_review import normalize_review_profile
    p = _profile_receipt()
    amendment = dict(form='8-K/A', reportDate='2026-03-05' if same_report else '2026-07-05',
        filingDate='2026-07-06', accessionNumber='0001835632-26-000099', primaryDocument='other.htm')
    for key, values in p['payload']['filings']['recent'].items():
        values.append(amendment[key])
    p.pop('normalized_sha256')
    return normalize_review_profile(p)


def test_unrelated_later_8k_amendment_does_not_replace_exact_report():
    from src.mrvl_after_tax_reconciliation import select_mrvl_after_tax_source
    p = _profile_with_amendment(same_report=False)
    assert select_mrvl_after_tax_source(p, as_of=NOW)['status'] == 'selected'
    assert _build(profile_receipt=p)['status'] == 'verified_issuer_reconciliation'


def test_exact_report_amendment_is_withheld_with_one_local_reason_prefix():
    from src.mrvl_after_tax_reconciliation import select_mrvl_after_tax_source
    p = _profile_with_amendment(same_report=True)
    selected = select_mrvl_after_tax_source(p, as_of=NOW)
    result = _build(profile_receipt=p)
    assert selected['status'] == result['status'] == 'withheld'
    assert result['reason'] == selected['reason'] == 'after_tax_8k_amendment_unreviewed'


@pytest.mark.parametrize('component', ['primary','exhibit'])
def test_unavailable_source_reason_names_the_failed_document(component):
    e = _evidence()
    e[component] = dict(status='unavailable', reason='network_error')
    result = _build(e)
    assert result['status'] == 'withheld'
    assert result['reason'] == f'after_tax_{component}_source_unavailable'


def test_ready_receipt_retains_precise_bad_digest_reason():
    e = _evidence(); e['exhibit']['payload_sha256'] = '0'*64
    assert _build(e)['reason'] == 'after_tax_raw_digest_changed'
