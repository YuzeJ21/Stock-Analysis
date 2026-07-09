from __future__ import annotations

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


def render_public_ux_review_checklist() -> str:
    responsive_rows = browser_qa_responsive_route_rows()
    lines = [
        "Public UX Review Checklist",
        "Read-only: this checklist does not refresh data, import rows, capture screenshots, stage files, commit, or push.",
        "Research-only: this is product QA, not investment advice, broker integration, data freshness proof, or trade instruction.",
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
    for row in responsive_rows:
        lines.append(
            "| {Page} | {Route} | {Desktop Viewport} | {Phone Viewport} | {First View Must Keep} | {Mobile Risk} | {Stop Rule} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "Desktop and mobile review rules:",
            "- Open each route at a normal desktop width and phone width.",
            "- Confirm the first viewport has one question, one short answer, one primary next action, and one stop rule.",
            "- Confirm the visible page question matches the route's job in the table above.",
            "- If the page fails, fix only the matching failure action before adding new sections or routes.",
            "- Confirm raw tables, command blocks, proof ledgers, provider setup, and operator evidence stay behind Advanced or operator mode.",
            "- Confirm text does not overflow, overlap, or hide the primary next action.",
            "- Confirm screenshots remain product evidence only and do not claim data freshness.",
            "",
            "Review log template:",
            "- Route reviewed: <route>",
            "- Width: desktop or phone",
            "- First answer visible: yes/no",
            "- Primary next action visible: yes/no",
            "- Advanced/raw details collapsed: yes/no",
            "- Issue classification: resolved, intentionally_deferred, environment_limited, skipped, or blocked_with_evidence",
            "",
            "Stop before sharing if:",
            "- Any public route shows a traceback, blank page, stale generated thumbnail, or raw table before the answer.",
            "- A blocked, candidate-only, skipped, or excluded lane appears as analysis-ready.",
            "- Any page suggests broker trading, order routing, auto-trading, direct buy/sell instructions, or investment advice.",
            "- A hosted URL or provider key is implied before it is configured and verified.",
            "",
            "Next safe commands:",
            "- make dashboard",
            "- make project-status-check",
            "- make browser-qa-evidence",
            "- make public-check",
            "- make diff-hygiene-summary",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    print(render_public_ux_review_checklist())


if __name__ == "__main__":
    main()
