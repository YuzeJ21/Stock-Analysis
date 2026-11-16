"""Comparison rules for validated consolidated 6-K results."""
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

_TSM_ARCHIVE = 'https://www.sec.gov/Archives/edgar/data/1046179/'
_TSM_Q3_REVENUE_SCOPE = {
    'field': 'revenue', 'ticker': 'TSM', 'sec_cik': '0001046179', 'form': '6-K',
    'unit': 'TWD', 'period_start': '2026-07-01', 'period_end': '2026-09-30',
}
_TSM_Q3_REVENUE_LINES = (
    {
        'accession': '0001046179-26-000726', 'concept': 'reported_net_sales', 'row_label': 'Net sales',
        'source_url': _TSM_ARCHIVE + '000104617926000726/a3q26e_withguidancexfinal.htm',
    },
    {
        'accession': '0001046179-26-000801', 'concept': 'reported_net_revenue',
        'row_label': 'NET REVENUE (Notes 20, 31 and 37)',
        'source_url': _TSM_ARCHIVE + '000104617926000801/a2026q3consolidatedreport-.htm',
    },
)


def reviewed_filing_revenue_definition(baseline, current):
    """Return the reviewed definition evidence for these exact, prevalidated filing lines."""
    for field, line in zip((baseline, current), _TSM_Q3_REVENUE_LINES, strict=True):
        if not field or any(field.get(key) != value for key, value in (_TSM_Q3_REVENUE_SCOPE | line).items()):
            return None
    return {
        'source_url': _TSM_ARCHIVE + '000104617926000726/a3q26presentatione.htm',
        'source_label': 'October SEC presentation · Exhibit 99.2, slide 4',
        'explanation': 'The October presentation calls this same consolidated line net revenue. '
                       'November Note 20 reconciles the line to revenue from customer contracts.',
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
