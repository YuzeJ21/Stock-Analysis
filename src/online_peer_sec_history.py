"""One current-pointer-bound historical SEC match, used for vendor identity only."""
from collections.abc import Mapping
from datetime import datetime,timezone
import base64,binascii,hashlib,re

from src.online_company_identity import _mode_reason
from src.company_sec_online_preview import _iso_date,_utc_timestamp
from src.online_sec_receipt import fetch_sec_json_receipt,MAX_RETAINED_SEC_JSON_BYTES
from src.sec_association_receipt import _json_object
from src.sec_exact_filing import _digest
from src.sec_selected_security import _fresh,FINANCIAL_FORMS,KEYS

SCHEMA='vendor-sec-history-v1'


def _need(value):
    if not value:raise ValueError('vendor_history_scope_unverified')


def _request(cik,profile,vendor,now):
    _need(isinstance(now,datetime) and now.utcoffset() is not None and isinstance(cik,str) and re.fullmatch(r'\d{10}',cik))
    _need(isinstance(profile,Mapping) and profile.get('status')=='ready' and profile.get('source_url')==f'https://data.sec.gov/submissions/CIK{cik}.json' and _fresh(profile.get('observed_at'),now))
    body=profile['payload'];_need(str(int(body['cik'])).zfill(10)==cik and ('normalized_sha256' not in profile or profile['normalized_sha256']==_digest(body)))
    _need(isinstance(vendor,Mapping) and vendor.get('status')=='observed' and _fresh(vendor.get('observed_at'),now) and vendor.get('normalized_sha256')==_digest(vendor['payload']))
    symbol=vendor['payload']['info']['symbol'];_need(isinstance(symbol,str) and re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,19}',symbol) and vendor.get('source_ref')==f'https://finance.yahoo.com/quote/{symbol}/')
    recent=body['filings']['recent'];cols=('form','reportDate','filingDate','accessionNumber','primaryDocument')
    _need(all(isinstance(recent.get(k),list) for k in cols) and 0<len(recent['form'])<=2000 and all(len(recent[k])==len(recent['form']) for k in cols))
    current=[dict(zip(cols,r)) for r in zip(*(recent[k] for k in cols))]
    filings=vendor['payload']['filings'];_need(isinstance(filings,list) and 0<len(filings)<=256)
    targets=[];already=False
    for row in filings:
        _need(isinstance(row,Mapping))
        if row.get('type') not in FINANCIAL_FORMS:continue
        match=re.fullmatch(r'https://finance\.yahoo\.com/sec-filing/'+re.escape(symbol)+r'/(\d{10}-\d{2}-\d{6})_(\d{1,10})',row.get('edgarUrl',''))
        _need(match is not None and str(int(match[2])).zfill(10)==cik and _iso_date(row.get('date')) is not None and _iso_date(row['date'])<=now.date())
        target=dict(form=row['type'],filingDate=row['date'],accessionNumber=match[1],source_ref=row['edgarUrl'],exhibit=row.get('exhibits',{}).get(row['type']))
        for r in current:
            expected=f'https://cdn.yahoofinance.com/prod/sec-filings/{cik}/{match[1].replace("-","")}/{r["primaryDocument"]}'
            if (r['form'],r['filingDate'],r['accessionNumber'],expected)==(target['form'],target['filingDate'],target['accessionNumber'],target['exhibit']):already=True
        targets.append(target)
    if already:return None,None
    _need(targets);latest=max(t['filingDate'] for t in targets);targets=[t for t in targets if t['filingDate']==latest]
    unique={_digest(t):t for t in targets};_need(len(unique)==1);target=next(iter(unique.values()))
    pointers=body['filings'].get('files');_need(isinstance(pointers,list) and 0<len(pointers)<=100);matches=[]
    for pointer in pointers:
        _need(isinstance(pointer,Mapping) and isinstance(pointer.get('name'),str) and re.fullmatch('CIK'+cik+r'-submissions-\d{3}\.json',pointer['name']))
        start,end=_iso_date(pointer.get('filingFrom')),_iso_date(pointer.get('filingTo'))
        _need(start is not None and end is not None and start<=end and type(pointer.get('filingCount')) is int and 0<pointer['filingCount']<=50000)
        if start<=_iso_date(target['filingDate'])<=end:matches.append(dict(pointer))
    _need(len(matches)==1)
    return target,matches[0]


def fetch_vendor_history_match(cik,profile,vendor,*,user_agent,fetcher=None,observed_at=None,workspace_mode='research'):
    held=dict(status='unavailable',reason=_mode_reason(workspace_mode) or 'vendor_history_scope_unverified')
    if _mode_reason(workspace_mode):return held
    try:
        now=observed_at or datetime.now(timezone.utc);target,pointer=_request(cik,profile,vendor,now)
        if target is None:return dict(status='not_applicable')
        url='https://data.sec.gov/submissions/'+pointer['name']
        receipt=fetch_sec_json_receipt(url,user_agent=user_agent,fetcher=fetcher,observed_at=observed_at,retain_raw=True)
        if receipt.get('status')!='ready':return dict(status='unavailable',reason='vendor_history_source_unavailable')
        packet=dict(schema_version=SCHEMA,status='observed',sec_cik=cik,target=target,pointer=pointer,receipt=receipt)
        return packet if validated_vendor_history_match(packet,cik=cik,profile=profile,vendor=vendor,as_of=observed_at or datetime.now(timezone.utc)) else held
    except (ValueError,TypeError,KeyError,AttributeError,OverflowError,RecursionError):return held


def validated_vendor_history_match(packet,*,cik,profile,vendor,as_of):
    if _mode_reason('research'):return []
    try:
        _need(isinstance(packet,Mapping) and packet.get('schema_version')==SCHEMA and packet.get('status')=='observed' and packet.get('sec_cik')==cik)
        target,pointer=_request(cik,profile,vendor,as_of);_need(target is not None and packet.get('target')==target and packet.get('pointer')==pointer)
        receipt=packet['receipt'];url='https://data.sec.gov/submissions/'+pointer['name'];encoded=receipt.get('payload_raw_base64')
        _need(receipt.get('status')=='ready' and receipt.get('source_url')==url and _fresh(receipt.get('observed_at'),as_of) and isinstance(encoded,str) and 0<len(encoded)<=4*((MAX_RETAINED_SEC_JSON_BYTES+2)//3))
        raw=base64.b64decode(encoded,validate=True);_need(0<len(raw)<=MAX_RETAINED_SEC_JSON_BYTES and hashlib.sha256(raw).hexdigest()==receipt.get('payload_sha256'))
        body=_json_object(raw,'invalid_history_json');_need(body==receipt.get('payload') and isinstance(body,Mapping) and all(isinstance(body.get(k),list) for k in KEYS))
        n=len(body['form']);_need(n==pointer['filingCount'] and 0<n<=50000 and all(len(body[k])==n for k in KEYS));matches=[]
        for values in zip(*(body[k] for k in KEYS)):
            row=dict(zip(KEYS,values))
            if (row['accessionNumber'],row['form'],row['filingDate'])!=(target['accessionNumber'],target['form'],target['filingDate']):continue
            end,filed=_iso_date(row['reportDate']),_iso_date(row['filingDate']);accepted=_utc_timestamp(row['acceptanceDateTime'])
            _need(end is not None and filed is not None and end<=filed<=as_of.date() and accepted is not None and end<=accepted.date() and accepted<=as_of)
            _need(isinstance(row['primaryDocument'],str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,200}',row['primaryDocument']) and '..' not in row['primaryDocument'] and all(type(row[k]) is int and row[k] in {0,1} for k in ('isInlineXBRL','isXBRL')))
            expected=f'https://cdn.yahoofinance.com/prod/sec-filings/{cik}/{row["accessionNumber"].replace("-","")}/{row["primaryDocument"]}'
            _need(target['exhibit']==expected);matches.append(row)
        return matches if len(matches)==1 else []
    except (ValueError,TypeError,KeyError,AttributeError,OverflowError,RecursionError,binascii.Error):return []
