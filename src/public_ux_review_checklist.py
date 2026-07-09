from __future__ import annotations

import argparse
import json

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
    "make project-status-check",
    "make browser-qa-evidence",
    "make public-check",
    "make diff-hygiene-summary",
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Print the public UX review checklist.")
    parser.add_argument("--json", action="store_true", help="Print the checklist as machine-readable JSON.")
    args = parser.parse_args()
    if args.json:
        print(json.dumps(public_ux_review_payload(), indent=2))
    else:
        print(render_public_ux_review_checklist())


if __name__ == "__main__":
    main()
