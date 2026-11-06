"""Identity-only proof for SO's one reviewed SEC co-registrant filing."""

import base64
import binascii
from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib
import re

from src.online_company_identity import _mode_reason
from src.online_sec_receipt import MAX_RETAINED_SEC_JSON_BYTES, fetch_sec_json_receipt
from src.sec_association_receipt import _json_object
from src.sec_exact_filing import MAX_FILING_BYTES, _digest, _fetch_html
from src.sec_selected_security import _bound_body, _fresh, _metadata


SCHEMA = 'so-vendor-sec-cofiling-v1'
PARENT_CIK = '0000092122'
CO_REGISTRANT_CIK = '0001160661'
FILING = dict(form='10-Q', reportDate='2025-09-30', filingDate='2025-10-30',
              acceptanceDateTime='2025-10-29T21:40:57.000Z', accessionNumber='0000092122-25-000084',
              primaryDocument='so-20250930.htm', isInlineXBRL=1, isXBRL=1)
VENDOR_LINK = 'https://finance.yahoo.com/sec-filing/SO/0000092122-25-000084_92122'
VENDOR_EXHIBIT = 'https://cdn.yahoofinance.com/prod/sec-filings/0001160661/000009212225000084/so-20250930.htm'
ARCHIVE_URLS = tuple(f'https://www.sec.gov/Archives/edgar/data/{cik}/000009212225000084/so-20250930.htm'
                     for cik in (92122, 1160661))
BODY_SHA256 = '3e5351fac2c5a2fc1a8759dc157dc331b679e0fb72bd59d68f79f9560936d8ab'
_SHA = re.compile(r'[0-9a-f]{64}\Z')
_DOC_KEYS = {'source_url', 'observed_at', 'payload_sha256', 'body_sha256'}
_PACKET_KEYS = {'schema_version', 'status', 'co_registrant', 'documents',
                'parent_sha256', 'vendor_sha256', 'packet_digest'}


def _submissions_url(cik):
    return f'https://data.sec.gov/submissions/CIK{cik}.json'


def _valid_digest(value):
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def _filing_confirmed(profile, cik, as_of):
    if (profile.get('status') != 'ready' or profile.get('source_url') != _submissions_url(cik)
        or not _fresh(profile.get('observed_at'), as_of) or not _valid_digest(profile.get('payload_sha256'))):
        return False
    body = profile['payload']
    if (type(body['cik']) not in {str, int} or str(int(body['cik'])).zfill(10) != cik
        or 'normalized_sha256' in profile and profile['normalized_sha256'] != _digest(body)):
        return False
    return [row for row in _metadata(profile) if row['accessionNumber'] == FILING['accessionNumber']] == [FILING]


def _matches_request(cik, profile, vendor, as_of):
    if (cik != PARENT_CIK or not isinstance(as_of, datetime) or as_of.utcoffset() is None
        or not _filing_confirmed(profile, cik, as_of)):
        return False
    tickers = profile['payload'].get('tickers')
    if (not isinstance(tickers, list) or tickers.count('SO') != 1 or vendor.get('status') != 'observed'
        or vendor.get('source_ref') != 'https://finance.yahoo.com/quote/SO/'
        or not _fresh(vendor.get('observed_at'), as_of)):
        return False
    payload = vendor['payload']
    filings = payload.get('filings')
    if (vendor.get('normalized_sha256') != _digest(payload) or payload['info'].get('symbol') != 'SO'
        or not isinstance(filings, list) or not 1 <= len(filings) <= 256):
        return False
    candidates = [row for row in filings if isinstance(row.get('edgarUrl'), str)
                  and FILING['accessionNumber'] in row['edgarUrl']]
    if len(candidates) != 1:
        return False
    row = candidates[0]
    return (row.get('edgarUrl') == VENDOR_LINK and row.get('type') == FILING['form']
            and row.get('date') == FILING['filingDate'] and row.get('exhibits', {}).get('10-Q') == VENDOR_EXHIBIT)


def _co_registrant_confirmed(receipt, as_of):
    if not _filing_confirmed(receipt, CO_REGISTRANT_CIK, as_of):
        return False
    encoded = receipt.get('payload_raw_base64')
    if not isinstance(encoded, str) or not 0 < len(encoded) <= 4 * ((MAX_RETAINED_SEC_JSON_BYTES + 2) // 3):
        return False
    raw = base64.b64decode(encoded, validate=True)
    return (0 < len(raw) <= MAX_RETAINED_SEC_JSON_BYTES
            and hashlib.sha256(raw).hexdigest() == receipt['payload_sha256']
            and _json_object(raw, 'invalid_co_registrant_json') == receipt['payload'])


def _seal(packet):
    return _digest({key: value for key, value in packet.items() if key != 'packet_digest'})


def fetch_vendor_cofiling_match(cik, profile, vendor, *, user_agent, fetcher=None, html_fetcher=None,
                               observed_at=None, workspace_mode='research'):
    """Verify two exact SEC archive responses before retaining their receipt digests."""
    if reason := _mode_reason(workspace_mode):
        return dict(status='unavailable', reason=reason)
    clock = lambda: observed_at or datetime.now(timezone.utc)
    held = dict(status='unavailable', reason='vendor_cofiling_scope_unverified')
    try:
        if not _matches_request(cik, profile, vendor, clock()):
            return dict(status='not_applicable')
        if not isinstance(user_agent, str) or not user_agent.strip() or any(c in user_agent for c in '\r\n'):
            return held
        co_registrant = fetch_sec_json_receipt(_submissions_url(CO_REGISTRANT_CIK), user_agent=user_agent,
                                             fetcher=fetcher, observed_at=observed_at, retain_raw=True)
        if co_registrant.get('status') != 'ready':
            return dict(status='unavailable', reason='vendor_cofiling_source_unavailable')
        if not _co_registrant_confirmed(co_registrant, clock()):
            return held
        documents = []
        for url in ARCHIVE_URLS:
            raw, _, final_url = (html_fetcher or _fetch_html)(url, user_agent.strip())
            if final_url != url or not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_FILING_BYTES:
                return held
            body_sha = hashlib.sha256(_bound_body(raw, 'sec-empty-tail-script-v1')).hexdigest()
            if body_sha != BODY_SHA256:
                return held
            documents.append(dict(source_url=url, observed_at=clock().astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                                  payload_sha256=hashlib.sha256(raw).hexdigest(), body_sha256=body_sha))
        packet = dict(schema_version=SCHEMA, status='observed', co_registrant=co_registrant, documents=documents,
                      parent_sha256=profile['payload_sha256'], vendor_sha256=vendor['normalized_sha256'])
        return dict(packet, packet_digest=_seal(packet))
    except (OSError, RuntimeError):
        return dict(status='unavailable', reason='vendor_cofiling_source_unavailable')
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError, binascii.Error):
        return held


def validated_vendor_cofiling_match(packet, *, cik, profile, vendor, as_of):
    """Recheck the sealed session receipts against the current exact request."""
    if _mode_reason('research') or not isinstance(packet, Mapping):
        return None
    try:
        if (set(packet) != _PACKET_KEYS or packet.get('schema_version') != SCHEMA or packet.get('status') != 'observed'
            or not _matches_request(cik, profile, vendor, as_of) or packet['parent_sha256'] != profile['payload_sha256']
            or packet['vendor_sha256'] != vendor['normalized_sha256'] or not _co_registrant_confirmed(packet['co_registrant'], as_of)):
            return None
        documents = packet['documents']
        if (not isinstance(documents, list) or len(documents) != len(ARCHIVE_URLS)
            or any(set(doc) != _DOC_KEYS or doc['source_url'] != url or not _fresh(doc['observed_at'], as_of)
                   or not _valid_digest(doc['payload_sha256']) or doc['body_sha256'] != BODY_SHA256
                   for doc, url in zip(documents, ARCHIVE_URLS, strict=True))
            or packet['packet_digest'] != _seal(packet)):
            return None
        receipt = packet['co_registrant']
        return dict(source_ref=VENDOR_LINK, accession=FILING['accessionNumber'], filed=FILING['filingDate'],
                    cofiling_documents=[dict(doc) for doc in documents], co_registrant_source_ref=receipt['source_url'],
                    co_registrant_observed_at=receipt['observed_at'], co_registrant_sha256=receipt['payload_sha256'],
                    financial_denominator_modified=False)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError, binascii.Error):
        return None
