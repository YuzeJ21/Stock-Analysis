"""Print a read-only coverage expansion execution loop.

The loop connects the lane planner to reviewed-batch preflight, packet,
comparison, proof-record, and hygiene commands. It does not refresh data,
stage imports, apply rows, or create research recommendations.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.readiness_ops import (
    DataCoverageExpansionStep,
    ReadinessLane,
    build_data_coverage_expansion_plan,
    build_readiness_ops_lanes,
    build_reviewed_batch_ledger_summaries,
)
from src.reviewed_batch_preflight import ReviewedBatchPreflight, build_reviewed_batch_preflight
from src.profile_context import READINESS_PREVIEW_COMMAND, READINESS_PREVIEW_NOTE
from src.session_source_preflight import load_session_source_preflight


LANE_TO_REVIEWED_BATCH = {
    "price_coverage": "prices",
    "fundamentals_dcf": "fundamentals",
    "share_count_proof": "share_count",
    "peer_mapping": "peers",
    "peer_valuation_inputs": "peers",
    "earnings_locked": "optional_context",
    "analyst_estimates_locked": "optional_context",
}


@dataclass(frozen=True)
class CoverageExpansionLaneStatus:
    lane: str
    label: str
    selected: bool
    readiness_state: str
    workflow_mode: str
    unlock_impact: int
    readiness_snapshot: str
    next_safe_command: str
    proof_command: str
    proceed_boundary: str


@dataclass(frozen=True)
class CoverageExpansionSourceProofGate:
    lane: str
    status: str
    evidence_to_collect: tuple[str, ...]
    accepted_sources: tuple[str, ...]
    rejected_shortcuts: tuple[str, ...]
    review_commands: tuple[str, ...]
    proof_ready_when: str


@dataclass(frozen=True)
class CoverageExpansionLoop:
    status: str
    selected_lane: str
    selected_label: str
    reviewed_batch_lane: str
    planner_step: DataCoverageExpansionStep | None
    preflight: ReviewedBatchPreflight | None
    next_safe_action: str
    copy_only_sequence: tuple[str, ...]
    do_not_proceed_if: tuple[str, ...]
    lane_board: tuple[CoverageExpansionLaneStatus, ...] = ()
    source_proof_gate: CoverageExpansionSourceProofGate | None = None
    session_source_preflight: dict[str, Any] | None = None
    pivot_notes: tuple[str, ...] = ()


def _normalize_planner_lane(value: str) -> str:
    key = str(value or "").strip().lower().replace("-", "_")
    aliases = {
        "auto": "auto",
        "price": "price_coverage",
        "prices": "price_coverage",
        "fundamental": "fundamentals_dcf",
        "fundamentals": "fundamentals_dcf",
        "dcf": "fundamentals_dcf",
        "share_count": "share_count_proof",
        "shares": "share_count_proof",
        "shares_outstanding": "share_count_proof",
        "peer": "peer_mapping",
        "peers": "peer_mapping",
        "peer_valuation": "peer_valuation_inputs",
        "optional": "earnings_locked",
        "optional_context": "earnings_locked",
    }
    return aliases.get(key, key)


def _select_step(steps: list[DataCoverageExpansionStep], lane: str) -> DataCoverageExpansionStep | None:
    if not steps:
        return None
    normalized = _normalize_planner_lane(lane)
    if normalized == "auto":
        return steps[0]
    for step in steps:
        if step.lane == normalized:
            return step
    return None


def _preferred_auto_lanes_from_session(preflight: dict[str, Any] | None) -> list[str]:
    if preflight is None:
        return []
    local_fundamentals = (preflight.get("sources") or {}).get("local_fundamentals", {})
    local_share_fixable = int(local_fundamentals.get("share_count_fixable_ticker_count", 0))
    local_fundamentals_fixable = int(local_fundamentals.get("fundamentals_fixable_ticker_count", 0))
    lane_map = {
        "sec_fundamentals_share_count": ["share_count_proof", "fundamentals_dcf"],
        "local_reviewed_fundamentals_share_count": (
            ["fundamentals_dcf", "share_count_proof"]
            if local_share_fixable == 0 and local_fundamentals_fixable > 0
            else ["share_count_proof", "fundamentals_dcf"]
        ),
        "yfinance_fundamentals_share_count": ["share_count_proof", "fundamentals_dcf"],
        "peer_mapping_proof": ["peer_mapping"],
        "peer_valuation_local_reviewed": ["peer_valuation_inputs"],
        "earnings_optional_manual": ["earnings_locked"],
        "analyst_estimates_optional_manual": ["analyst_estimates_locked"],
        "coverage_workflow_evidence": [],
    }
    preferred: list[str] = []
    for item in preflight.get("preferred_lane_order", []):
        preferred.extend(lane_map.get(str(item), []))
    preferred.append("price_coverage")
    seen: set[str] = set()
    ordered: list[str] = []
    for item in preferred:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _session_sec_unavailable(preflight: dict[str, Any] | None) -> bool:
    if not isinstance(preflight, dict):
        return False
    sources = preflight.get("sources", {})
    if not isinstance(sources, dict):
        return False
    sec = sources.get("sec", {})
    if not isinstance(sec, dict):
        return False
    return sec.get("status") == "unavailable"


def _source_activation_required(preflight: dict[str, Any] | None) -> bool:
    if not isinstance(preflight, dict):
        return False
    sources = preflight.get("sources", {})
    if not isinstance(sources, dict) or "price_ladder" not in sources:
        return False

    def source_available(name: str) -> bool:
        source = sources.get(name, {})
        return isinstance(source, dict) and source.get("status") == "available"

    local = sources.get("local_fundamentals", {})
    local_fixable = 0
    if isinstance(local, dict):
        local_fixable = int(local.get("share_count_fixable_ticker_count", 0) or 0) + int(
            local.get("fundamentals_fixable_ticker_count", 0) or 0
        )

    price_ladder = sources.get("price_ladder", {})
    configured_price_fallbacks: list[str] = []
    if isinstance(price_ladder, dict):
        configured_price_fallbacks = [
            str(item).strip()
            for item in price_ladder.get("configured_keyed_providers", [])
            if str(item).strip()
        ]

    return not any(
        (
            source_available("sec"),
            source_available("yfinance_stage"),
            source_available("fmp"),
            source_available("alpha_vantage"),
            source_available("finnhub"),
            bool(configured_price_fallbacks),
            local_fixable > 0,
        )
    )


def _free_tier_limit_summary(preflight: dict[str, Any] | None) -> str:
    if not isinstance(preflight, dict):
        return ""
    console = preflight.get("source_activation_console_v2", {})
    if not isinstance(console, dict):
        return ""
    limits = console.get("free_tier_batch_limits", {})
    if not isinstance(limits, dict):
        return ""
    pieces: list[str] = []
    for provider in ("fmp", "alpha_vantage", "finnhub"):
        policy = limits.get(provider)
        if not isinstance(policy, dict):
            continue
        daily = policy.get("recommended_daily_request_limit")
        batch = policy.get("recommended_batch_size")
        if daily in (None, "") or batch in (None, ""):
            continue
        pieces.append(f"{provider}<={daily}/day and <={batch}/run")
    return ", ".join(pieces)


def _preflight_routes_to_workflow_evidence(preflight: dict[str, Any] | None) -> bool:
    if not isinstance(preflight, dict):
        return False
    console = preflight.get("source_activation_console_v2")
    if not isinstance(console, dict):
        return False
    return str(console.get("next_executable_lane") or "").strip() == "coverage_workflow_evidence"


def _optional_context_ledger_covers_lanes(root: Path, lanes: list[ReadinessLane]) -> bool:
    summary = build_reviewed_batch_ledger_summaries(root).get("optional_context")
    if summary is None:
        return False
    optional_total = max(
        (
            lane.total_count
            for lane in lanes
            if lane.lane in {"earnings_locked", "analyst_estimates_locked"}
        ),
        default=0,
    )
    return optional_total > 0 and summary.unique_ticker_count >= optional_total


def _peer_mapping_ledger_covers_review_queue(root: Path, lanes: list[ReadinessLane]) -> bool:
    summary = build_reviewed_batch_ledger_summaries(root).get("peers")
    if summary is None:
        return False
    peer_blocked = max(
        (lane.blocked_count for lane in lanes if lane.lane == "peer_mapping"),
        default=0,
    )
    return peer_blocked > 0 and summary.unique_ticker_count >= peer_blocked


def _peer_valuation_inputs_ledger_covers_blockers(root: Path, lanes: list[ReadinessLane]) -> bool:
    summary = build_reviewed_batch_ledger_summaries(root).get("peer_valuation_inputs")
    if summary is None:
        return False
    peer_valuation_blocked = max(
        (lane.blocked_count for lane in lanes if lane.lane == "peer_valuation_inputs"),
        default=0,
    )
    return peer_valuation_blocked > 0 and summary.unique_ticker_count >= peer_valuation_blocked


def _lane_proceed_boundary(lane: ReadinessLane) -> str:
    if lane.workflow_mode == "dry_run_first":
        return "dry-run and reviewed scope before any capped provider refresh"
    if lane.workflow_mode == "preview_first_reviewed_apply":
        return "source proof, validate, preview, rejected-row review, explicit apply decision, rebuilt readiness"
    if lane.workflow_mode == "reviewed_apply":
        return "source-backed rows only; fallback context does not become trusted data"
    if lane.workflow_mode == "optional_source_ladder":
        return "locked until trusted local or reviewed provider-assisted rows exist; skipped is valid when source proof is unavailable"
    if lane.workflow_mode == "locked_manual":
        return "locked until trusted local rows exist; skipped is valid when source proof is unavailable"
    if lane.workflow_mode == "excluded":
        return "excluded/not applicable stays visible; do not force an analysis lane"
    return "review source proof and rebuilt readiness before recording supported"


def build_coverage_expansion_lane_board(
    lanes: list[ReadinessLane],
    *,
    selected_lane: str,
    top_n: int = 10,
) -> tuple[CoverageExpansionLaneStatus, ...]:
    normalized_selected = _normalize_planner_lane(selected_lane)
    workflow_rank = {
        "dry_run_first": 0,
        "preview_first_reviewed_apply": 1,
        "reviewed_apply": 2,
        "optional_source_ladder": 3,
        "locked_manual": 4,
        "excluded": 5,
    }
    ranked = sorted(
        lanes,
        key=lambda lane: (
            workflow_rank.get(lane.workflow_mode, 9),
            -lane.unlock_impact,
            lane.label,
        ),
    )
    board: list[CoverageExpansionLaneStatus] = []
    for lane in ranked[: max(top_n, 0)]:
        board.append(
            CoverageExpansionLaneStatus(
                lane=lane.lane,
                label=lane.label,
                selected=lane.lane == normalized_selected,
                readiness_state=lane.readiness_state,
                workflow_mode=lane.workflow_mode,
                unlock_impact=lane.unlock_impact,
                readiness_snapshot=(
                    f"ready={lane.ready_count}; partial={lane.partial_count}; "
                    f"blocked={lane.blocked_count}; excluded={lane.excluded_count}; total={lane.total_count}"
                ),
                next_safe_command=lane.next_safe_command,
                proof_command=lane.proof_command,
                proceed_boundary=_lane_proceed_boundary(lane),
            )
        )
    return tuple(board)


def build_source_proof_gate(
    lane: str,
    *,
    top_n: int = 10,
    session_preflight: dict[str, Any] | None = None,
) -> CoverageExpansionSourceProofGate:
    normalized = _normalize_planner_lane(lane)
    if normalized == "price_coverage":
        return CoverageExpansionSourceProofGate(
            lane=normalized,
            status="dry_run_first",
            evidence_to_collect=(
                "reviewed dry-run ticker scope",
                "provider/source notes for refreshed rows",
                "before and after readiness counts",
            ),
            accepted_sources=(
                "reviewed free-provider price rows",
                "normalized manual OHLCV files with source label",
                "local import rows that pass validation and preview",
            ),
            rejected_shortcuts=(
                "unreviewed full-universe refresh",
                "price rows without source/date/close validation",
                "committing broad generated CSV churn by default",
            ),
            review_commands=(
                f"make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N={top_n} PROVIDER=auto",
                "make price-validate && make price-preview",
                "make readiness-snapshot PROFILE=<default|demo|local> && make price-validate && make price-preview && make price-apply && make reviewed-batch-compare PROFILE=<default|demo|local> LANE=prices BATCH_ID=<reviewed_batch_id> REVIEW_DATE=<yyyy-mm-dd> && make status-check TOP_N=5",
            ),
            proof_ready_when="dry-run scope is reviewed, local price rows validate, readiness is rebuilt, and changed artifacts are classified.",
        )
    if normalized in {"fundamentals_dcf", "share_count_proof"}:
        sec_unavailable = _session_sec_unavailable(session_preflight)
        required = (
            "trusted revenue/free-cash-flow/free-cash-flow margin rows"
            if normalized == "fundamentals_dcf"
            else "trusted shares_outstanding row"
        )
        if sec_unavailable:
            first_review_command = f"make fundamentals-source-ladder-queue TOP_N={top_n}"
            source_evidence = "trusted local/manual source evidence; SEC is unavailable in this session"
            accepted_sources = (
                "existing trusted local fundamentals rows",
                "configured Yahoo/yfinance, FMP, Alpha Vantage, or Finnhub ladder rows that pass validation",
                "trusted manual fundamentals import rows with source",
                "previously reviewed SEC company facts rows already present locally",
            )
        else:
            first_review_command = f"make fundamentals-source-ladder-queue TOP_N={top_n}"
            source_evidence = "source file or fundamentals source-ladder staging evidence"
            accepted_sources = (
                "SEC company facts staging reviewed by the operator",
                "configured Yahoo/yfinance, FMP, Alpha Vantage, or Finnhub ladder rows that pass validation",
                "trusted manual fundamentals import rows with source",
                "existing trusted local fundamentals rows",
            )
        return CoverageExpansionSourceProofGate(
            lane=normalized,
            status="source_required",
            evidence_to_collect=(
                required,
                source_evidence,
                "validate/preview result and rejected-row status",
                "before and after DCF readiness output",
            ),
            accepted_sources=accepted_sources,
            rejected_shortcuts=(
                "placeholder fundamentals",
                "shares inferred from price, market cap, or peers",
                "DCF unlock claimed before rebuilt readiness and report proof",
            ),
            review_commands=(
                first_review_command,
                "make imports-validate IMPORT_TICKERS=<ticker-or-reviewed-batch> && make imports-preview IMPORT_TICKERS=<ticker-or-reviewed-batch>",
                "make readiness-snapshot PROFILE=<default|demo|local> && make imports-validate IMPORT_TICKERS=<ticker-or-reviewed-batch> && make imports-preview IMPORT_TICKERS=<ticker-or-reviewed-batch> && make imports-apply IMPORT_TICKERS=<ticker-or-reviewed-batch> && make dcf-readiness && make reviewed-batch-compare PROFILE=<default|demo|local> LANE=fundamentals BATCH_ID=<reviewed_batch_id> REVIEW_DATE=<yyyy-mm-dd>",
            ),
            proof_ready_when="source-backed rows pass validation and preview, rejected rows are reviewed, readiness is rebuilt, and the stock report proves the lane changed.",
        )
    if normalized in {"peer_mapping", "peer_valuation_inputs"}:
        return CoverageExpansionSourceProofGate(
            lane=normalized,
            status="source_required",
            evidence_to_collect=(
                "source-backed peer relationship or mapped-peer input evidence",
                "mapped-peer price/fundamental/market-cap or valuation input rows",
                "validate/preview result and rejected-row status when rows change",
                "before and after peer readiness output",
            ),
            accepted_sources=(
                "reviewed peer mapping rows with source",
                "trusted mapped-peer fundamentals or market-cap context",
                "verified mapped-peer price history when peer trend is the target",
            ),
            rejected_shortcuts=(
                "sector or industry similarity treated as trusted peer data",
                "self-peers or undocumented peer relationships",
                "peer valuation shown before mapped-peer inputs pass readiness",
            ),
            review_commands=(
                f"make peer-mapping-queue TOP_N={top_n}",
                "make imports-validate IMPORT_TICKERS=<ticker-or-reviewed-batch> && make imports-preview IMPORT_TICKERS=<ticker-or-reviewed-batch>",
                "make readiness-snapshot PROFILE=<default|demo|local> && make imports-validate IMPORT_TICKERS=<ticker-or-reviewed-batch> && make imports-preview IMPORT_TICKERS=<ticker-or-reviewed-batch> && make imports-apply IMPORT_TICKERS=<ticker-or-reviewed-batch> && make reviewed-batch-compare PROFILE=<default|demo|local> LANE=peers BATCH_ID=<reviewed_batch_id> REVIEW_DATE=<yyyy-mm-dd> && make peer-mapping-queue TOP_N=25",
            ),
            proof_ready_when="peer mappings and mapped-peer inputs are source-backed, validation/preview passes, readiness is rebuilt, and peer valuation remains blocked if inputs are still missing.",
        )
    return CoverageExpansionSourceProofGate(
        lane=normalized,
        status="locked_or_excluded",
        evidence_to_collect=(
            "trusted local or reviewed provider-assisted optional rows if the lane is earnings or estimates",
            "asset-type evidence if the lane is excluded/not applicable",
            "reviewer note when the correct outcome is skipped or excluded",
        ),
        accepted_sources=(
            "trusted local earnings rows with source",
            "trusted local analyst-estimate rows with source",
            "reviewed provider-assisted optional rows that pass validation and preview",
            "readiness/report output showing excluded/not applicable state",
        ),
        rejected_shortcuts=(
            "empty optional rows treated as analysis",
            "third-party estimates copied without trusted local/provider source review",
            "forcing operating-company valuation onto ETF/index/fund rows",
        ),
        review_commands=(
            f"make optional-context-source-ladder-queue TOP_N={top_n}",
            "make imports-validate IMPORT_TICKERS=<ticker-or-reviewed-batch> && make imports-preview IMPORT_TICKERS=<ticker-or-reviewed-batch>",
            "make optional-context-readiness",
        ),
        proof_ready_when="trusted optional rows exist and pass review, or the lane remains locked/skipped/excluded with that state recorded honestly.",
    )


def build_coverage_expansion_loop(
    root: Path | str = ".",
    *,
    lane: str = "auto",
    top_n: int = 10,
    max_candidates: int = 3500,
    provider: str = "yahoo",
    session_preflight: dict[str, Any] | None = None,
) -> CoverageExpansionLoop:
    root = Path(root)
    lanes = build_readiness_ops_lanes(root)
    steps = build_data_coverage_expansion_plan(lanes, top_n=top_n)
    normalized_requested_lane = _normalize_planner_lane(lane)
    if session_preflight is None and normalized_requested_lane == "auto":
        session_preflight = load_session_source_preflight(root)
    source_activation_lanes = {
        "auto",
        "price_coverage",
        "fundamentals_dcf",
        "share_count_proof",
        "earnings_locked",
        "analyst_estimates_locked",
    }
    if _preflight_routes_to_workflow_evidence(session_preflight) and normalized_requested_lane in source_activation_lanes:
        console = session_preflight.get("source_activation_console_v2", {}) if isinstance(session_preflight, dict) else {}
        next_command = str(console.get("next_executable_command") or "make project-status").strip() or "make project-status"
        return CoverageExpansionLoop(
            status="workflow_evidence_only",
            selected_lane="coverage_workflow_evidence",
            selected_label="Coverage Workflow Evidence",
            reviewed_batch_lane="-",
            planner_step=None,
            preflight=None,
            next_safe_action=next_command,
            copy_only_sequence=(
                next_command,
                "make session-source-preflight",
                "make coverage-frontier TOP_N=10",
                "make diff-hygiene-summary",
            ),
            do_not_proceed_if=(
                "current source-proof queues have no unreviewed executable company candidates",
                "new provider data, keyed sources, reviewed manual source rows, or changed blockers are not present",
            ),
            session_source_preflight=session_preflight,
            pivot_notes=(
                "current source-proof queues have no unreviewed executable company candidates; do not repeat reviewed dry-run loops until new source-backed rows, keyed providers, manual rows, or changed blockers appear.",
            ),
        )
    if _source_activation_required(session_preflight) and normalized_requested_lane in source_activation_lanes:
        pivot_notes: tuple[str, ...] = ()
        if _peer_mapping_ledger_covers_review_queue(root, lanes):
            pivot_notes = (
                *pivot_notes,
                "peer mapping already has reviewed proof ledger coverage for the current source-review queue; "
                "do not repeat peer-mapping source-review proof loops unless new trusted rows or new tickers appear.",
            )
        if _peer_valuation_inputs_ledger_covers_blockers(root, lanes):
            pivot_notes = (
                *pivot_notes,
                "peer valuation inputs already have reviewed proof ledger coverage for current mapped-peer input blockers; "
                "do not repeat focus-peers proof loops unless new trusted peer price or fundamentals rows appear.",
            )
        if _optional_context_ledger_covers_lanes(root, lanes):
            pivot_notes = (
                *pivot_notes,
                "optional context already has reviewed proof ledger coverage for the current universe; "
                "do not repeat optional-context worklist proof loops unless new trusted rows or new tickers appear.",
            )
        return CoverageExpansionLoop(
            status="source_activation_required",
            selected_lane="source_activation",
            selected_label="Source Activation",
            reviewed_batch_lane="-",
            planner_step=None,
            preflight=None,
            next_safe_action=(
                "Configure at least one provider key or add reviewed local source rows before running another "
                "coverage expansion batch."
            ),
            copy_only_sequence=(
                "cp config/provider_keys.env.example config/provider_keys.env",
                "chmod 600 config/provider_keys.env",
                "open -e config/provider_keys.env",
                "make session-source-preflight",
                "make readiness-ops-center",
            ),
            do_not_proceed_if=(
                "SEC is unavailable in this session",
                "Yahoo/yfinance staging is unavailable in this session",
                "no keyed fallback provider is configured",
                "local reviewed fundamentals rows do not fix current blockers",
            ),
            session_source_preflight=session_preflight,
            pivot_notes=pivot_notes,
        )
    if normalized_requested_lane == "auto" and session_preflight is not None:
        preferred_auto_lanes = _preferred_auto_lanes_from_session(session_preflight)
        if preferred_auto_lanes:
            ordered_steps = sorted(
                steps,
                key=lambda step: (
                    preferred_auto_lanes.index(step.lane) if step.lane in preferred_auto_lanes else len(preferred_auto_lanes),
                    steps.index(step),
                ),
            )
            selected = ordered_steps[0] if ordered_steps else None
        else:
            selected = _select_step(steps, lane)
    else:
        selected = _select_step(steps, lane)
    selected_lane = selected.lane if selected is not None else _normalize_planner_lane(lane)
    lane_board = build_coverage_expansion_lane_board(lanes, selected_lane=selected_lane, top_n=top_n)
    source_gate = build_source_proof_gate(selected_lane, top_n=top_n, session_preflight=session_preflight)
    if selected is None:
        return CoverageExpansionLoop(
            status="blocked_missing_lane",
            selected_lane=selected_lane,
            selected_label="No matching planner lane",
            reviewed_batch_lane="-",
            planner_step=None,
            preflight=None,
            next_safe_action=f"Run {READINESS_PREVIEW_COMMAND}, then choose a listed lane. {READINESS_PREVIEW_NOTE}",
            lane_board=lane_board,
            copy_only_sequence=(READINESS_PREVIEW_COMMAND, f"make data-coverage-planner TOP_N={top_n}", "make coverage-frontier TOP_N=10"),
            do_not_proceed_if=("no planner lane exists for the requested scope",),
            source_proof_gate=source_gate,
            session_source_preflight=session_preflight,
        )

    reviewed_lane = LANE_TO_REVIEWED_BATCH.get(selected.lane, selected.lane)
    preflight = build_reviewed_batch_preflight(
        root,
        lane=reviewed_lane,
        top_n=top_n,
        max_candidates=max_candidates,
        provider=provider,
        session_preflight=session_preflight,
    )
    status = "ready_for_reviewed_dry_run" if preflight.status == "ready_for_dry_run" else "blocked_by_preflight"
    if preflight.status != "ready_for_dry_run":
        next_safe_action = (
            "Fix the preflight gate before running the lane packet: "
            + "; ".join(preflight.do_not_proceed_if[:3])
        )
    else:
        next_safe_action = f"Run {preflight.packet_command}, review the packet, then run {preflight.dry_run_command}."

    sequence = (
        f"make coverage-expansion-loop LANE={selected.lane} TOP_N={top_n}",
        preflight.packet_command,
        preflight.snapshot_command,
        preflight.dry_run_command,
        preflight.capped_execution_command,
        "Review validation, preview, rejected rows, and apply decision before treating any source-lane change as supported",
        preflight.comparison_command,
        f"DRY_RUN=1 {preflight.proof_record_command}",
        "make diff-hygiene",
    )
    return CoverageExpansionLoop(
        status=status,
        selected_lane=selected.lane,
        selected_label=selected.label,
        reviewed_batch_lane=reviewed_lane,
        planner_step=selected,
        preflight=preflight,
        next_safe_action=next_safe_action,
        lane_board=lane_board,
        copy_only_sequence=sequence,
        do_not_proceed_if=preflight.do_not_proceed_if,
        source_proof_gate=source_gate,
        session_source_preflight=session_preflight,
    )


def render_coverage_expansion_loop(loop: CoverageExpansionLoop) -> str:
    lines = [
        "Coverage Expansion Execution Loop",
        "Read-only: this command prints the next reviewed coverage loop. It does not refresh data, stage imports, apply rows, rewrite CSVs, or record proof rows.",
        "Research-only: coverage expansion is data-readiness work, not investment advice, security ranking, or trade instruction.",
        "",
        f"Status: {loop.status}",
        f"Selected lane: {loop.selected_label} ({loop.selected_lane})",
        f"Reviewed batch lane: {loop.reviewed_batch_lane}",
        f"Next safe action: {loop.next_safe_action}",
        f"Inspection boundary: {READINESS_PREVIEW_COMMAND}. {READINESS_PREVIEW_NOTE}" if loop.status == "blocked_missing_lane" else "",
        "",
    ]
    if loop.session_source_preflight is not None:
        lines.extend(
            [
                "Session source availability:",
                f"- session_flags: {', '.join(loop.session_source_preflight.get('session_flags', [])) or '-'}",
                f"- preferred_lane_order: {', '.join(loop.session_source_preflight.get('preferred_lane_order', [])) or '-'}",
            ]
        )
        sources = loop.session_source_preflight.get("sources", {})
        if isinstance(sources, dict):
            for key in ("sec", "yfinance_stage", "local_fundamentals"):
                source = sources.get(key) or {}
                lines.append(f"- {key}: {source.get('status', 'unknown')} - {source.get('detail', '')}".rstrip())
        lines.append("")
    if loop.lane_board:
        lines.append("Lane readiness board:")
        for index, row in enumerate(loop.lane_board, start=1):
            selected = "yes" if row.selected else "no"
            lines.extend(
                [
                    f"{index}. {row.label} | selected={selected} | {row.readiness_state} | {row.workflow_mode} | unlock_impact={row.unlock_impact}",
                    f"   readiness: {row.readiness_snapshot}",
                    f"   proceed_boundary: {row.proceed_boundary}",
                    f"   next_safe_command: {row.next_safe_command}",
                    f"   proof_command: {row.proof_command}",
                ]
            )
        lines.append("")
    if loop.planner_step is not None:
        batch_scope = loop.planner_step.batch_scope
        review_gate = loop.planner_step.review_gate
        stop_condition = loop.planner_step.stop_condition
        if _session_sec_unavailable(loop.session_source_preflight) and loop.selected_lane in {"fundamentals_dcf", "share_count_proof"}:
            batch_scope = (
                "trusted-local or trusted-manual fundamentals rows for a capped reviewed company set; "
                "SEC staging is unavailable in this session"
            )
            review_gate = (
                "use trusted local/manual source proof, then require imports-validate, imports-preview, "
                "rejected-row review, and reviewed apply decision"
            )
            stop_condition = (
                "do not retry SEC in this session; if source proof is missing, mark the ticker still_blocked, "
                "skipped, or excluded with evidence and continue to the next executable lane"
            )
        lines.extend(
            [
                "Planner gate:",
                f"- batch_scope: {batch_scope}",
                f"- review_gate: {review_gate}",
                f"- stop_condition: {stop_condition}",
                f"- outcome_boundary: {loop.planner_step.outcome_boundary}",
                f"- generated_churn_policy: {loop.planner_step.generated_churn_policy}",
                "",
            ]
        )
    if loop.preflight is not None:
        lines.extend(
            [
                "Preflight gate:",
                f"- status: {loop.preflight.status}",
                f"- current_readiness_report: {'yes' if loop.preflight.current_report_exists else 'no'}",
                f"- prior_readiness_snapshot: {'yes' if loop.preflight.prior_snapshot_exists else 'no'}",
                f"- freshness: {loop.preflight.freshness_status} - {loop.preflight.freshness_message}",
                "",
            ]
        )
    if loop.source_proof_gate is not None:
        gate = loop.source_proof_gate
        lines.extend(
            [
                "Source proof intake:",
                f"- lane: {gate.lane}",
                f"- status: {gate.status}",
                "- evidence_to_collect:",
                *[f"  - {item}" for item in gate.evidence_to_collect],
                "- accepted_sources:",
                *[f"  - {item}" for item in gate.accepted_sources],
                "- rejected_shortcuts:",
                *[f"  - {item}" for item in gate.rejected_shortcuts],
                "- review_commands:",
                *[f"  - {command}" for command in gate.review_commands],
                f"- proof_ready_when: {gate.proof_ready_when}",
                "",
            ]
        )
    if loop.status == "source_activation_required":
        free_tier_limits = _free_tier_limit_summary(loop.session_source_preflight)
        preferred = [
            str(item).strip()
            for item in (loop.session_source_preflight or {}).get("preferred_lane_order", [])
            if str(item).strip()
        ]
        pivot_commands: list[str] = []
        if "peer_mapping_proof" in preferred:
            if not any("peer mapping already has reviewed proof ledger coverage" in note for note in loop.pivot_notes):
                pivot_commands.extend(
                    [
                        "make peer-mapping-queue TOP_N=25",
                        "make peer-mapping-source-review TOP_N=25",
                        "make imports-validate IMPORT_TICKERS=<ticker-or-reviewed-batch> && make imports-preview IMPORT_TICKERS=<ticker-or-reviewed-batch>",
                    ]
                )
        if "peer_valuation_local_reviewed" in preferred:
            if not any("peer valuation inputs already have reviewed proof ledger coverage" in note for note in loop.pivot_notes):
                pivot_commands.extend(
                    [
                        "make peer-mapping-queue TOP_N=25",
                        "make focus-peers TICKER=<ticker>",
                    ]
                )
        if "earnings_optional_manual" in preferred or "analyst_estimates_optional_manual" in preferred:
            if not any("optional context already has reviewed proof ledger coverage" in note for note in loop.pivot_notes):
                pivot_commands.append("make optional-context-worklist TOP_N=25")
        if "coverage_workflow_evidence" in preferred:
            pivot_commands.append("make public-wording-check && make diff-hygiene-summary")
        pivot_commands = list(dict.fromkeys(pivot_commands))
        if pivot_commands or loop.pivot_notes:
            pivot_lines = [
                "Executable pivot path while source activation is blocked:",
                "- Remote provider-backed coverage remains gated; do not run broad price/fundamentals/share-count batches.",
            ]
            if free_tier_limits:
                pivot_lines.append(f"- Free-tier limits: {free_tier_limits}.")
            pivot_lines.extend(
                [
                    *[f"- {note}" for note in loop.pivot_notes],
                    "- Use these copy-only commands to continue peer/proof workflow work without fabricating trusted data:",
                    *[f"  {index}. {command}" for index, command in enumerate(pivot_commands, start=1)],
                    "- Valid outcomes from this pivot are candidate_context_only, still_blocked, skipped, or excluded until source-backed rows pass review.",
                    "",
                ]
            )
            lines.extend(pivot_lines)
    if loop.status == "workflow_evidence_only":
        free_tier_limits = _free_tier_limit_summary(loop.session_source_preflight)
        pivot_lines = [
            "Workflow evidence pivot:",
            "- Current source-proof queues have no unreviewed executable company candidates.",
            "- Do not repeat reviewed dry-run loops until new source-backed rows, keyed providers, reviewed manual rows, or changed blockers appear.",
        ]
        if free_tier_limits:
            pivot_lines.append(f"- Free-tier limits: {free_tier_limits}.")
        pivot_lines.extend(
            [
                "- Use workflow/status evidence to keep the pilot path clear without fabricating trusted data.",
                "",
            ]
        )
        lines.extend(pivot_lines)
    lines.extend(["Copy-only loop:"])
    lines.extend(f"{index}. {command}" for index, command in enumerate(loop.copy_only_sequence, start=1))
    lines.extend(
        [
            "",
            "Do not proceed if:",
            *[f"- {condition}" for condition in loop.do_not_proceed_if],
            "",
            "Record supported only after source proof, validation, preview/apply decision, rebuilt readiness, comparison, and generated-artifact review all pass.",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print the read-only coverage expansion execution loop.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--lane", default="auto")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--max-candidates", type=int, default=3500)
    parser.add_argument("--provider", default="yahoo")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    loop = build_coverage_expansion_loop(
        args.root,
        lane=args.lane,
        top_n=args.top_n,
        max_candidates=args.max_candidates,
        provider=args.provider,
    )
    print(render_coverage_expansion_loop(loop))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
