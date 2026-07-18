"""Deterministic composition of evidence-bound forward research context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.quarterly_business_trend import QuarterlyTrendPacket


@dataclass(frozen=True)
class ForwardViewSection:
    name: str
    state: str
    answer: str
    details: tuple[dict[str, object], ...]
    boundary: str


@dataclass(frozen=True)
class ForwardViewPacket:
    ticker: str
    status: str
    source_cutoff: str
    freshness_state: str
    model_version: str
    historical_trend: ForwardViewSection
    valuation_scenarios: ForwardViewSection
    peer_context: ForwardViewSection
    thesis_context: ForwardViewSection
    earnings_outlook: ForwardViewSection
    withheld_fields: tuple[str, ...]
    next_research_task: str
    boundary: str


def _text(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null", "<na>"} else text


def _provenance_complete(rows: object) -> bool:
    return bool(rows) and all(
        isinstance(row, Mapping)
        and _text(row.get("source"))
        and _text(row.get("source_ref"))
        for row in rows
    )


def _blocked(name: str, answer: str, boundary: str) -> ForwardViewSection:
    return ForwardViewSection(name, "blocked", answer, (), boundary)


def _historical_section(packet: QuarterlyTrendPacket) -> ForwardViewSection:
    if packet.status == "blocked":
        return _blocked(
            "Historical Trend",
            packet.message,
            "Explicit, compatible quarterly Revenue and EPS observations are required.",
        )
    details = tuple(
        {
            "metric": label,
            "period": trend.latest_fiscal_period,
            "value": trend.latest_value,
            "sequential_change_pct": trend.sequential_change_pct,
            "year_over_year_change_pct": trend.year_over_year_change_pct,
            "source_ref": trend.latest_source_ref,
        }
        for label, trend in (("Revenue", packet.revenue), ("EPS", packet.eps))
        if trend.latest_value is not None and trend.latest_source_ref
    )
    state = "usable_now" if packet.status == "ready" else "partial"
    return ForwardViewSection(
        "Historical Trend",
        state,
        packet.message,
        details,
        "Trend is descriptive source evidence, not a future estimate.",
    )


def _valuation_section(report: Mapping[str, object], *, stale: bool) -> ForwardViewSection:
    readiness = {
        **dict(report.get("readiness") or {}),
        **dict(report.get("valuation_readiness") or {}),
    }
    valuation = report.get("valuation_snapshot") if isinstance(report.get("valuation_snapshot"), Mapping) else {}
    valuation = valuation or {}
    source_rows = valuation.get("source_metadata") or []
    scenarios = valuation.get("scenarios") or []
    dcf_ready = bool(readiness.get("dcf_ready"))
    if not dcf_ready or not _provenance_complete(source_rows):
        return _blocked(
            "Valuation Scenarios",
            "Bull, base, and bear valuation scenarios are withheld.",
            "DCF readiness and complete source provenance are required before scenario values appear.",
        )

    details: list[dict[str, object]] = []
    for scenario in scenarios:
        if not isinstance(scenario, Mapping):
            continue
        name = _text(scenario.get("name")).lower()
        result = scenario.get("dcf_result") if isinstance(scenario.get("dcf_result"), Mapping) else {}
        result = result or {}
        assumptions = scenario.get("assumptions") if isinstance(scenario.get("assumptions"), Mapping) else {}
        if name not in {"bear", "base", "bull"} or _text(result.get("status")).lower() != "calculated":
            continue
        value = result.get("fair_value_per_share")
        if value is None:
            continue
        details.append({"name": name, "per_share_value": value, "assumptions": dict(assumptions or {})})
    order = {"bear": 0, "base": 1, "bull": 2}
    details.sort(key=lambda row: order[str(row["name"])])
    if [row["name"] for row in details] != ["bear", "base", "bull"]:
        return _blocked(
            "Valuation Scenarios",
            "A complete bull, base, and bear scenario set is unavailable.",
            "All three bounded scenarios must calculate from the same source-backed input snapshot.",
        )
    return ForwardViewSection(
        "Valuation Scenarios",
        "partial" if stale else "usable_now",
        "Three bounded valuation scenarios are available from the saved DCF input set.",
        tuple(details),
        (
            "Saved inputs are stale; review their effective dates before relying on scenario sensitivity."
            if stale
            else "Scenario values test assumptions; they are not price predictions or recommendations."
        ),
    )


def _peer_section(peer_map: object | None) -> ForwardViewSection:
    if peer_map is None:
        return _blocked(
            "Trusted Peer Context",
            "Trusted peer read-through is unavailable.",
            "Source-backed peer relationships and comparable peer results are required.",
        )
    trusted = int(getattr(peer_map, "trusted_count", 0) or 0)
    candidate = int(getattr(peer_map, "candidate_count", 0) or 0)
    reviewable = int(getattr(peer_map, "reviewable_count", 0) or 0)
    if not trusted or not reviewable:
        state = "candidate_context_only" if candidate else "blocked"
        return ForwardViewSection(
            "Trusted Peer Context",
            state,
            f"{candidate} candidate peer relationship(s) are visible; no trusted read-through is reviewable.",
            (),
            "Candidate peer context is not trusted evidence and cannot change scenarios or forecasts.",
        )
    return ForwardViewSection(
        "Trusted Peer Context",
        "usable_now",
        f"{reviewable} source-backed peer result(s) are available for contextual review.",
        ({"trusted_count": trusted, "reviewable_count": reviewable, "candidate_count": candidate},),
        _text(getattr(peer_map, "boundary", "")) or "Peer evidence remains context only.",
    )


def _journal_details(entries: object) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "summary": _text(getattr(entry, "summary", "")),
            "source": _text(getattr(entry, "source", "")),
            "source_ref": _text(getattr(entry, "source_ref", "")),
        }
        for entry in tuple(entries or ())
        if _text(getattr(entry, "summary", ""))
        and _text(getattr(entry, "source", ""))
        and _text(getattr(entry, "source_ref", ""))
    )


def _thesis_section(journal_state: object | None) -> ForwardViewSection:
    if journal_state is None:
        return _blocked(
            "Reviewer Thesis Context",
            "No reviewed catalyst, risk, or invalidation evidence is available.",
            "Generated narrative cannot substitute for reviewer-authored, source-backed journal entries.",
        )
    details: list[dict[str, object]] = []
    for category, entries in (
        ("catalyst", getattr(journal_state, "catalysts", ())),
        ("risk", getattr(journal_state, "risks", ())),
        ("invalidation", getattr(journal_state, "invalidation_conditions", ())),
    ):
        details.extend({"category": category, **row} for row in _journal_details(entries))
    if not details:
        return _blocked(
            "Reviewer Thesis Context",
            "No source-backed catalyst, risk, or invalidation entry is available.",
            "The research journal remains reviewer-authored and append-only.",
        )
    return ForwardViewSection(
        "Reviewer Thesis Context",
        "usable_now",
        f"{len(details)} reviewed catalyst, risk, or invalidation item(s) are available.",
        tuple(details),
        "Journal evidence documents a hypothesis; it is not conviction, expected return, or an action instruction.",
    )


def _nowcast_section(packet: Mapping[str, object] | None) -> ForwardViewSection:
    if not packet or not isinstance(packet.get("forecast"), Mapping):
        return _blocked(
            "Earnings Outlook",
            "No real source-backed Earnings Outlook range is available.",
            "Exact-period point-in-time consensus and compatible quarterly actuals are required.",
        )
    readiness = packet.get("readiness") if isinstance(packet.get("readiness"), Mapping) else {}
    forecast = packet.get("forecast") or {}
    state = _text(readiness.get("state")).lower()
    if state not in {"baseline_ready", "signal_context_ready", "backtest_ready", "calibrated"}:
        return _blocked(
            "Earnings Outlook",
            "Earnings Outlook evidence does not pass the baseline gate.",
            "No numerical range is shown until the source-backed baseline is ready.",
        )
    details = tuple(
        {"metric": metric, "low": forecast.get(low), "high": forecast.get(high)}
        for metric, low, high in (
            ("Revenue", "revenue_low", "revenue_high"),
            ("EPS", "eps_low", "eps_high"),
        )
        if forecast.get(low) is not None and forecast.get(high) is not None
    )
    calibrated = state == "calibrated" and bool((packet.get("calibration") or {}).get("eligible"))
    return ForwardViewSection(
        "Earnings Outlook",
        "usable_now" if details else "partial",
        "A deterministic source-backed Revenue/EPS range is available." if details else "Only part of the Earnings Outlook range is available.",
        details,
        (
            "Calibration evidence passed; any eligible probability remains governed by the separate Nowcast contract."
            if calibrated
            else "Numerical surprise probability withheld until calibration evidence passes."
        ),
    )


def build_forward_view(
    report_payload: Mapping[str, object],
    quarterly_trend: QuarterlyTrendPacket,
    *,
    journal_state: object | None = None,
    peer_map: object | None = None,
    nowcast_packet: Mapping[str, object] | None = None,
    freshness_state: str = "unknown",
) -> ForwardViewPacket:
    ticker = _text(report_payload.get("ticker")).upper()
    source_cutoff = _text(report_payload.get("generated_at") or report_payload.get("as_of_timestamp"))
    freshness = _text(freshness_state).lower() or "unknown"
    sections = (
        _historical_section(quarterly_trend),
        _valuation_section(report_payload, stale=freshness == "stale"),
        _peer_section(peer_map),
        _thesis_section(journal_state),
        _nowcast_section(nowcast_packet),
    )
    withheld = tuple(
        key
        for key, section in zip(
            ("historical_trend", "valuation_scenarios", "trusted_peer_context", "thesis_context", "earnings_outlook"),
            sections,
        )
        if section.state in {"blocked", "partial", "candidate_context_only"}
    )
    if sections[4].state == "blocked":
        next_task = "Add exact-period point-in-time consensus before reviewing an Earnings Outlook range."
    elif sections[0].state == "blocked":
        next_task = "Review canonical quarterly Revenue and EPS evidence."
    elif sections[1].state == "blocked":
        next_task = "Review source-backed valuation inputs and scenario provenance."
    elif sections[3].state == "blocked":
        next_task = "Record one source-backed thesis risk or invalidation condition."
    else:
        next_task = "Review changed evidence and update one explicit research wait condition."
    status = "ready" if not withheld else "partial" if any(section.state == "usable_now" for section in sections) else "blocked"
    return ForwardViewPacket(
        ticker=ticker,
        status=status,
        source_cutoff=source_cutoff,
        freshness_state=freshness,
        model_version=_text(report_payload.get("method_version")) or "forward-view-v1",
        historical_trend=sections[0],
        valuation_scenarios=sections[1],
        peer_context=sections[2],
        thesis_context=sections[3],
        earnings_outlook=sections[4],
        withheld_fields=withheld,
        next_research_task=next_task,
        boundary=(
            f"Saved evidence freshness is {freshness}. Forward View composes existing evidence and scenario math only; "
            "it does not predict post-earnings price direction or provide an investment recommendation."
        ),
    )


def forward_view_cards(packet: ForwardViewPacket) -> list[dict[str, object]]:
    sections = (
        packet.historical_trend,
        packet.valuation_scenarios,
        packet.peer_context,
        packet.thesis_context,
        packet.earnings_outlook,
    )
    cards = [
        {
            "kicker": section.name.upper(),
            "title": section.state.replace("_", " ").title(),
            "body": f"{section.answer} {section.boundary}",
            "state": section.state,
            "badges": [section.state.replace("_", " "), "evidence-bound"],
            "command": "",
        }
        for section in sections
    ]
    cards.append(
        {
            "kicker": "NEXT RESEARCH TASK",
            "title": packet.next_research_task,
            "body": packet.boundary,
            "state": "review_now" if packet.status != "blocked" else "wait_for_evidence",
            "badges": ["research-only", packet.freshness_state.replace("_", " ")],
            "command": "",
        }
    )
    return cards


def forward_view_rows(packet: ForwardViewPacket) -> list[dict[str, object]]:
    return [
        {
            "Section": section.name,
            "State": section.state.replace("_", " "),
            "Answer": section.answer,
            "Evidence": list(section.details),
            "Boundary": section.boundary,
        }
        for section in (
            packet.historical_trend,
            packet.valuation_scenarios,
            packet.peer_context,
            packet.thesis_context,
            packet.earnings_outlook,
        )
    ]
