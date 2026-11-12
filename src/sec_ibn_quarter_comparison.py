"""Changes between independently verified consolidated IBN quarters."""
from datetime import timedelta

from src.company_sec_online_preview import _iso_date
from src.sec_ibn_interim_tables import DEFINITIONS


def compare_ibn_quarters(current, pair):
    """Compare matching direct income lines, keeping the cumulative data separate."""
    baseline = pair['baseline']
    before, after = baseline['periods'][0], current['periods'][0]
    if (pair['current_accession'] != current['accession'] or pair['current_period_end'] != after['period_end']
            or baseline['accession'] == current['accession']
            or before['kind'] != after['kind'] or after['kind'] != 'quarterly'
            or baseline['accounting_basis'] != current['accounting_basis']
            or _iso_date(after['period_start']) - _iso_date(before['period_end']) != timedelta(days=1)):
        return dict(status='withheld', fields={}, gaps=[])
    fields, gaps = {}, []
    for name, (caption, _, label) in DEFINITIONS.items():
        if caption != 'CONSOLIDATED FINANCIAL RESULTS':
            continue
        left, right = before['fields'].get(name), after['fields'].get(name)
        if not left or not right or any(left[key] != right[key] for key in ('definition', 'table_caption', 'unit', 'scale')):
            gaps.append(label)
            continue
        delta = right['value'] - left['value']
        fields[name] = dict(label=label, before=left['value'], after=right['value'], delta=delta,
                            fraction=delta / left['value'] if left['value'] > 0 else None)
    status = 'changed' if any(field['delta'] for field in fields.values()) else 'withheld' if gaps else 'unchanged'
    return dict(status=status, fields=fields, gaps=gaps, before=before['period_end'], after=after['period_end'])
