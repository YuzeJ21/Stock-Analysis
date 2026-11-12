"""Exact 6-K interim bank observations, bound to IBN's verified SEC identity."""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import timedelta
import re
from urllib.error import HTTPError

from src.company_sec_online_preview import _iso_date, _utc_timestamp
from src.online_company_identity import _mode_reason
from src.online_filing_context import _digest, _now, _ref, build_filing_inventory
from src.sec_exact_filing import MAP_URL, RIGHTS
from src.sec_ibn_interim_tables import ACCOUNTING_BASIS, BASIS_EVIDENCE, DEFINITIONS, NUMBER_SCHEMA, UNIT, valid_ibn_interim_number
from src.sec_online_ibn_evidence import (
    CIK, SUBMISSIONS_URL, TICKER, _FLAGS, _receipt_ref, _sealed, _verified_inventory,
    valid_saved_ibn_annual, validated_ibn_archive_annual,
)
from src.sec_online_native_quarter_evidence import (
    MAX_PRIMARY_REQUESTS, _Cover, _candidate_events, _clean, _read_document, _same_publication,
    _valid_duration, _valid_source_url,
)
from src.sec_online_quarter_evidence import _REF_KEYS, _held

SCHEMA = 'sec-online-ibn-interim-v1'
SOURCE_ID = 'sec_archive_ibn_interim_html'
_RECEIPT_SOURCE = 'exact_ibn_interim_receipt'
_FORMS = frozenset({'6-K', '6-K/A'})
_EVENT_KEYS = ('accession', 'form', 'filed', 'accepted_at', 'report_date', 'primary_document', 'source_url')
_METADATA = (*_EVENT_KEYS, 'ticker', 'sec_cik', 'source_id', 'observed_at', 'payload_sha256',
             'rights_status', 'unit', 'accounting_basis', 'source_scale', 'period_kind')
_KINDS = {'quarterly': 'quarterly', 'cumulative': 'interim'}
_FIELDS = frozenset(DEFINITIONS)
_PACKET_KEYS = set(_METADATA) | set(_FLAGS) | {'schema_version', 'status', 'reason', 'period_end', 'periods',
    'source_receipts', 'archive_identity', 'reviewed_preceding', 'withheld_fields', 'basis_evidence', 'packet_digest'}
_ROW_KEYS = set(_METADATA) | {'kind', 'period_start', 'period_end', 'fields', 'withheld_fields',
                             'unaudited', 'status', 'reason'}
_FIELD_KEYS = set(_METADATA) | {'field', 'label', 'definition', 'value', 'reported_text', 'reported_numeric_schema',
    'scale', 'sign', 'table_index', 'row_index', 'column_span', 'table_caption', 'period_start', 'period_end',
    'period_evidence', 'unit_evidence', 'source_ref'}
_WITHHELD = dict.fromkeys(('revenue', 'operating_income', 'net_interest_income', 'free_cash_flow', 'valuation'),
                         'not_a_direct_equivalent_in_selected_consolidated_statements')
_CONSOLIDATED = re.compile(r'\bconsolidated financial results\b', re.I)
_RESULTS = re.compile(r'\b(?:unaudited\s+financial\s+results\s*\(standalone\s+and\s+consolidated\)|'
                      r'(?:three|six|nine)\s+months\s+ended\b|quarter\s+ended\b)', re.I)
_REVISION = re.compile(r'\b(?:amended|corrected|correction|corrigendum|revised|restated|replaced|withdrawn)\b.{0,100}'
                       r'\b(?:financial\s+results|statements?|financial\s+report)\b', re.I)
_SOLE_NOTICE = re.compile(r'\btable\s+of\s+contents\s+items:\s*1\.\s*(?:other\s+news|others)\s+other\s+news\b', re.I)
_UNRELATED = {
    'gst_tax_appeal': (re.compile(r'\bgoods\s+and\s+services\s+tax\b', re.I), re.compile(r'\border\s+in\s+appeal\b', re.I)),
    'credit_rating': (re.compile(r'\bre-affirmed\s+the\s+credit\s+ratings\b', re.I), re.compile(r'\b(?:ICRA|CARE Ratings)\b', re.I)),
    'earnings_call_transcripts': (re.compile(r'\btranscripts?\s+of\s+the\s+(?:call|media\s+conference|earnings\s+call)\b', re.I),
                                  re.compile(r'\b(?:earnings\s+call|call\s+with\s+analysts)\b', re.I)),
    'earnings_call_recordings': (re.compile(r'\baudio\s+recordings?\s+of\s+(?:the\s+)?(?:call|earnings\s+call)\b', re.I),
                                 re.compile(r'\buploaded\s+on\s+the\s+website\s+of\s+the\s+bank\b', re.I)),
    'investor_presentation': (re.compile(r'\bsubject:\s*investor\s+presentation\b', re.I),
                              re.compile(r'\binvestor\s+presentation\b.{0,200}\bearnings\s+call\b', re.I)),
}


def _classify(raw, event):
    parser = _Cover()
    parser.feed(raw.decode('utf-8-sig'))
    parser.close()
    text = _clean(parser.text)
    forms = {form.upper() for form in re.findall(r'\bform\s+(6-k(?:/a)?)\b', text, re.I)}
    if (parser.has_base or event['form'] not in forms or event['form'] == '6-K' and '6-K/A' in forms
            or not re.search(r'\bicici\s+bank\s+limited\b', text[:10000], re.I)):
        return None
    if _CONSOLIDATED.search(text) and _RESULTS.search(text):
        return 'statement'
    if event['amendment'] or _REVISION.search(text) or _CONSOLIDATED.search(text) or not _SOLE_NOTICE.search(text):
        return None
    if any(re.search(r'\b(?:exhibit|financial\s+statements?)\b', label, re.I) for label, _ in parser.rows):
        return None
    reasons = [reason for reason, patterns in _UNRELATED.items() if all(pattern.search(text) for pattern in patterns)]
    return reasons[0] if len(reasons) == 1 else None


def _matched_submissions(annual, verified, ticker_map_receipt, submissions_receipt, now):
    mapping = _ref(ticker_map_receipt, MAP_URL, now)
    profile = _ref(submissions_receipt, SUBMISSIONS_URL, now)
    if (not mapping or not profile or ticker_map_receipt.get('status') != 'ready'
            or submissions_receipt.get('status') != 'ready'
            or [_receipt_ref(mapping), _receipt_ref(profile)] != annual['source_receipts'][:2]):
        return False
    return build_filing_inventory(submissions_receipt, ticker=TICKER, expected_cik=CIK,
                                  as_of=now)['packet_digest'] == verified['packet_digest']


def _is_non_xbrl(event, submissions_receipt):
    recent = submissions_receipt['payload']['filings']['recent']
    indexes = [i for i, accession in enumerate(recent['accessionNumber']) if accession == event['accession']]
    if len(indexes) != 1:
        return False
    index = indexes[0]
    flags = [recent[key][index] for key in ('isInlineXBRL', 'isXBRL')]
    return all(type(flag) is int and flag == 0 for flag in flags)


def _event_matches(packet, verified, annual, now, *, historical):
    anchor_time = _utc_timestamp(verified['observed_at'])
    events = _candidate_events(verified, anchor_time)
    index = next((i for i, item in enumerate(events[:MAX_PRIMARY_REQUESTS]) if item['accession'] == packet['accession']), None)
    if index is None:
        return False
    event = events[index]
    end, filed = _iso_date(packet['period_end']), _iso_date(event['filed'])
    accepted = _utc_timestamp(event['accepted_at'])
    if (not end or not _iso_date(annual['period_end']) < end <= min(filed, accepted.date())
            or any(_same_publication(a, b) for a, b in zip(events[:index + 1], events[1:index + 2]))
            or any(packet[key] != event[key] for key in _EVENT_KEYS)
            or not _valid_source_url(event['source_url'], CIK, event['accession'])):
        return False
    refs = packet['source_receipts']
    reviewed = packet['reviewed_preceding']
    if (packet['archive_identity'] != annual['archive_identity'] or not isinstance(refs, list) or len(refs) != 3
            or refs[:2] != annual['source_receipts'][:2] or refs[-1] != _receipt_ref(packet)
            or not _ref(refs[-1], event['source_url'], now, historical)
            or not isinstance(reviewed, list) or len(reviewed) != index):
        return False
    stamps = [_utc_timestamp(ref['observed_at']) for ref in refs[:2]]
    for record, earlier in zip(reviewed, events[:index]):
        if (not isinstance(record, Mapping) or set(record) != {'accession', 'reason', 'receipt'}
                or record['accession'] != earlier['accession'] or record['reason'] not in _UNRELATED
                or earlier['amendment'] or not _valid_source_url(earlier['source_url'], CIK, earlier['accession'])
                or set(record['receipt']) != set(_REF_KEYS)
                or not _ref(record['receipt'], earlier['source_url'], now, historical)):
            return False
        stamp = _utc_timestamp(record['receipt']['observed_at'])
        if stamp < _utc_timestamp(earlier['accepted_at']):
            return False
        stamps.append(stamp)
    stamps.append(_utc_timestamp(refs[-1]['observed_at']))
    return stamps == sorted(stamps) and stamps[-1] >= accepted and stamps[-1] - stamps[0] <= timedelta(hours=24)


def valid_ibn_interim_field(field, *, context, row, field_name):
    """Revalidate a typed numeric literal and its exact 6-K row ownership."""
    try:
        return (isinstance(field, Mapping) and set(field) == _FIELD_KEYS
                and field_name in _FIELDS and field.get('field') == field_name
                and field.get('reported_numeric_schema') == NUMBER_SCHEMA
                and field.get('ticker') == context.get('ticker') == TICKER and field.get('sec_cik') == context.get('sec_cik') == CIK
                and all(field[key] == row[key] for key in (*_METADATA, 'period_start', 'period_end'))
                and field.get('source_ref') == row['source_url'] and valid_ibn_interim_number(field))
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError):
        return False


def _valid_periods(packet):
    periods = packet['periods']
    if (not isinstance(periods, list) or not 1 <= len(periods) <= 2
            or [row.get('kind') for row in periods] != list(_KINDS)[:len(periods)]):
        return False
    for row in periods:
        fields, withheld = row.get('fields'), row.get('withheld_fields')
        if (set(row) != _ROW_KEYS or row.get('status') != 'available' or row.get('reason') is not None
                or row.get('period_end') != packet['period_end'] or row.get('unaudited') is not True
                or not _valid_duration(row, '0331') or any(row.get(key) != packet[key] for key in _METADATA)
                or not isinstance(fields, Mapping) or not fields or not isinstance(withheld, Mapping)
                or set(fields) | set(withheld) != _FIELDS or set(fields) & set(withheld)
                or row['kind'] == 'quarterly' and {'cash_from_operations', 'fixed_asset_purchases'} & set(fields)
                or any(not isinstance(reason, str) or not re.fullmatch(r'[a-z0-9_]{1,120}', reason) for reason in withheld.values())
                or any(not valid_ibn_interim_field(field, context=packet, row=row, field_name=name) for name, field in fields.items())):
            return False
    return True


def _verified_packet(packet, verified, annual, now, *, historical=False):
    return (isinstance(packet, Mapping) and set(packet) == _PACKET_KEYS
            and packet['schema_version'] == SCHEMA and packet['status'] == 'inspection_only' and packet['reason'] is None
            and packet['ticker'] == TICKER and packet['sec_cik'] == CIK and packet['form'] in _FORMS
            and packet['source_id'] == SOURCE_ID and packet['rights_status'] == RIGHTS and packet['unit'] == UNIT
            and packet['accounting_basis'] == ACCOUNTING_BASIS and packet['basis_evidence'] == BASIS_EVIDENCE
            and packet['source_scale'] == 'crore'
            and packet['period_kind'] == 'interim' and packet['withheld_fields'] == _WITHHELD
            and all(packet[key] is False for key in _FLAGS) and _sealed(packet)
            and _event_matches(packet, verified, annual, now, historical=historical) and _valid_periods(packet))


def validated_ibn_archive_interim(financial, *, ticker=None, expected_cik=None, inventory=None, as_of=None):
    """Read the current IBN interim report without borrowing Companyfacts ownership."""
    try:
        if (not isinstance(financial, Mapping) or (financial.get('ticker'), financial.get('sec_cik')) != (TICKER, CIK)
                or ticker not in {None, TICKER} or expected_cik not in {None, CIK} or _mode_reason('research')):
            return None
        now = _now(as_of)
        verified = _verified_inventory(financial.get('filing_inventory') if inventory is None else inventory, as_of=now)
        annual = validated_ibn_archive_annual(financial, inventory=verified, as_of=now) if verified else None
        packet = financial.get('ibn_archive_interim')
        return deepcopy(packet) if annual and _verified_packet(packet, verified, annual, now) else None
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError):
        return None


def valid_saved_ibn_interim(archive, *, context):
    """Verify normalized saved 6-K evidence against the annual identity and scoped coverage."""
    try:
        now = _utc_timestamp(context.get('observed_at'))
        if not now or (context.get('ticker'), context.get('sec_cik')) != (TICKER, CIK):
            return False
        annual = context['business_trend'].get('bank_annual')
        if not valid_saved_ibn_annual(annual, context=context):
            return False
        verified = _verified_inventory(context.get('filing_inventory'), as_of=now, historical=True)
        if not verified or not _verified_packet(archive, verified, annual, now, historical=True):
            return False
        refs = [ref for ref in context['source_receipts'] if isinstance(ref, Mapping) and ref.get('source') == _RECEIPT_SOURCE]
        if refs != [dict(ref, source=_RECEIPT_SOURCE, rights_status=RIGHTS) for ref in archive['source_receipts']]:
            return False
        coverage = context['filing_coverage']
        for row in archive['periods']:
            kind = _KINDS[row['kind']]
            current = coverage['current'][kind]
            anchor = current.get('anchor') or {}
            if (current.get('status') != 'corroborated' or current.get('reason') != 'exact_ibn_interim_table_and_filing'
                    or current.get('source_id') != SOURCE_ID or current.get('rights_status') != RIGHTS
                    or current != coverage['periods'][kind].get(row['period_end'])
                    or anchor.get('period_kind') != kind or anchor.get('period_basis') != 'exact_ibn_interim_table'
                    or any(anchor.get(key) != row[key] for key in (*_EVENT_KEYS, 'period_start', 'period_end'))):
                return False
        return True
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError):
        return False


def _build_packet(parsed, event, annual, receipt, reviewed):
    metadata = {key: event[key] for key in _EVENT_KEYS}
    metadata.update(ticker=TICKER, sec_cik=CIK, source_id=SOURCE_ID, **_receipt_ref(receipt),
                    rights_status=RIGHTS, unit=UNIT, accounting_basis=parsed['accounting_basis'],
                    source_scale='crore', period_kind='interim')
    periods = []
    for row in parsed['periods']:
        if not row['fields']:
            continue
        fields = {name: dict(value, **metadata, source_ref=receipt['source_url']) for name, value in row['fields'].items()}
        selected = {key: row[key] for key in ('kind', 'period_start', 'period_end', 'withheld_fields', 'unaudited')}
        periods.append(dict(selected, **metadata, fields=fields, status='available', reason=None))
    result = dict(metadata, **_FLAGS, schema_version=SCHEMA, status='inspection_only', reason=None,
                  period_end=periods[0]['period_end'], periods=periods, withheld_fields=_WITHHELD.copy(),
                  source_receipts=[*annual['source_receipts'][:2], _receipt_ref(receipt)],
                  archive_identity=deepcopy(annual['archive_identity']), reviewed_preceding=reviewed,
                  basis_evidence=parsed['basis_evidence'])
    result['packet_digest'] = _digest(result)
    return result


def fetch_ibn_archive_interim(financial, *, user_agent, ticker_map_receipt, submissions_receipt,
                               source_fetcher=None, observed_at=None):
    """Inspect a bounded sequence of recent primary 6-K documents for IBN."""
    def hold(reason):
        return _held(TICKER, CIK, reason, schema=SCHEMA)

    try:
        if (not isinstance(financial, Mapping) or (financial.get('ticker'), financial.get('sec_cik')) != (TICKER, CIK)
                or _mode_reason('research')):
            return hold('ibn_interim_scope_unavailable')
        now = _now(observed_at)
        verified = _verified_inventory(financial.get('filing_inventory'), as_of=now)
        annual = validated_ibn_archive_annual(financial, inventory=verified, as_of=now) if verified else None
        if not annual:
            return hold('ibn_interim_bank_identity_unverified')
        if not _matched_submissions(annual, verified, ticker_map_receipt, submissions_receipt, now):
            return hold('ibn_interim_source_receipts_unverified')
        if not isinstance(user_agent, str) or not user_agent.strip() or any(char in user_agent for char in '\r\n'):
            return hold('ibn_interim_user_agent_required')
        reviewed = []
        events = _candidate_events(verified, _utc_timestamp(verified['observed_at']))
        for index, event in enumerate(events[:MAX_PRIMARY_REQUESTS]):
            if index + 1 < len(events) and _same_publication(event, events[index + 1]):
                return hold('ibn_interim_same_timestamp_versions_unresolved')
            unresolved = 'ibn_interim_amendment_unresolved' if event['amendment'] else 'ibn_interim_newer_filing_scope_unresolved'
            if not _valid_source_url(event['source_url'], CIK, event['accession']) or not _is_non_xbrl(event, submissions_receipt):
                return hold(unresolved)
            raw, receipt = _read_document(event['source_url'], user_agent=user_agent, source_fetcher=source_fetcher,
                                           observed_at=observed_at)
            classification = _classify(raw, event)
            if not classification:
                return hold(unresolved)
            if classification != 'statement':
                reviewed.append(dict(accession=event['accession'], reason=classification, receipt=_receipt_ref(receipt)))
                continue
            from src.sec_ibn_interim_tables import parse_ibn_interim_tables

            parsed = parse_ibn_interim_tables(raw)
            if parsed.get('status') != 'inspection_only' or parsed.get('accounting_basis') != ACCOUNTING_BASIS:
                return hold('ibn_interim_amendment_unresolved' if event['amendment'] else 'ibn_interim_reporting_basis_unverified')
            packet = _build_packet(parsed, event, annual, receipt, reviewed)
            if not _verified_packet(packet, verified, annual, _now(observed_at)):
                return hold('ibn_interim_exact_html_unavailable')
            return packet
        return hold('ibn_interim_candidate_limit' if len(events) > MAX_PRIMARY_REQUESTS else 'ibn_interim_results_filing_unverified')
    except HTTPError as exc:
        return hold('sec_archive_access_limited' if exc.code in {403, 429, 503} else 'sec_archive_http_unavailable')
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError, OSError, RuntimeError):
        return hold('ibn_interim_exact_html_unavailable')
