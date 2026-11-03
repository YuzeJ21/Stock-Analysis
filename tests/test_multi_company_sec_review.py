"""Synthetic issuer observations; no real financial fixtures."""
import copy
import json
import pytest
from tests.test_sec_research_review import view, packet, reseal
from src import sec_research_review as review


def issuer_view(ticker='AMD',cik='0000002488'):
    v=copy.deepcopy(view());source=f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'
    v.update(ticker=ticker,sec_cik=cik,source_url=source,accession=f'{cik}-26-000001')
    v['companyfacts_identity'].update(ticker=ticker,sec_cik=cik,source_url=source)
    for row in v['approved_direct_fields']:row.update(source_ref=source,accession=v['accession'])
    return v


def capture(ticker='AMD',cik='0000002488',profile='test',when='2026-11-02T22:00:00Z'):
    return review.capture_review(issuer_view(ticker,cik),profile_key=profile,saved_at=when)


def test_multiple_issuers_roundtrip_without_cross_company_comparison(tmp_path):
    a=capture();b=capture('DUK','0001326160')
    assert a['schema_version']=='sec-research-review-v3'
    assert a['companyfacts_identity']==issuer_view()['companyfacts_identity']
    for p in (a,b):
        path=review.save_review(p,tmp_path);assert review.load_review(path.read_bytes())==p
        assert review.list_reviews(tmp_path,'test',p['ticker'])==[p]
    assert review.list_reviews(tmp_path,'other','AMD')==[]
    result=review.compare_reviews(a,b)
    assert result['status']=='withheld' and result['changes']==[]
    assert result['gaps']==[{'field':'all','reason':'ticker_mismatch'}]
    assert not (tmp_path/'data').exists()


def test_legacy_nem_and_generic_store_coexist(tmp_path):
    old=packet();a=capture(profile='default')
    for p in (old,a):review.save_review(p,tmp_path)
    assert review.list_reviews(tmp_path,'default')==[old]
    assert review.list_reviews(tmp_path,'default','AMD')==[a]
    assert review.compare_reviews(a,a)['status']=='unchanged'


@pytest.mark.parametrize('change',[
    lambda p:p.update(ticker='NVDA'),
    lambda p:p.update(sec_cik='0001045810'),
    lambda p:p['companyfacts_identity'].update(association_source_url='https://invalid.test/map'),
    lambda p:p['companyfacts_identity'].update(association_payload_sha256='bad'),
    lambda p:p['companyfacts_identity'].update(association_observed_at='2026-01-01T00:00:00Z'),
    lambda p:p['companyfacts_identity'].update(payload_sha256='c'*64),
    lambda p:p['companyfacts_identity'].update(raw_payload='not permitted'),
    lambda p:p['fields'][0].update(source_ref=review.SOURCE),
    lambda p:p['fields'][0].update(taxonomy='ifrs-full'),
])
def test_generic_import_requires_exact_association_and_source_binding(change):
    p=capture();change(p)
    with pytest.raises(ValueError):review.load_review(json.dumps(reseal(p)).encode())


@pytest.mark.parametrize('change',[
    lambda v:v.update(annual_form='20-F'),
    lambda v:v['approved_direct_fields'][0].update(unit='EUR'),
    lambda v:v['approved_direct_fields'].clear(),
    lambda v:v.update(ticker='../AMD'),
    lambda v:v['companyfacts_identity'].update(ticker='OTHER'),
])
def test_unsupported_financial_basis_cannot_become_qualified_receipt(change):
    v=issuer_view();change(v)
    with pytest.raises(ValueError):review.capture_review(v,profile_key='test')


def test_nem_exact_source_exception_cannot_attach_to_other_issuer():
    from tests.test_nem_operating_income_review import preview
    v=issuer_view();v['approved_direct_fields'].pop(1)
    p=review.capture_review(v,profile_key='test')
    with pytest.raises(ValueError):review.attach_operating_income_check(p,preview())


def test_generic_value_change_reuses_correct_ticker_event():
    a=capture();v=issuer_view();v['approved_direct_fields'][0]['value']=150
    v['companyfacts_identity']['payload_sha256']='c'*64
    b=review.capture_review(v,profile_key='test')
    result=review.compare_reviews(a,b)
    assert result['status']=='changed'
    assert result['changes'][0]['event']['ticker']=='AMD'


def test_new_observation_is_unchanged_but_association_digest_is_review_change():
    a=capture();v=issuer_view();v['retrieved_at_utc']='2026-11-02T21:05:00Z'
    v['companyfacts_identity']['observed_at']=v['retrieved_at_utc']
    for r in v['approved_direct_fields']:r['observed_at_utc']=v['retrieved_at_utc']
    b=review.capture_review(v,profile_key='test')
    assert review.compare_reviews(a,b)['status']=='unchanged'
    v['companyfacts_identity']['association_payload_sha256']='e'*64
    c=review.capture_review(v,profile_key='test');result=review.compare_reviews(b,c)
    assert result['status']=='review_changed' and not result['changes']
    assert result['review_changes']==['issuer_association']


def test_queue_separates_field_gaps_baselines_and_corrupt_company(tmp_path):
    a=capture();review.save_review(a,tmp_path)
    b=capture('DUK','0001326160');b['fields'].pop();b['gaps']=[dict(field='capital_expenditures',reason='direct_field_missing')];b=reseal(b)
    review.save_review(b,tmp_path)
    c=capture('FICT','0000001234');path=review.save_review(c,tmp_path);path.write_bytes(b'{}')
    q=review.review_queue(tmp_path,'test')
    assert q['companies']==3 and q['field_gap_companies']==1 and q['baseline_companies']==2 and q['unreadable_companies']==1
    assert next(i for i in q['items'] if i['ticker']=='FICT')['error']=='saved_receipts_unreadable'
    assert next(i for i in q['items'] if i['ticker']=='AMD')['latest']==a
    assert review.review_queue(tmp_path,'other')['companies']==0


def test_company_capacity_rejects_new_company_but_existing_can_save(tmp_path,monkeypatch):
    monkeypatch.setattr(review,'MAX_COMPANIES',1)
    a=capture();review.save_review(a,tmp_path)
    with pytest.raises(ValueError,match='company_history_limit'):review.save_review(capture('DUK','0001326160'),tmp_path)
    review.save_review(capture(when='2026-11-02T22:01:00Z'),tmp_path)
    assert len(review.list_reviews(tmp_path,'test','AMD'))==2


def test_symlink_company_is_held_without_hiding_readable_company(tmp_path):
    review.save_review(capture(),tmp_path)
    path=review._directory(tmp_path,'test','DUK');outside=tmp_path/'outside';outside.mkdir();path.symlink_to(outside,target_is_directory=True)
    q=review.review_queue(tmp_path,'test')
    assert q['companies']==2 and q['unreadable_companies']==1
    assert q['items'][0]['ticker']=='AMD'
    with pytest.raises(ValueError):review.save_review(capture('DUK','0001326160'),tmp_path)


@pytest.mark.parametrize('ticker',['../AMD','A/B','..','nem','',None])
def test_paths_reject_invalid_symbols(tmp_path,ticker):
    with pytest.raises(ValueError):review.list_reviews(tmp_path,'test',ticker)


def test_numeric_company_symlink_cannot_block_profile_inventory(tmp_path):
    review.save_review(capture(),tmp_path)
    path=review._directory(tmp_path,'test','0');outside=tmp_path/'outside';outside.mkdir();path.symlink_to(outside,target_is_directory=True)
    q=review.review_queue(tmp_path,'test')
    assert q['companies']==2 and q['unreadable_companies']==1
    assert next(i for i in q['items'] if i['ticker']=='AMD')['latest']['ticker']=='AMD'


def test_same_symbol_with_different_issuer_is_held():
    a=capture();b=capture('AMD','0001045810')
    result=review.compare_reviews(a,b)
    assert result['status']=='withheld' and result['gaps']==[{'field':'all','reason':'sec_cik_mismatch'}]


def test_receipt_moved_to_wrong_company_directory_is_not_replayed(tmp_path):
    p=capture();saved=review.save_review(p,tmp_path)
    other=review._directory(tmp_path,'test','DUK');other.mkdir()
    (other/saved.name).write_bytes(saved.read_bytes())
    with pytest.raises(ValueError,match='saved_receipt_scope_mismatch'):review.list_reviews(tmp_path,'test','DUK')
    q=review.review_queue(tmp_path,'test')
    assert q['unreadable_companies']==1 and q['companies']==2
