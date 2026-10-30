"""All observed official U.S. listings, reconciled with explicit universe gaps."""

import argparse
from collections import Counter, defaultdict
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
import sys
import hashlib
import json
import os
import re
import time
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from src.company_sec_online_preview import _utc_timestamp
from src.online_company_identity import _mode_reason
from src.online_research_coverage import METRICS, run_online_coverage_study, validated_coverage_summary
from src.online_sec_receipt import fetch_sec_json_receipt
from src.providers.sec_company_discovery import _modified_at
from src.us_listing_receipt_audit import _SOURCES, _parse_directory, _MAX_DIRECTORY_BYTES

MAP_URL = 'https://www.sec.gov/files/company_tickers.json'
EXCHANGE_URL = 'https://www.sec.gov/files/company_tickers_exchange.json'
SOURCE_URLS = [r[2] for r in _SOURCES] + [MAP_URL, EXCHANGE_URL]
SESSION_KEY = 'online_us_universe_v1'
VENUES = {'Nasdaq': 'Nasdaq', 'N': 'NYSE', 'A': 'NYSE American', 'P': 'NYSE Arca',
          'Z': 'Cboe BZX', 'V': 'IEX', 'M': 'NYSE Texas', 'TXSE': 'TXSE', 'F': 'unresolved code F'}
VENUE_GAPS = [
    {'venue': 'LTSE', 'status': 'listing_membership_not_independently_reconciled', 'source_url': 'https://ltse.com/'},
    {'venue': 'GIX', 'status': 'listing_membership_not_independently_reconciled', 'source_url': 'https://www.tradegix.com/'},
    {'venue': 'NYSE Texas', 'status': 'dual_listing_membership_not_independently_reconciled', 'source_url': 'https://www.nyse.com/markets/nyse-texas'},
    {'venue': 'other_registered_venues', 'status': 'primary_and_dual_listing_scope_review_required',
     'source_url': 'https://www.sec.gov/about/divisions-offices/division-trading-markets/national-securities-exchanges'},
]


def _fetch_directory(url, user_agent):
    with urlopen(Request(url, headers={'User-Agent': user_agent, 'Accept': 'text/plain'}), timeout=30) as response:
        result = response.read(_MAX_DIRECTORY_BYTES + 1), dict(response.headers.items()), response.geturl()
    time.sleep(0.2)
    return result


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def _alias(symbol):
    # Only the explicit dot/dash share-class representation is normalized.
    return symbol.replace('.', '-')


def _sec_records(mapping, exchange):
    if (not isinstance(mapping, Mapping) or not 1 <= len(mapping) <= 100000
        or not isinstance(exchange, Mapping) or exchange.get('fields') != ['cik', 'name', 'ticker', 'exchange']
        or not isinstance(exchange.get('data'), list) or not 1 <= len(exchange['data']) <= 100000):
        raise ValueError('sec_listing_schema_invalid')
    records = []; map_rows = []
    for row in mapping.values():
        if not isinstance(row, Mapping): raise ValueError('sec_listing_schema_invalid')
        map_rows.append((row.get('cik_str'), row.get('title') or row.get('ticker'), row.get('ticker'), None))
    for row in [*map_rows, *exchange['data']]:
        if not isinstance(row, (list, tuple)) or len(row) != 4: raise ValueError('sec_listing_schema_invalid')
        cik, name, ticker, venue = row
        if (type(cik) not in {int, str} or not re.fullmatch(r'\d{1,10}', str(cik)) or int(cik) == 0
            or not isinstance(ticker, str) or not re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,19}', ticker)
            or not isinstance(name, str) or not name or len(name) > 500
            or venue is not None and (not isinstance(venue, str) or not 1 <= len(venue) <= 80)):
            raise ValueError('sec_listing_schema_invalid')
        records.append((str(int(cik)).zfill(10), name, ticker, venue))
    return records[:len(map_rows)], records[len(map_rows):]


def _finish_inventory(rows, refs, excluded, otc, unknown_exchange, map_receipt):
    by_issuer = defaultdict(list)
    for row in rows:
        if row['sec_cik'] and row['sec_ticker'] and row['etf'] is not True:
            by_issuer[row['sec_cik']].append(row['sec_ticker'])
    queue = [{'sec_cik': cik, 'ticker': sorted(set(tickers))[0]} for cik, tickers in sorted(by_issuer.items())]
    manifest = dict(rows=rows, source_receipts=refs, excluded_test_issue_count=excluded,
                    otc_record_count=otc, unknown_exchange_record_count=unknown_exchange,
                    map_content_sha256=_digest(map_receipt['payload']))
    return dict(status='inspection_only', **manifest, inventory_fingerprint=_digest(manifest), map_receipt=map_receipt,
        listing_count=len(rows), known_etf_count=sum(r['etf'] is True for r in rows),
        unknown_security_type_count=sum(r['etf'] is not True for r in rows),
        resolved_issuer_count=len({r['sec_cik'] for r in rows if r['sec_cik']}),
        unmatched_listing_count=sum(r['sec_cik'] is None for r in rows),
        sec_only_listing_count=sum(r['listing_id'].startswith('sec:') for r in rows),
        unknown_venue_codes=sorted({r['venue_code'] for r in rows if r['source'] != 'sec' and r['venue_code'] not in VENUES}),
        by_venue=dict(Counter(r['venue'] for r in rows)), probe_issuer_count=len(queue), issuer_queue=queue,
        observed_from=min(r['observed_at'] for r in refs), observed_to=max(r['observed_at'] for r in refs),
        venue_gaps=VENUE_GAPS, market_universe_coverage_established=False, domicile_established=False,
        analysis_eligibility_established=False, point_in_time_coverage_established=False,
        rights_status='unregistered_listing_metadata_personal_inspection_only', commercial_eligible=False)


def load_online_us_universe(*, user_agent, fetcher=None, observed_at=None, workspace_mode='research'):
    held = {'status': 'unavailable', 'reason': _mode_reason(workspace_mode) or 'listing_source_unavailable'}
    if _mode_reason(workspace_mode): return held
    if not isinstance(user_agent, str) or not user_agent.strip() or any(c in user_agent for c in '\r\n'):
        return {**held, 'reason': 'sec_user_agent_required'}
    if observed_at is not None and (not isinstance(observed_at, datetime) or observed_at.utcoffset() is None): return held
    refs = []; directory_rows = []; excluded = 0
    try:
        for source, _, url, columns in _SOURCES:
            raw, headers, final_url = (fetcher or _fetch_directory)(url, user_agent)
            now = (observed_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
            if final_url != url or not isinstance(raw, bytes) or not 0 < len(raw) <= _MAX_DIRECTORY_BYTES:
                raise ValueError('unverified_listing_response')
            _, tests, _, created, parsed = _parse_directory(raw, source, columns, allow_unknown_venues=True)
            created_time = datetime.fromisoformat(created).replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc)
            if not timedelta(0) <= now - created_time <= timedelta(days=7): raise ValueError('stale_or_future_listing_directory')
            refs.append(dict(source_url=url, observed_at=now.strftime('%Y-%m-%dT%H:%M:%SZ'), source_created_at=created,
                             source_last_modified=_modified_at(headers, now), payload_sha256=hashlib.sha256(raw).hexdigest()))
            directory_rows.extend(parsed); excluded += tests
        mapping = fetch_sec_json_receipt(MAP_URL, user_agent=user_agent, fetcher=fetcher, observed_at=observed_at)
        exchange = fetch_sec_json_receipt(EXCHANGE_URL, user_agent=user_agent, fetcher=fetcher, observed_at=observed_at)
        if mapping['status'] != 'ready' or exchange['status'] != 'ready': raise ValueError('sec_listing_receipt_unavailable')
        map_rows, exchange_rows = _sec_records(mapping['payload'], exchange['payload'])
        refs.extend({k: receipt[k] for k in ('source_url', 'observed_at', 'source_last_modified', 'payload_sha256')} for receipt in (mapping, exchange))
        if max(_utc_timestamp(r['observed_at']) for r in refs) - min(_utc_timestamp(r['observed_at']) for r in refs) > timedelta(hours=24):
            raise ValueError('listing_observation_gap')
        aliases = defaultdict(set); eligible = defaultdict(set)
        for cik, _, ticker, _ in [*map_rows, *exchange_rows]: aliases[_alias(ticker)].add(cik)
        for cik, _, ticker, _ in map_rows: eligible[cik].add(ticker)
        rows = []; represented = set()
        for raw in directory_rows:
            symbols = {s for s in (raw['act_symbol'], raw['cqs_symbol'], raw['nasdaq_symbol']) if s}
            ciks = set().union(*(aliases[_alias(s)] for s in symbols))
            cik = next(iter(ciks)) if len(ciks) == 1 else None
            mapped = sorted(t for t in eligible[cik] if _alias(t) in {_alias(s) for s in symbols}) if cik else []
            sec_ticker = mapped[0] if mapped else None
            for s in symbols:
                if cik: represented.add((cik, _alias(s)))
            code = 'Nasdaq' if raw['source'] == 'nasdaq' else raw['exchange_code']
            rows.append(dict(listing_id=raw['source'] + ':' + raw['act_symbol'], symbol=raw['act_symbol'],
                source=raw['source'], venue_code=code, venue=VENUES.get(code, 'Unresolved venue ' + code),
                etf=raw['etf'] == 'Y', sec_cik=cik, sec_ticker=sec_ticker,
                association_reason='ambiguous_cik_association' if len(ciks) > 1 else 'source_symbol_cik_matched' if cik else 'sec_symbol_unmatched'))
        otc = unknown_exchange = 0
        for cik, _, ticker, venue in exchange_rows:
            if venue == 'OTC': otc += 1; continue
            if venue is None: unknown_exchange += 1; continue
            if (cik, _alias(ticker)) in represented: continue
            represented.add((cik, _alias(ticker)))
            mapped = sorted(t for t in eligible[cik] if _alias(t) == _alias(ticker))
            rows.append(dict(listing_id='sec:' + venue + ':' + ticker + ':' + cik, symbol=ticker, source='sec',
                venue_code=venue, venue=venue, etf=None, sec_cik=cik, sec_ticker=mapped[0] if mapped else None,
                association_reason='sec_exchange_only_type_and_directory_status_unverified'))
        rows.sort(key=lambda row: row['listing_id'])
        if len({r['listing_id'] for r in rows}) != len(rows): raise ValueError('duplicate_listing_identity')
        return _finish_inventory(rows, refs, excluded, otc, unknown_exchange, mapping)
    except (ValueError, TypeError, KeyError, OSError, RuntimeError, OverflowError):
        return held


def validated_us_universe(inventory):
    if not isinstance(inventory, Mapping) or inventory.get('status') != 'inspection_only': return None
    rows = inventory.get('rows'); refs = inventory.get('source_receipts'); mapping = inventory.get('map_receipt')
    if (not isinstance(rows, list) or not 1 <= len(rows) <= 100000 or not isinstance(refs, list) or len(refs) != 4
        or not isinstance(mapping, Mapping) or mapping.get('status') != 'ready' or mapping.get('source_url') != MAP_URL): return None
    for ref, url in zip(refs, SOURCE_URLS):
        if (not isinstance(ref, Mapping) or ref.get('source_url') != url or _utc_timestamp(ref.get('observed_at')) is None
            or not isinstance(ref.get('payload_sha256'), str) or not re.fullmatch(r'[0-9a-f]{64}', ref['payload_sha256'])): return None
    if any(mapping.get(k) != refs[2].get(k) for k in ('source_url', 'observed_at', 'payload_sha256')): return None
    ids = set()
    for row in rows:
        if not isinstance(row, Mapping): return None
        if (not isinstance(row.get('listing_id'), str) or row['listing_id'] in ids
            or not isinstance(row.get('symbol'), str) or not re.fullmatch(r'[A-Z0-9][A-Z0-9.$-]{0,19}', row['symbol'])
            or row.get('source') not in {'nasdaq', 'other', 'sec'} or row.get('etf') not in {True, False, None}
            or any(not isinstance(row.get(k), str) for k in ('venue_code', 'venue', 'association_reason'))): return None
        ids.add(row['listing_id']); cik = row.get('sec_cik'); ticker = row.get('sec_ticker')
        if cik is not None and (not isinstance(cik, str) or not re.fullmatch(r'\d{10}', cik) or int(cik) == 0): return None
        if ticker is not None and (not isinstance(ticker, str) or not re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,19}', ticker) or cik is None): return None
    for key in ('excluded_test_issue_count', 'otc_record_count', 'unknown_exchange_record_count'):
        if type(inventory.get(key)) is not int or inventory[key] < 0: return None
    try:
        result = _finish_inventory(rows, refs, inventory['excluded_test_issue_count'], inventory['otc_record_count'], inventory['unknown_exchange_record_count'], mapping)
    except (ValueError, TypeError, KeyError): return None
    return result if result['inventory_fingerprint'] == inventory.get('inventory_fingerprint') else None


def build_universe_coverage(inventory, observations):
    inventory = validated_us_universe(inventory)
    held = {'status': 'invalid', 'reason': 'invalid_or_incompatible_universe_evidence'}
    if inventory is None or not isinstance(observations, list): return held
    queue = {r['sec_cik']: r['ticker'] for r in inventory['issuer_queue']}; seen = set(); rows = []
    for obs in observations:
        if not isinstance(obs, Mapping) or obs.get('inventory_fingerprint') != inventory['inventory_fingerprint']: return held
        cik = obs.get('sec_cik'); row = obs.get('row')
        if not isinstance(cik, str) or cik not in queue or cik in seen or not isinstance(row, Mapping): return held
        ticker = queue[cik]
        checked = validated_coverage_summary(dict(status='inspection_only', requested_tickers=[ticker], rows=[row]))
        if (checked is None or not row.get('attempted') or row.get('sec_cik') not in (None, cik)
            or row.get('financial_source_matched') and row.get('sec_cik') != cik): return held
        if row['financial_source_matched'] and any(row['source_receipts'][1].get(k) != inventory['map_receipt'].get(k) for k in ('source_url', 'observed_at', 'payload_sha256')): return held
        for ref in row['source_receipts']:
            observed = _utc_timestamp(ref['observed_at']); mapped = _utc_timestamp(inventory['observed_from'])
            if not timedelta(0) <= observed - mapped <= timedelta(hours=24): return held
        seen.add(cik); rows.append(row)
    industries = defaultdict(list)
    for row in rows: industries[row['sic']].append(row)
    unprobed = len(queue) - len(rows)
    return dict(status='inspection_only', inventory_fingerprint=inventory['inventory_fingerprint'],
        listing_denominator=inventory['listing_count'], issuer_denominator=len(queue),
        resolved_issuer_count=inventory['resolved_issuer_count'], attempted_issuer_count=len(rows), unprobed_issuer_count=unprobed,
        source_failure_count=sum(not r['financial_source_matched'] for r in rows),
        unsupported_financial_count=sum(r['financial_source_matched'] and not any(r['fields'][m] for m in ('annual_revenue', 'quarterly_revenue', 'interim_revenue')) for r in rows),
        counts={m: sum(r['fields'][m] for r in rows) for m in METRICS},
        unknown_industry_count=unprobed + sum(r['sic'] is None for r in rows),
        by_industry=[dict(sic=sic, attempted_issuer_count=len(members), counts={m: sum(r['fields'][m] for r in members) for m in METRICS}) for sic, members in sorted(industries.items(), key=lambda item: item[0] or '')],
        all_probe_candidates_attempted=unprobed == 0, market_universe_coverage_established=False,
        unresolved_listing_count=inventory['unmatched_listing_count'], rows=rows)


def validated_access_pause(value):
    from src.online_sec_receipt import _URL
    if not isinstance(value,Mapping) or set(value)!={'source_url','http_status','retry_after_seconds','paused_at','resume_after'}:return None
    if (not isinstance(value.get('source_url'),str) or not _URL.fullmatch(value['source_url'])
        or type(value.get('http_status')) is not int or value['http_status'] not in {403,429,503}
        or type(value.get('retry_after_seconds')) is not int or not 1<=value['retry_after_seconds']<=3600):return None
    paused=_utc_timestamp(value.get('paused_at'));resume=_utc_timestamp(value.get('resume_after'))
    if paused is None or resume is None or resume-paused!=timedelta(seconds=value['retry_after_seconds']):return None
    return dict(value)


def inspect_next_universe_batch(state, *, user_agent, batch_size=20, source_fetcher=None, observed_at=None, workspace_mode='research'):
    reason = _mode_reason(workspace_mode)
    if reason: return {'status': 'unavailable', 'reason': reason}
    if (not isinstance(state, Mapping) or type(batch_size) is not int or not 1 <= batch_size <= 20): return {'status': 'unavailable', 'reason': 'invalid_universe_batch'}
    inventory = validated_us_universe(state.get('inventory')); observations = state.get('observations', [])
    coverage = build_universe_coverage(inventory, observations)
    if coverage['status'] != 'inspection_only': return coverage
    now = observed_at or datetime.now(timezone.utc)
    if (not isinstance(now, datetime) or now.utcoffset() is None
        or not timedelta(0) <= now - _utc_timestamp(inventory['observed_from']) <= timedelta(hours=24)):
        return {'status': 'unavailable', 'reason': 'inventory_refresh_required'}
    pause=state.get('source_access_pause')
    if pause is not None:
        pause=validated_access_pause(pause)
        if pause is None:return {'status':'unavailable','reason':'invalid_source_access_pause'}
        if now<_utc_timestamp(pause['resume_after']):
            return dict(status='inspection_only',inventory=inventory,observations=observations,coverage=coverage,source_access_pause=pause)
    attempted = {r['sec_cik'] for r in observations}
    pending = [r for r in inventory['issuer_queue'] if r['sec_cik'] not in attempted][:batch_size]
    result = [*observations];pause=None
    for issuer in pending:
        study = run_online_coverage_study([issuer['ticker']], user_agent=user_agent, source_fetcher=source_fetcher,
            observed_at=observed_at, workspace_mode=workspace_mode, ticker_map_receipt=inventory['map_receipt'])
        checked = validated_coverage_summary(study)
        if checked is None: return {'status': 'unavailable', 'reason': 'invalid_issuer_probe'}
        result.append(dict(inventory_fingerprint=inventory['inventory_fingerprint'], sec_cik=issuer['sec_cik'], row=checked['rows'][0]))
        limit=study.get('source_access_limit')
        if limit:
            paused=(observed_at or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(microsecond=0)
            pause={**limit,'paused_at':paused.strftime('%Y-%m-%dT%H:%M:%SZ'),
                   'resume_after':(paused+timedelta(seconds=limit['retry_after_seconds'])).strftime('%Y-%m-%dT%H:%M:%SZ')}
            break
    state=dict(status='inspection_only', inventory=inventory, observations=result, coverage=build_universe_coverage(inventory, result))
    if pause:state['source_access_pause']=pause
    return state


def get_online_us_universe(session_state, *, user_agent, load_requested=False, inspect_requested=False,
                           batch_size=20, source_fetcher=None, observed_at=None, workspace_mode='research'):
    reason = _mode_reason(workspace_mode)
    if reason: return {'status': 'unavailable', 'reason': reason}
    if load_requested:
        inventory = load_online_us_universe(user_agent=user_agent, fetcher=source_fetcher,
            observed_at=observed_at, workspace_mode=workspace_mode)
        if inventory['status'] != 'inspection_only':
            session_state[SESSION_KEY] = inventory
            return inventory
        session_state[SESSION_KEY] = dict(status='inspection_only', inventory=inventory, observations=[])
    state = session_state.get(SESSION_KEY)
    if state is None: return {'status': 'not_requested'}
    if not isinstance(state, Mapping) or 'inventory' not in state:
        return {'status': 'unavailable', 'reason': 'listing_source_unavailable'}
    if inspect_requested:
        result = inspect_next_universe_batch(state, user_agent=user_agent, batch_size=batch_size,
            source_fetcher=source_fetcher, observed_at=observed_at, workspace_mode=workspace_mode)
        if result.get('status') != 'inspection_only': return result
        session_state[SESSION_KEY] = result
        return result
    inventory = validated_us_universe(state.get('inventory'))
    coverage = build_universe_coverage(inventory, state.get('observations', []))
    if coverage['status'] != 'inspection_only': return coverage
    result=dict(status='inspection_only', inventory=inventory, observations=state.get('observations', []), coverage=coverage)
    if state.get('source_access_pause') is not None:
        pause=validated_access_pause(state['source_access_pause'])
        if pause is None:return {'status':'unavailable','reason':'invalid_source_access_pause'}
        result['source_access_pause']=pause
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='Online full observed listing inventory and serialized issuer coverage; no raw source files or price batch.')
    parser.add_argument('--scan-all', action='store_true', help='Attempt the complete observed issuer queue with serialized SEC access.')
    parser.add_argument('--batch-size', type=int, default=20)
    parser.add_argument('--batches', type=int, default=0, help='Number of financial batches; zero loads inventory only.')
    parser.add_argument('--checkpoint',help='Explicit private reduced JSON checkpoint; no raw financial amounts.')
    parser.add_argument('--resume',action='store_true',help='Restore this checkpoint without refetching its inventory.')
    args = parser.parse_args(argv)
    if not 1 <= args.batch_size <= 20 or not 0 <= args.batches <= 100000: parser.error('invalid batch limits')
    from src.online_coverage_checkpoint import load_coverage_checkpoint,save_coverage_checkpoint
    if args.resume and not args.checkpoint:parser.error('--resume requires --checkpoint')
    expected_digest=None
    if args.resume:
        restored=load_coverage_checkpoint(args.checkpoint)
        if restored['status']!='ready':print(json.dumps(restored));return 2
        state=restored['state'];inventory=state['inventory'];expected_digest=restored['checkpoint_digest']
    else:
        inventory=load_online_us_universe(user_agent=os.getenv('SEC_USER_AGENT'))
        if inventory['status']!='inspection_only':print(json.dumps(inventory));return 2
        state=dict(inventory=inventory,observations=[])
    def persist():
        nonlocal expected_digest
        if not args.checkpoint:return True
        saved=save_coverage_checkpoint(args.checkpoint,state,expected_digest=expected_digest)
        if saved['status']!='saved':print(json.dumps(saved));return False
        expected_digest=saved['checkpoint_digest'];return True
    if not persist():return 2
    batches = 0
    while args.scan_all or batches < args.batches:
        state = inspect_next_universe_batch(state, user_agent=os.getenv('SEC_USER_AGENT'), batch_size=args.batch_size)
        if state.get('status') != 'inspection_only': print(json.dumps(state)); return 2
        batches += 1
        if not persist():return 2
        print('Coverage checked '+str(state['coverage']['attempted_issuer_count'])+'/'+str(state['coverage']['issuer_denominator'])+' issuer candidates',file=sys.stderr,flush=True)
        if state.get('source_access_pause'):
            print(json.dumps({'status':'paused','coverage':state['coverage'],'source_access_pause':state['source_access_pause']},indent=2));return 3
        if state['coverage']['all_probe_candidates_attempted']: break
    summary = {k: v for k, v in inventory.items() if k not in {'map_receipt', 'rows', 'issuer_queue'}}
    print(json.dumps(dict(inventory=summary, coverage=build_universe_coverage(inventory, state['observations'])), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
