"""Pure Data Health overview and orientation card helpers.

These helpers own the top-of-page public/operator narrative for Data Health:
what is ready, what remains locked, which lane should be checked first, and
which routine is safe to run without changing files.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


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


def _compact_fragment(value: object, fallback: str = "Not available", *, max_chars: int = 180) -> str:
    text = _format_missing(value, fallback).replace("\n", " ").strip()
    if text == fallback:
        return text
    sentences = [part.strip() for part in text.split(". ") if part.strip()]
    compact = sentences[0] if sentences else text
    if compact and not compact.endswith((".", "?", "!")):
        compact += "."
    if len(compact) > max_chars:
        compact = compact[: max(0, max_chars - 1)].rstrip() + "..."
    if compact.endswith("..."):
        return compact
    return compact.rstrip(" .;:")


def _card_sentence(label: str, fragment: str) -> str:
    clean_label = label.strip().rstrip(":")
    clean_fragment = _format_missing(fragment, "Not available").strip()
    terminal = "" if clean_fragment.endswith((".", "?", "!", "...")) else "."
    return f"{clean_label}: {clean_fragment}{terminal}"


def _trusted_ready_count(frame: pd.DataFrame | None, column: str) -> int:
    if frame is None or frame.empty or column not in frame.columns:
        return 0
    return int(frame[column].astype(bool).sum())


def _public_status_label(value: object, fallback: str = "Not available") -> str:
    text = _format_missing(value, fallback=fallback)
    return {
        "stale": "Stale",
        "missing": "Missing",
        "current": "Current",
    }.get(text.strip().lower(), text)


def orientation_cards(readiness_summary: dict[str, object]) -> list[dict[str, object]]:
    price_ready = int(readiness_summary.get("price_ready") or 0)
    fundamentals_ready = int(readiness_summary.get("fundamentals_ready") or 0)
    dcf_ready = int(readiness_summary.get("dcf_ready") or 0)
    peer_ready = int(readiness_summary.get("peer_ready") or 0)
    earnings_ready = int(readiness_summary.get("earnings_ready") or 0)
    estimates_ready = int(readiness_summary.get("analyst_estimates_ready") or readiness_summary.get("analyst_ready") or 0)
    return [
        {
            "kicker": "WHAT THIS MEANS",
            "title": "Use this page to prove analysis readiness",
            "body": (
                "Data Health is not an error page. It shows what you can analyze now, what is still locked, "
                "which trusted local inputs are ready, and which proof path should be checked next."
            ),
            "badges": ["review guide", "copy only"],
            "command": "make status-check TOP_N=5",
        },
        {
            "kicker": "WHAT YOU CAN ANALYZE NOW",
            "title": f"{price_ready} price-ready / {fundamentals_ready} fundamentals-ready / {dcf_ready} DCF-ready",
            "body": (
                "What this means: price coverage makes setup review available first. Trusted fundamentals provide company-level "
                "valuation support only after required DCF fields pass readiness."
            ),
            "badges": ["price first", "fundamentals next"],
            "command": "make fundamentals-source-ladder-queue TOP_N=25",
        },
        {
            "kicker": "WHAT IS STILL LOCKED",
            "title": f"{peer_ready} peer-ready / {earnings_ready} earnings / {estimates_ready} estimates",
            "body": "What is still locked: peer, earnings, and estimate context stays unavailable until trusted rows exist. The app does not infer these inputs.",
            "badges": ["trusted rows only", "no inference"],
            "command": "make templates",
        },
    ]


def quick_read_cards(readiness_summary: dict[str, object]) -> list[dict[str, object]]:
    price_ready = int(readiness_summary.get("price_ready") or 0)
    fundamentals_ready = int(readiness_summary.get("fundamentals_ready") or 0)
    dcf_ready = int(readiness_summary.get("dcf_ready") or 0)
    peer_ready = int(readiness_summary.get("peer_ready") or 0)
    earnings_ready = int(readiness_summary.get("earnings_ready") or 0)
    estimates_ready = int(readiness_summary.get("analyst_estimates_ready") or readiness_summary.get("analyst_ready") or 0)

    if price_ready <= 0:
        first_title = "Start with trusted price coverage"
        first_body = (
            "No price-ready rows means setup, DCF, peer, earnings, and estimate analysis should stay locked. "
            "Use the scalable dry run first so you can review a capped batch plan instead of repeating 25-ticker refreshes by hand."
        )
        first_command = "make price-refresh-loop DRY_RUN=1"
        first_badges = ["price first", "dry run first"]
    elif fundamentals_ready < price_ready:
        gap = max(price_ready - fundamentals_ready, 0)
        first_title = "Prove fundamentals before valuation"
        first_body = (
            f"{gap} price-ready row(s) still need trusted fundamentals before company-quality or DCF review can expand. "
            "Missing fundamentals are an input gap, not a negative company signal. Review the fundamentals list first, then use the detailed proof steps only when source rows are ready."
        )
        first_command = "make fundamentals-source-ladder-queue TOP_N=25"
        first_badges = ["fundamentals next", "no valuation inference"]
    elif dcf_ready > peer_ready:
        gap = max(dcf_ready - peer_ready, 0)
        first_title = "Add trusted peers for DCF-ready names"
        first_body = (
            f"{gap} DCF-ready row(s) still have peer-relative valuation locked. Standalone DCF can be reviewed, "
            "but peer premium/discount stays withheld until source-backed peer rows, mappings, and peer valuation inputs exist."
        )
        first_command = "make peer-mapping-queue TOP_N=10"
        first_badges = ["peer unlock", "source-backed rows"]
    elif earnings_ready == 0 or estimates_ready == 0:
        first_title = "Optional context is intentionally locked"
        first_body = (
            "Earnings and analyst estimates add context only after trusted local CSV rows pass validation. "
            "Empty optional coverage should not weaken ready price, DCF, or peer analysis. Use the templates and import guide only when trusted rows are available; rejected-row paths stay in the detailed help."
        )
        first_command = "make optional-context-summary TOP_N=10"
        first_badges = ["optional context", "trusted rows only"]
    else:
        first_title = "Review single-stock reports"
        first_body = "Core proof paths look ready from current counts. Use ticker-level reports to inspect assumptions, blockers, and source readiness."
        first_command = "make stock-report-md TICKER=NVDA"
        first_badges = ["single-stock review", "source readiness"]

    return [
        {
            "kicker": "FIRST READ",
            "title": first_title,
            "body": f"What this means: {first_body}",
            "badges": first_badges,
            "command": first_command,
        },
        {
            "kicker": "ANALYZE NOW",
            "title": f"{price_ready} price / {dcf_ready} DCF / {peer_ready} peer-ready",
            "body": (
                "What you can analyze now: price-ready rows can support setup review; DCF-ready rows can support "
                "assumption and sensitivity review; peer-ready rows can support source-backed relative context. "
                "Do not read locked sections as weak conclusions."
            ),
            "badges": ["supported only", "plain English"],
            "command": "make status-check TOP_N=5",
        },
        {
            "kicker": "STILL LOCKED",
            "title": f"{earnings_ready} earnings / {estimates_ready} estimates",
            "body": (
                "What is still locked: optional context remains unavailable until trusted earnings and analyst-estimate "
                "rows exist; missing optional rows are not hidden analysis."
            ),
            "badges": ["no inference", "optional context"],
            "command": "make templates",
        },
    ]


def public_visitor_path_cards(readiness_summary: dict[str, object]) -> list[tuple[str, str, str, str]]:
    price_ready = int(readiness_summary.get("price_ready") or 0)
    dcf_ready = int(readiness_summary.get("dcf_ready") or 0)
    peer_ready = int(readiness_summary.get("peer_ready") or 0)
    review_body = (
        f"Open a ticker report to see exactly which sections are supported. Current proof: {price_ready:,} price-ready, "
        f"{dcf_ready:,} DCF-ready, and {peer_ready:,} peer-ready."
    )
    return [
        ("Review one stock", review_body, "Single-Stock Report", "neutral"),
        (
            "Check data coverage",
            "You are here. Read Quick Read first; the public page shows what is ready, what is blocked, and which trusted-data lane needs attention next.",
            "Data Health",
            "warning",
        ),
        (
            "Inspect proof",
            "Use the latest reviewed evidence before treating a changed readiness state as supported. Stop if source rows, freshness, or proof history are missing. Operator detail stays behind deeper drawers by default.",
            "Proof History",
            "neutral",
        ),
    ]


def public_first_30_second_cards(readiness_summary: dict[str, object]) -> list[dict[str, object]]:
    price_ready = int(readiness_summary.get("price_ready") or 0)
    dcf_ready = int(readiness_summary.get("dcf_ready") or 0)
    peer_ready = int(readiness_summary.get("peer_ready") or 0)
    fundamentals_ready = int(readiness_summary.get("fundamentals_ready") or 0)
    earnings_ready = int(readiness_summary.get("earnings_ready") or 0)
    estimates_ready = int(readiness_summary.get("analyst_estimates_ready") or readiness_summary.get("analyst_ready") or 0)
    still_locked = max(price_ready - fundamentals_ready, 0)
    return [
        {
            "kicker": "READY NOW",
            "title": f"{price_ready:,} price / {dcf_ready:,} DCF / {peer_ready:,} peer-ready",
            "body": (
                "Visitors should read these as supported analysis lanes only. Price coverage supports setup review; "
                "DCF and peer context appear only where trusted inputs pass readiness."
            ),
            "badges": ["supported lanes", "readiness first"],
            "command": "make status-check TOP_N=5",
        },
        {
            "kicker": "STILL BLOCKED",
            "title": f"{still_locked:,} names need trusted fundamentals before deeper review",
            "body": (
                "Blocked rows are not weak conclusions. They are proof checklists for source-backed fundamentals, "
                "shares, peers, earnings, or analyst-estimate rows."
            ),
            "badges": ["blocked visible", "no inference"],
            "command": "make data-coverage-proof-queues TOP_N=10",
        },
        {
            "kicker": "PROOF BOUNDARY",
            "title": f"{earnings_ready:,} earnings / {estimates_ready:,} estimates ready",
            "body": (
                "Optional context stays locked until trusted local rows exist. Public mode shows the product concept; "
                "operator mode keeps validate, preview, apply, and proof-record details."
            ),
            "badges": ["research-only", "operator details hidden"],
            "command": "make public-check",
        },
    ]


def operations_cockpit_cards(
    readiness_summary: dict[str, object],
    ops_frame: pd.DataFrame | None,
    frontier_frame: pd.DataFrame | None,
    earnings_readiness_frame: pd.DataFrame | None,
    analyst_readiness_frame: pd.DataFrame | None,
    freshness: Any,
) -> list[dict[str, object]]:
    price_ready = int(readiness_summary.get("price_ready") or 0)
    dcf_ready = int(readiness_summary.get("dcf_ready") or 0)
    peer_ready = int(readiness_summary.get("peer_ready") or 0)
    lane_count = 0 if ops_frame is None else len(ops_frame)
    review_lanes = 0
    dry_run_lanes = 0
    locked_lanes = 0
    if ops_frame is not None and not ops_frame.empty and "Workflow Mode" in ops_frame.columns:
        modes = ops_frame["Workflow Mode"].astype(str).str.lower()
        review_lanes = int(modes.str.contains("review", na=False).sum())
        dry_run_lanes = int(modes.str.contains("dry", na=False).sum())
        locked_lanes = int(modes.str.contains("locked|manual", regex=True, na=False).sum())

    frontier_title = "No frontier row yet"
    frontier_body = (
        "Run the read-only frontier view after readiness outputs exist; frontier rows describe data-lane impact, "
        "not security attractiveness."
    )
    frontier_command = "make coverage-frontier TOP_N=10"
    if frontier_frame is not None and not frontier_frame.empty:
        top = frontier_frame.iloc[0]
        frontier_title = _format_missing(top.get("Lane"), "Coverage frontier")
        impact = _format_missing(top.get("Unlock Impact"), "0")
        move = _compact_fragment(top.get("Possible State Move"), max_chars=150)
        frontier_body = (
            f"Top data-lane opportunity has unlock impact {impact}. "
            f"{_card_sentence('State move', move)} Use this as a proof queue, not a ranking."
        )
        frontier_command = _format_missing(top.get("Next Safe Command"), "make coverage-frontier TOP_N=10")

    earnings_ready = _trusted_ready_count(earnings_readiness_frame, "has_trusted_earnings")
    estimate_ready = _trusted_ready_count(analyst_readiness_frame, "has_trusted_analyst_estimates")
    earnings_total = 0 if earnings_readiness_frame is None else len(earnings_readiness_frame)
    estimate_total = 0 if analyst_readiness_frame is None else len(analyst_readiness_frame)
    optional_locked = max(earnings_total - earnings_ready, 0) + max(estimate_total - estimate_ready, 0)
    freshness_title = _public_status_label(freshness.status).title()
    freshness_body = (
        f"{freshness.message} "
        "Refresh readiness before relying on exact counts when artifacts are missing or stale. "
        "Treat stale or missing readiness artifacts as a stop sign before relying on final counts."
    )
    freshness_badges = [freshness.status, "refresh before counts"] if freshness.status in {"missing", "stale"} else [freshness.status, "counts usable"]

    return [
        {
            "kicker": "READINESS FRESHNESS",
            "title": freshness_title,
            "body": freshness_body,
            "badges": freshness_badges,
            "command": freshness.refresh_command,
        },
        {
            "kicker": "OPS COCKPIT",
            "title": f"{price_ready:,} price / {dcf_ready:,} DCF / {peer_ready:,} peer-ready",
            "body": (
                f"{lane_count} lane(s) are visible before ticker drilldown: {review_lanes} review lane(s), "
                f"{dry_run_lanes} dry-run lane(s), and {locked_lanes} locked/manual lane(s). "
                "Choose the data lane first, then inspect one capped proof path."
            ),
            "badges": ["lane-first", "copy-only"],
            "command": "make readiness-ops-center",
        },
        {
            "kicker": "NEXT FRONTIER",
            "title": frontier_title,
            "body": frontier_body,
            "badges": ["data-lane impact", "not a ranking"],
            "command": frontier_command,
        },
        {
            "kicker": "OPTIONAL CONTEXT",
            "title": f"{earnings_ready:,} earnings / {estimate_ready:,} estimates ready",
            "body": (
                f"{optional_locked:,} optional-context row(s) remain locked until trusted local rows exist. "
                "Inspect the read-only summary first; write readiness CSVs only after trusted optional rows change."
            ),
            "badges": ["read-only first", "trusted local rows"],
            "command": "make optional-context-summary TOP_N=10",
        },
        {
            "kicker": "PROOF HYGIENE",
            "title": "Preview, then prove",
            "body": (
                "Mutating workflows still go through validate, preview, apply, rejected-row review, and rebuilt readiness. "
                "Keep broad generated CSV churn out unless it is reviewed evidence."
            ),
            "badges": ["validate", "preview", "apply"],
            "command": "make diff-hygiene",
        },
    ]


def source_readiness_guidance_cards(
    freshness: Any,
    *,
    import_summary: dict[str, int] | None = None,
    research_health_summary: dict[str, int] | None = None,
    generated_churn_cards: list[dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    """Return the compact source-readiness strip shown before interpretation."""

    import_summary = import_summary or {}
    research_health_summary = research_health_summary or {}
    freshness_status = _public_status_label(getattr(freshness, "status", ""), fallback="Unknown")
    freshness_message = _compact_fragment(getattr(freshness, "message", ""), "No freshness message available.", max_chars=190)
    freshness_command = _format_missing(getattr(freshness, "refresh_command", ""), "make status-check TOP_N=5")
    rejected_rows = int(import_summary.get("rejected_rows") or 0)
    missing_reports = int(import_summary.get("missing_reports") or 0)
    staged_files = int(import_summary.get("staged_files") or 0)
    partial_rows = int(research_health_summary.get("partial_coverage") or 0)
    thin_liquidity = int(research_health_summary.get("thin_liquidity") or 0)

    generated_card = (generated_churn_cards or [{}])[0]
    generated_title = _format_missing(generated_card.get("title"), "Run diff hygiene before staging")
    generated_body = _compact_fragment(
        generated_card.get("body"),
        "Generated CSV/JSON/report churn stays excluded unless an exact artifact is reviewed evidence.",
        max_chars=190,
    )
    generated_command = _format_missing(generated_card.get("command"), "make diff-hygiene-summary")

    return [
        {
            "kicker": "SOURCE READINESS",
            "title": f"Freshness: {freshness_status}",
            "body": (
                f"{freshness_message} Confirm freshness before interpreting readiness counts or report sections."
            ),
            "badges": ["freshness first", "counts need proof"],
            "command": freshness_command,
        },
        {
            "kicker": "SOURCE QUEUES",
            "title": f"{partial_rows:,} partial coverage row(s)",
            "body": (
                f"{thin_liquidity:,} row(s) need liquidity review. Use research health as a source/gap check, "
                "not as a ranking or recommendation."
            ),
            "badges": ["source gaps", "review only"],
            "command": "make research-health-check TOP_N=10",
        },
        {
            "kicker": "REJECTED ROWS",
            "title": f"{rejected_rows:,} rejected row(s) / {missing_reports:,} missing report(s)",
            "body": (
                f"{staged_files:,} staged import file(s) are visible. Validate, preview, and inspect rejected-row "
                "reports before any apply or supported proof outcome."
            ),
            "badges": ["validate", "preview"],
            "command": "make imports-validate",
        },
        {
            "kicker": "ARTIFACT HYGIENE",
            "title": generated_title,
            "body": generated_body,
            "badges": ["exclude by default", "review evidence"],
            "command": generated_command,
        },
    ]


def freshness_routine_cards(readiness_summary: dict[str, object]) -> list[dict[str, object]]:
    master = int(readiness_summary.get("master_universe") or readiness_summary.get("universe_count") or 0)
    price_ready = int(readiness_summary.get("price_ready") or 0)
    missing_prices = max(master - price_ready, 0) if master else 0
    capped_target = ((min(max(missing_prices, 100), 3500) + 99) // 100) * 100 if missing_prices else 100
    return [
        {
            "kicker": "READ-ONLY ROUTINE",
            "title": "Start without changing files",
            "body": (
                "Use status, readiness, dashboard smoke, and a price-loop dry run as the normal freshness check. "
                "This keeps the app useful without hand-refreshing every ticker every day."
            ),
            "badges": ["safe default", "no file changes"],
            "command": "make status-check TOP_N=5 && make readiness && make dashboard-smoke && make price-refresh-loop DRY_RUN=1",
        },
        {
            "kicker": "PRICE FRESHNESS",
            "title": f"{missing_prices:,} ticker(s) still need price coverage",
            "body": (
                "Prices are the only broad lane designed for capped refresh loops. Run a real loop only after reviewing the dry-run plan, "
                "then inspect generated CSV diffs before committing anything."
            ),
            "badges": ["dry run first", "review diffs"],
            "command": f"make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES={capped_target} TOP_N=100 PROVIDER=auto",
        },
        {
            "kicker": "REVIEW-REQUIRED LANES",
            "title": "Do not automate source judgment",
            "body": (
                "Fundamentals, peer mappings, earnings, and analyst estimates stay review-required. "
                "Use trusted-data pilot packets, validation, preview, rejected-row checks, and readiness rebuilds before analysis changes."
            ),
            "badges": ["trusted source", "no unattended apply"],
            "command": "make trusted-data-pilot-candidates TOP_N=10",
        },
    ]
