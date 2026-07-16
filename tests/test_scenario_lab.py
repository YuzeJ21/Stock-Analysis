from dataclasses import asdict

import pytest

from src.scenario_lab import ScenarioParameters, run_scenario_lab, validate_scenario_parameters
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
