"""Direct native-currency amounts from explicitly dated consolidated SEC HTML tables."""

from calendar import monthrange
from collections.abc import Mapping
from datetime import date, timedelta
from decimal import Decimal
import re

from src.sec_html_bank import _Tables, _norm


NUMBER_SCHEMA = 'sec-native-table-number-v1'
TABLE_TAXONOMY = 'reported_consolidated_table'
_FIELDS = ('revenue', 'operating_income', 'cash_from_operations', 'capital_expenditures')
_INCOME_ROWS = {
    'net sales': ('revenue', 'reported_net_sales'),
    'revenue': ('revenue', 'reported_revenue'),
    'total revenue': ('revenue', 'reported_total_revenue'),
    'net revenue': ('revenue', 'reported_net_revenue'),
    'total net revenues': ('revenue', 'reported_total_net_revenues'),
    'operating income': ('operating_income', 'reported_operating_income'),
    'income from operations': ('operating_income', 'reported_income_from_operations'),
    'operating profit': ('operating_income', 'reported_operating_profit'),
    'operating loss': ('operating_income', 'reported_operating_loss'),
}
_CASH_ROWS = {
    'net cash provided by operating activities': ('cash_from_operations', 'reported_operating_cash_flow'),
    'net cash used in operating activities': ('cash_from_operations', 'reported_operating_cash_outflow'),
    'net cash generated from operating activities': ('cash_from_operations', 'reported_operating_cash_flow'),
    'net cash provided by (used in) operating activities': ('cash_from_operations', 'reported_operating_cash_flow'),
    'purchases of property, plant and equipment': ('capital_expenditures', 'reported_ppe_purchases'),
}
_ROWS = _INCOME_ROWS | _CASH_ROWS
_NON_EQUIVALENT_ROWS = {'net payments for property, plant and equipment': 'capital_expenditures'}
_CURRENCY = {
    'TWD': r'NT\$|NTD|TWD|(?:New Taiwan|NT) dollars?',
    'EUR': r'EUR|€|euros?',
    'CAD': r'CAD|C\$|Canadian dollars?',
    'GBP': r'GBP|£|pounds sterling',
    'JPY': r'JPY|Japanese yen',
    'CHF': r'CHF|Swiss francs?',
    'SEK': r'SEK|Swedish kronor',
    'INR': r'INR|Indian rupees?',
    'BRL': r'BRL|Brazilian reais',
    'MXN': r'MXN|Mexican pesos?',
}
_SCALES = {'units': 0, 'thousands': 3, 'millions': 6, 'billions': 9}
_UNIT_ANNOTATION = re.compile(r'\([^()]{1,125}\)')
_CURRENCY_MARKER = re.compile(
    r'\b(?:' + '|'.join(_CURRENCY.values()) + r'|USD|U\.S\. dollars?|foreign exchange|currency conversion)\b'
    r'|\$|€|£', re.I,
)
_UNSUPPORTED_SCOPE = re.compile(r'\b(?:adjusted|segment|non-IFRS|non-GAAP|guidance|standalone|pro forma)\b', re.I)
_DURATIONS = {'three': 3, 'six': 6, 'nine': 9}
COMPARISON_BASES = ('year_over_year', 'sequential')
_ORDINALS = {'first': 1, 'second': 2, 'third': 3, 'fourth': 4}
_MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September',
           'October', 'November', 'December')
_MONTH_NUMBERS = {m.lower(): i for i, m in enumerate(_MONTHS, 1)}
_MONTH_NUMBERS.update({m[:3].lower(): i for i, m in enumerate(_MONTHS, 1)})
_MONTH_NUMBERS['sept'] = 9
_DATE_PATTERN = r'[A-Za-z]{3,9}\.? \d{1,2},? \d{4}'
_DATE = re.compile(r'([A-Za-z]{3,9})\.? (\d{1,2}),? (\d{4})(?: \(Retrospectively Adjusted\))?', re.I)
_ENDED = re.compile(r'(first|second|third|fourth) quarter ended (' + _DATE_PATTERN + r')\b', re.I)
_RELEASE_CAPTION = re.compile(r'\b(\d{4}) (first|second|third|fourth) quarter consolidated results\s*:', re.I)
_RELEASE_COLUMN = re.compile(r'([1-4])Q(\d{2}|\d{4})\s*Amount\s*(a)?', re.I)
_PROVISIONAL = re.compile(
    r'\ba:\s*([1-4])Q(\d{4}) (?:figures|results) (?:have not|has not|are not|were not) '
    r'been approved by (?:the )?Board of Directors\b', re.I,
)
_STATEMENT_CAPTION = re.compile(
    r'\b(?:Summary of )?(?:Condensed )?Consolidated '
    r'(Statement(?:s)? of (?:Income|Operations|Profit or Loss|Cash Flows?)|Cash Flow Statement(?:s)?)'
    r'(?: Data)?\b:?\s*(?=\(|$)', re.I,
)
_DURATION = re.compile(r'(?:For the )?(three|six|nine) months ended', re.I)
_NUMBER = r'(?:[0-9]{1,3}(?:,[0-9]{3}){1,6}|[0-9]{1,20})(?:\.[0-9]{1,6})?'
_AMOUNT = re.compile(r'(-)?(' + _NUMBER + r')|\(\s*(' + _NUMBER + r')\s*\)')
_MAX_BYTES = 8 * 1024 * 1024
_MAX_COLUMNS = 64
_MAX_ROWS = 500
_MAX_TABLES = 1000


class _NativeTables(_Tables):
    def __init__(self):
        super().__init__()
        self.previous_end = 0

    def handle_starttag(self, tag, attrs):
        opening_table = tag == 'table' and not self.depth
        if opening_table and self.table_count >= _MAX_TABLES:
            raise ValueError('table_limit')
        super().handle_starttag(tag, attrs)
        if opening_table:
            # Only the text between this table and the previous top-level table can scope it.
            start = max(self.previous_end, len(self.all_text) - 300)
            self.table['nearby'] = _norm(' '.join(self.all_text[start:]))[-800:]
            self.table['visible_offset'] = len(self.all_text)

    def handle_endtag(self, tag):
        if tag == 'table' and self.depth == 1:
            self.previous_end = len(self.all_text)
            self.table['visible_end'] = self.previous_end
        super().handle_endtag(tag)


def _unit_scale(note, currency):
    if not isinstance(note, str) or currency not in _CURRENCY or len(note) > 127:
        return None
    aliases = '(?:' + _CURRENCY[currency] + ')'
    scales = r'units?|thousands?|millions?|billions?'
    body = re.fullmatch(
        rf'\((?:Unit(?:s)?:\s*)?(?:In\s+)?(?:(?P<forward>{aliases})\s+(?:in\s+)?(?P<s1>{scales})'
        rf'|(?P<s2>{scales})\s+of\s+{aliases})(?:,\s*except (?:for )?(?:EPS|per share data))?\)',
        note, re.I,
    )
    if not body:
        return None
    scale = (body['s1'] or body['s2']).lower().rstrip('s') + 's'
    return _SCALES[scale]


def _end_date(text):
    match = _DATE.fullmatch(text)
    if not match or match[1].lower() not in _MONTH_NUMBERS:
        return None
    try:
        return date(int(match[3]), _MONTH_NUMBERS[match[1].lower()], int(match[2]))
    except ValueError:
        return None


def _period(end, months, fiscal_year_end):
    if not isinstance(fiscal_year_end, str) or not re.fullmatch(r'\d{4}', fiscal_year_end):
        return None
    fiscal_month, fiscal_day = int(fiscal_year_end[:2]), int(fiscal_year_end[2:])
    if not 1 <= fiscal_month <= 12 or fiscal_month == 2 or fiscal_day != monthrange(2025, fiscal_month)[1]:
        return None
    if not end or end.year < 1901 or end.day != monthrange(end.year, end.month)[1]:
        return None
    month_in_year = (end.month - fiscal_month - 1) % 12 + 1
    if month_in_year % 3 or (months != 3 and months != month_in_year):
        return None
    first_month = end.year * 12 + end.month - months
    first_year, first_index = divmod(first_month, 12)
    start = date(first_year, first_index + 1, 1)
    return ('quarterly' if months == 3 else 'cumulative', start, end, month_in_year // 3)


def _comparison_end(current, basis):
    if basis == 'sequential':
        return current[1] - timedelta(days=1)
    if basis == 'year_over_year':
        end = current[2]
        return date(end.year - 1, end.month, monthrange(end.year - 1, end.month)[1])
    return None


def _release_period(header, evidence, fiscal_year_end, basis=None):
    amount = _RELEASE_COLUMN.fullmatch(header)
    explicit = _ENDED.fullmatch(evidence)
    if not amount or not explicit:
        return None
    current = _period(_end_date(explicit[2]), 3, fiscal_year_end)
    if not current or _ORDINALS[explicit[1].lower()] != current[3]:
        return None
    period = _period(_comparison_end(current, basis), 3, fiscal_year_end) if basis else current
    if not period or basis and amount[3]:
        return None
    _, _, end, quarter = period
    fiscal_month = int(fiscal_year_end[:2])
    label_year = end.year + (end.month > fiscal_month)
    if int(amount[1]) != quarter or amount[2] not in {str(label_year), str(label_year)[-2:]}:
        return None
    return period


def _statement_period(header, evidence, fiscal_year_end):
    duration = _DURATION.match(evidence)
    if not duration or evidence[duration.end():duration.end() + 1] != ' ':
        return None
    explicit_date = evidence[duration.end() + 1:]
    if header not in {explicit_date, evidence}:
        return None
    return _period(_end_date(explicit_date), _DURATIONS[duration[1].lower()], fiscal_year_end)


def _number(text, scale):
    if not isinstance(text, str) or not 1 <= len(text) <= 40:
        return None
    match = _AMOUNT.fullmatch(text)
    if not match:
        return None
    negative = bool(match[1] or match[3])
    value = Decimal((match[2] or match[3]).replace(',', '')).scaleb(scale)
    if negative:
        value = -value
    if abs(value) > Decimal('1e20'):
        return None
    return (int(value) if value == value.to_integral_value() else float(value), '-' if negative else '')


def _compatible_sign(concept, value):
    return concept not in {'reported_operating_loss', 'reported_operating_cash_outflow'} or value <= 0


def matching_native_quarter_definition(current, previous):
    """Confirm different period columns share the same directly reported table row."""
    return bool(current and previous and current['column_index'] != previous['column_index'] and all(
        current[key] == previous[key] for key in (
            'field', 'concept', 'taxonomy', 'unit', 'scale', 'unit_evidence', 'table_index', 'row_index', 'row_label',
        )
    ))


def valid_native_table_number(field, *, fiscal_year_end):
    """Recheck the bounded source literals behind a stored numeric observation."""
    if not isinstance(field, Mapping):
        return False
    try:
        if field['reported_numeric_schema'] != NUMBER_SCHEMA or field['taxonomy'] != TABLE_TAXONOMY:
            return False
        label = field['row_label']
        if (not isinstance(label, str) or (field['field'], field['concept']) != _ROWS.get(label.casefold())
                or type(field['value']) not in {int, float} or type(field['scale']) is not int):
            return False
        if any(type(field[name]) is not int or not 0 <= field[name] < bound for name, bound in (
            ('table_index', _MAX_TABLES), ('row_index', _MAX_ROWS), ('column_index', _MAX_COLUMNS),
        )):
            return False
        scale = _unit_scale(field['unit_evidence'], field['unit'])
        if scale is None or scale != field['scale']:
            return False
        result = _number(field['reported_text'], scale)
        if result != (field['value'], field['sign']) or not _compatible_sign(field['concept'], field['value']):
            return False
        header, evidence = field['column_header'], field['period_evidence']
        if not all(isinstance(s, str) and 1 <= len(s) <= 125 for s in (header, evidence)):
            return False
        basis, current, anchor = field.get('comparison_basis'), None, None
        if 'comparison_basis' in field or 'current_period_end' in field:
            if basis not in COMPARISON_BASES:
                return False
            anchor = date.fromisoformat(field['current_period_end'])
            current = _period(anchor, 3, fiscal_year_end)
            if not current or anchor.isoformat() != field['current_period_end']:
                return False
        period = _release_period(header, evidence, fiscal_year_end, basis)
        if period and label.casefold() not in _INCOME_ROWS:
            return False
        if period and basis and _end_date(_ENDED.fullmatch(evidence)[2]) != anchor:
            return False
        period = period or _statement_period(header, evidence, fiscal_year_end)
        if basis and (not period or period[0] != 'quarterly' or period[2] != _comparison_end(current, basis)):
            return False
        return bool(period and (field['period_start'], field['period_end']) == (
            period[1].isoformat(), period[2].isoformat(),
        ))
    except (KeyError, TypeError, ValueError):
        return False


def _grid(rows):
    grid = []
    for row in rows:
        cells, offset = [], 0
        for cell in row:
            end = offset + cell['span']
            cells.append({**cell, 'start': offset, 'end': end})
            offset = end
        if offset > _MAX_COLUMNS:
            return None
        grid.append((cells, offset))
    return grid


def _release_columns(headers, caption, prefix, fiscal_year_end, provisional):
    matches = {m[0] for m in _ENDED.finditer(prefix)
               if m[1].casefold() == caption[2].casefold() and m[2].endswith(caption[1])}
    if len(matches) != 1:
        return []
    evidence, = matches
    matches = []
    for index, (cells, width) in enumerate(headers):
        for cell in cells:
            header = cell['text']
            if not cell['start'] or not _RELEASE_COLUMN.fullmatch(header):
                continue
            period = _release_period(header, evidence, fiscal_year_end)
            if period and (not header.casefold().endswith('a') or provisional):
                matches.append((index, (cell, width, period, header, evidence)))
    if len(matches) != 1:
        return []
    index, current = matches[0]
    cells, width = headers[index]
    results = [current]
    for basis in COMPARISON_BASES:
        previous = [(cell, width, period, cell['text'], evidence) for cell in cells if cell['start']
                    if (period := _release_period(cell['text'], evidence, fiscal_year_end, basis))]
        if len(previous) == 1:
            results.extend(previous)
    return results


def _statement_columns(headers, fiscal_year_end):
    if any(re.search(r'\byear[\s-]+to[\s-]+date\b', cell['text'], re.I)
           for cells, _ in headers for cell in cells):
        return []
    matches = []
    for index, (cells, width) in enumerate(headers):
        for cell in cells:
            header = cell['text']
            if not cell['start']:
                continue
            if period := _statement_period(header, header, fiscal_year_end):
                matches.append((cell, width, period, header, header))
                continue
            duration = _DURATION.match(header)
            if not duration or index + 1 >= len(headers):
                continue
            next_cells, next_width = headers[index + 1]
            if width != next_width:
                continue
            group = header[duration.end():].strip()
            for candidate in next_cells:
                if not cell['start'] <= candidate['start'] < candidate['end'] <= cell['end']:
                    continue
                label = candidate['text']
                explicit_date = ' '.join((group, label)).strip()
                evidence = f'{duration[0]} {explicit_date}'
                if period := _statement_period(explicit_date, evidence, fiscal_year_end):
                    matches.append((candidate, width, period, explicit_date, evidence))
    # One physical data column cannot represent both a quarter and a year-to-date period.
    claimed, durations = set(), set()
    for column, _, (kind, _, end, _), *_ in matches:
        occupied = set(range(column['start'], column['end']))
        identity = (kind, end)
        if claimed & occupied or identity in durations:
            return []
        claimed.update(occupied)
        durations.add(identity)
    return matches


def _column_value(row, width, column):
    cells, row_width = row
    if row_width != width:
        return None
    selected = [cell for cell in cells if cell['start'] < column['end'] and cell['end'] > column['start']]
    if not selected or any(cell['bad'] or not column['start'] <= cell['start'] < cell['end'] <= column['end']
                           for cell in selected):
        return None
    return ' '.join(cell['text'] for cell in selected if cell['text']).strip()


def _statement_rows(caption):
    if not caption:
        return _INCOME_ROWS
    return _CASH_ROWS if 'cash flow' in caption[1].casefold() else _INCOME_ROWS


def _extract_table(table, parser, following, currency, fiscal_year_end):
    nearby = table['nearby']
    captions = list(_STATEMENT_CAPTION.finditer(nearby))
    releases = list(_RELEASE_CAPTION.finditer(nearby))
    if table['bad'] or not 1 <= len(table['rows']) <= _MAX_ROWS or len(captions) + len(releases) != 1:
        return []
    caption = captions[0] if captions else None
    release = releases[0] if releases else None
    scoped = nearby[(caption or release).end():]
    caption_context = nearby[max(0, (caption or release).start() - 50):]
    if _UNSUPPORTED_SCOPE.search(caption_context) or _UNIT_ANNOTATION.sub('', scoped).strip():
        return []
    definitions = _statement_rows(caption)
    rows = _grid(table['rows'])
    if not rows:
        return []
    body_start = next((index for index, (cells, _) in enumerate(rows)
                       if cells and cells[0]['text'] and not _UNIT_ANNOTATION.fullmatch(cells[0]['text'])), 0)
    if not 1 <= body_start <= 12 or not any(
        cells and cells[0]['text'].casefold() in definitions for cells, _ in rows[body_start:]
    ):
        return []
    headers = rows[:body_start]
    if any(cell['bad'] for cells, _ in headers for cell in cells):
        return []
    header_text = ' '.join(cell['text'] for cells, _ in headers for cell in cells)
    unit_context = scoped + ' ' + header_text
    unit_notes = [note[0] for note in _UNIT_ANNOTATION.finditer(unit_context)
                  if re.search(r'\b(?:units?|thousands?|millions?|billions?)\b', note[0], re.I)]
    if len(set(unit_notes)) != 1:
        return []
    unit_evidence = unit_notes[0]
    scale = _unit_scale(unit_evidence, currency)
    # A caption's native currency cannot override a separate conversion or currency column.
    if scale is None or _CURRENCY_MARKER.search(unit_context.replace(unit_evidence, '')):
        return []
    provisional = False
    if release:
        offset = table['visible_offset']
        prefix = _norm(' '.join(parser.all_text[max(0, offset - 2000):offset]))[-14000:]
        provisional = any(int(match[1]) == _ORDINALS[release[2].lower()] and match[2] == release[1]
                          for match in _PROVISIONAL.finditer(following))
        columns = _release_columns(headers, release, prefix, fiscal_year_end, provisional)
    else:
        columns = _statement_columns(headers, fiscal_year_end)
    release_end = columns[0][2][2] if release and columns else None
    unaudited = bool(re.search(r'\(Unaudited\)', unit_context, re.I))
    results = []
    for column, width, (kind, start, end, _), header, evidence in columns:
        fields, gaps = {}, {}
        for index, row in enumerate(rows[body_start:], body_start):
            cells, _ = row
            if not cells or cells[0]['bad']:
                continue
            label = cells[0]['text']
            key = label.casefold()
            if key in _NON_EQUIVALENT_ROWS and definitions is _CASH_ROWS:
                gaps.setdefault(_NON_EQUIVALENT_ROWS[key], 'non_equivalent_reported_component')
            if key not in definitions:
                continue
            field, concept = definitions[key]
            if field in fields or field in gaps and gaps[field] != 'non_equivalent_reported_component':
                fields.pop(field, None)
                gaps[field] = 'conflicting_reported_rows'
                continue
            raw = _column_value(row, width, column)
            result = _number(raw, scale)
            if result is None or not _compatible_sign(concept, result[0]):
                gaps[field] = 'direct_numeric_cell_unavailable'
                continue
            gaps.pop(field, None)
            value, sign = result
            fields[field] = dict(
                field=field, taxonomy=TABLE_TAXONOMY, concept=concept, unit=currency, value=value,
                period_start=start.isoformat(), period_end=end.isoformat(), reported_numeric_schema=NUMBER_SCHEMA,
                reported_text=raw, scale=scale, sign=sign, table_index=table['index'], row_index=index,
                column_index=column['start'], row_label=label, column_header=header,
                period_evidence=evidence, unit_evidence=unit_evidence,
            )
        results.append(dict(kind=kind, start=start, end=end, fields=fields, gaps=gaps, table_index=table['index'],
                            provisional=bool(provisional and end == release_end), unaudited=unaudited))
    return results


def _period_row(matching, currency, *, current=None, basis=None):
    fields, gaps = {}, {}
    if current:
        current_fields = current['fields']
        tables = {field['table_index'] for field in current_fields.values()}
        matching = [item for item in matching if item['table_index'] in tables]
        if not matching:
            return None
    for candidate in matching:
        observations, withheld = candidate['fields'], candidate['gaps']
        if current:
            observations = {name: field for name, field in observations.items()
                            if matching_native_quarter_definition(current_fields.get(name), field)}
        for name, reason in withheld.items():
            if reason != 'non_equivalent_reported_component' and name in fields:
                fields.pop(name)
                gaps[name] = 'conflicting_reported_rows'
            else:
                gaps.setdefault(name, reason)
        for name, field in observations.items():
            if name in fields or name in gaps and gaps[name] != 'non_equivalent_reported_component':
                fields.pop(name, None)
                gaps[name] = 'conflicting_reported_rows'
            else:
                gaps.pop(name, None)
                fields[name] = field
    for name in _FIELDS:
        if name not in fields:
            gaps.setdefault(name, 'direct_reported_row_unavailable')
    first = matching[0]
    row = dict(kind=first['kind'], period_start=first['start'].isoformat(), period_end=first['end'].isoformat(),
               unit=currency, fields=fields, withheld_fields=gaps,
               provisional=any(item['provisional'] for item in matching),
               unaudited=any(item['unaudited'] for item in matching))
    if current:
        comparison = {'comparison_basis': basis, 'current_period_end': current['period_end']}
        row.update(comparison, fields={name: dict(field, **comparison) for name, field in fields.items()})
    return row


def parse_native_quarter_tables(raw: bytes, *, currency: str, fiscal_year_end: str) -> dict:
    """Read separate reported quarter, same-end YTD, and comparable earlier-quarter columns."""
    held = {'status': 'withheld', 'reason': 'qualified_consolidated_native_period_unavailable',
            'periods': [], 'comparative_periods': []}
    if (not isinstance(currency, str) or currency not in _CURRENCY or not isinstance(raw, bytes)
            or not 0 < len(raw) <= _MAX_BYTES or b'\0' in raw or b'<!entity' in raw.lower()):
        return held
    try:
        parser = _NativeTables()
        parser.feed(raw.decode('utf-8-sig'))
        parser.close()
        candidates = []
        for index, table in enumerate(parser.tables):
            start = table['visible_end']
            next_offset = (parser.tables[index + 1]['visible_offset'] if index + 1 < len(parser.tables)
                           else len(parser.all_text))
            following = _norm(' '.join(parser.all_text[start:min(start + 80, next_offset)]))[:600]
            candidates.extend(_extract_table(table, parser, following, currency, fiscal_year_end))
        latest = max((period['end'] for period in candidates), default=None)
        periods = []
        for kind in ('quarterly', 'cumulative'):
            matching = [item for item in candidates if item['kind'] == kind and item['end'] == latest]
            if matching:
                periods.append(_period_row(matching, currency))
        if not any(period['fields'] for period in periods):
            return held
        comparative = []
        if periods[0]['kind'] == 'quarterly' and periods[0]['fields']:
            for basis in COMPARISON_BASES:
                target = _comparison_end(_period(latest, 3, fiscal_year_end), basis)
                matching = [item for item in candidates if item['kind'] == 'quarterly' and item['end'] == target]
                if matching:
                    row = _period_row(matching, currency, current=periods[0], basis=basis)
                    if row and row['fields']:
                        comparative.append(row)
        return {'status': 'inspection_only', 'reason': None, 'periods': periods, 'comparative_periods': comparative}
    except (ValueError, RecursionError):
        return held
