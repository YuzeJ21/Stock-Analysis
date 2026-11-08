"""Bounded SEC sources for an independent, in-memory MRVL annual review."""

from __future__ import annotations

import base64
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
import hashlib
import re

from src.company_sec_online_preview import _utc_timestamp
from src.online_company_identity import _mode_reason
from src.online_sec_receipt import fetch_sec_json_receipt
from src.providers.sec_company_discovery import _modified_at
from src import sec_exact_filing
from src.mrvl_earnings_review import (
    MRVL_CIK, SCHEMA, POLICIES,
    normalize_review_facts, normalize_review_profile, seal_review_packet,
)


def _unavailable(reason, source_url=None):
    result = {'status': 'unavailable', 'reason': reason}
    if source_url is not None:
        result['source_url'] = source_url
    return result


def _facts_identity_valid(receipt):
    if not isinstance(receipt, Mapping) or receipt.get('status') != 'ready':
        return False
    body = receipt.get('payload')
    if not isinstance(body, Mapping):
        return False
    cik = body.get('cik')
    return bool(
        type(cik) in {int, str} and re.fullmatch(r'\d{1,10}', str(cik))
        and int(cik) > 0 and str(int(cik)).zfill(10) == MRVL_CIK
        and receipt.get('source_url') == f'https://data.sec.gov/api/xbrl/companyfacts/CIK{MRVL_CIK}.json'
        and _utc_timestamp(receipt.get('observed_at')) is not None
        and isinstance(receipt.get('payload_sha256'), str)
        and re.fullmatch(r'[0-9a-f]{64}', receipt['payload_sha256']) is not None
        and isinstance(body.get('facts'), Mapping)
    )


def _fetch_document(url, *, user_agent, source_fetcher, observed_at):
    held = _unavailable('review_document_unavailable', url)
    try:
        raw, headers, final_url = (source_fetcher or sec_exact_filing._fetch_html)(url, user_agent)
        if (not isinstance(raw, bytes) or not 0 < len(raw) <= sec_exact_filing.MAX_FILING_BYTES
                or final_url != url):
            return _unavailable('unverified_filing_document', url)
        observed = (observed_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
        return {
            'status': 'ready', 'source_url': url,
            'observed_at': observed.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'source_last_modified': _modified_at(headers, observed),
            'payload_sha256': hashlib.sha256(raw).hexdigest(),
            'payload_raw_base64': base64.b64encode(raw).decode('ascii'),
        }
    except (OSError, RuntimeError, TimeoutError, ValueError, TypeError, AttributeError, RecursionError):
        return held


def _after_tax_sources(profile, *, annual_qualified, user_agent, source_fetcher, observed_at):
    """Reuse the profile; collect only fixed documents after its exact scope qualifies."""
    extension = {
        'schema_version': 'mrvl-after-tax-reconciliation-v1',
        'status': 'unavailable', 'reason': 'reconciliation_annual_scope_unavailable',
        'primary': _unavailable('reconciliation_primary_unavailable'),
        'exhibit': _unavailable('reconciliation_exhibit_unavailable'),
    }
    if not annual_qualified:
        return extension
    from src.mrvl_after_tax_reconciliation import RECONCILIATION_POLICY, select_mrvl_after_tax_source
    selection = select_mrvl_after_tax_source(profile, as_of=observed_at)
    if selection.get('status') != 'selected':
        extension['reason'] = selection.get('reason', 'reconciliation_8k_scope_unavailable')
        return extension
    extension['primary'] = _fetch_document(
        RECONCILIATION_POLICY['primary_url'], user_agent=user_agent,
        source_fetcher=source_fetcher, observed_at=observed_at,
    )
    extension['reason'] = 'reconciliation_primary_unavailable'
    if extension['primary'].get('status') != 'ready':
        return extension
    extension['exhibit'] = _fetch_document(
        RECONCILIATION_POLICY['exhibit_url'], user_agent=user_agent,
        source_fetcher=source_fetcher, observed_at=observed_at,
    )
    extension['reason'] = 'reconciliation_exhibit_unavailable'
    if extension['exhibit'].get('status') == 'ready':
        extension.update(status='unverified_sources', reason=None)
    return extension


def fetch_mrvl_earnings_review(
    facts_receipt, *, ticker, expected_cik, user_agent,
    source_fetcher=None, observed_at=None,
):
    """Reuse Companyfacts; at most two profiles, two annual and two earnings documents.

    These research receipts carry no registered field or document permissions. Each
    issuer's source failure is independent, and no request is retried or saved.
    """
    mode_reason = _mode_reason('research')
    reason = mode_reason
    if not reason and (ticker != 'MRVL' or expected_cik != MRVL_CIK or not _facts_identity_valid(facts_receipt)):
        reason = 'review_companyfacts_identity_mismatch'
    if not reason and (not isinstance(user_agent, str) or not user_agent.strip()
                       or any(c in user_agent for c in '\r\n')):
        reason = 'sec_user_agent_required'
    if not reason and observed_at is not None and (
        not isinstance(observed_at, datetime) or observed_at.utcoffset() is None
    ):
        reason = 'invalid_observation'
    now = (observed_at or datetime.now(timezone.utc)) if not reason else datetime.now(timezone.utc)
    now = now.astimezone(timezone.utc)
    if not reason and not timedelta(0) <= now - _utc_timestamp(facts_receipt['observed_at']) <= timedelta(hours=24):
        reason = 'review_companyfacts_observation_unavailable'
    packet = {
        'schema_version': SCHEMA, 'ticker': 'MRVL', 'sec_cik': MRVL_CIK,
        'observed_at': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'facts': _unavailable(reason or 'review_facts_unavailable'),
        'profiles': {}, 'documents': {},
    }
    if reason:
        packet['reason'] = reason
        return seal_review_packet(packet)
    packet['facts'] = normalize_review_facts(facts_receipt)
    if packet['facts'].get('status') != 'ready':
        packet['reason'] = 'review_facts_unavailable'
        return seal_review_packet(packet)
    mrvl_annual_qualified = False
    for name in ('MRVL', 'AVGO'):
        policy = POLICIES[name]
        profile_url = f"https://data.sec.gov/submissions/CIK{policy['sec_cik']}.json"
        receipt = fetch_sec_json_receipt(
            profile_url, user_agent=user_agent, fetcher=source_fetcher, observed_at=observed_at,
        )
        packet['profiles'][name] = normalize_review_profile(receipt)
        selection = sec_exact_filing.select_sec_filing(name, policy['sec_cik'], receipt, period_kind='annual')
        body = receipt.get('payload')
        tickers = body.get('tickers') if isinstance(body, Mapping) else None
        if (selection.get('status') != 'selected' or not isinstance(tickers, list) or name not in tickers
                or any(selection.get(key) != policy[key] for key in (
                    'sec_cik', 'accession', 'form', 'filed', 'period_end', 'primary_document', 'source_url'
                ))):
            packet['documents'][name] = _unavailable('review_annual_scope_unavailable', policy['source_url'])
            continue
        if name == 'MRVL':
            mrvl_annual_qualified = True
        packet['documents'][name] = _fetch_document(
            policy['source_url'], user_agent=user_agent.strip(), source_fetcher=source_fetcher, observed_at=observed_at,
        )
    packet['after_tax_reconciliation'] = _after_tax_sources(
        packet['profiles'].get('MRVL'), annual_qualified=mrvl_annual_qualified,
        user_agent=user_agent.strip(), source_fetcher=source_fetcher, observed_at=observed_at,
    )
    packet['observed_at'] = (observed_at or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    return seal_review_packet(packet)
