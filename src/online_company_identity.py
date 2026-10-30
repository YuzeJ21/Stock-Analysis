"""Qualified current listing associations; never a vendor issuer-ID approval."""

import re
import unicodedata
from collections.abc import Mapping
from datetime import timedelta

from src.company_sec_online_preview import _iso_date, _utc_timestamp, _finite_direct_number
from src.commercial_source_rights import commercial_mode_enabled
from src.online_company_prices import price_source_url
from src.online_sec_receipt import fetch_sec_json_receipt

PROFILE_RIGHTS='unregistered_identity_metadata_personal_inspection_only'
SESSION_KEY='online_company_sec_profile_v1'
_VENUES={
    'NMS':('Nasdaq',{'NasdaqGS','Nasdaq'}),'NGM':('Nasdaq',{'NasdaqGM','Nasdaq'}),
    'NCM':('Nasdaq',{'NasdaqCM','Nasdaq'}),'NYQ':('NYSE',{'NYSE'}),
    'ASE':('NYSE American',{'NYSE American','AMEX'}),
}


def _text(value,maximum=240):
    return isinstance(value,str) and 0<len(value)<=maximum and value==value.strip() and not any(unicodedata.category(c) in {'Cc','Cf'} for c in value)


def _digest(value):
    return isinstance(value,str) and re.fullmatch(r'[0-9a-f]{64}',value) is not None


def _cik(value):
    return isinstance(value,str) and re.fullmatch(r'\d{10}',value) is not None and int(value)>0


def _mode_reason(workspace_mode):
    if workspace_mode!='research': return 'personal_research_mode_required'
    try: return 'commercial_identity_rights_unreviewed' if commercial_mode_enabled() else None
    except ValueError: return 'invalid_commercial_mode_configuration'


def financial_identity_valid(ticker,identity):
    if (not isinstance(ticker,str) or not re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,19}',ticker)
        or not isinstance(identity,Mapping) or identity.get('status')!='source_matched'
        or identity.get('ticker')!=ticker or not _cik(identity.get('sec_cik'))): return False
    cik=identity['sec_cik']; observed=_utc_timestamp(identity.get('observed_at')); mapped=_utc_timestamp(identity.get('association_observed_at'))
    return bool(identity.get('source_url')==f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'
        and identity.get('association_source_url')=='https://www.sec.gov/files/company_tickers.json'
        and _digest(identity.get('payload_sha256')) and _digest(identity.get('association_payload_sha256'))
        and observed and mapped and timedelta(0)<=observed-mapped<=timedelta(hours=24))


def validated_sec_company_profile(profile,expected_cik):
    if not isinstance(profile,Mapping) or profile.get('status')!='inspection_only' or not _cik(expected_cik): return None
    if (profile.get('sec_cik')!=expected_cik or profile.get('source_url')!=f'https://data.sec.gov/submissions/CIK{expected_cik}.json'
        or profile.get('rights_status')!=PROFILE_RIGHTS or profile.get('commercial_eligible') is not False
        or not _digest(profile.get('payload_sha256')) or _utc_timestamp(profile.get('observed_at')) is None
        or not _text(profile.get('name'))): return None
    tickers=profile.get('tickers'); exchanges=profile.get('exchanges')
    if not isinstance(tickers,list) or not isinstance(exchanges,list) or len(tickers)>128 or len(exchanges)>32: return None
    if any(not isinstance(v,str) or not re.fullmatch(r'[A-Z0-9][A-Z0-9.$-]{0,20}',v) for v in tickers): return None
    if any(not _text(v,80) for v in exchanges) or len(set(tickers))!=len(tickers) or len(set(exchanges))!=len(exchanges): return None
    sic=profile.get('sic'); description=profile.get('sic_description')
    if sic is not None and (not isinstance(sic,str) or not re.fullmatch(r'\d{4}',sic) or sic=='0000'): return None
    if description is not None and not _text(description): return None
    return dict(profile)


def fetch_sec_company_profile(cik,*,user_agent,fetcher=None,observed_at=None,workspace_mode='research'):
    reason=_mode_reason(workspace_mode)
    held={'status':'unavailable','reason':reason or 'sec_profile_unavailable'}
    if reason or not _cik(cik): return held
    receipt=fetch_sec_json_receipt(f'https://data.sec.gov/submissions/CIK{cik}.json',user_agent=user_agent,fetcher=fetcher,observed_at=observed_at)
    if receipt['status']!='ready': return {**held,'reason':receipt.get('reason','sec_profile_unavailable')}
    raw=receipt['payload']; raw_cik=raw.get('cik')
    if type(raw_cik) not in {int,str} or not re.fullmatch(r'\d{1,10}',str(raw_cik)) or str(int(raw_cik)).zfill(10)!=cik: return held
    sic=raw.get('sic'); sic=str(sic) if type(sic) in {int,str} else ''
    sic=sic if re.fullmatch(r'\d{4}',sic) and sic!='0000' else None
    result={k:receipt[k] for k in ('source_url','observed_at','source_last_modified','payload_sha256')}
    result.update(status='inspection_only',sec_cik=cik,name=raw.get('name'),tickers=raw.get('tickers'),exchanges=raw.get('exchanges'),
        sic=sic,sic_description=raw.get('sicDescription') if _text(raw.get('sicDescription')) else None,
        rights_status=PROFILE_RIGHTS,commercial_eligible=False)
    return validated_sec_company_profile(result,cik) or held


def _price_identity_valid(ticker,prices):
    if not isinstance(prices,Mapping): return False
    symbol=ticker.replace('.','-'); observed=_utc_timestamp(prices.get('observed_at')); last=_iso_date(prices.get('last_price_date'))
    bars=prices.get('bars')
    if not isinstance(bars,list) or not 1<=len(bars)<=400: return False
    previous=None
    for row in bars:
        if not isinstance(row,Mapping): return False
        day=_iso_date(row.get('date')); close=row.get('close')
        if day is None or observed is None or day>observed.date() or previous is not None and day<=previous: return False
        if not _finite_direct_number(close) or close<=0: return False
        previous=day
    if last!=previous: return False
    return bool(prices.get('status')=='inspection_only' and prices.get('ticker')==ticker and prices.get('provider_symbol')==symbol
        and prices.get('source_id')=='yahoo_chart' and prices.get('source_url')==price_source_url(symbol)
        and prices.get('instrument_type')=='EQUITY' and prices.get('currency')=='USD'
        and prices.get('rights_status')=='exact_source_unregistered_personal_inspection_only' and prices.get('commercial_eligible') is False
        and _digest(prices.get('payload_sha256')) and observed and last and last<=observed.date())


def _held(ticker,reason):
    return {'status':'withheld','ticker':ticker,'reason':reason,'valuation_eligible':False,'source_receipts':[]}


def build_price_filing_association(ticker,financial_identity,prices,profile):
    reason=_mode_reason('research')
    if reason: return _held(ticker,reason)
    if not financial_identity_valid(ticker,financial_identity): return _held(ticker,'filing_identity_required')
    if not _price_identity_valid(ticker,prices): return _held(ticker,'validated_price_identity_required')
    cik=financial_identity['sec_cik']; profile=validated_sec_company_profile(profile,cik)
    if profile is None: return _held(ticker,'sec_profile_required')
    symbol=prices['provider_symbol']
    matched=[t for t in profile['tickers'] if t.replace('.','-')==symbol]
    if len(matched)!=1: return _held(ticker,'sec_ticker_association_mismatch_or_ambiguity')
    code=prices.get('exchange_code'); full_name=prices.get('full_exchange_name')
    venue=_VENUES.get(code) if isinstance(code,str) else None
    if venue is None: return _held(ticker,'provider_venue_unavailable_or_unsupported')
    if full_name is not None and (not isinstance(full_name,str) or full_name not in venue[1]):
        return _held(ticker,'provider_venue_metadata_conflict')
    if len(profile['exchanges'])!=1: return _held(ticker,'ambiguous_or_missing_issuer_exchange')
    if profile['exchanges'][0]!=venue[0]: return _held(ticker,'sec_provider_exchange_mismatch')
    times=[_utc_timestamp(v) for v in (financial_identity['observed_at'],financial_identity['association_observed_at'],prices['observed_at'],profile['observed_at'])]
    if max(times)-min(times)>timedelta(hours=24): return _held(ticker,'cross_source_observation_gap')
    refs=[{k:v[k] for k in ('source_url','observed_at','payload_sha256')} for v in (financial_identity,prices,profile)]
    refs.append({'source_url':financial_identity['association_source_url'],'observed_at':financial_identity['association_observed_at'],
                 'payload_sha256':financial_identity['association_payload_sha256']})
    return {'status':'matched_listing_association','ticker':ticker,'sec_cik':cik,'provider_symbol':symbol,'sec_ticker':matched[0],
            'exchange':venue[0],'share_class_alias_applied':ticker!=symbol,'source_receipts':refs,
            'issuer_identity_status':'vendor_issuer_identifier_unavailable','point_in_time_continuity_status':'unverified',
            'valuation_eligible':False,'reason':None}


def get_price_filing_association(ticker,financial_identity,prices,session_state,*,refresh_requested,user_agent,
                                 fetcher=None,observed_at=None,workspace_mode='research'):
    reason=_mode_reason(workspace_mode)
    if reason: return _held(ticker,reason)
    if not financial_identity_valid(ticker,financial_identity): return _held(ticker,'filing_identity_required')
    if not _price_identity_valid(ticker,prices): return _held(ticker,'validated_price_identity_required')
    cik=financial_identity['sec_cik']; cached=session_state.get(SESSION_KEY)
    if refresh_requested:
        profile=fetch_sec_company_profile(cik,user_agent=user_agent,fetcher=fetcher,observed_at=observed_at)
        session_state[SESSION_KEY]={'ticker':ticker,'sec_cik':cik,'profile':profile}
    else:
        profile=cached.get('profile') if isinstance(cached,Mapping) and cached.get('ticker')==ticker and cached.get('sec_cik')==cik else None
    return build_price_filing_association(ticker,financial_identity,prices,profile)

