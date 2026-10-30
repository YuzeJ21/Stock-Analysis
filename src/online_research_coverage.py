"""Explicit, bounded SEC field-coverage samples, never a market-wide denominator."""

import argparse
import json
import os
import re
from collections import defaultdict
from collections.abc import Mapping
from datetime import timedelta

from src.company_sec_online_preview import _iso_date, _utc_timestamp
from src.online_company_identity import financial_identity_valid, validated_sec_company_profile, fetch_sec_company_profile, _mode_reason
from src.online_history_contract import validated_annual_history
from src.online_sec_receipt import fetch_sec_json_receipt
from src.sec_annual_history import fetch_sec_online_research_view
from src.sec_quarterly_history import FIELDS, validated_quarterly_history
from src.sec_foreign_financials import validated_foreign_financials

DEFAULT_SAMPLE=('MSFT','JPM','JNJ','XOM','PG','MCD','CAT','NEM','DUK','O','VZ','TSM')
SESSION_KEY='online_research_coverage_sample_v1'
METRICS=tuple(f'{period}_{field}' for period in ('annual','quarterly') for field in FIELDS)+('cumulative_cash_from_operations','cumulative_capital_expenditures')+tuple('interim_'+f for f in FIELDS)
MAP_URL='https://www.sec.gov/files/company_tickers.json'


def _tickers(values):
    if isinstance(values,str): values=values.split(',')
    if not isinstance(values,(list,tuple)) or not 1<=len(values)<=20: return None
    if any(not isinstance(v,str) for v in values): return None
    result=[v.strip().upper() for v in values]
    if len(set(result))!=len(result) or any(not re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,19}',v) for v in result): return None
    return result


def _reason(value,fallback):
    return value if isinstance(value,str) and 0<len(value)<=200 else fallback


def _target_period(view,profile,kind,selected,identity):
    ends=[selected['period_end']] if _iso_date(selected.get('period_end')) else []
    anchors=view.get('reported_period_anchors',{})
    if not isinstance(anchors,Mapping): return None
    anchor=anchors.get(kind)
    if anchor is not None:
        if not isinstance(anchor,Mapping) or _iso_date(anchor.get('period_end')) is None: return None
        end,filed=_iso_date(anchor['period_end']),_iso_date(anchor.get('filed'))
        observed=_utc_timestamp(identity.get('observed_at')) if isinstance(identity,Mapping) else None
        if filed is None or observed is None or not end<=filed<=observed.date(): return None
        ends.append(anchor['period_end'])
    if profile:
        marker=profile.get('latest_'+kind+'_period_end')
        if marker is not None: ends.append(marker)
    return max(ends) if ends else None


def _aggregate(rows,requested):
    groups=defaultdict(list)
    for row in rows: groups[row['sic']].append(row)
    industries=[]
    for sic,members in sorted(groups.items(),key=lambda item:(item[0] is None,item[0] or '')):
        descriptions={r['sic_description'] for r in members if r['sic_description']}
        industries.append({'sic':sic,'description':next(iter(descriptions)) if len(descriptions)==1 else 'Unknown or varying source description',
            'requested_count':len(members),'counts':{m:sum(r['fields'][m] for r in members) for m in METRICS}})
    times=[ref['observed_at'] for r in rows for ref in r['source_receipts']]
    return {'status':'inspection_only','requested_tickers':requested,'requested_count':len(requested),
        'attempted_count':sum(r['attempted'] for r in rows),'resolved_issuer_count':len({r['sec_cik'] for r in rows if r['sec_cik']}),
        'counts':{m:sum(r['fields'][m] for r in rows) for m in METRICS},
        'source_failure_count':sum(not r['financial_source_matched'] for r in rows),
        'unsupported_financial_count':sum(r['financial_source_matched'] and not r['fields']['annual_revenue'] and not r['fields']['quarterly_revenue'] and not r['fields']['interim_revenue'] for r in rows),
        'unknown_industry_count':sum(r['sic'] is None for r in rows),'by_industry':industries,'rows':rows,
        'observed_from':min(times) if times else None,'observed_to':max(times) if times else None,
        'market_universe_coverage_established':False,'price_coverage_assessed':False,
        'coverage_basis':'latest_observed_period_per_requested_ticker_not_market_denominator',
        'source_rights':{'sec_companyfacts':'registered_direct_field_scope_raw_redistribution_held',
                         'sec_submissions':'unregistered_personal_identity_metadata_inspection_only'}}


def summarize_online_research_coverage(observations,requested_tickers):
    requested=_tickers(requested_tickers)
    if requested is None or not isinstance(observations,list): return {'status':'invalid','reason':'invalid_sample'}
    indexed={}
    for obs in observations:
        if not isinstance(obs,Mapping) or not isinstance(obs.get('ticker'),str) or obs['ticker'] not in requested or obs['ticker'] in indexed:
            return {'status':'invalid','reason':'duplicate_or_unrequested_observation'}
        indexed[obs['ticker']]=obs
    rows=[]
    for ticker in requested:
        obs=indexed.get(ticker,{}); view=obs.get('view',{})
        if not isinstance(view,Mapping): view={}
        identity=view.get('companyfacts_identity',{}); source_ok=financial_identity_valid(ticker,identity)
        cik=identity['sec_cik'] if source_ok else None
        profile=validated_sec_company_profile(obs.get('profile'),cik) if cik else None
        profile_issue='sic_unavailable'
        # SIC describes the matched issuer only when its current symbol is present.
        if profile and not any(t.replace('.','-')==ticker.replace('.','-') for t in profile['tickers']):
            profile=None; profile_issue='industry_ticker_mismatch'
        if profile and abs(_utc_timestamp(profile['observed_at'])-_utc_timestamp(identity['observed_at']))>timedelta(hours=24):
            profile=None; profile_issue='industry_observation_gap'
        annual=validated_annual_history(view) if source_ok else None
        quarterly=validated_quarterly_history(view) if source_ok else None
        a=annual['periods'][-1] if annual else {}; q=quarterly['periods'][-1] if quarterly else {}
        foreign=validated_foreign_financials(view) if source_ok else None
        fa=foreign['annual'][-1] if foreign and foreign['annual'] else {}
        fq=foreign['quarterly'][-1] if foreign and foreign['quarterly'] else {}
        interim=foreign['interim'][-1] if foreign and foreign['interim'] else {}
        selected_a=max((a,fa),key=lambda r:r.get('period_end',''))
        selected_q=max((q,fq),key=lambda r:r.get('period_end',''))
        annual_target=_target_period(view,profile,'annual',selected_a,identity)
        quarter_target=_target_period(view,profile,'quarterly',selected_q,identity)
        annual_current=a.get('status')=='available' and a.get('period_end')==annual_target
        quarter_current=q.get('status')=='available' and q.get('period_end')==quarter_target
        af={f['field'] for f in a.get('fields',[])} if annual_current else set()
        qf=set(q.get('fields',{})) if quarter_current else set()
        cf=set(q.get('cumulative_fields',{})) if quarter_current else set()
        native_annual=fa.get('status')=='available' and fa.get('period_end')==annual_target
        native_quarter=fq.get('status')=='available' and fq.get('period_end')==quarter_target
        if native_annual: af=set(fa['fields']); annual_current=True
        if native_quarter: qf=set(fq['fields']); quarter_current=True
        interim_fields=set(interim.get('fields',{})) if interim.get('status')=='available' else set()
        fields={**{'annual_'+f:f in af for f in FIELDS},**{'quarterly_'+f:f in qf for f in FIELDS},
                'cumulative_cash_from_operations':'cash_from_operations' in cf,'cumulative_capital_expenditures':'capital_expenditures' in cf,**{'interim_'+f:f in interim_fields for f in FIELDS}}
        refs=[]
        if source_ok:
            refs.append({k:identity[k] for k in ('source_url','observed_at','payload_sha256')})
            refs.append({'source_url':identity['association_source_url'],'observed_at':identity['association_observed_at'],'payload_sha256':identity['association_payload_sha256']})
        if profile: refs.append({k:profile[k] for k in ('source_url','observed_at','payload_sha256')})
        raw_quarter=view.get('quarterly_history',{})
        if not isinstance(raw_quarter,Mapping): raw_quarter={}
        rows.append({'ticker':ticker,'attempted':bool(obs),'sec_cik':cik,'financial_source_matched':source_ok,
            'sic':profile.get('sic') if profile else None,'sic_description':profile.get('sic_description') if profile else None,
            'fields':fields,'annual_period':annual_target,'quarterly_period':quarter_target,
            'annual_available_period':max([r['period_end'] for r in (annual['periods'] if annual else [])+(foreign['annual'] if foreign else []) if r['status']=='available'],default=None),
            'quarterly_available_period':max([r['period_end'] for r in (quarterly['periods'] if quarterly else [])+(foreign['quarterly'] if foreign else []) if r['status']=='available'],default=None),
            'interim_period':interim.get('period_end'),
            'interim_available_period':interim.get('period_end') if interim.get('status')=='available' else None,
            'annual_unit':foreign['unit'] if native_annual else 'USD' if annual_current else None,
            'quarterly_unit':foreign['unit'] if native_quarter else 'USD' if quarter_current else None,
            'interim_unit':foreign['unit'] if interim_fields else None,
            'industry_reason':'available' if profile and profile.get('sic') else _reason(obs.get('profile',{}).get('reason') if isinstance(obs.get('profile'),Mapping) else None,profile_issue),
            'annual_reason':'available' if annual_current else 'latest_reported_annual_not_covered' if a.get('period_end') and annual_target and a['period_end']<annual_target else _reason(a.get('reason') or view.get('reason'),'annual_evidence_unavailable'),
            'quarterly_reason':'available' if quarter_current else 'latest_reported_quarter_not_covered' if q.get('period_end') and quarter_target and q['period_end']<quarter_target else _reason(q.get('reason') or raw_quarter.get('reason'),'quarterly_evidence_unavailable'),
            'source_receipts':refs})
    return _aggregate(rows,requested)


def validated_coverage_summary(result):
    """Recompute counters from the session's reduced rows before rendering."""
    if not isinstance(result,Mapping) or result.get('status')!='inspection_only': return None
    requested=_tickers(result.get('requested_tickers')); rows=result.get('rows')
    if requested is None or not isinstance(rows,list) or len(rows)!=len(requested): return None
    for ticker,row in zip(requested,rows):
        if not isinstance(row,Mapping) or row.get('ticker')!=ticker: return None
        fields=row.get('fields'); refs=row.get('source_receipts')
        if not isinstance(fields,Mapping) or set(fields)!=set(METRICS) or any(type(v) is not bool for v in fields.values()): return None
        if type(row.get('attempted')) is not bool or type(row.get('financial_source_matched')) is not bool: return None
        cik=row.get('sec_cik'); sic=row.get('sic')
        if cik is not None and (not isinstance(cik,str) or not re.fullmatch(r'\d{10}',cik) or int(cik)==0): return None
        if sic is not None and (not isinstance(sic,str) or not re.fullmatch(r'\d{4}',sic) or sic=='0000'): return None
        if row.get('sic_description') is not None and not isinstance(row['sic_description'],str): return None
        if not row['financial_source_matched'] and (any(fields.values()) or cik is not None or sic is not None): return None
        if any(row.get(k) is not None and _iso_date(row[k]) is None for k in ('annual_period','quarterly_period','annual_available_period','quarterly_available_period','interim_period','interim_available_period')): return None
        if any(not isinstance(row.get(k),str) for k in ('annual_reason','quarterly_reason','industry_reason')): return None
        for kind in ('annual','quarterly','interim'):
            prefix=('quarterly_','cumulative_') if kind=='quarterly' else kind+'_'
            if any(value for name,value in fields.items() if name.startswith(prefix)):
                unit=row.get(kind+'_unit')
                if not isinstance(unit,str) or not re.fullmatch(r'[A-Z]{3}',unit): return None
                if row.get(kind+'_period') is None or row.get(kind+'_available_period')!=row[kind+'_period']: return None
        if not isinstance(refs,list) or len(refs)>3: return None
        expected_urls=[]
        if row['financial_source_matched']:
            if cik is None or not row['attempted'] or len(refs)<2: return None
            expected_urls=[f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json',MAP_URL]
            if len(refs)==3: expected_urls.append(f'https://data.sec.gov/submissions/CIK{cik}.json')
            if sic is not None and len(refs)!=3: return None
        elif refs: return None
        for ref,expected_url in zip(refs,expected_urls):
            if (not isinstance(ref,Mapping) or not isinstance(ref.get('source_url'),str)
                or ref['source_url']!=expected_url or _utc_timestamp(ref.get('observed_at')) is None
                or not isinstance(ref.get('payload_sha256'),str) or not re.fullmatch(r'[0-9a-f]{64}',ref['payload_sha256'])): return None
    return _aggregate(rows,requested)


def run_online_coverage_study(tickers=DEFAULT_SAMPLE,*,user_agent,source_fetcher=None,observed_at=None,workspace_mode='research',ticker_map_receipt=None):
    requested=_tickers(tickers); reason=_mode_reason(workspace_mode)
    if reason or requested is None: return {'status':'unavailable','reason':reason or 'invalid_sample'}
    from src.online_sec_receipt import _fetch_raw
    calls=[]
    def fetch(url,agent):
        calls.append(url)
        return (source_fetcher or _fetch_raw)(url,agent)
    mapping=ticker_map_receipt if ticker_map_receipt is not None else fetch_sec_json_receipt(MAP_URL,user_agent=user_agent,fetcher=fetch,observed_at=observed_at)
    if not isinstance(mapping,Mapping) or mapping.get('source_url')!=MAP_URL or mapping.get('status') not in {'ready','unavailable'}: return {'status':'invalid','reason':'invalid_map_receipt'}
    observations=[]
    for ticker in requested:
        view={'status':'unavailable','ticker':ticker,'reason':_reason(mapping.get('reason'),'sec_ticker_map_unavailable')}
        profile=None
        if mapping['status']=='ready':
            try:
                view=fetch_sec_online_research_view(ticker,user_agent=user_agent,ticker_map_receipt=mapping,source_fetcher=fetch,observed_at=observed_at)
            except (RuntimeError,ValueError,TypeError,OSError):
                view={'status':'unavailable','ticker':ticker,'reason':'sec_query_unavailable'}
            identity=view.get('companyfacts_identity',{})
            if financial_identity_valid(ticker,identity):
                profile=fetch_sec_company_profile(identity['sec_cik'],user_agent=user_agent,fetcher=fetch,observed_at=observed_at)
        observations.append({'ticker':ticker,'view':view,'profile':profile})
    result=summarize_online_research_coverage(observations,requested)
    result['source_request_count']=len(calls)
    return result


def get_online_coverage_study(session_state,*,refresh_requested,user_agent,tickers=DEFAULT_SAMPLE,
                              source_fetcher=None,observed_at=None,workspace_mode='research'):
    reason=_mode_reason(workspace_mode); requested=_tickers(tickers)
    if reason or requested is None: return {'status':'unavailable','reason':reason or 'invalid_sample'}
    if not refresh_requested:
        cached=session_state.get(SESSION_KEY)
        if isinstance(cached,Mapping) and cached.get('requested_tickers')==requested:
            checked=validated_coverage_summary(cached)
            return {**checked,'source_request_count':cached.get('source_request_count')} if checked else {'status':'unavailable','reason':'invalid_cached_sample'}
        return {'status':'not_requested','requested_tickers':requested}
    result=run_online_coverage_study(requested,user_agent=user_agent,source_fetcher=source_fetcher,observed_at=observed_at,workspace_mode=workspace_mode)
    session_state[SESSION_KEY]=result
    return result


def main():
    parser=argparse.ArgumentParser(description='Read-only bounded online SEC field coverage; no source cache or price batch.')
    parser.add_argument('--tickers',default=','.join(DEFAULT_SAMPLE))
    args=parser.parse_args()
    result=run_online_coverage_study(args.tickers,user_agent=os.getenv('SEC_USER_AGENT'))
    print(json.dumps(result,indent=2))
    return 0 if result.get('status')=='inspection_only' else 2


if __name__=='__main__':
    raise SystemExit(main())
