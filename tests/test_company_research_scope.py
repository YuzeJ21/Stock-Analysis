import json
from copy import deepcopy
import pytest
from test_security_classification import fixture_fetch
from test_online_us_universe import OBSERVED


def context(sic='3571',entity='operating',forms=None,wrapper=False):
 from src.security_classification import get_company_security_context
 original=fixture_fetch([])
 def fetch(url,agent):
  raw,headers,final=original(url,agent)
  if '/submissions/' in url:
   body=json.loads(raw);body.update(sic=sic,entityType=entity);body['filings']['recent']['form']=forms or ['10-K'];raw=json.dumps(body).encode()
  elif wrapper and 'nasdaqlisted' in url:
   assert b'Fictional - Common Stock' in raw
   raw=raw.replace(b'Fictional - Common Stock',b'Fictional - Warrants')
  return raw,headers,final
 return get_company_security_context('FICT',{},refresh_requested=True,user_agent='Synthetic',fetcher=fetch,expected_cik='0000001234',observed_at=OBSERVED)

@pytest.mark.parametrize('sic,entity,forms,want',[
 ('','other',['N-CSR'],'investment_company'),('6022','operating',['10-K'],'bank'),
 ('6770','operating',['10-K'],'blank_check'),('3571','operating',['10-K'],'operating_company_candidate'),
 ('3571','other',['10-K'],'issuer_review'),
])
def test_fund_bank_blank_check_and_operating_profiles_have_distinct_paths(sic,entity,forms,want):
 from src.company_research_scope import research_scope
 c=context(sic,entity,forms);before=deepcopy(c);r=research_scope(c,'FICT')
 assert r['path']==want and r['issuer_path']==want
 assert r['analysis_eligibility_established'] is False and r['legal_security_type_established'] is False
 assert c==before

def test_wrapper_does_not_become_underlying_company():
 from src.company_research_scope import research_scope
 r=research_scope(context(wrapper=True),'FICT')
 assert r['path']=='security_wrapper' and r['issuer_path']=='operating_company_candidate'
 assert 'warrant' in r['security_types'] and r['analysis_eligibility_established'] is False

def test_invalid_or_switched_context_is_unresolved():
 from src.company_research_scope import research_scope
 c=context();c['issuer_profile']['sic']='6022'
 assert research_scope(c,'FICT')['path']=='unresolved'
 assert research_scope(context(),'OTHER')['path']=='unresolved'

def test_commercial_mode_cannot_reuse_a_valid_personal_context(monkeypatch):
 from src.company_research_scope import research_scope
 cached=context()
 monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE','1')
 assert research_scope(cached,'FICT')['path']=='unresolved'

def test_mixed_forms_keep_affirmative_investment_company_evidence():
 from src.company_research_scope import research_scope
 c=context('',entity='investment-company',forms=['N-CSR','10-K'])
 assert c['issuer_profile']['reporting_profile']=='mixed_reporting'
 assert research_scope(c,'FICT')['path']=='investment_company'
