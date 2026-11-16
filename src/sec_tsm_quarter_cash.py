"""Private cash-flow reconciliation for TSM's September 2026 SEC filing scope."""
from collections.abc import Mapping
from decimal import Decimal, ROUND_HALF_UP

from src.company_sec_online_preview import _utc_timestamp
from src.online_filing_context import _now, _ref


_ARCHIVE = 'https://www.sec.gov/Archives/edgar/data/1046179/'


def _source(accession_end, filed, report_date, cover, exhibit):
    accession = '0001046179-26-' + accession_end
    base = _ARCHIVE + accession.replace('-', '') + '/'
    return dict(accession=accession, filed=filed, report_date=report_date, primary_url=base + cover,
                source_url=base + exhibit)


CASH_SOURCES = {
    'six_months': _source('000541', '2026-08-14', '2026-06-30', 'tsm-fsx20260814x6k.htm', 'a2026q2consolidatedreport-.htm'),
    'nine_months': _source('000801', '2026-11-13', '2026-09-30', 'tsm-fsx20261113x6k.htm', 'a2026q3consolidatedreport-.htm'),
    'presentation': _source('000726', '2026-10-15', '2026-09-30', 'tsm-20261015x6k.htm', 'a3q26presentatione.htm'),
}
CASH_SCOPE = dict(ticker='TSM', sec_cik='0001046179', form='6-K', unit='TWD', period_end='2026-09-30',
                  accession=CASH_SOURCES['nine_months']['accession'], source_url=CASH_SOURCES['nine_months']['source_url'])
FIELDS = ('cash_from_operations', 'capital_expenditures')


def is_reviewed_cash_scope(current):
    return isinstance(current, Mapping) and all(current.get(key) == value for key, value in CASH_SCOPE.items())


def cash_filing_events(verified):
    """Match the reviewed exhibits to the exact issuer's SEC filing inventory."""
    reports = verified['earnings_reports']
    events = {}
    for key, source in CASH_SOURCES.items():
        matches = [row for row in reports if row['accession'] == source['accession']]
        if len(matches) != 1:
            return None
        event = matches[0]
        if (event['form'] != '6-K' or event['source_url'] != source['primary_url']
                or event['filed'] != source['filed'] or event['report_date'] != source['report_date']):
            return None
        events[key] = event
    for key in ('six_months', 'nine_months'):
        event = events[key]
        if any(row['amendment'] and row['report_date'] == event['report_date']
               and _utc_timestamp(row['accepted_at']) >= _utc_timestamp(event['accepted_at']) for row in reports):
            return None
    return events


def valid_cash_reconciliation(evidence, *, current, as_of):
    if (not is_reviewed_cash_scope(current) or not isinstance(evidence, Mapping)
            or set(evidence) != {'receipts', 'inputs'}):
        return False
    receipts, inputs = evidence['receipts'], evidence['inputs']
    if (not isinstance(receipts, Mapping) or set(receipts) != set(CASH_SOURCES)
            or not isinstance(inputs, Mapping) or set(inputs) != set(CASH_SOURCES)):
        return False
    for key, source in CASH_SOURCES.items():
        receipt = receipts[key]
        values = inputs[key]
        if (_ref(receipt, source['source_url'], as_of, historical=True) != receipt
                or not isinstance(receipt, Mapping) or receipt['observed_at'][:10] < source['filed']
                or not isinstance(values, Mapping) or set(values) != set(FIELDS)
                or any(type(value) is not int or abs(value) >= 10**18 for value in values.values())
                or values['capital_expenditures'] < 0):
            return False
    if inputs['nine_months']['capital_expenditures'] < inputs['six_months']['capital_expenditures']:
        return False
    nine_months = receipts['nine_months']
    return all(nine_months[key] == current.get(key) for key in ('observed_at', 'payload_sha256'))


def load_cash_reconciliation(verified, current, latest_raw, latest_receipt, *, read, as_of):
    if not is_reviewed_cash_scope(current):
        return None
    events = cash_filing_events(verified)
    if events is None:
        return None
    from src.sec_tsm_cash_tables import parse_presentation_cash_flows, parse_reviewed_cash_flows

    try:
        june_raw, june_receipt = read(CASH_SOURCES['six_months']['source_url'], max_bytes=5 * 1024 * 1024)
        slides_raw, slides_receipt = read(CASH_SOURCES['presentation']['source_url'], max_bytes=64 * 1024)
        receipts = {'six_months': june_receipt, 'presentation': slides_receipt, 'nine_months': latest_receipt}
        if any(_utc_timestamp(receipts[key]['observed_at']) < _utc_timestamp(event['accepted_at'])
               for key, event in events.items()):
            return None
        inputs = {
            'six_months': parse_reviewed_cash_flows(june_raw, period_end='2026-06-30'),
            'nine_months': parse_reviewed_cash_flows(latest_raw, period_end='2026-09-30'),
            'presentation': parse_presentation_cash_flows(slides_raw),
        }
        evidence = dict(receipts=receipts, inputs=inputs)
        return evidence if valid_cash_reconciliation(evidence, current=current, as_of=_now(as_of)) else None
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RuntimeError):
        return None


def cash_flow_rows(evidence):
    """Calculate quarter-only amounts from cumulative inputs, then compare display precision."""
    inputs = evidence['inputs']
    rows = {}
    for field in FIELDS:
        june, september, preliminary = (inputs[key][field] for key in ('six_months', 'nine_months', 'presentation'))
        quarter = september - june
        at_presentation_precision = (Decimal(quarter) / 10_000).to_integral_value(rounding=ROUND_HALF_UP)
        rows[field] = dict(six_months_thousands=june, nine_months_thousands=september, quarter_thousands=quarter,
                           presentation_cent_billions=preliminary, matches_presentation=at_presentation_precision == preliminary)
    return rows


def matches_reviewed_cumulative_cash(evidence, periods):
    """Tie the September operand to the independently normalized nine-month cash flow."""
    for row in periods:
        if row.get('period_start') != '2026-01-01' or row.get('period_end') != CASH_SCOPE['period_end']:
            continue
        field = (row.get('fields') or {}).get('cash_from_operations')
        if is_reviewed_cash_scope(field):
            return field['value'] == 1000 * evidence['inputs']['nine_months']['cash_from_operations']
    return False
