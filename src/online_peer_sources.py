"""Bounded, explicit online research observations; no canonical apply or rights grant.

SEC receipt digests refer to original HTTP bytes. Reduced SEC payloads and public
SDK return values have separate normalized digests. SDK cookies/timezone caches
are managed by the installed library; source observations stay in session memory.
"""
from collections.abc import Mapping
from copy import deepcopy
from datetime import date, datetime, timezone
import os

from src.online_company_identity import _mode_reason
from src.online_company_prices import fetch_online_company_prices
from src.online_peer_valuation import (
    SCHEMA, MAX_CANDIDATES, normalized_digest, build_online_peer_valuation,
    _empty, _symbol, _KEY,
)
from src.online_sec_receipt import fetch_sec_json_receipt
from src.security_classification import fetch_classification, validated_classification, _selected
from src.annual_amendment_evidence import fetch_amendment_evidence, amendment_candidate
from src.sec_selected_security import fetch_selected_security_evidence,known_security_scope,FINANCIAL_FORMS,IDENTITY_FORMS,is_investment_company_form,valid_profile_metadata_shape
from src.online_peer_sec_history import fetch_vendor_history_match

SESSION_KEY = 'online_peer_valuation_observation_v1'
_INFO_FIELDS = ('symbol','quoteType','currency','financialCurrency','exchange','exchangeTimezoneName',
                'industryKey','industry','sectorKey','regularMarketTime','regularMarketPrice')


def _now(value=None):
    now=value if value is not None else datetime.now(timezone.utc)
    if not isinstance(now,datetime) or now.utcoffset() is None:
        raise ValueError('invalid_observation')
    return now.astimezone(timezone.utc)


def _stamp(value=None):
    return _now(value).strftime('%Y-%m-%dT%H:%M:%SZ')


def observe_vendor(ticker, *, sdk=None, observed_at=None, workspace_mode='research'):
    reason=_mode_reason(workspace_mode)
    held=dict(status='unavailable',reason=reason or 'vendor_context_source_unavailable')
    if reason or not _symbol(ticker):
        return held
    try:
        if sdk is None:
            import yfinance as sdk
        provider=sdk.Ticker(ticker.replace('.','-'))
        info=provider.get_info();filings=provider.get_sec_filings()
        if not isinstance(info,Mapping) or not isinstance(filings,list) or not 0<len(filings)<=256:
            return held
        normalized=[]
        for filing in filings:
            if not isinstance(filing,Mapping):
                return held
            day=filing.get('date')
            day=day.isoformat() if type(day) is date else day
            normalized.append(dict(type=filing.get('type'),date=day,edgarUrl=filing.get('edgarUrl'),
                                   exhibits=dict(filing['exhibits']) if isinstance(filing.get('exhibits'),Mapping) else None))
        payload=dict(info={k:info.get(k) for k in _INFO_FIELDS},filings=normalized)
        return dict(status='observed',source_ref=f'https://finance.yahoo.com/quote/{ticker.replace(".","-")}/',
                    adapter='yfinance_public_methods',adapter_version=getattr(sdk,'__version__','unknown'),
                    observed_at=_stamp(observed_at),payload=payload,normalized_sha256=normalized_digest(payload))
    except Exception:
        # Provider exceptions can contain identifiers or request internals. Keep a stable gap.
        return held


def observe_industry(key, sector, *, sdk=None, observed_at=None, workspace_mode='research'):
    reason=_mode_reason(workspace_mode)
    held=dict(status='unavailable',reason=reason or 'industry_candidate_source_unavailable')
    if reason or not isinstance(key,str) or not _KEY.fullmatch(key) or not isinstance(sector,str) or not _KEY.fullmatch(sector):
        return held
    try:
        if sdk is None:
            import yfinance as sdk
        industry=sdk.Industry(key)
        table=industry.top_companies
        if table is None or len(table)>200 or industry.sector_key!=sector:
            return held
        symbols=table.index.tolist()
        if not all(_symbol(s) for s in symbols):
            return held
        payload=dict(key=key,sector=sector,symbols=symbols)
        return dict(status='observed',source_ref=f'https://finance.yahoo.com/sectors/{sector}/{key}/',
                    adapter='yfinance_industry_top_companies',observed_at=_stamp(observed_at),
                    payload=payload,normalized_sha256=normalized_digest(payload))
    except Exception:
        return held


def _reduce_sec(receipt, kind):
    result=deepcopy(receipt)
    if not isinstance(result,dict) or result.get('status')!='ready' or not isinstance(result.get('payload'),Mapping):
        return result
    body=result['payload']
    if kind=='facts':
        eps=body.get('facts',{}).get('us-gaap',{}).get('EarningsPerShareDiluted')
        body=dict(cik=body.get('cik'),facts={'us-gaap': {'EarningsPerShareDiluted':eps} if isinstance(eps,Mapping) else {}})
    else:
        recent=body.get('filings',{}).get('recent',{})
        columns=('form','reportDate','filingDate','accessionNumber','primaryDocument')
        if 'acceptanceDateTime' in recent:columns+=('acceptanceDateTime',)
        if 'isInlineXBRL' in recent or 'isXBRL' in recent:columns+=('isInlineXBRL','isXBRL')
        if not valid_profile_metadata_shape(recent,max_rows=50000):
            return dict(status='unavailable',reason='filing_metadata_schema_invalid',source_url=result.get('source_url'))
        indices=[i for i,f in enumerate(recent['form']) if f in FINANCIAL_FORMS|IDENTITY_FORMS or is_investment_company_form(f)]
        files=body.get('filings',{}).get('files')
        body={k:body.get(k) for k in ('cik','entityType','sic','sicDescription','tickers','exchanges')}
        body['filings']={'recent':{k:[recent[k][i] for i in indices] for k in columns}}
        if files is not None:body['filings']['files']=files
    result.update(payload=body,normalized_sha256=normalized_digest(body),normalization='annual_peer_source_subset_v1')
    return result


def _ordinary_identity(classification,ticker,expected_cik=None):
    cik,rows=_selected(classification,ticker,expected_cik)
    explicit=[r for r in rows if r['source']!='sec']
    if not explicit or any(r['security_type']!='common_shares' for r in explicit):
        raise ValueError('ordinary_share_basis_unverified')
    return cik


def _attempt_source(function,*args,**kwargs):
    try:return function(*args,**kwargs)
    except Exception:return dict(status='unavailable',reason='source_component_unavailable')


def _collect_issuer(ticker,cik,deps,user_agent,as_of,vendor=None):
    vendor=vendor if vendor is not None else deps['vendor'](ticker,observed_at=as_of)
    if not isinstance(vendor,Mapping) or vendor.get('status')!='observed':
        return dict(ticker=ticker,status='unavailable',reason='vendor_context_source_unavailable')
    profile=_reduce_sec(_attempt_source(deps['sec'],f'https://data.sec.gov/submissions/CIK{cik}.json',user_agent=user_agent,observed_at=as_of),'profile')
    facts=_reduce_sec(_attempt_source(deps['sec'],f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json',user_agent=user_agent,observed_at=as_of),'facts')
    prices=_attempt_source(deps['prices'],ticker,observed_at=as_of,history_range='2y')
    result=dict(ticker=ticker,vendor=vendor,profile=profile,facts=facts,prices=prices)
    result['vendor_history']=_attempt_source(deps['history'],cik,profile,vendor,user_agent=user_agent,observed_at=as_of)
    if known_security_scope(ticker,cik):
        result['selected_security_evidence']=_attempt_source(deps['security'],ticker,cik,profile,user_agent=user_agent,observed_at=as_of)
    if amendment_candidate(ticker,cik,profile,as_of=as_of):
        result['amendment_evidence']=_attempt_source(deps['amendment'],ticker,cik,profile,user_agent=user_agent,observed_at=as_of)
    if any(not isinstance(r,Mapping) or r.get('status') not in {'ready','inspection_only'} for r in (profile,facts,prices)):
        result.update(status='unavailable',reason='issuer_source_unavailable')
    if any(isinstance(result.get(k),Mapping) and result[k].get('status')=='unavailable' and result[k].get('reason') in {'vendor_history_source_unavailable','selected_security_source_unavailable','source_component_unavailable'} for k in ('vendor_history','selected_security_evidence')):
        result.update(status='unavailable',reason='issuer_source_unavailable')
    return result


def _cache(state,ticker,collection,error,as_of):
    cached=dict(ticker=ticker,collection=collection,error=error,observed_at=_stamp(as_of))
    cached['packet_digest']=normalized_digest(cached)
    state[SESSION_KEY]=cached
    return cached


def _read(cached,ticker,expected_cik,as_of):
    try:
        if not isinstance(cached,Mapping) or cached.get('ticker')!=ticker:
            return {**_empty(ticker,'online_peer_update_not_requested'),'status':'not_requested'}
        if cached.get('packet_digest')!=normalized_digest({k:v for k,v in cached.items() if k!='packet_digest'}):
            return _empty(ticker,'cached_observation_changed')
        if cached.get('error'):
            return {**_empty(ticker,cached['error']),'attempted_at':cached['observed_at']}
        view=build_online_peer_valuation(cached.get('collection'),ticker=ticker,expected_cik=expected_cik,as_of=_now(as_of))
        view['attempted_at']=cached['observed_at']
        return view
    except (ValueError,TypeError,KeyError,AttributeError,OverflowError,RecursionError):
        return _empty(ticker,'cached_observation_invalid')


def get_online_peer_valuation(ticker,state,*,refresh_requested,expected_cik=None,user_agent=None,
                              dependencies=None,as_of=None,workspace_mode='research'):
    """No refresh means no network; explicit failure replaces the previous observation."""
    ticker=ticker.strip().upper() if isinstance(ticker,str) else ''
    reason=_mode_reason(workspace_mode)
    if reason or not _symbol(ticker):
        return _empty(ticker,reason or 'invalid_ticker')
    if not refresh_requested:
        return _read(state.get(SESSION_KEY),ticker,expected_cik,as_of)
    try:
        _now(as_of)
        # Clear a previous successful result before the first fallible request.
        _cache(state,ticker,None,'peer_refresh_incomplete',as_of)
        deps=dict(classification=fetch_classification,vendor=observe_vendor,industry=observe_industry,
                  sec=fetch_sec_json_receipt,prices=fetch_online_company_prices,amendment=fetch_amendment_evidence,security=fetch_selected_security_evidence,history=fetch_vendor_history_match)
        if dependencies is not None:
            deps.update(dependencies)
        classification=validated_classification(deps['classification'](user_agent=user_agent or os.getenv('SEC_USER_AGENT'),observed_at=as_of))
        if classification is None:
            return _read(_cache(state,ticker,None,'listing_classification_unavailable',as_of),ticker,expected_cik,as_of)
        try:
            cik=_ordinary_identity(classification,ticker,expected_cik)
        except (ValueError,KeyError,TypeError):
            try:
                cik,listings=_selected(classification,ticker,expected_cik)
                explicit=[r for r in listings if r['source']!='sec']
                if not (known_security_scope(ticker,cik) and explicit and all(r['security_type']=='unknown' and r['reason']=='explicit_instrument_description_unavailable' for r in explicit)):raise ValueError()
            except (ValueError,KeyError,TypeError):
                return _read(_cache(state,ticker,None,'selected_listing_or_cik_unverified',as_of),ticker,expected_cik,as_of)
        vendor=deps['vendor'](ticker,observed_at=as_of)
        if not isinstance(vendor,Mapping) or vendor.get('status')!='observed':
            return _read(_cache(state,ticker,None,'vendor_context_source_unavailable',as_of),ticker,expected_cik,as_of)
        info=vendor.get('payload',{}).get('info',{})
        key,sector=info.get('industryKey'),info.get('sectorKey')
        if not isinstance(key,str) or not _KEY.fullmatch(key) or not isinstance(sector,str) or not _KEY.fullmatch(sector):
            return _read(_cache(state,ticker,None,'industry_metadata_missing',as_of),ticker,expected_cik,as_of)
        industry=deps['industry'](key,sector,observed_at=as_of)
        payload=industry.get('payload',{}) if isinstance(industry,Mapping) else {}
        symbols=payload.get('symbols')
        if (industry.get('status')!='observed' or not isinstance(symbols,list) or len(symbols)>200 or not all(_symbol(s) for s in symbols)):
            return _read(_cache(state,ticker,None,'industry_candidate_source_unavailable',as_of),ticker,expected_cik,as_of)
        candidates=list(dict.fromkeys(s for s in symbols if s.replace('.','-')!=ticker.replace('.','-')))[:MAX_CANDIDATES]
        collection=dict(schema_version=SCHEMA,ticker=ticker,classification=classification,industry=industry,
                        issuers=[_collect_issuer(ticker,cik,deps,user_agent or os.getenv('SEC_USER_AGENT'),as_of,vendor)],observed_at=_stamp(as_of))
        preview=build_online_peer_valuation(collection,ticker=ticker,expected_cik=expected_cik,as_of=_now(as_of))
        if preview['subject'] is not None:
            failures=0
            for candidate in candidates:
                if failures>=2:
                    collection['issuers'].append(dict(ticker=candidate,status='unavailable',reason='source_paused_after_repeated_failures'))
                    continue
                try:
                    peer_cik=_ordinary_identity(classification,candidate)
                except (ValueError,KeyError,TypeError):
                    collection['issuers'].append(dict(ticker=candidate,status='unavailable',reason='peer_listing_or_share_basis_unverified'))
                    continue
                try:
                    packet=_collect_issuer(candidate,peer_cik,deps,user_agent or os.getenv('SEC_USER_AGENT'),as_of)
                except Exception:
                    packet=dict(ticker=candidate,status='unavailable',reason='issuer_source_unavailable')
                failures=failures+1 if packet.get('status')=='unavailable' else 0
                collection['issuers'].append(packet)
        collection['observed_at']=_stamp(as_of)
        cached=_cache(state,ticker,collection,None,as_of)
    except Exception:
        cached=_cache(state,ticker,None,'peer_source_unavailable',as_of=None)
    return _read(cached,ticker,expected_cik,as_of)
