import json
from copy import deepcopy
from datetime import datetime,timezone

import pytest

from test_sec_inline_filing import _xml,OBSERVED

MAP='https://www.sec.gov/files/company_tickers.json'
SUB='https://data.sec.gov/submissions/CIK0000001234.json'
URL='https://www.sec.gov/Archives/edgar/data/1234/000000432126000001/fict-20260630.htm'


def _submission():
    return {'cik':'0000001234','filings':{'recent':{
        'accessionNumber':['0000004321-26-000001'], 'reportDate':['2026-06-30'],
        'filingDate':['2026-08-01'],'acceptanceDateTime':['2026-08-01T12:00:00Z'],
        'form':['10-Q'],'primaryDocument':['fict-20260630.htm'],'isInlineXBRL':[1],'isXBRL':[1]}}}


def _receipt(payload=None):
    return dict(status='ready',payload=payload or _submission(),source_url=SUB,observed_at='2026-10-30T21:00:00Z',payload_sha256='a'*64)


def _fetch(calls,submission=None,document=None):
    def fetch(url,agent):
        calls.append(url)
        if url==MAP:return json.dumps({'0':{'ticker':'FICT','cik_str':1234}}).encode(),{},url
        if url==SUB:return json.dumps(submission or _submission()).encode(),{},url
        assert url==URL
        return (document or _xml()).encode(),{},url
    return fetch


def test_selection_binds_issuer_directory_to_agent_accession_and_publication():
    from src.sec_exact_filing import select_sec_filing
    s=select_sec_filing('FICT','0000001234',_receipt(),period_kind='quarterly')
    assert s['status']=='selected' and s['source_url']==URL
    assert s['accession']=='0000004321-26-000001'
    assert s['period_end']=='2026-06-30' and s['accepted_at']=='2026-08-01T12:00:00Z'


@pytest.mark.parametrize('problem',['accession','document','acceptance','period','arrays','tie'])
def test_newest_ambiguous_or_malformed_amendment_never_falls_back(problem):
    from src.sec_exact_filing import select_sec_filing
    body=_submission();r=body['filings']['recent']
    for key,values in r.items():values.append(values[0])
    r['form'][1]='10-Q/A';r['filingDate'][1]='2026-09-01';r['acceptanceDateTime'][1]='2026-09-01T12:00:00Z';r['accessionNumber'][1]='0000004321-26-000002'
    if problem=='accession':r['accessionNumber'][1]='bad'
    elif problem=='document':r['primaryDocument'][1]='../../outside.htm'
    elif problem=='acceptance':r['acceptanceDateTime'][1]='bad'
    elif problem=='period':r['reportDate'][1]='bad'
    elif problem=='arrays':r['isInlineXBRL'].pop()
    else:
        for key,values in r.items():values.append(values[1])
        r['accessionNumber'][2]='0000004321-26-000003'
    assert select_sec_filing('FICT','0000001234',_receipt(body),period_kind='quarterly')['status']=='withheld'


def test_fetch_pipeline_is_exact_bounded_personal_and_writes_no_company_files(tmp_path,monkeypatch):
    from src.sec_exact_filing import fetch_sec_filing_preview
    monkeypatch.chdir(tmp_path);calls=[]
    p=fetch_sec_filing_preview('FICT',period_kind='quarterly',user_agent='Research contact',fetcher=_fetch(calls),observed_at=OBSERVED)
    assert p['status']=='inspection_only' and calls==[MAP,SUB,URL]
    assert p['periods'][0]['fields']['revenue']['value']==1234000000
    assert len(p['source_receipts'])==3 and not list(tmp_path.iterdir())
    calls.clear()
    assert fetch_sec_filing_preview('FICT',period_kind='quarterly',user_agent='Research',fetcher=_fetch(calls),expected_cik='0000009999',observed_at=OBSERVED)['status']=='withheld'
    assert URL not in calls


def test_redirect_source_size_and_commercial_boundaries_hold_without_data(monkeypatch):
    from src import sec_exact_filing as source
    for problem in ['redirect','size']:
        calls=[];base=_fetch(calls)
        def fetch(url,agent):
            raw,headers,final=base(url,agent)
            if url==URL:
                if problem=='redirect':final='https://example.invalid/filing'
                else:raw=b'X'*(source.MAX_FILING_BYTES+1)
            return raw,headers,final
        assert source.fetch_sec_filing_preview('FICT',period_kind='quarterly',user_agent='Research',fetcher=fetch,observed_at=OBSERVED)['status']=='withheld'
    monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE','1')
    assert source.fetch_sec_filing_preview('FICT',period_kind='quarterly',user_agent='Research',fetcher=lambda *a:pytest.fail('blocked source requested'))['status']=='withheld'


def test_sec_next_business_day_filing_date_preserves_earlier_acceptance_timestamp():
    from src.sec_exact_filing import select_sec_filing
    body=_submission();r=body['filings']['recent']
    r['filingDate'][0]='2026-08-03';r['acceptanceDateTime'][0]='2026-07-31T22:00:00Z'
    selection=select_sec_filing('FICT','0000001234',_receipt(body),period_kind='quarterly')
    assert selection['status']=='selected'
    assert selection['filed']=='2026-08-03' and selection['accepted_at']=='2026-07-31T22:00:00Z'
