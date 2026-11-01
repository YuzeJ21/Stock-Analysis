"""Reported comparative EPS context; callers bind the SEC receipt and issuer first.

This historical percentage never changes P/E eligibility or peer membership.
"""
from collections.abc import Mapping
from datetime import timedelta
import math

from src.company_sec_online_preview import _iso_date


def _finite(value):
    try:
        return type(value) in {int, float} and abs(value) <= 1e20 and math.isfinite(value)
    except (OverflowError, ValueError):
        return False


def annual_eps_context(facts: Mapping, current: Mapping) -> dict:
    """Use only an adjacent annual comparative from the same bound filing."""
    result = dict(status='withheld', reason='comparative_eps_input_invalid', growth_fraction=None,
                  basis='same_annual_filing_reported_comparative_eps')
    try:
        if not isinstance(current, Mapping) or not isinstance(facts, Mapping):
            return result
        start, end = _iso_date(current.get('period_start')), _iso_date(current.get('period_end'))
        if (not start or not end or not 350 <= (end-start).days <= 380
                or not _finite(current.get('eps')) or not current.get('accession')
                or current.get('form') not in {'10-K', '10-K/A', '20-F', '20-F/A'}
                or _iso_date(current.get('filed')) is None):
            return result
        result.update(current_eps=current['eps'], current_period_start=start.isoformat(),
                      current_period_end=end.isoformat(), accession=current['accession'],
                      form=current['form'], filed=current['filed'])
        units = facts.get('facts', {}).get('us-gaap', {}).get('EarningsPerShareDiluted', {}).get('units', {})
        rows = units.get('USD/shares') if isinstance(units, Mapping) else None
        if not isinstance(rows, list) or not 0 < len(rows) <= 10000:
            return {**result, 'reason': 'comparative_eps_missing'}
        prior_end = (start-timedelta(days=1)).isoformat()
        candidates = []
        for row in rows:
            if not isinstance(row, Mapping):
                return result
            if row.get('accn') != current['accession'] or row.get('end') != prior_end:
                continue
            if row.get('form') != current['form'] or row.get('filed') != current['filed']:
                return {**result, 'reason': 'comparative_eps_metadata_mismatch'}
            previous_start = _iso_date(row.get('start'))
            if previous_start is None or not 350 <= (_iso_date(prior_end)-previous_start).days <= 380:
                return {**result, 'reason': 'comparative_eps_period_invalid'}
            if not _finite(row.get('val')):
                return {**result, 'reason': 'comparative_eps_value_invalid'}
            candidates.append((row['start'], prior_end, float(row['val'])))
        if not candidates:
            return {**result, 'reason': 'comparative_eps_missing'}
        if len(set(candidates)) != 1:
            return {**result, 'reason': 'comparative_eps_conflict'}
        for unit, other in units.items():
            if unit != 'USD/shares' and isinstance(other, list) and any(
                    isinstance(row, Mapping) and row.get('accn') == current['accession']
                    and row.get('end') == prior_end for row in other):
                return {**result, 'reason': 'comparative_eps_unit_conflict'}
        previous_start, previous_end, value = candidates[0]
        result.update(prior_eps=value, prior_period_start=previous_start, prior_period_end=previous_end)
        if value <= 0:
            return {**result, 'reason': 'comparative_eps_base_nonpositive'}
        growth = current['eps']/value-1
        if not math.isfinite(growth) or abs(growth) > 1e6:
            return {**result, 'reason': 'comparative_eps_growth_outside_range'}
        return {**result, 'status': 'supported', 'reason': 'same_filing_reported_eps_change', 'growth_fraction': growth}
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        return result
