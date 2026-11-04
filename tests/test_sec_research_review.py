"""Synthetic inputs only: portable NEM review behavior, never company claims."""
import copy
import json
from datetime import datetime, timezone
import pytest
from src import sec_research_review as review


def view():
    source='https://data.sec.gov/api/xbrl/companyfacts/CIK0001164727.json'
    observed='2026-11-02T21:00:00Z'
    rows=[]
    for name,concept,value in [('revenue','Revenues',100),('operating_income','OperatingIncomeLoss',20),
        ('cash_from_operations','NetCashProvidedByUsedInOperatingActivities',30),
        ('capital_expenditures','PaymentsToAcquirePropertyPlantAndEquipment',10)]:
        rows.append(dict(field=name,value=value,unit='USD',taxonomy='us-gaap',concept=concept,
            period_start='2025-01-01',period_end='2025-12-31',source_ref=source,
            accession='0001164727-26-000010',rights_status='approved_field_scope_raw_redistribution_held',
            observed_at_utc=observed,canonical_schema_status='review_required'))
    return dict(status='inspection_only',ticker='NEM',sec_cik='0001164727',source_url=source,
        safe_to_apply=False,retrieved_at_utc=observed,filing_date='2026-02-19',period_end='2025-12-31',
        accession='0001164727-26-000010',annual_form='10-K',approved_direct_fields=rows,withheld_fields=[],
        companyfacts_identity=dict(status='source_matched',ticker='NEM',sec_cik='0001164727',source_url=source,
            observed_at=observed,source_last_modified='2026-11-02T20:00:00Z',payload_sha256='a'*64,
            association_source_url='https://www.sec.gov/files/company_tickers.json',association_payload_sha256='b'*64,
            association_observed_at='2026-11-02T20:59:00Z'))


def packet(v=None,when='2026-11-02T22:00:00Z'):
    return review.capture_review(v or view(),profile_key='default',saved_at=when)


def test_capture_roundtrip_and_identical_inputs_unchanged(tmp_path):
    a=packet(); b=packet(when='2026-11-02T22:01:00Z')
    assert a['receipt_id']!=b['receipt_id']
    path=review.save_review(a,tmp_path)
    assert review.load_review(path.read_bytes())==a
    result=review.compare_reviews(a,b)
    assert result['status']=='unchanged' and result['changes']==[] and result['gaps']==[]
    assert review.list_reviews(tmp_path,'other')==[]
    assert len(review.list_reviews(tmp_path,'default'))==1
    review.save_review(a,tmp_path)
    assert len(review.list_reviews(tmp_path,'default'))==1
    assert not (tmp_path/'data').exists()


def test_compatible_value_change_reuses_evidence_events():
    v=view(); v['approved_direct_fields'][0]['value']=120
    v['companyfacts_identity']['payload_sha256']='c'*64
    result=review.compare_reviews(packet(),packet(v))
    assert result['status']=='changed'
    assert result['changes'][0]['field']=='revenue'
    assert result['changes'][0]['before']['value']==100
    assert result['changes'][0]['after']['value']==120
    assert result['changes'][0]['event']['family']=='fundamentals'


@pytest.mark.parametrize('field,value,reason',[
    ('unit','EUR','unit_mismatch'),('period_start','2025-02-01','duration_mismatch'),
    ('concept','SalesRevenueNet','concept_mismatch')])
def test_mismatched_basis_is_gap_not_value_change(field,value,reason):
    v=view(); v['approved_direct_fields'][0][field]=value
    result=review.compare_reviews(packet(),packet(v))
    assert result['status']=='withheld'
    assert any(reason in x['reason'] for x in result['gaps'])
    assert not result['changes']


def test_missing_field_remains_gap_and_identical_missing_input_unchanged():
    v=view();v['approved_direct_fields'].pop()
    a=packet(v);result=review.compare_reviews(a,a)
    assert result['status']=='unchanged'
    assert result['gaps'][0]['field']=='capital_expenditures'


@pytest.mark.parametrize('mutate',[
    lambda v:v.update(ticker='NEMCL'),lambda v:v.update(sec_cik='0000000001'),
    lambda v:v['companyfacts_identity'].update(payload_sha256='bad'),
    lambda v:v['companyfacts_identity'].update(sec_cik='0000000001'),
    lambda v:v.update(safe_to_apply=True)])
def test_wrong_identity_or_unqualified_source_rejected(mutate):
    v=view();mutate(v)
    with pytest.raises(ValueError):packet(v)


def test_tamper_duplicate_keys_nonfinite_and_oversize_rejected():
    p=packet();p['fields'][0]['value']=999
    for raw in [json.dumps(p).encode(),b'{"schema":1,"schema":2}',b'{"x":NaN}',b' '*100000]:
        with pytest.raises(ValueError):review.load_review(raw)


def test_changed_registry_withholds_replay_comparison(tmp_path):
    p=packet();raw=review.encode_review(p)
    registry=tmp_path/'rights.yml';registry.write_text('sources: []\n')
    assert review.load_review(raw)==p
    result=review.compare_reviews(p,p,registry_path=registry)
    assert result['status']=='withheld' and not result['changes']
    assert any(x['reason']=='rights_policy_changed' for x in result['gaps'])


def test_unknown_payload_material_cannot_be_retained():
    p=packet();p['prices']=[1,2]
    with pytest.raises(ValueError):review.encode_review(p)


def test_profile_and_period_mismatch_withheld():
    a=packet();b=review.capture_review(view(),profile_key='other',saved_at='2026-11-02T22:00:00Z')
    assert review.compare_reviews(a,b)['status']=='withheld'


def test_damaged_saved_receipt_is_visible_error(tmp_path):
    p=review.save_review(packet(),tmp_path);p.write_bytes(b'{}')
    with pytest.raises(ValueError):review.list_reviews(tmp_path,'default')


def test_new_observation_of_same_response_is_unchanged():
    v=view();v['retrieved_at_utc']='2026-11-02T21:10:00Z'
    v['companyfacts_identity']['observed_at']=v['retrieved_at_utc']
    for row in v['approved_direct_fields']:row['observed_at_utc']=v['retrieved_at_utc']
    result=review.compare_reviews(packet(),packet(v))
    assert result['status']=='unchanged' and not result['changes']


def reseal(p):
    import hashlib
    p=copy.deepcopy(p)
    p.pop('receipt_id')
    raw=json.dumps(p,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
    p['receipt_id']=hashlib.sha256(raw).hexdigest()
    return p


def test_import_field_order_does_not_create_changes():
    p=packet();q=copy.deepcopy(p);q['fields'].reverse();q=reseal(q)
    assert review.compare_reviews(p,review.load_review(json.dumps(q).encode()))['status']=='unchanged'


def test_saved_history_uses_chronological_utc_order(tmp_path):
    a=packet(when='2026-11-02T22:00:00Z');b=packet(when='2026-11-02T22:00:00.500000+00:00')
    review.save_review(a,tmp_path);review.save_review(b,tmp_path)
    assert [p['receipt_id'] for p in review.list_reviews(tmp_path,'default')]==[a['receipt_id'],b['receipt_id']]


def test_existing_store_file_is_an_error_not_empty(tmp_path):
    p=review.save_review(packet(),tmp_path);directory=p.parent
    p.unlink();directory.rmdir();directory.write_bytes(b'not a directory')
    with pytest.raises((ValueError,OSError)):review.list_reviews(tmp_path,'default')


def test_inaccessible_store_is_an_error_not_empty(tmp_path):
    p=review.save_review(packet(),tmp_path);directory=p.parent
    directory.chmod(0)
    try:
        with pytest.raises((ValueError,OSError)):review.list_reviews(tmp_path,'default')
    finally:directory.chmod(0o700)


def test_import_cannot_mix_component_durations():
    p=packet();p['fields'][1]['period_start']='2025-02-01';p=reseal(p)
    with pytest.raises(ValueError):review.load_review(json.dumps(p).encode())


def test_capture_withholds_mixed_duration_and_preserves_source_conflict():
    v=view();v['approved_direct_fields'][1]['period_start']='2025-02-01'
    p=packet(v)
    assert {'field':'operating_income','reason':'duration_mismatch'} in p['gaps']
    v=view();v['approved_direct_fields'].pop(1)
    v['withheld_fields']=[dict(field='operating_income',reason='raw_source_conflict')]
    assert {'field':'operating_income','reason':'raw_source_conflict'} in packet(v)['gaps']
