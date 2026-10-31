"""Dated listing-description observations, independent of issuer financial eligibility."""
from collections import Counter
from collections.abc import Mapping
from datetime import datetime,timezone,timedelta
import hashlib,json,re

from src.online_company_identity import _mode_reason
from src.online_us_universe import load_online_us_universe,validated_us_universe,_fetch_directory,_alias,MAP_URL
from src.online_sec_receipt import _fetch_raw,fetch_sec_json_receipt
from src.us_listing_receipt_audit import _SOURCES,_parse_directory
from src.company_sec_online_preview import _utc_timestamp

SCHEMA='security-classification-v1'
RIGHTS='unregistered_listing_metadata_personal_inspection_only'
RULES='directory-description-20261031-v2'
SESSION_KEY='company_security_context_v1'

def _digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def classify_description(name,etf):
 result=dict(security_type='unknown',rule='unresolved_description',basis='directory_description',reason='explicit_instrument_description_unavailable')
 if not isinstance(name,str) or not 0<len(name)<=500 or type(etf) not in {bool,type(None)}:return result
 s=' '.join(name.lower().split())
 debt=bool(re.search(r'\b(?:notes?\s+due|bonds?\s+due|debentures?|exchange traded notes?|etn)\b',s))
 if etf is True:
  return dict(security_type='unknown' if debt else 'etf',rule='conflicting_etf_description' if debt else 'declared_etf_flag',basis='directory_flag',reason='conflicting_source_labels' if debt else None)
 candidates=[]
 patterns={'unit':r'\bunits?\b','warrant':r'\bwarrants?\b',
  'right':r'\bright[s]?\s+to (?:receive|purchase)|\s-\s+rights?\b|\brights?$',
  'depositary_receipt':r'\b(?:american |global )?deposit[ao]ry (?:shares?|receipts?)\b|\b(?:adr|ads)\b',
  'preferred':r'\bpreferred\b|\bpreference shares?\b','common_shares':r'\b(?:common|ordinary) (?:stock|shares?)\b'}
 if debt:candidates.append('debt')
 for kind,pattern in patterns.items():
  if re.search(pattern,s):candidates.append(kind)
 # A named wrapper carries its underlying instruments in the description.
 for primary in ('unit','warrant','right','depositary_receipt'):
  if primary in candidates:
   wrappers=set(candidates)&{'unit','warrant','right','depositary_receipt'}
   if primary in {'warrant','right'} and 'common_shares' in candidates:
    explicit=re.search(r'\s-\s+(?:warrants?|rights?)\b|\b(?:warrants? to purchase|rights? to (?:receive|purchase))\b',s)
    if primary=='warrant':
     warrant=re.search(r'\bwarrants?\b',s);underlying=re.search(patterns['common_shares'],s)
     qualified=re.search(r'\bwarrants?[\s,(]+(?:each|entitling|exercisable|expiring)\b',s)
     explicit=explicit or (qualified and warrant.start()<underlying.start())
    if not explicit:return {**result,'reason':'ambiguous_composite_instrument'}
   allowed={'unit','warrant','right'} if primary=='unit' else {primary}
   if not wrappers<=allowed:return {**result,'reason':'ambiguous_composite_instrument'}
   return dict(security_type=primary,rule='explicit_'+primary,basis='directory_description',reason=None)
 if len(candidates)==1:return dict(security_type=candidates[0],rule='explicit_'+candidates[0],basis='directory_description',reason=None)
 if candidates:result['reason']='ambiguous_composite_instrument'
 return result

def build_classification(inventory,directory_rows):
 inv=validated_us_universe(inventory)
 if inv is None or not isinstance(directory_rows,list):raise ValueError('invalid_classification_inventory')
 descriptions={}
 expected={r['listing_id']:r for r in inv['rows'] if r['source']!='sec'}
 for r in directory_rows:
  key=r.get('source','')+':'+r.get('act_symbol','')
  base=expected.get(key);name=r.get('security_name')
  if (key in descriptions or base is None or not isinstance(name,str) or not 0<len(name)<=500
      or r.get('etf') not in {'Y','N'} or base['etf']!=(r['etf']=='Y')):raise ValueError('description_identity_mismatch')
  descriptions[key]=name
 if set(descriptions)!=set(expected):raise ValueError('incomplete_directory_descriptions')
 rows=[]
 for r in inv['rows']:
  name=descriptions.get(r['listing_id']);kind=classify_description(name,r['etf']) if name else dict(security_type='unknown',rule='sec_issuer_name_only',basis='unresolved',reason='issuer_name_is_not_security_description')
  rows.append({**r,'description':name,**kind,'legal_security_type_established':False})
 result=dict(status='inspection_only',schema_version=SCHEMA,rules_version=RULES,rights_status=RIGHTS,inventory=inv,descriptions=descriptions,rows=rows,counts=dict(Counter(r['security_type'] for r in rows)),financial_coverage_promoted=False,analysis_eligibility_established=False,domicile_established=False,active_status_established=False,point_in_time_established=False)
 result['legal_security_type_established']=False
 result['packet_digest']=_digest(result);return result

def validated_classification(packet):
 if not isinstance(packet,Mapping) or packet.get('schema_version')!=SCHEMA or not isinstance(packet.get('descriptions'),Mapping):return None
 try:
  rows=[dict(source=k.split(':',1)[0],act_symbol=k.split(':',1)[1],security_name=v,etf='Y' if r['etf'] else 'N') for r in packet['inventory']['rows'] if r['source']!='sec' for k,v in [(r['listing_id'],packet['descriptions'][r['listing_id']])]]
  expected=build_classification(packet['inventory'],rows)
  return expected if expected==dict(packet) else None
 except (ValueError,KeyError,TypeError,AttributeError,RecursionError):return None

def fetch_classification(*,user_agent,fetcher=None,observed_at=None,workspace_mode='research'):
 held=dict(status='withheld',reason=_mode_reason(workspace_mode) or 'classification_source_unavailable')
 if _mode_reason(workspace_mode):return held
 captured={}
 def capture(url,agent):
  result=(fetcher or (_fetch_directory if url in {s[2] for s in _SOURCES} else _fetch_raw))(url,agent)
  captured[url]=result[0];return result
 inv=load_online_us_universe(user_agent=user_agent,fetcher=capture,observed_at=observed_at,workspace_mode=workspace_mode)
 if inv.get('status')!='inspection_only':return held
 try:
  rows=[]
  for source,_,url,columns in _SOURCES:rows.extend(_parse_directory(captured[url],source,columns,allow_unknown_venues=True)[-1])
  return build_classification(inv,rows)
 except (ValueError,KeyError,TypeError,RecursionError):return held

def issuer_profile(cik,receipt):
 held=dict(status='withheld',sec_cik=cik,reason='issuer_metadata_unverified')
 if not isinstance(receipt,Mapping) or receipt.get('status')!='ready' or receipt.get('source_url')!=f'https://data.sec.gov/submissions/CIK{cik}.json':return held
 body=receipt.get('payload')
 try:
  filings=body.get('filings') if isinstance(body,Mapping) else None
  recent=filings.get('recent') if isinstance(filings,Mapping) else None
  forms=recent.get('form') if isinstance(recent,Mapping) else None
  if (not re.fullmatch(r'\d{10}',cik) or int(cik)==0 or type(body.get('cik')) not in {str,int} or str(int(body['cik'])).zfill(10)!=cik
      or _utc_timestamp(receipt.get('observed_at')) is None or not isinstance(receipt.get('payload_sha256'),str) or not re.fullmatch(r'[0-9a-f]{64}',receipt['payload_sha256'])
      or not isinstance(forms,list) or len(forms)>2000 or any(not isinstance(f,str) or len(f)>80 for f in forms)
      or not isinstance(body.get('entityType',''),str) or len(body.get('entityType',''))>100
      or body.get('sicDescription') is not None and (not isinstance(body['sicDescription'],str) or len(body['sicDescription'])>500)
      or not isinstance(body.get('tickers'),list) or not isinstance(body.get('exchanges'),list) or len(body['tickers'])!=len(body['exchanges'])
      or any(not isinstance(t,str) or not re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,19}',t) for t in body['tickers'])
      or any(not isinstance(e,str) or len(e)>80 for e in body['exchanges'])):return held
  kinds=[]
  if any(f in {'N-CSR','N-CSRS','N-CEN','NPORT-P','N-PORT'} for f in forms) or body.get('entityType')=='investment-company':kinds.append('investment_company_reporting')
  if any(f in {'10-K','10-K/A'} for f in forms):kinds.append('domestic_annual_reporting')
  if any(f in {'20-F','20-F/A','40-F','40-F/A'} for f in forms):kinds.append('foreign_annual_reporting')
  sic=body.get('sic');sic=str(sic) if type(sic) in {str,int} and sic!='' else None
  if sic is not None and not re.fullmatch(r'\d{1,4}',sic):return held
  metadata={k:body.get(k) for k in ('cik','entityType','sic','sicDescription','tickers','exchanges')};metadata['filings']={'recent':{'form':forms}}
  result=dict(status='inspection_only',sec_cik=cik,reporting_profile=kinds[0] if len(kinds)==1 else 'mixed_reporting' if kinds else 'unknown',form_counts=dict(Counter(forms)),entity_type=body.get('entityType'),sic=sic,security_type='unknown',domicile_established=False,active_status_established=False,analysis_eligibility_established=False,rights_status='unregistered_submissions_metadata_personal_inspection_only',source_receipt={k:receipt[k] for k in ('source_url','observed_at','payload_sha256')},source_metadata=metadata)
  result['packet_digest']=_digest(result);return result
 except (ValueError,TypeError,AttributeError,KeyError):return held

def _selected(snapshot,ticker,expected_cik):
 if not isinstance(ticker,str) or not re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,19}',ticker):raise ValueError('invalid_ticker')
 matches={str(int(r['cik_str'])).zfill(10) for r in snapshot['inventory']['map_receipt']['payload'].values() if _alias(r['ticker'])==_alias(ticker)}
 if len(matches)!=1 or expected_cik is not None and matches!={expected_cik}:raise ValueError('selected_company_identity_mismatch')
 cik=next(iter(matches));rows=[r for r in snapshot['rows'] if _alias(r['symbol'])==_alias(ticker) and r['sec_cik']==cik]
 return cik,rows

def validated_company_context(context,ticker,expected_cik=None):
 if not isinstance(context,Mapping) or context.get('ticker')!=ticker:return None
 try:
  snapshot=validated_classification(context['classification']);assert snapshot is not None
  cik,rows=_selected(snapshot,ticker,expected_cik);profile=context['issuer_profile']
  if profile.get('status')=='inspection_only':
   ref={**profile['source_receipt'],'status':'ready','payload':profile['source_metadata']}
   if issuer_profile(cik,ref)!=profile:return None
   if not any(_alias(t)==_alias(ticker) for t in profile['source_metadata']['tickers']):return None
   times=[_utc_timestamp(r['observed_at']) for r in snapshot['inventory']['source_receipts']]+[_utc_timestamp(ref['observed_at'])]
   if max(times)-min(times)>timedelta(hours=24) or times[-1]<max(times[:-1]):return None
  elif profile!=dict(status='withheld',sec_cik=cik,reason='issuer_metadata_unverified'):return None
  if context['sec_cik']!=cik or context['listing_rows']!=rows or context['packet_digest']!=_digest({k:v for k,v in context.items() if k!='packet_digest'}):return None
  return dict(context)
 except (AssertionError,KeyError,TypeError,ValueError,AttributeError,RecursionError):return None

def get_company_security_context(ticker,session_state,*,refresh_requested,user_agent,expected_cik=None,fetcher=None,observed_at=None,workspace_mode='research'):
 reason=_mode_reason(workspace_mode)
 held=dict(status='withheld',ticker=ticker,reason=reason or 'security_context_unverified')
 if reason:return held
 if not refresh_requested:
  cached=session_state.get(SESSION_KEY)
  if not isinstance(cached,Mapping) or cached.get('ticker')!=ticker:return dict(status='not_requested',ticker=ticker)
  return validated_company_context(cached,ticker,expected_cik) or held
 snapshot=fetch_classification(user_agent=user_agent,fetcher=fetcher,observed_at=observed_at,workspace_mode=workspace_mode)
 session_state[SESSION_KEY]=held
 try:
  if snapshot['status']!='inspection_only':return held
  cik,rows=_selected(snapshot,ticker,expected_cik)
  ref=fetch_sec_json_receipt(f'https://data.sec.gov/submissions/CIK{cik}.json',user_agent=user_agent,fetcher=fetcher,observed_at=observed_at)
  result=dict(status='inspection_only',ticker=ticker,sec_cik=cik,listing_rows=rows,classification=snapshot,issuer_profile=issuer_profile(cik,ref))
  result['packet_digest']=_digest(result)
  result=validated_company_context(result,ticker,expected_cik) or held;session_state[SESSION_KEY]=result;return result
 except (ValueError,TypeError,KeyError):return held
