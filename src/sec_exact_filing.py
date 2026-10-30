"""Exact SEC primary-document inspection; distinct from Companyfacts approval."""
from collections.abc import Mapping
from datetime import datetime, timezone, timedelta
import hashlib
import json
import re
import time
from urllib.error import HTTPError
from urllib.request import Request

from src.company_sec_online_preview import _iso_date, _utc_timestamp, ANNUAL_FORMS
from src.online_company_identity import _mode_reason
from src.online_sec_receipt import fetch_sec_json_receipt, open_exact_source as urlopen
from src.providers.sec_company_discovery import _modified_at

MAX_FILING_BYTES = 32 * 1024 * 1024
SOURCE_ID = 'sec_archive_inline'
RIGHTS = 'unregistered_sec_archive_personal_inspection_only'
SCHEMA = 'sec-exact-filing-v1'
SESSION_KEY = 'company_exact_sec_filing_v1'
MAP_URL = 'https://www.sec.gov/files/company_tickers.json'
FORMS = {'annual': ANNUAL_FORMS, 'quarterly': frozenset({'10-Q','10-Q/A'})}


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _cik(value):
    return type(value) in {str,int} and re.fullmatch(r'\d{1,10}',str(value)) is not None and int(value)>0


def _reference_valid(ref, url=None):
    return (isinstance(ref,Mapping) and (url is None or ref.get('source_url')==url)
        and _utc_timestamp(ref.get('observed_at')) is not None
        and isinstance(ref.get('payload_sha256'),str) and re.fullmatch(r'[0-9a-f]{64}',ref['payload_sha256']) is not None)


def select_sec_filing(ticker,cik,submissions_receipt,*,period_kind):
    held=dict(status='withheld',ticker=ticker,period_kind=period_kind,reason='filing_selection_unavailable')
    if (not isinstance(ticker,str) or not re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,19}',ticker)
        or not isinstance(cik,str) or not re.fullmatch(r'\d{10}',cik) or int(cik)==0
        or period_kind not in FORMS or not isinstance(submissions_receipt,Mapping)
        or submissions_receipt.get('status')!='ready'
        or not _reference_valid(submissions_receipt,f'https://data.sec.gov/submissions/CIK{cik}.json')): return held
    body=submissions_receipt.get('payload')
    if not isinstance(body,Mapping) or not _cik(body.get('cik')) or str(int(body['cik'])).zfill(10)!=cik: return {**held,'reason':'submissions_identity_mismatch'}
    filings=body.get('filings');recent=filings.get('recent') if isinstance(filings,Mapping) else None
    columns=('accessionNumber','reportDate','filingDate','acceptanceDateTime','form','primaryDocument','isInlineXBRL','isXBRL')
    if not isinstance(recent,Mapping) or any(not isinstance(recent.get(k),list) for k in columns): return held
    length=len(recent['form'])
    if not 1<=length<=2000 or any(len(recent[k])!=length for k in columns): return {**held,'reason':'filing_metadata_schema_invalid'}
    records=[{k:recent[k][i] for k in columns} for i in range(length) if isinstance(recent['form'][i],str) and recent['form'][i] in FORMS[period_kind]]
    if not records: return {**held,'reason':'supported_filing_form_unavailable'}
    observed=_utc_timestamp(submissions_receipt['observed_at'])
    # A malformed recent amendment must not silently restore an older filing.
    if any(_iso_date(r['reportDate']) is None or _iso_date(r['filingDate']) is None for r in records): return {**held,'reason':'unresolved_filing_dates'}
    end=max(r['reportDate'] for r in records); candidates=[r for r in records if r['reportDate']==end]
    filed=max(r['filingDate'] for r in candidates); candidates=[r for r in candidates if r['filingDate']==filed]
    if any(_utc_timestamp(r['acceptanceDateTime']) is None for r in candidates): return {**held,'reason':'unresolved_acceptance_time'}
    accepted=max(_utc_timestamp(r['acceptanceDateTime']) for r in candidates)
    candidates=[r for r in candidates if _utc_timestamp(r['acceptanceDateTime'])==accepted]
    if any(not all(isinstance(r[k],str) for k in columns[:6])
        or any(type(r[k]) is not int or r[k]!=1 for k in ('isInlineXBRL','isXBRL')) for r in candidates):
        return {**held,'reason':'latest_filing_identity_or_inline_metadata_invalid'}
    identities={tuple(r[k] for k in columns) for r in candidates}
    if len(identities)!=1: return {**held,'reason':'ambiguous_latest_filing'}
    r=candidates[0];document=r['primaryDocument']; accession=r['accessionNumber']
    if (not _iso_date(end)<=_iso_date(filed)<=observed.date() or not _iso_date(end)<=accepted.date()<=observed.date() or accepted>observed
        or not isinstance(accession,str) or not re.fullmatch(r'\d{10}-\d{2}-\d{6}',accession)
        or not isinstance(document,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,180}\.(?:htm|html|xhtml)',document)
        or '..' in document or type(r['isInlineXBRL']) is not int or r['isInlineXBRL']!=1
        or type(r['isXBRL']) is not int or r['isXBRL']!=1): return {**held,'reason':'latest_filing_identity_or_inline_metadata_invalid'}
    url=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace("-","")}/{document}'
    ref={k:submissions_receipt[k] for k in ('source_url','observed_at','payload_sha256')}
    return dict(status='selected',ticker=ticker,sec_cik=cik,period_kind=period_kind,period_end=end,form=r['form'],
        filed=filed,accepted_at=r['acceptanceDateTime'],accession=accession,primary_document=document,source_url=url,source_receipts=[ref])


def _fetch_html(url,user_agent):
    try:
        with urlopen(Request(url,headers={'User-Agent':user_agent,'Accept':'text/html'}),timeout=30) as response:
            return response.read(MAX_FILING_BYTES+1),dict(response.headers.items()),response.geturl()
    finally:
        time.sleep(0.2)


def fetch_sec_filing_preview(ticker,*,period_kind,user_agent,fetcher=None,observed_at=None,expected_cik=None,workspace_mode='research'):
    reason=_mode_reason(workspace_mode)
    held=dict(status='withheld',ticker=ticker,period_kind=period_kind,reason=reason or 'sec_filing_unavailable')
    if (reason or period_kind not in FORMS or not isinstance(ticker,str) or not re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,19}',ticker)
        or not isinstance(user_agent,str) or not user_agent.strip() or any(c in user_agent for c in '\r\n')): return held
    if observed_at is not None and (not isinstance(observed_at,datetime) or observed_at.utcoffset() is None): return held
    mapping=fetch_sec_json_receipt(MAP_URL,user_agent=user_agent,fetcher=fetcher,observed_at=observed_at)
    if mapping['status']!='ready' or not isinstance(mapping.get('payload'),Mapping): return {**held,'reason':mapping.get('reason','sec_map_unavailable')}
    aliases={ticker,ticker.replace('.','-'),ticker.replace('-','.')}; ciks=set()
    for r in mapping['payload'].values():
        if isinstance(r,Mapping) and r.get('ticker') in aliases:
            if not _cik(r.get('cik_str')): return held
            ciks.add(str(int(r['cik_str'])).zfill(10))
    if len(ciks)!=1: return {**held,'reason':'ambiguous_or_missing_sec_association'}
    cik=next(iter(ciks))
    if expected_cik is not None and expected_cik!=cik: return {**held,'reason':'selected_company_identity_mismatch'}
    submissions=fetch_sec_json_receipt(f'https://data.sec.gov/submissions/CIK{cik}.json',user_agent=user_agent,fetcher=fetcher,observed_at=observed_at)
    selection=select_sec_filing(ticker,cik,submissions,period_kind=period_kind)
    if selection['status']!='selected': return selection
    selection['source_receipts'].insert(0,{k:mapping[k] for k in ('source_url','observed_at','payload_sha256')})
    try:
        raw,headers,final_url=(fetcher or _fetch_html)(selection['source_url'],user_agent)
        now=(observed_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
        if not isinstance(raw,bytes) or not 0<len(raw)<=MAX_FILING_BYTES or final_url!=selection['source_url']:
            return {**held,'reason':'unverified_filing_document'}
        receipt=dict(status='ready',source_url=selection['source_url'],observed_at=now.strftime('%Y-%m-%dT%H:%M:%SZ'),
                     payload_sha256=hashlib.sha256(raw).hexdigest(),source_last_modified=_modified_at(headers,now))
        from src.sec_inline_filing import extract_inline_filing
        return extract_inline_filing(raw,selection,receipt)
    except HTTPError as exc:
        return {**held,'reason':'sec_archive_access_limited' if exc.code in {403,429,503} else 'sec_archive_http_unavailable'}
    except (OSError,ValueError,TypeError,RuntimeError,RecursionError): return held


def validated_filing_preview(packet,ticker,period_kind):
    if not isinstance(packet,Mapping) or packet.get('status')!='inspection_only': return None
    if (packet.get('schema_version')!=SCHEMA or packet.get('source_id')!=SOURCE_ID or packet.get('ticker')!=ticker
        or packet.get('period_kind')!=period_kind or period_kind not in FORMS or packet.get('rights_status')!=RIGHTS
        or packet.get('commercial_eligible') is not False or packet.get('readiness_promoted') is not False): return None
    cik=packet.get('sec_cik');acc=packet.get('accession');doc=packet.get('primary_document')
    if (not isinstance(cik,str) or not re.fullmatch(r'\d{10}',cik) or int(cik)==0 or not isinstance(acc,str)
        or not re.fullmatch(r'\d{10}-\d{2}-\d{6}',acc) or not isinstance(doc,str)
        or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,180}\.(?:htm|html|xhtml)',doc) or '..' in doc): return None
    url=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace("-","")}/{doc}'
    if packet.get('source_url')!=url: return None
    refs=packet.get('source_receipts');urls=[MAP_URL,f'https://data.sec.gov/submissions/CIK{cik}.json',url]
    if not isinstance(refs,list) or len(refs)!=3 or any(not _reference_valid(r,u) for r,u in zip(refs,urls)): return None
    times=[_utc_timestamp(r['observed_at']) for r in refs]
    if not times[0]<=times[1]<=times[2] or times[2]-times[0]>timedelta(hours=24): return None
    if any(packet.get(k)!=refs[-1].get(k) for k in ('observed_at','payload_sha256')): return None
    observed=_utc_timestamp(packet.get('observed_at'));end=_iso_date(packet.get('period_end'));filed=_iso_date(packet.get('filed'));accepted=_utc_timestamp(packet.get('accepted_at'))
    if not end or not filed or not accepted or not end<=filed<=observed.date() or not end<=accepted.date()<=observed.date() or accepted>observed or packet.get('form') not in FORMS[period_kind]: return None
    if packet.get('taxonomy') not in {'us-gaap','ifrs-full'} or not isinstance(packet.get('unit'),str) or not re.fullmatch(r'[A-Z]{3}',packet['unit']): return None
    periods=packet.get('periods')
    if not isinstance(periods,list) or not 1<=len(periods)<=2: return None
    from src.sec_inline_filing import CATALOG, FIELDS
    seen=set()
    for row in periods:
        if not isinstance(row,Mapping): return None
        kind=row.get('kind');start=_iso_date(row.get('period_start'))
        if kind in seen or kind not in {period_kind,'cumulative'} or kind=='cumulative' and period_kind!='quarterly' or not start or row.get('period_end')!=packet['period_end']: return None
        seen.add(kind);days=(end-start).days
        if not (300<=days<=430 if kind=='annual' else 70<=days<=105 if kind=='quarterly' else 105<days<=320): return None
        fields=row.get('fields');holds=row.get('withheld_fields')
        if not isinstance(fields,Mapping) or not isinstance(holds,Mapping) or set(fields)|set(holds)!=set(FIELDS) or set(fields)&set(holds): return None
        if any(not isinstance(v,str) or not v for v in holds.values()): return None
        for name,f in fields.items():
            if not isinstance(f,Mapping) or f.get('field')!=name or f.get('concept') not in CATALOG[packet['taxonomy']][name] or f.get('taxonomy')!=packet['taxonomy']: return None
            if (type(f.get('value')) not in {int,float} or not (-1e20<=f['value']<=1e20)
                or f.get('unit')!=packet['unit'] or f.get('period_start')!=row['period_start'] or f.get('period_end')!=row['period_end']
                or f.get('rights_status')!=RIGHTS or not isinstance(f.get('fact_id'),str) or f.get('source_ref')!=url+'#'+f['fact_id']): return None
    if period_kind not in seen: return None
    try:
        if packet.get('packet_digest')!=_digest({k:v for k,v in packet.items() if k!='packet_digest'}): return None
    except (TypeError,ValueError): return None
    return dict(packet)


def get_company_filing_preview(ticker,session_state,*,period_kind,refresh_requested,user_agent,fetcher=None,
                               observed_at=None,expected_cik=None,workspace_mode='research'):
    reason=_mode_reason(workspace_mode)
    if reason:return dict(status='withheld',ticker=ticker,period_kind=period_kind,reason=reason)
    if refresh_requested:
        packet=fetch_sec_filing_preview(ticker,period_kind=period_kind,user_agent=user_agent,fetcher=fetcher,
            observed_at=observed_at,expected_cik=expected_cik,workspace_mode=workspace_mode)
        session_state[SESSION_KEY]=dict(ticker=ticker,period_kind=period_kind,packet=packet)
        return packet
    cached=session_state.get(SESSION_KEY)
    if not isinstance(cached,Mapping) or cached.get('ticker')!=ticker or cached.get('period_kind')!=period_kind:
        return dict(status='not_requested',ticker=ticker,period_kind=period_kind)
    packet=cached.get('packet')
    if isinstance(packet,Mapping) and packet.get('status')=='withheld':
        reason=packet.get('reason')
        return dict(status='withheld',ticker=ticker,period_kind=period_kind,
            reason=reason if isinstance(reason,str) and len(reason)<=160 else 'filing_evidence_unavailable')
    validated=validated_filing_preview(packet,ticker,period_kind)
    if validated and (expected_cik is None or validated['sec_cik']==expected_cik):return validated
    return dict(status='withheld',ticker=ticker,period_kind=period_kind,reason='invalid_cached_filing_or_identity')
