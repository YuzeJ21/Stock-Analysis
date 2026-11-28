"""SAP source basis must remain separate from USD/ADS valuation."""
from hashlib import sha256

import pytest

from sap_depositary_fixtures import BODY, CIK, RATIO, fixture, observed
from src.online_peer_valuation_ui import online_peer_valuation_html
from test_online_peer_sources import get


def test_native_annual_eps_and_filed_adr_ratio_are_observations_without_valuation(monkeypatch):
    _, peer, state, deps, calls = observed(monkeypatch)
    assert peer.get('subject_source_context'), peer
    scope = peer['subject_source_context']['selected_security_scope']
    ratio, _, eps = scope['evidence_observations']
    assert (ratio['value'], ratio['unit']) == (1, 'ordinary_shares/ADR')
    assert (eps['value'], eps['raw_text'], eps['unit'], eps['security_basis']) == (4.2, '4.20', 'EUR/shares', 'ordinary')
    assert eps['period_start'] == '2025-01-01' and eps['period_end'] == '2025-12-31'
    assert eps['source_ref'].endswith('#annual-eps') and eps['context_source_ref'].endswith('#annual')
    assert all(row['financial_eligible'] is False for row in scope['evidence_observations'])
    assert peer['status'] == 'withheld' and peer['subject'] is None and peer['peer_count'] == 0
    assert peer['peer_median'] is None and peer['premium_fraction'] is None
    before = list(calls)
    assert len(before) == 2
    assert get(state, dependencies=deps, ticker='SAP', expected_cik=CIK) == peer
    assert calls == before


@pytest.mark.parametrize('sources_only', [False, True])
def test_current_views_show_native_precision_adr_units_source_and_remaining_method_hold(monkeypatch, sources_only):
    _, peer, *_ = observed(monkeypatch)
    html = online_peer_valuation_html(peer, sources_only=sources_only)
    assert '4.20 EUR/common share' in html
    assert '1 ordinary shares/ADR' in html
    assert 'annual.htm#annual-eps' in html and '2025-12-31' in html
    assert '2026-02-26' in html and '2026-11-01' in html
    assert 'USD conversion' in html and 'price-to-filing' in html
    assert '4.20 USD' not in html and '4.20 EUR/ADS' not in html


@pytest.mark.parametrize('old,new', [
    (b'iso:EUR', b'iso:USD'), (b'2025-01-01', b'2024-01-01'),
    (b'DilutedEarningsLossPerShare', b'BasicEarningsLossPerShare'),
    (b'0001000184</x:identifier>', b'0000001111</x:identifier>'),
    (b'>4.20</ix:nonFraction>', b'>4.30</ix:nonFraction>'),
    (b'each ADR represents one ordinary share', b'each ADR represents two ordinary shares'),
])
def test_resealed_source_cannot_substitute_currency_period_entity_earnings_or_ratio(monkeypatch, old, new):
    _, deps, _ = fixture(monkeypatch, raw=BODY.replace(old, new))
    peer = get({}, refresh=True, dependencies=deps, ticker='SAP', expected_cik=CIK)
    assert peer['status'] == 'withheld' and peer['subject'] is None
    assert 'selected_security_scope' not in peer.get('subject_source_context', {})


def test_ratio_extraction_rejects_ambiguous_depositary_disclosures(monkeypatch):
    raw = BODY.replace(RATIO.encode(), (RATIO + ' Each ADR represents one ordinary share.').encode())
    policy, deps, _ = fixture(monkeypatch, raw=raw)
    policy['documents']['annual']['inspection_observations'][0]['text_sha256'] = sha256(
        (RATIO + ' Each ADR represents one ordinary share.').encode()).hexdigest()
    peer = get({}, refresh=True, dependencies=deps, ticker='SAP', expected_cik=CIK)
    assert peer['subject'] is None and 'selected_security_scope' not in peer.get('subject_source_context', {})


def test_compact_native_basis_keeps_the_earnings_period_visible(monkeypatch):
    from src.online_peer_valuation_ui import _observations_html

    _, peer, *_ = observed(monkeypatch)
    scope = peer['subject_source_context']['selected_security_scope']
    compact = _observations_html(scope, compact=True)
    assert '2025-01-01 → 2025-12-31' in compact
