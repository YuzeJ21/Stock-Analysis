from __future__ import annotations

import math
import re


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
    if isinstance(value, float) and math.isnan(value):
        return fallback
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "<na>"}:
        return fallback
    return text


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
            "kicker": "WHERE AM I",
            "title": f"{ticker} - {state}",
            "body": f"Decision context: {decision}. Previous proof comes from the saved readiness row and report payload.",
            "badges": ["selected ticker", "local proof"],
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
            "title": "Where Data Health fits",
            "body": f"{handoff} The next command is copy-only; the dashboard does not run imports or refreshes.",
            "badges": ["copy only", "manual gate"],
            "command": command,
        },
        {
            "kicker": "STOP RULE",
            "title": "Stop before interpretation",
            "body": "Do not treat locked, partial, or excluded sections as conclusions. Reopen this report only after the matching proof command passes.",
            "badges": ["research only", "proof first"],
            "command": "make readiness",
        },
    ]
