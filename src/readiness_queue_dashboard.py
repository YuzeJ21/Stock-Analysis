from __future__ import annotations

import re
from typing import Callable

import pandas as pd


def _format_missing(value: object, fallback: str = "Not available") -> str:
    if value is None:
        return fallback
    try:
        if pd.isna(value):
            return fallback
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return text if text and text.lower() not in {"nan", "none", "null"} else fallback


def _compact_fragment(value: object, *, fallback: str = "Not available", max_chars: int = 140) -> str:
    text = " ".join(_format_missing(value, fallback).split())
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 3)].rstrip() + "..."


def _label(value: object) -> str:
    text = _format_missing(value, "not available").replace("_", " ").replace("-", " ")
    return " ".join(part.capitalize() for part in text.split())


def readiness_queue_lane_key(value: object) -> str:
    text = _format_missing(value, "").strip().lower()
    if "fundamental" in text or "dcf" in text:
        return "fundamentals"
    if "peer mapping" in text:
        return "peer_mapping"
    if "peer valuation" in text:
        return "peer_valuation_inputs"
    if "metric" in text:
        return "metrics"
    if "earnings" in text:
        return "earnings"
    if "analyst" in text or "estimate" in text:
        return "analyst_estimates"
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_") or "readiness"


def _dashboard_bool(value: object) -> bool:
    return str(value or "").strip().lower() in {"true", "1", "yes", "y"}


def _frame_column(frame: pd.DataFrame | None, *candidates: str) -> str | None:
    if frame is None or frame.empty:
        return None
    lower_to_original = {str(column).strip().lower(): str(column) for column in frame.columns}
    for candidate in candidates:
        column = lower_to_original.get(candidate.strip().lower())
        if column is not None:
            return column
    return None


def _top_readiness_examples(
    frame: pd.DataFrame | None,
    *,
    mask_builder: Callable[[pd.DataFrame], pd.Series],
    reason_columns: tuple[str, ...],
    limit: int = 3,
) -> str:
    if frame is None or frame.empty:
        return "No saved example rows available."
    ticker_col = _frame_column(frame, "ticker", "Ticker", "proposed_ticker", "Proposed Ticker")
    if ticker_col is None:
        return "No ticker examples available in saved rows."
    try:
        mask = mask_builder(frame)
    except Exception:
        mask = pd.Series([False] * len(frame), index=frame.index)
    work = frame.loc[mask].head(max(limit, 0))
    examples: list[str] = []
    for _, row in work.iterrows():
        ticker = _format_missing(row.get(ticker_col), "TICKER").upper()
        reason = ""
        for reason_col in reason_columns:
            actual = _frame_column(frame, reason_col)
            if actual is None:
                continue
            reason = _compact_fragment(row.get(actual), fallback="", max_chars=110)
            if reason:
                break
        examples.append(f"{ticker}: {reason or 'blocked input visible'}")
    return "; ".join(examples) if examples else "No current blocker examples in the saved capped rows."


def _queue_metric_examples(metric_queue_frame: pd.DataFrame | None, *, limit: int = 3) -> str:
    if metric_queue_frame is None or metric_queue_frame.empty:
        return "No metric-readiness rows available."
    blocker_col = _frame_column(metric_queue_frame, "Top Blocker")
    state_col = _frame_column(metric_queue_frame, "Overall State")
    if blocker_col is None:
        return "No metric blocker examples available."
    blockers = metric_queue_frame[blocker_col].fillna("").astype(str).str.lower()
    mask = blockers.ne("none") & blockers.ne("")
    if state_col is not None:
        states = metric_queue_frame[state_col].fillna("").astype(str).str.lower()
        mask = mask | states.isin({"partial", "blocked"})
    work = metric_queue_frame.loc[mask].head(max(limit, 0))
    examples: list[str] = []
    for _, row in work.iterrows():
        ticker = _format_missing(row.get(_frame_column(metric_queue_frame, "Ticker") or "Ticker"), "TICKER").upper()
        benchmark = _format_missing(row.get(_frame_column(metric_queue_frame, "Benchmark") or "Benchmark"), "benchmark")
        family = _format_missing(
            row.get(_frame_column(metric_queue_frame, "Blocker Family") or "Blocker Family"),
            "metric blocker",
        )
        blocker = _compact_fragment(row.get(blocker_col), fallback="blocked metric", max_chars=80)
        examples.append(f"{ticker} vs {benchmark}: {family} - {blocker}")
    return "; ".join(examples) if examples else "No metric blockers in the capped rows."


def queue_proof_packet_command(lane_key: str) -> str:
    command_by_lane = {
        "fundamentals": "DRY_RUN=1 make reviewed-batch LANE=fundamentals TOP_N=10",
        "peer_mapping": "DRY_RUN=1 make reviewed-batch LANE=peers TOP_N=10",
        "peer_valuation_inputs": "DRY_RUN=1 make reviewed-batch LANE=peers TOP_N=10",
        "metrics": "DRY_RUN=1 make reviewed-batch LANE=metrics TOP_N=10",
        "earnings": "DRY_RUN=1 make reviewed-batch LANE=optional_context TOP_N=10",
        "analyst_estimates": "DRY_RUN=1 make reviewed-batch LANE=optional_context TOP_N=10",
    }
    return command_by_lane.get(lane_key, "DRY_RUN=1 make reviewed-batch LANE=prices TOP_N=10")


def _queue_latest_proof_status(batch_proof_frame: pd.DataFrame | None, lane_key: str) -> str:
    if batch_proof_frame is None or batch_proof_frame.empty:
        return "No reviewed batch proof row recorded yet."
    lane_aliases = _queue_lane_aliases(lane_key)
    lane_col = _frame_column(batch_proof_frame, "Lane")
    if lane_col is None:
        return "Proof ledger rows exist, but lane status is unavailable."
    lanes = batch_proof_frame[lane_col].fillna("").astype(str).str.lower().str.strip()
    matches = batch_proof_frame.loc[lanes.isin(lane_aliases)]
    if matches.empty:
        return "No reviewed batch proof row recorded for this lane yet."
    latest = _latest_proof_row(matches)
    outcome = _format_missing(
        _row_value(latest, batch_proof_frame, "Final Outcome", "final_outcome"),
        "outcome not recorded",
    )
    review_date = _format_missing(
        _row_value(latest, batch_proof_frame, "Review Date", "review_date"),
        "date not recorded",
    )
    batch_id = _format_missing(
        _row_value(latest, batch_proof_frame, "Batch ID", "batch_id"),
        "batch id not recorded",
    )
    return f"{outcome} on {review_date}; batch {batch_id}."


def _queue_lane_aliases(lane_key: str) -> set[str]:
    return {
        "fundamentals": {"fundamentals", "fundamentals_dcf", "share_count"},
        "peer_mapping": {"peers", "peer_mapping", "peer_valuation_inputs"},
        "peer_valuation_inputs": {"peers", "peer_mapping", "peer_valuation_inputs"},
        "metrics": {"metrics"},
        "earnings": {"optional_context", "earnings"},
        "analyst_estimates": {"optional_context", "analyst_estimates"},
    }.get(lane_key, {lane_key})


def _row_value(row: pd.Series, frame: pd.DataFrame, *candidates: str) -> object:
    column = _frame_column(frame, *candidates)
    return row.get(column) if column is not None else None


def _latest_proof_row(frame: pd.DataFrame) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=object)
    review_col = _frame_column(frame, "Review Date", "review_date")
    batch_col = _frame_column(frame, "Batch ID", "batch_id")
    sort_columns = [column for column in (review_col, batch_col) if column is not None]
    if not sort_columns:
        return frame.iloc[0]
    return frame.sort_values(sort_columns, ascending=[False] * len(sort_columns)).iloc[0]


def _outcome_operator_cue(outcome: str) -> str:
    if outcome == "supported":
        return "Latest reviewed batch outcome is supported; keep source proof and generated-artifact review visible."
    if outcome == "still_blocked":
        return "Latest reviewed batch outcome is still blocked; use the lane drawer for the missing proof step."
    if outcome == "skipped":
        return "Latest reviewed batch outcome was skipped; reopen only when source proof or scope changes."
    if outcome == "excluded":
        return "Latest reviewed batch outcome was excluded; preserve the not-applicable boundary."
    return "No reviewed batch outcome recorded yet; open the lane drawer before recording a final outcome."


def build_readiness_queue_outcome_summary_frame(
    queue_frame: pd.DataFrame | None,
    batch_proof_frame: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Summarize the latest reviewed batch outcome for each readiness queue lane."""

    if queue_frame is None or queue_frame.empty:
        return pd.DataFrame(
            [
                {
                    "Lane": "Readiness queue",
                    "Queue State": "blocked",
                    "Latest Outcome": "not_recorded",
                    "Review Date": "not recorded",
                    "Batch ID": "not recorded",
                    "Changed Tickers": "not recorded",
                    "Changed Readiness Counts": "not recorded",
                    "Operator Cue": "Run make readiness-queue TOP_N=10 before reviewing lane outcomes.",
                    "Next Safe Action": "make readiness-queue TOP_N=10",
                    "Proof Ledger Command": "make reviewed-batch-proof",
                }
            ]
        )
    rows: list[dict[str, object]] = []
    for _, queue_row in queue_frame.iterrows():
        lane = _format_missing(queue_row.get("Lane"), "Readiness lane")
        lane_key = readiness_queue_lane_key(lane)
        latest = pd.Series(dtype=object)
        if batch_proof_frame is not None and not batch_proof_frame.empty:
            lane_col = _frame_column(batch_proof_frame, "Lane", "lane")
            if lane_col is not None:
                lanes = batch_proof_frame[lane_col].fillna("").astype(str).str.lower().str.strip()
                matches = batch_proof_frame.loc[lanes.isin(_queue_lane_aliases(lane_key))]
                if not matches.empty:
                    latest = _latest_proof_row(matches)
        outcome = _format_missing(
            _row_value(latest, batch_proof_frame, "Final Outcome", "final_outcome")
            if batch_proof_frame is not None and not latest.empty
            else None,
            "not_recorded",
        ).lower()
        rows.append(
            {
                "Lane": lane,
                "Queue State": _label(queue_row.get("State")),
                "Latest Outcome": outcome,
                "Review Date": _format_missing(
                    _row_value(latest, batch_proof_frame, "Review Date", "review_date")
                    if batch_proof_frame is not None and not latest.empty
                    else None,
                    "not recorded",
                ),
                "Batch ID": _format_missing(
                    _row_value(latest, batch_proof_frame, "Batch ID", "batch_id")
                    if batch_proof_frame is not None and not latest.empty
                    else None,
                    "not recorded",
                ),
                "Changed Tickers": _compact_fragment(
                    _row_value(latest, batch_proof_frame, "Changed Tickers", "changed_tickers")
                    if batch_proof_frame is not None and not latest.empty
                    else None,
                    fallback="not recorded",
                    max_chars=120,
                ),
                "Changed Readiness Counts": _compact_fragment(
                    _row_value(latest, batch_proof_frame, "Changed Readiness Counts", "changed_readiness_counts")
                    if batch_proof_frame is not None and not latest.empty
                    else None,
                    fallback="not recorded",
                    max_chars=150,
                ),
                "Operator Cue": _outcome_operator_cue(outcome),
                "Next Safe Action": _format_missing(
                    queue_row.get("Next Safe Command"),
                    queue_proof_packet_command(lane_key),
                ),
                "Proof Ledger Command": "make reviewed-batch-proof",
            }
        )
    return pd.DataFrame(rows)


def _queue_lane_examples(
    lane_key: str,
    *,
    ticker_readiness_frame: pd.DataFrame | None,
    peer_readiness_frame: pd.DataFrame | None,
    metric_queue_frame: pd.DataFrame | None,
) -> str:
    if lane_key == "fundamentals":
        return _top_readiness_examples(
            ticker_readiness_frame,
            mask_builder=lambda frame: ~frame.get("dcf_ready", pd.Series(False, index=frame.index)).map(_dashboard_bool)
            | ~frame.get("fundamentals_ready", pd.Series(False, index=frame.index)).map(_dashboard_bool),
            reason_columns=("missing_data", "blocked_features", "next_action"),
        )
    if lane_key == "peer_mapping":
        return _top_readiness_examples(
            peer_readiness_frame,
            mask_builder=lambda frame: frame.get(
                "peer_blocker_type",
                pd.Series("", index=frame.index),
            )
            .astype(str)
            .str.lower()
            .eq("missing_peer_mapping"),
            reason_columns=("missing_peer_reason", "peer_blocker_type", "mapping_status"),
        )
    if lane_key == "peer_valuation_inputs":
        return _top_readiness_examples(
            peer_readiness_frame,
            mask_builder=lambda frame: ~frame.get(
                "peer_valuation_comparison_ready",
                pd.Series(False, index=frame.index),
            ).map(_dashboard_bool)
            & ~frame.get("peer_blocker_type", pd.Series("", index=frame.index)).astype(str).str.lower().eq(
                "missing_peer_mapping"
            ),
            reason_columns=("missing_peer_reason", "peer_blocker_type", "peer_valuation_status"),
        )
    if lane_key == "metrics":
        return _queue_metric_examples(metric_queue_frame)
    if lane_key == "earnings":
        return _top_readiness_examples(
            ticker_readiness_frame,
            mask_builder=lambda frame: ~frame.get("earnings_ready", pd.Series(False, index=frame.index)).map(_dashboard_bool),
            reason_columns=("missing_data", "blocked_features", "next_action"),
        )
    if lane_key == "analyst_estimates":
        return _top_readiness_examples(
            ticker_readiness_frame,
            mask_builder=lambda frame: ~frame.get("analyst_estimates_ready", pd.Series(False, index=frame.index)).map(
                _dashboard_bool
            ),
            reason_columns=("missing_data", "blocked_features", "next_action"),
        )
    return "Open the lane evidence drawer for current examples."


def build_readiness_queue_drilldown_frame(
    queue_frame: pd.DataFrame | None,
    *,
    ticker_readiness_frame: pd.DataFrame | None = None,
    peer_readiness_frame: pd.DataFrame | None = None,
    metric_queue_frame: pd.DataFrame | None = None,
    batch_proof_frame: pd.DataFrame | None = None,
    freshness_status: object | None = None,
) -> pd.DataFrame:
    """Build compact per-lane drawer rows for the post-price readiness queue."""

    if queue_frame is None or queue_frame.empty:
        return pd.DataFrame(
            [
                {
                    "Lane": "Readiness queue",
                    "State": "blocked",
                    "Top Blocker Examples": "Run make readiness-queue TOP_N=10 after readiness artifacts exist.",
                    "Proof Packet Command": "make readiness-queue TOP_N=10",
                    "Stale / Source Warning": "Queue rows are unavailable.",
                    "Proof Record Status": "No reviewed batch proof row recorded yet.",
                    "Next Safe Action": "make readiness-queue TOP_N=10",
                }
            ]
        )
    rows: list[dict[str, object]] = []
    freshness_warning = ""
    if freshness_status is not None and getattr(freshness_status, "status", None) in {"missing", "stale"}:
        freshness_warning = f"{_label(getattr(freshness_status, 'status', 'stale'))}: {getattr(freshness_status, 'message', '')}"
    for _, row in queue_frame.iterrows():
        lane = _format_missing(row.get("Lane"), "Readiness lane")
        lane_key = readiness_queue_lane_key(lane)
        proof_gate = _compact_fragment(row.get("Proof Gate"), fallback="Open evidence drawer.", max_chars=160)
        source_mode = _format_missing(row.get("Source Mode"), "local readiness")
        source_warning = freshness_warning or f"Source mode: {source_mode}. {proof_gate}"
        rows.append(
            {
                "Lane": lane,
                "State": _label(row.get("State")),
                "Top Blocker Examples": _queue_lane_examples(
                    lane_key,
                    ticker_readiness_frame=ticker_readiness_frame,
                    peer_readiness_frame=peer_readiness_frame,
                    metric_queue_frame=metric_queue_frame,
                ),
                "Proof Packet Command": queue_proof_packet_command(lane_key),
                "Stale / Source Warning": source_warning,
                "Proof Record Status": _queue_latest_proof_status(batch_proof_frame, lane_key),
                "Next Safe Action": _format_missing(row.get("Next Safe Command"), queue_proof_packet_command(lane_key)),
            }
        )
    return pd.DataFrame(rows)


def _queue_lane_batch_lane(lane: object) -> str:
    lane_key = readiness_queue_lane_key(lane)
    return {
        "fundamentals": "fundamentals",
        "peer_mapping": "peers",
        "peer_valuation_inputs": "peers",
        "metrics": "metrics",
        "earnings": "optional_context",
        "analyst_estimates": "optional_context",
    }.get(lane_key, "prices")


def _queue_lane_operator_lane(lane: object) -> str:
    lane_key = readiness_queue_lane_key(lane)
    return {
        "fundamentals": "fundamentals",
        "peer_mapping": "peers",
        "peer_valuation_inputs": "peers",
        "metrics": "metrics",
        "earnings": "optional",
        "analyst_estimates": "optional",
    }.get(lane_key, "prices")


def _queue_lane_drawer_route(lane: object, drawer: str) -> str:
    operator_lane = _queue_lane_operator_lane(lane)
    clean_drawer = re.sub(r"[^a-z0-9-]+", "-", str(drawer or "queue").strip().lower()).strip("-") or "queue"
    return f"?mode=operator&page=data-health&lane={operator_lane}&drawer={clean_drawer}"


def _proof_lane_drawer_route(drawer: str) -> str:
    clean_drawer = re.sub(r"[^a-z0-9-]+", "-", str(drawer or "proof").strip().lower()).strip("-") or "proof"
    return f"?mode=operator&page=data-health&lane=proof&drawer={clean_drawer}"


def _queue_lane_gate_action(lane: object) -> tuple[str, str, str]:
    lane_key = readiness_queue_lane_key(lane)
    if lane_key == "metrics":
        return (
            "read_only_metric_review",
            "Metrics stay read-only; review readiness rows and do not run import/apply commands.",
            "make metric-readiness-board TOP_N=10",
        )
    if lane_key in {"earnings", "analyst_estimates"}:
        return (
            "optional_trusted_local_only",
            "Optional context stays locked unless trusted local rows exist and pass validate / preview checks.",
            "make imports-validate && make imports-preview",
        )
    if lane_key in {"peer_mapping", "peer_valuation_inputs"}:
        return (
            "validate_preview_apply",
            "Peer rows need source-backed relationships or mapped-peer inputs before any reviewed apply.",
            "make imports-validate && make imports-preview",
        )
    return (
        "validate_preview_apply",
        "Fundamentals rows need trusted SEC/manual source proof before any reviewed apply.",
        "make imports-validate && make imports-preview",
    )


def build_readiness_queue_lane_action_frame(row: pd.Series | dict[str, object]) -> pd.DataFrame:
    """Return the compact lane-local packet -> proof-record checklist."""

    get_value = row.get if isinstance(row, dict) else row.get
    lane = _format_missing(get_value("Lane"), "Readiness lane")
    batch_lane = _queue_lane_batch_lane(lane)
    packet_command = _format_missing(
        get_value("Proof Packet Command"),
        queue_proof_packet_command(readiness_queue_lane_key(lane)),
    )
    source_warning = _format_missing(get_value("Stale / Source Warning"), "Review source readiness before proceeding.")
    proof_status = _format_missing(get_value("Proof Record Status"), "No reviewed batch proof row recorded yet.")
    gate_status, gate_decision, gate_command = _queue_lane_gate_action(lane)
    compare_command = f"make reviewed-batch-compare LANE={batch_lane} BATCH_ID=<batch_id> REVIEW_DATE=<yyyy-mm-dd>"
    proof_command = (
        "DRY_RUN=1 make reviewed-batch-proof-record "
        "BATCH_ID=<batch_id> "
        f"LANE={batch_lane} "
        "REVIEW_DATE=<yyyy-mm-dd> "
        "FINAL_OUTCOME=<supported|still_blocked|skipped|excluded>"
    )
    return pd.DataFrame(
        [
            {
                "Step": "1. Packet",
                "Status": "copy-only",
                "Operator Decision": f"Preview the capped {lane} scope before any row-level review.",
                "Drawer Route": _queue_lane_drawer_route(lane, "queue"),
                "Route Boundary": "navigation-only; dashboard does not run commands or write data",
                "Copy-Only Command": packet_command,
                "Stop If": source_warning,
            },
            {
                "Step": "2. Validate / preview gate",
                "Status": gate_status,
                "Operator Decision": gate_decision,
                "Drawer Route": _queue_lane_drawer_route(lane, "source-proof"),
                "Route Boundary": "navigation-only; keep validate, preview, and apply as explicit reviewed commands",
                "Copy-Only Command": gate_command,
                "Stop If": "validation fails, preview shows unexpected rows, source proof is missing, or the lane is read-only",
            },
            {
                "Step": "3. Compare readiness",
                "Status": "after reviewed packet/run",
                "Operator Decision": "Use changed readiness counts and changed tickers as proof; no inferred unlocks.",
                "Drawer Route": _proof_lane_drawer_route("comparison"),
                "Route Boundary": "navigation-only; compare snapshots before recording any outcome",
                "Copy-Only Command": compare_command,
                "Stop If": "baseline snapshot or current readiness report is missing",
            },
            {
                "Step": "4. Proof-record command",
                "Status": proof_status,
                "Operator Decision": "Record only supported, still_blocked, skipped, or excluded after final review.",
                "Drawer Route": _proof_lane_drawer_route("proof-record"),
                "Route Boundary": "navigation-only; proof rows stay dry-run-first until required fields are reviewed",
                "Copy-Only Command": proof_command,
                "Stop If": "required fields still contain placeholders",
            },
            {
                "Step": "5. Artifact hygiene",
                "Status": "required before staging",
                "Operator Decision": "Classify generated CSV/JSON churn before any commit recommendation.",
                "Drawer Route": _proof_lane_drawer_route("artifacts"),
                "Route Boundary": "navigation-only; generated churn stays excluded unless intentionally reviewed evidence",
                "Copy-Only Command": "make diff-hygiene",
                "Stop If": "generated artifacts are dirty and not intentionally reviewed evidence",
            },
        ]
    )


def build_readiness_queue_route_cards(row: pd.Series | dict[str, object]) -> list[dict[str, object]]:
    """Return readable queue -> proof routing cards before the detailed action table."""

    get_value = row.get if isinstance(row, dict) else row.get
    lane = _format_missing(get_value("Lane"), "Readiness lane")
    lane_key = readiness_queue_lane_key(lane)
    batch_lane = _queue_lane_batch_lane(lane)
    packet_command = _format_missing(get_value("Proof Packet Command"), queue_proof_packet_command(lane_key))
    source_warning = _compact_fragment(
        get_value("Stale / Source Warning"),
        fallback="Review source readiness before proceeding.",
        max_chars=180,
    )
    proof_status = _compact_fragment(
        get_value("Proof Record Status"),
        fallback="No reviewed batch proof row recorded yet.",
        max_chars=160,
    )
    gate_status, gate_decision, gate_command = _queue_lane_gate_action(lane)

    return [
        {
            "kicker": "ROUTE 1",
            "title": f"{lane}: open queue packet",
            "body": (
                f"Start at {_queue_lane_drawer_route(lane, 'queue')} to review capped scope and blockers. "
                "This route is navigation-only; it does not run commands or write rows."
            ),
            "badges": ["queue first", "navigation-only"],
            "command": packet_command,
        },
        {
            "kicker": "ROUTE 2",
            "title": "Open source-proof gate before apply decisions",
            "body": (
                f"Gate state: {gate_status}. {gate_decision} Source warning: {source_warning}. "
                "Keep validate, preview, rejected-row review, and apply/skip as explicit reviewed steps."
            ),
            "badges": ["validate -> preview", "manual gate"],
            "command": gate_command,
        },
        {
            "kicker": "ROUTE 3",
            "title": "Compare readiness before proof record",
            "body": (
                f"Use {_proof_lane_drawer_route('comparison')} for before/after readiness proof, then "
                f"{_proof_lane_drawer_route('proof-record')} for the dry-run proof record. Current proof status: {proof_status}."
            ),
            "badges": ["compare first", "dry-run proof"],
            "command": f"make reviewed-batch-compare LANE={batch_lane} BATCH_ID=<batch_id> REVIEW_DATE=<yyyy-mm-dd>",
        },
        {
            "kicker": "ROUTE 4",
            "title": "Review generated artifacts before staging",
            "body": (
                f"Use {_proof_lane_drawer_route('artifacts')} to classify generated CSV/JSON/report churn before any commit package. "
                "Broad generated churn stays excluded unless it is intentionally reviewed evidence."
            ),
            "badges": ["artifact hygiene", "exclude churn"],
            "command": "make diff-hygiene",
        },
        {
            "kicker": "STOP RULE",
            "title": "Do not treat a route as an unlock",
            "body": (
                "Navigation links only move the operator through evidence. Missing source inputs stay blocked until "
                "reviewed source proof, validation, preview, rejected-row review, explicit apply/skip, rebuilt readiness, "
                "and proof record pass."
            ),
            "badges": ["blocked stays blocked", "research-only"],
            "command": "make diff-hygiene",
        },
    ]


def build_readiness_queue_route_strip_cards(row: pd.Series | dict[str, object]) -> list[dict[str, object]]:
    """Return a compact selected-lane workflow strip before queue drawer details."""

    get_value = row.get if isinstance(row, dict) else row.get
    lane = _format_missing(get_value("Lane"), "Readiness lane")
    lane_key = readiness_queue_lane_key(lane)
    queue_state = _label(get_value("State"))
    proof_status = _compact_fragment(
        get_value("Proof Record Status"),
        fallback="No reviewed batch proof row recorded yet.",
        max_chars=110,
    )
    next_action = _format_missing(get_value("Next Safe Action"), queue_proof_packet_command(lane_key))
    source_warning = _compact_fragment(
        get_value("Stale / Source Warning"),
        fallback="Review source readiness before proceeding.",
        max_chars=120,
    )
    gate_status, _, _ = _queue_lane_gate_action(lane)
    return [
        {
            "kicker": "WHERE AM I",
            "title": f"{lane}: {queue_state}",
            "body": "Selected lane is in the readiness queue. Open details only after the lane and gate are clear.",
            "badges": ["selected lane", "operator flow"],
        },
        {
            "kicker": "PREVIOUS PROOF",
            "title": proof_status,
            "body": "Latest reviewed-batch proof is context only; it does not unlock the current lane without fresh readiness proof.",
            "badges": ["proof ledger", "read-only"],
        },
        {
            "kicker": "NEXT SAFE ACTION",
            "title": next_action,
            "body": f"Gate status: {gate_status}. Source/freshness note: {source_warning}. Commands remain copy-only.",
            "badges": ["copy-only", "validate before apply"],
            "command": next_action,
        },
        {
            "kicker": "STOP RULE",
            "title": "Keep missing inputs blocked",
            "body": "Stop before any supported outcome if source proof, validation, preview, rejected-row review, apply/skip, rebuilt readiness, or artifact review is missing.",
            "badges": ["blocked stays blocked", "research-only"],
        },
    ]
