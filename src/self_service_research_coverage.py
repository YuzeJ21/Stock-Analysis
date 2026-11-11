"""Failure-inclusive, session-private capability study over twelve fixed companies.

Collection is explicit. Reads revalidate original source packets and recompute
tools locally. Reduced reports contain provenance and capability states, never
captured financial amounts, raw responses or user records.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, MutableMapping
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import re
from tempfile import TemporaryDirectory
from urllib.error import HTTPError

from src import online_peer_sources as peer_sources
from src.company_sec_online_preview import _utc_timestamp
from src.company_sec_online_preview import _iso_date
from src.online_company_identity import _mode_reason, financial_identity_valid, get_price_filing_association
from src.online_company_prices import fetch_online_company_prices
from src.online_filing_context import validated_filing_inventory
from src.online_listing_session import fresh_classification, SESSION_KEY as LISTING_SESSION_KEY, SCHEMA as LISTING_SCHEMA
from src.online_peer_valuation import normalized_digest
from src.online_peer_packet_storage import (
    SCHEMA as PEER_STORAGE_SCHEMA, MAX_EXPANDED_BYTES as MAX_EXPANDED_PEER_BYTES,
    pack_peer_packet, unpack_peer_packet, peer_classification_ref,
)
from src.online_research_tools import build_online_research_context, run_online_scenario
from src.online_sec_receipt import fetch_sec_json_receipt, _fetch_raw
from src.online_us_universe import _fetch_directory
from src.sec_annual_history import fetch_sec_online_research_view
from src.security_classification import validated_classification
from src.us_listing_receipt_audit import _SOURCES

SCHEMA = 'self-service-research-coverage-v1'
SESSION_KEY = 'self_service_research_coverage_v1'
SAMPLE_GROUPS = (
    ('Semiconductors', ('AMD', 'NVDA', 'QCOM')),
    ('Banks', ('JPM', 'BAC', 'C')),
    ('Utilities', ('DUK', 'SO', 'NEE')),
    ('Foreign issuers', ('TSM', 'SAP', 'IBN')),
)
SAMPLE = tuple(ticker for _, tickers in SAMPLE_GROUPS for ticker in tickers)
CAPABILITY_LABELS = {
    'matched_identity': 'SEC issuer match',
    'catalog': 'Usable filing catalog',
    'current_annual': 'Current annual facts',
    'direct_quarter': 'Current direct-quarter facts',
    'interim': 'Current interim facts',
    'dated_price': 'Dated close',
    'peer_comparison': 'Same-basis industry comparison',
    'trend': 'Compatible Business Trend metrics',
    'scenario_eligibility': 'Hypothetical scenario eligibility',
    'snapshot_replay': 'Exact private research replay',
}
PROBE_PARAMETERS = dict(revenue_growth=.08, fcf_margin=.15, wacc=.10, terminal_growth=.02, forecast_years=5)
PROBE_PROFILE = 'self-service-capability-study'
MAX_PACKET_BYTES = 8 * 1024 * 1024
MAX_STATE_BYTES = 64 * 1024 * 1024
_STATE_KEYS = {'schema_version', 'sample', 'packets', 'classifications', 'listing_ref',
    'adapter_operation_count', 'source_request_count', 'source_access_limit', 'digest'}
_STATUSES = ('available', 'partial', 'held', 'excluded', 'failed', 'unattempted')
_PEER_DEPENDENCIES = {'classification', 'vendor', 'industry', 'sec', 'prices', 'amendment', 'security', 'history'}
_DIRECTORY_URLS = frozenset(row[2] for row in _SOURCES)


def _default_source_fetcher(url, user_agent):
    """Preserve each existing transport's own headers, bounds and redirects."""
    fetch = _fetch_directory if isinstance(url,str) and url in _DIRECTORY_URLS else _fetch_raw
    return fetch(url,user_agent)


def default_dependencies():
    """Actual adapter defaults, also a narrow seam for constructed UI evidence."""
    return dict(financial=fetch_sec_online_research_view,prices=fetch_online_company_prices,
        source_fetcher=_default_source_fetcher,peer_dependencies={})


def _now(value):
    now = datetime.now(timezone.utc) if value is None else value
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError('invalid_observation')
    return now.astimezone(timezone.utc)


def _mapping(value):
    return value if isinstance(value,Mapping) else {}


def _bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _fresh(value, now):
    observed = _utc_timestamp(value)
    return observed is not None and timedelta(0) <= now-observed <= timedelta(hours=24)


def _seal(state):
    state['digest'] = normalized_digest({key:value for key,value in state.items() if key != 'digest'})
    return state


def _new():
    return _seal(dict(schema_version=SCHEMA, sample=list(SAMPLE), packets={}, classifications={}, listing_ref=None,
        adapter_operation_count=0, source_request_count=0, source_access_limit=None))


def _valid(state):
    try:
        if (not isinstance(state, Mapping) or set(state) != _STATE_KEYS or state.get('schema_version') != SCHEMA
            or state.get('sample') != list(SAMPLE) or not isinstance(state.get('packets'), Mapping)
            or not set(state['packets']) <= set(SAMPLE) or not isinstance(state.get('classifications'), Mapping)
            or len(state['classifications']) > len(SAMPLE) or len(_bytes(state)) > MAX_STATE_BYTES
            or state.get('digest') != normalized_digest({k:v for k,v in state.items() if k != 'digest'})):
            return False
        if any(type(state.get(key)) is not int or not 0 <= state[key] <= 1_000_000
               for key in ('adapter_operation_count', 'source_request_count')):
            return False
        if state['listing_ref'] is not None and state['listing_ref'] not in state['classifications']:
            return False
        for key, classification in state['classifications'].items():
            if normalized_digest(classification) != key or validated_classification(classification) is None:
                return False
        for ticker, packet in state['packets'].items():
            if not isinstance(packet, Mapping) or packet.get('ticker') != ticker or len(_bytes(packet)) > MAX_PACKET_BYTES:
                return False
            peer = packet.get('peer_packet')
            if isinstance(peer, Mapping) and peer.get('schema_version') == PEER_STORAGE_SCHEMA:
                reference = peer_classification_ref(peer)
                if reference is not None and reference not in state['classifications']:
                    return False
                continue
            collection = peer.get('collection') if isinstance(peer, Mapping) else None
            if isinstance(collection, Mapping) and ('classification' in collection
                or collection.get('classification_ref') not in state['classifications']):
                return False
        limit = state['source_access_limit']
        return limit is None or (isinstance(limit, Mapping) and limit.get('http_status') in {403,429,503}
            and isinstance(limit.get('source_url'), str) and type(limit.get('retry_after_seconds')) is int)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        return False


def _compact_peer(packet, state):
    result = deepcopy(packet)
    collection = result.get('collection')
    if isinstance(collection, Mapping):
        classification = collection.pop('classification', None)
        if validated_classification(classification) is None:
            return None
        key = normalized_digest(classification)
        state['classifications'][key] = classification
        collection['classification_ref'] = key
        state['listing_ref'] = key
    return result


def _expand_peer(packet, state):
    try:
        result = unpack_peer_packet(packet) if packet.get('schema_version') == PEER_STORAGE_SCHEMA else deepcopy(packet)
        if not isinstance(result, Mapping):
            return None
        collection = result.get('collection')
        if isinstance(collection, Mapping):
            key = collection.pop('classification_ref')
            collection['classification'] = state['classifications'][key]
        if result.get('packet_digest') != normalized_digest({k:v for k,v in result.items() if k != 'packet_digest'}):
            return None
        return result
    except (ValueError, TypeError, KeyError, AttributeError):
        return None


def _referenced_classifications(state):
    return {reference for packet in state['packets'].values()
        if (reference := peer_classification_ref(packet.get('peer_packet'))) is not None}


def _peer_storage_evidence(stored, restored):
    if not isinstance(stored, Mapping) or stored.get('schema_version') != PEER_STORAGE_SCHEMA:
        return None
    if restored is None:
        return dict(status='held',reason='peer_source_retention_invalid',encoding='zlib+base64',
            source_evidence_unchanged=False)
    return dict(status='retained',reason='full_original_peer_packet_restored',encoding='zlib+base64',
        stored_bytes=len(_bytes(stored)),expanded_bytes=stored['expanded_bytes'],
        packet_digest=restored['packet_digest'],source_evidence_unchanged=True)


def _recent_classification(state, now):
    candidates = [checked for value in state['classifications'].values()
        if (checked := fresh_classification(value, now)) is not None]
    return max(candidates, key=lambda item:item['inventory']['observed_from']) if candidates else None


def _failure(reason):
    return isinstance(reason, str) and any(value in reason for value in (
        'source_unavailable', 'receipt_unavailable', 'query_unavailable', 'component_unavailable', 'access_paused'))


def _cell(status, reason):
    return dict(status=status, reason=reason or 'evidence_unavailable')


def _held(reason):
    return _cell('failed' if _failure(reason) else 'held', reason)


def _period_cell(context, kind):
    state = context.get('filing_coverage', {}).get('current', {}).get(kind, {})
    anchor = state.get('anchor') or {}
    target = anchor.get('period_end')
    rows = [row for row in context.get('business_trend', {}).get('periods', []) if row.get('kind') == kind]
    matched = [row for row in rows if row.get('period_end') == target and row.get('status') == 'available'
        and isinstance(row.get('fields'), Mapping) and 'revenue' in row['fields']]
    if state.get('status') == 'corroborated' and matched:
        return _cell('available', state.get('reason') or 'current_exact_reported_period')
    return _held(state.get('reason') or 'current_' + kind + '_facts_unavailable')


def _replay_probe(context, usable):
    """Use the actual private store, with a disposable root and no user notes."""
    result = dict(status='held', reason='usable_current_research_fields_required',
        exact_context_match=False, comparison_status=None, disposable_store=True, user_store_written=False)
    if not usable or not context.get('sec_cik'):
        return result
    from src import online_research_context_store as store
    try:
        context_bytes = len(_bytes(context))
        if context_bytes > store.MAX_EXPANDED_SNAPSHOT_BYTES:
            result.update(reason='research_snapshot_size_limit',context_bytes=context_bytes,
                max_context_bytes=store.MAX_EXPANDED_SNAPSHOT_BYTES,
                max_stored_bytes=store.MAX_SNAPSHOT_BYTES,limit_kind='expanded')
            return result
        scope = {key:context[key] for key in ('profile_key', 'ticker', 'sec_cik')}
        with TemporaryDirectory(prefix='self-service-capability-') as temporary:
            root = Path(temporary)
            saved = store.save_research_context(context, **scope, project_root=root)
            reopened = store.load_research_context(saved['snapshot_id'], **scope, project_root=root)
            compared = store.compare_research_contexts(context, reopened)
            exact = reopened['context'] == context
            result.update(status='available' if exact and compared['status'] == 'unchanged' else 'held',
                reason='exact_private_context_replay' if exact and compared['status'] == 'unchanged' else 'private_context_replay_differs',
                exact_context_match=exact, comparison_status=compared['status'],
                snapshot_id=saved['snapshot_id'], source_revision=context['source_revision'])
    except store.ResearchSnapshotSizeError as error:
        result.update(reason='research_snapshot_size_limit',context_bytes=context_bytes,
            max_context_bytes=store.MAX_EXPANDED_SNAPSHOT_BYTES,
            max_stored_bytes=store.MAX_SNAPSHOT_BYTES,limit_kind=error.limit_kind)
    except (ValueError, OSError, TypeError, KeyError, AttributeError):
        result.update(status='failed', reason='disposable_private_replay_failed')
    return result


def _saved_replay(proof, context):
    held = dict(status='held',reason='snapshot_proof_needs_explicit_recheck',exact_context_match=False,
        comparison_status=None,disposable_store=True,user_store_written=False)
    try:
        if (not isinstance(proof,Mapping) or proof.get('schema_version') != 'self-service-private-replay-proof-v1'
            or proof.get('digest') != normalized_digest({key:value for key,value in proof.items() if key != 'digest'})
            or proof.get('context_sha256') != normalized_digest(context)
            or proof.get('source_revision') != context.get('source_revision')
            or not isinstance(proof.get('result'),Mapping)):
            return held
        result = proof['result']
        if (result.get('status') not in {'available','held','failed'} or result.get('disposable_store') is not True
            or result.get('user_store_written') is not False or (result.get('status') == 'available' and (
                result.get('exact_context_match') is not True or result.get('comparison_status') != 'unchanged'))):
            return held
        return deepcopy(dict(result))
    except (ValueError,TypeError,KeyError,AttributeError,RecursionError):
        return held


def _receipts(context):
    result = []
    def add(value, source=None):
        if not isinstance(value, Mapping):
            return
        row = {key:value[key] for key in ('source', 'status', 'reason', 'source_url', 'source_ref', 'observed_at',
            'observed_at_utc', 'retrieved_at_utc', 'payload_sha256', 'normalized_sha256', 'source_last_modified')
            if key in value and (value[key] is None or isinstance(value[key], str))}
        if source:
            row['source'] = source
        if row and row not in result:
            result.append(row)
    for value in context.get('source_receipts', []):
        add(value)
    peer = context.get('peer_read_through', {})
    if peer.get('industry_source_ref'):
        add(dict(source_url=peer['industry_source_ref'],observed_at=peer.get('industry_observed_at'),
            normalized_sha256=peer.get('industry_normalized_sha256')), 'industry_reference_directory')
    subject_context = _mapping(peer.get('subject_source_context'))
    if subject_context.get('profile_source_ref'):
        add(dict(source_url=subject_context['profile_source_ref'],observed_at=subject_context.get('profile_observed_at'),
            payload_sha256=subject_context.get('profile_sha256')), 'industry_reference_subject_profile')
    for row in [peer.get('subject') or {}, *peer.get('peers', [])]:
        if not row:
            continue
        add(dict(source_url=row.get('source_ref'), observed_at=row.get('observed_at'),
            payload_sha256=row.get('facts_sha256')), 'industry_reference_annual_eps')
        add(dict(source_url=row.get('price_source_ref'), observed_at=row.get('price_observed_at'),
            payload_sha256=row.get('price_sha256')), 'industry_reference_dated_close')
    return result[:80]


def _row(ticker, group, packet, state, now, mode_reason=None, *, collect_replay=False):
    attempted = packet is not None
    row = dict(ticker=ticker, group=group, attempted=attempted, attempted_at=packet.get('observed_at') if attempted else None,
        status='unattempted', reason='not_requested', sec_cik=None, capabilities={}, periods={},
        source_receipts=[], peer_references=[], peer_exclusions=[], peer_source_attempts=[], snapshot_replay=None)
    if not attempted or mode_reason:
        status = 'held' if attempted else 'unattempted'
        row.update(status=status, reason=mode_reason or 'not_requested',
            capabilities={key:_cell(status, mode_reason or 'not_requested') for key in CAPABILITY_LABELS})
        return row
    financial = packet.get('financial') if isinstance(packet.get('financial'), Mapping) else {}
    prices = packet.get('prices') if isinstance(packet.get('prices'), Mapping) else {}
    identity = _mapping(financial.get('companyfacts_identity'))
    raw_inventory = _mapping(financial.get('filing_inventory'))
    catalog = validated_filing_inventory(raw_inventory, ticker=ticker, expected_cik=raw_inventory.get('sec_cik'), as_of=now)
    identity_ok = (financial_identity_valid(ticker, identity) and financial.get('ticker') == ticker
        and financial.get('sec_cik', identity.get('sec_cik')) == identity.get('sec_cik') and _fresh(identity.get('observed_at'), now))
    cik = catalog['sec_cik'] if catalog else identity.get('sec_cik') if identity_ok else None
    peer_packet = _expand_peer(packet.get('peer_packet'), state) if isinstance(packet.get('peer_packet'), Mapping) else None
    if (isinstance(packet.get('peer_packet'),Mapping)
        and packet['peer_packet'].get('schema_version') == PEER_STORAGE_SCHEMA
        and peer_packet is not None and peer_packet.get('ticker') != ticker):
        peer_packet = None
    storage = _peer_storage_evidence(packet.get('peer_packet'),peer_packet)
    if storage and storage['status'] == 'held':
        peer_packet = peer_sources._cache({},ticker,None,'peer_source_retention_invalid',
            _utc_timestamp(packet.get('observed_at')) or now)
    context = build_online_research_context(financial, prices, peer_packet, packet.get('association'),
        ticker=ticker, profile_key=PROBE_PROFILE, expected_cik=cik, notes=None, scenario=None, as_of=now)
    financial_failure = any('/companyfacts/' in value.get('source_url','') or 'company_tickers.json' in value.get('source_url','')
        for value in packet.get('source_failures',[]) if isinstance(value,Mapping))
    capabilities = dict(
        matched_identity=_cell('available','matched_sec_companyfacts_identity') if identity_ok else _held(
            'companyfacts_source_unavailable' if financial_failure else
            'financial_identity_stale_or_mismatched' if identity else financial.get('reason') or 'financial_identity_unavailable'),
        catalog=_cell('available','validated_filing_catalog') if catalog else _held(raw_inventory.get('reason') or 'filing_catalog_stale_or_invalid'),
        current_annual=_period_cell(context, 'annual'), direct_quarter=_period_cell(context, 'quarterly'),
        interim=_period_cell(context, 'interim'))
    price_context = context.get('price_context', {})
    capabilities['dated_price'] = _cell('available','validated_dated_close') if price_context.get('status') == 'inspection_only' else _held(
        prices.get('reason') or price_context.get('reason') or 'dated_price_unavailable')
    peers = context.get('peer_read_through', {})
    reason = peers.get('reason') or 'industry_comparison_unavailable'
    listing_context = _mapping(_mapping(peer_packet).get('listing_context'))
    source_attempts = listing_context.get('source_attempts',[])
    source_attempts = [{key:value.get(key) for key in ('source_url','status','reason','observed_at','payload_sha256')
        if value.get(key) is not None} for value in source_attempts[:4] if isinstance(value,Mapping)] if isinstance(source_attempts,list) else []
    listing_transport_failed = reason == 'listing_classification_unavailable' and any(
        attempt.get('reason') in {'source_transport_unavailable','source_access_limited'} for attempt in source_attempts)
    capabilities['peer_comparison'] = _cell('available',reason) if peers.get('status') == 'research_comparison' else _cell(
        'partial' if peers.get('subject') and reason == 'at_least_three_compatible_industry_references_required' else
        'failed' if listing_transport_failed or _failure(reason) else 'held', reason)
    metrics = [metric for metric in context.get('business_trend', {}).get('metrics', []) if metric.get('status') == 'calculated']
    current_metric_ends = {period.get('period_end') for period in context.get('business_trend',{}).get('periods',[])
        if period.get('current') is True}
    capabilities['trend'] = _cell('available','compatible_metrics_in_current_reported_period' if any(
        metric.get('period_end') in current_metric_ends for metric in metrics) else 'compatible_historical_metrics_only') if metrics else _cell('held','compatible_observed_metrics_unavailable')
    scenario = run_online_scenario(context, PROBE_PARAMETERS)
    capabilities['scenario_eligibility'] = _cell('available','fixed_explicit_hypotheses_calculated') if scenario.get('status') == 'calculated' else _cell(
        'excluded' if scenario.get('status') == 'excluded' else 'held', scenario.get('reason'))
    usable = any(period.get('status') == 'available' and period.get('fields')
        for period in context.get('business_trend', {}).get('periods', []))
    replay_context = context
    if scenario.get('status') == 'calculated':
        replay_context = build_online_research_context(financial, prices, peer_packet, packet.get('association'),
            ticker=ticker, profile_key=PROBE_PROFILE, expected_cik=cik, notes=None, scenario=scenario, as_of=now)
    if collect_replay:
        replay = _replay_probe(replay_context, usable)
        proof = dict(schema_version='self-service-private-replay-proof-v1', context_sha256=normalized_digest(replay_context),
            source_revision=replay_context['source_revision'], result=replay)
        proof['digest'] = normalized_digest(proof)
        packet['replay_proof'] = proof
    else:
        replay = _saved_replay(packet.get('replay_proof'), replay_context)
    capabilities['snapshot_replay'] = _cell(replay['status'], replay['reason'])
    available = sum(cell['status'] == 'available' for cell in capabilities.values())
    failed = any(cell['status'] == 'failed' for cell in capabilities.values())
    row.update(status='available' if available == len(capabilities) else 'partial' if available else 'failed' if failed else 'held',
        reason='capabilities_revalidated' if available else 'source_attempt_failed' if failed else 'capabilities_held',
        sec_cik=cik, capabilities=capabilities, source_receipts=_receipts(context), snapshot_replay=replay,
        peer_references=[{key:value.get(key) for key in ('ticker','sec_cik','period_start','period_end','accession',
            'form','filed','price_date','filing_ref','source_ref','identity_basis')} for value in peers.get('peers',[])],
        peer_exclusions=[dict(ticker=value.get('ticker'),reason=value.get('reason')) for value in peers.get('excluded', [])],
        peer_source_attempts=source_attempts,
        listing_association_status=_mapping(packet.get('association')).get('status'),
        scenario_hypothesis_basis='Fixed capability-test hypotheses; not issuer guidance, consensus or user assumptions.',
        trend_metric_keys=sorted({metric['key'] for metric in metrics}))
    for kind, current in context.get('filing_coverage', {}).get('current', {}).items():
        anchor = current.get('anchor') or {}
        row['periods'][kind] = {key:anchor.get(key) for key in ('period_start','period_end','report_date','accession','form','filed','accepted_at','source_url')}
        row['periods'][kind].update(status=current.get('status'),reason=current.get('reason'))
    row['price_date'] = price_context.get('last_price_date')
    if storage:
        row['peer_storage'] = storage
    return row


def _summary(state, now, *, reason=None):
    rows = [_row(ticker, group, state['packets'].get(ticker), state, now, reason)
        for group, tickers in SAMPLE_GROUPS for ticker in tickers]
    def counts(members):
        return dict(attempted=sum(row['attempted'] for row in members), **{key:sum(
            row['capabilities'][key]['status'] == 'available' for row in members) for key in CAPABILITY_LABELS})
    by_group = [dict(group=group,tickers=list(tickers),requested_count=3,
        attempted_count=sum(row['attempted'] for row in rows if row['group'] == group),
        counts=counts([row for row in rows if row['group'] == group])) for group,tickers in SAMPLE_GROUPS]
    dates = [_utc_timestamp(receipt.get('observed_at') or receipt.get('retrieved_at_utc'))
        for row in rows for receipt in row['source_receipts']]
    dates = [value for value in dates if value is not None]
    return dict(schema_version=SCHEMA, status='unavailable' if reason else 'inspection_only', reason=reason,
        requested_tickers=list(SAMPLE), requested_count=12, attempted_count=sum(row['attempted'] for row in rows),
        pending_count=sum(not row['attempted'] for row in rows), counts=counts(rows), by_group=by_group, rows=rows,
        status_counts={status:sum(row['status'] == status for row in rows) for status in _STATUSES},
        capability_status_counts={key:{status:sum(row['capabilities'][key]['status'] == status for row in rows)
            for status in _STATUSES} for key in CAPABILITY_LABELS},
        paused=state['source_access_limit'] is not None, source_access_limit=state['source_access_limit'],
        adapter_operation_count=state['adapter_operation_count'], source_request_count=state['source_request_count'],
        observed_from=min(dates).isoformat() if dates else None, observed_to=max(dates).isoformat() if dates else None,
        scenario_probe_parameters=dict(PROBE_PARAMETERS), scenario_probe_basis='fixed_explicit_hypothetical_capability_check',
        sample_basis='Four selected study families; not an industry or domicile census.',
        session_only=True, market_universe_coverage_established=False, canonical_changed=False,
        user_notes_read=False, user_store_written=False, saved_readiness_promoted=False, commercial_eligible=False,
        rights_status='personal_inspection_only_source_redistribution_and_commercial_rights_unverified')


def validated_coverage_view(value):
    """Validate a reduced display contract and recompute every sample counter.

    This is not source revalidation: the getter performs that from private source
    packets. This helper prevents a display from trusting stored aggregate counts.
    """
    try:
        if (not isinstance(value,Mapping) or value.get('schema_version') != SCHEMA
            or value.get('status') not in {'inspection_only','unavailable'} or len(_bytes(value)) > 2*1024*1024
            or not isinstance(value.get('rows'),list) or len(value['rows']) != len(SAMPLE)):
            return None
        groups = {ticker:group for group,tickers in SAMPLE_GROUPS for ticker in tickers}
        for ticker,row in zip(SAMPLE,value['rows']):
            if (not isinstance(row,Mapping) or row.get('ticker') != ticker or row.get('group') != groups[ticker]
                or type(row.get('attempted')) is not bool or row.get('status') not in _STATUSES
                or not isinstance(row.get('capabilities'),Mapping) or set(row['capabilities']) != set(CAPABILITY_LABELS)
                or not isinstance(row.get('source_receipts'),list) or len(row['source_receipts']) > 80):
                return None
            cik = row.get('sec_cik')
            if cik is not None and (not isinstance(cik,str) or re.fullmatch(r'\d{10}',cik) is None or int(cik)==0):
                return None
            for key,cell in row['capabilities'].items():
                if (not isinstance(cell,Mapping) or set(cell) != {'status','reason'} or cell['status'] not in _STATUSES
                    or not isinstance(cell['reason'],str) or not 0<len(cell['reason'])<=300
                    or (not row['attempted'] and cell['status'] != 'unattempted')):
                    return None
                if cell['status']=='available' and key in {'matched_identity','catalog'} and cik is None:
                    return None
            if row['capabilities']['dated_price']['status']=='available' and _iso_date(row.get('price_date')) is None:
                return None
            replay = row.get('snapshot_replay')
            if row['capabilities']['snapshot_replay']['status']=='available' and (
                not isinstance(replay,Mapping) or replay.get('status')!='available'
                or replay.get('exact_context_match') is not True or replay.get('comparison_status')!='unchanged'
                or replay.get('disposable_store') is not True or replay.get('user_store_written') is not False):
                return None
            for receipt in row['source_receipts']:
                if not isinstance(receipt,Mapping) or any(v is not None and not isinstance(v,str) for v in receipt.values()):
                    return None
            storage = row.get('peer_storage')
            if storage is not None:
                if (not row['attempted'] or not isinstance(storage,Mapping) or storage.get('encoding')!='zlib+base64'
                    or storage.get('status') not in {'retained','held'}):
                    return None
                if storage['status']=='retained':
                    if (set(storage)!={'status','reason','encoding','stored_bytes','expanded_bytes','packet_digest','source_evidence_unchanged'}
                        or storage.get('reason')!='full_original_peer_packet_restored' or storage.get('source_evidence_unchanged') is not True
                        or type(storage.get('stored_bytes')) is not int or not 0<storage['stored_bytes']<=MAX_PACKET_BYTES
                        or type(storage.get('expanded_bytes')) is not int or not 0<storage['expanded_bytes']<=MAX_EXPANDED_PEER_BYTES
                        or not isinstance(storage.get('packet_digest'),str) or re.fullmatch(r'[0-9a-f]{64}',storage['packet_digest']) is None):
                        return None
                elif (set(storage)!={'status','reason','encoding','source_evidence_unchanged'}
                    or storage.get('reason')!='peer_source_retention_invalid' or storage.get('source_evidence_unchanged') is not False):
                    return None
        result = deepcopy(dict(value))
        rows = result['rows']
        def counts(members):
            return dict(attempted=sum(row['attempted'] for row in members), **{key:sum(
                row['capabilities'][key]['status']=='available' for row in members) for key in CAPABILITY_LABELS})
        result.update(requested_tickers=list(SAMPLE),requested_count=12,
            attempted_count=sum(row['attempted'] for row in rows),pending_count=sum(not row['attempted'] for row in rows),
            counts=counts(rows),by_group=[dict(group=group,tickers=list(tickers),requested_count=3,
                attempted_count=sum(row['attempted'] for row in rows if row['group']==group),
                counts=counts([row for row in rows if row['group']==group])) for group,tickers in SAMPLE_GROUPS],
            status_counts={status:sum(row['status']==status for row in rows) for status in _STATUSES},
            capability_status_counts={key:{status:sum(row['capabilities'][key]['status']==status for row in rows)
                for status in _STATUSES} for key in CAPABILITY_LABELS})
        return result
    except (ValueError,TypeError,KeyError,AttributeError,OverflowError,RecursionError):
        return None


def _collect(ticker, state, deps, now, user_agent):
    operations, requests, access = [], [], {}
    memo, failures = {}, {}
    memo_bytes = 0
    def limited(error, url):
        if error.code in {403,429,503} and isinstance(url,str) and re.match(r'https://(?:www\.)?(?:data\.)?sec\.gov/',url):
            retry = error.headers.get('Retry-After') if error.headers else None
            seconds = int(retry) if isinstance(retry,str) and re.fullmatch(r'\d{1,6}',retry) else 300
            access.update(source_url=url,http_status=error.code,retry_after_seconds=max(1,min(seconds,3600)))
    def raw(url, agent):
        nonlocal memo_bytes
        if access:
            raise RuntimeError('source_access_paused')
        if url in failures:
            raise OSError('source_unavailable_in_this_attempt')
        if url in memo:
            return memo[url]
        requests.append(url)
        try:
            result = deps['source_fetcher'](url, agent)
        except HTTPError as error:
            failures[url] = dict(source_url=url,reason='source_access_limited' if error.code in {403,429,503} else 'source_unavailable')
            limited(error,url)
            raise
        except (OSError,RuntimeError,TimeoutError,ValueError,TypeError):
            failures[url] = dict(source_url=url,reason='source_unavailable')
            raise
        if isinstance(result,tuple) and len(result)==3 and isinstance(result[0],bytes) and memo_bytes+len(result[0])<=32*1024*1024:
            memo[url] = result
            memo_bytes += len(result[0])
        return result
    def call(name, function, *args, **kwargs):
        operations.append(name)
        try:
            value = function(*args, **kwargs)
            return value if isinstance(value,Mapping) else dict(status='withheld',reason='source_component_schema_invalid',ticker=ticker)
        except HTTPError as error:
            limited(error,error.url)
            return dict(status='unavailable',reason='source_component_unavailable',ticker=ticker)
        except (OSError, RuntimeError, TimeoutError, ValueError, TypeError, KeyError, AttributeError):
            return dict(status='unavailable',reason='source_component_unavailable',ticker=ticker)
    classification = _recent_classification(state, now)
    mapping = classification['inventory']['map_receipt'] if classification else None
    if mapping and not any(isinstance(row,Mapping) and row.get('ticker') == ticker
        for row in mapping.get('payload',{}).values()):
        mapping = None
    financial = call('financial', deps['financial'], ticker, user_agent=user_agent,
        source_fetcher=raw, ticker_map_receipt=mapping, observed_at=now)
    identity = _mapping(financial.get('companyfacts_identity'))
    inventory = _mapping(financial.get('filing_inventory'))
    cik = identity.get('sec_cik') or inventory.get('sec_cik')
    prices = dict(status='unavailable',reason='source_access_paused') if access else call(
        'prices',deps['prices'],ticker,observed_at=now,include_verified_session_close=True)
    slot = {}
    if classification:
        envelope = dict(schema_version=LISTING_SCHEMA,classification=classification)
        envelope['digest'] = normalized_digest(envelope)
        slot[LISTING_SESSION_KEY] = envelope
    association = dict(status='withheld',reason='source_access_paused' if access else 'financial_identity_unavailable')
    if not access:
        association = call('association',get_price_filing_association,ticker,identity,prices,slot,
            refresh_requested=True,user_agent=user_agent,fetcher=raw,observed_at=now)
        peer_deps = dict(deps['peer_dependencies'])
        peer_deps.setdefault('sec',lambda url,**kwargs:fetch_sec_json_receipt(url,fetcher=raw,**kwargs))
        peer_deps.setdefault('classification',lambda **kwargs:peer_sources.fetch_classification(fetcher=raw,**kwargs))
        peer_deps.setdefault('prices',deps['prices'])
        peer_deps.setdefault('amendment',lambda *args,**kwargs:peer_sources.fetch_amendment_evidence(*args,fetcher=raw,**kwargs))
        peer_deps.setdefault('security',lambda *args,**kwargs:peer_sources.fetch_selected_security_evidence(*args,fetcher=raw,**kwargs))
        peer_deps.setdefault('history',lambda *args,**kwargs:peer_sources.fetch_vendor_history_match(*args,fetcher=raw,**kwargs))
        if classification:
            peer_deps['classification'] = lambda **kwargs:classification
        def counted(name, function):
            def invoke(*args, **kwargs):
                if access:
                    return dict(status='unavailable',reason='source_access_paused')
                return call('peer_'+name,function,*args,**kwargs)
            return invoke
        call('peers',peer_sources.get_online_peer_valuation,ticker,slot,refresh_requested=True,
            expected_cik=cik,user_agent=user_agent,as_of=now,
            dependencies={name:counted(name,fn) for name,fn in peer_deps.items()})
    packet = dict(ticker=ticker,observed_at=now.isoformat(),financial=financial,prices=prices,association=association,
        peer_packet=_compact_peer(slot.get(peer_sources.SESSION_KEY,{}),state), source_access_limit=access or None,
        source_failures=list(failures.values()))
    if len(_bytes(packet)) > MAX_PACKET_BYTES:
        # Retain all original source values, including exact filing bodies.
        # Reserve room for the small hash-bound replay proof added below.
        fixed_bytes = len(_bytes({**packet,'peer_packet':None}))-4
        budget = MAX_PACKET_BYTES-fixed_bytes-4096
        if budget > 0:
            retained = pack_peer_packet(packet['peer_packet'],max_stored_bytes=budget)
            if retained is not None:
                packet['peer_packet'] = retained
    if len(_bytes(packet)) > MAX_PACKET_BYTES:
        # Peer retention cannot erase independently successful financial/price
        # observations. Discard the whole peer collection with its real sealed
        # failure contract; never trim source arrays into a claimed PE verdict.
        listing_context = _mapping(slot.get(peer_sources.SESSION_KEY)).get('listing_context')
        packet['peer_packet'] = peer_sources._cache({},ticker,None,'peer_source_retention_size_limit',now,
            listing_context=listing_context)
    if len(_bytes(packet)) > MAX_PACKET_BYTES:
        packet = dict(ticker=ticker,observed_at=now.isoformat(),financial=dict(status='unavailable',reason='source_packet_size_limit'),
            prices={},association={},peer_packet=None,source_access_limit=access or None)
    state['packets'][ticker] = packet
    group = next(group for group,tickers in SAMPLE_GROUPS if ticker in tickers)
    _row(ticker,group,packet,state,now,collect_replay=True)
    referenced = _referenced_classifications(state)
    if state['listing_ref']:
        referenced.add(state['listing_ref'])
    state['classifications'] = {key:value for key,value in state['classifications'].items() if key in referenced}
    state['source_access_limit'] = access or None
    state['adapter_operation_count'] += len(operations)
    state['source_request_count'] += len(requests)
    return state


def get_self_service_coverage(session_state, *, inspect_requested=False, retry_ticker=None, reset_requested=False,
    user_agent=None, dependencies=None, as_of=None):
    """Inspect one next/retried company explicitly; ordinary reads never transport."""
    try:
        now = _now(as_of)
    except (ValueError, TypeError):
        return _summary(_new(),datetime.now(timezone.utc),reason='invalid_observation')
    if not isinstance(session_state,MutableMapping):
        return _summary(_new(),now,reason='invalid_self_service_coverage_session')
    existing = None if reset_requested else session_state.get(SESSION_KEY)
    if existing is not None and not _valid(existing):
        return _summary(_new(),now,reason='self_service_coverage_state_invalid')
    state = deepcopy(existing) if existing is not None else _new()
    reason = _mode_reason('research')
    if reason:
        return _summary(state,now,reason=reason)
    if type(inspect_requested) is not bool or type(reset_requested) is not bool:
        return _summary(state,now,reason='invalid_self_service_coverage_action')
    if reset_requested:
        session_state[SESSION_KEY] = state
        return _summary(state,now)
    if retry_ticker is not None and (retry_ticker not in SAMPLE or retry_ticker not in state['packets']):
        return _summary(state,now,reason='invalid_self_service_coverage_retry')
    target = retry_ticker
    if target is None and inspect_requested and state['source_access_limit'] is None:
        target = next((ticker for ticker in SAMPLE if ticker not in state['packets']),None)
    if target is None:
        return _summary(state,now)
    deps = default_dependencies()
    if dependencies is not None:
        if (not isinstance(dependencies,Mapping) or not set(dependencies) <= set(deps)
            or not isinstance(dependencies.get('peer_dependencies',{}),Mapping)
            or not set(dependencies.get('peer_dependencies',{})) <= _PEER_DEPENDENCIES):
            return _summary(state,now,reason='invalid_self_service_coverage_dependencies')
        deps.update(dependencies)
    if any(not callable(deps[key]) for key in ('financial','prices','source_fetcher')):
        return _summary(state,now,reason='invalid_self_service_coverage_dependencies')
    if not isinstance(user_agent,str) or not user_agent.strip() or any(c in user_agent for c in '\r\n'):
        return _summary(state,now,reason='sec_user_agent_required')
    state = _collect(target,state,deps,now,user_agent)
    if len(_bytes(state)) > MAX_STATE_BYTES:
        # An explicit unsuccessful replacement must never leave the prior
        # successful packet current on the next ordinary read.
        attempted_state = state
        state = deepcopy(existing) if existing is not None else _new()
        def bounded_failure(ticker, observed):
            return dict(ticker=ticker,observed_at=observed,
                financial=dict(status='withheld',ticker=ticker,reason='self_service_source_retention_size_limit'),
                prices={},association={},peer_packet=None,source_access_limit=None,source_failures=[])
        state['packets'][target] = bounded_failure(target,now.isoformat())
        state['adapter_operation_count'] = attempted_state['adapter_operation_count']
        state['source_request_count'] = attempted_state['source_request_count']
        state['source_access_limit'] = attempted_state['source_access_limit']
        referenced = _referenced_classifications(state)
        state['classifications'] = {key:value for key,value in state['classifications'].items() if key in referenced}
        state['listing_ref'] = next(iter(state['classifications']),None)
        if len(_bytes(state)) > MAX_STATE_BYTES:
            state['packets'] = {ticker:bounded_failure(ticker,packet.get('observed_at')) for ticker,packet in state['packets'].items()}
            state['classifications'],state['listing_ref'] = {},None
    session_state[SESSION_KEY] = _seal(state)
    return _summary(state,now)
