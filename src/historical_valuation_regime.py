"""Point-in-time historical valuation regime without denominator backfilling."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from statistics import median
from typing import Iterable, Mapping

from src.commercial_source_rights import (
    SourceRights,
    load_source_rights_registry,
    review_commercial_field_scope,
)
from src.earnings_nowcast_contract import parse_utc_timestamp


@dataclass(frozen=True)
class ValuationObservation:
    ticker: str
    metric: str
    numerator: float
    denominator: float
    numerator_as_of: str
    denominator_period_end: str
    denominator_available_at: str
    definition_id: str
    source: str
    source_ref: str
    retrieved_at: str


@dataclass(frozen=True)
class ValuationRegimePacket:
    ticker: str
    metric: str
    state: str
    definition_id: str
    observation_count: int
    rejected_count: int
    segment_count: int
    latest_multiple: float | None
    minimum_multiple: float | None
    median_multiple: float | None
    maximum_multiple: float | None
    percentile_rank: float | None
    freshness_state: str
    rejected_reasons: tuple[str, ...]
    source_refs: tuple[str, ...]
    commercial_blocker_count: int
    commercial_blockers: tuple[str, ...]
    boundary: str


def _numeric_evidence(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def load_valuation_observations(path: Path | str) -> tuple[ValuationObservation, ...]:
    source = Path(path)
    if not source.is_file():
        return ()
    with source.open(newline="", encoding="utf-8") as handle:
        rows = []
        for row in csv.DictReader(handle):
            rows.append(
                ValuationObservation(
                    ticker=str(row.get("ticker") or ""),
                    metric=str(row.get("metric") or ""),
                    numerator=_numeric_evidence(row.get("numerator")),
                    denominator=_numeric_evidence(row.get("denominator")),
                    numerator_as_of=str(row.get("numerator_as_of") or ""),
                    denominator_period_end=str(row.get("denominator_period_end") or ""),
                    denominator_available_at=str(row.get("denominator_available_at") or ""),
                    definition_id=str(row.get("definition_id") or ""),
                    source=str(row.get("source") or ""),
                    source_ref=str(row.get("source_ref") or ""),
                    retrieved_at=str(row.get("retrieved_at") or ""),
                )
            )
    return tuple(rows)


def _validate_observation(row: ValuationObservation, *, as_of: str) -> str | None:
    if not row.ticker.strip() or not row.metric.strip() or not row.definition_id.strip():
        return "ticker, metric, and definition_id are required"
    if not row.source.strip() or not row.source_ref.strip():
        return "source and source_ref are required"
    if not math.isfinite(row.numerator) or not math.isfinite(row.denominator):
        return "numerator and denominator must be finite"
    if row.denominator == 0:
        return "denominator cannot be zero"
    period_end = str(row.denominator_period_end or "").strip()
    try:
        if date.fromisoformat(period_end).isoformat() != period_end:
            raise ValueError
    except ValueError:
        return "denominator_period_end must use YYYY-MM-DD"
    try:
        numerator_at = parse_utc_timestamp(row.numerator_as_of, label="numerator_as_of")
        denominator_at = parse_utc_timestamp(row.denominator_available_at, label="denominator_available_at")
        retrieved_at = parse_utc_timestamp(row.retrieved_at, label="retrieved_at")
        cutoff = parse_utc_timestamp(as_of, label="valuation cutoff")
    except ValueError as exc:
        return str(exc)
    if denominator_at > numerator_at:
        return "denominator was not public at the price timestamp"
    if numerator_at > retrieved_at:
        return "numerator timestamp cannot be after retrieval"
    if numerator_at > cutoff or denominator_at > cutoff or retrieved_at > cutoff:
        return "observation contains post-cutoff evidence"
    return None


def build_valuation_regime(
    observations: Iterable[ValuationObservation],
    *,
    ticker: str,
    metric: str,
    as_of: str,
    minimum_observations: int = 8,
    stale_after_days: int = 120,
    commercial_mode: bool = False,
    rights_registry: Mapping[str, SourceRights] | None = None,
) -> ValuationRegimePacket:
    symbol = str(ticker or "").strip().upper()
    metric_name = str(metric or "").strip().lower()
    accepted: list[ValuationObservation] = []
    rejected: list[str] = []
    for row in observations:
        if row.ticker.strip().upper() != symbol or row.metric.strip().lower() != metric_name:
            continue
        reason = _validate_observation(row, as_of=as_of)
        if reason:
            rejected.append(reason)
        else:
            accepted.append(row)
    segments: dict[str, list[ValuationObservation]] = {}
    for row in accepted:
        segments.setdefault(row.definition_id, []).append(row)
    if not segments:
        return ValuationRegimePacket(
            symbol, metric_name, "insufficient_history", "", 0, len(rejected), 0,
            None, None, None, None, None, "stale_or_unknown", tuple(rejected), (),
            0, (),
            "Historical valuation is withheld until aligned point-in-time observations exist; current denominators are never backfilled over old prices.",
        )
    latest_definition = max(
        segments,
        key=lambda definition: max(parse_utc_timestamp(row.numerator_as_of) for row in segments[definition]),
    )
    active = sorted(segments[latest_definition], key=lambda row: parse_utc_timestamp(row.numerator_as_of))
    commercial_blockers: list[str] = []
    if commercial_mode:
        registry = rights_registry if rights_registry is not None else load_source_rights_registry()
        for row in active:
            review = review_commercial_field_scope(
                registry, row.source, ("valuation_history",)
            )
            if not review.commercial_evidence_ready:
                missing = ", ".join(review.missing_supported_fields) or "valuation_history"
                commercial_blockers.append(
                    f"{row.source_ref}: exact source {row.source or '-'} is {review.rights_status}; "
                    f"registered scope missing: {missing}"
                )
    if commercial_blockers:
        return ValuationRegimePacket(
            symbol, metric_name, "commercial_evidence_blocked", latest_definition,
            0, len(rejected), len(segments), None, None, None, None, None,
            "stale_or_unknown", tuple(rejected), (), len(commercial_blockers),
            tuple(commercial_blockers),
            "Historical valuation is withheld until every used row has approved exact-source rights and registered valuation_history scope.",
        )
    multiples = [row.numerator / row.denominator for row in active]
    latest = multiples[-1]
    percentile = round(sum(value <= latest for value in multiples) / len(multiples) * 100.0, 2)
    latest_at = parse_utc_timestamp(active[-1].numerator_as_of)
    age_days = (parse_utc_timestamp(as_of) - latest_at).total_seconds() / 86400
    state = "ready" if len(active) >= minimum_observations else "insufficient_history"
    return ValuationRegimePacket(
        ticker=symbol,
        metric=metric_name,
        state=state,
        definition_id=latest_definition,
        observation_count=len(active),
        rejected_count=len(rejected),
        segment_count=len(segments),
        latest_multiple=round(latest, 6),
        minimum_multiple=round(min(multiples), 6),
        median_multiple=round(median(multiples), 6),
        maximum_multiple=round(max(multiples), 6),
        percentile_rank=percentile,
        freshness_state="current" if age_days <= stale_after_days else "stale",
        rejected_reasons=tuple(rejected),
        source_refs=tuple(row.source_ref for row in active),
        commercial_blocker_count=0,
        commercial_blockers=(),
        boundary="This is descriptive point-in-time valuation context, not a cheap/expensive label, forecast, recommendation, or action.",
    )


def valuation_regime_cards(packet: ValuationRegimePacket) -> list[dict[str, object]]:
    if packet.state == "commercial_evidence_blocked":
        title = "Historical valuation commercial evidence is blocked"
        body = (
            f"{packet.commercial_blocker_count} observation(s) lack approved exact-source "
            "rights or registered valuation-history scope. Technical rows cannot override that gate."
        )
    elif packet.state != "ready":
        title = "Historical valuation context is withheld"
        body = (
            f"{packet.observation_count} compatible point-in-time observation(s) are available in the latest definition segment. "
            "At least 8 are required; current denominators are never backfilled over historical prices."
        )
    else:
        title = f"Historical {packet.metric.replace('_', ' ')} regime is reviewable"
        body = (
            f"Latest {packet.latest_multiple:.2f}; observed range {packet.minimum_multiple:.2f} to {packet.maximum_multiple:.2f}; "
            f"latest observation percentile {packet.percentile_rank:.0f}. {packet.boundary}"
        )
    return [{
        "kicker": "VALUATION HISTORY",
        "title": title,
        "body": body,
        "badges": [packet.state.replace("_", " "), packet.freshness_state.replace("_", " "), "descriptive only"],
        "command": "",
    }]
