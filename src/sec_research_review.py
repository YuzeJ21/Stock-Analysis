"""Portable normalized NEM SEC receipts. No transport or canonical writes."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from src.commercial_source_rights import DEFAULT_REGISTRY_PATH, parse_source_rights_registry
from src.company_sec_online_preview import (
    REVENUE_CONCEPTS, OPERATING_COMPONENT_CONCEPTS, _finite_direct_number, _iso_date, _utc_timestamp,
)
from src.online_company_identity import financial_identity_valid
from src.research_change_snapshot import ResearchChangeSnapshot, TickerResearchState, SCHEMA_VERSION as SNAPSHOT_SCHEMA
from src.research_change_monitor import compare_research_snapshots

SCHEMA = 'sec-research-review-v1'
FIELDS = ('revenue', 'operating_income', 'cash_from_operations', 'capital_expenditures')
CIK = '0001164727'
SOURCE = f'https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json'
RIGHTS = 'approved_field_scope_raw_redistribution_held'
MAX_BYTES = 65536
MAX_RECEIPTS = 100
CONCEPTS = {'revenue': REVENUE_CONCEPTS, **OPERATING_COMPONENT_CONCEPTS}
PACKET_KEYS = {'schema_version','ticker','sec_cik','profile_key','saved_at','source_url',
    'source_observed_at','source_last_modified','raw_payload_sha256','rights_registry_sha256',
    'period_end','filing_date','accession','form','fields','gaps','receipt_id'}
ROW_KEYS = {'field','value','unit','taxonomy','concept','period_start','period_end','source_ref',
    'accession','rights_status','observed_at_utc'}


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def _digest(value):
    return hashlib.sha256(value).hexdigest()


def _hex(value):
    return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None


def _policy(path=DEFAULT_REGISTRY_PATH):
    raw=Path(path).read_bytes()
    rule=parse_source_rights_registry(raw).get('sec_companyfacts')
    if (not rule or rule.commercial_use!='approved' or rule.redistribution!='derived_data_only'
            or not set(FIELDS)<=set(rule.supported_fields)):
        raise ValueError('rights_policy_unavailable')
    return _digest(raw)


def _row_reason(row, packet):
    if not isinstance(row,dict) or set(row)!=ROW_KEYS or row.get('field') not in FIELDS:
        return 'invalid_field_schema'
    if row['unit']!='USD':return 'unit_mismatch'
    if not _finite_direct_number(row['value']):return 'invalid_direct_value'
    if (row['taxonomy'],row['concept']) not in CONCEPTS[row['field']]:return 'unsupported_concept'
    start,end=_iso_date(row['period_start']),_iso_date(row['period_end'])
    if not start or not end or not 300<=(end-start).days<=430:return 'duration_mismatch'
    if row['period_end']!=packet['period_end']:return 'period_mismatch'
    if row['accession']!=packet['accession'] or row['source_ref']!=SOURCE:return 'source_mismatch'
    if row['observed_at_utc']!=packet['source_observed_at']:return 'observation_mismatch'
    if row['rights_status']!=RIGHTS:return 'rights_mismatch'
    return None


def _validate(packet):
    if not isinstance(packet,dict) or set(packet)!=PACKET_KEYS:raise ValueError('invalid_packet_schema')
    if packet['schema_version']!=SCHEMA or packet['ticker']!='NEM' or packet['sec_cik']!=CIK or packet['source_url']!=SOURCE:
        raise ValueError('unsupported_receipt_identity')
    profile=packet['profile_key']
    if not isinstance(profile,str) or not 1<=len(profile)<=200 or any(ord(c)<32 for c in profile):raise ValueError('invalid_profile')
    saved,observed=_utc_timestamp(packet['saved_at']),_utc_timestamp(packet['source_observed_at'])
    filed,end=_iso_date(packet['filing_date']),_iso_date(packet['period_end'])
    modified=packet['source_last_modified']
    if (not saved or not observed or saved<observed or not filed or not end or not end<=filed<=observed.date()
        or modified is not None and (not _utc_timestamp(modified) or _utc_timestamp(modified)>observed)):
        raise ValueError('invalid_receipt_dates')
    if not isinstance(packet['accession'],str) or not re.fullmatch(r'\d{10}-\d{2}-\d{6}',packet['accession']) or packet['form'] not in {'10-K','10-K/A'}:
        raise ValueError('invalid_filing_anchor')
    if not all(_hex(packet[k]) for k in ('raw_payload_sha256','rights_registry_sha256','receipt_id')):
        raise ValueError('invalid_digest')
    rows,gaps=packet['fields'],packet['gaps']
    if not isinstance(rows,list) or not isinstance(gaps,list) or len(rows)+len(gaps)!=len(FIELDS):raise ValueError('invalid_field_count')
    names=[]
    for row in rows:
        reason=_row_reason(row,packet)
        if reason:raise ValueError(reason)
        names.append(row['field'])
    for gap in gaps:
        if (not isinstance(gap,dict) or set(gap)!={'field','reason'} or gap['field'] not in FIELDS
                or not isinstance(gap['reason'],str) or not re.fullmatch('[a-z_]{1,100}',gap['reason'])):
            raise ValueError('invalid_gap')
        names.append(gap['field'])
    if set(names)!=set(FIELDS) or len(set(names))!=len(names):raise ValueError('duplicate_or_missing_field')
    if packet['receipt_id']!=_digest(_json({k:v for k,v in packet.items() if k!='receipt_id'})):
        raise ValueError('receipt_checksum_mismatch')
    return packet


def capture_review(view, *, profile_key, saved_at=None, registry_path=DEFAULT_REGISTRY_PATH):
    """Copy only qualified direct fields from an existing online observation."""
    if (not isinstance(view,dict) or view.get('status')!='inspection_only' or view.get('safe_to_apply') is not False
            or view.get('ticker')!='NEM' or view.get('sec_cik')!=CIK or view.get('source_url')!=SOURCE
            or not financial_identity_valid('NEM',view.get('companyfacts_identity'))
            or view['companyfacts_identity']['sec_cik']!=CIK):raise ValueError('unqualified_nem_source')
    identity=view['companyfacts_identity']
    packet=dict(schema_version=SCHEMA,ticker='NEM',sec_cik=CIK,profile_key=profile_key,
        saved_at=saved_at or datetime.now(timezone.utc).isoformat(),source_url=SOURCE,
        source_observed_at=identity['observed_at'],source_last_modified=identity.get('source_last_modified'),
        raw_payload_sha256=identity['payload_sha256'],rights_registry_sha256=_policy(registry_path),
        period_end=view.get('period_end'),filing_date=view.get('filing_date'),accession=view.get('accession'),
        form=view.get('annual_form'),fields=[],gaps=[])
    # Upstream preview timestamps may precede completion of the HTTP request. They
    # describe the same fetch; retain the actual receipt observation on all rows.
    rows=view.get('approved_direct_fields')
    if not isinstance(rows,list) or len(rows)>32 or any(not isinstance(r,dict) for r in rows):raise ValueError('invalid_fields')
    for field in FIELDS:
        found=[r for r in rows if r.get('field')==field]
        reason='direct_field_missing' if not found else 'duplicate_direct_field' if len(found)>1 else None
        if reason is None:
            source_row=found[0]
            row={k:source_row.get(k) for k in ROW_KEYS}
            if row['observed_at_utc']!=view.get('retrieved_at_utc'):reason='observation_mismatch'
            else:
                row['observed_at_utc']=packet['source_observed_at']
                reason=_row_reason(row,packet)
        if reason:packet['gaps'].append(dict(field=field,reason=reason))
        else:packet['fields'].append(row)
    packet['receipt_id']=_digest(_json(packet))
    return _validate(packet)


def encode_review(packet):
    _validate(packet)
    raw=_json(packet)+b'\n'
    if len(raw)>MAX_BYTES:raise ValueError('receipt_too_large')
    return raw


def load_review(raw):
    """Validate a portable normalized receipt, without contacting any source."""
    if not isinstance(raw,bytes) or not 0<len(raw)<=MAX_BYTES:raise ValueError('invalid_receipt_size')
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('duplicate_json_key')
            result[key]=value
        return result
    def constant(_):raise ValueError('nonfinite_json_number')
    try:return _validate(json.loads(raw,object_pairs_hook=unique,parse_constant=constant))
    except (TypeError,KeyError,UnicodeError,RecursionError,OverflowError) as exc:raise ValueError('invalid_receipt') from exc


def _snapshot(packet, rows):
    fundamentals=tuple((r['field'],str(r['value'])) for r in rows)
    state=TickerResearchState('NEM',(),fundamentals,'','','',(),(f"sec-accession:{packet['accession']}",))
    return ResearchChangeSnapshot(SNAPSHOT_SCHEMA,packet['profile_key'],packet['receipt_id'],
        packet['source_observed_at'],packet['filing_date'],(state,))


def compare_reviews(before, after, *, registry_path=DEFAULT_REGISTRY_PATH):
    """Gate basis before using existing snapshot events; never infer missing values."""
    _validate(after)
    if before is not None:_validate(before)
    result={'status':'baseline_missing','changes':[],'gaps':list(after['gaps'])}
    try:policy=_policy(registry_path)
    except (OSError,ValueError):policy=None
    if any(p['rights_registry_sha256']!=policy for p in (before,after) if p is not None):
        return dict(status='withheld',changes=[],gaps=[dict(field='all',reason='rights_policy_changed')])
    if before is None:
        result['gaps'].append(dict(field='all',reason='baseline_missing'))
        return result
    for key in ('profile_key','ticker','sec_cik','period_end'):
        if before[key]!=after[key]:return dict(status='withheld',changes=[],gaps=[dict(field='all',reason=key+'_mismatch')])
    left={r['field']:r for r in before['fields']};right={r['field']:r for r in after['fields']}
    compatible=[];basis_held=False
    for field in FIELDS:
        a,b=left.get(field),right.get(field)
        if a is None or b is None:
            if not any(g['field']==field for g in result['gaps']):result['gaps'].append(dict(field=field,reason='prior_direct_field_missing'))
            continue
        mismatch=next((reason for keys,reason in [
            (('unit',),'unit_mismatch'),(('period_start','period_end'),'duration_mismatch'),
            (('taxonomy','concept'),'concept_mismatch'),(('rights_status',),'rights_mismatch')]
            if any(a[k]!=b[k] for k in keys)),None)
        if mismatch:
            result['gaps'].append(dict(field=field,reason=mismatch));basis_held=True
        else:compatible.append(field)
    def comparable_rows(packet):
        return [{k:v for k,v in r.items() if k!='observed_at_utc'} for r in packet['fields']]
    # Retrieval time alone is not a revision of the filing.
    if before['raw_payload_sha256']==after['raw_payload_sha256'] and comparable_rows(before)!=comparable_rows(after):
        basis_held=True
        result['gaps'].append(dict(field='all',reason='same_source_digest_conflict'))
        compatible=[]
    events=compare_research_snapshots(_snapshot(before,[left[f] for f in compatible]),_snapshot(after,[right[f] for f in compatible]))
    for field in compatible:
        a,b=left[field],right[field]
        dimensions=[k for k in ('value','accession') if a[k]!=b[k]]
        if dimensions:
            event=next((asdict(e) for e in events if e.source_ref.endswith('#'+field)),None)
            result['changes'].append(dict(field=field,before=a,after=b,changed_dimensions=dimensions,event=event))
    input_same=comparable_rows(before)==comparable_rows(after) and before['gaps']==after['gaps'] and before['accession']==after['accession']
    result['status']='withheld' if basis_held else 'changed' if result['changes'] else 'unchanged' if input_same else 'gaps_changed'
    return result


def _directory(root,profile_key):
    base=Path(root).resolve()
    path=base/'outputs'/'local'/'sec-research-reviews'/_digest(profile_key.encode())/'NEM'
    cursor=path
    while cursor!=base:
        if cursor.is_symlink():raise ValueError('symlink_receipt_store')
        cursor=cursor.parent
    return path


def list_reviews(root,profile_key):
    directory=_directory(root,profile_key)
    paths=sorted(directory.glob('*.json'))
    if len(paths)>MAX_RECEIPTS:raise ValueError('receipt_history_limit')
    result=[]
    for path in paths:
        if path.is_symlink() or path.stat().st_size>MAX_BYTES:raise ValueError('invalid_saved_receipt')
        p=load_review(path.read_bytes())
        if p['profile_key']!=profile_key or path.stem!=p['receipt_id']:raise ValueError('saved_receipt_scope_mismatch')
        result.append(p)
    return sorted(result,key=lambda p:(p['saved_at'],p['receipt_id']))


def save_review(packet,root):
    raw=encode_review(packet)
    directory=_directory(root,packet['profile_key'])
    existing=list_reviews(root,packet['profile_key'])
    target=directory/(packet['receipt_id']+'.json')
    if target.exists():
        if target.is_symlink() or target.read_bytes()!=raw:raise ValueError('immutable_receipt_conflict')
        return target
    if len(existing)>=MAX_RECEIPTS:raise ValueError('receipt_history_limit')
    directory.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as handle:handle.write(raw)
    return target
