from datetime import datetime, timedelta, timezone
from copy import deepcopy
import json

import pytest

from test_online_company_prices import _payload, _fetch, OBSERVED
from test_online_peer_valuation import collection, build
from test_online_peer_sources import source_dependencies, get


def large_payload(count):
    payload = _payload(); row = payload['chart']['result'][0]
    last = datetime(2026, 10, 29, 14, tzinfo=timezone.utc)
    row['timestamp'] = [int((last-timedelta(days=count-1-i)).timestamp()) for i in range(count)]
    row['indicators']['quote'] = [dict(open=[10]*count, high=[12]*count, low=[9]*count,
                                     close=[11]*count, volume=[100]*count)]
    return payload


def test_two_year_range_accepts_over_four_hundred_rows_and_binds_the_exact_request():
    from src.online_company_prices import fetch_online_company_prices, price_source_url
    calls = []
    def fetch(url): calls.append(url); return json.dumps(large_payload(510)).encode(), url
    result = fetch_online_company_prices('FICT', history_range='2y', observed_at=OBSERVED, fetcher=fetch)
    assert result['status'] == 'inspection_only' and len(result['bars']) == 510
    assert calls == [price_source_url('FICT', history_range='2y')]
    assert result['source_url'] == calls[0] and result['history_range'] == '2y'
    assert result['bars'][0]['date'] < '2025-09-30'
    assert result['commercial_eligible'] is False


@pytest.mark.parametrize('size,period,accepted', [(400,'1y',True),(401,'1y',False),
    (800,'2y',True),(801,'2y',False)])
def test_range_specific_bar_limits_stay_bounded(size, period, accepted):
    from src.online_company_prices import fetch_online_company_prices
    result = fetch_online_company_prices('FICT', history_range=period, observed_at=OBSERVED,
                                         fetcher=_fetch(large_payload(size)))
    assert (result['status'] == 'inspection_only') == accepted


@pytest.mark.parametrize('period', ['max','5y',None,[],1,'2y&interval=1m'])
def test_invalid_ranges_are_rejected_before_transport(period):
    from src.online_company_prices import fetch_online_company_prices
    result = fetch_online_company_prices('FICT', history_range=period,
                                         fetcher=lambda _:pytest.fail('unexpected transport'))
    assert result['reason'] == 'unsupported_price_history_range'


@pytest.mark.parametrize('mode,commercial', [('public',None),('operator',None),('research','1'),('research','invalid')])
def test_extended_range_never_bypasses_mode_guards(monkeypatch, mode, commercial):
    from src.online_company_prices import fetch_online_company_prices
    if commercial is None: monkeypatch.delenv('COMMERCIAL_RESEARCH_MODE', raising=False)
    else: monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE',commercial)
    assert fetch_online_company_prices('FICT', history_range='2y', workspace_mode=mode,
        fetcher=lambda _:pytest.fail('unexpected transport'))['status'] == 'unavailable'


def test_redirect_or_different_range_response_is_not_accepted():
    from src.online_company_prices import fetch_online_company_prices, price_source_url
    result = fetch_online_company_prices('FICT', history_range='2y', observed_at=OBSERVED,
        fetcher=lambda _: (json.dumps(_payload()).encode(), price_source_url('FICT')))
    assert result['reason'] == 'unverified_price_response'


def test_standalone_default_and_legacy_receipts_remain_one_year():
    from src.online_company_prices import fetch_online_company_prices, price_source_url
    from src.online_research_history_view import validated_online_price_history
    result = fetch_online_company_prices('FICT', observed_at=OBSERVED, fetcher=_fetch())
    assert result['history_range'] == '1y' and result['source_url'] == price_source_url('FICT')
    result.pop('history_range')
    assert validated_online_price_history(result) == result


@pytest.mark.parametrize('change', ['url','range','symbol','oversize'])
def test_validated_history_rejects_range_identity_and_row_limit_mismatch(change):
    from src.online_company_prices import fetch_online_company_prices
    from src.online_research_history_view import validated_online_price_history
    result = fetch_online_company_prices('FICT', history_range='2y', observed_at=OBSERVED,
                                         fetcher=_fetch(large_payload(510)))
    assert validated_online_price_history(result) is not None
    if change == 'url': result['source_url'] = result['source_url'].replace('range=2y','range=1y')
    elif change == 'range': result['history_range'] = '5y'
    elif change == 'symbol': result['provider_symbol'] = 'OTHER'
    else: result['bars'] = result['bars']*2
    assert validated_online_price_history(result) is None


def old_year_collection():
    c = collection()
    for row in c['issuers']:
        recent = row['profile']['payload']['filings']['recent']; recent['reportDate'] = ['2025-09-30']
        eps = row['facts']['payload']['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]
        eps.update(start='2024-10-01',end='2025-09-30')
    return c


def two_year_prices(c):
    from src.online_company_prices import price_source_url
    for row in c['issuers']:
        row['prices'].update(history_range='2y',source_url=price_source_url(row['ticker'],history_range='2y'))
        row['prices']['bars'].insert(0,dict(date='2024-11-01',close=row['prices']['bars'][0]['close']))
    return c


def test_actual_extended_history_recovers_old_period_without_altering_annual_definition():
    c = old_year_collection()
    assert build(c)['reason'] == 'split_history_does_not_cover_period_end'
    result = build(two_year_prices(c))
    assert result['status'] == 'research_comparison' and result['peer_count'] == 3
    assert result['subject']['price_history_range'] == '2y'
    assert result['subject']['price_history_first_date'] == '2024-11-01'
    assert result['subject']['price_history_last_date'] == '2026-10-30'
    assert result['subject']['basis'] == 'reported_annual_diluted_GAAP_EPS'


@pytest.mark.parametrize('change,reason', [('short','split_history_does_not_cover_period_end'),
    ('split','post_period_split_requires_share_basis_review'),('url','completed_price_source_unverified')])
def test_requested_range_alone_never_clears_insufficient_actual_coverage_or_splits(change, reason):
    c = two_year_prices(old_year_collection()); price = c['issuers'][0]['prices']
    if change == 'short': price['bars'].pop(0)
    elif change == 'split': price['splits'] = [dict(date='2026-01-01',numerator=2,denominator=1)]
    else: price['source_url'] = price['source_url'].replace('range=2y','range=1y')
    result = build(c)
    assert result['reason'] == reason and result['premium_fraction'] is None


def test_peer_collector_explicitly_requests_extended_history_and_retains_diagnostic_range():
    c = two_year_prices(collection()); d, calls = source_dependencies(c); original = d['prices']; ranges = []
    def prices(ticker, **kwargs):
        ranges.append(kwargs.get('history_range'))
        return original(ticker, **kwargs)
    d['prices'] = prices
    result = get({},refresh=True,dependencies=d)
    assert result['status'] == 'research_comparison' and ranges == ['2y']*4
    bad = deepcopy(c); bad['issuers'][1]['prices']['splits'] = [dict(date='2026-01-01',numerator=2,denominator=1)]
    diagnostic = build(bad)['excluded'][0]['diagnostics']['price_observation']
    assert diagnostic['history_range'] == '2y' and diagnostic['first_date'] == '2024-11-01'
