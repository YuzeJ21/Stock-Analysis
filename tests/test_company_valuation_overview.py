from copy import deepcopy
from datetime import date
import pytest

DAY=date(2026,10,31)

def observation(ticker,cik,value):
 return dict(ticker=ticker,sec_cik=cik,metric='pe',denominator_definition='diluted_GAAP_EPS',multiple=value,currency='USD',basis='TTM',period_start='2025-07-01',period_end='2026-06-30',price_date='2026-10-30',published_at='2026-08-01',observed_at='2026-10-31T01:00:00Z',source_ref='https://example.com/filing/'+ticker,identity_verified=True,rights_permitted=True,relationship_reviewed=True,relationship_rationale='Synthetic comparable business and accounting basis',relationship_source_ref='https://example.com/relation/'+ticker)

def report():
 return {'ticker':'FICT','valuation_readiness':{'peer_ready':True,'asset_type':'stock'},'quant_interpretation':{'valuation':{'family':'valuation','scope':'FICT:valuation_snapshot','interpretation_state':'current_context_eligible','calculation_state':'available','observation_state':'current','observation_through_date':'2026-10-30','provenance_state':'verified','rights_state':'permitted','field_scope_state':'permitted'}},'valuation_snapshot':{'relative_valuation':{'comparison_inputs':{'pe':{'subject':observation('FICT','0000001234',30),'peers':[observation('FA','0000002345',20),observation('FB','0000003456',25),observation('FC','0000004567',40)]}}}}}

def build(p=None,ticker='FICT'):
 from src.company_valuation_overview import build_valuation_overview
 return build_valuation_overview(ticker,report() if p is None else p,as_of_date=DAY)

def test_compatible_peers_show_hand_checked_median_and_premium():
 p=report();before=deepcopy(p);v=build(p);m=v['metrics']['pe']
 assert m['status']=='supported' and m['subject_multiple']==30 and m['peer_median']==25
 assert m['premium_fraction']==pytest.approx(.2) and m['peer_count']==3
 assert m['peer_tickers']==['FA','FB','FC'] and p==before
 assert v['status']=='supported' and 'score' not in v and 'target_price' not in v

@pytest.mark.parametrize('key,bad',[('multiple',0),('multiple',-3),('multiple',float('nan')),('multiple',float('inf')),('multiple',True),('identity_verified',False),('rights_permitted',False),('source_ref','javascript:alert(1)'),('period_start','bad'),('basis','forward'),('published_at','2026-10-31')])
def test_invalid_subject_cannot_imply_a_cheap_valuation(key,bad):
 p=report();p['valuation_snapshot']['relative_valuation']['comparison_inputs']['pe']['subject'][key]=bad
 m=build(p)['metrics']['pe'];assert m['status']=='withheld' and m['premium_fraction'] is None

@pytest.mark.parametrize('key,bad',[('currency','TWD'),('basis','annual'),('period_end','2026-03-31'),('price_date','2026-10-29'),('denominator_definition','adjusted_EPS'),('metric','forward_pe'),('relationship_reviewed',False),('relationship_rationale',''),('relationship_source_ref','local:unreviewed'),('ticker','FICT'),('sec_cik','0000001234')])
def test_mixed_or_unreviewed_peer_is_excluded_and_thin_group_is_withheld(key,bad):
 p=report();p['valuation_snapshot']['relative_valuation']['comparison_inputs']['pe']['peers'][0][key]=bad
 m=build(p)['metrics']['pe'];assert m['status']=='withheld' and m['peer_count']==2 and m['premium_fraction'] is None
 assert len(m['excluded'])==1

def test_metric_counts_are_independent_and_do_not_use_aggregate_peer_count():
 p=report();r=p['valuation_snapshot']['relative_valuation'];r['peer_count']=100;r['comparison_inputs']['ps']=deepcopy(r['comparison_inputs']['pe']);r['comparison_inputs']['ps']['peers']=r['comparison_inputs']['ps']['peers'][:2]
 for row in [r['comparison_inputs']['ps']['subject'],*r['comparison_inputs']['ps']['peers']]:row.update(metric='ps',denominator_definition='reported_revenue')
 v=build(p);assert v['metrics']['pe']['peer_count']==3 and v['metrics']['ps']['peer_count']==2
 assert v['metrics']['ps']['status']=='withheld' and v['metrics']['pe']['status']=='supported'

def test_duplicate_issuer_classes_do_not_count_twice():
 p=report();peers=p['valuation_snapshot']['relative_valuation']['comparison_inputs']['pe']['peers'];peers[1]['sec_cik']=peers[0]['sec_cik']
 assert build(p)['metrics']['pe']['peer_count']==2

@pytest.mark.parametrize('change',['ticker','scope','quant','old','fund','rights'])
def test_existing_readiness_cannot_override_identity_freshness_rights_or_fund_gate(change):
 p=report()
 if change=='ticker':p['ticker']='OTHER'
 elif change=='scope':p['quant_interpretation']['valuation']['scope']='OTHER:valuation_snapshot'
 elif change=='quant':p['quant_interpretation']['valuation']['interpretation_state']='historical_review_only'
 elif change=='old':p['quant_interpretation']['valuation']['observation_through_date']='2026-05-22'
 elif change=='fund':p['valuation_readiness']['asset_type']='fund'
 else:p['quant_interpretation']['valuation']['rights_state']='unverified'
 assert build(p)['metrics']['pe']['premium_fraction'] is None

def test_missing_observations_never_promote_stored_aggregate_medians():
 p=report();p['valuation_snapshot']['relative_valuation']={'peer_count':3,'subject_multiples':{'pe':30},'peer_median_multiples':{'pe':25}}
 assert build(p)['status']=='withheld'

def test_example_is_clearly_labelled_and_cannot_populate_company_values():
 from src.company_valuation_overview import build_valuation_overview,valuation_overview_html
 v=build_valuation_overview('FICT',None,as_of_date=DAY);html=valuation_overview_html(v)
 assert v['metrics']['pe']['premium_fraction'] is None
 assert 'Illustrative example' in html and 'ExampleCo' in html and '20%' in html
 assert 'not proof of overvaluation' in html
 assert '<h1' not in html and '30×' not in html.split('Illustrative example')[0]

def test_commercial_mode_cannot_reuse_research_comparison(monkeypatch):
 monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE','1');assert build()['status']=='withheld'

def test_unbounded_integer_input_does_not_throw():
 p=report();p['valuation_snapshot']['relative_valuation']['comparison_inputs']['pe']['subject']['multiple']=10**500
 assert build(p)['metrics']['pe']['premium_fraction'] is None

def test_nonfinite_comparison_from_tiny_peer_denominator_is_held():
 p=report()
 for row in p['valuation_snapshot']['relative_valuation']['comparison_inputs']['pe']['peers']:row['multiple']=1e-320
 assert build(p)['metrics']['pe']['premium_fraction'] is None

def test_thin_group_keeps_qualified_count_and_exclusion_reason_visible():
 from src.company_valuation_overview import valuation_overview_html
 p=report();p['valuation_snapshot']['relative_valuation']['comparison_inputs']['pe']['peers'][0]['currency']='TWD'
 v=build(p);html=valuation_overview_html(v)
 assert '2 verified' in html and 'FA' in html and 'currency or price date differs' in html
 assert '25.0×' not in html and v['metrics']['pe']['premium_fraction'] is None

def test_comparison_price_date_must_match_quant_evidence_cutoff():
 p=report();p['quant_interpretation']['valuation']['observation_through_date']='2026-10-29'
 assert build(p)['metrics']['pe']['premium_fraction'] is None

@pytest.mark.parametrize('case',['blank_definition','old_annual','old_ttm'])
def test_unknown_definitions_and_stale_financial_periods_cannot_be_current(case):
 p=report();m=p['valuation_snapshot']['relative_valuation']['comparison_inputs']['pe']
 for row in [m['subject'],*m['peers']]:
  if case=='blank_definition':row['denominator_definition']='  '
  elif case=='old_annual':row.update(basis='annual',period_start='2016-07-01',period_end='2017-06-30',published_at='2017-08-01')
  else:row.update(period_start='2025-01-01',period_end='2025-12-31',published_at='2026-02-01')
 assert build(p)['metrics']['pe']['premium_fraction'] is None
