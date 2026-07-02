"""Pilot-review helper logic for the Data Health dashboard.

The Streamlit page should render the product, not decide the workflow. These
helpers keep pilot gate, packet, and reviewer-walkthrough copy in a small,
read-only module that never refreshes data or writes canonical CSV rows.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

import pandas as pd

from src.license_status import DECISION_OPTIONS, NO_LICENSE_SHARE_BOUNDARY


DEFAULT_PACKET_PATH = Path("outputs/pilot_readiness_packet.md")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTROLLED_PILOT_OUTCOMES = {
    "supported",
    "human_reviewed_supported",
    "auto_supported",
    "candidate_context_only",
    "still_blocked",
    "skipped",
    "excluded",
}
CONTROLLED_PILOT_LANES = {
    "fundamentals",
    "fundamentals_dcf",
    "share_count",
    "share_count_proof",
    "peers",
    "peer_mapping",
    "peer_mapping_proof",
    "peer_valuation_inputs",
}
CONTROLLED_PILOT_BROAD_MARKERS = {
    "all-universe",
    "broad-universe",
    "broad universe",
    "capped ",
    "changed tickers",
    "coverage",
    "missing-price",
    "optional context",
    "price refresh",
    "queue",
    "refreshed",
}
CONTROLLED_PILOT_SINGLE_SCOPE_MARKERS = {
    "one-company",
    "reviewed ticker",
    "trusted-data pilot packet",
}


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


def _license_decision_options_summary() -> str:
    options = []
    for option in DECISION_OPTIONS:
        goal = _format_missing(option.get("goal"), "License goal")
        path = _format_missing(option.get("path"), "License path")
        options.append(f"{goal} | {path}")
    return "License decision options: " + "; ".join(options)


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


def controlled_pilot_outcome_frame(
    ledger_frame: pd.DataFrame | None,
    *,
    target_min: int = 5,
    target_max: int = 10,
) -> pd.DataFrame:
    """Summarize whether the controlled pilot has enough reviewed outcomes."""

    if ledger_frame is None or ledger_frame.empty or "Final Outcome" not in ledger_frame.columns:
        reviewed = pd.DataFrame()
    else:
        reviewed = ledger_frame.copy()
        reviewed["_outcome"] = reviewed["Final Outcome"].fillna("").astype(str).str.strip().str.lower()
        reviewed = reviewed[reviewed["_outcome"].isin(CONTROLLED_PILOT_OUTCOMES)]
        controlled_mask = reviewed.apply(_is_controlled_pilot_row, axis=1)
        reviewed = reviewed[controlled_mask].copy()

    ignored_rows = 0
    if ledger_frame is not None and not ledger_frame.empty and "Final Outcome" in ledger_frame.columns:
        outcome_rows = ledger_frame["Final Outcome"].fillna("").astype(str).str.strip().str.lower().isin(CONTROLLED_PILOT_OUTCOMES)
        ignored_rows = max(int(outcome_rows.sum()) - int(len(reviewed)), 0)

    reviewed_tickers: list[str] = []
    for _, row in reviewed.iterrows():
        tickers = _pilot_ticker_tokens(_cell_text(row, "Tickers", "tickers"))
        if not tickers:
            tickers = _pilot_ticker_tokens(_cell_text(row, "Changed Tickers", "changed_tickers"))
        reviewed_tickers.extend(tickers[:10])
    unique_tickers = sorted(dict.fromkeys(reviewed_tickers))
    reviewed_count = int(len(unique_tickers))
    status = "pilot_exit_ready" if reviewed_count >= target_min else "needs_more_packets"
    if reviewed_count > target_max:
        status = "pilot_scope_review"
    if status == "pilot_scope_review":
        count_answer = f"{reviewed_count} reviewed ticker outcome(s); select {target_min} to {target_max} for this pilot"
    else:
        count_answer = f"{reviewed_count} / {target_min} minimum reviewed ticker outcome(s)"
    if status == "pilot_exit_ready":
        next_packet_action = "make pilot-readiness-packet OUTPUT=outputs/pilot_readiness_packet.md"
    else:
        next_packet_action = "make project-status"
    outcome_counts = reviewed["_outcome"].value_counts().to_dict() if not reviewed.empty else {}
    outcome_mix = ", ".join(
        f"{outcome}={int(outcome_counts[outcome])}"
        for outcome in sorted(outcome_counts)
        if int(outcome_counts[outcome]) > 0
    )
    latest = reviewed.iloc[0] if not reviewed.empty else None
    latest_summary = (
        f"{_format_missing(latest.get('Batch ID'), 'latest batch')} / "
        f"{_format_missing(latest.get('Lane'), 'lane')} / "
        f"{_format_missing(latest.get('Final Outcome'), 'outcome')}"
        if latest is not None
        else "No reviewed pilot packet outcome yet."
    )

    rows = [
        {
            "Question": "Can the controlled pilot exit?",
            "Status": status,
            "Answer": count_answer,
            "Evidence": (
                f"Controlled pilot can exit when reviewed packet outcomes cover the selected 5 to 10 company set. "
                f"Reviewed tickers: {', '.join(unique_tickers[:target_max]) or '-'}. "
                f"Ignored broad/non-pilot proof rows: {ignored_rows}."
                if status == "pilot_exit_ready"
                else (
                    (
                        "Select a 5 to 10 company pilot set from reviewed outcomes before calling the controlled pilot complete. "
                        if status == "pilot_scope_review"
                        else (
                            "Run project-status first; use provider setup when source-proof queues are exhausted; "
                            "do not call unsupported lanes ready. "
                        )
                    )
                    + f"Reviewed tickers: {', '.join(unique_tickers[:target_max]) or '-'}. "
                    + f"Ignored broad/non-pilot proof rows: {ignored_rows}."
                )
            ),
            "Next Safe Action": next_packet_action,
            "Stop Rule": "Pilot outcome counts are not a coverage unlock; source-proof gates still control every lane.",
        },
        {
            "Question": "What outcome states are recorded?",
            "Status": "reviewed" if reviewed_count else "manual",
            "Answer": outcome_mix or "No reviewed outcomes recorded",
            "Evidence": outcome_mix or "Record supported, candidate_context_only, still_blocked, skipped, or excluded after proof review.",
            "Next Safe Action": "make reviewed-batch-proof",
            "Stop Rule": "Do not record supported outcomes without validation, preview, rejected-row review, source proof, and artifact review.",
        },
        {
            "Question": "What was the latest packet outcome?",
            "Status": "reviewed" if reviewed_count else "manual",
            "Answer": latest_summary,
            "Evidence": _compact_fragment(latest.get("Notes"), fallback="No notes recorded.", max_chars=190) if latest is not None else "No latest outcome.",
            "Next Safe Action": "make pilot-readiness-packet OUTPUT=outputs/pilot_readiness_packet.md",
            "Stop Rule": "Keep broad generated CSV/JSON/report churn excluded unless the exact packet artifact is reviewed evidence.",
        },
    ]
    return pd.DataFrame(rows)


def controlled_pilot_outcome_cards(frame: pd.DataFrame | None, *, limit: int = 3) -> list[dict[str, object]]:
    if frame is None or frame.empty:
        return [
            {
                "kicker": "PILOT OUTCOMES",
                "title": "Load reviewed pilot outcomes",
                "body": "Use reviewed batch proof rows to see whether the controlled 5 to 10 company pilot has enough outcomes.",
                "badges": ["read-only", "pilot exit"],
                "command": "make reviewed-batch-proof",
            }
        ]
    cards: list[dict[str, object]] = []
    for _, row in frame.head(max(limit, 0)).iterrows():
        question = _format_missing(row.get("Question"), "Pilot outcome")
        status = _format_missing(row.get("Status"), "manual")
        answer = _compact_fragment(row.get("Answer"), max_chars=150)
        evidence = _compact_fragment(row.get("Evidence"), max_chars=170)
        stop_rule = _compact_fragment(row.get("Stop Rule"), max_chars=160)
        command = _format_missing(row.get("Next Safe Action"), "make reviewed-batch-proof")
        cards.append(
            {
                "kicker": "PILOT OUTCOMES",
                "title": question,
                "body": f"{_card_sentence('Answer', answer)} {_card_sentence('Evidence', evidence)} {_card_sentence('Stop rule', stop_rule)}",
                "badges": [status, "read-only"],
                "command": command,
            }
        )
    return cards


def _pilot_verdict(counts: dict[str, int]) -> tuple[str, str]:
    if counts["blocked"] > 0:
        return "Blocked before pilot", "blocked"
    if counts["manual"] > 0:
        return "Pilot-ready with manual gates", "manual gates"
    if counts["green"] > 0:
        return "Pilot-ready", "green"
    return "Run pilot readiness check", "read-only"


def _cell_text(row: pd.Series, *names: str) -> str:
    for name in names:
        if name in row:
            return _format_missing(row.get(name), "").strip()
    return ""


def _pilot_ticker_tokens(value: object) -> list[str]:
    text = _format_missing(value, "").upper()
    tokens = re.findall(r"\b[A-Z][A-Z0-9.]{0,9}\b", text)
    return [token for token in tokens if token not in {"NONE", "NULL", "NAN", "TOP", "TICKERS", "TICKER"}]


def _is_controlled_pilot_row(row: pd.Series) -> bool:
    lane = _cell_text(row, "Lane", "lane").lower()
    if lane not in CONTROLLED_PILOT_LANES:
        return False
    scope = _cell_text(row, "Scope", "scope").lower()
    tickers = _pilot_ticker_tokens(_cell_text(row, "Tickers", "tickers"))
    changed_tickers = _pilot_ticker_tokens(_cell_text(row, "Changed Tickers", "changed_tickers"))
    explicit_single_scope = any(marker in scope for marker in CONTROLLED_PILOT_SINGLE_SCOPE_MARKERS)
    explicit_single_ticker = len(tickers) == 1 or len(changed_tickers) == 1
    if not explicit_single_scope and not explicit_single_ticker:
        return False
    if "batch" in scope and not explicit_single_scope and not explicit_single_ticker:
        return False
    scope_text = " ".join(
        [
            scope,
            _cell_text(row, "Tickers", "tickers").lower(),
            _cell_text(row, "Changed Tickers", "changed_tickers").lower(),
        ]
    )
    return not any(marker in scope_text for marker in CONTROLLED_PILOT_BROAD_MARKERS)


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


def _proof_queue_route_lane(proof_queue: pd.Series | None) -> str:
    if proof_queue is None:
        return "fundamentals"
    text = " ".join(
        _format_missing(proof_queue.get(column), "")
        for column in ["Queue", "Next Safe Command", "Top Blockers"]
    ).lower()
    if "price" in text:
        return "prices"
    if "peer" in text:
        return "peers"
    if "earnings" in text or "estimate" in text or "optional" in text:
        return "optional"
    if "proof" in text and "history" in text:
        return "proof"
    return "fundamentals"


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

    proof_answer = "Check source-proof gate"
    proof_status = "manual"
    proof_command = "make project-status"
    proof_boundary = "Run project-status first; use provider setup when source-proof queues are exhausted before reopening proof tables."
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
                "body": f"{_card_sentence('One answer', answer)} {_card_sentence('Boundary', boundary)}",
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

    proof_focus = "Check source-proof gate"
    proof_command = "make project-status"
    proof_boundary = "Run project-status first; use provider setup when source-proof queues are exhausted before reopening proof tables."
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

    proof_title = "Check source-proof gate"
    proof_status = "deferred"
    proof_command = "make project-status"
    proof_boundary = "Run project-status first; use provider setup when source-proof queues are exhausted before reopening proof tables."
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
    root: Path | None = None,
) -> pd.DataFrame:
    """Return a compact final public-share checklist for Data Health."""

    license_path = (root or PROJECT_ROOT) / "LICENSE"
    license_present = license_path.exists()
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
            "Gate": "Share-now answer",
            "Status": "portfolio_demo_only",
            "Review": (
                "Share as portfolio/demo only after public-check passes and generated churn stays excluded. "
                "Do not call this open source until a root LICENSE exists. "
                "If source-proof queues are exhausted, use provider setup before broad proof loops. "
                "Do not stage generated churn or sample reports unless exact artifacts are reviewed evidence."
            ),
            "Command": "make public-release-package",
            "Stop Rule": (
                "Stop before sharing if public-check fails, generated churn is staged, or license wording "
                "claims open-source reuse before a root LICENSE exists."
            ),
        },
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
            "Gate": "License status",
            "Status": "portfolio_demo_only" if not license_present else "license_present",
            "Review": (
                f"No root LICENSE file is present; {NO_LICENSE_SHARE_BOUNDARY} "
                f"{_license_decision_options_summary()}"
                if not license_present
                else "Root LICENSE file is present; confirm README wording matches the selected license. "
                f"{_license_decision_options_summary()}"
            ),
            "Command": "make license-status",
            "Stop Rule": (
                "Do not claim reuse rights until a root LICENSE is selected and README wording is updated."
                if not license_present
                else "Stop if README License wording conflicts with the selected license."
            ),
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


def pilot_share_first_answer_frame(
    pilot_frame: pd.DataFrame | None,
    proof_queue_frame: pd.DataFrame | None,
    *,
    output_path: Path = DEFAULT_PACKET_PATH,
) -> pd.DataFrame:
    """Return the first pilot/share answer before detailed gate tables."""

    counts = _status_counts(pilot_frame)
    sync_row = _area_row(pilot_frame, "GitHub sync")
    churn_row = _area_row(pilot_frame, "Generated artifact hygiene")
    public_row = _area_row(pilot_frame, "Public safety")
    browser_row = _area_row(pilot_frame, "Browser QA evidence")
    license_row = _area_row(pilot_frame, "License status")
    proof_queue = _leading_proof_queue(proof_queue_frame)

    def status(row: pd.Series | None, fallback: str = "manual") -> str:
        return _format_missing(row.get("Status") if row is not None else None, fallback).replace("_", " ")

    def detail(row: pd.Series | None, fallback: str) -> str:
        return _compact_fragment(row.get("Detail") if row is not None else None, fallback=fallback, max_chars=180)

    source_answer = "No source-proof queue loaded."
    source_command = "make project-status"
    if proof_queue is not None:
        source_queue = _format_missing(proof_queue.get("Queue"), "Source-proof queue").replace("_", " ")
        source_state = _format_missing(proof_queue.get("State"), "manual").replace("_", " ")
        source_blockers = _compact_fragment(proof_queue.get("Top Blockers"), fallback="No blocker summary reported.", max_chars=130)
        source_answer = f"{source_queue}: {source_state}; {source_blockers}."
        source_command = _format_missing(proof_queue.get("Next Safe Command"), source_command)

    rows = [
        {
            "Question": "Can I share this now?",
            "Answer": (
                "Portfolio/demo only with manual gates; "
                f"{counts['blocked']} blocked gate(s), {counts['manual']} manual gate(s), {counts['green']} green gate(s)."
            ),
            "Next Safe Action": "make public-check",
        },
        {
            "Question": "What must be true first?",
            "Answer": (
                f"GitHub sync: {status(sync_row)}; generated hygiene: {status(churn_row)}; "
                f"public-check: {status(public_row)}; browser evidence: {status(browser_row)}."
            ),
            "Next Safe Action": "make public-check && make browser-qa-evidence",
        },
        {
            "Question": "What stays out?",
            "Answer": f"{detail(churn_row, 'Generated churn stays excluded by default.')} License boundary: {detail(license_row, 'No root LICENSE file found.')}",
            "Next Safe Action": "make diff-hygiene-summary",
        },
        {
            "Question": "What blocks deeper analysis?",
            "Answer": source_answer,
            "Next Safe Action": source_command,
        },
        {
            "Question": "What packet should I create?",
            "Answer": f"{output_path.as_posix()} is copy-only evidence; it does not refresh data or unlock blocked inputs.",
            "Next Safe Action": f"make pilot-readiness-packet OUTPUT={output_path.as_posix()}",
        },
    ]
    return pd.DataFrame(rows, columns=["Question", "Answer", "Next Safe Action"])


def public_share_final_gate_cards(frame: pd.DataFrame | None, *, limit: int = 8) -> list[dict[str, object]]:
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
            "title": "Can I share this?",
            "body": (
                "One-card answer: share as portfolio/demo evidence only after GitHub sync, public-check, "
                "real screenshots and screenshot evidence, generated churn and generated-churn exclusion, pilot packet, license boundary, "
                "source-proof blockers, and research-only wording are reviewed. Keep blocked inputs visible."
            ),
            "badges": ["final gate", "read-only"],
            "command": "make public-check && make browser-qa-evidence",
        }
    ]
    for _, row in frame.head(max(limit, 0)).iterrows():
        gate = _format_missing(row.get("Gate"), "Public gate")
        status = _public_status_label(row.get("Status"))
        review_max_chars = 700 if gate in {"License status", "Share-now answer"} else 150
        review = _compact_fragment(row.get("Review"), max_chars=review_max_chars)
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
    proof_route_lane = _proof_queue_route_lane(proof_queue)

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
            "Step": "3. Readiness context",
            "Purpose": f"Clear the current leading gate: {gate_title}.",
            "Primary View": "Readiness Context",
            "Next Safe Action": gate_command,
            "Route": "?mode=operator&page=data-health",
            "Stop Rule": "Do not jump to raw tables before the current gate is understood.",
        },
        {
            "Step": "4. Navigation-only queue route map",
            "Purpose": f"Choose the leading source-proof lane: {proof_title}. Route links do not execute commands.",
            "Primary View": "Readiness queue review details",
            "Next Safe Action": proof_command,
            "Route": f"?mode=operator&page=data-health&lane={proof_route_lane}&drawer=queue",
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
                "Follow evidence review -> final share gate -> readiness context -> navigation-only queue route map -> "
                "proof lane -> artifact hygiene before opening raw tables. Commands remain copy-only."
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


def pilot_operator_runbook_frame(
    pilot_frame: pd.DataFrame | None,
    proof_queue_frame: pd.DataFrame | None,
    *,
    output_path: Path = DEFAULT_PACKET_PATH,
) -> pd.DataFrame:
    """Return the shortest operator runbook across share and source gates."""

    public_row = _area_row(pilot_frame, "Public safety")
    browser_row = _area_row(pilot_frame, "Browser QA evidence")
    churn_row = _area_row(pilot_frame, "Generated artifact hygiene")
    proof_queue = _leading_proof_queue(proof_queue_frame)

    share_command = "make public-check"
    if public_row is not None:
        share_command = _format_missing(public_row.get("Command"), share_command)
    browser_command = "make browser-qa-evidence"
    if browser_row is not None:
        browser_command = _format_missing(browser_row.get("Command"), browser_command)
    churn_command = "make diff-hygiene-summary"
    if churn_row is not None:
        churn_command = _format_missing(churn_row.get("Command"), churn_command)

    queue_title = "current source-proof queues"
    queue_state = "reviewed or exhausted"
    if proof_queue is not None:
        queue_title = _format_missing(proof_queue.get("Queue"), queue_title)
        queue_state = _format_missing(proof_queue.get("State"), queue_state)

    rows = [
        {
            "Step": "1. Share gate",
            "Operator Answer": "Share only after public-check, real screenshot evidence, generated-churn exclusion, and license boundary are visible.",
            "Next Safe Action": share_command,
            "Evidence": f"Also verify {browser_command}; screenshots are product evidence only.",
            "Stop Rule": "Stop before sharing if public-check, browser evidence, wording, or license boundary is not reviewed.",
        },
        {
            "Step": "2. Source gate",
            "Operator Answer": f"Run project-status before opening source-proof tables; {queue_title} is {queue_state}.",
            "Next Safe Action": "make project-status",
            "Evidence": "Project status decides whether company candidates are executable or queues are exhausted.",
            "Stop Rule": "Do not reopen broad proof loops when current queues are reviewed or exhausted.",
        },
        {
            "Step": "3. Provider setup",
            "Operator Answer": "Use provider setup only when project-status says source-proof queues are exhausted or new provider data could change the gate.",
            "Next Safe Action": "make provider-setup-checklist",
            "Evidence": "Provider setup shows free/public sources, keyed gaps, optional read-only providers, and source boundaries without secrets.",
            "Stop Rule": "Do not treat provider setup as an import, apply, or analysis unlock.",
        },
        {
            "Step": "4. Reviewed one-ticker smoke command",
            "Operator Answer": "Configure at most one provider, rerun preflight, then run a reviewed one-ticker smoke command before any broader batch.",
            "Next Safe Action": "make session-source-preflight",
            "Evidence": "Reviewed smoke command comes from provider setup; broad batches wait until the one-ticker path is source-backed.",
            "Stop Rule": "Do not configure every provider at once or start broad refreshes from setup.",
        },
        {
            "Step": "5. Validate / preview",
            "Operator Answer": "Rows can move only after validation passes, preview scope is intended, rejected rows are zero, and provenance exists.",
            "Next Safe Action": "make imports-validate IMPORT_TICKERS=<ticker> && make imports-preview IMPORT_TICKERS=<ticker>",
            "Evidence": "Apply remains separate and reviewed; missing rows stay blocked, skipped, excluded, or candidate-context-only.",
            "Stop Rule": "Do not apply fabricated, inferred, broad, or rejected rows.",
        },
        {
            "Step": "6. Packet and hygiene",
            "Operator Answer": "Write the reviewer packet only after gates are reviewed; generated churn stays excluded unless exact artifacts are selected evidence.",
            "Next Safe Action": f"make pilot-readiness-packet OUTPUT={output_path.as_posix()} && {churn_command}",
            "Evidence": output_path.as_posix(),
            "Stop Rule": "Do not stage broad generated CSV/JSON/report churn or sample reports by default.",
        },
    ]
    return pd.DataFrame(rows)


def pilot_operator_runbook_cards(frame: pd.DataFrame | None, *, limit: int = 6) -> list[dict[str, object]]:
    if frame is None or frame.empty:
        return [
            {
                "kicker": "PILOT OPERATOR RUNBOOK",
                "title": "Load pilot gates first",
                "body": "Load share-readiness, provider setup, and source-proof queue state before opening raw proof tables.",
                "badges": ["read-only", "operator path"],
                "command": "make pilot-readiness-check TOP_N=10",
            }
        ]

    cards: list[dict[str, object]] = [
        {
            "kicker": "PILOT OPERATOR RUNBOOK",
            "title": "One path across share and source gates",
            "body": (
                "Connect share-readiness, provider setup, and exhausted proof queues before raw tables. "
                "Do not reopen broad proof loops; move through a reviewed one-ticker smoke command, validate / preview, packet, and hygiene."
            ),
            "badges": ["share gate", "source gate", "copy-only"],
            "command": "make project-status",
        }
    ]
    for _, row in frame.head(max(limit, 0)).iterrows():
        step = _format_missing(row.get("Step"), "Runbook step")
        answer = _compact_fragment(row.get("Operator Answer"), max_chars=165)
        evidence = _compact_fragment(row.get("Evidence"), max_chars=140)
        stop_rule = _compact_fragment(row.get("Stop Rule"), max_chars=145)
        command = _format_missing(row.get("Next Safe Action"), "make project-status")
        cards.append(
            {
                "kicker": step.upper(),
                "title": answer,
                "body": f"{_card_sentence('Evidence', evidence)} {_card_sentence('Stop rule', stop_rule)}",
                "badges": ["copy-only", "review gate"],
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
        queue_title = "Check source-proof gate"
        queue_detail = "Run project-status first; if source-proof queues are exhausted, use provider setup before reopening proof tables."
        queue_command = "make project-status"
        queue_stop = "Do not edit raw CSV rows without a source-proof queue, provider setup pivot, or review gate."
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

    proof_title = "Check source-proof gate"
    proof_command = "make project-status"
    proof_status = "deferred"
    proof_evidence = "Run project-status first; if source-proof queues are exhausted, use provider setup before reopening proof tables or editing data rows."
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
