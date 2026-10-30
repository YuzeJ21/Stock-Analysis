"""Source-bound IFRS direct amounts in a single reporting currency; no conversion."""

from collections import defaultdict
from collections.abc import Mapping
import re

from src.company_sec_online_preview import ANNUAL_FORMS, _iso_date, _utc_timestamp, _finite_direct_number
from src.online_company_identity import financial_identity_valid
from src.sec_fundamentals_preview import _valid_companyfacts_payload
from src.sec_quarterly_history import FIELDS, RIGHTS, REVISION_HOLD, field_is_permitted

CONCEPTS = {
    'revenue': ('Revenue',),
    'operating_income': ('ProfitLossFromOperatingActivities',),
    'cash_from_operations': ('CashFlowsFromUsedInOperatingActivities', 'CashFlowsFromUsedInOperatingActivitiesContinuingOperations'),
    'capital_expenditures': ('PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities',),
}
FORMS = ANNUAL_FORMS | {'6-K', '6-K/A', '10-Q', '10-Q/A'}
BASIS = 'latest_reported_as_observed_not_point_in_time'


def _kind(start, end, form):
    if start is None or end is None or not isinstance(form, str): return None
    days = (end - start).days
    if 300 <= days <= 430 and form in ANNUAL_FORMS: return 'annual'
    if 70 <= days <= 105: return 'quarterly'
    if 150 <= days <= 210 or 240 <= days <= 300: return 'interim'
    return None


def _context(raw, observed):
    start, end, filed = (_iso_date(raw.get(k)) for k in ('start', 'end', 'filed'))
    if (not start or not end or not filed or not start < end <= filed <= observed.date()
        or not isinstance(raw.get('form'), str) or raw['form'] not in FORMS or not isinstance(raw.get('accn'), str)
        or not re.fullmatch(r'\d{10}-\d{2}-\d{6}', raw['accn'])): return None
    kind = _kind(start, end, raw['form'])
    return kind if kind else None


def _records(payload, concept):
    return payload['facts'].get('ifrs-full', {}).get(concept, {}).get('units', {})


def _reported_anchors(payload, observed):
    """Period metadata across IFRS concepts, independent of usable revenue."""
    groups = defaultdict(list)
    for fact in payload['facts'].get('ifrs-full', {}).values():
        for records in fact['units'].values():
            for raw in records:
                kind = _context(raw, observed)
                if kind: groups[kind].append(raw)
    result = {}
    for kind in ('annual', 'quarterly', 'interim'):
        records = groups[kind]
        if not records:
            result[kind] = None
            continue
        end = max(r['end'] for r in records)
        relevant = [r for r in records if r['end'] == end]
        filed = max(r['filed'] for r in relevant)
        starts = {r['start'] for r in relevant if r['filed'] == filed}
        result[kind] = dict(period_end=end, filed=filed, period_start=next(iter(starts)) if len(starts) == 1 else None)
    return result


def _revision_hold(payload, concepts, context, kind, observed):
    for concept in concepts:
        for records in _records(payload, concept).values():
            for raw in records:
                if raw.get('end') != context['end'] and not (_iso_date(raw.get('end')) is None and raw.get('start') == context['start']): continue
                start, end, filed = (_iso_date(raw.get(k)) for k in ('start', 'end', 'filed'))
                raw_kind = _kind(start, end, raw.get('form'))
                if raw_kind and raw_kind != kind: continue
                if start and raw.get('start') != context['start'] and raw_kind is None: continue
                if filed and (filed < _iso_date(context['filed']) or filed > observed.date()): continue
                if filed is None or any(raw.get(k) != v for k, v in context.items()): return True
    return False


def _direct(payload, field, unit, context, kind, observed, metadata, permitted):
    if not permitted: return None, 'field_scope_unreviewed'
    if _revision_hold(payload, CONCEPTS[field], context, kind, observed): return None, REVISION_HOLD
    for concept in CONCEPTS[field]:
        rows = [r for r in _records(payload, concept).get(unit, []) if all(r.get(k) == v for k, v in context.items())]
        if not rows: continue
        if any(not _finite_direct_number(r.get('val')) for r in rows) or len({r['val'] for r in rows}) != 1:
            return None, 'raw_source_conflict'
        return dict(field=field, taxonomy='ifrs-full', concept=concept, unit=unit, value=rows[0]['val'],
            period_start=context['start'], period_end=context['end'], filed=context['filed'],
            accession=context['accn'], form=context['form'], rights_status=RIGHTS, **metadata), None
    return None, 'matching_direct_fact_unavailable'


def build_sec_foreign_financials(ticker, payload, *, expected_cik, observed_at, source_url, payload_sha256):
    held = dict(status='withheld', reason='foreign_source_unavailable', ticker=ticker, annual=[], quarterly=[], interim=[])
    observed = _utc_timestamp(observed_at)
    if (not isinstance(ticker, str) or not re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,19}', ticker)
        or not isinstance(expected_cik, str) or not re.fullmatch(r'\d{10}', expected_cik) or int(expected_cik) == 0
        or source_url != f'https://data.sec.gov/api/xbrl/companyfacts/CIK{expected_cik}.json'
        or not isinstance(payload_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', payload_sha256)
        or observed is None or not _valid_companyfacts_payload(payload)): return held
    raw_cik = payload.get('cik')
    if type(raw_cik) not in {int, str} or not re.fullmatch(r'\d{1,10}', str(raw_cik)) or str(int(raw_cik)).zfill(10) != expected_cik:
        return {**held, 'reason': 'companyfacts_identity_mismatch'}
    if 'ifrs-full' not in payload['facts']: return {**held, 'reason': 'ifrs_standard_facts_unavailable'}
    anchors = _reported_anchors(payload, observed)
    held['reported_period_anchors'] = anchors
    permitted = {f: field_is_permitted(f) for f in FIELDS}
    if not permitted['revenue']: return {**held, 'reason': 'field_scope_unreviewed'}
    candidates = [(unit, r) for unit, rows in _records(payload, 'Revenue').items() for r in rows
                  if re.fullmatch(r'[A-Z]{3}', unit) and _context(r, observed)]
    if not candidates: return {**held, 'reason': 'supported_ifrs_revenue_unavailable'}
    newest_end = max(r['end'] for _, r in candidates)
    # A later convenience USD publication cannot silently replace native history.
    units = {u for u, r in candidates if r['end'] == newest_end}
    native = units - {'USD'}
    if len(native) > 1: return {**held, 'reason': 'ambiguous_reporting_currency'}
    unit = next(iter(native)) if native else 'USD'
    groups = defaultdict(list)
    for currency, r in candidates:
        if currency == unit: groups[(_context(r, observed), r['end'])].append(r)
    result = {**held, 'status': 'inspection_only', 'reason': None, 'unit': unit,
        'sec_cik': expected_cik, 'source_url': source_url, 'payload_sha256': payload_sha256,
        'observed_at': observed_at, 'history_basis': BASIS,
        'currency_basis': 'single_non_USD_currency_preferred_to_convenience_USD_no_conversion'}
    metadata = dict(source_ref=source_url, observed_at=observed_at, payload_sha256=payload_sha256)
    for (kind, end), records in sorted(groups.items()):
        filed = max(r['filed'] for r in records)
        contexts = {(r['start'], r['accn'], r['form']) for r in records if r['filed'] == filed}
        row = dict(period_end=end, period_start=None, filed=filed, status='withheld', fields={},
                   withheld_fields={f: 'revenue_anchor_withheld' for f in FIELDS}, reason='ambiguous_filing_context')
        if len(contexts) == 1:
            start, accession, form = next(iter(contexts))
            row.update(period_start=start, accession=accession, form=form)
            context = dict(start=start, end=end, filed=filed, accn=accession, form=form)
            revenue, reason = _direct(payload, 'revenue', unit, context, kind, observed, metadata, True)
            row['reason'] = reason
            if revenue:
                row.update(status='available', fields={'revenue': revenue}, withheld_fields={})
                for name in FIELDS[1:]:
                    field, reason = _direct(payload, name, unit, context, kind, observed, metadata, permitted[name])
                    if field: row['fields'][name] = field
                    else: row['withheld_fields'][name] = reason
        result[kind].append(row)
    for kind, maximum in [('annual', 6), ('quarterly', 12), ('interim', 12)]:
        latest = anchors[kind]
        if latest and (not result[kind] or latest['period_end'] > result[kind][-1]['period_end']):
            result[kind].append(dict(**latest, status='withheld', fields={},
                withheld_fields={f: 'revenue_anchor_withheld' for f in FIELDS},
                reason='latest_reported_foreign_revenue_unavailable'))
        result[kind] = result[kind][-maximum:]
    return result


def validated_foreign_financials(view):
    if not isinstance(view, Mapping): return None
    h = view.get('foreign_financials'); identity = view.get('companyfacts_identity')
    if (not isinstance(h, Mapping) or h.get('status') != 'inspection_only'
        or not financial_identity_valid(view.get('ticker'), identity)
        or any(h.get(k) != identity.get(k) for k in ('ticker', 'sec_cik', 'source_url', 'observed_at', 'payload_sha256'))
        or not isinstance(h.get('unit'), str) or not re.fullmatch(r'[A-Z]{3}', h['unit']) or h.get('history_basis') != BASIS): return None
    observed = _utc_timestamp(h['observed_at'])
    for kind, maximum in [('annual', 6), ('quarterly', 12), ('interim', 12)]:
        rows = h.get(kind)
        if not isinstance(rows, list) or len(rows) > maximum: return None
        previous = None
        for row in rows:
            if not isinstance(row, Mapping): return None
            start, end, filed = (_iso_date(row.get(k)) for k in ('period_start', 'period_end', 'filed'))
            if not end or not filed or not end <= filed <= observed.date() or previous and end <= previous: return None
            previous = end
            if row.get('status') == 'withheld':
                if row.get('fields') != {} or row.get('reason') not in {'ambiguous_filing_context', REVISION_HOLD, 'raw_source_conflict', 'matching_direct_fact_unavailable', 'latest_reported_foreign_revenue_unavailable'}: return None
                continue
            if (row.get('status') != 'available' or not start or _kind(start, end, row.get('form')) != kind
                or row.get('form') not in FORMS or not isinstance(row.get('accession'), str)
                or not re.fullmatch(r'\d{10}-\d{2}-\d{6}', row['accession'])): return None
            fields, withheld = row.get('fields'), row.get('withheld_fields')
            if (not isinstance(fields, Mapping) or not isinstance(withheld, Mapping) or 'revenue' not in fields
                or set(fields) | set(withheld) != set(FIELDS) or set(fields) & set(withheld)): return None
            if any(r not in {'field_scope_unreviewed', REVISION_HOLD, 'raw_source_conflict', 'matching_direct_fact_unavailable'} for r in withheld.values()): return None
            for name, field in fields.items():
                if (not isinstance(field, Mapping) or field.get('field') != name or field.get('taxonomy') != 'ifrs-full'
                    or field.get('concept') not in CONCEPTS[name] or field.get('unit') != h['unit']
                    or field.get('rights_status') != RIGHTS or not _finite_direct_number(field.get('value'))): return None
                expected = dict(period_start=row['period_start'], period_end=row['period_end'], filed=row['filed'],
                    accession=row['accession'], form=row['form'], source_ref=h['source_url'], observed_at=h['observed_at'], payload_sha256=h['payload_sha256'])
                if any(field.get(k) != v for k, v in expected.items()): return None
    return dict(h)
