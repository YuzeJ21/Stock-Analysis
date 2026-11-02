"""Synthetic source contracts; no real company documents or financial values."""
import base64
import hashlib
from copy import deepcopy

from test_online_peer_valuation import NOW, STAMP, issuer

META_KEYS=('form','reportDate','filingDate','acceptanceDateTime','accessionNumber','primaryDocument','isInlineXBRL','isXBRL')


def fixture():
    row=issuer('FICT','0000001001',30)
    annual=dict(form='10-K',reportDate='2025-12-31',filingDate='2026-02-01',acceptanceDateTime='2026-02-01T12:00:00Z',accessionNumber='0000001001-26-000001',primaryDocument='annual.htm',isInlineXBRL=1,isXBRL=1)
    cover=dict(form='8-K',reportDate='2026-10-20',filingDate='2026-10-20',acceptanceDateTime='2026-10-20T12:00:00Z',accessionNumber='0000001001-26-000002',primaryDocument='cover.htm',isInlineXBRL=1,isXBRL=1)
    def xml(end,form,annual=False):
        numbers='''<x:unit id="eps"><x:divide><x:unitNumerator><x:measure>iso:USD</x:measure></x:unitNumerator><x:unitDenominator><x:measure>x:shares</x:measure></x:unitDenominator></x:divide></x:unit><ix:nonFraction id="eps-fact" name="g:EarningsPerShareDiluted" contextRef="base" unitRef="eps" decimals="2">1</ix:nonFraction><ix:nonFraction id="capital" name="g:CommonStockParOrStatedValuePerShare" contextRef="base" unitRef="eps" decimals="2">0.01</ix:nonFraction><ix:nonNumeric id="note" name="g:EarningsPerSharePolicyTextBlock" contextRef="base">Diluted earnings per common share is reported directly.</ix:nonNumeric>''' if annual else ''
        return f'''<html xmlns="http://www.w3.org/1999/xhtml" xmlns:x="http://www.xbrl.org/2003/instance" xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" xmlns:dei="http://xbrl.sec.gov/dei/2025" xmlns:g="http://fasb.org/us-gaap/2025" xmlns:d="http://xbrl.org/2006/xbrldi" xmlns:iso="http://www.xbrl.org/2003/iso4217"><x:context id="base"><x:entity><x:identifier scheme="http://www.sec.gov/CIK">0000001001</x:identifier></x:entity><x:period><x:startDate>{'2025-01-01' if annual else end}</x:startDate><x:endDate>{end}</x:endDate></x:period></x:context><x:context id="common"><x:entity><x:identifier scheme="http://www.sec.gov/CIK">0000001001</x:identifier><x:segment><d:explicitMember dimension="g:StatementClassOfStockAxis">g:CommonStockMember</d:explicitMember></x:segment></x:entity><x:period><x:startDate>{'2025-01-01' if annual else end}</x:startDate><x:endDate>{end}</x:endDate></x:period></x:context><ix:nonNumeric id="doc-type" name="dei:DocumentType" contextRef="base">{form}</ix:nonNumeric><ix:nonNumeric id="period" name="dei:DocumentPeriodEndDate" contextRef="base">{end}</ix:nonNumeric><ix:nonNumeric id="title" name="dei:Security12bTitle" contextRef="common">Common Stock</ix:nonNumeric><ix:nonNumeric id="symbol" name="dei:TradingSymbol" contextRef="common">FICT</ix:nonNumeric><ix:nonNumeric id="exchange" name="dei:SecurityExchangeName" contextRef="common">Nasdaq</ix:nonNumeric>{numbers}</html>'''.encode()
    raw={'annual':xml('2025-12-31','10-K',True),'cover':xml('2026-10-20','8-K')}
    docs={key:dict(metadata=meta,sha256=hashlib.sha256(raw[key]).hexdigest(),cover_fact_ids=['title','symbol','exchange']) for key,meta in [('annual',annual),('cover',cover)]}
    policy=dict(policy_id='synthetic-common-v1',ticker='FICT',sec_cik='0000001001',kind='supported_common',issuer_symbols=['FICT','FP'],documents=docs,basis_fact_ids=['capital','note'],reason='literal_common_scope_supported')
    body=row['profile']['payload'];body['tickers']=['FICT','FP'];body['exchanges']=['Nasdaq','Nasdaq'];body['filings']['recent']={k:[m[k] for m in [annual,cover]] for k in META_KEYS}
    row['profile']['normalized_sha256']=digest(body)
    packet=dict(schema_version='sec-selected-security-v1',status='observed',ticker='FICT',sec_cik='0000001001',documents={})
    for key,doc in docs.items():
        meta=doc['metadata'];url=f'https://www.sec.gov/Archives/edgar/data/1001/{meta["accessionNumber"].replace("-","")}/{meta["primaryDocument"]}'
        packet['documents'][key]=dict(status='ready',source_url=url,observed_at=STAMP,payload_sha256=doc['sha256'],payload_raw_base64=base64.b64encode(raw[key]).decode())
    return policy,row,packet,raw


def digest(v):
    from src.online_peer_valuation import normalized_digest
    return normalized_digest(v)


def install(monkeypatch,policy):
    from src import sec_selected_security as security
    monkeypatch.setattr(security,'POLICIES',(deepcopy(policy),))


def validate(policy,row,packet,**kwargs):
    from src.sec_selected_security import validate_selected_security_evidence
    return validate_selected_security_evidence(packet,ticker=kwargs.pop('ticker','FICT'),cik=kwargs.pop('cik','0000001001'),profile=row['profile'],issuer_symbols=kwargs.pop('issuer_symbols',{'FICT','FP'}),as_of=kwargs.pop('as_of',NOW),**kwargs)


def scoped_collection(other_common=False,unknown_literal=False):
    import json
    from test_online_peer_valuation import collection
    from test_online_us_universe import N_URL,O_URL,M_URL,E_URL
    from src.security_classification import fetch_classification
    policy,row,packet,raw=fixture();c=collection();c['issuers'][0]=row;row['selected_security_evidence']=packet
    symbols=['FICT','FA','FB','FC','FP'];mapping={str(i):dict(ticker=s,cik_str=1001+i if s!='FP' else 1001,title='Synthetic') for i,s in enumerate(symbols)}
    exchange=dict(fields=['cik','name','ticker','exchange'],data=[[r['cik_str'],'Synthetic',r['ticker'],'Nasdaq'] for r in mapping.values()])
    nasdaq='Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares\n'+''.join(f'{s}|Synthetic - {"Preferred Stock" if s=="FP" and not other_common else "Common Stock"}|Q|N|N|100|N|N\n' for s in symbols)+'File Creation Time: 1030202615:41|||||||\n'
    other='ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol\nUNMAP|Unmapped - Common Stock|N|UNMAP|N|100|N|UNMAP\nFile Creation Time: 1030202615:41|||||||\n'
    if unknown_literal:nasdaq=nasdaq.replace('FICT|Synthetic - Common Stock|','FICT|Synthetic Company|')
    bodies={N_URL:nasdaq.encode(),O_URL:other.encode(),M_URL:json.dumps(mapping).encode(),E_URL:json.dumps(exchange).encode()}
    c['classification']=fetch_classification(user_agent='Synthetic contact',fetcher=lambda url,agent:(bodies[url],{},url),observed_at=NOW)
    return policy,c
