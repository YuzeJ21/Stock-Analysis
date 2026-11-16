"""Matched cumulative operating cash from NEE's exact June and September 10-Qs."""
from collections.abc import Mapping
import hashlib

from src.company_sec_online_preview import _utc_timestamp
from src.online_filing_context import _now, _ref
from src.sec_exact_filing import RIGHTS, SOURCE_ID
from src.sec_inline_filing import extract_inline_filing, valid_numeric_proof


TICKER, CIK = 'NEE', '0000753308'
SCHEMA = 'sec-nee-q3-operating-cash-v1'
NUMERIC_SCHEMA = 'sec-nee-cumulative-operating-cash-number-v1'
BASE = 'https://www.sec.gov/Archives/edgar/data/753308/'
SOURCES = {
    'six_months': ('0000753308-26-000060', '2026-06-30', '2026-07-24'),
    'nine_months': ('0000753308-26-000081', '2026-09-30', '2026-10-21'),
}
_REF_KEYS = ('source_url', 'observed_at', 'payload_sha256')
_ANCHOR_KEYS = ('accession', 'form', 'period_end', 'filed', 'accepted_at', 'primary_document', 'source_url')
_CFO = dict(field='cash_from_operations', taxonomy='us-gaap', namespace_uri='http://fasb.org/us-gaap/2026',
    concept='NetCashProvidedByUsedInOperatingActivities', unit='USD', unit_id='usd', context_id='c-1',
    period_start='2026-01-01', fact_id='f-345', rights_status=RIGHTS, scale=6, decimals='-6',
    sign='', transformation='num-dot-decimal')


def _filing_pair(inventory):
    """Both reviewed versions must be current for their periods."""
    if (inventory['ticker'], inventory['sec_cik']) != (TICKER, CIK):
        return None
    rows = inventory['periods']['quarterly']
    selected = {}
    for key, (accession, end, filed) in SOURCES.items():
        version = [row for row in rows if row['period_end'] == end]
        doc = 'nee-' + end.replace('-', '') + '.htm'
        url = BASE + accession.replace('-', '') + '/' + doc
        if (len(version) != 1 or any(gap['period_end'] == end and gap['form'] in {'10-Q', '10-Q/A'}
                                     for gap in inventory.get('metadata_gaps', []))):
            return None
        anchor = version[0]
        if (anchor['accession'], anchor['form'], anchor['filed'], anchor['source_url']) != (accession, '10-Q', filed, url):
            return None
        selected[key] = anchor
    return selected if inventory['latest']['quarterly'] == selected['nine_months'] else None


def _operand(packet, anchor):
    if (packet.get('nee_cumulative_cfo_verified') is not True or packet.get('ticker') != TICKER
            or packet.get('sec_cik') != CIK or packet.get('source_id') != SOURCE_ID or packet.get('unit') != 'USD'
            or any(packet.get(key) != anchor[key] for key in _ANCHOR_KEYS)):
        return None
    field = next((row['fields'].get('cash_from_operations') for row in packet['periods']
                  if row['kind'] == 'cumulative'), None)
    if (not field or any(field.get(key) != value for key, value in _CFO.items())
            or field.get('period_end') != anchor['period_end'] or field.get('source_ref') != anchor['source_url'] + '#f-345'
            or not valid_numeric_proof(field)):
        return None
    return {**{key: packet[key] for key in _REF_KEYS}, 'value': field['value'],
            'reported_text': field['raw_text'], 'reported_numeric_schema': NUMERIC_SCHEMA}


def _valid_pair(evidence, events, september_receipt, *, as_of, historical):
    if (not events or not isinstance(evidence, Mapping)
            or set(evidence) != {'schema_version', *SOURCES} or evidence['schema_version'] != SCHEMA):
        return False
    for key, anchor in events.items():
        row = evidence[key]
        if (not isinstance(row, Mapping) or set(row) != {*_REF_KEYS, 'reported_numeric_schema', 'reported_text', 'value'}
                or row['reported_numeric_schema'] != NUMERIC_SCHEMA or type(row['value']) is not int
                or not 0 < row['value'] < 10**16 or row['value'] % 1_000_000
                or not _ref(row, anchor['source_url'], as_of, historical)
                or _utc_timestamp(row['observed_at']) < _utc_timestamp(anchor['accepted_at'])
                or not valid_numeric_proof(dict(_CFO, raw_text=row['reported_text'], value=row['value']))):
            return False
    september = evidence['nine_months']
    return (all(september[key] == september_receipt.get(key) for key in _REF_KEYS)
            and _utc_timestamp(september['observed_at']) <= _utc_timestamp(evidence['six_months']['observed_at']))


def load_nee_quarter_cash(inventory, september, *, read, as_of):
    events = _filing_pair(inventory)
    nine = _operand(september, events['nine_months']) if events else None
    if not nine:
        return None
    anchor = events['six_months']
    try:
        raw, receipt = read(anchor['source_url'])
        selection = dict(status='selected', ticker=TICKER, sec_cik=CIK, period_kind='quarterly',
                         source_receipts=september['source_receipts'][:2],
                         **{key: anchor[key] for key in _ANCHOR_KEYS})
        six = _operand(extract_inline_filing(raw, selection, receipt), anchor)
        evidence = dict(schema_version=SCHEMA, six_months=six, nine_months=nine)
        return evidence if _valid_pair(evidence, events, nine, as_of=_now(as_of), historical=False) else None
    except (KeyError, OSError, ValueError, RuntimeError, TypeError, RecursionError):
        return None


def read_nee_cash_document(url, *, user_agent, source_fetcher=None, observed_at=None):
    from src.sec_exact_filing import _fetch_html

    max_bytes = 5 * 1024 * 1024
    raw, _, final_url = (source_fetcher(url, user_agent) if source_fetcher
                         else _fetch_html(url, user_agent, max_bytes=max_bytes))
    if not isinstance(raw, bytes) or not 0 < len(raw) <= max_bytes or final_url != url:
        raise ValueError('Unverified historical SEC document')
    return raw, dict(status='ready', source_url=url, observed_at=_now(observed_at).strftime('%Y-%m-%dT%H:%M:%SZ'),
                     payload_sha256=hashlib.sha256(raw).hexdigest())


def validated_live_nee_quarter_cash(evidence, inventory, september, *, as_of):
    if not evidence:
        return None
    events = _filing_pair(inventory)
    if (events and _valid_pair(evidence, events, september, as_of=_now(as_of), historical=False)
            and _operand(september, events['nine_months']) == evidence['nine_months']):
        return evidence
    return None


def valid_saved_nee_quarter_cash(evidence, *, context):
    from src.online_filing_context import validated_filing_inventory

    now = _utc_timestamp(context.get('observed_at'))
    refs = context.get('source_receipts')
    if (context.get('ticker'), context.get('sec_cik')) != (TICKER, CIK) or not now or not isinstance(refs, list):
        return False
    inventory = validated_filing_inventory(context.get('filing_inventory'), ticker=TICKER, expected_cik=CIK,
                                          as_of=now, allow_historical=True)
    events = _filing_pair(inventory) if inventory else None
    if not events:
        return False

    def matches(key, source):
        return [row for row in refs if isinstance(row, Mapping) and row.get('source') == source
                and row.get('source_url') == events[key]['source_url']
                and row.get('rights_status') == RIGHTS]

    nine = matches('nine_months', 'exact_quarter_receipt')
    six = matches('six_months', 'exact_nee_cash_baseline_receipt')
    return (len(nine) == len(six) == 1
            and _valid_pair(evidence, events, nine[0], as_of=now, historical=True)
            and all(evidence['six_months'][key] == six[0].get(key) for key in _REF_KEYS))


def nee_cash_baseline_receipt(evidence):
    return dict({key: evidence['six_months'][key] for key in _REF_KEYS}, source='exact_nee_cash_baseline_receipt',
                rights_status=RIGHTS)
