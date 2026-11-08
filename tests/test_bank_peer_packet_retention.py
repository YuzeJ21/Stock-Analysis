"""Storage preserves complete observed inputs and unchanged valuation admission."""
from copy import deepcopy
from datetime import timedelta
import base64

import pytest

from test_self_service_research_coverage import dependencies, study, NOW


def oversized_sources(monkeypatch):
    from src import self_service_research_coverage as coverage
    original = coverage.peer_sources.get_online_peer_valuation
    captured = []
    def observed(*args, **kwargs):
        result = original(*args, **kwargs)
        slot = args[1]
        packet = slot[coverage.peer_sources.SESSION_KEY]
        # Constructed ancillary source bytes are deliberately not an approved
        # financial field. Storage must retain them without altering a verdict.
        packet['collection']['source_documents'] = [dict(
            source_url='https://www.sec.gov/Archives/edgar/data/1001/000000100126000001/research.htm',
            payload_raw_base64=base64.b64encode(b'<html>'+b' retained source evidence '*350000+b'</html>').decode(),
            rights_status='personal_inspection_only')]
        packet['packet_digest'] = coverage.normalized_digest({k:v for k,v in packet.items() if k!='packet_digest'})
        captured.append(deepcopy(packet))
        return result
    monkeypatch.setattr(coverage.peer_sources,'get_online_peer_valuation',observed)
    return captured


def test_large_source_packet_restores_every_original_value_before_unchanged_peer_validation(monkeypatch):
    from src import self_service_research_coverage as coverage
    captured = oversized_sources(monkeypatch)
    deps,calls = dependencies(); state={}
    view = study(state,inspect=True,deps=deps)
    packet = state[coverage.SESSION_KEY]['packets']['AMD']
    assert len(coverage._bytes(captured[0])) > coverage.MAX_PACKET_BYTES
    restored = coverage._expand_peer(packet['peer_packet'],state[coverage.SESSION_KEY])
    assert restored == captured[0]
    assert len(coverage._bytes(packet)) <= coverage.MAX_PACKET_BYTES
    assert view['rows'][0]['capabilities']['peer_comparison']['status']=='available'
    storage = view['rows'][0]['peer_storage']
    assert storage['status']=='retained' and storage['source_evidence_unchanged'] is True
    assert storage['encoding']=='zlib+base64' and storage['expanded_bytes']>coverage.MAX_PACKET_BYTES
    monkeypatch.setattr(coverage,'_replay_probe',lambda *a,**k:pytest.fail('Ordinary read wrote a snapshot'))
    before=list(calls); again=study(state,deps=deps)
    assert again==view and calls==before
    stale=study(state,deps=deps,now=NOW+timedelta(hours=25))
    assert stale['rows'][0]['capabilities']['peer_comparison']['status']!='available'


def test_corrupt_retained_peer_is_a_precise_gap_without_erasing_independent_fields(monkeypatch):
    from src import self_service_research_coverage as coverage
    oversized_sources(monkeypatch); deps,calls=dependencies();state={}
    study(state,inspect=True,deps=deps)
    private=state[coverage.SESSION_KEY]; retained=private['packets']['AMD']['peer_packet']
    assert retained.get('encoding')=='zlib+base64'
    retained['compressed_sha256']='0'*64
    coverage._seal(private)
    view=study(state,deps=deps); row=view['rows'][0]
    assert row['capabilities']['peer_comparison']=={'status':'held','reason':'peer_source_retention_invalid'}
    assert row['capabilities']['current_annual']['status']=='available'
    assert row['capabilities']['dated_price']['status']=='available'
    assert row['peer_storage']['status']=='held'


def test_another_companys_valid_storage_is_not_certified_for_the_selected_company(monkeypatch):
    from src import self_service_research_coverage as coverage
    from src.online_peer_packet_storage import pack_peer_packet
    oversized_sources(monkeypatch);deps,calls=dependencies();state={}
    study(state,inspect=True,deps=deps);private=state[coverage.SESSION_KEY]
    expanded=coverage._expand_peer(private['packets']['AMD']['peer_packet'],private)
    expanded['ticker']='BAC';expanded['collection']['ticker']='BAC'
    expanded['packet_digest']=coverage.normalized_digest({k:v for k,v in expanded.items() if k!='packet_digest'})
    other=coverage._compact_peer(expanded,private)
    private['packets']['AMD']['peer_packet']=pack_peer_packet(other,max_stored_bytes=coverage.MAX_PACKET_BYTES)
    coverage._seal(private)
    row=study(state,deps=deps)['rows'][0]
    assert row['capabilities']['peer_comparison']=={'status':'held','reason':'peer_source_retention_invalid'}
    assert row['peer_storage']['status']=='held' and row['peer_storage']['source_evidence_unchanged'] is False
    assert row['capabilities']['current_annual']['status']=='available'


@pytest.mark.parametrize('state_limit',[False,True])
def test_older_compressed_sources_keep_their_classification_after_new_observation_and_pruning(monkeypatch,state_limit):
    from src import self_service_research_coverage as coverage
    from test_online_peer_valuation import classification, collection, issuer, digest
    from test_online_peer_sources import source_dependencies
    captured=oversized_sources(monkeypatch);deps,calls=dependencies();state={}
    study(state,inspect=True,deps=deps)
    original=deepcopy(captured[0]);private=state[coverage.SESSION_KEY]
    old_key=private['listing_ref']
    if state_limit:
        monkeypatch.setattr(coverage,'MAX_STATE_BYTES',len(coverage._bytes(private))+4096)
    monkeypatch.setattr(coverage,'_recent_classification',lambda *a:None)
    symbols=['AMD','NVDA','FA','FB','FC']; peer=collection()
    peer.update(ticker='NVDA',classification=classification(symbols,observed_at=NOW+timedelta(minutes=1)))
    peer['industry']['payload']['symbols']=symbols
    peer['industry']['normalized_sha256']=digest(peer['industry']['payload'])
    peer['issuers']=[issuer(t,str(1001+i).zfill(10),30) for i,t in enumerate(symbols)]
    sources,_=source_dependencies(peer)
    study(state,inspect=True,deps={**deps,'peer_dependencies':sources},now=NOW+timedelta(minutes=1))
    private=state[coverage.SESSION_KEY]
    assert old_key in private['classifications']
    restored=coverage._expand_peer(private['packets']['AMD']['peer_packet'],private)
    assert restored==original
    assert coverage._valid(private)
    if not state_limit:
        assert private['listing_ref']!=old_key and len(private['classifications'])==2
