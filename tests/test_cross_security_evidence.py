"""Synthetic dimensionless covers; no actual issuer source values."""
import base64,hashlib
from copy import deepcopy
import pytest
from selected_security_fixtures import scoped_collection,install,validate,NOW
from test_online_peer_valuation import build


def dimensionless():
    policy,c=scoped_collection();row=c['issuers'][0];packet=row['selected_security_evidence']
    for role,doc in policy['documents'].items():
        raw=base64.b64decode(packet['documents'][role]['payload_raw_base64'])
        raw=raw.replace(b'<x:segment><d:explicitMember dimension="g:StatementClassOfStockAxis">g:CommonStockMember</d:explicitMember></x:segment>',b'')
        doc['cover_context']=dict(kind='dimensionless',context_id='common',period_start='2025-01-01' if role=='annual' else '2026-10-20')
        seal(doc,packet['documents'][role],raw)
    return policy,c


def seal(doc,receipt,raw):
    doc['sha256']=hashlib.sha256(raw).hexdigest();receipt.update(payload_sha256=doc['sha256'],payload_raw_base64=base64.b64encode(raw).decode())


def test_explicit_dimensionless_scope_qualifies_literal_common_without_assigning_sibling(monkeypatch):
    policy,c=dimensionless();install(monkeypatch,policy);before=deepcopy(c);v=build(c)
    assert v['status']=='research_comparison' and v['subject']['multiple']==30
    scope=v['subject']['selected_security_scope']
    assert scope['alias_mappings_established'] is False and scope['unassigned_issuer_symbols']==['FP']
    assert c==before


@pytest.mark.parametrize('mutation',[
    lambda raw:raw.replace(b'id="common"',b'id="different"'),
    lambda raw:raw.replace(b'<x:startDate>2025-01-01</x:startDate>',b'<x:startDate>2024-01-01</x:startDate>'),
    lambda raw:raw.replace(b'</x:entity>',b'<x:segment/></x:entity>'),
    lambda raw:raw.replace(b'</x:context>',b'<x:scenario/></x:context>'),
    lambda raw:raw.replace(b'</x:identifier>',b'</x:identifier><x:identifier scheme="http://www.sec.gov/CIK">0000001001</x:identifier>'),
    lambda raw:raw.replace(b'</x:period>',b'<x:instant>2025-12-31</x:instant></x:period>'),
    lambda raw:raw.replace(b'</x:entity>',b'<x:segment><d:explicitMember dimension="g:StatementClassOfStockAxis">g:CommonStockMember</d:explicitMember></x:segment></x:entity>'),
])
def test_resealed_dimensionless_scope_rejects_wrong_duration_or_qualified_structure(monkeypatch,mutation):
    policy,c=dimensionless();receipt=c['issuers'][0]['selected_security_evidence']['documents']['annual'];raw=mutation(base64.b64decode(receipt['payload_raw_base64']))
    seal(policy['documents']['annual'],receipt,raw);install(monkeypatch,policy)
    assert build(c)['subject'] is None


def test_dimensionless_source_without_explicit_contract_remains_held(monkeypatch):
    policy,c=dimensionless()
    for doc in policy['documents'].values():doc.pop('cover_context')
    install(monkeypatch,policy);assert build(c)['subject'] is None


def test_dimensionless_common_does_not_override_genuine_other_common_listing(monkeypatch):
    policy,c=dimensionless();_,other=scoped_collection(other_common=True);c['classification']=other['classification'];install(monkeypatch,policy)
    assert build(c)['reason']=='multiple_issuer_share_classes_unresolved'


def test_exact_literal_scope_resolves_missing_directory_description_only(monkeypatch):
    policy,c=dimensionless();_,unknown=scoped_collection(unknown_literal=True);c['classification']=unknown['classification'];install(monkeypatch,policy)
    assert build(c)['subject']['multiple']==30
    c['issuers'][0].pop('selected_security_evidence')
    assert build(c)['subject'] is None


def test_known_scope_allows_bounded_peer_collection_for_unknown_description_not_qualification(monkeypatch):
    from src.online_peer_sources import _ordinary_identity
    from src.security_classification import validated_classification
    policy,c=dimensionless();_,unknown=scoped_collection(unknown_literal=True);install(monkeypatch,policy)
    assert _ordinary_identity(validated_classification(unknown['classification']),'FICT')=='0000001001'
    policy['ticker']='OTHER';install(monkeypatch,policy)
    with pytest.raises(ValueError):_ordinary_identity(validated_classification(unknown['classification']),'FICT')
