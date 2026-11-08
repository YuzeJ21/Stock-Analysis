"""A held USD preview cannot erase an independently matched native source identity."""
from copy import deepcopy
from datetime import datetime, timezone
import json

import pytest

from src.sec_annual_history import fetch_sec_online_research_view
from src.online_company_identity import financial_identity_valid
from src.sec_foreign_financials import validated_foreign_financials
from test_sec_industry_financials import _foreign_payload

NOW=datetime(2026,11,8,12,tzinfo=timezone.utc)
CIK='0000001234'
MAP='https://www.sec.gov/files/company_tickers.json'
FACTS=f'https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json'
PROFILE=f'https://data.sec.gov/submissions/CIK{CIK}.json'


def _profile():
    rows=[('20-F','2025-12-31','2026-03-01','0000001234-26-000001'),
          ('6-K','2026-08-20','2026-08-01','0000001234-26-000002')]
    return dict(cik=1234,tickers=['FICT'],name='Constructed native issuer',sic='3571',entityType='operating',
        filings={'recent':dict(form=[r[0] for r in rows],reportDate=[r[1] for r in rows],
            filingDate=[r[2] for r in rows],accessionNumber=[r[3] for r in rows],
            acceptanceDateTime=[r[2]+'T12:00:00Z' for r in rows],primaryDocument=['annual.htm','results.htm'])})


def _fetch(payload=None, *, unavailable=False, mapping=None):
    sources={MAP:{'0':{'ticker':'FICT','cik_str':1234}} if mapping is None else mapping,
             FACTS:_foreign_payload() if payload is None else payload,PROFILE:_profile()}
    calls=[]
    def fetch(url,agent):
        assert agent=='Constructed research contact'
        calls.append(url)
        if unavailable and url==FACTS: raise RuntimeError('Constructed Companyfacts unavailable')
        assert url in sources, 'Unexpected source transport'
        return json.dumps(sources[url]).encode(),{},url
    return fetch,calls


@pytest.mark.parametrize('currency',['EUR','TWD'])
def test_unavailable_usd_annual_keeps_exact_matched_identity_for_native_financials(currency):
    payload=_foreign_payload()
    if currency!='EUR':
        for fact in payload['facts']['ifrs-full'].values():
            if 'EUR' in fact['units']: fact['units'][currency]=fact['units'].pop('EUR')
    before=deepcopy(payload)
    fetch,calls=_fetch(payload)
    view=fetch_sec_online_research_view('FICT',user_agent='Constructed research contact',source_fetcher=fetch,observed_at=NOW)
    assert view['status']=='unavailable' and view['reason']=='invalid_annual_source_anchor'
    assert view['ticker']=='FICT' and view['sec_cik']==CIK
    assert financial_identity_valid('FICT',view['companyfacts_identity'])
    assert view['companyfacts_identity']['sec_cik']==view['sec_cik']
    assert view['approved_direct_fields']==[] and view['safe_to_apply'] is False
    assert 'annual_history' not in view
    foreign=validated_foreign_financials(view)
    assert foreign is not None and foreign['unit']==currency
    assert foreign['annual'][-1]['fields']['revenue']['value']==100
    assert view['filing_coverage']['current']['annual']['status']=='corroborated'
    assert calls==[MAP,FACTS,PROFILE]
    assert payload==before


def test_wrong_companyfacts_cik_cannot_acquire_view_identity_from_mapping_alone():
    payload=_foreign_payload(); payload['cik']=9999
    fetch,calls=_fetch(payload)
    view=fetch_sec_online_research_view('FICT',user_agent='Constructed research contact',source_fetcher=fetch,observed_at=NOW)
    assert view['companyfacts_identity']==dict(status='withheld',reason='companyfacts_identity_mismatch')
    assert view.get('sec_cik') is None and 'foreign_financials' not in view
    assert calls==[MAP,FACTS]


def test_unavailable_companyfacts_keeps_catalog_independent_without_facts_identity():
    fetch,calls=_fetch(unavailable=True)
    view=fetch_sec_online_research_view('FICT',user_agent='Constructed research contact',source_fetcher=fetch,observed_at=NOW)
    assert view['status']=='unavailable'
    assert view.get('sec_cik') is None and 'companyfacts_identity' not in view
    assert 'foreign_financials' not in view
    assert view['filing_inventory']['status']=='inspection_only'
    assert view['filing_coverage']['current']['annual']['status']=='withheld'
    assert view['approved_direct_fields']==[]
    assert calls==[MAP,FACTS,PROFILE]


def test_ambiguous_map_cannot_promote_native_source_identity():
    fetch,calls=_fetch(mapping={'0':{'ticker':'FICT','cik_str':1234},'1':{'ticker':'FICT','cik_str':9999}})
    with pytest.raises(ValueError,match='Ambiguous SEC ticker association'):
        fetch_sec_online_research_view('FICT',user_agent='Constructed research contact',source_fetcher=fetch,observed_at=NOW)
    assert calls==[MAP]
