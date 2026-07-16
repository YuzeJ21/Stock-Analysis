from dataclasses import asdict

import pytest

from src.scenario_lab import (
    ScenarioParameters,
    default_scenario_parameters,
    render_scenario_lab_result,
    run_scenario_lab,
    validate_scenario_parameters,
)
from src.valuation import ValuationInput


def _input(**overrides) -> ValuationInput:
    values = {
        "ticker": "SYN1",
        "current_price": 100.0,
        "revenue": 1_000.0,
        "revenue_growth": 0.10,
        "free_cash_flow": 200.0,
        "fcf_margin": 0.20,
        "shares_outstanding": 10.0,
        "cash": 100.0,
        "debt": 50.0,
        "source_metadata": [
            {
                "source": "synthetic_fixture",
                "source_ref": "fixture:SYN1:2026Q2",
                "as_of_date": "2026-06-30",
            }
        ],
    }
    values.update(overrides)
    return ValuationInput(**values)


def _parameters(**overrides) -> ScenarioParameters:
    values = {
        "revenue_growth": 0.12,
        "fcf_margin": 0.22,
        "wacc": 0.09,
        "terminal_growth": 0.03,
        "forecast_years": 5,
    }
    values.update(overrides)
    return ScenarioParameters(**values)


def test_scenario_lab_blocks_when_selected_ticker_is_not_dcf_ready():
    result = run_scenario_lab(
        _input(),
        _parameters(),
        profile_key="demo",
        dcf_ready=False,
        asset_type="company",
    )

    assert result.status == "blocked"
    assert "DCF readiness" in result.reason
    assert result.baseline_result is None
    assert result.scenario_result is None


def test_scenario_lab_excludes_non_company_assets():
    result = run_scenario_lab(
        _input(ticker="SYNETF"),
        _parameters(),
        profile_key="demo",
        dcf_ready=True,
        asset_type="etf",
    )

    assert result.status == "excluded"
    assert "operating companies" in result.reason
    assert result.scenario_result is None


def test_scenario_lab_blocks_without_source_provenance_or_per_share_inputs():
    missing_source = run_scenario_lab(
        _input(source_metadata=[]),
        _parameters(),
        profile_key="demo",
        dcf_ready=True,
        asset_type="company",
    )
    missing_shares = run_scenario_lab(
        _input(shares_outstanding=None),
        _parameters(),
        profile_key="demo",
        dcf_ready=True,
        asset_type="company",
    )

    assert missing_source.status == "blocked"
    assert "source provenance" in missing_source.reason
    assert missing_shares.status == "blocked"
    assert "per-share" in missing_shares.reason


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("revenue_growth", -0.51),
        ("revenue_growth", 0.41),
        ("fcf_margin", -0.51),
        ("fcf_margin", 0.46),
        ("wacc", 0.049),
        ("wacc", 0.201),
        ("terminal_growth", -0.021),
        ("terminal_growth", 0.051),
        ("forecast_years", 0),
        ("forecast_years", 11),
    ],
)
def test_scenario_parameters_enforce_conservative_bounds(field, value):
    with pytest.raises(ValueError, match=field):
        validate_scenario_parameters(_parameters(**{field: value}))


def test_terminal_growth_must_remain_below_wacc():
    with pytest.raises(ValueError, match="terminal_growth must remain below wacc"):
        validate_scenario_parameters(_parameters(wacc=0.05, terminal_growth=0.05))


def test_calculated_scenario_does_not_mutate_source_backed_input():
    valuation_input = _input()
    before = asdict(valuation_input)

    result = run_scenario_lab(
        valuation_input,
        _parameters(),
        profile_key="demo",
        dcf_ready=True,
        asset_type="company",
    )

    assert result.status == "calculated"
    assert result.baseline_result is not None
    assert result.scenario_result is not None
    assert result.scenario_result.fair_value_per_share is not None
    assert asdict(valuation_input) == before


def test_scenario_input_identity_is_stable_and_changes_with_profile_source_or_parameters():
    first = run_scenario_lab(
        _input(), _parameters(), profile_key="demo", dcf_ready=True, asset_type="company"
    )
    repeat = run_scenario_lab(
        _input(), _parameters(), profile_key="demo", dcf_ready=True, asset_type="company"
    )
    other_profile = run_scenario_lab(
        _input(), _parameters(), profile_key="local", dcf_ready=True, asset_type="company"
    )
    other_source = run_scenario_lab(
        _input(source_metadata=[{"source": "fixture", "source_ref": "fixture:changed"}]),
        _parameters(),
        profile_key="demo",
        dcf_ready=True,
        asset_type="company",
    )
    other_parameters = run_scenario_lab(
        _input(), _parameters(wacc=0.10), profile_key="demo", dcf_ready=True, asset_type="company"
    )

    assert first.input_identity == repeat.input_identity
    assert len(first.input_identity) == 64
    assert len({first.input_identity, other_profile.input_identity, other_source.input_identity, other_parameters.input_identity}) == 4


def test_scenario_result_lists_only_changed_assumptions_with_direction():
    result = run_scenario_lab(
        _input(), _parameters(), profile_key="demo", dcf_ready=True, asset_type="company"
    )

    changes = {row["assumption"]: row for row in result.changed_assumptions}

    assert set(changes) == {"revenue_growth", "fcf_margin"}
    assert changes["revenue_growth"] == {
        "assumption": "revenue_growth",
        "baseline": 0.10,
        "scenario": 0.12,
        "direction": "higher",
    }
    assert changes["fcf_margin"]["direction"] == "higher"


def test_scenario_result_includes_sensitivity_range_and_terminal_value_contribution():
    result = run_scenario_lab(
        _input(), _parameters(), profile_key="demo", dcf_ready=True, asset_type="company"
    )

    assert result.sensitivity_table is not None
    assert result.sensitivity_table.status == "calculated"
    assert result.sensitivity_low is not None
    assert result.sensitivity_high is not None
    assert result.sensitivity_low < result.scenario_result.fair_value_per_share < result.sensitivity_high
    assert result.terminal_value_contribution is not None
    assert 0 < result.terminal_value_contribution < 1

    grid = result.sensitivity_table.fair_value_grid
    assert grid[0][0] < grid[0][-1]
    assert grid[0][0] > grid[-1][0]


def test_rendered_scenario_result_is_assumption_review_not_transaction_language():
    result = run_scenario_lab(
        _input(), _parameters(), profile_key="demo", dcf_ready=True, asset_type="company"
    )

    rendered = render_scenario_lab_result(result).lower()

    assert "scenario lab" in rendered
    assert "assumption test" in rendered
    assert "sensitivity range" in rendered
    assert "terminal-value contribution" in rendered
    assert "revenue_growth" in rendered
    for prohibited in ("buy", "sell", "hold", "order", "target price", "position size", "recommendation"):
        assert prohibited not in rendered


def test_default_scenario_parameters_use_source_backed_growth_and_margin():
    parameters = default_scenario_parameters(_input())

    assert parameters == ScenarioParameters(
        revenue_growth=0.10,
        fcf_margin=0.20,
        wacc=0.09,
        terminal_growth=0.03,
        forecast_years=5,
    )
