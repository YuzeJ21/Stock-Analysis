"""A full observed listing denominator must retain every failed/unprobed issuer."""
from copy import deepcopy
from datetime import datetime, timezone
import json

import pytest

OBSERVED = datetime(2026, 10, 30, 22, tzinfo=timezone.utc)
N_URL = 'https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt'
O_URL = 'https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt'
M_URL = 'https://www.sec.gov/files/company_tickers.json'
E_URL = 'https://www.sec.gov/files/company_tickers_exchange.json'
N_BODY = ('Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares\n'
          'FICT|Fictional Co|Q|N|N|100|N|N\n'
          'FICT.B|Fictional B|Q|N|N|100|N|N\n'
          'FUND|Fictional ETF|G|N|N|100|Y|N\n'
          'ZZTEST|Test|Q|Y|N|100|N|N\n'
          'File Creation Time: 1030202615:41|||||||\n')
O_BODY = ('ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol\n'
          'BANK|Fictional Bank|N|BANK|N|100|N|BANK\n'
          'UNMAP|Unmapped issuer|WUT|UNMAP|N|100|N|UNMAP\n'
          'File Creation Time: 1030202615:41||||||\n')
MAP = {'0': {'ticker': 'FICT', 'cik_str': 1234, 'title': 'Fictional'},
       '1': {'ticker': 'FICT-B', 'cik_str': 1234, 'title': 'Fictional B'},
       '2': {'ticker': 'BANK', 'cik_str': 5678, 'title': 'Bank'},
       '3': {'ticker': 'TEX', 'cik_str': 9876, 'title': 'Texas'},
       '4': {'ticker': 'OTCO', 'cik_str': 3333, 'title': 'OTC'}}
EXCHANGE = {'fields': ['cik', 'name', 'ticker', 'exchange'], 'data': [
    [1234, 'Fictional', 'FICT', 'Nasdaq'], [1234, 'Fictional B', 'FICT-B', 'Nasdaq'],
    [5678, 'Bank', 'BANK', 'NYSE'], [9876, 'Texas', 'TEX', 'TXSE'],
    [3333, 'OTC', 'OTCO', 'OTC'], [4444, 'Unknown venue', 'NONE', None]]}


def _fetch(calls, *, fail_bank=False):
    from test_sec_quarterly_history import _quarter_payload
    from test_online_company_identity import _profile_payload
    def fetch(url, agent):
        calls.append(url)
        if url == N_URL: return N_BODY.encode(), {}, url
        if url == O_URL: return O_BODY.encode(), {}, url
        if url == M_URL: body = MAP
        elif url == E_URL: body = EXCHANGE
        elif '/companyfacts/' in url:
            if fail_bank and '0000005678' in url: raise OSError('private source error')
            body = _quarter_payload(); body['cik'] = int(url.rsplit('CIK', 1)[1].split('.')[0])
        elif '/submissions/' in url:
            cik = url.rsplit('CIK', 1)[1].split('.')[0]; ticker = {'0000001234': 'FICT', '0000005678': 'BANK', '0000009876': 'TEX'}[cik]
            body = _profile_payload(); body.update(cik=cik, tickers=[ticker], sic='6021' if ticker == 'BANK' else '3571')
        else: pytest.fail('unexpected source ' + url)
        return json.dumps(body).encode(), {}, url
    return fetch


def _inventory(calls=None, fetcher=None):
    from src.online_us_universe import load_online_us_universe
    return load_online_us_universe(user_agent='Research contact', fetcher=fetcher or _fetch(calls if calls is not None else []), observed_at=OBSERVED)


def test_full_observed_inventory_keeps_sec_only_unknown_venues_and_excludes_test_issues():
    result = _inventory()
    assert result['status'] == 'inspection_only'
    assert result['listing_count'] == 6  # five directory non-tests plus SEC-only TEX
    assert result['excluded_test_issue_count'] == 1
    assert result['known_etf_count'] == 1
    assert result['resolved_issuer_count'] == 3
    assert result['probe_issuer_count'] == 3  # FICT classes count once
    assert result['unmatched_listing_count'] == 2  # FUND and UNMAP
    assert result['sec_only_listing_count'] == 1
    assert result['otc_record_count'] == result['unknown_exchange_record_count'] == 1
    assert result['unknown_venue_codes'] == ['WUT']
    assert result['market_universe_coverage_established'] is False
    assert result['domicile_established'] is False
    assert {'LTSE', 'GIX'} <= {r['venue'] for r in result['venue_gaps']}
    assert len(result['source_receipts']) == 4
    assert not any(row['symbol'] == 'ZZTEST' for row in result['rows'])


def test_source_schema_dates_and_redirects_fail_closed():
    for issue in ['schema', 'future', 'redirect', 'flags']:
        base = _fetch([])
        def bad(url, agent):
            raw, headers, final = base(url, agent)
            if url == N_URL:
                if issue == 'schema': raw = raw.replace(b'Security Name', b'Name')
                if issue == 'future': raw = raw.replace(b'10302026', b'11012026')
                if issue == 'redirect': final = 'https://example.invalid/source'
                if issue == 'flags': raw = raw.replace(b'|Q|N|N|100', b'|Q|MAYBE|N|100')
            return raw, headers, final
        result = _inventory(fetcher=bad)
        assert result['status'] == 'unavailable'
        assert result.get('rows', []) == []


def test_conflicting_cik_alias_is_held_instead_of_name_matching():
    base = _fetch([])
    def fetch(url, agent):
        if url == M_URL:
            data = deepcopy(MAP); data['5'] = {'ticker': 'FICT.B', 'cik_str': 9999, 'title': 'Fictional B'}
            return json.dumps(data).encode(), {}, url
        return base(url, agent)
    result = _inventory(fetcher=fetch)
    row = next(r for r in result['rows'] if r['symbol'] == 'FICT.B')
    assert row['sec_cik'] is None and row['association_reason'] == 'ambiguous_cik_association'


def alias_collision_fetch(url, agent):
    directory_rows = (
        'INN$F|Summit Hotel Properties Series F Preferred Stock|N|INNpF|N|100|N|INN-F\n'
        'T$C|AT&T Series C Depositary Shares|N|TpC|N|100|N|T-C\n'
        'ALIAS|Fictional ordinary shares|N|ALTC|N|100|N|ALTC\n'
        'CROSS|Fictional notes|N|XB|N|100|N|XB\n'
        'MISSING|Fictional preferred shares|N|MISS|N|100|N|MISS\n'
    )
    tickers = [
        (1497645, 'Summit Hotel Properties', 'INN-PF', 'NYSE'),
        (1889791, 'Innocan Pharma', 'INNPF', 'OTC'),
        (77543, 'Tutor Perini', 'TPC', 'NYSE'),
        (1234, 'Fictional', 'ALTC', 'NYSE'),
        (5678, 'Fictional', 'XB', 'Nasdaq'),
        (5678, 'Fictional', 'MISS', None),
    ]
    if url == O_URL:
        return O_BODY.replace('File Creation Time:', directory_rows + 'File Creation Time:').encode(), {}, url
    if url == E_URL:
        return json.dumps({**EXCHANGE, 'data': [*EXCHANGE['data'], *tickers]}).encode(), {}, url
    if url == M_URL:
        mapping = dict(MAP)
        for i, (cik, title, ticker, _) in enumerate(tickers, len(mapping)):
            mapping[str(i)] = dict(cik_str=cik, title=title, ticker=ticker)
        return json.dumps(mapping).encode(), {}, url
    return _fetch([])(url, agent)


def test_directory_aliases_require_compatible_security_level_exchange_evidence():
    inventory = _inventory(fetcher=alias_collision_fetch)
    rows = {r['listing_id']: r for r in inventory['rows']}
    for symbol, reason in (
        ('INN$F', 'sec_symbol_exchange_conflict'),
        ('T$C', 'sec_symbol_exchange_unconfirmed'),
        ('CROSS', 'sec_symbol_exchange_conflict'),
        ('MISSING', 'sec_symbol_exchange_unconfirmed'),
    ):
        row = rows['other:' + symbol]
        assert row['sec_cik'] is row['sec_ticker'] is None
        assert row['association_reason'] == reason
    assert rows['sec:NYSE:INN-PF:0001497645']['sec_ticker'] == 'INN-PF'
    assert rows['sec:NYSE:TPC:0000077543']['sec_cik'] == '0000077543'
    assert rows['sec:Nasdaq:XB:0000005678']['sec_ticker'] == 'XB'
    assert rows['other:ALIAS']['sec_ticker'] == 'ALTC'
    assert 'sec:NYSE:ALTC:0000001234' not in rows
    assert rows['nasdaq:FICT.B']['sec_ticker'] == 'FICT-B'


def test_discover_shows_conflicting_alias_and_separate_sec_candidate():
    from src.security_classification import fetch_classification
    from src.security_classification_view import classification_html

    packet = fetch_classification(user_agent='Research contact', fetcher=alias_collision_fetch, observed_at=OBSERVED)
    directory = classification_html(packet, 'INN$F')
    assert 'Issuer match withheld · SEC exchange evidence conflicts with this listing' in directory
    assert '0001889791' not in directory
    assert 'SEC issuer candidate 0001497645' in classification_html(packet, 'INN-PF', observation_scope='SEC-only')


def test_batches_count_unique_issuers_and_leave_failures_and_unprobed_in_denominator(tmp_path, monkeypatch):
    from src.online_us_universe import inspect_next_universe_batch, build_universe_coverage
    calls = []; state = {'inventory': _inventory(calls), 'observations': []}
    assert len(calls) == 4
    before = build_universe_coverage(state['inventory'], [])
    assert before['issuer_denominator'] == 3 and before['unprobed_issuer_count'] == 3
    monkeypatch.chdir(tmp_path)
    result = inspect_next_universe_batch(state, user_agent='Research contact', batch_size=1, source_fetcher=_fetch(calls), observed_at=OBSERVED)
    assert result['coverage']['attempted_issuer_count'] == 1
    assert result['coverage']['unprobed_issuer_count'] == 2
    result = inspect_next_universe_batch(result, user_agent='Research contact', batch_size=2, source_fetcher=_fetch(calls, fail_bank=True), observed_at=OBSERVED)
    coverage = result['coverage']
    assert coverage['issuer_denominator'] == coverage['attempted_issuer_count'] == 3
    assert coverage['unprobed_issuer_count'] == 0 and coverage['source_failure_count'] == 1
    assert coverage['counts']['quarterly_revenue'] == 2
    assert len([u for u in calls if '/companyfacts/' in u]) == 3
    count = len(calls)
    inspect_next_universe_batch(result, user_agent='Research contact', source_fetcher=_fetch(calls), observed_at=OBSERVED)
    assert len(calls) == count
    assert not list(tmp_path.iterdir())
    assert 'private source error' not in json.dumps(result)
    assert '"value"' not in json.dumps(result)


def test_invalid_cached_inventory_or_cross_inventory_observation_cannot_be_counted():
    from src.online_us_universe import build_universe_coverage, inspect_next_universe_batch
    inventory = _inventory(); bad = deepcopy(inventory); bad['rows'][0]['sec_cik'] = '0000099999'
    assert build_universe_coverage(bad, [])['status'] == 'invalid'
    state = inspect_next_universe_batch({'inventory': inventory, 'observations': []}, user_agent='Research', batch_size=1, source_fetcher=_fetch([]), observed_at=OBSERVED)
    state['observations'][0]['inventory_fingerprint'] = 'f' * 64
    assert build_universe_coverage(inventory, state['observations'])['status'] == 'invalid'


def test_nonpersonal_activation_and_cached_reuse_make_no_requests(monkeypatch):
    from src.online_us_universe import load_online_us_universe, inspect_next_universe_batch
    inventory = _inventory()
    def forbidden(*a): pytest.fail('blocked mode fetched')
    assert load_online_us_universe(user_agent='Research', fetcher=forbidden, workspace_mode='commercial')['status'] == 'unavailable'
    monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE', '1')
    result = inspect_next_universe_batch({'inventory': inventory, 'observations': []}, user_agent='Research', source_fetcher=forbidden)
    assert result['status'] == 'unavailable'


def test_duplicate_or_wrong_cik_observation_cannot_inflate_coverage():
    from src.online_us_universe import inspect_next_universe_batch, build_universe_coverage
    state = inspect_next_universe_batch({'inventory': _inventory(), 'observations': []}, user_agent='Research', batch_size=1, source_fetcher=_fetch([]), observed_at=OBSERVED)
    obs = state['observations'][0]
    assert build_universe_coverage(state['inventory'], [obs, obs])['status'] == 'invalid'
    wrong = deepcopy(obs); wrong['row']['sec_cik'] = '0000099999'
    assert build_universe_coverage(state['inventory'], [wrong])['status'] == 'invalid'


def test_progress_requires_the_inventory_ticker_map_receipt_not_only_its_fingerprint():
    from src.online_us_universe import inspect_next_universe_batch, build_universe_coverage
    state = inspect_next_universe_batch({'inventory': _inventory(), 'observations': []}, user_agent='Research', batch_size=1, source_fetcher=_fetch([]), observed_at=OBSERVED)
    state['observations'][0]['row']['source_receipts'][1]['payload_sha256'] = 'd' * 64
    assert build_universe_coverage(state['inventory'], state['observations'])['status'] == 'invalid'


def test_directory_transport_requests_text_not_json_and_preserves_raw_receipt(monkeypatch):
    from src import online_us_universe as universe
    requests = []
    class Response:
        headers = {'Last-Modified': 'Fri, 30 Oct 2026 19:41:00 GMT'}
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, limit): return N_BODY.encode()
        def geturl(self): return N_URL
    def open_source(request, timeout):
        requests.append(request)
        # The real directory returns HTTP 406 for the SEC JSON Accept header.
        if request.get_header('Accept') == 'application/json': raise OSError('406')
        return Response()
    monkeypatch.setattr(universe, 'urlopen', open_source, raising=False)
    raw, headers, url = universe._fetch_directory(N_URL, 'Research contact')
    assert raw == N_BODY.encode() and url == N_URL
    assert requests[0].get_header('Accept') == 'text/plain'


def test_sec_access_limit_preserves_completed_row_and_pauses_remaining_issuer_requests():
    from urllib.error import HTTPError
    from src.online_us_universe import inspect_next_universe_batch
    calls=[];state={'inventory':_inventory(),'observations':[]};base=_fetch(calls)
    def limited(url,agent):
        if '/companyfacts/' in url and '0000005678' in url:
            calls.append(url)
            raise HTTPError(url,429,'Too many requests',{'Retry-After':'120'},None)
        return base(url,agent)
    result=inspect_next_universe_batch(state,user_agent='Research',batch_size=3,source_fetcher=limited,observed_at=OBSERVED)
    assert result['coverage']['attempted_issuer_count']==2
    assert result['coverage']['source_failure_count']==1 and result['coverage']['unprobed_issuer_count']==1
    assert result['source_access_pause']['http_status']==429
    assert not any('CIK0000009876' in u for u in calls)
    before=len(calls)
    same=inspect_next_universe_batch(result,user_agent='Research',source_fetcher=limited,observed_at=OBSERVED)
    assert len(calls)==before and same['source_access_pause']==result['source_access_pause']
