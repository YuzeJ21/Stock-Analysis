"""Explicit private reduced coverage checkpoints; never canonical company data."""
from collections.abc import Mapping
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile

from src.company_sec_online_preview import _utc_timestamp
from src.online_company_identity import _mode_reason
from src.online_us_universe import validated_us_universe, build_universe_coverage, validated_access_pause
from src.sec_association_receipt import _json_object

PROJECT_ROOT=Path(__file__).resolve().parents[1]
SCHEMA='online-coverage-checkpoint-v1'
CONTRACT='online-us-coverage-20261030-v1'
MAX_CHECKPOINT_BYTES=32*1024*1024
DEFAULT_CHECKPOINT=PROJECT_ROOT/'outputs/local/online_us_coverage.json'
SESSION_RECEIPT_KEY='coverage_checkpoint_write_receipt_v1'
ROW_KEYS={'ticker','attempted','sec_cik','financial_source_matched','sic','sic_description','fields','annual_period','quarterly_period','annual_available_period','quarterly_available_period','interim_period','interim_available_period','annual_unit','quarterly_unit','interim_unit','industry_reason','annual_reason','quarterly_reason','source_receipts'}
LISTING_KEYS={'listing_id','symbol','source','venue_code','venue','etf','sec_cik','sec_ticker','association_reason'}


class CheckpointError(ValueError):
    pass


def checkpoint_digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()).hexdigest()


def _now(value):
    value=value or datetime.now(timezone.utc)
    if not isinstance(value,datetime) or value.utcoffset() is None:raise CheckpointError('invalid_checkpoint_clock')
    return value.astimezone(timezone.utc)


def _path(value):
    original=Path(value).expanduser().absolute()
    if original.is_symlink():raise CheckpointError('checkpoint_symlink_refused')
    path=original.resolve()
    if path.suffix!='.json' or len(path.name)>160:raise CheckpointError('invalid_checkpoint_path')
    try:relative=path.relative_to(PROJECT_ROOT)
    except ValueError:relative=None
    if relative is not None and relative.parts[:2]!=('outputs','local'):
        raise CheckpointError('checkpoint_destination_not_local_audit')
    return path


def _reduced_state(state,now):
    if not isinstance(state,Mapping):raise CheckpointError('invalid_checkpoint_state')
    inventory=validated_us_universe(state.get('inventory'));observations=state.get('observations',[])
    coverage=build_universe_coverage(inventory,observations)
    if inventory is None or coverage.get('status')!='inspection_only':raise CheckpointError('invalid_checkpoint_state')
    if any(set(row)!=LISTING_KEYS for row in inventory['rows']):raise CheckpointError('checkpoint_not_reduced')
    for item in inventory['map_receipt']['payload'].values():
        if (not isinstance(item,Mapping) or not set(item)<={'ticker','cik_str','title'}
            or not isinstance(item.get('ticker'),str) or not re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,19}',item['ticker'])
            or type(item.get('cik_str')) not in {str,int} or not re.fullmatch(r'\d{1,10}',str(item['cik_str'])) or int(item['cik_str'])==0
            or item.get('title') is not None and (not isinstance(item['title'],str) or len(item['title'])>500)):
            raise CheckpointError('checkpoint_not_reduced')
    for obs in observations:
        if set(obs)!={'inventory_fingerprint','sec_cik','row'} or set(obs['row'])!=ROW_KEYS:
            raise CheckpointError('checkpoint_not_reduced')
    refs=[*inventory['source_receipts'],*(ref for o in observations for ref in o['row']['source_receipts'])]
    if any(_utc_timestamp(r['observed_at'])>now for r in refs):raise CheckpointError('future_checkpoint_observation')
    result=dict(status='inspection_only',inventory=inventory,observations=observations)
    pause=state.get('source_access_pause')
    if pause is not None:
        pause=validated_access_pause(pause)
        if pause is None:raise CheckpointError('invalid_source_access_pause')
        result['source_access_pause']=pause
    return result,coverage


def _read(path,now):
    try:
        descriptor=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
        with os.fdopen(descriptor,'rb') as f:
            metadata=os.fstat(f.fileno())
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size>MAX_CHECKPOINT_BYTES:raise CheckpointError('invalid_checkpoint_file')
            raw=f.read(MAX_CHECKPOINT_BYTES+1)
        if len(raw)>MAX_CHECKPOINT_BYTES:raise CheckpointError('checkpoint_too_large')
        obj=_json_object(raw,'invalid_checkpoint_json')
        if (set(obj)!={'schema_version','contract_version','sequence','previous_digest','written_at','state','content_digest'}
            or obj.get('schema_version')!=SCHEMA or obj.get('contract_version')!=CONTRACT
            or type(obj.get('sequence')) is not int or obj['sequence']<1
            or _utc_timestamp(obj.get('written_at')) is None or _utc_timestamp(obj['written_at'])>now
            or obj.get('previous_digest') is not None and (not isinstance(obj['previous_digest'],str) or not re.fullmatch(r'[0-9a-f]{64}',obj['previous_digest']))
            or obj.get('content_digest')!=checkpoint_digest({k:v for k,v in obj.items() if k!='content_digest'})):
            raise CheckpointError('checkpoint_schema_or_digest_invalid')
        state,coverage=_reduced_state(obj['state'],now)
        return raw,obj,{**state,'coverage':coverage}
    except (OSError,TypeError,KeyError,RecursionError,ValueError) as e:
        if isinstance(e,CheckpointError):raise
        raise CheckpointError('checkpoint_unreadable_or_invalid') from e


def load_coverage_checkpoint(path=DEFAULT_CHECKPOINT,*,observed_at=None,workspace_mode='research'):
    reason=_mode_reason(workspace_mode)
    if reason:return dict(status='unavailable',reason=reason)
    try:
        path=_path(path);now=_now(observed_at);_,obj,state=_read(path,now)
        fresh=timedelta(0)<=now-_utc_timestamp(state['inventory']['observed_from'])<=timedelta(hours=24)
        return dict(status='ready',state=state,checkpoint_digest=obj['content_digest'],sequence=obj['sequence'],
            probing_allowed=fresh,path=str(path),written_at=obj['written_at'])
    except (CheckpointError,OSError,TypeError,ValueError):return dict(status='unavailable',reason='checkpoint_unreadable_or_invalid')


@contextmanager
def _locked(path):
    try:import fcntl
    except ImportError as e:raise CheckpointError('checkpoint_lock_unavailable') from e
    lock=path.with_suffix(path.suffix+'.lock')
    if lock.is_symlink():raise CheckpointError('checkpoint_symlink_refused')
    descriptor=os.open(lock,os.O_RDWR|os.O_CREAT|getattr(os,'O_NOFOLLOW',0),0o600)
    with os.fdopen(descriptor,'r+b') as stream:
        metadata=os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode):raise CheckpointError('invalid_checkpoint_lock')
        try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as e:raise CheckpointError('checkpoint_busy') from e
        try:yield
        finally:fcntl.flock(stream,fcntl.LOCK_UN)


def _atomic_bytes(path,raw):
    descriptor,name=tempfile.mkstemp(prefix='.coverage-',suffix='.tmp',dir=path.parent)
    try:
        os.fchmod(descriptor,0o600)
        with os.fdopen(descriptor,'wb') as stream:
            descriptor=None;stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.replace(name,path)
    finally:
        if descriptor is not None:os.close(descriptor)
        if os.path.exists(name):os.unlink(name)


def save_coverage_checkpoint(path,state,*,expected_digest=None,observed_at=None,workspace_mode='research'):
    reason=_mode_reason(workspace_mode)
    if reason:return dict(status='unavailable',reason=reason)
    try:
        path=_path(path);now=_now(observed_at);reduced,_=_reduced_state(state,now)
        path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        with _locked(path):
            if path.is_symlink():raise CheckpointError('checkpoint_symlink_refused')
            previous=None;old_raw=None
            if path.exists():
                old_raw,previous,_=_read(path,now)
                if expected_digest!=previous['content_digest']:raise CheckpointError('checkpoint_digest_conflict')
                old=previous['state']
                if old['inventory']['inventory_fingerprint']==reduced['inventory']['inventory_fingerprint']:
                    prior=old['observations']
                    if reduced['observations'][:len(prior)]!=prior:raise CheckpointError('checkpoint_progress_conflict')
                pause=old.get('source_access_pause')
                if pause and now<_utc_timestamp(pause['resume_after']) and reduced.get('source_access_pause')!=pause:
                    raise CheckpointError('checkpoint_access_pause_conflict')
            elif expected_digest is not None:raise CheckpointError('checkpoint_digest_conflict')
            obj=dict(schema_version=SCHEMA,contract_version=CONTRACT,sequence=previous['sequence']+1 if previous else 1,
                previous_digest=previous['content_digest'] if previous else None,written_at=now.strftime('%Y-%m-%dT%H:%M:%SZ'),state=reduced)
            obj['content_digest']=checkpoint_digest(obj)
            raw=json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
            if len(raw)>MAX_CHECKPOINT_BYTES:raise CheckpointError('checkpoint_too_large')
            if old_raw is not None:
                backup=path.with_suffix('.previous.json')
                if backup.is_symlink():raise CheckpointError('checkpoint_symlink_refused')
                if backup.exists():_read(backup,now)
                _atomic_bytes(backup,old_raw)
            _atomic_bytes(path,raw)
            directory=os.open(path.parent,os.O_RDONLY|getattr(os,'O_DIRECTORY',0))
            try:os.fsync(directory)
            finally:os.close(directory)
            return dict(status='saved',checkpoint_digest=obj['content_digest'],sequence=obj['sequence'],path=str(path))
    except CheckpointError as e:return dict(status='unavailable',reason=str(e))
    except (OSError,TypeError,ValueError,KeyError,RecursionError):return dict(status='unavailable',reason='checkpoint_write_failed')


def handle_coverage_checkpoint_action(session_state,*,path=DEFAULT_CHECKPOINT,save_requested=False,
                                      restore_requested=False,new_run_requested=False,observed_at=None,workspace_mode='research'):
    from src.online_us_universe import SESSION_KEY
    reason=_mode_reason(workspace_mode)
    if reason:return dict(status='unavailable',reason=reason)
    if sum(bool(v) for v in (save_requested,restore_requested,new_run_requested))>1:return dict(status='unavailable',reason='ambiguous_checkpoint_action')
    if not any((save_requested,restore_requested,new_run_requested)):return dict(status='not_requested')
    try:target=_path(path)
    except (OSError,ValueError,TypeError):return dict(status='unavailable',reason='invalid_checkpoint_path')
    if new_run_requested:
        expected=None
        if target.exists():
            loaded=load_coverage_checkpoint(target,observed_at=observed_at,workspace_mode=workspace_mode)
            if loaded['status']!='ready':return loaded
            expected=loaded['checkpoint_digest']
        session_state[SESSION_RECEIPT_KEY]=dict(path=str(target),checkpoint_digest=expected)
        return dict(status='run_prepared')
    if restore_requested:
        loaded=load_coverage_checkpoint(target,observed_at=observed_at,workspace_mode=workspace_mode)
        if loaded['status']!='ready':return loaded
        session_state[SESSION_KEY]=loaded['state']
        session_state[SESSION_RECEIPT_KEY]=dict(path=str(target),checkpoint_digest=loaded['checkpoint_digest'])
        return dict(status='restored',checkpoint_digest=loaded['checkpoint_digest'],sequence=loaded['sequence'],probing_allowed=loaded['probing_allowed'])
    receipt=session_state.get(SESSION_RECEIPT_KEY)
    if receipt is None and not target.exists():receipt=dict(path=str(target),checkpoint_digest=None)
    if not isinstance(receipt,Mapping) or receipt.get('path')!=str(target):
        return dict(status='unavailable',reason='checkpoint_restore_required')
    result=save_coverage_checkpoint(target,session_state.get(SESSION_KEY),expected_digest=receipt.get('checkpoint_digest'),
        observed_at=observed_at,workspace_mode=workspace_mode)
    if result['status']=='saved':session_state[SESSION_RECEIPT_KEY]=dict(path=str(target),checkpoint_digest=result['checkpoint_digest'])
    return result
