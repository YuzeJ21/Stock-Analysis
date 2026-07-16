"""Detect deterministic, evidence-backed changes between research snapshots."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

from src.research_change_snapshot import (
    ResearchChangeSnapshot,
    TickerResearchState,
    load_research_change_snapshot,
)


EVENT_ID_FIELDS = (
    "profile_key",
    "ticker",
    "family",
    "subtype",
    "prior_value",
    "current_value",
    "source_ref",
    "prior_snapshot_identity",
    "current_snapshot_identity",
)
READINESS_SUBTYPES = {
    "price_ready": "price_readiness_changed",
    "momentum_ready": "momentum_readiness_changed",
    "fundamentals_ready": "fundamentals_readiness_changed",
    "dcf_ready": "dcf_readiness_changed",
    "peer_ready": "peer_readiness_changed",
    "earnings_ready": "earnings_readiness_changed",
    "analyst_estimates_ready": "analyst_estimates_readiness_changed",
    "blocked_features": "blocked_inputs_changed",
    "overall_readiness_state": "overall_readiness_changed",
}
FUNDAMENTAL_VALUE_FIELDS = {
    "revenue",
    "eps",
    "free_cash_flow",
    "fcf",
    "fcf_margin",
    "operating_margin",
    "profit_margin",
    "ebitda",
    "cash",
    "debt",
    "net_debt",
    "shares_outstanding",
    "market_cap",
    "enterprise_value",
}


@dataclass(frozen=True)
class ResearchChangeEvent:
    event_id: str
    ticker: str
    family: str
    subtype: str
    prior_value: str
    current_value: str
    source: str
    source_ref: str
    source_published_at: str
    retrieved_at: str
    detected_at: str
    profile_key: str
    prior_snapshot_identity: str
    current_snapshot_identity: str
    evidence_status: str
    materiality: str
    suggested_research_task: str


@dataclass(frozen=True)
class ResearchChangeResult:
    status: str
    events: tuple[ResearchChangeEvent, ...]
    message: str


def event_id_for(event_fields: Mapping[str, str]) -> str:
    identity = "\x1f".join(str(event_fields.get(key) or "") for key in EVENT_ID_FIELDS)
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _empty_state(ticker: str) -> TickerResearchState:
    return TickerResearchState(ticker, (), (), "", "", "", (), ())


def _materiality(subtype: str, prior_value: str, current_value: str) -> str:
    if subtype in {"dcf_readiness_changed", "fundamentals_readiness_changed"}:
        return "high" if prior_value == "true" and current_value == "false" else "medium"
    if subtype in {"shares_outstanding_revised", "fundamentals_revised", "nowcast_consensus_changed"}:
        return "medium"
    if subtype == "sec_filing_arrived":
        return "medium"
    return "context"


def _task(subtype: str, ticker: str) -> str:
    tasks = {
        "dcf_readiness_changed": "Review the DCF readiness inputs and source evidence.",
        "fundamentals_readiness_changed": "Review the fundamentals readiness evidence and missing inputs.",
        "peer_readiness_changed": "Review trusted-peer evidence and readiness boundaries.",
        "sec_filing_arrived": "Review the new SEC filing and identify source-backed research updates.",
        "shares_outstanding_revised": "Review the explicit share-count revision and downstream readiness impact.",
        "fundamentals_revised": "Review the revised source-backed fundamental and affected analysis inputs.",
        "nowcast_consensus_changed": "Review the point-in-time consensus change and Nowcast readiness.",
        "price_history_advanced": "Review whether the additional price history changes momentum readiness.",
        "blocked_inputs_changed": "Review which source-proof blocker changed and why.",
    }
    return f"{ticker}: {tasks.get(subtype, 'Review the changed evidence and readiness state.')}"


def _source_ref(state: TickerResearchState, fallback: str) -> str:
    return state.source_refs[0] if state.source_refs else fallback


def _event(
    *,
    before: ResearchChangeSnapshot,
    after: ResearchChangeSnapshot,
    state: TickerResearchState,
    ticker: str,
    family: str,
    subtype: str,
    prior_value: str,
    current_value: str,
    source: str,
    source_ref: str,
    source_published_at: str = "",
) -> ResearchChangeEvent:
    fields = {
        "profile_key": after.profile_key,
        "ticker": ticker,
        "family": family,
        "subtype": subtype,
        "prior_value": prior_value,
        "current_value": current_value,
        "source_ref": source_ref,
        "prior_snapshot_identity": before.snapshot_identity,
        "current_snapshot_identity": after.snapshot_identity,
    }
    return ResearchChangeEvent(
        event_id=event_id_for(fields),
        ticker=ticker,
        family=family,
        subtype=subtype,
        prior_value=prior_value,
        current_value=current_value,
        source=source,
        source_ref=source_ref,
        source_published_at=source_published_at,
        retrieved_at=after.captured_at,
        detected_at=after.captured_at,
        profile_key=after.profile_key,
        prior_snapshot_identity=before.snapshot_identity,
        current_snapshot_identity=after.snapshot_identity,
        evidence_status="source_backed" if state.source_refs else "snapshot_evidence",
        materiality=_materiality(subtype, prior_value, current_value),
        suggested_research_task=_task(subtype, ticker),
    )


def _readiness_events(
    before: ResearchChangeSnapshot,
    after: ResearchChangeSnapshot,
    prior: TickerResearchState,
    current: TickerResearchState,
) -> list[ResearchChangeEvent]:
    prior_values = dict(prior.readiness)
    current_values = dict(current.readiness)
    events: list[ResearchChangeEvent] = []
    for field in sorted(set(prior_values) | set(current_values)):
        old = prior_values.get(field, "")
        new = current_values.get(field, "")
        subtype = READINESS_SUBTYPES.get(field)
        if old == new or subtype is None:
            continue
        events.append(
            _event(
                before=before,
                after=after,
                state=current,
                ticker=current.ticker,
                family="readiness",
                subtype=subtype,
                prior_value=old,
                current_value=new,
                source="selected_profile_readiness",
                source_ref=f"readiness:{field}",
            )
        )
    return events


def _filing_events(
    before: ResearchChangeSnapshot,
    after: ResearchChangeSnapshot,
    prior: TickerResearchState,
    current: TickerResearchState,
) -> list[ResearchChangeEvent]:
    if not current.latest_filing_accession or current.latest_filing_accession == prior.latest_filing_accession:
        return []
    fundamentals = dict(current.fundamentals)
    return [
        _event(
            before=before,
            after=after,
            state=current,
            ticker=current.ticker,
            family="filing",
            subtype="sec_filing_arrived",
            prior_value=prior.latest_filing_accession,
            current_value=current.latest_filing_accession,
            source=fundamentals.get("source", "sec_filing"),
            source_ref=f"sec-accession:{current.latest_filing_accession}",
            source_published_at=current.latest_filing_date,
        )
    ]


def _fundamental_events(
    before: ResearchChangeSnapshot,
    after: ResearchChangeSnapshot,
    prior: TickerResearchState,
    current: TickerResearchState,
) -> list[ResearchChangeEvent]:
    old_values = dict(prior.fundamentals)
    new_values = dict(current.fundamentals)
    events: list[ResearchChangeEvent] = []
    for field in sorted(FUNDAMENTAL_VALUE_FIELDS & (set(old_values) | set(new_values))):
        old = old_values.get(field, "")
        new = new_values.get(field, "")
        if old == new:
            continue
        subtype = "shares_outstanding_revised" if field == "shares_outstanding" else "fundamentals_revised"
        events.append(
            _event(
                before=before,
                after=after,
                state=current,
                ticker=current.ticker,
                family="fundamentals",
                subtype=subtype,
                prior_value=old,
                current_value=new,
                source=new_values.get("source", "selected_profile_fundamentals"),
                source_ref=f"{_source_ref(current, 'fundamentals')}#{field}",
                source_published_at=new_values.get("as_of_date", ""),
            )
        )
    return events


def _context_events(
    before: ResearchChangeSnapshot,
    after: ResearchChangeSnapshot,
    prior: TickerResearchState,
    current: TickerResearchState,
) -> list[ResearchChangeEvent]:
    events: list[ResearchChangeEvent] = []
    if current.latest_price_date and current.latest_price_date != prior.latest_price_date:
        events.append(
            _event(
                before=before,
                after=after,
                state=current,
                ticker=current.ticker,
                family="price",
                subtype="price_history_advanced",
                prior_value=prior.latest_price_date,
                current_value=current.latest_price_date,
                source="selected_profile_prices",
                source_ref="prices.csv",
                source_published_at=current.latest_price_date,
            )
        )
    if current.nowcast_consensus_ids != prior.nowcast_consensus_ids:
        events.append(
            _event(
                before=before,
                after=after,
                state=current,
                ticker=current.ticker,
                family="earnings_nowcast",
                subtype="nowcast_consensus_changed",
                prior_value="|".join(prior.nowcast_consensus_ids),
                current_value="|".join(current.nowcast_consensus_ids),
                source="point_in_time_consensus",
                source_ref=_source_ref(current, "earnings_nowcast/consensus_snapshots.csv"),
            )
        )
    return events


def compare_research_snapshots(
    before: ResearchChangeSnapshot,
    after: ResearchChangeSnapshot,
) -> tuple[ResearchChangeEvent, ...]:
    if before.profile_key != after.profile_key:
        raise ValueError("Research snapshots must use the same selected profile.")
    prior_by_ticker = {state.ticker: state for state in before.tickers}
    current_by_ticker = {state.ticker: state for state in after.tickers}
    events: list[ResearchChangeEvent] = []
    for ticker in sorted(set(prior_by_ticker) | set(current_by_ticker)):
        prior = prior_by_ticker.get(ticker, _empty_state(ticker))
        current = current_by_ticker.get(ticker, _empty_state(ticker))
        events.extend(_readiness_events(before, after, prior, current))
        events.extend(_filing_events(before, after, prior, current))
        events.extend(_fundamental_events(before, after, prior, current))
        events.extend(_context_events(before, after, prior, current))
    deduplicated = {event.event_id: event for event in events}
    return tuple(
        sorted(
            deduplicated.values(),
            key=lambda event: (event.ticker, event.family, event.subtype, event.source_ref, event.event_id),
        )
    )


def compare_optional_snapshots(
    before: ResearchChangeSnapshot | None,
    after: ResearchChangeSnapshot | None,
) -> ResearchChangeResult:
    if before is None:
        return ResearchChangeResult("baseline_missing", (), "A prior comparable snapshot is required.")
    if after is None:
        return ResearchChangeResult("current_missing", (), "A current comparable snapshot is required.")
    events = compare_research_snapshots(before, after)
    return ResearchChangeResult(
        "changes_detected" if events else "no_changes",
        events,
        f"Detected {len(events)} evidence-backed research change event(s)." if events else "No evidence-backed changes detected.",
    )


def render_change_monitor(result: ResearchChangeResult) -> str:
    if not result.events:
        return f"Research Change Monitor\nStatus: {result.status}\n{result.message}"
    lines = ["Research Change Monitor", f"Status: {result.status}", f"Events: {len(result.events)}"]
    lines.extend(
        f"- {event.ticker} | {event.subtype} | {event.prior_value or '-'} -> {event.current_value or '-'} | {event.suggested_research_task}"
        for event in result.events
    )
    return "\n".join(lines)


def event_payload(event: ResearchChangeEvent) -> dict[str, str]:
    return asdict(event)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare two generated research state snapshots without changing data.")
    parser.add_argument("--before")
    parser.add_argument("--after", required=True)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    before_path = Path(args.before) if args.before else None
    before = load_research_change_snapshot(before_path) if before_path and before_path.is_file() else None
    after_path = Path(args.after)
    if not after_path.is_file():
        raise ValueError(f"Current research change snapshot is missing: {after_path}")
    result = compare_optional_snapshots(before, load_research_change_snapshot(after_path))
    if args.json:
        print(
            json.dumps(
                {
                    "status": result.status,
                    "message": result.message,
                    "events": [event_payload(event) for event in result.events],
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(render_change_monitor(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
