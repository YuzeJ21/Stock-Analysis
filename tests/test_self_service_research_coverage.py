"""Constructed online responses exercise actual self-service adapters offline."""
from copy import deepcopy
from datetime import timedelta
import json
from urllib.error import HTTPError

import pytest

from test_online_peer_valuation import NOW, collection, classification, issuer, digest


@pytest.fixture(autouse=True)
def no_unconstructed_transport(monkeypatch):
    from src import self_service_research_coverage as coverage
    def blocked(*args,**kwargs):pytest.fail('Unexpected external source adapter')
    monkeypatch.setattr(coverage,'_fetch_raw',blocked)
    monkeypatch.setattr(coverage.peer_sources,'observe_vendor',blocked)
    monkeypatch.setattr(coverage.peer_sources,'observe_industry',blocked)


def dependencies():
    from test_sec_annual_history import _payload
    from test_sec_quarterly_history import _quarter_payload
    from test_online_peer_sources import source_dependencies
    from src.self_service_research_coverage import SAMPLE
    peer=collection(); symbols=['AMD','FA','FB','FC']
    peer['ticker']='AMD';peer['classification']=classification(symbols)
    peer['industry']['payload']['symbols']=symbols
    peer['industry']['normalized_sha256']=digest(peer['industry']['payload'])
    peer['issuers']=[issuer(t,str(1001+i).zfill(10),multiple)
        for i,(t,multiple) in enumerate(zip(symbols,[30,20,25,40]))]
    peers, calls=source_dependencies(peer)
    by_cik={str(1001+i).zfill(10):ticker for i,ticker in enumerate(SAMPLE)}
    def raw(url,agent):
        calls.append(('source',url))
        if url=='https://www.sec.gov/files/company_tickers.json':
            body={str(i):dict(ticker=t,cik_str=1001+i,title='Constructed '+t) for i,t in enumerate(SAMPLE)}
        else:
            cik=next((c for c in by_cik if 'CIK'+c in url),None)
            if cik is None: raise OSError('Unrequested constructed source')
            ticker=by_cik[cik]
            if '/companyfacts/' in url:
                body=_payload();q=_quarter_payload()
                for concept, fact in q['facts']['us-gaap'].items():
                    body['facts']['us-gaap'][concept]['units']['USD'] += fact['units']['USD']
                body['cik']=int(cik)
                for fact in body['facts']['us-gaap'].values():
                    for row in fact['units']['USD']:
                        row['accn']=row['accn'].replace('0000001234',cik)
                        if row['form']=='10-K':row['filed']='2026-02-01'
            else:
                rows=[dict(form='10-K',reportDate='2025-12-31',filingDate='2026-02-01',
                    accessionNumber=cik+'-26-000001',acceptanceDateTime='2026-02-01T12:00:00Z',primaryDocument='annual.htm')]
                rows += [dict(form='10-Q',reportDate=end,filingDate=filed,accessionNumber=cik+f'-25-00000{i+1}',
                    acceptanceDateTime=filed+'T12:00:00Z',primaryDocument='quarter.htm')
                    for i,(end,filed) in enumerate([('2025-03-31','2025-05-01'),('2025-06-30','2025-08-01'),('2025-09-30','2025-11-01')])]
                body=dict(cik=int(cik),name='Constructed '+ticker,tickers=[ticker],exchanges=['Nasdaq'],
                    sic='3674',entityType='operating',fiscalYearEnd='1231',filings={'recent':{k:[r[k] for r in rows] for k in rows[0]}})
        return json.dumps(body).encode(),{},url
    def prices(ticker,**kwargs):
        calls.append(('company_prices',ticker,kwargs.get('include_verified_session_close')))
        cik=next(c for c,t in by_cik.items() if t==ticker)
        result=issuer(ticker,cik,30)['prices']
        result['instrument_type']='EQUITY'
        return result
    return dict(source_fetcher=raw,prices=prices,peer_dependencies=peers),calls


def study(state,*,inspect=False,retry=None,reset=False,deps=None,now=NOW):
    from src.self_service_research_coverage import get_self_service_coverage
    return get_self_service_coverage(state,inspect_requested=inspect,retry_ticker=retry,
        reset_requested=reset,user_agent='Constructed research contact',dependencies=deps,as_of=now)


def test_frozen_denominators_and_initial_navigation_have_no_transport_or_store_writes(tmp_path,monkeypatch):
    from src.self_service_research_coverage import SAMPLE,SAMPLE_GROUPS,CAPABILITY_LABELS
    from src import online_research_context_store as store
    monkeypatch.setattr(store,'save_research_context',lambda *a,**k:pytest.fail('Read attempted a snapshot write'))
    deps,calls=dependencies();result=study({},deps=deps)
    assert SAMPLE==('AMD','NVDA','QCOM','JPM','BAC','C','DUK','SO','NEE','TSM','SAP','IBN')
    assert result['requested_count']==12 and result['attempted_count']==0 and result['pending_count']==12
    assert [g['requested_count'] for g in result['by_group']]==[3]*4
    assert result['counts']==dict.fromkeys(['attempted',*CAPABILITY_LABELS],0)
    assert all(row['status']=='unattempted' for row in result['rows'])
    assert not calls and result['market_universe_coverage_established'] is False


def test_explicit_next_uses_actual_tools_and_private_disposable_exact_replay_then_reads_offline(tmp_path,monkeypatch):
    from src import online_research_context_store as store
    roots=[];save=store.save_research_context
    def track(context,**kwargs):
        roots.append(kwargs['project_root'])
        assert context['notes'] is None
        return save(context,**kwargs)
    monkeypatch.setattr(store,'save_research_context',track)
    deps,calls=dependencies();state={'workbench-existing':{'ticker':'NVDA','notes':'user draft'}}
    result=study(state,inspect=True,deps=deps);row=result['rows'][0]
    assert result['attempted_count']==1 and result['pending_count']==11
    assert all(row['capabilities'][key]['status']=='available' for key in
        ('matched_identity','catalog','current_annual','direct_quarter','dated_price','peer_comparison','trend','scenario_eligibility','snapshot_replay'))
    assert row['snapshot_replay']['exact_context_match'] is True and row['snapshot_replay']['comparison_status']=='unchanged'
    assert len(row['peer_references'])==3 and row['peer_references'][0]['form']=='10-K'
    assert any(receipt.get('source')=='industry_reference_directory' for receipt in row['source_receipts'])
    assert roots and all(not root.exists() for root in roots)
    assert state['workbench-existing']=={'ticker':'NVDA','notes':'user draft'}
    assert ('company_prices','AMD',True) in calls
    monkeypatch.setattr('src.self_service_research_coverage._replay_probe',lambda *a,**k:pytest.fail('Read replayed the store'))
    before=list(calls);again=study(state,deps=deps)
    assert again==result and before==calls
    assert '"payload":' not in json.dumps(result)
    assert not any(key in json.dumps(result) for key in ['enterprise_value','projected_fcfs','"close":','"revenue":'])


def test_next_and_retry_replace_only_selected_attempt_and_preserve_classification_dedup():
    from src.self_service_research_coverage import SESSION_KEY
    deps,calls=dependencies();state={}
    study(state,inspect=True,deps=deps);result=study(state,inspect=True,deps=deps)
    assert result['attempted_count']==2
    assert len([c for c in calls if c[0]=='classification'])==1
    assert len(state[SESSION_KEY]['classifications'])==1
    def failed(*a,**k):return {'status':'unavailable','ticker':'AMD','reason':'source_component_unavailable'}
    bad={**deps,'financial':failed,'prices':failed,'peer_dependencies':{**deps['peer_dependencies'],'vendor':failed}}
    result=study(state,retry='AMD',deps=bad)
    assert result['attempted_count']==2 and result['pending_count']==10
    assert result['rows'][0]['capabilities']['matched_identity']['status']=='failed'
    assert result['rows'][1]['capabilities']['matched_identity']['status']=='available'


def test_expired_sources_are_recomputed_held_without_refresh_or_old_success():
    deps,calls=dependencies();state={};study(state,inspect=True,deps=deps)
    before=list(calls);result=study(state,deps=deps,now=NOW+timedelta(days=2))
    assert before==calls and result['attempted_count']==1 and result['counts']['current_annual']==0
    assert result['rows'][0]['capabilities']['matched_identity']['status']=='held'
    assert result['rows'][0]['capabilities']['peer_comparison']['status']=='held'


@pytest.mark.parametrize('code',[403,429,503])
def test_sec_access_limit_pauses_next_attempts_and_keeps_all_remaining_unattempted(code):
    deps,calls=dependencies();state={}
    def denied(url,agent):
        calls.append(('denied',url));raise HTTPError(url,code,'Constructed access limit',{'Retry-After':'60'},None)
    denied_deps={**deps,'source_fetcher':denied}
    result=study(state,inspect=True,deps=denied_deps)
    assert result['paused'] and result['source_access_limit']['http_status']==code
    assert result['attempted_count']==1 and result['pending_count']==11
    assert result['rows'][0]['status']=='failed'
    before=list(calls);assert study(state,inspect=True,deps=denied_deps)==result and calls==before
    retried=study(state,retry='AMD',deps=deps)
    assert not retried['paused'] and retried['rows'][0]['capabilities']['matched_identity']['status']=='available'


def test_explicit_reset_never_requests_sources_and_ordinary_read_never_resets_attempts():
    deps,calls=dependencies();state={};study(state,inspect=True,deps=deps);before=list(calls)
    result=study(state,reset=True,deps=deps)
    assert result['attempted_count']==0 and result['pending_count']==12 and calls==before
    assert study(state,deps=deps)==result and calls==before


def test_invalid_retry_or_changed_private_state_cannot_request_or_promote_source_flags():
    from src.self_service_research_coverage import SESSION_KEY
    deps,calls=dependencies();state={};study(state,inspect=True,deps=deps);before=list(calls)
    assert study(state,retry='UNKNOWN',deps=deps)['status']=='unavailable' and calls==before
    state[SESSION_KEY]['packets']['AMD']['financial']['ticker']='OTHER'
    result=study(state,deps=deps)
    assert result['status']=='unavailable' and result['counts']['current_annual']==0 and calls==before


@pytest.mark.parametrize('mode',['1','invalid'])
def test_mode_hold_precedes_all_source_and_saved_verdict_reuse(monkeypatch,mode):
    deps,calls=dependencies();state={};study(state,inspect=True,deps=deps);before=list(calls)
    monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE',mode)
    result=study(state,inspect=True,deps=deps)
    assert result['status']=='unavailable' and result['counts']['current_annual']==0 and calls==before
    assert result['requested_count']==12 and result['attempted_count']==1


def test_reduced_view_recomputes_all_denominators_and_counters_without_transport():
    from src.self_service_research_coverage import validated_coverage_view
    deps,calls=dependencies();state={};view=study(state,inspect=True,deps=deps);before=list(calls)
    changed=deepcopy(view);changed['counts']['current_annual']=999;changed['requested_count']=999
    changed['by_group'][0]['counts']['catalog']=999;changed['attempted_count']=999
    valid=validated_coverage_view(changed)
    assert valid['requested_count']==12 and valid['attempted_count']==1
    assert valid['counts']['current_annual']==1 and valid['by_group'][0]['counts']['catalog']==1
    assert before==calls
    changed['rows'][0]['ticker']='OUTSIDE'
    assert validated_coverage_view(changed) is None


def test_banks_are_method_exclusions_not_source_failure_counts():
    from src.self_service_research_coverage import SAMPLE
    deps,calls=dependencies();raw=deps['source_fetcher']
    def banking(url,agent):
        body,headers,final=raw(url,agent)
        if '/submissions/' in url:
            payload=json.loads(body);payload['sic']='6021';body=json.dumps(payload).encode()
        return body,headers,final
    deps={**deps,'source_fetcher':banking};state={}
    for _ in range(4):view=study(state,inspect=True,deps=deps)
    bank=view['rows'][3]
    assert bank['ticker']=='JPM' and bank['capabilities']['matched_identity']['status']=='available'
    assert bank['capabilities']['scenario_eligibility']['status']=='excluded'
    assert bank['capabilities']['catalog']['status']=='available'
    assert bank['capabilities']['current_annual']['status']=='available'


def test_catalog_remains_independent_when_companyfacts_fail_and_empty_context_cannot_prove_research_replay():
    deps,calls=dependencies();raw=deps['source_fetcher']
    def failed_facts(url,agent):
        if '/companyfacts/' in url:raise OSError('Constructed facts outage')
        return raw(url,agent)
    result=study({},inspect=True,deps={**deps,'source_fetcher':failed_facts})
    row=result['rows'][0]
    assert row['capabilities']['catalog']['status']=='available'
    assert row['capabilities']['matched_identity']['status']=='failed'
    assert row['capabilities']['snapshot_replay']['status']=='held'
    assert row['sec_cik']=='0000001001'


def test_default_dependencies_is_the_ui_seam_and_no_peer_source_callback_can_hide_sec_access_pause(monkeypatch):
    from src import self_service_research_coverage as coverage
    deps,calls=dependencies()
    def limited(url,**kwargs):raise HTTPError(url,429,'Constructed peer limit',{'Retry-After':'90'},None)
    deps['peer_dependencies']={**deps['peer_dependencies'],'sec':limited}
    defaults=coverage.default_dependencies();defaults.update(deps)
    monkeypatch.setattr(coverage,'default_dependencies',lambda:defaults)
    result=study({},inspect=True)
    assert result['paused'] and result['source_access_limit']['http_status']==429
    assert result['attempted_count']==1 and result['pending_count']==11


@pytest.mark.parametrize('bad',[None,[],42,{'companyfacts_identity':['bad'],'filing_inventory':['bad']}])
def test_malformed_independent_adapter_results_stay_held_and_keep_denominators(bad):
    deps,calls=dependencies()
    result=study({},inspect=True,deps={**deps,'financial':lambda *a,**k:deepcopy(bad),'prices':lambda *a,**k:deepcopy(bad)})
    assert result['requested_count']==12 and result['attempted_count']==1
    assert result['counts']['current_annual']==0 and result['counts']['snapshot_replay']==0
    json.dumps(result,allow_nan=False)


def test_missing_state_container_fails_closed_without_external_sources():
    from src.self_service_research_coverage import get_self_service_coverage
    result=get_self_service_coverage(None,inspect_requested=True,user_agent='Constructed',as_of=NOW)
    assert result['status']=='unavailable' and result['requested_count']==12


def test_replay_proof_is_hash_bound_and_tampering_never_reruns_or_recovers_success(monkeypatch):
    from src import self_service_research_coverage as coverage
    deps,calls=dependencies();state={};initial=study(state,inspect=True,deps=deps)
    assert initial['counts']['snapshot_replay']==1
    proof=state[coverage.SESSION_KEY]['packets']['AMD']['replay_proof']
    proof['context_sha256']='0'*64
    state[coverage.SESSION_KEY]['digest']=digest({k:v for k,v in state[coverage.SESSION_KEY].items() if k!='digest'})
    monkeypatch.setattr(coverage,'_replay_probe',lambda *a,**k:pytest.fail('Read attempted replay'))
    before=list(calls);result=study(state,deps=deps)
    assert calls==before and result['counts']['snapshot_replay']==0
    assert 'recheck' in result['rows'][0]['capabilities']['snapshot_replay']['reason']


def test_historical_trend_is_labelled_historical_when_new_financial_period_is_pending():
    from src.sec_annual_history import fetch_sec_online_research_view
    from test_online_research_tools import reseal_inventory
    deps,calls=dependencies()
    def pending(ticker,**kwargs):
        view=fetch_sec_online_research_view(ticker,**kwargs);view.pop('quarterly_history',None)
        inventory=view['filing_inventory'];inventory['periods']['quarterly']=[];inventory['latest']['quarterly']=None
        anchor=inventory['latest']['annual']
        new={**anchor,'period_end':'2026-06-30','report_date':'2026-06-30','filed':'2026-09-01',
            'accepted_at':'2026-09-01T12:00:00Z','accession':'0000001001-26-000002',
            'source_url':'https://www.sec.gov/Archives/edgar/data/1001/000000100126000002/annual.htm'}
        inventory['periods']['annual'].append(new);inventory['latest']['annual']=new
        view['filing_inventory']=reseal_inventory(inventory)
        return view
    row=study({},inspect=True,deps={**deps,'financial':pending})['rows'][0]
    assert row['capabilities']['current_annual']['status']=='held'
    assert row['capabilities']['trend']['status']=='available'
    assert row['capabilities']['trend']['reason']=='compatible_historical_metrics_only'
    assert row['capabilities']['scenario_eligibility']['status']=='held'


def test_oversized_explicit_retry_does_not_restore_previous_success_on_later_read(monkeypatch):
    from src import self_service_research_coverage as coverage
    deps,calls=dependencies();state={};assert study(state,inspect=True,deps=deps)['counts']['current_annual']==1
    limit=coverage.MAX_STATE_BYTES
    financial=coverage.fetch_sec_online_research_view
    def grows(ticker,**kwargs):
        result=financial(ticker,**kwargs)
        monkeypatch.setattr(coverage,'MAX_STATE_BYTES',20000)
        return result
    retried=study(state,retry='AMD',deps={**deps,'financial':grows})
    monkeypatch.setattr(coverage,'MAX_STATE_BYTES',limit)
    read=study(state,deps=deps)
    assert retried['counts']['current_annual']==0 and read['counts']['current_annual']==0


def test_default_dispatcher_preserves_exact_directory_transport_and_custom_override(monkeypatch):
    from src import self_service_research_coverage as coverage
    from src.us_listing_receipt_audit import _SOURCES
    calls=[]
    def directory(url,agent):calls.append(('directory',url,agent));return b'directory',{},url
    def sec(url,agent):calls.append(('sec',url,agent));return b'{}',{},url
    monkeypatch.setattr(coverage,'_fetch_directory',directory)
    monkeypatch.setattr(coverage,'_fetch_raw',sec)
    fetch=coverage.default_dependencies()['source_fetcher']
    for _,_,url,_ in _SOURCES:fetch(url,'Constructed agent')
    assert [row[0] for row in calls]==['directory']*len(_SOURCES)
    url=_SOURCES[0][2]+'?other=1';fetch(url,'Constructed agent')
    assert calls[-1][0]=='sec'
    fetch('https://www.sec.gov/files/company_tickers.json','Constructed agent')
    assert calls[-1][0]=='sec'
    deps,source_calls=dependencies();result=study({},inspect=True,deps=deps)
    assert result['attempted_count']==1 and source_calls
    assert len(calls)==len(_SOURCES)+2


@pytest.mark.parametrize('failure',['source_transport_unavailable','source_access_limited'])
def test_listing_transport_failure_is_failed_with_original_attempt_reason_not_method_unsupported(failure):
    from src.online_us_universe import SOURCE_URLS
    deps,calls=dependencies()
    blocked=dict(status='unavailable',reason='classification_source_unavailable',source_attempts=[
        dict(source_url=SOURCE_URLS[0],observed_at=NOW.isoformat(),status='unavailable',reason=failure)])
    deps['peer_dependencies']={**deps['peer_dependencies'],'classification':lambda **kwargs:deepcopy(blocked)}
    result=study({},inspect=True,deps=deps);row=result['rows'][0]
    assert row['capabilities']['peer_comparison']['status']=='failed'
    assert row['capabilities']['peer_comparison']['reason']=='listing_classification_unavailable'
    assert row['peer_source_attempts'][0]['reason']==failure
    assert result['capability_status_counts']['peer_comparison']['failed']==1


def test_oversized_research_context_is_an_explicit_size_hold_before_any_snapshot_save(monkeypatch):
    from src import online_research_context_store as store
    monkeypatch.setattr(store,'MAX_EXPANDED_SNAPSHOT_BYTES',1)
    monkeypatch.setattr(store,'save_research_context',lambda *a,**k:pytest.fail('Oversized context attempted a save'))
    deps,calls=dependencies();state={};result=study(state,inspect=True,deps=deps)
    row=result['rows'][0];proof=row['snapshot_replay']
    assert row['capabilities']['snapshot_replay']=={'status':'held','reason':'research_snapshot_size_limit'}
    assert proof['context_bytes']>proof['max_context_bytes']==1
    assert proof['limit_kind'] == 'expanded' and proof['max_stored_bytes'] == store.MAX_SNAPSHOT_BYTES
    assert proof['disposable_store'] is True and proof['user_store_written'] is False
    before=list(calls);again=study(state,deps=deps)
    assert calls==before and again['rows'][0]['snapshot_replay']==proof


def test_snapshot_store_size_failure_is_held_and_keeps_proof_on_read(monkeypatch):
    from src import online_research_context_store as store

    def size_failure(*args, **kwargs):
        raise store.ResearchSnapshotSizeError('Research snapshot size limit exceeded', limit_kind='stored')

    monkeypatch.setattr(store, 'save_research_context', size_failure)
    deps, calls = dependencies()
    state = {}
    result = study(state, inspect=True, deps=deps)
    row = result['rows'][0]
    proof = row['snapshot_replay']
    assert row['capabilities']['snapshot_replay'] == {'status': 'held', 'reason': 'research_snapshot_size_limit'}
    assert proof['limit_kind'] == 'stored' and proof['max_stored_bytes'] == store.MAX_SNAPSHOT_BYTES
    assert proof['context_bytes'] <= proof['max_context_bytes'] == store.MAX_EXPANDED_SNAPSHOT_BYTES
    assert proof['disposable_store'] is True and proof['user_store_written'] is False
    before = list(calls)
    assert study(state, deps=deps)['rows'][0]['snapshot_replay'] == proof
    assert calls == before


def test_oversized_peer_packet_preserves_independent_financial_catalog_and_price(monkeypatch):
    from src import self_service_research_coverage as coverage
    deps,calls=dependencies();state={};study(state,inspect=True,deps=deps)
    original=state[coverage.SESSION_KEY]['packets']['AMD']
    smaller=deepcopy(original);smaller['peer_packet']=None
    limit=(len(coverage._bytes(original))+len(coverage._bytes(smaller)))//2
    financial=coverage.fetch_sec_online_research_view
    def bounded(ticker,**kwargs):
        result=financial(ticker,**kwargs);monkeypatch.setattr(coverage,'MAX_PACKET_BYTES',limit)
        return result
    result=study(state,retry='AMD',deps={**deps,'financial':bounded});row=result['rows'][0]
    assert result['attempted_count']==1 and result['pending_count']==11
    assert all(row['capabilities'][key]['status']=='available' for key in
        ('matched_identity','catalog','current_annual','dated_price','trend','scenario_eligibility'))
    assert row['capabilities']['peer_comparison']=={'status':'held','reason':'peer_source_retention_size_limit'}
    packet=state[coverage.SESSION_KEY]['packets']['AMD']
    assert packet['financial']['companyfacts_identity']['status']=='source_matched'
    assert packet['peer_packet']['collection'] is None
    assert len(coverage._bytes(packet))<=limit
    before=list(calls);assert study(state,deps=deps)==result and calls==before
