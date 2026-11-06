"""Exact visible-cover evidence for two coarse SEC submissions venue labels."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import re

from src.company_sec_online_preview import _iso_date, _utc_timestamp
from src.online_company_identity import _mode_reason
from src.sec_exact_filing import _digest, _fetch_html
from src.sec_listing_cover import (
    MAX_COVER_BYTES, FilingCase, document_receipt, filing_metadata, read_listing_cover,
)
from src.sec_selected_security import FINANCIAL_FORMS, IDENTITY_FORMS, _bound_body, _fresh, _metadata


@dataclass(frozen=True)
class _VenueScope:
    case: FilingCase
    report_date: str
    filed: str
    accepted_at: str
    common_title: str
    body_sha256: str


_SCOPES = {
    ('BKTI', '0000002186'): _VenueScope(
        FilingCase('BKTI', '0000002186', '0001437749-26-032498', 'bkti20261012_8k.htm'),
        '2026-10-08', '2026-10-13', '2026-10-13T11:15:08.000Z',
        'Common Stock , par value $0.60 per share',
        '12b2eb37d92e574fdbd03893eeba4711437e041a25a198eca40e64ab84cf1371',
    ),
    ('UMAC', '0001956955'): _VenueScope(
        FilingCase('UMAC', '0001956955', '0001683168-26-008349', 'umac_i10q-093026.htm', '10-Q'),
        '2026-09-30', '2026-11-05', '2026-11-05T21:07:09.000Z',
        'Common Stock, par value $0.01 per share',
        '6f300103af0d2707d186cee791a788db30980d1603397313c1cdc0d7dec49d43',
    ),
}
_EVENT_FORMS = {
    '8-A', '8-A12B', '8-A12G', '8-K12B', 'CERT', '25', '25-NSE',
    '15', '15-12B', '15-12G', '15-15D', '15F', '15F-12B', '15F-12G', '15F-15D',
}
LISTING_EVENT_FORMS = frozenset(_EVENT_FORMS | {form + '/A' for form in _EVENT_FORMS})
_RELEVANT_FORMS = FINANCIAL_FORMS | IDENTITY_FORMS | LISTING_EVENT_FORMS
_SCHEMA = 'peer-listing-venue-v1'
_SHA = re.compile(r'[0-9a-f]{64}\Z')
_PACKET_KEYS = {'schema_version', 'status', 'ticker', 'sec_cik', 'profile_sha256', 'document', 'packet_digest'}
_DOCUMENT_KEYS = {'source_url', 'observed_at', 'payload_sha256', 'body_sha256'}


def _scope(ticker, cik):
    return _SCOPES.get((ticker, cik)) if isinstance(ticker, str) and isinstance(cik, str) else None


def known_listing_venue_scope(ticker, cik):
    return _scope(ticker, cik) is not None


def _sha_valid(value):
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def _current_profile(profile, scope, now):
    case = scope.case
    if (not isinstance(now, datetime) or now.utcoffset() is None or not isinstance(profile, Mapping)
        or profile.get('status') != 'ready' or profile.get('source_url') != case.metadata_url
        or not _fresh(profile.get('observed_at'), now) or not _sha_valid(profile.get('payload_sha256'))):
        return False
    now = now.astimezone(timezone.utc)
    payload = profile['payload']
    if (payload.get('tickers') != [case.symbol] or payload.get('exchanges') != ['NYSE']
        or 'normalized_sha256' in profile and profile['normalized_sha256'] != _digest(payload)):
        return False
    metadata = filing_metadata(profile, case)
    if (not metadata or metadata['filed'] != scope.filed or metadata['report_date'] != scope.report_date
        or _utc_timestamp(metadata['accepted_at']) != _utc_timestamp(scope.accepted_at)):
        return False
    ordered = []
    for row in _metadata(profile):
        if row['form'] not in _RELEVANT_FORMS:
            continue
        filed = _iso_date(row['filingDate'])
        accepted = _utc_timestamp(row['acceptanceDateTime'])
        if filed is None or accepted is None or filed > now.date() or accepted > now:
            return False
        ordered.append(((filed, accepted), row))
    reviewed_order = (_iso_date(scope.filed), _utc_timestamp(scope.accepted_at))
    if not ordered or max(order for order, _ in ordered) != reviewed_order:
        return False
    latest = [row for order, row in ordered if order == reviewed_order]
    return (len(latest) == 1 and latest[0]['accessionNumber'] == case.accession
            and latest[0]['isInlineXBRL'] == latest[0]['isXBRL'] == 1)


def _seal(packet):
    return _digest({key: value for key, value in packet.items() if key != 'packet_digest'})


def fetch_listing_venue_evidence(ticker, cik, profile, *, user_agent, fetcher=None, observed_at=None,
                                 workspace_mode='research'):
    """Read one exact primary document on request and retain only its receipt."""
    if reason := _mode_reason(workspace_mode):
        return dict(status='unavailable', reason=reason)
    held = dict(status='unavailable', reason='listing_venue_scope_unverified')
    scope = _scope(ticker, cik)
    if scope is None:
        return dict(status='not_applicable')
    try:
        now = observed_at if observed_at is not None else datetime.now(timezone.utc)
        if not _current_profile(profile, scope, now):
            return held
        if not isinstance(user_agent, str) or not user_agent.strip() or any(c in user_agent for c in '\r\n'):
            return held
        url = scope.case.source_url
        if fetcher is None:
            raw, _, final = _fetch_html(url, user_agent.strip(), max_bytes=MAX_COVER_BYTES)
        else:
            raw, _, final = fetcher(url, user_agent.strip())
        document = document_receipt(raw, final, scope.case, observed_at)
        if document is None:
            return held
        body_sha256 = hashlib.sha256(_bound_body(raw, 'sec-empty-tail-script-v1')).hexdigest()
        if (body_sha256 != scope.body_sha256
            or read_listing_cover(raw, ticker) != (scope.common_title, ['NYSE American'])):
            return held
        document.update(source_url=url, body_sha256=body_sha256)
        packet = dict(schema_version=_SCHEMA, status='observed', ticker=ticker, sec_cik=cik,
                      profile_sha256=profile['payload_sha256'], document=document)
        return dict(packet, packet_digest=_seal(packet))
    except (OSError, RuntimeError):
        return dict(status='unavailable', reason='listing_venue_source_unavailable')
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        return held


def validated_listing_venue_evidence(packet, *, ticker, cik, profile, as_of):
    """Revalidate the original dated receipt without requesting another document."""
    scope = _scope(ticker, cik)
    if _mode_reason('research') or scope is None or not isinstance(packet, Mapping):
        return None
    try:
        if (set(packet) != _PACKET_KEYS or packet['schema_version'] != _SCHEMA or packet['status'] != 'observed'
            or (packet['ticker'], packet['sec_cik']) != (ticker, cik) or not _current_profile(profile, scope, as_of)
            or packet['profile_sha256'] != profile['payload_sha256'] or packet['packet_digest'] != _seal(packet)):
            return None
        document = packet['document']
        if (not isinstance(document, Mapping) or set(document) != _DOCUMENT_KEYS
            or document['source_url'] != scope.case.source_url or not _fresh(document['observed_at'], as_of)
            or _utc_timestamp(document['observed_at']) < _utc_timestamp(scope.accepted_at)
            or not _sha_valid(document['payload_sha256']) or document['body_sha256'] != scope.body_sha256):
            return None
        return dict(document, accession=scope.case.accession, form=scope.case.form, filed=scope.filed,
                    reported_exchange='NYSE', confirmed_exchange='NYSE American')
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        return None
