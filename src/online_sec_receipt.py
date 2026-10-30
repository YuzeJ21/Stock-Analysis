"""Bounded, exact-URL SEC JSON receipts kept entirely in memory."""

import hashlib
import re
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen

from src.providers.sec_company_discovery import _modified_at
from src.sec_association_receipt import _json_object

MAX_SEC_RESPONSE_BYTES = 16 * 1024 * 1024
_URL = re.compile(r'https://(?:www\.sec\.gov/files/company_tickers(?:_exchange)?\.json|data\.sec\.gov/(?:api/xbrl/companyfacts|submissions)/CIK\d{10}\.json)\Z')


def _fetch_raw(url, user_agent):
    with urlopen(Request(url, headers={'User-Agent':user_agent,'Accept':'application/json'}), timeout=30) as response:
        result = response.read(MAX_SEC_RESPONSE_BYTES + 1), dict(response.headers.items()), response.geturl()
    time.sleep(0.2)
    return result


def fetch_sec_json_receipt(url, *, user_agent, fetcher=None, observed_at=None):
    held={'status':'unavailable','source_url':url if isinstance(url,str) and _URL.fullmatch(url) else None}
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
    return {'status':'ready','payload':payload,'source_url':url,
            'observed_at':observed.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'source_last_modified':modified,'payload_sha256':hashlib.sha256(raw).hexdigest()}

