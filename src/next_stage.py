from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.continuation_gate import build_continuation_gate
from src.hosted_demo_readiness import build_hosted_demo_readiness
from src.paths import resolve_project_root
from src.profile_context import build_profile_context
from src.project_status import build_project_status_payload
from src.source_activation_guide import build_provider_setup_checklist


def _stage_state(payload: dict[str, Any], stage_name: str) -> tuple[str, str, str]:
    for row in payload.get("remaining_public_stage_rows", []):
        if str(row.get("Stage") or "").strip() == stage_name:
            return (
                str(row.get("State") or "unknown").strip(),
                str(row.get("Evidence") or "").strip(),
                str(row.get("Next Action") or "").strip(),
            )
    return ("unknown", "", "")


def _hosted_url_status(root: Path) -> str:
    for check in build_hosted_demo_readiness(root):
        if check.name == "Hosted URL":
            return f"{check.status}; {check.detail}"
    return "unknown; run make hosted-demo-readiness"


def _hosted_gate_instruction(hosted_status: str) -> str:
    if hosted_status.startswith("manual_verify_required;"):
        return (
            "   Hosted URL is configured but still needs the five-page public workflow "
            "check before public copy changes."
        )
    if hosted_status.startswith("external_account_required;"):
        return (
            "   Hosted demo is awaiting external setup (underlying diagnostic: "
            "external_account_required). Continue other executable repo work until a public URL opens."
        )
    return "   Run hosted-demo-readiness to classify the hosted URL gate before changing public copy."


def _hosted_next_action(hosted_status: str) -> str:
    if hosted_status.startswith("manual_verify_required;"):
        return (
            "- If you have a hosted URL: open it, verify the five-page public "
            "workflow, then rerun public gates before changing public copy."
        )
    return (
        "- If you want a hosted URL: make hosted-demo-readiness, then follow "
        "docs/HOSTED_DEMO_DEPLOYMENT.md after choosing an external host/account."
    )


def _provider_status(root: Path) -> tuple[str, str, str]:
    checklist = build_provider_setup_checklist(root=root)
    first_answer = checklist.get("first_answer", {})
    source_answer = checklist.get("source_answer", {})
    if not isinstance(first_answer, dict):
        first_answer = {}
    if not isinstance(source_answer, dict):
        source_answer = {}
    return (
        str(source_answer.get("needs_key") or "-").strip(),
        str(source_answer.get("configured_keyed") or "-").strip(),
        str(first_answer.get("reviewed_one_ticker_smoke") or first_answer.get("one_safe_smoke") or "-").strip(),
    )


def render_next_stage(root: Path | str | None = None, *, top_n: int = 10) -> str:
    project_root = resolve_project_root(Path(root or "."))
    project_status = build_project_status_payload(project_root, top_n=top_n)
    summary = project_status["summary"]
    linkedin_state, linkedin_evidence, linkedin_next = _stage_state(project_status, "LinkedIn publish")
    source_state, source_evidence, source_next = _stage_state(project_status, "Source-proof queues")
    generated_state, generated_evidence, generated_next = _stage_state(project_status, "Generated artifacts")
    coverage_state, coverage_evidence, coverage_next = _stage_state(project_status, "Coverage depth")
    hosted_status = _hosted_url_status(project_root)
    missing_keys, configured_keys, smoke_command = _provider_status(project_root)
    workflow_continuation = project_status.get("workflow_continuation", {})
    if not isinstance(workflow_continuation, dict):
        workflow_continuation = {}
    continuation_state = str(workflow_continuation.get("State") or "unknown").strip()
    continuation_evidence = str(workflow_continuation.get("Evidence") or "").strip()
    continuation_gate = project_status.get("continuation_gate", {})
    if not isinstance(continuation_gate, dict):
        continuation_gate = {}
    if not continuation_gate:
        continuation_gate = asdict(build_continuation_gate(build_profile_context(project_root)))
    suppress_execution = bool(continuation_gate.get("suppress_execution"))
    next_safe_command = str(
        continuation_gate.get("next_safe_command") or "make project-status-check"
    ).strip()

    if suppress_execution:
        executable_lines = [f"- Readiness inspection: {next_safe_command}"]
        external_heading = "External unblock conditions (not executable now):"
        external_lines = [
            f"- Hosted account/environment: {hosted_status}",
            f"- Provider credentials: configured={configured_keys}; missing={missing_keys}; reviewed smoke after authorization={smoke_command}",
            "- Source rights, independent reviewers, and supplied point-in-time evidence remain separate external gates.",
        ]
        decision_lines = [
            f"1. Readiness inspection: {next_safe_command}",
            "   This is the sole executable continuation action until readiness evidence is tracked or separately reviewed.",
            "2. Owner gate: remote synchronization and public sharing require separate authorization.",
            "3. External gates: hosted operation, credentials, source rights, reviewers, and supplied evidence remain unavailable until their state changes.",
            "4. Stop rule: Do not run broad proof queues while the continuation gate suppresses execution.",
            "5. Artifact rule: Generated churn stays excluded unless one exact artifact is reviewed evidence.",
        ]
    else:
        executable_lines = [
            "- First safe status read: make project-status-check",
            "- Public share verification: make public-check",
        ]
        external_heading = "Remaining external unblock conditions:"
        external_lines = [
            "- Source rights, independent reviewers, and supplied point-in-time evidence remain separate external gates.",
        ]
        if hosted_status.startswith("manual_verify_required;"):
            executable_lines.append(_hosted_next_action(hosted_status))
        else:
            external_lines.append(f"- Hosted account/environment: {hosted_status}")
        if configured_keys != "-":
            executable_lines.append(
                f"- After separate reviewed authorization, run one configured-provider smoke: {smoke_command}"
            )
        elif missing_keys != "-":
            external_lines.append(
                f"- Provider credentials: configured={configured_keys}; missing={missing_keys}; reviewed smoke after authorization={smoke_command}"
            )
        decision_lines = [
            "1. Current truth: make project-status-check",
            "   Use this before reopening any proof queue or quoting coverage.",
            "2. Public share gate: make public-check",
            "   Use this before sharing the GitHub link or LinkedIn Featured card.",
            "3. Hosted app gate: make hosted-demo-readiness",
            _hosted_gate_instruction(hosted_status),
            "4. Provider key gate: make provider-setup-checklist",
            "   Run at most one configured-provider smoke after separate reviewed authorization; setup alone does not make evidence reviewable.",
            "5. Stop rule: Do not run broad proof queues unless project-status-check shows executable source-backed candidates.",
            "6. Artifact rule: Generated churn stays excluded unless one exact artifact is reviewed evidence.",
        ]

    if linkedin_next:
        external_lines.append(f"- Remote/public owner gate: {linkedin_next}")

    lines = [
        "Stock Research Command Center next-stage ladder",
        "Read-only: this target prints the current next-stage decision ladder only. It does not refresh data, import rows, stage files, commit, push, deploy, or expose secrets.",
        "",
        "Current package answer:",
        f"- Public/GitHub share: {linkedin_state}; {linkedin_evidence or 'run make public-check before sharing'}",
        f"- Coverage depth: {coverage_state}; {coverage_evidence or 'run make project-status-check before quoting counts'}",
        f"- Generated artifacts: {generated_state}; {generated_evidence or 'keep generated churn excluded by default'}",
        f"- Roadmap continuation: {continuation_state}; {continuation_evidence or 'run make project-status-check'}",
        f"- Current counts: prices {summary['tickers_with_prices']}/{summary['tickers_total']}; fundamentals/input {summary.get('tickers_fundamentals_ready', 0)}/{summary['tickers_total']}; DCF {summary['tickers_dcf_ready']}/{summary['tickers_total']}; peers {summary['tickers_peer_ready']}/{summary['tickers_total']}",
        "",
        "Next executable repo-side item:",
        *executable_lines,
        "",
        external_heading,
        *external_lines,
        "",
        f"Hosted demo status: {hosted_status}",
        f"Provider key status: configured={configured_keys}; missing={missing_keys}",
        f"Source-proof queue status: {source_state}; {source_evidence or source_next or 'run make project-status-check'}",
        "",
        "Decision ladder:",
        *decision_lines,
        "",
        "Boundary:",
        "- Research-only: no investment advice, no broker trading, no order routing, no auto-trading, and no direct buy/sell instructions.",
        "- Missing fundamentals, shares, peers, earnings, estimates, valuation inputs, and metrics stay blocked until source proof and validate/preview/apply gates pass.",
    ]
    if linkedin_next and not suppress_execution:
        lines.append(f"- LinkedIn/manual share next action: {linkedin_next}")
    if generated_next:
        lines.append(f"- Artifact hygiene next action: {generated_next}")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Print the current next-stage decision ladder.")
    parser.add_argument("--root", default=".", help="Project root")
    parser.add_argument("--top-n", type=int, default=10, help="Maximum rows for status helpers")
    args = parser.parse_args()
    print(render_next_stage(args.root, top_n=args.top_n))


if __name__ == "__main__":
    main()
