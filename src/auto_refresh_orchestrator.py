from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


AUTO_REFRESH_OUTCOMES = {
    "auto_supported",
    "human_reviewed_supported",
    "candidate_context_only",
    "still_blocked",
    "skipped",
    "excluded",
}


@dataclass(frozen=True)
class LanePolicy:
    lane: str
    label: str
    cadence: str
    provider_order: tuple[str, ...]
    max_batch_size: int
    auto_apply: bool
    dry_run_command: str
    gated_apply_command: str
    proof_command: str
    source_boundary: str


@dataclass(frozen=True)
class AutoGateInput:
    lane: str
    changed_rows: int
    max_batch_size: int
    validation_status: str
    preview_status: str
    rejected_rows: int
    source_provenance_present: bool
    fabricated_values_detected: bool
    unexpected_scope_change: bool
    provider_available: bool


@dataclass(frozen=True)
class AutoGateDecision:
    status: str
    outcome: str
    reasons: tuple[str, ...]
    required_next_commands: tuple[str, ...]


@dataclass(frozen=True)
class SchedulerPlan:
    policies: tuple[LanePolicy, ...]
    schedule: str
    daily_commands: tuple[str, ...]
    weekly_commands: tuple[str, ...]
    optional_commands: tuple[str, ...]
    guardrails: tuple[str, ...]


def build_default_lane_policies() -> tuple[LanePolicy, ...]:
    return (
        LanePolicy(
            lane="daily_price_refresh",
            label="Daily Price Coverage",
            cadence="daily_after_market_close",
            provider_order=("stooq", "yahoo", "fmp", "alpha_vantage", "finnhub"),
            max_batch_size=3500,
            auto_apply=True,
            dry_run_command="make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=auto",
            gated_apply_command="make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=auto SLEEP_SECONDS=30",
            proof_command="make price-coverage TOP_N=25 && make readiness && make status-check TOP_N=5",
            source_boundary="Provider OHLCV rows only; no fabricated or padded price history.",
        ),
        LanePolicy(
            lane="daily_sec_filing_share_count",
            label="Daily SEC Filing Share Count",
            cadence="daily",
            provider_order=("sec_submissions", "sec_filing_document", "sec_companyfacts"),
            max_batch_size=25,
            auto_apply=True,
            dry_run_command="make share-count-proof-queue TOP_N=25",
            gated_apply_command=(
                "make sec-filing-share-stage TICKERS=<ticker> && "
                "make imports-validate IMPORT_TICKERS=<ticker> IMPORT_FILES=fundamentals.csv && "
                "make imports-preview IMPORT_TICKERS=<ticker> IMPORT_FILES=fundamentals.csv && "
                "make auto-apply-gate LANE=share_count CHANGED_ROWS=<rows> VALIDATION_STATUS=valid "
                "PREVIEW_STATUS=valid REJECTED_ROWS=0 SOURCE_PROVENANCE=present && "
                "make imports-apply IMPORT_TICKERS=<ticker> IMPORT_FILES=fundamentals.csv"
            ),
            proof_command="make dcf-readiness && make readiness && make stock-report-md TICKER=<ticker>",
            source_boundary="Only explicit SEC filing document facts with CIK, form, filed date, accession, and entity proof.",
        ),
        LanePolicy(
            lane="daily_fundamentals_dcf",
            label="Daily Fundamentals / DCF Source Ladder",
            cadence="daily",
            provider_order=("sec_companyfacts", "yfinance", "fmp", "alpha_vantage", "finnhub"),
            max_batch_size=25,
            auto_apply=True,
            dry_run_command="make fundamentals-source-ladder-queue TOP_N=25",
            gated_apply_command=(
                "make imports-validate IMPORT_TICKERS=<ticker> IMPORT_FILES=fundamentals.csv && "
                "make imports-preview IMPORT_TICKERS=<ticker> IMPORT_FILES=fundamentals.csv && "
                "make auto-apply-gate LANE=fundamentals_dcf CHANGED_ROWS=<rows> VALIDATION_STATUS=valid "
                "PREVIEW_STATUS=valid REJECTED_ROWS=0 SOURCE_PROVENANCE=present && "
                "make imports-apply IMPORT_TICKERS=<ticker> IMPORT_FILES=fundamentals.csv"
            ),
            proof_command="make dcf-readiness && make readiness && make stock-report-md TICKER=<ticker>",
            source_boundary="SEC/provider fundamentals only; no placeholder revenue, cash flow, margin, or share rows.",
        ),
        LanePolicy(
            lane="weekly_peer_candidates",
            label="Weekly Peer Candidate Context",
            cadence="weekly",
            provider_order=("local_industry", "sic", "sector", "reviewed_peer_sources"),
            max_batch_size=100,
            auto_apply=False,
            dry_run_command="make peer-mapping-queue TOP_N=25",
            gated_apply_command="DRY_RUN=1 make reviewed-batch LANE=peers TOP_N=25",
            proof_command="make readiness && make peer-mapping-queue TOP_N=25",
            source_boundary="Candidate peers are context only; trusted peer proof requires reviewed source-backed rows.",
        ),
        LanePolicy(
            lane="optional_earnings_estimates",
            label="Optional Earnings / Analyst Estimates",
            cadence="daily_or_weekly_when_provider_configured",
            provider_order=("yfinance", "fmp", "alpha_vantage", "finnhub"),
            max_batch_size=25,
            auto_apply=True,
            dry_run_command="make optional-context-source-ladder-queue TOP_N=10",
            gated_apply_command=(
                "make imports-validate IMPORT_TICKERS=<ticker> && "
                "make imports-preview IMPORT_TICKERS=<ticker> && "
                "make auto-apply-gate LANE=optional_context CHANGED_ROWS=<rows> VALIDATION_STATUS=valid "
                "PREVIEW_STATUS=valid REJECTED_ROWS=0 SOURCE_PROVENANCE=present && "
                "make imports-apply IMPORT_TICKERS=<ticker> && make optional-context-readiness"
            ),
            proof_command="make optional-context-readiness && make readiness",
            source_boundary="Optional provider rows only; empty or unavailable estimates stay locked.",
        ),
    )


def evaluate_auto_apply_gate(gate: AutoGateInput) -> AutoGateDecision:
    reasons: list[str] = []
    validation = gate.validation_status.strip().lower()
    preview = gate.preview_status.strip().lower()

    if not gate.provider_available:
        reasons.append("provider or source path is unavailable")
    if validation not in {"valid", "passed", "ok"}:
        reasons.append("validation did not pass")
    if preview not in {"valid", "passed", "ok"}:
        reasons.append("preview did not pass")
    if gate.rejected_rows != 0:
        reasons.append("rejected rows are present")
    if not gate.source_provenance_present:
        reasons.append("source provenance is missing")
    if gate.fabricated_values_detected:
        reasons.append("fabricated values were detected")
    if gate.unexpected_scope_change:
        reasons.append("preview changed an unexpected scope")
    if gate.changed_rows < 1:
        reasons.append("no changed rows to apply")
    if gate.changed_rows > gate.max_batch_size:
        reasons.append("changed row count exceeds lane max batch size")

    if reasons:
        return AutoGateDecision(
            status="blocked",
            outcome="still_blocked",
            reasons=tuple(reasons),
            required_next_commands=(
                "record auto-refresh proof with FINAL_OUTCOME=still_blocked",
                "pivot to the next executable lane",
            ),
        )

    return AutoGateDecision(
        status="auto_apply_ready",
        outcome="auto_supported",
        reasons=("validation, preview, provenance, scope, and no-fabrication gates passed",),
        required_next_commands=(
            "make imports-apply IMPORT_TICKERS=<ticker-or-reviewed-batch>",
            "make readiness && make reviewed-batch-proof-record FINAL_OUTCOME=auto_supported",
        ),
    )


def build_scheduler_plan(
    policies: Iterable[LanePolicy] | None = None,
    *,
    schedule: str = "all",
) -> SchedulerPlan:
    selected = tuple(policies or build_default_lane_policies())
    def _commands_for(policy: LanePolicy) -> tuple[str, str]:
        return (policy.dry_run_command, policy.gated_apply_command)

    daily = tuple(
        command
        for policy in selected
        if policy.cadence.startswith("daily") and "optional" not in policy.lane
        for command in _commands_for(policy)
    )
    weekly = tuple(
        command
        for policy in selected
        if policy.cadence.startswith("weekly")
        for command in _commands_for(policy)
    )
    optional = tuple(
        command
        for policy in selected
        if "optional" in policy.lane
        for command in _commands_for(policy)
    )
    return SchedulerPlan(
        policies=selected,
        schedule=schedule,
        daily_commands=daily if schedule in {"all", "daily"} else (),
        weekly_commands=weekly if schedule in {"all", "weekly"} else (),
        optional_commands=optional if schedule in {"all", "optional"} else (),
        guardrails=(
            "Research-only.",
            "No investment advice.",
            "No broker integration.",
            "No auto-trading, order routing, or direct buy/sell instructions.",
            "No fabricated prices, fundamentals, shares, peers, earnings, estimates, or valuation inputs.",
            "Generated CSV/JSON/report churn stays excluded unless intentionally reviewed evidence.",
        ),
    )


def render_scheduler_plan(plan: SchedulerPlan) -> str:
    lines = [
        "Auto Refresh Orchestrator Plan",
        "Read-only plan: this command prints scheduler-ready coverage commands and deterministic auto-apply gates.",
        "Research-only: no broker integration, no auto-trading, no order routing, and no direct buy/sell instructions.",
        "",
        "Proof outcomes: auto_supported, human_reviewed_supported, candidate_context_only, still_blocked, skipped, excluded.",
        "",
        "Daily commands:",
    ]
    lines.extend(f"- {command}" for command in plan.daily_commands)
    lines.append("Weekly commands:")
    lines.extend(f"- {command}" for command in plan.weekly_commands)
    lines.append("Optional provider-gated commands:")
    lines.extend(f"- {command}" for command in plan.optional_commands)
    lines.append("Lane policies:")
    for policy in plan.policies:
        lines.append(
            f"- {policy.label}: cadence={policy.cadence}; max_batch_size={policy.max_batch_size}; "
            f"auto_apply={str(policy.auto_apply).lower()}; providers={','.join(policy.provider_order)}"
        )
        lines.append(f"  source boundary: {policy.source_boundary}")
        lines.append(f"  gated apply: {policy.gated_apply_command}")
        lines.append(f"  proof: {policy.proof_command}")
    lines.append("Guardrails:")
    lines.extend(f"- {guardrail}" for guardrail in plan.guardrails)
    return "\n".join(lines)


def _build_gate_from_args(args: argparse.Namespace) -> AutoGateInput:
    return AutoGateInput(
        lane=args.gate_lane,
        changed_rows=args.changed_rows,
        max_batch_size=args.max_batch_size,
        validation_status=args.validation_status,
        preview_status=args.preview_status,
        rejected_rows=args.rejected_rows,
        source_provenance_present=args.source_provenance == "present",
        fabricated_values_detected=args.fabricated_values == "detected",
        unexpected_scope_change=args.scope_change == "unexpected",
        provider_available=args.provider_status == "available",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan and gate unattended source-backed coverage refreshes.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--schedule", choices=("all", "daily", "weekly", "optional"), default="all")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--gate-lane", default="")
    parser.add_argument("--changed-rows", type=int, default=0)
    parser.add_argument("--max-batch-size", type=int, default=25)
    parser.add_argument("--validation-status", default="not_run")
    parser.add_argument("--preview-status", default="not_run")
    parser.add_argument("--rejected-rows", type=int, default=0)
    parser.add_argument("--source-provenance", choices=("present", "missing"), default="missing")
    parser.add_argument("--fabricated-values", choices=("none", "detected"), default="none")
    parser.add_argument("--scope-change", choices=("expected", "unexpected"), default="expected")
    parser.add_argument("--provider-status", choices=("available", "unavailable"), default="available")
    args = parser.parse_args(argv)
    Path(args.root).resolve()

    if args.gate_lane:
        decision = evaluate_auto_apply_gate(_build_gate_from_args(args))
        if args.json:
            print(json.dumps(asdict(decision), indent=2, sort_keys=True))
        else:
            print("Auto Apply Gate")
            print(f"status: {decision.status}")
            print(f"outcome: {decision.outcome}")
            print("reasons:")
            for reason in decision.reasons:
                print(f"- {reason}")
            print("required_next_commands:")
            for command in decision.required_next_commands:
                print(f"- {command}")
        return 0 if decision.status == "auto_apply_ready" else 2

    plan = build_scheduler_plan(schedule=args.schedule)
    if args.json:
        print(json.dumps(asdict(plan), indent=2, sort_keys=True))
    else:
        print(render_scheduler_plan(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
