from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from src.session_source_preflight import build_session_source_preflight


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
            source_boundary=(
                "Optional provider rows only; earnings timing or price-target-only rows are candidate_context_only "
                "until earnings metrics or EPS/revenue estimate fields unlock readiness."
            ),
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
    all_policies = tuple(policies or build_default_lane_policies())

    def _policy_matches_schedule(policy: LanePolicy) -> bool:
        if schedule == "all":
            return True
        if schedule == "daily":
            return policy.cadence.startswith("daily") and "optional" not in policy.lane
        if schedule == "weekly":
            return policy.cadence.startswith("weekly")
        if schedule == "optional":
            return "optional" in policy.lane
        return True

    selected = tuple(policy for policy in all_policies if _policy_matches_schedule(policy))

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
            "Run make session-source-preflight before scheduler batches.",
            "Free-tier fallback caps: fmp<=250/day and <=25/run; alpha_vantage<=25/day and <=5/run; finnhub<=60/day and <=10/run.",
            "Do not repeat exhausted source-proof queues; run make coverage-expansion-loop TOP_N=10 and pivot to workflow evidence until new source-backed rows, keyed providers, reviewed manual rows, or changed blockers appear.",
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
        "Source activation boundaries:",
        "- make session-source-preflight",
        "- Free-tier fallback caps: fmp<=250/day and <=25/run; alpha_vantage<=25/day and <=5/run; finnhub<=60/day and <=10/run.",
        "- Do not repeat exhausted source-proof queues; run make coverage-expansion-loop TOP_N=10 and pivot to workflow evidence until new source-backed rows, keyed providers, reviewed manual rows, or changed blockers appear.",
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


def _human_source_gate(value: object) -> str:
    text = str(value or "-")
    labels = {
        "coverage_workflow_evidence": "workflow evidence only; current source-proof queues are exhausted",
        "fundamentals_share_count_source_ladder": "fundamentals/share-count source ladder",
        "workflow_evidence_only": "workflow evidence only",
    }
    for token, label in labels.items():
        text = text.replace(token, label)
    return text


def render_scheduler_runbook(plan: SchedulerPlan, preflight: dict[str, object] | None = None) -> str:
    schedule_label = plan.schedule.replace("_", " ").title()
    lines = [
        f"Auto Refresh {schedule_label} Runbook",
        "Compact unattended checklist. Research-only; no broker integration, no auto-trading, no order routing.",
        "",
        "Start:",
        "- make session-source-preflight",
        "- make readiness-ops-center",
        "- make coverage-frontier TOP_N=10",
        "",
    ]
    if preflight is not None:
        payload = build_auto_refresh_status_payload(preflight, plan)
        lines.extend(
            [
                "Current source gate:",
                f"- can_run_now: {_human_source_gate(payload['can_run_now'])}",
                f"- needs_setup: {payload['needs_setup']}",
                f"- avoid_repeating: {_human_source_gate(payload['avoid_repeating'])}",
                f"- next_executable_command: {payload['next_executable_command']}",
                f"- next_step_reason: {payload['next_step_reason']}",
                "- If the next executable command is project-status/provider setup, do not open broad lane loops until new source-backed rows, keyed providers, reviewed manual rows, or changed blockers appear.",
                "",
            ]
        )
    lines.append("Lane loop:")
    for index, policy in enumerate(plan.policies, start=1):
        gate_mode = (
            "Run the deterministic gate before apply; if blocked, use "
            "ALLOW_BLOCKED_GATE=1 make auto-apply-gate to record still_blocked and pivot."
            if policy.auto_apply
            else "No auto-apply; keep candidate context separate from trusted proof."
        )
        lines.extend(
            [
                f"{index}. {policy.label}",
                f"   dry-run: {policy.dry_run_command}",
                f"   gated apply: {policy.gated_apply_command}",
                f"   proof: {policy.proof_command}",
                f"   gate rule: {gate_mode}",
                f"   source boundary: {policy.source_boundary}",
            ]
        )
    lines.extend(
        [
            "",
            "After each slice:",
            "- make public-wording-check",
            "- make readiness-ops-center",
            "- make coverage-frontier TOP_N=10",
            "- make diff-hygiene-summary",
            "- git diff --check",
            "",
            "Stop/pivot rule:",
            "- If no source-backed row is available, record still_blocked/skipped/excluded and move to the next executable lane.",
            "- Keep generated CSV/JSON/report churn excluded unless intentionally reviewed evidence.",
        ]
    )
    return "\n".join(lines)


def _join_values(value: object) -> str:
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value if str(item).strip()) or "-"
    if isinstance(value, dict):
        formatted_limits = []
        for provider, limits in value.items():
            if not isinstance(limits, dict):
                continue
            daily_limit = limits.get("recommended_daily_request_limit")
            batch_size = limits.get("recommended_batch_size")
            if daily_limit and batch_size:
                formatted_limits.append(f"{provider}<={daily_limit}/day and <={batch_size}/run")
        if formatted_limits:
            return "; ".join(formatted_limits)
    text = str(value or "").strip()
    return text or "-"


def render_auto_refresh_status(preflight: dict[str, object], plan: SchedulerPlan) -> str:
    payload = build_auto_refresh_status_payload(preflight, plan)
    categories = payload["source_categories"]
    lines = [
        "Auto Refresh Status",
        "Read-only scheduler summary. It does not refresh, import, apply, or rewrite local data.",
        "Research-only: no investment advice, broker actions, auto-trading, order routing, or direct buy/sell instructions.",
        "",
        f"source_activation: {payload['source_activation']}",
        f"source_activation_reason: {_human_source_gate(payload['source_activation_reason'])}",
        f"can_run_now: {_human_source_gate(payload['can_run_now'])}",
        f"needs_setup: {payload['needs_setup']}",
        f"avoid_repeating: {_human_source_gate(payload['avoid_repeating'])}",
        f"next_executable_command: {payload['next_executable_command']}",
        f"next_step_reason: {payload['next_step_reason']}",
        f"next_runbook: {payload['next_runbook']}",
        "",
        "source_categories:",
        f"- free_public_available: {categories['free_public_available']}",
        f"- keyed_free_tier_available: {categories['keyed_free_tier_available']}",
        f"- optional_broker_disabled: {categories['optional_broker_disabled']}",
        f"- paid_or_locked: {categories['paid_or_locked']}",
        "",
        f"free_tier_batch_limits: {payload['free_tier_batch_limits']}",
        f"pivot_rule: {payload['pivot_rule']}",
        f"artifact_policy: {payload['artifact_policy']}",
    ]
    return "\n".join(lines)


def build_auto_refresh_status_payload(preflight: dict[str, object], plan: SchedulerPlan) -> dict[str, object]:
    activation = preflight.get("source_activation", {})
    activation = activation if isinstance(activation, dict) else {}
    categories = preflight.get("source_categories", {})
    categories = categories if isinstance(categories, dict) else {}
    console = preflight.get("source_activation_console_v2", {})
    console = console if isinstance(console, dict) else {}
    operator_summary = console.get("operator_summary", {})
    operator_summary = operator_summary if isinstance(operator_summary, dict) else {}

    next_command = _join_values(console.get("next_executable_command") or operator_summary.get("next_step"))
    schedule = plan.schedule
    return {
        "source_activation": _join_values(activation.get("status")),
        "source_activation_reason": _join_values(activation.get("reason")),
        "can_run_now": _join_values(operator_summary.get("can_run_now") or console.get("next_executable_lane")),
        "needs_setup": _join_values(operator_summary.get("needs_setup")),
        "avoid_repeating": _join_values(operator_summary.get("avoid_repeating")),
        "next_executable_command": next_command,
        "next_step_reason": _join_values(operator_summary.get("next_step_reason") or activation.get("next_action")),
        "next_runbook": f"make auto-refresh-runbook SCHEDULE={schedule}",
        "source_categories": {
            "free_public_available": _join_values(categories.get("free_public_available")),
            "keyed_free_tier_available": _join_values(categories.get("keyed_free_tier_available")),
            "optional_broker_disabled": _join_values(categories.get("optional_broker_disabled")),
            "paid_or_locked": _join_values(categories.get("paid_or_locked")),
        },
        "free_tier_batch_limits": _join_values(console.get("free_tier_batch_limits")),
        "pivot_rule": "if a source path is unavailable or already reviewed non-actionable, record the outcome once and move to the next executable lane.",
        "artifact_policy": "generated CSV/JSON/report churn stays excluded unless intentionally reviewed evidence.",
    }


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
    parser.add_argument("--runbook", action="store_true")
    parser.add_argument("--status", action="store_true")
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
    parser.add_argument(
        "--blocked-exit-zero",
        action="store_true",
        help=(
            "Return zero for blocked gate reports so a scheduler can record the outcome and pivot. "
            "Do not use in a shell chain that continues directly to imports-apply."
        ),
    )
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
        if decision.status == "auto_apply_ready" or args.blocked_exit_zero:
            return 0
        return 2

    plan = build_scheduler_plan(schedule=args.schedule)
    if args.status:
        preflight = build_session_source_preflight(Path(args.root).resolve())
        if args.json:
            print(json.dumps(build_auto_refresh_status_payload(preflight, plan), indent=2, sort_keys=True))
        else:
            print(render_auto_refresh_status(preflight, plan))
        return 0
    if args.json:
        print(json.dumps(asdict(plan), indent=2, sort_keys=True))
    elif args.runbook:
        preflight = build_session_source_preflight(Path(args.root).resolve())
        print(render_scheduler_runbook(plan, preflight))
    else:
        print(render_scheduler_plan(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
