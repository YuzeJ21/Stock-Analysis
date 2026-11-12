"""Exact ICICI Bank consolidated AS 25 interim results from a SEC 6-K."""

from collections.abc import Mapping
import re

from src.sec_html_bank import _norm
from src.sec_native_quarter_tables import _NativeTables, _grid, _number


NUMBER_SCHEMA = 'sec-ibn-interim-number-v1'
ACCOUNTING_BASIS = 'Indian GAAP (AS 25)'
UNIT = 'INR'
SCALE = 10_000_000
UNIT_EVIDENCE = '(₹ in crore)'
_JUNE_UNIT_EVIDENCE = '(Rs. in crore)'
_INCOME = 'CONSOLIDATED FINANCIAL RESULTS'
_CASH = 'CONSOLIDATED CASH FLOW STATEMENTS'
_AS_25 = 'Accounting Standards 25 “Interim Financial Reporting”'
_INDIAN_GAAP = 'other accounting principles generally accepted in India'
BASIS_EVIDENCE = _AS_25 + ' · ' + _INDIAN_GAAP
DEFINITIONS = {
    'interest_earned': (_INCOME, 'Interest earned (a)+(b)+(c)+(d)', 'Interest earned · gross'),
    'other_income': (_INCOME, 'Other income (e)+(f)', 'Other income'),
    'total_income': (_INCOME, 'TOTAL INCOME (1)+(2)', 'Total income · before interest expense'),
    'interest_expended': (_INCOME, 'Interest expended', 'Interest expended'),
    'net_profit_for_period': (_INCOME, 'NET PROFIT FOR THE PERIOD (15)–(16)', 'Net profit for the period'),
    'cash_from_operations': (_CASH, 'Net cash flow from/(used in) operating activities (i)+(ii)+(iii)',
                             'Net operating cash flow'),
    'fixed_asset_purchases': (_CASH, 'Purchase of fixed assets', 'Fixed-asset purchases · signed cash flow'),
}
_MARKERS = {'interest_earned': '1', 'other_income': '2', 'total_income': '3', 'interest_expended': '4',
            'net_profit_for_period': '17', 'cash_from_operations': '(A)', 'fixed_asset_purchases': ''}
_INCOME_COLUMNS = (('Sr. No.', 1, '4'), ('Particulars', 2, '4'), ('Three months ended', 3, '1'))
_HEADERS = {
    (_INCOME, 1): (*_INCOME_COLUMNS, ('Year ended', 1, '1')),
    (_INCOME, 2): (*_INCOME_COLUMNS, ('Six months ended', 2, '1'), ('Year ended', 1, '1')),
    (_CASH, 2): (('Particulars', 1, '4'), ('', 1, '4'), ('Period ended', 3, '1')),
}
_PERIOD_COLUMNS = {(_INCOME, 'Three months ended'): (3, 'quarterly'),
                   (_INCOME, 'Six months ended'): (6, 'cumulative'),
                   (_CASH, 'Period ended'): (2, 'cumulative')}
_DISCLOSURE = re.compile(
    r'\bUnaudited financial results \(standalone and consolidated\) for the (quarter(?: and six months)?) ended '
    r'((?:June|September) 30, [0-9]{4})\b', re.I,
)
_BASIS = re.compile(
    r'^The consolidated financial results have been prepared in accordance with the recognition and '
    r'measurement principles laid down in ' + re.escape(_AS_25) + r'.{0,680}\b' + re.escape(_INDIAN_GAAP) + r'\b',
    re.I,
)
_CONFLICTING_BASIS = re.compile(r'\b(?:IFRS|International Financial Reporting Standards|U\.S\. GAAP|Ind AS)\b', re.I)
_AUDIT = '(Unaudited)'
_MAX_DOCUMENT_BYTES = 2 * 1024 * 1024
_MAX_ROWS = 200


class _InterimTables(_NativeTables):
    """Capture original row spans so only the known ICICI header geometry can use them."""

    def handle_starttag(self, tag, attrs):
        span = None
        if tag in {'td', 'th'} and self.depth == 1:
            declared = [value for name, value in attrs if name == 'rowspan']
            span = '1' if not declared else declared[0] if len(declared) == 1 else ''
            if sum(name == 'colspan' for name, _ in attrs) > 1:
                span = ''
            attrs = [(name, value) for name, value in attrs if name != 'rowspan']
        super().handle_starttag(tag, attrs)
        if tag in {'td', 'th'} and self.depth == 1 and self.cell is not None:
            self.cell['source_rowspan'] = span


def _reported_period(text):
    match = re.fullmatch(r'(June|September) 30, ([0-9]{4})', text)
    if match and 1901 < int(match[2]) < 9999:
        return int(match[2]), 1 if match[1] == 'June' else 2
    return None


def _label_key(text):
    return text.casefold().replace('–', '-')


def _duration(caption, evidence):
    if not isinstance(evidence, str) or len(evidence) > 120:
        return None
    pieces = evidence.split(' | ')
    if len(pieces) != 4:
        return None
    duration, filed_end, fiscal_label, audit = pieces
    selected = _PERIOD_COLUMNS.get((caption, duration))
    period = _reported_period(filed_end)
    if not selected or not period or audit != _AUDIT:
        return None
    year, quarter = period
    column, kind = selected
    if (quarter == 1 and kind != 'quarterly'
            or fiscal_label != f"({'Q' + str(quarter) if kind == 'quarterly' else 'H1'}-{year + 1})"):
        return None
    start_month = '07' if quarter == 2 and kind == 'quarterly' else '04'
    return (column, kind, f'{year}-{start_month}-01', f"{year}-{'06' if quarter == 1 else '09'}-30")


def valid_ibn_interim_number(field):
    """Recheck a bounded signed value and its directly printed reporting duration."""
    if not isinstance(field, Mapping):
        return False
    try:
        caption, label, definition = DEFINITIONS[field['field']]
        if (not isinstance(field['label'], str) or len(field['label']) > 120 or _label_key(field['label']) != _label_key(label)
                or field['definition'] != definition or field['table_caption'] != caption
                or field['unit'] != UNIT
                or field['reported_numeric_schema'] != NUMBER_SCHEMA or type(field['scale']) is not int
                or field['scale'] != SCALE or type(field['value']) is not int
                or type(field['table_index']) is not int or not 0 <= field['table_index'] < 1000
                or type(field['row_index']) is not int or not 4 <= field['row_index'] < _MAX_ROWS):
            return False
        number = _number(field['reported_text'], 7)
        if number != (field['value'], field['sign']):
            return False
        duration = _duration(caption, field['period_evidence'])
        if not duration:
            return False
        column, _, start, end = duration
        span = field['column_span']
        unit_evidence = _JUNE_UNIT_EVIDENCE if end.endswith('-06-30') else UNIT_EVIDENCE
        return (isinstance(span, list) and len(span) == 2 and all(type(index) is int for index in span)
                and span == [column, column + 1]
                and field['period_start'] == start and field['period_end'] == end
                and field['unit_evidence'] == unit_evidence)
    except (KeyError, TypeError, ValueError):
        return False


def _expected_headers(caption, year, quarter):
    september = f'September 30, {year}'
    prior = f'September 30, {year - 1}'
    annual = f'March 31, {year}'
    if quarter == 1:
        return ((f'June 30, {year}', annual, f'June 30, {year - 1}', annual),
                (f'(Q1-{year + 1})', f'(Q4-{year})', f'(Q1-{year})', f'(FY{year})'),
                (_AUDIT, '(Audited) 8', _AUDIT, '(Audited)'))
    if caption == _INCOME:
        return ((september, f'June 30, {year}', prior, september, prior, annual),
                (f'(Q2-{year + 1})', f'(Q1-{year + 1})', f'(Q2-{year})', f'(H1-{year + 1})',
                 f'(H1-{year})', f'(FY{year})'),
                (_AUDIT, _AUDIT, _AUDIT, _AUDIT, _AUDIT, '(Audited)'))
    return ((september, annual, prior), (f'(H1-{year + 1})', f'(FY{year})', f'(H1-{year})'),
            (_AUDIT, '(Audited)', _AUDIT))


def _table_has_verified_headers(table, caption, year, quarter):
    rows = table['rows']
    if table['bad'] or not 5 <= len(rows) <= _MAX_ROWS:
        return False
    # June's unselected March balancing column carries an audit footnote. The current header must be clean.
    if any(cell['bad'] and not (quarter == 1 and (index, position) == (3, 1))
           for index, row in enumerate(rows[:4]) for position, cell in enumerate(row)):
        return False
    first = tuple((cell['text'], cell['span'], cell['source_rowspan']) for cell in rows[0])
    if first != _HEADERS[(caption, quarter)]:
        return False
    if any(cell['span'] != 1 or cell['source_rowspan'] != '1' for row in rows[1:4] for cell in row):
        return False
    if any(cell['source_rowspan'] != '1' for row in rows[4:] for cell in row):
        return False
    return tuple(tuple(cell['text'] for cell in row) for row in rows[1:4]) == _expected_headers(caption, year, quarter)


def _selected_tables(tables, caption):
    return [table for table in tables for unit in (UNIT_EVIDENCE, _JUNE_UNIT_EVIDENCE)
            if table['context'][-2:] == [caption, unit] and table['nearby'].endswith(caption + ' ' + unit)]


def _consolidated_basis(tables, income_index):
    starts = [i for i, table in enumerate(tables) if table['index'] > income_index
              and table['nearby'].casefold().endswith('notes on consolidated financial results:')]
    if len(starts) != 1:
        return None
    start = starts[0]
    matches = []
    for table in tables[start:start + 12]:
        if re.search(r'\b(?:standalone|segmental|auditors)\b', table['nearby'], re.I):
            break
        if not table['bad']:
            matches.extend(cell['text'] for row in table['rows'] for cell in row
                           if not cell['bad'] and _BASIS.search(cell['text']))
    return tables[start]['index'] if len(matches) == 1 and not _CONFLICTING_BASIS.search(matches[0]) else None


def _period_evidence(table, caption, duration):
    column, _ = _PERIOD_COLUMNS[(caption, duration)]
    position = column - (3 if caption == _INCOME else 2)
    values = [row[position]['text'] for row in table['rows'][1:4]]
    return ' | '.join([duration, *values])


def _field_value(caption, row, label_index, column, key, width):
    if len(row) <= label_index or row[label_index]['bad']:
        return None
    grid = _grid([row])
    if not grid or grid[0][1] != width:
        return None
    cells = grid[0][0]
    label = cells[label_index]
    if caption == _INCOME:
        marker = cells[0]
        if marker['start'] != 0 or marker['end'] != 1 or (label['start'], label['end']) != (1, 3):
            return None
    else:
        marker = cells[1]
        if (label['start'], label['end']) != (0, 1) or (marker['start'], marker['end']) != (1, 2):
            return None
    if marker['bad'] or marker['text'] != _MARKERS[key]:
        return None
    amount = next((cell for cell in cells if cell['start'] == column and cell['end'] == column + 1), None)
    if not amount or amount['bad']:
        return None
    number = _number(amount['text'], 7)
    return (amount['text'], *number) if number else None


def _extract_fields(table, caption, duration):
    evidence = _period_evidence(table, caption, duration)
    column, _, start, end = _duration(caption, evidence)
    width = sum(cell['span'] for cell in table['rows'][0])
    fields, gaps = {}, {}
    for key, (statement, expected_label, definition) in DEFINITIONS.items():
        if statement != caption:
            continue
        matches = [(index, row, position) for index, row in enumerate(table['rows'][4:], 4)
                   for position, cell in enumerate(row) if _label_key(cell['text']) == _label_key(expected_label)]
        if not matches:
            gaps[key] = 'direct_reported_row_unavailable'
            continue
        if len(matches) != 1:
            gaps[key] = 'conflicting_reported_rows'
            continue
        index, row, position = matches[0]
        if position != (1 if caption == _INCOME else 0):
            gaps[key] = 'direct_numeric_cell_unavailable'
            continue
        result = _field_value(caption, row, position, column, key, width)
        if result is None:
            gaps[key] = 'direct_numeric_cell_unavailable'
            continue
        reported, value, sign = result
        fields[key] = dict(field=key, label=row[position]['text'], definition=definition, unit=UNIT, value=value,
                           reported_text=reported, reported_numeric_schema=NUMBER_SCHEMA, scale=SCALE, sign=sign,
                           table_index=table['index'], row_index=index, column_span=[column, column + 1],
                           table_caption=caption, period_start=start, period_end=end, period_evidence=evidence,
                           unit_evidence=table['context'][-1])
    return fields, gaps


def parse_ibn_interim_tables(raw: bytes, *, period_end: str | None = None) -> dict:
    """Read direct June/September quarters and separately printed September year-to-date columns."""
    held = {'status': 'withheld', 'reason': 'qualified_ibn_interim_source_unavailable', 'periods': []}
    if (not isinstance(raw, bytes) or not 0 < len(raw) <= _MAX_DOCUMENT_BYTES or b'\0' in raw
            or b'<!entity' in raw.lower()):
        return held
    try:
        parser = _InterimTables()
        parser.feed(raw.decode('utf-8-sig'))
        parser.close()
        prefix = _norm(' '.join(parser.all_text[:260]))[:4500]
        if not re.search(r'\bFORM 6-K(?:/A)?\b', prefix, re.I) or not re.search(
            r"\bICICI Bank Limited \(Translation of registrant['’]s name into English\)", prefix, re.I
        ):
            return held
        income_tables = _selected_tables(parser.tables, _INCOME)
        if len(income_tables) != 1:
            return held
        income = income_tables[0]
        notes_index = _consolidated_basis(parser.tables, income['index'])
        if notes_index is None:
            return held
        printed = {(match[1].casefold(), match[2]) for match in _DISCLOSURE.finditer(prefix)}
        if len(printed) != 1:
            return held
        cover_duration, cover_end = next(iter(printed))
        period = _reported_period(cover_end)
        if not period:
            return held
        year, quarter = period
        june = quarter == 1
        unit_evidence = _JUNE_UNIT_EVIDENCE if june else UNIT_EVIDENCE
        if (cover_duration != ('quarter' if june else 'quarter and six months')
                or income['context'][-1] != unit_evidence
                or not _table_has_verified_headers(income, _INCOME, year, quarter)):
            return held
        end = f"{year}-{'06' if june else '09'}-30"
        if period_end is not None and period_end != end:
            return held
        cash_tables = [] if june else _selected_tables(parser.tables, _CASH)
        cash = cash_tables[0] if len(cash_tables) == 1 else None
        cash_verified = (cash and income['index'] < cash['index'] < notes_index
                         and cash['context'][-1] == unit_evidence
                         and _table_has_verified_headers(cash, _CASH, year, quarter))
        periods = []
        scopes = [('quarterly', 'Three months ended', '04' if june else '07')]
        if not june:
            scopes.append(('cumulative', 'Six months ended', '04'))
        for kind, duration, month in scopes:
            fields, gaps = _extract_fields(income, _INCOME, duration)
            if kind == 'cumulative' and cash_verified:
                cash_fields, cash_gaps = _extract_fields(cash, _CASH, 'Period ended')
                fields.update(cash_fields)
                gaps.update(cash_gaps)
            else:
                reason = ('direct_quarter_cash_statement_unavailable' if kind == 'quarterly'
                          else 'cumulative_cash_statement_unavailable')
                gaps.update({key: reason for key, definition in DEFINITIONS.items() if definition[0] == _CASH})
            periods.append(dict(kind=kind, period_start=f'{year}-{month}-01', period_end=end, unit=UNIT,
                                unaudited=True, fields=fields, withheld_fields=gaps))
        if not any(period['fields'] for period in periods):
            return held
        return {'status': 'inspection_only', 'reason': None, 'accounting_basis': ACCOUNTING_BASIS,
                'basis_evidence': BASIS_EVIDENCE, 'periods': periods}
    except (ValueError, RecursionError):
        return held
