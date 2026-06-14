"""Reviewed batch preflight checks.

The preflight command tells an operator whether the snapshot, freshness, dry-run,
comparison, and proof-ledger steps are ready before a reviewed batch. It is
read-only and does not refresh, import, apply, or infer missing data.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.readiness_comparison import DEFAULT_AFTER, DEFAULT_BEFORE
from src.reviewed_batch import normalize_batch_lane, readiness_freshness_status


LANE_LABELS = {
    "price_coverage": "Price Coverage",
    "fundamentals_dcf": "Fundamentals / DCF",
    "peer_mapping": "Peer Mapping",
    "peer_valuation_inputs": "Peer Valuation Inputs",
    "earnings_locked": "Earnings Locked Context",
    "analyst_estimates_locked": "Analyst Estimates Locked Context",
}


@dataclass(frozen=True)
class ReviewedBatchPreflight:
    lane: str
    lane_scope: str
    batch_id: str
    review_date: str
    status: str
    current_report_exists: bool
    prior_snapshot_exists: bool
    freshness_status: str
    freshness_message: str
    packet_command: str
    snapshot_command: str
    dry_run_command: str
    capped_execution_command: str
    comparison_command: str
    proof_record_command: str
    do_not_proceed_if: tuple[str, ...]
    expected_artifacts: tuple[str, ...]
    post_run_hygiene: tuple[str, ...] = (
        "make diff-hygiene",
        "make diff-hygiene-files",
        "make staged-hygiene-check after staging product/docs/tests only",
    )


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _batch_id() -> str:
    return datetime.now(timezone.utc).strftime("RB-%Y%m%dT%H%M%SZ")


def _lane_plan(lane: str, *, top_n: int, max_candidates: int, provider: str) -> tuple[str, str, tuple[str, ...]]:
    if lane == "price_coverage":
        return (
            f"make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES={max_candidates} TOP_N={top_n} PROVIDER={provider}",
            f"make price-refresh-loop MAX_CANDIDATES={max_candidates} TOP_N={top_n} PROVIDER={provider} SLEEP_SECONDS=30",
            (
                "data/prices.csv",
                "data/reports/price_coverage_report.csv",
                "data/reports/ticker_readiness_report.csv",
            ),
        )
    if lane == "fundamentals_dcf":
        return (
            f"make sec-stage-queue TOP_N={top_n}",
            "make imports-validate && make imports-preview && make imports-apply only after reviewed trusted fundamentals rows",
            (
                "data/imports/fundamentals.csv",
                "data/fundamentals.csv",
                "data/reports/dcf_readiness_report.csv",
            ),
        )
    if lane in {"peer_mapping", "peer_valuation_inputs"}:
        return (
            f"make peer-mapping-queue TOP_N={top_n}",
            "make imports-validate && make imports-preview && make imports-apply only after source-backed peer rows or mapped-peer inputs",
            (
                "data/imports/peers.csv",
                "data/peers.csv",
                "data/reports/peer_readiness_report.csv",
                "data/reports/peer_unlock_worklist.csv",
            ),
        )
    return (
        f"make optional-context-worklist TOP_N={top_n}",
        "make imports-validate && make imports-preview && make imports-apply only after trusted local optional rows",
        (
            "data/imports/earnings.csv",
            "data/imports/analyst_estimates.csv",
            "data/reports/earnings_readiness_report.csv",
            "data/reports/analyst_estimates_readiness_report.csv",
        ),
    )


def build_reviewed_batch_preflight(
    root: Path | str = ".",
    *,
    lane: str = "prices",
    top_n: int = 10,
    max_candidates: int = 3500,
    provider: str = "yahoo",
    batch_id: str | None = None,
    review_date: str | None = None,
) -> ReviewedBatchPreflight:
    root = Path(root)
    lane_codes = normalize_batch_lane(lane)
    primary_lane = lane_codes[0]
    batch_id = batch_id or _batch_id()
    review_date = review_date or _today_utc()
    freshness = readiness_freshness_status(root)
    current_report_exists = (root / DEFAULT_AFTER).exists()
    prior_snapshot_exists = (root / DEFAULT_BEFORE).exists()
    blockers: list[str] = []
    if not current_report_exists:
        blockers.append("current readiness report is missing; run make readiness")
    if not prior_snapshot_exists:
        blockers.append("prior readiness snapshot is missing; run make readiness-snapshot before a reviewed batch")
    if freshness.status in {"missing", "stale"}:
        blockers.append(f"readiness freshness is {freshness.status}; run {freshness.refresh_command}")
    blockers.extend(
        [
            "dry-run scope is not reviewed",
            "source proof is unavailable",
            "validation or preview fails",
            "generated artifacts cannot be classified before staging",
        ]
    )
    dry_run, capped_execution, artifacts = _lane_plan(
        primary_lane,
        top_n=top_n,
        max_candidates=max_candidates,
        provider=provider,
    )
    status = "ready_for_dry_run" if current_report_exists and prior_snapshot_exists and freshness.status == "current" else "needs_preflight_fix"
    lane_scope = ", ".join(LANE_LABELS.get(code, code) for code in lane_codes)
    return ReviewedBatchPreflight(
        lane=lane,
        lane_scope=lane_scope,
        batch_id=batch_id,
        review_date=review_date,
        status=status,
        current_report_exists=current_report_exists,
        prior_snapshot_exists=prior_snapshot_exists,
        freshness_status=freshness.status,
        freshness_message=freshness.message,
        packet_command=f"make reviewed-batch LANE={lane} TOP_N={top_n}",
        snapshot_command="make readiness-snapshot",
        dry_run_command=dry_run,
        capped_execution_command=capped_execution,
        comparison_command=f"make reviewed-batch-compare LANE={lane} BATCH_ID={batch_id} REVIEW_DATE={review_date} TOP_N={top_n}",
        proof_record_command=(
            f'make reviewed-batch-proof-record BATCH_ID="{batch_id}" LANE="{lane}" REVIEW_DATE="{review_date}" '
            'FINAL_OUTCOME="<supported|still_blocked|skipped|excluded>" '
            'CHANGED_READINESS_COUNTS="<from reviewed-batch-compare>" CHANGED_TICKERS="<from reviewed-batch-compare>"'
        ),
        do_not_proceed_if=tuple(blockers),
        expected_artifacts=artifacts,
        post_run_hygiene=(
            "make diff-hygiene",
            "make diff-hygiene-files",
            "make staged-hygiene-check after staging product/docs/tests only",
        ),
    )


def render_reviewed_batch_preflight(preflight: ReviewedBatchPreflight) -> str:
    lines = [
        "Reviewed Batch Preflight",
        "Read-only: checks whether a reviewed batch has the required snapshot, freshness, dry-run, comparison, and proof-ledger steps.",
        "Research-only: this does not refresh data, apply imports, connect to brokers, route orders, or provide direct buy/sell instructions.",
        "",
        f"Status: {preflight.status}",
        f"Batch ID: {preflight.batch_id}",
        f"Review date: {preflight.review_date}",
        f"Lane: {preflight.lane} ({preflight.lane_scope})",
        f"Current readiness report exists: {'yes' if preflight.current_report_exists else 'no'}",
        f"Prior readiness snapshot exists: {'yes' if preflight.prior_snapshot_exists else 'no'}",
        f"Freshness: {preflight.freshness_status} - {preflight.freshness_message}",
        "",
        "Copyable sequence:",
        f"1. {preflight.packet_command}",
        f"2. {preflight.snapshot_command}",
        f"3. {preflight.dry_run_command}",
        f"4. {preflight.capped_execution_command}",
        f"5. make readiness",
        f"6. {preflight.comparison_command}",
        f"7. {preflight.proof_record_command}",
        "",
        "Expected artifacts to review:",
        *[f"- {artifact}" for artifact in preflight.expected_artifacts],
        "",
        "Post-run hygiene before any public commit:",
        *[f"- {command}" for command in preflight.post_run_hygiene],
        "- Keep broad generated CSV/JSON churn unstaged unless that exact artifact is intentionally reviewed evidence.",
        "",
        "Do not proceed if:",
        *[f"- {blocker}" for blocker in preflight.do_not_proceed_if],
        "",
        "Use supported only when source proof, validation, preview/apply decision, rebuilt readiness, and artifact review all support it.",
    ]
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print a reviewed batch preflight checklist.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--lane", default="prices")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--max-candidates", type=int, default=3500)
    parser.add_argument("--provider", default="yahoo")
    parser.add_argument("--batch-id", default="")
    parser.add_argument("--review-date", default="")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    preflight = build_reviewed_batch_preflight(
        args.root,
        lane=args.lane,
        top_n=args.top_n,
        max_candidates=args.max_candidates,
        provider=args.provider,
        batch_id=args.batch_id or None,
        review_date=args.review_date or None,
    )
    print(render_reviewed_batch_preflight(preflight))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
