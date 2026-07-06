"""Single-stock workflow helpers for readiness-first dashboard rendering."""

from __future__ import annotations

import re

import pandas as pd


PUBLIC_STATUS_LABELS = {
    "avoid": "No Setup",
    "broken": "Thesis Review Needed",
    "broken / avoid": "Thesis Review Needed / No Setup",
    "broken / no setup": "Thesis Review Needed / No Setup",
    "ignore": "Not Prioritized",
    "insufficient_data": "Insufficient data",
    "insufficient_peer_data": "Insufficient peer data",
    "missing_file": "Missing file",
    "monitor_context": "Monitor context",
    "not_ready": "Not ready",
    "peer_data_unavailable": "Peer data unavailable",
    "valid_with_warnings": "Valid with warnings",
    "blocked_until_fundamentals_dcf": "Blocked until fundamentals / DCF",
    "wait_for_core_data": "Waiting for price, fundamentals, and DCF",
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


def _normalize_operator_command(command: object) -> str:
    command_text = _format_missing(command, "")
    if command_text == "make status":
        return "make status-check TOP_N=5"
    if command_text == "make onboarding":
        return "make status-check TOP_N=5"
    return command_text


def _public_status_label(value: object, fallback: str = "Not available") -> str:
    text = _format_missing(value, fallback=fallback)
    lowered = text.strip().lower()
    if lowered in PUBLIC_STATUS_LABELS:
        return PUBLIC_STATUS_LABELS[lowered]
    replacements = {
        "valuation_status=not_ready": "valuation status is not ready",
        "peer_data_unavailable": "peer data unavailable",
        "insufficient_data": "insufficient data",
        "insufficient_peer_data": "insufficient peer data",
        "monitor_context": "monitor context",
        "blocked_until_fundamentals_dcf": "blocked until fundamentals / DCF",
        "wait_for_core_data": "waiting for price, fundamentals, and DCF",
    }
    for old, new in replacements.items():
        text = re.sub(rf"\b{re.escape(old)}\b", new, text, flags=re.IGNORECASE)
    return text


def _compact_reason(value: object, max_sentences: int = 1, max_chars: int = 150) -> str:
    text = _format_missing(value)
    if text == "Not available":
        return text
    text = re.sub(r"\s+", " ", text).strip()
    sentences = [part.strip() for part in text.split(". ") if part.strip()]
    compact = ". ".join(sentences[:max_sentences])
    if compact and not compact.endswith((".", "?", "!")):
        compact += "."
    if len(compact) > max_chars:
        compact = compact[: max_chars - 1].rstrip() + "..."
    return compact


def _ticker_focus_command(lane: str, ticker: object, fallback: str = "") -> str:
    ticker_text = _format_missing(ticker, fallback="").upper()
    if not ticker_text:
        return fallback
    lane_key = _format_missing(lane, fallback="").strip().lower()
    command_map = {
        "prices": f"make focus-price TICKER={ticker_text}",
        "fundamentals": f"make focus-fundamentals TICKER={ticker_text}",
        "peers": f"make focus-peers TICKER={ticker_text}",
    }
    return command_map.get(lane_key, fallback)


def _preferred_row_command(row: pd.Series | dict[str, object], fallback: str = "") -> str:
    def _raw_value(key: str) -> object:
        return row.get(key) if hasattr(row, "get") else ""

    focus_command = ""
    if hasattr(row, "get"):
        focus_command = _normalize_operator_command(_format_missing(_raw_value("focus_command"), fallback=""))
    example_command = _normalize_operator_command(_format_missing(_raw_value("example_command"), fallback=""))
    return focus_command or example_command or _normalize_operator_command(fallback)


def _stock_report_md_command(ticker: object, fallback: str = "TICKER") -> str:
    ticker_text = _format_missing(ticker, fallback).upper()
    return f"make stock-report-md TICKER={ticker_text}"


def single_stock_next_command(snapshot: dict[str, object]) -> str:
    ticker = _format_missing(snapshot.get("ticker"), "TICKER").upper()
    asset_type = _format_missing(snapshot.get("asset_type"), "").lower()
    dcf_status = _format_missing(snapshot.get("dcf_status"), "").lower()
    if dcf_status == "excluded" or asset_type in {"etf", "index_proxy", "fund"}:
        return _stock_report_md_command(ticker)
    if not snapshot.get("price_ready"):
        return f"make focus-price TICKER={ticker}"
    if dcf_status == "blocked":
        return f"make focus-fundamentals TICKER={ticker}"
    if dcf_status == "ready" and not snapshot.get("peer_ready") and "peer" in _format_missing(snapshot.get("missing_data"), "").lower():
        return f"make focus-peers TICKER={ticker}"
    if not snapshot.get("earnings_ready") or not snapshot.get("analyst_estimates_ready"):
        return "make optional-context-worklist TOP_N=25"
    return _stock_report_md_command(ticker)


def single_stock_report_data_health_route(
    *,
    asset_type: object,
    valuation_status: object,
    price_ready: bool,
    dcf_ready: bool,
    peer_ready: bool,
    earnings_ready: bool,
    estimates_ready: bool,
) -> dict[str, str]:
    """Return the Data Health route for a loaded single-stock report."""

    normalized_asset_type = _format_missing(asset_type, "").lower()
    normalized_valuation_status = _format_missing(valuation_status, "").lower()
    monitor_context = normalized_asset_type in {"etf", "index_proxy", "fund"} or "excluded" in normalized_valuation_status

    if monitor_context:
        return {
            "route": "?mode=operator&page=data-health&lane=proof&drawer=proof",
            "route_label": "Proof History",
            "stop_rule": "Stop if monitor context is read as operating-company DCF or peer valuation.",
        }
    if not price_ready:
        return {
            "route": "?mode=operator&page=data-health&lane=prices",
            "route_label": "Prices lane",
            "stop_rule": "Stop if price rows are missing, stale, rejected, or not tied to the selected ticker.",
        }
    if not dcf_ready:
        return {
            "route": "?mode=operator&page=data-health&lane=fundamentals",
            "route_label": "Fundamentals / DCF source-proof lane",
            "stop_rule": "Stop if fundamentals, shares, market cap, or DCF inputs would be inferred or placeholder-backed.",
        }
    if not peer_ready:
        return {
            "route": "?mode=operator&page=data-health&lane=peers",
            "route_label": "Peers source-proof lane",
            "stop_rule": "Stop if peer mappings or peer valuation inputs lack source-backed rows.",
        }
    if not earnings_ready or not estimates_ready:
        return {
            "route": "?mode=operator&page=data-health&lane=optional",
            "route_label": "Optional context lane",
            "stop_rule": "Stop if earnings or analyst estimates are absent from trusted local rows.",
        }
    return {
        "route": "?mode=operator&page=data-health&lane=proof&drawer=proof",
        "route_label": "Proof History",
        "stop_rule": "Stop if readiness changed since the report was generated; rebuild proof first.",
    }


def single_stock_workflow_loop_cards(snapshot: dict[str, object]) -> list[dict[str, object]]:
    """Return a compact loop summary before single-stock details."""

    ticker = _format_missing(snapshot.get("ticker"), "TICKER").upper()
    state = _public_status_label(snapshot.get("status"))
    decision = _format_missing(snapshot.get("decision_subtype") or snapshot.get("decision_bucket"), "Not classified")
    dcf_status = _format_missing(snapshot.get("dcf_status"), "blocked").lower()
    asset_type = _format_missing(snapshot.get("asset_type"), "").lower()
    monitor_context = dcf_status == "excluded" or asset_type in {"etf", "index_proxy", "fund"}
    command = single_stock_next_command(snapshot)

    if not snapshot or snapshot.get("status") == "missing":
        next_step = "Refresh local readiness before reading ticker-level output."
        stop_rule = "Stop until the ticker appears in local readiness outputs."
        badges = ["missing ticker", "readiness first"]
    elif monitor_context:
        next_step = "Read monitor context, then use proof history only if source freshness needs review."
        stop_rule = "Stop if ETF, fund, or index context is read as operating-company DCF."
        badges = ["monitor context", "excluded methods visible"]
    elif not snapshot.get("price_ready"):
        next_step = "Prove trusted price history before setup, trend, valuation, peer, or optional context."
        stop_rule = "Stop if price rows are missing, stale, rejected, or not tied to this ticker."
        badges = ["price first", "no inference"]
    elif dcf_status == "blocked":
        next_step = "Route fundamentals, shares, market-cap, or DCF blockers to Data Health source review."
        stop_rule = "Stop if valuation inputs would be inferred or placeholder-backed."
        badges = ["fundamentals gate", "source proof"]
    elif dcf_status == "ready" and not snapshot.get("peer_ready"):
        next_step = "Review standalone DCF now; route peer-relative context to the peers lane."
        stop_rule = "Stop if peer mappings or peer inputs lack source-backed rows."
        badges = ["DCF reviewable", "peer gated"]
    elif not snapshot.get("earnings_ready") or not snapshot.get("analyst_estimates_ready"):
        next_step = "Review core sections now; keep optional earnings and estimate context locked."
        stop_rule = "Stop if optional context is absent from trusted local rows."
        badges = ["core reviewable", "optional locked"]
    else:
        next_step = "Read supported sections, then rerun proof after any local import or refresh."
        stop_rule = "Stop if readiness changed since this report was generated."
        badges = ["reviewable", "proof first"]

    return [
        {
            "kicker": "CURRENT STEP",
            "title": f"{ticker}: Single-stock review",
            "body": f"Previous proof: saved readiness row. Current state: {state}. Decision context: {decision}.",
            "badges": ["selected ticker", "local proof"],
            "command": _stock_report_md_command(ticker),
        },
        {
            "kicker": "NEXT SAFE ACTION",
            "title": "Use the right proof lane before deeper interpretation",
            "body": f"{next_step} The dashboard keeps this as navigation and copy-only command context.",
            "badges": badges,
            "command": command,
        },
        {
            "kicker": "STOP RULE",
            "title": "No trusted input, no conclusion",
            "body": f"{stop_rule} Locked, partial, and excluded sections stay visible until proof changes the state.",
            "badges": ["research-only", "blocked stays blocked"],
            "command": "make readiness",
        },
    ]


def single_stock_workflow_fit_cards(snapshot: dict[str, object]) -> list[dict[str, object]]:
    """Return ticker workflow cards for the Single-Stock page before raw detail."""

    ticker = _format_missing(snapshot.get("ticker"), "TICKER").upper()
    state = _public_status_label(snapshot.get("status"))
    decision = _format_missing(snapshot.get("decision_subtype") or snapshot.get("decision_bucket"), "Not classified")
    dcf_status = _format_missing(snapshot.get("dcf_status"), "blocked").lower()
    asset_type = _format_missing(snapshot.get("asset_type"), "").lower()
    monitor_context = dcf_status == "excluded" or asset_type in {"etf", "index_proxy", "fund"}
    price_ready = bool(snapshot.get("price_ready"))
    peer_ready = bool(snapshot.get("peer_ready"))
    earnings_ready = bool(snapshot.get("earnings_ready"))
    estimates_ready = bool(snapshot.get("analyst_estimates_ready"))
    command = single_stock_next_command(snapshot)
    route_decision = single_stock_report_data_health_route(
        asset_type=asset_type,
        valuation_status=dcf_status,
        price_ready=price_ready,
        dcf_ready=dcf_status == "ready",
        peer_ready=peer_ready,
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
    )
    route_label = route_decision["route_label"]
    route_stop_rule = route_decision["stop_rule"]

    if not snapshot or snapshot.get("status") == "missing":
        return [
            {
                "kicker": "WHERE AM I",
                "title": f"{ticker} is not in the current readiness view",
                "body": "Previous proof is missing. Refresh universe and readiness outputs before opening ticker-level interpretation.",
                "badges": ["missing", "readiness first"],
                "command": _format_missing(snapshot.get("next_action") if snapshot else "", "make universe-report"),
            },
            {
                "kicker": "STOP RULE",
                "title": "No local row, no interpretation",
                "body": "Do not use a typed ticker as proof. Keep the page blocked until local readiness outputs include the ticker.",
                "badges": ["blocked visible", "no inference"],
                "command": "make readiness",
            },
        ]

    if not price_ready:
        review_now = "Ticker metadata can be checked, but setup, trend, valuation, peer, and optional context stay locked."
        blocked = "Trusted price history is the first required proof before single-stock interpretation."
        handoff = "Open Data Health price lane or run the focus-price proof command before returning here."
    elif monitor_context:
        review_now = "Monitor context can be reviewed from local price, liquidity, and risk outputs."
        blocked = "Operating-company DCF and peer valuation are excluded for this asset type, not missing."
        handoff = "Use Data Health only if source freshness or proof history needs review; otherwise read the monitor report."
    elif dcf_status == "blocked":
        review_now = "Price/setup context can be reviewed; valuation and fundamentals trend panels stay locked."
        blocked = _compact_reason(snapshot.get("dcf_reason"), max_sentences=1, max_chars=150)
        handoff = "Open Data Health fundamentals lane for source review, evidence intake, validate, preview, and apply/skip gates."
    elif dcf_status == "ready" and not peer_ready:
        review_now = "Standalone DCF assumptions and source readiness can be reviewed from trusted local inputs."
        blocked = "Peer-relative valuation remains locked until source-backed peer mappings and peer inputs are ready."
        handoff = "Open Data Health peer lane before treating peer-relative context as available."
    elif not earnings_ready or not estimates_ready:
        review_now = "Core company review is available from trusted price, fundamentals, DCF, and peer inputs."
        blocked = "Earnings and analyst-estimate context stays optional and locked until trusted local rows exist."
        handoff = "Use optional-context worklists only if you have reviewed trusted local source rows."
    else:
        review_now = "Supported single-stock review is available from current trusted local inputs."
        blocked = "No core lock is detected, but source readiness and methodology notes still need review."
        handoff = "Regenerate the Markdown report after any import or refresh before interpreting changed output."

    return [
        {
            "kicker": "ANSWER FIRST",
            "title": f"{ticker} - {state}",
            "body": (
                f"Use now: {review_now} Blocked/context: {blocked} Data Health only if blocked/freshness: {handoff} "
                f"Manual review boundary: {route_stop_rule} "
                "Read this first before detailed review. Previous proof comes from the saved readiness checks. "
                f"Decision context: {decision}."
            ),
            "badges": ["one answer", "local proof"],
            "command": _stock_report_md_command(ticker),
        },
        {
            "kicker": "REVIEW NOW",
            "title": "What this page can support",
            "body": review_now,
            "badges": ["read now", "readiness-gated"],
            "command": _stock_report_md_command(ticker) if price_ready else command,
        },
        {
            "kicker": "BLOCKED / EXCLUDED",
            "title": "What must stay withheld",
            "body": blocked,
            "badges": ["blocked visible", "no inference"],
            "command": command,
        },
        {
            "kicker": "NEXT SAFE STEP",
            "title": "Open Data Health only if blocked",
            "body": (
                f"{handoff} Open {route_label} only for the blocked or freshness question. "
                f"{route_stop_rule} Commands stay in operator details; the dashboard does not run imports or refreshes."
            ),
            "badges": ["manual proof", "manual gate"],
            "command": command,
        },
        {
            "kicker": "STOP RULE",
            "title": "Stop before interpretation",
            "body": "Do not treat locked, partial, or excluded sections as conclusions. Reopen this report only after the matching source-proof gate passes.",
            "badges": ["research only", "proof first"],
            "command": "make readiness",
        },
    ]


def single_stock_one_answer_frame(snapshot: dict[str, object]) -> pd.DataFrame:
    """Return one plain-language Single-Stock answer before command-heavy detail."""

    ticker = _format_missing(snapshot.get("ticker"), "TICKER").upper()
    dcf_status = _format_missing(snapshot.get("dcf_status"), "blocked").lower()
    asset_type = _format_missing(snapshot.get("asset_type"), "").lower()
    price_ready = bool(snapshot.get("price_ready"))
    peer_ready = bool(snapshot.get("peer_ready"))
    earnings_ready = bool(snapshot.get("earnings_ready"))
    estimates_ready = bool(snapshot.get("analyst_estimates_ready"))
    monitor_context = dcf_status == "excluded" or asset_type in {"etf", "index_proxy", "fund"}
    route_decision = single_stock_report_data_health_route(
        asset_type=asset_type,
        valuation_status=dcf_status,
        price_ready=price_ready,
        dcf_ready=dcf_status == "ready",
        peer_ready=peer_ready,
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
    )

    if not snapshot or snapshot.get("status") == "missing":
        use_now = "No local readiness row is available for this ticker yet."
        blocked = "All ticker-level interpretation stays blocked until local readiness outputs include the ticker."
        context = "No context is usable until the ticker appears in readiness outputs."
        next_action = "Refresh universe and readiness outputs before opening ticker-level interpretation."
    elif not price_ready:
        use_now = "Only ticker identity and local row status can be checked."
        blocked = "Setup, trend, valuation, peer, optional context, and metrics stay blocked until trusted price history exists."
        context = "No analysis context should be read before price proof."
        next_action = "Open Data Health price lane before returning to this review."
    elif monitor_context:
        use_now = "Monitor context can be reviewed from local price, liquidity, and risk outputs."
        blocked = "Operating-company DCF and peer valuation are excluded for this asset type."
        context = "Use as market, theme, liquidity, or risk context only."
        next_action = "Use Data Health only if source freshness or proof history needs review."
    elif dcf_status == "blocked":
        use_now = "Price/setup context can be reviewed, but valuation and fundamentals trend panels stay locked."
        blocked = _compact_reason(snapshot.get("dcf_reason"), max_sentences=1, max_chars=150)
        context = "Peer and optional context stay unavailable until core DCF proof is ready."
        next_action = "Open Data Health fundamentals lane before treating valuation as available."
    elif dcf_status == "ready" and not peer_ready:
        use_now = "Standalone DCF assumptions and source readiness can be reviewed from trusted local inputs."
        blocked = "Peer-relative valuation remains locked until source-backed peer mappings and peer inputs are ready."
        context = "Earnings and analyst estimates remain optional until trusted rows exist."
        next_action = "Open Data Health peer lane before treating peer-relative context as available."
    elif not earnings_ready or not estimates_ready:
        use_now = "Core company review is available from trusted price, fundamentals, DCF, and peer inputs."
        blocked = "Earnings and analyst-estimate context stays optional and locked until trusted local rows exist."
        context = "Optional context is context only, never a recommendation."
        next_action = "Use optional-context worklists only if trusted local source rows exist."
    else:
        use_now = "Supported single-stock review is available from current trusted local inputs."
        blocked = "No core lock is detected, but source readiness and methodology notes still need review."
        context = "Recheck proof after any local import or refresh."
        next_action = "Read supported sections, then use Proof History only for evidence review."

    return pd.DataFrame(
        [
            {
                "Ticker": ticker,
                "Use Now": use_now,
                "Still Blocked": blocked,
                "Context Only": context,
                "Next Safe Action": next_action,
                "Review Boundary": route_decision["stop_rule"],
            }
        ],
        columns=[
            "Ticker",
            "Use Now",
            "Still Blocked",
            "Context Only",
            "Next Safe Action",
            "Review Boundary",
        ],
    )


def single_stock_data_health_handoff_cards(snapshot: dict[str, object]) -> list[dict[str, object]]:
    """Return a compact route-focused handoff from one ticker back to Data Health."""

    ticker = _format_missing(snapshot.get("ticker"), "TICKER").upper()
    state = _public_status_label(snapshot.get("status"))
    dcf_status = _format_missing(snapshot.get("dcf_status"), "blocked").lower()
    asset_type = _format_missing(snapshot.get("asset_type"), "").lower()
    price_ready = bool(snapshot.get("price_ready"))
    peer_ready = bool(snapshot.get("peer_ready"))
    earnings_ready = bool(snapshot.get("earnings_ready"))
    estimates_ready = bool(snapshot.get("analyst_estimates_ready"))
    monitor_context = dcf_status == "excluded" or asset_type in {"etf", "index_proxy", "fund"}
    command = single_stock_next_command(snapshot)
    route_decision = single_stock_report_data_health_route(
        asset_type=asset_type,
        valuation_status=dcf_status,
        price_ready=price_ready,
        dcf_ready=dcf_status == "ready",
        peer_ready=peer_ready,
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
    )
    route_label = route_decision["route_label"]
    route = route_decision["route"]
    stop_rule = route_decision["stop_rule"]

    if not snapshot or snapshot.get("status") == "missing":
        route_label = "Universe and readiness refresh"
        route = "?mode=operator&page=data-health&drawer=queue"
        command = _format_missing(snapshot.get("next_action") if snapshot else "", "make universe-report")
        current_read = "No local readiness row is available for this ticker yet."
        blocked_state = "All ticker-level interpretation stays blocked until local readiness outputs include the ticker."
        stop_rule = "Stop until the ticker appears in local readiness outputs."
        badges = ["missing row", "readiness first"]
    elif not price_ready:
        current_read = "Only ticker identity and local row status can be checked."
        blocked_state = "Setup, trend, DCF, peer context, optional context, and metrics stay blocked until trusted price history exists."
        badges = ["prices lane", "first proof"]
    elif monitor_context:
        current_read = "Monitor context can be read from local price, liquidity, and risk rows."
        blocked_state = "Operating-company DCF and peer valuation are excluded for this asset type."
        badges = ["monitor context", "excluded visible"]
    elif dcf_status == "blocked":
        current_read = "Price/setup context can be read, but valuation and fundamentals trend panels stay locked."
        blocked_state = "Fundamentals, shares, market cap, FCF, or DCF inputs need reviewed source proof before interpretation."
        badges = ["fundamentals lane", "source proof"]
    elif dcf_status == "ready" and not peer_ready:
        current_read = "Standalone DCF context can be reviewed from trusted local inputs."
        blocked_state = "Peer-relative context stays blocked until mappings and peer valuation inputs are source-backed."
        badges = ["peers lane", "peer proof"]
    elif not earnings_ready or not estimates_ready:
        current_read = "Core price, fundamentals, DCF, and peer context can be reviewed."
        blocked_state = "Optional earnings and analyst-estimate context remains locked unless trusted local rows exist."
        badges = ["optional lane", "locked context"]
    else:
        current_read = "Supported single-stock sections can be reviewed from current trusted local inputs."
        blocked_state = "If any readiness artifact changed, rebuild proof before interpreting refreshed output."
        badges = ["proof lane", "freshness"]

    return [
        {
            "kicker": "ANSWER FIRST",
            "title": "Use this report first",
            "body": (
                f"Use now: {current_read} Blocked: {blocked_state} "
                f"Next proof: open Data Health only for {route_label}. "
                "Proof History is evidence review, not a second report."
            ),
            "badges": ["one path", "details collapsed"],
            "command": _stock_report_md_command(ticker),
        },
        {
            "kicker": "CURRENT REPORT",
            "title": f"{ticker}: {state}",
            "body": f"What can be reviewed now: {current_read}",
            "badges": ["selected ticker", "review scope"],
            "command": _stock_report_md_command(ticker),
        },
        {
            "kicker": "LOCKED INPUTS",
            "title": "Keep blocked sections visible",
            "body": blocked_state,
            "badges": ["blocked visible", "no inference"],
            "command": command,
        },
        {
            "kicker": "OPEN DATA HEALTH",
            "title": route_label,
            "body": (
                f"Use {route} to continue the readiness loop in the matching lane answer. "
                "This is a manual proof path; the dashboard does not write canonical data."
            ),
            "badges": badges,
            "command": command,
        },
        {
            "kicker": "STOP RULE",
            "title": "Return only after proof changes",
            "body": f"{stop_rule} Do not turn missing, partial, locked, or excluded inputs into conclusions.",
            "badges": ["research only", "proof first"],
            "command": "make readiness",
        },
    ]


def single_stock_workflow_command_rows(cards: list[dict[str, object]]) -> list[dict[str, str]]:
    """Return collapsed command rows for the single-stock workflow drawer."""

    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for card in cards:
        command = _format_missing(card.get("command"), "")
        if not command:
            continue
        step = _format_missing(card.get("kicker"), "Workflow step")
        key = (step, command)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "Step": step,
                "Command": command,
                "Boundary": "Copy-only; the dashboard does not run imports, refreshes, or proof writes.",
            }
        )
    return rows


def _coverage_dataset_row(coverage: pd.DataFrame, dataset: str) -> pd.Series | None:
    if coverage.empty or "dataset" not in coverage.columns:
        return None
    matches = coverage.loc[coverage["dataset"].astype(str).str.strip().str.lower().eq(dataset)]
    if matches.empty:
        return None
    return matches.iloc[0]


def _coverage_row_present(row: pd.Series | None) -> bool:
    if row is None:
        return False
    value = row.get("ticker_present", False)
    return str(value).strip().lower() in {"true", "1", "yes"}


def single_stock_pre_report_contract_cards(
    ticker: str,
    coverage: pd.DataFrame,
    peer_summary: dict[str, object],
    *,
    report_open: bool = False,
) -> list[dict[str, object]]:
    """Return a compact pre-click readiness contract for the selected ticker."""

    ticker_text = _format_missing(ticker, "TICKER").upper()
    price_row = _coverage_dataset_row(coverage, "prices")
    fundamentals_row = _coverage_dataset_row(coverage, "fundamentals")
    peer_row = _coverage_dataset_row(coverage, "peers")
    price_ready = _coverage_row_present(price_row)
    fundamentals_ready = _coverage_row_present(fundamentals_row)
    peer_ready = _coverage_row_present(peer_row) and bool(peer_summary.get("peer_dataset_present"))
    available_datasets = (
        0
        if coverage.empty
        else int(
            coverage.get("ticker_present", pd.Series(dtype=object))
            .astype(str)
            .str.lower()
            .isin({"true", "1", "yes"})
            .sum()
        )
    )
    peer_count = int(peer_summary.get("peer_count") or 0)

    if not price_ready:
        state_title = "Price proof comes first"
        review_now = (
            "The open review can show local ticker status, but price-backed sections stay locked until price rows are trusted."
            if report_open
            else "Only ticker identity and local row status should be reviewed before price history is trusted."
        )
        blocked = "Setup, trend, DCF, peer, optional context, and review metrics stay locked until price rows are ready."
        stop_rule = "Stop if price rows are missing, stale, rejected, or not tied to the selected ticker."
        next_command = _ticker_focus_command("prices", ticker_text, fallback=f"make price-refresh TICKERS={ticker_text}")
        next_lane = "Data Health price lane"
        badges = ["price first", "blocked"]
    elif not fundamentals_ready:
        state_title = "Price context ready; fundamentals gated"
        review_now = (
            "Read the price-backed sections in the open review; DCF and fundamentals trend panels stay unavailable."
            if report_open
            else "Local price context can be reviewed, but DCF and fundamentals trend panels stay unavailable."
        )
        blocked = "Trusted fundamentals, shares, FCF, market cap, and valuation inputs remain source-proof work."
        stop_rule = "Stop if fundamentals, shares, market cap, FCF, or valuation inputs would be inferred or placeholder-backed."
        next_command = (
            _preferred_row_command(
                fundamentals_row,
                _ticker_focus_command("fundamentals", ticker_text, fallback=f"make sec-stage TICKERS={ticker_text}"),
            )
            if fundamentals_row is not None
            else _ticker_focus_command("fundamentals", ticker_text, fallback=f"make sec-stage TICKERS={ticker_text}")
        )
        next_lane = "Data Health fundamentals lane"
        badges = ["price ready", "fundamentals gated"]
    elif not peer_ready:
        state_title = "Core inputs present; peer context gated"
        review_now = (
            "Read the supported price and fundamentals sections in the open review; peer-relative context remains gated."
            if report_open
            else "Price and fundamentals context can be reviewed before opening the full review."
        )
        blocked = "Peer-relative context stays unavailable until source-backed mappings and peer inputs exist."
        stop_rule = "Stop if peer mappings or peer valuation inputs lack source-backed rows."
        next_command = (
            _preferred_row_command(
                peer_row,
                _ticker_focus_command("peers", ticker_text, fallback="make peer-mapping-queue TOP_N=25"),
            )
            if peer_row is not None
            else _ticker_focus_command("peers", ticker_text, fallback="make peer-mapping-queue TOP_N=25")
        )
        next_lane = "Data Health peers lane"
        badges = ["core review", "peer gated"]
    else:
        state_title = "Ready to open the review"
        review_now = (
            "Read the supported price, fundamentals, and peer sections in the open review; optional locked sections stay labeled."
            if report_open
            else "The selected ticker has price, fundamentals, and peer setup context available for the review."
        )
        blocked = "Optional earnings, analyst estimates, or metric families may still be locked inside the report."
        stop_rule = "Stop if readiness changed after a local import, refresh, or proof update; rebuild the report first."
        next_command = _stock_report_md_command(ticker_text)
        next_lane = "Single-Stock Report"
        badges = ["open report", "proof first"]

    return [
        {
            "kicker": "SELECTED TICKER",
            "title": f"{ticker_text}: {state_title}",
            "body": (
                f"{available_datasets} local data source row(s) are present before the review opens. "
                f"Peer mappings: {peer_count}. Start here, then read the supported sections only."
            ),
            "badges": ["selected ticker", "data coverage"],
            "command": _stock_report_md_command(ticker_text),
        },
        {
            "kicker": "REVIEW NOW",
            "title": "What can be read in the open review" if report_open else "What can be reviewed before opening details",
            "body": review_now,
            "badges": (["open review", "readiness-gated"] if report_open else ["before review", "readiness-gated"]),
        },
        {
            "kicker": "BLOCKED / EXCLUDED",
            "title": "What must not be inferred",
            "body": blocked,
            "badges": ["blocked visible", "no inference"],
        },
        {
            "kicker": "NEXT STEP",
            "title": next_lane,
            "body": (
                f"Use this as the one next path for this ticker. Stop rule: {stop_rule} "
                "The dashboard does not run imports, refreshes, or proof writes."
            ),
            "badges": badges,
            "command": next_command,
        },
    ]
