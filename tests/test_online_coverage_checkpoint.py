from copy import deepcopy
import json
import os
from pathlib import Path

import pytest

from test_online_us_universe import _inventory,_fetch,OBSERVED


def _state(checked=0):
    from src.online_us_universe import inspect_next_universe_batch
    state=dict(inventory=_inventory(),observations=[])
    if checked:state=inspect_next_universe_batch(state,user_agent='Research',batch_size=checked,source_fetcher=_fetch([]),observed_at=OBSERVED)
    return state


def _save(path,state,expected=None):
    from src.online_coverage_checkpoint import save_coverage_checkpoint
    return save_coverage_checkpoint(path,state,expected_digest=expected,observed_at=OBSERVED)


def _load(path):
    from src.online_coverage_checkpoint import load_coverage_checkpoint
    return load_coverage_checkpoint(path,observed_at=OBSERVED)


def test_checkpoint_resume_continues_next_unique_issuer_without_network_during_load(tmp_path):
    from src.online_us_universe import inspect_next_universe_batch
    path=tmp_path/'coverage.json';state=_state(1)
    saved=_save(path,state)
    assert saved['status']=='saved'
    restored=_load(path)
    assert restored['status']=='ready' and restored['state']['coverage']['attempted_issuer_count']==1
    assert restored['checkpoint_digest']==saved['checkpoint_digest']
    calls=[]
    next_state=inspect_next_universe_batch(restored['state'],user_agent='Research',batch_size=1,source_fetcher=_fetch(calls),observed_at=OBSERVED)
    assert next_state['coverage']['attempted_issuer_count']==2
    assert not any('/CIK0000001234.json' in u for u in calls)
    assert '"value"' not in path.read_text() and 'raw_companyfacts' not in path.read_text()
    assert path.stat().st_mode & 0o777==0o600


def test_explicit_second_save_keeps_exact_prior_backup_and_requires_expected_digest(tmp_path):
    path=tmp_path/'coverage.json';first=_save(path,_state(1));before=path.read_bytes()
    assert _save(path,_state(2))['status']=='unavailable'
    second=_save(path,_state(2),first['checkpoint_digest'])
    assert second['status']=='saved' and second['sequence']==2
    assert path.with_suffix('.previous.json').read_bytes()==before
    assert _load(path)['state']['coverage']['attempted_issuer_count']==2
    assert _save(path,_state(3),first['checkpoint_digest'])['status']=='unavailable'
    assert _load(path)['checkpoint_digest']==second['checkpoint_digest']


@pytest.mark.parametrize('problem',['corrupt','contract','inventory','duplicate','raw_values'])
def test_corrupt_incompatible_or_unreduced_state_is_not_restored_or_overwritten(tmp_path,problem):
    from src.online_coverage_checkpoint import checkpoint_digest
    path=tmp_path/'coverage.json';saved=_save(path,_state(1));obj=json.loads(path.read_text())
    if problem=='corrupt':path.write_text('{"broken":')
    else:
        if problem=='contract':obj['contract_version']='wrong-contract'
        elif problem=='inventory':obj['state']['inventory']['rows'][0]['sec_cik']='0000099999'
        elif problem=='duplicate':obj['state']['observations'].append(deepcopy(obj['state']['observations'][0]))
        else:obj['state']['observations'][0]['row']['raw_financial_values']={'revenue':999}
        obj['content_digest']=checkpoint_digest({k:v for k,v in obj.items() if k!='content_digest'})
        path.write_text(json.dumps(obj))
    before=path.read_bytes()
    assert _load(path)['status']=='unavailable'
    assert _save(path,_state(2),saved['checkpoint_digest'])['status']=='unavailable'
    assert path.read_bytes()==before


def test_unrelated_existing_files_and_symlink_targets_are_never_overwritten(tmp_path):
    unrelated=tmp_path/'personal.json';unrelated.write_text('{"private":"keep"}')
    assert _save(unrelated,_state())['status']=='unavailable'
    assert unrelated.read_text()=='{"private":"keep"}'
    target=tmp_path/'valid.json';_save(target,_state());before=target.read_bytes()
    link=tmp_path/'linked.json';link.symlink_to(target)
    assert _save(link,_state(1))['status']=='unavailable'
    assert _load(link)['status']=='unavailable' and target.read_bytes()==before


def test_canonical_or_code_destination_is_rejected_before_any_write():
    import src.online_coverage_checkpoint as store
    for relative in ['data/private.json','config/checkpoint.json','src/checkpoint.json']:
        result=_save(store.PROJECT_ROOT/relative,_state())
        assert result['status']=='unavailable' and result['reason']=='checkpoint_destination_not_local_audit'


def test_atomic_replace_failure_preserves_previous_checkpoint(tmp_path,monkeypatch):
    from src import online_coverage_checkpoint as store
    path=tmp_path/'coverage.json';saved=_save(path,_state(1));before=path.read_bytes();replace=store.os.replace
    def fail_current(source,dest):
        if Path(dest)==path:raise OSError('simulated interrupted replacement')
        return replace(source,dest)
    monkeypatch.setattr(store.os,'replace',fail_current)
    assert _save(path,_state(2),saved['checkpoint_digest'])['status']=='unavailable'
    assert path.read_bytes()==before
    assert _load(path)['checkpoint_digest']==saved['checkpoint_digest']


def test_concurrent_writer_lock_preserves_checkpoint(tmp_path):
    import fcntl
    path=tmp_path/'coverage.json';first=_save(path,_state());before=path.read_bytes()
    lock=path.with_suffix('.json.lock')
    with lock.open('r+b') as f:
        fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        result=_save(path,_state(1),first['checkpoint_digest'])
        assert result['status']=='unavailable' and result['reason']=='checkpoint_busy'
    assert path.read_bytes()==before


def test_personal_checkpoint_restore_and_save_are_blocked_in_commercial_mode(tmp_path,monkeypatch):
    path=tmp_path/'coverage.json';_save(path,_state());before=path.read_bytes()
    monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE','1')
    assert _load(path)['status']=='unavailable'
    assert _save(path,_state())['status']=='unavailable'
    assert path.read_bytes()==before


def test_session_save_restore_is_explicit_local_and_does_not_fetch_on_read(tmp_path):
    from src.online_coverage_checkpoint import handle_coverage_checkpoint_action
    from src.online_us_universe import SESSION_KEY
    path=tmp_path/'session.json';session={SESSION_KEY:_state(1)}
    assert handle_coverage_checkpoint_action(session,path=path,observed_at=OBSERVED)['status']=='not_requested'
    assert not path.exists()
    saved=handle_coverage_checkpoint_action(session,path=path,save_requested=True,observed_at=OBSERVED)
    assert saved['status']=='saved'
    session.clear()
    result=handle_coverage_checkpoint_action(session,path=path,restore_requested=True,observed_at=OBSERVED)
    assert result['status']=='restored'
    assert session[SESSION_KEY]['coverage']['attempted_issuer_count']==1
    before=path.read_bytes()
    assert handle_coverage_checkpoint_action(session,path=path,save_requested=True,restore_requested=True,observed_at=OBSERVED)['status']=='unavailable'
    assert path.read_bytes()==before
