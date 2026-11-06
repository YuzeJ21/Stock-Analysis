"""Synthetic evidence only; public source shapes do not imply real company coverage."""
from copy import deepcopy
from datetime import datetime, timezone, date, timedelta
import hashlib
import json

import pytest

NOW = datetime(2026, 11, 1, 4, tzinfo=timezone.utc)
STAMP = NOW.isoformat()
SYMBOLS = ['FICT', 'FA', 'FB', 'FC']


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def classification(symbols=SYMBOLS, *, observed_at=NOW):
    from src.security_classification import fetch_classification
    from test_online_us_universe import N_URL, O_URL, M_URL, E_URL
    mapping = {str(i): dict(ticker=s, cik_str=1001+i, title='Synthetic '+s) for i, s in enumerate(symbols)}
    exchange = dict(fields=['cik', 'name', 'ticker', 'exchange'],
                    data=[[r['cik_str'], r['title'], r['ticker'], 'Nasdaq'] for r in mapping.values()])
    nasdaq = 'Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares\n'
    nasdaq += ''.join(f'{s}|Synthetic {s} - Common Stock|Q|N|N|100|N|N\n' for s in symbols)
    nasdaq += 'File Creation Time: 1030202615:41|||||||\n'
    other = ('ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol\n'
             'UNMAP|Unmapped - Common Stock|N|UNMAP|N|100|N|UNMAP\nFile Creation Time: 1030202615:41|||||||\n')
    bodies = {N_URL: nasdaq.encode(), O_URL: other.encode(), M_URL: json.dumps(mapping).encode(), E_URL: json.dumps(exchange).encode()}
    return fetch_classification(user_agent='Synthetic contact', fetcher=lambda url, agent: (bodies[url], {}, url), observed_at=observed_at)


def sec_receipt(cik, kind, body):
    url = f'https://data.sec.gov/{"submissions" if kind=="profile" else "api/xbrl/companyfacts"}/CIK{cik}.json'
    return dict(status='ready', source_url=url, payload=body, payload_sha256=digest(body), observed_at=STAMP)


def vendor_receipt(ticker, payload):
    return dict(status='observed', source_ref=f'https://finance.yahoo.com/quote/{ticker}/',
                adapter='yfinance_public_methods', observed_at=STAMP,
                payload=payload, normalized_sha256=digest(payload))


def issuer(ticker, cik, multiple, *, agent_prefix=False):
    from src.online_company_prices import price_source_url
    accession = ('0001193125' if agent_prefix else cik)+'-26-000001'
    annual = dict(form='10-K', reportDate='2025-12-31', filingDate='2026-02-01', accessionNumber=accession, primaryDocument='annual.htm')
    profile = dict(cik=int(cik), entityType='operating', sic='3674', tickers=[ticker], exchanges=['Nasdaq'],
                   filings={'recent': {k: [v] for k, v in annual.items()}})
    eps = dict(start='2025-01-01', end='2025-12-31', val=1.0, accn=accession, form='10-K', filed='2026-02-01', fy=2025, fp='FY')
    facts = dict(cik=int(cik), facts={'us-gaap': {'EarningsPerShareDiluted': {'units': {'USD/shares': [eps]}}}})
    info = dict(symbol=ticker, quoteType='EQUITY', currency='USD', financialCurrency='USD', exchange='NMS',
                exchangeTimezoneName='America/New_York', industryKey='semiconductors', sectorKey='technology',
                regularMarketTime=int(datetime(2026, 10, 30, 20, tzinfo=timezone.utc).timestamp()), regularMarketPrice=multiple)
    filing = dict(type='10-K', date='2026-02-01', edgarUrl=f'https://finance.yahoo.com/sec-filing/{ticker}/{accession}_{int(cik)}',
                  exhibits={'10-K': f'https://cdn.yahoofinance.com/prod/sec-filings/{cik}/{accession.replace("-", "")}/annual.htm'})
    prices = dict(status='inspection_only', ticker=ticker, provider_symbol=ticker, source_id='yahoo_chart',
                  source_url=price_source_url(ticker), payload_sha256='b'*64, observed_at=STAMP,
                  commercial_eligible=False, rights_status='exact_source_unregistered_personal_inspection_only',
                  currency='USD', exchange_code='NMS', full_exchange_name='NasdaqGS', exchange_timezone='America/New_York',
                  bars=[dict(date='2025-10-31', close=multiple), dict(date='2026-10-30', close=multiple)],
                  last_price_date='2026-10-30', splits=[])
    return dict(ticker=ticker, profile=sec_receipt(cik, 'profile', profile), facts=sec_receipt(cik, 'facts', facts),
                vendor=vendor_receipt(ticker, dict(info=info, filings=[filing])), prices=prices)


def collection():
    industry = dict(key='semiconductors', sector='technology', symbols=SYMBOLS[1:])
    return dict(schema_version='online-peer-collection-v1', ticker='FICT', observed_at=STAMP,
                classification=classification(), industry=dict(status='observed', payload=industry,
                    normalized_sha256=digest(industry), observed_at=STAMP,
                    source_ref='https://finance.yahoo.com/sectors/technology/semiconductors/'),
                issuers=[issuer(s, str(1001+i).zfill(10), value, agent_prefix=i==3)
                         for i, (s, value) in enumerate(zip(SYMBOLS, [30, 20, 25, 40]))])


def build(c=None, **kwargs):
    from src.online_peer_valuation import build_online_peer_valuation
    return build_online_peer_valuation(collection() if c is None else c, ticker='FICT', as_of=NOW, **kwargs)


def rehash_vendor(row):
    row['vendor']['normalized_sha256'] = digest(row['vendor']['payload'])


def test_hand_checked_comparison_keeps_actual_sources_and_does_not_promote_saved_models():
    c=collection(); before=deepcopy(c); v=build(c)
    assert v['status']=='research_comparison' and v['subject']['multiple']==30
    assert v['peer_median']==25 and v['premium_fraction']==pytest.approx(.2)
    assert [r['ticker'] for r in v['peers']]==['FA','FB','FC'] and v['peer_count']==3
    assert v['subject']['concept']=='EarningsPerShareDiluted' and v['subject']['unit']=='USD/shares'
    assert v['subject']['filed']=='2026-02-01' and v['subject']['price_date']=='2026-10-30'
    assert v['subject']['filing_ref'].endswith('/annual.htm')
    assert v['commercial_eligible'] is False and v['saved_readiness_promoted'] is False
    assert c==before and not {'score','target_price','recommendation','peer_ready'} & set(v)


def test_filing_agent_accession_prefix_is_not_mistaken_for_issuer_cik():
    assert build()['peer_count']==3


@pytest.mark.parametrize('value',[0,-2,True,float('nan'),float('inf'),10**500])
def test_invalid_or_loss_eps_never_means_cheap(value):
    c=collection(); c['issuers'][0]['facts']['payload']['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]['val']=value
    v=build(c); assert v['status']=='withheld' and v['premium_fraction'] is None


@pytest.mark.parametrize('change',['cik','ticker','currency','venue','vendor_cik','vendor_doc','filing_date','facts_cik','unit','industry','sic','split','malformed_split','quote_date','quote_price','current_day','duplicate_eps','amendment','duration','source_time','raw_ref','vendor_digest','multi_class','investment','blank_check'])
def test_subject_source_failures_remain_specific_and_withhold_every_verdict(change):
    c=collection(); r=c['issuers'][0]; info=r['vendor']['payload']['info']; f=r['facts']['payload']; p=r['profile']['payload']
    entry=f['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]
    if change=='cik': p['cik']=9999
    elif change=='ticker': info['symbol']='OTHER'
    elif change=='currency': info['currency']='EUR'
    elif change=='venue': info['exchange']='NYQ'
    elif change=='vendor_cik':r['vendor']['payload']['filings'][0]['edgarUrl']=r['vendor']['payload']['filings'][0]['edgarUrl'].replace('_1001','_9999')
    elif change=='vendor_doc':r['vendor']['payload']['filings'][0]['exhibits']['10-K']=r['vendor']['payload']['filings'][0]['exhibits']['10-K'].replace('annual.htm','other.htm')
    elif change=='filing_date':entry['filed']='2026-02-02'
    elif change=='facts_cik':f['cik']=9999
    elif change=='unit':f['facts']['us-gaap']['EarningsPerShareDiluted']['units']={'EUR/shares':[entry]}
    elif change=='industry':info['industryKey']='software'
    elif change=='sic':p['sic']=''
    elif change=='split':r['prices']['splits']=[dict(date='2026-05-01',numerator=2,denominator=1)]
    elif change=='malformed_split':r['prices']['splits']=[dict(date='bad',numerator=True,denominator=1)]
    elif change=='quote_date':info['regularMarketTime']-=86400
    elif change=='quote_price':info['regularMarketPrice']=29.5
    elif change=='current_day':info['regularMarketTime']=int(NOW.timestamp())
    elif change=='duplicate_eps':f['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'].append({**entry,'val':2.0})
    elif change=='amendment':
        for k,v in dict(form='10-K/A',reportDate='2025-12-31',filingDate='2026-03-01',accessionNumber='0000001001-26-000002',primaryDocument='amend.htm').items():p['filings']['recent'][k].append(v)
    elif change=='duration':entry['start']='2025-07-01'
    elif change=='source_time':r['facts']['observed_at']='2026-10-29T00:00:00Z'
    elif change=='raw_ref':r['facts']['source_url']='https://example.com/unknown'
    elif change=='multi_class':p['tickers'].append('FICT.B');p['exchanges'].append('Nasdaq')
    elif change=='investment':p['entityType']='investment-company'
    elif change=='blank_check':p['sic']='6770'
    if change!='vendor_digest':rehash_vendor(r)
    else:r['vendor']['normalized_sha256']='0'*64
    v=build(c); assert v['status']=='withheld' and v['premium_fraction'] is None and v['reason']!=''


@pytest.mark.parametrize('change',['industry','sic','price_date','fiscal_window','loss','identity','split'])
def test_incompatible_peer_is_excluded_instead_of_padding_the_median(change):
    c=collection();r=c['issuers'][1]
    if change=='industry':r['vendor']['payload']['info']['industryKey']='software';rehash_vendor(r)
    elif change=='sic':r['profile']['payload']['sic']='3571'
    elif change=='price_date':r['prices']['bars'][-1]['date']='2026-10-29';r['prices']['last_price_date']='2026-10-29';r['vendor']['payload']['info']['regularMarketTime']-=86400;rehash_vendor(r)
    elif change=='fiscal_window':
        e=r['facts']['payload']['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0];e.update(start='2025-03-01',end='2026-02-28',filed='2026-04-01')
        r['profile']['payload']['filings']['recent'].update(reportDate=['2026-02-28'],filingDate=['2026-04-01'])
        r['vendor']['payload']['filings'][0]['date']='2026-04-01';rehash_vendor(r)
    elif change=='loss':r['facts']['payload']['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]['val']=-1
    elif change=='identity':r['vendor']['payload']['info']['symbol']='OTHER';rehash_vendor(r)
    else:r['prices']['splits']=[dict(date='2026-01-05',numerator=10,denominator=1)]
    v=build(c);assert v['status']=='withheld' and v['peer_count']==2 and v['peer_median'] is None
    assert v['excluded'][0]['ticker']=='FA' and v['excluded'][0]['reason']


def test_duplicate_issuer_packet_and_over_bound_collection_fail_closed():
    c=collection();c['issuers'].append(deepcopy(c['issuers'][1]));assert build(c)['status']=='withheld'
    c=collection();c['issuers']*=4;assert build(c)['status']=='withheld'


def test_route_cik_is_independently_enforced():
    assert build(expected_cik='0000099999')['status']=='withheld'


@pytest.mark.parametrize('mode',['1','invalid'])
def test_commercial_or_invalid_mode_cannot_read_a_research_comparison(monkeypatch,mode):
    monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE',mode)
    assert build()['status']=='withheld'


def test_older_cached_source_becomes_withheld_without_changing_the_collection():
    from src.online_peer_valuation import build_online_peer_valuation
    c=collection();before=deepcopy(c)
    assert build_online_peer_valuation(c,ticker='FICT',as_of=datetime(2026,11,3,tzinfo=timezone.utc))['status']=='withheld'
    assert c==before


def test_discount_and_equal_values_are_not_translated_into_recommendations():
    for price,want in [(20,-.2),(25,0)]:
        c=collection();r=c['issuers'][0];r['vendor']['payload']['info']['regularMarketPrice']=price
        r['prices']['bars'][-1]['close']=price;rehash_vendor(r)
        v=build(c);assert v['premium_fraction']==pytest.approx(want) and 'recommendation' not in v


@pytest.mark.parametrize('days,want',[(35,3),(36,2)])
def test_declared_fiscal_boundary_is_applied_to_actual_periods(days,want):
    c=collection();r=c['issuers'][1]
    start=(date(2025,1,1)+timedelta(days=days)).isoformat()
    end=(date(2025,12,31)+timedelta(days=days)).isoformat()
    e=r['facts']['payload']['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]
    e.update(start=start,end=end,filed='2026-03-01')
    r['profile']['payload']['filings']['recent'].update(reportDate=[end],filingDate=['2026-03-01'])
    r['vendor']['payload']['filings'][0]['date']='2026-03-01';rehash_vendor(r)
    v=build(c);assert v['peer_count']==want
    if want==3:assert v['peers'][0]['period_end']==end
    else:assert v['excluded'][0]['reason']=='peer_fiscal_window_differs'


def test_missing_price_digest_cannot_create_a_source_backed_multiple():
    c=collection();del c['issuers'][0]['prices']['payload_sha256']
    assert build(c)['status']=='withheld'


def test_daily_close_cannot_predate_its_quote_observation():
    from src.online_peer_valuation import build_online_peer_valuation
    c=collection()
    # A Friday close cannot already have been observed at 15:00 New York.
    now=datetime(2026,10,31,4,tzinfo=timezone.utc)
    for r in c['issuers']:
        for receipt in [r['facts'],r['profile'],r['vendor'],r['prices']]:receipt['observed_at']=now.isoformat()
    c['issuers'][0]['prices']['observed_at']='2026-10-30T19:00:00Z'
    c['classification']=classification(observed_at=now)
    c['industry']['observed_at']=now.isoformat()
    c['observed_at']=now.isoformat()
    v=build_online_peer_valuation(c,ticker='FICT',as_of=now)
    assert v['status']=='withheld'


@pytest.mark.parametrize('has_amended_eps',[False,True])
def test_same_day_annual_versions_use_acceptance_time_without_falling_back(has_amended_eps):
    c=collection();r=c['issuers'][0];recent=r['profile']['payload']['filings']['recent']
    recent['acceptanceDateTime']=['2026-02-01T20:00:00Z']
    amended=dict(form='10-K/A',reportDate='2025-12-31',filingDate='2026-02-01',
                 accessionNumber='0000001001-26-000000',primaryDocument='amend.htm',
                 acceptanceDateTime='2026-02-01T21:00:00Z')
    for k,v in amended.items():recent[k].append(v)
    if has_amended_eps:
        eps=r['facts']['payload']['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares']
        eps.append({**eps[0],'form':'10-K/A','accn':amended['accessionNumber'],'val':2.0})
    v=build(c)
    if has_amended_eps:
        assert v['status']=='research_comparison' and v['subject']['multiple']==15
        assert v['subject']['accession']==amended['accessionNumber']
    else:
        assert v['reason']=='latest_annual_eps_missing_including_amendment' and v['premium_fraction'] is None


def test_identity_disclosure_selects_most_recent_matched_filing_not_last_list_item():
    c=collection();r=c['issuers'][0];recent=r['profile']['payload']['filings']['recent']
    old=dict(form='10-K',reportDate='2021-12-31',filingDate='2022-02-01',accessionNumber='0000001001-22-000001',primaryDocument='old.htm')
    for k,v in old.items():recent[k].append(v)
    r['vendor']['payload']['filings'].append(dict(type='10-K',date='2022-02-01',
        edgarUrl='https://finance.yahoo.com/sec-filing/FICT/0000001001-22-000001_1001',
        exhibits={'10-K':'https://cdn.yahoofinance.com/prod/sec-filings/0000001001/000000100122000001/old.htm'}))
    rehash_vendor(r)
    assert build(c)['subject']['vendor_filing']['filed']=='2026-02-01'


@pytest.mark.parametrize('case',['loss','amendment','fiscal_window','split'])
def test_excluded_peer_retains_independent_source_diagnostics_without_joining_the_median(case):
    c=collection();r=c['issuers'][1];recent=r['profile']['payload']['filings']['recent']
    eps=r['facts']['payload']['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]
    if case=='loss':eps['val']=-1
    elif case=='amendment':
        for k,v in dict(form='10-K/A',reportDate='2025-12-31',filingDate='2026-03-01',accessionNumber='0000001002-26-000099',primaryDocument='amend.htm').items():recent[k].append(v)
    elif case=='fiscal_window':
        eps.update(start='2025-03-01',end='2026-02-28',filed='2026-04-01')
        recent.update(reportDate=['2026-02-28'],filingDate=['2026-04-01'])
        r['vendor']['payload']['filings'][0]['date']='2026-04-01';rehash_vendor(r)
    else:r['prices']['splits']=[dict(date='2026-05-01',numerator=2,denominator=1)]
    v=build(c);excluded=v['excluded'][0];d=excluded['diagnostics']
    assert v['peer_count']==2 and v['peer_median'] is None and excluded['ticker']=='FA'
    assert d['sec_cik']=='0000001002' and d['facts_query_ref'].endswith('/CIK0000001002.json')
    assert d['candidate_source_ref']=='https://finance.yahoo.com/sectors/technology/semiconductors/'
    if case=='amendment':
        assert any(a['accession']=='0000001002-26-000099' for a in d['annual_versions'])
        assert 'annual_eps_observation' not in d
    else:
        observation=d['annual_eps_observation']
        assert observation['eps']==(-1 if case=='loss' else 1)
        assert observation['unit']=='USD/shares' and observation['filed']
        assert observation['source_ref'].endswith('/CIK0000001002.json')
    if case=='split':assert d['splits_observed']==[dict(date='2026-05-01',numerator=2,denominator=1)]


def test_unresolved_peer_identity_keeps_discovery_source_without_a_fabricated_cik():
    c=collection();c['industry']['payload']['symbols']=['UNKNOWN','FA','FB','FC']
    c['industry']['normalized_sha256']=digest(c['industry']['payload'])
    v=build(c);d=next(r['diagnostics'] for r in v['excluded'] if r['ticker']=='UNKNOWN')
    assert d['candidate_source_ref'].startswith('https://finance.yahoo.com/sectors/')
    assert 'sec_cik' not in d and 'annual_eps_observation' not in d


def test_mismatched_quote_and_close_dates_are_disclosed_without_admitting_peers():
    from src.company_answer_summary import build_company_answers

    c = collection()
    subject = c['issuers'][0]
    subject['vendor']['payload']['info']['regularMarketTime'] += 86400
    rehash_vendor(subject)
    view = build(c)
    assert view['reason'] == 'quote_not_same_recent_completed_day'
    assert view['subject'] is None and view['excluded'] == []
    card = build_company_answers('FICT', {}, {}, {}, {}, view)[-1]
    assert '供应商报价日期 2026-10-31 · 日线收盘 2026-10-30。' in card['evidence']
    assert ('本公司供应商报价来源', subject['vendor']['source_ref']) in card['links']
    assert ('本公司日线来源', subject['prices']['source_url']) in card['links']


@pytest.mark.parametrize("proof_kind", ["matching", "missing", "wrong_date", "mismatched_price"])
def test_same_day_observation_needs_close_proof_even_on_later_replay(proof_kind):
    from src.online_peer_valuation import build_online_peer_valuation

    c = collection()
    now = datetime(2026, 10, 31, 4, tzinfo=timezone.utc)
    c["classification"] = classification(observed_at=now)
    c["industry"]["observed_at"] = c["observed_at"] = now.isoformat()
    for issuer_row in c["issuers"]:
        for key in ("facts", "profile", "vendor", "prices"):
            issuer_row[key]["observed_at"] = now.isoformat()
    row = c["issuers"][0]
    prices = row["prices"]
    prices["observed_at"] = "2026-10-30T21:00:00Z"
    stamp = row["vendor"]["payload"]["info"]["regularMarketTime"]
    if proof_kind != "missing":
        offset = 86400 if proof_kind == "wrong_date" else 0
        prices["completed_regular_session"] = {
            "start": stamp - 23400 - offset,
            "end": stamp - offset,
            "quote_time": stamp - offset,
            "price": 31 if proof_kind == "mismatched_price" else 30,
        }
    view = build_online_peer_valuation(c, ticker="FICT", as_of=now)
    if proof_kind == "matching":
        assert view["status"] == "research_comparison"
        assert view["subject"]["price_date"] == "2026-10-30"
    else:
        assert view["status"] == "withheld"
        assert view["reason"] == "quote_not_same_recent_completed_day"
