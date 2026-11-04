import json
from copy import deepcopy

import pytest

from test_online_company_prices import OBSERVED, _fetch, _payload

SOURCE='https://data.sec.gov/api/xbrl/companyfacts/CIK0000001234.json'


def _profile_payload():
    return {'cik':'0000001234','name':'Fictional Company','sic':'3571','sicDescription':'Electronic Computers',
            'tickers':['FICT'],'exchanges':['Nasdaq'],'entityType':'operating'}


def _profile_fetch(payload=None):
    return lambda url,agent:(json.dumps(_profile_payload() if payload is None else payload).encode(),{},url)


def _identity():
    return {'status':'source_matched','ticker':'FICT','sec_cik':'0000001234','source_url':SOURCE,
            'observed_at':'2026-10-30T18:00:00Z','payload_sha256':'a'*64,
            'association_source_url':'https://www.sec.gov/files/company_tickers.json',
            'association_payload_sha256':'b'*64,'association_observed_at':'2026-10-30T18:00:00Z'}


def _inputs():
    from src.online_company_identity import fetch_sec_company_profile
    from src.online_company_prices import fetch_online_company_prices
    p=_payload(); p['chart']['result'][0]['meta'].update(exchangeName='NMS',fullExchangeName='NasdaqGS',longName='Fictional Company')
    prices=fetch_online_company_prices('FICT',observed_at=OBSERVED,fetcher=_fetch(p))
    profile=fetch_sec_company_profile('0000001234',user_agent='Research contact',fetcher=_profile_fetch(),observed_at=OBSERVED)
    return _identity(),prices,profile


def test_profile_preserves_sic_and_source_receipt_without_claiming_commercial_approval(tmp_path,monkeypatch):
    from src.online_company_identity import fetch_sec_company_profile
    monkeypatch.chdir(tmp_path)
    p=fetch_sec_company_profile('0000001234',user_agent='Research',fetcher=_profile_fetch(),observed_at=OBSERVED)
    assert p['status']=='inspection_only' and p['sic']=='3571'
    assert p['tickers']==['FICT'] and p['exchanges']==['Nasdaq']
    assert p['rights_status']=='unregistered_identity_metadata_personal_inspection_only'
    assert p['commercial_eligible'] is False and len(p['payload_sha256'])==64
    assert not list(tmp_path.iterdir())


def test_exact_current_listing_association_keeps_vendor_identifier_and_valuation_unverified():
    from src.online_company_identity import build_price_filing_association
    i,prices,p=_inputs(); before=deepcopy((i,prices,p))
    link=build_price_filing_association('FICT',i,prices,p)
    assert link['status']=='matched_listing_association'
    assert link['sec_cik']=='0000001234' and link['exchange']=='Nasdaq'
    assert link['issuer_identity_status']=='vendor_issuer_identifier_unavailable'
    assert link['point_in_time_continuity_status']=='unverified'
    assert link['valuation_eligible'] is False
    assert len(link['source_receipts'])==4
    assert (i,prices,p)==before


@pytest.mark.parametrize('change',['cik','ticker','symbol','venue','full_venue','multiple_venues','old_observation','price_digest','financial_source','profile_source','profile_rights','bad_price_type','missing_bars','invalid_close'])
def test_mismatched_or_ambiguous_sources_cannot_form_an_association(change):
    from src.online_company_identity import build_price_filing_association
    i,prices,p=_inputs()
    if change=='cik': p['sec_cik']='0000009999'
    elif change=='ticker': p['tickers']=['OTHER']
    elif change=='symbol': prices['provider_symbol']='OTHER'
    elif change=='venue': prices['exchange_code']='NYQ'
    elif change=='full_venue': prices['full_exchange_name']='NYSE'
    elif change=='multiple_venues': p['exchanges']=['Nasdaq','NYSE']
    elif change=='old_observation': prices['observed_at']='2026-10-20T18:00:00Z'
    elif change=='price_digest': prices['payload_sha256']='not-a-digest'
    elif change=='financial_source': i['source_url']='https://example.invalid/'
    elif change=='profile_source': p['source_url']='https://example.invalid/'
    elif change=='profile_rights': p['rights_status']='approved'
    elif change=='bad_price_type': prices['instrument_type']='ETF'
    elif change=='missing_bars': prices['bars']=[]
    else: prices['bars'][0]['close']=True
    result=build_price_filing_association('FICT',i,prices,p)
    assert result['status']=='withheld' and result['valuation_eligible'] is False


def test_share_class_alias_is_explicit_and_names_are_never_used_as_a_join_key():
    from src.online_company_identity import build_price_filing_association
    i,prices,p=_inputs()
    i['ticker']='BRK.B'; prices.update(ticker='BRK.B',provider_symbol='BRK-B',exchange_code='NYQ',full_exchange_name='NYSE')
    prices['source_url']=prices['source_url'].replace('/FICT?','/BRK-B?')
    p.update(tickers=['BRK-A','BRK-B'],exchanges=['NYSE'],name='Name deliberately differs')
    result=build_price_filing_association('BRK.B',i,prices,p)
    assert result['status']=='matched_listing_association' and result['share_class_alias_applied'] is True
    p['tickers']=['BRK-A']
    assert build_price_filing_association('BRK.B',i,prices,p)['status']=='withheld'


def test_optional_industry_gaps_do_not_destroy_the_profile_identity():
    from src.online_company_identity import fetch_sec_company_profile
    raw=_profile_payload(); raw.pop('sic'); raw.pop('sicDescription')
    p=fetch_sec_company_profile('0000001234',user_agent='Research',fetcher=_profile_fetch(raw),observed_at=OBSERVED)
    assert p['status']=='inspection_only' and p['sic'] is None


def test_repeated_identical_exchange_entries_do_not_look_like_multiple_venues():
    from src.online_company_identity import fetch_sec_company_profile,build_price_filing_association
    raw=_profile_payload(); raw['tickers']=['FICT','FICT-PA']; raw['exchanges']=['Nasdaq','Nasdaq']
    raw['filings']={'recent':{'form':['10-K','10-Q'],'reportDate':['2025-12-31','2026-09-30'],'filingDate':['2026-03-01','2026-10-20']}}
    profile=fetch_sec_company_profile('0000001234',user_agent='Research',fetcher=_profile_fetch(raw),observed_at=OBSERVED)
    assert profile['status']=='inspection_only' and profile['exchanges']==['Nasdaq']
    assert profile['latest_annual_period_end']=='2025-12-31' and profile['latest_quarterly_period_end']=='2026-09-30'
    i,prices,_=_inputs()
    assert build_price_filing_association('FICT',i,prices,profile)['status']=='matched_listing_association'


@pytest.mark.parametrize('change',['cik','tickers','exchanges','name'])
def test_malformed_profile_identity_is_withheld(change):
    from src.online_company_identity import fetch_sec_company_profile
    raw=_profile_payload()
    raw[change]={'cik':9999,'tickers':['FICT',True],'exchanges':'Nasdaq','name':{'bad':'name'}}[change]
    p=fetch_sec_company_profile('0000001234',user_agent='Research',fetcher=_profile_fetch(raw),observed_at=OBSERVED)
    assert p['status']=='unavailable'


def test_identity_network_is_explicit_session_scoped_and_commercial_cache_is_blocked(monkeypatch):
    from src.online_company_identity import get_price_filing_association
    i,prices,p=_inputs(); calls=[]; state={}
    def fetch(url,agent): calls.append(url); return _profile_fetch()(url,agent)
    result=get_price_filing_association('FICT',i,prices,state,refresh_requested=False,user_agent='Research',fetcher=fetch,observed_at=OBSERVED)
    assert result['status']=='withheld' and not calls
    result=get_price_filing_association('FICT',i,prices,state,refresh_requested=True,user_agent='Research',fetcher=fetch,observed_at=OBSERVED)
    assert result['status']=='matched_listing_association' and len(calls)==1
    get_price_filing_association('FICT',i,prices,state,refresh_requested=False,user_agent='Research',fetcher=fetch)
    assert len(calls)==1
    monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE','1')
    assert get_price_filing_association('FICT',i,prices,state,refresh_requested=False,user_agent='Research',fetcher=fetch)['status']=='withheld'
    assert len(calls)==1


def test_no_profile_request_without_both_sources_or_outside_personal_mode():
    from src.online_company_identity import get_price_filing_association
    def no_fetch(*a): pytest.fail('unexpected profile request')
    i,prices,p=_inputs()
    for financial,price,mode in [({},prices,'research'),(i,{},'research'),(i,prices,'public')]:
        result=get_price_filing_association('FICT',financial,price,{},refresh_requested=True,user_agent='Research',fetcher=no_fetch,workspace_mode=mode)
        assert result['status']=='withheld'
