"""Compose already validated annual observations in one reporting currency."""
from datetime import timedelta
from math import isfinite

from src.company_sec_online_preview import _iso_date


def native_archive_annual_rows(foreign, archive):
    """Use the entire exact filing row and retain same-currency prior periods."""
    current = archive['periods'][0]
    prior = foreign['annual'] if foreign and foreign['unit'] == archive['unit'] else ()
    return [*(row for row in prior if row['period_end'] < current['period_end']), current]


def native_annual_comparison(current, history, coverage):
    """Find a corroborated consecutive year with a comparable reported field."""
    if current['status'] != 'available':
        return None
    start, end = _iso_date(current['period_start']), _iso_date(current['period_end'])
    if not start or not end or not 300 <= (end - start).days <= 430:
        return None
    states = coverage.get('periods', {}).get('annual', {})
    matches = []
    for row in history:
        if row['status'] != 'available' or states.get(row['period_end'], {}).get('status') != 'corroborated':
            continue
        prior_start, prior_end = _iso_date(row['period_start']), _iso_date(row['period_end'])
        if (prior_start and prior_end and prior_end == start - timedelta(days=1)
                and abs((end - start).days - (prior_end - prior_start).days) <= 14):
            matches.append(row)
    if len(matches) != 1:
        return None
    prior = matches[0]
    for name in ('revenue', 'operating_income'):
        before, after = prior['fields'].get(name), current['fields'].get(name)
        if (before and after and all(before[key] == after[key] for key in ('taxonomy', 'concept', 'unit'))
                and all(type(field['value']) in {int, float} and isfinite(field['value']) for field in (before, after))
                and before['value'] > 0):
            return dict(field=name, value=before['value'], current_value=after['value'],
                        period_end=prior['period_end'], source_ref=before['source_ref'])
    return None
