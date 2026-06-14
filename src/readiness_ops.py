"""Read-only lane operations center for broad data readiness workflows."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


LANE_ORDER = (
    "price_coverage",
    "fundamentals_dcf",
    "peer_mapping",
    "peer_valuation_inputs",
    "earnings_locked",
    "analyst_estimates_locked",
    "excluded_not_applicable",
)


@dataclass(frozen=True)
class ReadinessLane:
    lane: str
    label: str
    readiness_state: str
    workflow_mode: str
    total_count: int
    ready_count: int
    partial_count: int
    blocked_count: int
    excluded_count: int
    unlock_impact: int
    source_lane: str
    source_readiness: str
    next_safe_command: str
    proof_command: str
    generated_churn_policy: str
    stale_proof_warning: str
    notes: str


@dataclass(frozen=True)
class CoverageFrontierOpportunity:
    rank: int
    lane: str
    label: str
    unlock_impact: int
    possible_state_move: str
    source_lane: str
    workflow_mode: str
    next_safe_command: str
    proof_command: str
    generated_churn_policy: str
    guardrail: str


@dataclass(frozen=True)
class DataCoverageExpansionStep:
    step: int
    lane: str
    label: str
    workflow_mode: str
    batch_scope: str
    next_safe_command: str
    review_gate: str
    proof_command: str
    stop_condition: str
    generated_churn_policy: str
    outcome_boundary: str


@dataclass(frozen=True)
class PeerReadinessSummary:
    total_count: int
    peer_mapping_ready: int
    peer_price_ready: int
    peer_momentum_ready: int
    peer_fundamentals_ready: int
    peer_valuation_ready: int
    peer_valuation_comparison_ready: int
    missing_mapping: int
    missing_peer_price: int
    missing_peer_momentum: int
    missing_peer_fundamentals: int
    peer_valuation_blocked: int
    source_context: str

    @property
    def trend_ready(self) -> int:
        return self.peer_momentum_ready

    @property
    def summary_text(self) -> str:
        return (
            f"mapping={self.peer_mapping_ready}/{self.total_count}; "
            f"peer_price={self.peer_price_ready}; peer_momentum={self.peer_momentum_ready}; "
            f"peer_fundamentals={self.peer_fundamentals_ready}; "
            f"peer_valuation={self.peer_valuation_ready}; "
            f"peer_valuation_comparison={self.peer_valuation_comparison_ready}; "
            f"blocked: mappings={self.missing_mapping}, peer_prices={self.missing_peer_price}, "
            f"peer_momentum={self.missing_peer_momentum}, peer_fundamentals={self.missing_peer_fundamentals}, "
            f"peer_valuation_inputs={self.peer_valuation_blocked}"
        )


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _truthy(value: object) -> bool:
    return str(value or "").strip().lower() in {"true", "1", "yes", "y"}


def _clean(value: object, fallback: str = "-") -> str:
    text = str(value or "").strip()
    if not text or text.lower() == "nan":
        return fallback
    return text


def _count_true(rows: Iterable[dict[str, str]], field: str) -> int:
    return sum(1 for row in rows if _truthy(row.get(field)))


def _count_contains(rows: Iterable[dict[str, str]], field: str, text: str) -> int:
    needle = text.lower()
    return sum(1 for row in rows if needle in str(row.get(field) or "").lower())


def _feature_row(feature_rows: list[dict[str, str]], feature: str) -> dict[str, str] | None:
    for row in feature_rows:
        if str(row.get("feature") or "").strip().lower() == feature:
            return row
    return None


def _int_value(value: object, fallback: int = 0) -> int:
    try:
        return int(float(str(value or "").strip()))
    except (TypeError, ValueError):
        return fallback


def _lane_state(*, ready: int, partial: int = 0, blocked: int = 0, excluded: int = 0) -> str:
    if excluded and not ready and not partial and not blocked:
        return "excluded"
    if ready and not partial and not blocked:
        return "ready"
    if ready or partial:
        return "partial"
    if blocked:
        return "blocked"
    return "blocked"


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return 0.0


def build_stale_proof_warning(root: Path) -> str:
    ledger = root / "data" / "reviewed_data_proofs.csv"
    proof_time = _mtime(ledger)
    if not proof_time:
        return "No reviewed proof ledger found; record proof only after reviewed source changes."
    watched = [
        root / "data" / "prices.csv",
        root / "data" / "fundamentals.csv",
        root / "data" / "peers.csv",
        root / "data" / "earnings.csv",
        root / "data" / "analyst_estimates.csv",
        root / "data" / "reports" / "ticker_readiness_report.csv",
    ]
    newer = [path.relative_to(root).as_posix() for path in watched if _mtime(path) > proof_time]
    if not newer:
        return "Latest reviewed proof is at least as recent as watched source/readiness files."
    return "Reviewed proof may be stale after changes in: " + ", ".join(newer[:6])


def _feature_counts(
    feature_rows: list[dict[str, str]],
    feature: str,
    readiness_rows: list[dict[str, str]],
    readiness_field: str,
) -> tuple[int, int, int, int, int]:
    row = _feature_row(feature_rows, feature)
    total = len(readiness_rows) or _int_value((row or {}).get("total_count"))
    ready = _int_value((row or {}).get("ready_count"), _count_true(readiness_rows, readiness_field))
    partial = _int_value((row or {}).get("partial_count"))
    blocked = _int_value((row or {}).get("blocked_count"), max(total - ready - partial, 0))
    excluded = _int_value((row or {}).get("excluded_count"))
    return total, ready, partial, blocked, excluded


def build_peer_readiness_summary(root: Path | str = ".") -> PeerReadinessSummary:
    root = Path(root)
    rows = _read_csv(root / "data" / "reports" / "peer_readiness_report.csv")
    total = len(rows)
    if not rows:
        return PeerReadinessSummary(
            total_count=0,
            peer_mapping_ready=0,
            peer_price_ready=0,
            peer_momentum_ready=0,
            peer_fundamentals_ready=0,
            peer_valuation_ready=0,
            peer_valuation_comparison_ready=0,
            missing_mapping=0,
            missing_peer_price=0,
            missing_peer_momentum=0,
            missing_peer_fundamentals=0,
            peer_valuation_blocked=0,
            source_context="data/reports/peer_readiness_report.csv missing; run make readiness before using peer sub-state counts.",
        )
    return PeerReadinessSummary(
        total_count=total,
        peer_mapping_ready=sum(1 for row in rows if str(row.get("mapping_status") or "").strip().lower() == "mapped"),
        peer_price_ready=_count_true(rows, "peer_price_ready"),
        peer_momentum_ready=_count_true(rows, "peer_momentum_ready"),
        peer_fundamentals_ready=_count_true(rows, "peer_fundamentals_ready"),
        peer_valuation_ready=_count_true(rows, "peer_valuation_ready"),
        peer_valuation_comparison_ready=_count_true(rows, "peer_valuation_comparison_ready"),
        missing_mapping=sum(1 for row in rows if str(row.get("peer_blocker_type") or "").strip() == "missing_peer_mapping"),
        missing_peer_price=sum(1 for row in rows if str(row.get("peer_blocker_type") or "").strip() == "peer_price_missing"),
        missing_peer_momentum=sum(1 for row in rows if str(row.get("peer_blocker_type") or "").strip() == "peer_momentum_missing"),
        missing_peer_fundamentals=sum(1 for row in rows if str(row.get("peer_blocker_type") or "").strip() == "peer_fundamentals_missing"),
        peer_valuation_blocked=sum(1 for row in rows if str(row.get("peer_blocker_type") or "").strip() == "peer_valuation_blocked"),
        source_context="data/reports/peer_readiness_report.csv; peer trend can be ready before peer valuation comparison is ready.",
    )


def build_readiness_ops_lanes(root: Path | str = ".") -> list[ReadinessLane]:
    root = Path(root)
    data = root / "data"
    reports = data / "reports"
    readiness_rows = _read_csv(reports / "ticker_readiness_report.csv")
    feature_rows = _read_csv(reports / "feature_readiness_summary.csv")
    peer_unlock_rows = _read_csv(reports / "peer_unlock_worklist.csv")
    peer_summary = build_peer_readiness_summary(root)
    stale_warning = build_stale_proof_warning(root)

    total = len(readiness_rows)
    price_total, price_ready, price_partial, price_blocked, price_excluded = _feature_counts(
        feature_rows, "price", readiness_rows, "price_ready"
    )
    fundamentals_total, fundamentals_ready, fundamentals_partial, fundamentals_blocked, fundamentals_excluded = _feature_counts(
        feature_rows, "fundamentals", readiness_rows, "fundamentals_ready"
    )
    dcf_ready = _count_true(readiness_rows, "dcf_ready")
    peer_ready = _count_true(readiness_rows, "peer_ready")
    peer_mapping_blocked = _count_contains(readiness_rows, "missing_data", "source-backed peer mappings")
    peer_valuation_blocked = len(peer_unlock_rows) or _count_contains(readiness_rows, "missing_data", "peer")
    earnings_ready = _count_true(readiness_rows, "earnings_ready")
    analyst_ready = _count_true(readiness_rows, "analyst_estimates_ready")
    earnings_blocked = max(total - earnings_ready, 0)
    analyst_blocked = max(total - analyst_ready, 0)
    excluded_dcf = _count_contains(readiness_rows, "excluded_features", "dcf")

    return [
        ReadinessLane(
            lane="price_coverage",
            label="Price Coverage",
            readiness_state=_lane_state(ready=price_ready, partial=price_partial, blocked=price_blocked, excluded=price_excluded),
            workflow_mode="dry_run_first",
            total_count=price_total,
            ready_count=price_ready,
            partial_count=price_partial,
            blocked_count=price_blocked,
            excluded_count=price_excluded,
            unlock_impact=price_blocked + price_partial,
            source_lane="prices",
            source_readiness="Provider-assisted price rows can be planned at scale; dry-run and capped review come first.",
            next_safe_command="make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=yahoo",
            proof_command="make readiness && make price-coverage TOP_N=25 && make status-check TOP_N=5",
            generated_churn_policy="Price refreshes can create broad CSV churn; keep refreshed data local unless intentionally reviewed.",
            stale_proof_warning=stale_warning,
            notes="Improves setup, momentum, liquidity, risk, and peer trend inputs only; it does not create fundamentals or valuation inputs.",
        ),
        ReadinessLane(
            lane="fundamentals_dcf",
            label="Fundamentals / DCF Proof",
            readiness_state=_lane_state(
                ready=min(fundamentals_ready, dcf_ready),
                partial=max(fundamentals_ready - dcf_ready, fundamentals_partial, 0),
                blocked=fundamentals_blocked,
                excluded=fundamentals_excluded,
            ),
            workflow_mode="preview_first_reviewed_apply",
            total_count=fundamentals_total,
            ready_count=dcf_ready,
            partial_count=max(fundamentals_ready - dcf_ready, fundamentals_partial, 0),
            blocked_count=fundamentals_blocked,
            excluded_count=fundamentals_excluded,
            unlock_impact=fundamentals_blocked + max(fundamentals_ready - dcf_ready, 0),
            source_lane="fundamentals",
            source_readiness="SEC staging or trusted manual rows must pass validation, preview, rejected-row review, and readiness proof.",
            next_safe_command="make sec-stage-queue TOP_N=25",
            proof_command="make imports-validate && make imports-preview && make readiness && make dcf-readiness",
            generated_churn_policy="Stage/apply only reviewed trusted fundamentals rows; avoid broad generated report churn by default.",
            stale_proof_warning=stale_warning,
            notes="Missing fundamentals keep DCF withheld; no placeholder revenue, cash flow, margin, or shares rows.",
        ),
        ReadinessLane(
            lane="peer_mapping",
            label="Peer Mapping Proof",
            readiness_state=_lane_state(ready=peer_ready, blocked=peer_mapping_blocked),
            workflow_mode="reviewed_apply",
            total_count=total,
            ready_count=peer_ready,
            partial_count=max(peer_valuation_blocked - peer_mapping_blocked, 0),
            blocked_count=peer_mapping_blocked,
            excluded_count=0,
            unlock_impact=peer_mapping_blocked,
            source_lane="peers",
            source_readiness="Peer relationships must be source-backed or clearly labeled fallback context only.",
            next_safe_command="make peer-mapping-queue TOP_N=25",
            proof_command="make imports-validate && make imports-preview && make readiness && make peer-mapping-queue TOP_N=25",
            generated_churn_policy="Apply only reviewed peer rows; do not infer trusted peers from sector similarity.",
            stale_proof_warning=stale_warning,
            notes=(
                "Source-backed peer mappings unlock peer trend checks, but peer valuation still waits for mapped-peer inputs. "
                f"Peer sub-states: {peer_summary.summary_text}."
            ),
        ),
        ReadinessLane(
            lane="peer_valuation_inputs",
            label="Peer Valuation Inputs Proof",
            readiness_state=_lane_state(ready=peer_ready, partial=max(peer_valuation_blocked - peer_mapping_blocked, 0), blocked=peer_valuation_blocked),
            workflow_mode="preview_first_reviewed_apply",
            total_count=total,
            ready_count=peer_ready,
            partial_count=max(peer_valuation_blocked - peer_mapping_blocked, 0),
            blocked_count=peer_valuation_blocked,
            excluded_count=0,
            unlock_impact=peer_valuation_blocked,
            source_lane="mapped_peer_inputs",
            source_readiness="Mapped peers need trusted price, fundamentals, market-cap, or valuation inputs before peer valuation appears.",
            next_safe_command="make peer-mapping-queue TOP_N=25",
            proof_command="make readiness && make peer-mapping-queue TOP_N=25",
            generated_churn_policy="Keep mapped-peer data changes reviewed; broad readiness/report CSV churn is not staged by default.",
            stale_proof_warning=stale_warning,
            notes=(
                "Peer trend can be partial while peer valuation remains blocked; keep those states separate. "
                f"Peer sub-states: {peer_summary.summary_text}."
            ),
        ),
        ReadinessLane(
            lane="earnings_locked",
            label="Earnings Locked Lane",
            readiness_state=_lane_state(ready=earnings_ready, blocked=earnings_blocked),
            workflow_mode="locked_manual",
            total_count=total,
            ready_count=earnings_ready,
            partial_count=0,
            blocked_count=earnings_blocked,
            excluded_count=0,
            unlock_impact=earnings_blocked,
            source_lane="earnings",
            source_readiness="Trusted local earnings rows only; empty rows render unavailable, not analysis.",
            next_safe_command="make optional-context-worklist TOP_N=25",
            proof_command="make imports-validate && make imports-preview && make optional-context-readiness",
            generated_churn_policy="Do not apply or publish earnings rows unless trusted source rows were reviewed.",
            stale_proof_warning=stale_warning,
            notes="Optional context stays locked until trusted local rows exist.",
        ),
        ReadinessLane(
            lane="analyst_estimates_locked",
            label="Analyst Estimates Locked Lane",
            readiness_state=_lane_state(ready=analyst_ready, blocked=analyst_blocked),
            workflow_mode="locked_manual",
            total_count=total,
            ready_count=analyst_ready,
            partial_count=0,
            blocked_count=analyst_blocked,
            excluded_count=0,
            unlock_impact=analyst_blocked,
            source_lane="analyst_estimates",
            source_readiness="Trusted local analyst-estimate rows only; consensus context is optional and never a recommendation.",
            next_safe_command="make optional-context-worklist TOP_N=25",
            proof_command="make imports-validate && make imports-preview && make optional-context-readiness",
            generated_churn_policy="Do not apply or publish estimates unless trusted source rows were reviewed.",
            stale_proof_warning=stale_warning,
            notes="Optional context is unavailable by design when local trusted rows are missing.",
        ),
        ReadinessLane(
            lane="excluded_not_applicable",
            label="Excluded / Not Applicable",
            readiness_state="excluded",
            workflow_mode="excluded",
            total_count=total,
            ready_count=0,
            partial_count=0,
            blocked_count=0,
            excluded_count=excluded_dcf,
            unlock_impact=0,
            source_lane="asset_type_scope",
            source_readiness="ETF/index/fund rows can support market monitoring while operating-company DCF is excluded.",
            next_safe_command="make stock-report-md TICKER=QQQ",
            proof_command="make readiness && make stock-report-md TICKER=QQQ",
            generated_churn_policy="Excluded examples are demo/report artifacts only when intentionally reviewed.",
            stale_proof_warning=stale_warning,
            notes="Excluded means not applicable, not failed; do not force company valuation onto non-company rows.",
        ),
    ]


def build_coverage_frontier(lanes: list[ReadinessLane], *, top_n: int = 10) -> list[CoverageFrontierOpportunity]:
    ranked_lanes = [
        lane
        for lane in lanes
        if lane.workflow_mode != "excluded" and lane.unlock_impact > 0
    ]
    workflow_rank = {
        "dry_run_first": 0,
        "preview_first_reviewed_apply": 1,
        "reviewed_apply": 2,
        "locked_manual": 3,
    }
    ranked_lanes.sort(key=lambda lane: (workflow_rank.get(lane.workflow_mode, 9), -lane.unlock_impact, lane.label))
    rows: list[CoverageFrontierOpportunity] = []
    for rank, lane in enumerate(ranked_lanes[: max(top_n, 0)], start=1):
        if lane.workflow_mode == "dry_run_first":
            move = "blocked/partial price coverage -> reviewed price-ready coverage after capped run proof"
        elif lane.workflow_mode == "locked_manual":
            move = "locked optional context -> partial/ready only after trusted local rows are reviewed"
        else:
            move = "blocked/partial analysis lane -> supported only after source proof and rebuilt readiness"
        rows.append(
            CoverageFrontierOpportunity(
                rank=rank,
                lane=lane.lane,
                label=lane.label,
                unlock_impact=lane.unlock_impact,
                possible_state_move=move,
                source_lane=lane.source_lane,
                workflow_mode=lane.workflow_mode,
                next_safe_command=lane.next_safe_command,
                proof_command=lane.proof_command,
                generated_churn_policy=lane.generated_churn_policy,
                guardrail="This rank is an operations queue, not a security recommendation or evidence that data is already available.",
            )
        )
    return rows


def _expansion_batch_scope(lane: ReadinessLane) -> str:
    if lane.lane == "price_coverage":
        return "broad capped missing-price batches; dry-run first; no ticker-by-ticker loop by default"
    if lane.lane == "fundamentals_dcf":
        return "SEC-stageable or trusted-manual fundamentals rows for a capped reviewed company set"
    if lane.lane == "peer_mapping":
        return "source-backed peer relationships for capped peer blockers; mapping before valuation inputs"
    if lane.lane == "peer_valuation_inputs":
        return "mapped-peer price, fundamentals, market-cap, or valuation-input proof after mappings exist"
    if lane.workflow_mode == "locked_manual":
        return "optional trusted-local rows only; keep locked until reviewed files exist"
    return "readiness lane review only"


def _expansion_next_command(lane: ReadinessLane) -> str:
    if lane.lane == "fundamentals_dcf":
        return "make fundamentals-batch-proof TOP_N=10"
    if lane.lane in {"peer_mapping", "peer_valuation_inputs"}:
        return "make peer-batch-proof TOP_N=10"
    return lane.next_safe_command


def _expansion_review_gate(lane: ReadinessLane) -> str:
    if lane.lane == "price_coverage":
        return "review dry-run tickers, provider/source notes, expected artifacts, and save readiness snapshot before any real capped refresh"
    if lane.lane == "fundamentals_dcf":
        return "verify SEC_USER_AGENT or trusted manual source proof, then require imports-validate, imports-preview, rejected-row review, and reviewed apply decision"
    if lane.lane == "peer_mapping":
        return "verify source-backed peer relationships; sector or industry similarity stays fallback context, not trusted peer mapping"
    if lane.lane == "peer_valuation_inputs":
        return "verify mapped peers have trusted price, fundamentals, market-cap, or valuation inputs before peer valuation appears"
    if lane.workflow_mode == "locked_manual":
        return "do not unlock optional context unless trusted local earnings or analyst-estimate rows exist"
    return "review readiness state and proof notes before changing local files"


def _expansion_stop_condition(lane: ReadinessLane) -> str:
    if lane.lane == "price_coverage":
        return "stop if the dry run has unexpected scope, provider failures, or source rows that cannot be reviewed"
    if lane.lane == "fundamentals_dcf":
        return "stop if SEC staging is not configured, source proof is missing, validation fails, or preview/rejected rows are unresolved"
    if lane.lane == "peer_mapping":
        return "stop if peer relationships are guessed, undocumented, self-peers only, or not source-backed"
    if lane.lane == "peer_valuation_inputs":
        return "stop if mapped peers lack trusted fundamentals, market-cap, price, or valuation-input rows"
    if lane.workflow_mode == "locked_manual":
        return "stop if no trusted local rows exist; locked optional context is the correct state"
    return "stop if proof would rely on inferred or stale data"


def _expansion_outcome_boundary(lane: ReadinessLane) -> str:
    if lane.lane == "price_coverage":
        return "price readiness can unlock setup, risk, liquidity, and benchmark review; it does not unlock fundamentals or valuation by itself"
    if lane.lane == "fundamentals_dcf":
        return "fundamentals can unlock DCF only after required trusted fields are present; no placeholder revenue, FCF, margin, shares, or market context"
    if lane.lane == "peer_mapping":
        return "peer mappings can unlock peer trend setup, but peer valuation remains blocked until mapped-peer inputs exist"
    if lane.lane == "peer_valuation_inputs":
        return "peer valuation dispersion appears only when peer input readiness passes; sector fallback remains context only"
    if lane.workflow_mode == "locked_manual":
        return "earnings and analyst estimates are optional review context, not required analysis inputs or auto-unlocks"
    return "excluded or unsupported states remain visible"


def build_data_coverage_expansion_plan(
    lanes: list[ReadinessLane],
    *,
    top_n: int = 10,
) -> list[DataCoverageExpansionStep]:
    frontier = build_coverage_frontier(lanes, top_n=top_n)
    lane_by_name = {lane.lane: lane for lane in lanes}
    steps: list[DataCoverageExpansionStep] = []
    for row in frontier:
        lane = lane_by_name.get(row.lane)
        if lane is None:
            continue
        steps.append(
            DataCoverageExpansionStep(
                step=len(steps) + 1,
                lane=lane.lane,
                label=lane.label,
                workflow_mode=lane.workflow_mode,
                batch_scope=_expansion_batch_scope(lane),
                next_safe_command=_expansion_next_command(lane),
                review_gate=_expansion_review_gate(lane),
                proof_command=lane.proof_command,
                stop_condition=_expansion_stop_condition(lane),
                generated_churn_policy=lane.generated_churn_policy,
                outcome_boundary=_expansion_outcome_boundary(lane),
            )
        )
    return steps


def render_data_coverage_expansion_plan(steps: list[DataCoverageExpansionStep]) -> str:
    lines = [
        "Data Coverage Expansion Planner",
        "Read-only: repeatable lane batches, not ticker-by-ticker work. This command does not refresh, import, apply, or rewrite local data.",
        "Research-only: planning data readiness coverage does not create security rankings, investment advice, or trade instructions.",
        "",
    ]
    if not steps:
        lines.append("No expansion steps are available. Run make readiness before using the planner if saved reports are missing.")
        return "\n".join(lines)
    for step in steps:
        lines.extend(
            [
                f"{step.step}. {step.label} | {step.workflow_mode}",
                f"   batch_scope: {step.batch_scope}",
                f"   next_safe_command: {step.next_safe_command}",
                f"   review_gate: {step.review_gate}",
                f"   proof_command: {step.proof_command}",
                f"   stop_condition: {step.stop_condition}",
                f"   generated_churn_policy: {step.generated_churn_policy}",
                f"   outcome_boundary: {step.outcome_boundary}",
            ]
        )
    return "\n".join(lines)


def render_readiness_ops_center(lanes: list[ReadinessLane]) -> str:
    lines = [
        "Data Readiness Operations Center",
        "Read-only: lane-level operations view. It does not refresh, import, apply, or rewrite local data.",
        "Research-only: lanes show data readiness and proof commands, not investment advice or trade instructions.",
        "",
    ]
    for lane in lanes:
        lines.extend(
            [
                f"- {lane.label} | {lane.readiness_state} | {lane.workflow_mode}",
                f"  counts: ready={lane.ready_count}; partial={lane.partial_count}; blocked={lane.blocked_count}; excluded={lane.excluded_count}; total={lane.total_count}",
                f"  unlock_impact: {lane.unlock_impact}",
                f"  source_lane: {lane.source_lane}; source_readiness: {lane.source_readiness}",
                f"  next_safe_command: {lane.next_safe_command}",
                f"  proof_command: {lane.proof_command}",
                f"  generated_churn_policy: {lane.generated_churn_policy}",
                f"  proof_freshness: {lane.stale_proof_warning}",
                f"  notes: {lane.notes}",
            ]
        )
    return "\n".join(lines)


def render_coverage_frontier(frontier: list[CoverageFrontierOpportunity]) -> str:
    lines = [
        "Coverage Frontier Planner",
        "Read-only: ranks batch data-readiness opportunities by unlock impact. It does not imply data is available.",
        "Research-only: this is an operations queue, not investment advice or trade instruction.",
        "",
    ]
    if not frontier:
        lines.append("No coverage frontier rows are available. Run make readiness first if saved reports are missing.")
        return "\n".join(lines)
    for row in frontier:
        lines.extend(
            [
                f"{row.rank}. {row.label} | unlock_impact={row.unlock_impact} | {row.workflow_mode}",
                f"   possible_state_move: {row.possible_state_move}",
                f"   source_lane: {row.source_lane}",
                f"   next_safe_command: {row.next_safe_command}",
                f"   proof_command: {row.proof_command}",
                f"   generated_churn_policy: {row.generated_churn_policy}",
                f"   guardrail: {row.guardrail}",
            ]
        )
    return "\n".join(lines)


def render_readiness_ops_evidence(lanes: list[ReadinessLane], frontier: list[CoverageFrontierOpportunity]) -> str:
    latest = frontier[0] if frontier else None
    lines = [
        "Readiness Ops Evidence",
        "Durable proof checklist for broad lane operations.",
        "",
        f"- lane_count: {len(lanes)}",
        f"- frontier_count: {len(frontier)}",
        f"- top_frontier_lane: {latest.label if latest else '-'}",
        f"- top_frontier_command: {latest.next_safe_command if latest else '-'}",
        "- proof_required_before_supported: source proof, validation, preview, rejected-row review, apply when appropriate, rebuilt readiness, and reviewed proof row.",
        "- generated_churn_policy: broad CSV/JSON churn stays out of commits unless intentionally reviewed evidence.",
        "- locked_lanes: earnings and analyst estimates remain locked unless trusted local rows exist.",
        "- excluded_lanes: non-company DCF exclusion remains excluded/not applicable, not failed.",
    ]
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print read-only readiness operations views.")
    parser.add_argument("--root", default=".", help="Project root.")
    parser.add_argument("--coverage-frontier", action="store_true", help="Print coverage frontier planner.")
    parser.add_argument("--expansion-plan", action="store_true", help="Print repeatable data coverage expansion plan.")
    parser.add_argument("--evidence", action="store_true", help="Print readiness ops evidence checklist.")
    parser.add_argument("--top-n", type=int, default=10)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root)
    lanes = build_readiness_ops_lanes(root)
    frontier = build_coverage_frontier(lanes, top_n=args.top_n)
    if args.evidence:
        print(render_readiness_ops_evidence(lanes, frontier))
    elif args.expansion_plan:
        print(render_data_coverage_expansion_plan(build_data_coverage_expansion_plan(lanes, top_n=args.top_n)))
    elif args.coverage_frontier:
        print(render_coverage_frontier(frontier))
    else:
        print(render_readiness_ops_center(lanes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
