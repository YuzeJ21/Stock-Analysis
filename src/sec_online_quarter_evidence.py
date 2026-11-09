"""Exact archive quarters, kept apart from Companyfacts and commercial approval.

The live wrapper retains the original validated filing packet so every read can
repeat its source and bank-classification checks. Only the returned DTO is fit
for display/context snapshots; it contains numeric literals, never source bodies.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import json
import re

from src.online_company_identity import _mode_reason, financial_identity_valid
from src.online_filing_context import _digest, _fresh, _now, _ref, build_filing_inventory, validated_filing_inventory
from src.sec_exact_filing import MAP_URL, RIGHTS, SOURCE_ID, BANK_SOURCE_ID, validated_filing_preview
from src.sec_inline_filing import valid_numeric_proof, _taxonomy

SCHEMA = 'sec-online-archive-quarter-v1'
NUMERIC_SCHEMA = 'sec-reported-numeric-v1'
MAX_WRAPPER_BYTES = 8 * 1024 * 1024
MAX_DTO_BYTES = 128 * 1024
_ANCHOR_KEYS = ('accession', 'form', 'period_end', 'filed', 'accepted_at', 'primary_document', 'source_url')
_REF_KEYS = ('source_url', 'observed_at', 'payload_sha256')
_FIELD_KEYS = frozenset(('field', 'taxonomy', 'concept', 'namespace_uri', 'unit', 'unit_id',
    'context_id', 'period_start', 'period_end', 'fact_id', 'source_ref', 'rights_status',
    'value', 'raw_text', 'scale', 'sign', 'decimals', 'transformation'))


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _held(ticker, cik, reason):
    return dict(schema_version=SCHEMA, status='withheld', reason=reason, ticker=ticker, sec_cik=cik,
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


def _source_packet(financial, wrapper, *, ticker, cik, inventory, as_of):
    verified = _identity_inventory(financial, ticker, cik, inventory, as_of)
    if not verified or not isinstance(wrapper, Mapping):
        return None
    if (wrapper.get('schema_version') != SCHEMA or wrapper.get('status') != 'inspection_only'
            or wrapper.get('reason') is not None or wrapper.get('ticker') != ticker or wrapper.get('sec_cik') != cik
            or wrapper.get('rights_status') != RIGHTS or wrapper.get('commercial_eligible') is not False
            or wrapper.get('saved_readiness_promoted') is not False
            or len(_json(wrapper)) > MAX_WRAPPER_BYTES
            or wrapper.get('packet_digest') != _digest({k: v for k, v in wrapper.items() if k != 'packet_digest'})):
        return None
    packet = validated_filing_preview(wrapper.get('source_packet'), ticker, 'quarterly')
    if (not packet or packet.get('sec_cik') != cik or packet.get('source_id') not in {SOURCE_ID, BANK_SOURCE_ID}
            or wrapper.get('source_packet_digest') != packet.get('packet_digest')):
        return None
    anchor = verified['latest']['quarterly']
    if not anchor or anchor['form'] not in {'10-Q', '10-Q/A'} or any(packet.get(k) != anchor[k] for k in _ANCHOR_KEYS):
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


def build_archive_quarter(financial, source_packet, *, inventory=None, as_of=None):
    """Bind a complete source packet to the current inventory without transport."""
    ticker = financial.get('ticker') if isinstance(financial, Mapping) else None
    cik = financial.get('sec_cik') if isinstance(financial, Mapping) else None
    held = _held(ticker, cik, 'archive_quarter_evidence_unavailable')
    if not isinstance(source_packet, Mapping) or source_packet.get('status') != 'inspection_only':
        return held
    wrapper = dict(schema_version=SCHEMA, status='inspection_only', reason=None, ticker=ticker, sec_cik=cik,
        source_packet=deepcopy(source_packet), source_packet_digest=source_packet.get('packet_digest'),
        rights_status=RIGHTS, commercial_eligible=False, saved_readiness_promoted=False)
    try:
        wrapper['packet_digest'] = _digest(wrapper)
        selected_inventory = inventory if inventory is not None else financial.get('filing_inventory')
        return wrapper if _source_packet(financial, wrapper, ticker=ticker, cik=cik,
                                        inventory=selected_inventory, as_of=as_of) else held
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError):
        return held


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
        packet, verified = source
        source_metadata = {k: packet[k] for k in (*_ANCHOR_KEYS, 'ticker', 'sec_cik', 'source_id', 'observed_at', 'payload_sha256')}
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
        result = dict(schema_version=SCHEMA, status='inspection_only', reason=None, **source_metadata,
            period_kind='quarterly', taxonomy=packet['taxonomy'], unit=packet['unit'], periods=periods,
            source_receipts=[{k: r[k] for k in _REF_KEYS} for r in packet['source_receipts']], source_packet_digest=packet['packet_digest'],
            inventory_digest=verified['packet_digest'], rights_status=RIGHTS, commercial_eligible=False,
            saved_readiness_promoted=False, readiness_promoted=False)
        if len(_json(result)) > MAX_DTO_BYTES:
            return None
        result['packet_digest'] = _digest(result)
        return result
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError):
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
        identity = financial['companyfacts_identity']; now = _now(observed_at)
        map_ref = _ref(ticker_map_receipt, MAP_URL, now)
        profile_ref = _ref(submissions_receipt, f'https://data.sec.gov/submissions/CIK{cik}.json', now)
        expected_map = dict(source_url=identity['association_source_url'], observed_at=identity['association_observed_at'],
                            payload_sha256=identity['association_payload_sha256'])
        if (not map_ref or not profile_ref or ticker_map_receipt.get('status') != 'ready'
                or any(map_ref[k] != expected_map[k] for k in _REF_KEYS)
                or any(profile_ref[k] != verified['source_receipt'][k] for k in _REF_KEYS)):
            return _held(ticker, cik, 'archive_quarter_receipt_mismatch')
        replayed = build_filing_inventory(submissions_receipt, ticker=ticker, expected_cik=cik, as_of=observed_at)
        if replayed.get('packet_digest') != verified['packet_digest']:
            return _held(ticker, cik, 'archive_quarter_profile_mismatch')
        anchor = verified['latest']['quarterly']
        if not anchor or anchor['form'] not in {'10-Q', '10-Q/A'}:
            return held
        # Recompute from the fresh structured evidence; caller-supplied coverage
        # cannot force a source request for an already covered quarter.
        from src.online_filing_context import corroborate_online_financials
        current = corroborate_online_financials(financial, verified, as_of=observed_at)['current']['quarterly']
        if current.get('status') == 'corroborated':
            return held
        if current.get('status') not in {'facts_pending', 'withheld', 'amendment_unresolved'}:
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
