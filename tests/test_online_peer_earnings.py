from copy import deepcopy

import pytest

from test_online_peer_valuation import build, collection, digest


def evidence():
    row = collection()['issuers'][0]
    facts = row['facts']['payload']
    current_row = facts['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]
    current_row['val'] = 1.25
    prior = {**current_row, 'start': '2024-01-01', 'end': '2024-12-31', 'val': 1.0}
    facts['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'].append(prior)
    current = dict(eps=1.25, period_start='2025-01-01', period_end='2025-12-31',
                   accession=current_row['accn'], form=current_row['form'], filed=current_row['filed'])
    return facts, current, prior


def context(facts=None, current=None):
    from src.online_peer_earnings import annual_eps_context
    if facts is None: facts, current, _ = evidence()
    return annual_eps_context(facts, current)


def test_same_filing_comparative_eps_has_hand_checked_growth_and_exact_periods():
    facts, current, _ = evidence(); before = deepcopy((facts, current))
    result = context(facts, current)
    assert result['status'] == 'supported' and result['growth_fraction'] == .25
    assert result['current_eps'] == 1.25 and result['prior_eps'] == 1.0
    assert result['prior_period_start'] == '2024-01-01' and result['prior_period_end'] == '2024-12-31'
    assert result['current_period_start'] == '2025-01-01' and result['current_period_end'] == '2025-12-31'
    assert result['accession'] == current['accession'] and result['basis'] == 'same_annual_filing_reported_comparative_eps'
    assert (facts, current) == before


def test_revised_same_filing_prior_wins_over_older_accession_and_identical_duplicates_are_harmless():
    facts, current, prior = evidence()
    rows = facts['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares']
    rows.extend([{**prior, 'accn': '0000001001-25-000001', 'val': .5}, dict(prior)])
    assert context(facts, current)['growth_fraction'] == .25


@pytest.mark.parametrize('change,reason', [
    ('missing', 'comparative_eps_missing'), ('accession', 'comparative_eps_missing'),
    ('form', 'comparative_eps_metadata_mismatch'), ('filed', 'comparative_eps_metadata_mismatch'),
    ('unit', 'comparative_eps_unit_conflict'), ('conflict', 'comparative_eps_conflict'),
    ('short', 'comparative_eps_period_invalid'), ('gap', 'comparative_eps_missing'),
    ('nonfinite', 'comparative_eps_value_invalid'), ('boolean', 'comparative_eps_value_invalid'),
    ('string', 'comparative_eps_value_invalid'), ('oversize', 'comparative_eps_value_invalid'),
    ('ambiguous_period', 'comparative_eps_conflict'), ('huge_growth', 'comparative_eps_growth_outside_range'),
])
def test_invalid_or_missing_comparatives_never_fall_back_to_another_filing(change, reason):
    facts, current, prior = evidence()
    units = facts['facts']['us-gaap']['EarningsPerShareDiluted']['units']; rows = units['USD/shares']
    if change == 'missing': rows.pop()
    elif change == 'accession': prior['accn'] = '0000001001-25-000001'
    elif change == 'form': prior['form'] = '10-Q'
    elif change == 'filed': prior['filed'] = '2025-02-01'
    elif change == 'unit': units['EUR/shares'] = [dict(prior)]
    elif change == 'conflict': rows.append({**prior, 'val': .9})
    elif change == 'short': prior['start'] = '2024-10-01'
    elif change == 'gap': prior['end'] = '2024-12-30'
    elif change == 'nonfinite': prior['val'] = float('nan')
    elif change == 'boolean': prior['val'] = True
    elif change == 'string': prior['val'] = '1.0'
    elif change == 'oversize': prior['val'] = 10**500
    elif change == 'ambiguous_period': rows.append({**prior, 'start': '2024-01-02'})
    elif change == 'huge_growth': prior['val'] = 1e-12
    result = context(facts, current)
    assert result['status'] == 'withheld' and result['reason'] == reason
    assert result['growth_fraction'] is None


@pytest.mark.parametrize('value', [0, -1])
def test_nonpositive_base_retains_direct_observations_without_a_misleading_percentage(value):
    facts, current, prior = evidence(); prior['val'] = value
    result = context(facts, current)
    assert result['prior_eps'] == value and result['current_eps'] == 1.25
    assert result['growth_fraction'] is None and result['reason'] == 'comparative_eps_base_nonpositive'


def test_negative_current_is_a_reported_decline_not_a_pe_eligibility_decision():
    facts, current, _ = evidence(); current['eps'] = -.25
    assert context(facts, current)['growth_fraction'] == -1.25


@pytest.mark.parametrize('facts,current', [(None, None), ({}, {}), ([], []), ({'facts': []}, {})])
def test_malformed_inputs_return_a_bounded_gap(facts, current):
    from src.online_peer_earnings import annual_eps_context
    result = annual_eps_context(facts, current)
    assert result['status'] == 'withheld' and result['growth_fraction'] is None


def test_missing_growth_keeps_qualified_pe_and_same_reference_membership():
    result = build()
    assert result['status'] == 'research_comparison' and result['peer_count'] == 3
    assert result['peer_median'] == 25 and result['premium_fraction'] == pytest.approx(.2)
    assert result['subject']['earnings_context']['reason'] == 'comparative_eps_missing'


def test_context_is_recomputed_from_bound_facts_and_retained_for_excluded_loss_diagnostics():
    c = collection()
    for row in c['issuers']:
        rows = row['facts']['payload']['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares']
        rows.append({**rows[0], 'start': '2024-01-01', 'end': '2024-12-31', 'val': .8})
        row['facts']['normalized_sha256'] = digest(row['facts']['payload'])
    first = build(c)
    assert first['subject']['earnings_context']['growth_fraction'] == .25
    c['issuers'][1]['facts']['payload']['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]['val'] = -.2
    c['issuers'][1]['facts']['normalized_sha256'] = digest(c['issuers'][1]['facts']['payload'])
    result = build(c)
    assert result['peer_count'] == 2
    diagnostic = result['excluded'][0]['diagnostics']['annual_eps_observation']
    assert diagnostic['earnings_context']['growth_fraction'] == -1.25


@pytest.mark.parametrize('unit', ['USD/shares','EUR/shares'])
def test_same_filing_quarterly_rows_do_not_suppress_the_valid_annual_comparative(unit):
    facts, current, prior = evidence()
    units = facts['facts']['us-gaap']['EarningsPerShareDiluted']['units']
    units.setdefault(unit, []).append({**prior, 'start': '2024-10-01', 'val': .2})
    result = context(facts, current)
    assert result['status'] == 'supported' and result['growth_fraction'] == .25
    assert result['prior_period_start'] == '2024-01-01'


def test_excluded_earnings_context_retains_the_bound_facts_receipt_digest():
    c=collection();row=c['issuers'][1]
    row['facts']['payload']['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]['val']=-1
    diagnostic=build(c)['excluded'][0]['diagnostics']
    assert diagnostic['annual_eps_observation']['facts_sha256']==row['facts']['payload_sha256']
    from src.online_peer_valuation_ui import _diagnostic_html
    html=_diagnostic_html(diagnostic)
    assert 'SEC 原始响应 SHA-256' in html and row['facts']['payload_sha256'] in html
