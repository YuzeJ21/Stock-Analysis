from copy import deepcopy
from datetime import timedelta

import pytest

from test_online_peer_valuation import collection, NOW, SYMBOLS, digest
from test_online_peer_sources import source_dependencies


def dependencies():
    c=collection();c['industry']['payload']['symbols']=list(SYMBOLS)
    c['industry']['normalized_sha256']=digest(c['industry']['payload'])
    deps,calls=source_dependencies(c)
    from src.online_peer_sec_history import fetch_vendor_history_match
    def history(*args,**kwargs):
        calls.append(('history',args[0]));return fetch_vendor_history_match(*args,**kwargs)
    deps['history']=history
    return deps,calls


def audit(state,*,inspect=False,retry=None,reset=False,tickers=SYMBOLS,as_of=NOW,deps=None,mode='research'):
    from src.online_peer_coverage import get_peer_coverage
    return get_peer_coverage(state,inspect_requested=inspect,retry_ticker=retry,reset_requested=reset,
        tickers=tickers,as_of=as_of,dependencies=deps,workspace_mode=mode,user_agent='Synthetic contact')


def test_initial_read_retains_full_requested_denominator_without_requests():
    d,calls=dependencies();state={};result=audit(state,deps=d)
    assert not calls and result['requested_count']==4 and result['attempted_count']==0
    assert result['pending_count']==4 and len(result['rows'])==4
    assert result['subject_pe_count']==0 and result['comparison_count']==0
    assert result['market_universe_coverage_established'] is False and result['session_only'] is True


def test_one_explicit_operation_inspects_one_company_then_reads_only_revalidate():
    d,calls=dependencies();state={};result=audit(state,inspect=True,deps=d)
    assert result['attempted_count']==1 and result['pending_count']==3
    assert result['subject_pe_count']==1 and result['comparison_count']==1
    assert result['reference_assessed_count']==1 and result['adapter_operation_count']==len(calls)
    before=list(calls);again=audit(state,deps=d)
    assert again==result and calls==before
    second=audit(state,inspect=True,deps=d)
    assert second['attempted_count']==2 and second['rows'][1]['ticker']=='FA'
    assert second['comparison_count']==2 and second['pending_count']==2


def test_blocked_subject_is_not_zero_peers_and_keeps_independently_bound_industry():
    c=collection();c['issuers'][0]['facts']['payload']['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]['val']=-1
    d,calls=source_dependencies(c);result=audit({},inspect=True,deps=d)
    row=result['rows'][0]
    assert row['subject_pe_state']=='withheld' and row['reference_state']=='not_assessed_subject_blocked'
    assert row['accepted_reference_count'] is None and result['reference_assessed_count']==0
    assert row['industry_key']=='semiconductors' and row['sic']=='3674'
    assert result['by_industry'][0]['requested_count']==1
    assert result['primary_reason_counts']['annual_eps_nonpositive_or_invalid']==1
    assert [x[1] for x in calls if x[0]=='vendor']==['FICT']


def test_failure_pending_and_unknown_industry_stay_in_all_counts():
    d,calls=dependencies();state={};audit(state,inspect=True,deps=d)
    d['vendor']=lambda *a,**kw:dict(status='unavailable')
    result=audit(state,inspect=True,deps=d)
    assert result['requested_count']==4 and result['attempted_count']==2 and result['pending_count']==2
    assert result['subject_pe_count']==1 and result['comparison_count']==1
    assert sum(g['requested_count'] for g in result['by_industry'])==4
    unknown=next(g for g in result['by_industry'] if g['industry_key'] is None)
    assert unknown['requested_count']==3
    assert result['rows'][1]['primary_reason']=='vendor_context_source_unavailable'


def test_two_subject_source_failures_pause_without_dropping_pending_and_retry_is_explicit():
    d,calls=dependencies();d['vendor']=lambda *a,**kw:dict(status='unavailable');state={}
    audit(state,inspect=True,deps=d);result=audit(state,inspect=True,deps=d)
    assert result['paused'] is True and result['attempted_count']==2 and result['pending_count']==2
    before=list(calls);assert audit(state,inspect=True,deps=d)==result and calls==before
    good,_=dependencies();retried=audit(state,retry='FA',deps=good)
    assert retried['attempted_count']==2 and retried['paused'] is False and retried['comparison_count']==1
    continued=audit(state,inspect=True,deps=good)
    assert continued['attempted_count']==3 and continued['rows'][2]['subject_pe_state']=='available'


def test_failed_explicit_retry_replaces_that_company_success_and_keeps_other_packets():
    d,calls=dependencies();state={};audit(state,inspect=True,deps=d);audit(state,inspect=True,deps=d)
    d['vendor']=lambda *a,**kw:dict(status='unavailable')
    result=audit(state,retry='FICT',deps=d)
    assert result['comparison_count']==1 and result['rows'][0]['comparison_state']=='withheld'
    assert result['rows'][1]['comparison_state']=='available' and result['pending_count']==2


def test_expired_packets_are_revalidated_withheld_without_transport_or_false_industry():
    d,calls=dependencies();state={};audit(state,inspect=True,deps=d);before=list(calls)
    result=audit(state,deps=d,as_of=NOW+timedelta(days=2))
    assert calls==before and result['attempted_count']==1 and result['comparison_count']==0
    assert result['rows'][0]['industry_key'] is None and result['rows'][0]['accepted_reference_count'] is None


@pytest.mark.parametrize('change',['state_seal','packet_seal','raw_vendor','method','counts'])
def test_tampered_state_or_source_cannot_promote_an_old_verdict(monkeypatch,change):
    from src.online_peer_coverage import SESSION_KEY
    d,calls=dependencies();state={};audit(state,inspect=True,deps=d);packet=state[SESSION_KEY]
    if change=='state_seal':packet['digest']='0'*64
    elif change=='method':packet['method_version']='unsupported'
    elif change=='counts':packet['comparison_count']=999
    else:
        raw=packet['packets']['FICT']
        if change=='packet_seal':raw['packet_digest']='0'*64
        else:raw['collection']['issuers'][0]['vendor']['payload']['info']['regularMarketPrice']=1
        packet['digest']=digest({k:v for k,v in packet.items() if k!='digest'})
    before=list(calls);result=audit(state,deps=d)
    assert calls==before and result.get('comparison_count',0)==0


def test_changed_sample_requires_explicit_reset_and_retry_never_adds_unknown_ticker():
    d,calls=dependencies();state={};audit(state,inspect=True,deps=d);before=list(calls)
    assert audit(state,inspect=True,tickers=['FA'],deps=d)['status']=='unavailable' and calls==before
    assert audit(state,retry='OTHER',deps=d)['status']=='unavailable' and calls==before
    cleared=audit(state,reset=True,tickers=['FA'],deps=d)
    assert cleared['requested_count']==1 and cleared['attempted_count']==0 and calls==before


@pytest.mark.parametrize('values',[[],['A']*2,['A.B','A-B'],['A']*21,['bad value'],None])
def test_invalid_or_duplicate_alias_samples_do_not_request_sources(values):
    d,calls=dependencies();assert audit({},inspect=True,tickers=values,deps=d)['status']=='unavailable'
    assert not calls


@pytest.mark.parametrize('mode,commercial',[('public',None),('operator',None),('research','1'),('research','invalid')])
def test_mode_guards_precede_network_and_cached_reuse(monkeypatch,mode,commercial):
    d,calls=dependencies();state={};audit(state,inspect=True,deps=d);before=list(calls)
    if commercial:monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE',commercial)
    result=audit(state,inspect=True,deps=d,mode=mode)
    assert result['status']=='unavailable' and calls==before


def test_partial_reference_pause_is_not_completed_assessment_or_zero_reference_failure():
    d,calls=dependencies();base=d['vendor']
    d['vendor']=lambda ticker,**kw:base(ticker,**kw) if ticker=='FICT' else dict(status='unavailable')
    result=audit({},inspect=True,deps=d);row=result['rows'][0]
    assert row['subject_pe_state']=='available' and row['reference_state']=='partially_assessed'
    assert row['accepted_reference_count']==0 and result['reference_assessed_count']==0
    assert result['excluded_reason_counts']['source_paused_after_repeated_failures']==1


def test_profile_and_vendor_attribution_conflicts_do_not_get_a_verified_industry_group():
    c=collection();c['issuers'][0]['profile']['payload']['cik']=9999
    d,calls=source_dependencies(c);result=audit({},inspect=True,deps=d)
    assert result['rows'][0]['industry_key'] is None and result['rows'][0]['sic'] is None


def test_local_audit_never_reads_or_writes_financial_checkpoint(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path);d,calls=dependencies();audit({},inspect=True,deps=d)
    assert list(tmp_path.iterdir())==[]


def test_shared_classification_receipt_is_stored_once_and_reused_without_relabelling_time():
    from src.online_peer_coverage import SESSION_KEY
    d,calls=dependencies();state={};audit(state,inspect=True,deps=d);audit(state,inspect=True,deps=d)
    saved=state[SESSION_KEY]
    assert len(saved['classifications'])==1
    assert len([c for c in calls if c[0]=='classification'])==1
    for packet in saved['packets'].values():
        assert 'classification' not in packet['collection']
        assert packet['collection']['classification_ref'] in saved['classifications']
    assert audit(state,deps=d)['comparison_count']==2


def test_shared_classification_uses_newest_valid_source_cut_not_insertion_order():
    from src.online_peer_coverage import _recent_classification
    from test_online_peer_valuation import classification
    earlier=classification();later=classification(observed_at=NOW+timedelta(minutes=5))
    state={'classifications':{'later':later,'earlier':earlier}}
    chosen=_recent_classification(state,NOW+timedelta(minutes=6))
    assert chosen['inventory']['observed_from']=='2026-11-01T04:05:00Z'


def test_changed_shared_evidence_cannot_be_promoted_even_with_a_resealed_outer_state():
    from src.online_peer_coverage import SESSION_KEY
    d,calls=dependencies();state={};audit(state,inspect=True,deps=d)
    saved=state[SESSION_KEY];shared=next(iter(saved['classifications'].values()))
    shared['inventory']['source_receipts'][0]['observed_at']='2026-11-02T00:00:00Z'
    saved['digest']=digest({k:v for k,v in saved.items() if k!='digest'})
    before=list(calls)
    assert audit(state,deps=d)['status']=='unavailable' and calls==before


def test_explicit_retry_drops_an_unreferenced_old_classification_receipt():
    from src.online_peer_coverage import SESSION_KEY
    from test_online_peer_valuation import classification
    d,calls=dependencies();state={};audit(state,inspect=True,deps=d)
    later=NOW+timedelta(days=2)
    d['classification']=lambda **kwargs:classification(observed_at=later)
    audit(state,retry='FICT',deps=d,as_of=later)
    assert len(state[SESSION_KEY]['classifications'])==1


@pytest.mark.parametrize('failure',['unavailable','exception'])
def test_two_subject_price_access_failures_pause_and_third_next_makes_no_calls(failure):
    d,calls=dependencies()
    def prices(ticker,**kwargs):
        calls.append(('price_failure',ticker))
        if failure=='exception':raise OSError('private transport error')
        return dict(status='unavailable',reason='price_source_unavailable')
    d['prices']=prices;state={}
    first=audit(state,inspect=True,deps=d);second=audit(state,inspect=True,deps=d)
    assert first['rows'][0]['subject_source_failure'] is True
    assert second['attempted_count']==2 and second['paused'] is True
    before=list(calls);third=audit(state,inspect=True,deps=d)
    assert third==second and calls==before and third['pending_count']==2


def test_unsupported_price_definition_is_a_gap_without_a_false_source_access_pause():
    d,calls=dependencies();d['prices']=lambda *a,**kw:dict(status='unavailable',reason='unsupported_price_currency')
    state={};audit(state,inspect=True,deps=d);second=audit(state,inspect=True,deps=d)
    assert second['paused'] is False and second['rows'][0]['subject_source_failure'] is False


@pytest.mark.parametrize('action',['next','retry'])
def test_malformed_but_resealed_shared_receipt_returns_a_stable_gap_on_actions(action):
    from src.online_peer_coverage import SESSION_KEY
    d,calls=dependencies();state={};audit(state,inspect=True,deps=d);saved=state[SESSION_KEY]
    oldkey=next(iter(saved['classifications']));bad={'inventory':None};newkey=digest(bad)
    saved['classifications']={newkey:bad}
    for packet in saved['packets'].values():packet['collection']['classification_ref']=newkey
    saved['digest']=digest({k:v for k,v in saved.items() if k!='digest'})
    before=list(calls)
    result=audit(state,inspect=action=='next',retry='FICT' if action=='retry' else None,deps=d)
    assert result['status']=='unavailable' and calls==before


def test_selected_sample_detail_revalidates_without_fetch_or_state_mutation():
    from src.online_peer_coverage import get_peer_coverage

    deps, calls = dependencies()
    state = {}
    audit(state, inspect=True, deps=deps)
    before = deepcopy(state)
    requests = list(calls)

    def detail(ticker, as_of=NOW):
        return get_peer_coverage(
            state, tickers=SYMBOLS, as_of=as_of, dependencies=deps, detail_ticker=ticker
        ).get("selected_detail")

    assert detail("FA") is None
    assert detail("OTHER") is None
    current = detail("FICT")
    assert current["status"] == "research_comparison"
    assert current["ticker"] == "FICT"
    assert current["peer_count"] == 3
    expired = detail("FICT", NOW + timedelta(days=2))
    assert expired["status"] == "withheld"
    assert expired["peer_median"] is None
    assert state == before and calls == requests
