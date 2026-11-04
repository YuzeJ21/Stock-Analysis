"""Original-dated, session-only listing recovery; never financial verdict reuse."""
from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from src.company_sec_online_preview import _utc_timestamp
from src.online_company_identity import _mode_reason
from src.online_us_universe import SOURCE_URLS
from src.security_classification import validated_classification, _digest

SESSION_KEY='online_listing_last_good_v1'
SCHEMA='online-listing-session-v1'
_FAILURES={'classification_source_unavailable','listing_source_unavailable'}
_REASONS={'directory_incomplete','source_transport_unavailable','source_access_limited',
          'source_response_unverified','directory_schema_invalid','directory_date_invalid'}


def fresh_classification(packet, as_of):
    """Revalidate the complete packet and both clocks, without renewing either."""
    try:
        if not isinstance(as_of,datetime) or as_of.utcoffset() is None:return None
        checked=validated_classification(packet)
        if checked is None:return None
        for ref in checked['inventory']['source_receipts']:
            observed=_utc_timestamp(ref['observed_at'])
            if observed is None or not timedelta(0)<=as_of-observed<=timedelta(hours=24):return None
            if 'source_created_at' in ref:
                value=ref['source_created_at']
                created=datetime.strptime(value,'%Y-%m-%dT%H:%M')
                if created.strftime('%Y-%m-%dT%H:%M')!=value:return None
                created=created.replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc)
                if not timedelta(0)<=as_of-created<=timedelta(days=7):return None
        return checked
    except (ValueError,TypeError,KeyError,AttributeError,OverflowError,RecursionError):return None


def _attempts(value):
    rows=value if isinstance(value,list) and len(value)<=4 else []
    result=[]
    for row in rows:
        if not isinstance(row,Mapping) or row.get('source_url') not in SOURCE_URLS:continue
        reason=row.get('reason')
        out=dict(source_url=row['source_url'],status='unavailable' if reason else 'received',
                 reason=reason if reason in _REASONS else 'source_response_unverified' if reason else None)
        if _utc_timestamp(row.get('observed_at')) is not None:out['observed_at']=row['observed_at']
        if type(row.get('byte_count')) is int and 0<=row['byte_count']<=8*1024*1024:out['byte_count']=row['byte_count']
        digest=row.get('payload_sha256')
        if isinstance(digest,str) and len(digest)==64 and all(c in '0123456789abcdef' for c in digest):out['payload_sha256']=digest
        result.append(out)
    return result


def acquire_classification(state, fetch, *, as_of=None, clock=None):
    """One explicit acquisition; unavailable source may use this session's receipt."""
    context=dict(schema_version=SCHEMA,selection='none',attempt_status='unavailable',
                 source_attempts=[],source_receipts=[],reason='classification_source_unavailable')
    if _mode_reason('research'):
        context['reason']=_mode_reason('research');return None,context
    clock=clock or (lambda:datetime.now(timezone.utc))
    started=as_of if as_of is not None else clock()
    if not isinstance(started,datetime) or started.utcoffset() is None:
        context['reason']='invalid_observation';return None,context
    context['attempted_at']=started.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    try:incoming=fetch()
    except Exception:incoming=dict(status='unavailable',reason='classification_source_unavailable')
    completed=as_of if as_of is not None else clock()
    if not isinstance(completed,datetime) or completed.utcoffset() is None or completed<started:
        context['reason']='invalid_observation';return None,context
    context['completed_at']=completed.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    packet=fresh_classification(incoming,completed)
    if packet is not None:
        envelope=dict(schema_version=SCHEMA,classification=deepcopy(packet))
        envelope['digest']=_digest(envelope);state[SESSION_KEY]=envelope
        context.update(selection='returned_receipt',attempt_status='returned',reason=None)
    else:
        if not isinstance(incoming,Mapping):return None,context
        context['source_attempts']=_attempts(incoming.get('source_attempts'))
        if incoming.get('status') not in {'withheld','unavailable'} or incoming.get('reason') not in _FAILURES:
            context['reason']='classification_receipt_invalid_or_expired';return None,context
        if any(r.get('reason')=='source_access_limited' for r in context['source_attempts']):return None,context
        saved=state.get(SESSION_KEY)
        try:
            valid=(isinstance(saved,Mapping) and saved.get('schema_version')==SCHEMA
                   and saved.get('digest')==_digest({k:v for k,v in saved.items() if k!='digest'}))
            packet=fresh_classification(saved.get('classification'),completed) if valid else None
        except (ValueError,TypeError,AttributeError,RecursionError):packet=None
        if packet is None:return None,context
        context['selection']='recent_session'
    receipts=deepcopy(packet['inventory']['source_receipts'])
    context.update(source_receipts=receipts,classification_digest=packet['packet_digest'],
                   observed_from=min(r['observed_at'] for r in receipts),observed_to=max(r['observed_at'] for r in receipts))
    return packet,context
