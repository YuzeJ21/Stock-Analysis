"""Changes between columns of an already validated consolidated 6-K results table."""
from math import isfinite

from src.sec_native_quarter_tables import matching_native_quarter_definition


BASES = {'year_over_year': 'Same quarter last year', 'sequential': 'Previous quarter'}
FIELDS = ('revenue', 'operating_income', 'cash_from_operations', 'capital_expenditures')
REASONS = {
    'compatible_quarter_field_unavailable': 'A matching directly reported field is unavailable.',
    'non_equivalent_reported_component': 'The source reports net property and equipment payments. Gross purchases need verification.',
    'positive_prior_value_required': 'Prior value must be positive for a percentage change.',
    'same_filing_comparison_unavailable': 'A comparable three-month column is unavailable.',
    'independent_comparison_revision_unresolved': 'A newer filing or amendment leaves the prior reporting basis unresolved.',
}


def quarter_changes(current, comparatives):
    """Calculate changes only for same-source current/prior field pairs."""
    result = {}
    for prior in comparatives:
        if prior['current_period_end'] != current['period_end']:
            continue
        changes = {}
        for name in FIELDS:
            latest, baseline = current['fields'].get(name), prior['fields'].get(name)
            if (not matching_native_quarter_definition(latest, baseline)
                    or any(latest[key] != baseline[key] for key in ('source_ref', 'payload_sha256'))):
                reason = current.get('withheld_fields', {}).get(name)
                changes[name] = dict(reason='non_equivalent_reported_component' if reason == 'non_equivalent_reported_component'
                                     else 'compatible_quarter_field_unavailable')
                continue
            delta = latest['value'] - baseline['value']
            fraction = delta / baseline['value'] if baseline['value'] > 0 else None
            if fraction is not None and not isfinite(fraction):
                fraction = None
            changes[name] = dict(current=latest, prior=baseline, fraction=fraction,
                                 reason='positive_prior_value_required' if fraction is None else None)
        result[prior['comparison_basis']] = dict(period=prior, fields=changes)
    return result
