"""Fail-closed preparation of current, session-local Scenario Lab state."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

from src.scenario_lab import (
    ScenarioLabResult,
    ScenarioParameters,
    default_scenario_parameters,
    run_scenario_lab,
    validate_scenario_parameters,
)
from src.valuation import ValuationInput


_SCENARIO_FIELDS = (
    "revenue_growth",
    "fcf_margin",
    "wacc",
    "terminal_growth",
    "forecast_years",
)
_FALLBACK_PARAMETERS = ScenarioParameters(0.08, 0.15, 0.09, 0.03, 5)
_SOURCE_BASELINE_BLOCKER = (
    "A source-backed revenue growth and FCF margin baseline is required before "
    "Scenario Lab session values can be reviewed."
)


@dataclass(frozen=True)
class ScenarioLabSessionSnapshot:
    state: str
    blocker: str
    parameters: ScenarioParameters
    result: ScenarioLabResult | None
    widget_keys: tuple[tuple[str, str], ...]


def scenario_lab_input_from_report(report_payload: dict[str, object]) -> ValuationInput:
    """Build a scenario input from the selected report without inventing fields."""

    price = report_payload.get("price_snapshot", {}) or {}
    financials = report_payload.get("financial_summary", {}) or {}
    valuation = report_payload.get("valuation_snapshot", {}) or {}
    return ValuationInput(
        ticker=str(report_payload.get("ticker") or "").strip().upper(),
        current_price=price.get("price"),
        revenue=financials.get("revenue"),
        revenue_growth=financials.get("revenue_growth"),
        free_cash_flow=financials.get("free_cash_flow"),
        fcf_margin=financials.get("fcf_margin"),
        operating_margin=financials.get("operating_margin"),
        profit_margin=financials.get("profit_margin"),
        eps=financials.get("eps"),
        ebitda=financials.get("ebitda"),
        shares_outstanding=financials.get("shares_outstanding"),
        cash=financials.get("cash"),
        debt=financials.get("debt"),
        net_debt=financials.get("net_debt"),
        market_cap=financials.get("market_cap"),
        trailing_pe=financials.get("trailing_pe"),
        forward_pe=financials.get("forward_pe"),
        price_to_book=financials.get("price_to_book"),
        source_metadata=[dict(row) for row in (valuation.get("source_metadata") or [])],
        screener_context=dict(report_payload.get("screener_context", {}) or {}),
    )


def scenario_lab_widget_keys(profile_key: str, ticker: str) -> dict[str, str]:
    """Return deterministic keys that isolate controls by profile and ticker."""

    profile_scope = str(profile_key or "").strip() or "unscoped-profile"
    ticker_scope = str(ticker or "").strip().upper() or "UNSCOPED-TICKER"
    return {
        field: f"scenario-lab:{profile_scope}:{ticker_scope}:{field}"
        for field in _SCENARIO_FIELDS
    }


def _finite_number(value: object, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def _parameters_from_state(
    state: Mapping[str, object],
    *,
    defaults: ScenarioParameters,
    widget_keys: Mapping[str, str],
) -> ScenarioParameters:
    values: dict[str, float | int] = {}
    for field in _SCENARIO_FIELDS:
        raw = state.get(widget_keys[field], getattr(defaults, field))
        number = _finite_number(raw, field)
        if field == "forecast_years":
            if not number.is_integer():
                raise ValueError("forecast_years must be a whole number")
            values[field] = int(number)
        else:
            values[field] = number
    parameters = ScenarioParameters(**values)
    validate_scenario_parameters(parameters)
    return parameters


def scenario_lab_parameters_from_state(
    report_payload: dict[str, object],
    state: Mapping[str, object],
    *,
    profile_key: str,
) -> ScenarioParameters:
    """Read and validate only the current profile/ticker's session controls."""

    valuation_input = scenario_lab_input_from_report(report_payload)
    defaults = default_scenario_parameters(valuation_input)
    widget_keys = scenario_lab_widget_keys(profile_key, valuation_input.ticker)
    return _parameters_from_state(state, defaults=defaults, widget_keys=widget_keys)


def run_scenario_lab_from_state(
    report_payload: dict[str, object],
    state: Mapping[str, object],
    *,
    profile_key: str,
    dcf_ready: bool,
    asset_type: str,
) -> ScenarioLabSessionSnapshot:
    """Prepare one current Scenario Lab result without caching or state repair."""

    valuation_input = scenario_lab_input_from_report(report_payload)
    widget_keys = scenario_lab_widget_keys(profile_key, valuation_input.ticker)
    frozen_widget_keys = tuple((field, widget_keys[field]) for field in _SCENARIO_FIELDS)
    try:
        defaults = default_scenario_parameters(valuation_input)
    except (ArithmeticError, TypeError, ValueError):
        return ScenarioLabSessionSnapshot(
            state="blocked",
            blocker=_SOURCE_BASELINE_BLOCKER,
            parameters=_FALLBACK_PARAMETERS,
            result=None,
            widget_keys=frozen_widget_keys,
        )

    try:
        parameters = _parameters_from_state(
            state,
            defaults=defaults,
            widget_keys=widget_keys,
        )
    except (ArithmeticError, TypeError, ValueError) as exc:
        detail = str(exc).replace("_", " ").strip()
        return ScenarioLabSessionSnapshot(
            state="withheld",
            blocker=f"Invalid Scenario Lab session values: {detail}.",
            parameters=defaults,
            result=None,
            widget_keys=frozen_widget_keys,
        )

    result = run_scenario_lab(
        valuation_input,
        parameters,
        profile_key=profile_key,
        dcf_ready=dcf_ready,
        asset_type=asset_type,
    )
    return ScenarioLabSessionSnapshot(
        state=result.status,
        blocker=result.reason,
        parameters=parameters,
        result=result,
        widget_keys=frozen_widget_keys,
    )
