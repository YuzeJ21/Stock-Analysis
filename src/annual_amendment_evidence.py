"""Exact-byte-bound scope interpretation, never a general amendment fallback.

The known amendment corrects MD&A percentages, affirming other disclosures are
unchanged. Its false AmendmentFlag is retained as a discrepancy, not repaired.
Raw documents stay in session evidence; no source or commercial approval follows.
"""
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
import base64
import binascii
import hashlib
import re
import xml.etree.ElementTree as ET

from src.company_sec_online_preview import _iso_date, _utc_timestamp
from src.online_company_identity import _mode_reason
from src.sec_exact_filing import MAX_FILING_BYTES, _fetch_html
from src.sec_inline_filing import X, IX, ISO, _tree, _qname, _taxonomy, _number, extract_inline_filing

SCHEMA='annual-amendment-evidence-v1'
_KEYS=('form','reportDate','filingDate','acceptanceDateTime','accessionNumber','primaryDocument','isInlineXBRL','isXBRL')
POLICIES=({
    'policy_id':'amd-2025-client-mdna-correction-v1','ticker':'AMD','sec_cik':'0000002488',
    'original':dict(form='10-K',reportDate='2025-12-27',filingDate='2026-02-04',acceptanceDateTime='2026-02-03T23:14:52Z',
                    accessionNumber='0000002488-26-000018',primaryDocument='amd-20251227.htm',isInlineXBRL=1,isXBRL=1),
    'amendment':dict(form='10-K/A',reportDate='2025-12-27',filingDate='2026-02-04',acceptanceDateTime='2026-02-04T20:06:57Z',
                     accessionNumber='0000002488-26-000021',primaryDocument='amd-20251227.htm',isInlineXBRL=1,isXBRL=1),
    'original_sha256':'1d7f6ab4bb68480687dc1a72b1795beb7c5fb544ff73cbc0b985afa69140282e',
    'amendment_sha256':'8eefb69edbe045fcf3a9e08d27a4261aa205f374ff22076586ea85f49a929a17',
},)


def _known_pair(ticker,cik,filings):
    if not isinstance(filings,list) or not 0<len(filings)<=2000:return None
    annual=[r for r in filings if isinstance(r,Mapping) and r.get('form') in {'10-K','10-K/A','20-F','20-F/A'}]
    if not annual or any(_iso_date(r.get('reportDate')) is None or _iso_date(r.get('filingDate')) is None for r in annual):return None
    end=max(r['reportDate'] for r in annual);same=[r for r in annual if r['reportDate']==end]
    filed=max(r['filingDate'] for r in same);same=[r for r in same if r['filingDate']==filed]
    if any(_utc_timestamp(r.get('acceptanceDateTime')) is None for r in same):return None
    accepted=max(_utc_timestamp(r['acceptanceDateTime']) for r in same)
    latest=[r for r in same if _utc_timestamp(r['acceptanceDateTime'])==accepted]
    if len(latest)!=1:return None
    def matches(row,expected):
        return all((_utc_timestamp(row.get(k))==_utc_timestamp(expected[k]) if k=='acceptanceDateTime'
                    else type(row.get(k)) is type(expected[k]) and row.get(k)==expected[k]) for k in _KEYS)
    for policy in POLICIES:
        originals=[r for r in annual if r.get('accessionNumber')==policy['original']['accessionNumber']]
        if (policy['ticker']==ticker and policy['sec_cik']==cik and matches(latest[0],policy['amendment'])
                and len(originals)==1 and matches(originals[0],policy['original'])):return policy
    return None


def _url(cik,filing):
    return f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{filing["accessionNumber"].replace("-", "")}/{filing["primaryDocument"]}'


def _fresh(value,now):
    stamp=_utc_timestamp(value)
    return stamp is not None and timedelta(0)<=now-stamp<=timedelta(hours=24)


def amendment_candidate(ticker,cik,profile,*,as_of=None):
    try:
        now=as_of or datetime.now(timezone.utc)
        if (not isinstance(profile,Mapping) or profile.get('status')!='ready'
                or profile.get('source_url')!=f'https://data.sec.gov/submissions/CIK{cik}.json'
                or not _fresh(profile.get('observed_at'),now)):return False
        body=profile['payload'];recent=body['filings']['recent']
        if type(body.get('cik')) not in {int,str} or str(int(body['cik'])).zfill(10)!=cik:return False
        if not all(isinstance(recent.get(k),list) for k in _KEYS):return False
        n=len(recent['form'])
        if not 0<n<=2000 or any(len(recent[k])!=n for k in _KEYS):return False
        return _known_pair(ticker,cik,[dict(zip(_KEYS,row)) for row in zip(*(recent[k] for k in _KEYS))]) is not None
    except (ValueError,TypeError,KeyError,AttributeError,OverflowError):return False


def fetch_amendment_evidence(ticker,cik,profile,*,user_agent,fetcher=None,observed_at=None,workspace_mode='research'):
    reason=_mode_reason(workspace_mode)
    held=dict(status='unavailable',reason=reason or 'amendment_source_unavailable')
    if reason:return held
    if not amendment_candidate(ticker,cik,profile,as_of=observed_at):return dict(status='not_applicable')
    if not isinstance(user_agent,str) or not user_agent.strip() or any(c in user_agent for c in '\r\n'):return held
    recent=profile['payload']['filings']['recent'];rows=[dict(zip(_KEYS,r)) for r in zip(*(recent[k] for k in _KEYS))]
    policy=_known_pair(ticker,cik,rows)
    result=dict(schema_version=SCHEMA,status='observed',ticker=ticker,sec_cik=cik)
    try:
        for key in ('original','amendment'):
            url=_url(cik,policy[key]);raw,headers,final=(fetcher or _fetch_html)(url,user_agent.strip())
            if not isinstance(raw,bytes) or not 0<len(raw)<=MAX_FILING_BYTES or final!=url:return held
            now=observed_at or datetime.now(timezone.utc)
            result[key]=dict(status='ready',source_url=url,observed_at=now.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                payload_sha256=hashlib.sha256(raw).hexdigest(),payload_raw_base64=base64.b64encode(raw).decode('ascii'))
        return result
    except (OSError,ValueError,TypeError,RuntimeError,OverflowError):return held


def _document(packet,key,policy,cik,now):
    receipt=packet[key];encoded=receipt.get('payload_raw_base64')
    if (receipt.get('status')!='ready' or receipt.get('source_url')!=_url(cik,policy[key]) or not _fresh(receipt.get('observed_at'),now)
            or not isinstance(encoded,str) or not 0<len(encoded)<=4*((MAX_FILING_BYTES+2)//3)):raise ValueError()
    raw=base64.b64decode(encoded,validate=True)
    if not 0<len(raw)<=MAX_FILING_BYTES or hashlib.sha256(raw).hexdigest()!=policy[key+'_sha256'] or receipt.get('payload_sha256')!=policy[key+'_sha256']:raise ValueError()
    selected=dict(status='selected',ticker=policy['ticker'],sec_cik=cik,period_kind='annual',period_end=policy[key]['reportDate'],
        form=policy[key]['form'],source_url=receipt['source_url'],source_receipts=[])
    return raw,receipt,selected


def _original_eps(raw,cik,end,url):
    root,namespaces=_tree(raw);contexts={};units=set()
    for node in root.iter(f'{{{X}}}context'):
        entity=node.find(f'{{{X}}}entity');period=node.find(f'{{{X}}}period')
        if entity is None or period is None or len(node)!=2 or len(entity)!=1 or len(period)!=2:continue
        ident=entity.find(f'{{{X}}}identifier');start=period.find(f'{{{X}}}startDate');finish=period.find(f'{{{X}}}endDate')
        if ident is None or start is None or finish is None or ident.get('scheme')!='http://www.sec.gov/CIK':continue
        if not isinstance(ident.text,str) or not re.fullmatch(r'\d{1,10}',ident.text.strip()) or str(int(ident.text)).zfill(10)!=cik:continue
        if _iso_date(start.text) and finish.text==end and 350<=(_iso_date(end)-_iso_date(start.text)).days<=380:
            contexts[node.get('id')]=start.text
    for unit in root.iter(f'{{{X}}}unit'):
        if len(unit)!=1 or unit[0].tag!=f'{{{X}}}divide' or len(unit[0])!=2:continue
        numerator=unit[0].find(f'{{{X}}}unitNumerator');denominator=unit[0].find(f'{{{X}}}unitDenominator')
        if numerator is None or denominator is None or len(numerator)!=1 or len(denominator)!=1:continue
        if numerator[0].tag!=f'{{{X}}}measure' or denominator[0].tag!=f'{{{X}}}measure':continue
        if _qname(numerator[0].text,namespaces)==(ISO,'USD') and _qname(denominator[0].text,namespaces)==(X,'shares'):units.add(unit.get('id'))
    observations=[];proofs=[]
    for node in root.iter(f'{{{IX}}}nonFraction'):
        uri,name=_qname(node.get('name'),namespaces)
        if _taxonomy(uri)!='us-gaap' or name!='EarningsPerShareDiluted' or node.get('contextRef') not in contexts:continue
        if node.get('unitRef') not in units:raise ValueError()
        numeric,reason=_number(node,namespaces)
        if reason or numeric is None:raise ValueError()
        observations.append((contexts[node.get('contextRef')],end,numeric['value']))
        proofs.append(dict(**numeric,context_id=node.get('contextRef'),unit_id=node.get('unitRef'),unit='USD/shares',
            concept=name,namespace_uri=uri,source_ref=url+('#'+node.get('id') if node.get('id') else '')))
    if not observations or len(set(observations))!=1:raise ValueError()
    start,end,value=observations[0]
    return dict(period_start=start,period_end=end,eps=value,proofs=proofs)


def validate_amendment_evidence(packet,*,ticker,cik,filings,as_of):
    held=dict(status='withheld',reason='amendment_scope_unverified')
    if _mode_reason('research'):return held
    try:
        if (not isinstance(as_of,datetime) or as_of.utcoffset() is None or not isinstance(packet,Mapping)
                or packet.get('schema_version')!=SCHEMA or packet.get('status')!='observed'
                or (packet.get('ticker'),packet.get('sec_cik'))!=(ticker,cik)):return held
        policy=_known_pair(ticker,cik,filings)
        if policy is None:return held
        original,oreceipt,oselect=_document(packet,'original',policy,cik,as_of)
        amendment,areceipt,aselect=_document(packet,'amendment',policy,cik,as_of)
        if extract_inline_filing(original,oselect,oreceipt).get('status')!='inspection_only':return held
        amended=extract_inline_filing(amendment,aselect,areceipt)
        if amended.get('reason')!='filing_dei_identity_or_period_mismatch':return held
        # Known bytes establish this exact flag/type discrepancy; never relax the parser.
        root,ns=_tree(amendment);forms=set();flags=set()
        for node in root.iter(f'{{{IX}}}nonNumeric'):
            uri,name=_qname(node.get('name'),ns)
            if not uri or not re.fullmatch(r'https?://xbrl.sec.gov/dei/\d{4}',uri):continue
            text=' '.join(''.join(node.itertext()).split()).lower()
            if name=='DocumentType':forms.add(text)
            if name=='AmendmentFlag':flags.add(text)
        if forms!={'10-k/a'} or flags!={'false'}:return held
        eps=_original_eps(original,cik,policy['original']['reportDate'],oreceipt['source_url'])
        return dict(status='supported',policy_id=policy['policy_id'],original_eps=eps,
            original=dict(policy['original']),amendment=dict(policy['amendment']),amendment_flag_discrepancy=True,
            scope_basis='known_mdna_correction_other_disclosures_unchanged_technical_interpretation',
            shared_amendment_parser_reason=amended['reason'],commercial_eligible=False,readiness_promoted=False,
            rights_status='unregistered_sec_archive_personal_inspection_only',
            source_receipts=[{k:r[k] for k in ('source_url','observed_at','payload_sha256')} for r in (oreceipt,areceipt)])
    except (ValueError,TypeError,KeyError,AttributeError,OverflowError,RecursionError,ET.ParseError,binascii.Error):return held
