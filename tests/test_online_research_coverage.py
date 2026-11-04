import json
from copy import deepcopy

import pytest

from test_online_company_identity import _identity, _inputs, _profile_payload
from test_sec_annual_history import _view, _payload
from test_sec_quarterly_history import _build, _quarter_payload
from test_online_company_prices import OBSERVED


def _observation(ticker='FICT',*,supported=True,sic='3571',cik='0000001234'):
    from src.sec_annual_history import build_sec_annual_history
    i=_identity(); i.update(ticker=ticker,sec_cik=cik,source_url=f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json')
    view=_view() if supported else {'status':'unavailable','ticker':ticker,'reason':'unsupported_annual_anchor'}
    view['ticker']=ticker; view['companyfacts_identity']=i
    if supported:
        view['annual_history']=build_sec_annual_history(view,_payload())
        view['quarterly_history']=_build()
    else: view['quarterly_history']={'status':'withheld','reason':'supported_direct_quarter_revenue_unavailable','periods':[]}
    p=_inputs()[2]; p.update(sec_cik=cik,source_url=f'https://data.sec.gov/submissions/CIK{cik}.json',tickers=[ticker],sic=sic)
    return {'ticker':ticker,'view':view,'profile':p}


def test_sample_denominator_keeps_unsupported_missing_and_unknown_industry_queries():
    from src.online_research_coverage import summarize_online_research_coverage
    result=summarize_online_research_coverage([_observation(),_observation('GAP',supported=False,sic='6021',cik='0000005678')],['FICT','GAP','MISSING'])
    assert result['status']=='inspection_only'
    assert result['requested_count']==3 and result['attempted_count']==2
    assert result['resolved_issuer_count']==2
    assert result['counts']['annual_revenue']==1
    assert result['counts']['quarterly_revenue']==1
    assert result['counts']['quarterly_cash_from_operations']==0
    assert result['counts']['cumulative_cash_from_operations']==1
    assert result['unsupported_financial_count']==1 and result['source_failure_count']==1
    assert result['unknown_industry_count']==1
    assert sum(g['requested_count'] for g in result['by_industry'])==3
    assert result['market_universe_coverage_established'] is False
    assert [r['ticker'] for r in result['rows']]==['FICT','GAP','MISSING']


def test_coverage_counts_latest_withheld_period_instead_of_cherry_picking_an_older_quarter():
    from src.online_research_coverage import summarize_online_research_coverage
    obs=_observation(); h=obs['view']['quarterly_history']
    h['periods'][-1].update(status='withheld',fields={},cumulative_fields={},cumulative_anchor=None,reason='raw_source_conflict')
    result=summarize_online_research_coverage([obs],['FICT'])
    assert result['counts']['quarterly_revenue']==0
    assert result['rows'][0]['quarterly_period']=='2025-09-30'
    assert result['rows'][0]['quarterly_reason']=='raw_source_conflict'


def test_duplicate_or_unrequested_observations_are_not_silently_counted():
    from src.online_research_coverage import summarize_online_research_coverage
    assert summarize_online_research_coverage([_observation(),_observation()],['FICT'])['status']=='invalid'
    assert summarize_online_research_coverage([_observation()],['OTHER'])['status']=='invalid'


def _study_fetcher(calls):
    def fetch(url,agent):
        calls.append(url)
        if url.endswith('company_tickers.json'):
            body={'0':{'ticker':'FICT','cik_str':1234},'1':{'ticker':'BANK','cik_str':5678}}
        elif '/companyfacts/' in url:
            body=_quarter_payload(); body['cik']=5678 if '0000005678' in url else 1234
        elif '/submissions/' in url:
            body=_profile_payload()
            if '0000005678' in url: body.update(cik='0000005678',tickers=['BANK'],exchanges=['NYSE'],sic='6021',sicDescription='National Commercial Banks')
        else: pytest.fail('coverage requested an unexpected or bulk price source')
        return json.dumps(body).encode(),{},url
    return fetch


def test_real_study_pipeline_shares_one_map_and_writes_no_csv_or_source_cache(tmp_path,monkeypatch):
    from src.online_research_coverage import run_online_coverage_study
    monkeypatch.chdir(tmp_path); calls=[]
    result=run_online_coverage_study(['FICT','BANK'],user_agent='Research contact',source_fetcher=_study_fetcher(calls),observed_at=OBSERVED)
    assert result['requested_count']==2 and result['counts']['quarterly_revenue']==2
    assert result['counts']['annual_revenue']==0
    assert len(calls)==5 and sum(u.endswith('company_tickers.json') for u in calls)==1
    assert {g['sic'] for g in result['by_industry']}=={'3571','6021'}
    assert not list(tmp_path.iterdir())
    assert '"value"' not in json.dumps(result)


def test_study_is_explicit_cached_and_blocked_outside_personal_mode(monkeypatch):
    from src.online_research_coverage import get_online_coverage_study
    calls=[]; state={}; options={'user_agent':'Research','tickers':['FICT','BANK'],'source_fetcher':_study_fetcher(calls),'observed_at':OBSERVED}
    assert get_online_coverage_study(state,refresh_requested=False,**options)['status']=='not_requested'
    assert not calls
    first=get_online_coverage_study(state,refresh_requested=True,**options)
    assert first['counts']['quarterly_revenue']==2
    cached=get_online_coverage_study(state,refresh_requested=False,**options)
    assert cached==first and len(calls)==5
    monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE','1')
    assert get_online_coverage_study(state,refresh_requested=False,**options)['status']=='unavailable'
    assert len(calls)==5


def test_invalid_sample_does_not_fetch_and_failure_remains_in_denominator():
    from src.online_research_coverage import run_online_coverage_study
    def no_fetch(*a): pytest.fail('invalid sample fetched')
    for tickers in [[],['FICT','FICT'],['BAD/URL'],['X'+str(i) for i in range(21)]]:
        assert run_online_coverage_study(tickers,user_agent='Research',source_fetcher=no_fetch)['status']=='unavailable'
    result=run_online_coverage_study(['FICT','BANK'],user_agent='Research',source_fetcher=lambda *a: (_ for _ in ()).throw(OSError('private diagnostic')))
    assert result['requested_count']==2 and result['source_failure_count']==2
    assert result['attempted_count']==2
    assert result['counts']['quarterly_revenue']==0
    assert 'private diagnostic' not in json.dumps(result)


def test_reduced_coverage_rows_require_their_exact_sec_receipts():
    from src.online_research_coverage import summarize_online_research_coverage,validated_coverage_summary
    result=summarize_online_research_coverage([_observation()],['FICT'])
    assert validated_coverage_summary(result) is not None
    result['rows'][0]['source_receipts'][0]['source_url']='https://example.invalid/pretend-sec'
    assert validated_coverage_summary(result) is None


def test_recent_sec_reporting_marker_does_not_count_old_supported_evidence_as_latest_coverage():
    from src.online_research_coverage import summarize_online_research_coverage
    obs=_observation()
    obs['profile'].update(latest_annual_period_end='2026-06-30',latest_quarterly_period_end='2026-09-30')
    result=summarize_online_research_coverage([obs],['FICT'])
    assert result['counts']['annual_revenue']==0 and result['counts']['quarterly_revenue']==0
    assert result['rows'][0]['annual_period']=='2026-06-30'
    assert result['rows'][0]['quarterly_period']=='2026-09-30'
    assert result['rows'][0]['annual_reason']=='latest_reported_annual_not_covered'


def test_old_industry_profile_is_not_joined_to_a_new_financial_observation():
    from src.online_research_coverage import summarize_online_research_coverage
    obs=_observation(); obs['profile']['observed_at']='2026-10-01T18:00:00Z'
    result=summarize_online_research_coverage([obs],['FICT'])
    assert result['unknown_industry_count']==1
    assert result['counts']['annual_revenue']==1
