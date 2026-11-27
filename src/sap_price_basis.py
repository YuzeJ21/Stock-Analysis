"""Read-only SAP listing/price context; never a currency or valuation approval."""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from src.company_sec_online_preview import _iso_date, _utc_timestamp
from src.online_company_identity import _mode_reason, _price_identity_valid
from src.sec_sap_snapshot_evidence import saved_sap_numeric_observation_indices


PRICE_IDENTITY_FIELDS = ('source_id', 'instrument_type', 'exchange_code', 'full_exchange_name',
    'exchange_timezone', 'adjustment_basis', 'rights_status', 'commercial_eligible')
PRICE_BASIS_FIELDS = ('status', 'ticker', 'provider_symbol', 'source_url', 'observed_at',
    'payload_sha256', 'currency', 'last_price_date', 'close', *PRICE_IDENTITY_FIELDS)


def assess_sap_price_basis(context):
    """Recompute from original source metadata, including on historical replay.

    This matches a quoted symbol/venue to the reviewed depositary listing. It
    cannot establish a vendor issuer identifier or historical security continuity.
    """
    result = dict(status='withheld', reason='sap_price_listing_context_unverified', ticker='SAP',
        sec_cik='0001000184', valuation_eligible=False, commercial_eligible=False,
        fx_status='unverified', vendor_issuer_identity_status='unverified', continuity_status='unverified',
        adjustment_status='unverified', accounting_comparability_status='unverified')
    try:
        if (_mode_reason('research') or context.get('saved_readiness_promoted') is not False
                or context.get('commercial_eligible') is not False):
            return result
        owner = context['peer_read_through']['subject_source_context']
        scope = owner['selected_security_scope']
        if not saved_sap_numeric_observation_indices(scope, context=context):
            return result
        price = context['price_context']
        # Reuse the original identity contract without treating a normalized
        # closing observation as a complete retained history.
        identity = dict(price, bars=[dict(date=price['last_price_date'], close=price['close'])])
        if (not _price_identity_valid('SAP', identity) or price.get('exchange_code') != 'NYQ'
                or price.get('full_exchange_name') != 'NYSE'
                or price.get('exchange_timezone') != 'America/New_York'
                or price.get('adjustment_basis') != 'provider_close_adjustment_basis_unverified'):
            return result
        receipts = context['source_receipts']
        if not isinstance(receipts, list):
            return result
        refs = [r for r in receipts if isinstance(r, dict) and r.get('source') == 'daily_prices']
        if len(refs) != 1 or any(refs[0].get(k) != price.get(k) for k in
                ('status', 'source_url', 'observed_at', 'payload_sha256')):
            return result
        binding = refs[0].get('price_identity')
        expected = {key: price.get(key) for key in PRICE_BASIS_FIELDS}
        if (not isinstance(binding, dict) or binding != expected
                or any(type(binding[key]) is not type(expected[key]) for key in PRICE_BASIS_FIELDS)):
            return result
        cutoff = _utc_timestamp(context['observed_at'])
        times = [_utc_timestamp(row) for row in (price['observed_at'], owner['profile_observed_at'],
            owner['selected_depositary_listing']['observed_at'])]
        if not cutoff or any(t is None or t > cutoff for t in times) or max(times)-min(times) > timedelta(hours=24):
            return result
        day = _iso_date(price['last_price_date'])
        close_clock = datetime.combine(day, time(16), ZoneInfo('America/New_York'))
        if (day.weekday() >= 5 or close_clock > times[0]
                or not timedelta(0) <= times[0]-close_clock <= timedelta(days=7)):
            return result
        return dict(result, status='matched_listing_context', reason=None,
            price_date=price['last_price_date'], observed_at=price['observed_at'],
            source_url=price['source_url'], payload_sha256=price['payload_sha256'])
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        return result
