"""Deterministic, read-only momentum and valuation research queue."""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Iterable
from urllib.parse import quote


QUEUE_BOUNDARY = (
    "Research candidates only; this queue does not change readiness, create a "
    "forecast or probability, rank a company, or provide investment advice."
)


@dataclass(frozen=True)
class DailyQueuePolicy:
    valuation_percentile_max: float = 40.0
    maximum_debt_to_equity: float = 2.0


@dataclass(frozen=True)
class DailyQueueEvidence:
    ticker: str
    company_name: str
    observation_through_date: str
    momentum_ready: bool
    current_market_eligible: bool
    price_provenance_eligible: bool
    price_rights_eligible: bool
    price_field_scope_eligible: bool
    close: float | None
    sma_50: float | None
    sma_200: float | None
    return_3m: float | None
    return_6m: float | None
    relative_return_vs_spy: float | None
    valuation_state: str
    valuation_freshness_state: str
    valuation_commercial_eligible: bool
    valuation_metric: str
    valuation_percentile: float | None
    free_cash_flow: float | None
    revenue_growth: float | None
    debt_to_equity: float | None
    fundamentals_provenance_eligible: bool
    fundamentals_rights_eligible: bool
    fundamentals_field_scope_eligible: bool


@dataclass(frozen=True)
class DailyQueueItem:
    ticker: str
    company_name: str
    state: str
    blockers: tuple[str, ...]
    observation_through_date: str
    momentum_summary: str
    valuation_summary: str
    fundamentals_summary: str
    workbench_url: str


@dataclass(frozen=True)
class DailyQueueResult:
    status: str
    eligible: tuple[DailyQueueItem, ...]
    withheld: tuple[DailyQueueItem, ...]
    message: str
    boundary: str = QUEUE_BOUNDARY


@dataclass(frozen=True)
class DailyQueueComparison:
    status: str
    current_eligible: tuple[DailyQueueItem, ...]
    current_withheld: tuple[DailyQueueItem, ...]
    new_today: tuple[DailyQueueItem, ...]
    still_qualifies: tuple[DailyQueueItem, ...]
    exited_today: tuple[DailyQueueItem, ...]
    boundary: str = QUEUE_BOUNDARY


def _finite(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _numeric_blockers(row: DailyQueueEvidence, policy: DailyQueuePolicy) -> list[str]:
    blockers: list[str] = []
    if not _finite(row.close):
        blockers.append("price_missing")
    elif _finite(row.sma_50) and float(row.close) <= float(row.sma_50):
        blockers.append("price_not_above_sma50")

    if not _finite(row.sma_50):
        blockers.append("sma50_missing")
    if not _finite(row.sma_200):
        blockers.append("sma200_missing")
    if _finite(row.sma_50) and _finite(row.sma_200) and float(row.sma_50) <= float(row.sma_200):
        blockers.append("sma50_not_above_sma200")

    for value, missing, failed in (
        (row.return_3m, "three_month_return_missing", "three_month_return_not_positive"),
        (row.return_6m, "six_month_return_missing", "six_month_return_not_positive"),
        (
            row.relative_return_vs_spy,
            "spy_relative_return_missing",
            "spy_relative_return_not_positive",
        ),
    ):
        if not _finite(value):
            blockers.append(missing)
        elif float(value) <= 0:
            blockers.append(failed)

    if not _finite(row.valuation_percentile):
        blockers.append("valuation_percentile_missing")
    elif float(row.valuation_percentile) > policy.valuation_percentile_max:
        blockers.append("valuation_percentile_above_threshold")

    if not _finite(row.free_cash_flow):
        blockers.append("free_cash_flow_missing")
    elif float(row.free_cash_flow) <= 0:
        blockers.append("free_cash_flow_not_positive")

    if not _finite(row.revenue_growth):
        blockers.append("revenue_growth_missing")
    elif float(row.revenue_growth) < 0:
        blockers.append("revenue_growth_negative")

    if not _finite(row.debt_to_equity):
        blockers.append("debt_to_equity_missing")
    elif float(row.debt_to_equity) > policy.maximum_debt_to_equity:
        blockers.append("debt_above_threshold")
    return blockers


def _blockers(row: DailyQueueEvidence, policy: DailyQueuePolicy) -> tuple[str, ...]:
    blockers: list[str] = []
    for passed, blocker in (
        (row.momentum_ready, "momentum_not_ready"),
        (row.current_market_eligible, "current_market_evidence_ineligible"),
        (row.price_provenance_eligible, "price_provenance_ineligible"),
        (row.price_rights_eligible, "price_rights_ineligible"),
        (row.price_field_scope_eligible, "price_field_scope_ineligible"),
    ):
        if not passed:
            blockers.append(blocker)
    blockers.extend(_numeric_blockers(row, policy))
    if row.valuation_state != "ready":
        blockers.append("valuation_not_ready")
    if row.valuation_freshness_state != "current":
        blockers.append("valuation_stale")
    if not row.valuation_commercial_eligible:
        blockers.append("valuation_commercial_evidence_ineligible")
    for passed, blocker in (
        (row.fundamentals_provenance_eligible, "fundamentals_provenance_ineligible"),
        (row.fundamentals_rights_eligible, "fundamentals_rights_ineligible"),
        (row.fundamentals_field_scope_eligible, "fundamentals_field_scope_ineligible"),
    ):
        if not passed:
            blockers.append(blocker)
    return tuple(blockers)


def _number(value: float | None, *, percent: bool = False) -> str:
    if not _finite(value):
        return "Unavailable"
    numeric = float(value)
    return f"{numeric * 100:.1f}%" if percent else f"{numeric:.2f}"


def _evaluate(row: DailyQueueEvidence, policy: DailyQueuePolicy) -> DailyQueueItem:
    ticker = str(row.ticker or "").strip().upper()
    if not ticker:
        raise ValueError("ticker must be non-empty")
    blockers = _blockers(row, policy)
    return DailyQueueItem(
        ticker=ticker,
        company_name=str(row.company_name or "").strip() or ticker,
        state="withheld" if blockers else "eligible",
        blockers=blockers,
        observation_through_date=str(row.observation_through_date or "").strip(),
        momentum_summary=(
            f"Close {_number(row.close)}; SMA50 {_number(row.sma_50)}; "
            f"SMA200 {_number(row.sma_200)}; 3M {_number(row.return_3m, percent=True)}; "
            f"6M {_number(row.return_6m, percent=True)}; "
            f"vs SPY {_number(row.relative_return_vs_spy, percent=True)}."
        ),
        valuation_summary=(
            f"{str(row.valuation_metric or 'valuation').replace('_', ' ')} percentile "
            f"{_number(row.valuation_percentile)}; threshold {policy.valuation_percentile_max:.0f}."
        ),
        fundamentals_summary=(
            f"Free cash flow {_number(row.free_cash_flow)}; revenue growth "
            f"{_number(row.revenue_growth, percent=True)}; debt to equity "
            f"{_number(row.debt_to_equity)}."
        ),
        workbench_url=(
            "?mode=research&page=company-workbench&ticker="
            f"{quote(ticker, safe='')}"
        ),
    )


def evaluate_daily_queue(
    evidence: Iterable[DailyQueueEvidence],
    *,
    policy: DailyQueuePolicy = DailyQueuePolicy(),
) -> DailyQueueResult:
    """Evaluate supplied evidence without reading, writing, or ranking."""

    seen: set[str] = set()
    items: list[DailyQueueItem] = []
    for row in evidence:
        ticker = str(row.ticker or "").strip().upper()
        if ticker in seen:
            raise ValueError(f"duplicate ticker evidence: {ticker}")
        seen.add(ticker)
        items.append(_evaluate(row, policy))
    ordered = tuple(sorted(items, key=lambda item: item.ticker))
    eligible = tuple(item for item in ordered if item.state == "eligible")
    withheld = tuple(item for item in ordered if item.state == "withheld")
    return DailyQueueResult(
        status="eligible" if eligible else "withheld",
        eligible=eligible,
        withheld=withheld,
        message=(
            f"{len(eligible)} company research candidate(s) pass every required evidence gate."
            if eligible
            else "No company currently passes every required evidence gate."
        ),
    )


def compare_daily_queues(
    current: DailyQueueResult,
    previous: DailyQueueResult | None,
) -> DailyQueueComparison:
    """Compare explicit snapshots; never infer that a missing baseline is empty."""

    if previous is None:
        return DailyQueueComparison(
            status="baseline_missing",
            current_eligible=current.eligible,
            current_withheld=current.withheld,
            new_today=(),
            still_qualifies=(),
            exited_today=(),
        )
    current_eligible = {item.ticker: item for item in current.eligible}
    current_withheld = {item.ticker: item for item in current.withheld}
    previous_eligible = {item.ticker: item for item in previous.eligible}
    new_today = tuple(current_eligible[ticker] for ticker in sorted(current_eligible.keys() - previous_eligible))
    still = tuple(current_eligible[ticker] for ticker in sorted(current_eligible.keys() & previous_eligible))
    exited: list[DailyQueueItem] = []
    for ticker in sorted(previous_eligible.keys() - current_eligible):
        if ticker in current_withheld:
            exited.append(replace(current_withheld[ticker], state="exited_today"))
        else:
            exited.append(
                replace(
                    previous_eligible[ticker],
                    state="exited_today",
                    blockers=("current_evidence_missing",),
                )
            )
    return DailyQueueComparison(
        status="comparable",
        current_eligible=current.eligible,
        current_withheld=current.withheld,
        new_today=new_today,
        still_qualifies=still,
        exited_today=tuple(exited),
    )


def daily_queue_display_rows(comparison: DailyQueueComparison) -> list[dict[str, str]]:
    """Return compact, presentation-safe rows for the primary queue surface."""

    if comparison.status == "baseline_missing":
        groups = (("Current eligible", comparison.current_eligible),)
    else:
        groups = (
            ("New today", comparison.new_today),
            ("Still qualifies", comparison.still_qualifies),
            ("Exited today", comparison.exited_today),
        )
    rows: list[dict[str, str]] = []
    for group, items in groups:
        for item in items:
            rows.append(
                {
                    "Status": group,
                    "Ticker": item.ticker,
                    "Company": item.company_name,
                    "Observation Through": item.observation_through_date or "Unavailable",
                    "Momentum Evidence": item.momentum_summary,
                    "Valuation Evidence": item.valuation_summary,
                    "Fundamental Safeguards": item.fundamentals_summary,
                    "Why": (
                        "Passes every required research-candidate gate."
                        if not item.blockers
                        else ", ".join(item.blockers)
                    ),
                    "Open Company Workbench": item.workbench_url,
                }
            )
    return rows


def daily_queue_summary_cards(comparison: DailyQueueComparison) -> list[dict[str, object]]:
    """Return answer-first queue status without exposing a company rank."""

    current_count = len(comparison.current_eligible)
    if comparison.status == "baseline_missing":
        body = (
            f"{current_count} current research candidate(s) pass every gate. "
            "No comparable prior queue was supplied, so daily entries and exits are withheld."
        )
        badges = [f"{current_count} current", "baseline missing", "alphabetical"]
    else:
        body = (
            f"{len(comparison.new_today)} new, {len(comparison.still_qualifies)} continuing, "
            f"and {len(comparison.exited_today)} exited research candidate(s)."
        )
        badges = [
            f"{len(comparison.new_today)} new",
            f"{len(comparison.still_qualifies)} continuing",
            f"{len(comparison.exited_today)} exited",
        ]
    return [
        {
            "kicker": "DAILY RESEARCH QUEUE",
            "title": (
                f"{current_count} research candidate(s) pass every required gate"
                if current_count
                else "No company passes every required gate"
            ),
            "body": f"{body} {QUEUE_BOUNDARY}",
            "badges": badges,
            "command": "",
        }
    ]
