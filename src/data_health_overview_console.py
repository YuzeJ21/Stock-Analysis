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


def _humanize_list_text(value: object, fallback: str = "Not available") -> str:
    return _format_missing(value, fallback).replace("_", " ")


def _trusted_ready_count(frame: pd.DataFrame | None, column: str) -> int:
    if frame is None or frame.empty or column not in frame.columns:
        return 0
    return int(frame[column].astype(bool).sum())


def _series_value(row: pd.Series, *names: str, fallback: object = None) -> object:
    lower_to_name = {str(column).strip().lower(): column for column in row.index}
    for name in names:
        column = lower_to_name.get(name.strip().lower())
        if column is not None:
            return row.get(column)
    return fallback


def _series_int(row: pd.Series, *names: str) -> int:
    value = _series_value(row, *names, fallback=0)
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _lane_one_answer(row: pd.Series) -> str:
    lane = _format_missing(_series_value(row, "Lane", "lane"), "Lane")
    mode = _format_missing(_series_value(row, "Workflow Mode", "workflow_mode"), "").lower()
    state = _format_missing(_series_value(row, "State", "state"), "").lower()
    ready = _series_int(row, "Ready", "ready")
    partial = _series_int(row, "Partial", "partial")
    blocked = _series_int(row, "Blocked", "blocked")
    excluded = _series_int(row, "Excluded", "excluded")
    answer = _lane_primary_answer(lane, mode, state, ready, partial, blocked, excluded).rstrip(" .;:")
    return f"{lane} -> {answer}"


def _lane_primary_answer(
    lane: str,
    mode: str,
    state: str,
    ready: int,
    partial: int,
    blocked: int,
    excluded: int,
) -> str:
    lane_text = lane.lower()
    if "optional" in mode or "locked" in mode or "manual" in mode:
        return "Do not use as analysis input yet; locked optional context needs trusted rows."
    if "price" in lane_text and ready > 0 and partial > 0 and blocked == 0:
        return f"Use ready price rows now; review {_qualified_row_count(partial, 'partial')} only if freshness depth matters."
    if ready > 0 and partial > 0 and blocked > 0:
        return f"Use {_qualified_row_count(ready, 'ready')}; review {_qualified_row_count(partial, 'partial')}; keep {_qualified_row_count(blocked, 'blocked')} locked."
    if ready > 0 and blocked > 0:
        return f"Use {_qualified_row_count(ready, 'ready')}; keep {_qualified_row_count(blocked, 'blocked')} locked until source proof exists."
    if ready > 0 and excluded > 0 and blocked == 0 and partial == 0:
        return f"Use {_qualified_row_count(ready, 'ready')}; keep {_qualified_row_count(excluded, 'excluded/not-applicable')} out."
    if ready > 0:
        return f"Use {_qualified_row_count(ready, 'ready')}."
    if blocked > 0:
        return f"Do not use yet; {_row_count_phrase(blocked)} need source proof."
    if state == "excluded" or excluded > 0:
        return "Use applicable rows only; excluded rows are not failed analysis inputs."
    return "No usable lane state reported yet."


def _count_label(count: int, label: str) -> str:
    return f"{count:,} {label}" if count > 0 else "-"


def _row_count_phrase(count: int) -> str:
    return f"{count:,} row" if count == 1 else f"{count:,} row(s)"


def _qualified_row_count(count: int, qualifier: str) -> str:
    return f"{count:,} {qualifier} row" if count == 1 else f"{count:,} {qualifier} row(s)"


def _lane_review_boundary(
    lane: str,
    mode: str,
    state: str,
    ready: int,
    partial: int,
    blocked: int,
    excluded: int,
) -> str:
    lane_text = lane.lower()
    if "optional" in mode or "locked" in mode or "manual" in mode:
        return "Use as optional context only; keep raw provider/manual setup in collapsed operator drawers."
    if "price" in lane_text and ready > 0 and partial > 0 and blocked == 0:
        return "Use the ready price evidence now; inspect the one partial row only if freshness depth matters."
    if "peer" in lane_text and ready > 0 and blocked > 0:
        return "Treat ready peer rows as usable and blocked rows as locked until trusted source proof exists."
    if blocked > 0 and ready == 0:
        return "Treat this lane as locked until source proof exists; keep raw rows in operator drawers."
    if excluded > 0 or state == "excluded":
        return "Use applicable ready rows only; excluded rows are not failed analysis inputs."
    return "Open details for the source-backed next step; commands stay in operator drawers."


def _lane_next_safe_action(
    lane: str,
    mode: str,
    state: str,
    ready: int,
    partial: int,
    blocked: int,
    excluded: int,
) -> str:
    lane_text = lane.lower()
    if "optional" in mode or "locked" in mode or "manual" in mode:
        return "Keep optional context locked until trusted rows exist."
    if "price" in lane_text and ready > 0 and partial > 0 and blocked == 0:
        return "Inspect the partial price row only if freshness depth matters."
    if "peer" in lane_text and blocked > 0:
        return "Use provider setup before reopening broad proof queues."
    if blocked > 0 and ready == 0:
        return "Wait for source proof before treating this lane as usable."
    if state == "excluded" or (excluded > 0 and ready == 0 and partial == 0 and blocked == 0):
        return "Use applicable rows only; keep excluded rows out of analysis."
    return "Open details for the source-backed next step."


def lane_answer_frame(ops_frame: pd.DataFrame | None) -> pd.DataFrame:
    """Return the default Data Health lane answer as one scan-friendly row per lane."""
    columns = [
        "Lane",
        "Primary Answer",
        "Use Now",
        "Partial",
        "Blocked",
        "Context Only",
        "Excluded / Not Applicable",
        "Next Safe Action",
        "Review Boundary",
    ]
    if ops_frame is None or ops_frame.empty:
        return pd.DataFrame(
            [
                {
                    "Lane": "Data Health",
                    "Primary Answer": "No lane summary is loaded yet.",
                    "Use Now": "-",
                    "Partial": "-",
                    "Blocked": "lane summary not loaded",
                    "Context Only": "-",
                    "Excluded / Not Applicable": "-",
                    "Next Safe Action": "Open details for the source-backed next step.",
                    "Review Boundary": "Open details for the source-backed next step; do not infer readiness from missing summary data.",
                }
            ],
            columns=columns,
        )

    rows: list[dict[str, str]] = []
    for _, row in ops_frame.iterrows():
        lane = _format_missing(_series_value(row, "Lane", "lane"), "Lane")
        mode = _format_missing(_series_value(row, "Workflow Mode", "workflow_mode"), "").lower()
        state = _format_missing(_series_value(row, "State", "state"), "").lower()
        ready = _series_int(row, "Ready", "ready")
        partial = _series_int(row, "Partial", "partial")
        blocked = _series_int(row, "Blocked", "blocked")
        excluded = _series_int(row, "Excluded", "excluded")
        context_only = (
            "locked/manual or candidate context"
            if "locked" in mode or "manual" in mode or "optional" in mode or "candidate" in state
            else "-"
        )
        rows.append(
            {
                "Lane": lane,
                "Primary Answer": _lane_primary_answer(lane, mode, state, ready, partial, blocked, excluded),
                "Use Now": _count_label(ready, "ready row(s)"),
                "Partial": _count_label(partial, "partial row(s)"),
                "Blocked": _count_label(blocked, "blocked row(s)"),
                "Context Only": context_only,
                "Excluded / Not Applicable": _count_label(excluded, "excluded/not applicable"),
                "Next Safe Action": _lane_next_safe_action(lane, mode, state, ready, partial, blocked, excluded),
                "Review Boundary": _lane_review_boundary(lane, mode, state, ready, partial, blocked, excluded),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def _public_status_label(value: object, fallback: str = "Not available") -> str:
    text = _format_missing(value, fallback=fallback)
    return {
        "stale": "Stale",
        "missing": "Missing",
        "current": "Current",
    }.get(text.strip().lower(), text)


def lane_answer_card(ops_frame: pd.DataFrame | None) -> dict[str, object]:
    if ops_frame is None or ops_frame.empty:
        return {
            "kicker": "LANE ANSWER",
            "title": "What can I use now?",
            "body": (
                "Use now: no lane summary is loaded yet. Blocked: run the read-only operations center before opening "
                "raw proof tables. Context only: no candidate/context lane reported. Excluded/not applicable: no excluded lane reported. "
                "Next safe action: open operator details for the selected lane."
            ),
            "badges": ["answer first", "raw details collapsed"],
            "command": "make readiness-ops-center",
        }

    ready_fragments: list[str] = []
    partial_fragments: list[str] = []
    blocked_fragments: list[str] = []
    context_fragments: list[str] = []
    excluded_fragments: list[str] = []
    lane_answer_fragments: list[str] = []
    next_action_fragments: list[str] = []

    for _, row in ops_frame.iterrows():
        lane_answer_fragments.append(_lane_one_answer(row))
        lane = _format_missing(_series_value(row, "Lane", "lane"), "Lane")
        mode = _format_missing(_series_value(row, "Workflow Mode", "workflow_mode"), "").lower()
        state = _format_missing(_series_value(row, "State", "state"), "").lower()
        ready = _series_int(row, "Ready", "ready")
        partial = _series_int(row, "Partial", "partial")
        blocked = _series_int(row, "Blocked", "blocked")
        excluded = _series_int(row, "Excluded", "excluded")

        if not ready_fragments and ready > 0:
            ready_fragments.append(f"{lane} has {ready:,} ready row(s)")
        if partial > 0:
            partial_fragments.append(f"{lane} has {partial:,} partial row(s)")
        if blocked > 0:
            blocked_fragments.append(f"{lane} has {blocked:,} blocked row(s)")
        if excluded > 0 or state == "excluded":
            excluded_fragments.append(f"{lane} has {excluded:,} excluded/not-applicable row(s)")
        if ("locked" in mode or "manual" in mode or "candidate" in state) and not context_fragments:
            context_fragments.append(f"{lane} is locked/manual until trusted optional rows exist")
        next_action = _lane_next_safe_action(lane, mode, state, ready, partial, blocked, excluded)
        if next_action and len(next_action_fragments) < 3:
            next_action_fragments.append(f"{lane} -> {next_action.rstrip(' .;:')}")

    body = (
        f"One answer per lane: {' | '.join(lane_answer_fragments)}. "
        f"Use now: {'; '.join(ready_fragments) if ready_fragments else 'no ready lane reported'}. "
        f"Partly usable: {'; '.join(partial_fragments) if partial_fragments else 'no partial lane reported'}. "
        f"Blocked: {'; '.join(blocked_fragments) if blocked_fragments else 'no blocked lane reported'}. "
        f"Context only: {'; '.join(context_fragments) if context_fragments else 'no candidate/context lane reported'}. "
        f"Excluded/not applicable: {'; '.join(excluded_fragments) if excluded_fragments else 'no excluded lane reported'}. "
        f"Next safe action: {'; '.join(next_action_fragments) if next_action_fragments else 'open operator details for the selected lane'}."
    )
    return {
        "kicker": "LANE ANSWER",
        "title": "What can I use now?",
        "body": body,
        "badges": ["answer first", "raw details collapsed"],
        "command": "make readiness-ops-center",
    }


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
        ("Single-Stock Report", review_body, "Single-Stock Report", "neutral"),
        (
            "Data Health",
            "You are here. Read Quick Read first; the public page shows what is ready, what is blocked, and which trusted-data lane needs attention next.",
            "Data Health",
            "warning",
        ),
        (
            "Proof History",
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
                "shares, peers, earnings, or analyst-estimate rows. Use the source gate first; if current queues "
                "are reviewed or exhausted, provider setup is the next safe path."
            ),
            "badges": ["blocked visible", "no inference"],
            "command": "make project-status",
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
        lane_answer_card(ops_frame),
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


def auto_refresh_status_cards(status_payload: dict[str, object] | None) -> list[dict[str, object]]:
    payload = status_payload or {}
    categories = payload.get("source_categories", {})
    categories = categories if isinstance(categories, dict) else {}
    source_activation = _human_provider_gate(_format_missing(payload.get("source_activation"), "unknown"))
    can_run_now = _human_provider_gate(_format_missing(payload.get("can_run_now"), "No executable lane reported"))
    needs_setup = _humanize_list_text(payload.get("needs_setup"), "No setup gaps reported")
    avoid_repeating = _human_provider_gate(_format_missing(payload.get("avoid_repeating"), "No avoid-repeat lane reported"))
    next_command = _format_missing(payload.get("next_executable_command"), "make auto-refresh-status SCHEDULE=daily")
    next_runbook = _format_missing(payload.get("next_runbook"), "make auto-refresh-runbook SCHEDULE=daily")
    free_public = _format_missing(categories.get("free_public_available"), "No free public source reported")
    paid_or_locked = _humanize_list_text(categories.get("paid_or_locked"), "No locked providers reported")
    free_tier_limits = _format_missing(payload.get("free_tier_batch_limits"), "No free-tier limits reported")
    artifact_policy = _compact_fragment(
        payload.get("artifact_policy"),
        "Generated CSV/JSON/report churn stays excluded unless intentionally reviewed evidence.",
        max_chars=190,
    )

    return [
        {
            "kicker": "AUTO REFRESH STATUS",
            "title": f"Source activation: {source_activation}",
            "body": (
                f"Can run now: {can_run_now}. Avoid repeating: {avoid_repeating}. "
                f"{artifact_policy}"
            ),
            "badges": ["read-only", "pivot-safe"],
            "command": "make auto-refresh-status SCHEDULE=daily",
        },
        {
            "kicker": "SOURCE SETUP",
            "title": f"Needs setup: {needs_setup}",
            "body": (
                f"Free public available: {free_public}. Paid or locked: {paid_or_locked}. "
                f"Free-tier limits: {free_tier_limits}."
            ),
            "badges": ["free-public first", "keyed fallbacks"],
            "command": "make session-source-preflight",
        },
        {
            "kicker": "NEXT SCHEDULER STEP",
            "title": next_command,
            "body": (
                "Use the compact runbook for the selected schedule. It keeps validation, preview, apply boundary, "
                "proof, and pivot rules visible before any data-changing step."
            ),
            "badges": ["runbook", "no broad retry loops"],
            "command": next_runbook,
        },
    ]


def _provider_names_by_category(providers: list[dict[str, object]], categories: set[str]) -> str:
    names = [
        _format_missing(row.get("provider"), "Unnamed source")
        for row in providers
        if str(row.get("category") or "").strip() in categories
    ]
    return ", ".join(names) if names else "None reported"


def _provider_detail_for_category(providers: list[dict[str, object]], categories: set[str]) -> str:
    fragments = []
    for row in providers:
        if str(row.get("category") or "").strip() not in categories:
            continue
        provider = _format_missing(row.get("provider"), "Unnamed source")
        category = _format_missing(row.get("category"), "category not reported")
        usage = _format_missing(row.get("usage"), "source usage not reported")
        can_cover = _format_missing(row.get("can_cover"), "coverage not reported")
        batch_policy = _format_missing(row.get("batch_policy"), "")
        fragment = f"{provider}: {category}; {usage}; can cover {can_cover}"
        if batch_policy:
            fragment = f"{fragment}; {batch_policy}"
        fragments.append(fragment)
    return " | ".join(fragments) if fragments else "No provider detail reported"


def source_activation_setup_cards(guide: dict[str, object] | None) -> list[dict[str, object]]:
    payload = guide or {}
    providers_value = payload.get("providers", [])
    providers = [row for row in providers_value if isinstance(row, dict)] if isinstance(providers_value, list) else []
    setup_commands = payload.get("setup_commands", [])
    setup_command = (
        str(setup_commands[0]).strip()
        if isinstance(setup_commands, list) and setup_commands and str(setup_commands[0]).strip()
        else "make source-activation-guide"
    )
    activation_plan = payload.get("activation_plan", [])
    activation_plan_text = _format_missing(
        activation_plan,
        "Run project-status first; if source-proof queues are exhausted, use provider setup before reopening broad loops.",
    )
    apply_gate = payload.get("apply_gate", [])
    apply_gate_text = _format_missing(apply_gate, "Run validate and preview before apply.")

    free_detail = _provider_detail_for_category(providers, {"free_public_available"})
    keyed_detail = _provider_detail_for_category(
        providers,
        {"keyed_free_tier_missing", "keyed_free_tier_available"},
    )
    broker_names = _provider_names_by_category(
        providers,
        {"optional_broker_disabled", "optional_broker_configured"},
    )

    return [
        {
            "kicker": "ACTIVATION PLAN",
            "title": "Start with status, then one reviewed smoke command",
            "body": activation_plan_text,
            "badges": ["no broad loops", "one source first"],
            "command": "make project-status",
        },
        {
            "kicker": "FREE PUBLIC SOURCES",
            "title": _provider_names_by_category(providers, {"free_public_available"}),
            "body": (
                f"{free_detail}. Use these as source-backed or metadata-only lanes according to their usage labels; "
                "they do not turn missing proof into analysis-ready data."
            ),
            "badges": ["free public", "source boundary"],
            "command": "make source-activation-guide",
        },
        {
            "kicker": "KEYED FREE-TIER SETUP",
            "title": _provider_names_by_category(
                providers,
                {"keyed_free_tier_missing", "keyed_free_tier_available"},
            ),
            "body": (
                f"{keyed_detail}. Keep keys outside GitHub and use small capped batches before validate and preview."
            ),
            "badges": ["no secrets", "small batches"],
            "command": setup_command,
        },
        {
            "kicker": "BROKER DATA BOUNDARY",
            "title": f"{broker_names} stays disabled unless configured",
            "body": (
                f"{broker_names} stays disabled by default. If configured, it is for daily OHLCV only, with no "
                "broker actions, order routing, auto-trading, fundamentals, shares, peers, earnings, or estimates."
            ),
            "badges": ["read-only", "disabled by default"],
            "command": "make session-source-preflight",
        },
        {
            "kicker": "APPLY GATE",
            "title": "Validate and preview before any data-changing step",
            "body": (
                f"{apply_gate_text}. Apply only when validation passes, preview scope is intended, rejected rows are "
                "zero, and source provenance exists."
            ),
            "badges": ["validate", "preview", "proof"],
            "command": "make imports-preview IMPORT_TICKERS=<ticker>",
        },
    ]


def _checklist_rows(checklist: dict[str, object] | None) -> list[dict[str, object]]:
    rows_value = (checklist or {}).get("rows", [])
    return [row for row in rows_value if isinstance(row, dict)] if isinstance(rows_value, list) else []


def _checklist_rows_by_state(rows: list[dict[str, object]], states: set[str]) -> str:
    fragments = []
    for row in rows:
        state = str(row.get("setup_state") or "").strip()
        if state not in states:
            continue
        provider = _format_missing(row.get("provider"), "Unnamed source")
        lanes = _format_missing(row.get("unlock_lanes"), "unlock lanes not reported")
        fragments.append(f"{provider}: {state}; unlocks {lanes}")
    return " | ".join(fragments) if fragments else "No matching provider setup state reported"


def _checklist_rows_by_category(rows: list[dict[str, object]], categories: set[str]) -> str:
    fragments = []
    for row in rows:
        category = str(row.get("category") or "").strip()
        if category not in categories:
            continue
        provider = _format_missing(row.get("provider"), "Unnamed source")
        state = _format_missing(row.get("setup_state"), "unknown")
        lanes = _format_missing(row.get("unlock_lanes"), "unlock lanes not reported")
        fragments.append(f"{provider}: {state}; unlocks {lanes}")
    return " | ".join(fragments) if fragments else "No matching provider setup state reported"


def _checklist_next_steps_by_state(rows: list[dict[str, object]], states: set[str]) -> str:
    fragments = []
    for row in rows:
        state = str(row.get("setup_state") or "").strip()
        if state not in states:
            continue
        provider = _format_missing(row.get("provider"), "Unnamed source")
        next_step = _format_missing(row.get("safe_next_step"), "")
        smoke_command = _format_missing(row.get("post_setup_smoke_command"), "")
        if next_step:
            if smoke_command:
                fragments.append(f"{provider}: {next_step} Reviewed smoke command: {smoke_command}")
            else:
                fragments.append(f"{provider}: {next_step}")
    return " | ".join(fragments)


def _checklist_one_provider_setup_step(payload: dict[str, object]) -> str:
    setup_order = payload.get("one_provider_setup_order", [])
    if not isinstance(setup_order, list):
        return ""
    first = next((row for row in setup_order if isinstance(row, dict)), None)
    if not first:
        return ""
    provider = _format_missing(first.get("provider"), "next keyed provider")
    reason = _format_missing(first.get("why_first"), "configure one provider before retrying broader source paths")
    setup_env = _format_missing(first.get("setup_env"), "provider key")
    smoke_command = _format_missing(first.get("smoke_command"), "make session-source-preflight")
    return (
        f"Configure first: {provider}. {reason} Setup env: {setup_env}. "
        f"Reviewed smoke command: {smoke_command}. Do not configure all missing providers at once."
    )


def _checklist_first_answer(payload: dict[str, object]) -> dict[str, object]:
    first_answer = payload.get("first_answer")
    if isinstance(first_answer, dict):
        return first_answer
    source_answer = payload.get("source_answer")
    source_answer = source_answer if isinstance(source_answer, dict) else {}
    unlock_decision = payload.get("coverage_unlock_decision")
    unlock_decision = unlock_decision if isinstance(unlock_decision, dict) else {}
    smoke_command = ""
    rows = _checklist_rows(payload)
    for row in rows:
        if str(row.get("setup_state") or "").strip() == "configured":
            smoke_command = str(row.get("post_setup_smoke_command") or "").strip()
            if smoke_command:
                break
    return {
        "question": "What source can I use next?",
        "free_source_now": source_answer.get("free_public_now") or "see provider rows",
        "missing_key": source_answer.get("needs_key") or "-",
        "do_not_retry": unlock_decision.get("do_not_retry") or "Do not retry exhausted proof queues.",
        "one_safe_smoke": smoke_command or "make session-source-preflight",
        "boundary": "Provider setup only makes a source executable; readiness changes still require validate/preview/apply gates.",
    }


def _checklist_current_gate_value(payload: dict[str, object], name: str, fallback: str = "-") -> str:
    current_gate = payload.get("current_gate")
    if not isinstance(current_gate, dict):
        return fallback
    value = current_gate.get(name)
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value if str(item).strip()) or fallback
    return _format_missing(value, fallback)


def _human_provider_gate(value: str) -> str:
    """Translate source-gate tokens before they reach the operator summary."""

    normalized = value.strip()
    labels = {
        "coverage_workflow_evidence": "Workflow evidence only; current source-proof queues are exhausted",
        "fundamentals_share_count_source_ladder": "fundamentals/share-count source ladder",
    }
    for token, label in labels.items():
        normalized = normalized.replace(token, label)
    return normalized


def _source_boundary_decision_summary(payload: dict[str, object]) -> str:
    rows = payload.get("source_boundary_decision")
    if not isinstance(rows, list):
        return "Source boundary decision is available in provider setup details."
    fragments: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        source_group = _format_missing(row.get("source_group"), "")
        status = _format_missing(row.get("status"), "")
        if not source_group or not status:
            continue
        fragments.append(f"{source_group}: {status}")
    return "; ".join(fragments) if fragments else "Source boundary decision is available in provider setup details."


def provider_setup_first_answer_frame(checklist: dict[str, object] | None) -> pd.DataFrame:
    """Return a compact source-boundary answer before provider setup details."""

    payload = checklist or {}
    first_answer = _checklist_first_answer(payload)
    current_can_run = _human_provider_gate(
        _checklist_current_gate_value(
            payload,
            "can_run_now",
            _format_missing(first_answer.get("free_source_now"), "see provider rows"),
        )
    )
    needs_setup = _checklist_current_gate_value(
        payload,
        "needs_setup",
        _format_missing(first_answer.get("missing_key"), "-"),
    )
    avoid_repeating = _human_provider_gate(
        _checklist_current_gate_value(
            payload,
            "avoid_repeating",
            _format_missing(first_answer.get("do_not_retry"), "Do not retry exhausted proof queues."),
        )
    )
    next_step_reason = _checklist_current_gate_value(payload, "next_step_reason", "")
    boundary = _format_missing(
        first_answer.get("boundary"),
        "Provider setup is not an import, apply, or readiness unlock.",
    )
    if "not an import" not in boundary.lower():
        boundary = f"{boundary} Provider setup is not an import, apply, or readiness unlock."

    return pd.DataFrame(
        [
            {
                "Question": "What can run now?",
                "Answer": current_can_run,
                "Review Boundary": "Use this as source-boundary evidence only; it does not change readiness by itself.",
            },
            {
                "Question": "What setup changes the gate?",
                "Answer": needs_setup,
                "Review Boundary": (
                    "Configure one missing source only after project status shows a real source gap; "
                    "keyed setup is not required for pilot/demo sharing."
                ),
            },
            {
                "Question": "Which source boundary matters?",
                "Answer": _source_boundary_decision_summary(payload),
                "Review Boundary": (
                    "Use this summary before provider setup details; metadata-only, broker-disabled, and locked lanes "
                    "do not become proof."
                ),
            },
            {
                "Question": "What should not be retried?",
                "Answer": f"{avoid_repeating}. {next_step_reason}".strip(),
                "Review Boundary": "One-ticker smoke stays in source setup details; do not reopen broad proof loops from this row.",
            },
            {
                "Question": "What boundary stays true?",
                "Answer": boundary,
                "Review Boundary": "Validation and preview still happen after a reviewed source row exists.",
            },
            {
                "Question": "What should I do next?",
                "Answer": (
                    "Stay in Data Health source setup until provider data, reviewed manual rows, or changed blockers "
                    "create a new source-backed row; then validate and preview one reviewed ticker before any apply step."
                ),
                "Review Boundary": "This is a workflow answer only; it does not refresh, stage, apply, or unlock coverage.",
            },
        ],
        columns=["Question", "Answer", "Review Boundary"],
    )


def provider_setup_checklist_cards(checklist: dict[str, object] | None) -> list[dict[str, object]]:
    payload = checklist or {}
    rows = _checklist_rows(payload)
    secret_policy = _format_missing(payload.get("secret_policy"), "Real key values are never printed.")
    unlock_decision = payload.get("coverage_unlock_decision")
    unlock_decision = unlock_decision if isinstance(unlock_decision, dict) else {}
    source_answer = payload.get("source_answer")
    source_answer = source_answer if isinstance(source_answer, dict) else {}
    concise_answer = _format_missing(
        source_answer.get("answer"),
        "Use the free/public baseline first; configure keyed fallbacks only when project-status says source-proof queues are exhausted.",
    )
    free_public_now = _format_missing(source_answer.get("free_public_now"), "see provider rows")
    configured_keyed = _format_missing(source_answer.get("configured_keyed"), "-")
    needs_key = _format_missing(source_answer.get("needs_key"), "-")
    optional_broker = _format_missing(source_answer.get("optional_broker"), "-")
    source_state = (
        f"Free public sources: {free_public_now}. "
        f"Keyed free-tier fallbacks: configured {configured_keyed}; needs key {needs_key}. "
        f"Optional broker boundary: {optional_broker}. "
        f"Free now: {free_public_now}. Configured keyed: {configured_keyed}. "
        f"Needs key: {needs_key}. Optional broker: {optional_broker}"
    )
    current_gate = payload.get("current_gate")
    current_gate = current_gate if isinstance(current_gate, dict) else {}
    current_gate_summary = ""
    if current_gate:
        current_gate_summary = (
            f" Current source gate: can run now: {_human_provider_gate(_checklist_current_gate_value(payload, 'can_run_now'))}; "
            f"needs setup: {_format_missing(current_gate.get('needs_setup'), '-')}; "
            f"avoid repeating: {_human_provider_gate(_checklist_current_gate_value(payload, 'avoid_repeating'))}; "
            f"next: {_format_missing(current_gate.get('next_step'), '-')}; "
            f"{_human_provider_gate(_format_missing(current_gate.get('next_step_reason'), '-'))}"
        )
    free_public_summary = _checklist_rows_by_category(rows, {"free_public_available"})
    keyed_summary = _checklist_rows_by_state(rows, {"configured", "needs_key"})
    keyed_next_steps = _checklist_next_steps_by_state(rows, {"configured", "needs_key"})
    one_provider_setup_step = _checklist_one_provider_setup_step(payload)
    broker_summary = _checklist_rows_by_state(rows, {"optional_disabled", "optional_configured"})
    all_summary = _checklist_rows_by_state(
        rows,
        {"available", "configured", "needs_key", "optional_disabled", "optional_configured"},
    )
    next_step = next(
        (
            str(row.get("safe_next_step") or "").strip()
            for row in rows
            if str(row.get("setup_state") or "").strip() == "needs_key"
            and str(row.get("safe_next_step") or "").strip()
        ),
        "Run make session-source-preflight, then dry-run the matching source ladder.",
    )

    first_answer = _checklist_first_answer(payload)
    cards = [
        {
            "kicker": "PROVIDER RUN DECISION",
            "title": "Do I run coverage now?",
            "body": (
                "Do not run broad coverage from setup alone. Reopen one reviewed ticker only after new "
                "source-backed rows, keyed provider data, reviewed manual rows, or changed blockers appear. "
                "Use project-status first so provider setup stays source-boundary evidence, not data proof."
            ),
            "badges": ["answer first", "no broad batch", "source boundary"],
            "command": "make project-status",
        },
        {
            "kicker": "PROVIDER FIRST ANSWER",
            "title": _human_provider_gate(_format_missing(first_answer.get("question"), "What source can I use next?")),
            "body": (
                f"What free source can run now: {_human_provider_gate(_format_missing(first_answer.get('free_source_now'), '-'))}. "
                f"What key is missing: {_human_provider_gate(_format_missing(first_answer.get('missing_key'), '-'))}. "
                f"What should not be retried: {_human_provider_gate(_format_missing(first_answer.get('do_not_retry'), '-'))}. "
                f"Setup prerequisite: {_human_provider_gate(_format_missing(first_answer.get('setup_prerequisite'), 'Run preflight before provider reviewed smoke commands'))}. "
                "Review boundary: reviewed one-ticker smoke commands stay in source setup details; "
                "do not treat source reachability as a coverage unlock. "
                f"{_human_provider_gate(_format_missing(first_answer.get('boundary'), 'Provider setup does not change readiness by itself.'))}"
            ),
            "badges": ["answer first", "one source", "no retry loop"],
            "command": "make provider-setup-checklist",
        }
    ]
    if unlock_decision:
        cards.append(
            {
                "kicker": "COVERAGE UNLOCK DECISION",
                "title": _human_provider_gate(
                    _format_missing(
                        unlock_decision.get("answer"),
                        "No broad coverage batch should run from setup alone.",
                    )
                ),
                "body": (
                    f"{_human_provider_gate(_format_missing(unlock_decision.get('can_use_now'), 'Use source gates first.'))} "
                    f"{_human_provider_gate(_format_missing(unlock_decision.get('configure_first'), 'Configure one source path only when needed.'))} "
                    f"{_human_provider_gate(_format_missing(unlock_decision.get('do_not_retry'), 'Do not retry exhausted proof queues.'))} "
                    f"{_human_provider_gate(_format_missing(unlock_decision.get('proof_boundary'), 'Provider setup does not change readiness by itself.'))}"
                ),
                "badges": ["answer first", "source gate", "no broad batch"],
                "command": "make project-status",
            }
        )

    cards.extend(
        [
        {
            "kicker": "PROVIDER SETUP CHECKLIST",
            "title": "Source setup states without secrets",
            "body": f"{concise_answer} {source_state}.{current_gate_summary} {secret_policy} Detailed rows: {all_summary}.",
            "badges": ["setup states", "no secrets"],
            "command": "make provider-setup-checklist",
        },
        {
            "kicker": "WORKFLOW PIVOT",
            "title": "Use scoped review when proof queues are exhausted",
            "body": (
                "When proof queues are exhausted, pivot to source setup and scoped review: run project-status, "
                "provider setup, make universe-scope TOP_N=10, make risk-context, then make universe-preview-summary. "
                "Universe membership is source metadata only; it does not unlock fundamentals, share count, "
                "DCF, peer valuation, earnings, or estimates. "
                "Do not reopen trusted-data candidates until project-status shows executable company candidates."
            ),
            "badges": ["no stale loops", "scope first"],
            "command": "make universe-scope TOP_N=10 && make risk-context",
        },
        {
            "kicker": "SAFE SETUP PATH",
            "title": "Project status before any provider work",
            "body": (
                "Project-status -> provider setup -> reviewed one-ticker smoke command -> validate/preview. "
                "Do not reopen broad proof loops from setup; use this path only when source-proof queues are exhausted "
                "or new source-backed rows/provider keys change the gate."
            ),
            "badges": ["status first", "one provider", "preview gate"],
            "command": "make project-status",
        },
        {
            "kicker": "FREE PUBLIC BASELINE",
            "title": "Free/public baseline works before keys",
            "body": (
                f"{free_public_summary}. These sources can support current proof workflows before optional keyed setup, "
                "but they still respect metadata-only labels, validate/preview gates, and source-proof blockers."
            ),
            "badges": ["free public", "works before keys"],
            "command": "make session-source-preflight",
        },
        {
            "kicker": "KEYED FALLBACKS",
            "title": "Configured or needs key",
            "body": (
                f"{keyed_summary}. Keyed fallbacks expand coverage; they are not required for pilot/demo sharing. "
                f"They remain small-batch source paths and do not bypass validate, preview, rejected-row review, "
                f"or source provenance. {one_provider_setup_step} {keyed_next_steps}"
            ),
            "badges": ["small batch", "source-backed"],
            "command": "make provider-setup-checklist",
        },
        {
            "kicker": "OPTIONAL BROKER",
            "title": "Read-only price data boundary",
            "body": (
                f"{broker_summary}. Optional broker data stays read-only daily OHLCV and does not unlock broker "
                "actions, order routing, auto-trading, fundamentals, shares, peers, earnings, or estimates."
            ),
            "badges": ["read-only", "disabled by default"],
            "command": "make provider-setup-checklist",
        },
        {
            "kicker": "NEXT SAFE STEP",
            "title": "Set up one source path, then preflight",
            "body": next_step,
            "badges": ["preflight first", "no broad retry"],
            "command": "make session-source-preflight",
        },
        ]
    )
    return cards


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
            "title": "Check source setup before proof loops",
            "body": (
                "Fundamentals, peer mappings, earnings, and analyst estimates stay review-required. "
                "Run project status first; if source-proof queues are exhausted, use provider setup instead of repeating trusted-data candidate loops. "
                "Use validation, preview, rejected-row checks, and readiness rebuilds before analysis changes."
            ),
            "badges": ["status gate", "no unattended apply"],
            "command": "make project-status",
        },
    ]
