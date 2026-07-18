"""In-memory, fail-closed quarterly cash-generation evidence contracts."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date
from typing import Iterable

from src.earnings_nowcast_contract import QuarterlyActual, parse_utc_timestamp


SUPPORTED_COMPONENT_METRICS = frozenset(
    {"operating_income", "cash_from_operations", "capital_expenditures"}
)
_FISCAL_PERIOD_PATTERN = re.compile(r"^\d{4}-Q[1-4]$")


def _required_text(value: object, *, label: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise ValueError(f"{label} is required")
    return cleaned


def _normalized_code(value: object, *, label: str) -> str:
    return _required_text(value, label=label).lower()


def _finite(value: object, *, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be finite")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be finite") from exc
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _positive(value: object, *, label: str) -> float:
    number = _finite(value, label=label)
    if number <= 0:
        raise ValueError(f"{label} must be positive")
    return number


@dataclass(frozen=True)
class QuarterlyBusinessObservation:
    ticker: str
    fiscal_period: str
    period_end_date: str
    metric: str
    value: float
    currency: str
    unit_scale: float
    accounting_basis: str
    duration_basis: str
    source: str
    source_ref: str
    published_at: str
    retrieved_at: str
    q4_evidence_state: str = "not_q4"
    supersedes_source_ref: str | None = None

    def __post_init__(self) -> None:
        ticker = _required_text(self.ticker, label="ticker").upper()
        fiscal_period = _required_text(self.fiscal_period, label="fiscal_period").upper()
        if not _FISCAL_PERIOD_PATTERN.fullmatch(fiscal_period):
            raise ValueError("fiscal_period must use YYYY-Q[1-4]")
        try:
            period_end_date = date.fromisoformat(
                _required_text(self.period_end_date, label="period_end_date")
            ).isoformat()
        except ValueError as exc:
            raise ValueError("period_end_date must use YYYY-MM-DD") from exc
        metric = _normalized_code(self.metric, label="metric")
        if metric not in SUPPORTED_COMPONENT_METRICS:
            raise ValueError("unsupported quarterly business metric")
        q4_state = _normalized_code(self.q4_evidence_state, label="q4_evidence_state")
        if fiscal_period.endswith("-Q4") and q4_state != "explicit_filed_quarter":
            raise ValueError("Q4 requires explicit filed-quarter evidence")
        if not fiscal_period.endswith("-Q4") and q4_state != "not_q4":
            raise ValueError("non-Q4 evidence must use not_q4")

        object.__setattr__(self, "ticker", ticker)
        object.__setattr__(self, "fiscal_period", fiscal_period)
        object.__setattr__(self, "period_end_date", period_end_date)
        object.__setattr__(self, "metric", metric)
        object.__setattr__(self, "value", _finite(self.value, label="value"))
        object.__setattr__(self, "currency", _required_text(self.currency, label="currency").upper())
        object.__setattr__(self, "unit_scale", _positive(self.unit_scale, label="unit_scale"))
        object.__setattr__(
            self,
            "accounting_basis",
            _normalized_code(self.accounting_basis, label="accounting_basis"),
        )
        object.__setattr__(
            self,
            "duration_basis",
            _normalized_code(self.duration_basis, label="duration_basis"),
        )
        object.__setattr__(self, "source", _required_text(self.source, label="source"))
        object.__setattr__(self, "source_ref", _required_text(self.source_ref, label="source_ref"))
        object.__setattr__(
            self,
            "published_at",
            parse_utc_timestamp(self.published_at, label="published_at").isoformat(),
        )
        object.__setattr__(
            self,
            "retrieved_at",
            parse_utc_timestamp(self.retrieved_at, label="retrieved_at").isoformat(),
        )
        object.__setattr__(self, "q4_evidence_state", q4_state)
        supersedes = str(self.supersedes_source_ref or "").strip() or None
        object.__setattr__(self, "supersedes_source_ref", supersedes)


@dataclass(frozen=True)
class QuarterlyBusinessMetricPoint:
    metric: str
    fiscal_period: str
    period_end_date: str
    value: float
    definition: tuple[object, ...]
    source_refs: tuple[str, ...]


@dataclass(frozen=True)
class QuarterlyBusinessDerivation:
    points: tuple[QuarterlyBusinessMetricPoint, ...]
    blockers: tuple[str, ...]
    revision_count: int
    supplied_observation_count: int


def _component_definition(row: QuarterlyBusinessObservation) -> tuple[object, ...]:
    return (
        row.currency,
        row.unit_scale,
        row.accounting_basis,
        row.duration_basis,
        row.period_end_date,
    )


def _same_component(
    left: QuarterlyBusinessObservation,
    right: QuarterlyBusinessObservation,
) -> bool:
    return left.value == right.value and _component_definition(left) == _component_definition(right)


def _resolve_component(
    rows: list[QuarterlyBusinessObservation],
) -> tuple[QuarterlyBusinessObservation | None, int]:
    unique = list({row.source_ref: row for row in rows}.values())
    if len(unique) == 1:
        return unique[0], 0
    if all(_same_component(unique[0], row) for row in unique[1:]):
        return max(unique, key=lambda row: parse_utc_timestamp(row.published_at)), sum(
            bool(row.supersedes_source_ref) for row in unique
        )
    superseded = {row.supersedes_source_ref for row in unique if row.supersedes_source_ref}
    leaves = [row for row in unique if row.source_ref not in superseded]
    if len(leaves) == 1 and leaves[0].supersedes_source_ref:
        return leaves[0], sum(bool(row.supersedes_source_ref) for row in unique)
    return None, 0


def _revenue_definition(row: QuarterlyActual) -> tuple[object, ...]:
    return (
        row.revenue_currency,
        row.revenue_unit_scale,
        row.revenue_basis,
        "three_months",
        row.period_end_date,
    )


def _point(
    *,
    metric: str,
    fiscal_period: str,
    period_end_date: str,
    value: float,
    definition: tuple[object, ...],
    source_refs: tuple[str, ...],
) -> QuarterlyBusinessMetricPoint:
    return QuarterlyBusinessMetricPoint(
        metric=metric,
        fiscal_period=fiscal_period,
        period_end_date=period_end_date,
        value=round(value, 12),
        definition=definition,
        source_refs=source_refs,
    )


def derive_quarterly_business_metrics(
    ticker: str,
    observations: Iterable[QuarterlyBusinessObservation],
    revenue_actuals: Iterable[QuarterlyActual],
    *,
    as_of: str | None = None,
) -> QuarterlyBusinessDerivation:
    """Derive descriptive quarterly metrics without persistence or readiness promotion."""

    symbol = str(ticker or "").strip().upper()
    cutoff = parse_utc_timestamp(as_of).timestamp() if as_of else None
    supplied = [row for row in observations if row.ticker == symbol]
    blockers: list[str] = []
    eligible: list[QuarterlyBusinessObservation] = []
    for row in supplied:
        if cutoff is not None and parse_utc_timestamp(row.published_at).timestamp() > cutoff:
            blockers.append(f"{row.fiscal_period}:{row.metric}:post_cutoff")
        else:
            eligible.append(row)

    grouped: dict[tuple[str, str], list[QuarterlyBusinessObservation]] = {}
    for row in eligible:
        grouped.setdefault((row.fiscal_period, row.metric), []).append(row)

    resolved: dict[tuple[str, str], QuarterlyBusinessObservation] = {}
    revision_count = 0
    for key, rows in grouped.items():
        chosen, revisions = _resolve_component(rows)
        revision_count += revisions
        if chosen is None:
            blockers.append(f"{key[0]}:{key[1]}:ambiguous_revision")
        else:
            resolved[key] = chosen

    revenues: dict[str, QuarterlyActual] = {}
    for row in revenue_actuals:
        if row.ticker != symbol or row.revenue_actual is None:
            continue
        if cutoff is not None and parse_utc_timestamp(row.reported_at).timestamp() > cutoff:
            continue
        existing = revenues.get(row.fiscal_period)
        if existing is None or parse_utc_timestamp(row.reported_at) > parse_utc_timestamp(existing.reported_at):
            revenues[row.fiscal_period] = row

    periods = sorted({period for period, _metric in resolved})
    points: list[QuarterlyBusinessMetricPoint] = []
    for period in periods:
        operating_income = resolved.get((period, "operating_income"))
        cash_from_operations = resolved.get((period, "cash_from_operations"))
        capital_expenditures = resolved.get((period, "capital_expenditures"))
        revenue = revenues.get(period)

        if operating_income is not None:
            if (
                revenue is None
                or revenue.revenue_actual in (None, 0)
                or _component_definition(operating_income) != _revenue_definition(revenue)
            ):
                blockers.append(f"{period}:operating_margin:incompatible_revenue")
            else:
                points.append(
                    _point(
                        metric="operating_margin",
                        fiscal_period=period,
                        period_end_date=operating_income.period_end_date,
                        value=operating_income.value / revenue.revenue_actual,
                        definition=_component_definition(operating_income),
                        source_refs=(operating_income.source_ref, revenue.source_ref),
                    )
                )

        free_cash_flow_value: float | None = None
        free_cash_flow_definition: tuple[object, ...] | None = None
        free_cash_flow_refs: tuple[str, ...] = ()
        if cash_from_operations is not None and capital_expenditures is not None:
            if _component_definition(cash_from_operations) != _component_definition(capital_expenditures):
                blockers.append(f"{period}:free_cash_flow:incompatible_components")
            else:
                free_cash_flow_value = cash_from_operations.value + capital_expenditures.value
                free_cash_flow_definition = _component_definition(cash_from_operations)
                free_cash_flow_refs = (
                    cash_from_operations.source_ref,
                    capital_expenditures.source_ref,
                )
                points.append(
                    _point(
                        metric="free_cash_flow",
                        fiscal_period=period,
                        period_end_date=cash_from_operations.period_end_date,
                        value=free_cash_flow_value,
                        definition=free_cash_flow_definition,
                        source_refs=free_cash_flow_refs,
                    )
                )

        if free_cash_flow_value is not None and free_cash_flow_definition is not None:
            if (
                revenue is None
                or revenue.revenue_actual in (None, 0)
                or free_cash_flow_definition != _revenue_definition(revenue)
            ):
                blockers.append(f"{period}:fcf_margin:incompatible_revenue")
            else:
                points.append(
                    _point(
                        metric="fcf_margin",
                        fiscal_period=period,
                        period_end_date=str(free_cash_flow_definition[-1]),
                        value=free_cash_flow_value / revenue.revenue_actual,
                        definition=free_cash_flow_definition,
                        source_refs=(*free_cash_flow_refs, revenue.source_ref),
                    )
                )

    return QuarterlyBusinessDerivation(
        points=tuple(sorted(points, key=lambda point: (point.fiscal_period, point.metric))),
        blockers=tuple(dict.fromkeys(blockers)),
        revision_count=revision_count,
        supplied_observation_count=len(supplied),
    )
