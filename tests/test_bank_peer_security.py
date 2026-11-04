"""Synthetic financial behavior; real policy tests inspect metadata/transport only."""
import base64,hashlib,json
from copy import deepcopy
from datetime import datetime,timezone
import pytest
from document_set_fixtures import document_set_fixture
from selected_security_fixtures import fixture,digest
from test_online_peer_valuation import collection,issuer,build,NOW,rehash_vendor


def bank_collection(monkeypatch):
    from src import sec_selected_security as security
    from src.security_classification import fetch_classification
    from test_online_us_universe import N_URL,O_URL,M_URL,E_URL
    c=collection();policies=[];symbols=['FICT','FA','FB','FC','FA-P','FB-P','FC-P'];mapping={}
    for i,t in enumerate(symbols):mapping[str(i)]=dict(ticker=t,cik_str=1001+['FICT','FA','FB','FC'].index(t.removesuffix('-P')),title='Synthetic')
    exchange=dict(fields=['cik','name','ticker','exchange'],data=[[r['cik_str'],'Synthetic',r['ticker'],'Nasdaq'] for r in mapping.values()])
    n='Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares\n'+''.join(t+'|Synthetic - '+('Preferred Stock' if t.endswith('-P') else 'Common Stock')+'|Q|N|N|100|N|N\n' for t in symbols)+'File Creation Time: 1030202615:41|||||||\n'
    o='ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol\nUNMAP|Unmapped - Common Stock|N|UNMAP|N|100|N|UNMAP\nFile Creation Time: 1030202615:41|||||||\n'
    bodies={N_URL:n.encode(),O_URL:o.encode(),M_URL:json.dumps(mapping).encode(),E_URL:json.dumps(exchange).encode()}
    c['classification']=fetch_classification(user_agent='Synthetic contact',fetcher=lambda url,a:(bodies[url],{},url),observed_at=NOW)
    for i,(t,value) in enumerate([('FA',20),('FB',25),('FC',40)],2):
        p,r,s,raw=document_set_fixture('financial' if t=='FA' else 'cover') if t!='FC' else fixture()
        cik=str(1000+i).zfill(10)
        p=json.loads(json.dumps(p).replace('FICT',t).replace('0000001001',cik).replace('FP',t+'-P'))
        row=issuer(t,cik,value);profile=json.loads(json.dumps(r['profile']).replace('FICT',t).replace('0000001001',cik).replace('FP',t+'-P'))
        profile['payload']['cik']=int(cik);row['profile']=profile
        for role,doc in p['documents'].items():
            for child in (False,True) if 'companion' in doc else (False,):
                key=role+'-companion' if child else role;body=raw[key].replace(b'FICT',t.encode()).replace(b'0000001001',cik.encode())
                target=doc['companion'] if child else doc;target['sha256']=hashlib.sha256(body).hexdigest()
                meta=doc['metadata'];name=target['primaryDocument'] if child else meta['primaryDocument'];url=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{meta["accessionNumber"].replace("-","")}/{name}'
                ref=dict(status='ready',source_url=url,observed_at=s['documents'][role]['observed_at'],payload_sha256=target['sha256'],payload_raw_base64=base64.b64encode(body).decode())
                if child:s['documents'][role]['companion']=ref
                else:s['documents'][role]=ref
        s.update(ticker=t,sec_cik=cik);row['selected_security_evidence']=s;policies.append(p);c['issuers'][i-1]=row
    for row in c['issuers']:
        row['profile']['payload']['sic']='6021';row['profile']['normalized_sha256']=digest(row['profile']['payload'])
        row['vendor']['payload']['info'].update(industryKey='banks-diversified',sectorKey='financial-services');rehash_vendor(row)
    c['industry']['payload'].update(key='banks-diversified',sector='financial-services');c['industry']['normalized_sha256']=digest(c['industry']['payload']);c['industry']['source_ref']='https://finance.yahoo.com/sectors/financial-services/banks-diversified/'
    monkeypatch.setattr(security,'POLICIES',tuple(policies));return c


def test_three_independently_supported_bank_common_scopes_form_a_hand_checked_comparison(monkeypatch):
    c=bank_collection(monkeypatch);before=deepcopy(c);v=build(c)
    assert v['status']=='research_comparison' and v['peer_count']==3
    assert [r['ticker'] for r in v['peers']]==['FA','FB','FC']
    assert v['peer_median']==25 and v['premium_fraction']==pytest.approx(.2)
    assert all(r['selected_security_scope']['commercial_eligible'] is False for r in v['peers'])
    assert c==before


@pytest.mark.parametrize('gate',['missing_companion','eps','sic','split','price','currency','issuer','period'])
def test_common_security_proof_does_not_override_other_peer_gates(monkeypatch,gate):
    c=bank_collection(monkeypatch);row=c['issuers'][1]
    if gate=='missing_companion':row['selected_security_evidence']['documents']['annual'].pop('companion')
    elif gate=='eps':row['facts']['payload']['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]['val']=2
    elif gate=='sic':row['profile']['payload']['sic']='6022';row['profile']['normalized_sha256']=digest(row['profile']['payload'])
    elif gate=='split':row['prices']['splits']=[dict(date='2026-05-01',numerator=2,denominator=1)]
    elif gate=='price':row['prices']['bars'][-1]['date']='2026-10-29';row['prices']['last_price_date']='2026-10-29'
    elif gate=='currency':row['vendor']['payload']['info']['financialCurrency']='CAD';rehash_vendor(row)
    elif gate=='issuer':row['facts']['payload']['cik']=1001
    else:row['facts']['payload']['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]['start']='2025-10-01'
    v=build(c);assert v['peer_count']==2 and v['status']=='withheld' and v['premium_fraction'] is None
    assert 'FA' not in [r['ticker'] for r in v['peers']]


@pytest.mark.parametrize('ticker,cik,expected_count',[('BAC','0000070858',2),('WFC','0000072971',3),('C','0000831001',4)])
def test_registered_bank_scope_drives_bounded_transport_but_metadata_alone_never_qualifies(monkeypatch,ticker,cik,expected_count):
    from src.sec_selected_security import fetch_selected_security_evidence,validate_selected_security_evidence
    from src.sec_selected_security_policies import POLICIES
    policy=next((p for p in POLICIES if p['ticker']==ticker),None)
    assert policy is not None,'Missing source-supported bank path'
    profile=dict(status='ready',source_url=f'https://data.sec.gov/submissions/CIK{cik}.json',observed_at='2026-11-02T00:00:00Z',payload=dict(cik=int(cik),tickers=policy['issuer_symbols'],exchanges=['NYSE']*len(policy['issuer_symbols']),filings={'recent':{k:[d['metadata'][k] for d in policy['documents'].values()] for k in policy['documents']['annual']['metadata']}}))
    calls=[]
    def fetch(url,agent):calls.append(url);return b'<html>not financial proof</html>',{},url
    now=datetime(2026,11,2,1,tzinfo=timezone.utc)
    packet=fetch_selected_security_evidence(ticker,cik,profile,user_agent='Synthetic contact',fetcher=fetch,observed_at=now)
    assert packet['status']=='observed' and len(calls)==expected_count and len(set(calls))==expected_count
    assert all(u.startswith('https://www.sec.gov/Archives/edgar/data/'+str(int(cik))+'/') for u in calls)
    assert validate_selected_security_evidence(packet,ticker=ticker,cik=cik,profile=profile,issuer_symbols=policy['issuer_symbols'],as_of=now)['status']=='withheld'
