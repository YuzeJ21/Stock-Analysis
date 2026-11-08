"""Additive review integration using constructed receipts, never live observations."""
from copy import deepcopy
import base64
import hashlib
import json

from tests.test_mrvl_earnings_review import packet
from tests.test_mrvl_after_tax_reconciliation import _evidence, _profile_receipt, NOW, STAMP


def _renormalize(receipt, kind):
    from src.mrvl_earnings_review import normalize_review_facts, normalize_review_profile
    receipt = deepcopy(receipt)
    receipt.pop('normalized_sha256', None); receipt.pop('normalization', None)
    receipt['payload_sha256'] = hashlib.sha256(json.dumps(receipt['payload']).encode()).hexdigest()
    return (normalize_review_facts if kind == 'facts' else normalize_review_profile)(receipt)


def qualified_packet():
    from src.mrvl_earnings_review import seal_review_packet
    p = packet(); p['observed_at'] = STAMP
    for concept, value in {
        'NetIncomeLoss':160_000_000, 'EarningsPerShareDiluted':1.60,
        'ShareBasedCompensation':10_000_000, 'AmortizationOfIntangibleAssets':8_200_000,
        'GainLossOnSaleOfBusiness':4_400_000,
    }.items():
        for rows in p['facts']['payload']['facts']['us-gaap'][concept]['units'].values():
            for row in rows: row['val'] = value
    p['facts'] = _renormalize(p['facts'], 'facts')
    recent = p['profiles']['MRVL']['payload']['filings']['recent']
    additional = _profile_receipt()['payload']['filings']['recent']
    optional = {'acceptanceDateTime':['2026-03-05T21:06:03Z'], 'isInlineXBRL':[1], 'isXBRL':[1]}
    for key in recent:
        recent[key] += additional.get(key, optional.get(key, [None]))
    p['profiles']['MRVL'] = _renormalize(p['profiles']['MRVL'], 'profile')
    p['after_tax_reconciliation'] = _evidence()
    return seal_review_packet(p)


def qualified_sources():
    """Raw constructed HTTP payloads for the actual refresh/Workbench/browser path."""
    from tests.test_mrvl_earnings_sources import _sources, _facts_payload, MRVL_PROFILE, MRVL_FACTS
    from tests.test_mrvl_after_tax_reconciliation import PRIMARY_URL, EXHIBIT_URL
    p = qualified_packet(); sources = _sources()
    sources[MRVL_PROFILE] = deepcopy(p['profiles']['MRVL']['payload'])
    facts = _facts_payload()
    facts['facts']['us-gaap'].update(deepcopy(p['facts']['payload']['facts']['us-gaap']))
    sources[MRVL_FACTS] = facts
    sources[PRIMARY_URL] = base64.b64decode(p['after_tax_reconciliation']['primary']['payload_raw_base64'])
    sources[EXHIBIT_URL] = base64.b64decode(p['after_tax_reconciliation']['exhibit']['payload_raw_base64'])
    return sources


def test_verified_bridge_replaces_only_aggregate_gap_without_promoting_any_method():
    from src.mrvl_earnings_review import build_mrvl_earnings_review, seal_review_packet
    p = qualified_packet(); before = deepcopy(p)
    prior = deepcopy(p); del prior['after_tax_reconciliation']; prior = seal_review_packet(prior)
    baseline = build_mrvl_earnings_review(prior, as_of=NOW)
    result = build_mrvl_earnings_review(p, as_of=NOW)
    assert result['quality']['after_tax_reconciliation']['status'] == 'verified_issuer_reconciliation'
    assert 'adjusted_after_tax_reconciliation_unresolved' not in result['quality']['gaps']
    assert 'sale_specific_tax_allocation_unavailable' in result['quality']['gaps']
    assert result['quality']['fields'] == baseline['quality']['fields']
    assert result['peer_context'] == baseline['peer_context']
    assert result['commercial_eligible'] is False and result['readiness_promoted'] is False
    assert result['peer_context']['numerical_admission'] == 'not_granted'
    assert p == before


def test_bad_reconciliation_retains_all_valid_annual_fields_and_peer_context():
    from src.mrvl_earnings_review import build_mrvl_earnings_review, seal_review_packet
    p = qualified_packet(); original = build_mrvl_earnings_review(p, as_of=NOW)
    p['after_tax_reconciliation']['exhibit'] = {'status':'unavailable','reason':'reconciliation_exhibit_unavailable'}
    p = seal_review_packet(p)
    result = build_mrvl_earnings_review(p, as_of=NOW)
    assert result['status'] == 'inspection_only'
    assert result['quality']['after_tax_reconciliation']['status'] == 'withheld'
    assert 'adjusted_after_tax_reconciliation_unresolved' in result['quality']['gaps']
    assert result['quality']['fields'] == original['quality']['fields']
    assert result['peer_context'] == original['peer_context']


def test_new_raw_size_limit_is_checked_before_parent_packet_hash(monkeypatch):
    from src import mrvl_earnings_review as engine
    p = packet(); p['after_tax_reconciliation'] = {'schema_version':'mrvl-after-tax-reconciliation-v1',
        'primary':{'payload_raw_base64':'A'*5500}, 'exhibit':{}}
    monkeypatch.setattr(engine, 'MAX_FILING_BYTES', 4096)
    def forbidden_digest(_):
        raise AssertionError('Oversized reconciliation bytes must be rejected before hashing')
    monkeypatch.setattr(engine, '_digest', forbidden_digest)
    result = engine.build_mrvl_earnings_review(p, as_of=NOW)
    assert result['status'] == 'withheld'
    assert result['reason'] == 'review_reconciliation_document_oversized'
