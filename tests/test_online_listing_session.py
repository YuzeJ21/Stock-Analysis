"""Synthetic listing recovery; no network, disk source cache or market claims."""
from copy import deepcopy
from datetime import timedelta
import pytest

from test_online_peer_valuation import NOW, classification
from test_online_peer_sources import source_dependencies, get


def unavailable():
    return {'status':'withheld','reason':'classification_source_unavailable'}


def test_recent_session_receipt_recovers_without_renewing_dates_or_digests():
    from src.online_listing_session import acquire_classification
    state={};original=classification();before=deepcopy(original)
    first,context=acquire_classification(state,lambda:original,as_of=NOW)
    recovered,context=acquire_classification(state,unavailable,as_of=NOW+timedelta(hours=1))
    assert recovered==before==first and original==before
    assert context['selection']=='recent_session' and context['attempt_status']=='unavailable'
    assert context['attempted_at']=='2026-11-01T05:00:00Z'
    assert context['observed_from']==context['observed_to']=='2026-11-01T04:00:00Z'
    assert context['source_receipts']==before['inventory']['source_receipts']


@pytest.mark.parametrize('hours,want',[(24,True),(24.000001,False),(-.01,False)])
def test_all_original_receipts_must_stay_inside_the_24_hour_window(hours,want):
    from src.online_listing_session import acquire_classification
    state={};acquire_classification(state,classification,as_of=NOW)
    result,_=acquire_classification(state,unavailable,as_of=NOW+timedelta(hours=hours))
    assert (result is not None)==want


def test_directory_creation_age_is_independent_of_receipt_observation_age():
    from src.online_listing_session import fresh_classification
    # Synthetic directory creation is Oct 30 15:41 New York = 19:41 UTC.
    cutoff=NOW.replace(day=6,hour=19,minute=41)
    packet=classification(observed_at=cutoff)
    assert fresh_classification(packet,cutoff) is not None
    assert fresh_classification(packet,cutoff+timedelta(microseconds=1)) is None


@pytest.mark.parametrize('change',['payload','seal','successful_invalid','access_limit'])
def test_invalid_or_untrusted_acquisition_cannot_recover(change):
    from src.online_listing_session import acquire_classification, SESSION_KEY
    state={};acquire_classification(state,classification,as_of=NOW)
    fetch=unavailable
    if change=='payload':state[SESSION_KEY]['classification']['rows'][0]['security_type']='debt'
    elif change=='seal':state[SESSION_KEY]['digest']='0'*64
    elif change=='successful_invalid':fetch=lambda:{'status':'inspection_only','rows':[]}
    else:fetch=lambda:{**unavailable(),'source_attempts':[{'source_url':'https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt','status':'unavailable','reason':'source_access_limited','observed_at':'2026-11-01T04:00:00Z'}]}
    result,context=acquire_classification(state,fetch,as_of=NOW)
    assert result is None and context['selection']=='none'


def test_live_success_replaces_last_good_without_sharing_mutable_input():
    from src.online_listing_session import acquire_classification
    state={};first=classification();acquire_classification(state,lambda:first,as_of=NOW)
    newer=classification(observed_at=NOW+timedelta(minutes=5))
    acquire_classification(state,lambda:newer,as_of=NOW+timedelta(minutes=5))
    newer['rows'].clear()
    result,_=acquire_classification(state,unavailable,as_of=NOW+timedelta(minutes=6))
    assert result['inventory']['observed_from']=='2026-11-01T04:05:00Z' and result['rows']


def test_mode_guard_prevents_both_acquisition_and_recent_reuse(monkeypatch):
    from src.online_listing_session import acquire_classification
    state={};acquire_classification(state,classification,as_of=NOW)
    monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE','1')
    def forbidden():raise AssertionError('transport was reached')
    assert acquire_classification(state,forbidden,as_of=NOW)[0] is None


def test_recovery_collects_new_financials_and_withdraws_old_verdict_on_failure():
    deps,calls=source_dependencies();state={}
    assert get(state,refresh=True,dependencies=deps)['subject']['multiple']==30
    deps['classification']=lambda **kw:unavailable()
    previous=len(calls)
    view=get(state,refresh=True,dependencies=deps)
    assert view['subject']['multiple']==30 and len(calls)>previous
    assert view['listing_context']['selection']=='recent_session'
    deps['vendor']=lambda *a,**kw:(_ for _ in ()).throw(OSError('private failure'))
    failed=get(state,refresh=True,dependencies=deps)
    assert failed['subject'] is None and failed['premium_fraction'] is None
    assert failed['listing_context']['selection']=='recent_session'
    assert 'private failure' not in str(failed)


def test_recovered_receipt_does_not_bypass_expected_company_identity():
    deps,calls=source_dependencies();state={};get(state,refresh=True,dependencies=deps)
    deps['classification']=lambda **kw:unavailable();before=list(calls)
    view=get(state,refresh=True,dependencies=deps,expected_cik='0000099999')
    assert view['subject'] is None and calls==before


def test_empty_directory_keeps_safe_source_specific_diagnostic_and_no_retry():
    from src.security_classification import fetch_classification
    from test_online_us_universe import O_URL
    from test_security_classification import fixture_fetch,OBSERVED
    calls=[];base=fixture_fetch(calls)
    def fetch(url,agent):
        if url==O_URL:
            calls.append(url)
            return (b'ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol\nFile Creation Time: 1030202615:41|||||||\n',{},url)
        return base(url,agent)
    result=fetch_classification(user_agent='Synthetic contact',fetcher=fetch,observed_at=OBSERVED)
    assert result['status']=='withheld' and calls.count(O_URL)==1
    failed=result['source_attempts'][-1]
    assert failed['source_url']==O_URL and failed['reason']=='directory_incomplete'
    assert failed['byte_count']==130 and len(failed['payload_sha256'])==64


def test_no_prior_receipt_holds_without_financial_transport():
    deps,calls=source_dependencies();deps['classification']=lambda **kw:unavailable()
    result=get({},refresh=True,dependencies=deps)
    assert result['subject'] is None and result['listing_context']['selection']=='none' and not calls


def test_invalid_observation_is_held_without_raising_or_transport():
    deps,calls=source_dependencies()
    result=get({},refresh=True,dependencies=deps,as_of='invalid')
    assert result['subject'] is None and not calls


def test_stale_directory_has_a_separate_safe_date_diagnostic():
    from src.security_classification import fetch_classification
    from test_security_classification import fixture_fetch,OBSERVED
    result=fetch_classification(user_agent='Synthetic contact',fetcher=fixture_fetch([]),observed_at=OBSERVED+timedelta(days=8))
    assert result['status']=='withheld'
    assert result['source_attempts'][-1]['reason']=='directory_date_invalid'


@pytest.mark.parametrize('kind',['transport','redirect','access_limit'])
def test_failed_acquisition_never_leaks_exception_or_headers_or_retries(kind):
    from urllib.error import HTTPError
    from src.security_classification import fetch_classification
    from test_security_classification import OBSERVED
    calls=[]
    def fetch(url,agent):
        calls.append(url)
        if kind=='transport':raise OSError('PRIVATE-CREDENTIAL')
        if kind=='access_limit':raise HTTPError(url,429,'PRIVATE-CREDENTIAL',{'Set-Cookie':'PRIVATE-CREDENTIAL'},None)
        return b'PRIVATE-CREDENTIAL',{},'https://example.test/redirect'
    result=fetch_classification(user_agent='Synthetic contact',fetcher=fetch,observed_at=OBSERVED)
    assert result['status']=='withheld' and len(calls)==1
    assert 'PRIVATE-CREDENTIAL' not in str(result)
    assert result['source_attempts'][0]['reason']=={'transport':'source_transport_unavailable','redirect':'source_response_unverified','access_limit':'source_access_limited'}[kind]
