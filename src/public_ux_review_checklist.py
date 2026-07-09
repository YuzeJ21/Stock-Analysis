from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.browser_qa_evidence import browser_qa_responsive_route_rows


PUBLIC_ROUTES = [
    (
        "Home",
        "http://localhost:8501/?mode=public",
        "What is this product and where do I start?",
        "Current question, Primary next step, Stop rule, First 30 Seconds, Primary Workflow",
        "Visitor understands the readiness-first path before seeing operator detail.",
        "Tighten the first answer and primary Stock Selector handoff; move duplicated methodology or route copy behind Advanced.",
    ),
    (
        "Stock Selector",
        "http://localhost:8501/?mode=public&page=stock-selector",
        "Which stock can I review?",
        "Current question, Primary next step, Stop rule, selected ticker handoff, readiness-backed rows",
        "Visitor can choose one ticker without treating the queue as advice.",
        "Move filters/raw rows below the selected-ticker handoff; keep the queue language readiness-backed, not recommendation-like.",
    ),
    (
        "Single-Stock Report",
        "http://localhost:8501/?mode=public&page=single-stock-report&ticker=NVDA&open=1",
        "What can I use for this ticker right now?",
        "Current question, Primary next step, Stop rule, selected ticker, usable now, blocked inputs",
        "Visitor sees what can be used now before detailed report sections.",
        "Put selected ticker, usable-now, blocked inputs, and one Data Health handoff before detailed report tabs.",
    ),
    (
        "Data Health",
        "http://localhost:8501/?mode=public&page=data-health",
        "Why is something blocked and how do I fix it?",
        "Current question, Primary next step, Stop rule, one lane answer, blocked/candidate/excluded states",
        "Visitor sees why a lane is blocked before raw proof, queues, or route maps.",
        "Show one lane answer first; keep provider setup, route maps, proof ledgers, and raw tables under Advanced/operator mode.",
    ),
    (
        "Proof History",
        "http://localhost:8501/?mode=public&page=proof-history",
        "What evidence changed a readiness state?",
        "Current question, Primary next step, Stop rule, evidence-only page, latest proof outcome",
        "Visitor can inspect evidence without mistaking it for another command center.",
        "Keep latest proof outcomes first and raw ledger rows collapsed; remove command-center style next-action duplication.",
    ),
]


DESKTOP_AND_MOBILE_RULES = [
    "Open each route at a normal desktop width and phone width.",
    "Confirm the first viewport has one question, one short answer, one primary next action, and one stop rule.",
    "Confirm the visible page question matches the route's job in the table above.",
    "If the page fails, fix only the matching failure action before adding new sections or routes.",
    "Confirm raw tables, command blocks, proof ledgers, provider setup, and operator evidence stay behind Advanced or operator mode.",
    "Confirm text does not overflow, overlap, or hide the primary next action.",
    "Confirm screenshots remain product evidence only and do not claim data freshness.",
]


BROWSER_CAPTURE_FALLBACK = [
    "If in-app browser capture is unavailable or times out, classify the review as environment_limited and continue with a normal local browser review.",
    "Keep the existing real screenshot assets unless a normal browser shows a route mismatch, traceback, raw-table-first view, or missing research-only boundary.",
    "Do not replace screenshot assets from a timed-out, blank, cropped, or loading capture.",
]


STOP_BEFORE_SHARING = [
    "Any public route shows a traceback, blank page, stale generated thumbnail, or raw table before the answer.",
    "A blocked, candidate-only, skipped, or excluded lane appears as analysis-ready.",
    "Any page suggests broker trading, order routing, auto-trading, direct buy/sell instructions, or investment advice.",
    "A hosted URL or provider key is implied before it is configured and verified.",
]


NEXT_SAFE_COMMANDS = [
    "make dashboard",
    "make public-ux-review-checklist-json",
    "make public-ux-review-notes-check",
    "make project-status-check",
    "make dashboard-smoke",
    "make browser-qa-evidence",
    "make public-check",
    "make diff-hygiene-summary",
]

REVIEW_NOTE_ARTIFACT = {
    "suggested_local_folder": "/tmp/stock-command-center-public-ux-review",
    "suggested_notes_file": "public-ux-review-notes.md",
    "git_boundary": "local audit notes only; do not stage unless intentionally reviewed",
}

LIVE_REVIEW_PROTOCOL = [
    "Create the suggested local audit folder before opening routes.",
    "Record one note row per page/viewport before changing code or screenshots.",
    "Save screenshots only after confirming they show the real app, the right route, and a stable first viewport.",
    "Keep raw tables, commands, provider setup, route maps, and proof ledgers collapsed unless the review intentionally opens Advanced.",
    "If capture is environment_limited, record that state once and continue with repo-side checks.",
]


def public_ux_review_payload() -> dict[str, object]:
    return {
        "title": "Public UX Review Checklist",
        "mode": "read_only_product_qa",
        "research_boundary": "product QA, not investment advice, broker integration, data freshness proof, or trade instruction",
        "public_workflow": [step for step, *_ in PUBLIC_ROUTES],
        "route_checks": [
            {
                "page": step,
                "route": route,
                "question": question,
                "first_viewport_must_show": markers,
                "pass_condition": pass_condition,
                "if_it_fails": failure_action,
            }
            for step, route, question, markers, pass_condition, failure_action in PUBLIC_ROUTES
        ],
        "responsive_route_checks": browser_qa_responsive_route_rows(),
        "desktop_and_mobile_rules": DESKTOP_AND_MOBILE_RULES,
        "browser_capture_fallback": BROWSER_CAPTURE_FALLBACK,
        "review_note_artifact": REVIEW_NOTE_ARTIFACT,
        "live_review_protocol": LIVE_REVIEW_PROTOCOL,
        "review_log_template": [
            "Route reviewed: <route>",
            "Width: desktop or phone",
            "First answer visible: yes/no",
            "Primary next action visible: yes/no",
            "Advanced/raw details collapsed: yes/no",
            "Issue classification: resolved, intentionally_deferred, environment_limited, skipped, or blocked_with_evidence",
        ],
        "stop_before_sharing": STOP_BEFORE_SHARING,
        "next_safe_commands": NEXT_SAFE_COMMANDS,
    }


def render_public_ux_review_checklist() -> str:
    payload = public_ux_review_payload()
    responsive_rows = payload["responsive_route_checks"]
    lines = [
        str(payload["title"]),
        "Read-only: this checklist does not refresh data, import rows, capture screenshots, stage files, commit, or push.",
        f"Research-only: this is {payload['research_boundary']}.",
        "",
        "Use this before public sharing or after UI copy/layout changes.",
        "",
        "| Step | Route | Page question | First viewport must show | Pass condition | If it fails |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for step, route, question, markers, pass_condition, failure_action in PUBLIC_ROUTES:
        lines.append(f"| {step} | {route} | {question} | {markers} | {pass_condition} | {failure_action} |")
    lines.extend(
        [
            "",
            "Responsive route checks:",
            "| Page | Route | Desktop viewport | Phone viewport | First view must keep | Mobile risk | Stop rule |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in responsive_rows:  # type: ignore[assignment]
        lines.append(
            "| {Page} | {Route} | {Desktop Viewport} | {Phone Viewport} | {First View Must Keep} | {Mobile Risk} | {Stop Rule} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "Desktop and mobile review rules:",
            *[f"- {rule}" for rule in DESKTOP_AND_MOBILE_RULES],
            "",
            "Browser capture fallback:",
            *[f"- {rule}" for rule in BROWSER_CAPTURE_FALLBACK],
            "",
            "Review note artifact:",
            f"- Suggested local folder: {REVIEW_NOTE_ARTIFACT['suggested_local_folder']}",
            f"- Suggested notes file: {REVIEW_NOTE_ARTIFACT['suggested_notes_file']}",
            f"- Git boundary: {REVIEW_NOTE_ARTIFACT['git_boundary']}",
            "",
            "Live review protocol:",
            *[f"- {rule}" for rule in LIVE_REVIEW_PROTOCOL],
            "",
            "Review log template:",
            *[f"- {item}" for item in payload["review_log_template"]],  # type: ignore[index]
            "",
            "Stop before sharing if:",
            *[f"- {rule}" for rule in STOP_BEFORE_SHARING],
            "",
            "Next safe commands:",
            *[f"- {command}" for command in NEXT_SAFE_COMMANDS],
        ]
    )
    return "\n".join(lines)


def render_public_ux_review_notes() -> str:
    payload = public_ux_review_payload()
    lines = [
        "# Public UX Review Notes",
        "",
        "Research-only product QA notes; not investment advice, data freshness proof, or trade instruction.",
        "Screenshots remain product evidence only and do not unlock blocked inputs.",
        "",
        "## Review Boundary",
        "",
        f"- Suggested local folder: {REVIEW_NOTE_ARTIFACT['suggested_local_folder']}",
        f"- Git boundary: {REVIEW_NOTE_ARTIFACT['git_boundary']}",
        "- Do not stage this file unless it is intentionally reviewed as pilot evidence.",
        "",
        "## Live Review Protocol",
        "",
        *[f"- {rule}" for rule in LIVE_REVIEW_PROTOCOL],
        "",
        "## Route Notes",
        "",
        "| Page | Viewport | First answer visible | Primary next action visible | Advanced/raw details collapsed | Issue classification | Notes |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for route in payload["route_checks"]:  # type: ignore[index]
        page = str(route["page"])  # type: ignore[index]
        for viewport in ("desktop", "phone"):
            lines.append(f"| {page} | {viewport} | pending | pending | pending | pending |  |")
    lines.extend(
        [
            "",
            "## Stop Before Sharing If Observed",
            "",
            *[f"- {rule}" for rule in STOP_BEFORE_SHARING],
            "",
            "## Next Safe Commands",
            "",
            *[f"- {command}" for command in NEXT_SAFE_COMMANDS],
        ]
    )
    return "\n".join(lines)


def write_public_ux_review_notes(output_dir: str | Path | None = None) -> Path:
    destination = Path(output_dir or REVIEW_NOTE_ARTIFACT["suggested_local_folder"])
    destination.mkdir(parents=True, exist_ok=True)
    output_path = destination / REVIEW_NOTE_ARTIFACT["suggested_notes_file"]
    output_path.write_text(render_public_ux_review_notes() + "\n", encoding="utf-8")
    return output_path


def _default_review_notes_path() -> Path:
    return Path(REVIEW_NOTE_ARTIFACT["suggested_local_folder"]) / str(REVIEW_NOTE_ARTIFACT["suggested_notes_file"])


def _parse_review_note_rows(notes_text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    in_route_notes = False
    headers: list[str] = []
    for raw_line in notes_text.splitlines():
        line = raw_line.strip()
        if line == "## Route Notes":
            in_route_notes = True
            continue
        if in_route_notes and line.startswith("## "):
            break
        if not in_route_notes or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not headers:
            headers = cells
            continue
        if all(set(cell) <= {"-", " "} for cell in cells):
            continue
        if len(cells) != len(headers):
            continue
        rows.append(dict(zip(headers, cells)))
    return rows


def _route_for_page(page: str) -> str:
    for route_page, route, *_ in PUBLIC_ROUTES:
        if route_page == page:
            return route
    return ""


def _first_pending_review(rows: list[dict[str, str]] | None = None) -> dict[str, str]:
    if rows:
        for row in rows:
            classification = row.get("Issue classification", "").strip() or "pending"
            if classification == "pending":
                page = row.get("Page", "")
                return {
                    "page": page,
                    "viewport": row.get("Viewport", ""),
                    "route": _route_for_page(page),
                }
    first_page, first_route, *_ = PUBLIC_ROUTES[0]
    return {"page": first_page, "viewport": "desktop", "route": first_route}


def _escape_note_cell(value: str) -> str:
    return value.replace("|", "/").replace("\n", " ").strip()


def record_public_ux_review_note(
    *,
    page: str,
    viewport: str,
    first_answer_visible: str,
    primary_next_action_visible: str,
    advanced_details_collapsed: str,
    classification: str,
    notes: str,
    notes_path: str | Path | None = None,
) -> Path:
    path = Path(notes_path) if notes_path is not None else _default_review_notes_path()
    if not path.exists():
        write_public_ux_review_notes(path.parent)

    lines = path.read_text(encoding="utf-8").splitlines()
    replacement = (
        f"| {_escape_note_cell(page)} | {_escape_note_cell(viewport)} | "
        f"{_escape_note_cell(first_answer_visible)} | {_escape_note_cell(primary_next_action_visible)} | "
        f"{_escape_note_cell(advanced_details_collapsed)} | {_escape_note_cell(classification)} | {_escape_note_cell(notes)} |"
    )
    matched = False
    updated_lines: list[str] = []
    for line in lines:
        if line.startswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) == 7 and cells[0] == page and cells[1] == viewport:
                updated_lines.append(replacement)
                matched = True
                continue
        updated_lines.append(line)

    if not matched:
        raise ValueError(f"No public UX review note row matched {page} / {viewport}.")

    path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
    return path


def public_ux_review_notes_status(notes_path: str | Path | None = None) -> dict[str, object]:
    path = Path(notes_path) if notes_path is not None else _default_review_notes_path()
    expected_rows = len(PUBLIC_ROUTES) * 2
    if not path.exists():
        return {
            "status": "notes_missing",
            "path": str(path),
            "total_rows": 0,
            "expected_rows": expected_rows,
            "pending_rows": expected_rows,
            "classification_counts": {"pending": expected_rows},
            "problem_rows": [],
            "next_pending_review": _first_pending_review(),
            "next_safe_command": "make public-ux-review-notes",
            "boundary": REVIEW_NOTE_ARTIFACT["git_boundary"],
        }

    rows = _parse_review_note_rows(path.read_text(encoding="utf-8"))
    classification_counts: dict[str, int] = {}
    problem_rows: list[dict[str, str]] = []
    for row in rows:
        classification = row.get("Issue classification", "").strip() or "pending"
        classification_counts[classification] = classification_counts.get(classification, 0) + 1
        if classification not in {"pending", "resolved"}:
            problem_rows.append(
                {
                    "page": row.get("Page", ""),
                    "viewport": row.get("Viewport", ""),
                    "classification": classification,
                    "notes": row.get("Notes", ""),
                }
            )

    pending_rows = classification_counts.get("pending", 0)
    if pending_rows == expected_rows:
        status = "not_started"
    elif pending_rows:
        status = "review_in_progress"
    elif problem_rows:
        status = "review_has_deferred_or_limited_items"
    else:
        status = "review_complete"

    return {
        "status": status,
        "path": str(path),
        "total_rows": len(rows),
        "expected_rows": expected_rows,
        "pending_rows": pending_rows,
        "classification_counts": classification_counts,
        "problem_rows": problem_rows,
        "next_pending_review": _first_pending_review(rows) if pending_rows else {},
        "next_safe_command": "make public-ux-review-notes",
        "boundary": REVIEW_NOTE_ARTIFACT["git_boundary"],
    }


def render_public_ux_review_notes_status(notes_path: str | Path | None = None) -> str:
    status = public_ux_review_notes_status(notes_path)
    counts = status["classification_counts"]
    count_parts = [f"{key}: {value}" for key, value in sorted(counts.items())]  # type: ignore[union-attr]
    lines = [
        "Public UX Review Notes Status",
        "Read-only: this status does not open the browser, refresh data, stage files, commit, or push.",
        "Research-only: review notes are product QA evidence only, not data freshness proof or trade instruction.",
        "",
        f"status: {status['status']}",
        f"path: {status['path']}",
        f"rows: {status['total_rows']} recorded / {status['expected_rows']} expected",
        f"pending_rows: {status['pending_rows']}",
        f"classification_counts: {', '.join(count_parts) if count_parts else '-'}",
        f"next_safe_command: {status['next_safe_command']}",
        f"boundary: {status['boundary']}",
    ]
    next_pending = status["next_pending_review"]
    if next_pending:
        lines.append(
            "next_pending_review: {page} | {viewport} | {route}".format(**next_pending)  # type: ignore[arg-type]
        )
    problem_rows = status["problem_rows"]
    if problem_rows:
        lines.extend(["", "Deferred / limited / blocked rows:"])
        for row in problem_rows:  # type: ignore[assignment]
            lines.append(f"- {row['page']} | {row['viewport']} | {row['classification']} | {row['notes']}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Print the public UX review checklist.")
    parser.add_argument("--json", action="store_true", help="Print the checklist as machine-readable JSON.")
    parser.add_argument("--notes", action="store_true", help="Write a local Markdown notes template for live UX review.")
    parser.add_argument("--notes-status", action="store_true", help="Summarize the local public UX review notes status.")
    parser.add_argument("--record-note", action="store_true", help="Record one local public UX review note row.")
    parser.add_argument("--page", default=None, help="Page name for --record-note.")
    parser.add_argument("--viewport", default=None, help="Viewport for --record-note: desktop or phone.")
    parser.add_argument("--first-answer-visible", default="pending", help="yes/no/pending for --record-note.")
    parser.add_argument("--primary-next-action-visible", default="pending", help="yes/no/pending for --record-note.")
    parser.add_argument("--advanced-details-collapsed", default="pending", help="yes/no/pending for --record-note.")
    parser.add_argument("--classification", default="pending", help="Outcome classification for --record-note.")
    parser.add_argument("--note-text", default="", help="Freeform note text for --record-note.")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for --notes output. Defaults to /tmp/stock-command-center-public-ux-review.",
    )
    args = parser.parse_args()
    if args.notes:
        output_path = write_public_ux_review_notes(args.output_dir)
        print(f"Wrote: {output_path}")
    elif args.record_note:
        if not args.page or not args.viewport:
            raise SystemExit("--record-note requires --page and --viewport.")
        notes_path = None
        if args.output_dir:
            notes_path = Path(args.output_dir) / str(REVIEW_NOTE_ARTIFACT["suggested_notes_file"])
        output_path = record_public_ux_review_note(
            page=args.page,
            viewport=args.viewport,
            first_answer_visible=args.first_answer_visible,
            primary_next_action_visible=args.primary_next_action_visible,
            advanced_details_collapsed=args.advanced_details_collapsed,
            classification=args.classification,
            notes=args.note_text,
            notes_path=notes_path,
        )
        print(f"Updated: {output_path}")
        print(render_public_ux_review_notes_status(output_path))
    elif args.notes_status:
        print(render_public_ux_review_notes_status())
    elif args.json:
        print(json.dumps(public_ux_review_payload(), indent=2))
    else:
        print(render_public_ux_review_checklist())


if __name__ == "__main__":
    main()
