"""Failure-inclusive session sample, distinct from financial-universe coverage."""
from collections import Counter, defaultdict
from collections.abc import Mapping
from copy import deepcopy
from datetime import timedelta

from src import online_peer_sources as sources
from src.online_company_identity import _mode_reason
from src.online_peer_valuation import normalized_digest, _symbol
from src.company_sec_online_preview import _utc_timestamp
from src.security_classification import validated_classification

SESSION_KEY='online_peer_coverage_session_v1'
DISCOVER_SESSION_KEY='online_peer_coverage_discover_v1'
SCHEMA='online-peer-coverage-v1'
METHOD='reported-annual-pe-selected-security-v1'
DEFAULT_SAMPLE=('AMD','TXN','QCOM','MSFT','JPM','JNJ','XOM','PG','MCD','CAT','NEM','DUK','O','VZ','TSM')
REPRESENTATIVE_GROUPS=(
    ('半导体', ('AMD', 'TXN', 'QCOM')),
    ('银行', ('JPM', 'BAC', 'WFC')),
    ('公用事业', ('DUK', 'SO', 'NEE')),
)
_PRIORITY_SAMPLE=tuple(
    ticker for rank in zip(*(members for _, members in REPRESENTATIVE_GROUPS)) for ticker in rank
)
DISCOVER_SAMPLE=(*_PRIORITY_SAMPLE, *(ticker for ticker in DEFAULT_SAMPLE if ticker not in _PRIORITY_SAMPLE))
_SOURCE_FAILURES={'vendor_context_source_unavailable','industry_candidate_source_unavailable','listing_classification_unavailable',
    'issuer_source_unavailable','sec_source_unavailable_or_mismatched','peer_source_unavailable','amendment_source_unavailable'}
_STATE_KEYS={'schema_version','method_version','requested_tickers','packets','classifications','adapter_operation_count','source_failure_streak','digest'}


def _targets(value):
    if isinstance(value,str):value=value.split(',')
    if not isinstance(value,(list,tuple)) or not 1<=len(value)<=20 or any(not isinstance(v,str) for v in value):return None
    tickers=[v.strip().upper() for v in value]
    if not all(_symbol(t) for t in tickers) or len({t.replace('.','-') for t in tickers})!=len(tickers):return None
    return tickers


def _seal(state):
    state['digest']=normalized_digest({k:v for k,v in state.items() if k!='digest'})
    return state


def _new(requested):
    return _seal(dict(schema_version=SCHEMA,method_version=METHOD,requested_tickers=requested,
        packets={},classifications={},adapter_operation_count=0,source_failure_streak=0))


def _valid(state,requested):
    try:
        return (isinstance(state,Mapping) and set(state)==_STATE_KEYS and state.get('schema_version')==SCHEMA
            and state.get('method_version')==METHOD and state.get('requested_tickers')==requested
            and isinstance(state.get('packets'),Mapping) and set(state['packets'])<=set(requested)
            and isinstance(state.get('classifications'),Mapping) and len(state['classifications'])<=20
            and all(isinstance(v,Mapping) and normalized_digest(v)==key and validated_classification(v) is not None
                for key,v in state['classifications'].items())
            and all(isinstance(v,Mapping) for v in state['packets'].values())
            and all(not isinstance(p.get('collection'),Mapping) or ('classification' not in p['collection']
                and p['collection'].get('classification_ref') in state['classifications']) for p in state['packets'].values())
            and type(state.get('adapter_operation_count')) is int and 0<=state['adapter_operation_count']<=100000
            and type(state.get('source_failure_streak')) is int and 0<=state['source_failure_streak']<=2
            and state.get('digest')==normalized_digest({k:v for k,v in state.items() if k!='digest'}))
    except (ValueError,TypeError,RecursionError,OverflowError):return False


def _coverage_session(session_state, requested):
    if tuple(requested) != DISCOVER_SAMPLE:
        return SESSION_KEY, session_state.get(SESSION_KEY)
    if DISCOVER_SESSION_KEY in session_state:
        return DISCOVER_SESSION_KEY, session_state.get(DISCOVER_SESSION_KEY)
    legacy = session_state.get(SESSION_KEY)
    if _valid(legacy, list(DEFAULT_SAMPLE)):
        # Keep receipts and their original dates. The first expanded action writes only its own slot.
        return DISCOVER_SESSION_KEY, _seal({**legacy, 'requested_tickers': requested})
    return DISCOVER_SESSION_KEY, None


def _compact_packet(packet,state):
    result=dict(packet);collection=packet.get('collection')
    if isinstance(collection,Mapping):
        collection=dict(collection);classification=collection.pop('classification');key=normalized_digest(classification)
        state['classifications'].setdefault(key,classification);collection['classification_ref']=key;result['collection']=collection
    return result


def _expand_packet(packet,state):
    result=dict(packet);collection=packet.get('collection')
    if isinstance(collection,Mapping):
        collection=dict(collection);key=collection.pop('classification_ref');collection['classification']=state['classifications'][key];result['collection']=collection
    return result


def _recent_classification(state,as_of):
    from src.online_listing_session import fresh_classification
    now=sources._now(as_of)
    valid=[checked for packet in state['classifications'].values() if (checked:=fresh_classification(packet,now)) is not None]
    return max(valid,key=lambda p:(p['inventory']['observed_from'],p['packet_digest'])) if valid else None


def reason_gate(reason):
    if reason=='not_requested':return 'pending'
    if reason in _SOURCE_FAILURES or 'source_unavailable' in reason:return 'source_access'
    if reason=='at_least_three_compatible_industry_references_required':return 'insufficient_references'
    if any(s in reason for s in ('eps','annual_filing','amendment','annual_period')):return 'annual_earnings'
    if any(s in reason for s in ('identity','listing','issuer','security','share_classes','ordinary','investment_company','quote_exchange','cik')):return 'identity_security'
    if any(s in reason for s in ('industry','sic')):return 'industry'
    if any(s in reason for s in ('fiscal','price_date_differs')):return 'period_comparability'
    if any(s in reason for s in ('price','split','quote','currency')):return 'price_share_basis'
    return 'validation'


def _subject_source_failure(view,packet):
    """Access failures and financial eligibility blockers are independent signals."""
    if view.get('reason') in _SOURCE_FAILURES:return True
    collection=packet.get('collection') if isinstance(packet,Mapping) else None
    if not isinstance(collection,Mapping):return False
    issuers=collection.get('issuers',[])
    if not isinstance(issuers,list):return False
    for row in issuers:
        if not isinstance(row,Mapping) or row.get('ticker')!=view.get('ticker'):continue
        for key in ('prices','profile','facts','amendment_evidence','selected_security_evidence','vendor_history'):
            component=row.get(key)
            if (isinstance(component,Mapping) and component.get('status')=='unavailable'
                    and component.get('reason') in {'price_source_unavailable','sec_receipt_unavailable',
                        'amendment_source_unavailable','selected_security_source_unavailable','vendor_history_source_unavailable','source_component_unavailable'}):return True
    return False


def _summary(state,as_of,workspace_mode,*,detail_ticker=None):
    rows=[];primary=Counter();excluded=Counter();groups=defaultdict(list)
    selected_detail = None
    for ticker in state['requested_tickers']:
        attempted=ticker in state['packets'];packet=_expand_packet(state['packets'][ticker],state) if attempted else None
        view=sources.get_online_peer_valuation(ticker,{sources.SESSION_KEY:packet},refresh_requested=False,as_of=as_of,workspace_mode=workspace_mode) if attempted else {}
        if attempted and ticker == detail_ticker:
            selected_detail = view
        subject=view.get('subject');subject=subject if isinstance(subject,Mapping) else None
        context=view.get('subject_source_context',{});attribution=context.get('industry_observation',{}) if isinstance(context,Mapping) else {}
        key,sic=attribution.get('industry_key'),attribution.get('sic')
        reason=view.get('reason','cached_observation_invalid') if attempted else 'not_requested'
        reference_state='not_assessed_subject_blocked' if attempted else 'not_assessed'
        outcomes=view.get('excluded',[])
        if subject:
            reference_state='partially_assessed' if any(r.get('reason') in {'peer_not_collected','source_paused_after_repeated_failures'} for r in outcomes) else 'assessed'
        refs=list(attribution.get('source_refs',[]))
        sec_sic = context.get('sec_sic_observation') if isinstance(context, Mapping) else None
        if sec_sic and not sic:
            refs.append(dict(source_url=sec_sic['source_ref'], observed_at=sec_sic['observed_at'], payload_sha256=sec_sic['payload_sha256']))
        scope=subject.get('selected_security_scope',{}) if subject else context.get('selected_security_scope',{})
        if not isinstance(scope,Mapping):scope={}
        refs.extend(dict(source_url=d['source_ref'],observed_at=d['observed_at'],payload_sha256=d['payload_sha256'],body_sha256=d.get('body_sha256')) for d in scope.get('documents',[]))
        if subject:
            refs.extend([dict(source_url=subject['source_ref'],observed_at=subject['observed_at'],payload_sha256=subject['facts_sha256']),
                         dict(source_url=subject['price_source_ref'],observed_at=subject['price_observed_at'],payload_sha256=subject['price_sha256'])])
        row=dict(ticker=ticker,attempted=attempted,attempted_at=packet.get('observed_at') if packet else None,
            selected_security_state=scope.get('status','unverified'),selected_security_reason=scope.get('reason'),
            subject_source_failure=_subject_source_failure(view,packet) if attempted else False,
            sec_cik=subject['sec_cik'] if subject else context.get('sec_cik') if isinstance(context,Mapping) else None,
            industry_key=key if key and sic else None,sic=sic if key and sic else None,
            industry_label=attribution.get('industry_label') if key and sic else None,
            subject_pe_state='available' if subject else 'withheld' if attempted else 'not_assessed',
            subject_multiple=subject.get('multiple') if subject else None,reference_state=reference_state,
            accepted_reference_count=view.get('peer_count',0) if subject else None,
            comparison_state='available' if view.get('status')=='research_comparison' else 'withheld' if attempted else 'not_assessed',
            primary_reason=reason,reason_gate=reason_gate(reason),candidate_count=view.get('candidate_count') if attempted else None,
            vendor_candidate_total=view.get('industry_candidate_total') if attempted else None,
            excluded=[dict(ticker=r.get('ticker'),reason=r.get('reason')) for r in outcomes],source_refs=refs)
        if subject and subject.get('price_date') is not None:
            row['price_date'] = subject['price_date']
        if sec_sic:
            row['sec_sic'] = sec_sic['sic']
        rows.append(row);groups[(row['industry_key'],row['sic'])].append(row)
        if attempted and row['comparison_state']!='available':primary[reason]+=1
        excluded.update(r['reason'] for r in row['excluded'])
    by_industry=[]
    for (key,sic),members in sorted(groups.items(),key=lambda pair:(pair[0][0] is None,pair[0][0] or '',pair[0][1] or '')):
        by_industry.append(dict(industry_key=key,sic=sic,industry_label=members[0]['industry_label'],
            requested_count=len(members),attempted_count=sum(r['attempted'] for r in members),
            subject_pe_count=sum(r['subject_pe_state']=='available' for r in members),
            reference_assessed_count=sum(r['reference_state']=='assessed' for r in members),
            comparison_count=sum(r['comparison_state']=='available' for r in members)))
    return dict(status='inspection_only',method_version=METHOD,requested_tickers=list(state['requested_tickers']),
        requested_count=len(rows),attempted_count=sum(r['attempted'] for r in rows),pending_count=sum(not r['attempted'] for r in rows),
        subject_pe_count=sum(r['subject_pe_state']=='available' for r in rows),reference_assessed_count=sum(r['reference_state']=='assessed' for r in rows),
        comparison_count=sum(r['comparison_state']=='available' for r in rows),rows=rows,by_industry=by_industry,
        selected_detail=selected_detail,
        source_failure_count=sum(r['subject_source_failure'] for r in rows),
        primary_reason_counts=dict(primary),excluded_reason_counts=dict(excluded),
        adapter_operation_count=state['adapter_operation_count'],paused=state['source_failure_streak']>=2,
        session_only=True,market_universe_coverage_established=False,canonical_changed=False,
        rights_status='personal_research_only_commercial_and_redistribution_unverified')


def get_peer_coverage(session_state,*,inspect_requested=False,inspect_ticker=None,reset_requested=False,retry_ticker=None,tickers=DEFAULT_SAMPLE,
                      user_agent=None,dependencies=None,as_of=None,workspace_mode='research',detail_ticker=None):
    reason=_mode_reason(workspace_mode);requested=_targets(tickers)
    if reason or requested is None:return dict(status='unavailable',reason=reason or 'invalid_peer_coverage_sample')
    try:sources._now(as_of)
    except (ValueError,TypeError):return dict(status='unavailable',reason='invalid_observation')
    if inspect_ticker is not None and (inspect_requested or reset_requested or retry_ticker is not None):
        return dict(status='unavailable',reason='ambiguous_peer_coverage_action')
    session_key, existing = _coverage_session(session_state, requested)
    if reset_requested:existing=None
    if existing is not None and not _valid(existing,requested):return dict(status='unavailable',reason='peer_coverage_state_or_sample_changed')
    state=existing if existing is not None else _new(requested)
    if reset_requested:
        session_state[session_key]=state
        return _summary(state,as_of,workspace_mode)
    if retry_ticker is not None and (retry_ticker not in requested or retry_ticker not in state['packets']):
        return dict(status='unavailable',reason='invalid_peer_coverage_retry')
    if inspect_ticker is not None and (inspect_ticker not in requested or inspect_ticker in state['packets']):
        return dict(status='unavailable',reason='invalid_peer_coverage_inspect_ticker')
    target=retry_ticker
    if target is None and state['source_failure_streak']<2:
        if inspect_ticker is not None:
            target = inspect_ticker
        elif inspect_requested:
            target=next((t for t in requested if t not in state['packets']),None)
    if target is None:return _summary(state,as_of,workspace_mode,detail_ticker=detail_ticker)
    state=deepcopy(state)
    deps=dict(classification=sources.fetch_classification,vendor=sources.observe_vendor,industry=sources.observe_industry,
              sec=sources.fetch_sec_json_receipt,prices=sources.fetch_online_company_prices,amendment=sources.fetch_amendment_evidence,
              security=sources.fetch_selected_security_evidence,history=sources.fetch_vendor_history_match)
    if dependencies is not None:
        if not isinstance(dependencies,Mapping) or not set(dependencies)<=set(deps):return dict(status='unavailable',reason='invalid_peer_coverage_dependencies')
        deps.update(dependencies)
    cached_classification=_recent_classification(state,as_of)
    if cached_classification is not None:deps['classification']=lambda **kwargs:cached_classification
    operations=[]
    def counted(name,fn):
        def call(*args,**kwargs):operations.append(name);return fn(*args,**kwargs)
        return call
    slot={}
    view=sources.get_online_peer_valuation(target,slot,refresh_requested=True,user_agent=user_agent,as_of=as_of,
        workspace_mode=workspace_mode,dependencies={name:counted(name,fn) for name,fn in deps.items()})
    if sources.SESSION_KEY not in slot:return dict(status='unavailable',reason='peer_coverage_attempt_unavailable')
    state['packets'][target]=_compact_packet(slot[sources.SESSION_KEY],state)
    referenced={p['collection']['classification_ref'] for p in state['packets'].values() if isinstance(p.get('collection'),Mapping)}
    state['classifications']={k:v for k,v in state['classifications'].items() if k in referenced}
    state['adapter_operation_count']+=len(operations)
    streak=0 if retry_ticker is not None else state['source_failure_streak']
    state['source_failure_streak']=min(2,streak+1) if _subject_source_failure(view,slot[sources.SESSION_KEY]) else 0
    session_state[session_key]=_seal(state)
    return _summary(state,as_of,workspace_mode)
