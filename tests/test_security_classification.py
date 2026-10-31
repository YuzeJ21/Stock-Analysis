from copy import deepcopy
import json
import pytest
from test_online_us_universe import _fetch,OBSERVED,N_BODY,N_URL

@pytest.mark.parametrize('name,etf,want',[
 ('Fict - Common Stock',False,'common_shares'),('Fict - Ordinary Shares',False,'common_shares'),
 ('Fict - American Depositary Shares',False,'depositary_receipt'),('Fict Depositary Shares representing preferred shares',False,'depositary_receipt'),
 ('Fict Series A Preferred Stock',False,'preferred'),('Fict 6% Notes due 2030',False,'debt'),
 ('Fict - Units containing common stock and warrants',False,'unit'),('Fict - Warrants to purchase common stock',False,'warrant'),
 ('Fict - Rights to receive common stock',False,'right'),('Fict Income Trust',False,'unknown'),
 ('Fict Common Stock and Warrants',False,'unknown'),('Fict Fund',True,'etf'),('Fict ETN',False,'debt'),
 ('Fict',None,'unknown'),('Fict Common Stock',True,'etf'),('Fict Exchange Traded Notes',True,'unknown')])
def test_primary_instrument_is_not_its_underlying_equity(name,etf,want):
 from src.security_classification import classify_description
 assert classify_description(name,etf)['security_type']==want

def fixture_fetch(calls):
 original=_fetch(calls)
 def fetch(url,agent):
  if '/submissions/' in url:
   calls.append(url);return json.dumps(dict(cik=1234,entityType='operating',sic='3571',sicDescription='Computers',tickers=['FICT','FICT-B'],exchanges=['Nasdaq','Nasdaq'],filings={'recent':{'form':['10-K','10-Q']}})).encode(),{},url
  if url==N_URL:
   calls.append(url);return N_BODY.replace('Fictional Co','Fictional - Common Stock').replace('Fictional B','Fictional - Preferred Stock').encode(),{},url
  return original(url,agent)
 return fetch

def packet():
 from src.security_classification import fetch_classification
 return fetch_classification(user_agent='Synthetic contact',fetcher=fixture_fetch([]),observed_at=OBSERVED)

def test_full_listing_identity_and_unknowns_are_preserved_without_financial_promotion():
 from src.security_classification import validated_classification
 p=packet();assert p['status']=='inspection_only';assert validated_classification(p) is not None
 rows={r['listing_id']:r for r in p['rows']}
 assert rows['nasdaq:FICT']['security_type']=='common_shares'
 assert rows['nasdaq:FICT.B']['security_type']=='preferred'
 assert rows['nasdaq:FUND']['security_type']=='etf'
 assert next(r for r in p['rows'] if r['source']=='sec')['security_type']=='unknown'
 assert len(p['rows'])==p['inventory']['listing_count'] and p['inventory']['excluded_test_issue_count']==1
 assert p['analysis_eligibility_established'] is False and p['financial_coverage_promoted'] is False

@pytest.mark.parametrize('change',['type','name','identity','rights','counts'])
def test_cache_rederives_classification_and_rejects_incoherent_packets(change):
 from src.security_classification import validated_classification,_digest
 p=deepcopy(packet())
 if change=='type':p['rows'][0]['security_type']='debt'
 elif change=='name':p['rows'][0]['description']='Fict Warrants'
 elif change=='identity':p['rows'][0]['sec_cik']='0000099999'
 elif change=='rights':p['rights_status']='approved'
 else:p['counts']['unknown']=999
 p['packet_digest']=_digest({k:v for k,v in p.items() if k!='packet_digest'})
 assert validated_classification(p) is None

def test_form_profile_is_independent_of_security_type_and_financial_readiness():
 from src.security_classification import issuer_profile
 ref=dict(status='ready',source_url='https://data.sec.gov/submissions/CIK0000001234.json',observed_at='2026-10-30T22:00:00Z',payload_sha256='a'*64,payload=dict(cik=1234,entityType='investment-company',sic='0',sicDescription='',tickers=['FICT'],exchanges=['NYSE'],filings={'recent':{'form':['N-CSR','NPORT-P']}}))
 p=issuer_profile('0000001234',ref)
 assert p['reporting_profile']=='investment_company_reporting'
 assert p['security_type']=='unknown' and p['domicile_established'] is False and p['analysis_eligibility_established'] is False
 ref['payload']['cik']=999;assert issuer_profile('0000001234',ref)['status']=='withheld'

def test_company_actions_are_explicit_ticker_scoped_and_recheck_cik():
 from src.security_classification import get_company_security_context
 state={};calls=[];fetch=fixture_fetch(calls)
 assert get_company_security_context('FICT',state,refresh_requested=False,user_agent='Synthetic',fetcher=fetch)['status']=='not_requested'
 assert not calls
 p=get_company_security_context('FICT',state,refresh_requested=True,user_agent='Synthetic',fetcher=fetch,expected_cik='0000001234',observed_at=OBSERVED)
 assert p['status']=='inspection_only' and p['issuer_profile']['reporting_profile']=='domestic_annual_reporting'
 assert {r['security_type'] for r in p['listing_rows']}=={'common_shares'}
 n=len(calls);assert get_company_security_context('FICT',state,refresh_requested=False,user_agent='Synthetic',fetcher=fetch,expected_cik='0000001234')['status']=='inspection_only';assert len(calls)==n
 assert get_company_security_context('BANK',state,refresh_requested=False,user_agent='Synthetic',fetcher=fetch)['status']=='not_requested'
 assert get_company_security_context('FICT',state,refresh_requested=False,user_agent='Synthetic',fetcher=fetch,expected_cik='0000099999')['status']=='withheld'

def test_commercial_mode_cannot_fetch_or_reuse_personal_classification(monkeypatch):
 from src.security_classification import fetch_classification,get_company_security_context
 calls=[];monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE','1')
 assert fetch_classification(user_agent='Synthetic',fetcher=fixture_fetch(calls))['status']=='withheld'
 assert get_company_security_context('FICT',{},refresh_requested=True,user_agent='Synthetic',fetcher=fixture_fetch(calls))['status']=='withheld'
 assert not calls

@pytest.mark.parametrize('body',[{'cik':1234,'filings':None},{'cik':1234,'filings':{'recent':None}},{'cik':1234,'filings':{'recent':{'form':[1]}}}])
def test_malformed_submissions_are_held_without_losing_the_selected_company(body):
 from src.security_classification import issuer_profile
 p=issuer_profile('0000001234',dict(status='ready',source_url='https://data.sec.gov/submissions/CIK0000001234.json',observed_at='2026-10-30T22:00:00Z',payload_sha256='a'*64,payload=body))
 assert p['status']=='withheld' and p['sec_cik']=='0000001234'

def test_failed_explicit_refresh_cannot_restore_prior_context_on_rerender():
 from src.security_classification import get_company_security_context
 state={};get_company_security_context('FICT',state,refresh_requested=True,user_agent='Synthetic',fetcher=fixture_fetch([]),observed_at=OBSERVED)
 def fail(*args):raise OSError('Synthetic unavailable')
 assert get_company_security_context('FICT',state,refresh_requested=True,user_agent='Synthetic',fetcher=fail,observed_at=OBSERVED)['status']=='withheld'
 assert get_company_security_context('FICT',state,refresh_requested=False,user_agent='Synthetic')['status']=='withheld'

def test_directory_common_label_never_certifies_current_legal_instrument_type():
 p=packet()
 assert p['legal_security_type_established'] is False
 assert all(r['legal_security_type_established'] is False for r in p['rows'])
