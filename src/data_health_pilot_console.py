"""Pilot-review helper logic for the Data Health dashboard.

The Streamlit page should render the product, not decide the workflow. These
helpers keep pilot gate, packet, and reviewer-walkthrough copy in a small,
read-only module that never refreshes data or writes canonical CSV rows.
"""

from __future__ import annotations

import html
from pathlib import Path

import pandas as pd


DEFAULT_PACKET_PATH = Path("outputs/pilot_readiness_packet.md")


def _format_missing(value: object, fallback: str = "Not available") -> str:
    if value is None:
        return fallback
    try:
        if pd.isna(value):
            return fallback
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "<na>"}:
        return fallback
    return text


def _compact_fragment(value: object, fallback: str = "Not available", *, max_chars: int = 170) -> str:
    text = _format_missing(value, fallback=fallback).replace("\n", " ").strip()
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 1)].rstrip() + "..."


def _public_status_label(value: object, fallback: str = "Not available") -> str:
    text = _format_missing(value, fallback=fallback)
    return text.replace("_", " ").replace("-", " ").title()


def _card_sentence(label: str, fragment: object) -> str:
    clean = _format_missing(fragment).strip()
    terminal = "" if clean.endswith((".", "?", "!", "...")) else "."
    return f"{label}: {clean}{terminal}"


def _status_counts(frame: pd.DataFrame | None) -> dict[str, int]:
    if frame is None or frame.empty or "Status" not in frame.columns:
        return {"green": 0, "manual": 0, "blocked": 0}
    statuses = frame["Status"].fillna("").astype(str).str.strip().str.lower()
    return {
        "green": int((statuses == "green").sum()),
        "manual": int((statuses == "manual").sum()),
        "blocked": int((statuses == "blocked").sum()),
    }


def _pilot_verdict(counts: dict[str, int]) -> tuple[str, str]:
    if counts["blocked"] > 0:
        return "Blocked before pilot", "blocked"
    if counts["manual"] > 0:
        return "Pilot-ready with manual gates", "manual gates"
    if counts["green"] > 0:
        return "Pilot-ready", "green"
    return "Run pilot readiness check", "read-only"


def _priority_gate(frame: pd.DataFrame | None) -> pd.Series | None:
    if frame is None or frame.empty or "Status" not in frame.columns:
        return None
    priority = {"blocked": 0, "manual": 1, "green": 2}
    work = frame.copy()
    work["_rank"] = work["Status"].map(lambda value: priority.get(str(value).strip().lower(), 9))
    return work.sort_values(["_rank", "Area"]).iloc[0]


def _leading_proof_queue(frame: pd.DataFrame | None) -> pd.Series | None:
    if frame is None or frame.empty:
        return None
    return frame.iloc[0]


def pilot_readiness_cards(frame: pd.DataFrame | None, *, limit: int = 4) -> list[dict[str, object]]:
    if frame is None or frame.empty:
        return [
            {
                "kicker": "PILOT GATE",
                "title": "Run pilot readiness check",
                "body": (
                    "The pilot gate needs sync, hygiene, freshness, source-proof, public-check, "
                    "and research-only guardrail status before sharing."
                ),
                "badges": ["read-only", "pilot gate"],
                "command": "make pilot-readiness-check TOP_N=10",
            }
        ]
    counts = _status_counts(frame)
    verdict, badge = _pilot_verdict(counts)
    cards: list[dict[str, object]] = [
        {
            "kicker": "PILOT READINESS",
            "title": verdict,
            "body": (
                f"{counts['green']} green gate(s), {counts['manual']} manual gate(s), "
                f"and {counts['blocked']} blocked gate(s). This is a packaging checklist, "
                "not an analysis unlock; missing trusted inputs stay visible."
            ),
            "badges": [badge, "research-only"],
            "command": "make pilot-readiness-check TOP_N=10",
        }
    ]
    priority = {"blocked": 0, "manual": 1, "green": 2}
    work = frame.copy()
    work["_rank"] = work["Status"].map(lambda value: priority.get(str(value).strip().lower(), 9))
    for _, row in work.sort_values(["_rank", "Area"]).head(max(limit, 0)).iterrows():
        area = _format_missing(row.get("Area"), "Pilot gate")
        status = _public_status_label(row.get("Status"))
        detail = _compact_fragment(row.get("Detail"), max_chars=170)
        stop_rule = _compact_fragment(row.get("Stop Rule"), max_chars=150)
        command = _format_missing(row.get("Command"), "make pilot-readiness-check TOP_N=10")
        cards.append(
            {
                "kicker": "PILOT CHECK",
                "title": area,
                "body": f"{_card_sentence('Status', status)} {_card_sentence('Detail', detail)} {_card_sentence('Stop rule', stop_rule)}",
                "badges": [status],
                "command": command,
            }
        )
    return cards


def pilot_packet_cards(frame: pd.DataFrame | None, *, output_path: Path = DEFAULT_PACKET_PATH) -> list[dict[str, object]]:
    counts = _status_counts(frame)
    if frame is None or frame.empty:
        verdict = "Run pilot readiness first"
        status_badge = "read-only"
    else:
        verdict, status_badge = _pilot_verdict(counts)
        packet_copy = {
            "Blocked before pilot": ("Packet will show blocked pilot gates", "blocked gates visible"),
            "Pilot-ready with manual gates": ("Packet will show manual pilot gates", "manual gates visible"),
            "Pilot-ready": ("Packet will show pilot-ready gates", "green gates"),
        }
        verdict, status_badge = packet_copy.get(verdict, ("Run pilot readiness first", status_badge))
    return [
        {
            "kicker": "PILOT PACKET",
            "title": verdict,
            "body": (
                f"Write `{output_path.as_posix()}` as a reviewer-ready summary of the pilot verdict, readiness snapshot, "
                "source-proof queues, proof ledger, stop rules, and excluded generated artifacts. The command does not refresh data or apply rows."
            ),
            "badges": [status_badge, "reviewer packet"],
            "command": f"make pilot-readiness-packet OUTPUT={output_path.as_posix()}",
        }
    ]


def pilot_handoff_summary_frame(
    pilot_frame: pd.DataFrame | None,
    proof_queue_frame: pd.DataFrame | None,
    *,
    output_path: Path = DEFAULT_PACKET_PATH,
) -> pd.DataFrame:
    """Return the compact pilot reviewer handoff before detailed tables."""

    counts = _status_counts(pilot_frame)
    verdict, verdict_badge = _pilot_verdict(counts)
    priority_gate = _priority_gate(pilot_frame)
    proof_queue = _leading_proof_queue(proof_queue_frame)

    gate_answer = "Run pilot readiness check"
    gate_status = "blocked"
    gate_command = "make pilot-readiness-check TOP_N=10"
    gate_boundary = "Stop before sharing until the pilot gate has been run."
    if priority_gate is not None:
        gate_answer = _format_missing(priority_gate.get("Area"), gate_answer)
        gate_status = _format_missing(priority_gate.get("Status"), gate_status)
        gate_command = _format_missing(priority_gate.get("Command"), gate_command)
        gate_boundary = _compact_fragment(priority_gate.get("Stop Rule"), max_chars=180)

    proof_answer = "Load source-proof queues"
    proof_status = "manual"
    proof_command = "make data-coverage-proof-queues TOP_N=10"
    proof_boundary = "Do not edit source rows until proof queues are loaded and reviewed."
    if proof_queue is not None:
        proof_answer = _format_missing(proof_queue.get("Queue"), proof_answer)
        proof_status = _format_missing(proof_queue.get("State"), proof_status)
        proof_command = _format_missing(proof_queue.get("Next Safe Command"), proof_command)
        blocked = int(pd.to_numeric(pd.Series([proof_queue.get("Blocked", 0)]), errors="coerce").fillna(0).iloc[0])
        blockers = _compact_fragment(proof_queue.get("Top Blockers"), max_chars=150)
        proof_boundary = f"{blocked:,} blocked item(s); top blockers: {blockers}."

    rows = [
        {
            "Question": "Can this be shared as a pilot?",
            "Status": verdict_badge,
            "Answer": verdict,
            "Next Safe Action": gate_command,
            "Boundary": "Pilot readiness is a packaging gate, not an analysis or recommendation unlock.",
        },
        {
            "Question": "What must be reviewed first?",
            "Status": gate_status,
            "Answer": gate_answer,
            "Next Safe Action": gate_command,
            "Boundary": gate_boundary,
        },
        {
            "Question": "What blocks deeper analysis?",
            "Status": proof_status,
            "Answer": proof_answer,
            "Next Safe Action": proof_command,
            "Boundary": proof_boundary,
        },
        {
            "Question": "What stays out of staging?",
            "Status": "manual",
            "Answer": "Generated CSV/JSON/report churn",
            "Next Safe Action": "make diff-hygiene-summary",
            "Boundary": "Do not stage broad generated churn unless the exact artifact is intentionally reviewed evidence.",
        },
        {
            "Question": "What should the reviewer run next?",
            "Status": "copy-only",
            "Answer": output_path.as_posix(),
            "Next Safe Action": f"make pilot-readiness-packet OUTPUT={output_path.as_posix()}",
            "Boundary": "The packet is read-only; it does not refresh data, apply imports, record proof, stage files, commit, or push.",
        },
    ]
    return pd.DataFrame(rows)


def pilot_handoff_summary_cards(frame: pd.DataFrame | None, *, limit: int = 5) -> list[dict[str, object]]:
    if frame is None or frame.empty:
        return [
            {
                "kicker": "PILOT HANDOFF",
                "title": "Run pilot readiness first",
                "body": "Load pilot gates and source-proof queues before reviewing package status.",
                "badges": ["read-only", "blocked visible"],
                "command": "make pilot-readiness-check TOP_N=10",
            }
        ]
    cards: list[dict[str, object]] = []
    for _, row in frame.head(max(limit, 0)).iterrows():
        question = _format_missing(row.get("Question"), "Pilot question")
        status = _public_status_label(row.get("Status"))
        answer = _format_missing(row.get("Answer"), question)
        boundary = _compact_fragment(row.get("Boundary"), max_chars=170)
        command = _format_missing(row.get("Next Safe Action"), "make pilot-readiness-check TOP_N=10")
        cards.append(
            {
                "kicker": question.upper(),
                "title": answer,
                "body": _card_sentence("Boundary", boundary),
                "badges": [status, "copy-only"],
                "command": command,
            }
        )
    return cards


def pilot_commit_package_cards(frame: pd.DataFrame | None, *, limit: int = 4) -> list[dict[str, object]]:
    if frame is None or frame.empty:
        return [
            {
                "kicker": "COMMIT PACKAGE",
                "title": "Run pilot readiness check first",
                "body": "Load the copy-only product staging and generated-churn exclusion handoff before packaging the pilot.",
                "badges": ["read-only", "copy-only"],
                "command": "make pilot-readiness-check TOP_N=10",
            }
        ]
    cards: list[dict[str, object]] = []
    for _, row in frame.head(max(limit, 0)).iterrows():
        step = _format_missing(row.get("Step"), "Commit package step")
        status = _public_status_label(row.get("Status"))
        boundary = _compact_fragment(row.get("Boundary"), max_chars=180)
        command = _format_missing(row.get("Copy-only Command"), "make pilot-readiness-check TOP_N=10")
        cards.append(
            {
                "kicker": "COMMIT PACKAGE",
                "title": step,
                "body": _card_sentence("Boundary", boundary),
                "badges": [status, "copy-only"],
                "command": command,
            }
        )
    return cards


def pilot_packaging_summary_frame(
    pilot_frame: pd.DataFrame | None,
    proof_queue_frame: pd.DataFrame | None,
    *,
    output_path: Path = DEFAULT_PACKET_PATH,
) -> pd.DataFrame:
    counts = _status_counts(pilot_frame)
    verdict, verdict_badge = _pilot_verdict(counts)
    priority_gate = _priority_gate(pilot_frame)
    proof_queue = _leading_proof_queue(proof_queue_frame)

    manual_gate = "No manual gate loaded"
    manual_command = "make pilot-readiness-check TOP_N=10"
    manual_stop = "Run pilot readiness before sharing."
    if priority_gate is not None:
        manual_gate = _format_missing(priority_gate.get("Area"), "Pilot gate")
        manual_command = _format_missing(priority_gate.get("Command"), manual_command)
        manual_stop = _compact_fragment(priority_gate.get("Stop Rule"), max_chars=170)

    proof_focus = "Load source-proof queues"
    proof_command = "make data-coverage-proof-queues TOP_N=10"
    proof_boundary = "Open review details before editing any source rows."
    if proof_queue is not None:
        proof_focus = _format_missing(proof_queue.get("Queue"), "Source-proof queue")
        proof_command = _format_missing(proof_queue.get("Next Safe Command"), proof_command)
        blockers = _compact_fragment(proof_queue.get("Top Blockers"), max_chars=160)
        blocked = int(pd.to_numeric(pd.Series([proof_queue.get("Blocked", 0)]), errors="coerce").fillna(0).iloc[0])
        proof_boundary = f"{blocked:,} blocked item(s); leading blockers: {blockers}."

    rows = [
        {
            "Review Question": "Is this pilot shareable now?",
            "Status": verdict_badge,
            "Answer": verdict,
            "Next Safe Action": manual_command,
            "Boundary": "Share only after product changes are committed, public-check passes, and manual gates are acknowledged.",
        },
        {
            "Review Question": "What blocks packaging?",
            "Status": _format_missing(priority_gate.get("Status") if priority_gate is not None else "blocked"),
            "Answer": manual_gate,
            "Next Safe Action": manual_command,
            "Boundary": manual_stop,
        },
        {
            "Review Question": "What blocks deeper analysis?",
            "Status": _format_missing(proof_queue.get("State") if proof_queue is not None else "deferred"),
            "Answer": proof_focus,
            "Next Safe Action": proof_command,
            "Boundary": proof_boundary,
        },
        {
            "Review Question": "What artifact can be reviewed?",
            "Status": "copy-only",
            "Answer": output_path.as_posix(),
            "Next Safe Action": f"make pilot-readiness-packet OUTPUT={output_path.as_posix()}",
            "Boundary": "The packet is reviewed evidence only when intentionally selected; broad generated CSV/JSON/report churn stays excluded.",
        },
    ]
    return pd.DataFrame(rows)


def pilot_packaging_summary_cards(frame: pd.DataFrame | None, *, limit: int = 4) -> list[dict[str, object]]:
    if frame is None or frame.empty:
        return [
            {
                "kicker": "PILOT PACKAGE",
                "title": "Run pilot readiness first",
                "body": "Load pilot gates and source-proof queues before calling the product share-ready.",
                "badges": ["read-only", "blocked visible"],
                "command": "make pilot-readiness-check TOP_N=10",
            }
        ]
    cards: list[dict[str, object]] = []
    for _, row in frame.head(max(limit, 0)).iterrows():
        question = _format_missing(row.get("Review Question"), "Pilot review")
        status = _public_status_label(row.get("Status"))
        answer = _format_missing(row.get("Answer"), question)
        boundary = _compact_fragment(row.get("Boundary"), max_chars=170)
        command = _format_missing(row.get("Next Safe Action"), "make pilot-readiness-check TOP_N=10")
        cards.append(
            {
                "kicker": question.upper(),
                "title": answer,
                "body": _card_sentence("Boundary", boundary),
                "badges": [status, "copy-only"],
                "command": command,
            }
        )
    return cards


def _area_row(frame: pd.DataFrame | None, area: str) -> pd.Series | None:
    if frame is None or frame.empty or "Area" not in frame.columns:
        return None
    areas = frame["Area"].fillna("").astype(str).str.strip().str.lower()
    matches = frame.loc[areas.eq(area.strip().lower())]
    if matches.empty:
        return None
    return matches.iloc[0]


def pilot_evidence_review_frame(
    pilot_frame: pd.DataFrame | None,
    proof_queue_frame: pd.DataFrame | None,
    *,
    output_path: Path = DEFAULT_PACKET_PATH,
) -> pd.DataFrame:
    """Return one compact pilot evidence review table for the operator page."""

    counts = _status_counts(pilot_frame)
    verdict, verdict_badge = _pilot_verdict(counts)
    browser_row = _area_row(pilot_frame, "Browser QA evidence")
    public_row = _area_row(pilot_frame, "Public safety")
    churn_row = _area_row(pilot_frame, "Generated artifact hygiene")
    proof_queue = _leading_proof_queue(proof_queue_frame)

    screenshot_status = _format_missing(browser_row.get("Status") if browser_row is not None else None, "manual")
    screenshot_detail = _compact_fragment(
        browser_row.get("Detail") if browser_row is not None else None,
        fallback="Run browser QA evidence to review real screenshot assets and pending captures.",
        max_chars=190,
    )
    screenshot_stop = _compact_fragment(
        browser_row.get("Stop Rule") if browser_row is not None else None,
        fallback="Use real app screenshots only; do not use generated thumbnails as product proof.",
        max_chars=180,
    )

    public_status = _format_missing(public_row.get("Status") if public_row is not None else None, "manual")
    public_stop = _compact_fragment(
        public_row.get("Stop Rule") if public_row is not None else None,
        fallback="Run public-check before sharing.",
        max_chars=180,
    )

    churn_status = _format_missing(churn_row.get("Status") if churn_row is not None else None, "manual")
    churn_detail = _compact_fragment(
        churn_row.get("Detail") if churn_row is not None else None,
        fallback="Generated CSV/JSON/report churn stays excluded unless intentionally reviewed evidence.",
        max_chars=190,
    )

    proof_title = "Load source-proof queues"
    proof_status = "deferred"
    proof_command = "make data-coverage-proof-queues TOP_N=10"
    proof_boundary = "Open review details before editing source rows."
    if proof_queue is not None:
        proof_title = _format_missing(proof_queue.get("Queue"), proof_title)
        proof_status = _format_missing(proof_queue.get("State"), proof_status)
        proof_command = _format_missing(proof_queue.get("Next Safe Command"), proof_command)
        blockers = _compact_fragment(proof_queue.get("Top Blockers"), max_chars=150)
        blocked = int(pd.to_numeric(pd.Series([proof_queue.get("Blocked", 0)]), errors="coerce").fillna(0).iloc[0])
        proof_boundary = f"{blocked:,} blocked item(s); leading blockers: {blockers}."

    rows = [
        {
            "Evidence Area": "Pilot verdict",
            "Status": verdict_badge,
            "Review State": verdict,
            "What To Check": f"{counts['green']} green, {counts['manual']} manual, {counts['blocked']} blocked gate(s).",
            "Next Safe Action": "make pilot-readiness-check TOP_N=10",
            "Stop Rule": "Pilot readiness is packaging evidence, not an analysis or recommendation unlock.",
        },
        {
            "Evidence Area": "Screenshot evidence",
            "Status": screenshot_status,
            "Review State": "Real screenshots and pending captures",
            "What To Check": screenshot_detail,
            "Next Safe Action": "make browser-qa-evidence",
            "Stop Rule": screenshot_stop,
        },
        {
            "Evidence Area": "Pilot packet",
            "Status": "copy-only",
            "Review State": output_path.as_posix(),
            "What To Check": "Reviewer packet summarizes verdict, freshness, source-proof queues, proof ledger, stop rules, and excluded generated artifacts.",
            "Next Safe Action": f"make pilot-readiness-packet OUTPUT={output_path.as_posix()}",
            "Stop Rule": "Packet generation is read-only; commit only as intentionally reviewed pilot evidence.",
        },
        {
            "Evidence Area": "Public release gate",
            "Status": public_status,
            "Review State": "Public-check boundary",
            "What To Check": "Public wording, tests, dashboard smoke, browser evidence, and visitor path stay research-only.",
            "Next Safe Action": "make public-check",
            "Stop Rule": public_stop,
        },
        {
            "Evidence Area": "Generated churn boundary",
            "Status": churn_status,
            "Review State": "Exclude broad generated artifacts",
            "What To Check": churn_detail,
            "Next Safe Action": "make diff-hygiene-summary",
            "Stop Rule": "Do not stage broad generated CSV/JSON/report churn unless the exact artifact is reviewed evidence.",
        },
        {
            "Evidence Area": "Source-proof blocker",
            "Status": proof_status,
            "Review State": proof_title,
            "What To Check": proof_boundary,
            "Next Safe Action": proof_command,
            "Stop Rule": "Blocked fundamentals, shares, market cap, peers, earnings, estimates, valuation inputs, and metrics stay blocked until source proof exists.",
        },
    ]
    return pd.DataFrame(rows)


def pilot_evidence_review_cards(frame: pd.DataFrame | None, *, limit: int = 6) -> list[dict[str, object]]:
    if frame is None or frame.empty:
        return [
            {
                "kicker": "PILOT EVIDENCE",
                "title": "Run pilot readiness first",
                "body": "Load screenshot evidence, packet status, public-check boundary, generated-churn policy, and source-proof blockers before sharing.",
                "badges": ["read-only", "research-only"],
                "command": "make pilot-readiness-check TOP_N=10",
            }
        ]

    cards: list[dict[str, object]] = [
        {
            "kicker": "PILOT EVIDENCE REVIEW",
            "title": "Screenshots, packet, public gate, churn, and source proof in one place",
            "body": (
                "Use this review strip before opening raw tables. It does not refresh data, apply imports, "
                "record proof rows, stage files, commit, push, or unlock blocked inputs."
            ),
            "badges": ["review first", "copy-only"],
            "command": "make pilot-readiness-check TOP_N=10 && make browser-qa-evidence",
        }
    ]
    for _, row in frame.head(max(limit, 0)).iterrows():
        area = _format_missing(row.get("Evidence Area"), "Pilot evidence")
        status = _public_status_label(row.get("Status"))
        state = _format_missing(row.get("Review State"), area)
        check = _compact_fragment(row.get("What To Check"), max_chars=150)
        stop_rule = _compact_fragment(row.get("Stop Rule"), max_chars=150)
        command = _format_missing(row.get("Next Safe Action"), "make pilot-readiness-check TOP_N=10")
        cards.append(
            {
                "kicker": area.upper(),
                "title": state,
                "body": f"{_card_sentence('Check', check)} {_card_sentence('Stop rule', stop_rule)}",
                "badges": [status, "evidence"],
                "command": command,
            }
        )
    return cards


def public_share_final_gate_frame(
    pilot_frame: pd.DataFrame | None,
    *,
    output_path: Path = DEFAULT_PACKET_PATH,
) -> pd.DataFrame:
    """Return a compact final public-share checklist for Data Health."""

    sync_row = _area_row(pilot_frame, "GitHub sync")
    public_row = _area_row(pilot_frame, "Public safety")
    browser_row = _area_row(pilot_frame, "Browser QA evidence")
    churn_row = _area_row(pilot_frame, "Generated artifact hygiene")
    guardrail_row = _area_row(pilot_frame, "Research guardrails")

    def row_status(row: pd.Series | None, fallback: str = "manual") -> str:
        return _format_missing(row.get("Status") if row is not None else None, fallback)

    def row_detail(row: pd.Series | None, fallback: str) -> str:
        return _compact_fragment(row.get("Detail") if row is not None else None, fallback=fallback, max_chars=180)

    def row_stop(row: pd.Series | None, fallback: str) -> str:
        return _compact_fragment(row.get("Stop Rule") if row is not None else None, fallback=fallback, max_chars=170)

    rows = [
        {
            "Gate": "GitHub sync",
            "Status": row_status(sync_row, "blocked"),
            "Review": row_detail(sync_row, "Confirm local branch state before public sharing."),
            "Command": _format_missing(sync_row.get("Command") if sync_row is not None else None, "git status --short --branch"),
            "Stop Rule": row_stop(sync_row, "Stop if the branch diverges or has unreviewed commits."),
        },
        {
            "Gate": "Public-check",
            "Status": row_status(public_row, "manual"),
            "Review": row_detail(public_row, "Run the public release gate before sharing."),
            "Command": "make public-check",
            "Stop Rule": row_stop(public_row, "Stop if public-check fails."),
        },
        {
            "Gate": "Browser QA evidence",
            "Status": row_status(browser_row, "manual"),
            "Review": row_detail(browser_row, "Review real screenshot assets and pending workflow captures."),
            "Command": "make browser-qa-evidence",
            "Stop Rule": row_stop(browser_row, "Stop if screenshots are generated thumbnails, tracebacks, or stale proof substitutes."),
        },
        {
            "Gate": "Generated churn exclusion",
            "Status": row_status(churn_row, "manual"),
            "Review": row_detail(churn_row, "Generated CSV/JSON/report churn stays excluded unless intentionally reviewed evidence."),
            "Command": "make diff-hygiene-summary",
            "Stop Rule": row_stop(churn_row, "Do not stage broad generated churn by default."),
        },
        {
            "Gate": "Pilot packet",
            "Status": "copy-only",
            "Review": f"{output_path.as_posix()} summarizes the pilot state from saved local artifacts.",
            "Command": f"make pilot-readiness-packet OUTPUT={output_path.as_posix()}",
            "Stop Rule": "Packet generation is read-only; do not treat the packet as a data or source-proof unlock.",
        },
        {
            "Gate": "Research-only boundary",
            "Status": row_status(guardrail_row, "green"),
            "Review": row_detail(
                guardrail_row,
                "Public surfaces must remain readiness-first, research-only, and free of execution language.",
            ),
            "Command": _format_missing(
                guardrail_row.get("Command") if guardrail_row is not None else None,
                "make public-wording-check",
            ),
            "Stop Rule": row_stop(
                guardrail_row,
                "Stop if any public or dashboard wording turns readiness queues into trade instructions.",
            ),
        },
    ]
    return pd.DataFrame(rows)


def public_share_final_gate_cards(frame: pd.DataFrame | None, *, limit: int = 6) -> list[dict[str, object]]:
    if frame is None or frame.empty:
        return [
            {
                "kicker": "PUBLIC SHARE GATE",
                "title": "Run pilot readiness first",
                "body": "Load sync, public-check, browser evidence, generated churn, packet, and research-only status before sharing.",
                "badges": ["read-only", "public gate"],
                "command": "make pilot-readiness-check TOP_N=10",
            }
        ]

    cards: list[dict[str, object]] = [
        {
            "kicker": "PUBLIC SHARE GATE",
            "title": "One final review before GitHub or LinkedIn",
            "body": (
                "Confirm sync, public-check, real screenshots, generated-churn exclusion, packet freshness, and "
                "research-only wording before treating the product as share-ready."
            ),
            "badges": ["final gate", "read-only"],
            "command": "make public-check && make browser-qa-evidence",
        }
    ]
    for _, row in frame.head(max(limit, 0)).iterrows():
        gate = _format_missing(row.get("Gate"), "Public gate")
        status = _public_status_label(row.get("Status"))
        review = _compact_fragment(row.get("Review"), max_chars=150)
        stop_rule = _compact_fragment(row.get("Stop Rule"), max_chars=150)
        command = _format_missing(row.get("Command"), "make public-check")
        cards.append(
            {
                "kicker": gate.upper(),
                "title": status,
                "body": f"{_card_sentence('Review', review)} {_card_sentence('Stop rule', stop_rule)}",
                "badges": [status, "copy-only"],
                "command": command,
            }
        )
    return cards


def data_health_workflow_continuity_frame(
    pilot_frame: pd.DataFrame | None,
    proof_queue_frame: pd.DataFrame | None,
    *,
    output_path: Path = DEFAULT_PACKET_PATH,
) -> pd.DataFrame:
    """Return the connected operator flow across Data Health sections."""

    priority_gate = _priority_gate(pilot_frame)
    proof_queue = _leading_proof_queue(proof_queue_frame)
    gate_title = _format_missing(priority_gate.get("Area") if priority_gate is not None else None, "Pilot evidence review")
    gate_command = _format_missing(priority_gate.get("Command") if priority_gate is not None else None, "make pilot-readiness-check TOP_N=10")

    proof_title = _format_missing(proof_queue.get("Queue") if proof_queue is not None else None, "Source-proof queue")
    proof_command = _format_missing(
        proof_queue.get("Next Safe Command") if proof_queue is not None else None,
        "make data-coverage-proof-queues TOP_N=10",
    )
    proof_stop = _compact_fragment(
        proof_queue.get("Stop Rule") if proof_queue is not None else None,
        fallback="Do not edit source rows until the proof queue and review gates are visible.",
        max_chars=170,
    )

    rows = [
        {
            "Step": "1. Evidence review",
            "Purpose": "Confirm share status, screenshot evidence, packet, public gate, churn, and source blocker.",
            "Primary View": "Pilot Evidence Review",
            "Next Safe Action": gate_command,
            "Route": "?mode=operator&page=data-health",
            "Stop Rule": "Do not treat pilot packaging as an analysis unlock.",
        },
        {
            "Step": "2. Final share gate",
            "Purpose": "Check sync, public-check, real screenshots, generated-churn exclusion, packet, and guardrails.",
            "Primary View": "Public Share Final Gate",
            "Next Safe Action": "make public-check && make browser-qa-evidence",
            "Route": "?mode=operator&page=data-health",
            "Stop Rule": "Stop before sharing if public-check or browser evidence fails.",
        },
        {
            "Step": "3. Next safe action",
            "Purpose": f"Clear the current leading gate: {gate_title}.",
            "Primary View": "Next Data-Readiness Action",
            "Next Safe Action": gate_command,
            "Route": "?mode=operator&page=data-health",
            "Stop Rule": "Do not jump to raw tables before the current gate is understood.",
        },
        {
            "Step": "4. Queue route map",
            "Purpose": f"Choose the leading source-proof lane: {proof_title}.",
            "Primary View": "Readiness queue review details",
            "Next Safe Action": proof_command,
            "Route": "?mode=operator&page=data-health&lane=fundamentals&drawer=queue",
            "Stop Rule": proof_stop,
        },
        {
            "Step": "5. Proof lane",
            "Purpose": "Compare readiness, inspect proof-record status, and keep proof rows dry-run-first.",
            "Primary View": "Proof History",
            "Next Safe Action": "make reviewed-batch-proof",
            "Route": "?mode=operator&page=data-health&lane=proof",
            "Stop Rule": "Do not record supported outcomes before source proof and comparison pass.",
        },
        {
            "Step": "6. Artifact hygiene",
            "Purpose": "Classify generated files before staging or public sharing.",
            "Primary View": "Generated Artifact Review",
            "Next Safe Action": "make diff-hygiene-summary",
            "Route": "?mode=operator&page=data-health&lane=proof&drawer=artifacts",
            "Stop Rule": "Do not stage broad generated CSV/JSON/report churn by default.",
        },
        {
            "Step": "7. Reviewer packet",
            "Purpose": "Write one read-only handoff packet after evidence is reviewed.",
            "Primary View": output_path.as_posix(),
            "Next Safe Action": f"make pilot-readiness-packet OUTPUT={output_path.as_posix()}",
            "Route": output_path.as_posix(),
            "Stop Rule": "The packet is reviewed evidence only when intentionally selected.",
        },
    ]
    return pd.DataFrame(rows)


def data_health_workflow_continuity_cards(frame: pd.DataFrame | None, *, limit: int = 7) -> list[dict[str, object]]:
    if frame is None or frame.empty:
        return [
            {
                "kicker": "DATA HEALTH FLOW",
                "title": "Load operator workflow",
                "body": "Load pilot evidence, share gate, queue route, proof lane, and artifact hygiene before raw tables.",
                "badges": ["read-only", "operator flow"],
                "command": "make pilot-readiness-check TOP_N=10",
            }
        ]

    cards: list[dict[str, object]] = [
        {
            "kicker": "DATA HEALTH FLOW",
            "title": "One operator path, then drawers",
            "body": (
                "Follow evidence review -> final share gate -> next action -> queue route map -> proof lane -> "
                "artifact hygiene before opening raw tables. Commands remain copy-only."
            ),
            "badges": ["one flow", "drawers later"],
            "command": "make pilot-readiness-check TOP_N=10",
        }
    ]
    for _, row in frame.head(max(limit, 0)).iterrows():
        step = _format_missing(row.get("Step"), "Workflow step")
        view = _format_missing(row.get("Primary View"), step)
        purpose = _compact_fragment(row.get("Purpose"), max_chars=145)
        stop_rule = _compact_fragment(row.get("Stop Rule"), max_chars=145)
        command = _format_missing(row.get("Next Safe Action"), "make pilot-readiness-check TOP_N=10")
        cards.append(
            {
                "kicker": step.upper(),
                "title": view,
                "body": f"{_card_sentence('Purpose', purpose)} {_card_sentence('Stop rule', stop_rule)}",
                "badges": ["copy-only", "collapsed detail"],
                "command": command,
            }
        )
    return cards


def pilot_reviewer_walkthrough_frame(
    pilot_frame: pd.DataFrame | None,
    proof_queue_frame: pd.DataFrame | None,
    *,
    output_path: Path = DEFAULT_PACKET_PATH,
) -> pd.DataFrame:
    counts = _status_counts(pilot_frame)
    verdict, verdict_badge = _pilot_verdict(counts)
    priority_gate = _priority_gate(pilot_frame)
    proof_queue = _leading_proof_queue(proof_queue_frame)

    if priority_gate is None:
        gate_title = "Run the pilot gate first"
        gate_detail = "Pilot sync, hygiene, freshness, source-proof, public-check, and guardrail status are not loaded yet."
        gate_command = "make pilot-readiness-check TOP_N=10"
        gate_stop = "Stop before pilot sharing until the readiness gate has been run."
    else:
        gate_title = _format_missing(priority_gate.get("Area"), "Pilot gate")
        gate_detail = _compact_fragment(priority_gate.get("Detail"), max_chars=190)
        gate_command = _format_missing(priority_gate.get("Command"), "make pilot-readiness-check TOP_N=10")
        gate_stop = _compact_fragment(priority_gate.get("Stop Rule"), max_chars=190)

    if proof_queue is None:
        queue_title = "Load source-proof queues"
        queue_detail = "DCF, shares, fundamentals, peer mapping, and peer valuation queues are deferred until review details are opened."
        queue_command = "Switch Readiness queue detail level to Review details."
        queue_stop = "Do not edit raw CSV rows without a source-proof queue and review gate."
    else:
        queue_title = _format_missing(proof_queue.get("Queue"), "Source-proof queue")
        blocked = int(pd.to_numeric(pd.Series([proof_queue.get("Blocked", 0)]), errors="coerce").fillna(0).iloc[0])
        blockers = _compact_fragment(proof_queue.get("Top Blockers"), max_chars=160)
        queue_detail = f"{blocked:,} blocked item(s). Top blockers: {blockers}"
        queue_command = _format_missing(proof_queue.get("Next Safe Command"), "make data-coverage-proof-queues TOP_N=10")
        queue_stop = _compact_fragment(proof_queue.get("Stop Rule"), max_chars=190)

    rows = [
        {
            "Stage": "Pilot status",
            "Status": verdict_badge,
            "What Reviewer Sees": verdict,
            "Next Safe Action": gate_command,
            "Evidence": f"{counts['green']} green, {counts['manual']} manual, {counts['blocked']} blocked pilot gate(s).",
            "Stop Rule": "Missing trusted inputs remain blocked; the pilot gate is not an analysis unlock.",
        },
        {
            "Stage": "Manual gate to clear",
            "Status": _format_missing(priority_gate.get("Status") if priority_gate is not None else "blocked"),
            "What Reviewer Sees": gate_title,
            "Next Safe Action": gate_command,
            "Evidence": gate_detail,
            "Stop Rule": gate_stop,
        },
        {
            "Stage": "Source-proof focus",
            "Status": _format_missing(proof_queue.get("State") if proof_queue is not None else "deferred"),
            "What Reviewer Sees": queue_title,
            "Next Safe Action": queue_command,
            "Evidence": queue_detail,
            "Stop Rule": queue_stop,
        },
        {
            "Stage": "Reviewer packet",
            "Status": "copy-only",
            "What Reviewer Sees": output_path.as_posix(),
            "Next Safe Action": f"make pilot-readiness-packet OUTPUT={output_path.as_posix()}",
            "Evidence": "One Markdown packet summarizing verdict, snapshot, proof queues, ledger outcome, manual gates, stop rules, and excluded generated artifacts.",
            "Stop Rule": "Commit the packet only as reviewed pilot evidence; keep broad generated CSV/JSON/report churn excluded.",
        },
        {
            "Stage": "Public boundary",
            "Status": "manual",
            "What Reviewer Sees": "Public-check remains the final share gate",
            "Next Safe Action": "make public-check",
            "Evidence": "Runs public wording, whitespace, tests, dashboard smoke, and visitor-demo checks.",
            "Stop Rule": "Stop before sharing if public-check, wording, dashboard smoke, or whitespace checks fail.",
        },
    ]
    return pd.DataFrame(rows)


def pilot_reviewer_walkthrough_cards(frame: pd.DataFrame | None, *, limit: int = 5) -> list[dict[str, object]]:
    if frame is None or frame.empty:
        return [
            {
                "kicker": "PILOT REVIEWER PATH",
                "title": "Run the pilot gate first",
                "body": "Load the pilot checklist and source-proof queues before opening raw tables or sharing a pilot link.",
                "badges": ["read-only", "copy-only"],
                "command": "make pilot-readiness-check TOP_N=10",
            }
        ]
    cards: list[dict[str, object]] = [
        {
            "kicker": "PILOT REVIEWER PATH",
            "title": "One compact path before raw tables",
            "body": (
                "Reviewer flow: confirm pilot gate, inspect the leading source-proof blocker, write the packet, "
                "then run public-check. Commands stay copy-only and broad generated churn stays excluded."
            ),
            "badges": ["first-screen guide", "research-only"],
            "command": "make pilot-readiness-check TOP_N=10",
        }
    ]
    for _, row in frame.head(max(limit, 0)).iterrows():
        stage = _format_missing(row.get("Stage"), "Pilot step")
        status = _public_status_label(row.get("Status"))
        title = _format_missing(row.get("What Reviewer Sees"), stage)
        evidence = _compact_fragment(row.get("Evidence"), max_chars=160)
        stop_rule = _compact_fragment(row.get("Stop Rule"), max_chars=150)
        command = _format_missing(row.get("Next Safe Action"), "make pilot-readiness-check TOP_N=10")
        cards.append(
            {
                "kicker": stage.upper(),
                "title": title,
                "body": f"{_card_sentence('Evidence', evidence)} {_card_sentence('Stop rule', stop_rule)}",
                "badges": [status, "copy-only"],
                "command": command,
            }
        )
    return cards


def operator_next_action_summary_frame(
    pilot_frame: pd.DataFrame | None,
    proof_queue_frame: pd.DataFrame | None,
    *,
    output_path: Path = DEFAULT_PACKET_PATH,
) -> pd.DataFrame:
    """Return the first-screen operator summary for the next safe action.

    This is intentionally read-only. It summarizes saved readiness/proof state
    and names copy-only commands without refreshing data, applying rows, or
    inferring missing source inputs.
    """

    counts = _status_counts(pilot_frame)
    verdict, verdict_badge = _pilot_verdict(counts)
    priority_gate = _priority_gate(pilot_frame)
    proof_queue = _leading_proof_queue(proof_queue_frame)

    gate_title = "Run pilot readiness check"
    gate_command = "make pilot-readiness-check TOP_N=10"
    gate_status = "blocked"
    if priority_gate is not None:
        gate_title = _format_missing(priority_gate.get("Area"), "Pilot gate")
        gate_command = _format_missing(priority_gate.get("Command"), gate_command)
        gate_status = _format_missing(priority_gate.get("Status"), "manual")

    proof_title = "Load source-proof queues"
    proof_command = "make data-coverage-proof-queues TOP_N=10"
    proof_status = "deferred"
    proof_evidence = "Source-proof queues are not loaded in fast view; open review details before editing any data rows."
    if proof_queue is not None:
        proof_title = _format_missing(proof_queue.get("Queue"), "Source-proof queue")
        proof_status = _format_missing(proof_queue.get("State"), "partial")
        proof_command = _format_missing(proof_queue.get("Next Safe Command"), proof_command)
        blocked = int(pd.to_numeric(pd.Series([proof_queue.get("Blocked", 0)]), errors="coerce").fillna(0).iloc[0])
        blockers = _compact_fragment(proof_queue.get("Top Blockers"), max_chars=130)
        proof_evidence = f"{blocked:,} blocked item(s). Leading blocker: {blockers}."

    rows = [
        {
            "Question": "Can this be piloted?",
            "Status": verdict_badge,
            "Answer": verdict,
            "Next Safe Action": gate_command,
            "Evidence": f"{counts['green']} green, {counts['manual']} manual, {counts['blocked']} blocked gate(s).",
            "Boundary": "Pilot status is a packaging gate, not a research decision.",
        },
        {
            "Question": "What is the main manual gate?",
            "Status": gate_status,
            "Answer": gate_title,
            "Next Safe Action": gate_command,
            "Evidence": "Clear this gate before calling the package share-ready.",
            "Boundary": "Do not push, stage generated churn, or quote stale counts until the gate is reviewed.",
        },
        {
            "Question": "What blocks deeper analysis?",
            "Status": proof_status,
            "Answer": proof_title,
            "Next Safe Action": proof_command,
            "Evidence": proof_evidence,
            "Boundary": "Missing fundamentals, shares, market cap, peer, earnings, and estimate rows stay blocked until source-proof exists.",
        },
        {
            "Question": "What should stay hidden first?",
            "Status": "copy-only",
            "Answer": "Raw tables and proof commands",
            "Next Safe Action": f"make pilot-readiness-packet OUTPUT={output_path.as_posix()}",
            "Evidence": "Use the packet or collapsed drawers for review detail; keep the first screen focused on status and next action.",
            "Boundary": "Commands remain copy-only; canonical data writes require validate, preview, rejected-row review, and explicit apply or skip.",
        },
    ]
    return pd.DataFrame(rows)


def operator_next_action_summary_cards(frame: pd.DataFrame | None, *, limit: int = 4) -> list[dict[str, object]]:
    if frame is None or frame.empty:
        return [
            {
                "kicker": "NEXT ACTION",
                "title": "Run pilot readiness check",
                "body": "Load pilot gate and source-proof status before opening raw tables or data-changing workflows.",
                "badges": ["read-only", "research-only"],
                "command": "make pilot-readiness-check TOP_N=10",
            }
        ]

    cards: list[dict[str, object]] = []
    for _, row in frame.head(max(limit, 0)).iterrows():
        question = _format_missing(row.get("Question"), "Operator question")
        status = _public_status_label(row.get("Status"))
        answer = _format_missing(row.get("Answer"), question)
        evidence = _compact_fragment(row.get("Evidence"), max_chars=150)
        boundary = _compact_fragment(row.get("Boundary"), max_chars=150)
        command = _format_missing(row.get("Next Safe Action"), "make pilot-readiness-check TOP_N=10")
        cards.append(
            {
                "kicker": question.upper(),
                "title": answer,
                "body": f"{_card_sentence('Evidence', evidence)} {_card_sentence('Boundary', boundary)}",
                "badges": [status, "copy-only"],
                "command": command,
            }
        )
    return cards


def pilot_reviewer_walkthrough_strip_html(frame: pd.DataFrame | None, *, limit: int = 5) -> str:
    if frame is None or frame.empty:
        frame = pilot_reviewer_walkthrough_frame(pd.DataFrame(), pd.DataFrame())
    steps: list[str] = []
    for index, (_, row) in enumerate(frame.head(max(limit, 0)).iterrows(), start=1):
        stage = _format_missing(row.get("Stage"), "Pilot step")
        status = _public_status_label(row.get("Status"))
        title = _compact_fragment(row.get("What Reviewer Sees"), max_chars=72)
        action = _compact_fragment(row.get("Next Safe Action"), max_chars=92)
        status_key = str(row.get("Status", "")).strip().lower().replace("_", "-").replace(" ", "-")
        status_class = {
            "green": "ready",
            "manual": "manual",
            "manual-gates": "manual",
            "blocked": "blocked",
            "deferred": "manual",
            "copy-only": "copy",
        }.get(status_key, "copy")
        steps.append(
            "<div class='pilot-flow-step'>"
            "<div class='pilot-flow-top'>"
            f"<span class='pilot-flow-index'>{index}</span>"
            f"<span class='pilot-flow-status {html.escape(status_class)}'>{html.escape(status)}</span>"
            "</div>"
            f"<div class='pilot-flow-stage'>{html.escape(stage)}</div>"
            f"<div class='pilot-flow-title'>{html.escape(title)}</div>"
            f"<div class='pilot-flow-action'>{html.escape(action)}</div>"
            "</div>"
        )
    return (
        "<div class='pilot-flow'>"
        "<div class='pilot-flow-head'>"
        "<div class='pilot-flow-kicker'>Pilot workflow</div>"
        "<div class='pilot-flow-summary'>Gate, proof focus, packet, and public-check before raw tables.</div>"
        "</div>"
        "<div class='pilot-flow-grid'>"
        + "".join(steps)
        + "</div>"
        "</div>"
    )
