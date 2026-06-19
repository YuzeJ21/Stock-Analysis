"""Read-only pilot readiness checklist for public/demo pilot packaging."""

from __future__ import annotations

import argparse
import csv
import importlib.util
from shlex import quote
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from scripts.diff_hygiene import StatusEntry, group_entries, load_status
except ModuleNotFoundError:
    _DIFF_HYGIENE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "diff_hygiene.py"
    _DIFF_HYGIENE_SPEC = importlib.util.spec_from_file_location("stock_analysis_diff_hygiene", _DIFF_HYGIENE_PATH)
    if _DIFF_HYGIENE_SPEC is None or _DIFF_HYGIENE_SPEC.loader is None:
        raise
    _DIFF_HYGIENE_MODULE = importlib.util.module_from_spec(_DIFF_HYGIENE_SPEC)
    sys.modules[_DIFF_HYGIENE_SPEC.name] = _DIFF_HYGIENE_MODULE
    _DIFF_HYGIENE_SPEC.loader.exec_module(_DIFF_HYGIENE_MODULE)
    StatusEntry = _DIFF_HYGIENE_MODULE.StatusEntry
    group_entries = _DIFF_HYGIENE_MODULE.group_entries
    load_status = _DIFF_HYGIENE_MODULE.load_status

from src.readiness_ops import build_data_coverage_proof_queues
from src.reviewed_batch import readiness_freshness_status


VALID_STATUSES = {"green", "manual", "blocked"}
DEFAULT_PACKET_PATH = Path("outputs/pilot_readiness_packet.md")
REVIEWED_PACKET_PATH = DEFAULT_PACKET_PATH.as_posix()


@dataclass(frozen=True)
class PilotReadinessCheck:
    area: str
    status: str
    title: str
    detail: str
    command: str
    stop_rule: str


@dataclass(frozen=True)
class ReadinessSnapshot:
    total_tickers: int
    price_ready: int
    momentum_ready: int
    dcf_ready: int
    peer_ready: int
    data_sources_available: int
    data_sources_total: int
    optional_manual_lanes_locked: int
    missing_data_steps: int
    urgent_missing_data_steps: int


@dataclass(frozen=True)
class PilotHandoffItem:
    question: str
    status: str
    answer: str
    next_safe_command: str
    boundary: str


@dataclass(frozen=True)
class PilotCommitPackageItem:
    step: str
    status: str
    command: str
    boundary: str


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _truthy(value: object) -> bool:
    return str(value or "").strip().lower() in {"true", "1", "yes", "y"}


def _int_value(value: object, fallback: int = 0) -> int:
    try:
        return int(float(str(value or "").replace(",", "").strip()))
    except (TypeError, ValueError):
        return fallback


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


def _diff_hygiene_groups(root: Path) -> dict[str, list[StatusEntry]]:
    return group_entries(load_status(root))


def _git_add_command(entries: list[StatusEntry]) -> str:
    if not entries:
        return "# no product/code/docs/test files to stage"
    return "git add -- " + " ".join(quote(entry.path) for entry in entries)


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
        groups = _diff_hygiene_groups(root)
    except Exception as exc:
        return PilotReadinessCheck(
            area="Diff hygiene",
            status="blocked",
            title="Diff hygiene unavailable",
            detail=f"Could not classify the dirty tree: {exc}",
            command="make diff-hygiene-summary",
            stop_rule="Stop until dirty files are classified.",
        )

    packet_count = sum(1 for entry in groups["product_candidate"] if entry.path == REVIEWED_PACKET_PATH)
    product_count = len([entry for entry in groups["product_candidate"] if entry.path != REVIEWED_PACKET_PATH])
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
    elif generated_count or packet_count:
        status = "manual"
        packet_detail = f"{packet_count} reviewed pilot packet artifact(s) pending; " if packet_count else ""
        detail = f"{packet_detail}{generated_count} generated CSV/JSON/report artifact(s) are dirty and excluded by default."
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


def _source_gate_check(root: Path, *, top_n: int, source_queues: list[object] | None = None) -> PilotReadinessCheck:
    rows = source_queues if source_queues is not None else build_data_coverage_proof_queues(root, top_n=top_n)
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


def build_readiness_snapshot(root: Path | str = ".") -> ReadinessSnapshot:
    root = Path(root)
    readiness_rows = _read_csv(root / "data" / "reports" / "ticker_readiness_report.csv")
    try:
        from src.project_status import build_project_status_payload

        summary = build_project_status_payload(root, top_n=5)["summary"]
        total = len(readiness_rows) or _int_value(summary.get("tickers_total"))
        if total:
            return ReadinessSnapshot(
                total_tickers=total,
                price_ready=sum(1 for row in readiness_rows if _truthy(row.get("price_ready"))),
                momentum_ready=sum(1 for row in readiness_rows if _truthy(row.get("momentum_ready"))),
                dcf_ready=sum(1 for row in readiness_rows if _truthy(row.get("dcf_ready"))),
                peer_ready=sum(1 for row in readiness_rows if _truthy(row.get("peer_ready"))),
                data_sources_available=_int_value(summary.get("data_sources_available")),
                data_sources_total=_int_value(summary.get("data_sources_total")),
                optional_manual_lanes_locked=_int_value(summary.get("data_sources_optional_locked")),
                missing_data_steps=_int_value(summary.get("onboarding_actions")),
                urgent_missing_data_steps=_int_value(summary.get("critical_actions")),
            )
    except Exception:
        pass
    source_rows = _read_csv(root / "data" / "reports" / "data_source_status.csv")
    action_rows = _read_csv(root / "outputs" / "research_action_queue.csv")
    total = len(readiness_rows)
    available_sources = sum(1 for row in source_rows if str(row.get("status") or "").strip().lower() == "available")
    optional_locked = sum(
        1
        for row in source_rows
        if str(row.get("status") or "").strip().lower() in {"manual_only", "locked", "empty"}
        and _truthy(row.get("manual_fallback_available"))
    )
    urgent_steps = sum(
        1
        for row in action_rows
        if str(row.get("priority") or row.get("Priority") or "").strip().upper() in {"P0", "P1", "1", "URGENT"}
    )
    return ReadinessSnapshot(
        total_tickers=total,
        price_ready=sum(1 for row in readiness_rows if _truthy(row.get("price_ready"))),
        momentum_ready=sum(1 for row in readiness_rows if _truthy(row.get("momentum_ready"))),
        dcf_ready=sum(1 for row in readiness_rows if _truthy(row.get("dcf_ready"))),
        peer_ready=sum(1 for row in readiness_rows if _truthy(row.get("peer_ready"))),
        data_sources_available=available_sources,
        data_sources_total=len(source_rows),
        optional_manual_lanes_locked=optional_locked,
        missing_data_steps=len(action_rows),
        urgent_missing_data_steps=urgent_steps,
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


def _latest_proof_summary(root: Path) -> str:
    rows = _read_csv(root / "data" / "reviewed_batch_proofs.csv")
    if not rows:
        return "No reviewed batch proof rows yet."
    latest = rows[-1]
    return (
        f"{latest.get('batch_id', '-')} / {latest.get('lane', '-')} / "
        f"{latest.get('final_outcome', '-')} / {latest.get('notes', '-')}"
    )


def _excluded_generated_artifacts(root: Path) -> list[str]:
    try:
        return [entry.path for entry in _diff_hygiene_groups(root)["generated_csv_churn"]]
    except Exception:
        return []


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


def build_pilot_readiness_checks(
    root: Path | str = ".",
    *,
    top_n: int = 10,
    source_queues: list[object] | None = None,
) -> list[PilotReadinessCheck]:
    root = Path(root)
    checks = [
        _sync_check(root),
        _hygiene_check(root),
        _freshness_check(root),
        _source_gate_check(root, top_n=top_n, source_queues=source_queues),
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


def _priority_check(checks: list[PilotReadinessCheck]) -> PilotReadinessCheck | None:
    priority = {"blocked": 0, "manual": 1, "green": 2}
    if not checks:
        return None
    return sorted(checks, key=lambda check: (priority.get(check.status, 9), check.area))[0]


def _leading_source_queue(source_queues: list[object] | None) -> object | None:
    if not source_queues:
        return None
    return source_queues[0]


def _queue_value(row: object, *names: str, fallback: object = "") -> object:
    if isinstance(row, dict):
        for name in names:
            for candidate in {name, name.replace("_", " "), name.replace("_", " ").title()}:
                if candidate in row:
                    return row[candidate]
        return fallback
    for name in names:
        if hasattr(row, name):
            return getattr(row, name)
    return fallback


def build_pilot_handoff_summary(
    checks: list[PilotReadinessCheck],
    *,
    source_queues: list[object] | None = None,
    excluded_artifacts: list[str] | None = None,
) -> list[PilotHandoffItem]:
    """Build the compact reviewer handoff before detailed pilot tables."""

    verdict = pilot_readiness_verdict(checks)
    priority = _priority_check(checks)
    leading_queue = _leading_source_queue(source_queues)
    artifacts = excluded_artifacts or []

    gate_status = priority.status if priority is not None else "blocked"
    gate_answer = priority.area if priority is not None else "Run pilot readiness check"
    gate_command = priority.command if priority is not None else "make pilot-readiness-check TOP_N=10"
    gate_boundary = priority.stop_rule if priority is not None else "Stop before sharing until the pilot gate has been run."

    if leading_queue is None:
        proof_answer = "Load source-proof queues"
        proof_status = "manual"
        proof_command = "make data-coverage-proof-queues TOP_N=10"
        proof_boundary = "Do not edit source rows until proof queues are loaded and reviewed."
    else:
        proof_answer = str(_queue_value(leading_queue, "label", "queue", fallback="Source-proof queue"))
        proof_status = str(_queue_value(leading_queue, "readiness_state", "state", fallback="manual"))
        proof_command = str(
            _queue_value(
                leading_queue,
                "next_safe_command",
                "next safe command",
                fallback="make data-coverage-proof-queues TOP_N=10",
            )
        )
        proof_boundary = (
            f"{_int_value(_queue_value(leading_queue, 'blocked_count', 'blocked')):,} blocked item(s); "
            f"top blockers: {_queue_value(leading_queue, 'top_blockers', 'top blockers', fallback='-')}"
        )

    churn_status = "manual" if artifacts else "green"
    churn_answer = f"{len(artifacts)} generated artifact(s) excluded by default" if artifacts else "No generated churn detected"

    return [
        PilotHandoffItem(
            question="Can this be shared as a pilot?",
            status="blocked" if verdict == "blocked" else "manual" if "manual" in verdict else "green",
            answer=verdict,
            next_safe_command=gate_command,
            boundary="Pilot readiness is a packaging gate, not an analysis or recommendation unlock.",
        ),
        PilotHandoffItem(
            question="What must be reviewed first?",
            status=gate_status,
            answer=gate_answer,
            next_safe_command=gate_command,
            boundary=gate_boundary,
        ),
        PilotHandoffItem(
            question="What blocks deeper analysis?",
            status=proof_status,
            answer=proof_answer,
            next_safe_command=proof_command,
            boundary=proof_boundary,
        ),
        PilotHandoffItem(
            question="What stays out of staging?",
            status=churn_status,
            answer=churn_answer,
            next_safe_command="make diff-hygiene-summary",
            boundary="Do not stage broad generated CSV/JSON/report churn unless a specific artifact is intentionally reviewed evidence.",
        ),
        PilotHandoffItem(
            question="What should the reviewer run next?",
            status="copy-only",
            answer=REVIEWED_PACKET_PATH,
            next_safe_command=f"make pilot-readiness-packet OUTPUT={REVIEWED_PACKET_PATH}",
            boundary="The packet is read-only; it does not refresh data, apply imports, record proof, stage files, commit, or push.",
        ),
    ]


def build_pilot_commit_package_handoff(root: Path | str = ".") -> list[PilotCommitPackageItem]:
    """Build a copy-only product staging handoff for the current dirty tree."""

    root = Path(root)
    try:
        groups = _diff_hygiene_groups(root)
    except Exception as exc:
        return [
            PilotCommitPackageItem(
                step="Classify dirty tree",
                status="blocked",
                command="make diff-hygiene-summary",
                boundary=f"Could not classify dirty files: {exc}",
            )
        ]

    product_entries = groups["product_candidate"] + groups["sample_report_candidate"]
    generated_entries = groups["generated_csv_churn"]
    manual_entries = groups["review_manually"]
    product_status = "ready_to_stage" if product_entries and not manual_entries else "manual_review" if manual_entries else "no_product_changes"
    generated_status = "excluded" if generated_entries else "none"

    return [
        PilotCommitPackageItem(
            step="Stage reviewed product package",
            status=product_status,
            command=_git_add_command(product_entries),
            boundary=(
                f"{len(product_entries)} product/code/docs/test or reviewed Markdown file(s) are eligible for staging. "
                "Review the diff first; do not use git add -A."
            ),
        ),
        PilotCommitPackageItem(
            step="Verify staged package",
            status="copy-only",
            command="make staged-hygiene-check && git diff --cached --check",
            boundary="Stop if staged hygiene shows generated CSV/JSON churn or manual-review paths.",
        ),
        PilotCommitPackageItem(
            step="Commit reviewed package",
            status="copy-only",
            command='git commit -m "Improve pilot handoff and workflow continuity"',
            boundary="Commit only after tests, public wording, and staged hygiene pass.",
        ),
        PilotCommitPackageItem(
            step="Keep generated churn out",
            status=generated_status,
            command="make diff-hygiene-summary",
            boundary=(
                f"{len(generated_entries)} generated CSV/JSON/report artifact(s) remain excluded by default. "
                "Stage only a specific reviewed evidence artifact if intentionally selected."
            ),
        ),
    ]


def render_pilot_readiness_checks(
    checks: list[PilotReadinessCheck],
    *,
    source_queues: list[object] | None = None,
    excluded_artifacts: list[str] | None = None,
    commit_handoff: list[PilotCommitPackageItem] | None = None,
) -> str:
    verdict = pilot_readiness_verdict(checks)
    handoff = build_pilot_handoff_summary(
        checks,
        source_queues=source_queues,
        excluded_artifacts=excluded_artifacts,
    )
    lines = [
        "Pilot Readiness Checklist",
        "Read-only: this checklist does not refresh data, apply imports, stage files, commit, push, or rewrite CSVs.",
        "Research-only: this is a pilot packaging gate, not investment advice, ranking, recommendation, or trade instruction.",
        f"Verdict: {verdict}",
        "",
        "Reviewer Handoff Summary",
        "Question | Status | Answer | Next Safe Command | Boundary",
        "--- | --- | --- | --- | ---",
        *[
            " | ".join(
                [
                    item.question,
                    item.status,
                    item.answer,
                    item.next_safe_command,
                    item.boundary,
                ]
            )
            for item in handoff
        ],
        "",
        "Commit Package Handoff",
        "Step | Status | Copy-only Command | Boundary",
        "--- | --- | --- | ---",
        *[
            " | ".join(
                [
                    item.step,
                    item.status,
                    item.command,
                    item.boundary,
                ]
            )
            for item in (commit_handoff or [])
        ],
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


def _status_counts(checks: list[PilotReadinessCheck]) -> str:
    counts = {status: 0 for status in VALID_STATUSES}
    for check in checks:
        counts[check.status] = counts.get(check.status, 0) + 1
    return ", ".join(f"{status}: {counts.get(status, 0)}" for status in ("green", "manual", "blocked"))


def _markdown_table(headers: list[str], rows: list[list[object]]) -> list[str]:
    def _cell(value: object) -> str:
        return str(value).replace("\n", " ").replace("|", "\\|").strip()

    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(_cell(value) for value in row) + " |")
    return lines


def render_pilot_readiness_packet(
    *,
    checks: list[PilotReadinessCheck],
    snapshot: ReadinessSnapshot,
    source_queues: list[object],
    latest_proof: str,
    excluded_artifacts: list[str],
    commit_handoff: list[PilotCommitPackageItem] | None = None,
) -> str:
    verdict = pilot_readiness_verdict(checks)
    manual_gates = [check for check in checks if check.status == "manual"]
    blocked_gates = [check for check in checks if check.status == "blocked"]
    next_commands = list(dict.fromkeys(check.command for check in checks if check.command))
    handoff = build_pilot_handoff_summary(
        checks,
        source_queues=source_queues,
        excluded_artifacts=excluded_artifacts,
    )
    lines = [
        "# Pilot Readiness Packet",
        "",
        "> Data readiness first. Analysis second. Research decision last.",
        "",
        "This packet is a read-only reviewer summary. It does not refresh data, apply imports, record proof, stage files, commit, push, connect to brokers, route orders, auto-trade, or provide direct buy/sell instructions.",
        "",
        f"## Verdict: {verdict}",
        "",
        f"- Gate counts: {_status_counts(checks)}.",
        f"- Manual gates still required: {len(manual_gates)}.",
        f"- Blocked gates: {len(blocked_gates)}.",
        "- Blocked source inputs remain blocked until trusted source proof and review gates pass.",
        "",
        "## Reviewer Handoff Summary",
        "",
        *_markdown_table(
            ["Question", "Status", "Answer", "Next safe command", "Boundary"],
            [
                [
                    item.question,
                    item.status,
                    item.answer,
                    item.next_safe_command,
                    item.boundary,
                ]
                for item in handoff
            ],
        ),
        "",
        "## Commit Package Handoff",
        "",
        *_markdown_table(
            ["Step", "Status", "Copy-only command", "Boundary"],
            [
                [item.step, item.status, item.command, item.boundary]
                for item in (commit_handoff or [])
            ],
        ),
        "",
        "## Readiness Snapshot",
        "",
        *_markdown_table(
            ["Metric", "Current saved value"],
            [
                ["Tracked tickers", snapshot.total_tickers],
                ["Price-ready", f"{snapshot.price_ready}/{snapshot.total_tickers}"],
                ["Momentum usable", f"{snapshot.momentum_ready}/{snapshot.total_tickers}"],
                ["DCF-ready", f"{snapshot.dcf_ready}/{snapshot.total_tickers}"],
                ["Peer-ready", f"{snapshot.peer_ready}/{snapshot.total_tickers}"],
                ["Data sources available", f"{snapshot.data_sources_available}/{snapshot.data_sources_total}"],
                ["Optional/manual lanes locked", snapshot.optional_manual_lanes_locked],
                ["Missing-data steps", snapshot.missing_data_steps],
                ["Urgent missing-data steps", snapshot.urgent_missing_data_steps],
            ],
        ),
        "",
        "## Pilot Gates",
        "",
        *_markdown_table(
            ["Area", "Status", "Gate", "Detail", "Command"],
            [[check.area, check.status, check.title, check.detail, check.command] for check in checks],
        ),
        "",
        "## Source-Proof Queue Summary",
        "",
        *_markdown_table(
            ["Queue", "State", "Ready", "Partial", "Blocked", "Top blockers", "Next safest command"],
            [
                [
                    getattr(row, "label", "-"),
                    getattr(row, "readiness_state", "-"),
                    getattr(row, "ready_count", "-"),
                    getattr(row, "partial_count", "-"),
                    getattr(row, "blocked_count", "-"),
                    getattr(row, "top_blockers", "-"),
                    getattr(row, "next_safe_command", "-"),
                ]
                for row in source_queues
            ],
        ),
        "",
        "## Latest Reviewed Batch Proof",
        "",
        f"- {latest_proof}",
        "",
        "## Manual Gates Still Required",
        "",
    ]
    if manual_gates:
        lines.extend(f"- {check.area}: {check.stop_rule}" for check in manual_gates)
    else:
        lines.append("- None from the current checklist.")
    lines.extend(
        [
            "",
            "## Stop Rules",
            "",
            *[f"- {check.area}: {check.stop_rule}" for check in checks],
            "",
            "## Exact Next Safest Commands",
            "",
            *[f"- `{command}`" for command in next_commands],
            "",
            "## Generated Artifacts Excluded From Staging",
            "",
        ]
    )
    if excluded_artifacts:
        lines.extend(f"- `{path}`" for path in excluded_artifacts)
    else:
        lines.append("- No generated CSV/JSON/report churn is currently dirty.")
    lines.extend(
        [
            "",
            "## Research-Only Guardrails",
            "",
            "- This is research software, not investment advice.",
            "- No broker integration, order routing, auto-trading, options recommendations, or direct buy/sell instructions.",
            "- Do not fabricate prices, fundamentals, shares, market cap, peers, earnings, estimates, valuation inputs, metrics, or recommendations.",
            "- Preserve ready, partial, blocked, excluded, supported, still_blocked, and skipped states.",
            "- Keep broad generated CSV/JSON/report churn out of commits unless a specific artifact is intentionally reviewed evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def write_pilot_readiness_packet(
    root: Path | str = ".",
    *,
    top_n: int = 10,
    output: Path | str = DEFAULT_PACKET_PATH,
) -> Path:
    root = Path(root)
    output_path = root / Path(output)
    source_queues = build_data_coverage_proof_queues(root, top_n=top_n)
    checks = build_pilot_readiness_checks(root, top_n=top_n, source_queues=source_queues)
    packet = render_pilot_readiness_packet(
        checks=checks,
        snapshot=build_readiness_snapshot(root),
        source_queues=source_queues,
        latest_proof=_latest_proof_summary(root),
        excluded_artifacts=_excluded_generated_artifacts(root),
        commit_handoff=build_pilot_commit_package_handoff(root),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(packet, encoding="utf-8")
    return output_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print a read-only pilot readiness checklist.")
    parser.add_argument("--root", default=".", help="Project root.")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--packet", action="store_true", help="Write the reviewer-ready pilot packet.")
    parser.add_argument("--output", default=str(DEFAULT_PACKET_PATH), help="Packet output path.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.packet:
        output = write_pilot_readiness_packet(args.root, top_n=args.top_n, output=args.output)
        print(f"Wrote pilot readiness packet: {output}")
    else:
        root = Path(args.root)
        source_queues = build_data_coverage_proof_queues(root, top_n=args.top_n)
        print(
            render_pilot_readiness_checks(
                build_pilot_readiness_checks(root, top_n=args.top_n, source_queues=source_queues),
                source_queues=source_queues,
                excluded_artifacts=_excluded_generated_artifacts(root),
                commit_handoff=build_pilot_commit_package_handoff(root),
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
