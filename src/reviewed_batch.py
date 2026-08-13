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

from src.dcf_input_proof_queue import build_dcf_input_proof_queue_from_files
from src.readiness_ops import ReadinessLane, build_readiness_ops_lanes
from src.session_source_preflight import load_session_source_preflight
from src.share_count_proof_queue import build_share_count_proof_queue_from_files
from src.paths import DataProfile, resolve_project_root
from src.profile_context import build_profile_context
from src.readiness_source_boundary import (
    ReadinessSourceBoundaryError,
    validate_readiness_source_boundary,
)


DEFAULT_PACKET_MD = Path("outputs/reviewed_batch_packet.md")
DEFAULT_PACKET_CSV = Path("outputs/reviewed_batch_packet.csv")
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
    refresh_command: str = "make readiness-preview TOP_N=20"


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
    profile: str
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
    "share_count": ("share_count_proof",),
    "shares": ("share_count_proof",),
    "shares_outstanding": ("share_count_proof",),
    "share_count_proof": ("share_count_proof",),
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
    raise ValueError("Unknown reviewed batch lane. Use prices, fundamentals, share_count, peers, metrics, or optional_context.")


def _reviewed_batch_profile(root: Path, profile: str) -> DataProfile:
    """Resolve an existing profile safely, while preserving missing-data preflight output."""

    try:
        return validate_readiness_source_boundary(root, profile)
    except ReadinessSourceBoundaryError:
        data_relative, outputs_relative = {
            "default": (Path("data"), Path("outputs")),
            "demo": (Path("data/demo"), Path("outputs/demo")),
            "local": (Path("data/local"), Path("outputs/local")),
        }[profile]
        lexical_root = root.expanduser().absolute()
        lexical_data = lexical_root / data_relative
        if lexical_data.exists() or lexical_data.is_symlink():
            raise
        return DataProfile(
            name=profile,
            data_dir=lexical_data.resolve(strict=False),
            outputs_dir=(lexical_root / outputs_relative).resolve(strict=False),
        )


def readiness_freshness_status(
    root: Path | str = ".",
    *,
    profile: str | None = None,
    data_dir: Path | str | None = None,
    output_dir: Path | str | None = None,
    include_evidence: bool = True,
) -> FreshnessStatus:
    project_root = resolve_project_root(root)
    profile_context = build_profile_context(
        project_root=project_root,
        profile=profile,
        data_dir=data_dir,
        output_dir=output_dir,
    )
    if profile_context.freshness_state != "current":
        message = profile_context.freshness_message
        if profile_context.freshness_state == "missing":
            message = f"Missing readiness artifact(s). {profile_context.freshness_message}"
        return FreshnessStatus(
            profile_context.freshness_state,
            message,
            profile_context.refresh_command,
        )
    if include_evidence and profile_context.readiness_evidence_state in {
        "working_artifact_uncommitted",
        "unverified",
    }:
        return FreshnessStatus(
            profile_context.readiness_evidence_state,
            profile_context.readiness_evidence_message,
            "make readiness-preview TOP_N=20",
        )
    return FreshnessStatus("current", "Readiness artifacts are current relative to watched source files.")


def _ticker_from_rows(rows: list[dict[str, str]], field: str = "ticker") -> list[str]:
    values: list[str] = []
    for row in rows:
        ticker = str(row.get(field) or "").strip().upper()
        if ticker and ticker not in values:
            values.append(ticker)
    return values


def _peer_worklist_rows_for_lane(rows: list[dict[str, str]], lane: str) -> list[dict[str, str]]:
    if lane == "peer_mapping":
        return [
            row
            for row in rows
            if str(row.get("peer_blocker_type") or "").strip().lower() == "missing_peer_mapping"
            or str(row.get("workflow_group") or "").strip().lower()
            in {"dcf_ready_peer_mapping", "price_ready_peer_mapping", "peer_mapping_after_price", "peer_mapping"}
        ]
    if lane == "peer_valuation_inputs":
        return [
            row
            for row in rows
            if str(row.get("workflow_group") or "").strip().lower() == "peer_valuation_unlock"
            or str(row.get("peer_blocker_type") or "").strip().lower()
            in {"peer_fundamentals_missing", "peer_valuation_blocked", "peer_valuation_inputs"}
        ]
    return rows


def _candidate_tickers(
    root: Path,
    lane: str,
    top_n: int,
    selected_tickers: tuple[str, ...],
    *,
    data_dir: Path,
) -> tuple[str, ...]:
    if selected_tickers:
        return selected_tickers[: max(top_n, 0)]
    reports = data_dir / "reports"
    rows: list[dict[str, str]]
    if lane == "price_coverage":
        rows = [
            row
            for row in _read_csv(reports / "price_coverage_report.csv")
            if not _truthy(row.get("price_ready"))
        ]
    elif lane == "fundamentals_dcf":
        session_state = _session_source_state(root)
        if not session_state["sec_available"] and int(session_state["local_fundamentals_fixable"]) > 0:
            queue_limit = max(top_n * 5, top_n + 25, 0)
            local_queue = build_dcf_input_proof_queue_from_files(
                root,
                data_dir=data_dir,
                top_n=queue_limit,
            )
            local_tickers = [
                row.ticker
                for row in local_queue
                if row.missing_input_family != "price"
            ]
            if local_tickers:
                return tuple(local_tickers[: max(top_n, 0)])
        rows = [
            row
            for row in _read_csv(reports / "fundamentals_coverage_report.csv")
            if not _truthy(row.get("fundamentals_ready"))
        ]
    elif lane == "share_count_proof":
        return tuple(
            row.ticker
            for row in build_share_count_proof_queue_from_files(
                root,
                data_dir=data_dir,
                top_n=max(top_n, 0),
            )
        )
    elif lane in {"peer_mapping", "peer_valuation_inputs"}:
        rows = _peer_worklist_rows_for_lane(_read_csv(reports / "peer_unlock_worklist.csv"), lane)
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


def reviewed_batch_packet_status(packet: ReviewedBatchPacket) -> str:
    if not packet.actions:
        return "blocked_no_actions"
    return "ready_for_review"


def reviewed_batch_next_safe_action(packet: ReviewedBatchPacket) -> str:
    status = reviewed_batch_packet_status(packet)
    if status == "blocked_no_actions":
        return f"make readiness-snapshot PROFILE={packet.profile}"
    first_action = packet.actions[0] if packet.actions else None
    if first_action is None:
        return f"make readiness-snapshot PROFILE={packet.profile}"
    return first_action.pre_run_readiness_snapshot


def _session_source_state(root: Path) -> dict[str, object]:
    preflight = load_session_source_preflight(root) or {}
    sources = preflight.get("sources", {}) if isinstance(preflight, dict) else {}
    local = sources.get("local_fundamentals", {}) if isinstance(sources, dict) else {}
    sec_available = (sources.get("sec", {}) if isinstance(sources, dict) else {}).get("status") == "available"
    return {
        "sec_available": sec_available,
        "local_fundamentals_fixable": int(local.get("fundamentals_fixable_ticker_count", 0) or 0),
        "local_share_fixable": int(local.get("share_count_fixable_ticker_count", 0) or 0),
    }


def _lane_commands(
    lane: str,
    tickers: tuple[str, ...],
    top_n: int,
    *,
    root: Path,
    profile: str,
) -> dict[str, str]:
    ticker_arg = _join_ticker_arg(tickers)
    session_state = _session_source_state(root)
    sec_available = bool(session_state["sec_available"])
    local_fundamentals_fixable = int(session_state["local_fundamentals_fixable"])
    local_share_fixable = int(session_state["local_share_fixable"])
    compare_lane = {
        "price_coverage": "prices",
        "fundamentals_dcf": "fundamentals",
        "share_count_proof": "share_count",
        "peer_mapping": "peers",
        "peer_valuation_inputs": "peers",
        "metric_readiness_review": "metrics",
    }.get(lane, "optional_context")
    compare = (
        f"make reviewed-batch-compare PROFILE={profile} LANE={compare_lane} "
        "BATCH_ID=<batch_id> REVIEW_DATE=<yyyy-mm-dd>"
    )
    if lane == "price_coverage":
        return {
            "dry_run": f"make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N={top_n} PROVIDER=auto",
            "execute": f"make price-refresh-loop MAX_CANDIDATES=3500 TOP_N={top_n} PROVIDER=auto SLEEP_SECONDS=30",
            "validate": "make price-validate",
            "preview": "make price-preview",
            "apply": "make price-apply only for reviewed trusted rows",
            "post": compare,
            "compare": compare,
            "artifacts": "data/prices.csv; data/reports/price_coverage_report.csv; outputs/reviewed_batch_packet.csv",
            "rollback": "If refreshed prices are incomplete or suspicious, keep generated CSV churn unstaged and restore reviewed local price files from git or the readiness snapshot.",
        }
    if lane == "fundamentals_dcf":
        if not sec_available and local_fundamentals_fixable > 0:
            execute = (
                f"make focus-fundamentals TICKER={tickers[0] if tickers else '<ticker>'}, "
                "then place only reviewed trusted fundamentals rows in data/imports/fundamentals.csv"
            )
            dry_run = f"make dcf-input-proof-queue TOP_N={top_n}"
        else:
            execute = f"make sec-stage TICKERS={ticker_arg} only if SEC_USER_AGENT is configured, or place reviewed trusted rows in data/imports/fundamentals.csv"
            dry_run = f"make sec-stage-queue TOP_N={top_n}"
        return {
            "dry_run": dry_run,
            "execute": execute,
            "validate": "make imports-validate",
            "preview": "make imports-preview",
            "apply": "make imports-apply only after reviewed trusted fundamentals rows pass preview",
            "post": compare,
            "compare": compare,
            "artifacts": "data/imports/fundamentals.csv; data/fundamentals.csv; data/rejected/fundamentals_import_rejected.csv; data/reports/dcf_readiness_report.csv",
            "rollback": f"If preview/rejected rows are wrong, do not apply. If applied rows are wrong, restore data/fundamentals.csv from git/backups and rerun the profile-bound comparison: {compare}.",
        }
    if lane == "share_count_proof":
        if not sec_available and local_share_fixable == 0:
            execute = (
                f"make focus-fundamentals TICKER={tickers[0] if tickers else '<ticker>'}, "
                "then use only reviewed manual shares_outstanding rows if source proof exists"
            )
        else:
            execute = f"make sec-stage TICKERS={ticker_arg} only if SEC/manual source proof includes shares_outstanding, or place reviewed trusted share-count rows in data/imports/fundamentals.csv"
        return {
            "dry_run": f"make share-count-proof-queue TOP_N={top_n}",
            "execute": execute,
            "validate": "make imports-validate",
            "preview": "make imports-preview",
            "apply": "make imports-apply only after reviewed trusted shares_outstanding rows pass preview",
            "post": compare,
            "compare": compare,
            "artifacts": "data/imports/fundamentals.csv; data/fundamentals.csv; data/rejected/fundamentals_import_rejected.csv; data/reports/dcf_readiness_report.csv; outputs/reviewed_batch_packet.csv",
            "rollback": f"If share-count rows are wrong, do not apply. If applied rows are wrong, restore data/fundamentals.csv from git/backups, run make dcf-readiness, then {compare}.",
        }
    if lane == "peer_mapping":
        return {
            "dry_run": f"make peer-mapping-queue TOP_N={top_n}",
            "execute": f"make focus-peers TICKER={tickers[0] if tickers else '<ticker>'}, then add only reviewed source-backed peer mappings to data/imports/peers.csv",
            "validate": "make imports-validate",
            "preview": "make imports-preview",
            "apply": "make imports-apply only after source-backed peer mapping rows are reviewed",
            "post": compare,
            "compare": compare,
            "artifacts": "data/imports/peers.csv; data/peers.csv; data/rejected/peers_import_rejected.csv; data/reports/peer_readiness_report.csv; data/reports/peer_unlock_worklist.csv",
            "rollback": f"If peer mapping rows are wrong, do not apply. If applied rows are wrong, restore data/peers.csv from git/backups and rerun the profile-bound comparison: {compare}.",
        }
    if lane == "peer_valuation_inputs":
        return {
            "dry_run": f"make peer-mapping-queue TOP_N={top_n}",
            "execute": f"make focus-peers TICKER={tickers[0] if tickers else '<ticker>'}, then follow mapped-peer dependencies with make focus-fundamentals TICKER=<peer> or verified peer price/market-cap context",
            "validate": "make imports-validate",
            "preview": "make imports-preview",
            "apply": "make imports-apply only after reviewed mapped-peer fundamentals, price, market-cap, or valuation-input rows pass preview",
            "post": f"{compare} && make metric-readiness TICKERS={ticker_arg} BENCHMARK=SPY",
            "compare": compare,
            "artifacts": "data/imports/fundamentals.csv; data/imports/prices.csv; data/imports/peers.csv if mappings change; data/rejected/fundamentals_import_rejected.csv; data/rejected/price_import_rejected.csv; data/rejected/peers_import_rejected.csv; data/reports/peer_readiness_report.csv; data/reports/peer_unlock_worklist.csv",
            "rollback": f"If mapped-peer input rows are wrong, do not apply. If applied rows are wrong, restore the touched canonical fundamentals, prices, or peers CSVs, then rerun the profile-bound comparison: {compare}.",
        }
    if lane == "metric_readiness_review":
        return {
            "dry_run": f"make metric-readiness-board TOP_N={top_n} TICKERS={ticker_arg}",
            "execute": f"make metric-readiness-board TOP_N={top_n} TICKERS={ticker_arg} BENCHMARKS=SPY,QQQ",
            "validate": "not_applicable_read_only_metric_review",
            "preview": "review metric blocker families, source gates, and row-level missing inputs before any data work",
            "apply": "not_applicable; metrics remain blocked until the underlying trusted source rows are reviewed through their lane",
            "post": compare,
            "compare": compare,
            "artifacts": "metric-readiness console output; Data Health Metrics lane; optional reviewed_batch_packet.csv",
            "rollback": "No local data is mutated by metric-readiness review. If follow-up source rows are changed in another lane, use that lane's rollback path.",
        }
    return {
        "dry_run": f"make optional-context-worklist TOP_N={top_n}",
        "execute": f"make templates, then prepare trusted local optional rows for {ticker_arg}",
        "validate": "make imports-validate",
        "preview": "make imports-preview",
        "apply": "make imports-apply only after trusted local earnings/estimate rows pass preview",
        "post": compare,
        "compare": compare,
        "artifacts": "data/imports/earnings.csv; data/imports/analyst_estimates.csv; data/reports/earnings_readiness_report.csv; data/reports/analyst_estimates_readiness_report.csv",
        "rollback": "If optional rows are wrong, do not apply. If applied rows are wrong, restore earnings/analyst-estimates CSVs and rerun optional-context readiness.",
    }


def _do_not_proceed(lane: ReadinessLane) -> str:
    blockers = [
        "the profile-bound prior readiness snapshot is missing or invalid",
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
    if lane.lane == "share_count_proof":
        blockers.extend(
            [
                "SEC/manual source proof does not explicitly verify shares_outstanding",
                "share count would be inferred from price, market cap, peers, or placeholders",
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
    return "; ".join(blockers)


def _lane_proof_instructions(lane: str, top_n: int, *, profile: str) -> list[str]:
    def compare(compare_lane: str) -> str:
        return (
            f"make reviewed-batch-compare PROFILE={profile} LANE={compare_lane} "
            "BATCH_ID=<reviewed_batch_id> REVIEW_DATE=<yyyy-mm-dd>"
        )
    if lane == "price_coverage":
        return [
            "Record pre-run price-ready, momentum-ready, liquidity, and correlation counts before any refresh.",
            "Use dry-run output to cap scope; do not treat provider availability as reviewed data.",
            f"After execution, run {compare('prices')} so changed counts come from the saved baseline and current in-memory row set.",
        ]
    if lane == "fundamentals_dcf":
        return [
            "Record pre-run fundamentals-ready and DCF-ready counts plus the exact missing fields.",
            f"Start from the first-class packet command: make fundamentals-batch-proof PROFILE={profile} TOP_N=<n> or make fundamentals-batch-proof PROFILE={profile} TICKERS=<scope>.",
            "Use make sec-stage-queue TOP_N=<n> for a dry-run queue; run make sec-stage TICKERS=<scope> only when SEC_USER_AGENT is configured.",
            "If SEC staging is unavailable, place only reviewed trusted manual rows in data/imports/fundamentals.csv.",
            "Run make imports-validate and make imports-preview before imports-apply; rejected-row reports must be clear or explained.",
            f"After apply, run make dcf-readiness and {compare('fundamentals')} before calling any ticker supported.",
        ]
    if lane == "share_count_proof":
        return [
            "Record pre-run DCF-ready counts and the exact tickers blocked by shares_outstanding.",
            f"Start from the first-class queue command: make share-count-proof-queue TOP_N={top_n}.",
            "Use SEC/manual source documents only when they explicitly verify shares_outstanding; do not infer it from market cap, price, peers, or placeholders.",
            "Run make imports-validate and make imports-preview before imports-apply; rejected-row reports must be clear or explained.",
            f"After apply, run make dcf-readiness, {compare('share_count')}, and the relevant stock report before calling the lane supported.",
        ]
    if lane == "peer_mapping":
        return [
            "Record peer_mapping_ready, peer_price_ready, peer_momentum_ready, peer_fundamentals_ready, peer_valuation_ready, and peer_valuation_comparison_ready before changes.",
            f"Start from the first-class packet command: make peer-batch-proof PROFILE={profile} TOP_N=<n> or make peer-batch-proof PROFILE={profile} TICKERS=<scope>.",
            f"Inspect missing peer relationships with make peer-mapping-queue TOP_N={top_n} and make focus-peers TICKER=<ticker>.",
            "Peer mapping import schema: ticker, peer_ticker, peer_group, sector, industry, peer_role, relationship_rationale, comparability_basis, valuation_anchor_eligible, source, as_of_date.",
            "Source proof checklist: source must name the peer relationship or comparable business context, include a durable URL or local document reference, and have a review date; do not use memory, popularity, or row-count convenience as proof.",
            "Treat sector or industry fallback as context only; it is not trusted peer mapping proof.",
            "Run make imports-validate and make imports-preview before imports-apply; data/rejected/peers_import_rejected.csv must be clear or explained.",
            f"After reviewed mapping rows, run {compare('peers')} and make peer-mapping-queue before reading peer valuation dispersion.",
        ]
    if lane == "peer_valuation_inputs":
        return [
            "Record peer_mapping_ready, peer_price_ready, peer_momentum_ready, peer_fundamentals_ready, peer_valuation_ready, and peer_valuation_comparison_ready before changes.",
            f"Start from the first-class packet command: make peer-batch-proof PROFILE={profile} TOP_N=<n> or make peer-batch-proof PROFILE={profile} TICKERS=<scope>.",
            f"Inspect the peer valuation sub-lane with make peer-mapping-queue TOP_N={top_n} and make focus-peers TICKER=<ticker>.",
            "Follow the printed mapped-peer dependency with make focus-fundamentals TICKER=<peer> or verified peer price/market-cap proof.",
            "Do not treat mapped peers as valuation-ready until mapped-peer inputs pass validate, preview, rejected-row review, and rebuilt readiness.",
            f"After reviewed mapped-peer inputs, run {compare('peers')} and make peer-mapping-queue before reading peer valuation dispersion.",
        ]
    if lane == "metric_readiness_review":
        return [
            "Record the SPY/QQQ blocker-family summary before opening row-level proof.",
            "Map each blocked metric to its source lane: prices, fundamentals, market context, or peer inputs.",
            "Do not apply rows from the metrics packet; use the underlying reviewed lane packet when source proof exists.",
            f"After any reviewed source-lane change, run {compare('metrics')} and make metric-readiness-board before describing the metric as ready.",
        ]
    return [
        "Record pre-run optional context readiness counts.",
        "Apply only trusted local earnings or analyst-estimate rows after validate and preview.",
        "After apply, rerun optional-context readiness and keep unsupported optional context locked where rows are absent.",
    ]


def _proof_template_csv_row(packet: ReviewedBatchPacket) -> str:
    comparison_command = (
        packet.actions[0].readiness_comparison_command
        if packet.actions
        else (
            f"make reviewed-batch-compare PROFILE={packet.profile} LANE={packet.selected_lane} "
            "BATCH_ID=<batch_id> REVIEW_DATE=<yyyy-mm-dd>"
        )
    )
    values = {
        "batch_id": packet.batch_id,
        "lane": packet.selected_scope,
        "scope": packet.selected_lane,
        "tickers": ",".join(packet.tickers) if packet.tickers else f"top {packet.top_n}",
        "pre_run_readiness_snapshot": f"make readiness-snapshot PROFILE={packet.profile}",
        "command_run": "<copy exact command>",
        "validation_result": "<pass/fail/not_applicable>",
        "preview_result": "<reviewed rows / no unexpected rows / not_applicable>",
        "apply_result": "<not_run/applied/skipped>",
        "post_run_readiness_snapshot": comparison_command,
        "changed_readiness_counts": "<before -> after counts, or none>",
        "changed_tickers": "<tickers changed, or none>",
        "reviewer": "<name>",
        "review_date": "<YYYY-MM-DD>",
        "source_files": "<trusted local source files reviewed>",
        "generated_artifacts_reviewed": "<CSV/JSON artifacts kept/excluded>",
        "final_outcome": "supported|candidate_context_only|still_blocked|skipped|excluded",
        "notes": "<source proof, blockers, rollback notes>",
    }
    return ",".join(values[field] for field in PROOF_TEMPLATE_FIELDS)


def _proof_record_scaffold(batch_id: str, lane: str) -> str:
    return (
        "make reviewed-batch-proof-record "
        f'BATCH_ID="{batch_id}" '
        f'LANE="{lane}" '
        'REVIEW_DATE="<yyyy-mm-dd>" '
        'FINAL_OUTCOME="<supported|candidate_context_only|still_blocked|skipped|excluded>" '
        'COMMAND_RUN="<exact reviewed command>" '
        'VALIDATION_RESULT="<pass/fail/not_run>" '
        'PREVIEW_RESULT="<reviewed/not_run>" '
        'APPLY_RESULT="<applied/not_run/skipped>" '
        'CHANGED_READINESS_COUNTS="<from reviewed-batch-compare>" '
        'CHANGED_TICKERS="<from reviewed-batch-compare>"'
    )


def _metric_readiness_lane(
    root: Path,
    top_n: int,
    tickers: tuple[str, ...],
    *,
    data_dir: Path,
    profile: str,
) -> ReadinessLane:
    candidate_count = len(
        _candidate_tickers(
            root,
            "metric_readiness_review",
            top_n,
            tickers,
            data_dir=data_dir,
        )
    )
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
        stale_proof_warning=f"Use make readiness-snapshot PROFILE={profile} before changes and the profile-bound in-memory comparison afterward.",
        notes="Review metrics are coverage diagnostics only, not rankings or recommendations.",
    )


def build_reviewed_batch_packet(
    root: Path | str = ".",
    *,
    lane: str = "prices",
    top_n: int = 10,
    tickers: str | Iterable[str] | None = None,
    profile: str = "default",
) -> ReviewedBatchPacket:
    root = Path(root)
    if profile not in {"default", "demo", "local"}:
        raise ValueError("Unknown reviewed batch profile. Use default, demo, or local.")
    selected_profile = _reviewed_batch_profile(root, profile)
    selected_lane_codes = normalize_batch_lane(lane)
    selected_tickers = _split_tickers(tickers)
    freshness = FreshnessStatus(
        "not_used",
        "Tracked-current saved-artifact freshness is not used; use the profile-bound baseline and current in-memory comparison.",
        f"make readiness-snapshot PROFILE={profile}",
    )
    lanes = [
        lane_row
        for lane_row in build_readiness_ops_lanes(
            root,
            profile=profile,
            data_dir=selected_profile.data_dir,
            output_dir=selected_profile.outputs_dir,
        )
        if lane_row.lane in selected_lane_codes
    ]
    if "metric_readiness_review" in selected_lane_codes and not any(lane_row.lane == "metric_readiness_review" for lane_row in lanes):
        lanes.append(
            _metric_readiness_lane(
                root,
                top_n,
                selected_tickers,
                data_dir=selected_profile.data_dir,
                profile=profile,
            )
        )
    lane_lookup = {lane_row.lane: lane_row for lane_row in lanes}
    batch_id = datetime.now(timezone.utc).strftime("RB-%Y%m%dT%H%M%SZ")
    actions: list[ReviewedBatchAction] = []
    for lane_code in selected_lane_codes:
        lane_row = lane_lookup.get(lane_code)
        if lane_row is None:
            continue
        action_tickers = _candidate_tickers(
            root,
            lane_code,
            top_n,
            selected_tickers,
            data_dir=selected_profile.data_dir,
        )
        commands = _lane_commands(lane_code, action_tickers, top_n, root=root, profile=profile)
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
                    do_not_proceed_if=_do_not_proceed(lane_row),
                    pre_run_readiness_snapshot=f"make readiness-snapshot PROFILE={profile}",
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
                    final_outcome="supported|candidate_context_only|still_blocked|skipped|excluded",
                    notes="<source proof, blockers, rollback notes>",
                )
            )
    return ReviewedBatchPacket(
        batch_id=batch_id,
        profile=profile,
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
    packet_status = reviewed_batch_packet_status(packet)
    next_safe_action = reviewed_batch_next_safe_action(packet)
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
        f"- Packet status: `{packet_status}`",
        f"- Next safe action: `{next_safe_action}`",
        "",
        "## Readiness Snapshot",
        "",
        f"- Pre-run snapshot command: `make readiness-snapshot PROFILE={packet.profile}`",
        f"- Post-apply proof: `make reviewed-batch-compare PROFILE={packet.profile} LANE=<lane> BATCH_ID=<batch_id> REVIEW_DATE=<yyyy-mm-dd>`",
        "- Current operations view: `make readiness-ops-center`",
        "- Current frontier view: `make coverage-frontier TOP_N=10`",
        "",
        "## Proposed Actions",
        "",
    ]
    if not packet.actions:
        lines.extend(
            [
                f"No proposed actions were created. Capture `make readiness-snapshot PROFILE={packet.profile}` and choose one of `prices`, `fundamentals`, `share_count`, `peers`, `metrics`, or `optional_context`.",
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
                *[f"- {instruction}" for instruction in _lane_proof_instructions(action.lane, packet.top_n, profile=packet.profile)],
                "",
            ]
        )
    lines.extend(
        [
            "## Review Checklist",
            "",
            f"- Confirm the pre-run baseline was captured with `make readiness-snapshot PROFILE={packet.profile}` before any apply decision.",
            "- Confirm the dry run matches the intended lane and capped scope.",
            "- Confirm source files are trusted and local.",
            "- For mutating workflows, run validate -> preview -> apply only after review.",
            "- Check rejected-row reports before treating any lane as supported.",
            "- Run post-run readiness verification and record supported, candidate_context_only, still_blocked, skipped, or excluded honestly.",
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


def render_packet_preview(packet: ReviewedBatchPacket) -> str:
    packet_status = reviewed_batch_packet_status(packet)
    next_safe_action = reviewed_batch_next_safe_action(packet)
    lines = [
        "Reviewed batch packet preview",
        "Research-only: preview data-readiness work only; no broker integration, no auto-trading, no account execution, and no direct transaction instructions.",
        f"status: preview",
        f"batch_id: {packet.batch_id}",
        f"selected_lane: {packet.selected_lane}",
        f"lane_scope: {packet.selected_scope}",
        f"freshness_status: {packet.freshness.status}",
        f"packet_status: {packet_status}",
        f"next_safe_action: {next_safe_action}",
        f"actions: {len(packet.actions)}",
        "message: Previewed reviewed batch packet; no Markdown or CSV artifacts were written.",
    ]
    if packet.actions:
        action = packet.actions[0]
        lines.extend(
            [
                "top_action:",
                f"- lane: {action.lane_label}",
                f"- proposed_ticker: {action.proposed_ticker}",
                f"- dry_run_command: {action.dry_run_command}",
                f"- capped_execution_command: {action.capped_execution_command}",
                f"- validation_command: {action.validation_command}",
                f"- preview_command: {action.preview_command}",
                f"- apply_gate: {action.apply_command}",
                f"- post_run_verification: {action.post_run_verification}",
                f"- readiness_comparison: {action.readiness_comparison_command}",
                f"- proof_record_command: {action.proof_record_command}",
                f"- do_not_proceed_if: {action.do_not_proceed_if}",
            ]
        )
        remaining = len(packet.actions) - 1
        if remaining > 0:
            lines.append(f"additional_actions: {remaining}")
    else:
        lines.append(f"top_action: none; run make readiness-snapshot PROFILE={packet.profile} and choose a supported lane.")
    lines.extend(
        [
            "guardrails:",
            "- Do not fabricate prices, fundamentals, peers, earnings, analyst estimates, valuation inputs, or recommendations.",
            "- Write reviewed batch artifacts only when the packet itself is intentionally reviewed evidence.",
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
    parser = argparse.ArgumentParser(description="Preview or write a reviewed batch run packet.")
    parser.add_argument("--root", default=".", help="Project root.")
    parser.add_argument("--lane", default="prices", help="prices, fundamentals, share_count, peers, metrics, optional_context.")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--tickers", default="", help="Optional comma-separated ticker scope.")
    parser.add_argument("--profile", choices=("default", "demo", "local"), default="default")
    parser.add_argument("--md-output", default=str(DEFAULT_PACKET_MD))
    parser.add_argument("--csv-output", default=str(DEFAULT_PACKET_CSV))
    parser.add_argument("--dry-run", action="store_true", help="Preview the packet without writing Markdown or CSV artifacts.")
    parser.add_argument("--print", action="store_true", help="Print packet markdown after writing outputs.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    packet = build_reviewed_batch_packet(
        args.root,
        lane=args.lane,
        top_n=args.top_n,
        tickers=args.tickers,
        profile=args.profile,
    )
    if args.dry_run:
        print(render_packet_markdown(packet) if args.print else render_packet_preview(packet))
        return 0
    write_reviewed_batch_packet(packet, md_output=Path(args.md_output), csv_output=Path(args.csv_output))
    if args.print:
        print(render_packet_markdown(packet))
    else:
        print(f"Wrote {args.md_output}")
        print(f"Wrote {args.csv_output}")
        print(f"Freshness status: {packet.freshness.status} - {packet.freshness.message}")
        print(f"Packet status: {reviewed_batch_packet_status(packet)}")
        print(f"Next safe action: {reviewed_batch_next_safe_action(packet)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
