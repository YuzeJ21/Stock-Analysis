"""Project five independent research lanes onto one dated SEC issuer queue."""

from collections import Counter, defaultdict
from datetime import timedelta

from src.company_sec_online_preview import _utc_timestamp
from src.online_us_universe import build_universe_coverage, validated_us_universe


LANES = ('search', 'identity', 'financial', 'price', 'peer')
REVENUE_FIELDS = ('annual_revenue', 'quarterly_revenue', 'interim_revenue')


def _group(label, sic=None):
    return dict(label=label, sic=sic, denominator=0, lanes={
        lane: dict(available=0, failed=0, unprobed=0, reasons=Counter()) for lane in LANES
    })


def _count(group, results):
    group['denominator'] += 1
    for key, outcome in zip(LANES, results):
        lane = group['lanes'][key]
        if outcome is True:
            lane['available'] += 1
        elif outcome is None:
            lane['unprobed'] += 1
        else:
            lane['failed'] += 1
            lane['reasons'][outcome] += 1


def _financial_lanes(row):
    if not row:
        return None, None
    if not row['financial_source_matched']:
        return 'sec_facts_or_issuer_match_unavailable', row['annual_reason']
    identity = True if len(row['source_receipts']) == 3 else row['industry_reason']
    if any(row['fields'][field] for field in REVENUE_FIELDS):
        return identity, True
    reasons = sorted({row['annual_reason'], row['quarterly_reason']} - {'available'})
    return identity, ' / '.join(reasons) or 'no_supported_revenue_field'


def _recent_rows(rows, first):
    return {row['ticker']: row for row in rows
            if (observed := _utc_timestamp(row.get('attempted_at'))) is not None
            and timedelta(0) <= observed - first <= timedelta(hours=24)}


def _peer_result(row, cik, sic):
    if not row:
        return None
    if row.get('sec_cik') not in (None, cik):
        return 'peer_issuer_mismatch'
    if sic and row.get('sic') not in (None, sic):
        return 'peer_sec_sic_mismatch'
    if row.get('comparison_state') == 'available':
        if row.get('sec_cik') != cik or type(row.get('accepted_reference_count')) is not int or row['accepted_reference_count'] < 3:
            return 'peer_comparison_evidence_unverified'
        return True
    return row.get('primary_reason') or 'peer_comparison_unavailable'


def build_industry_coverage(inventory, observations, peer_summary=None, price_rows=()):
    """Read validated issuer/financial observations and in-process price/peer projections."""
    inventory = validated_us_universe(inventory)
    coverage = build_universe_coverage(inventory, observations)
    if coverage['status'] != 'inspection_only':
        return None
    first = _utc_timestamp(inventory['observed_from'])
    last = _utc_timestamp(inventory['observed_to'])
    search_probed = 'discover_searchable' in inventory['rows'][0]
    searchable = {row['sec_cik'] for row in inventory['rows']
                  if row.get('discover_searchable') is True and row['etf'] is not True}
    queue = {row['sec_cik']: row['ticker'] for row in inventory['issuer_queue']}
    listed_ciks = {row['sec_cik'] for row in inventory['rows'] if row['sec_cik']}
    financial_by_cik = {observation['sec_cik']: observation['row'] for observation in observations}
    representative_counts = Counter(queue.values())
    sample = peer_summary['rows'] if peer_summary and peer_summary.get('status') == 'inspection_only' else []
    peers = _recent_rows((row for row in sample if row.get('attempted') is True), first)
    prices = _recent_rows(price_rows, first)
    price_dates = set()
    total = _group('All issuer candidates')
    groups = {}
    descriptions = defaultdict(set)
    for cik, ticker in queue.items():
        financial = financial_by_cik.get(cik)
        sic = financial['sic'] if financial else None
        if sic and financial['sic_description']:
            descriptions[sic].add(financial['sic_description'])
        search = (True if cik in searchable else 'no_unambiguous_sec_search_route') if search_probed else None
        identity, financial_state = _financial_lanes(financial)
        price = prices.get(ticker)
        price_state = None
        if price and price['sec_cik'] == cik:
            price_state = price['reason'] or 'dated_price_unavailable'
            if price['available'] and price.get('price_date'):
                price_dates.add(price['price_date'])
                price_state = True
        peer_row = peers.get(ticker)
        if peer_row and representative_counts[ticker] > 1 and peer_row.get('sec_cik') != cik:
            peer_row = None
        peer = _peer_result(peer_row, cik, sic)
        for evidence in (price if price_state is not None else None, peer_row):
            if evidence:
                last = max(last, _utc_timestamp(evidence['attempted_at']))
        if financial:
            for receipt in financial['source_receipts']:
                last = max(last, _utc_timestamp(receipt['observed_at']))
        results = (search, identity, financial_state, price_state, peer)
        if sic not in groups:
            groups[sic] = _group('Unknown SIC' if sic is None else f'SIC {sic}', sic)
        _count(groups[sic], results)
        _count(total, results)
    for sic, labels in descriptions.items():
        if len(labels) == 1:
            groups[sic]['label'] += f' · {next(iter(labels))}'
    venues = [gap['venue'] for gap in inventory['venue_gaps']]
    venues.extend(venue for venue in inventory['by_venue'] if venue.lower().startswith('unresolved'))
    return dict(total=total, groups=[groups[sic] for sic in sorted(groups, key=lambda sic: sic or '99999')],
                peer_sample_size=len(sample), scope=dict(
                    observed_from=inventory['observed_from'], observed_to=inventory['observed_to'],
                    latest_evidence_at=last.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    source_receipts=inventory['source_receipts'], price_dates=sorted(price_dates),
                    inventory_count=inventory['listing_count'], known_etf_count=inventory['known_etf_count'],
                    unmatched_listing_count=inventory['unmatched_listing_count'],
                    outside_queue_cik_count=len(listed_ciks - queue.keys()),
                    sec_exchange_only_count=inventory['sec_only_listing_count'],
                    otc_excluded_count=inventory['otc_record_count'],
                    null_exchange_excluded_count=inventory['unknown_exchange_record_count'],
                    test_issues_excluded_count=inventory['excluded_test_issue_count'], venue_gaps=venues))
