"""Fail-closed quarterly business trend packets for Personal Research Mode."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.earnings_nowcast_contract import (
    QuarterlyActual,
    eps_split_basis_verified,
    parse_utc_timestamp,
)
from src.quarterly_cash_generation import (
    QuarterlyBusinessMetricPoint,
    QuarterlyBusinessObservation,
    derive_quarterly_business_metrics,
)


@dataclass(frozen=True)
class QuarterlyMetricTrend:
    metric: str
    status: str
    latest_value: float | None
    latest_fiscal_period: str
    latest_source_ref: str
    sequential_change_pct: float | None
    year_over_year_change_pct: float | None
    available_periods: tuple[str, ...]
    missing_comparisons: tuple[str, ...]
    withheld_reason: str


@dataclass(frozen=True)
class QuarterlyTrendPacket:
    ticker: str
    status: str
    latest_fiscal_period: str
    available_periods: tuple[str, ...]
    revenue: QuarterlyMetricTrend
    eps: QuarterlyMetricTrend
    operating_margin: QuarterlyMetricTrend
    free_cash_flow: QuarterlyMetricTrend
    fcf_margin: QuarterlyMetricTrend
    withheld_metrics: tuple[str, ...]
    ambiguous_periods: tuple[str, ...]
    revision_count: int
    source_confidence: str
    q4_policy: str
    message: str


@dataclass(frozen=True)
class QuarterlyActualLoadResult:
    actuals: tuple[QuarterlyActual, ...]
    accepted_count: int
    rejected_count: int
    rejected_rows: tuple[dict[str, object], ...]


def _optional_float(value: object) -> float | None:
    cleaned = str(value or "").strip()
    return float(cleaned) if cleaned else None


def load_quarterly_actuals_csv(path: Path | str) -> QuarterlyActualLoadResult:
    """Load explicit quarterly actual rows without modifying or repairing the source."""

    source = Path(path)
    if not source.is_file():
        return QuarterlyActualLoadResult((), 0, 0, ())
    accepted: list[QuarterlyActual] = []
    rejected: list[dict[str, object]] = []
    with source.open(newline="", encoding="utf-8") as handle:
        for row_number, row in enumerate(csv.DictReader(handle), start=2):
            try:
                accepted.append(
                    QuarterlyActual(
                        ticker=row.get("ticker", ""),
                        fiscal_period=row.get("fiscal_period", ""),
                        period_end_date=row.get("period_end_date", ""),
                        reported_at=row.get("reported_at", ""),
                        revenue_actual=_optional_float(row.get("revenue_actual")),
                        eps_actual=_optional_float(row.get("eps_actual")),
                        source=row.get("source", ""),
                        source_ref=row.get("source_ref", ""),
                        retrieved_at=row.get("retrieved_at", ""),
                        revenue_currency=row.get("revenue_currency", ""),
                        revenue_unit_scale=_optional_float(row.get("revenue_unit_scale")),
                        revenue_basis=row.get("revenue_basis", ""),
                        eps_currency=row.get("eps_currency", ""),
                        eps_basis=row.get("eps_basis", ""),
                        eps_share_basis=row.get("eps_share_basis", ""),
                        eps_operations_basis=row.get("eps_operations_basis", ""),
                        split_adjustment_basis=row.get("split_adjustment_basis", ""),
                        supersedes_source_ref=row.get("supersedes_source_ref") or None,
                    )
                )
            except (TypeError, ValueError) as exc:
                rejected.append({"row_number": row_number, "reason": str(exc)})
    return QuarterlyActualLoadResult(
        actuals=tuple(accepted),
        accepted_count=len(accepted),
        rejected_count=len(rejected),
        rejected_rows=tuple(rejected),
    )


def _period_key(period: str) -> tuple[int, int]:
    return int(period[:4]), int(period[-1])


def _previous_period(period: str) -> str:
    year, quarter = _period_key(period)
    return f"{year - 1}-Q4" if quarter == 1 else f"{year}-Q{quarter - 1}"


def _prior_year_period(period: str) -> str:
    year, quarter = _period_key(period)
    return f"{year - 1}-Q{quarter}"


def _latest_timestamp(rows: Iterable[QuarterlyActual]) -> QuarterlyActual:
    return max(rows, key=lambda row: parse_utc_timestamp(row.reported_at).timestamp())


def _same_observation(left: QuarterlyActual, right: QuarterlyActual) -> bool:
    fields = (
        "revenue_actual",
        "eps_actual",
        "revenue_currency",
        "revenue_unit_scale",
        "revenue_basis",
        "eps_currency",
        "eps_basis",
        "eps_share_basis",
        "eps_operations_basis",
        "split_adjustment_basis",
    )
    return all(getattr(left, field) == getattr(right, field) for field in fields)


def _resolve_period(rows: list[QuarterlyActual]) -> tuple[QuarterlyActual | None, int]:
    unique_by_ref = {row.source_ref: row for row in rows}
    unique = list(unique_by_ref.values())
    if len(unique) == 1:
        return unique[0], 0
    if all(_same_observation(unique[0], row) for row in unique[1:]):
        return _latest_timestamp(unique), sum(bool(row.supersedes_source_ref) for row in unique)
    superseded_refs = {row.supersedes_source_ref for row in unique if row.supersedes_source_ref}
    leaves = [row for row in unique if row.source_ref not in superseded_refs]
    if len(leaves) == 1 and leaves[0].supersedes_source_ref:
        return leaves[0], sum(bool(row.supersedes_source_ref) for row in unique)
    return None, 0


def _revenue_definition(row: QuarterlyActual) -> tuple[object, ...]:
    return row.revenue_currency, row.revenue_unit_scale, row.revenue_basis


def _eps_definition(row: QuarterlyActual) -> tuple[object, ...]:
    return (
        row.eps_currency,
        row.eps_basis,
        row.eps_share_basis,
        row.eps_operations_basis,
        row.split_adjustment_basis,
    )


def _pct_change(current: float | None, prior: float | None) -> float | None:
    if current is None or prior is None or prior == 0:
        return None
    return round((current - prior) / abs(prior) * 100.0, 6)


def _blocked_metric(metric: str, reason: str) -> QuarterlyMetricTrend:
    return QuarterlyMetricTrend(metric, "blocked", None, "", "", None, None, (), (), reason)


def _withheld_metric(metric: str) -> QuarterlyMetricTrend:
    return QuarterlyMetricTrend(
        metric,
        "withheld",
        None,
        "",
        "",
        None,
        None,
        (),
        (),
        (
            "A reviewed explicit versioned quarterly source contract and source adapter "
            "are required before this metric can be shown."
        ),
    )


def _metric_trend(
    metric: str,
    rows_by_period: dict[str, QuarterlyActual],
    *,
    value_field: str,
    definition,
) -> QuarterlyMetricTrend:
    unverified_eps_periods = tuple(
        sorted(
            (
                period
                for period, row in rows_by_period.items()
                if metric == "eps"
                and row.eps_actual is not None
                and not eps_split_basis_verified(row.split_adjustment_basis)
            ),
            key=_period_key,
        )
    )
    available = {
        period: row
        for period, row in rows_by_period.items()
        if getattr(row, value_field) is not None
        and not (
            metric == "eps"
            and not eps_split_basis_verified(row.split_adjustment_basis)
        )
    }
    if not available:
        if unverified_eps_periods:
            return _blocked_metric(
                metric,
                "Quarterly EPS split basis is unverified; explicit primary-source proof is required.",
            )
        return _blocked_metric(metric, f"No explicit source-backed quarterly {metric} observation is available.")
    periods = tuple(sorted(available, key=_period_key))
    latest_period = periods[-1]
    latest = available[latest_period]
    latest_value = getattr(latest, value_field)
    missing: list[str] = []
    withheld: list[str] = (
        [f"unverified EPS split basis withheld for {', '.join(unverified_eps_periods)}"]
        if unverified_eps_periods
        else []
    )

    previous_period = _previous_period(latest_period)
    previous = available.get(previous_period)
    sequential: float | None = None
    if previous is None:
        missing.append("previous quarter unavailable")
    elif definition(previous) != definition(latest):
        withheld.append("sequential comparison uses incompatible metric definitions")
    else:
        sequential = _pct_change(latest_value, getattr(previous, value_field))
        if sequential is None:
            withheld.append("sequential comparison denominator is unavailable or zero")

    prior_year_period = _prior_year_period(latest_period)
    prior_year = available.get(prior_year_period)
    year_over_year: float | None = None
    if prior_year is None:
        missing.append("prior-year quarter unavailable")
    elif definition(prior_year) != definition(latest):
        withheld.append("year-over-year comparison uses incompatible metric definitions")
    else:
        year_over_year = _pct_change(latest_value, getattr(prior_year, value_field))
        if year_over_year is None:
            withheld.append("year-over-year comparison denominator is unavailable or zero")

    status = (
        "ready"
        if sequential is not None and year_over_year is not None and not unverified_eps_periods
        else "partial"
    )
    return QuarterlyMetricTrend(
        metric=metric,
        status=status,
        latest_value=latest_value,
        latest_fiscal_period=latest_period,
        latest_source_ref=latest.source_ref,
        sequential_change_pct=sequential,
        year_over_year_change_pct=year_over_year,
        available_periods=periods,
        missing_comparisons=tuple(missing),
        withheld_reason="; ".join(withheld),
    )


def _point_metric_trend(
    metric: str,
    points: Iterable[QuarterlyBusinessMetricPoint],
    *,
    blockers: tuple[str, ...],
) -> QuarterlyMetricTrend:
    available = {point.fiscal_period: point for point in points if point.metric == metric}
    if not available:
        tokens = {
            "operating_margin": ("operating_income", "operating_margin"),
            "free_cash_flow": ("cash_from_operations", "capital_expenditures", "free_cash_flow"),
            "fcf_margin": (
                "cash_from_operations",
                "capital_expenditures",
                "free_cash_flow",
                "fcf_margin",
            ),
        }[metric]
        matching = tuple(
            blocker.replace("_", " ")
            for blocker in blockers
            if any(token in blocker for token in tokens)
        )
        reason = "; ".join(matching) or "Required quarterly components are unavailable or incompatible."
        return _blocked_metric(metric, reason)

    periods = tuple(sorted(available, key=_period_key))
    latest_period = periods[-1]
    latest = available[latest_period]
    missing: list[str] = []
    withheld: list[str] = []

    previous_period = _previous_period(latest_period)
    previous = available.get(previous_period)
    sequential: float | None = None
    if previous is None:
        missing.append("previous quarter unavailable")
    elif previous.definition != latest.definition:
        withheld.append("sequential comparison uses incompatible metric definitions")
    else:
        sequential = _pct_change(latest.value, previous.value)
        if sequential is None:
            withheld.append("sequential comparison denominator is unavailable or zero")

    prior_year_period = _prior_year_period(latest_period)
    prior_year = available.get(prior_year_period)
    year_over_year: float | None = None
    if prior_year is None:
        missing.append("prior-year quarter unavailable")
    elif prior_year.definition != latest.definition:
        withheld.append("year-over-year comparison uses incompatible metric definitions")
    else:
        year_over_year = _pct_change(latest.value, prior_year.value)
        if year_over_year is None:
            withheld.append("year-over-year comparison denominator is unavailable or zero")

    return QuarterlyMetricTrend(
        metric=metric,
        status="ready" if sequential is not None and year_over_year is not None else "partial",
        latest_value=latest.value,
        latest_fiscal_period=latest_period,
        latest_source_ref=";".join(latest.source_refs),
        sequential_change_pct=sequential,
        year_over_year_change_pct=year_over_year,
        available_periods=periods,
        missing_comparisons=tuple(missing),
        withheld_reason="; ".join(withheld),
    )


def _supplemental_trends(
    ticker: str,
    observations: tuple[QuarterlyBusinessObservation, ...],
    revenues: Iterable[QuarterlyActual],
    *,
    as_of: str | None,
) -> tuple[QuarterlyMetricTrend, QuarterlyMetricTrend, QuarterlyMetricTrend, int]:
    if not observations:
        return (
            _withheld_metric("operating_margin"),
            _withheld_metric("free_cash_flow"),
            _withheld_metric("fcf_margin"),
            0,
        )
    derived = derive_quarterly_business_metrics(
        ticker,
        observations,
        revenues,
        as_of=as_of,
    )
    return (
        _point_metric_trend("operating_margin", derived.points, blockers=derived.blockers),
        _point_metric_trend("free_cash_flow", derived.points, blockers=derived.blockers),
        _point_metric_trend("fcf_margin", derived.points, blockers=derived.blockers),
        derived.revision_count,
    )


def _withheld_metric_names(*trends: QuarterlyMetricTrend) -> tuple[str, ...]:
    return tuple(trend.metric for trend in trends if trend.status in {"blocked", "withheld"})


def build_quarterly_trend_packet(
    ticker: str,
    actuals: Iterable[QuarterlyActual],
    *,
    as_of: str | None = None,
    business_observations: Iterable[QuarterlyBusinessObservation] = (),
) -> QuarterlyTrendPacket:
    symbol = str(ticker or "").strip().upper()
    cutoff = parse_utc_timestamp(as_of).timestamp() if as_of else None
    matching = [
        row
        for row in actuals
        if row.ticker == symbol
        and (cutoff is None or parse_utc_timestamp(row.reported_at).timestamp() <= cutoff)
    ]
    grouped: dict[str, list[QuarterlyActual]] = {}
    for row in matching:
        grouped.setdefault(row.fiscal_period, []).append(row)

    resolved: dict[str, QuarterlyActual] = {}
    ambiguous: list[str] = []
    revision_count = 0
    for period, rows in grouped.items():
        chosen, revisions = _resolve_period(rows)
        revision_count += revisions
        if chosen is None:
            ambiguous.append(period)
        else:
            resolved[period] = chosen

    supplemental_input = tuple(business_observations)
    operating_margin, free_cash_flow, fcf_margin, supplemental_revisions = _supplemental_trends(
        symbol,
        supplemental_input,
        resolved.values(),
        as_of=as_of,
    )
    revision_count += supplemental_revisions

    if not resolved:
        reason = (
            "Quarterly observations are ambiguous because explicit revision lineage is missing."
            if ambiguous
            else "No source-backed quarterly actual is available by the review cutoff."
        )
        metric_reason = "Quarterly actual is ambiguous; explicit revision lineage is required." if ambiguous else reason
        return QuarterlyTrendPacket(
            ticker=symbol,
            status="blocked",
            latest_fiscal_period="",
            available_periods=(),
            revenue=_blocked_metric("revenue", metric_reason),
            eps=_blocked_metric("eps", metric_reason),
            operating_margin=operating_margin,
            free_cash_flow=free_cash_flow,
            fcf_margin=fcf_margin,
            withheld_metrics=_withheld_metric_names(operating_margin, free_cash_flow, fcf_margin),
            ambiguous_periods=tuple(sorted(ambiguous, key=_period_key)),
            revision_count=revision_count,
            source_confidence=(
                "source_backed"
                if any(
                    trend.latest_value is not None
                    for trend in (operating_margin, free_cash_flow, fcf_margin)
                )
                else "withheld"
            ),
            q4_policy="explicit_filed_quarter_only",
            message=(
                f"{reason} Independent quarterly cash-generation evidence remains separately reviewable."
                if any(
                    trend.latest_value is not None
                    for trend in (operating_margin, free_cash_flow, fcf_margin)
                )
                else reason
            ),
        )

    periods = tuple(sorted(resolved, key=_period_key))
    revenue = _metric_trend("revenue", resolved, value_field="revenue_actual", definition=_revenue_definition)
    eps = _metric_trend("eps", resolved, value_field="eps_actual", definition=_eps_definition)
    status = "ready" if revenue.status == "ready" and eps.status == "ready" else "partial"
    return QuarterlyTrendPacket(
        ticker=symbol,
        status=status,
        latest_fiscal_period=periods[-1],
        available_periods=periods,
        revenue=revenue,
        eps=eps,
        operating_margin=operating_margin,
        free_cash_flow=free_cash_flow,
        fcf_margin=fcf_margin,
        withheld_metrics=_withheld_metric_names(operating_margin, free_cash_flow, fcf_margin),
        ambiguous_periods=tuple(sorted(ambiguous, key=_period_key)),
        revision_count=revision_count,
        source_confidence="source_backed",
        q4_policy="explicit_filed_quarter_only",
        message=(
            "Comparable quarterly Revenue and EPS trends are available."
            if status == "ready"
            else "Quarterly evidence is partial; unavailable comparisons remain withheld."
        ),
    )


def _display_change(value: float | None) -> str:
    return f"{value:+.1f}%" if value is not None else "withheld"


def _display_value(trend: QuarterlyMetricTrend) -> object:
    if trend.latest_value is None:
        return "withheld"
    if trend.metric in {"operating_margin", "fcf_margin"}:
        return f"{trend.latest_value * 100.0:.1f}%"
    return trend.latest_value


def quarterly_trend_rows(packet: QuarterlyTrendPacket) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for label, trend in (
        ("Revenue", packet.revenue),
        ("EPS", packet.eps),
        ("Operating margin", packet.operating_margin),
        ("Free cash flow", packet.free_cash_flow),
        ("FCF margin", packet.fcf_margin),
    ):
        boundary_parts = list(trend.missing_comparisons)
        if trend.withheld_reason:
            boundary_parts.append(trend.withheld_reason)
        rows.append(
            {
                "Metric": label,
                "State": trend.status,
                "Latest period": trend.latest_fiscal_period or "unavailable",
                "Latest value": _display_value(trend),
                "Sequential": _display_change(trend.sequential_change_pct),
                "Year over year": _display_change(trend.year_over_year_change_pct),
                "Source reference": trend.latest_source_ref or "unavailable",
                "Boundary": "; ".join(boundary_parts) or "Comparable source-backed periods available.",
            }
        )
    return rows
