"""Pilot-review helper logic for the Data Health dashboard.

The Streamlit page should render the product, not decide the workflow. These
helpers keep pilot gate, packet, and reviewer-walkthrough copy in a small,
read-only module that never refreshes data or writes canonical CSV rows.
"""

from __future__ import annotations

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
    work = frame.copy()
    blocked = pd.to_numeric(work.get("Blocked", 0), errors="coerce").fillna(0)
    queued = pd.to_numeric(work.get("Queued Rows", 0), errors="coerce").fillna(0)
    work["_blocked"] = blocked
    work["_queued"] = queued
    return work.sort_values(["_blocked", "_queued", "Queue"], ascending=[False, False, True]).iloc[0]


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
