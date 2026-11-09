"""Observed online research adapters; no canonical approvals or saved readiness.

Every calculation is local. Source collection remains an explicit action owned by
the caller. Annual, direct-quarter and cumulative observations keep their scopes.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass, replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import re

from src.company_sec_online_preview import _iso_date, _utc_timestamp
from src.catalyst_evidence_timeline import CatalystEvent, preview_event
from src.company_research_notes import CompanyNotes
from src.decision_process_scorecard import build_decision_process_scorecard
from src.online_company_identity import financial_identity_valid, validated_price_filing_association
from src.online_history_contract import validated_annual_history
from src.online_peer_valuation import build_online_peer_valuation
from src.online_research_history_view import validated_online_price_history
from src.research_decision_lab import build_research_decision_lab_state
from src.research_outcome_review import ResearchOutcome, derive_outcome_status, preview_outcome
from src.research_thesis_journal import JournalEntry, derive_journal_state, validate_journal_entry
from src.scenario_lab import ScenarioParameters, validate_scenario_parameters
from src.sec_foreign_financials import validated_foreign_financials
from src.sec_quarterly_history import validated_quarterly_history
from src.valuation import DCFAssumptions, ValuationInput, calculate_dcf

SCHEMA = 'online-company-research-v1'
SCENARIO_SCHEMA = 'online-hypothetical-scenario-v1'
BOUNDARY = ('Personal research observations and hypothetical assumptions only. '
            'No saved readiness, approved research, company grade or investment action is produced.')
_NUMBER_LIMIT = 1e20
_RAW_KEYS = {'payload', 'raw', 'body', 'raw_body', 'raw_payload', 'raw_response', 'response_body',
             'archive', 'archives', 'raw_archive', 'archive_body', 'html', 'xml', 'bytes', 'base64', 'collection'}
_METADATA = {'observed_at', 'observed_at_utc', 'retrieved_at_utc', 'retrieved_at',
             'attempted_at', 'payload_sha256', 'association_payload_sha256',
             'association_observed_at', 'source_last_modified', 'raw_sha256',
             'normalized_sha256', 'inventory_sha256', 'packet_digest', 'digest', 'sha256'}


def _finite(value):
    try:
        return type(value) in {int, float} and math.isfinite(value) and abs(value) <= _NUMBER_LIMIT
    except (OverflowError, ValueError):
        return False


def _json(value, depth=0):
    """Copy bounded normalized structures; never accept raw source payloads."""
    if depth > 18:
        return None
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, Mapping):
        return {str(k): _json(v, depth+1) for k, v in list(value.items())[:400]
                if str(k).casefold() not in _RAW_KEYS}
    if isinstance(value, (list, tuple)):
        return [_json(v, depth+1) for v in value[:2000]]
    if isinstance(value, str):
        return value[:16000]
    if value is None or type(value) is bool:
        return value
    if _finite(value):
        return value
    return None


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _semantic(value):
    if isinstance(value, Mapping):
        return {k: _semantic(v) for k, v in value.items()
                if k not in _METADATA and not k.endswith('_sha256') and not k.endswith('_observed_at')}
    if isinstance(value, list):
        return [_semantic(v) for v in value]
    return value


def _metadata_projection(value):
    """Observe receipt changes independently from economic/filing revisions."""
    if isinstance(value, Mapping):
        result = {}
        for key, child in value.items():
            if key in _METADATA or key.endswith('_sha256') or key.endswith('_observed_at'):
                result[key] = child
            elif isinstance(child, (Mapping, list)):
                nested = _metadata_projection(child)
                if nested:
                    result[key] = nested
        return result
    if isinstance(value, list):
        return [_metadata_projection(child) for child in value]
    return None


def _now(as_of):
    result = _utc_timestamp(as_of) if isinstance(as_of, str) else as_of
    if result is None:
        result = datetime.now(timezone.utc)
    if not isinstance(result, datetime) or result.utcoffset() is None:
        raise ValueError('as_of must include a timezone')
    return result.astimezone(timezone.utc)


def _fresh(timestamp, now):
    observed = _utc_timestamp(timestamp)
    return observed is not None and timedelta(0) <= now-observed <= timedelta(hours=24)


def _fields(row):
    value = row.get('fields', {})
    fields = {f['field']: dict(f) for f in value} if isinstance(value, list) else {key:dict(f) for key,f in value.items()}
    # Annual direct fields bind accession and dates through the validated row;
    # carry that real filing metadata into derived source references as well.
    for field in fields.values():
        for key in ('form', 'filed'):
            if field.get(key) is None:
                field[key] = row.get(key)
    return fields


def _ref(field):
    return {k: field.get(k) for k in ('source_ref', 'taxonomy', 'concept', 'unit',
        'period_start', 'period_end', 'filed', 'accession', 'form')}


def _same_period(*fields):
    return bool(fields) and all(fields) and all(
        len({f.get(key) for f in fields}) == 1
        for key in ('period_start', 'period_end', 'unit', 'accession', 'form'))


def _definition(*fields):
    return bool(fields) and all(fields) and len({(f.get('taxonomy'), f.get('concept'), f.get('unit')) for f in fields}) == 1


def _compatible(previous, current, kind, *, sequential=False):
    if previous.get('status') != 'available' or current.get('status') != 'available':
        return False
    ps, pe, cs, ce = (_iso_date(v) for v in (previous['period_start'], previous['period_end'],
                                            current['period_start'], current['period_end']))
    if None in (ps, pe, cs, ce):
        return False
    if previous['currency'] != current['currency'] or abs((pe-ps).days-(ce-cs).days) > 14:
        return False
    if sequential or kind == 'annual':
        return (cs-pe).days == 1 and ((70 <= (ce-pe).days <= 110) if kind == 'quarterly' else (300 <= (ce-pe).days <= 430))
    return 350 <= (ce-pe).days <= 380 and 350 <= (cs-ps).days <= 380


def _metric(key, label, period, fields, value=None, reason=None, *, unit='ratio', prior=None, basis=None):
    return dict(key=key, label=label, status='calculated' if value is not None else 'withheld',
        value=value, unit=unit, period_kind=period['kind'], period_start=period['period_start'],
        period_end=period['period_end'], from_period_end=prior.get('period_end') if prior else None,
        source_refs=[_ref(f) for f in fields if f], reason=reason,
        basis=basis or 'Personal derived observation; latest reported as observed, not point-in-time history')


def _cash_metric(period, fields):
    cfo, ppe = fields.get('cash_from_operations'), fields.get('capital_expenditures')
    reason = 'matching_total_cfo_and_positive_ppe_spending_required'
    value = None
    if (_same_period(cfo, ppe) and cfo['unit'] == period['currency'] and ppe['value'] > 0
        and 'ContinuingOperations' not in cfo['concept']
        and ppe.get('concept') in {'PaymentsToAcquirePropertyPlantAndEquipment', 'PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities'}):
        value, reason = cfo['value']-ppe['value'], None
    return _metric('cfo_less_ppe', 'Operating cash flow less PP&E spending', period, [cfo, ppe],
        value, reason, unit=period['currency'],
        basis='Total reported CFO less positive PP&E spending; not issuer-defined FCF and not FCFF for DCF')


def _trend(histories, coverage):
    periods, metrics, gaps = [], [], []
    for kind, history_rows, currency in histories:
        rows = []
        for source in history_rows:
            period = {k: source.get(k) for k in ('period_start', 'period_end', 'filed', 'accession', 'form', 'status', 'reason')}
            state = coverage.get('periods', {}).get(kind, {}).get(source['period_end'], {})
            period.update(kind=kind, currency=currency, fields=_fields(source),
                cumulative_fields=_json(source.get('cumulative_fields', {})),
                filing_status=state.get('status', 'unverified'), current=False)
            if kind == 'interim' and not state:
                period.update(status='withheld',reason='interim_filing_source_unverified')
            current = coverage.get('current', {}).get(kind, {})
            anchor = current.get('anchor') or {}
            period['current'] = (current.get('status') == 'corroborated'
                and state.get('status') == 'corroborated'
                and anchor.get('period_end', anchor.get('report_date')) == period['period_end'])
            if state.get('status') in {'facts_pending', 'amendment_unresolved', 'withheld'}:
                period.update(status='withheld', reason=state.get('reason') or state['status'])
            rows.append(period); periods.append(period)
        for index, period in enumerate(rows):
            fields = period['fields'] if period['status'] == 'available' else {}
            revenue, income = fields.get('revenue'), fields.get('operating_income')
            margin = income['value']/revenue['value'] if _same_period(income, revenue) and revenue['value'] > 0 else None
            metrics.append(_metric('operating_margin', 'Operating margin', period, [revenue, income], margin,
                None if margin is not None else 'matching_revenue_and_operating_income_required'))
            metrics.append(_cash_metric(period, fields))
            if period['cumulative_fields'] and period['status'] == 'available':
                cf = period['cumulative_fields']; first = next(iter(cf.values()))
                cumulative = {**period, 'kind':'cumulative', 'period_start':first['period_start']}
                metrics.append(_cash_metric(cumulative, cf))
            if kind not in {'annual', 'quarterly'}:
                continue
            for key, sequential in [('revenue_yoy', False)] + ([('revenue_qoq', True)] if kind == 'quarterly' else []):
                prior = rows[index-1] if index else None
                if kind == 'quarterly' and not sequential:
                    prior = next((p for p in reversed(rows[:index]) if _compatible(p, period, kind)), None)
                pr = prior['fields'].get('revenue') if prior else None
                good = bool(prior and _compatible(prior, period, kind, sequential=sequential) and _definition(pr, revenue) and pr['value'] > 0)
                metrics.append(_metric(key, 'Revenue sequential growth' if sequential else 'Revenue year-over-year growth', period,
                    [pr, revenue], revenue['value']/pr['value']-1 if good else None,
                    None if good else 'compatible_periods_and_revenue_definition_required', prior=prior))
            prior = rows[index-1] if index else None
            pr = prior['fields'].get('revenue') if prior else None
            pi = prior['fields'].get('operating_income') if prior else None
            good = (prior and _compatible(prior, period, kind, sequential=(kind=='quarterly'))
                and margin is not None and _same_period(pr, pi) and pr['value'] > 0
                and _definition(pr, revenue) and _definition(pi, income))
            metrics.append(_metric('operating_margin_change_pp', 'Operating margin change', period,
                [pr, pi, revenue, income], (margin-pi['value']/pr['value'])*100 if good else None,
                None if good else 'compatible_operating_income_definitions_and_periods_required',
                unit='percentage_points', prior=prior))
    if not periods:
        gaps.append('Validated financial history is unavailable; refresh source observations explicitly.')
    gaps.append('Reported EPS is not automatically comparable across stock splits; no EPS growth is inferred.')
    return dict(status='inspection_only' if periods else 'withheld', periods=periods, metrics=metrics,
        narrative=['Exact reported dates separate annual, direct-quarter and cumulative flows.',
                   'Derived observations do not promote saved readiness or source rights.'], gaps=gaps)


def _receipt_rows(financial, prices, inventory, peers):
    rows = []
    def add(source, name):
        if not isinstance(source, Mapping):
            return
        row = {k: source[k] for k in ('status', 'reason', 'source_url', 'source_ref', 'observed_at',
            'observed_at_utc', 'retrieved_at_utc', 'payload_sha256', 'source_last_modified', 'normalized_sha256') if k in source}
        row['source'] = name
        if row not in rows:
            rows.append(row)
    add(financial, 'annual_financials'); add(financial.get('companyfacts_identity'), 'companyfacts_identity')
    add(prices, 'daily_prices'); add(inventory, 'filing_inventory')
    for row in inventory.get('source_receipts', []):
        add(row, 'filing_receipt')
    for row in (peers.get('subject') or {}, *peers.get('peers', [])):
        add(row, 'annual_pe_industry_reference')
    return _json(rows)


def _peer_context(peers, *, ticker, cik, now, coverage, prices):
    if peers is None:
        from src.online_peer_valuation import _empty
        result = {**_empty(ticker,'online_peer_update_not_requested'),'status':'not_requested'}
    elif isinstance(peers,Mapping) and 'packet_digest' in peers:
        from src.online_peer_sources import _read
        result = _read(peers,ticker,cik,now)
    else:
        collection = peers.get('collection', peers) if isinstance(peers, Mapping) else None
        result = build_online_peer_valuation(collection, ticker=ticker, expected_cik=cik, as_of=now)
    # Keep normalized accepted/excluded observations, never their source archives.
    result = _json(result)
    result['relationship'] = 'observed_industry_references_not_trusted_economic_peers'
    current = coverage.get('current', {}).get('annual', {})
    subject = result.get('subject') or {}
    reason = None
    if subject:
        if current.get('status') != 'corroborated':
            reason = 'latest_annual_filing_not_corroborated'
        elif (current.get('anchor') or {}).get('period_end', (current.get('anchor') or {}).get('report_date')) != subject.get('period_end'):
            reason = 'peer_subject_annual_period_differs_from_current_financials'
        elif any((current.get('anchor') or {}).get(key) != subject.get(key) for key in ('accession', 'form', 'filed')):
            reason = 'peer_subject_filing_version_differs_from_current_financials'
        elif prices.get('status') != 'inspection_only' or prices.get('last_price_date') != subject.get('price_date'):
            reason = 'peer_subject_price_date_differs_from_current_prices'
        elif not math.isclose(prices.get('close'),subject.get('price'),rel_tol=1e-7,abs_tol=1e-6):
            reason = 'peer_subject_price_differs_from_current_prices'
    if reason:
        result.update(status='withheld', reason=reason, peer_median=None, premium_fraction=None)
    return result


def _notes_context(notes, *, ticker, cik, profile_key, now):
    normalized = None
    try:
        if notes is not None:
            raw = asdict(notes) if isinstance(notes, CompanyNotes) else notes
            if not isinstance(raw, Mapping) or raw.get('scope') != dict(profile_key=profile_key, ticker=ticker, sec_cik=cik):
                raise ValueError('note_scope_mismatch')
            journal = tuple(r if isinstance(r, JournalEntry) else JournalEntry(**r) for r in raw.get('journal', ()))
            outcomes = tuple(r if isinstance(r, ResearchOutcome) else ResearchOutcome(**r) for r in raw.get('outcomes', ()))
            catalysts = tuple(r if isinstance(r, CatalystEvent) else CatalystEvent(**r) for r in raw.get('catalysts', ()))
            checked = []
            for row in journal:
                if row.profile_key != profile_key or row.ticker != ticker or _utc_timestamp(row.recorded_at) > now:
                    raise ValueError('note_identity_or_time_mismatch')
                validate_journal_entry(row, existing_entries=checked); checked.append(row)
            checked = []
            for row in outcomes:
                if row.profile_key != profile_key or row.ticker != ticker or _utc_timestamp(row.reviewed_at) > now:
                    raise ValueError('outcome_identity_or_time_mismatch')
                if preview_outcome(row, existing=checked).state != 'reviewable':
                    raise ValueError('invalid_outcome_record')
                checked.append(row)
            checked = []
            for row in catalysts:
                if row.profile_key != profile_key or row.ticker != ticker or _utc_timestamp(row.retrieved_at) > now:
                    raise ValueError('catalyst_identity_or_time_mismatch')
                if preview_event(row, existing=checked).state == 'rejected':
                    raise ValueError('invalid_catalyst_record')
                checked.append(row)
            normalized = _json(raw)
        else:
            journal, outcomes = (), ()
        state = derive_journal_state(journal, profile_key=profile_key, ticker=ticker, as_of=now.isoformat())
        scorecard = build_decision_process_scorecard({'ticker':ticker}, profile_key=profile_key,
            journal_state=state, review_items=())
        outcome = derive_outcome_status(outcomes, profile_key=profile_key, ticker=ticker)
        decision = asdict(build_research_decision_lab_state(profile_key=profile_key,
            journal_state=state, scorecard=scorecard, outcome_status=outcome))
        # The saved DCF lane stays blocked. Online assumptions have a separate lane
        # because documenting them never constitutes saved valuation readiness.
        decision['saved_readiness_promoted'] = False
        summary = dict(status='inspection_only', current_thesis=state.current_thesis.summary if state.current_thesis else None,
            journal_count=len(journal), outcome_count=len(outcomes), review_due_date=state.review_due_date or None,
            contrary_evidence=[r.summary for r in state.conflicting_evidence],
            invalidation_conditions=[r.summary for r in state.invalidation_conditions])
        return normalized, summary, _json(decision)
    except (TypeError, ValueError, KeyError, AttributeError):
        return None, dict(status='withheld', reason='issuer_scoped_notes_invalid', current_thesis=None), dict(
            status='unavailable', reason='issuer_scoped_notes_invalid', lanes=[],
            next_process_step='Verify saved issuer-scoped notes before using Decision Lab.', saved_readiness_promoted=False)


def _validated_earnings_components(value, *, ticker, cik, inventory, identity, now):
    """Revalidate the separate personal-inspection component display boundary.

    The producer owns concept selection; this checks its normalized result still
    belongs to the current source receipts and annual version before display.
    """
    from src.online_filing_context import COMPONENT_SCHEMA, RIGHTS, _FIELDS
    held = dict(schema_version=COMPONENT_SCHEMA, status='withheld',
        reason='current_annual_earnings_components_unverified', ticker=ticker, sec_cik=cik,
        fields={}, withheld_fields={name:'current_component_context_unverified' for name in _FIELDS},
        rights_status=RIGHTS, saved_readiness_promoted=False, commercial_eligible=False)
    try:
        if (not isinstance(value, Mapping) or value.get('schema_version') != COMPONENT_SCHEMA
            or value.get('status') not in {'inspection_only', 'withheld'} or value.get('ticker') != ticker
            or value.get('sec_cik') != cik or value.get('rights_status') != RIGHTS
            or value.get('saved_readiness_promoted') is not False or value.get('commercial_eligible') is not False
            or inventory.get('status') != 'inspection_only' or not financial_identity_valid(ticker, identity)):
            return held
        anchor = inventory.get('latest', {}).get('annual')
        receipts = value.get('source_receipts')
        if (not anchor or value.get('annual_anchor') != anchor or value.get('period_end') != anchor['period_end']
            or not isinstance(receipts, list) or len(receipts) != 2 or receipts[1] != inventory.get('source_receipt')):
            return held
        source = receipts[0]
        if (not isinstance(source, Mapping) or source.get('source_url') != identity.get('source_url')
            or source.get('payload_sha256') != identity.get('payload_sha256')
            or source.get('observed_at') != identity.get('observed_at')
            or not _fresh(source.get('observed_at'), now) or not _fresh(receipts[1].get('observed_at'), now)):
            return held
        fields, withheld = value.get('fields'), value.get('withheld_fields')
        if (not isinstance(fields, Mapping) or not isinstance(withheld, Mapping)
            or set(fields) | set(withheld) != set(_FIELDS) or set(fields) & set(withheld)
            or any(not isinstance(reason, str) or not re.fullmatch(r'[a-z_]{1,100}', reason) for reason in withheld.values())):
            return held
        if not fields:
            return _json(value) if value.get('status') == 'withheld' else held
        start, end = _iso_date(value.get('period_start')), _iso_date(value.get('period_end'))
        currency = value.get('currency')
        if (value.get('status') != 'inspection_only' or value.get('reason') is not None
            or not start or not end or not 300 <= (end-start).days <= 430
            or not isinstance(currency, str) or not re.fullmatch('[A-Z]{3}', currency)):
            return held
        for name, field in fields.items():
            if (not isinstance(field, Mapping) or field.get('field') != name or not _finite(field.get('value'))
                or field.get('concept') not in _FIELDS[name].get(field.get('taxonomy'), ())
                or field.get('unit') != currency + ('/shares' if name == 'diluted_eps' else '')
                or field.get('period_start') != value['period_start'] or field.get('period_end') != value['period_end']
                or any(field.get(key) != anchor[key] for key in ('accession', 'form', 'filed'))
                or field.get('source_ref') != source['source_url'] or field.get('observed_at') != source['observed_at']
                or field.get('payload_sha256') != source['payload_sha256'] or field.get('rights_status') != RIGHTS):
                return held
        return _json(value)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        return held


def build_online_research_context(financial, prices, peers=None, association=None, *, ticker,
    profile_key, expected_cik=None, notes=None, scenario=None, as_of=None):
    """Build one JSON-safe normalized context from independently validated sources."""
    now = _now(as_of)
    financial = financial if isinstance(financial, Mapping) else {}
    prices = prices if isinstance(prices, Mapping) else {}
    identity = financial.get('companyfacts_identity', {})
    identity_valid = financial_identity_valid(ticker, identity) and financial.get('ticker') == ticker
    cik = identity.get('sec_cik') if identity_valid else expected_cik
    identity_valid = identity_valid and (expected_cik is None or cik == expected_cik) and financial.get('sec_cik', cik) == cik
    gaps, histories = [], []
    annual = quarterly = foreign = None
    if identity_valid and _fresh(identity.get('observed_at'), now):
        annual = validated_annual_history(financial) if financial.get('status') == 'inspection_only' else None
        quarterly = validated_quarterly_history(financial)
        foreign = validated_foreign_financials(financial)
        if annual and _fresh(annual.get('observed_at'), now):
            histories.append(('annual', annual['periods'], annual['unit']))
        else:
            annual = None
        if quarterly:
            histories.append(('quarterly', quarterly['periods'], quarterly['unit']))
        if foreign:
            for kind in ('annual', 'quarterly', 'interim'):
                if foreign[kind] and foreign['unit'] != 'USD':
                    histories = [h for h in histories if h[0] != kind]
                    histories.append((kind, foreign[kind], foreign['unit']))
                elif foreign[kind] and not any(h[0] == kind for h in histories):
                    histories.append((kind, foreign[kind], foreign['unit']))
    else:
        gaps.append('Current financial source identity is unavailable, stale or mismatched.')
    from src.online_filing_context import validated_filing_inventory, corroborate_online_financials
    inventory = validated_filing_inventory(financial.get('filing_inventory'), ticker=ticker, expected_cik=cik, as_of=now) if cik else None
    inventory = inventory or dict(status='withheld', reason='filing_inventory_unavailable', latest={}, periods={}, issuer={})
    coverage = dict(status='withheld', current={}, periods={}, gaps=['Current filing inventory is unavailable.'])
    if inventory.get('status') == 'inspection_only':
        try:
            coverage = corroborate_online_financials(financial, inventory, as_of=now)
        except (TypeError, ValueError, KeyError, AttributeError, OverflowError):
            coverage = dict(status='withheld', current={}, periods={}, gaps=['Financial filing coverage could not be verified.'])
    from src.sec_online_quarter_evidence import validated_archive_quarter
    from src.sec_online_quarter_view import merge_archive_quarter
    archive = validated_archive_quarter(financial, ticker=ticker, expected_cik=cik, inventory=inventory, as_of=now) if identity_valid else None
    if archive:
        rows = next((rows for kind, rows, _ in histories if kind == 'quarterly'), [])
        histories = [history for history in histories if history[0] != 'quarterly']
        histories.append(('quarterly', merge_archive_quarter(rows, archive), archive['unit']))
    trend = _trend(histories, coverage)
    base = dict(status='withheld', reason='validated_current_annual_revenue_required', revenue=None,
        currency=None, period_start=None, period_end=None, source_refs=[])
    current = coverage.get('current', {}).get('annual', {})
    annual_rows = [p for p in trend['periods'] if p['kind']=='annual']
    latest = annual_rows[-1] if annual_rows else None
    if latest and latest['status']=='available' and current.get('status')=='corroborated' and latest['current']:
        revenue = latest['fields'].get('revenue')
        if revenue and _finite(revenue['value']) and revenue['value']>0:
            base.update(status='available', reason=None, revenue=revenue['value'], currency=revenue['unit'],
                period_start=latest['period_start'], period_end=latest['period_end'], source_refs=[_ref(revenue)])
    issuer = inventory.get('issuer', {})
    sic, entity_type = issuer.get('sic'), issuer.get('entity_type')
    if str(sic or '').startswith('6'):
        base.update(status='excluded', reason='financial_sector_operating_company_dcf_excluded', revenue=None)
    elif entity_type not in {'operating', 'operating_company'} or not isinstance(sic, str) or not re.fullmatch(r'\d{4}', sic):
        base.update(status='withheld', reason='operating_company_classification_required', revenue=None)
    price_history = validated_online_price_history(prices, ticker=ticker)
    price = dict(status='withheld', reason=prices.get('reason') or 'validated_price_observation_unavailable')
    if price_history and _fresh(price_history.get('observed_at'), now):
        price = {k: price_history.get(k) for k in ('ticker', 'provider_symbol', 'source_url', 'observed_at',
            'payload_sha256', 'currency', 'last_price_date')}
        price.update(status='inspection_only', close=price_history['bars'][-1]['close'])
    peer = _peer_context(peers, ticker=ticker, cik=cik, now=now, coverage=coverage, prices=price)
    notes_value, notes_summary, decision = _notes_context(notes, ticker=ticker, cik=cik, profile_key=profile_key, now=now)
    earnings = _validated_earnings_components(financial.get('earnings_components'), ticker=ticker,
        cik=cik, inventory=inventory, identity=identity if identity_valid else {}, now=now)
    link = validated_price_filing_association(association)
    receipts = _receipt_rows(financial, prices, inventory, peer)
    if archive:
        receipts.extend(dict(row, source='exact_quarter_receipt', rights_status=archive['rights_status']) for row in archive['source_receipts'])
    semantic_inputs = dict(ticker=ticker, sec_cik=cik, financial_identity_valid=identity_valid,
        financial_status=financial.get('status'), financial_reason=financial.get('reason'),
        filing_inventory=inventory, filing_coverage=coverage, earnings_components=earnings,
        business_trend=trend, price_context=price, peer_read_through=peer,
        listing_association=link)
    revision = _digest(_semantic(_json(semantic_inputs)))
    metadata_revision = _digest(dict(receipts=receipts, metadata=_metadata_projection(_json(semantic_inputs))))
    valid_scenario = (isinstance(scenario, Mapping) and scenario.get('status')=='calculated'
        and scenario.get('schema_version')==SCENARIO_SCHEMA and scenario.get('source_revision')==revision
        and scenario.get('ticker')==ticker and scenario.get('sec_cik')==cik and scenario.get('profile_key')==profile_key)
    scenario_value = _json(scenario) if valid_scenario else None
    if scenario is not None and not valid_scenario:
        gaps.append('Scenario results need rerunning for this company and source revision; retain draft assumptions separately.')
    assumptions = scenario_value.get('assumptions') if scenario_value else None
    decision['hypothetical_assumptions'] = dict(status='documented' if assumptions else 'not_started',
        assumptions=assumptions, boundary='Documented hypothetical assumptions do not establish saved DCF eligibility.')
    contrary = notes_summary.get('contrary_evidence', [])
    decision['contrary_evidence'] = dict(status='documented' if contrary else 'not_started',
        records=contrary, next_step='Review the recorded contrary evidence.' if contrary else
        'Research and record contrary evidence; observed trends do not automatically supply it.')
    if not contrary and decision.get('status') == 'process_documented':
        decision.update(status='process_work_needed', next_process_step=decision['contrary_evidence']['next_step'])
    for lane in decision.get('lanes', []):
        if lane['key'] == 'scenario':
            lane.update(state='hypothetical_documented' if assumptions else 'not_started',
                answer='Explicit hypothetical scenario assumptions are documented' if assumptions else 'No hypothetical scenario assumptions are documented',
                evidence='Online assumptions are separate from saved DCF eligibility; saved readiness is not promoted.',
                next_step='Review assumptions and sensitivity against your hypothesis.' if assumptions else 'Run Scenario Lab with explicit hypothetical assumptions when the revenue base is available.')
    forward = dict(status='research_context', user_hypothesis=notes_summary.get('current_thesis'),
        contrary_evidence=contrary, invalidation_conditions=notes_summary.get('invalidation_conditions', []),
        user_catalysts=notes_value.get('catalysts', []) if notes_value else [],
        observed_trends=[m for m in trend['metrics'] if m['status']=='calculated'][-12:],
        industry_references=dict(status=peer['status'], reason=peer['reason'], accepted_count=peer.get('peer_count', 0)),
        assumptions=assumptions, review_triggers=_json(inventory.get('review_triggers', inventory.get('earnings_reports', []))),
        gaps=list(gaps), boundary='Observed filings are research review triggers; no guidance, consensus or earnings probability is invented.')
    if base.get('reason'):
        gaps.append(base['reason'])
    if peer.get('status') != 'research_comparison':
        gaps.append(peer.get('reason') or 'Observed industry references are unavailable.')
    observation_times = []
    for source in (identity if identity_valid else {}, annual or {}, quarterly or {}, foreign or {}, archive or {}, inventory, price):
        stamp = source.get('observed_at')
        if _fresh(stamp, now):
            observation_times.append(_utc_timestamp(stamp))
    observed_at = max(observation_times).isoformat() if observation_times else now.isoformat()
    forward['gaps'] = list(gaps)
    return _json(dict(schema_version=SCHEMA, ticker=ticker, sec_cik=cik, profile_key=profile_key,
        status='inspection_only' if histories else 'withheld', observed_at=observed_at,
        source_revision=revision, source_metadata_revision=metadata_revision, source_receipts=receipts,
        filing_inventory=inventory, filing_coverage=coverage, earnings_components=earnings,
        business_trend=trend, scenario_base=base, price_context=price, peer_read_through=peer,
        forward_view=forward, decision_lab=decision, notes_summary=notes_summary, notes=notes_value,
        scenario=scenario_value, assumptions=assumptions,
        gaps=gaps+list(coverage.get('gaps', []))+trend['gaps'],
        saved_readiness_promoted=False, commercial_eligible=False, boundary=BOUNDARY))


def run_online_scenario(context, parameters, *, assumed_net_debt=None, assumed_shares=None, capital_structure_basis=None):
    """Calculate enterprise-value assumptions over a validated annual revenue base."""
    context = context if isinstance(context, Mapping) else {}
    result = dict(schema_version=SCENARIO_SCHEMA, status='withheld', reason='validated_annual_context_required',
        ticker=context.get('ticker'), sec_cik=context.get('sec_cik'), profile_key=context.get('profile_key'),
        source_revision=context.get('source_revision'), input_identity=None, currency=None,
        enterprise_value=None, equity_value=None, value_per_assumed_share=None, fair_value_per_share=None,
        projected_fcfs=[], discounted_fcfs=[], sensitivity=None, assumptions=None,
        market_price_comparison=None, gaps=[], saved_readiness_promoted=False, commercial_eligible=False,
        boundary='Hypothetical FCFF-margin enterprise-value math; capital structure and share counts are user assumptions, not reported facts.')
    base = context.get('scenario_base', {})
    if (context.get('schema_version') != SCHEMA or context.get('status') != 'inspection_only'
        or context.get('saved_readiness_promoted') is not False or context.get('commercial_eligible') is not False
        or not isinstance(base, Mapping) or base.get('status') != 'available'
        or not _finite(base.get('revenue')) or base['revenue'] <= 0):
        result.update(status='excluded' if base.get('status')=='excluded' else 'withheld', reason=base.get('reason') or result['reason'])
        return result
    result['currency'] = base.get('currency')
    try:
        parameters = parameters if isinstance(parameters, ScenarioParameters) else ScenarioParameters(**parameters)
        if any(not _finite(getattr(parameters, name)) for name in ('revenue_growth', 'fcf_margin', 'wacc', 'terminal_growth')) or type(parameters.forecast_years) is not int:
            raise ValueError('Assumptions must be finite numbers and forecast years a whole number.')
        validate_scenario_parameters(parameters)
        if assumed_net_debt is not None and not _finite(assumed_net_debt):
            raise ValueError('Assumed net debt must be finite.')
        if assumed_shares is not None and (not _finite(assumed_shares) or assumed_shares <= 0):
            raise ValueError('Assumed shares must be positive and finite.')
    except (TypeError, ValueError, AttributeError, OverflowError) as error:
        result.update(status='invalid', reason=str(error)); return result
    basis_valid = bool(isinstance(capital_structure_basis, str) and capital_structure_basis.strip())
    if isinstance(capital_structure_basis, Mapping):
        basis_valid = (capital_structure_basis.get('currency') == base['currency']
            and capital_structure_basis.get('share_basis') == 'assumed_common_shares'
            and bool(str(capital_structure_basis.get('label') or '').strip()))
    net_debt = assumed_net_debt if basis_valid else None
    shares = assumed_shares if basis_valid else None
    source = ValuationInput(ticker=context['ticker'], revenue=base['revenue'], free_cash_flow=None,
        source_metadata=[dict(source='online_annual_revenue_observation', **r) for r in base['source_refs']])
    assumptions = DCFAssumptions(method_name='revenue_hypothetical_fcff_margin',
        revenue_growth=parameters.revenue_growth, fcf_margin=parameters.fcf_margin, operating_margin=None,
        # The revenue/FCFF-margin kernel does not use a separate tax rate.
        # Keep it absent rather than manufacturing a zero-tax observation.
        tax_rate=None, wacc=parameters.wacc, terminal_growth=parameters.terminal_growth,
        forecast_years=parameters.forecast_years, base_revenue=base['revenue'], base_free_cash_flow=None,
        net_debt=net_debt, shares_outstanding=shares,
        observed_revenue_growth=parameters.revenue_growth, observed_fcf_margin=parameters.fcf_margin,
        normalized_growth_target=parameters.revenue_growth, max_projected_fcf_growth=None)
    calculated = calculate_dcf(source, assumptions)
    if calculated.status != 'calculated' or not _finite(calculated.enterprise_value):
        result.update(status='invalid', reason='hypothetical_scenario_did_not_calculate'); return result
    explicit = dict(asdict(parameters), basis='user_hypothetical', cash_flow_basis='assumed_unlevered_FCFF_margin',
        assumed_net_debt=assumed_net_debt, assumed_shares=assumed_shares,
        capital_structure_basis=_json(capital_structure_basis), source_revenue=base['revenue'],
        source_period_start=base['period_start'], source_period_end=base['period_end'],
        growth_path=calculated.assumptions['applied_growth_by_year'],
        kernel_normalization_warnings=calculated.warnings)
    waccs = sorted({max(.05, parameters.wacc-.01), parameters.wacc, min(.2, parameters.wacc+.01)})
    terminal = sorted({max(-.02, parameters.terminal_growth-.01), parameters.terminal_growth, min(.05, parameters.terminal_growth+.01)})
    grid, share_grid = [], []
    for wacc in waccs:
        ev_row, share_row = [], []
        for growth in terminal:
            value = calculate_dcf(source, replace(assumptions, wacc=wacc, terminal_growth=growth)) if growth<wacc else None
            ev_row.append(value.enterprise_value if value and value.status=='calculated' else None)
            share_row.append(value.fair_value_per_share if value and value.status=='calculated' else None)
        grid.append(ev_row); share_grid.append(share_row)
    gaps = []
    if net_debt is None:
        gaps.append('Explicit net debt and a compatible capital-structure basis are required for equity value.')
    if shares is None:
        gaps.append('Explicit assumed shares and a compatible basis are required for value per assumed share.')
    result.update(status='calculated', reason='hypothetical_assumptions_applied_to_observed_annual_revenue',
        enterprise_value=calculated.enterprise_value, equity_value=calculated.equity_value,
        value_per_assumed_share=calculated.fair_value_per_share, fair_value_per_share=calculated.fair_value_per_share,
        projected_fcfs=calculated.projected_fcfs, discounted_fcfs=calculated.discounted_fcfs,
        discounted_terminal_value=calculated.discounted_terminal_value,
        terminal_value_contribution=calculated.discounted_terminal_value/calculated.enterprise_value if calculated.enterprise_value else None,
        sensitivity=dict(wacc_values=waccs, terminal_growth_values=terminal, enterprise_value_grid=grid,
            value_per_assumed_share_grid=share_grid), assumptions=explicit, gaps=gaps,
        input_identity=_digest(dict(ticker=context['ticker'], sec_cik=context['sec_cik'], profile_key=context['profile_key'],
            source_revision=context['source_revision'], assumptions=explicit)))
    return _json(result)
