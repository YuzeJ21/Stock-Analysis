from copy import deepcopy
from datetime import timedelta
import base64,hashlib,json
import pytest
from test_online_peer_valuation import collection,NOW,issuer,build,digest

CIK='0000001001'
URL='https://data.sec.gov/submissions/CIK0000001001-submissions-001.json'

SO_PARENT = '0000092122'
SO_CHILD = '0001160661'
SO_ACCESSION = '0000092122-25-000084'
SO_EXHIBIT = 'https://cdn.yahoofinance.com/prod/sec-filings/0001160661/000009212225000084/so-20250930.htm'
SO_INDICES = [f'https://www.sec.gov/Archives/edgar/data/{cik}/000009212225000084/{SO_ACCESSION}-index.htm'
              for cik in ('92122', '1160661')]


@pytest.fixture
def so_joint(monkeypatch):
    from src import online_peer_sec_history

    row = issuer('SO', SO_PARENT, 30)
    recent = row['profile']['payload']['filings']['recent']
    recent.update(acceptanceDateTime=['2026-02-01T12:00:00Z'], isInlineXBRL=[1], isXBRL=[1])
    joint = dict(form='10-Q', reportDate='2025-09-30', filingDate='2025-10-30',
        acceptanceDateTime='2025-10-29T21:40:57.000Z', accessionNumber=SO_ACCESSION,
        primaryDocument='so-20250930.htm', isInlineXBRL=1, isXBRL=1)
    for key, value in joint.items():
        recent[key].append(value)
    vendor = row['vendor']
    vendor['payload']['filings'] = [dict(type='10-Q', date='2025-10-30',
        edgarUrl=f'https://finance.yahoo.com/sec-filing/SO/{SO_ACCESSION}_92122',
        exhibits={'10-Q': SO_EXHIBIT})]
    vendor['normalized_sha256'] = digest(vendor['payload'])
    raw = b'<html><body>Constructed index bytes for two co-registrants</body></html>'
    monkeypatch.setattr(online_peer_sec_history, '_SO_INDEX_SHA256', hashlib.sha256(raw).hexdigest(), raising=False)
    return row, raw


def _capture_joint(row, transport):
    from src.online_peer_sec_history import fetch_vendor_history_match
    return fetch_vendor_history_match(SO_PARENT, row['profile'], row['vendor'],
        user_agent='Synthetic contact', observed_at=NOW, fetcher=transport)


def test_so_joint_identity_keeps_parent_annual_eps_and_discloses_both_indices(so_joint):
    from src.online_peer_valuation import _annual_eps, _filings, _vendor_identity
    from src.online_peer_valuation_ui import _history_html

    row, raw = so_joint
    requests = []
    def transport(url, agent):
        requests.append(url)
        return raw, {}, url

    row['vendor_history'] = _capture_joint(row, transport)
    assert requests == SO_INDICES
    filings = _filings(row['profile']['payload'], NOW)
    identity = _vendor_identity(row, row['vendor']['payload'], filings, 'SO', SO_PARENT, NOW)
    assert identity['accession'] == SO_ACCESSION
    assert identity['joint_filing']['co_registrant_cik'] == SO_CHILD
    assert identity['joint_filing']['exhibit_ref'] == SO_EXHIBIT
    assert [ref['source_url'] for ref in identity['joint_filing']['indices']] == SO_INDICES
    assert identity['financial_denominator_modified'] is False
    annual = _annual_eps(row['facts']['payload'], filings, NOW.date())
    assert (annual['form'], annual['accession'], annual['eps']) == ('10-K', '0000092122-26-000001', 1.0)
    html = _history_html(identity)
    assert 'SEC joint filing match' in html and all(url in html for url in SO_INDICES)


@pytest.mark.parametrize('change', ['child_index_bytes', 'redirect', 'wrong_exhibit_cik',
    'wrong_accession', 'wrong_form', 'wrong_receipt_date', 'parent_metadata', 'duplicate_provider_row'])
def test_so_joint_match_rejects_unreviewed_vendor_scope_and_index_receipt(so_joint, change):
    from src.online_peer_valuation import _filings, _vendor_identity

    row, raw = so_joint
    vendor = row['vendor']['payload']['filings'][0]
    if change == 'wrong_exhibit_cik':
        vendor['exhibits']['10-Q'] = SO_EXHIBIT.replace(SO_CHILD, '0000003153')
    elif change == 'wrong_accession':
        vendor['edgarUrl'] = vendor['edgarUrl'].replace('000084', '000076')
    elif change == 'wrong_form':
        vendor.update(type='10-K', exhibits={'10-K': SO_EXHIBIT})
    elif change == 'parent_metadata':
        row['profile']['payload']['filings']['recent']['reportDate'][1] = '2025-06-30'
    elif change == 'duplicate_provider_row':
        row['vendor']['payload']['filings'].append(deepcopy(vendor))
    row['vendor']['normalized_sha256'] = digest(row['vendor']['payload'])

    def transport(url, agent):
        if url == SO_INDICES[1] and change == 'child_index_bytes':
            return raw + b'changed', {}, url
        if url == SO_INDICES[1] and change == 'redirect':
            return raw, {}, SO_INDICES[0]
        return raw, {}, url

    row['vendor_history'] = _capture_joint(row, transport)
    if change == 'wrong_receipt_date':
        row['vendor_history']['indices'][1]['observed_at'] = '2026-09-01T00:00:00Z'
    filings = _filings(row['profile']['payload'], NOW)
    with pytest.raises(ValueError, match='vendor_filing_not_matched_to_sec|vendor_joint_filing'):
        _vendor_identity(row, row['vendor']['payload'], filings, 'SO', SO_PARENT, NOW)


def history_fixture():
    c=collection();row=c['issuers'][0];old=deepcopy(row['vendor']['payload']['filings'][0]);acc='0000001001-25-000003'
    old.update(date='2025-02-01',edgarUrl=f'https://finance.yahoo.com/sec-filing/FICT/{acc}_1001',exhibits={'10-K':f'https://cdn.yahoofinance.com/prod/sec-filings/{CIK}/{acc.replace("-","")}/old.htm'})
    row['vendor']['payload']['filings']=[old];row['vendor']['normalized_sha256']=digest(row['vendor']['payload'])
    row['profile']['payload']['filings']['files']=[dict(name='CIK0000001001-submissions-001.json',filingCount=1,filingFrom='2025-01-01',filingTo='2025-12-31')]
    row['profile']['normalized_sha256']=digest(row['profile']['payload'])
    meta=dict(form='10-K',reportDate='2024-12-31',filingDate='2025-02-01',acceptanceDateTime='2025-02-01T12:00:00Z',accessionNumber=acc,primaryDocument='old.htm',isInlineXBRL=1,isXBRL=1)
    raw=json.dumps({k:[v] for k,v in meta.items()}).encode()
    return c,row,raw


def fetch(row,raw,**kwargs):
    from src.online_peer_sec_history import fetch_vendor_history_match
    return fetch_vendor_history_match(CIK,row['profile'],row['vendor'],user_agent='Synthetic contact',observed_at=NOW,fetcher=kwargs.pop('fetcher',lambda url,agent:(raw,{},url)),**kwargs)


def validate(row,packet,**kwargs):
    from src.online_peer_sec_history import validated_vendor_history_match
    return validated_vendor_history_match(packet,cik=CIK,profile=row['profile'],vendor=row['vendor'],as_of=kwargs.pop('as_of',NOW),**kwargs)


def test_exact_old_vendor_identity_is_bound_without_replacing_latest_annual_eps():
    c,row,raw=history_fixture();before=deepcopy(row['profile']);row['vendor_history']=fetch(row,raw)
    matched=validate(row,row['vendor_history']);assert len(matched)==1 and matched[0]['accessionNumber']=='0000001001-25-000003'
    result=build(c);assert result['subject']['accession']=='0000001001-26-000001' and result['subject']['multiple']==30
    assert result['subject']['vendor_filing']['accession']=='0000001001-25-000003'
    assert result['subject']['vendor_filing']['history_source_ref']==URL and row['profile']==before


@pytest.mark.parametrize('change',[
    lambda row,p:p['receipt'].update(payload_sha256='e'*64),
    lambda row,p:p['receipt'].update(source_url=URL.replace('1001-','9999-')),
    lambda row,p:p['receipt'].update(payload_raw_base64=base64.b64encode(b'{"form":[]}').decode()),
    lambda row,p:p['receipt'].update(observed_at='2026-09-01T00:00:00Z'),
    lambda row,p:row['profile']['payload']['filings']['files'][0].update(filingTo='2025-01-31'),
    lambda row,p:row['profile']['payload']['filings']['files'].append(deepcopy(row['profile']['payload']['filings']['files'][0])),
    lambda row,p:row['vendor']['payload']['filings'][0].update(date='2025-03-01'),
])
def test_changed_receipt_pointer_or_vendor_target_cannot_reuse_old_identity(change):
    _,row,raw=history_fixture();packet=fetch(row,raw);change(row,packet)
    row['profile']['normalized_sha256']=digest(row['profile']['payload']);row['vendor']['normalized_sha256']=digest(row['vendor']['payload'])
    assert validate(row,packet)==[]


@pytest.mark.parametrize('failure',['redirect','oversize','exception','duplicate_json','wrong_columns'])
def test_bad_archive_is_a_stable_gap_and_never_starts_another_request(failure):
    _,row,raw=history_fixture();calls=[]
    def source(url,agent):
        calls.append(url)
        if failure=='exception':raise OSError('no source')
        if failure=='oversize':return b'x'*(2*1024*1024+1),{},url
        if failure=='duplicate_json':return b'{"form":[],"form":[]}',{},url
        if failure=='wrong_columns':return b'{"form":["10-K"]}',{},url
        return raw,{},url+'/redirect'
    packet=fetch(row,raw,fetcher=source)
    assert validate(row,packet)==[] and calls==[URL]


def test_current_matched_vendor_never_requests_an_archive():
    c=collection();row=c['issuers'][0];calls=[]
    packet=fetch(row,b'{}',fetcher=lambda *args:calls.append(args))
    assert packet['status']=='not_applicable' and calls==[]


def test_wrong_issuer_and_unbound_archive_filename_stop_before_transport():
    _,row,raw=history_fixture();row['profile']['payload']['filings']['files'][0]['name']='CIK0000009999-submissions-001.json';row['profile']['normalized_sha256']=digest(row['profile']['payload'])
    def forbidden(*a):pytest.fail('unbound transport')
    assert fetch(row,raw,fetcher=forbidden)['status']=='unavailable'


def test_archive_matching_does_not_restore_missing_current_annual():
    c,row,raw=history_fixture();row['vendor_history']=fetch(row,raw)
    recent=row['profile']['payload']['filings']['recent'];recent['form']=['10-Q'];recent['reportDate']=['2026-06-30'];recent['filingDate']=['2026-08-01'];recent['accessionNumber']=['0000001001-26-000002'];recent['primaryDocument']=['quarter.htm'];row['profile']['normalized_sha256']=digest(row['profile']['payload'])
    assert build(c)['reason']=='annual_filing_missing'


@pytest.mark.parametrize('url',[URL,URL.replace('001.json','../001.json'),URL.replace('001.json','001.json?other=1')])
def test_sec_archive_url_allowlist_is_exact(url):
    from src.online_sec_receipt import fetch_sec_json_receipt
    called=[]
    result=fetch_sec_json_receipt(url,user_agent='Synthetic contact',fetcher=lambda u,a:(called.append(u) or b'{}',{},u),observed_at=NOW)
    assert (result['status']=='ready')==(url==URL) and bool(called)==(url==URL)
