"""Synthetic exact filings only; no real source data in distributable fixtures."""
import copy
import hashlib
import json
import pytest
from tests.test_sec_research_review import view, packet, reseal
from tests.test_sec_inline_filing import _xml, _selection
from src.sec_inline_filing import extract_inline_filing
from src.sec_exact_filing import validated_filing_preview
from src import sec_research_review as review


def gap_packet():
    v=view();v['approved_direct_fields']=[r for r in v['approved_direct_fields'] if r['field']!='operating_income']
    return packet(v)


def preview(direct=False):
    selection=_selection('annual')
    url='https://www.sec.gov/Archives/edgar/data/1164727/000116472726000010/nem-synthetic.htm'
    selection.update(ticker='NEM',sec_cik='0001164727',form='10-K',filed='2026-02-19',
        accepted_at='2026-02-19T21:18:40Z',accession='0001164727-26-000010',primary_document='nem-synthetic.htm',source_url=url)
    selection['source_receipts'][1]['source_url']='https://data.sec.gov/submissions/CIK0001164727.json'
    xml=_xml().replace('0000001234','0001164727').replace('2026-04-01','2025-01-01').replace('2026-06-30','2025-12-31').replace('2026-01-01','2025-01-01').replace('10-Q','10-K')
    if not direct:xml=xml.replace('g:OperatingIncomeLoss','g:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest')
    raw=xml.encode()
    p=extract_inline_filing(raw,selection,dict(status='ready',source_url=url,observed_at='2026-10-30T21:00:00Z',payload_sha256=hashlib.sha256(raw).hexdigest(),source_last_modified=None))
    assert validated_filing_preview(p,'NEM','annual') is not None
    return p


def attach(p=None,source=None,when='2026-11-02T22:01:00Z'):
    return review.attach_operating_income_check(p or gap_packet(),source or preview(),saved_at=when)


def test_missing_direct_fact_saved_without_archive_values_and_legacy_preserved(tmp_path):
    old=gap_packet();before=copy.deepcopy(old);new=attach(old)
    assert old==before and old['schema_version']==review.SCHEMA
    assert new['schema_version']=='sec-research-review-v2'
    assert new['fields']==old['fields']
    assert new['gaps']==[{'field':'operating_income','reason':'matching_direct_native_unit_fact_unavailable'}]
    check=new['operating_income_check']
    assert check['concept']=='OperatingIncomeLoss' and check['rights_status']=='unregistered_sec_archive_personal_inspection_only'
    assert 'value' not in check and 'raw_text' not in check
    for p in (old,new):review.save_review(p,tmp_path)
    assert review.list_reviews(tmp_path,'default')==[old,new]
    assert review.load_review(review.encode_review(new))==new
    result=review.compare_reviews(old,new)
    assert result['status']=='gaps_changed' and result['changes']==[]
    assert result['review_changes']==['operating_income_check']


def test_direct_fact_is_still_rights_held_never_imported():
    p=attach(source=preview(True))
    assert p['gaps'][0]['reason']=='exact_direct_fact_rights_held'
    assert all(r['field']!='operating_income' for r in p['fields'])


def test_identical_check_and_new_observation_unchanged():
    a=attach();source=preview();source['observed_at']='2026-10-30T21:01:00Z'
    source['source_receipts'][-1]['observed_at']=source['observed_at']
    from src.sec_inline_filing import _digest
    source['packet_digest']=_digest({k:v for k,v in source.items() if k!='packet_digest'})
    b=attach(source=source,when='2026-11-02T22:02:00Z')
    assert review.compare_reviews(a,b)['status']=='unchanged'
    assert review.compare_reviews(a,b)['review_changes']==[]


def test_changed_source_digest_is_review_change_not_financial_revision():
    a=attach();b=copy.deepcopy(a);b['operating_income_check']['payload_sha256']='d'*64;b=reseal(b)
    result=review.compare_reviews(a,b)
    assert result['status']=='review_changed' and result['changes']==[]


@pytest.mark.parametrize('key,value',[('accession','0001164727-26-000011'),('filing_date','2026-02-20'),('form','10-K/A'),('period_end','2025-12-30')])
def test_mismatched_anchor_keeps_original_gap(key,value):
    p=gap_packet();p[key]=value
    if key=='accession':
        for r in p['fields']:r[key]=value
    if key=='period_end':
        for r in p['fields']:r[key]=value
    p=reseal(p);original=copy.deepcopy(p)
    with pytest.raises(ValueError):attach(p)
    assert p==original


@pytest.mark.parametrize('mutate',[
    lambda p:p['operating_income_check'].update(value=123),
    lambda p:p['operating_income_check'].update(unit='EUR'),
    lambda p:p['operating_income_check'].update(period_start='2025-02-01'),
    lambda p:p['operating_income_check'].update(source_url='https://evil.example/file.htm'),
    lambda p:p['operating_income_check'].update(rights_status='approved'),
    lambda p:p['operating_income_check'].update(observed_at='2030-01-01T00:00:00Z'),
    lambda p:p['operating_income_check'].update(reason='pretax_is_operating_income'),
    lambda p:p['gaps'][0].update(reason='direct_field_missing'),
])
def test_malformed_check_rejected_even_with_resealed_checksum(mutate):
    p=attach();mutate(p)
    with pytest.raises(ValueError):review.load_review(json.dumps(reseal(p)).encode())


def test_unqualified_source_or_present_approved_field_not_overridden():
    for p,s in [(packet(),preview()),(gap_packet(),{'status':'withheld'})]:
        with pytest.raises(ValueError):attach(p,s)


@pytest.mark.parametrize('key,value',[('sec_cik','0000001234'),('unit','EUR'),('taxonomy','ifrs-full'),('period_start','2025-02-01')])
def test_check_import_never_crosses_identity_currency_definition_duration(key,value):
    p=attach();p['operating_income_check'][key]=value
    with pytest.raises(ValueError):review.load_review(json.dumps(reseal(p)).encode())


def test_conflicting_facts_and_unusable_numeric_proofs_stay_distinct_gaps():
    from src.sec_inline_filing import _digest
    for reason,expected in [('conflicting_direct_facts','conflicting_direct_facts'),('source_fact_id_unavailable','exact_direct_fact_unusable')]:
        source=preview();source['periods'][0]['withheld_fields']['operating_income']=reason
        source['packet_digest']=_digest({k:v for k,v in source.items() if k!='packet_digest'})
        p=attach(source=source)
        assert p['gaps'][0]['reason']==expected
        assert review.compare_reviews(p,p)['status']=='unchanged'


def test_valid_next_business_day_filing_date_roundtrips():
    from src.sec_inline_filing import _digest
    source=preview();source['accepted_at']='2026-02-18T23:00:00Z'
    source['packet_digest']=_digest({k:v for k,v in source.items() if k!='packet_digest'})
    assert validated_filing_preview(source,'NEM','annual') is not None
    p=attach(source=source)
    assert review.load_review(review.encode_review(p))==p
    assert review.compare_reviews(p,p)['status']=='unchanged'


def test_acceptance_before_report_period_rejected():
    p=attach();p['operating_income_check']['accepted_at']='2025-01-01T23:00:00Z'
    with pytest.raises(ValueError):review.load_review(json.dumps(reseal(p)).encode())
