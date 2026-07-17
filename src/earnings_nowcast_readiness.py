from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Sequence

from src.earnings_nowcast_contract import (
    ConsensusSnapshot,
    FreshnessState,
    NowcastState,
    QuarterlyActual,
    parse_utc_timestamp,
)


EXCLUDED_ASSET_TYPES = {"etf", "index", "fund", "mutual_fund"}


@dataclass(frozen=True)
class NowcastReadiness:
    ticker: str
    fiscal_period: str
    as_of_timestamp: str
    state: NowcastState
    revenue_ready: bool
    eps_ready: bool
    consensus_ready: bool
    freshness_state: FreshnessState
    missing_evidence: tuple[str, ...]
    source_ids: tuple[str, ...]
    evidence_source_ids: tuple[str, ...]
    conflict_source_ids: tuple[str, ...]
    next_action: str


@dataclass(frozen=True)
class CanonicalActualEvidence:
    revenue_rows: tuple[QuarterlyActual, ...]
    eps_rows: tuple[QuarterlyActual, ...]
    revenue_conflict_source_ids: tuple[str, ...]
    eps_conflict_source_ids: tuple[str, ...]
    revenue_incompatible_periods: tuple[str, ...]
    eps_incompatible_periods: tuple[str, ...]
    all_source_ids: tuple[str, ...]


def _sign_changes(values: Iterable[float]) -> int:
    signs = [1 if value > 0 else -1 for value in values if value != 0]
    return sum(left != right for left, right in zip(signs, signs[1:]))


def _freshness(
    snapshot_at: str,
    cutoff: str,
    *,
    current_after_days: int,
    stale_after_days: int,
) -> FreshnessState:
    snapshot = parse_utc_timestamp(snapshot_at, label="consensus snapshot")
    boundary = parse_utc_timestamp(cutoff, label="forecast cutoff")
    age_days = (boundary - snapshot).total_seconds() / 86400
    if age_days <= current_after_days:
        return FreshnessState.CURRENT
    if age_days <= stale_after_days:
        return FreshnessState.REVIEW_DUE
    return FreshnessState.STALE_OR_UNKNOWN


def _latest_consensus(rows: Sequence[ConsensusSnapshot]) -> ConsensusSnapshot | None:
    if not rows:
        return None
    return max(rows, key=lambda row: parse_utc_timestamp(row.snapshot_at))


def _dedupe(items: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item for item in items if item))


def _metric_definition(row: QuarterlyActual | ConsensusSnapshot, metric: str) -> tuple[object, ...]:
    if metric == "revenue":
        return (row.revenue_currency, row.revenue_unit_scale, row.revenue_basis)
    return (
        row.eps_currency,
        row.eps_basis,
        row.eps_share_basis,
        row.eps_operations_basis,
        row.split_adjustment_basis,
    )


def _previous_period(period: str) -> str:
    year, quarter = period.split("-Q", 1)
    return f"{int(year) - 1}-Q4" if quarter == "1" else f"{year}-Q{int(quarter) - 1}"


def contiguous_metric_window(
    rows: Sequence[QuarterlyActual],
    target_period: str,
    metric: str,
    minimum_quarters: int,
) -> tuple[QuarterlyActual, ...]:
    value_field = f"{metric}_actual"
    rows_by_period = {
        row.fiscal_period: row
        for row in rows
        if getattr(row, value_field) is not None
    }
    expected_period = _previous_period(target_period)
    window: list[QuarterlyActual] = []
    for _ in range(minimum_quarters):
        row = rows_by_period.get(expected_period)
        if row is None:
            return ()
        window.append(row)
        expected_period = _previous_period(expected_period)
    return tuple(reversed(window))


def _canonical_period_row(rows: Sequence[QuarterlyActual], metric: str) -> tuple[QuarterlyActual | None, tuple[str, ...]]:
    value_field = f"{metric}_actual"
    ordered = sorted(rows, key=lambda row: (parse_utc_timestamp(row.reported_at), parse_utc_timestamp(row.retrieved_at), row.source_ref))
    values = {float(getattr(row, value_field)) for row in ordered}
    if len(values) == 1:
        return ordered[-1], ()
    latest = ordered[-1]
    by_ref = {row.source_ref: row for row in ordered}
    if len(by_ref) == len(ordered):
        position_by_ref = {row.source_ref: index for index, row in enumerate(ordered)}
        visited: set[str] = set()
        current = latest
        while current.source_ref not in visited:
            visited.add(current.source_ref)
            supersedes = current.supersedes_source_ref
            if not supersedes:
                break
            prior = by_ref.get(supersedes)
            if prior is None or position_by_ref[prior.source_ref] >= position_by_ref[current.source_ref]:
                break
            current = prior
        if len(visited) == len(ordered):
            return latest, ()
    return None, tuple(sorted(row.source_ref for row in ordered))


def canonicalize_actuals(
    rows: Sequence[QuarterlyActual],
    consensus: ConsensusSnapshot | None,
) -> CanonicalActualEvidence:
    selected: dict[str, list[QuarterlyActual]] = {"revenue": [], "eps": []}
    conflicts: dict[str, list[str]] = {"revenue": [], "eps": []}
    incompatible: dict[str, list[str]] = {"revenue": [], "eps": []}
    for metric in ("revenue", "eps"):
        by_period: dict[str, list[QuarterlyActual]] = {}
        for row in rows:
            if getattr(row, f"{metric}_actual") is not None:
                by_period.setdefault(row.fiscal_period, []).append(row)
        expected_definition = _metric_definition(consensus, metric) if consensus is not None else None
        for period, period_rows in sorted(by_period.items()):
            definitions = {_metric_definition(row, metric) for row in period_rows}
            if expected_definition is None:
                compatible = period_rows if len(definitions) == 1 else []
            else:
                compatible = [row for row in period_rows if _metric_definition(row, metric) == expected_definition]
            if not compatible:
                incompatible[metric].append(period)
                continue
            chosen, period_conflicts = _canonical_period_row(compatible, metric)
            if chosen is None:
                conflicts[metric].extend(period_conflicts)
            else:
                selected[metric].append(chosen)
    all_source_ids = tuple(sorted({row.source_ref for row in rows}))
    return CanonicalActualEvidence(
        revenue_rows=tuple(selected["revenue"]),
        eps_rows=tuple(selected["eps"]),
        revenue_conflict_source_ids=tuple(sorted(set(conflicts["revenue"]))),
        eps_conflict_source_ids=tuple(sorted(set(conflicts["eps"]))),
        revenue_incompatible_periods=tuple(incompatible["revenue"]),
        eps_incompatible_periods=tuple(incompatible["eps"]),
        all_source_ids=all_source_ids,
    )


def assess_nowcast_readiness(
    *,
    ticker: str,
    fiscal_period: str,
    as_of_timestamp: str,
    actuals: Sequence[QuarterlyActual],
    consensus: Sequence[ConsensusSnapshot],
    asset_type: str = "company",
    minimum_history_quarters: int = 5,
    current_after_days: int = 45,
    stale_after_days: int = 90,
) -> NowcastReadiness:
    normalized_ticker = str(ticker or "").strip().upper()
    normalized_period = str(fiscal_period or "").strip().upper()
    normalized_cutoff = parse_utc_timestamp(as_of_timestamp, label="forecast cutoff").isoformat()
    normalized_asset_type = str(asset_type or "").strip().lower()

    if normalized_asset_type in EXCLUDED_ASSET_TYPES:
        return NowcastReadiness(
            ticker=normalized_ticker,
            fiscal_period=normalized_period,
            as_of_timestamp=normalized_cutoff,
            state=NowcastState.EXCLUDED,
            revenue_ready=False,
            eps_ready=False,
            consensus_ready=False,
            freshness_state=FreshnessState.STALE_OR_UNKNOWN,
            missing_evidence=("not_applicable_to_non_company_instrument",),
            source_ids=(),
            evidence_source_ids=(),
            conflict_source_ids=(),
            next_action="No company earnings nowcast applies to this instrument.",
        )

    matching_actuals = [row for row in actuals if row.ticker == normalized_ticker]
    matching_consensus = [
        row
        for row in consensus
        if row.ticker == normalized_ticker and row.fiscal_period == normalized_period
    ]
    post_cutoff = False
    for row in (*matching_actuals, *matching_consensus):
        try:
            row.available_at(normalized_cutoff)
        except ValueError:
            post_cutoff = True

    available_actuals = [
        row
        for row in matching_actuals
        if parse_utc_timestamp(row.reported_at) <= parse_utc_timestamp(normalized_cutoff)
        and row.fiscal_period != normalized_period
    ]
    available_consensus = [
        row
        for row in matching_consensus
        if parse_utc_timestamp(row.snapshot_at) <= parse_utc_timestamp(normalized_cutoff)
    ]
    available_actuals.sort(key=lambda row: (row.period_end_date, row.reported_at, row.source_ref))
    selected_consensus = _latest_consensus(available_consensus)
    canonical = canonicalize_actuals(available_actuals, selected_consensus)

    revenue_window = contiguous_metric_window(
        canonical.revenue_rows,
        normalized_period,
        "revenue",
        minimum_history_quarters,
    )
    eps_window = contiguous_metric_window(
        canonical.eps_rows,
        normalized_period,
        "eps",
        minimum_history_quarters,
    )
    revenue_history = [row.revenue_actual for row in revenue_window]
    eps_history = [row.eps_actual for row in eps_window]
    enough_revenue_history = len(revenue_window) == minimum_history_quarters
    enough_eps_history = len(eps_window) == minimum_history_quarters
    revenue_history_gap = bool(canonical.revenue_rows) and not enough_revenue_history
    eps_history_gap = bool(canonical.eps_rows) and not enough_eps_history
    stable_eps_history = enough_eps_history and _sign_changes(float(value) for value in eps_history) <= 1

    freshness_state = (
        _freshness(
            selected_consensus.snapshot_at,
            normalized_cutoff,
            current_after_days=current_after_days,
            stale_after_days=stale_after_days,
        )
        if selected_consensus is not None
        else FreshnessState.STALE_OR_UNKNOWN
    )
    consensus_ready = selected_consensus is not None
    current_consensus = freshness_state != FreshnessState.STALE_OR_UNKNOWN
    revenue_consensus_ready = selected_consensus is not None and selected_consensus.revenue_consensus is not None
    eps_consensus_ready = selected_consensus is not None and selected_consensus.eps_consensus is not None

    revenue_ready = (
        enough_revenue_history
        and revenue_consensus_ready
        and current_consensus
        and not post_cutoff
        and not canonical.revenue_conflict_source_ids
        and not canonical.revenue_incompatible_periods
    )
    eps_ready = (
        stable_eps_history
        and eps_consensus_ready
        and current_consensus
        and not post_cutoff
        and not canonical.eps_conflict_source_ids
        and not canonical.eps_incompatible_periods
    )

    missing: list[str] = []
    if post_cutoff:
        missing.append("post_cutoff_evidence")
    if not enough_revenue_history:
        missing.append("quarterly_actual_history")
    if revenue_history_gap or eps_history_gap:
        missing.append("quarter_history_gap")
    if canonical.revenue_conflict_source_ids:
        missing.append("conflicting_quarterly_revenue")
    if canonical.eps_conflict_source_ids:
        missing.append("conflicting_quarterly_eps")
    if canonical.revenue_incompatible_periods:
        missing.append("incompatible_revenue_definition")
    if canonical.eps_incompatible_periods:
        missing.append("incompatible_eps_definition")
    if not consensus_ready:
        missing.append("point_in_time_consensus")
    if consensus_ready and not revenue_consensus_ready:
        missing.append("revenue_consensus")
    if not stable_eps_history:
        missing.append("stable_eps_history")
    if consensus_ready and not eps_consensus_ready:
        missing.append("eps_consensus")
    if consensus_ready and not current_consensus:
        missing.append("current_consensus")

    state = NowcastState.BASELINE_READY if revenue_ready or eps_ready else NowcastState.BLOCKED
    source_ids = tuple(row.source_ref for row in (*revenue_window, *eps_window))
    if selected_consensus is not None:
        source_ids += (
            selected_consensus.source_ref
            or f"consensus:{selected_consensus.source}:{selected_consensus.snapshot_at}",
        )
    source_ids = tuple(sorted(set(source_ids)))

    if state == NowcastState.BASELINE_READY and not missing:
        next_action = "Review the deterministic Revenue/EPS range and consensus-relative classification."
    elif state == NowcastState.BASELINE_READY:
        next_action = "Review the ready metric and keep unsupported metrics analytically withheld."
    else:
        next_action = "Add source-backed quarterly history and an exact-period point-in-time consensus snapshot."

    return NowcastReadiness(
        ticker=normalized_ticker,
        fiscal_period=normalized_period,
        as_of_timestamp=normalized_cutoff,
        state=state,
        revenue_ready=revenue_ready,
        eps_ready=eps_ready,
        consensus_ready=consensus_ready,
        freshness_state=freshness_state,
        missing_evidence=_dedupe(missing),
        source_ids=source_ids,
        evidence_source_ids=canonical.all_source_ids,
        conflict_source_ids=tuple(
            sorted(set((*canonical.revenue_conflict_source_ids, *canonical.eps_conflict_source_ids)))
        ),
        next_action=next_action,
    )


def readiness_payload(readiness: NowcastReadiness) -> dict[str, object]:
    payload = asdict(readiness)
    payload["state"] = readiness.state.value
    payload["freshness_state"] = readiness.freshness_state.value
    payload["missing_evidence"] = list(readiness.missing_evidence)
    payload["source_ids"] = list(readiness.source_ids)
    payload["evidence_source_ids"] = list(readiness.evidence_source_ids)
    payload["conflict_source_ids"] = list(readiness.conflict_source_ids)
    return payload
