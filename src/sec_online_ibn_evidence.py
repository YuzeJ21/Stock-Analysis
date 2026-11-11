"""Private IBN non-XBRL annual evidence, independent of Companyfacts."""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import timedelta
import re

from src.company_sec_online_preview import _iso_date, _utc_timestamp
from src.online_company_identity import _mode_reason
from src.online_filing_context import _digest, _now, _ref, build_filing_inventory, validated_filing_inventory
from src.sec_exact_filing import BANK_SICS, MAP_URL, RIGHTS, fetch_sec_filing_preview, select_sec_filing
from src.sec_html_bank import CIK, DEFINITIONS, SOURCE_ID, WITHHELD, validated_bank_html
from src.sec_online_quarter_evidence import _ANCHOR_KEYS, _REF_KEYS, _held, _json

SCHEMA = 'sec-online-ibn-annual-v1'
NUMBER_SCHEMA = 'sec-ibn-bank-number-v1'
TICKER = 'IBN'
SUBMISSIONS_URL = f'https://data.sec.gov/submissions/CIK{CIK}.json'
MAX_PACKET_BYTES = 128 * 1024
_FORMS = frozenset({'20-F', '20-F/A'})
_IDENTITY_KIND = 'sec_ticker_map_and_submissions'
_FLAGS = dict(commercial_eligible=False, readiness_promoted=False, saved_readiness_promoted=False,
              financial_coverage_promoted=False)
_SOURCE_KEYS = (*_ANCHOR_KEYS, 'ticker', 'sec_cik', 'source_id', 'observed_at', 'payload_sha256',
                'rights_status', 'unit', 'accounting_basis', 'source_scale', 'period_kind')
_ROW_SOURCE_KEYS = tuple(key for key in _SOURCE_KEYS if key != 'period_end')
_ROW_KEYS = set(_ROW_SOURCE_KEYS) | {'kind', 'status', 'reason', 'period_start', 'period_end', 'fields', 'withheld_fields'}
_FIELD_KEYS = set(_ROW_SOURCE_KEYS) | {'field', 'label', 'definition', 'value', 'scale', 'table_index', 'row_index',
    'column_span', 'anchor', 'source_ref', 'period_start', 'period_end', 'reported_text', 'reported_numeric_schema'}
_DTO_KEYS = set(_SOURCE_KEYS) | set(_FLAGS) | {'schema_version', 'status', 'reason', 'archive_identity', 'periods',
    'registration_observation', 'source_receipts', 'source_packet_sha256', 'withheld_fields', 'packet_digest'}
_WRAPPER_KEYS = set(_FLAGS) | {'schema_version', 'status', 'reason', 'ticker', 'sec_cik', 'rights_status',
                              'archive_identity', 'source_packet', 'packet_digest'}
_REGISTRATION_KEYS = {'status', 'declared_type', 'label', 'as_of', 'current_legal_type_established', 'source_ref', 'table_index'}


def _sealed(packet):
    return (len(_json(packet)) <= MAX_PACKET_BYTES
            and packet.get('packet_digest') == _digest({k: v for k, v in packet.items() if k != 'packet_digest'}))


def _verified_inventory(inventory, *, as_of, historical=False):
    verified = validated_filing_inventory(inventory, ticker=TICKER, expected_cik=CIK,
                                          as_of=as_of, allow_historical=historical)
    if not verified or verified['issuer']['sic'] not in BANK_SICS or verified['issuer']['fiscal_year_end'] != '0331':
        return None
    annual = verified['latest']['annual']
    return verified if annual and annual['form'] in _FORMS else None


def _receipt_ref(receipt):
    return {key: receipt[key] for key in _REF_KEYS}


def _identity_refs_match(identity, refs, *, verified, now, historical=False):
    keys = {'kind', 'ticker', 'sec_cik', 'ticker_map_receipt', 'submissions_receipt'}
    if (not isinstance(identity, Mapping) or set(identity) != keys or identity['kind'] != _IDENTITY_KIND
            or identity['ticker'] != TICKER or identity['sec_cik'] != CIK
            or not isinstance(refs, list) or len(refs) != 3):
        return False
    urls = [MAP_URL, SUBMISSIONS_URL, verified['latest']['annual']['source_url']]
    if any(not isinstance(ref, Mapping) or set(ref) != set(_REF_KEYS) or not _ref(ref, url, now, historical)
           for ref, url in zip(refs, urls)):
        return False
    stamps = [_utc_timestamp(ref['observed_at']) for ref in refs]
    return (identity['ticker_map_receipt'] == refs[0] and identity['submissions_receipt'] == refs[1]
            and refs[1] == _receipt_ref(verified['source_receipt']) and stamps == sorted(stamps)
            and stamps[-1] - stamps[0] <= timedelta(hours=24))


def _selection_verified(selection, submissions, annual):
    if (selection.get('status') != 'selected' or selection.get('adapter') != 'ibn_html_bank'
            or any(selection.get(key) != annual[key] for key in _ANCHOR_KEYS)):
        return False
    recent = submissions['payload']['filings']['recent']
    indexes = [i for i, accession in enumerate(recent['accessionNumber']) if accession == annual['accession']]
    if len(indexes) != 1:
        return False
    index = indexes[0]
    return recent['isInlineXBRL'][index] == 0 and recent['isXBRL'][index] == 0


def _source_wrapper(financial, *, verified, now):
    wrapper = financial.get('ibn_archive_annual')
    if (not isinstance(wrapper, Mapping) or set(wrapper) != _WRAPPER_KEYS or wrapper['schema_version'] != SCHEMA
            or wrapper['status'] != 'inspection_only' or wrapper['reason'] is not None
            or wrapper['ticker'] != TICKER or wrapper['sec_cik'] != CIK or wrapper['rights_status'] != RIGHTS
            or any(wrapper[key] is not False for key in _FLAGS) or not _sealed(wrapper)):
        return None
    packet = validated_bank_html(wrapper['source_packet'], TICKER, 'annual')
    if (not packet or not packet['periods'][0]['fields']
            or any(packet[key] != verified['latest']['annual'][key] for key in _ANCHOR_KEYS)
            or not _identity_refs_match(wrapper['archive_identity'], packet['source_receipts'], verified=verified, now=now)):
        return None
    return wrapper


def _row_state(fields):
    return ('available', None) if fields else ('withheld', 'ibn_direct_fields_unavailable')


def _normalized(wrapper):
    packet = wrapper['source_packet']
    metadata = {key: packet[key] for key in _SOURCE_KEYS}
    source = {key: packet[key] for key in _ROW_SOURCE_KEYS}
    periods = []
    for row in packet['periods']:
        duration = {key: row[key] for key in ('period_start', 'period_end')}
        fields = {}
        for name, original in row['fields'].items():
            field = {key: deepcopy(value) for key, value in original.items() if key != 'raw_text'}
            field.update(source, **duration, reported_text=original['raw_text'], reported_numeric_schema=NUMBER_SCHEMA)
            fields[name] = field
        status, reason = _row_state(fields)
        periods.append(dict(source, **duration, kind='annual', status=status, reason=reason, fields=fields,
                            withheld_fields=deepcopy(row['withheld_fields'])))
    registration = packet['registration_observation']
    result = dict(metadata, **_FLAGS, schema_version=SCHEMA, status='inspection_only', reason=None, periods=periods,
                  source_packet_sha256=packet['packet_digest'], source_receipts=deepcopy(packet['source_receipts']),
                  archive_identity=deepcopy(wrapper['archive_identity']), withheld_fields=deepcopy(packet['withheld_fields']),
                  registration_observation={key: value for key, value in registration.items()
                    if key not in {'raw_cover_table', 'underlying_note'}})
    result['packet_digest'] = _digest(result)
    return result if _sealed(result) else None


def validated_ibn_archive_annual(financial, *, ticker=None, expected_cik=None, inventory=None, as_of=None):
    """Read the exact latest IBN annual table without claiming a Companyfacts identity."""
    try:
        if (not isinstance(financial, Mapping) or financial.get('ticker') != TICKER or financial.get('sec_cik') != CIK
                or ticker not in {None, TICKER} or expected_cik not in {None, CIK} or _mode_reason('research')):
            return None
        now = _now(as_of)
        selected = financial.get('filing_inventory') if inventory is None else inventory
        verified = _verified_inventory(selected, as_of=now)
        if not verified:
            return None
        wrapper = _source_wrapper(financial, verified=verified, now=now)
        return _normalized(wrapper) if wrapper else None
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError):
        return None


def valid_ibn_annual_field(field, *, context, row, field_name):
    """Check the normalized exact HTML cell and its receipt and reporting period."""
    from src.sec_html_bank import valid_bank_html_numeric

    try:
        return (isinstance(field, Mapping) and set(field) == _FIELD_KEYS
                and field['reported_numeric_schema'] == NUMBER_SCHEMA and field['field'] == field_name
                and field['ticker'] == context.get('ticker') == TICKER and field['sec_cik'] == context.get('sec_cik') == CIK
                and all(field[key] == row[key] for key in (*_ROW_SOURCE_KEYS, 'period_start', 'period_end'))
                and valid_bank_html_numeric(dict(field, raw_text=field['reported_text']), field_name=field_name,
                                            source_url=row['source_url']))
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError):
        return False


def _saved_registration_valid(registration, archive):
    if not isinstance(registration, Mapping) or registration.get('current_legal_type_established') is not False:
        return False
    if registration.get('status') == 'withheld':
        return registration == {'status': 'withheld', 'reason': 'qualified_cover_security_disclosure_unavailable',
                                'current_legal_type_established': False}
    return (set(registration) == _REGISTRATION_KEYS and registration['status'] == 'observed_as_filed'
            and registration['declared_type'] == 'depositary_receipt' and registration['label'] == 'American Depositary Shares'
            and registration['as_of'] == archive['filed'] and registration['source_ref'] == archive['source_url']
            and type(registration['table_index']) is int and 0 <= registration['table_index'] < 20)


def _saved_periods_valid(archive, context):
    periods = archive['periods']
    if not isinstance(periods, list) or len(periods) != 3:
        return False
    year = _iso_date(archive['period_end']).year
    for index, row in enumerate(periods):
        if (not isinstance(row, Mapping) or set(row) != _ROW_KEYS or row['kind'] != 'annual'
                or row['period_start'] != f'{year - index - 1}-04-01' or row['period_end'] != f'{year - index}-03-31'
                or any(row[key] != archive[key] for key in _ROW_SOURCE_KEYS)):
            return False
        fields, withheld = row['fields'], row['withheld_fields']
        if (not isinstance(fields, Mapping) or not isinstance(withheld, Mapping)
                or set(fields) | set(withheld) != set(DEFINITIONS) or set(fields) & set(withheld)
                or (row['status'], row['reason']) != _row_state(fields)
                or any(not isinstance(reason, str) or not re.fullmatch(r'[a-z_]{1,100}', reason) for reason in withheld.values())):
            return False
        if any(not valid_ibn_annual_field(field, context=context, row=row, field_name=name) for name, field in fields.items()):
            return False
    return bool(periods[0]['fields'])


def valid_saved_ibn_annual(archive, *, context):
    """Verify a body-free saved annual observation against its catalog and receipts."""
    try:
        if (not isinstance(archive, Mapping) or set(archive) != _DTO_KEYS or archive['schema_version'] != SCHEMA
                or archive['ticker'] != context.get('ticker') or archive['sec_cik'] != context.get('sec_cik')
                or archive['status'] != 'inspection_only' or archive['reason'] is not None
                or archive['ticker'] != TICKER or archive['sec_cik'] != CIK or archive['period_kind'] != 'annual'
                or archive['source_id'] != SOURCE_ID or archive['unit'] != 'INR' or archive['accounting_basis'] != 'Indian GAAP'
                or archive['source_scale'] != 'thousands' or archive['rights_status'] != RIGHTS
                or archive['withheld_fields'] != WITHHELD or any(archive[key] is not False for key in _FLAGS)
                or not isinstance(archive['source_packet_sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', archive['source_packet_sha256'])
                or not _sealed(archive)):
            return False
        now = _utc_timestamp(context.get('observed_at'))
        if not now:
            return False
        verified = _verified_inventory(context.get('filing_inventory'), as_of=now, historical=True)
        refs = archive['source_receipts']
        if (not verified or any(archive[key] != verified['latest']['annual'][key] for key in _ANCHOR_KEYS)
                or not _identity_refs_match(archive['archive_identity'], refs, verified=verified, now=now, historical=True)
                or _receipt_ref(archive) != refs[-1]
                or _utc_timestamp(refs[-1]['observed_at']) < _utc_timestamp(archive['accepted_at'])):
            return False
        context_refs = [ref for ref in context['source_receipts'] if isinstance(ref, Mapping)
                        and ref.get('source') == 'exact_ibn_annual_receipt']
        if context_refs != [dict(ref, source='exact_ibn_annual_receipt', rights_status=RIGHTS) for ref in refs]:
            return False
        coverage = context['filing_coverage']
        current = coverage['current']['annual']
        anchor = current.get('anchor') or {}
        if (current.get('status') != 'corroborated' or current.get('reason') != 'exact_ibn_annual_table_and_filing'
                or current.get('source_id') != SOURCE_ID or current.get('rights_status') != RIGHTS
                or current != coverage['periods']['annual'].get(archive['period_end'])
                or any(anchor.get(key) != archive[key] for key in _ANCHOR_KEYS)):
            return False
        return _saved_registration_valid(archive['registration_observation'], archive) and _saved_periods_valid(archive, context)
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError):
        return False


def fetch_ibn_archive_annual(financial, *, user_agent, ticker_map_receipt, submissions_receipt,
                             source_fetcher=None, observed_at=None):
    """Use the already acquired map and submissions to inspect one qualified 20-F."""
    def hold(reason):
        return _held(TICKER, CIK, reason, schema=SCHEMA)

    try:
        if _mode_reason('research') or (financial.get('ticker'), financial.get('sec_cik')) != (TICKER, CIK):
            return hold('ibn_annual_scope_unavailable')
        now = _now(observed_at)
        inventory = _verified_inventory(financial.get('filing_inventory'), as_of=now)
        if not inventory:
            return hold('ibn_annual_current_bank_filing_unverified')
        mapping, submissions = _ref(ticker_map_receipt, MAP_URL, now), _ref(submissions_receipt, SUBMISSIONS_URL, now)
        if (not mapping or not submissions or ticker_map_receipt.get('status') != 'ready'
                or submissions_receipt.get('status') != 'ready'
                or build_filing_inventory(submissions_receipt, ticker=TICKER, expected_cik=CIK, as_of=now)['packet_digest'] != inventory['packet_digest']):
            return hold('ibn_annual_source_receipts_unverified')
        selection = select_sec_filing(TICKER, CIK, submissions_receipt, period_kind='annual', allow_non_inline=True)
        if not _selection_verified(selection, submissions_receipt, inventory['latest']['annual']):
            return hold('ibn_annual_latest_non_xbrl_filing_unverified')
        packet = fetch_sec_filing_preview(TICKER, period_kind='annual', user_agent=user_agent, fetcher=source_fetcher,
                                         expected_cik=CIK, observed_at=observed_at, ticker_map_receipt=ticker_map_receipt,
                                         submissions_receipt=submissions_receipt)
        validated = validated_bank_html(packet, TICKER, 'annual')
        if not validated:
            reason = packet.get('reason')
            return hold(reason if isinstance(reason, str) and re.fullmatch(r'[a-z0-9_]{1,120}', reason)
                        else 'ibn_annual_exact_html_unavailable')
        if not validated['periods'][0]['fields']:
            return hold('ibn_annual_current_fields_unavailable')
        identity = dict(kind=_IDENTITY_KIND, ticker=TICKER, sec_cik=CIK,
                        ticker_map_receipt=_receipt_ref(mapping), submissions_receipt=_receipt_ref(submissions))
        wrapper = dict(schema_version=SCHEMA, status='inspection_only', reason=None, ticker=TICKER, sec_cik=CIK,
                       archive_identity=identity, source_packet=validated, rights_status=RIGHTS, **_FLAGS)
        wrapper['packet_digest'] = _digest(wrapper)
        return (wrapper if _source_wrapper({'ibn_archive_annual': wrapper}, verified=inventory, now=_now(observed_at))
                else hold('ibn_annual_exact_html_unavailable'))
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError, OSError, RuntimeError):
        return hold('ibn_annual_exact_html_unavailable')
