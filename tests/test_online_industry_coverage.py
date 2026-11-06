"""The five lanes share one issuer denominator and keep missing evidence visible."""

from copy import deepcopy
from datetime import timedelta
import json

from test_online_us_universe import E_URL, EXCHANGE, OBSERVED, _fetch, _inventory


def test_search_requires_an_exact_unambiguous_route_in_the_actual_discover_directory():
    from src.online_industry_coverage import build_industry_coverage

    base = _fetch([])

    def fetch(url, agent):
        if url == E_URL:
            exchange = deepcopy(EXCHANGE)
            exchange['data'] = [row for row in exchange['data'] if row[2] != 'BANK']
            return json.dumps(exchange).encode(), {}, url
        return base(url, agent)

    inventory = _inventory(fetcher=fetch)
    report = build_industry_coverage(inventory, [])
    assert report['total']['denominator'] == 3
    assert report['total']['lanes']['search'] == {
        'available': 2, 'failed': 1, 'unprobed': 0,
        'reasons': {'no_unambiguous_sec_search_route': 1},
    }
    assert [group['sic'] for group in report['groups']] == [None]
    assert report['scope']['unmatched_listing_count'] == 2
    assert report['scope']['known_etf_count'] == 1


def test_issuer_lanes_count_failed_pending_and_reject_cross_issuer_or_stale_evidence():
    from src.online_industry_coverage import build_industry_coverage
    from src.online_us_universe import inspect_next_universe_batch

    inventory = _inventory()
    state = inspect_next_universe_batch(
        {'inventory': inventory, 'observations': []}, user_agent='Research',
        batch_size=2, source_fetcher=_fetch([], fail_bank=True), observed_at=OBSERVED,
    )
    when = inventory['observed_from']
    stale = (OBSERVED + timedelta(hours=25)).strftime('%Y-%m-%dT%H:%M:%SZ')
    peer = {'status': 'inspection_only', 'rows': [
        dict(ticker='FICT', sec_cik='0000001234', attempted=True, attempted_at=when,
             comparison_state='available', accepted_reference_count=3, sic='3571'),
        dict(ticker='BANK', sec_cik='0000009999', attempted=True, attempted_at=when,
             comparison_state='available', accepted_reference_count=3, sic='6021'),
        dict(ticker='TEX', sec_cik='0000009876', attempted=True, attempted_at=stale,
             comparison_state='available', accepted_reference_count=3, sic='3571'),
    ]}
    price = [dict(ticker='BANK', sec_cik='0000005678', attempted_at=when,
                  available=False, reason='price_source_unavailable')]
    result = build_industry_coverage(inventory, state['observations'], peer, price)
    total = result['total']
    assert total['denominator'] == 3
    for lane in total['lanes'].values():
        assert lane['available'] + lane['failed'] + lane['unprobed'] == 3
        assert sum(lane['reasons'].values()) == lane['failed']
    assert [total['lanes'][name]['available'] for name in ('search', 'identity', 'financial', 'price', 'peer')] == [3, 1, 1, 0, 1]
    assert total['lanes']['peer']['reasons'] == {'peer_issuer_mismatch': 1}
    assert total['lanes']['peer']['unprobed'] == 1
    assert total['lanes']['price']['reasons'] == {'price_source_unavailable': 1}
    assert [(g['sic'], g['denominator']) for g in result['groups']] == [('3571', 1), (None, 2)]


def test_historical_checkpoint_without_search_proof_preserves_other_evidence():
    from src.online_industry_coverage import build_industry_coverage
    from src.online_us_universe import _finish_inventory

    inventory = _inventory()
    rows = [{k: v for k, v in row.items() if k != 'discover_searchable'} for row in inventory['rows']]
    old = _finish_inventory(rows, inventory['source_receipts'], inventory['excluded_test_issue_count'],
                            inventory['otc_record_count'], inventory['unknown_exchange_record_count'], inventory['map_receipt'])
    report = build_industry_coverage(old, [])
    assert report['total']['lanes']['search']['unprobed'] == 3
    assert report['total']['lanes']['search']['failed'] == 0
    assert report['scope']['observed_from'] == old['observed_from']
    assert build_industry_coverage(old, [{'inventory_fingerprint': 'another inventory'}]) is None


def test_inventory_does_not_claim_searchability_above_discover_response_limit():
    from src.online_industry_coverage import build_industry_coverage
    from src.providers.sec_company_discovery import MAX_RESPONSE_BYTES, search_sec_company_candidates

    base = _fetch([])
    oversized = json.dumps(EXCHANGE).encode() + b' ' * MAX_RESPONSE_BYTES

    def fetch(url, agent):
        return (oversized, {}, url) if url == E_URL else base(url, agent)

    search = search_sec_company_candidates('FICT', user_agent='Research', observed_at=OBSERVED,
                                           fetcher=lambda url, agent: (oversized, {}))
    inventory = _inventory(fetcher=fetch)
    assert search['reason'] == 'invalid_response_size'
    assert inventory['status'] == 'inspection_only'
    assert build_industry_coverage(inventory, [])['total']['lanes']['search']['available'] == 0
