import pytest
from selected_security_fixtures import scoped_collection,install
from test_online_peer_valuation import build
from src.online_peer_valuation_ui import online_peer_valuation_html


@pytest.mark.parametrize('sources',[False,True])
def test_company_shows_selected_common_scope_without_asserting_other_symbol_aliases(monkeypatch,sources):
    policy,c=scoped_collection();install(monkeypatch,policy);html=online_peer_valuation_html(build(c),sources_only=sources)
    assert '所选证券与其他关联代码' in html and 'FICT、FP' in html
    assert '不代表这些代码已逐一完成证券映射' in html and 'annual.htm' in html and 'cover.htm' in html
    assert c['issuers'][0]['selected_security_evidence']['documents']['annual']['payload_sha256'] in html


@pytest.mark.parametrize('reason,phrase',[
    ('selected_common_other_security_basis_unresolved','其他关联证券的收益口径仍未核对'),
    ('depositary_security_requires_separate_method','ADS'),
    ('successor_annual_basis_unverified','旧 CIK'),
])
def test_independent_identity_observations_explain_remaining_gaps_without_valuation(monkeypatch,reason,phrase):
    policy,c=scoped_collection();policy.update(kind='inspection_only',reason=reason);install(monkeypatch,policy);v=build(c);html=online_peer_valuation_html(v,sources_only=True)
    assert phrase in html and 'cover.htm' in html and '来源权限' in html
    if reason!='successor_annual_basis_unverified':assert v['subject'] is None


def test_history_identity_disclosure_keeps_current_annual_denominator_explicit():
    from test_online_peer_sec_history import history_fixture,fetch
    c,row,raw=history_fixture();row['vendor_history']=fetch(row,raw);v=build(c);html=online_peer_valuation_html(v,sources_only=True)
    assert '历史 SEC 索引仅用于供应商身份核对' in html and 'submissions-001.json' in html
    assert v['subject']['accession']=='0000001001-26-000001'


def test_sample_keeps_security_scope_separate_from_financial_qualification(monkeypatch):
    from src.online_peer_coverage import _new,_compact_packet,_seal,get_peer_coverage,SESSION_KEY
    from src.online_peer_sources import _cache
    from selected_security_fixtures import NOW
    policy,c=scoped_collection();policy.update(kind='inspection_only',reason='depositary_security_requires_separate_method');install(monkeypatch,policy)
    raw=_cache({},'FICT',c,None,NOW);audit=_new(['FICT']);audit['packets']['FICT']=_compact_packet(raw,audit);_seal(audit)
    result=get_peer_coverage({SESSION_KEY:audit},tickers=['FICT'],as_of=NOW);row=result['rows'][0]
    assert row['selected_security_state']=='inspection_only' and result['subject_pe_count']==0
    assert row['reference_state']=='not_assessed_subject_blocked' and any('annual.htm' in r['source_url'] for r in row['source_refs'])


def test_previous_sample_method_requires_an_explicit_reset_without_source_calls():
    from src.online_peer_coverage import _new,_seal,get_peer_coverage,SESSION_KEY
    from selected_security_fixtures import NOW
    previous=_new(['FICT']);previous['method_version']='reported-annual-pe-amendment-scope-v1';_seal(previous);state={SESSION_KEY:previous}
    def forbidden(**kw):raise AssertionError('source requested')
    assert get_peer_coverage(state,tickers=['FICT'],as_of=NOW,dependencies={'classification':forbidden})['status']=='unavailable'
    result=get_peer_coverage(state,tickers=['FICT'],as_of=NOW,reset_requested=True,dependencies={'classification':forbidden})
    assert result['pending_count']==1 and result['attempted_count']==0


def test_sample_accepts_and_counts_security_and_history_components(monkeypatch):
    from src.online_peer_coverage import get_peer_coverage
    from test_online_peer_sources import source_dependencies
    from selected_security_fixtures import NOW
    policy,c=scoped_collection();install(monkeypatch,policy);deps,calls=source_dependencies(c);extra=[]
    def security(ticker,cik,profile,**kw):extra.append('security');return c['issuers'][0]['selected_security_evidence']
    def history(*a,**kw):extra.append('history');return dict(status='not_applicable')
    deps.update(security=security,history=history)
    result=get_peer_coverage({},tickers=['FICT'],inspect_requested=True,dependencies=deps,user_agent='Synthetic contact',as_of=NOW)
    assert result['subject_pe_count']==1 and result['comparison_count']==1
    assert result['adapter_operation_count']==len(calls)+len(extra) and extra.count('security')==1 and extra.count('history')==4


@pytest.mark.parametrize('sources',[False,True])
def test_bank_source_disclosure_distinguishes_incorporated_roles_and_actual_fact_resources(monkeypatch,sources):
    from test_bank_peer_security import bank_collection
    v=build(bank_collection(monkeypatch));html=online_peer_valuation_html(v,sources_only=sources)
    assert '同次申报附件' in html and 'EX-13' in html and 'EX-99.01' in html
    assert '主文件引用' in html and 'annual-linked.htm#eps-fact' in html
    assert 'annual-linked.htm#base' in html and 'annual-linked.htm#eps' in html
    assert 'annual-linked.htm#title' in html and 'annual.htm#common' in html
    assert 'EPS 原始事实' in html and '事实期间与单位' in html
    assert v['peer_count']==3 and '来源权限' in html


def test_bank_link_labels_escape_untrusted_parent_text_and_reject_unsafe_fact_urls(monkeypatch):
    from test_bank_peer_security import bank_collection
    v=build(bank_collection(monkeypatch));scope=v['peers'][0]['selected_security_scope']
    scope['documents'][1]['parent_href']='<img src=x onerror=alert(1)>'
    scope['original_eps']['proofs'][0]['source_ref']='javascript:alert(1)'
    html=online_peer_valuation_html(v,sources_only=True)
    assert '&lt;img src=x onerror=alert(1)&gt;' in html
    assert '<img src=x' not in html and 'javascript:' not in html


def inspected_view(monkeypatch):
    from test_security_inspection_observations import observation_fixture
    import hashlib,base64
    policy,c=scoped_collection();policy.update(kind='inspection_only',reason='depositary_security_requires_separate_method');doc=policy['documents']['annual'];receipt=c['issuers'][0]['selected_security_evidence']['documents']['annual']
    body,contracts=observation_fixture();doc.update(sha256=hashlib.sha256(body).hexdigest(),inspection_observations=contracts);receipt.update(payload_sha256=doc['sha256'],payload_raw_base64=base64.b64encode(body).decode());install(monkeypatch,policy)
    return build(c)


@pytest.mark.parametrize('sources',[False,True])
def test_inspected_ads_currency_and_complete_note_sources_remain_outside_pe(monkeypatch,sources):
    v=inspected_view(monkeypatch);html=online_peer_valuation_html(v,sources_only=sources)
    assert '15.21' in html and '0.49' in html and 'TWD/ADS' in html and 'USD/ADS' in html
    assert '原始单位' in html and '便利折算' in html and '不参与 P/E' in html
    assert 'annual.htm#ads-native' in html and 'annual.htm#ads' in html and 'annual.htm#twd' in html
    assert 'annual.htm#note-tail' in html and '/html[1]/div[1]' in html
    assert v['subject'] is None and v['premium_fraction'] is None


def test_inspection_labels_and_source_locations_are_escaped(monkeypatch):
    v=inspected_view(monkeypatch);scope=v['subject_source_context']['selected_security_scope'];o=scope['evidence_observations'][0]
    o.update(label='<img src=x onerror=alert(1)>',source_ref='javascript:alert(1)')
    html=online_peer_valuation_html(v,sources_only=True)
    assert '&lt;img src=x' in html and '<img src=x' not in html and 'javascript:' not in html


def test_unknown_sibling_mapping_does_not_erase_qualified_literal_common(monkeypatch):
    from test_cross_security_evidence import dimensionless
    policy,c=dimensionless();install(monkeypatch,policy);v=build(c);html=online_peer_valuation_html(v,sources_only=True)
    assert '尚未逐一建立证券映射' in html and 'FP' in html and v['status']=='research_comparison'


def test_note_only_inspection_summary_shows_verified_evidence_instead_of_empty_heading(monkeypatch):
    from src.online_peer_valuation_ui import _observations_html
    v=inspected_view(monkeypatch);scope=v['subject_source_context']['selected_security_scope'];scope['evidence_observations']=[o for o in scope['evidence_observations'] if o['kind']=='note']
    html=_observations_html(scope,compact=True)
    assert 'Convenience basis' in html and 'annual.htm#fx-note' in html
    assert '不参与 P/E' in html
