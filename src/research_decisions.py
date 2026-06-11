from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.loader import normalize_columns
from src.paths import format_path_context, resolve_data_dir, resolve_outputs_dir, resolve_project_root
from src.readiness_engine import build_ticker_readiness_report


DECISION_COLUMNS = [
    "ticker",
    "name",
    "asset_type",
    "exchange",
    "sector",
    "industry",
    "theme",
    "decision_bucket",
    "decision_subtype",
    "decision_boundary",
    "confidence",
    "main_reason",
    "primary_blocker",
    "supporting_features",
    "blocked_features",
    "excluded_features",
    "missing_data",
    "next_action",
    "next_best_action",
    "data_readiness_score",
    "readiness_score",
    "data_confidence",
    "evaluation_status",
    "purpose_fit",
    "setup_quality",
    "valuation_view",
    "risk_view",
    "missing_data_summary",
    "next_research_step",
    "source_freshness_summary",
    "analysis_score",
    "decision_score",
    "purpose_thesis",
    "purpose_alignment",
    "setup_evaluation",
    "valuation_evaluation",
    "supported_analysis",
    "unsupported_analysis",
    "risk_watchpoint",
    "invalidation_condition",
    "next_research_question",
    "review_priority_reason",
    "confidence_explanation",
    "feature_summary",
    "updated_at",
    "Reason",
]

CORE_COMPANY_BLOCKERS = {"fundamentals", "dcf"}


def _now() -> str:
    return pd.Timestamp.now(tz="UTC").isoformat()


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    frame.columns = normalize_columns(list(frame.columns))
    if "ticker" in frame.columns:
        frame["ticker"] = frame["ticker"].astype("string").str.upper().str.strip()
    return frame


def _split_features(value: Any) -> list[str]:
    if value is None:
        return []
    try:
        if pd.isna(value):
            return []
    except (TypeError, ValueError):
        pass
    text = str(value or "").strip()
    if not text or text.lower() in {"nan", "none", "null", "<na>"}:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def _score_features(ready: list[str], partial: list[str], blocked: list[str], excluded: list[str]) -> float:
    possible = len(ready) + len(partial) + len(blocked)
    if possible <= 0:
        return 0.0
    score = (len(ready) + 0.45 * len(partial)) / possible
    if blocked:
        score *= max(0.35, 1 - 0.07 * len(blocked))
    if excluded and not ready:
        score *= 0.8
    return round(float(max(0, min(score, 1))), 3)


def _data_confidence_label(score: float) -> str:
    if score >= 0.8:
        return "high"
    if score >= 0.55:
        return "medium"
    if score >= 0.25:
        return "low"
    return "blocked"


def _primary_blocker(blocked: list[str], missing_data: Any) -> str:
    blocked_set = set(blocked)
    missing_text = str(missing_data or "").lower()
    if "price" in blocked_set:
        return "price"
    if {"fundamentals", "dcf"} & blocked_set or any(
        token in missing_text
        for token in ("free_cash_flow", "shares_outstanding", "revenue", "fcf_margin", "fundamental")
    ):
        return "fundamentals"
    if "peer" in blocked_set or "peer" in missing_text:
        return "peers"
    if "price" in missing_text:
        return "price"
    if "earnings" in blocked_set:
        return "earnings"
    if "analyst_estimates" in blocked_set:
        return "analyst_estimates"
    if blocked:
        return blocked[0]
    return "none"


def _decision_subtype(
    bucket: str,
    asset_type: str,
    ready: list[str],
    partial: list[str],
    blocked: list[str],
    excluded: list[str],
    primary_blocker: str,
) -> str:
    blocked_set = set(blocked)
    partial_set = set(partial)
    peer_limited = primary_blocker == "peers" or bool({"peer", "peers"} & (blocked_set | partial_set))
    if bucket == "Monitor" and asset_type in {"etf", "index_proxy", "fund"}:
        return "Monitor - ETF Market Proxy"
    if bucket == "Monitor" and ("price" in ready or "momentum" in ready):
        return "Monitor - Price/Momentum Ready"
    if bucket == "Research Now" and "dcf" in ready and peer_limited:
        return "Research Candidate - DCF Ready But Peer Blocked"
    if bucket == "Research Now" and (
        primary_blocker in {"earnings", "analyst_estimates", "optional_context"}
        or bool({"earnings", "analyst_estimates"} & blocked_set)
        and not bool({"price", "fundamentals", "dcf", "peer"} & blocked_set)
    ):
        return "Research Candidate - Optional Context Locked"
    if bucket == "Research Now":
        return "Research Candidate - Core Data Ready"
    if bucket == "Blocked by Data":
        labels = {
            "price": "Blocked by Data - Missing Price",
            "fundamentals": "Blocked by Data - Missing Fundamentals",
            "peers": "Blocked by Data - Missing Peer Mapping",
            "earnings": "Blocked by Data - Missing Optional Context",
            "analyst_estimates": "Blocked by Data - Missing Optional Context",
        }
        return labels.get(primary_blocker, "Blocked by Data - Missing Required Inputs")
    if bucket == "Excluded" and "dcf" in excluded:
        return "Excluded - DCF Not Applicable"
    return bucket


def _feature_summary(ready: list[str], partial: list[str], blocked: list[str], excluded: list[str]) -> str:
    parts = [
        f"ready: {', '.join(ready) or '-'}",
        f"partial: {', '.join(partial) or '-'}",
        f"blocked: {', '.join(blocked) or '-'}",
        f"excluded: {', '.join(excluded) or '-'}",
    ]
    return "; ".join(parts)


def _price_unlock_guidance(ticker: str) -> str:
    return (
        f"Start with make focus-price TICKER={ticker}, then run make price-refresh-loop DRY_RUN=1 "
        "to preview the missing-only capped batch plan. If remote data is unavailable, stage verified OHLCV rows "
        "in data/imports/prices.csv and run make price-validate, make price-preview, and make price-apply."
    )


def _decision_next_action(ticker: str, primary_blocker: str, next_action: Any) -> str:
    text = _text_value(next_action, "")
    if primary_blocker == "price":
        if text and "price-refresh-loop dry_run=1" in text.lower() and "price-validate" in text.lower():
            return text
        prefix = f"{text.rstrip('.')}." if text else f"Unlock trusted price history for {ticker}."
        return f"{prefix} {_price_unlock_guidance(ticker)}"
    if primary_blocker == "peers":
        lowered = text.lower()
        if text and (
            "mapped peer" in lowered
            or "price history" in lowered
            or "peer fundamentals" in lowered
            or "dcf-ready fundamentals" in lowered
        ):
            if "price history" in lowered and "price-refresh-loop dry_run=1" not in lowered:
                return (
                    f"{text.rstrip('.')}. Start with make focus-peers TICKER={ticker}; "
                    "then run make price-refresh-loop DRY_RUN=1 to preview a capped missing-only price plan "
                    "for mapped peers, or stage verified peer OHLCV rows in data/imports/prices.csv and run "
                    "make price-validate, make price-preview, and make price-apply."
                )
            return text
        return (
            f"Add at least 2 source-backed peer mappings for {ticker} in data/imports/peers.csv; "
            "then run make imports-validate, make imports-preview, and make imports-apply."
        )
    if primary_blocker in {"earnings", "analyst_estimates", "optional_context"}:
        return (
            f"Optional context for {ticker} stays locked unless trusted local earnings or analyst-estimate rows exist; "
            "use make templates, make import-earnings or make import-analyst-estimates, then run "
            "make imports-validate, make imports-preview, and make imports-apply."
        )
    if primary_blocker == "fundamentals":
        prefix = f"{text.rstrip('.')}." if text else f"Complete trusted fundamentals and DCF inputs for {ticker}."
        return (
            f"{prefix} Inspect make focus-fundamentals TICKER={ticker}; use make sec-stage TICKERS={ticker} "
            "when SEC_USER_AGENT is configured or stage trusted manual rows in data/imports/fundamentals.csv; "
            "then run make imports-validate, make imports-preview, make imports-apply, make dcf-readiness, and make readiness "
            "before reading DCF output."
        )
    return text


def _decision_boundary(bucket: str, subtype: str, primary_blocker: str, asset_type: str) -> str:
    if bucket == "Research Now":
        if "Peer Blocked" in subtype:
            return (
                "Workflow state only: core company and DCF review can continue, but peer-relative valuation "
                "stays locked until trusted peer mappings and peer valuation inputs are available."
            )
        if "Optional Context Locked" in subtype:
            return (
                "Workflow state only: core research can continue, but earnings and analyst-estimate context "
                "stays locked until trusted optional rows are imported."
            )
        return (
            "Workflow state only: ready for deeper manual research using supported local evidence; "
            "not a final conclusion or instruction."
        )
    if bucket == "Monitor":
        if asset_type in {"etf", "index_proxy", "fund"}:
            return (
                "Monitor context only: useful for market, theme, liquidity, or risk review; "
                "operating-company DCF and peer-relative company valuation are excluded."
            )
        return (
            "Monitor context only: price or momentum context can be reviewed, but deeper company evaluation "
            "waits for missing trusted inputs."
        )
    if bucket == "Blocked by Data":
        blocker = primary_blocker if primary_blocker and primary_blocker != "none" else "required inputs"
        return (
            f"Missing-data proof state: {blocker} blocks evaluation, so valuation conclusions and thesis-level "
            "interpretation stay withheld."
        )
    if bucket == "Excluded":
        return (
            "Method-exclusion state: this analysis is intentionally omitted for the ticker or asset type, "
            "not treated as a failed calculation."
        )
    return "Review state only: use readiness, blockers, and source readiness before drawing a conclusion."


def _text_value(value: Any, fallback: str = "Not available") -> str:
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


def _purpose_value(asset_type: str, watch_row: pd.Series) -> str:
    return _text_value(
        watch_row.get("primarypurpose"),
        "ETF / Defensive / Hedge" if asset_type in {"etf", "index_proxy", "fund"} else "Research candidate",
    )


def _purpose_family(purpose: str, asset_type: str) -> str:
    normalized = purpose.lower()
    if asset_type in {"etf", "index_proxy", "fund"} or "etf" in normalized or "hedge" in normalized or "defensive" in normalized:
        return "etf_hedge"
    if "momentum" in normalized:
        return "momentum"
    if "pullback" in normalized:
        return "pullback"
    if "compounder" in normalized or "core" in normalized:
        return "compounder"
    if "re-rating" in normalized or "undervalued" in normalized or "value" in normalized:
        return "rerating"
    if "speculative" in normalized or "optionality" in normalized:
        return "speculative"
    if "broken" in normalized or "avoid" in normalized:
        return "broken"
    return "general"


def _purpose_thesis(asset_type: str, watch_row: pd.Series, ready: list[str], blocked: list[str]) -> str:
    purpose = _purpose_value(asset_type, watch_row)
    family = _purpose_family(purpose, asset_type)
    final_state = _text_value(watch_row.get("finalstate"), "readiness gated")
    if asset_type in {"etf", "index_proxy", "fund"}:
        return f"Purpose: {purpose}. Evaluate as market, theme, liquidity, or risk context; operating-company valuation remains excluded."
    if family == "momentum":
        return f"Purpose: {purpose}. Judge the brief through trend, relative strength, extension risk, and setup quality; current state is {final_state}."
    if family == "compounder":
        return f"Purpose: {purpose}. Test whether trend, fundamentals, and DCF support the long-duration thesis; current state is {final_state}."
    if family == "speculative":
        return f"Purpose: {purpose}. Treat the brief as high-uncertainty research; price, volatility, and data gaps matter before thesis quality."
    if family == "rerating":
        return f"Purpose: {purpose}. Require fundamentals, DCF, and peer context before any re-rating interpretation is supported."
    if family == "pullback":
        return f"Purpose: {purpose}. Evaluate pullback quality only when price and momentum data support setup context; current state is {final_state}."
    if family == "broken":
        return f"Purpose: {purpose}. Treat the row as thesis-review context and data triage, not a transaction instruction."
    if "dcf" in ready and "fundamentals" in ready:
        return f"Purpose: {purpose}. Current setup is {final_state}; available data supports a research brief, not a recommendation."
    if {"fundamentals", "dcf"} & set(blocked):
        return f"Purpose: {purpose}. Thesis cannot be evaluated fully until trusted fundamentals and DCF inputs are complete."
    return f"Purpose: {purpose}. Current setup is {final_state}; interpretation is limited to ready local features."


def _purpose_alignment(asset_type: str, watch_row: pd.Series, ready: list[str], blocked: list[str]) -> str:
    purpose = _purpose_value(asset_type, watch_row)
    family = _purpose_family(purpose, asset_type)
    final_state = _text_value(watch_row.get("finalstate"), "")
    review_state = _text_value(watch_row.get("reviewstate"), "")
    setup = _text_value(watch_row.get("setupstatus"), "")
    reason = _text_value(watch_row.get("reason"), "")
    reason_lower = reason.lower()
    if "price" in blocked:
        return f"Purpose alignment for {purpose} cannot be checked until usable price history exists."
    if asset_type in {"etf", "index_proxy", "fund"}:
        return f"Purpose alignment: {purpose} is evaluated as market/risk context when price, liquidity, and correlation data are ready; operating-company valuation is not applicable."
    if family == "momentum" and ("weak rs" in reason_lower or "relative strength is weak" in reason_lower):
        return f"Purpose alignment needs review: {purpose} requires relative strength support, but saved research views flag weak relative strength."
    if family == "compounder" and ("broken" in final_state.lower() or "trend is broken" in reason_lower or "below the 50sma" in reason_lower):
        return f"Purpose alignment needs review: {purpose} depends on durable thesis support, but saved research views flag trend/thesis conflict. {reason}"
    if family == "rerating" and ("dcf" in blocked or "fundamentals" in blocked or "peer" in blocked):
        return f"Purpose alignment is blocked: {purpose} requires valuation inputs, but missing fundamentals, DCF, or peer context prevents a supported re-rating read."
    if family == "compounder" and ("fundamentals" in blocked or "dcf" in blocked):
        setup_note = f" Current setup `{setup}` can be reviewed as price/setup context only." if setup and setup != "Not available" else ""
        return (
            f"Purpose alignment is not confirmed: {purpose} requires trusted fundamentals and DCF evidence, "
            f"but those inputs are still blocked.{setup_note}"
        )
    if family == "speculative" and "price" not in ready:
        return f"Purpose alignment for {purpose} is not testable until price, liquidity, and volatility context are available."
    if final_state in {"Broken", "Review Thesis", "Risk Reduce"} or review_state in {"Broken", "Review Thesis", "Risk Reduce"}:
        context = reason if reason != "Not available" else f"final state is {final_state or review_state}"
        return f"Purpose alignment needs review: saved research views show `{final_state or review_state}` for {purpose}. {context}"
    if "marked as" in reason_lower or "conflict" in reason_lower or "but trend" in reason_lower:
        return f"Purpose alignment needs review: {reason}"
    if setup and setup != "Not available":
        return f"Purpose alignment appears consistent with current setup `{setup}` for {purpose}, subject to the missing-data limits below."
    return f"Purpose alignment is not fully testable yet for {purpose}; use the ready features and blocker list before interpreting thesis quality."


def _setup_evaluation(watch_row: pd.Series, ready: list[str], blocked: list[str]) -> str:
    purpose = _purpose_value("company", watch_row)
    family = _purpose_family(purpose, "company")
    setup = _text_value(watch_row.get("setupstatus"), "Not available")
    final_state = _text_value(watch_row.get("finalstate"), "Not available")
    rank_reason = _text_value(watch_row.get("rankreason"), "")
    if "price" in blocked:
        return "Setup cannot be evaluated because usable price history is missing."
    if setup != "Not available":
        suffix = f" {rank_reason}" if rank_reason else ""
        if family == "momentum":
            return f"Momentum setup: {setup}; final state: {final_state}. Check relative strength, trend, volume context, and extension risk before deeper research.{suffix}".strip()
        if family == "pullback":
            return f"Pullback setup: {setup}; final state: {final_state}. Confirm price support and momentum stabilization before treating the setup as research-ready.{suffix}".strip()
        if family == "compounder":
            if final_state in {"Broken", "Review Thesis", "Risk Reduce"}:
                return f"Compounder setup: {setup}; final state: {final_state}. Trend conflict matters because it can challenge the stated long-duration purpose.{suffix}".strip()
            return f"Compounder setup: {setup}; final state: {final_state}. Track trend quality alongside fundamentals and DCF before treating the long-duration thesis as well supported.{suffix}".strip()
        return f"Setup status: {setup}; final state: {final_state}.{suffix}".strip()
    if "momentum" in ready:
        return "Momentum is ready, but setup detail is not available in the current watchlist output."
    return "Setup interpretation is unavailable until price and momentum inputs are ready."


def _valuation_evaluation(asset_type: str, watch_row: pd.Series, ready: list[str], blocked: list[str], excluded: list[str]) -> str:
    valuation_status = _text_value(watch_row.get("valuationstatus"), "Not available")
    value_category = _text_value(watch_row.get("finalvaluecategory"), "Not available")
    peer_status = _text_value(watch_row.get("peerrelativestatus"), "Not available")
    if asset_type in {"etf", "index_proxy", "fund"} or "dcf" in excluded:
        return "Operating-company DCF is excluded for this asset type; use market/risk context instead of valuation conclusions."
    if "dcf" in ready:
        if value_category.lower() == "insufficient data" or peer_status.lower() in {"insufficient peer data", "peer data unavailable"}:
            return f"DCF inputs are ready, but valuation interpretation is constrained by {value_category} and peer status `{peer_status}`."
        return f"Valuation status: {valuation_status}; value category: {value_category}; peer context: {peer_status}."
    if "dcf" in blocked or "fundamentals" in blocked:
        return "Valuation conclusion is blocked until trusted DCF/fundamental inputs are complete."
    return "Valuation interpretation is not supported by the saved research views."


def _supported_analysis(bucket: str, asset_type: str, ready: list[str], partial: list[str], excluded: list[str]) -> str:
    supported: list[str] = []
    if "price" in ready:
        supported.append("price history")
    if "momentum" in ready:
        supported.append("setup and momentum context")
    if "market_direction" in ready:
        supported.append("market/theme context")
    if "liquidity" in ready:
        supported.append("liquidity context")
    if "correlation" in ready:
        supported.append("correlation/risk context")
    if asset_type not in {"etf", "index_proxy", "fund"} and "fundamentals" in ready:
        supported.append("fundamental context")
    if asset_type not in {"etf", "index_proxy", "fund"} and "dcf" in ready:
        supported.append("standalone DCF scenario analysis")
    if "peer" in ready:
        supported.append("peer-relative comparison")
    if asset_type in {"etf", "index_proxy", "fund"} or "dcf" in excluded:
        supported.append("ETF/index monitoring, not operating-company valuation")
    if not supported:
        return "Supported analysis: none yet; this row is a data-proof checklist until core inputs are available."
    partial_text = f" Partial inputs present: {', '.join(partial)}." if partial else ""
    return f"Supported analysis: {', '.join(supported)}.{partial_text}"


def _purpose_supported_analysis(asset_type: str, watch_row: pd.Series, ready: list[str]) -> str:
    purpose = _purpose_value(asset_type, watch_row)
    family = _purpose_family(purpose, asset_type)
    if family == "momentum" and {"price", "momentum"} <= set(ready):
        return "Purpose-specific support: momentum review can use trend, setup, and relative-strength context, while valuation remains secondary."
    if family == "compounder" and "fundamentals" in ready and "dcf" in ready:
        return "Purpose-specific support: compounder review can use fundamentals and standalone DCF, but thesis quality still depends on trend and source readiness."
    if family == "etf_hedge" and "price" in ready:
        return "Purpose-specific support: ETF/hedge review can use market, theme, liquidity, and correlation context; company valuation is excluded."
    if family == "speculative" and "price" in ready:
        return "Purpose-specific support: speculative review can use price and volatility context, but missing fundamentals keep thesis quality uncertain."
    if family == "rerating" and "dcf" in ready and "fundamentals" in ready:
        return "Purpose-specific support: re-rating review can use standalone DCF/fundamentals, but peer and optional context still constrain interpretation."
    if family == "pullback" and {"price", "momentum"} <= set(ready):
        return "Purpose-specific support: pullback review can use setup, price support, and momentum stabilization context."
    if family == "broken":
        return "Purpose-specific support: no-setup thesis-review rows support thesis review and blocker diagnosis only."
    return ""


def _unsupported_analysis(asset_type: str, watch_row: pd.Series, blocked: list[str], excluded: list[str]) -> str:
    purpose = _purpose_value(asset_type, watch_row)
    family = _purpose_family(purpose, asset_type)
    unsupported: list[str] = []
    if "price" in blocked:
        unsupported.append("trend, setup, liquidity, volatility, and relative strength")
    if "fundamentals" in blocked:
        unsupported.append("fundamental quality and operating-company valuation")
    if "dcf" in blocked:
        unsupported.append("DCF interpretation")
    if "peer" in blocked:
        unsupported.append("peer-relative valuation or opportunity-cost comparison")
    if "earnings" in blocked:
        unsupported.append("earnings timing or surprise context")
    if "analyst_estimates" in blocked:
        unsupported.append("analyst estimate trend context")
    if asset_type in {"etf", "index_proxy", "fund"} or "dcf" in excluded:
        unsupported.append("operating-company DCF conclusions")
    if family == "momentum" and ("price" in blocked or "momentum" in blocked):
        unsupported.append("momentum leadership assessment")
    if family == "compounder" and ("fundamentals" in blocked or "dcf" in blocked):
        unsupported.append("compounder thesis confirmation")
    if family == "rerating" and ("fundamentals" in blocked or "dcf" in blocked or "peer" in blocked):
        unsupported.append("re-rating or undervaluation conclusion")
    if family == "pullback" and ("price" in blocked or "momentum" in blocked):
        unsupported.append("pullback setup quality")
    if family == "speculative" and "price" in blocked:
        unsupported.append("speculative setup and volatility read")
    if not unsupported:
        return "Currently withheld: no major locked analysis areas are listed, but conclusions still depend on source readiness and assumptions."
    return f"Currently withheld: {', '.join(dict.fromkeys(unsupported))}."


def _risk_watchpoint(asset_type: str, watch_row: pd.Series, ready: list[str], blocked: list[str]) -> str:
    purpose = _purpose_value(asset_type, watch_row)
    family = _purpose_family(purpose, asset_type)
    final_state = _text_value(watch_row.get("finalstate"), "")
    setup = _text_value(watch_row.get("setupstatus"), "")
    reason = _text_value(watch_row.get("reason"), "")
    if "price" in blocked:
        return "Primary risk is analytical blindness from missing price history; do not interpret trend or volatility yet."
    if family == "momentum":
        return "Risk watchpoint: momentum purpose is sensitive to relative-strength deterioration, extension risk, and trend breaks."
    if family == "compounder" and final_state in {"Broken", "Review Thesis", "Risk Reduce"}:
        return f"Risk watchpoint: compounder purpose is under thesis review because final state is `{final_state}`. {reason}".strip()
    if family == "speculative":
        return "Risk watchpoint: speculative optionality has high uncertainty; missing fundamentals, volatility context, or liquidity gaps reduce interpretability."
    if family == "rerating":
        return "Risk watchpoint: re-rating analysis can overclaim when DCF, peer, or optional context is incomplete."
    if family == "pullback":
        return "Risk watchpoint: pullback purpose depends on support holding and momentum stabilizing; unsupported setup reads should stay locked."
    if family == "broken":
        return "Risk watchpoint: no-setup purpose is a thesis-review label, not a transaction instruction."
    if final_state in {"Broken", "Risk Reduce", "Review Thesis"}:
        return f"Risk watchpoint: final state is `{final_state}`. {reason}".strip()
    if setup == "Extended":
        return "Risk watchpoint: setup is extended; do not over-interpret momentum without a pullback or consolidation context."
    if asset_type in {"etf", "index_proxy", "fund"}:
        return "Risk watchpoint: monitor liquidity, correlation, and theme exposure; company-specific DCF does not apply."
    if "peer" in blocked:
        return "Risk watchpoint: peer-relative context is incomplete, so valuation comparison and opportunity cost remain uncertain."
    return "Risk watchpoint: monitor setup deterioration, valuation-input quality, and missing optional context."


def _invalidation_condition(asset_type: str, watch_row: pd.Series, ready: list[str], blocked: list[str]) -> str:
    purpose = _purpose_value(asset_type, watch_row)
    family = _purpose_family(purpose, asset_type)
    final_state = _text_value(watch_row.get("finalstate"), "")
    if "price" in blocked:
        return "Invalidation cannot be defined from local price data until price history is available."
    if final_state == "Broken":
        return "Already invalidated for trend/purpose review in the saved setup state."
    if asset_type in {"etf", "index_proxy", "fund"}:
        return "Invalidate market-proxy usefulness if liquidity, correlation, or theme trend no longer supports the intended monitoring role."
    if family == "momentum":
        return "Invalidate the momentum research setup if relative strength weakens, trend support fails, or extension risk dominates the setup."
    if family == "compounder":
        return "Invalidate the compounder thesis review if trend conflict persists and updated fundamentals/DCF no longer support the stated purpose."
    if family == "speculative":
        return "Invalidate speculative research framing if price/liquidity context is missing or the setup cannot be distinguished from data noise."
    if family == "rerating":
        return "Invalidate any re-rating interpretation until fundamentals, DCF assumptions, and peer context are complete enough to support it."
    if family == "pullback":
        return "Invalidate pullback setup framing if price support fails or momentum does not stabilize after the pullback."
    if family == "broken":
        return "Keep no-setup thesis-review rows in thesis-review mode until data and setup evidence justify a different research classification."
    if "momentum" in ready:
        return "Invalidate the current setup if price support fails, relative strength deteriorates, or the watchlist final state turns Broken."
    return "Invalidate only after the missing core inputs are available; current data is insufficient for a setup-level condition."


def _next_research_question(
    watch_row: pd.Series,
    bucket: str,
    asset_type: str,
    primary_blocker: str,
    ready: list[str],
    partial: list[str],
    blocked: list[str],
) -> str:
    purpose = _purpose_value(asset_type, watch_row)
    family = _purpose_family(purpose, asset_type)
    peer_limited = "peer" in blocked or "peer" in partial or primary_blocker == "peers"
    if bucket == "Research Now":
        if family == "momentum":
            return "Does relative strength, trend quality, and extension risk still support the momentum purpose after reviewing the latest local price context?"
        if family == "compounder":
            return "Do trend, fundamentals, DCF assumptions, and thesis conflict notes still support the compounder purpose?"
        if family == "rerating":
            return "Are DCF assumptions, peer context, and missing valuation fields sufficient before considering a re-rating thesis?"
        if peer_limited:
            return "Which source-backed peers and peer metrics would confirm or challenge the standalone DCF and setup read?"
        return "Do purpose, setup, valuation assumptions, and risk watchpoints agree enough to justify deeper manual research?"
    if bucket == "Monitor" and asset_type in {"etf", "index_proxy", "fund"}:
        return "What market, sector, or hedge signal is this proxy intended to monitor, and is that signal still supported by local price/risk data?"
    if primary_blocker == "price":
        if family == "speculative":
            return "Can trusted price rows be added so speculative optionality can be separated from missing-data noise?"
        return "Can trusted local price rows be added before interpreting setup, risk, or relative strength?"
    if primary_blocker == "fundamentals":
        if family == "compounder":
            return "Which trusted fundamentals or DCF fields are needed to confirm whether the compounder thesis remains supported?"
        if family == "rerating":
            return "Which trusted fundamentals, DCF fields, or peer inputs are missing before a re-rating read is supportable?"
        return "Which trusted fundamentals or DCF fields are missing, and can SEC staging or manual import fill them?"
    if primary_blocker == "peers":
        return "Which source-backed peer mappings or peer metrics are needed before peer-relative analysis is shown?"
    if primary_blocker in {"earnings", "analyst_estimates", "optional_context"}:
        return "Is there trusted local earnings or estimate data worth importing, or should optional context remain locked?"
    return "Which missing input most improves the next supported research read?"


def _review_priority_reason(
    bucket: str,
    subtype: str,
    primary_blocker: str,
    asset_type: str,
    watch_row: pd.Series,
    ready: list[str],
    partial: list[str],
    blocked: list[str],
) -> str:
    purpose = _purpose_value(asset_type, watch_row)
    family = _purpose_family(purpose, asset_type)
    final_state = _text_value(watch_row.get("finalstate"), "")
    score = _text_value(watch_row.get("watchlistscore"), "")
    if family == "momentum" and bucket == "Research Now":
        return "High review priority: momentum purpose has enough core data for trend/relative-strength review, but confirm setup quality manually."
    if family == "compounder" and final_state in {"Broken", "Review Thesis", "Risk Reduce"}:
        return "High review priority: compounder purpose conflicts with current trend/thesis state and needs manual thesis review."
    if family == "rerating" and ("peer" in blocked or "fundamentals" in blocked or "dcf" in blocked):
        return "Proof priority: re-rating purpose is valuation-gated until fundamentals, DCF, and peer context are sufficiently complete."
    if family == "speculative" and "price" in blocked:
        return "Proof priority: speculative optionality cannot be evaluated until trusted price history exists."
    if family == "pullback" and ("price" in blocked or "momentum" in blocked):
        return "Proof priority: pullback purpose requires price and momentum context before setup quality can be reviewed."
    if family == "broken":
        return "Review priority: no-setup purpose should remain thesis-review context until readiness supports a different classification."
    if bucket == "Research Now" and ("peer" in blocked or "peer" in partial):
        return "High review priority: core company data is ready, but peer-relative context is still limiting valuation interpretation."
    if bucket == "Research Now":
        return f"High review priority: core data supports a research brief for {purpose}; confirm assumptions, setup, and risk notes manually."
    if bucket == "Monitor" and asset_type in {"etf", "index_proxy", "fund"}:
        return "Monitor priority: use this proxy for market, theme, liquidity, or risk context; do not treat it as operating-company valuation."
    if bucket == "Blocked by Data" and "price" not in blocked and "price" in ready:
        return f"Proof priority: price context exists, but {primary_blocker} blocks deeper analysis."
    if bucket == "Blocked by Data":
        return f"Proof priority: {primary_blocker} is the first blocker before setup, valuation, or risk interpretation should be trusted."
    if final_state != "Not available":
        suffix = f" with watchlist score {score}" if score != "Not available" else ""
        return f"Review priority is current-state driven: final state `{final_state}`{suffix}; use readiness before drawing conclusions."
    return f"Review priority follows `{subtype}` and the current readiness blockers."


def _confidence_explanation(bucket: str, data_label: str, primary_blocker: str, ready: list[str], blocked: list[str], excluded: list[str]) -> str:
    if bucket == "Research Now":
        return f"Data confidence is {data_label}: core price, fundamentals, and DCF are ready; blockers still reduce breadth: {', '.join(blocked) or 'none'}."
    if bucket == "Monitor":
        return f"Data confidence is {data_label}: monitoring is supported by {', '.join(ready) or 'limited ready features'}, while {', '.join(blocked) or 'no blocked features'} remains unavailable."
    if bucket == "Blocked by Data":
        return f"Data confidence is {data_label}: primary blocker is {primary_blocker}; blocked features are {', '.join(blocked) or 'not specified'}."
    if bucket == "Excluded":
        return f"Data confidence is {data_label}: excluded features are {', '.join(excluded) or 'not specified'}, so unsupported analysis is intentionally omitted."
    return f"Data confidence is {data_label}: current readiness does not support a stronger classification."


def _evaluation_status(bucket: str, subtype: str, primary_blocker: str, asset_type: str) -> str:
    if bucket == "Research Now":
        return "Ready for a supported research brief; manual thesis review still required."
    if bucket == "Monitor":
        if asset_type in {"etf", "index_proxy", "fund"}:
            return "Ready for market, theme, liquidity, or risk monitoring; operating-company valuation is excluded."
        return "Price-supported monitoring is available; deeper research waits for the missing inputs."
    if bucket == "Blocked by Data":
        return f"Not ready for evaluation; prove {primary_blocker} coverage before drawing a thesis-level conclusion."
    if bucket == "Excluded":
        return f"Analysis is intentionally excluded for this ticker or asset type: {subtype}."
    return "Review later; current local data does not support a stronger evaluation state."


def _purpose_fit_view(asset_type: str, watch_row: pd.Series, ready: list[str], blocked: list[str]) -> str:
    alignment = _purpose_alignment(asset_type, watch_row, ready, blocked)
    if "needs review" in alignment.lower():
        return f"Purpose fit needs review: {alignment}"
    if "blocked" in alignment.lower() or "cannot be checked" in alignment.lower() or "not testable" in alignment.lower():
        return f"Purpose fit locked by data: {alignment}"
    return f"Purpose fit: {alignment}"


def _setup_quality_view(watch_row: pd.Series, ready: list[str], blocked: list[str]) -> str:
    setup = _setup_evaluation(watch_row, ready, blocked)
    if "cannot be evaluated" in setup.lower() or "unavailable" in setup.lower():
        return f"Setup quality unavailable: {setup}"
    if "extended" in setup.lower() or "broken" in setup.lower() or "review thesis" in setup.lower():
        return f"Setup quality needs review: {setup}"
    return f"Setup quality: {setup}"


def _valuation_view(asset_type: str, watch_row: pd.Series, ready: list[str], blocked: list[str], excluded: list[str]) -> str:
    text = _valuation_evaluation(asset_type, watch_row, ready, blocked, excluded)
    if asset_type in {"etf", "index_proxy", "fund"} or "dcf" in excluded:
        return f"Valuation view: DCF excluded, not failed. {text}"
    if "blocked" in text.lower() or "not supported" in text.lower():
        return f"Valuation view: blocked until trusted inputs are ready. {text}"
    if "constrained" in text.lower():
        return f"Valuation view: partial. {text}"
    return f"Valuation view: {text}"


def _risk_view(asset_type: str, watch_row: pd.Series, ready: list[str], blocked: list[str]) -> str:
    return _risk_watchpoint(asset_type, watch_row, ready, blocked)


def _missing_data_summary(blocked: list[str], excluded: list[str], missing_data: Any) -> str:
    missing = _text_value(missing_data, "")
    if blocked:
        detail = f"Blocked inputs: {', '.join(blocked)}."
        if missing:
            detail += f" Detail: {missing}."
        return detail
    if excluded:
        return f"Excluded analyses: {', '.join(excluded)}. These are omitted intentionally, not inferred."
    return "No major missing required inputs are listed by the current readiness report."


def _source_freshness_summary(row: pd.Series) -> str:
    updated = _text_value(row.get("updated_at"), "not available")
    return f"Based on current local CSV readiness outputs; readiness row updated {updated}. Verify source readiness before relying on stale imported data."


def build_research_decisions_frame(readiness: pd.DataFrame, final_watchlist: pd.DataFrame | None = None) -> pd.DataFrame:
    final_watchlist = final_watchlist if final_watchlist is not None else pd.DataFrame()
    if not final_watchlist.empty:
        final_watchlist = final_watchlist.copy()
        final_watchlist.columns = normalize_columns(list(final_watchlist.columns))
    if not final_watchlist.empty and "ticker" in final_watchlist.columns:
        final_watchlist["ticker"] = final_watchlist["ticker"].astype("string").str.upper().str.strip()
        watch_lookup = final_watchlist.set_index("ticker", drop=False)
    else:
        watch_lookup = pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for _, row in readiness.iterrows():
        ticker = str(row.get("ticker") or "").upper().strip()
        if not ticker:
            continue
        ready = _split_features(row.get("ready_features"))
        partial = _split_features(row.get("partial_features"))
        blocked = _split_features(row.get("blocked_features"))
        excluded = _split_features(row.get("excluded_features"))
        asset_type = str(row.get("asset_type") or "unknown").lower()
        company_like = asset_type in {"company", "adr", "preferred", "unknown", "other"}
        core_company_blockers = sorted(CORE_COMPANY_BLOCKERS & set(blocked))
        watch_row = watch_lookup.loc[ticker] if not watch_lookup.empty and ticker in watch_lookup.index else pd.Series(dtype=object)
        if isinstance(watch_row, pd.DataFrame):
            watch_row = watch_row.iloc[-1]
        analysis_score = pd.to_numeric(pd.Series([watch_row.get("watchlistscore")]), errors="coerce").iloc[0] if not watch_row.empty else pd.NA
        analysis_score_normalized = 0.0 if pd.isna(analysis_score) else min(max(float(analysis_score) / 100.0, 0), 1)
        data_score = _score_features(ready, partial, blocked, excluded)
        primary_blocker = _primary_blocker(blocked, row.get("missing_data", ""))

        if "price" in blocked:
            bucket = "Blocked by Data"
            main_reason = "Missing usable price data."
        elif asset_type in {"etf", "index_proxy", "fund"} and "price" in ready:
            bucket = "Monitor"
            main_reason = f"{asset_type} is usable for market/risk monitoring and excluded from company DCF."
        elif "dcf" in excluded and not ready:
            bucket = "Excluded"
            main_reason = "Ticker is excluded from the relevant company analysis."
        elif company_like and core_company_blockers:
            bucket = "Blocked by Data"
            main_reason = f"Company research is blocked by missing {', '.join(core_company_blockers)} data."
        elif asset_type == "company" and "momentum" in ready and "dcf" in ready and "fundamentals" in ready:
            bucket = "Research Now"
            main_reason = "Core data is ready for a supported research pass."
        elif "momentum" in ready or "price" in ready:
            bucket = "Monitor"
            main_reason = "Price-supported monitoring is available, but deeper data is still partial or blocked."
        elif blocked:
            bucket = "Blocked by Data"
            main_reason = "Required research data is missing."
        else:
            bucket = "Review Later"
            main_reason = "Ticker is known but not currently supported by enough analysis-ready data."

        if bucket == "Monitor" and asset_type in {"etf", "index_proxy", "fund"}:
            if "peer" in blocked:
                primary_blocker = "peers"
            elif "earnings" in blocked or "analyst_estimates" in blocked:
                primary_blocker = "optional_context"
            else:
                primary_blocker = "none"

        if bucket == "Research Now":
            confidence = min(0.9, 0.55 * data_score + 0.45 * analysis_score_normalized)
        elif bucket == "Monitor":
            confidence = min(0.75, 0.65 * data_score + 0.25 * analysis_score_normalized)
        elif bucket == "Blocked by Data":
            confidence = min(0.45, 0.2 + 0.15 * data_score)
        elif bucket == "Excluded":
            confidence = 0.7
        else:
            confidence = min(0.55, 0.3 + 0.2 * data_score)
        decision_score = round(float(confidence) * 100, 1)
        subtype = _decision_subtype(bucket, asset_type, ready, partial, blocked, excluded, primary_blocker)
        raw_next_action = row.get("next_action", "")
        next_action = _decision_next_action(ticker, primary_blocker, raw_next_action)
        data_confidence = _data_confidence_label(data_score)
        purpose_fit = _purpose_fit_view(asset_type, watch_row, ready, blocked)
        setup_quality = _setup_quality_view(watch_row, ready, blocked)
        valuation_view = _valuation_view(asset_type, watch_row, ready, blocked, excluded)
        risk_view = _risk_view(asset_type, watch_row, ready, blocked)
        next_research_step = _next_research_question(watch_row, bucket, asset_type, primary_blocker, ready, partial, blocked)
        rows.append(
            {
                "ticker": ticker,
                "name": row.get("name", ""),
                "asset_type": asset_type,
                "exchange": row.get("exchange", ""),
                "sector": row.get("sector", ""),
                "industry": row.get("industry", ""),
                "theme": row.get("theme", ""),
                "decision_bucket": bucket,
                "decision_subtype": subtype,
                "decision_boundary": _decision_boundary(bucket, subtype, primary_blocker, asset_type),
                "confidence": round(float(confidence), 3),
                "main_reason": main_reason,
                "primary_blocker": primary_blocker,
                "supporting_features": ", ".join(ready),
                "blocked_features": row.get("blocked_features", ""),
                "excluded_features": row.get("excluded_features", ""),
                "missing_data": row.get("missing_data", ""),
                "next_action": next_action,
                "next_best_action": next_action,
                "data_readiness_score": data_score,
                "readiness_score": data_score,
                "data_confidence": data_confidence,
                "evaluation_status": _evaluation_status(bucket, subtype, primary_blocker, asset_type),
                "purpose_fit": purpose_fit,
                "setup_quality": setup_quality,
                "valuation_view": valuation_view,
                "risk_view": risk_view,
                "missing_data_summary": _missing_data_summary(blocked, excluded, row.get("missing_data", "")),
                "next_research_step": next_research_step,
                "source_freshness_summary": _source_freshness_summary(row),
                "analysis_score": round(float(analysis_score_normalized), 3),
                "decision_score": decision_score,
                "purpose_thesis": _purpose_thesis(asset_type, watch_row, ready, blocked),
                "purpose_alignment": _purpose_alignment(asset_type, watch_row, ready, blocked),
                "setup_evaluation": _setup_evaluation(watch_row, ready, blocked),
                "valuation_evaluation": _valuation_evaluation(asset_type, watch_row, ready, blocked, excluded),
                "supported_analysis": " ".join(
                    part
                    for part in [
                        _supported_analysis(bucket, asset_type, ready, partial, excluded),
                        _purpose_supported_analysis(asset_type, watch_row, ready),
                    ]
                    if part
                ),
                "unsupported_analysis": _unsupported_analysis(asset_type, watch_row, blocked, excluded),
                "risk_watchpoint": _risk_watchpoint(asset_type, watch_row, ready, blocked),
                "invalidation_condition": _invalidation_condition(asset_type, watch_row, ready, blocked),
                "next_research_question": next_research_step,
                "review_priority_reason": _review_priority_reason(bucket, subtype, primary_blocker, asset_type, watch_row, ready, partial, blocked),
                "confidence_explanation": _confidence_explanation(bucket, data_confidence, primary_blocker, ready, blocked, excluded),
                "feature_summary": _feature_summary(ready, partial, blocked, excluded),
                "updated_at": _now(),
                "Reason": main_reason,
            }
        )
    return pd.DataFrame(rows, columns=DECISION_COLUMNS)


def write_research_decisions(
    base_dir: Path | str | None = None,
    *,
    data_dir: Path | str | None = None,
    output_dir: Path | str | None = None,
) -> pd.DataFrame:
    root = resolve_project_root(base_dir)
    data_path = resolve_data_dir(data_dir, root)
    output_path = resolve_outputs_dir(output_dir, root)
    reports = build_ticker_readiness_report(root, data_dir=data_path, output_dir=output_path)
    readiness = reports["ticker_readiness_report"]
    final_watchlist = _read_csv(output_path / "final_watchlist.csv")
    decisions = build_research_decisions_frame(readiness, final_watchlist)
    data_output = data_path / "outputs" / "research_decisions.csv"
    output_copy = output_path / "research_decisions.csv"
    data_output.parent.mkdir(parents=True, exist_ok=True)
    output_path.mkdir(parents=True, exist_ok=True)
    decisions.to_csv(data_output, index=False)
    decisions.to_csv(output_copy, index=False)
    return decisions


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate readiness-aware ticker research decisions.")
    parser.add_argument("--project-root", help="Project root. Defaults to this repository.")
    parser.add_argument("--data-dir", help="Optional data directory. Relative paths resolve from project root.")
    parser.add_argument("--output-dir", help="Optional output directory. Relative paths resolve from project root.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = resolve_project_root(args.project_root)
    data_path = resolve_data_dir(args.data_dir, root)
    output_path = resolve_outputs_dir(args.output_dir, root)
    decisions = write_research_decisions(root, data_dir=data_path, output_dir=output_path)
    payload = {
        "status": "written",
        "rows": len(decisions),
        "data_output": str(data_path / "outputs" / "research_decisions.csv"),
        "output_copy": str(output_path / "research_decisions.csv"),
        "buckets": decisions["decision_bucket"].value_counts().to_dict() if not decisions.empty else {},
    }
    if args.json:
        print(json.dumps(payload, indent=2))
        return
    print(format_path_context(root, data_path, output_path))
    for key, value in payload.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
