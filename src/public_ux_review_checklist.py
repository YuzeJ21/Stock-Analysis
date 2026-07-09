from __future__ import annotations


PUBLIC_ROUTES = [
    (
        "Home",
        "http://localhost:8501/?mode=public",
        "Current question, Primary next step, Stop rule, First 30 Seconds, Primary Workflow",
        "Visitor understands the readiness-first path before seeing operator detail.",
    ),
    (
        "Stock Selector",
        "http://localhost:8501/?mode=public&page=stock-selector",
        "Current question, Primary next step, Stop rule, selected ticker handoff, readiness-backed rows",
        "Visitor can choose one ticker without treating the queue as advice.",
    ),
    (
        "Single-Stock Report",
        "http://localhost:8501/?mode=public&page=single-stock-report&ticker=NVDA&open=1",
        "Current question, Primary next step, Stop rule, selected ticker, usable now, blocked inputs",
        "Visitor sees what can be used now before detailed report sections.",
    ),
    (
        "Data Health",
        "http://localhost:8501/?mode=public&page=data-health",
        "Current question, Primary next step, Stop rule, one lane answer, blocked/candidate/excluded states",
        "Visitor sees why a lane is blocked before raw proof, queues, or route maps.",
    ),
    (
        "Proof History",
        "http://localhost:8501/?mode=public&page=proof-history",
        "Current question, Primary next step, Stop rule, evidence-only page, latest proof outcome",
        "Visitor can inspect evidence without mistaking it for another command center.",
    ),
]


def render_public_ux_review_checklist() -> str:
    lines = [
        "Public UX Review Checklist",
        "Read-only: this checklist does not refresh data, import rows, capture screenshots, stage files, commit, or push.",
        "Research-only: this is product QA, not investment advice, broker integration, data freshness proof, or trade instruction.",
        "",
        "Use this before public sharing or after UI copy/layout changes.",
        "",
        "| Step | Route | First viewport must show | Pass condition |",
        "| --- | --- | --- | --- |",
    ]
    for step, route, markers, pass_condition in PUBLIC_ROUTES:
        lines.append(f"| {step} | {route} | {markers} | {pass_condition} |")
    lines.extend(
        [
            "",
            "Desktop and mobile checks:",
            "- Open each route at a normal desktop width and phone width.",
            "- Confirm the first viewport has one question, one short answer, one primary next action, and one stop rule.",
            "- Confirm raw tables, command blocks, proof ledgers, provider setup, and operator evidence stay behind Advanced or operator mode.",
            "- Confirm text does not overflow, overlap, or hide the primary next action.",
            "- Confirm screenshots remain product evidence only and do not claim data freshness.",
            "",
            "Stop before sharing if:",
            "- Any public route shows a traceback, blank page, stale generated thumbnail, or raw table before the answer.",
            "- A blocked, candidate-only, skipped, or excluded lane appears as analysis-ready.",
            "- Any page suggests broker trading, order routing, auto-trading, direct buy/sell instructions, or investment advice.",
            "- A hosted URL or provider key is implied before it is configured and verified.",
            "",
            "Next safe commands:",
            "- make dashboard",
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
