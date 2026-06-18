"""Read-only pilot readiness checklist for public/demo pilot packaging."""

from __future__ import annotations

import argparse
import csv
import subprocess
from dataclasses import dataclass
from pathlib import Path

from scripts.diff_hygiene import group_entries, load_status

from src.readiness_ops import build_data_coverage_proof_queues
from src.reviewed_batch import readiness_freshness_status


VALID_STATUSES = {"green", "manual", "blocked"}


@dataclass(frozen=True)
class PilotReadinessCheck:
    area: str
    status: str
    title: str
    detail: str
    command: str
    stop_rule: str


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _git_status_line(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "status", "--short", "--branch"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        return "git status unavailable"
    first_line = result.stdout.splitlines()[0] if result.stdout.splitlines() else ""
    return first_line or "git status unavailable"


def _sync_check(root: Path) -> PilotReadinessCheck:
    line = _git_status_line(root)
    lowered = line.lower()
    if "behind" in lowered:
        status = "blocked"
        detail = f"{line}; pull/reconcile remote changes before a public pilot package."
        command = "git pull --ff-only"
        stop_rule = "Stop if the branch is behind or diverged; do not package stale local code."
    elif "ahead" in lowered:
        status = "manual"
        detail = f"{line}; reviewed local commits still need a push before the GitHub pilot link is current."
        command = "git push origin main"
        stop_rule = "Do not push if unreviewed product changes or generated churn are staged."
    else:
        status = "green"
        detail = f"{line}; local branch is not ahead of the tracked remote."
        command = "git status --short --branch"
        stop_rule = "Stop if a later status check shows unreviewed commits or divergence."
    return PilotReadinessCheck(
        area="GitHub sync",
        status=status,
        title="GitHub branch state",
        detail=detail,
        command=command,
        stop_rule=stop_rule,
    )


def _hygiene_check(root: Path) -> PilotReadinessCheck:
    try:
        groups = group_entries(load_status(root))
    except Exception as exc:
        return PilotReadinessCheck(
            area="Diff hygiene",
            status="blocked",
            title="Diff hygiene unavailable",
            detail=f"Could not classify the dirty tree: {exc}",
            command="make diff-hygiene-summary",
            stop_rule="Stop until dirty files are classified.",
        )

    product_count = len(groups["product_candidate"])
    report_count = len(groups["sample_report_candidate"])
    generated_count = len(groups["generated_csv_churn"])
    manual_count = len(groups["review_manually"])
    if product_count or report_count or manual_count:
        status = "blocked"
        detail = (
            f"{product_count} product/code/docs/test file(s), {report_count} sample report(s), "
            f"and {manual_count} manual-review path(s) are dirty."
        )
        stop_rule = "Stop before pilot packaging until product files are staged/committed or intentionally left local."
    elif generated_count:
        status = "manual"
        detail = f"{generated_count} generated CSV/JSON/report artifact(s) are dirty and excluded by default."
        stop_rule = "Do not stage broad generated churn unless those exact artifacts are reviewed pilot evidence."
    else:
        status = "green"
        detail = "Working tree has no dirty product files or generated churn."
        stop_rule = "Stop if later commands create broad generated churn."
    return PilotReadinessCheck(
        area="Generated artifact hygiene",
        status=status,
        title="Dirty tree classification",
        detail=detail,
        command="make diff-hygiene-summary",
        stop_rule=stop_rule,
    )


def _freshness_check(root: Path) -> PilotReadinessCheck:
    freshness = readiness_freshness_status(root)
    status = "green" if freshness.status == "current" else "blocked"
    command = "make status-check TOP_N=5" if freshness.status == "current" else "make readiness"
    return PilotReadinessCheck(
        area="Readiness freshness",
        status=status,
        title=f"Readiness artifacts are {freshness.status}",
        detail=freshness.message,
        command=command,
        stop_rule="Stop before quoting final counts or proof deltas if readiness artifacts are stale or missing.",
    )


def _source_gate_check(root: Path, *, top_n: int) -> PilotReadinessCheck:
    rows = build_data_coverage_proof_queues(root, top_n=top_n)
    if not rows:
        return PilotReadinessCheck(
            area="Source proof gates",
            status="blocked",
            title="Proof queues unavailable",
            detail="No DCF, fundamentals, share-count, peer, or mapped-peer proof queues could be built.",
            command="make data-coverage-proof-queues TOP_N=10",
            stop_rule="Stop until proof queues can show what is ready, blocked, or manual.",
        )
    blocked = sum(row.blocked_count for row in rows)
    partial = sum(row.partial_count for row in rows)
    leading = rows[0]
    return PilotReadinessCheck(
        area="Source proof gates",
        status="manual" if blocked or partial else "green",
        title=f"{leading.label} leads the source-review queue",
        detail=(
            f"{blocked:,} blocked and {partial:,} partial proof item(s) remain across "
            "DCF inputs, trusted fundamentals, share count, peer mapping, and peer valuation inputs. "
            "That is acceptable for pilot review only if missing inputs stay visible."
        ),
        command=f"make data-coverage-proof-queues TOP_N={top_n}",
        stop_rule="Do not call a lane supported until source proof, validate, preview, rejected-row review, apply/skip decision, rebuilt readiness, and proof record pass.",
    )


def _proof_ledger_check(root: Path) -> PilotReadinessCheck:
    rows = _read_csv(root / "data" / "reviewed_batch_proofs.csv")
    if not rows:
        status = "manual"
        title = "No reviewed batch proof rows yet"
        detail = "Pilot can start, but supported/still-blocked/skipped/excluded outcomes need ledger rows after reviewed batches."
    else:
        status = "green"
        title = f"{len(rows)} reviewed batch proof row(s)"
        latest = rows[-1]
        detail = (
            f"Latest outcome: {latest.get('final_outcome', '-')}; "
            f"lane: {latest.get('lane', '-')}; batch: {latest.get('batch_id', '-')}."
        )
    return PilotReadinessCheck(
        area="Proof ledger",
        status=status,
        title=title,
        detail=detail,
        command="make reviewed-batch-proof",
        stop_rule="Do not record supported outcomes without reviewed proof-row fields and generated-artifact review.",
    )


def _public_check_gate() -> PilotReadinessCheck:
    return PilotReadinessCheck(
        area="Public safety",
        status="manual",
        title="Run the public share gate before pilot sharing",
        detail=(
            "The pilot checklist is read-only; public-check remains the explicit test, wording, "
            "dashboard smoke, and visitor-demo gate."
        ),
        command="make public-check",
        stop_rule="Stop before public pilot sharing if public-check, public wording, dashboard smoke, or whitespace checks fail.",
    )


def _guardrail_check() -> PilotReadinessCheck:
    return PilotReadinessCheck(
        area="Research guardrails",
        status="green",
        title="Research-only boundary remains required",
        detail=(
            "Pilot surfaces must stay readiness-first and must not include broker integration, order routing, "
            "auto-trading, direct buy/sell instructions, fabricated inputs, or recommendations."
        ),
        command="make public-wording-check",
        stop_rule="Stop if any public or dashboard wording turns readiness queues into advice or trade instructions.",
    )


def build_pilot_readiness_checks(root: Path | str = ".", *, top_n: int = 10) -> list[PilotReadinessCheck]:
    root = Path(root)
    checks = [
        _sync_check(root),
        _hygiene_check(root),
        _freshness_check(root),
        _source_gate_check(root, top_n=top_n),
        _proof_ledger_check(root),
        _public_check_gate(),
        _guardrail_check(),
    ]
    return checks


def pilot_readiness_verdict(checks: list[PilotReadinessCheck]) -> str:
    if any(check.status == "blocked" for check in checks):
        return "blocked"
    if any(check.status == "manual" for check in checks):
        return "pilot-ready with manual gates"
    return "pilot-ready"


def render_pilot_readiness_checks(checks: list[PilotReadinessCheck]) -> str:
    verdict = pilot_readiness_verdict(checks)
    lines = [
        "Pilot Readiness Checklist",
        "Read-only: this checklist does not refresh data, apply imports, stage files, commit, push, or rewrite CSVs.",
        "Research-only: this is a pilot packaging gate, not investment advice, ranking, recommendation, or trade instruction.",
        f"Verdict: {verdict}",
        "",
        "Area | Status | Gate | Detail | Command",
        "--- | --- | --- | --- | ---",
    ]
    for check in checks:
        lines.append(
            " | ".join([check.area, check.status, check.title, check.detail, check.command])
        )
    lines.append("")
    lines.append("Stop rules:")
    for check in checks:
        lines.append(f"- {check.area}: {check.stop_rule}")
    lines.append("")
    lines.append(
        "Guardrail: missing fundamentals, shares, market cap, peers, earnings, estimates, valuation inputs, "
        "or metrics stay blocked until trusted source proof and review gates pass."
    )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print a read-only pilot readiness checklist.")
    parser.add_argument("--root", default=".", help="Project root.")
    parser.add_argument("--top-n", type=int, default=10)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    print(render_pilot_readiness_checks(build_pilot_readiness_checks(args.root, top_n=args.top_n)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
