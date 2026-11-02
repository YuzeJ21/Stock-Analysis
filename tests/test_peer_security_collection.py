from copy import deepcopy
import pytest

from selected_security_fixtures import fixture,install,scoped_collection,NOW
from src.online_peer_sources import _reduce_sec,get_online_peer_valuation,SESSION_KEY


def test_large_profile_keeps_financial_cover_and_investment_forms_without_blind_truncation():
    _,row,_,_=fixture();receipt=deepcopy(row['profile']);recent=receipt['payload']['filings']['recent']
    for key,values in recent.items():values[:0]=['424B2' if key=='form' else values[0]]*3000
    for key,values in recent.items():values.append('N-CSR' if key=='form' else values[-1])
    result=_reduce_sec(receipt,'profile')
    assert result['payload']['filings']['recent']['form']==['10-K','8-K','N-CSR']
    assert result['payload_sha256']==receipt['payload_sha256'] and result['normalized_sha256']!=receipt['normalized_sha256']


@pytest.mark.parametrize('change',[
    lambda r:r['filingDate'].pop(),
    lambda r:r['form'].__setitem__(1,None),
    lambda r:[v.extend([v[0]]*50000) for v in r.values()],
])
def test_malformed_or_overbound_recent_is_not_reduced_into_valid_metadata(change):
    _,row,_,_=fixture();receipt=deepcopy(row['profile']);change(receipt['payload']['filings']['recent'])
    assert _reduce_sec(receipt,'profile')['status']=='unavailable'


def test_explicit_source_collection_passes_proof_and_cache_reads_make_no_source_calls(monkeypatch):
    policy,c=scoped_collection();install(monkeypatch,policy);packets={r['ticker']:r for r in c['issuers']};calls=[]
    def sec(url,**kw):
        calls.append(url);cik=url.split('CIK')[1][:10];kind='profile' if '/submissions/' in url else 'facts'
        return next(r[kind] for r in packets.values() if str(r[kind]['payload']['cik']).zfill(10)==cik)
    deps=dict(classification=lambda **kw:c['classification'],vendor=lambda t,**kw:packets[t]['vendor'],industry=lambda *a,**kw:c['industry'],sec=sec,prices=lambda t,**kw:packets[t]['prices'],security=lambda t,cik,profile,**kw:packets[t].get('selected_security_evidence',dict(status='not_applicable')))
    state={};v=get_online_peer_valuation('FICT',state,refresh_requested=True,user_agent='Synthetic contact',dependencies=deps,as_of=NOW)
    assert v['subject']['multiple']==30 and v['peer_median']==25
    before=len(calls);assert get_online_peer_valuation('FICT',state,refresh_requested=False,as_of=NOW)==v
    assert len(calls)==before and state[SESSION_KEY]['collection']['issuers'][0]['selected_security_evidence']['status']=='observed'


def test_scope_outage_counts_as_access_failure_but_unsupported_scope_is_a_gap():
    from src.online_peer_coverage import _subject_source_failure
    view=dict(ticker='FICT',reason='multiple_issuer_share_classes_unresolved')
    row=dict(ticker='FICT',selected_security_evidence=dict(status='unavailable',reason='selected_security_source_unavailable'))
    assert _subject_source_failure(view,dict(collection=dict(issuers=[row]))) is True
    row['selected_security_evidence']=dict(status='not_applicable',reason='selected_security_scope_unverified')
    assert _subject_source_failure(view,dict(collection=dict(issuers=[row]))) is False


def test_history_source_outages_pause_peer_candidates_and_are_counted_for_subjects(monkeypatch):
    from src.online_peer_sec_history import fetch_vendor_history_match
    from src.online_peer_coverage import _subject_source_failure
    from selected_security_fixtures import digest
    policy,c=scoped_collection();install(monkeypatch,policy);packets={r['ticker']:r for r in c['issuers']}
    for ticker in ['FA','FB']:
        row=packets[ticker];cik=str(row['profile']['payload']['cik']).zfill(10);accession=cik+'-25-000003'
        f=row['vendor']['payload']['filings'][0];f.update(date='2025-02-01',edgarUrl=f'https://finance.yahoo.com/sec-filing/{ticker}/{accession}_{int(cik)}',exhibits={'10-K':f'https://cdn.yahoofinance.com/prod/sec-filings/{cik}/{accession.replace("-","")}/old.htm'})
        row['vendor']['normalized_sha256']=digest(row['vendor']['payload']);row['profile']['payload']['filings']['files']=[dict(name=f'CIK{cik}-submissions-001.json',filingCount=1,filingFrom='2025-01-01',filingTo='2025-12-31')];row['profile']['normalized_sha256']=digest(row['profile']['payload'])
    def sec(url,**kw):
        cik=url.split('CIK')[1][:10];kind='profile' if '/submissions/' in url else 'facts';return next(r[kind] for r in packets.values() if str(r[kind]['payload']['cik']).zfill(10)==cik)
    def unavailable(*a):raise OSError('source unavailable')
    def history(cik,profile,vendor,**kw):return fetch_vendor_history_match(cik,profile,vendor,fetcher=unavailable,**kw)
    deps=dict(classification=lambda **kw:c['classification'],vendor=lambda t,**kw:packets[t]['vendor'],industry=lambda *a,**kw:c['industry'],sec=sec,prices=lambda t,**kw:packets[t]['prices'],security=lambda t,cik,profile,**kw:packets[t].get('selected_security_evidence',dict(status='not_applicable')),history=history)
    v=get_online_peer_valuation('FICT',{},refresh_requested=True,user_agent='Synthetic contact',dependencies=deps,as_of=NOW)
    assert next(r for r in v['excluded'] if r['ticker']=='FC')['reason']=='source_paused_after_repeated_failures'
    row=dict(ticker='FICT',vendor_history=dict(status='unavailable',reason='vendor_history_source_unavailable'))
    assert _subject_source_failure(dict(ticker='FICT',reason='vendor_filing_not_matched_to_sec'),dict(collection=dict(issuers=[row]))) is True


@pytest.mark.parametrize('form',['N-CSR/A','N-CSRS/A','N-CEN/A','NPORT-P/A','N-PORT/A'])
def test_investment_company_amendment_is_retained_and_excludes_an_operating_comparison(monkeypatch,form):
    from test_online_peer_valuation import build
    policy,c=scoped_collection();install(monkeypatch,policy);profile=c['issuers'][0]['profile'];recent=profile['payload']['filings']['recent']
    for k,values in recent.items():values.append(form if k=='form' else values[-1])
    profile=_reduce_sec(profile,'profile');c['issuers'][0]['profile']=profile
    assert form in profile['payload']['filings']['recent']['form'] and build(c)['reason']=='investment_company_requires_separate_method'


@pytest.mark.parametrize('column',['reportDate','filingDate','accessionNumber','primaryDocument','acceptanceDateTime','isInlineXBRL','isXBRL'])
def test_large_profile_cannot_discard_structurally_malformed_cells(column):
    _,row,_,_=fixture();receipt=deepcopy(row['profile']);recent=receipt['payload']['filings']['recent']
    for k,values in recent.items():values[:0]=['424B2' if k=='form' else values[0]]*3000
    recent[column][1000]={'malformed':'cell'}
    assert _reduce_sec(receipt,'profile')['status']=='unavailable'


def test_cached_profile_with_malformed_nonfinancial_cells_also_withholds(monkeypatch):
    from test_online_peer_valuation import build
    from selected_security_fixtures import digest
    policy,c=scoped_collection();install(monkeypatch,policy);profile=c['issuers'][0]['profile'];recent=profile['payload']['filings']['recent']
    for key,values in recent.items():values.append('424B2' if key=='form' else {'malformed':'cell'} if key=='filingDate' else values[-1])
    profile['normalized_sha256']=digest(profile['payload'])
    assert build(c)['subject'] is None
