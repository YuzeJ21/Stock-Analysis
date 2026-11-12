"""Exact archive quarters, kept apart from Companyfacts and commercial approval.

The live wrapper retains the original validated filing packet so every read can
repeat its source and bank-classification checks. Only the returned DTO is fit
for display/context snapshots; it contains numeric literals, never source bodies.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import timedelta
import json
import re

from src.company_sec_online_preview import _utc_timestamp
from src.online_company_identity import _mode_reason, financial_identity_valid
from src.online_filing_context import _digest, _fresh, _now, _ref, build_filing_inventory, validated_filing_inventory
from src.sec_exact_filing import MAP_URL, RIGHTS, SOURCE_ID, BANK_SOURCE_ID, validated_filing_preview
from src.sec_inline_filing import valid_numeric_proof, _taxonomy

SCHEMA = 'sec-online-archive-quarter-v1'
NUMERIC_SCHEMA = 'sec-reported-numeric-v1'
CAPITAL_PURCHASE_NUMERIC_SCHEMA = 'sec-nee-capital-purchase-number-v1'
MAX_WRAPPER_BYTES = 8 * 1024 * 1024
MAX_DTO_BYTES = 128 * 1024
_ANCHOR_KEYS = ('accession', 'form', 'period_end', 'filed', 'accepted_at', 'primary_document', 'source_url')
_REF_KEYS = ('source_url', 'observed_at', 'payload_sha256')
_FIELD_KEYS = frozenset(('field', 'taxonomy', 'concept', 'namespace_uri', 'unit', 'unit_id',
    'context_id', 'period_start', 'period_end', 'fact_id', 'source_ref', 'rights_status',
    'value', 'raw_text', 'scale', 'sign', 'decimals', 'transformation'))
_QUARTER_FORMS = frozenset({'10-Q', '10-Q/A'})
_QUARTER_SOURCES = frozenset({SOURCE_ID, BANK_SOURCE_ID})
_NEE_TICKER, _NEE_CIK = 'NEE', '0000753308'
_NEE_REVIEWED_ACCESSION = '0000753308-26-000081'
_SOURCE_METADATA = (*_ANCHOR_KEYS, 'ticker', 'sec_cik', 'source_id', 'observed_at', 'payload_sha256')
_CAPITAL_PURCHASE_RAW_KEYS = {'schema_version', 'status', 'period_kind', 'period_start', 'period_end', 'unit',
                              'capital_expenditures_equivalent', 'cash_generation_eligible', 'fields'}
_CAPITAL_PURCHASE_FIELD_KEYS = _FIELD_KEYS | {'label', 'presentation', 'statement', 'presentation_evidence'}
_CAPITAL_PURCHASE_PROOF_KEYS = (_CAPITAL_PURCHASE_FIELD_KEYS - {'raw_text'}) | set(_SOURCE_METADATA) | {
    'reported_text', 'reported_numeric_schema'}
_CAPITAL_PURCHASE_FLAGS = dict(rights_status=RIGHTS, commercial_eligible=False, saved_readiness_promoted=False)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _held(ticker, cik, reason, *, schema=SCHEMA):
    return dict(schema_version=schema, status='withheld', reason=reason, ticker=ticker, sec_cik=cik,
                rights_status=RIGHTS, commercial_eligible=False, saved_readiness_promoted=False)


def _identity_inventory(financial, ticker, cik, inventory, as_of):
    if _mode_reason('research') or not isinstance(financial, Mapping):
        return None
    identity = financial.get('companyfacts_identity')
    if (financial.get('ticker') != ticker or financial.get('sec_cik') != cik
            or not financial_identity_valid(ticker, identity) or identity['sec_cik'] != cik):
        return None
    now = _now(as_of)
    if not now or not _fresh(identity.get('observed_at'), now) or not _fresh(identity.get('association_observed_at'), now):
        return None
    return validated_filing_inventory(inventory, ticker=ticker, expected_cik=cik, as_of=as_of)


def _source_packet(financial, wrapper, *, ticker, cik, inventory, as_of, schema=SCHEMA,
                   period_kind='quarterly', forms=_QUARTER_FORMS, source_ids=_QUARTER_SOURCES):
    verified = _identity_inventory(financial, ticker, cik, inventory, as_of)
    if not verified or not isinstance(wrapper, Mapping):
        return None
    if (wrapper.get('schema_version') != schema or wrapper.get('status') != 'inspection_only'
            or wrapper.get('reason') is not None or wrapper.get('ticker') != ticker or wrapper.get('sec_cik') != cik
            or wrapper.get('rights_status') != RIGHTS or wrapper.get('commercial_eligible') is not False
            or wrapper.get('saved_readiness_promoted') is not False
            or len(_json(wrapper)) > MAX_WRAPPER_BYTES
            or wrapper.get('packet_digest') != _digest({k: v for k, v in wrapper.items() if k != 'packet_digest'})):
        return None
    packet = validated_filing_preview(wrapper.get('source_packet'), ticker, period_kind)
    if (not packet or packet.get('sec_cik') != cik or packet.get('source_id') not in source_ids
            or wrapper.get('source_packet_digest') != packet.get('packet_digest')):
        return None
    anchor = verified['latest'][period_kind]
    if not anchor or anchor['form'] not in forms or any(packet.get(k) != anchor[k] for k in _ANCHOR_KEYS):
        return None
    refs = packet['source_receipts']; now = _now(as_of)
    if any(not _ref(ref, ref.get('source_url'), now) for ref in refs):
        return None
    identity = financial['companyfacts_identity']
    association = dict(source_url=identity['association_source_url'], observed_at=identity['association_observed_at'],
                       payload_sha256=identity['association_payload_sha256'])
    if (any(refs[0].get(k) != association[k] for k in _REF_KEYS)
            or any(refs[1].get(k) != verified['source_receipt'].get(k) for k in _REF_KEYS)):
        return None
    # The original validator validates the whole preview, including bank_scope.
    # Apply numeric and metadata proof checks to all fields, including nonbanks.
    for row in packet['periods']:
        for field in row['fields'].values():
            if (set(field) != _FIELD_KEYS or not valid_numeric_proof(field) or _taxonomy(field.get('namespace_uri')) != packet['taxonomy']
                    or any(not isinstance(field.get(k), str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]{0,127}', field[k])
                           for k in ('context_id', 'unit_id', 'fact_id'))):
                return None
    return packet, verified


def _wrap_source_packet(ticker, cik, source_packet, *, schema):
    wrapper = dict(schema_version=schema, status='inspection_only', reason=None, ticker=ticker, sec_cik=cik,
        source_packet=deepcopy(source_packet), source_packet_digest=source_packet.get('packet_digest'),
        rights_status=RIGHTS, commercial_eligible=False, saved_readiness_promoted=False)
    wrapper['packet_digest'] = _digest(wrapper)
    return wrapper


def build_archive_quarter(financial, source_packet, *, inventory=None, as_of=None):
    """Bind a complete source packet to the current inventory without transport."""
    ticker = financial.get('ticker') if isinstance(financial, Mapping) else None
    cik = financial.get('sec_cik') if isinstance(financial, Mapping) else None
    held = _held(ticker, cik, 'archive_quarter_evidence_unavailable')
    if not isinstance(source_packet, Mapping) or source_packet.get('status') != 'inspection_only':
        return held
    try:
        wrapper = _wrap_source_packet(ticker, cik, source_packet, schema=SCHEMA)
        selected_inventory = inventory if inventory is not None else financial.get('filing_inventory')
        return wrapper if _source_packet(financial, wrapper, ticker=ticker, cik=cik,
                                        inventory=selected_inventory, as_of=as_of) else held
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError):
        return held


def _capital_purchase_dto(packet, source_metadata):
    evidence = packet.get('capital_purchase_evidence')
    if (not isinstance(evidence, Mapping) or set(evidence) != _CAPITAL_PURCHASE_RAW_KEYS
            or evidence.get('period_end') != packet['period_end'] or evidence.get('unit') != packet['unit']):
        return None
    from src.sec_inline_filing import valid_nee_capital_purchase_evidence

    if not valid_nee_capital_purchase_evidence(evidence, source_url=packet['source_url']):
        return None
    fields = {}
    for name, original in evidence['fields'].items():
        if set(original) != _CAPITAL_PURCHASE_FIELD_KEYS:
            return None
        field = {key: deepcopy(value) for key, value in original.items() if key != 'raw_text'}
        field.update(source_metadata, reported_text=original['raw_text'],
                     reported_numeric_schema=CAPITAL_PURCHASE_NUMERIC_SCHEMA)
        fields[name] = field
    result = dict(evidence, **source_metadata, **_CAPITAL_PURCHASE_FLAGS)
    result['fields'] = fields
    result['packet_digest'] = _digest(result)
    return result


def _archive_dto(packet, verified, *, schema, period_kind):
    source_metadata = {k: packet[k] for k in _SOURCE_METADATA}
    periods = []
    for row in packet['periods']:
        fields = {}
        for name, value in row['fields'].items():
            field = {k: deepcopy(v) for k, v in value.items() if k != 'raw_text'}
            field.update(reported_text=value['raw_text'], reported_numeric_schema=NUMERIC_SCHEMA,
                         **source_metadata)
            fields[name] = field
        available = 'revenue' in fields
        periods.append(dict(kind=row['kind'], period_start=row['period_start'],
            period_end=row['period_end'], fields=fields, withheld_fields=deepcopy(row['withheld_fields']),
            status='available' if available else 'withheld',
            reason=None if available else row['withheld_fields'].get('revenue', 'reported_revenue_unavailable'),
            **{k: v for k, v in source_metadata.items() if k != 'period_end'}))
    result = dict(schema_version=schema, status='inspection_only', reason=None, **source_metadata,
        period_kind=period_kind, taxonomy=packet['taxonomy'], unit=packet['unit'], periods=periods,
        source_receipts=[{k: r[k] for k in _REF_KEYS} for r in packet['source_receipts']], source_packet_digest=packet['packet_digest'],
        inventory_digest=verified['packet_digest'], rights_status=RIGHTS, commercial_eligible=False,
        saved_readiness_promoted=False, readiness_promoted=False)
    if period_kind == 'quarterly' and (packet['ticker'], packet['sec_cik']) == (_NEE_TICKER, _NEE_CIK):
        evidence = _capital_purchase_dto(packet, source_metadata)
        if evidence:
            result['capital_purchase_evidence'] = evidence
    if len(_json(result)) > MAX_DTO_BYTES:
        return None
    result['packet_digest'] = _digest(result)
    return result


def validated_archive_quarter(financial, *, ticker=None, expected_cik=None, inventory=None, as_of=None):
    """Return a personal DTO only after revalidating the original exact packet.

    The returned period status is available only when that exact duration has a
    reported revenue fact. Bank components and cumulative cash flows stay in
    their own fields/durations and never manufacture a quarter revenue or cash flow.
    """
    try:
        if not isinstance(financial, Mapping):
            return None
        ticker = financial.get('ticker') if ticker is None else ticker
        cik = financial.get('sec_cik') if expected_cik is None else expected_cik
        selected_inventory = inventory if inventory is not None else financial.get('filing_inventory')
        source = _source_packet(financial, financial.get('archive_quarterly'), ticker=ticker, cik=cik,
                                inventory=selected_inventory, as_of=as_of)
        if not source:
            return None
        return _archive_dto(*source, schema=SCHEMA, period_kind='quarterly')
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError):
        return None


def _saved_capital_purchase_fields(packet):
    """Rebuild the typed source proof without persisting an HTML or XML body."""
    from src.sec_inline_filing import valid_nee_capital_purchase_evidence

    fields = packet['fields']
    if not isinstance(fields, Mapping) or not fields:
        return False
    raw = {key: packet[key] for key in _CAPITAL_PURCHASE_RAW_KEYS if key != 'fields'}
    raw['fields'] = {}
    for name, field in fields.items():
        if (not isinstance(field, Mapping) or set(field) != _CAPITAL_PURCHASE_PROOF_KEYS
                or field['reported_numeric_schema'] != CAPITAL_PURCHASE_NUMERIC_SCHEMA
                or any(field[key] != packet[key] for key in _SOURCE_METADATA)):
            return False
        proof = {key: field[key] for key in _CAPITAL_PURCHASE_FIELD_KEYS if key != 'raw_text'}
        proof['raw_text'] = field['reported_text']
        raw['fields'][name] = proof
    return valid_nee_capital_purchase_evidence(raw, source_url=packet['source_url'])


def valid_saved_capital_purchase_evidence(packet, *, context):
    """Validate the exact NEE cumulative sibling independently of generic numeric proofs."""
    try:
        keys = _CAPITAL_PURCHASE_RAW_KEYS | set(_SOURCE_METADATA) | set(_CAPITAL_PURCHASE_FLAGS) | {'packet_digest'}
        if (not isinstance(packet, Mapping) or set(packet) != keys
                or (context.get('ticker'), context.get('sec_cik')) != (_NEE_TICKER, _NEE_CIK)
                or (packet['ticker'], packet['sec_cik']) != (_NEE_TICKER, _NEE_CIK)
                or packet['source_id'] != SOURCE_ID or packet['rights_status'] != RIGHTS
                or packet['commercial_eligible'] is not False or packet['saved_readiness_promoted'] is not False
                or len(_json(packet)) > MAX_DTO_BYTES
                or packet['packet_digest'] != _digest({key: value for key, value in packet.items() if key != 'packet_digest'})):
            return False
        now = _utc_timestamp(context.get('observed_at'))
        if not now:
            return False
        verified = validated_filing_inventory(context.get('filing_inventory'), ticker=_NEE_TICKER, expected_cik=_NEE_CIK,
                                              as_of=now, allow_historical=True)
        anchor = verified['latest']['quarterly'] if verified else None
        if not anchor or any(packet[key] != anchor[key] for key in _ANCHOR_KEYS):
            return False
        refs = [ref for ref in context['source_receipts'] if isinstance(ref, Mapping) and ref.get('source') == 'exact_quarter_receipt']
        urls = (MAP_URL, verified['source_receipt']['source_url'], anchor['source_url'])
        if (len(refs) != len(urls) or any(ref.get('rights_status') != RIGHTS or not _ref(ref, url, now, historical=True)
                                          for ref, url in zip(refs, urls))
                or any(refs[1][key] != verified['source_receipt'][key] or refs[2][key] != packet[key] for key in _REF_KEYS)):
            return False
        times = [_utc_timestamp(ref['observed_at']) for ref in refs]
        return (times == sorted(times) and times[-1] - times[0] <= timedelta(hours=24)
                and times[-1] >= _utc_timestamp(packet['accepted_at']) and _saved_capital_purchase_fields(packet))
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError):
        return False


def _receipt_gap(financial, verified, ticker_map_receipt, submissions_receipt, as_of):
    ticker, cik = financial['ticker'], financial['sec_cik']
    identity = financial['companyfacts_identity']
    now = _now(as_of)
    map_ref = _ref(ticker_map_receipt, MAP_URL, now)
    profile_ref = _ref(submissions_receipt, f'https://data.sec.gov/submissions/CIK{cik}.json', now)
    expected_map = dict(source_url=identity['association_source_url'], observed_at=identity['association_observed_at'],
                        payload_sha256=identity['association_payload_sha256'])
    if (not map_ref or not profile_ref or ticker_map_receipt.get('status') != 'ready'
            or any(map_ref[k] != expected_map[k] for k in _REF_KEYS)
            or any(profile_ref[k] != verified['source_receipt'][k] for k in _REF_KEYS)):
        return 'receipt_mismatch'
    replayed = build_filing_inventory(submissions_receipt, ticker=ticker, expected_cik=cik, as_of=as_of)
    if replayed.get('packet_digest') != verified['packet_digest']:
        return 'profile_mismatch'
    return None


def fetch_archive_quarter(financial, *, user_agent, ticker_map_receipt, submissions_receipt,
                          source_fetcher=None, observed_at=None):
    """Acquire only an unresolved current quarter, reusing the original receipts."""
    ticker = financial.get('ticker') if isinstance(financial, Mapping) else None
    cik = financial.get('sec_cik') if isinstance(financial, Mapping) else None
    held = _held(ticker, cik, 'archive_quarter_not_required')
    try:
        inventory = financial.get('filing_inventory') if isinstance(financial, Mapping) else None
        verified = _identity_inventory(financial, ticker, cik, inventory, observed_at)
        if not verified:
            return _held(ticker, cik, 'archive_quarter_current_source_unavailable')
        gap = _receipt_gap(financial, verified, ticker_map_receipt, submissions_receipt, observed_at)
        if gap:
            return _held(ticker, cik, 'archive_quarter_' + gap)
        anchor = verified['latest']['quarterly']
        if not anchor or anchor['form'] not in _QUARTER_FORMS:
            return held
        # Recompute from the fresh structured evidence; caller-supplied coverage
        # cannot force a source request for an already covered quarter.
        from src.online_filing_context import corroborate_online_financials
        current = corroborate_online_financials(financial, verified, as_of=observed_at)['current']['quarterly']
        supplemental = ((ticker, cik) == (_NEE_TICKER, _NEE_CIK) and anchor['accession'] == _NEE_REVIEWED_ACCESSION
                        and anchor['form'] == '10-Q')
        needed = current.get('status') in {'facts_pending', 'withheld', 'amendment_unresolved'}
        if not needed and not (current.get('status') == 'corroborated' and supplemental):
            return held
        from src.sec_exact_filing import fetch_sec_filing_preview
        packet = fetch_sec_filing_preview(ticker, period_kind='quarterly', user_agent=user_agent,
            fetcher=source_fetcher, observed_at=observed_at, expected_cik=cik,
            ticker_map_receipt=ticker_map_receipt, submissions_receipt=submissions_receipt)
        result = build_archive_quarter(financial, packet, inventory=verified, as_of=observed_at)
        if result['status'] != 'inspection_only':
            reason = packet.get('reason') if isinstance(packet, Mapping) else None
            if isinstance(reason, str) and re.fullmatch(r'[a-z0-9_]{1,160}', reason):
                result['reason'] = reason
        return result
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError, OSError, RuntimeError):
        return _held(ticker, cik, 'archive_quarter_evidence_unavailable')
