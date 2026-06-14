"""Print a read-only coverage expansion execution loop.

The loop connects the lane planner to reviewed-batch preflight, packet,
comparison, proof-record, and hygiene commands. It does not refresh data,
stage imports, apply rows, or create research recommendations.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from src.readiness_ops import (
    DataCoverageExpansionStep,
    ReadinessLane,
    build_data_coverage_expansion_plan,
    build_readiness_ops_lanes,
)
from src.reviewed_batch_preflight import ReviewedBatchPreflight, build_reviewed_batch_preflight


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


def _lane_proceed_boundary(lane: ReadinessLane) -> str:
    if lane.workflow_mode == "dry_run_first":
        return "dry-run and reviewed scope before any capped provider refresh"
    if lane.workflow_mode == "preview_first_reviewed_apply":
        return "source proof, validate, preview, rejected-row review, explicit apply decision, rebuilt readiness"
    if lane.workflow_mode == "reviewed_apply":
        return "source-backed rows only; fallback context does not become trusted data"
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
        "locked_manual": 3,
        "excluded": 4,
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


def build_coverage_expansion_loop(
    root: Path | str = ".",
    *,
    lane: str = "auto",
    top_n: int = 10,
    max_candidates: int = 3500,
    provider: str = "yahoo",
) -> CoverageExpansionLoop:
    root = Path(root)
    lanes = build_readiness_ops_lanes(root)
    steps = build_data_coverage_expansion_plan(lanes, top_n=top_n)
    selected = _select_step(steps, lane)
    selected_lane = selected.lane if selected is not None else _normalize_planner_lane(lane)
    lane_board = build_coverage_expansion_lane_board(lanes, selected_lane=selected_lane, top_n=top_n)
    if selected is None:
        return CoverageExpansionLoop(
            status="blocked_missing_lane",
            selected_lane=selected_lane,
            selected_label="No matching planner lane",
            reviewed_batch_lane="-",
            planner_step=None,
            preflight=None,
            next_safe_action="Run make readiness and make data-coverage-planner TOP_N=10, then choose a listed lane.",
            lane_board=lane_board,
            copy_only_sequence=("make readiness", f"make data-coverage-planner TOP_N={top_n}", "make coverage-frontier TOP_N=10"),
            do_not_proceed_if=("no planner lane exists for the requested scope",),
        )

    reviewed_lane = LANE_TO_REVIEWED_BATCH.get(selected.lane, selected.lane)
    preflight = build_reviewed_batch_preflight(
        root,
        lane=reviewed_lane,
        top_n=top_n,
        max_candidates=max_candidates,
        provider=provider,
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
        "make readiness",
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
        "",
    ]
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
        lines.extend(
            [
                "Planner gate:",
                f"- batch_scope: {loop.planner_step.batch_scope}",
                f"- review_gate: {loop.planner_step.review_gate}",
                f"- stop_condition: {loop.planner_step.stop_condition}",
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
