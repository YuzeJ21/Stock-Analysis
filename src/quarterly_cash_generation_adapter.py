"""Read-only acceptance contract for one-company cash-generation adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from src.commercial_source_rights import SourceRights, commercial_eligibility
from src.earnings_nowcast_contract import QuarterlyActual
from src.quarterly_cash_generation import (
    QuarterlyBusinessObservation,
    derive_quarterly_business_metrics,
)


REQUIRED_SOURCE_FIELDS = frozenset(
    {"operating_income", "cash_from_operations", "capital_expenditures"}
)
REQUIRED_DERIVED_METRICS = frozenset(
    {"operating_margin", "free_cash_flow", "fcf_margin"}
)


@dataclass(frozen=True)
class QuarterlyAdapterAcceptance:
    ticker: str
    source_id: str
    status: str
    blockers: tuple[str, ...]
    accepted_observation_count: int
    reviewed_metrics: tuple[str, ...]
    derived_point_count: int
    explicit_q4_periods: tuple[str, ...]
    rights_status: str
    production_activation: bool = False
    readiness_promotions: tuple[str, ...] = ()


def assess_quarterly_cash_generation_adapter(
    ticker: str,
    source_id: str,
    observations: Iterable[QuarterlyBusinessObservation],
    revenue_actuals: Iterable[QuarterlyActual],
    *,
    rights_registry: Mapping[str, SourceRights],
    as_of: str | None = None,
) -> QuarterlyAdapterAcceptance:
    """Assess an in-memory candidate batch without activating or persisting it."""

    symbol = str(ticker or "").strip().upper()
    normalized_source = str(source_id or "").strip()
    supplied = tuple(observations)
    revenues = tuple(revenue_actuals)
    blockers: list[str] = []
    if not symbol:
        blockers.append("ticker_required")
    if not normalized_source:
        blockers.append("source_id_required")
    if not supplied:
        blockers.append("observations_required")
    for other in sorted({row.ticker for row in supplied if row.ticker != symbol}):
        blockers.append(f"mixed_ticker:{other}")
    for other in sorted({row.source for row in supplied if row.source != normalized_source}):
        blockers.append(f"source_mismatch:{other}")

    decision = commercial_eligibility(rights_registry, normalized_source)
    if not decision.allowed:
        blockers.append(f"source_rights:{decision.status}")
    rights = rights_registry.get(normalized_source)
    if rights is not None:
        missing_fields = sorted(REQUIRED_SOURCE_FIELDS - set(rights.supported_fields))
        if missing_fields:
            blockers.append(f"source_fields_missing:{','.join(missing_fields)}")

    candidate_rows = tuple(
        row
        for row in supplied
        if row.ticker == symbol and row.source == normalized_source
    )
    metrics_by_period: dict[str, set[str]] = {}
    for row in candidate_rows:
        metrics_by_period.setdefault(row.fiscal_period, set()).add(row.metric)
    for period in sorted(metrics_by_period):
        for metric in sorted(REQUIRED_SOURCE_FIELDS - metrics_by_period[period]):
            blockers.append(f"{period}:missing_component:{metric}")

    derivation = derive_quarterly_business_metrics(
        symbol,
        candidate_rows,
        revenues,
        as_of=as_of,
    )
    blockers.extend(derivation.blockers)
    points_by_period: dict[str, set[str]] = {}
    for point in derivation.points:
        points_by_period.setdefault(point.fiscal_period, set()).add(point.metric)
    complete_periods = tuple(
        sorted(
            period
            for period, metrics in points_by_period.items()
            if REQUIRED_DERIVED_METRICS.issubset(metrics)
        )
    )
    if not complete_periods:
        blockers.append("complete_derived_period_required")

    stable_blockers = tuple(dict.fromkeys(blockers))
    reviewed_metrics = tuple(sorted({row.metric for row in candidate_rows}))
    q4_periods = tuple(
        sorted(
            {
                row.fiscal_period
                for row in candidate_rows
                if row.fiscal_period.endswith("-Q4")
            }
        )
    )
    return QuarterlyAdapterAcceptance(
        ticker=symbol,
        source_id=normalized_source,
        status="blocked" if stable_blockers else "accepted_for_review",
        blockers=stable_blockers,
        accepted_observation_count=0 if stable_blockers else len(candidate_rows),
        reviewed_metrics=reviewed_metrics,
        derived_point_count=len(derivation.points),
        explicit_q4_periods=q4_periods,
        rights_status=decision.status,
    )
