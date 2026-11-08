"""Generic SEC filing versions and separate personal annual inspection fields.

This module performs no transport and never changes canonical/approved fields. A
receipt's original HTTP digest is retained separately from normalized metadata.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re

from src.company_sec_online_preview import ANNUAL_FORMS, _iso_date, _utc_timestamp, _finite_direct_number
from src.online_company_identity import _mode_reason, financial_identity_valid

SCHEMA = 'online-filing-inventory-v1'
COMPONENT_SCHEMA = 'online-earnings-components-v1'
RIGHTS = 'personal_inspection_only'
MAX_NORMALIZED_BYTES = 2 * 1024 * 1024
_FORMS = {'annual': ANNUAL_FORMS, 'quarterly': frozenset({'10-Q', '10-Q/A'})}
_COLUMNS = ('accessionNumber', 'form', 'reportDate', 'filingDate', 'acceptanceDateTime', 'primaryDocument')
_ANCHOR_KEYS = {'accession', 'form', 'period_end', 'report_date', 'filed', 'accepted_at', 'primary_document', 'source_url', 'amendment'}
_FIELDS = {
    'net_income': {'us-gaap': ('NetIncomeLoss', 'ProfitLoss'), 'ifrs-full': ('ProfitLoss',)},
    'diluted_eps': {'us-gaap': ('EarningsPerShareDiluted',), 'ifrs-full': ('DilutedEarningsLossPerShare',)},
    'stock_based_compensation': {'us-gaap': ('ShareBasedCompensation',), 'ifrs-full': ('SharebasedPaymentExpense',)},
    'intangible_amortization': {'us-gaap': ('AmortizationOfIntangibleAssets',), 'ifrs-full': ('AmortisationOfIntangibleAssets',)},
    'disposal_gain': {'us-gaap': ('GainLossOnSaleOfBusiness',), 'ifrs-full': ()},
}


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _digest(value):
    return hashlib.sha256(_json(value)).hexdigest()


def _hash(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _identity(ticker, cik):
    return (isinstance(ticker, str) and re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,19}', ticker) is not None
            and isinstance(cik, str) and re.fullmatch(r'\d{10}', cik) is not None and int(cik) > 0)


def _cik(value):
    if type(value) not in {int, str} or re.fullmatch(r'\d{1,10}', str(value)) is None or int(value) == 0:
        return None
    return str(int(value)).zfill(10)


def _now(as_of):
    value = datetime.now(timezone.utc) if as_of is None else as_of
    if not isinstance(value, datetime) or value.utcoffset() is None:
        return None
    return value.astimezone(timezone.utc)


def _fresh(value, now, historical=False):
    observed = _utc_timestamp(value)
    return bool(observed and now and timedelta(0) <= now - observed
                and (historical or now - observed <= timedelta(hours=24)))


def _ref(receipt, url, now, historical=False):
    if not isinstance(receipt, Mapping) or receipt.get('source_url') != url or not _hash(receipt.get('payload_sha256')):
        return None
    if not _fresh(receipt.get('observed_at'), now, historical):
        return None
    modified = receipt.get('source_last_modified')
    if modified is not None and (_utc_timestamp(modified) is None or _utc_timestamp(modified) > _utc_timestamp(receipt['observed_at'])):
        return None
    return {k: receipt.get(k) for k in ('source_url', 'observed_at', 'source_last_modified', 'payload_sha256')}


def _safe_text(value, maximum=240):
    return isinstance(value, str) and 0 < len(value) <= maximum and value == value.strip() and not any(ord(c) < 32 or ord(c) == 127 for c in value)


def _valid_anchor(anchor, cik, observed, forms):
    if not isinstance(anchor, Mapping) or set(anchor) != _ANCHOR_KEYS:
        return False
    end, filed = _iso_date(anchor.get('period_end')), _iso_date(anchor.get('filed'))
    accepted = _utc_timestamp(anchor.get('accepted_at'))
    accession, document = anchor.get('accession'), anchor.get('primary_document')
    event_without_date = anchor.get('form') in {'8-K', '8-K/A', '6-K', '6-K/A'} and anchor.get('period_end') is None
    if ((not end and not event_without_date) or not filed or not accepted
            or not filed <= observed.date() or not accepted.date() <= observed.date() or accepted > observed
            or end is not None and (end > filed or end > accepted.date())
            or anchor.get('report_date') != anchor.get('period_end')
            or not isinstance(anchor.get('form'), str) or anchor['form'] not in forms
            or type(anchor.get('amendment')) is not bool or anchor['amendment'] != anchor['form'].endswith('/A')
            or not isinstance(accession, str) or re.fullmatch(r'\d{10}-\d{2}-\d{6}', accession) is None
            or not isinstance(document, str) or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,180}\.(?:htm|html|xhtml)', document) is None
            or '..' in document):
        return False
    return anchor.get('source_url') == f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace("-", "")}/{document}'


def _sort(anchor):
    return anchor['period_end'] or '', anchor['filed'], _utc_timestamp(anchor['accepted_at']), anchor['accession']


def _latest(rows):
    if not rows:
        return None
    end = max(r['period_end'] for r in rows)
    relevant = [r for r in rows if r['period_end'] == end]
    publication = max((r['filed'], _utc_timestamp(r['accepted_at'])) for r in relevant)
    relevant = [r for r in relevant if (r['filed'], _utc_timestamp(r['accepted_at'])) == publication]
    if len(relevant) != 1:
        return None
    return deepcopy(relevant[0])


def _normalized(packet):
    return {k: packet[k] for k in ('issuer', 'latest', 'periods', 'earnings_reports', 'review_triggers')}


def _seal(packet):
    result = deepcopy(packet)
    result['normalized_sha256'] = _digest(_normalized(result))
    result['packet_digest'] = _digest(result)
    return result


def _empty(ticker, cik, reason):
    return _seal(dict(schema_version=SCHEMA, status='withheld', reason=reason, ticker=ticker if isinstance(ticker, str) else None,
        sec_cik=cik if isinstance(cik, str) else None, observed_at=None, source_receipt=None, source_receipts=[],
        issuer=dict(name=None, sic=None, entity_type=None, fiscal_year_end=None),
        latest=dict(annual=None, quarterly=None), periods=dict(annual=[], quarterly=[]), earnings_reports=[], review_triggers=[],
        rights_status=RIGHTS, commercial_eligible=False, saved_readiness_promoted=False))


def build_filing_inventory(receipt, *, ticker, expected_cik, as_of=None):
    """Normalize one current submissions receipt; newest reporting period wins.

    Every revision remains in ``periods``. 6-K/8-K metadata is kept as review
    triggers; its event report date is never invented into a financial quarter.
    """
    reason = _mode_reason('research')
    held = _empty(ticker, expected_cik, reason or 'filing_inventory_unavailable')
    now = _now(as_of)
    if reason or not _identity(ticker, expected_cik) or now is None:
        return held
    url = f'https://data.sec.gov/submissions/CIK{expected_cik}.json'
    ref = _ref(receipt, url, now)
    if not ref or receipt.get('status') != 'ready':
        return _empty(ticker, expected_cik, 'submissions_receipt_unavailable')
    body = receipt.get('payload')
    if not isinstance(body, Mapping) or _cik(body.get('cik')) != expected_cik:
        return _empty(ticker, expected_cik, 'submissions_identity_mismatch')
    try:
        aliases = {ticker, ticker.replace('.', '-'), ticker.replace('-', '.')}
        tickers = body.get('tickers')
        if tickers is not None and (not isinstance(tickers, list) or len(tickers) > 128
                or any(not _safe_text(t, 24) for t in tickers) or tickers and not aliases.intersection(tickers)):
            raise ValueError('submissions_ticker_mismatch')
        issuer = dict(name=body.get('name'), sic=body.get('sic'), entity_type=body.get('entityType'), fiscal_year_end=body.get('fiscalYearEnd'))
        for key in ('name', 'entity_type'):
            if issuer[key] in ('', None): issuer[key] = None
            elif not _safe_text(issuer[key]): raise ValueError('issuer_metadata_invalid')
        if issuer['sic'] in ('', None): issuer['sic'] = None
        elif type(issuer['sic']) in {int, str} and re.fullmatch(r'\d{4}', str(issuer['sic'])) and str(issuer['sic']) != '0000': issuer['sic'] = str(issuer['sic'])
        else: raise ValueError('issuer_metadata_invalid')
        if issuer['fiscal_year_end'] in ('', None): issuer['fiscal_year_end'] = None
        elif not isinstance(issuer['fiscal_year_end'], str) or re.fullmatch(r'\d{4}', issuer['fiscal_year_end']) is None or _iso_date('2000-' + issuer['fiscal_year_end'][:2] + '-' + issuer['fiscal_year_end'][2:]) is None:
            raise ValueError('issuer_metadata_invalid')
        filings = body.get('filings')
        recent = filings.get('recent') if isinstance(filings, Mapping) else None
        if not isinstance(recent, Mapping) or any(not isinstance(recent.get(k), list) for k in _COLUMNS):
            raise ValueError('filing_metadata_schema_invalid')
        length = len(recent['form'])
        if not 0 <= length <= 2000 or any(len(recent[k]) != length for k in _COLUMNS):
            raise ValueError('filing_metadata_schema_invalid')
        observed = _utc_timestamp(ref['observed_at'])
        periods = dict(annual=[], quarterly=[])
        reports = []
        for i, form in enumerate(recent['form']):
            if not isinstance(form, str): raise ValueError('filing_form_invalid')
            kind = next((k for k, forms in _FORMS.items() if form in forms), None)
            if not kind and form not in {'8-K', '8-K/A', '6-K', '6-K/A'}:
                continue
            accession, document = recent['accessionNumber'][i], recent['primaryDocument'][i]
            report_date = recent['reportDate'][i]
            if not kind and report_date in ('', None): report_date = None
            anchor = dict(accession=accession, form=form, period_end=report_date, report_date=report_date,
                filed=recent['filingDate'][i], accepted_at=recent['acceptanceDateTime'][i], primary_document=document,
                source_url=f'https://www.sec.gov/Archives/edgar/data/{int(expected_cik)}/{accession.replace("-", "")}/{document}' if isinstance(accession, str) else None,
                amendment=form.endswith('/A'))
            if not _valid_anchor(anchor, expected_cik, observed, _FORMS[kind] if kind else {form}):
                raise ValueError('filing_metadata_invalid')
            target = periods[kind] if kind else reports
            if anchor not in target: target.append(anchor)
        for rows in (*periods.values(), reports): rows.sort(key=_sort)
        # Ambiguous versions remain in their own period; no accession tie-break.
        latest = {kind: _latest(rows) for kind, rows in periods.items()}
        triggers = [dict(trigger_type='newly_observed_filing', anchor=deepcopy(a)) for a in latest.values() if a]
        triggers += [dict(trigger_type='reported_earnings_filing' if _earnings_item(recent, a) else 'current_report_filing', anchor=deepcopy(a)) for a in reversed(reports)]
        packet = dict(schema_version=SCHEMA, status='inspection_only', reason=None, ticker=ticker, sec_cik=expected_cik,
            observed_at=ref['observed_at'], source_receipt=ref, source_receipts=[ref], issuer=issuer, latest=latest,
            periods=periods, earnings_reports=reports, review_triggers=triggers, rights_status=RIGHTS,
            commercial_eligible=False, saved_readiness_promoted=False)
        if len(_json(packet)) > MAX_NORMALIZED_BYTES: raise ValueError('filing_inventory_oversized')
        return _seal(packet)
    except (ValueError, TypeError, AttributeError, OverflowError, RecursionError):
        return _empty(ticker, expected_cik, 'filing_metadata_invalid')


def _earnings_item(recent, anchor):
    items = recent.get('items')
    if not isinstance(items, list) or len(items) != len(recent['form']):
        return False
    return any(recent['accessionNumber'][index] == anchor['accession'] and isinstance(value, str)
               and '2.02' in re.split(r'[,;\s]+', value) for index, value in enumerate(items))


def validated_filing_inventory(inventory, *, ticker, expected_cik, as_of=None, allow_historical=False):
    """Revalidate normalized cached metadata, including its exact source paths."""
    try:
        if (_mode_reason('research') or type(allow_historical) is not bool or not _identity(ticker, expected_cik)
                or not isinstance(inventory, Mapping) or inventory.get('schema_version') != SCHEMA
                or inventory.get('status') != 'inspection_only' or inventory.get('reason') is not None
                or inventory.get('ticker') != ticker or inventory.get('sec_cik') != expected_cik
                or inventory.get('rights_status') != RIGHTS or inventory.get('commercial_eligible') is not False
                or inventory.get('saved_readiness_promoted') is not False or len(_json(inventory)) > MAX_NORMALIZED_BYTES):
            return None
        if inventory.get('packet_digest') != _digest({k: v for k, v in inventory.items() if k != 'packet_digest'}): return None
        if inventory.get('normalized_sha256') != _digest(_normalized(inventory)): return None
        ref = _ref(inventory.get('source_receipt'), f'https://data.sec.gov/submissions/CIK{expected_cik}.json', _now(as_of), allow_historical)
        if not ref or inventory.get('source_receipts') != [ref] or inventory.get('observed_at') != ref['observed_at']: return None
        observed = _utc_timestamp(ref['observed_at'])
        issuer = inventory.get('issuer')
        if not isinstance(issuer, Mapping) or set(issuer) != {'name', 'sic', 'entity_type', 'fiscal_year_end'}: return None
        if any(issuer[k] is not None and not _safe_text(issuer[k]) for k in ('name', 'entity_type')): return None
        if issuer['sic'] is not None and (not isinstance(issuer['sic'], str) or re.fullmatch(r'\d{4}', issuer['sic']) is None or issuer['sic'] == '0000'): return None
        fye = issuer['fiscal_year_end']
        if fye is not None and (not isinstance(fye, str) or re.fullmatch(r'\d{4}', fye) is None or _iso_date('2000-'+fye[:2]+'-'+fye[2:]) is None): return None
        periods, latest = inventory.get('periods'), inventory.get('latest')
        if not isinstance(periods, Mapping) or set(periods) != set(_FORMS) or not isinstance(latest, Mapping) or set(latest) != set(_FORMS): return None
        anchors = []
        for kind, forms in _FORMS.items():
            rows = periods[kind]
            if not isinstance(rows, list) or len(rows) > 2000 or any(not _valid_anchor(r, expected_cik, observed, forms) for r in rows): return None
            if rows != sorted(rows, key=_sort) or len({_digest(r) for r in rows}) != len(rows) or latest[kind] != _latest(rows): return None
            for end in {r['period_end'] for r in rows}: _latest([r for r in rows if r['period_end'] == end])
            anchors.extend(rows)
        reports = inventory.get('earnings_reports')
        if not isinstance(reports, list) or len(reports) > 2000 or any(not _valid_anchor(r, expected_cik, observed, {'8-K', '8-K/A', '6-K', '6-K/A'}) for r in reports): return None
        if reports != sorted(reports, key=_sort) or len({_digest(r) for r in reports}) != len(reports): return None
        triggers = inventory.get('review_triggers')
        if not isinstance(triggers, list) or len(triggers) != len(reports) + sum(a is not None for a in latest.values()): return None
        for trigger in triggers:
            if (not isinstance(trigger, Mapping) or set(trigger) != {'trigger_type', 'anchor'}
                    or trigger.get('trigger_type') not in {'newly_observed_filing', 'reported_earnings_filing', 'current_report_filing'}
                    or trigger.get('anchor') not in [*latest.values(), *reports]): return None
        return deepcopy(dict(inventory))
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        return None


def _coverage_state(status, reason, anchor=None):
    return dict(status=status, reason=reason, anchor=deepcopy(anchor))


def corroborate_online_financials(financial, inventory, *, as_of=None):
    """Keep filing freshness separate from amounts; never rewrite history rows."""
    held = _coverage_state('withheld', 'filing_inventory_or_financial_identity_unavailable')
    result = dict(status='withheld', current={k: deepcopy(held) for k in _FORMS}, periods={k: {} for k in _FORMS}, gaps=[])
    if not isinstance(financial, Mapping): return result
    ticker = financial.get('ticker')
    identity = financial.get('companyfacts_identity')
    cik = identity.get('sec_cik') if isinstance(identity, Mapping) else None
    verified = validated_filing_inventory(inventory, ticker=ticker, expected_cik=cik, as_of=as_of)
    if (not verified or not financial_identity_valid(ticker, identity) or not _fresh(identity.get('observed_at'), _now(as_of))
            or financial.get('sec_cik', cik) != cik):
        result['gaps'].append(held['reason'])
        return result
    from src.online_history_contract import validated_annual_history
    from src.sec_quarterly_history import validated_quarterly_history
    from src.sec_foreign_financials import validated_foreign_financials
    from src.online_company_analysis import build_online_company_analysis
    histories = {'annual': [], 'quarterly': []}
    annual = validated_annual_history(financial)
    quarterly = validated_quarterly_history(financial)
    foreign = validated_foreign_financials(financial)
    if annual: histories['annual'].extend(annual['periods'])
    elif build_online_company_analysis(financial)['status'] == 'inspection_only':
        histories['annual'].append(dict(status='available', period_end=financial['period_end'], period_start=next(f['period_start'] for f in financial['approved_direct_fields'] if f['field']=='revenue'),
            accession=financial['accession'], form=financial['annual_form'], filed=financial['filing_date']))
    if quarterly: histories['quarterly'].extend(quarterly['periods'])
    if foreign:
        for kind in _FORMS: histories[kind].extend(foreign[kind])
    known = [a for rows in verified['periods'].values() for a in rows]
    def state(kind, end, anchor):
        rows = [r for r in histories[kind] if r.get('period_end') == end and r.get('status') == 'available']
        period_versions = [a for a in verified['periods'][kind] if a['period_end'] == end]
        if anchor is None and period_versions:
            return _coverage_state('withheld', 'ambiguous_filing_version')
        exact = [r for r in rows if anchor and all(r.get(k) == anchor[k] for k in ('accession', 'form', 'filed'))]
        if exact: return _coverage_state('corroborated', 'exact_reporting_period_and_filing', anchor)
        for row in rows:
            sources = [a for a in known if all(row.get(k) == a[k] for k in ('accession', 'form', 'filed'))]
            if len(sources) != 1: continue
            source = sources[0]
            source_kind = next(k for k, forms in _FORMS.items() if source['form'] in forms)
            versions = [a for a in verified['periods'][source_kind] if a['period_end'] == source['period_end']]
            # Later amendments to the comparative source invalidate that source,
            # independent of revisions of the older comparison period itself.
            if _latest(versions) != source: continue
            if source['period_end'] > end and (anchor is None or source['filed'] >= anchor['filed']):
                return _coverage_state('corroborated', 'comparative_fact_in_later_known_filing', anchor or source)
        if anchor is None:
            return _coverage_state('withheld', 'reporting_period_not_in_submissions')
        if anchor['amendment']:
            return _coverage_state('amendment_unresolved', 'amended_filing_structured_facts_unresolved', anchor)
        return _coverage_state('facts_pending', 'new_filing_structured_facts_pending', anchor)
    for kind in _FORMS:
        ends = {r['period_end'] for r in verified['periods'][kind]} | {r['period_end'] for r in histories[kind]}
        for end in sorted(ends):
            versions = [a for a in verified['periods'][kind] if a['period_end'] == end]
            result['periods'][kind][end] = state(kind, end, _latest(versions))
        latest = verified['latest'][kind]
        result['current'][kind] = result['periods'][kind][latest['period_end']] if latest else _coverage_state('withheld', 'ambiguous_filing_version' if verified['periods'][kind] else 'supported_filing_form_unavailable')
        if result['current'][kind]['status'] != 'corroborated':
            result['gaps'].append(kind + ':' + result['current'][kind]['reason'])
    result['status'] = 'corroborated' if all(s['status'] == 'corroborated' for s in result['current'].values()) else 'partial' if any(s['status'] == 'corroborated' for s in result['current'].values()) else 'withheld'
    return result


def build_online_earnings_components(facts_receipt, inventory, *, ticker, expected_cik, as_of=None):
    """Inspect exact annual standard concepts without approving new field scopes."""
    result = dict(schema_version=COMPONENT_SCHEMA, status='withheld', reason='annual_components_unavailable', ticker=ticker if isinstance(ticker, str) else None,
        sec_cik=expected_cik if isinstance(expected_cik, str) else None, annual_anchor=None, period_start=None, period_end=None, currency=None, fields={},
        withheld_fields={f: 'annual_source_unavailable' for f in _FIELDS}, source_receipts=[], rights_status=RIGHTS,
        commercial_eligible=False, saved_readiness_promoted=False)
    verified = validated_filing_inventory(inventory, ticker=ticker, expected_cik=expected_cik, as_of=as_of)
    ref = _ref(facts_receipt, f'https://data.sec.gov/api/xbrl/companyfacts/CIK{expected_cik}.json', _now(as_of))
    if not verified or not ref or facts_receipt.get('status') != 'ready': return result
    body = facts_receipt.get('payload')
    if not isinstance(body, Mapping) or _cik(body.get('cik')) != expected_cik or not isinstance(body.get('facts'), Mapping): return result
    anchor = verified['latest']['annual']
    if anchor is None: return result
    result.update(annual_anchor=anchor, period_end=anchor['period_end'], source_receipts=[ref, verified['source_receipt']])
    all_candidates = {}
    for name, catalog in _FIELDS.items():
        candidates = []
        malformed = False
        version_gap = False
        for taxonomy, concepts in catalog.items():
            tax = body['facts'].get(taxonomy, {})
            if not isinstance(tax, Mapping): malformed = True; continue
            for concept in concepts:
                fact = tax.get(concept)
                if fact is None: continue
                units = fact.get('units') if isinstance(fact, Mapping) else None
                if not isinstance(units, Mapping) or len(units) > 16: malformed = True; continue
                for unit, rows in units.items():
                    if not isinstance(unit, str) or not isinstance(rows, list) or len(rows) > 10000:
                        malformed = True; continue
                    for row in rows:
                        if not isinstance(row, Mapping): malformed = True; continue
                        if row.get('end') != anchor['period_end']: continue
                        if all(row.get(k) == anchor[v] for k, v in (('accn', 'accession'), ('form', 'form'), ('filed', 'filed'))):
                            candidates.append((taxonomy, concept, unit, row))
                        else:
                            start, filed = _iso_date(row.get('start')), _iso_date(row.get('filed'))
                            annual_duration = start is None or 300 <= (_iso_date(anchor['period_end']) - start).days <= 430
                            if annual_duration and (filed is None or filed >= _iso_date(anchor['filed'])):
                                version_gap = True
        all_candidates[name] = (candidates, malformed, version_gap)
    # A unique shared duration across distinct standard fields binds the annual
    # context; this does not infer a denominator or EPS split adjustment.
    starts = []
    for candidates, _, _ in all_candidates.values():
        compatible = {_r['start'] for _, _, _, _r in candidates if _iso_date(_r.get('start')) and 300 <= (_iso_date(anchor['period_end'])-_iso_date(_r['start'])).days <= 430}
        if len(compatible) == 1: starts.append(next(iter(compatible)))
    counts = Counter(starts)
    common_start = counts.most_common(1)[0][0] if counts and list(counts.values()).count(max(counts.values())) == 1 else None
    result['period_start'] = common_start
    currencies = set()
    for name, (candidates, malformed, version_gap) in all_candidates.items():
        reason = 'matching_current_annual_fact_unavailable'
        if malformed: reason = 'annual_concept_schema_invalid'
        elif version_gap: reason = 'newer_or_unresolved_annual_fact_version'
        elif candidates:
            concepts = {(tax, concept) for tax, concept, _, _ in candidates}
            units = {unit for _, _, unit, _ in candidates}
            unit = next(iter(units)) if len(units) == 1 else None
            valid_unit = isinstance(unit, str) and re.fullmatch(r'[A-Z]{3}/shares' if name == 'diluted_eps' else r'[A-Z]{3}', unit) is not None
            if len(concepts) != 1: reason = 'ambiguous_standard_concept'
            elif not valid_unit: reason = 'annual_unit_conflict'
            elif not common_start or any(row.get('start') != common_start for _, _, _, row in candidates): reason = 'incompatible_annual_duration'
            elif any(not _finite_direct_number(row.get('val')) for _, _, _, row in candidates) or len({row['val'] for _, _, _, row in candidates}) != 1: reason = 'annual_value_conflict'
            else:
                tax, concept, unit, row = candidates[0]
                currencies.add(unit.split('/')[0])
                result['fields'][name] = dict(field=name, taxonomy=tax, concept=concept, value=row['val'], unit=unit,
                    period_start=common_start, period_end=anchor['period_end'], accession=anchor['accession'], form=anchor['form'],
                    filed=anchor['filed'], source_ref=ref['source_url'], observed_at=ref['observed_at'], payload_sha256=ref['payload_sha256'], rights_status=RIGHTS)
                result['withheld_fields'].pop(name)
                continue
        result['withheld_fields'][name] = reason
    if len(currencies) > 1:
        # A component denominated in another currency cannot be joined to EPS.
        counts = Counter(f['unit'].split('/')[0] for f in result['fields'].values())
        selected = counts.most_common(1)[0][0] if list(counts.values()).count(max(counts.values())) == 1 else None
        for name, field in list(result['fields'].items()):
            if selected is None or field['unit'].split('/')[0] != selected:
                result['fields'].pop(name); result['withheld_fields'][name] = 'annual_currency_conflict'
        currencies = {f['unit'].split('/')[0] for f in result['fields'].values()}
    result['currency'] = next(iter(currencies)) if len(currencies) == 1 else None
    if result['fields']: result.update(status='inspection_only', reason=None)
    return result
