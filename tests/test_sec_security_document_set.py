from copy import deepcopy
import base64,hashlib
import pytest
from document_set_fixtures import document_set_fixture,reseal
from selected_security_fixtures import fixture,install,validate,NOW


def test_linked_financial_report_supplies_eps_and_cover_context_with_actual_source_refs(monkeypatch):
    policy,row,packet,_=document_set_fixture();install(monkeypatch,policy)
    result=validate(policy,row,packet)
    assert result['status']=='supported_common'
    proof=result['original_eps']['proofs'][0]
    assert proof['source_ref'].endswith('/annual-linked.htm#eps-fact')
    assert proof['context_source_ref'].endswith('/annual-linked.htm#base')
    assert proof['unit_source_ref'].endswith('/annual-linked.htm#eps')
    assert result['original_eps']['eps']==1
    assert result['documents'][0]['selected_common']['context_source_ref'].endswith('/annual-linked.htm#common')
    exhibit=result['documents'][1]
    assert exhibit['form']=='EX-13' and exhibit['parent_form']=='10-K'
    assert exhibit['parent_source_ref'].endswith('/annual.htm')
    assert all(r['source_ref'].split('#')[0].endswith('/annual-linked.htm') for r in result['basis_refs'])


def test_linked_cover_exhibits_resolve_parent_metadata_contexts_without_relabelling_sources(monkeypatch):
    policy,row,packet,_=document_set_fixture('cover');install(monkeypatch,policy)
    result=validate(policy,row,packet)
    assert result['status']=='supported_common'
    annual=result['documents'][0]['selected_common']
    assert annual['fact_refs'][0].endswith('/annual-linked.htm#title')
    assert annual['context_source_ref'].endswith('/annual.htm#common')
    assert result['original_eps']['proofs'][0]['source_ref'].endswith('/annual.htm#eps-fact')
    assert [d['form'] for d in result['documents']]==['10-K','EX-99.01','8-K','EX-99.01']


@pytest.mark.parametrize('failure',['missing','raw_digest','stale','future','cross_accession','redirect_url','unlinked'])
def test_missing_changed_stale_or_unlinked_companion_withholds_even_after_packet_reseal(monkeypatch,failure):
    policy,row,packet,raw=document_set_fixture();ref=packet['documents']['annual']['companion']
    if failure=='missing':packet['documents']['annual'].pop('companion')
    elif failure=='raw_digest':ref['payload_sha256']='a'*64
    elif failure=='stale':ref['observed_at']='2026-10-01T00:00:00Z'
    elif failure=='future':ref['observed_at']='2026-11-02T00:00:00Z'
    elif failure=='cross_accession':ref['source_url']=ref['source_url'].replace('000000100126000001','000000100126000099')
    elif failure=='redirect_url':ref['source_url']+='?redirect=1'
    else:raw['annual']=raw['annual'].replace(b'href="annual-linked.htm"',b'href="other.htm"');reseal(policy,packet,raw)
    install(monkeypatch,policy)
    assert validate(policy,row,packet)['status']=='withheld'


@pytest.mark.parametrize('failure',['duplicate_id','prefix_conflict','missing_context','missing_unit','target','wrong_entity','wrong_currency','wrong_period','external_base'])
def test_document_set_cannot_mix_ambiguous_or_unsupported_resources(monkeypatch,failure):
    policy,row,packet,raw=document_set_fixture();key='annual-companion';body=raw[key]
    if failure=='duplicate_id':body=body.replace(b'</html>',b'<span id="period">duplicate</span></html>')
    elif failure=='prefix_conflict':body=body.replace(b'xmlns:g="http://fasb.org/us-gaap/2025"',b'xmlns:g="http://example.invalid/gaap"')
    elif failure=='missing_context':body=body.replace(b'id="common"',b'id="other"')
    elif failure=='missing_unit':body=body.replace(b'id="eps"',b'id="no-eps"')
    elif failure=='target':body=body.replace(b'id="eps-fact"',b'id="eps-fact" target="other"')
    elif failure=='wrong_entity':body=body.replace(b'0000001001</x:identifier>',b'0000009999</x:identifier>')
    elif failure=='wrong_currency':body=body.replace(b'iso:USD',b'iso:CAD')
    elif failure=='wrong_period':body=body.replace(b'2025-01-01',b'2025-10-01')
    else:body=body.replace(b'</html>',b'<base href="https://example.invalid/"/></html>')
    raw[key]=body;reseal(policy,packet,raw,companion=True);install(monkeypatch,policy)
    assert validate(policy,row,packet)['status']=='withheld'


@pytest.mark.parametrize('kind',['financial','cover'])
def test_explicit_fetch_collects_only_declared_same_accession_companions_and_cached_read_is_pure(monkeypatch,kind):
    from src.sec_selected_security import fetch_selected_security_evidence
    policy,row,_,raw=document_set_fixture(kind);install(monkeypatch,policy);calls=[]
    def fetch(url,agent):
        calls.append(url)
        for role,doc in policy['documents'].items():
            if url.endswith('/'+doc['metadata']['primaryDocument']):return raw[role],{},url
            if doc.get('companion') and url.endswith('/'+doc['companion']['primaryDocument']):return raw[role+'-companion'],{},url
        raise AssertionError('undeclared URL')
    packet=fetch_selected_security_evidence('FICT','0000001001',row['profile'],user_agent='Synthetic contact',fetcher=fetch,observed_at=NOW)
    result=validate(policy,row,packet)
    assert result['status']=='supported_common' and len(calls)==(3 if kind=='financial' else 4)
    before=deepcopy(packet);validate(policy,row,packet)
    assert packet==before and len(calls)==(3 if kind=='financial' else 4)


def test_only_enumerated_identical_cover_duplicates_can_select_the_visible_fact(monkeypatch):
    policy,row,packet,raw=fixture();role='cover'
    raw[role]=raw[role].replace(b'</html>',b'<ix:nonNumeric id="hidden-exchange" name="dei:SecurityExchangeName" contextRef="common">Nasdaq</ix:nonNumeric></html>')
    reseal(policy,packet,raw,role);policy['documents'][role]['cover_duplicate_groups']=[dict(concept='SecurityExchangeName',namespace_uri='http://xbrl.sec.gov/dei/2025',context_id='common',fact_ids=['exchange','hidden-exchange'])]
    install(monkeypatch,policy);result=validate(policy,row,packet)
    assert result['status']=='supported_common'
    assert result['documents'][-1]['selected_common']['fact_refs'][-1].endswith('#exchange')
    assert result['documents'][-1]['selected_common']['consistent_duplicate_refs'][-1].endswith('#hidden-exchange')


@pytest.mark.parametrize('change',['conflict','extra','wrong_context','target','continued','nil','format','not_enumerated'])
def test_duplicate_policy_never_hides_conflicts_or_unlisted_facts(monkeypatch,change):
    policy,row,packet,raw=fixture();role='cover'
    dup=b'<ix:nonNumeric id="hidden-exchange" name="dei:SecurityExchangeName" contextRef="common">Nasdaq</ix:nonNumeric>'
    if change=='conflict':dup=dup.replace(b'>Nasdaq<',b'>NYSE<')
    if change=='extra':dup+=dup.replace(b'hidden-exchange',b'extra')
    if change=='wrong_context':dup=dup.replace(b'contextRef="common"',b'contextRef="base"')
    if change in {'target','continued','format'}:dup=dup.replace(b'id="hidden-exchange"',b'id="hidden-exchange" '+{'target':b'target="other"','continued':b'continuedAt="other"','format':b'format="g:unknown"'}[change])
    if change=='nil':dup=dup.replace(b'id="hidden-exchange"',b'id="hidden-exchange" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:nil="true"')
    raw[role]=raw[role].replace(b'</html>',dup+b'</html>');reseal(policy,packet,raw,role)
    if change!='not_enumerated':policy['documents'][role]['cover_duplicate_groups']=[dict(concept='SecurityExchangeName',namespace_uri='http://xbrl.sec.gov/dei/2025',context_id='common',fact_ids=['exchange','hidden-exchange'])]
    install(monkeypatch,policy)
    assert validate(policy,row,packet)['status']=='withheld'


def test_total_scope_budget_stops_collection_before_a_fourth_large_document(monkeypatch):
    from src.sec_selected_security import fetch_selected_security_evidence
    policy,row,_,_=document_set_fixture('cover');install(monkeypatch,policy);calls=[]
    def fetch(url,agent):
        calls.append(url)
        return b'x'*(24*1024*1024),{},url
    result=fetch_selected_security_evidence('FICT','0000001001',row['profile'],user_agent='Synthetic contact',fetcher=fetch,observed_at=NOW)
    assert result['status']=='unavailable' and len(calls)==3
