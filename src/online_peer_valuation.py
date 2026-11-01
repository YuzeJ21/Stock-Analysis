"""Personal-research annual P/E from independently bound, dated source observations.

This method never constructs a saved report, grants source rights, or sets peer_ready.
An industry reference selected by disclosed rules is not an analyst-approved peer set.
"""
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import re
from statistics import median
from zoneinfo import ZoneInfo

from src.company_sec_online_preview import _iso_date, _utc_timestamp
from src.online_company_identity import _mode_reason, _VENUES
from src.online_company_prices import price_source_url
from src.online_research_history_view import validated_online_price_history
from src.security_classification import validated_classification, _selected

SCHEMA = 'online-peer-collection-v1'
MAX_CANDIDATES = 12
MIN_PEERS = 3
FISCAL_WINDOW_DAYS = 35
RIGHTS = 'personal_research_only_commercial_and_redistribution_unverified'
_SYMBOL = re.compile(r'[A-Z0-9][A-Z0-9.-]{0,19}\Z')
_KEY = re.compile(r'[a-z][a-z0-9-]{0,79}\Z')
_ANNUAL = {'10-K', '10-K/A', '20-F', '20-F/A'}
_PERIODIC = _ANNUAL | {'10-Q', '10-Q/A'}


class _Hold(ValueError):
    pass


def _need(condition, reason):
    if not condition:
        raise _Hold(reason)


def normalized_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _positive(value):
    try:
        return type(value) in {int, float} and 0 < value <= 1e20 and math.isfinite(value)
    except (OverflowError, ValueError):
        return False


def _symbol(value):
    return isinstance(value, str) and _SYMBOL.fullmatch(value) is not None


def _cik(value):
    _need(type(value) in {int, str} and re.fullmatch(r'\d{1,10}', str(value)) is not None and int(value)>0,
          'issuer_identity_unverified')
    return str(int(value)).zfill(10)


def _observed(value, as_of):
    observed = _utc_timestamp(value)
    _need(observed is not None and timedelta(0) <= as_of-observed <= timedelta(hours=24), 'source_observation_stale_or_future')
    return observed


def _receipt(receipt, url, as_of):
    _need(isinstance(receipt, Mapping) and receipt.get('status')=='ready' and receipt.get('source_url')==url,
          'sec_source_unavailable_or_mismatched')
    _observed(receipt.get('observed_at'), as_of)
    _need(isinstance(receipt.get('payload_sha256'), str) and re.fullmatch(r'[0-9a-f]{64}', receipt['payload_sha256']) is not None,
          'source_digest_missing')
    _need(isinstance(receipt.get('payload'), Mapping), 'sec_payload_invalid')
    if 'normalized_sha256' in receipt:
        _need(receipt['normalized_sha256']==normalized_digest(receipt['payload']), 'normalized_sec_observation_changed')
    return receipt['payload']


def _normalized(receipt, source_ref, as_of):
    _need(isinstance(receipt, Mapping) and receipt.get('status')=='observed' and receipt.get('source_ref')==source_ref,
          'vendor_source_unavailable_or_mismatched')
    _observed(receipt.get('observed_at'), as_of)
    payload=receipt.get('payload')
    _need(isinstance(payload, Mapping) and normalized_digest(payload)==receipt.get('normalized_sha256'), 'normalized_observation_changed')
    return payload


def _filings(profile, as_of):
    recent=profile.get('filings', {}).get('recent')
    keys=('form', 'reportDate', 'filingDate', 'accessionNumber', 'primaryDocument')
    if isinstance(recent,Mapping) and 'acceptanceDateTime' in recent:
        keys+=('acceptanceDateTime',)
    _need(isinstance(recent, Mapping) and all(isinstance(recent.get(k), list) for k in keys), 'filing_metadata_missing')
    count=len(recent['form'])
    _need(0<count<=2000 and all(len(recent[k])==count for k in keys), 'filing_metadata_invalid')
    result=[]
    for values in zip(*(recent[k] for k in keys)):
        row=dict(zip(keys, values))
        if row['form'] not in _PERIODIC:
            continue
        end, filed=(_iso_date(row[k]) for k in ('reportDate', 'filingDate'))
        _need(end and filed and end<=filed<=as_of.date()
              and isinstance(row['accessionNumber'], str) and re.fullmatch(r'\d{10}-\d{2}-\d{6}',row['accessionNumber'])
              and isinstance(row['primaryDocument'], str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,200}',row['primaryDocument']),
              'filing_metadata_invalid')
        if 'acceptanceDateTime' in row:
            accepted=_utc_timestamp(row['acceptanceDateTime'])
            _need(accepted is not None and end<=accepted.date() and accepted<=as_of, 'filing_acceptance_time_invalid')
        result.append(row)
    return result


def _vendor_filing_match(filings, sec_filings, ticker, cik):
    _need(isinstance(filings, list) and 0<len(filings)<=256, 'vendor_filing_identity_missing')
    matched=None
    for row in filings:
        _need(isinstance(row, Mapping), 'vendor_filing_identity_invalid')
        if row.get('type') not in _PERIODIC:
            continue
        url=row.get('edgarUrl')
        pattern=r'https://finance\.yahoo\.com/sec-filing/'+re.escape(ticker.replace('.','-'))+r'/(\d{10}-\d{2}-\d{6})_(\d{1,10})'
        link=re.fullmatch(pattern, url) if isinstance(url,str) else None
        _need(link is not None and _cik(link[2])==cik, 'vendor_filing_issuer_conflict')
        for sec in sec_filings:
            if (link[1],row.get('type'),row.get('date'))!=(sec['accessionNumber'],sec['form'],sec['filingDate']):
                continue
            exhibit='https://cdn.yahoofinance.com/prod/sec-filings/'+cik+'/'+link[1].replace('-','')+'/'+sec['primaryDocument']
            if isinstance(row.get('exhibits'),Mapping) and row['exhibits'].get(row['type'])==exhibit:
                matched=dict(source_ref=url, accession=link[1], filed=sec['filingDate'])
    _need(matched is not None, 'vendor_filing_not_matched_to_sec')
    return matched


def _annual_eps(facts, filings, price_date):
    annual=[r for r in filings if r['form'] in _ANNUAL]
    _need(bool(annual), 'annual_filing_missing')
    latest_end=max(r['reportDate'] for r in annual)
    latest_filed=max(r['filingDate'] for r in annual if r['reportDate']==latest_end)
    selected=[r for r in annual if r['reportDate']==latest_end and r['filingDate']==latest_filed]
    if len(selected)>1 and all(r.get('acceptanceDateTime') for r in selected):
        latest_accepted=max(_utc_timestamp(r['acceptanceDateTime']) for r in selected)
        selected=[r for r in selected if _utc_timestamp(r['acceptanceDateTime'])==latest_accepted]
    _need(len(selected)==1, 'annual_filing_tie_unresolved')
    filing=selected[0]
    _need(_iso_date(latest_filed)<=price_date and 0<=(price_date-_iso_date(latest_end)).days<=550,
          'annual_period_or_publication_not_current_for_price')
    units=facts.get('facts',{}).get('us-gaap',{}).get('EarningsPerShareDiluted',{}).get('units',{})
    rows=units.get('USD/shares') if isinstance(units,Mapping) else None
    _need(isinstance(rows,list) and 0<len(rows)<=10000, 'annual_diluted_eps_usd_missing')
    candidates=[]
    for row in rows:
        _need(isinstance(row,Mapping), 'annual_eps_schema_invalid')
        if row.get('accn')!=filing['accessionNumber'] or row.get('end')!=latest_end:
            continue
        start,end=_iso_date(row.get('start')),_iso_date(row.get('end'))
        _need(start and end, 'annual_eps_period_invalid')
        if not 350<=(end-start).days<=380:
            continue
        _need(row.get('form')==filing['form'] and row.get('filed')==latest_filed, 'annual_eps_filing_mismatch')
        _need(_positive(row.get('val')), 'annual_eps_nonpositive_or_invalid')
        candidates.append((row['start'],row['end'],float(row['val'])))
    _need(bool(candidates), 'latest_annual_eps_missing_including_amendment')
    _need(len(set(candidates))==1, 'annual_eps_conflict')
    start,end,value=candidates[0]
    # A different currency for this same annual observation cannot be ignored.
    for unit,other in units.items():
        if unit!='USD/shares' and isinstance(other,list):
            _need(not any(isinstance(r,Mapping) and r.get('accn')==filing['accessionNumber'] and r.get('start')==start and r.get('end')==end for r in other),
                  'annual_eps_unit_conflict')
    return dict(period_start=start,period_end=end,eps=value,filed=latest_filed,accession=filing['accessionNumber'],
                form=filing['form'],primary_document=filing['primaryDocument'])


def _issuer(row, classification, industry_key, as_of):
    ticker=row.get('ticker')
    _need(_symbol(ticker), 'issuer_symbol_invalid')
    cik,listings=_selected(classification,ticker,None)
    issuer_symbols={r['ticker'].replace('.','-') for r in classification['inventory']['map_receipt']['payload'].values()
                    if _cik(r['cik_str'])==cik}
    _need(len(issuer_symbols)==1, 'multiple_issuer_share_classes_unresolved')
    explicit=[r for r in listings if r['source']!='sec']
    _need(bool(explicit) and all(r['security_type']=='common_shares' for r in explicit), 'ordinary_share_basis_unverified')
    profile=_receipt(row.get('profile'),f'https://data.sec.gov/submissions/CIK{cik}.json',as_of)
    facts=_receipt(row.get('facts'),f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json',as_of)
    _need(_cik(profile.get('cik'))==cik and _cik(facts.get('cik'))==cik, 'issuer_identity_mismatch')
    _need(profile.get('entityType')=='operating', 'operating_issuer_required')
    _need(profile.get('tickers')==[ticker] and isinstance(profile.get('exchanges'),list) and len(profile['exchanges'])==1,
          'sec_security_class_or_exchange_unresolved')
    sic=profile.get('sic')
    _need(type(sic) in {str,int} and re.fullmatch(r'\d{4}',str(sic)) is not None and str(sic) not in {'0000','6770'},
          'industry_or_operating_scope_unverified')
    forms=profile.get('filings',{}).get('recent',{}).get('form',[])
    _need(not any(f in {'N-CSR','N-CSRS','N-CEN','NPORT-P','N-PORT'} for f in forms), 'investment_company_requires_separate_method')
    filings=_filings(profile,as_of)
    vendor=_normalized(row.get('vendor'),f'https://finance.yahoo.com/quote/{ticker.replace(".","-")}/',as_of)
    info=vendor.get('info')
    _need(isinstance(info,Mapping) and info.get('symbol')==ticker.replace('.','-') and info.get('quoteType')=='EQUITY', 'quote_identity_or_type_mismatch')
    _need(info.get('currency')=='USD' and info.get('financialCurrency')=='USD', 'unsupported_quote_or_financial_currency')
    _need(info.get('industryKey')==industry_key, 'provider_industry_differs')
    venue=_VENUES.get(info.get('exchange'))
    _need(venue is not None and profile['exchanges']==[venue[0]] and all(r['venue']==venue[0] for r in explicit), 'quote_exchange_mismatch')
    identity=_vendor_filing_match(vendor.get('filings'),filings,ticker,cik)
    prices=validated_online_price_history(row.get('prices'),ticker=ticker)
    _need(prices is not None and prices.get('source_url')==price_source_url(ticker.replace('.','-')), 'completed_price_source_unverified')
    price_observed=_observed(prices.get('observed_at'),as_of)
    _need(isinstance(prices.get('payload_sha256'),str) and re.fullmatch(r'[0-9a-f]{64}',prices['payload_sha256']), 'price_source_digest_missing')
    _need(prices.get('exchange_code')==info['exchange'], 'price_exchange_mismatch')
    zone=ZoneInfo(info.get('exchangeTimezoneName'))
    _need(prices.get('exchange_timezone')==zone.key, 'price_timezone_mismatch')
    stamp=info.get('regularMarketTime')
    _need(type(stamp) is int and 0<stamp<=as_of.timestamp(), 'quote_time_invalid')
    _need(stamp<=min(price_observed,_utc_timestamp(row['vendor']['observed_at'])).timestamp(), 'price_quote_chronology_invalid')
    quote_date=datetime.fromtimestamp(stamp,tz=timezone.utc).astimezone(zone).date()
    price_date=_iso_date(prices['last_price_date'])
    _need(quote_date==price_date and price_date<as_of.astimezone(zone).date() and 0<=(as_of.astimezone(zone).date()-price_date).days<=7,
          'quote_not_same_recent_completed_day')
    price=info.get('regularMarketPrice')
    _need(_positive(price) and math.isclose(price,prices['bars'][-1]['close'],rel_tol=1e-7,abs_tol=1e-6), 'quote_and_daily_close_differ')
    eps=_annual_eps(facts,filings,price_date)
    _need(_iso_date(prices['bars'][0]['date'])<=_iso_date(eps['period_end']), 'split_history_does_not_cover_period_end')
    splits=prices.get('splits')
    _need(isinstance(splits,list) and len(splits)<=64, 'split_evidence_invalid')
    for split in splits:
        _need(isinstance(split,Mapping) and _iso_date(split.get('date')) is not None and _positive(split.get('numerator')) and _positive(split.get('denominator')),
              'split_evidence_invalid')
        day=_iso_date(split['date'])
        _need(day<=as_of.astimezone(zone).date(), 'future_split_evidence')
        _need(day<=_iso_date(eps['period_end']), 'post_period_split_requires_share_basis_review')
    multiple=price/eps['eps']
    _need(_positive(multiple) and multiple<=1e6, 'multiple_outside_supported_range')
    filing_ref=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{eps["accession"].replace("-", "")}/{eps["primary_document"]}'
    return dict(ticker=ticker,sec_cik=cik,sic=str(sic),industry_key=industry_key,price=float(price),price_date=price_date.isoformat(),
                multiple=multiple,**eps,concept='EarningsPerShareDiluted',taxonomy='us-gaap',unit='USD/shares',currency='USD',
                basis='reported_annual_diluted_GAAP_EPS',identity_basis='vendor_filing_matched_to_independent_sec_metadata',
                vendor_filing=identity,filing_ref=filing_ref,source_ref=row['facts']['source_url'],
                observed_at=row['facts']['observed_at'],price_observed_at=prices['observed_at'],
                vendor_observed_at=row['vendor']['observed_at'],price_source_ref=prices['source_url'],
                facts_sha256=row['facts']['payload_sha256'],price_sha256=prices.get('payload_sha256'),
                vendor_normalized_sha256=row['vendor']['normalized_sha256'],rights_status=RIGHTS)


def _empty(ticker, reason):
    return dict(ticker=ticker,status='withheld',reason=reason,metric='reported_annual_diluted_pe',
                subject=None,peers=[],excluded=[],peer_count=0,peer_median=None,premium_fraction=None,
                commercial_eligible=False,saved_readiness_promoted=False,rights_status=RIGHTS,
                fiscal_window_days=FISCAL_WINDOW_DAYS,minimum_peers=MIN_PEERS,candidate_count=0)


def build_online_peer_valuation(collection, *, ticker, expected_cik=None, as_of=None):
    """Revalidate every observation; never trust a precomputed verdict or readiness flag."""
    result=_empty(ticker,_mode_reason('research') or 'online_peer_evidence_unavailable')
    if _mode_reason('research') or not _symbol(ticker):
        return result
    now=as_of if as_of is not None else datetime.now(timezone.utc)
    try:
        _need(isinstance(now,datetime) and now.utcoffset() is not None, 'invalid_observation')
        now=now.astimezone(timezone.utc)
        _need(isinstance(collection,Mapping) and collection.get('schema_version')==SCHEMA and collection.get('ticker')==ticker,
              'collection_identity_or_schema_mismatch')
        _observed(collection.get('observed_at'),now)
        classification=validated_classification(collection.get('classification'))
        _need(classification is not None, 'listing_classification_unverified')
        for receipt in classification['inventory']['source_receipts']:
            _observed(receipt.get('observed_at'),now)
        industry=collection.get('industry',{}).get('payload',{})
        key,sector=industry.get('key'),industry.get('sector')
        _need(isinstance(key,str) and _KEY.fullmatch(key) and isinstance(sector,str) and _KEY.fullmatch(sector), 'industry_source_unavailable')
        industry=_normalized(collection['industry'],f'https://finance.yahoo.com/sectors/{sector}/{key}/',now)
        symbols=industry.get('symbols')
        _need(isinstance(symbols,list) and len(symbols)<=200 and all(_symbol(s) for s in symbols), 'industry_candidate_schema_invalid')
        candidates=list(dict.fromkeys(s for s in symbols if s.replace('.','-')!=ticker.replace('.','-')))[:MAX_CANDIDATES]
        result.update(candidate_count=len(candidates),industry_source_ref=collection['industry']['source_ref'],
                      industry_key=key,industry_candidate_total=len(symbols),candidate_limit=MAX_CANDIDATES,
                      industry_observed_at=collection['industry']['observed_at'],industry_normalized_sha256=collection['industry']['normalized_sha256'])
        packets=collection.get('issuers')
        _need(isinstance(packets,list) and 0<len(packets)<=MAX_CANDIDATES+1 and all(isinstance(p,Mapping) and _symbol(p.get('ticker')) for p in packets), 'issuer_collection_invalid')
        rows={p['ticker']:p for p in packets}
        _need(len(rows)==len(packets) and set(rows)<={ticker,*candidates} and ticker in rows, 'duplicate_or_unrequested_issuer')
        subject=_issuer(rows[ticker],classification,key,now)
        _need(expected_cik is None or subject['sec_cik']==expected_cik, 'selected_company_cik_mismatch')
        result['subject']=subject
        seen={subject['sec_cik']}
        for symbol in candidates:
            try:
                _need(symbol in rows, 'peer_not_collected')
                if rows[symbol].get('status')=='unavailable':
                    raise _Hold(str(rows[symbol].get('reason') or 'peer_source_unavailable'))
                peer=_issuer(rows[symbol],classification,key,now)
                _need(peer['sec_cik'] not in seen, 'duplicate_peer_issuer')
                _need(peer['sic']==subject['sic'], 'sec_industry_differs')
                _need(peer['price_date']==subject['price_date'], 'peer_price_date_differs')
                _need(all(abs((_iso_date(peer[k])-_iso_date(subject[k])).days)<=FISCAL_WINDOW_DAYS for k in ('period_start','period_end')),
                      'peer_fiscal_window_differs')
                result['peers'].append(peer);seen.add(peer['sec_cik'])
            except (ValueError,TypeError,KeyError,AttributeError,OverflowError) as error:
                result['excluded'].append(dict(ticker=symbol,reason=str(error) if isinstance(error,_Hold) else 'invalid_peer_source_evidence'))
        result['peer_count']=len(result['peers'])
        _need(result['peer_count']>=MIN_PEERS, 'at_least_three_compatible_industry_references_required')
        middle=float(median(p['multiple'] for p in result['peers']))
        premium=subject['multiple']/middle-1
        _need(math.isfinite(premium) and abs(premium)<=1e6, 'relative_multiple_outside_supported_range')
        result.update(status='research_comparison',reason='reported_annual_pe_industry_reference_only',peer_median=middle,premium_fraction=premium)
    except (ValueError,TypeError,KeyError,AttributeError,OverflowError,RecursionError) as error:
        result['reason']=str(error) if isinstance(error,_Hold) else 'invalid_source_evidence'
    return result
