from copy import deepcopy
from datetime import timedelta

import pytest

from test_online_peer_valuation import collection, NOW, digest


def source_dependencies(c=None):
    c=deepcopy(collection() if c is None else c); calls=[]
    rows={r['ticker']:r for r in c['issuers']}
    def classification(**kwargs):calls.append(('classification',));return deepcopy(c['classification'])
    def vendor(ticker,**kwargs):calls.append(('vendor',ticker));return deepcopy(rows[ticker]['vendor'])
    def industry(key,sector,**kwargs):calls.append(('industry',key,sector));return deepcopy(c['industry'])
    def sec(url,**kwargs):
        calls.append(('sec',url))
        for r in rows.values():
            for key in ('profile','facts'):
                if r[key]['source_url']==url:return deepcopy(r[key])
        raise OSError('Synthetic source unavailable')
    def prices(ticker,**kwargs):calls.append(('prices',ticker));return deepcopy(rows[ticker]['prices'])
    return dict(classification=classification,vendor=vendor,industry=industry,sec=sec,prices=prices),calls


def get(state,*,refresh=False,dependencies=None,as_of=NOW,ticker='FICT',expected_cik=None):
    from src.online_peer_sources import get_online_peer_valuation
    return get_online_peer_valuation(ticker,state,refresh_requested=refresh,expected_cik=expected_cik,
                                    user_agent='Synthetic contact',dependencies=dependencies,as_of=as_of)


def test_ordinary_read_never_requests_a_source_and_success_reuses_the_same_evidence():
    d,calls=source_dependencies();state={}
    assert get(state,dependencies=d)['status']=='not_requested' and not calls
    v=get(state,refresh=True,dependencies=d);assert v['status']=='research_comparison'
    before=list(calls);again=get(state,dependencies=d)
    assert again==v and calls==before and len([c for c in calls if c[0]=='vendor'])==4


def test_so_cofiling_sources_are_needed_only_when_the_normal_vendor_match_fails():
    from src.online_peer_sec_cofiling import FILING, PARENT_CIK, VENDOR_EXHIBIT, VENDOR_LINK
    from src.online_peer_sources import _collect_issuer
    from test_online_peer_valuation import issuer, rehash_vendor

    row = issuer('SO', PARENT_CIK, 30)
    normal, = row['vendor']['payload']['filings']
    cofiling = dict(type='10-Q', date=FILING['filingDate'], edgarUrl=VENDOR_LINK, exhibits={'10-Q': VENDOR_EXHIBIT})
    row['vendor']['payload']['filings'].append(cofiling)
    rehash_vendor(row)
    deps, calls = source_dependencies({'issuers': [row]})

    def capture(*args, **kwargs):
        calls.append(('cofiling',))
        return {'status': 'not_applicable'}

    deps.update(history=lambda *args, **kwargs: {'status': 'not_applicable'},
                security=lambda *args, **kwargs: {'status': 'not_applicable'}, cofiling=capture)
    _collect_issuer('SO', PARENT_CIK, deps, 'Synthetic contact', NOW, row['vendor'])
    assert ('cofiling',) not in calls

    row['vendor']['payload']['filings'].remove(normal)
    rehash_vendor(row)
    _collect_issuer('SO', PARENT_CIK, deps, 'Synthetic contact', NOW, row['vendor'])
    assert calls.count(('cofiling',)) == 1


def test_explicit_failed_retry_replaces_success_instead_of_showing_an_old_verdict():
    d,calls=source_dependencies();state={}
    assert get(state,refresh=True,dependencies=d)['status']=='research_comparison'
    d['vendor']=lambda *a,**kw: (_ for _ in ()).throw(OSError('private diagnostic must not leak'))
    v=get(state,refresh=True,dependencies=d)
    assert v['status']=='withheld' and v['premium_fraction'] is None
    assert 'private diagnostic' not in str(v)
    assert get(state,dependencies=d)==v


def test_source_failure_during_peer_collection_is_counted_and_not_fabricated():
    d,calls=source_dependencies();state={};original=d['prices']
    def fail(ticker,**kwargs):
        if ticker=='FA':raise OSError('private source detail')
        return original(ticker,**kwargs)
    d['prices']=fail
    v=get(state,refresh=True,dependencies=d)
    assert v['peer_count']==2 and v['peer_median'] is None
    assert v['excluded'][0]['ticker']=='FA' and 'private source detail' not in str(v)
    diagnostic=v['excluded'][0]['diagnostics']
    assert diagnostic['annual_eps_observation']['eps']==1.0
    assert diagnostic['price_source_status']=='unavailable'


@pytest.mark.parametrize('change',['ticker','expected_cik','time','payload','seal'])
def test_cache_is_ticker_and_cik_scoped_and_revalidated_without_transport(change):
    from src.online_peer_sources import SESSION_KEY
    d,calls=source_dependencies();state={};get(state,refresh=True,dependencies=d);before=list(calls)
    options={}
    if change=='ticker':options['ticker']='OTHER'
    elif change=='expected_cik':options['expected_cik']='0000099999'
    elif change=='time':options['as_of']=NOW+timedelta(days=2)
    elif change=='payload':state[SESSION_KEY]['collection']['issuers'][0]['vendor']['payload']['info']['regularMarketPrice']=1
    else:state[SESSION_KEY]['packet_digest']='0'*64
    v=get(state,dependencies=d,**options)
    assert v['status'] in {'not_requested','withheld'} and v['premium_fraction'] is None and calls==before


@pytest.mark.parametrize('mode',['1','invalid'])
def test_mode_guard_precedes_all_requests_and_prevents_cached_reuse(monkeypatch,mode):
    d,calls=source_dependencies();state={};get(state,refresh=True,dependencies=d);before=list(calls)
    monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE',mode)
    assert get(state,refresh=True,dependencies=d)['status']=='withheld'
    assert get(state,dependencies=d)['status']=='withheld' and calls==before


def test_route_identity_conflict_stops_before_vendor_or_price_transport():
    d,calls=source_dependencies();v=get({},refresh=True,expected_cik='0000099999',dependencies=d)
    assert v['status']=='withheld' and not any(c[0] in {'vendor','prices'} for c in calls)


def test_at_most_twelve_other_candidates_are_attempted_and_unknowns_are_retained():
    c=collection();payload=c['industry']['payload'];payload['symbols']=[f'ZZ{i}' for i in range(20)]
    c['industry']['normalized_sha256']=digest(payload)
    d,calls=source_dependencies(c);v=get({},refresh=True,dependencies=d)
    assert v['candidate_count']==12 and v['industry_candidate_total']==20
    assert len(v['excluded'])==12 and all(r['reason'] for r in v['excluded'])
    assert [x[1] for x in calls if x[0]=='vendor']==['FICT']


def test_two_consecutive_source_failures_pause_remaining_requests():
    d,calls=source_dependencies();original=d['vendor'];attempts=[]
    def vendor(ticker,**kwargs):
        attempts.append(ticker)
        if ticker!='FICT':raise OSError('private failure')
        return original(ticker,**kwargs)
    d['vendor']=vendor
    v=get({},refresh=True,dependencies=d)
    assert attempts==['FICT','FA','FB'] and len(v['excluded'])==3
    assert v['excluded'][-1]['reason']=='source_paused_after_repeated_failures'


def test_sdk_normalization_distinguishes_normalized_digest_from_raw_http_evidence():
    from src.online_peer_sources import observe_vendor
    from test_online_peer_valuation import issuer
    from datetime import date
    raw=issuer('FICT','0000001001',30)['vendor']['payload']
    raw['filings'][0]['date']=date(2026,2,1)
    class Ticker:
        def get_info(self):return raw['info']
        def get_sec_filings(self):return raw['filings']
    class SDK:
        @staticmethod
        def Ticker(ticker):return Ticker()
    v=observe_vendor('FICT',sdk=SDK,observed_at=NOW)
    assert v['status']=='observed' and 'payload_sha256' not in v
    assert v['payload']['filings'][0]['date']=='2026-02-01'
    assert v['normalized_sha256']==digest(v['payload'])


def test_missing_sdk_capability_is_an_explicit_gap():
    from src.online_peer_sources import observe_vendor,observe_industry
    assert observe_vendor('FICT',sdk=object(),observed_at=NOW)['status']=='unavailable'
    assert observe_industry('semiconductors','technology',sdk=object(),observed_at=NOW)['status']=='unavailable'


def test_industry_adapter_retains_provider_order_without_turning_it_into_a_ranking():
    from src.online_peer_sources import observe_industry
    import pandas as pd
    class Industry:
        sector_key='technology'
        top_companies=pd.DataFrame({'name':['Synthetic B','Synthetic A']},index=['FB','FA'])
        def __init__(self,key):assert key=='semiconductors'
    class SDK:pass
    SDK.Industry=Industry
    v=observe_industry('semiconductors','technology',sdk=SDK,observed_at=NOW)
    assert v['status']=='observed' and v['payload']['symbols']==['FB','FA']
    assert v['normalized_sha256']==digest(v['payload']) and 'ranking' not in v


def test_collector_retains_raw_sec_digest_and_binds_its_reduced_payload():
    from src.online_peer_sources import SESSION_KEY
    d,calls=source_dependencies();state={};v=get(state,refresh=True,dependencies=d)
    assert v['status']=='research_comparison'
    source=state[SESSION_KEY]['collection']['issuers'][0]['facts']
    assert source['payload_sha256'] and source['normalized_sha256']==digest(source['payload'])
    source['payload']['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]['val']=100
    cache=state[SESSION_KEY];cache['packet_digest']=digest({k:v for k,v in cache.items() if k!='packet_digest'})
    assert get(state,dependencies=d)['status']=='withheld'
