"""Bounded, exact-URL SEC JSON receipts kept entirely in memory."""

import base64
import hashlib
import re
import time
from datetime import datetime, timezone
from urllib.request import Request, HTTPRedirectHandler, build_opener

from src.providers.sec_company_discovery import _modified_at
from src.sec_association_receipt import _json_object

MAX_SEC_RESPONSE_BYTES = 16 * 1024 * 1024
MAX_RETAINED_SEC_JSON_BYTES = 2 * 1024 * 1024
_URL = re.compile(r'https://(?:www\.sec\.gov/files/company_tickers(?:_exchange)?\.json|data\.sec\.gov/(?:api/xbrl/companyfacts|submissions)/CIK\d{10}\.json)\Z')


class _ExactSourceRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        # Refuse before issuing another request or forwarding identifying headers.
        return None


def open_exact_source(request, *, timeout=30):
    return build_opener(_ExactSourceRedirectHandler()).open(request, timeout=timeout)


urlopen = open_exact_source


def _fetch_raw(url, user_agent):
    try:
        with urlopen(Request(url, headers={'User-Agent':user_agent,'Accept':'application/json'}), timeout=30) as response:
            return response.read(MAX_SEC_RESPONSE_BYTES + 1), dict(response.headers.items()), response.geturl()
    finally:
        # Failed access is throttled too; callers can pause rather than storming.
        time.sleep(0.2)


def fetch_sec_json_receipt(url, *, user_agent, fetcher=None, observed_at=None, retain_raw=False):
    held={'status':'unavailable','source_url':url if isinstance(url,str) and _URL.fullmatch(url) else None}
    if type(retain_raw) is not bool:return {**held,'reason':'invalid_retention_request'}
    if not isinstance(url,str) or not _URL.fullmatch(url): return {**held,'reason':'unsupported_sec_url'}
    if not isinstance(user_agent,str) or not user_agent.strip() or any(c in user_agent for c in '\r\n'):
        return {**held,'reason':'sec_user_agent_required'}
    if observed_at is not None and (not isinstance(observed_at,datetime) or observed_at.utcoffset() is None):
        return {**held,'reason':'invalid_observation'}
    try:
        raw,headers,final_url=(fetcher or _fetch_raw)(url,user_agent.strip())
        observed=(observed_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
        if not isinstance(raw,bytes) or not 0<len(raw)<=MAX_SEC_RESPONSE_BYTES or final_url!=url:
            return {**held,'reason':'unverified_sec_response'}
        modified=_modified_at(headers,observed)
        payload=_json_object(raw,'invalid_sec_json')
    except (OSError,RuntimeError,TimeoutError,ValueError,TypeError,AttributeError,RecursionError):
        return {**held,'reason':'sec_receipt_unavailable'}
    result={'status':'ready','payload':payload,'source_url':url,
            'observed_at':observed.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'source_last_modified':modified,'payload_sha256':hashlib.sha256(raw).hexdigest()}
    if retain_raw and len(raw)<=MAX_RETAINED_SEC_JSON_BYTES:result['payload_raw_base64']=base64.b64encode(raw).decode('ascii')
    return result
