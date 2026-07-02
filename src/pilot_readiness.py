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
from src.browser_qa_evidence import browser_qa_evidence_payload
from src.license_status import NO_LICENSE_SHARE_BOUNDARY, build_license_status
from src.reviewed_batch import readiness_freshness_status
from src.session_source_preflight import load_session_source_preflight
from src.source_activation_guide import build_provider_setup_checklist


VALID_STATUSES = {"green", "manual", "blocked"}
DEFAULT_PACKET_PATH = Path("outputs/pilot_readiness_packet.md")
DEFAULT_SHARE_BRIEF_PATH = Path("outputs/pilot_share_brief.md")
REVIEWED_PACKET_PATH = DEFAULT_PACKET_PATH.as_posix()
REVIEWED_SHARE_BRIEF_PATH = DEFAULT_SHARE_BRIEF_PATH.as_posix()
GENERATED_ARTIFACT_EXCLUSION_PATTERNS = (
    "data/*.csv",
    "data/reports/*.csv",
    "outputs/*.csv",
    "data/reports/ticker_readiness_report.previous.csv",
)


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


def _generated_exclusion_pattern_text() -> str:
    return "; ".join(GENERATED_ARTIFACT_EXCLUSION_PATTERNS)


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
    share_brief_count = sum(1 for entry in groups["product_candidate"] if entry.path == REVIEWED_SHARE_BRIEF_PATH)
    product_count = len(
        [
            entry
            for entry in groups["product_candidate"]
            if entry.path not in {REVIEWED_PACKET_PATH, REVIEWED_SHARE_BRIEF_PATH}
        ]
    )
    report_count = len(groups["sample_report_candidate"])
    generated_count = len(groups["generated_csv_churn"])
    manual_count = len(groups["review_manually"])
    if product_count or manual_count:
        status = "blocked"
        detail = (
            f"{product_count} product/code/docs/test file(s), {report_count} sample report(s), "
            f"and {manual_count} manual-review path(s) are dirty."
        )
        stop_rule = "Stop before pilot packaging until product files are staged/committed or intentionally left local."
    elif generated_count or packet_count or share_brief_count or report_count:
        status = "manual"
        packet_detail = f"{packet_count} reviewed pilot packet artifact(s) pending; " if packet_count else ""
        share_brief_detail = f"{share_brief_count} reviewed share brief artifact(s) pending; " if share_brief_count else ""
        report_detail = f"{report_count} broad sample report artifact(s) pending review; " if report_count else ""
        detail = (
            f"{packet_detail}{report_detail}"
            f"{share_brief_detail}"
            f"{generated_count} generated CSV/JSON/report artifact(s) are dirty and excluded by default."
        )
        stop_rule = (
            "Do not stage broad generated stock reports or broad generated churn unless those exact artifacts "
            "are reviewed pilot evidence."
        )
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


def _source_queues_reviewed_or_exhausted(rows: list[object]) -> bool:
    if not rows:
        return False
    for row in rows:
        text = " ".join(
            str(
                _queue_value(
                    row,
                    field,
                    field.replace("_", " "),
                    fallback="",
                )
            )
            for field in (
                "possible_state_move",
                "reviewed_proof_status",
                "source_readiness",
                "notes",
                "next_safe_command",
            )
        ).lower()
        if not (
            "reviewed proof already recorded" in text
            or "reviewed non-actionable" in text
            or "no unreviewed executable" in text
        ):
            return False
    return True


def _preflight_routes_source_gate_to_workflow(preflight: dict[str, object] | None) -> bool:
    if not isinstance(preflight, dict):
        return False
    actionability = preflight.get("source_actionability", {})
    actionability = actionability if isinstance(actionability, dict) else {}
    console = preflight.get("source_activation_console_v2", {})
    console = console if isinstance(console, dict) else {}
    operator_summary = console.get("operator_summary", {})
    operator_summary = operator_summary if isinstance(operator_summary, dict) else {}

    def _text(value: object) -> str:
        if isinstance(value, (list, tuple)):
            return " ".join(str(item) for item in value)
        return str(value or "")

    avoid_repeating = _text(operator_summary.get("avoid_repeating")).lower()
    can_run_now = _text(operator_summary.get("can_run_now") or console.get("next_executable_lane")).lower()
    return (
        str(actionability.get("do_not_repeat_without_new_source", "")).strip().lower() in {"yes", "true", "1"}
        or str(actionability.get("dcf_queue_reviewed_non_actionable", "")).strip().lower() in {"yes", "true", "1"}
        or "fundamentals_share_count_source_ladder" in avoid_repeating
        or "coverage_workflow_evidence" in can_run_now
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
    if _source_queues_reviewed_or_exhausted(rows) or _preflight_routes_source_gate_to_workflow(
        load_session_source_preflight(root)
    ):
        return PilotReadinessCheck(
            area="Source proof gates",
            status="manual" if blocked or partial else "green",
            title="Source-proof queues reviewed or exhausted",
            detail=(
                f"{blocked:,} blocked and {partial:,} partial proof item(s) remain visible, but current proof "
                "queues are already reviewed or non-actionable. Use project-status and provider setup before "
                "reopening broad proof queues."
            ),
            command="make project-status",
            stop_rule=(
                "Do not reopen broad proof queues until project-status shows executable company candidates, "
                "new source-backed rows, keyed providers, reviewed manual rows, or changed blockers."
            ),
        )
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
        detail = "Pilot can start, but supported/candidate-context-only/still-blocked/skipped/excluded outcomes need ledger rows after reviewed batches."
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


def _license_status_check(root: Path) -> PilotReadinessCheck:
    if (root / "LICENSE").exists():
        return PilotReadinessCheck(
            area="License status",
            status="green",
            title="Root LICENSE file is present",
            detail="Confirm README License wording matches the selected license before public reuse claims.",
            command="make license-status",
            stop_rule="Stop if README License wording conflicts with the selected license.",
        )
    return PilotReadinessCheck(
        area="License status",
        status="manual",
        title="No root LICENSE file found",
        detail=NO_LICENSE_SHARE_BOUNDARY,
        command="make license-status",
        stop_rule="Do not claim reuse rights until a root LICENSE is selected and README wording is updated.",
    )


def _browser_qa_evidence_check(root: Path) -> PilotReadinessCheck:
    try:
        payload = browser_qa_evidence_payload(root)
    except Exception as exc:
        return PilotReadinessCheck(
            area="Browser QA evidence",
            status="blocked",
            title="Screenshot evidence unavailable",
            detail=f"Could not inspect committed real screenshot evidence: {exc}",
            command="make browser-qa-evidence",
            stop_rule="Stop before using screenshots publicly until real app evidence can be inspected.",
        )

    verdict = str(payload.get("verdict") or "blocked")
    assets = list(payload.get("committed_screenshot_assets") or [])
    pending = [
        row
        for row in list(payload.get("manual_capture_targets") or [])
        if str(row.get("State") or "").strip().lower() == "manual_capture_pending"
    ]
    ready_assets = [
        row
        for row in assets
        if str(row.get("State") or "").strip().lower() == "ready"
    ]
    if verdict == "ready":
        status = "green"
        title = "Real screenshot evidence is ready"
        stop_rule = "Stop if later screenshots are generated thumbnails, tracebacks, or stale proof substitutes."
    elif verdict == "ready_with_manual_capture_pending":
        status = "manual"
        title = "Public screenshot ready; workflow captures pending"
        stop_rule = "Use committed real public screenshots now; capture pending workflow views in a normal browser before claiming full workflow evidence."
    else:
        status = "blocked"
        title = "Real public screenshot evidence is blocked"
        stop_rule = "Stop before public sharing until at least the real public dashboard screenshot is committed."

    pending_names = ", ".join(str(row.get("Capture Target")) for row in pending) if pending else "none"
    reviewed_asset_stage_command = str(payload.get("reviewed_asset_stage_command") or "").strip()
    reviewed_asset_note = (
        " Reviewed asset staging command is available from browser QA JSON and capture plan after visual review."
        if reviewed_asset_stage_command
        else ""
    )
    return PilotReadinessCheck(
        area="Browser QA evidence",
        status=status,
        title=title,
        detail=(
            f"{len(ready_assets)} committed screenshot asset(s) ready; "
            f"pending workflow capture(s): {pending_names}. "
            "Screenshots are product evidence only and do not refresh data or unlock blocked inputs."
            f"{reviewed_asset_note}"
        ),
        command="make browser-qa-evidence",
        stop_rule=stop_rule,
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
        _browser_qa_evidence_check(root),
        _public_check_gate(),
        _license_status_check(root),
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
    source_gate_check = next((check for check in checks if check.area == "Source proof gates"), None)

    gate_status = priority.status if priority is not None else "blocked"
    gate_answer = priority.area if priority is not None else "Run pilot readiness check"
    gate_command = priority.command if priority is not None else "make pilot-readiness-check TOP_N=10"
    gate_boundary = priority.stop_rule if priority is not None else "Stop before sharing until the pilot gate has been run."
    license_check = next((check for check in checks if check.area == "License status"), None)
    license_status = license_check.status if license_check is not None else "manual"
    license_answer = license_check.title if license_check is not None else "Review license status"
    license_command = license_check.command if license_check is not None else "docs/LICENSE_DECISION_GUIDE.md"
    license_boundary = (
        license_check.stop_rule
        if license_check is not None
        else "Do not claim reuse rights until license status is reviewed."
    )

    if source_gate_check is not None and source_gate_check.title == "Source-proof queues reviewed or exhausted":
        proof_answer = "Check source-proof gate"
        proof_status = source_gate_check.status
        proof_command = source_gate_check.command
        proof_boundary = source_gate_check.detail
    elif leading_queue is None:
        proof_answer = "Check source-proof gate"
        proof_status = "manual"
        proof_command = "make project-status"
        proof_boundary = "Run project-status first; use provider setup when source-proof queues are exhausted before reopening proof tables."
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
    churn_boundary = (
        "Keep these broad generated patterns out by default: "
        f"{_generated_exclusion_pattern_text()}. Stage only a specific artifact if it is intentionally reviewed evidence."
    )
    share_answer = (
        "Share as portfolio/demo only with manual gates; keep generated churn excluded; "
        "source-proof blockers stay visible; license boundary still applies."
    )

    return [
        PilotHandoffItem(
            question="What is the share package answer?",
            status="manual" if verdict != "blocked" else "blocked",
            answer=share_answer,
            next_safe_command="make public-check",
            boundary="This is a packaging answer only; it does not unlock analysis, source proof, reuse rights, or data freshness.",
        ),
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
            boundary=churn_boundary,
        ),
        PilotHandoffItem(
            question="What license boundary applies?",
            status=license_status,
            answer=license_answer,
            next_safe_command=license_command,
            boundary=license_boundary,
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

    product_entries = groups["product_candidate"]
    sample_report_entries = groups["sample_report_candidate"]
    generated_entries = groups["generated_csv_churn"]
    manual_entries = groups["review_manually"]
    product_status = "ready_to_stage" if product_entries and not manual_entries else "manual_review" if manual_entries else "no_product_changes"
    generated_status = "excluded" if generated_entries else "none"
    commit_command = (
        'git commit -m "Package reviewed product changes"'
        if product_entries and not manual_entries
        else "# no reviewed product package to commit"
    )
    commit_boundary = (
        "Commit only after tests, public wording, and staged hygiene pass."
        if product_entries and not manual_entries
        else "Do not create a release commit just for excluded generated churn."
    )

    return [
        PilotCommitPackageItem(
            step="Stage reviewed product package",
            status=product_status,
            command=_git_add_command(product_entries),
            boundary=(
                f"{len(product_entries)} product/code/docs/test file(s) are eligible for staging. "
                f"{len(sample_report_entries)} sample report artifact(s) stay excluded unless individually reviewed. "
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
            command=commit_command,
            boundary=commit_boundary,
        ),
        PilotCommitPackageItem(
            step="Keep generated churn out",
            status=generated_status,
            command="make diff-hygiene-summary",
            boundary=(
                f"{len(generated_entries)} generated CSV/JSON/report artifact(s) and "
                f"{len(sample_report_entries)} broad generated stock report artifact(s) remain excluded by default. "
                f"Keep these patterns out by default: {_generated_exclusion_pattern_text()}. "
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


def _sentence(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "-"
    return text if text.endswith((".", "!", "?")) else f"{text}."


def _provider_setup_checklist_rows() -> list[list[object]]:
    checklist = build_provider_setup_checklist()
    rows = []
    for row in checklist["rows"]:
        rows.append(
            [
                row["provider"],
                row["setup_state"],
                row["unlock_lanes"],
                row["usage"],
                row.get("post_setup_smoke_command", "") or "not_applicable",
                row["cannot_unlock"],
                row["safe_next_step"],
            ]
        )
    return rows


def _provider_activation_plan_lines() -> list[str]:
    checklist = build_provider_setup_checklist()
    steps = checklist.get("activation_plan", [])
    if not isinstance(steps, list) or not steps:
        return ["- Run `make project-status` before reopening broad proof loops."]
    return [f"- {step}" for step in steps]


def _provider_one_setup_lines() -> list[str]:
    checklist = build_provider_setup_checklist()
    setup_order = checklist.get("one_provider_setup_order", [])
    if not isinstance(setup_order, list):
        return []
    first = next((row for row in setup_order if isinstance(row, dict)), None)
    if not first:
        return []
    provider = str(first.get("provider") or "-")
    reason = str(first.get("why_first") or "Configure one provider before retrying broader source paths.")
    setup_env = str(first.get("setup_env") or "-")
    smoke_command = str(first.get("smoke_command") or "make session-source-preflight")
    return [
        f"- Configure first: {provider}.",
        f"- Why first: {reason}",
        f"- Setup env: `{setup_env}`.",
        f"- One-ticker smoke command: `{smoke_command}`.",
        "- Do not configure all missing providers at once; configure one, rerun preflight, smoke one ticker, then validate/preview before any apply.",
    ]


def _provider_source_bucket_lines(root: Path | str = ".") -> list[str]:
    checklist = build_provider_setup_checklist(load_session_source_preflight(Path(root)))
    source_answer = checklist.get("source_answer", {})
    if not isinstance(source_answer, dict) or not source_answer:
        return []
    return [
        "- Free public sources: " + str(source_answer.get("free_public_now", "-")),
        (
            "- Keyed free-tier fallbacks: "
            f"configured {source_answer.get('configured_keyed', '-')}; "
            f"needs key {source_answer.get('needs_key', '-')}"
        ),
        "- Optional broker boundary: " + str(source_answer.get("optional_broker", "-")),
    ]


def _share_brief_provider_setup_lines(root: Path | str = ".") -> list[str]:
    checklist = build_provider_setup_checklist(load_session_source_preflight(Path(root)))
    unlock_decision = checklist.get("coverage_unlock_decision", {})
    source_answer = checklist.get("source_answer", {})
    source_answer = source_answer if isinstance(source_answer, dict) else {}
    lines = [
        "- Next setup view: `make provider-setup-checklist`.",
        "- Real key values are never printed.",
    ]
    if source_answer:
        lines.extend(
            [
                "- Source buckets:",
                f"  - Free public sources: {source_answer.get('free_public_now', '-')}",
                (
                    "  - Keyed free-tier fallbacks: "
                    f"configured {source_answer.get('configured_keyed', '-')}; "
                    f"needs key {source_answer.get('needs_key', '-')}"
                ),
                f"  - Optional broker boundary: {source_answer.get('optional_broker', '-')}",
            ]
        )
    if isinstance(unlock_decision, dict) and unlock_decision:
        lines.extend(
            [
                "- Coverage unlock decision:",
                f"  - {unlock_decision.get('answer', 'No broad coverage batch should run from setup alone.')}",
                f"  - {unlock_decision.get('can_use_now', 'Use free/public sources for already executable proof paths.')}",
                f"  - {unlock_decision.get('configure_first', 'Configure one keyed fallback only if needed, then smoke one ticker.')}",
                f"  - {unlock_decision.get('do_not_retry', 'Do not retry exhausted proof queues until source evidence changes.')}",
                f"  - {unlock_decision.get('proof_boundary', 'Provider setup only makes a source executable; readiness changes still require proof gates.')}",
            ]
        )
    lines.extend(_provider_one_setup_lines())
    for row in checklist["rows"]:
        provider = str(row.get("provider") or "").strip()
        if provider not in {"FMP free tier", "Alpha Vantage free tier", "Finnhub free tier", "IBKR read-only"}:
            continue
        setup_state = str(row.get("setup_state") or "").strip()
        unlock_lanes = str(row.get("unlock_lanes") or "").strip()
        cannot_unlock = str(row.get("cannot_unlock") or "").strip()
        smoke_command = str(row.get("post_setup_smoke_command") or "").strip()
        smoke_fragment = f"; smoke: `{smoke_command}`" if smoke_command else ""
        lines.append(f"- {provider}: {setup_state} -> {unlock_lanes}{smoke_fragment}; cannot unlock {cannot_unlock}")
    return lines


def _license_decision_option_rows(root: Path) -> list[list[object]]:
    status = build_license_status(root)
    options = status.get("decision_options", [])
    rows: list[list[object]] = []
    if not isinstance(options, list):
        return rows
    for option in options:
        if not isinstance(option, dict):
            continue
        rows.append(
            [
                option.get("goal", "-"),
                option.get("path", "-"),
                option.get("visitor_expectation", "-"),
            ]
        )
    return rows


def render_pilot_readiness_packet(
    *,
    root: Path | str = ".",
    checks: list[PilotReadinessCheck],
    snapshot: ReadinessSnapshot,
    source_queues: list[object],
    latest_proof: str,
    excluded_artifacts: list[str],
    commit_handoff: list[PilotCommitPackageItem] | None = None,
) -> str:
    root_path = Path(root)
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
        "## Provider Setup Checklist",
        "",
        "Use `make provider-setup-checklist` for the current checklist-style setup view. Real key values are never printed.",
        "",
        "### Source Buckets",
        "",
        *_provider_source_bucket_lines(root_path),
        "",
        "### Provider Activation Plan",
        "",
        *_provider_activation_plan_lines(),
        "",
        "### One-Provider Setup Decision",
        "",
        *_provider_one_setup_lines(),
        "",
        *_markdown_table(
            ["Provider", "Setup state", "Unlock lanes", "Usage", "Smoke command", "Cannot unlock", "Safe next step"],
            _provider_setup_checklist_rows(),
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
            "## License Decision Options",
            "",
            *_markdown_table(
                ["Goal", "Path", "Visitor expectation"],
                _license_decision_option_rows(root_path),
            ),
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
            "Default broad exclusion patterns:",
            *[f"- `{pattern}`" for pattern in GENERATED_ARTIFACT_EXCLUSION_PATTERNS],
            "",
            "Currently dirty generated artifacts:",
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


def render_pilot_share_brief(
    *,
    checks: list[PilotReadinessCheck],
    snapshot: ReadinessSnapshot,
    source_queues: list[object],
    excluded_artifacts: list[str],
    root: Path | str = ".",
) -> str:
    """Render a concise public/demo pilot brief from the same readiness gates."""

    verdict = pilot_readiness_verdict(checks)
    leading_queue = _leading_source_queue(source_queues)
    license_check = next((check for check in checks if check.area == "License status"), None)
    license_answer = license_check.title if license_check is not None else "Review license status"
    license_boundary = (
        license_check.stop_rule
        if license_check is not None
        else "Do not claim reuse rights until license status is reviewed."
    )
    source_gate_check = next((check for check in checks if check.area == "Source proof gates"), None)
    queue_name = str(_queue_value(leading_queue, "label", "queue", fallback="No source-proof queue loaded"))
    queue_state = str(_queue_value(leading_queue, "readiness_state", "state", fallback="-"))
    queue_blocked = _int_value(_queue_value(leading_queue, "blocked_count", "blocked"))
    queue_top_blockers = str(_queue_value(leading_queue, "top_blockers", "top blockers", fallback="-"))
    queue_command = str(
        _queue_value(
            leading_queue,
            "next_safe_command",
            "next safe command",
            fallback="make data-coverage-proof-queues TOP_N=10",
        )
    )
    if source_gate_check is not None and source_gate_check.title == "Source-proof queues reviewed or exhausted":
        queue_name = source_gate_check.title
        queue_state = source_gate_check.status
        queue_top_blockers = source_gate_check.detail
        queue_command = source_gate_check.command
    artifacts = excluded_artifacts or []

    lines = [
        "# Pilot Share Brief",
        "",
        "> Data readiness first. Analysis second. Research decision last.",
        "",
        "Use this as research-only product evidence. It summarizes what can be shown now, what is blocked by missing proof, and what must stay out of a share package.",
        "",
        f"## Current Pilot State: {verdict}",
        "",
        "## What can be used now",
        "",
        f"- Price-ready setup coverage: {snapshot.price_ready}/{snapshot.total_tickers}.",
        f"- Momentum usable: {snapshot.momentum_ready}/{snapshot.total_tickers}.",
        f"- Fundamentals/input-ready coverage: {snapshot.data_sources_available}/{snapshot.data_sources_total} data sources available; {snapshot.optional_manual_lanes_locked} optional/manual lane(s) locked.",
        f"- DCF-ready operating-company coverage: {snapshot.dcf_ready}/{snapshot.total_tickers}.",
        f"- Peer-ready coverage: {snapshot.peer_ready}/{snapshot.total_tickers}.",
        "",
        "## What is still blocked",
        "",
        f"- Leading proof queue: {queue_name} ({queue_state}).",
        f"- Blocked items in that queue: {queue_blocked:,}.",
        f"- Top blockers: {_sentence(queue_top_blockers)}",
        f"- Next source-proof command: `{queue_command}`.",
        "",
        "## How coverage expands next",
        "",
        *_share_brief_provider_setup_lines(root),
        "",
        "## How to demo or review next",
        "",
        "- Choose a focused review set first: `make universe-scope TOP_N=10`.",
        "- Review liquidity/correlation context only after scope selection: `make risk-context`.",
        "- Run the explicit public gate before sharing: `make public-check`.",
        "- Screenshots and scope/risk context do not update saved data or unlock blocked inputs.",
        "",
        "## What must stay out of the share package",
        "",
    ]
    if artifacts:
        lines.extend(f"- `{path}`" for path in artifacts)
    else:
        lines.append("- No generated CSV/JSON/report churn is currently dirty.")
    lines.extend(
        [
            "",
            "## License boundary",
            "",
            f"- {license_answer}.",
            f"- {license_boundary}",
            "",
            "## Research-only boundary",
            "",
            "- This is not investment advice, a ranking, or a recommendation.",
            "- The product does not connect to brokers, route orders, auto-trade, or give direct trade instructions.",
            "- Missing fundamentals, shares, peers, earnings, estimates, valuation inputs, and metrics stay blocked until trusted source proof passes.",
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
        root=root,
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


def write_pilot_share_brief(
    root: Path | str = ".",
    *,
    top_n: int = 10,
    output: Path | str = DEFAULT_SHARE_BRIEF_PATH,
) -> Path:
    root = Path(root)
    output_path = root / Path(output)
    source_queues = build_data_coverage_proof_queues(root, top_n=top_n)
    checks = build_pilot_readiness_checks(root, top_n=top_n, source_queues=source_queues)
    brief = render_pilot_share_brief(
        checks=checks,
        snapshot=build_readiness_snapshot(root),
        source_queues=source_queues,
        excluded_artifacts=_excluded_generated_artifacts(root),
        root=root,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(brief, encoding="utf-8")
    return output_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print a read-only pilot readiness checklist.")
    parser.add_argument("--root", default=".", help="Project root.")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--packet", action="store_true", help="Write the reviewer-ready pilot packet.")
    parser.add_argument("--share-brief", action="store_true", help="Write the concise public/demo pilot share brief.")
    parser.add_argument("--output", default=str(DEFAULT_PACKET_PATH), help="Packet output path.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.share_brief:
        output = write_pilot_share_brief(args.root, top_n=args.top_n, output=args.output)
        print(f"Wrote pilot share brief: {output}")
    elif args.packet:
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
