"""Exact furnished MRVL reconciliation for personal inspection, without valuation authority.

No transport or storage. Reported amounts retain their original precision and source
locations. The annual start is inherited from the independently verified 10-K.
"""
from collections.abc import Mapping
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
import base64
import binascii
import hashlib
import re

from src.sec_exact_filing import MAX_FILING_BYTES

SCHEMA = 'mrvl-after-tax-reconciliation-v1'
RIGHTS = 'personal_research_only_commercial_and_redistribution_unverified'
_BASE = 'https://www.sec.gov/Archives/edgar/data/1835632/000183563226000006/'
RECONCILIATION_POLICY = dict(
    sec_cik='0001835632', accession='0001835632-26-000006', form='8-K',
    filed='2026-03-05', report_date='2026-03-05', primary_document='mrvl-20260305.htm',
    exhibit_document='q426_8kx1312026ex-991.htm', primary_url=_BASE+'mrvl-20260305.htm',
    exhibit_url=_BASE+'q426_8kx1312026ex-991.htm', exhibit_designation='99.1',
    legal_status='furnished_not_filed')
_GAPS = ('sale_specific_tax_allocation_unavailable', 'item_specific_after_tax_eps_unavailable',
         'normalized_earnings_not_qualified', 'adjusted_valuation_denominator_not_qualified')
_ROWS = (
    ('gaap_net_income', 'GAAP net income (loss)', 'USD'),
    ('stock_based_compensation', 'Stock-based compensation', 'USD'),
    ('amortization_of_acquired_intangibles', 'Amortization of acquired intangible assets', 'USD'),
    ('restructuring_related_charges', 'Restructuring related charges (a)', 'USD'),
    ('other_cost_of_goods_sold', 'Other cost of goods sold (b)', 'USD'),
    ('gain_on_sale_of_business', 'Gain on sale of business', 'USD'),
    ('other', 'Other (c)', 'USD'),
    ('pretax_special_items_total', 'Pre-tax total special items', 'USD'),
    ('tax_effects', 'Other income tax effects and adjustments (d)', 'USD'),
    ('issuer_non_gaap_net_income', 'Non-GAAP net income', 'USD'),
    ('gaap_basic_shares', 'GAAP weighted-average shares — basic', 'shares'),
    ('gaap_diluted_shares', 'GAAP weighted-average shares — diluted', 'shares'),
    ('issuer_non_gaap_diluted_shares', 'Non-GAAP weighted-average shares — diluted (e)', 'shares'),
    ('gaap_diluted_eps', 'GAAP diluted net income (loss) per share', 'USD/shares'),
    ('issuer_non_gaap_diluted_eps', 'Non-GAAP diluted net income per share', 'USD/shares'),
)
_ERRORS = (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError)


class _Hold(ValueError):
    pass


def _need(condition, reason):
    if not condition:
        raise _Hold(reason if reason.startswith('after_tax_') else 'after_tax_'+reason)


def _norm(value):
    return ' '.join(value.split())


def _number(value):
    """Signed source decimal; a dash is a source-disclosed zero, not missingness."""
    value = _norm(value)
    if value in {'—', '–', '-'}:
        return Decimal(0)
    if value.startswith('(') and value.endswith(')'):
        value = '-'+value[1:-1]
    _need(re.fullmatch(r'[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?', value) is not None,
          'numeric_text_unsupported')
    amount = Decimal(value.replace(',', ''))
    _need(amount.is_finite() and abs(amount) <= Decimal('1e14'), 'numeric_value_unbounded')
    return amount


def _json_number(value):
    return int(value) if value == value.to_integral_value() else float(value)


def _half_quantum(value):
    return Decimal(10) ** value.as_tuple().exponent / 2


def _source_ref(receipt):
    return {k: receipt[k] for k in ('source_url','observed_at','payload_sha256')}


def _withheld(reason):
    return dict(status='withheld', reason=reason, basis='issuer_reported_non_gaap',
                rights_status=RIGHTS, normalized_earnings=False, valuation_denominator_eligible=False,
                commercial_eligible=False, readiness_promoted=False, filing=None, annual_period=None,
                components=[], checks={}, gaps=list(_GAPS), source_refs=[])


def _select(profile_receipt, now):
    # Import at call time: the parent review imports this builder inside its entrypoint.
    from src.mrvl_earnings_review import _receipt_payload, _cik, _iso_date, _utc_timestamp
    p = RECONCILIATION_POLICY
    body = _receipt_payload(profile_receipt, 'https://data.sec.gov/submissions/CIK0001835632.json', now)
    _need(_cik(body.get('cik')) == p['sec_cik'] and body.get('tickers') == ['MRVL'], 'profile_identity_mismatch')
    recent = body.get('filings', {}).get('recent')
    columns = ('form','reportDate','filingDate','accessionNumber','primaryDocument')
    _need(isinstance(recent, Mapping) and all(isinstance(recent.get(k), list) for k in columns), 'profile_schema_invalid')
    count = len(recent['form'])
    _need(0 < count <= 2000 and all(len(v) == count for v in recent.values()), 'profile_schema_invalid')
    matches = []
    for i in range(count):
        row = {k: recent[k][i] for k in columns}
        if row['form'] not in {'8-K','8-K/A'} and row['accessionNumber'] != p['accession']:
            continue
        report, filed = _iso_date(row['reportDate']), _iso_date(row['filingDate'])
        _need(report is not None and filed is not None and report <= filed <= now.date(), '8k_metadata_invalid')
        if 'acceptanceDateTime' in recent:
            accepted = _utc_timestamp(recent['acceptanceDateTime'][i])
            _need(accepted is not None and report <= accepted.date() <= filed and accepted <= now, '8k_metadata_invalid')
        # A matching report's amendment needs review; other events' later
        # amendments do not replace this exact furnished report.
        same_report = row['reportDate'] == p['report_date'] or row['accessionNumber'] == p['accession']
        _need(not (row['form'] == '8-K/A' and row['filingDate'] >= p['filed'] and same_report),
              '8k_amendment_unreviewed')
        if row['accessionNumber'] == p['accession'] or row['reportDate'] == p['report_date']:
            matches.append(row)
    _need(len(matches) == 1, 'exact_8k_missing_or_conflicting')
    row = matches[0]
    _need(tuple(row[k] for k in columns) == (p['form'], p['report_date'], p['filed'], p['accession'], p['primary_document']),
          'exact_8k_metadata_mismatch')
    return dict(status='selected', reason=None, **deepcopy(p))


def select_mrvl_after_tax_source(profile_receipt, *, as_of=None):
    """Qualify the one fixed accession before any collector requests its HTML."""
    from src.mrvl_earnings_review import _now
    from src.online_company_identity import _mode_reason
    try:
        mode = _mode_reason('research')
        _need(mode is None, mode or 'personal_research_required')
        return _select(profile_receipt, _now(as_of))
    except _ERRORS as exc:
        return dict(status='withheld', reason=str(exc) if isinstance(exc, ValueError) else 'after_tax_profile_invalid')


class _Node:
    def __init__(self, tag, attrs, parent=None):
        self.tag, self.attrs, self.parent, self.parts = tag, dict(attrs), parent, []
        declarations = re.sub(r'\s+', '', self.attrs.get('style','').lower())
        self.hidden = (tag in {'head','script','style','template','ix:hidden'} or 'hidden' in self.attrs
                       or self.attrs.get('aria-hidden','').lower() == 'true'
                       or bool(re.search(r'(?:^|;)(?:display:none|visibility:(?:hidden|collapse)|content-visibility:hidden|opacity:(?:0+(?:\.0*)?|\.0+)|font-size:0(?:px|pt|em|rem|%)?)(?:!important)?(?:;|$)', declarations))
                       or bool(parent and parent.hidden))

    def nodes(self):
        yield self
        for part in self.parts:
            if isinstance(part, _Node):
                yield from part.nodes()

    def text(self, *, visible=True):
        if visible and self.hidden:
            return ''
        return _norm(' '.join(p.text(visible=visible) if isinstance(p, _Node) else p for p in self.parts))


class _HTML(HTMLParser):
    """Small bounded DOM retaining visibility, source order and original cell spans."""
    _VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}

    def __init__(self, raw):
        super().__init__(convert_charrefs=True)
        _need(b'<!entity' not in raw.lower() and b'\x00' not in raw, 'document_markup_unsupported')
        self.root = _Node('root', [])
        self.stack, self.count = [self.root], 0
        text = raw.decode('utf-8-sig')
        if re.match(r'\s*<DOCUMENT>', text, re.I):
            envelope = re.fullmatch(
                r'\s*<DOCUMENT>\s*<TYPE>EX-99\.1\s*<SEQUENCE>2\s*'
                r'<FILENAME>q426_8kx1312026ex-991\.htm\s*<DESCRIPTION>EXHIBIT 99\.1\s*'
                r'<TEXT>\s*(<html\b.*</html>)\s*</TEXT>\s*</DOCUMENT>\s*', text, re.I | re.S)
            _need(envelope is not None, 'exhibit_envelope_mismatch')
            text = envelope[1]
        self.feed(text)
        self.close()
        _need(len(self.stack) == 1, 'document_unclosed_markup')
        _need(not any(n.tag == 'style' or n.tag == 'link' and
                      'stylesheet' in n.attrs.get('rel','').lower().split()
                      for n in self.root.nodes()), 'document_stylesheet_visibility_unreviewed')

    def handle_starttag(self, tag, attrs):
        self.count += 1
        _need(self.count <= 350000 and len(self.stack) <= 256, 'document_structure_unbounded')
        _need(len(dict(attrs)) == len(attrs), 'document_duplicate_attribute')
        node = _Node(tag, attrs, self.stack[-1])
        self.stack[-1].parts.append(node)
        if tag not in self._VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self._VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in self._VOID:
            return
        _need(len(self.stack) > 1 and self.stack[-1].tag == tag, 'document_malformed_markup')
        self.stack.pop()

    def handle_data(self, data):
        self.stack[-1].parts.append(data)


def _raw_document(receipt, url, now):
    from src.mrvl_earnings_review import _base_receipt
    document = 'primary' if url == RECONCILIATION_POLICY['primary_url'] else 'exhibit'
    _need(isinstance(receipt, Mapping) and receipt.get('status') == 'ready', document+'_source_unavailable')
    _need(receipt.get('source_url') == url, document+'_source_url_mismatch')
    _base_receipt(receipt, url, now)
    encoded = receipt.get('payload_raw_base64')
    _need(isinstance(encoded, str) and 0 < len(encoded) <= 4*((MAX_FILING_BYTES+2)//3), 'raw_bytes_missing_or_oversized')
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise _Hold('after_tax_raw_bytes_invalid') from None
    _need(0 < len(raw) <= MAX_FILING_BYTES and hashlib.sha256(raw).hexdigest() == receipt['payload_sha256'], 'raw_digest_changed')
    return _HTML(raw).root


def _primary_proof(root):
    all_nodes = list(root.nodes())
    facts = {}
    for node in all_nodes:
        if node.tag == 'ix:nonnumeric':
            facts.setdefault(node.attrs.get('name'), []).append(node.text(visible=False))
    for name, accepted in [('dei:EntityCentralIndexKey', {'0001835632','1835632'}),
                           ('dei:DocumentType', {'8-K'}),
                           ('dei:DocumentPeriodEndDate', {'2026-03-05','March 5, 2026'})]:
        _need(bool(facts.get(name)) and set(facts[name]) <= accepted, 'primary_metadata_mismatch')
    _need(set(facts.get('dei:AmendmentFlag', ['false'])) == {'false'}, 'primary_amendment_unreviewed')
    visible = root.text()
    _need('MARVELL TECHNOLOGY, INC.' in visible.upper() and '8-K' in visible and 'March 5, 2026' in visible,
          'primary_visible_identity_missing')
    # Text scope follows the actual Item 2.02 heading, stopping at the next item.
    item = re.search(r'Item 2\.02\s+Results of Operations and Financial Condition\.(.*?)(?=Item 9\.01\s+Financial Statements and Exhibits\.)', visible, re.I)
    _need(item is not None, 'primary_item_202_missing')
    text = item[1]
    _need(re.search(r'including (?:the )?accompanying Exhibit 99\.1.{0,100}?is being furnished', text, re.I)
          and re.search(r'shall not be deemed [“"]?filed', text, re.I), 'primary_furnished_status_missing')
    links = [n for n in all_nodes if n.tag == 'a' and n.attrs.get('href') in {
        RECONCILIATION_POLICY['exhibit_document'], RECONCILIATION_POLICY['exhibit_url']}]
    _need(len(links) == 1 and not links[0].hidden and bool(links[0].text()), 'primary_exact_exhibit_link_missing')
    link = links[0]
    row = link.parent
    while row is not None and row.tag not in {'tr','div','p'}:
        row = row.parent
    _need(row is not None and len(row.text()) <= 2000 and re.match(r'^99\.1\b', row.text())
          and 'March 5, 2026' in row.text(),
          'primary_exhibit_designation_unbound')


def _grid(table):
    _need(not table.hidden and not any(n.attrs.get('class') for n in table.nodes()),
          'table_hidden_or_unsupported_visibility')
    rows = []
    tr_nodes = [n for n in table.nodes() if n.tag == 'tr']
    _need(0 < len(tr_nodes) <= 500 and sum(n.tag == 'table' for n in table.nodes()) == 1,
          'table_structure_unsupported')
    for row in tr_nodes:
        # Workiva emits entirely empty hidden spacer rows. They carry no
        # observation, header, label or numeric glyph. Hidden content in any
        # nonempty row remains disqualifying, including hidden duplicates.
        _need(not row.text(visible=False) or not any(n.hidden for n in row.nodes()),
              'table_hidden_observation')
        cells, start = [], 0
        for cell in (n for n in row.parts if isinstance(n, _Node) and n.tag in {'td','th'}):
            span = cell.attrs.get('colspan','1')
            _need(re.fullmatch(r'[1-9]\d?', span) is not None and cell.attrs.get('rowspan','1') == '1', 'table_span_unsupported')
            end = start + int(span)
            _need(end <= 64, 'table_width_unbounded')
            cells.append(dict(start=start, end=end, text=cell.text()))
            start = end
        _need(start == 33, 'table_column_width_mismatch')
        rows.append(cells)
    return rows


def _table_rows(root, receipt):
    candidates = [n for n in root.nodes() if n.tag == 'table'
                  and any(c.tag in {'td','th'} and c.text(visible=False) == 'GAAP net income (loss)' for c in n.nodes())
                  and 'Reconciliations from GAAP to Non-GAAP' in n.text(visible=False)]
    _need(len(candidates) == 1, 'qualified_table_missing_or_ambiguous')
    table = candidates[0]
    index = [n for n in root.nodes() if n.tag == 'table'].index(table)
    rows = _grid(table)
    texts = [' '.join(c['text'] for c in row if c['text']) for row in rows]
    _need(texts.count('Marvell Technology, Inc.') == 1
          and texts.count('Reconciliations from GAAP to Non-GAAP (Unaudited)') == 1
          and texts.count('(In millions, except per share amounts)') == 1, 'table_identity_title_or_scale_mismatch')
    headers = [(i,r) for i,r in enumerate(rows) if any(c['text'] == 'Year Ended' for c in r)]
    _need(len(headers) == 1, 'annual_header_missing_or_ambiguous')
    hi, groups = headers[0]
    allowed_preamble = {'', 'Marvell Technology, Inc.',
                        'Reconciliations from GAAP to Non-GAAP (Unaudited)',
                        '(In millions, except per share amounts)'}
    _need(all(text in allowed_preamble for text in texts[:hi]), 'conflicting_table_preamble')
    _need([(c['text'],c['start'],c['end']) for c in groups if c['text']] ==
          [('Three Months Ended',6,21),('Year Ended',24,33)], 'duration_header_span_mismatch')
    _need(hi+1 < len(rows), 'annual_dates_missing')
    dates = [(c['text'],c['start'],c['end']) for c in rows[hi+1] if c['text']]
    _need(dates == [('January 31, 2026',6,9),('November 1, 2025',12,15),
                    ('February 1, 2025',18,21),('January 31, 2026',24,27),('February 1, 2025',30,33)],
          'annual_date_columns_mismatch')
    anchors = [i for i,r in enumerate(rows) if r[0]['text'] == _ROWS[0][1]]
    _need(len(anchors) == 1 and anchors[0] > hi+1, 'net_income_section_ambiguous')
    # Earlier income subsections may have ordinary financial rows, but a new
    # unit/currency/duration heading would change the basis of this section.
    context = ' '.join(texts[hi+2:anchors[0]])
    _need(re.search(r'\b(?:thousands?|millions?|billions?|dollars?|rupees?|USD|CAD|EUR|GBP|JPY|INR|CNY|RMB|HKD|AUD)\b'
                    r'|\b(?:years?|months?|quarters?)\s+(?:ended|ending)\b', context, re.I) is None,
          'conflicting_section_context')
    selected = []
    for ri in range(anchors[0],len(rows)):
        row = rows[ri]
        if not any(c['text'] for c in row):
            continue
        label = row[0]['text']
        if label == 'Special items - expenses (income):':
            _need(len(selected) == 1 and all(not c['text'] for c in row[1:]), 'special_items_heading_mismatch')
            continue
        _need(len(selected) < len(_ROWS), 'extra_reconciliation_row')
        field, expected, unit = _ROWS[len(selected)]
        _need(label == expected and row[0]['start'] == 0 and row[0]['end'] == 3,
              'reconciliation_rows_missing_extra_or_conflicting')
        # Selected annual block must align exactly to Year Ended's current-year
        # date span, even when currency and numeric glyphs occupy separate cells.
        block = [c for c in row if c['start'] < 27 and c['end'] > 24]
        _need(block and block[0]['start'] == 24 and block[-1]['end'] == 27, 'annual_numeric_span_mismatch')
        raw = ' '.join(c['text'] for c in block if c['text'] and c['text'] != '$')
        _need(sum(c['text'] == '$' for c in block) <= 1, 'currency_mark_ambiguous')
        if field in {'gaap_net_income','issuer_non_gaap_net_income','gaap_diluted_eps','issuer_non_gaap_diluted_eps'}:
            _need(sum(c['text'] == '$' for c in block) == 1, 'annual_dollar_mark_missing')
        amount = _number(raw)
        scale = 1 if unit == 'USD/shares' else 1_000_000
        selected.append(dict(field=field, label=label, value=_json_number(amount*Decimal(scale)),
                             unit=unit, scale=scale, source_value=str(amount), raw_text=raw,
                             source_ref=receipt['source_url'], observed_at=receipt['observed_at'],
                             payload_sha256=receipt['payload_sha256'], table_index=index,
                             row_index=ri, column_span=[24,27]))
    _need(len(selected) == len(_ROWS), 'reconciliation_rows_incomplete')
    return selected


def _annual_anchor(fields, filing, components, now):
    from src.mrvl_earnings_review import MRVL, _fresh, _sha
    _need(isinstance(filing, Mapping) and all(filing.get(k) == v for k,v in MRVL.items()), 'annual_filing_scope_mismatch')
    _need(isinstance(fields, list) and len(fields) <= 100, 'annual_anchor_invalid')
    by_field = {r['field']:r for r in components}
    refs = []
    for field, concept, target, unit in [('net_income','NetIncomeLoss','gaap_net_income','USD'),
                                         ('diluted_eps','EarningsPerShareDiluted','gaap_diluted_eps','USD/shares')]:
        matches = [r for r in fields if isinstance(r, Mapping) and r.get('field') == field]
        _need(len(matches) == 1, 'annual_anchor_missing_or_duplicate')
        row = matches[0]
        _need(row.get('status') == 'available' and row.get('reason') is None and row.get('concept') == concept
              and row.get('unit') == unit and all(row.get(k) == MRVL[k] for k in ('accession','form','filed','period_start','period_end')),
              'annual_anchor_scope_mismatch')
        _need(type(row.get('value')) in {int,float} and Decimal(str(row['value'])) == Decimal(str(by_field[target]['value'])),
              'annual_gaap_anchor_mismatch')
        _need(row.get('source_ref') == 'https://data.sec.gov/api/xbrl/companyfacts/CIK0001835632.json'
              and _sha(row.get('payload_sha256')), 'annual_anchor_provenance_invalid')
        _fresh(row.get('observed_at'), now)
        ref = dict(source_url=row['source_ref'], observed_at=row['observed_at'], payload_sha256=row['payload_sha256'])
        if ref not in refs:
            refs.append(ref)
    return refs


def _checks(components):
    rows = {r['field']:r for r in components}
    amounts = {k:Decimal(v['source_value']) for k,v in rows.items()}
    tolerances = {k: Decimal(0) if rows[k]['raw_text'] in {'—','–','-'} else _half_quantum(v)
                  for k,v in amounts.items()}
    special = [r[0] for r in _ROWS[1:7]]
    pretax_residual = sum((amounts[k] for k in special), Decimal(0))-amounts['pretax_special_items_total']
    pretax_tol = sum((tolerances[k] for k in special+['pretax_special_items_total']), Decimal(0))
    ni_keys = ['gaap_net_income','pretax_special_items_total','tax_effects','issuer_non_gaap_net_income']
    ni_residual = sum((amounts[k] for k in ni_keys[:-1]), Decimal(0))-amounts[ni_keys[-1]]
    ni_tol = sum((tolerances[k] for k in ni_keys), Decimal(0))
    checks = dict(pretax_components_residual_usd=_json_number(pretax_residual*1000000),
                  pretax_components_passed=abs(pretax_residual) <= pretax_tol,
                  pretax_rounding_tolerance_usd=_json_number(pretax_tol*1000000),
                  net_income_residual_usd=_json_number(ni_residual*1000000),
                  net_income_passed=abs(ni_residual) <= ni_tol,
                  net_income_rounding_tolerance_usd=_json_number(ni_tol*1000000),
                  annual_gaap_anchor_passed=True, annual_currency_basis='USD_bound_to_independent_annual_GAAP_observations')
    _need(checks['pretax_components_passed'] and checks['net_income_passed'], 'net_income_arithmetic_mismatch')
    _need(amounts['gaap_basic_shares'] > 0 and amounts['gaap_diluted_shares'] >= amounts['gaap_basic_shares'],
          'gaap_shares_invalid')
    for name, ni, shares, eps in [('gaap_eps','gaap_net_income','gaap_diluted_shares','gaap_diluted_eps'),
                                   ('issuer_non_gaap_eps','issuer_non_gaap_net_income','issuer_non_gaap_diluted_shares','issuer_non_gaap_diluted_eps')]:
        n,s,e = amounts[ni],amounts[shares],amounts[eps]
        nt,st,et = tolerances[ni],tolerances[shares],tolerances[eps]
        _need(s-st > 0, 'diluted_shares_invalid')
        # Both independently disclosed denominators retain source precision.
        ratios = [(n+dn)/(s+ds) for dn in (-nt,nt) for ds in (-st,st)]
        passed = min(ratios) < e+et and max(ratios) >= e-et
        checks[name] = dict(passed=passed, method='reported_rounding_interval_overlap',
                            numerator_field=ni, denominator_field=shares, reported_eps_field=eps,
                            reported_eps=rows[eps]['value'], reported_decimal_places=max(0,-e.as_tuple().exponent))
        _need(passed, 'disclosed_eps_rounding_mismatch')
    return checks


def build_mrvl_after_tax_reconciliation(evidence, *, profile_receipt, annual_fields, annual_filing, as_of=None):
    """Return an additive local result; never mutate independently verified inputs."""
    from src.mrvl_earnings_review import _now
    try:
        selected = select_mrvl_after_tax_source(profile_receipt, as_of=as_of)
        _need(selected['status'] == 'selected', selected.get('reason') or 'source_unavailable')
        now = _now(as_of)
        _need(isinstance(evidence, Mapping) and evidence.get('schema_version') == SCHEMA, 'evidence_schema_invalid')
        primary = _raw_document(evidence.get('primary'), RECONCILIATION_POLICY['primary_url'], now)
        exhibit = _raw_document(evidence.get('exhibit'), RECONCILIATION_POLICY['exhibit_url'], now)
        _primary_proof(primary)
        components = _table_rows(exhibit, evidence['exhibit'])
        anchors = _annual_anchor(annual_fields, annual_filing, components, now)
        checks = _checks(components)
        result = _withheld(None)
        result.update(status='verified_issuer_reconciliation', filing=deepcopy(RECONCILIATION_POLICY),
                      annual_period=dict(period_start=annual_filing['period_start'], period_end=annual_filing['period_end'],
                                         period_start_source='independently_verified_10_k',
                                         annual_filing_accession=annual_filing['accession'], source_duration_header='Year Ended'),
                      components=components, checks=checks,
                      source_refs=[_source_ref(profile_receipt), _source_ref(evidence['primary']), _source_ref(evidence['exhibit'])]+anchors)
        return result
    except _ERRORS + (InvalidOperation, UnicodeError) as exc:
        return _withheld(str(exc) if isinstance(exc, ValueError) else 'after_tax_evidence_invalid')
