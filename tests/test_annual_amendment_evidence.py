"""Synthetic documents only; a test-only policy exercises the bound parser."""
from copy import deepcopy
from datetime import timedelta
import base64
import hashlib

import pytest

from test_online_peer_valuation import collection, NOW, STAMP, build, digest


def document(form='10-K', *, eps='7.5'):
    return f'''<html xmlns="http://www.w3.org/1999/xhtml" xmlns:x="http://www.xbrl.org/2003/instance" xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" xmlns:dei="http://xbrl.sec.gov/dei/2026" xmlns:g="http://fasb.org/us-gaap/2026" xmlns:iso="http://www.xbrl.org/2003/iso4217" xmlns:ixt="http://www.xbrl.org/inlineXBRL/transformation/2020-02-12">
    <head><x:context id="annual"><x:entity><x:identifier scheme="http://www.sec.gov/CIK">0000001001</x:identifier></x:entity><x:period><x:startDate>2025-01-01</x:startDate><x:endDate>2025-12-31</x:endDate></x:period></x:context>
    <x:unit id="money"><x:measure>iso:USD</x:measure></x:unit><x:unit id="eps"><x:divide><x:unitNumerator><x:measure>iso:USD</x:measure></x:unitNumerator><x:unitDenominator><x:measure>x:shares</x:measure></x:unitDenominator></x:divide></x:unit></head><body>
    <ix:nonNumeric name="dei:EntityCentralIndexKey" contextRef="annual">0000001001</ix:nonNumeric><ix:nonNumeric name="dei:DocumentType" contextRef="annual">{form}</ix:nonNumeric><ix:nonNumeric name="dei:DocumentPeriodEndDate" contextRef="annual">2025-12-31</ix:nonNumeric><ix:nonNumeric name="dei:AmendmentFlag" contextRef="annual" format="ixt:fixed-false">false</ix:nonNumeric>
    <ix:nonFraction name="g:Revenues" contextRef="annual" unitRef="money" decimals="0" id="revenue">100</ix:nonFraction><ix:nonFraction name="g:EarningsPerShareDiluted" contextRef="annual" unitRef="eps" decimals="2" id="earnings">{eps}</ix:nonFraction></body></html>'''.encode()


def fixture(monkeypatch, original=None, amended=None):
    import src.annual_amendment_evidence as module
    c=collection();row=c['issuers'][0];recent=row['profile']['payload']['filings']['recent']
    recent.update(acceptanceDateTime=['2026-02-01T12:00:00Z'],isInlineXBRL=[1],isXBRL=[1])
    old={k:v[0] for k,v in recent.items()}
    new={**old,'accessionNumber':'0000001001-26-000002','form':'10-K/A','filingDate':'2026-03-01',
         'acceptanceDateTime':'2026-03-01T12:00:00Z','primaryDocument':'amend.htm'}
    for k,v in new.items():recent[k].append(v)
    originals=document() if original is None else original
    amendments=document('10-K/A',eps='0') if amended is None else amended
    policy=dict(policy_id='synthetic-scope-v1',ticker='FICT',sec_cik='0000001001',
                original=old,amendment=new,original_sha256=hashlib.sha256(originals).hexdigest(),
                amendment_sha256=hashlib.sha256(amendments).hexdigest())
    monkeypatch.setattr(module,'POLICIES',(policy,))
    def receipt(raw,filing):
        url=f'https://www.sec.gov/Archives/edgar/data/1001/{filing["accessionNumber"].replace("-", "")}/{filing["primaryDocument"]}'
        return dict(status='ready',source_url=url,observed_at=STAMP,payload_sha256=hashlib.sha256(raw).hexdigest(),payload_raw_base64=base64.b64encode(raw).decode())
    packet=dict(schema_version='annual-amendment-evidence-v1',status='observed',ticker='FICT',sec_cik='0000001001',
                original=receipt(originals,old),amendment=receipt(amendments,new))
    row['amendment_evidence']=packet
    row['facts']['payload']['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]['val']=7.5
    return c,packet,policy


def validate(c,packet,**kwargs):
    from src.annual_amendment_evidence import validate_amendment_evidence
    from src.online_peer_valuation import _filings
    return validate_amendment_evidence(packet,ticker='FICT',cik='0000001001',
        filings=_filings(c['issuers'][0]['profile']['payload'],NOW),as_of=kwargs.get('as_of',NOW))


def test_exact_bound_original_eps_is_recovered_and_amendment_discrepancy_is_explicit(monkeypatch):
    c,packet,_=fixture(monkeypatch);before=deepcopy((c,packet))
    proof=validate(c,packet)
    assert proof['status']=='supported' and proof['original_eps']['eps']==7.5
    assert proof['original_eps']['period_start']=='2025-01-01' and proof['original_eps']['period_end']=='2025-12-31'
    assert proof['amendment_flag_discrepancy'] is True and proof['shared_amendment_parser_reason']=='filing_dei_identity_or_period_mismatch'
    assert len(proof['source_receipts'])==2 and proof['original_eps']['proofs'][0]['context_id']=='annual'
    result=build(c)
    assert result['status']=='research_comparison' and result['subject']['eps']==7.5
    assert result['subject']['accession']=='0000001001-26-000001' and result['subject']['form']=='10-K'
    assert result['subject']['amendment_scope']['amendment']['accessionNumber']=='0000001001-26-000002'
    assert result['commercial_eligible'] is False and result['saved_readiness_promoted'] is False
    assert (c,packet)==before


@pytest.mark.parametrize('change',['absent','original_bytes','amended_bytes','receipt_digest','url','ticker','cik','stale','future','base64','schema'])
def test_unbound_changed_or_expired_scope_proof_never_restores_original_eps(monkeypatch,change):
    c,p,_=fixture(monkeypatch)
    if change=='absent':c['issuers'][0].pop('amendment_evidence')
    elif change in {'original_bytes','amended_bytes'}:
        key='original' if change=='original_bytes' else 'amendment';raw=base64.b64decode(p[key]['payload_raw_base64'])+b' '
        p[key]['payload_raw_base64']=base64.b64encode(raw).decode();p[key]['payload_sha256']=hashlib.sha256(raw).hexdigest()
    elif change=='receipt_digest':p['original']['payload_sha256']='0'*64
    elif change=='url':p['original']['source_url']=p['amendment']['source_url']
    elif change=='ticker':p['ticker']='OTHER'
    elif change=='cik':p['sec_cik']='0000099999'
    elif change=='stale':p['original']['observed_at']='2026-10-29T00:00:00Z'
    elif change=='future':p['amendment']['observed_at']='2026-11-02T00:00:00Z'
    elif change=='base64':p['original']['payload_raw_base64']='%%%'
    else:p['schema_version']='unsupported'
    result=build(c)
    assert result['subject'] is None and result['premium_fraction'] is None


@pytest.mark.parametrize('change',['new_amendment','new_annual','tie','missing_acceptance','flags','metadata','facts_value','facts_unit','facts_accession'])
def test_current_version_metadata_and_companyfacts_agreement_are_required(monkeypatch,change):
    c,p,_=fixture(monkeypatch);row=c['issuers'][0];recent=row['profile']['payload']['filings']['recent']
    if change in {'new_amendment','new_annual','tie'}:
        new={k:v[-1] for k,v in recent.items()};new['accessionNumber']='0000001001-26-000003'
        if change!='tie':new.update(filingDate='2026-04-01',acceptanceDateTime='2026-04-01T12:00:00Z')
        if change=='new_annual':new.update(form='10-K',reportDate='2026-09-30')
        for k,v in new.items():recent[k].append(v)
    elif change=='missing_acceptance':recent.pop('acceptanceDateTime')
    elif change=='flags':recent['isInlineXBRL'][-1]=0
    elif change=='metadata':recent['primaryDocument'][-1]='other.htm'
    else:
        facts=row['facts']['payload']['facts']['us-gaap']['EarningsPerShareDiluted']['units'];eps=facts['USD/shares'][0]
        if change=='facts_value':eps['val']=7.4
        elif change=='facts_unit':facts['EUR/shares']=facts.pop('USD/shares')
        else:eps['accn']='0000001001-25-000001'
    result=build(c)
    assert result['subject'] is None and result['premium_fraction'] is None


@pytest.mark.parametrize('change',['dei','dimension','period','unit','reversed_unit','namespace','continuing','conflict','nil','transform','amendment_flag'])
def test_even_byte_bound_policy_cannot_admit_invalid_financial_context(monkeypatch,change):
    raw=document().decode();amend=None
    if change=='dei':raw=raw.replace('>10-K<','>20-F<')
    elif change=='dimension':raw=raw.replace('</x:entity>','<x:segment/></x:entity>')
    elif change=='period':raw=raw.replace('2025-01-01','2025-10-01')
    elif change=='unit':raw=raw.replace('<x:divide><x:unitNumerator><x:measure>iso:USD</x:measure></x:unitNumerator><x:unitDenominator><x:measure>x:shares</x:measure></x:unitDenominator></x:divide>','<x:measure>iso:USD</x:measure>')
    elif change=='reversed_unit':raw=raw.replace('iso:USD</x:measure></x:unitNumerator>','x:shares</x:measure></x:unitNumerator>').replace('x:shares</x:measure></x:unitDenominator>','iso:USD</x:measure></x:unitDenominator>')
    elif change=='namespace':raw=raw.replace('http://fasb.org/us-gaap/2026','https://example.invalid/us-gaap/2026')
    elif change=='continuing':raw=raw.replace('EarningsPerShareDiluted','EarningsPerShareDilutedContinuingOperations')
    elif change=='conflict':raw=raw.replace('</body>','<ix:nonFraction name="g:EarningsPerShareDiluted" contextRef="annual" unitRef="eps" decimals="2" id="other">7.4</ix:nonFraction></body>')
    elif change=='nil':raw=raw.replace('id="earnings"','id="earnings" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:nil="true"')
    elif change=='transform':raw=raw.replace('id="earnings"','id="earnings" format="ixt:unsupported"')
    elif change=='amendment_flag':amend=document('10-K/A').replace(b'>false<',b'>true<')
    c,p,_=fixture(monkeypatch,original=raw.encode(),amended=amend)
    assert validate(c,p)['status']=='withheld'


def test_general_inline_validator_still_rejects_the_amended_false_flag(monkeypatch):
    from src.sec_inline_filing import extract_inline_filing
    c,p,policy=fixture(monkeypatch)
    selected=dict(status='selected',ticker='FICT',sec_cik='0000001001',period_kind='annual',period_end='2025-12-31',
                  form='10-K/A',source_url=p['amendment']['source_url'])
    result=extract_inline_filing(base64.b64decode(p['amendment']['payload_raw_base64']),selected,p['amendment'])
    assert result['reason']=='filing_dei_identity_or_period_mismatch'


def test_fetch_is_explicit_exact_bounded_and_no_other_ticker_uses_the_policy(monkeypatch):
    from src.annual_amendment_evidence import fetch_amendment_evidence
    c,p,_=fixture(monkeypatch);calls=[]
    def fetch(url,agent):
        calls.append(url)
        r=next(r for r in [p['original'],p['amendment']] if r['source_url']==url)
        return base64.b64decode(r['payload_raw_base64']),{},url
    profile=c['issuers'][0]['profile']
    result=fetch_amendment_evidence('FICT','0000001001',profile,user_agent='Synthetic contact',fetcher=fetch,observed_at=NOW)
    assert result['status']=='observed' and len(calls)==2 and validate(c,result)['status']=='supported'
    calls.clear();assert fetch_amendment_evidence('OTHER','0000001001',profile,user_agent='Synthetic contact',fetcher=fetch)['status']=='not_applicable'
    assert not calls


@pytest.mark.parametrize('mode',['public','operator'])
def test_nonresearch_modes_precede_amendment_transport(monkeypatch,mode):
    from src.annual_amendment_evidence import fetch_amendment_evidence
    c,p,_=fixture(monkeypatch)
    assert fetch_amendment_evidence('FICT','0000001001',c['issuers'][0]['profile'],user_agent='Synthetic contact',workspace_mode=mode,
        fetcher=lambda *a:pytest.fail('transport'))['status']=='unavailable'


@pytest.mark.parametrize('rehash',[False,True])
def test_source_collector_and_cache_revalidate_the_same_original_bridge(monkeypatch,rehash):
    from test_online_peer_sources import source_dependencies,get
    from src.online_peer_sources import SESSION_KEY
    c,p,_=fixture(monkeypatch);deps,calls=source_dependencies(c);deps['amendment']=lambda *a,**kw:deepcopy(p);state={}
    result=get(state,refresh=True,dependencies=deps)
    assert result['subject']['eps']==7.5
    before=list(calls);assert get(state,dependencies=deps)==result and calls==before
    state[SESSION_KEY]['collection']['issuers'][0]['amendment_evidence']['original']['payload_raw_base64']='AAAA'
    if rehash:
        state[SESSION_KEY]['packet_digest']=digest({k:v for k,v in state[SESSION_KEY].items() if k!='packet_digest'})
    assert get(state,dependencies=deps)['subject'] is None


@pytest.mark.parametrize('problem',['redirect','oversize','unavailable','agent','commercial','invalid_mode'])
def test_transport_and_mode_guards_keep_the_source_unavailable(monkeypatch,problem):
    import src.annual_amendment_evidence as module
    c,p,_=fixture(monkeypatch);calls=[]
    def fetch(url,agent):
        calls.append(url)
        if problem=='unavailable':raise OSError('private diagnostic')
        key=next(k for k in ('original','amendment') if p[k]['source_url']==url)
        return base64.b64decode(p[key]['payload_raw_base64']),{},'https://example.invalid/' if problem=='redirect' else url
    if problem=='oversize':monkeypatch.setattr(module,'MAX_FILING_BYTES',100)
    if problem in {'commercial','invalid_mode'}:monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE','1' if problem=='commercial' else 'invalid')
    result=module.fetch_amendment_evidence('FICT','0000001001',c['issuers'][0]['profile'],
        user_agent='bad\nagent' if problem=='agent' else 'Synthetic contact',fetcher=fetch,observed_at=NOW)
    assert result['status']=='unavailable' and 'private diagnostic' not in str(result)
    if problem in {'commercial','invalid_mode','agent'}:assert not calls
