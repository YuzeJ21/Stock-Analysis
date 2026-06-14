"""Generate reviewed batch run packets for data-readiness lanes.

This module writes copy-only batch packets. It does not refresh providers,
import rows, apply staged data, route orders, or produce investment advice.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from src.readiness_ops import ReadinessLane, build_readiness_ops_lanes


DEFAULT_PACKET_MD = Path("outputs/reviewed_batch_packet.md")
DEFAULT_PACKET_CSV = Path("outputs/reviewed_batch_packet.csv")
REQUIRED_READINESS_REPORTS = (
    "data/reports/ticker_readiness_report.csv",
    "data/reports/feature_readiness_summary.csv",
)
SOURCE_FILES_FOR_FRESHNESS = (
    "data/prices.csv",
    "data/fundamentals.csv",
    "data/peers.csv",
    "data/earnings.csv",
    "data/analyst_estimates.csv",
)
PROOF_TEMPLATE_FIELDS = (
    "batch_id",
    "lane",
    "scope",
    "tickers",
    "pre_run_readiness_snapshot",
    "command_run",
    "validation_result",
    "preview_result",
    "apply_result",
    "post_run_readiness_snapshot",
    "changed_readiness_counts",
    "changed_tickers",
    "reviewer",
    "review_date",
    "source_files",
    "generated_artifacts_reviewed",
    "final_outcome",
    "notes",
)
FINAL_OUTCOME_OPTIONS = ("supported", "still_blocked", "skipped", "excluded")
ACTION_COLUMNS = (
    "batch_id",
    "lane",
    "lane_label",
    "ticker_scope",
    "proposed_ticker",
    "workflow_mode",
    "source_context",
    "freshness_status",
    "dry_run_command",
    "capped_execution_command",
    "validation_command",
    "preview_command",
    "apply_command",
    "post_run_verification",
    "readiness_comparison_command",
    "proof_record_command",
    "expected_artifacts",
    "rollback",
    "do_not_proceed_if",
    "pre_run_readiness_snapshot",
    "command_run",
    "validation_result",
    "preview_result",
    "apply_result",
    "post_run_readiness_snapshot",
    "changed_readiness_counts",
    "changed_tickers",
    "reviewer",
    "review_date",
    "source_files",
    "generated_artifacts_reviewed",
    "final_outcome",
    "notes",
)


@dataclass(frozen=True)
class FreshnessStatus:
    status: str
    message: str
    refresh_command: str = "make readiness"


@dataclass(frozen=True)
class ReviewedBatchAction:
    batch_id: str
    lane: str
    lane_label: str
    ticker_scope: str
    proposed_ticker: str
    workflow_mode: str
    source_context: str
    freshness_status: str
    dry_run_command: str
    capped_execution_command: str
    validation_command: str
    preview_command: str
    apply_command: str
    post_run_verification: str
    readiness_comparison_command: str
    proof_record_command: str
    expected_artifacts: str
    rollback: str
    do_not_proceed_if: str
    pre_run_readiness_snapshot: str
    command_run: str
    validation_result: str
    preview_result: str
    apply_result: str
    post_run_readiness_snapshot: str
    changed_readiness_counts: str
    changed_tickers: str
    reviewer: str
    review_date: str
    source_files: str
    generated_artifacts_reviewed: str
    final_outcome: str
    notes: str


@dataclass(frozen=True)
class ReviewedBatchPacket:
    batch_id: str
    selected_lane: str
    selected_scope: str
    top_n: int
    tickers: tuple[str, ...]
    freshness: FreshnessStatus
    lanes: tuple[ReadinessLane, ...]
    actions: tuple[ReviewedBatchAction, ...]


LANE_ALIASES = {
    "price": ("price_coverage",),
    "prices": ("price_coverage",),
    "price_coverage": ("price_coverage",),
    "fundamental": ("fundamentals_dcf",),
    "fundamentals": ("fundamentals_dcf",),
    "dcf": ("fundamentals_dcf",),
    "fundamentals_dcf": ("fundamentals_dcf",),
    "peer": ("peer_mapping", "peer_valuation_inputs"),
    "peers": ("peer_mapping", "peer_valuation_inputs"),
    "peer_mapping": ("peer_mapping",),
    "peer_valuation": ("peer_valuation_inputs",),
    "peer_valuation_inputs": ("peer_valuation_inputs",),
    "optional": ("earnings_locked", "analyst_estimates_locked"),
    "optional_context": ("earnings_locked", "analyst_estimates_locked"),
    "earnings": ("earnings_locked",),
    "analyst_estimates": ("analyst_estimates_locked",),
    "metric": ("metric_readiness_review",),
    "metrics": ("metric_readiness_review",),
    "review_metrics": ("metric_readiness_review",),
    "metric_readiness": ("metric_readiness_review",),
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, rows: Iterable[ReviewedBatchAction]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ACTION_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for action in rows:
            writer.writerow({column: getattr(action, column) for column in ACTION_COLUMNS})


def _truthy(value: object) -> bool:
    return str(value or "").strip().lower() in {"true", "1", "yes", "y"}


def _clean(value: object, fallback: str = "-") -> str:
    text = str(value or "").strip()
    if not text or text.lower() == "nan":
        return fallback
    return text


def _split_tickers(value: str | Iterable[str] | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        raw_values = value.split(",")
    else:
        raw_values = list(value)
    return tuple(dict.fromkeys(str(item).strip().upper() for item in raw_values if str(item).strip()))


def normalize_batch_lane(value: str) -> tuple[str, ...]:
    key = str(value or "").strip().lower().replace("-", "_")
    if key in LANE_ALIASES:
        return LANE_ALIASES[key]
    raise ValueError("Unknown reviewed batch lane. Use prices, fundamentals, peers, metrics, or optional_context.")


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return 0.0


def readiness_freshness_status(root: Path) -> FreshnessStatus:
    missing = [path for path in REQUIRED_READINESS_REPORTS if not (root / path).exists()]
    if missing:
        return FreshnessStatus(
            "missing",
            "Missing readiness artifact(s): "
            + ", ".join(missing)
            + ". Run make readiness before using this packet for execution.",
        )
    readiness_time = min(_mtime(root / path) for path in REQUIRED_READINESS_REPORTS)
    newer_sources = [path for path in SOURCE_FILES_FOR_FRESHNESS if _mtime(root / path) > readiness_time]
    if newer_sources:
        return FreshnessStatus(
            "stale",
            "Readiness artifacts may be stale because source file(s) changed after the saved reports: "
            + ", ".join(newer_sources)
            + ". Run make readiness before relying on final counts.",
        )
    return FreshnessStatus("current", "Readiness artifacts are current relative to watched source files.")


def _ticker_from_rows(rows: list[dict[str, str]], field: str = "ticker") -> list[str]:
    values: list[str] = []
    for row in rows:
        ticker = str(row.get(field) or "").strip().upper()
        if ticker and ticker not in values:
            values.append(ticker)
    return values


def _candidate_tickers(root: Path, lane: str, top_n: int, selected_tickers: tuple[str, ...]) -> tuple[str, ...]:
    if selected_tickers:
        return selected_tickers[: max(top_n, 0)]
    reports = root / "data" / "reports"
    rows: list[dict[str, str]]
    if lane == "price_coverage":
        rows = [
            row
            for row in _read_csv(reports / "price_coverage_report.csv")
            if not _truthy(row.get("price_ready"))
        ]
    elif lane == "fundamentals_dcf":
        rows = [
            row
            for row in _read_csv(reports / "fundamentals_coverage_report.csv")
            if not _truthy(row.get("fundamentals_ready"))
        ]
    elif lane in {"peer_mapping", "peer_valuation_inputs"}:
        rows = _read_csv(reports / "peer_unlock_worklist.csv")
    elif lane == "earnings_locked":
        rows = [
            row
            for row in _read_csv(reports / "earnings_readiness_report.csv")
            if not _truthy(row.get("has_trusted_earnings"))
        ]
    elif lane == "analyst_estimates_locked":
        rows = [
            row
            for row in _read_csv(reports / "analyst_estimates_readiness_report.csv")
            if not _truthy(row.get("has_trusted_analyst_estimates"))
        ]
    elif lane == "metric_readiness_review":
        rows = [
            row
            for row in _read_csv(reports / "ticker_readiness_report.csv")
            if str(row.get("overall_readiness_state") or "").strip().lower() != "excluded"
        ]
    else:
        rows = []
    if not rows:
        rows = _read_csv(reports / "ticker_readiness_report.csv")
    return tuple(_ticker_from_rows(rows)[: max(top_n, 0)])


def _join_ticker_arg(tickers: tuple[str, ...]) -> str:
    return ",".join(tickers) if tickers else "<reviewed_scope>"


def _lane_commands(lane: str, tickers: tuple[str, ...], top_n: int) -> dict[str, str]:
    ticker_arg = _join_ticker_arg(tickers)
    if lane == "price_coverage":
        return {
            "dry_run": f"make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N={top_n} PROVIDER=yahoo",
            "execute": f"make price-refresh-loop MAX_CANDIDATES=3500 TOP_N={top_n} PROVIDER=yahoo SLEEP_SECONDS=30",
            "validate": "make price-validate",
            "preview": "make price-preview",
            "apply": "make price-apply only for reviewed trusted rows",
            "post": f"make readiness && make price-coverage TOP_N={top_n} && make status-check TOP_N=5",
            "compare": "make reviewed-batch-compare LANE=prices BATCH_ID=<batch_id> REVIEW_DATE=<yyyy-mm-dd>",
            "artifacts": "data/prices.csv; data/reports/price_coverage_report.csv; outputs/reviewed_batch_packet.csv",
            "rollback": "If refreshed prices are incomplete or suspicious, keep generated CSV churn unstaged and restore reviewed local price files from git or the readiness snapshot.",
        }
    if lane == "fundamentals_dcf":
        return {
            "dry_run": f"make sec-stage-queue TOP_N={top_n}",
            "execute": f"make sec-stage TICKERS={ticker_arg} only if SEC_USER_AGENT is configured, or place reviewed trusted rows in data/imports/fundamentals.csv",
            "validate": "make imports-validate",
            "preview": "make imports-preview",
            "apply": "make imports-apply only after reviewed trusted fundamentals rows pass preview",
            "post": "make readiness && make dcf-readiness && make status-check TOP_N=5",
            "compare": "make reviewed-batch-compare LANE=fundamentals BATCH_ID=<batch_id> REVIEW_DATE=<yyyy-mm-dd>",
            "artifacts": "data/imports/fundamentals.csv; data/fundamentals.csv; data/rejected/fundamentals_import_rejected.csv; data/reports/dcf_readiness_report.csv",
            "rollback": "If preview/rejected rows are wrong, do not apply. If applied rows are wrong, restore data/fundamentals.csv from git/backups and rerun make readiness.",
        }
    if lane == "peer_mapping":
        return {
            "dry_run": f"make peer-mapping-queue TOP_N={top_n}",
            "execute": f"make focus-peers TICKER={tickers[0] if tickers else '<ticker>'}, then add only reviewed source-backed peer mappings to data/imports/peers.csv",
            "validate": "make imports-validate",
            "preview": "make imports-preview",
            "apply": "make imports-apply only after source-backed peer mapping rows are reviewed",
            "post": f"make readiness && make peer-mapping-queue TOP_N={top_n} && make status-check TOP_N=5",
            "compare": "make reviewed-batch-compare LANE=peers BATCH_ID=<batch_id> REVIEW_DATE=<yyyy-mm-dd>",
            "artifacts": "data/imports/peers.csv; data/peers.csv; data/rejected/peers_import_rejected.csv; data/reports/peer_readiness_report.csv; data/reports/peer_unlock_worklist.csv",
            "rollback": "If peer mapping rows are wrong, do not apply. If applied rows are wrong, restore data/peers.csv from git/backups and rerun readiness.",
        }
    if lane == "peer_valuation_inputs":
        return {
            "dry_run": f"make peer-mapping-queue TOP_N={top_n}",
            "execute": f"make focus-peers TICKER={tickers[0] if tickers else '<ticker>'}, then follow mapped-peer dependencies with make focus-fundamentals TICKER=<peer> or verified peer price/market-cap context",
            "validate": "make imports-validate",
            "preview": "make imports-preview",
            "apply": "make imports-apply only after reviewed mapped-peer fundamentals, price, market-cap, or valuation-input rows pass preview",
            "post": f"make readiness && make peer-mapping-queue TOP_N={top_n} && make metric-readiness TICKERS={ticker_arg} BENCHMARK=SPY",
            "compare": "make reviewed-batch-compare LANE=peers BATCH_ID=<batch_id> REVIEW_DATE=<yyyy-mm-dd>",
            "artifacts": "data/imports/fundamentals.csv; data/imports/prices.csv; data/imports/peers.csv if mappings change; data/rejected/fundamentals_import_rejected.csv; data/rejected/price_import_rejected.csv; data/rejected/peers_import_rejected.csv; data/reports/peer_readiness_report.csv; data/reports/peer_unlock_worklist.csv",
            "rollback": "If mapped-peer input rows are wrong, do not apply. If applied rows are wrong, restore the touched canonical fundamentals, prices, or peers CSVs, then rerun readiness.",
        }
    if lane == "metric_readiness_review":
        return {
            "dry_run": f"make metric-readiness-board TOP_N={top_n} TICKERS={ticker_arg}",
            "execute": f"make metric-readiness-board TOP_N={top_n} TICKERS={ticker_arg} BENCHMARKS=SPY,QQQ",
            "validate": "not_applicable_read_only_metric_review",
            "preview": "review metric blocker families, source gates, and row-level missing inputs before any data work",
            "apply": "not_applicable; metrics remain blocked until the underlying trusted source rows are reviewed through their lane",
            "post": f"make readiness && make metric-readiness-board TOP_N={top_n} TICKERS={ticker_arg} BENCHMARKS=SPY,QQQ",
            "compare": "make reviewed-batch-compare LANE=metrics BATCH_ID=<batch_id> REVIEW_DATE=<yyyy-mm-dd>",
            "artifacts": "metric-readiness console output; Data Health Metrics lane; optional reviewed_batch_packet.csv",
            "rollback": "No local data is mutated by metric-readiness review. If follow-up source rows are changed in another lane, use that lane's rollback path.",
        }
    return {
        "dry_run": f"make optional-context-worklist TOP_N={top_n}",
        "execute": f"make templates, then prepare trusted local optional rows for {ticker_arg}",
        "validate": "make imports-validate",
        "preview": "make imports-preview",
        "apply": "make imports-apply only after trusted local earnings/estimate rows pass preview",
        "post": "make optional-context-readiness && make readiness",
        "compare": "make reviewed-batch-compare LANE=optional_context BATCH_ID=<batch_id> REVIEW_DATE=<yyyy-mm-dd>",
        "artifacts": "data/imports/earnings.csv; data/imports/analyst_estimates.csv; data/reports/earnings_readiness_report.csv; data/reports/analyst_estimates_readiness_report.csv",
        "rollback": "If optional rows are wrong, do not apply. If applied rows are wrong, restore earnings/analyst-estimates CSVs and rerun optional-context readiness.",
    }


def _do_not_proceed(lane: ReadinessLane, freshness: FreshnessStatus) -> str:
    blockers = [
        "readiness artifacts are missing or stale",
        "source proof is unavailable",
        "validation fails",
        "preview shows unexpected rows",
        "rejected-row reports contain unresolved rows",
        "the operator cannot identify changed source files",
    ]
    if lane.workflow_mode == "locked_manual":
        blockers.append("trusted local optional-context rows do not exist")
    if lane.lane == "fundamentals_dcf":
        blockers.extend(
            [
                "SEC_USER_AGENT is not configured and no reviewed manual fundamentals rows exist",
                "staged/manual rows do not include required DCF fields such as revenue, free cash flow, shares, cash, or debt when needed",
                "data/rejected/fundamentals_import_rejected.csv has unresolved rows",
            ]
        )
    if lane.lane == "peer_mapping":
        blockers.extend(
            [
                "peer relationship proof is unavailable or only sector/industry similarity exists",
                "data/rejected/peers_import_rejected.csv has unresolved rows",
            ]
        )
    if lane.lane == "peer_valuation_inputs":
        blockers.extend(
            [
                "mapped peers lack trusted fundamentals, price history, market-cap context, or valuation inputs",
                "mapped-peer input rows have not passed validate, preview, and rejected-row review",
            ]
        )
    if lane.lane == "metric_readiness_review":
        blockers.append("the missing metric inputs have not been traced to prices, fundamentals, market cap, or peer-input proof")
    if freshness.status in {"missing", "stale"}:
        blockers.insert(0, f"{freshness.status}: run {freshness.refresh_command}")
    return "; ".join(blockers)


def _lane_proof_instructions(lane: str, top_n: int) -> list[str]:
    if lane == "price_coverage":
        return [
            "Record pre-run price-ready, momentum-ready, liquidity, and correlation counts before any refresh.",
            "Use dry-run output to cap scope; do not treat provider availability as reviewed data.",
            "After execution, rerun readiness and compare changed readiness counts before keeping artifacts.",
            "Use make reviewed-batch-compare after make readiness so the proof ledger records changed counts and changed tickers without guessing.",
        ]
    if lane == "fundamentals_dcf":
        return [
            "Record pre-run fundamentals-ready and DCF-ready counts plus the exact missing fields.",
            "Start from the first-class packet command: make fundamentals-batch-proof TOP_N=<n> or make fundamentals-batch-proof TICKERS=<scope>.",
            "Use make sec-stage-queue TOP_N=<n> for a dry-run queue; run make sec-stage TICKERS=<scope> only when SEC_USER_AGENT is configured.",
            "If SEC staging is unavailable, place only reviewed trusted manual rows in data/imports/fundamentals.csv.",
            "Run make imports-validate and make imports-preview before imports-apply; rejected-row reports must be clear or explained.",
            "After apply, rerun make readiness and make dcf-readiness before calling any ticker supported.",
        ]
    if lane == "peer_mapping":
        return [
            "Record peer_mapping_ready, peer_price_ready, peer_momentum_ready, peer_fundamentals_ready, peer_valuation_ready, and peer_valuation_comparison_ready before changes.",
            "Start from the first-class packet command: make peer-batch-proof TOP_N=<n> or make peer-batch-proof TICKERS=<scope>.",
            f"Inspect missing peer relationships with make peer-mapping-queue TOP_N={top_n} and make focus-peers TICKER=<ticker>.",
            "Treat sector or industry fallback as context only; it is not trusted peer mapping proof.",
            "Run make imports-validate and make imports-preview before imports-apply; data/rejected/peers_import_rejected.csv must be clear or explained.",
            "After reviewed mapping rows, rerun make readiness and make peer-mapping-queue before reading peer valuation dispersion.",
        ]
    if lane == "peer_valuation_inputs":
        return [
            "Record peer_mapping_ready, peer_price_ready, peer_momentum_ready, peer_fundamentals_ready, peer_valuation_ready, and peer_valuation_comparison_ready before changes.",
            "Start from the first-class packet command: make peer-batch-proof TOP_N=<n> or make peer-batch-proof TICKERS=<scope>.",
            f"Inspect the peer valuation sub-lane with make peer-mapping-queue TOP_N={top_n} and make focus-peers TICKER=<ticker>.",
            "Follow the printed mapped-peer dependency with make focus-fundamentals TICKER=<peer> or verified peer price/market-cap proof.",
            "Do not treat mapped peers as valuation-ready until mapped-peer inputs pass validate, preview, rejected-row review, and rebuilt readiness.",
            "After reviewed mapped-peer inputs, rerun make readiness and make peer-mapping-queue before reading peer valuation dispersion.",
        ]
    if lane == "metric_readiness_review":
        return [
            "Record the SPY/QQQ blocker-family summary before opening row-level proof.",
            "Map each blocked metric to its source lane: prices, fundamentals, market context, or peer inputs.",
            "Do not apply rows from the metrics packet; use the underlying reviewed lane packet when source proof exists.",
            "After any reviewed source-lane change, rerun make readiness and make metric-readiness-board before describing the metric as ready.",
        ]
    return [
        "Record pre-run optional context readiness counts.",
        "Apply only trusted local earnings or analyst-estimate rows after validate and preview.",
        "After apply, rerun optional-context readiness and keep unsupported optional context locked where rows are absent.",
    ]


def _proof_template_csv_row(packet: ReviewedBatchPacket) -> str:
    values = {
        "batch_id": packet.batch_id,
        "lane": packet.selected_scope,
        "scope": packet.selected_lane,
        "tickers": ",".join(packet.tickers) if packet.tickers else f"top {packet.top_n}",
        "pre_run_readiness_snapshot": "make readiness-snapshot or saved readiness counts before command",
        "command_run": "<copy exact command>",
        "validation_result": "<pass/fail/not_applicable>",
        "preview_result": "<reviewed rows / no unexpected rows / not_applicable>",
        "apply_result": "<not_run/applied/skipped>",
        "post_run_readiness_snapshot": "make readiness && lane proof command",
        "changed_readiness_counts": "<before -> after counts, or none>",
        "changed_tickers": "<tickers changed, or none>",
        "reviewer": "<name>",
        "review_date": "<YYYY-MM-DD>",
        "source_files": "<trusted local source files reviewed>",
        "generated_artifacts_reviewed": "<CSV/JSON artifacts kept/excluded>",
        "final_outcome": "supported|still_blocked|skipped|excluded",
        "notes": "<source proof, blockers, rollback notes>",
    }
    return ",".join(values[field] for field in PROOF_TEMPLATE_FIELDS)


def _proof_record_scaffold(batch_id: str, lane: str) -> str:
    return (
        "make reviewed-batch-proof-record "
        f'BATCH_ID="{batch_id}" '
        f'LANE="{lane}" '
        'REVIEW_DATE="<yyyy-mm-dd>" '
        'FINAL_OUTCOME="<supported|still_blocked|skipped|excluded>" '
        'COMMAND_RUN="<exact reviewed command>" '
        'VALIDATION_RESULT="<pass/fail/not_run>" '
        'PREVIEW_RESULT="<reviewed/not_run>" '
        'APPLY_RESULT="<applied/not_run/skipped>" '
        'CHANGED_READINESS_COUNTS="<from reviewed-batch-compare>" '
        'CHANGED_TICKERS="<from reviewed-batch-compare>"'
    )


def _metric_readiness_lane(root: Path, top_n: int, tickers: tuple[str, ...]) -> ReadinessLane:
    candidate_count = len(_candidate_tickers(root, "metric_readiness_review", top_n, tickers))
    return ReadinessLane(
        lane="metric_readiness_review",
        label="Metric Readiness Review",
        readiness_state="partial",
        workflow_mode="read_only_review",
        total_count=candidate_count,
        ready_count=0,
        partial_count=candidate_count,
        blocked_count=0,
        excluded_count=0,
        unlock_impact=candidate_count,
        source_lane="review_metrics",
        source_readiness="Requires trusted local prices, benchmark rows, fundamentals, market context, and peer inputs depending on blocker family.",
        next_safe_command=f"make metric-readiness-board TOP_N={top_n} BENCHMARKS=SPY,QQQ",
        proof_command=f"make metric-readiness-board TOP_N={top_n} BENCHMARKS=SPY,QQQ",
        generated_churn_policy="read-only console proof by default; do not stage generated CSV unless intentionally exported as reviewed evidence",
        stale_proof_warning="Run make readiness first if readiness artifacts are stale before interpreting final counts.",
        notes="Review metrics are coverage diagnostics only, not rankings or recommendations.",
    )


def build_reviewed_batch_packet(
    root: Path | str = ".",
    *,
    lane: str = "prices",
    top_n: int = 10,
    tickers: str | Iterable[str] | None = None,
) -> ReviewedBatchPacket:
    root = Path(root)
    selected_lane_codes = normalize_batch_lane(lane)
    selected_tickers = _split_tickers(tickers)
    freshness = readiness_freshness_status(root)
    lanes = [lane_row for lane_row in build_readiness_ops_lanes(root) if lane_row.lane in selected_lane_codes]
    if "metric_readiness_review" in selected_lane_codes and not any(lane_row.lane == "metric_readiness_review" for lane_row in lanes):
        lanes.append(_metric_readiness_lane(root, top_n, selected_tickers))
    lane_lookup = {lane_row.lane: lane_row for lane_row in lanes}
    batch_id = datetime.now(timezone.utc).strftime("RB-%Y%m%dT%H%M%SZ")
    actions: list[ReviewedBatchAction] = []
    for lane_code in selected_lane_codes:
        lane_row = lane_lookup.get(lane_code)
        if lane_row is None:
            continue
        action_tickers = _candidate_tickers(root, lane_code, top_n, selected_tickers)
        commands = _lane_commands(lane_code, action_tickers, top_n)
        action_scope = _join_ticker_arg(action_tickers)
        for proposed in action_tickers or ("<lane_scope>",):
            actions.append(
                ReviewedBatchAction(
                    batch_id=batch_id,
                    lane=lane_code,
                    lane_label=lane_row.label,
                    ticker_scope=action_scope,
                    proposed_ticker=proposed,
                    workflow_mode=lane_row.workflow_mode,
                    source_context=lane_row.source_readiness,
                    freshness_status=f"{freshness.status}: {freshness.message}",
                    dry_run_command=commands["dry_run"],
                    capped_execution_command=commands["execute"],
                    validation_command=commands["validate"],
                    preview_command=commands["preview"],
                    apply_command=commands["apply"],
                    post_run_verification=commands["post"],
                    readiness_comparison_command=commands["compare"].replace("<batch_id>", batch_id),
                    proof_record_command=_proof_record_scaffold(batch_id, lane_code),
                    expected_artifacts=commands["artifacts"],
                    rollback=commands["rollback"],
                    do_not_proceed_if=_do_not_proceed(lane_row, freshness),
                    pre_run_readiness_snapshot="record saved counts before command; run make readiness-snapshot if needed",
                    command_run="<copy exact command actually run>",
                    validation_result="<pass/fail/not_applicable>",
                    preview_result="<reviewed rows / no unexpected rows / not_applicable>",
                    apply_result="<not_run/applied/skipped>",
                    post_run_readiness_snapshot=commands["post"],
                    changed_readiness_counts="<before -> after counts, or none>",
                    changed_tickers="<tickers changed, or none>",
                    reviewer="<reviewer>",
                    review_date="<YYYY-MM-DD>",
                    source_files=commands["artifacts"],
                    generated_artifacts_reviewed="<kept evidence or excluded local churn>",
                    final_outcome="supported|still_blocked|skipped|excluded",
                    notes="<source proof, blockers, rollback notes>",
                )
            )
    return ReviewedBatchPacket(
        batch_id=batch_id,
        selected_lane=lane,
        selected_scope=", ".join(selected_lane_codes),
        top_n=top_n,
        tickers=selected_tickers,
        freshness=freshness,
        lanes=tuple(lanes),
        actions=tuple(actions),
    )


def render_packet_markdown(packet: ReviewedBatchPacket) -> str:
    tickers = ", ".join(packet.tickers) if packet.tickers else f"top {packet.top_n}"
    lines = [
        "# Reviewed Batch Run Packet",
        "",
        "Research-only: this packet plans data-readiness work. It is not investment advice, does not connect to brokers, does not route orders, and does not provide direct buy/sell instructions.",
        "",
        f"- Batch ID: `{packet.batch_id}`",
        f"- Selected lane: `{packet.selected_lane}`",
        f"- Lane scope: `{packet.selected_scope}`",
        f"- Ticker scope: `{tickers}`",
        f"- Freshness status: `{packet.freshness.status}`",
        f"- Freshness note: {packet.freshness.message}",
        f"- Refresh command if blocked: `{packet.freshness.refresh_command}`",
        "",
        "## Readiness Snapshot",
        "",
        "- Pre-run snapshot command: `make readiness-snapshot`",
        "- Refresh saved readiness reports before relying on final counts: `make readiness`",
        "- Current operations view: `make readiness-ops-center`",
        "- Current frontier view: `make coverage-frontier TOP_N=10`",
        "",
        "## Proposed Actions",
        "",
    ]
    if not packet.actions:
        lines.extend(
            [
                "No proposed actions were created. Run `make readiness` and choose one of `prices`, `fundamentals`, `peers`, `metrics`, or `optional_context`.",
                "",
            ]
        )
    for action in packet.actions:
        lines.extend(
            [
                f"### {action.lane_label}: {action.proposed_ticker}",
                "",
                f"- Workflow mode: `{action.workflow_mode}`",
                f"- Source/freshness context: {action.source_context} Freshness: {action.freshness_status}",
                f"- Dry-run command: `{action.dry_run_command}`",
                f"- Capped execution command: `{action.capped_execution_command}`",
                f"- Validate: `{action.validation_command}`",
                f"- Preview: `{action.preview_command}`",
                f"- Apply gate: `{action.apply_command}`",
                f"- Post-run verification: `{action.post_run_verification}`",
                f"- Readiness comparison: `{action.readiness_comparison_command}`",
                f"- Proof ledger record: `{action.proof_record_command}`",
                f"- Expected artifacts: {action.expected_artifacts}",
                f"- Rollback checklist: {action.rollback}",
                f"- Do not proceed if: {action.do_not_proceed_if}",
                "",
                "Peer/sub-lane proof instructions:" if action.lane in {"peer_mapping", "peer_valuation_inputs"} else "Lane proof instructions:",
                *[f"- {instruction}" for instruction in _lane_proof_instructions(action.lane, packet.top_n)],
                "",
            ]
        )
    lines.extend(
        [
            "## Review Checklist",
            "",
            "- Confirm readiness artifacts are current or run `make readiness`.",
            "- Confirm the dry run matches the intended lane and capped scope.",
            "- Confirm source files are trusted and local.",
            "- For mutating workflows, run validate -> preview -> apply only after review.",
            "- Check rejected-row reports before treating any lane as supported.",
            "- Run post-run readiness verification and record supported, still_blocked, skipped, or excluded honestly.",
            "- Record changed readiness counts and changed tickers only when the before/after proof supports them.",
            "- Classify generated CSV/JSON artifacts as kept evidence or excluded local churn before staging.",
            "",
            "## Proof Row Template",
            "",
            "Ledger path suggestion: `data/reviewed_batch_proofs.csv` or the existing reviewed data proof ledger.",
            f"Final outcome options: {', '.join(FINAL_OUTCOME_OPTIONS)}.",
            "",
        ]
    )
    for field in PROOF_TEMPLATE_FIELDS:
        lines.append(f"- {field}:")
    lines.extend(
        [
            "",
            "CSV template row:",
            "",
            f"`{_proof_template_csv_row(packet)}`",
            "",
            "## Guardrails",
            "",
            "- Do not fabricate prices, fundamentals, peers, earnings, analyst estimates, valuation inputs, or recommendations.",
            "- Do not treat a high unlock-impact lane as a security ranking.",
            "- Do not stage broad generated CSV/JSON churn unless it is intentionally reviewed evidence.",
            "- Do not proceed when source proof, validation, preview, rejected-row checks, or rollback path is unclear.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_reviewed_batch_packet(
    packet: ReviewedBatchPacket,
    *,
    md_output: Path = DEFAULT_PACKET_MD,
    csv_output: Path = DEFAULT_PACKET_CSV,
) -> None:
    md_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.write_text(render_packet_markdown(packet), encoding="utf-8")
    _write_csv(csv_output, packet.actions)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write a reviewed batch run packet.")
    parser.add_argument("--root", default=".", help="Project root.")
    parser.add_argument("--lane", default="prices", help="prices, fundamentals, peers, metrics, optional_context.")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--tickers", default="", help="Optional comma-separated ticker scope.")
    parser.add_argument("--md-output", default=str(DEFAULT_PACKET_MD))
    parser.add_argument("--csv-output", default=str(DEFAULT_PACKET_CSV))
    parser.add_argument("--print", action="store_true", help="Print packet markdown after writing outputs.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    packet = build_reviewed_batch_packet(
        args.root,
        lane=args.lane,
        top_n=args.top_n,
        tickers=args.tickers,
    )
    write_reviewed_batch_packet(packet, md_output=Path(args.md_output), csv_output=Path(args.csv_output))
    if args.print:
        print(render_packet_markdown(packet))
    else:
        print(f"Wrote {args.md_output}")
        print(f"Wrote {args.csv_output}")
        print(f"Freshness status: {packet.freshness.status} - {packet.freshness.message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
