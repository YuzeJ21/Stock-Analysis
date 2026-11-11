"""Personal native-currency annual observations from exact IFRS filings."""
from __future__ import annotations

from collections.abc import Mapping
import re

from src.company_sec_online_preview import _iso_date
from src.sec_exact_filing import SOURCE_ID
from src.sec_foreign_financials import validated_foreign_financials
from src.sec_online_quarter_evidence import (
    _ANCHOR_KEYS, _archive_dto, _held, _identity_inventory, _receipt_gap,
    _source_packet, _wrap_source_packet,
)

SCHEMA = 'sec-online-archive-annual-v1'
_FORMS = frozenset({'20-F', '20-F/A'})
_SOURCE_IDS = frozenset({SOURCE_ID})
_UNAVAILABLE = 'archive_annual_evidence_unavailable'


def _newer_structured_annual(financial, anchor, foreign):
    # Period hints can withhold this observation. Only the verified exact filing
    # can supply amounts, so a newer structured period cannot be filled by an older filing.
    markers = financial.get('reported_period_anchors')
    marker = markers.get('annual') if isinstance(markers, Mapping) else None
    rows = list(foreign['annual']) if foreign else []
    if isinstance(marker, Mapping):
        rows.append(marker)
    end, filed = _iso_date(anchor['period_end']), _iso_date(anchor['filed'])
    for row in rows:
        row_end, row_filed = _iso_date(row.get('period_end')), _iso_date(row.get('filed'))
        if row_end and (row_end > end or row_end == end and row_filed and row_filed > filed):
            return True
    return False


def _annual_gap(financial, packet):
    if packet['taxonomy'] != 'ifrs-full' or packet['unit'] == 'USD':
        return 'archive_annual_native_ifrs_required'
    foreign = validated_foreign_financials(financial)
    if foreign and foreign['unit'] != packet['unit']:
        return 'archive_annual_reporting_currency_conflict'
    if _newer_structured_annual(financial, packet, foreign):
        return 'archive_annual_newer_structured_period_or_version'
    return None


def _annual_source(financial, wrapper, *, ticker, cik, inventory, as_of):
    return _source_packet(financial, wrapper, ticker=ticker, cik=cik, inventory=inventory, as_of=as_of,
                          schema=SCHEMA, period_kind='annual', forms=_FORMS, source_ids=_SOURCE_IDS)


def build_archive_annual(financial, source_packet, *, inventory=None, as_of=None):
    """Bind the original Inline XBRL evidence to the latest verified 20-F."""
    ticker = financial.get('ticker') if isinstance(financial, Mapping) else None
    cik = financial.get('sec_cik') if isinstance(financial, Mapping) else None
    held = _held(ticker, cik, _UNAVAILABLE, schema=SCHEMA)
    if not isinstance(source_packet, Mapping) or source_packet.get('status') != 'inspection_only':
        return held
    try:
        wrapper = _wrap_source_packet(ticker, cik, source_packet, schema=SCHEMA)
        selected = inventory if inventory is not None else financial.get('filing_inventory')
        source = _annual_source(financial, wrapper, ticker=ticker, cik=cik, inventory=selected, as_of=as_of)
        if not source:
            return held
        reason = _annual_gap(financial, source[0])
        return dict(held, reason=reason) if reason else wrapper
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError):
        return held


def validated_archive_annual(financial, *, ticker=None, expected_cik=None, inventory=None, as_of=None):
    """Revalidate the source and return native direct amounts with normalized proofs."""
    try:
        if not isinstance(financial, Mapping):
            return None
        ticker = financial.get('ticker') if ticker is None else ticker
        cik = financial.get('sec_cik') if expected_cik is None else expected_cik
        selected = inventory if inventory is not None else financial.get('filing_inventory')
        source = _annual_source(financial, financial.get('archive_annual'), ticker=ticker, cik=cik,
                                inventory=selected, as_of=as_of)
        if not source or _annual_gap(financial, source[0]):
            return None
        return _archive_dto(*source, schema=SCHEMA, period_kind='annual')
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError):
        return None


def fetch_archive_annual(financial, *, user_agent, ticker_map_receipt, submissions_receipt,
                         source_fetcher=None, observed_at=None):
    """Acquire one latest annual filing when qualified structured coverage is absent."""
    ticker = financial.get('ticker') if isinstance(financial, Mapping) else None
    cik = financial.get('sec_cik') if isinstance(financial, Mapping) else None
    held = _held(ticker, cik, 'archive_annual_not_required', schema=SCHEMA)
    try:
        inventory = financial.get('filing_inventory') if isinstance(financial, Mapping) else None
        verified = _identity_inventory(financial, ticker, cik, inventory, observed_at)
        if not verified:
            return dict(held, reason='archive_annual_current_source_unavailable')
        anchor = verified['latest']['annual']
        if not anchor or anchor['form'] not in _FORMS:
            return held
        if _newer_structured_annual(financial, anchor, validated_foreign_financials(financial)):
            return dict(held, reason='archive_annual_newer_structured_period_or_version')
        from src.online_filing_context import corroborate_online_financials
        current = corroborate_online_financials(financial, verified, as_of=observed_at)['current']['annual']
        if current.get('status') not in {'facts_pending', 'withheld', 'amendment_unresolved'}:
            return held
        gap = _receipt_gap(financial, verified, ticker_map_receipt, submissions_receipt, observed_at)
        if gap:
            return dict(held, reason='archive_annual_' + gap)
        from src.sec_exact_filing import fetch_sec_filing_preview, select_sec_filing
        selection = select_sec_filing(ticker, cik, submissions_receipt, period_kind='annual')
        if selection.get('status') != 'selected':
            return dict(held, reason=selection.get('reason') or _UNAVAILABLE)
        if any(selection.get(k) != anchor[k] for k in _ANCHOR_KEYS):
            return dict(held, reason='archive_annual_latest_filing_mismatch')
        if 'bank_scope' in selection:
            return dict(held, reason='archive_annual_native_ifrs_required')
        packet = fetch_sec_filing_preview(ticker, period_kind='annual', user_agent=user_agent,
            fetcher=source_fetcher, observed_at=observed_at, expected_cik=cik,
            ticker_map_receipt=ticker_map_receipt, submissions_receipt=submissions_receipt)
        result = build_archive_annual(financial, packet, inventory=verified, as_of=observed_at)
        reason = packet.get('reason') if isinstance(packet, Mapping) else None
        if result['status'] != 'inspection_only' and isinstance(reason, str) and re.fullmatch(r'[a-z0-9_]{1,160}', reason):
            result['reason'] = reason
        return result
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError, OSError, RuntimeError):
        return dict(held, reason=_UNAVAILABLE)
