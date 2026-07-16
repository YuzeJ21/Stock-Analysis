"""Session-local, readiness-gated orchestration for DCF assumption review."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from src.valuation import (
    DCFAssumptions,
    DCFResult,
    SensitivityTable,
    ValuationInput,
    build_default_scenarios,
    calculate_dcf,
)


@dataclass(frozen=True)
class ScenarioParameters:
    revenue_growth: float
    fcf_margin: float
    wacc: float
    terminal_growth: float
    forecast_years: int


@dataclass(frozen=True)
class ScenarioLabResult:
    status: str
    reason: str
    profile_key: str
    ticker: str
    input_identity: str
    baseline_assumptions: DCFAssumptions | None
    scenario_parameters: ScenarioParameters | None
    changed_assumptions: tuple[dict[str, Any], ...]
    baseline_result: DCFResult | None
    scenario_result: DCFResult | None
    sensitivity_table: SensitivityTable | None
    sensitivity_low: float | None
    sensitivity_high: float | None
    terminal_value_contribution: float | None
    source_metadata: tuple[dict[str, Any], ...]
    warnings: tuple[str, ...]


def validate_scenario_parameters(parameters: ScenarioParameters) -> None:
    bounds = {
        "revenue_growth": (-0.50, 0.40),
        "fcf_margin": (-0.50, 0.45),
        "wacc": (0.05, 0.20),
        "terminal_growth": (-0.02, 0.05),
        "forecast_years": (1, 10),
    }
    for field, (lower, upper) in bounds.items():
        value = getattr(parameters, field)
        if value < lower or value > upper:
            raise ValueError(f"{field} must be between {lower} and {upper}")
    if parameters.terminal_growth >= parameters.wacc:
        raise ValueError("terminal_growth must remain below wacc")


def _empty_result(
    *,
    status: str,
    reason: str,
    profile_key: str,
    valuation_input: ValuationInput,
    source_metadata: tuple[dict[str, Any], ...] = (),
) -> ScenarioLabResult:
    return ScenarioLabResult(
        status=status,
        reason=reason,
        profile_key=profile_key,
        ticker=valuation_input.ticker,
        input_identity="",
        baseline_assumptions=None,
        scenario_parameters=None,
        changed_assumptions=(),
        baseline_result=None,
        scenario_result=None,
        sensitivity_table=None,
        sensitivity_low=None,
        sensitivity_high=None,
        terminal_value_contribution=None,
        source_metadata=source_metadata,
        warnings=(),
    )


def _provenance_complete(source_metadata: list[dict[str, Any]]) -> bool:
    return bool(source_metadata) and all(
        str(row.get("source") or "").strip() and str(row.get("source_ref") or "").strip()
        for row in source_metadata
    )


def _like_for_like_baseline(valuation_input: ValuationInput) -> DCFAssumptions | None:
    if valuation_input.revenue is None:
        return None
    margin = valuation_input.fcf_margin
    if margin is None and valuation_input.free_cash_flow is not None and valuation_input.revenue:
        margin = valuation_input.free_cash_flow / valuation_input.revenue
    if margin is None:
        return None
    base = build_default_scenarios(valuation_input)["base"]
    return replace(
        base,
        method_name="revenue_fcf_margin",
        base_free_cash_flow=None,
        fcf_margin=margin,
        observed_fcf_margin=margin,
    )


def run_scenario_lab(
    valuation_input: ValuationInput,
    parameters: ScenarioParameters,
    *,
    profile_key: str,
    dcf_ready: bool,
    asset_type: str,
) -> ScenarioLabResult:
    """Calculate a session-local scenario without mutating source-backed inputs."""

    source_metadata = tuple(dict(row) for row in valuation_input.source_metadata)
    if str(asset_type or "").strip().lower() not in {"company", "operating_company"}:
        return _empty_result(
            status="excluded",
            reason="Scenario Lab is limited to DCF-eligible operating companies.",
            profile_key=profile_key,
            valuation_input=valuation_input,
            source_metadata=source_metadata,
        )
    if not dcf_ready:
        return _empty_result(
            status="blocked",
            reason="DCF readiness must pass for the selected profile before scenario math is available.",
            profile_key=profile_key,
            valuation_input=valuation_input,
            source_metadata=source_metadata,
        )
    if not _provenance_complete(valuation_input.source_metadata):
        return _empty_result(
            status="blocked",
            reason="source provenance is required for the Scenario Lab baseline.",
            profile_key=profile_key,
            valuation_input=valuation_input,
            source_metadata=source_metadata,
        )
    validate_scenario_parameters(parameters)
    baseline_assumptions = _like_for_like_baseline(valuation_input)
    if baseline_assumptions is None or valuation_input.shares_outstanding is None:
        return _empty_result(
            status="blocked",
            reason="A source-backed revenue, FCF margin, and per-share baseline is required.",
            profile_key=profile_key,
            valuation_input=valuation_input,
            source_metadata=source_metadata,
        )
    baseline_result = calculate_dcf(valuation_input, baseline_assumptions)
    if baseline_result.status != "calculated" or baseline_result.fair_value_per_share is None:
        return _empty_result(
            status="blocked",
            reason="The source-backed per-share baseline did not calculate.",
            profile_key=profile_key,
            valuation_input=valuation_input,
            source_metadata=source_metadata,
        )
    scenario_assumptions = replace(
        baseline_assumptions,
        revenue_growth=parameters.revenue_growth,
        observed_revenue_growth=parameters.revenue_growth,
        fcf_margin=parameters.fcf_margin,
        observed_fcf_margin=parameters.fcf_margin,
        wacc=parameters.wacc,
        terminal_growth=parameters.terminal_growth,
        forecast_years=parameters.forecast_years,
    )
    scenario_result = calculate_dcf(valuation_input, scenario_assumptions)
    if scenario_result.status != "calculated" or scenario_result.fair_value_per_share is None:
        return _empty_result(
            status="invalid",
            reason="The selected assumptions did not produce valid per-share scenario math.",
            profile_key=profile_key,
            valuation_input=valuation_input,
            source_metadata=source_metadata,
        )
    return ScenarioLabResult(
        status="calculated",
        reason="Scenario math is available for review from the selected source-backed baseline.",
        profile_key=profile_key,
        ticker=valuation_input.ticker,
        input_identity="",
        baseline_assumptions=baseline_assumptions,
        scenario_parameters=parameters,
        changed_assumptions=(),
        baseline_result=baseline_result,
        scenario_result=scenario_result,
        sensitivity_table=None,
        sensitivity_low=None,
        sensitivity_high=None,
        terminal_value_contribution=None,
        source_metadata=source_metadata,
        warnings=tuple(scenario_result.warnings),
    )
