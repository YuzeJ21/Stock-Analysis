"""Session-local, readiness-gated orchestration for DCF assumption review."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from typing import Any

from src.valuation import (
    DCFAssumptions,
    DCFResult,
    SensitivityTable,
    ValuationInput,
    build_default_scenarios,
    build_sensitivity_table,
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


def _input_identity(
    valuation_input: ValuationInput,
    parameters: ScenarioParameters,
    *,
    profile_key: str,
) -> str:
    payload = {
        "profile_key": profile_key,
        "valuation_input": valuation_input.to_dict(),
        "scenario_parameters": asdict(parameters),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _changed_assumptions(
    baseline: DCFAssumptions,
    parameters: ScenarioParameters,
) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for field in ("revenue_growth", "fcf_margin", "wacc", "terminal_growth", "forecast_years"):
        prior = getattr(baseline, field)
        current = getattr(parameters, field)
        if prior == current:
            continue
        rows.append(
            {
                "assumption": field,
                "baseline": prior,
                "scenario": current,
                "direction": "higher" if current > prior else "lower",
            }
        )
    return tuple(rows)


def _sensitivity_values(parameters: ScenarioParameters) -> tuple[list[float], list[float]]:
    wacc_values = sorted(
        {
            max(0.05, parameters.wacc - 0.01),
            parameters.wacc,
            min(0.20, parameters.wacc + 0.01),
        }
    )
    max_terminal = min(0.05, min(wacc_values) - 0.005)
    terminal_values = sorted(
        {
            max(-0.02, min(parameters.terminal_growth - 0.01, max_terminal)),
            min(parameters.terminal_growth, max_terminal),
            min(parameters.terminal_growth + 0.01, max_terminal),
        }
    )
    return wacc_values, terminal_values


def render_scenario_lab_result(result: ScenarioLabResult) -> str:
    """Render concise assumption-review output without transaction framing."""

    lines = ["Scenario Lab", f"Status: {result.status}", result.reason]
    if result.status != "calculated" or result.baseline_result is None or result.scenario_result is None:
        lines.append("No scenario valuation is shown while the eligibility gate is closed.")
        return "\n".join(lines)
    lines.extend(
        [
            f"Baseline per-share scenario math: {result.baseline_result.fair_value_per_share:.2f}",
            f"Adjusted per-share scenario math: {result.scenario_result.fair_value_per_share:.2f}",
            f"Sensitivity range: {result.sensitivity_low:.2f} to {result.sensitivity_high:.2f}",
            f"Terminal-value contribution: {result.terminal_value_contribution:.1%}",
        ]
    )
    lines.extend(
        f"Changed {row['assumption']}: {row['baseline']} -> {row['scenario']} ({row['direction']})"
        for row in result.changed_assumptions
    )
    lines.append("Boundary: this is an assumption test using the selected source-backed baseline.")
    return "\n".join(lines)


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
    wacc_values, terminal_growth_values = _sensitivity_values(parameters)
    sensitivity = build_sensitivity_table(
        valuation_input,
        scenario_assumptions,
        wacc_values=wacc_values,
        terminal_growth_values=terminal_growth_values,
    )
    grid_values = [
        value
        for row in sensitivity.fair_value_grid
        for value in row
        if value is not None
    ]
    terminal_contribution = None
    if scenario_result.discounted_terminal_value is not None and scenario_result.enterprise_value:
        terminal_contribution = scenario_result.discounted_terminal_value / scenario_result.enterprise_value
    return ScenarioLabResult(
        status="calculated",
        reason="Scenario math is available for review from the selected source-backed baseline.",
        profile_key=profile_key,
        ticker=valuation_input.ticker,
        input_identity=_input_identity(valuation_input, parameters, profile_key=profile_key),
        baseline_assumptions=baseline_assumptions,
        scenario_parameters=parameters,
        changed_assumptions=_changed_assumptions(baseline_assumptions, parameters),
        baseline_result=baseline_result,
        scenario_result=scenario_result,
        sensitivity_table=sensitivity,
        sensitivity_low=min(grid_values) if grid_values else None,
        sensitivity_high=max(grid_values) if grid_values else None,
        terminal_value_contribution=terminal_contribution,
        source_metadata=source_metadata,
        warnings=tuple(scenario_result.warnings),
    )
