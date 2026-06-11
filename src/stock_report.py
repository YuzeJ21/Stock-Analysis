from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from src.indicators import compute_return
from src.providers.market_data import (
    AnalystEstimateSummary,
    EarningsSummary,
    FinancialSnapshot,
    MarketDataProvider,
    QuoteSnapshot,
    make_source_metadata,
)
from src.providers.local_market_data import LocalCSVMarketDataProvider
from src.providers.local_importer import apply_import_merge, preview_import_merge, validate_imports
from src.providers.local_templates import write_import_staging_files, write_local_data_templates
from src.providers.mock_market_data import MockMarketDataProvider
from src.providers.sec_companyfacts import build_sec_fundamentals_rows, write_sec_fundamentals_import
from src.paths import format_path_context, resolve_data_dir, resolve_outputs_dir, resolve_project_root
from src.valuation import ValuationInput, ValuationResult, build_valuation_result


@dataclass
class PerformanceSummary:
    one_month: float | None
    three_month: float | None
    one_year: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DataFreshnessNote:
    provider: str
    freshness: str
    retrieved_at: str
    official: bool
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StockReport:
    ticker: str
    generated_at: str
    provider_name: str
    price_snapshot: dict[str, Any]
    performance: PerformanceSummary
    financial_summary: dict[str, Any]
    valuation_snapshot: dict[str, Any]
    earnings_summary: dict[str, Any]
    analyst_estimate_summary: dict[str, Any]
    key_risks: list[str]
    missing_data_warnings: list[str]
    data_freshness: list[DataFreshnessNote]
    valuation_readiness: dict[str, Any] = field(default_factory=dict)
    dataset_coverage: list[dict[str, Any]] = field(default_factory=list)
    local_data_validation: list[dict[str, Any]] = field(default_factory=list)
    screener_context: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "generated_at": self.generated_at,
            "provider_name": self.provider_name,
            "price_snapshot": self.price_snapshot,
            "performance": self.performance.to_dict(),
            "financial_summary": self.financial_summary,
            "valuation_snapshot": self.valuation_snapshot,
            "earnings_summary": self.earnings_summary,
            "analyst_estimate_summary": self.analyst_estimate_summary,
            "key_risks": self.key_risks,
            "missing_data_warnings": self.missing_data_warnings,
            "data_freshness": [note.to_dict() for note in self.data_freshness],
            "valuation_readiness": self.valuation_readiness,
            "dataset_coverage": self.dataset_coverage,
            "local_data_validation": self.local_data_validation,
            "screener_context": self.screener_context,
        }


def _metadata_from_source(source) -> DataFreshnessNote:
    return DataFreshnessNote(
        provider=source.provider,
        freshness=source.freshness,
        retrieved_at=source.retrieved_at,
        official=source.official,
        notes=list(source.notes),
    )


def _clean_number(value: float | int | None) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


FIELD_LABELS = {
    "analyst_estimates": "analyst estimates",
    "correlation": "correlation",
    "dcf": "DCF",
    "earnings": "earnings",
    "fundamentals": "fundamentals",
    "liquidity": "liquidity",
    "market_direction": "market direction",
    "momentum": "momentum",
    "peer": "peer",
    "portfolio": "portfolio",
    "DebtToEquity": "debt to equity",
    "ebitda": "EBITDA",
    "EPSGrowth": "EPS growth",
    "EVToEBITDA": "EV/EBITDA",
    "EVToSales": "EV/sales",
    "FCFYield": "FCF yield",
    "ForwardPE": "forward P/E",
    "GrossMargin": "gross margin",
    "PE": "P/E",
    "P/E": "P/E",
    "PriceToFCF": "price to free cash flow",
    "fcf_margin": "FCF margin",
    "free_cash_flow": "free cash flow",
    "market_cap_or_price_and_shares": "market cap, price, and share count",
    "analyst_estimates": "analyst estimates",
    "earnings": "earnings",
    "pe": "P/E",
    "p/e": "P/E",
    "p_fcf": "price/free-cash-flow",
    "ps": "price/sales",
    "price": "price",
    "revenue": "revenue",
    "shares_outstanding": "shares outstanding",
}


def _display_field_name(value: Any) -> str:
    text = _display_value(value, "")
    if not text:
        return "missing field"
    if text in FIELD_LABELS:
        return FIELD_LABELS[text]
    normalized = text.strip().strip("`.,;:")
    if normalized in FIELD_LABELS:
        return FIELD_LABELS[normalized]
    if "_" in normalized:
        return normalized.replace("_", " ")
    spaced = re.sub(r"(?<!^)(?=[A-Z][a-z])", " ", normalized)
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", spaced)
    return spaced.lower() if spaced else text


def _format_inline_make_commands(text: str) -> str:
    """Render bare make commands in prose as inline copyable commands."""
    simple_targets = {
        "coverage",
        "daily",
        "dashboard",
        "demo",
        "monthly",
        "onboarding",
        "pipeline",
        "readiness",
        "templates",
        "test",
        "verify",
    }
    command_pattern = re.compile(
        r"(?<!`)\bmake\s+(?P<target>[A-Za-z0-9_-]+)(?P<args>(?:\s+[A-Z_]+=[A-Za-z0-9_:/.-]+)*)(?!`)"
    )

    def wrap_if_make_target(match: re.Match[str]) -> str:
        target = match.group("target")
        if "-" not in target and target not in simple_targets:
            return match.group(0)
        return f"`{match.group(0)}`"

    return command_pattern.sub(wrap_if_make_target, text)


def _humanize_schema_terms(value: Any) -> str:
    text = _display_value(value)
    if text == "Not available":
        return text
    for raw, label in sorted(FIELD_LABELS.items(), key=lambda item: len(item[0]), reverse=True):
        text = re.sub(rf"(?<![A-Za-z0-9_]){re.escape(raw)}(?![A-Za-z0-9_])", label, text)
    text = text.replace("make DCF-", "make dcf-")
    text = text.replace("missing DCF", "missing DCF")
    return _format_inline_make_commands(text)


def _display_field_list(value: Any, fallback: str = "Not available") -> str:
    if value is None:
        return fallback
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return fallback
        prefix = ""
        lowered = text.lower()
        if lowered.startswith("missing "):
            prefix = "missing "
            text = text[8:].strip()
        parts = [part.strip() for part in re.split(r"[,;]", text) if part.strip()]
        if not parts:
            return fallback
        return prefix + ", ".join(_display_field_name(part) for part in parts)
    if isinstance(value, (list, tuple, set)):
        parts = [_display_field_name(part) for part in value if _display_value(part, "")]
        return ", ".join(parts) if parts else fallback
    return _humanize_schema_terms(value)


def _display_report_list(value: Any, empty_label: str = "none") -> str:
    text = _humanize_schema_terms(_display_value(value, ""))
    if not text or text == "Not available":
        return empty_label
    return text


def _performance_from_history(history: pd.DataFrame) -> PerformanceSummary:
    if history.empty or "close" not in history.columns:
        return PerformanceSummary(one_month=None, three_month=None, one_year=None)

    closes = pd.to_numeric(history["close"], errors="coerce").dropna()
    return PerformanceSummary(
        one_month=_clean_number(compute_return(closes, 21)),
        three_month=_clean_number(compute_return(closes, 63)),
        one_year=_clean_number(compute_return(closes, 252)),
    )


def _build_risks(
    performance: PerformanceSummary,
    financials: FinancialSnapshot,
    earnings: EarningsSummary,
    estimates: AnalystEstimateSummary,
) -> list[str]:
    risks: list[str] = []

    if performance.one_year is None:
        risks.append("1Y price performance is unavailable.")
    elif performance.one_year < 0:
        risks.append("1Y price performance is negative.")

    if financials.free_cash_flow is None:
        risks.append("Free-cash-flow coverage is unavailable.")
    elif financials.free_cash_flow < 0:
        risks.append("Free cash flow is negative.")

    if financials.operating_margin is None:
        risks.append("Operating margin coverage is unavailable.")
    elif financials.operating_margin < 0:
        risks.append("Operating margin is negative.")

    if financials.net_debt is not None and financials.net_debt > 0:
        risks.append("Net debt is positive and should be reviewed against cash-flow durability.")

    if earnings.next_earnings_date is None:
        risks.append("Next earnings date is unavailable.")

    if estimates.current_quarter_eps is None and estimates.current_quarter_revenue is None:
        risks.append("Analyst estimate coverage is limited.")

    return risks


def _build_missing_data_warnings(
    performance: PerformanceSummary,
    financials: FinancialSnapshot,
    earnings: EarningsSummary,
    estimates: AnalystEstimateSummary,
    dataset_coverage: list[dict[str, Any]],
    valuation: ValuationResult,
) -> list[str]:
    warnings: list[str] = []
    core_datasets = {"prices", "fundamentals", "earnings", "analyst_estimates"}
    if performance.one_month is None:
        warnings.append("1M performance is unavailable from the current local price history.")
    if performance.three_month is None:
        warnings.append("3M performance is unavailable from the current local price history.")
    if performance.one_year is None:
        warnings.append("1Y performance is unavailable from the current local price history.")
    if financials.revenue is None:
        warnings.append("Revenue is unavailable from the current local fundamentals dataset.")
    if financials.eps is None:
        warnings.append("EPS is unavailable from the current local fundamentals dataset.")
    if financials.free_cash_flow is None:
        warnings.append("Free cash flow is unavailable from the current local fundamentals dataset.")
    warnings.extend(earnings.notes)
    warnings.extend(estimates.notes)
    warnings.extend(valuation.warnings)
    warnings.extend(valuation.relative_valuation.peer_missing_data_warnings)
    warnings.extend([f"Valuation missing field: {_display_field_name(field)}" for field in valuation.missing_fields])
    for row in dataset_coverage:
        if row.get("dataset_name") in core_datasets and not row.get("ticker_present"):
            warnings.append(f"{_display_field_name(row['dataset_name'])} has no local row for this ticker.")
    return sorted(set(warnings))


def _price_snapshot_dict(quote: QuoteSnapshot) -> dict[str, Any]:
    return {
        "ticker": quote.ticker,
        "price": quote.price,
        "previous_close": quote.previous_close,
        "open": quote.open,
        "day_high": quote.day_high,
        "day_low": quote.day_low,
        "volume": quote.volume,
        "currency": quote.currency,
        "market_time": quote.market_time,
        "source": quote.source.to_dict(),
    }


def _financial_summary_dict(financials: FinancialSnapshot) -> dict[str, Any]:
    return {
        "revenue": financials.revenue,
        "revenue_growth": financials.revenue_growth,
        "eps": financials.eps,
        "gross_margin": financials.gross_margin,
        "operating_margin": financials.operating_margin,
        "profit_margin": financials.profit_margin,
        "free_cash_flow": financials.free_cash_flow,
        "fcf_margin": financials.fcf_margin,
        "ebitda": financials.ebitda,
        "market_cap": financials.market_cap,
        "enterprise_value": financials.enterprise_value,
        "trailing_pe": financials.trailing_pe,
        "forward_pe": financials.forward_pe,
        "price_to_book": financials.price_to_book,
        "shares_outstanding": financials.shares_outstanding,
        "cash": financials.cash,
        "debt": financials.debt,
        "net_debt": financials.net_debt,
        "debt_to_equity": financials.debt_to_equity,
        "currency": financials.currency,
        "as_of_date": financials.as_of_date,
        "source": financials.source.to_dict() if financials.source else None,
    }


def _valuation_snapshot_dict(result: ValuationResult) -> dict[str, Any]:
    return result.to_dict()


def _valuation_readiness_dict(
    valuation: ValuationResult,
    earnings: EarningsSummary,
    estimates: AnalystEstimateSummary,
    peer_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    dcf_missing = list(valuation.dcf_result.missing_fields)
    relative_missing = list(valuation.relative_valuation.missing_fields)
    return {
        "dcf_ready": valuation.dcf_result.status == "calculated",
        "relative_ready": valuation.relative_valuation.status in {"calculated", "partial", "peer_data_unavailable"},
        "peer_ready": valuation.relative_valuation.status in {"calculated", "partial"},
        "peer_count": valuation.relative_valuation.peer_count,
        "peer_group": valuation.relative_valuation.peer_group,
        "peer_tickers": valuation.relative_valuation.peer_tickers,
        "peer_relative_status": valuation.relative_valuation.peer_relative_status,
        "peer_missing_data_warnings": list(valuation.relative_valuation.peer_missing_data_warnings),
        "earnings_available": any(
            value is not None
            for value in (
                earnings.next_earnings_date,
                earnings.last_earnings_date,
                earnings.eps_estimate,
                earnings.eps_actual,
                earnings.revenue_estimate,
                earnings.revenue_actual,
            )
        ),
        "analyst_estimates_available": any(
            value is not None
            for value in (
                estimates.current_quarter_eps,
                estimates.next_quarter_eps,
                estimates.current_year_eps,
                estimates.next_year_eps,
                estimates.target_mean_price,
            )
        ),
        "dcf_missing_fields": dcf_missing,
        "relative_missing_fields": relative_missing,
        "peer_summary": peer_summary or {},
        "notes": [
            "DCF readiness requires either direct free cash flow or revenue plus FCF margin.",
            "Peer-relative readiness requires local peers plus enough peer fundamentals to form median multiples.",
        ],
    }


def build_stock_report(ticker: str, provider: MarketDataProvider) -> StockReport:
    ticker = ticker.upper()
    quote = provider.get_quote(ticker)
    history = provider.get_price_history(ticker, period="1y", interval="1d")
    financials = provider.get_financials(ticker)
    earnings = provider.get_earnings(ticker)
    estimates = provider.get_analyst_estimates(ticker)

    performance = _performance_from_history(history)
    data_freshness = [_metadata_from_source(quote.source)]
    if financials.source:
        data_freshness.append(_metadata_from_source(financials.source))
    if earnings.source:
        data_freshness.append(_metadata_from_source(earnings.source))
    if estimates.source:
        data_freshness.append(_metadata_from_source(estimates.source))

    dataset_coverage = provider.get_ticker_dataset_coverage(ticker) if hasattr(provider, "get_ticker_dataset_coverage") else []
    local_data_validation = provider.get_local_data_validation() if hasattr(provider, "get_local_data_validation") else []
    screener_context = provider.get_screener_context(ticker) if hasattr(provider, "get_screener_context") else {}
    peer_summary = provider.get_peer_summary(ticker) if hasattr(provider, "get_peer_summary") else {}
    valuation = build_valuation_result(
        ValuationInput(
            ticker=ticker,
            current_price=quote.price,
            revenue=financials.revenue,
            revenue_growth=financials.revenue_growth,
            free_cash_flow=financials.free_cash_flow,
            fcf_margin=financials.fcf_margin,
            operating_margin=financials.operating_margin,
            profit_margin=financials.profit_margin,
            eps=financials.eps,
            ebitda=financials.ebitda,
            shares_outstanding=financials.shares_outstanding,
            cash=financials.cash,
            debt=financials.debt,
            net_debt=financials.net_debt,
            market_cap=financials.market_cap,
            trailing_pe=financials.trailing_pe,
            forward_pe=financials.forward_pe,
            price_to_book=financials.price_to_book,
            peer_inputs=provider.get_peer_valuation_inputs(ticker) if hasattr(provider, "get_peer_valuation_inputs") else [],
            source_metadata=[note.to_dict() for note in data_freshness],
            screener_context=screener_context,
        )
    )
    missing_data_warnings = _build_missing_data_warnings(
        performance,
        financials,
        earnings,
        estimates,
        dataset_coverage,
        valuation,
    )

    return StockReport(
        ticker=ticker,
        generated_at=pd.Timestamp.now(tz="UTC").isoformat(),
        provider_name=type(provider).__name__,
        price_snapshot=_price_snapshot_dict(quote),
        performance=performance,
        financial_summary=_financial_summary_dict(financials),
        valuation_snapshot=_valuation_snapshot_dict(valuation),
        earnings_summary=earnings.to_dict(),
        analyst_estimate_summary=estimates.to_dict(),
        key_risks=_build_risks(performance, financials, earnings, estimates),
        missing_data_warnings=missing_data_warnings,
        data_freshness=data_freshness,
        valuation_readiness=_valuation_readiness_dict(valuation, earnings, estimates, peer_summary),
        dataset_coverage=dataset_coverage,
        local_data_validation=local_data_validation,
        screener_context=screener_context,
    )


def export_stock_report_json(report: StockReport, output_path: Path | None = None) -> str:
    payload = json.dumps(report.to_dict(), indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload + "\n", encoding="utf-8")
    return payload


def _display_value(value: Any, fallback: str = "Not available") -> str:
    if value is None:
        return fallback
    if not isinstance(value, (list, tuple, dict, set)) and pd.isna(value):
        return fallback
    text = str(value).strip()
    return fallback if not text or text.lower() in {"nan", "none", "nat", "null"} else text


def _proof_language(value: Any, fallback: str = "Not available") -> str:
    text = _display_value(value, fallback)
    if text == fallback:
        return text
    replacements = {
        "Unlock priority:": "Proof priority:",
        "unlock priority:": "proof priority:",
        "Unlock path:": "Proof path:",
        "unlock path:": "proof path:",
        "an unlock checklist": "a proof checklist",
        "An unlock checklist": "A proof checklist",
        "Unlock checklist": "Proof checklist",
        "unlock checklist": "proof checklist",
        "an proof checklist": "a proof checklist",
        "An proof checklist": "A proof checklist",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _display_setup_text(value: Any, fallback: str = "Not available") -> str:
    text = _display_value(value, fallback)
    replacements = {
        "Extended / No Chase": "Extended",
        "Broken / Avoid": "No Setup / Thesis Review Needed",
        "Broken / No Setup": "No Setup / Thesis Review Needed",
        "current setup `Avoid`": "current setup `No Setup`",
        "setup `Avoid`": "setup `No Setup`",
        "setup: Avoid": "setup: No Setup",
        "Setup status: Avoid": "Setup status: No Setup",
        "Compounder setup: Avoid": "Compounder setup: No Setup",
        "current state is Broken": "current state needs thesis review",
        "final state: Broken": "final state: Thesis Review Needed",
        "final state `Broken`": "final state `Thesis Review Needed`",
        "Final state `Broken`": "Final state `Thesis Review Needed`",
        "Compounder setup: Broken": "Compounder setup: Thesis Review Needed",
        "Setup status: Broken": "Setup status: Thesis Review Needed",
        "ReviewState: Broken": "ReviewState: Thesis Review Needed",
        "reviewstate: Broken": "reviewstate: Thesis Review Needed",
        "Trend is broken": "Trend support failed",
        "trend is broken": "trend support failed",
        "Holding trend is broken": "Holding trend support failed",
        "holding trend is broken": "holding trend support failed",
        "Already invalidated for trend/purpose review": "Already flagged for trend/purpose review",
        "final state is `Broken`": "final state is `Thesis Review Needed`",
        "valuation_status=not_ready": "valuation is not ready",
        "valuation status is not ready": "valuation is not ready",
        "valuation readiness is `not_ready`": "valuation readiness is not ready",
        "treat as monitor-only until missing data is resolved": "treat as data-limited review until missing data is resolved",
        "current state is Ignore": "current state is not prioritized",
        "final state: Ignore": "final state: Not Prioritized",
        "final state `Ignore`": "final state `Not Prioritized`",
        "Ignored names are left unranked": "Not-prioritized names are left unranked",
        "Confidence is ": "Data confidence is ",
        "Confidence is:": "Data confidence is:",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return _humanize_schema_terms(text)


def _display_report_status(value: Any, fallback: str = "not available") -> str:
    if isinstance(value, bool):
        return "ready" if value else "not ready"
    text = _display_setup_text(value, fallback)
    normalized = text.strip().lower()
    replacements = {
        "true": "ready",
        "false": "not ready",
        "monitor_context": "monitor context",
        "blocked_until_fundamentals_dcf": "blocked until fundamentals / DCF",
        "wait_for_core_data": "waiting for price, fundamentals, and DCF",
        "insufficient_data": "insufficient data",
        "peer_data_unavailable": "peer data unavailable",
        "not_ready": "not ready",
    }
    if normalized in replacements:
        return replacements[normalized]
    if "_" in text and text == normalized:
        return text.replace("_", " ")
    return text


def _is_ready_flag(value: Any) -> bool:
    return _display_report_status(value).lower() == "ready"


def _display_dcf_method(value: Any) -> str:
    method = _display_value(value, "")
    labels = {
        "fcf_direct": "direct free cash flow",
        "revenue_fcf_margin": "revenue times FCF margin",
    }
    return labels.get(method, _humanize_schema_terms(method) if method else "not available")


def _sentence_value(value: Any, fallback: str = "Not available") -> str:
    return _format_inline_make_commands(_display_value(value, fallback)).rstrip(".")


def _brief_value(value: Any, *prefixes: str, fallback: str = "Not available") -> str:
    text = _display_value(value, fallback)
    text = text.replace("source/freshness", "source readiness")
    text = text.replace("source freshness", "source readiness")
    for prefix in prefixes:
        if text.lower().startswith(prefix.lower()):
            return text[len(prefix) :].strip()
    return text


def _public_report_brief(value: Any, *prefixes: str, fallback: str = "Not available", max_chars: int = 260) -> str:
    text = _brief_value(value, *prefixes, fallback=fallback)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_chars:
        return text
    first_sentence = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0].strip()
    if len(first_sentence) > max_chars:
        first_sentence = first_sentence[: max_chars - 1].rstrip(" ,;:") + "."
    blocker_match = re.search(r"\bNext blocker:\s*([^.;]+)", text, flags=re.IGNORECASE)
    blocker_suffix = f" Next blocker: {blocker_match.group(1).strip()}." if blocker_match else ""
    withheld_match = re.search(r"\bWithheld:\s*([^.;]+)", text, flags=re.IGNORECASE)
    withheld_suffix = f" Withheld: {withheld_match.group(1).strip()}." if withheld_match else ""
    return (
        f"{first_sentence}{blocker_suffix}{withheld_suffix} "
        "Review the readiness sections below before drawing conclusions."
    )


def _atr_or_volatility_source_label(source: Any) -> str:
    normalized = str(source or "").strip().lower()
    if normalized == "atr":
        return "ATR from high/low/close"
    if normalized == "volatility_proxy":
        return "Volatility proxy approximation"
    return "Volatility source unavailable"


def _stock_report_volatility_lines(payload: dict[str, Any]) -> list[str]:
    momentum = ((payload.get("screener_context") or {}).get("momentum_leaders") or {})
    volatility_value = momentum.get("ATRorVolatilityPct")
    if _display_value(volatility_value) == "Not available":
        return ["- ATR / volatility: Not available; missing values stay visible instead of guessed."]
    source_label = _atr_or_volatility_source_label(momentum.get("ATRorVolatilitySource"))
    if source_label == "Volatility proxy approximation":
        suffix = " This is an approximation from close-to-close volatility because high/low ATR inputs were unavailable."
    elif source_label == "Volatility source unavailable":
        suffix = " Source provenance was not recorded in this saved report; rerun the local workflow to classify ATR versus proxy."
    else:
        suffix = " This comes from the available local OHLC price fields."
    return [f"- ATR / volatility: {_format_pct(volatility_value)} ({source_label}).{suffix}"]


def _source_freshness_summary(item: dict[str, Any]) -> str:
    freshness = _display_value(item.get("freshness"))
    if freshness != "Not available":
        return f"source readiness: {freshness}"
    provider = _display_value(item.get("provider"))
    if provider.startswith("local:"):
        return "source readiness: local file metadata"
    retrieved = _display_value(item.get("retrieved_at"))
    return f"retrieved: {retrieved}"


def _format_pct(value: Any) -> str:
    if value is None:
        return "Not available"
    try:
        if pd.isna(value):
            return "Not available"
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return _display_value(value)


def _format_money(value: Any) -> str:
    if value is None:
        return "Not available"
    try:
        if pd.isna(value):
            return "Not available"
        numeric = float(value)
    except (TypeError, ValueError):
        return _display_value(value)
    return f"${numeric:,.2f}"


def _format_compact_number(value: Any) -> str:
    if value is None:
        return "Not available"
    try:
        if pd.isna(value):
            return "Not available"
        numeric = float(value)
    except (TypeError, ValueError):
        return _display_value(value)
    abs_value = abs(numeric)
    for scale, suffix in ((1_000_000_000_000, "T"), (1_000_000_000, "B"), (1_000_000, "M")):
        if abs_value >= scale:
            return f"{numeric / scale:.1f}{suffix}"
    return f"{numeric:,.0f}"


def _format_compact_money(value: Any) -> str:
    formatted = _format_compact_number(value)
    return formatted if formatted == "Not available" or formatted.startswith("$") else f"${formatted}"


def _has_report_value(value: Any) -> bool:
    return _display_value(value) != "Not available"


def _dcf_input_trace_line(assumptions: dict[str, Any]) -> str:
    base_revenue = _format_compact_money(assumptions.get("base_revenue"))
    base_free_cash_flow = _format_compact_money(assumptions.get("base_free_cash_flow"))
    fcf_margin = _format_pct(assumptions.get("fcf_margin"))
    shares = _format_compact_number(assumptions.get("shares_outstanding"))
    net_debt = assumptions.get("net_debt")
    if _has_report_value(net_debt):
        balance_sheet_adjustment = f"net debt={_format_compact_money(net_debt)}"
    else:
        balance_sheet_adjustment = (
            f"cash={_format_compact_money(assumptions.get('cash'))}; "
            f"debt={_format_compact_money(assumptions.get('debt'))}"
        )
    return (
        "- DCF input trace: "
        f"base revenue={base_revenue}; "
        f"base FCF={base_free_cash_flow}; "
        f"FCF margin={fcf_margin}; "
        f"shares outstanding={shares}; "
        f"balance-sheet adjustment uses {balance_sheet_adjustment}."
    )


def _dcf_sensitivity_snapshot_line(sensitivity: dict[str, Any]) -> str:
    if not isinstance(sensitivity, dict) or _display_value(sensitivity.get("status")).lower() != "calculated":
        return ""
    wacc_values = list(sensitivity.get("wacc_values") or [])
    terminal_growth_values = list(sensitivity.get("terminal_growth_values") or [])
    fair_value_grid = list(sensitivity.get("fair_value_grid") or [])
    if not wacc_values or not terminal_growth_values or not fair_value_grid:
        return ""
    row_index = min(len(wacc_values) // 2, len(fair_value_grid) - 1)
    row_values = fair_value_grid[row_index] if isinstance(fair_value_grid[row_index], list) else []
    cases = []
    for terminal_growth, fair_value in zip(terminal_growth_values[:3], row_values[:3]):
        cases.append(f"TG {_format_pct(terminal_growth)} -> {_format_money(fair_value)}")
    if not cases:
        return ""
    return f"- Sensitivity snapshot: at WACC {_format_pct(wacc_values[row_index])}, " + "; ".join(cases) + "."


def _stock_report_valuation_lines(
    *,
    valuation_snapshot: dict[str, Any],
    valuation_readiness: dict[str, Any],
    dcf: dict[str, Any],
    dcf_status_text: str,
    monitor_context: bool,
) -> list[str]:
    if monitor_context or dcf_status_text.lower() == "excluded":
        return [
            "- DCF applicability: excluded for ETF/index/fund monitor context; this is not a failed valuation input.",
            "- Valuation conclusion: not shown because operating-company DCF and peer valuation do not apply to this monitor role.",
        ]

    dcf_result = valuation_snapshot.get("dcf_result", {}) if isinstance(valuation_snapshot, dict) else {}
    assumptions = dcf_result.get("assumptions", {}) if isinstance(dcf_result, dict) else {}
    sensitivity = valuation_snapshot.get("sensitivity_table", {}) if isinstance(valuation_snapshot, dict) else {}
    relative = valuation_snapshot.get("relative_valuation", {}) if isinstance(valuation_snapshot, dict) else {}
    scenarios = valuation_snapshot.get("scenarios", []) if isinstance(valuation_snapshot, dict) else []
    missing_fields = dcf.get("missing_dcf_fields") or valuation_readiness.get("dcf_missing_fields", [])
    fair_value = dcf_result.get("fair_value_per_share") if isinstance(dcf_result, dict) else None
    scenario_names = [
        _display_value(item.get("name"))
        for item in scenarios
        if isinstance(item, dict) and _display_value(item.get("name")) != "Not available"
    ]
    dcf_is_ready_calculated = dcf_result.get("status") == "calculated" and dcf_status_text.lower() == "ready"
    dcf_status_display = "calculated" if dcf_is_ready_calculated else dcf_status_text
    lines = [
        f"- DCF status: {_display_report_status(dcf_status_display)}.",
    ]
    if dcf_is_ready_calculated:
        lines.extend(
            [
                f"- Base DCF scenario fair value/share: {_format_money(fair_value)}.",
                _dcf_input_trace_line(assumptions),
                (
                    "- Base DCF assumptions: "
                    f"input path={_display_dcf_method(assumptions.get('method_name'))}, "
                    f"revenue growth={_format_pct(assumptions.get('revenue_growth'))}, "
                    f"FCF margin={_format_pct(assumptions.get('fcf_margin'))}, "
                    f"WACC={_format_pct(assumptions.get('wacc'))}, "
                    f"terminal growth={_format_pct(assumptions.get('terminal_growth'))}, "
                    f"forecast years={_display_value(assumptions.get('forecast_years'))}."
                ),
                f"- Scenario coverage: {', '.join(scenario_names) if scenario_names else 'Not available'}.",
                (
                    f"- Sensitivity table: {_display_value(sensitivity.get('status'))}; "
                    "it tests fair value across WACC and terminal-growth assumptions when per-share DCF inputs are ready."
                ),
            ]
        )
        sensitivity_snapshot = _dcf_sensitivity_snapshot_line(sensitivity)
        if sensitivity_snapshot:
            lines.append(sensitivity_snapshot)
    else:
        lines.extend(
            [
                f"- DCF missing inputs: {_display_field_list(missing_fields)}.",
                f"- Why DCF is blocked: {_display_field_list(dcf.get('reason_not_ready'))}.",
            ]
        )
        lines.append("- DCF assumptions: withheld until price, fundamentals, free cash flow or FCF margin, and share-count inputs are ready.")
        lines.append("- Sensitivity table: unavailable until the base DCF can be calculated.")

    relative_status = _display_value(relative.get("status") if isinstance(relative, dict) else None)
    peer_count = _display_value(relative.get("peer_count") if isinstance(relative, dict) else None)
    peer_missing = []
    if isinstance(relative, dict):
        peer_missing = list(relative.get("missing_fields") or []) + list(relative.get("peer_missing_data_warnings") or [])
    relative_status_key = relative_status.lower()
    relative_status_display = _display_report_status(relative_status)
    peer_inputs_missing = peer_count in {"0", "Not available"}
    if dcf_status_text.lower() != "ready":
        lines.append(
            "- Relative valuation: withheld until trusted fundamentals and DCF readiness pass; "
            f"available peer context is held back until the company DCF gate is ready "
            f"(peer status={relative_status_display}; peer count={peer_count})."
        )
    elif relative_status_key in {"insufficient_data", "not available", "peer_data_unavailable"} or peer_inputs_missing:
        lines.append(
            f"- Relative valuation: blocked until trusted peer mappings and peer valuation inputs are ready; "
            f"current status={relative_status_display}; peer count={peer_count}."
        )
    elif relative_status_key == "partial":
        limitation = f" Missing peer valuation fields: {'; '.join(peer_missing)}." if peer_missing else ""
        lines.append(
            f"- Relative valuation: partial from available trusted peer inputs; peer count={peer_count}."
            f"{limitation}"
        )
    elif peer_missing:
        lines.append(
            f"- Relative valuation: {relative_status_display} from trusted peer inputs, with caveats; "
            f"peer count={peer_count}. Missing peer valuation fields: {'; '.join(peer_missing)}."
        )
    else:
        lines.append(f"- Relative valuation: {relative_status_display}; peer count={peer_count}.")
    lines.append("- Valuation conclusion is shown only when trusted DCF and peer inputs support it; missing valuation inputs are not inferred.")
    return lines


def _stock_report_dcf_calculation_path_lines(
    *,
    valuation_snapshot: dict[str, Any],
    valuation_readiness: dict[str, Any],
    dcf: dict[str, Any],
    dcf_status_text: str,
    monitor_context: bool,
) -> list[str]:
    if monitor_context or dcf_status_text.lower() == "excluded":
        return [
            "- State: excluded; operating-company DCF is not the right method for ETF/index/fund monitor context.",
            "- Formula path: not run for this ticker because the asset-type gate excludes company DCF.",
            "- Reader takeaway: use supported market, theme, liquidity, or risk context instead of treating DCF as failed.",
        ]

    dcf_result = valuation_snapshot.get("dcf_result", {}) if isinstance(valuation_snapshot, dict) else {}
    assumptions = dcf_result.get("assumptions", {}) if isinstance(dcf_result, dict) else {}
    sensitivity = valuation_snapshot.get("sensitivity_table", {}) if isinstance(valuation_snapshot, dict) else {}
    missing_fields = dcf.get("missing_dcf_fields") or valuation_readiness.get("dcf_missing_fields", [])
    dcf_is_ready_calculated = dcf_result.get("status") == "calculated" and dcf_status_text.lower() == "ready"

    if not dcf_is_ready_calculated:
        return [
            "- State: blocked; the product withholds DCF math until trusted company inputs pass readiness checks.",
            (
                "- Required local inputs: trusted price, revenue, free cash flow or FCF margin, shares outstanding, "
                "and cash/debt or net-debt context."
            ),
            f"- Missing now: {_display_field_list(missing_fields)}.",
            "- Formula path: withheld before base FCF, projected FCF, terminal value, equity value, or fair value/share are calculated.",
            "- Sensitivity: unavailable until the base DCF can be calculated from trusted inputs.",
        ]

    lines = [
        "- State: ready; standalone DCF math is calculated locally from trusted price and fundamentals inputs.",
        (
            "- Formula path: base FCF -> projected FCF -> discounted FCF plus discounted terminal value -> "
            "enterprise value -> equity value -> fair value per share."
        ),
        (
            "- Input source: local price/fundamentals rows; "
            f"base revenue={_format_compact_money(assumptions.get('base_revenue'))}; "
            f"base FCF={_format_compact_money(assumptions.get('base_free_cash_flow'))}; "
            f"shares outstanding={_format_compact_number(assumptions.get('shares_outstanding'))}."
        ),
        (
            "- Assumptions used: "
            f"revenue growth={_format_pct(assumptions.get('revenue_growth'))}; "
            f"FCF margin={_format_pct(assumptions.get('fcf_margin'))}; "
            f"WACC={_format_pct(assumptions.get('wacc'))}; "
            f"terminal growth={_format_pct(assumptions.get('terminal_growth'))}; "
            f"forecast years={_display_value(assumptions.get('forecast_years'))}."
        ),
        (
            f"- Sensitivity: {_display_value(sensitivity.get('status'))}; "
            "reader should compare WACC and terminal-growth cases before interpreting fair value."
        ),
    ]
    sensitivity_snapshot = _dcf_sensitivity_snapshot_line(sensitivity)
    if sensitivity_snapshot:
        lines.append(sensitivity_snapshot)
    lines.append("- Reader takeaway: this is scenario math and methodology evidence, not a price target or direct recommendation.")
    return lines


DCF_INPUT_TRIAGE = {
    "price": {
        "why": "anchors per-share valuation and lets the report verify market context before deeper company analysis.",
        "path": "run `make focus-price TICKER={ticker}` first, then use the price import validate/preview/apply flow if local rows are missing.",
    },
    "fundamentals": {
        "why": "provides the company row used to connect revenue, cash-flow, balance-sheet, and share-count fields.",
        "path": "run `make focus-fundamentals TICKER={ticker}` and stage SEC or trusted manual rows before import validation.",
    },
    "revenue": {
        "why": "sets the operating scale used for forecast assumptions when direct free cash flow is not enough by itself.",
        "path": "use `make focus-fundamentals TICKER={ticker}`, then `make sec-stage TICKERS={ticker}` or trusted manual fundamentals import.",
    },
    "free_cash_flow": {
        "why": "drives base FCF for projected cash flows; without it the DCF cannot calculate operating cash generation.",
        "path": "add trusted free-cash-flow rows through SEC staging or `data/imports/fundamentals.csv`, then validate and preview.",
    },
    "fcf_margin": {
        "why": "lets the model estimate free cash flow from revenue when direct free cash flow is unavailable.",
        "path": "add a trusted FCF margin or direct free-cash-flow field before rerunning DCF readiness.",
    },
    "shares_outstanding": {
        "why": "converts equity value into fair value per share; missing share count blocks per-share DCF output.",
        "path": "add trusted shares outstanding in the fundamentals import, then run `make imports-validate` and `make dcf-readiness`.",
    },
    "market_cap_or_price_and_shares": {
        "why": "lets the product reconcile market value or per-share inputs before showing valuation context.",
        "path": "refresh trusted price rows and add share-count fundamentals before rerunning readiness.",
    },
}


def _stock_report_dcf_input_triage_lines(
    *,
    ticker: str,
    dcf: dict[str, Any],
    valuation_readiness: dict[str, Any],
    dcf_status_text: str,
    monitor_context: bool,
) -> list[str]:
    if monitor_context or dcf_status_text.lower() == "excluded":
        return [
            "- DCF input triage: not required for ETF/index/fund monitor context; operating-company valuation is excluded rather than repaired.",
        ]
    raw_missing = dcf.get("missing_dcf_fields") or valuation_readiness.get("dcf_missing_fields") or dcf.get("reason_not_ready")
    if dcf_status_text.lower() == "ready":
        return [
            "- DCF input triage: required inputs passed readiness for standalone DCF review.",
            "- Next check: review assumptions, sensitivity, and source readiness; do not convert fair value math into a recommendation.",
        ]
    missing_parts: list[str] = []
    if isinstance(raw_missing, str):
        text = raw_missing.strip()
        if text.lower().startswith("missing "):
            text = text[8:].strip()
        missing_parts = [part.strip().strip("`.,;:") for part in re.split(r"[,;]", text) if part.strip()]
    elif isinstance(raw_missing, (list, tuple, set)):
        missing_parts = [str(part).strip().strip("`.,;:") for part in raw_missing if _display_value(part, "")]

    if not missing_parts:
        missing_parts = ["fundamentals"]

    lines = [
        "- DCF input triage: blocked inputs are repair steps, not negative company signals.",
        "- Calculation dependency: trusted price and share count anchor per-share output; revenue plus free cash flow or FCF margin builds base FCF; cash/debt adjusts enterprise value to equity value.",
    ]
    for raw_field in missing_parts[:6]:
        normalized = raw_field.strip()
        label = _display_field_name(normalized)
        key = normalized if normalized in DCF_INPUT_TRIAGE else normalized.lower().replace(" ", "_")
        detail = DCF_INPUT_TRIAGE.get(key)
        if detail is None:
            lines.append(
                f"- Missing {label}: this required DCF input is unavailable from trusted local rows; "
                f"run `make focus-fundamentals TICKER={ticker}` before attempting valuation review."
            )
            continue
        lines.append(
            f"- Missing {label}: {detail['why']} Proof path: {detail['path'].format(ticker=ticker)}"
        )
    lines.append(
        "- Safe sequence: `make focus-fundamentals TICKER={ticker}` -> stage SEC or trusted manual fundamentals rows -> "
        "`make imports-validate` -> `make imports-preview` -> `make imports-apply` -> `make dcf-readiness`.".format(ticker=ticker)
    )
    return lines


def _stock_report_valuation_boundary_checklist_lines(
    *,
    dcf_status_text: str,
    monitor_context: bool,
    peer_ready: Any,
    earnings_ready: Any,
    estimates_ready: Any,
) -> list[str]:
    if monitor_context or dcf_status_text.lower() == "excluded":
        dcf_boundary = "excluded for ETF/index/fund monitor context; this is not a failed company DCF input."
        peer_boundary = "excluded for monitor context; peer-relative company valuation is not shown."
    elif dcf_status_text.lower() == "ready":
        dcf_boundary = "ready for assumption, scenario, and sensitivity review; still research context, not a price target."
        peer_boundary = (
            "available only from trusted peer mappings and peer valuation inputs."
            if bool(peer_ready)
            else "blocked until source-backed peer mappings and peer valuation inputs pass readiness."
        )
    else:
        dcf_boundary = "blocked until trusted price, fundamentals, cash-flow or margin, share-count, and DCF fields pass readiness."
        peer_boundary = "withheld until trusted fundamentals and DCF readiness pass first."

    optional_boundary = (
        "available for timing and consensus context."
        if bool(earnings_ready) and bool(estimates_ready)
        else "locked until trusted local earnings and analyst-estimate rows pass import validation."
    )
    return [
        f"- DCF boundary: {dcf_boundary}",
        f"- Peer-relative boundary: {peer_boundary}",
        f"- Optional-context boundary: {optional_boundary}",
        "- Conclusion boundary: missing or excluded inputs do not become intrinsic value, peer-relative value, undervalued, or overvalued conclusions.",
    ]


def _stock_report_missing_data_lines(payload: dict[str, Any], *, monitor_context: bool, dcf_status_text: str) -> list[str]:
    warnings = list(payload.get("missing_data_warnings", []))
    if dcf_status_text.lower() != "ready":
        dcf_warning_prefixes = (
            "normalized growth target",
            "observed fcf margin",
            "observed revenue growth",
        )
        warnings = [
            warning
            for warning in warnings
            if not any(str(warning).lower().startswith(prefix) for prefix in dcf_warning_prefixes)
        ]
    if monitor_context:
        excluded_prefixes = (
            "valuation missing field:",
            "revenue is unavailable from the current local fundamentals dataset",
            "eps is unavailable from the current local fundamentals dataset",
            "free cash flow is unavailable from the current local fundamentals dataset",
            "fundamentals has no local row for this ticker",
        )
        warnings = [
            warning
            for warning in warnings
            if not any(str(warning).lower().startswith(prefix) for prefix in excluded_prefixes)
        ]
    lines = [f"- {_stock_report_missing_warning_copy(warning)}" for warning in warnings[:20]]
    if monitor_context:
        lines.insert(
            0,
            "- Operating-company DCF and peer valuation are excluded for this monitor context, so company valuation fields are not treated as repair items.",
        )
    if not lines:
        lines.append("- None reported by the local provider.")
    return lines


def _stock_report_missing_warning_copy(warning: Any) -> str:
    """Make diagnostic missing-data warnings readable without hiding blockers."""

    text = _humanize_schema_terms(warning).strip()
    lower = text.lower()
    if lower == "analyst estimates has no local row for this ticker.":
        return "Analyst estimates: no trusted local row for this ticker; optional context stays locked."
    if lower == "earnings has no local row for this ticker.":
        return "Earnings: no trusted local row for this ticker; optional context stays locked."
    if lower.startswith("valuation missing field:"):
        field = text.split(":", 1)[1].strip().rstrip(".")
        return f"Valuation input still missing: {field}."
    peer_match = re.match(r"peer inputs for (?P<metric>.+?) were unavailable for: (?P<peers>.+)\.?$", text, flags=re.IGNORECASE)
    if peer_match:
        metric = _display_field_name(peer_match.group("metric").strip())
        peers = peer_match.group("peers").strip().rstrip(".")
        return f"Peer input still missing: {metric} unavailable for peer(s) {peers}."
    return text


def _stock_report_operator_summary(
    *,
    ticker: str,
    readiness: dict[str, Any],
    decision: dict[str, Any],
) -> str:
    asset_type = _display_value(readiness.get("asset_type"), "").lower()
    excluded_features = _display_value(readiness.get("excluded_features"), "").lower()
    bucket = _display_value(decision.get("decision_bucket"), "").lower()
    subtype = _display_value(decision.get("decision_subtype") or decision.get("decision_bucket"), "Decision not classified")
    purpose_status = _brief_value(
        _display_setup_text(decision.get("purpose_alignment") or decision.get("purpose_thesis")),
        "Purpose alignment:",
        "Purpose:",
        fallback="Purpose status unavailable",
    ).rstrip(".; ")
    monitor_context = (
        "monitor" in bucket
        or "market proxy" in subtype.lower()
        or "dcf" in excluded_features
        or asset_type in {"etf", "index_proxy", "fund"}
    )
    if monitor_context:
        return (
            f"Research review summary: Monitor context; {subtype}. "
            "Monitor role: market, theme, liquidity, or risk proxy. "
            "Withheld: operating-company DCF and peer valuation are excluded. "
            "Invalidation: proxy usefulness weakens if liquidity, correlation, or theme trend no longer supports monitoring."
        )

    blocker = _display_value(decision.get("primary_blocker"), "none")
    unsupported = _brief_value(
        decision.get("unsupported_analysis") or decision.get("valuation_evaluation"),
        "Unsupported analysis:",
        "Currently withheld:",
        fallback="Unavailable inputs remain withheld rather than inferred.",
    )
    invalidation = _display_setup_text(
        decision.get("invalidation_condition"),
        f"Invalidate this research read if {ticker} no longer passes the required readiness checks.",
    )
    return (
        f"Research review summary: {purpose_status}; {subtype}. "
        f"Next blocker: {blocker}. Withheld: {unsupported} "
        f"Invalidation: {invalidation}"
    )


def _stock_report_purpose_fields(
    *,
    ticker: str,
    readiness: dict[str, Any],
    decision: dict[str, Any],
    dcf_status_text: str,
    peer_ready: Any = None,
    relative_status: str | None = None,
) -> dict[str, str]:
    asset_type = _display_value(readiness.get("asset_type"), "company").lower()
    monitor_context = _stock_report_is_monitor_context(readiness=readiness, decision=decision, dcf_status_text=dcf_status_text)
    bucket = _display_value(decision.get("decision_bucket"), "Not classified")
    subtype = _display_value(decision.get("decision_subtype"), bucket)
    blocker = _display_value(decision.get("primary_blocker") or readiness.get("missing_data"), "none")
    ready = _display_value(readiness.get("ready_features"), "current ready local inputs")
    missing = _display_value(
        decision.get("missing_data") or readiness.get("missing_data") or readiness.get("blocked_features"),
        "missing local inputs",
    )
    confidence = _display_value(decision.get("data_confidence") or decision.get("confidence"), "limited")
    main_reason = _display_value(decision.get("main_reason"), "Current decision is based on local readiness state.")

    if monitor_context:
        fallback = {
            "purpose_thesis": "Purpose: ETF / Defensive / Hedge. Use as market, theme, liquidity, or risk context; operating-company valuation remains excluded.",
            "purpose_alignment": "Purpose alignment: monitor context is evaluated only from ready local price, momentum, liquidity, correlation, and theme context.",
            "setup_evaluation": f"Setup status: {subtype}; treat setup as monitor context rather than an operating-company recommendation.",
            "valuation_evaluation": "Operating-company DCF and peer valuation are excluded for this asset type; use market/risk context instead of valuation conclusions.",
            "supported_analysis": f"Supported analysis: {ready}; ETF/index/fund monitoring context.",
            "unsupported_analysis": "Currently withheld: operating-company DCF and peer valuation are excluded, not failed inputs.",
            "risk_watchpoint": "Risk watchpoint: monitor liquidity, correlation, theme exposure, and whether the proxy still represents the intended market context.",
            "invalidation_condition": "Invalidate market-proxy usefulness if liquidity, correlation, or theme trend no longer supports the intended monitoring role.",
            "next_research_question": f"What market, theme, liquidity, or risk context should {ticker} monitor, and what would invalidate that proxy role?",
            "review_priority_reason": "Monitor priority: use this proxy for market, theme, liquidity, or risk context; do not treat it as operating-company valuation.",
            "confidence_explanation": f"Data confidence is {confidence}: only ready local monitor inputs are used. Operating-company DCF and peer valuation are excluded.",
        }
    else:
        blocker_verb = "remain" if blocker.lower().endswith("s") else "remains"
        valuation = "Valuation interpretation is limited to the locally ready inputs; unavailable valuation inputs are not inferred."
        next_question = f"Which trusted local input would prove the next supported analysis for {ticker}?"
        if blocker.lower() in {"peer", "peers"} or "peer" in missing.lower():
            valuation = "Standalone DCF may be reviewable, but peer-relative valuation is withheld until source-backed peer inputs are ready."
            next_question = f"Which source-backed peers should be added for {ticker} before peer-relative valuation is reviewed?"
        elif blocker.lower() in {"fundamentals", "dcf"} or "fundamental" in missing.lower() or "dcf" in missing.lower():
            valuation = "Valuation is withheld until trusted fundamentals and DCF inputs pass local readiness checks."
            next_question = f"Which trusted fundamentals or DCF inputs are still missing for {ticker}?"
        elif blocker.lower() == "price" or "price" in missing.lower():
            valuation = "Valuation and setup interpretation are blocked until trusted price coverage passes local readiness checks."
            next_question = f"Which local price coverage gap must be repaired for {ticker} before setup analysis is reviewed?"
        elif "earnings" in missing.lower() or "analyst" in missing.lower():
            valuation = "Core valuation context may be reviewed, while earnings and analyst-estimate context stays locked until trusted local rows exist."
            next_question = f"Is trusted local earnings or analyst-estimate context available for {ticker}, or should optional context stay locked?"
        fallback = {
            "purpose_thesis": f"Purpose: {asset_type.title()} research lane. Current purpose is interpreted from local readiness and decision state, not inferred from missing data.",
            "purpose_alignment": f"Purpose alignment: {main_reason}",
            "setup_evaluation": f"Setup status: {subtype}. Supported local features: {ready}.",
            "valuation_evaluation": valuation,
            "supported_analysis": f"Supported analysis: {ready}.",
            "unsupported_analysis": f"Currently withheld: {missing}; unavailable inputs remain withheld rather than inferred.",
            "risk_watchpoint": f"Risk watchpoint: conclusions are limited by {blocker}.",
            "invalidation_condition": f"Invalidate this research read if local readiness no longer supports the stated purpose or if {blocker} {blocker_verb} unresolved for the intended analysis.",
            "next_research_question": next_question,
            "review_priority_reason": f"{bucket} / {subtype}; primary blocker: {blocker}.",
            "confidence_explanation": f"Data confidence is {confidence}: only ready local inputs are used; missing inputs are not inferred.",
        }

    result = {key: _display_setup_text(decision.get(key), value) for key, value in fallback.items()}
    if monitor_context:
        peer_question_terms = ("source-backed peer", "peer mapping", "peer metric", "peer-relative")
        current_question = result.get("next_research_question", "").lower()
        if any(term in current_question for term in peer_question_terms):
            result["next_research_question"] = fallback["next_research_question"]
        return result
    relative_status_key = _display_value(relative_status, "").lower()
    if (
        not monitor_context
        and bool(peer_ready)
        and relative_status_key in {"calculated", "partial"}
        and "peer data unavailable" in result.get("valuation_evaluation", "").lower()
    ):
        result["valuation_evaluation"] = (
            f"Report-local peer valuation is {relative_status_key} from trusted peer inputs; "
            "broad value labels may still remain limited when optional value-engine fields are missing."
        )
    return result


def _stock_report_is_monitor_context(*, readiness: dict[str, Any], decision: dict[str, Any], dcf_status_text: str = "") -> bool:
    asset_type = _display_value(readiness.get("asset_type"), "").lower()
    excluded_features = _display_value(readiness.get("excluded_features"), "").lower()
    bucket = _display_value(decision.get("decision_bucket"), "").lower()
    subtype = _display_value(decision.get("decision_subtype") or decision.get("decision_bucket"), "").lower()
    return (
        "monitor" in bucket
        or "market proxy" in subtype
        or dcf_status_text.lower() == "excluded"
        or "dcf" in excluded_features
        or asset_type in {"etf", "index_proxy", "fund"}
    )


def _stock_report_monitor_next_action(ticker: str) -> str:
    return f"Review {ticker} as ETF/index/fund monitor context; operating-company DCF and peer valuation stay excluded."


def _stock_report_decision_boundary(*, readiness: dict[str, Any], decision: dict[str, Any]) -> str:
    explicit = _display_value(decision.get("decision_boundary"), "")
    if explicit:
        return _humanize_schema_terms(explicit)
    bucket = _display_value(decision.get("decision_bucket"), "").lower()
    subtype = _display_value(decision.get("decision_subtype"), "").lower()
    asset_type = _display_value(readiness.get("asset_type"), "").lower()
    blocker = _display_value(decision.get("primary_blocker") or readiness.get("missing_data"), "required inputs")
    if "research now" in bucket and "peer blocked" in subtype:
        return (
            "Workflow state only: standalone company and DCF review can continue, but peer-relative valuation "
            "stays locked until trusted peer inputs are ready."
        )
    if "research now" in bucket:
        return "Workflow state only: ready for deeper manual research using supported local evidence, not a final conclusion."
    if "monitor" in bucket or asset_type in {"etf", "index_proxy", "fund"}:
        return (
            "Monitor context only: use market, theme, liquidity, or risk context; operating-company DCF and "
            "peer-relative company valuation stay excluded."
        )
    if "blocked" in bucket:
        return f"Missing-data proof state: {blocker} blocks evaluation, so conclusions stay withheld."
    if "excluded" in bucket:
        return "Method-exclusion state: the analysis is intentionally omitted, not treated as a failed calculation."
    return "Review state only: use readiness, blockers, and source readiness before drawing a conclusion."


def _stock_report_next_action(
    *,
    ticker: str,
    readiness: dict[str, Any],
    decision: dict[str, Any],
    peer: dict[str, Any],
    dcf_status_text: str = "",
) -> str:
    if _stock_report_is_monitor_context(readiness=readiness, decision=decision, dcf_status_text=dcf_status_text):
        return _stock_report_monitor_next_action(ticker)
    if not bool(readiness.get("price_ready")):
        return (
            f"Add or refresh trusted local price history for {ticker}; run `make focus-price TICKER={ticker}` "
            "before interpreting setup, fundamentals, DCF, or peer context."
        )
    primary_blocker = str(decision.get("primary_blocker", "")).strip().lower()
    peer_action = peer.get("next_peer_action") or peer.get("missing_peer_reason")
    if primary_blocker in {"peer", "peers"} and _display_value(peer_action) != "Not available":
        return _display_value(peer_action)
    return _display_value(decision.get("next_best_action") or decision.get("next_action") or readiness.get("next_action"))


def _stock_report_one_minute_state_phrase(
    *,
    ticker: str,
    readiness: dict[str, Any],
    dcf_status_text: str,
    peer_ready: Any,
    optional_locked: bool,
    monitor_context: bool,
) -> str:
    state = _display_value(readiness.get("overall_readiness_state"))
    state_text = state.lower()
    if state_text == "partial" and monitor_context:
        return f"{ticker} overall readiness: partial because monitor context is usable while company valuation is excluded."
    if state_text == "partial" and dcf_status_text == "ready" and bool(peer_ready) and optional_locked:
        return f"{ticker} overall readiness: partial because optional earnings/estimate context is locked; core DCF and peer inputs are ready."
    if state_text == "partial" and dcf_status_text == "ready" and optional_locked:
        return f"{ticker} overall readiness: partial because optional earnings/estimate context is locked; standalone DCF inputs are ready."
    if state_text == "partial":
        return f"{ticker} overall readiness: partial; review ready inputs first and treat locked inputs as missing-data review work."
    return f"{ticker} overall readiness: {state}."


def _stock_report_analysis_quality_lines(
    *,
    readiness: dict[str, Any],
    dcf_status_text: str,
    peer_ready: Any,
    earnings_ready: Any,
    estimates_ready: Any,
) -> list[str]:
    asset_type = _display_value(readiness.get("asset_type"), "").lower()
    price_ready = bool(readiness.get("price_ready"))
    dcf_ready = dcf_status_text == "ready" or bool(readiness.get("dcf_ready"))
    peer_is_ready = bool(peer_ready)
    monitor_context = dcf_status_text == "excluded" or asset_type in {"etf", "index_proxy", "fund"}

    if monitor_context:
        quality_title = "Monitor-only context"
        quality_reason = (
            "Use market, theme, liquidity, or risk context. Operating-company DCF and peer valuation are "
            "excluded, not failed."
        )
    elif dcf_ready and peer_is_ready:
        quality_title = "DCF-ready review"
        quality_reason = "Price, fundamentals, standalone DCF, and peer context are ready for a fuller research pass."
    elif dcf_ready:
        quality_title = "Standalone DCF review"
        quality_reason = (
            "DCF assumptions can be reviewed, but peer-relative valuation remains limited until trusted peer "
            "inputs are ready."
        )
    elif price_ready:
        quality_title = "Price/setup review only"
        quality_reason = (
            "Use price and setup context only. Company valuation stays blocked until trusted fundamentals and "
            "DCF inputs exist."
        )
    else:
        quality_title = "Data needed before analysis"
        quality_reason = (
            "Start with verified local price history before relying on momentum, liquidity, valuation, or peer context."
        )

    if not price_ready:
        confidence_line = "low: price history is still the first required input."
    elif monitor_context:
        confidence_line = "medium: market, theme, liquidity, or risk context may be reviewable, while company valuation is excluded."
    elif dcf_ready and peer_is_ready:
        if bool(earnings_ready) and bool(estimates_ready):
            confidence_line = "high: core price, fundamentals, DCF, peer, earnings, and estimate inputs are ready."
        else:
            confidence_line = "medium: core price, fundamentals, DCF, and peer inputs are ready, but optional context is still locked."
    elif dcf_ready:
        confidence_line = "medium: standalone DCF inputs are ready, but peer-relative valuation remains locked."
    else:
        confidence_line = "low: price/setup context is available, but company valuation inputs are blocked."

    optional_context = (
        "Optional earnings and analyst-estimate context is available for review."
        if bool(earnings_ready) and bool(estimates_ready)
        else "Earnings and analyst estimates stay locked until trusted local rows exist."
    )
    return [
        f"- Analysis mode: {quality_title}.",
        f"- Confidence: {confidence_line}",
        f"- Why: {quality_reason}",
        f"- Optional context: {optional_context}",
    ]


def _stock_report_function_quality_lines(
    *,
    readiness: dict[str, Any],
    dcf_status_text: str,
    peer_ready: Any,
    earnings_ready: Any,
    estimates_ready: Any,
) -> list[str]:
    price_ready = bool(readiness.get("price_ready"))
    momentum_ready = bool(readiness.get("momentum_ready"))
    liquidity_ready = bool(readiness.get("liquidity_ready"))
    correlation_ready = bool(readiness.get("correlation_ready"))
    fundamentals_ready = bool(readiness.get("fundamentals_ready"))
    peer_is_ready = bool(peer_ready)
    optional_ready = bool(earnings_ready) and bool(estimates_ready)
    asset_type = _display_value(readiness.get("asset_type"), "").lower()
    monitor_context = dcf_status_text == "excluded" or asset_type in {"etf", "index_proxy", "fund"}

    price_status = (
        "ready for local trend/setup review"
        if price_ready and momentum_ready
        else "locked until enough trusted price history is available"
    )
    risk_status = (
        "ready for local liquidity/correlation context"
        if liquidity_ready and correlation_ready
        else "partial until liquidity and correlation inputs pass readiness checks"
    )
    if monitor_context:
        valuation_status = "excluded for ETF/index/fund monitor context, not failed"
    elif dcf_status_text == "ready" and fundamentals_ready:
        valuation_status = "ready for standalone DCF assumptions and sensitivity review"
    else:
        valuation_status = "blocked until trusted fundamentals, cash-flow or margin, share-count, and DCF inputs are ready"
    peer_status = (
        "ready for peer-relative review"
        if peer_is_ready and not monitor_context
        else "excluded for monitor context"
        if monitor_context
        else "blocked until source-backed peer mappings and peer valuation inputs are ready"
    )
    optional_status = (
        "ready for earnings and analyst-estimate context"
        if optional_ready
        else "locked until trusted local earnings and analyst-estimate rows exist"
    )

    return [
        "- Readiness gate: strongest function; it decides ready, blocked, or excluded before any conclusion is shown.",
        f"- Price and setup: {price_status}.",
        f"- Risk context: {risk_status}.",
        f"- Fundamentals / DCF: {valuation_status}.",
        f"- Peer comparison: {peer_status}.",
        f"- Optional context: {optional_status}.",
        "- Method source: readiness gates, DCF boundaries, peer blockers, and report wording are implemented in project code; standard libraries/adapters support data handling and UI, but shipped analysis comes from project code and local data.",
    ]


def _stock_report_methodology_lines(
    *,
    readiness: dict[str, Any],
    dcf_status_text: str,
    peer_ready: Any,
) -> list[str]:
    asset_type = _display_value(readiness.get("asset_type"), "").lower()
    monitor_context = dcf_status_text == "excluded" or asset_type in {"etf", "index_proxy", "fund"}
    if monitor_context:
        valuation_method = (
            "operating-company DCF is excluded because this ticker is treated as ETF/index/fund monitor context; "
            "use ready price, liquidity, correlation, theme, or risk context instead"
        )
    elif dcf_status_text == "ready":
        valuation_method = (
            "standalone DCF projects free cash flow under bear/base/bull assumptions, discounts projected cash flows "
            "and terminal value by WACC, adjusts for cash/debt or net debt, and divides by shares outstanding"
        )
    else:
        valuation_method = (
            "standalone DCF stays blocked until trusted local price, revenue, free cash flow or FCF margin, "
            "shares outstanding, and DCF fields pass readiness checks"
        )

    if monitor_context:
        peer_method = "peer-relative company valuation is excluded for monitor context"
    elif bool(peer_ready):
        peer_method = "peer-relative valuation can be reviewed because source-backed peer inputs are ready"
    else:
        peer_method = "peer-relative valuation stays withheld until source-backed peer mappings and peer valuation inputs are ready"
    return [
        "- Method order: readiness gate first, supported analysis second, valuation math third, explanation last.",
        "- Input boundary: local or provider-assisted rows supply data; project rules decide readiness, calculations, blockers, and report wording.",
        "- Analysis recipe: prices support setup/trend review; fundamentals support field review and DCF input quality; DCF supports scenario math; source-backed peers support peer context; optional earnings and estimates add timing or consensus context only.",
        "- Black-box check: every supported section should trace back to a ready input, a visible formula or score, or an explicit blocker listed in this report.",
        "- Methodology proof ladder: input row -> readiness gate -> local calculation or score -> supported/blocked/excluded label -> explicit next step.",
        "- Reader check path: start with Source Readiness, then Data Readiness, then DCF Calculation Path or Peer Workflow; if any step is missing, the related conclusion stays withheld.",
        "- Fundamental analysis: local revenue, cash-flow, margin, share-count, cash/debt, and source fields are reviewed only when present; missing fields are not inferred.",
        "- DCF formula path: base FCF -> projected FCF -> discounted FCF plus discounted terminal value -> enterprise value -> equity value -> fair value per share.",
        "- DCF status boundary: ready means assumptions can be reviewed, blocked means required company inputs are missing, and excluded means the method does not fit ETF/index/fund monitor context.",
        f"- DCF method: {valuation_method}.",
        f"- Peer method: {peer_method}.",
        "- Score boundary: setup, watchlist, confidence, and monthly scores are triage aids for review order only; they are not price targets, expected returns, or allocation instructions.",
        "- Report method: text is built from local readiness, DCF, peer, decision, and source readiness outputs; blocked or excluded sections are explained instead of filled.",
    ]


def _stock_report_source_logic_lines(
    *,
    readiness: dict[str, Any],
    dcf_status_text: str,
    peer_ready: Any,
    earnings_ready: Any,
    estimates_ready: Any,
) -> list[str]:
    asset_type = _display_value(readiness.get("asset_type"), "company").lower()
    monitor_context = dcf_status_text == "excluded" or asset_type in {"etf", "index_proxy", "fund"}
    if monitor_context:
        dcf_logic = "excluded by asset-type gate"
        peer_logic = "excluded for monitor context"
    elif dcf_status_text == "ready":
        dcf_logic = "calculated locally from trusted price, fundamentals, cash-flow or margin, share count, and cash/debt inputs"
        peer_logic = (
            "available only from source-backed peer mappings and peer valuation inputs"
            if bool(peer_ready)
            else "blocked locally until source-backed peer mappings and peer metrics exist"
        )
    else:
        dcf_logic = "blocked locally because required price, fundamentals, cash-flow or margin, share count, or DCF fields are missing"
        peer_logic = "blocked locally until source-backed peer mappings and peer metrics exist"
    optional_logic = (
        "available from trusted local earnings and analyst-estimate rows"
        if bool(earnings_ready) and bool(estimates_ready)
        else "locked locally until trusted earnings and analyst-estimate rows pass import validation"
    )
    return [
        "- Source inputs: local CSV rows or labeled provider-assisted rows supply prices, fundamentals, peers, earnings, and estimates.",
        "- Product checks: project readiness gates decide whether each input is usable before report sections appear.",
        f"- DCF method: {dcf_logic}; the report does not ask a third party or model to create a valuation opinion.",
        f"- Peer method: {peer_logic}; sector or industry fallback is not treated as trusted peer valuation.",
        f"- Optional context method: {optional_logic}; empty optional files are an intentional locked state, not hidden analysis.",
        "- Output wording: supported, blocked, partial, and excluded sections are written from project code so missing data cannot become a weak conclusion.",
    ]


def _stock_report_reader_guide_lines(
    *,
    dcf_status_text: str,
    monitor_context: bool,
    price_ready: bool,
    peer_ready: Any = None,
) -> list[str]:
    if monitor_context:
        current_use = "Monitor-only context when local price, liquidity, correlation, or theme inputs are ready."
    elif dcf_status_text == "ready" and bool(peer_ready):
        current_use = "DCF-ready review for company-level assumptions and sensitivity when trusted local fundamentals are ready."
    elif dcf_status_text == "ready":
        current_use = "Standalone DCF review: company DCF assumptions can be reviewed, while peer-relative valuation stays locked until source-backed peer inputs are ready."
    elif price_ready:
        current_use = "Price/setup review only until trusted fundamentals, DCF, and peer inputs are ready."
    elif dcf_status_text == "blocked":
        current_use = "Data needed before analysis until trusted price, fundamentals, DCF, and peer inputs are ready."
    else:
        current_use = "Only the local inputs explicitly marked ready in this report should be interpreted."
    return [
        "- Read top-down: readiness state first, supported analysis second, blocked or excluded analysis third.",
        f"- Current use: {current_use}",
        "- Method source: project code implements readiness gates and report wording; libraries and adapters support data handling/UI, but shipped analysis comes from project code and local data.",
        "- Boundary: this is research context only. It does not provide allocation instructions, account actions, or direct recommendations.",
    ]


def _stock_report_reader_question_lines(
    *,
    ticker: str,
    supported_now: str,
    locked_now: str,
    next_action: str,
    dcf_status_text: str,
    monitor_context: bool,
    price_ready: bool,
    peer_ready: Any = None,
    earnings_ready: Any = None,
    estimates_ready: Any = None,
) -> list[str]:
    if not price_ready:
        next_input = "Trusted local price history."
        command = f"make focus-price TICKER={ticker}"
    elif monitor_context:
        next_input = "No company DCF input is required for monitor context."
        command = f"make stock-report-md TICKER={ticker}"
    elif dcf_status_text == "blocked":
        next_input = "Trusted fundamentals such as revenue, free cash flow or margin, and shares outstanding."
        command = f"make focus-fundamentals TICKER={ticker}"
    elif dcf_status_text == "ready" and not bool(peer_ready):
        next_input = "Source-backed peer mappings and peer valuation inputs."
        command = f"make focus-peers TICKER={ticker}"
    elif not bool(earnings_ready) or not bool(estimates_ready):
        next_input = "Trusted optional earnings or analyst-estimate CSV rows, only if you have a source you trust."
        command = f"make optional-context-worklist TICKERS={ticker} TOP_N=10"
    else:
        next_input = "Review source readiness notes before interpreting the supported sections."
        command = f"make stock-report-md TICKER={ticker}"
    lane = _stock_report_data_health_handoff_line(
        ticker=ticker,
        dcf_status_text=dcf_status_text,
        monitor_context=monitor_context,
        price_ready=price_ready,
        peer_ready=peer_ready,
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
    )
    return [
        f"- Analyze now: {_sentence_value(supported_now)}.",
        f"- Still locked: {_sentence_value(locked_now)}.",
        f"- Trusted input: {_sentence_value(next_input)}.",
        lane,
        f"- Next research step: {_sentence_value(_humanize_schema_terms(next_action), 'No next local action is available')}.",
    ]


def _stock_report_next_layer_lines(
    *,
    ticker: str,
    dcf_status_text: str,
    monitor_context: bool,
    price_ready: Any,
    peer_ready: Any,
    earnings_ready: Any,
    estimates_ready: Any,
) -> list[str]:
    if not bool(price_ready):
        current_layer = "Data needed before analysis; conclusions stay withheld until trusted local price history exists."
        next_input = "Trusted local price history."
        proof_command = f"make focus-price TICKER={ticker}"
    elif monitor_context:
        current_layer = "Monitor-only context; market, theme, liquidity, or risk review can be read when local inputs are ready."
        next_input = "No operating-company DCF or peer-valuation input is required for this monitor role."
        proof_command = f"make stock-report-md TICKER={ticker}"
    elif dcf_status_text == "blocked":
        current_layer = "Price/setup review only; company valuation stays locked until fundamentals and DCF inputs pass readiness."
        next_input = "Trusted fundamentals, free-cash-flow or margin inputs, share count, and DCF fields."
        proof_command = f"make focus-fundamentals TICKER={ticker}"
    elif dcf_status_text == "ready" and not bool(peer_ready):
        current_layer = "Standalone DCF review; assumptions and sensitivity can be read before peer-relative valuation."
        next_input = "Source-backed peer mappings plus peer price, fundamentals, and valuation inputs."
        proof_command = f"make focus-peers TICKER={ticker}"
    elif not bool(earnings_ready) or not bool(estimates_ready):
        current_layer = "DCF-ready review; core company and peer context can be read while optional context remains locked."
        next_input = "Trusted earnings or analyst-estimate CSV rows only when a source is available."
        proof_command = f"make optional-context-worklist TICKERS={ticker} TOP_N=10"
    else:
        current_layer = "Full local research review; ready sections still need source/freshness review before interpretation."
        next_input = "No missing required layer is flagged; review source readiness and rerun the report after data changes."
        proof_command = f"make stock-report-md TICKER={ticker}"

    return [
        f"- Current supported layer: {current_layer}",
        f"- Next trusted input: {next_input}",
        f"- Proof command: `{proof_command}` before treating the next layer as available.",
        "- Stop rule: if trusted rows are unavailable, leave the section locked; do not infer, backfill, or use placeholders.",
    ]


def _stock_report_data_health_handoff_line(
    *,
    ticker: str,
    dcf_status_text: str,
    monitor_context: bool,
    price_ready: Any,
    peer_ready: Any,
    earnings_ready: Any,
    estimates_ready: Any,
) -> str:
    if not bool(price_ready):
        lane = "Price Coverage Batch"
        command = f"make focus-price TICKER={ticker}"
        proof = "make price-coverage TOP_N=25 && make readiness"
    elif monitor_context:
        lane = "Single-Stock Review"
        command = f"make stock-report-md TICKER={ticker}"
        proof = "make readiness"
    elif dcf_status_text == "blocked":
        lane = "Fundamentals / DCF Proof"
        command = f"make focus-fundamentals TICKER={ticker}"
        proof = "make dcf-readiness && make readiness"
    elif not bool(peer_ready):
        lane = "Peer Mapping Proof"
        command = f"make focus-peers TICKER={ticker}"
        proof = f"make readiness && make peer-mapping-queue TICKERS={ticker} TOP_N=10"
    elif not bool(earnings_ready) or not bool(estimates_ready):
        lane = "Optional Context Proof"
        command = f"make optional-context-worklist TICKERS={ticker} TOP_N=10"
        proof = "make optional-context-readiness && make readiness"
    else:
        lane = "Single-Stock Review"
        command = f"make stock-report-md TICKER={ticker}"
        proof = "make readiness"
    return f"- Data Health lane: {lane}. Suggested local check: `{command}`. Confirm with `{proof}` before treating the lane as available."


def _stock_report_executive_summary_lines(
    *,
    ticker: str,
    analysis_quality_lines: list[str],
    supported_now: str,
    locked_now: str,
    next_action: str,
) -> list[str]:
    mode = "Not classified"
    why = "Only ready local inputs should be interpreted."
    for line in analysis_quality_lines:
        if "Analysis mode:" in line:
            mode = _brief_value(line, "- Analysis mode:").rstrip(".")
        elif line.startswith("- Why:"):
            why = _brief_value(line, "- Why:").rstrip(".")
    next_step = _sentence_value(next_action, "No next local action is available")
    return [
        f"- Bottom line: {ticker} is in `{mode}` mode. {why}.",
        f"- Use now: {_sentence_value(supported_now)}.",
        f"- Do not infer: {_sentence_value(locked_now)}.",
        f"- Next step: {next_step}.",
    ]


def _stock_report_evaluation_snapshot_lines(
    *,
    supported_now: str,
    locked_now: str,
    next_action: str,
    analysis_quality_lines: list[str],
    dcf_status_text: str,
    monitor_context: bool,
    peer_ready: Any,
) -> list[str]:
    confidence = "Use only the ready sections; locked sections remain unavailable."
    for line in analysis_quality_lines:
        if line.startswith("- Confidence:"):
            confidence = _brief_value(line, "- Confidence:").rstrip(".")
            break

    if monitor_context:
        valuation_boundary = (
            "Operating-company DCF and peer valuation are excluded for this monitor role; use market, theme, liquidity, and risk context only."
        )
    elif dcf_status_text == "ready" and bool(peer_ready):
        valuation_boundary = (
            "Standalone DCF assumptions and source-backed peer context can be reviewed; optional context may still be locked."
        )
    elif dcf_status_text == "ready":
        valuation_boundary = (
            "Standalone DCF assumptions can be reviewed, but peer-relative valuation stays locked until source-backed peer inputs exist."
        )
    else:
        valuation_boundary = (
            "Company valuation is blocked until trusted fundamentals, cash-flow or margin, share-count, and DCF inputs pass readiness."
        )

    return [
        f"- Supported evaluation: {_sentence_value(supported_now)}.",
        f"- Valuation boundary: {valuation_boundary}",
        f"- Confidence cue: {confidence}.",
        f"- Next proof: {_sentence_value(next_action, 'No next local proof step is available')}.",
        f"- Stop rule: {_sentence_value(locked_now)}.",
    ]


def _stock_report_proof_checklist_lines(
    *,
    ticker: str,
    report_mode: str,
    dcf_status_text: str,
    monitor_context: bool,
    price_ready: bool,
    peer_ready: Any,
    earnings_ready: Any,
    estimates_ready: Any,
    next_action: str,
    locked_now: str,
) -> list[str]:
    if not price_ready:
        evidence = "trusted local price history is not ready, so this report is a missing-data checklist."
        next_proof = f"`make focus-price TICKER={ticker}` followed by readiness rebuild."
    elif monitor_context:
        evidence = "asset-type gate marks this as monitor context, so company DCF and peer valuation are excluded."
        next_proof = f"`make stock-report-md TICKER={ticker}` after any local data changes."
    elif dcf_status_text == "ready" and bool(peer_ready):
        evidence = "price, fundamentals, DCF, and source-backed peer inputs passed local readiness."
        if bool(earnings_ready) and bool(estimates_ready):
            next_proof = f"`make stock-report-md TICKER={ticker}` after source-readiness review."
        else:
            next_proof = f"`make optional-context-worklist TICKERS={ticker} TOP_N=10` only if trusted optional rows exist."
    elif dcf_status_text == "ready":
        evidence = "standalone DCF passed local readiness, while peer-relative valuation remains locked."
        next_proof = f"`make focus-peers TICKER={ticker}` with source-backed peer mappings and peer inputs."
    else:
        evidence = "price/setup may be usable, but fundamentals or DCF inputs have not passed readiness."
        next_proof = f"`make focus-fundamentals TICKER={ticker}` before reviewing company valuation."

    return [
        f"- Current mode proof: `{report_mode}` because {evidence}",
        f"- Next proof step: {next_proof}",
        f"- Withhold until proven: {_sentence_value(locked_now)}.",
        f"- Manual check: {_sentence_value(_humanize_schema_terms(next_action), 'No next local action is available')}.",
    ]


def _stock_report_best_review_path_lines(
    *,
    ticker: str,
    dcf_status_text: str,
    monitor_context: bool,
    price_ready: bool,
    peer_ready: Any,
    earnings_ready: Any,
    estimates_ready: Any,
) -> list[str]:
    if not price_ready:
        primary = (
            "Start with Missing-Data Proof Summary and Price Coverage. Do not interpret setup, valuation, or peer context "
            "until trusted local price history is ready."
        )
        proof = f"`make focus-price TICKER={ticker}`"
    elif monitor_context:
        primary = (
            "Start with monitor context. Operating-company DCF and peer-relative company valuation are excluded, "
            "so review market, theme, liquidity, and risk context only."
        )
        proof = f"`make stock-report-md TICKER={ticker}`"
    elif dcf_status_text == "ready" and bool(peer_ready):
        primary = (
            "Start with DCF Calculation Path, then Peer Workflow, then Source Readiness. This is the richest "
            "company-review path, but it remains research context."
        )
        proof = f"`make stock-report-md TICKER={ticker}`"
    elif dcf_status_text == "ready":
        primary = (
            "Start with DCF Calculation Path and Valuation Boundary Checklist. Peer-relative valuation stays locked "
            "until source-backed peer inputs pass readiness."
        )
        proof = f"`make focus-peers TICKER={ticker}`"
    else:
        primary = (
            "Start with DCF Input Triage and Missing-Data Proof Summary. Company valuation stays blocked until trusted "
            "fundamentals and DCF inputs are ready."
        )
        proof = f"`make focus-fundamentals TICKER={ticker}`"

    optional_note = (
        "Optional earnings and analyst-estimate context is ready to review."
        if bool(earnings_ready) and bool(estimates_ready)
        else "Optional earnings and analyst-estimate context remains locked unless trusted local rows exist."
    )
    return [
        f"- First read: {primary}",
        "- Then check: What We Can Analyze Now, Valuation Boundary Checklist, and Source Readiness Check.",
        f"- Optional context: {optional_note}",
        f"- Copy-only proof step: {proof}",
    ]


def _stock_report_at_a_glance_lines(
    *,
    mode: str,
    decision: dict[str, Any],
    dcf_status_text: str,
    dcf: dict[str, Any],
    readiness: dict[str, Any],
    peer_ready: Any,
    earnings_ready: Any,
    estimates_ready: Any,
    next_action: str,
    valuation_snapshot: dict[str, Any] | None = None,
) -> list[str]:
    asset_type = _display_value(readiness.get("asset_type"), "").lower()
    monitor_context = dcf_status_text == "excluded" or asset_type in {"etf", "index_proxy", "fund"}
    peer_status = (
        "Excluded for monitor context"
        if monitor_context
        else "Ready for source-backed peer review"
        if bool(peer_ready)
        else "Locked until source-backed peer inputs are ready"
    )
    optional_status = (
        "Ready"
        if bool(earnings_ready) and bool(estimates_ready)
        else "Locked until trusted earnings and analyst-estimate rows exist"
    )
    dcf_status = (
        "Excluded for ETF/index/fund monitor context"
        if monitor_context
        else "Ready for scenario review"
        if dcf_status_text == "ready"
        else "Blocked until trusted fundamentals and DCF inputs are ready"
    )
    valuation_snapshot = valuation_snapshot or {}
    nested_dcf_result = dcf.get("dcf_result") if isinstance(dcf.get("dcf_result"), dict) else {}
    snapshot_dcf_result = (
        valuation_snapshot.get("dcf_result") if isinstance(valuation_snapshot.get("dcf_result"), dict) else {}
    )
    fair_value = _clean_number(
        dcf.get("fair_value_per_share")
        or nested_dcf_result.get("fair_value_per_share")
        or snapshot_dcf_result.get("fair_value_per_share")
    )
    missing_fields = dcf.get("missing_dcf_fields") or dcf.get("reason_not_ready")
    if monitor_context:
        valuation_support = "Monitor context only; operating-company DCF and peer valuation are excluded."
        method_line = (
            "project readiness gates decide what can appear; monitor reports use local price, market, liquidity, "
            "correlation, or theme context and exclude operating-company valuation methods."
        )
    elif dcf_status_text == "ready":
        fair_value_note = (
            f"; base scenario fair value/share is {_format_money(fair_value)} as scenario math"
            if fair_value is not None
            else "; review the DCF section for scenario math"
        )
        valuation_support = f"Standalone DCF assumptions and sensitivity are reviewable{fair_value_note}."
        method_line = (
            "project readiness gates decide what can appear; DCF uses local free-cash-flow inputs, discounted cash flows, "
            "discounted terminal value, cash/debt adjustment, and fair value per share when ready."
        )
    else:
        missing_note = _display_field_list(missing_fields)
        valuation_support = (
            f"Blocked until trusted DCF inputs are ready; missing now: {missing_note}."
            if missing_note != "Not available"
            else "Blocked until trusted price, fundamentals, cash-flow or margin, and share-count inputs are ready."
        )
        method_line = (
            "project readiness gates decide what can appear; DCF formula output is withheld until trusted price, "
            "fundamentals, cash-flow or margin, share-count, and DCF fields pass readiness."
        )
    decision_label = _display_value(
        decision.get("decision_subtype") or decision.get("decision_bucket"),
        "Not classified",
    )
    return [
        f"- Mode: `{mode}`.",
        f"- Decision view: {decision_label}.",
        f"- DCF: {dcf_status}.",
        f"- Valuation support: {valuation_support}",
        f"- Peer context: {peer_status}.",
        f"- Optional context: {optional_status}.",
        f"- Method: {method_line}",
        f"- Next local step: {_sentence_value(_humanize_schema_terms(next_action), 'No next local action is available')}.",
    ]


def _stock_report_mode_from_quality_lines(analysis_quality_lines: list[str]) -> str:
    for line in analysis_quality_lines:
        if "Analysis mode:" in line:
            return _brief_value(line, "- Analysis mode:").rstrip(".")
    return "Not classified"


def _stock_report_mode_guide_lines(current_mode: str) -> list[str]:
    descriptions = {
        "DCF-ready review": "Fullest company review: price, fundamentals, DCF, and source-backed peer context are ready.",
        "Standalone DCF review": "Company DCF can be reviewed, but peer-relative valuation remains blocked.",
        "Price/setup review only": "Use trend/setup context only; company valuation waits for trusted fundamentals and DCF inputs.",
        "Monitor-only context": "Use ETF/index/fund market or risk context; operating-company DCF is excluded, not failed.",
        "Data needed before analysis": "Reference state for tickers with no trusted local inputs yet; add the first missing input before drawing conclusions.",
    }
    lines = []
    for mode, description in descriptions.items():
        marker = "current" if mode == current_mode else "other"
        if mode == "Data needed before analysis" and mode == current_mode:
            description = "Pause analysis for this ticker until the first trusted local input is available."
        lines.append(f"- `{mode}` ({marker}): {description}")
    return lines


def _stock_report_source_audit_lines(
    *,
    ticker: str,
    readiness: dict[str, Any],
    coverage: dict[str, Any],
    dcf: dict[str, Any],
    peer: dict[str, Any],
    earnings_ready: Any,
    estimates_ready: Any,
    dcf_status_text: str,
) -> list[str]:
    sec_status = "present" if os.environ.get("SEC_USER_AGENT", "").strip() else "missing"
    stooq_status = "present" if (os.environ.get("STOOQ_API_KEY", "").strip() or os.environ.get("STOQ_API_KEY", "").strip()) else "missing"
    price_window = (
        f"{_display_value(coverage.get('first_price_date'), 'unknown')} to "
        f"{_display_value(coverage.get('last_price_date'), 'unknown')}; "
        f"rows={_display_value(coverage.get('price_rows'))}"
    )
    monitor_context = _stock_report_is_monitor_context(readiness=readiness, decision={}, dcf_status_text=dcf_status_text)
    core_data_before_peers = not monitor_context and dcf_status_text.lower() != "ready"
    if monitor_context:
        peer_status = "monitor context"
        peer_action = "No peer import is required; operating-company peer valuation is excluded for ETF/index/fund monitor context"
    elif core_data_before_peers:
        peer_status = "blocked until fundamentals / DCF"
        peer_action = "Peer-relative valuation should wait until trusted price, fundamentals, and DCF inputs are ready"
    else:
        peer_status = _display_report_status(peer.get("peer_blocker_type") or peer.get("missing_peer_reason"), "ready")
        peer_action = _sentence_value(peer.get("next_peer_action") or peer.get("missing_peer_reason"))
    dcf_reason = _display_field_list(dcf.get("reason_not_ready") or dcf.get("missing_dcf_fields"), "")
    dcf_reason_clause = f"; reason {dcf_reason}" if dcf_reason and dcf_reason != "Not available" else ""
    return [
        f"- Prices: {_display_report_status(readiness.get('price_ready'))}; local source `data/prices.csv`; coverage {price_window}; import file path `data/staged/prices/` or `data/imports/prices.csv`; rejected rows `data/rejected/price_import_rejected.csv`.",
        f"- Fundamentals / DCF: {_display_report_status(dcf_status_text)}; local source `data/fundamentals.csv`{dcf_reason_clause}; SEC_USER_AGENT {sec_status}; import file path `data/staged/fundamentals/` or `data/imports/fundamentals.csv`; rejected rows `data/rejected/fundamentals_import_rejected.csv`.",
        f"- Peers: {peer_status}; local source `data/peers.csv`; import file path `data/imports/peers.csv`; next peer action {peer_action}.",
        f"- Earnings: {_display_report_status(earnings_ready)}; trusted local CSV only; import file path `data/staged/earnings/`; command `make import-earnings`; rejected rows `data/rejected/earnings_import_rejected.csv`.",
        f"- Analyst estimates: {_display_report_status(estimates_ready)}; trusted local CSV only; import file path `data/staged/analyst_estimates/`; command `make import-analyst-estimates`; rejected rows `data/rejected/analyst_estimates_import_rejected.csv`.",
        f"- Credentials: SEC_USER_AGENT {sec_status}; STOOQ_API_KEY {stooq_status}; missing remote credentials should not break local CSV reports or preview-first local import workflows.",
        f"- Report command: `make stock-report-md TICKER={ticker}`. Research-only Markdown output; copyable command only.",
    ]


def _stock_report_data_unlock_lines(
    *,
    ticker: str,
    readiness: dict[str, Any],
    coverage: dict[str, Any],
    dcf: dict[str, Any],
    peer: dict[str, Any],
    earnings_ready: Any,
    estimates_ready: Any,
    dcf_status_text: str,
) -> list[str]:
    monitor_context = _stock_report_is_monitor_context(readiness=readiness, decision={}, dcf_status_text=dcf_status_text)
    price_ready = bool(readiness.get("price_ready"))
    peer_ready = bool(peer.get("peer_ready") or readiness.get("peer_ready"))
    optional_ready = bool(earnings_ready and estimates_ready)
    price_rows = _display_value(coverage.get("price_rows"), "0")
    dcf_reason = _display_field_list(
        dcf.get("reason_not_ready") or dcf.get("missing_dcf_fields"),
        "No missing DCF fields flagged",
    )
    peer_reason = _sentence_value(peer.get("next_peer_action") or peer.get("missing_peer_reason"))
    handoff_line = _stock_report_data_health_handoff_line(
        ticker=ticker,
        dcf_status_text=dcf_status_text,
        monitor_context=monitor_context,
        price_ready=price_ready,
        peer_ready=peer_ready,
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
    )

    if price_ready:
        price_line = f"Price history is usable now ({price_rows} local row(s)); keep it fresh before relying on setup or risk context."
    else:
        price_line = f"Price history is the first required input. Run `make focus-price TICKER={ticker}` or use the price import flow before interpreting setup."

    if monitor_context:
        dcf_line = "Operating-company DCF is excluded for this ETF/index/fund monitor context; no fundamentals import is required for company valuation."
    elif dcf_status_text == "ready":
        dcf_line = "Fundamentals and standalone DCF inputs are usable now; review assumptions, sensitivity, and source readiness before interpreting valuation context."
    elif not price_ready:
        dcf_line = (
            f"Wait on fundamentals / DCF interpretation until price coverage starts. "
            f"After `make focus-price TICKER={ticker}` is resolved, run `make focus-fundamentals TICKER={ticker}` for the next DCF fields."
        )
    else:
        dcf_line = (
            f"Fundamentals / DCF are blocked: {dcf_reason}. Inspect `make focus-fundamentals TICKER={ticker}`, "
            f"then use `make sec-stage TICKERS={ticker}` when SEC_USER_AGENT is configured or prepare trusted "
            "manual fundamentals rows before `make imports-validate`, `make imports-preview`, `make imports-apply`, "
            "and `make dcf-readiness`."
        )

    if monitor_context:
        peer_line = "Peer valuation is excluded for monitor context; peer rows are optional context, not a required company-valuation input."
    elif peer_ready:
        peer_line = "Peer context is usable now; review mapped peers and source readiness before interpreting peer-relative context."
    elif dcf_status_text != "ready":
        peer_line = "Peer valuation should wait until trusted price, fundamentals, and DCF inputs are ready."
    else:
        peer_suffix = "" if "data/imports/peers.csv" in peer_reason else " Add source-backed mappings in `data/imports/peers.csv`."
        peer_line = f"Peer context is the next proof path after DCF: {peer_reason}.{peer_suffix}"

    if optional_ready:
        optional_line = "Earnings and analyst-estimate context is available from trusted local rows; treat it as context, not a recommendation."
    else:
        optional_line = (
            "Earnings and analyst estimates remain optional and locked until trusted local rows are imported with "
            "`make templates`, `make imports-validate`, `make imports-preview`, and `make imports-apply`."
        )

    return [
        handoff_line,
        f"- Price proof path: {price_line}",
        f"- Fundamentals / DCF proof path: {dcf_line}",
        f"- Peer proof path: {peer_line}",
        f"- Optional context proof path: {optional_line}",
        "- Import paths, rejected-row files, and credential state are listed in the Source Readiness Check below.",
    ]


def _stock_report_peer_unlock_lines(
    *,
    ticker: str,
    peer: dict[str, Any],
    dcf_status_text: str,
    monitor_context: bool,
    peer_ready: Any,
    next_peer_action: str,
) -> list[str]:
    trend_ready = _is_ready_flag(peer.get("peer_trend_comparison_ready"))
    valuation_ready = any(
        _is_ready_flag(value)
        for value in (peer.get("peer_valuation_comparison_ready"), peer.get("peer_dcf_comparison_ready"), peer_ready)
    )
    peer_count = _display_value(peer.get("peer_count"), "0")
    mapping_status = _display_report_status(peer.get("mapping_status"), "not ready")
    blocker = _display_report_status(peer.get("peer_blocker_type") or peer.get("missing_peer_reason"), "not ready")
    if monitor_context:
        return [
            "- What this means: peer-relative company valuation is excluded for ETF/index/fund monitor context.",
            "- What can be reviewed now: market, theme, liquidity, or risk proxy context from the ticker's own ready local inputs.",
            "- What is still locked: operating-company peer valuation is not a repair item for this monitor role.",
            "- Trusted input path: no peer import is required for monitor context; do not add guessed peers to force valuation.",
        ]
    if dcf_status_text.lower() != "ready":
        return [
            "- What this means: peer valuation waits behind price, fundamentals, and standalone DCF readiness.",
            "- What can be reviewed now: only the ready local inputs listed above; peer rows should not create valuation context yet.",
            "- What is still locked: peer trend and peer valuation remain withheld until core company inputs are ready.",
            f"- Trusted input path: resolve fundamentals / DCF first, then use `make focus-peers TICKER={ticker}` if peer context is still needed.",
        ]
    if valuation_ready:
        return [
            "- What this means: peer context is ready from source-backed peer inputs; review mapped peers and source readiness before interpreting relative valuation.",
            f"- What can be reviewed now: peer trend status={_display_report_status(trend_ready)}; peer valuation status={_display_report_status(valuation_ready)}; peer count={peer_count}.",
            "- What is still locked: any missing peer metric listed below stays unavailable and should not be inferred from sector or industry fallback.",
            f"- Trusted input path: review `data/peers.csv` and rerun `make focus-peers TICKER={ticker}` before relying on peer-relative context.",
        ]
    if trend_ready:
        reviewable_peer_context = (
            "peer trend comparison can be reviewed from mapped peer price history, but peer-relative valuation, "
            "premium/discount, and peer DCF comparison stay withheld."
        )
    else:
        reviewable_peer_context = "peer trend status=not ready until mapped peer price history is sufficient."
    return [
        f"- What this means: standalone DCF can be reviewed, but peer-relative valuation is locked by {blocker}.",
        f"- What can be reviewed now: DCF assumptions and sensitivity; {reviewable_peer_context} Mapped peer count={peer_count}.",
        "- What is still locked: peer valuation, peer-relative premium/discount, and peer DCF comparison until source-backed peer mappings and peer valuation inputs pass readiness.",
        f"- Trusted input path: add source-backed rows in `data/imports/peers.csv`, then run `make templates`, `make imports-validate`, `make imports-preview`, and `make imports-apply`.",
        f"- Next peer action: {_sentence_value(next_peer_action, f'Run make focus-peers TICKER={ticker}')}.",
        f"- Fallback boundary: sector or industry context is fallback only; it is not trusted manual peer data. Current mapping status={mapping_status}.",
    ]


def _stock_report_peer_evidence_ladder_lines(
    *,
    ticker: str,
    peer: dict[str, Any],
    dcf_status_text: str,
    monitor_context: bool,
    peer_ready: Any,
) -> list[str]:
    trend_ready = _is_ready_flag(peer.get("peer_trend_comparison_ready"))
    valuation_ready = any(
        _is_ready_flag(value)
        for value in (peer.get("peer_valuation_comparison_ready"), peer.get("peer_dcf_comparison_ready"), peer_ready)
    )
    peer_count = _display_value(peer.get("peer_count"), "0")
    mapping_status = _display_report_status(peer.get("mapping_status"), "not ready")
    blocker = _display_report_status(peer.get("peer_blocker_type") or peer.get("missing_peer_reason"), "not ready")
    if monitor_context:
        return [
            "- Peer ladder: monitor context; operating-company peer valuation is excluded rather than repaired.",
            "- Mapping evidence: optional context only for ETF/index/fund monitor rows; do not add guessed peers to force company valuation.",
            "- Trend evidence: use the ticker's own ready market, theme, liquidity, or risk inputs instead.",
            "- Valuation evidence: excluded; no peer-relative premium/discount or peer DCF comparison is shown.",
        ]
    if dcf_status_text.lower() != "ready":
        return [
            "- Peer ladder: paused behind core company readiness.",
            f"- Mapping evidence: mapping status={mapping_status}; peer count={peer_count}. Do not use peer rows to bypass missing price, fundamentals, or DCF inputs.",
            "- Trend evidence: withheld until core company readiness passes and mapped peer price history is useful.",
            "- Valuation evidence: withheld until standalone DCF plus source-backed peer mappings and peer valuation inputs pass readiness.",
            f"- Next safe command: `make focus-peers TICKER={ticker}` only after the core DCF blockers are resolved.",
        ]
    if valuation_ready:
        return [
            "- Peer ladder: ready for source-backed peer context.",
            f"- Mapping evidence: mapping status={mapping_status}; peer count={peer_count}.",
            f"- Trend evidence: {_display_report_status(trend_ready)} from mapped peer price history.",
            "- Valuation evidence: available only from trusted peer mappings and peer valuation inputs; review source readiness before interpretation.",
            f"- Next safe command: `make focus-peers TICKER={ticker}` to inspect mapped peer evidence before reading relative context.",
        ]
    trend_line = (
        "possible from mapped peer price history"
        if trend_ready
        else "not ready until mapped peer price history is sufficient"
    )
    return [
        "- Peer ladder: standalone DCF can be reviewed before peer valuation is ready.",
        f"- Mapping evidence: mapping status={mapping_status}; peer count={peer_count}; blocker={blocker}.",
        f"- Trend evidence: {trend_line}.",
        "- Valuation evidence: locked; do not show peer-relative premium/discount, peer valuation comparison, or peer DCF comparison.",
        "- Trusted peer path: add source-backed rows in `data/imports/peers.csv`, then run `make imports-validate`, `make imports-preview`, `make imports-apply`, `make readiness`, and `make peer-mapping-queue TOP_N=25`.",
    ]


def _stock_report_optional_context_ladder_lines(
    *,
    ticker: str,
    earnings_ready: Any,
    estimates_ready: Any,
    earnings_summary: dict[str, Any],
    analyst_estimate_summary: dict[str, Any],
) -> list[str]:
    earnings_available = bool(earnings_ready)
    estimates_available = bool(estimates_ready)
    earnings_date = _display_value(
        earnings_summary.get("next_earnings_date") or earnings_summary.get("latest_report_date"),
        "not available",
    )
    estimate_context = _display_value(
        analyst_estimate_summary.get("current_quarter_eps")
        or analyst_estimate_summary.get("current_year_eps")
        or analyst_estimate_summary.get("target_mean_price"),
        "not available",
    )
    lines = [
        "- Optional context ladder: earnings and analyst estimates add timing, consensus, and revision context only; they never create a valuation conclusion by themselves.",
    ]
    if earnings_available:
        lines.append(
            f"- Earnings evidence: available from trusted local rows; next known/report date={earnings_date}. Treat it as event timing context."
        )
    else:
        lines.append(
            "- Earnings evidence: locked; missing trusted local CSV input is an intentional state, not broken analysis. "
            "Use schema-only templates first; templates are not data."
        )
    if estimates_available:
        lines.append(
            f"- Analyst-estimate evidence: available from trusted local rows; sample consensus field={estimate_context}. Treat consensus as context, not a conclusion."
        )
    else:
        lines.append(
            "- Analyst-estimate evidence: locked; missing trusted local CSV input is an intentional state, not hidden consensus analysis."
        )
    lines.extend(
        [
            "- Earnings path: `make templates` -> place trusted rows in `data/staged/earnings/` -> `make import-earnings` -> `make imports-validate` -> `make imports-preview` -> `make imports-apply`.",
            "- Analyst-estimates path: `make templates` -> place trusted rows in `data/staged/analyst_estimates/` -> `make import-analyst-estimates` -> `make imports-validate` -> `make imports-preview` -> `make imports-apply`.",
            "- Rejected-row checks: review `data/rejected/earnings_import_rejected.csv` and `data/rejected/analyst_estimates_import_rejected.csv` before trusting optional context.",
            f"- Rebuild proof: run `make optional-context-readiness`, then `make stock-report-md TICKER={ticker}` to confirm optional sections changed from locked to available.",
            "- No-conclusion boundary: missing earnings or estimates must not appear as event timing, consensus, revision, upside, downside, undervalued, or overvalued analysis.",
        ]
    )
    return lines


def _stock_report_unlock_command_lines(
    *,
    ticker: str,
    readiness: dict[str, Any],
    dcf_status_text: str,
    peer_ready: Any,
    earnings_ready: Any,
    estimates_ready: Any,
) -> list[str]:
    asset_type = _display_value(readiness.get("asset_type"), "").lower()
    monitor_context = dcf_status_text == "excluded" or asset_type in {"etf", "index_proxy", "fund"}
    price_ready = bool(readiness.get("price_ready"))
    fundamentals_ready = bool(readiness.get("fundamentals_ready"))
    peer_is_ready = bool(peer_ready)
    optional_ready = bool(earnings_ready) and bool(estimates_ready)
    needs_company_proof_packet = (
        not monitor_context and (not fundamentals_ready or dcf_status_text != "ready" or not peer_is_ready)
    )

    lines = [
        "- Copy-only: these are local research commands to copy when you choose; the report does not run imports or refreshes and does not connect to external accounts.",
        f"- Inspect this ticker: `make stock-report-md TICKER={ticker}`.",
    ]
    if needs_company_proof_packet:
        lines.append(f"- One-company proof packet: `make trusted-data-pilot-packet TICKER={ticker}`.")
    if not price_ready:
        lines.extend(
            [
                f"- Price first: `make focus-price TICKER={ticker}`.",
                f"- Price coverage checklist: `make price-worklist TICKERS={ticker} TOP_N=10`.",
                "- Price import safety: `make price-validate && make price-preview && make price-apply`.",
                "- Price rebuild proof: `make price-coverage TOP_N=25 && make readiness` before interpreting setup, trend, or valuation context.",
            ]
        )
    else:
        lines.append(f"- Price source readiness: `make focus-price TICKER={ticker}`.")

    if monitor_context:
        lines.append("- Fundamentals / DCF: no operating-company DCF command is required for ETF/index/fund monitor context.")
    elif not fundamentals_ready or dcf_status_text != "ready":
        lines.extend(
            [
                f"- Fundamentals / DCF: `make focus-fundamentals TICKER={ticker}`.",
                f"- SEC/manual import checklist: `make sec-stage-queue TICKERS={ticker} TOP_N=10`.",
                "- Fundamentals import safety: `make imports-validate && make imports-preview && make imports-apply`.",
                "- DCF rebuild proof: `make dcf-readiness && make readiness` before reading standalone DCF output.",
            ]
        )
    else:
        lines.append(f"- DCF review: `make focus-fundamentals TICKER={ticker}`.")

    if monitor_context:
        lines.append("- Peers: no peer-valuation command is required for ETF/index/fund monitor context.")
    elif not peer_is_ready:
        lines.extend(
            [
                f"- Peer mapping: `make focus-peers TICKER={ticker}`.",
                f"- Peer mapping checklist: `make peer-mapping-queue TICKERS={ticker} TOP_N=10`.",
                "- Peer import safety: `make templates && make imports-validate && make imports-preview && make imports-apply`.",
                f"- Peer rebuild proof: `make readiness && make peer-mapping-queue TICKERS={ticker} TOP_N=10` before reading peer-relative valuation.",
            ]
        )
    else:
        lines.append(f"- Peer review: `make focus-peers TICKER={ticker}`.")

    if not optional_ready:
        lines.extend(
            [
                f"- Optional context checklist: `make optional-context-worklist TICKERS={ticker} TOP_N=10`.",
                "- Optional templates: `make templates`.",
                "- Earnings import: `make import-earnings`.",
                "- Analyst-estimates import: `make import-analyst-estimates`.",
                "- Optional import safety: `make imports-validate && make imports-preview && make imports-apply`.",
                "- Optional-context rebuild proof: `make optional-context-readiness && make readiness` before treating earnings or estimates as available context.",
            ]
        )
    return lines


def _load_local_context(ticker: str, output_dir: Path, data_dir: Path) -> dict[str, Any]:
    symbol = ticker.upper().strip()

    def row_from(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        frame = pd.read_csv(path)
        if "ticker" not in frame.columns:
            return {}
        matches = frame.loc[frame["ticker"].astype(str).str.upper().str.strip().eq(symbol)]
        if matches.empty:
            return {}
        return matches.iloc[-1].to_dict()

    return {
        "readiness": row_from(data_dir / "reports" / "ticker_readiness_report.csv"),
        "decision": row_from(output_dir / "research_decisions.csv"),
        "price_coverage": row_from(data_dir / "price_coverage_report.csv"),
        "dcf": row_from(data_dir / "dcf_readiness.csv"),
        "peer": row_from(data_dir / "reports" / "peer_readiness_report.csv"),
        "earnings": row_from(data_dir / "earnings_readiness.csv"),
        "analyst_estimates": row_from(data_dir / "analyst_estimates_readiness.csv"),
    }


def build_stock_report_markdown(report: StockReport, local_context: dict[str, Any] | None = None) -> str:
    payload = report.to_dict()
    local_context = local_context or {}
    readiness = dict(local_context.get("readiness", {}))
    decision = local_context.get("decision", {})
    coverage = local_context.get("price_coverage", {})
    dcf = local_context.get("dcf", {})
    peer = local_context.get("peer", {})
    earnings = local_context.get("earnings", {})
    estimates = local_context.get("analyst_estimates", {})
    valuation_readiness = payload.get("valuation_readiness", {})
    freshness = payload.get("data_freshness", [])
    source_lines = []
    for item in freshness:
        provider = _display_value(item.get("provider"))
        official = "official" if item.get("official") else "research-grade / local"
        freshness_summary = _source_freshness_summary(item)
        notes = "; ".join(str(note) for note in item.get("notes", []) if str(note).strip())
        source_lines.append(f"- {provider}: {official}; {freshness_summary}" + (f"; {notes}" if notes else ""))
    if not source_lines:
        source_lines.append("- Not available")

    valuation_status = _display_value(payload.get("valuation_snapshot", {}).get("status")).lower()
    if "price_ready" not in readiness:
        readiness["price_ready"] = _has_report_value(payload.get("price_snapshot", {}).get("price"))
    if "momentum_ready" not in readiness:
        performance = payload.get("performance", {})
        readiness["momentum_ready"] = any(
            _has_report_value(performance.get(field)) for field in ("one_month", "three_month", "one_year")
        )
    if "fundamentals_ready" not in readiness:
        financials = payload.get("financial_summary", {})
        readiness["fundamentals_ready"] = valuation_status == "calculated" or any(
            _has_report_value(financials.get(field))
            for field in ("revenue", "free_cash_flow", "fcf_margin", "shares_outstanding")
        )
    if "dcf_ready" not in readiness:
        readiness["dcf_ready"] = valuation_status == "calculated"

    dcf_ready = readiness.get("dcf_ready") if "dcf_ready" in readiness else valuation_readiness.get("dcf_ready")
    peer_ready = readiness.get("peer_ready") if "peer_ready" in readiness else valuation_readiness.get("peer_ready")
    earnings_ready = (
        readiness.get("earnings_ready") if "earnings_ready" in readiness else earnings.get("has_trusted_earnings")
    )
    estimates_ready = (
        readiness.get("analyst_estimates_ready")
        if "analyst_estimates_ready" in readiness
        else estimates.get("has_trusted_analyst_estimates")
    )
    asset_type = _display_value(readiness.get("asset_type"))
    dcf_status_text = "excluded" if "dcf" in str(readiness.get("excluded_features", "")).lower() or asset_type.lower() in {"etf", "index_proxy", "fund"} else "ready" if dcf_ready else "blocked"
    optional_locked = not earnings_ready or not estimates_ready
    monitor_context = _stock_report_is_monitor_context(readiness=readiness, decision=decision, dcf_status_text=dcf_status_text)
    missing_lines = _stock_report_missing_data_lines(
        payload,
        monitor_context=monitor_context,
        dcf_status_text=dcf_status_text,
    )
    one_minute_parts = [
        _stock_report_one_minute_state_phrase(
            ticker=report.ticker,
            readiness=readiness,
            dcf_status_text=dcf_status_text,
            peer_ready=peer_ready,
            optional_locked=optional_locked,
            monitor_context=monitor_context,
        ),
        f"Decision: {_display_value(decision.get('decision_subtype') or decision.get('decision_bucket'))}.",
        f"DCF: {dcf_status_text}.",
    ]
    if monitor_context:
        one_minute_parts.append("Monitor context: operating-company DCF and peer valuation are excluded.")
    else:
        one_minute_parts.append(f"Primary blocker: {_display_report_status(decision.get('primary_blocker'))}.")
    peer_blocker = peer.get("peer_blocker_type") or peer.get("missing_peer_reason")
    core_data_before_peers = not monitor_context and dcf_status_text != "ready"
    if core_data_before_peers:
        one_minute_parts.append("Peer workflow: waits for trusted price, fundamentals, and DCF inputs first.")
    elif not monitor_context and bool(peer_ready):
        one_minute_parts.append("Peer workflow: ready for source-backed peer context.")
    elif peer_blocker and not monitor_context and _display_value(peer_blocker) != "Not available":
        one_minute_parts.append(f"Peer workflow: {_display_report_status(peer_blocker)}.")
    if optional_locked:
        one_minute_parts.append("Optional earnings or analyst-estimate context is unavailable until trusted local CSV rows exist.")
    one_minute_next = _humanize_schema_terms(_stock_report_next_action(
        ticker=report.ticker,
        readiness=readiness,
        decision=decision,
        peer=peer,
        dcf_status_text=dcf_status_text,
    ))
    if one_minute_next != "Not available":
        one_minute_parts.append(f"Next: {_sentence_value(one_minute_next)}.")
    one_minute_summary = " ".join(part for part in one_minute_parts if part)
    purpose_fields = _stock_report_purpose_fields(
        ticker=report.ticker,
        readiness=readiness,
        decision=decision,
        dcf_status_text=dcf_status_text,
        peer_ready=peer_ready,
        relative_status=payload.get("valuation_snapshot", {}).get("relative_valuation", {}).get("status"),
    )
    purpose_decision = {**decision, **purpose_fields}
    operator_summary = _stock_report_operator_summary(ticker=report.ticker, readiness=readiness, decision=purpose_decision)
    decision_primary_blocker = "monitor context" if monitor_context else _display_report_status(decision.get("primary_blocker"))
    if monitor_context:
        peer_blocker_display = "monitor context"
        mapping_status_display = "monitor context"
        peer_next_action_display = "No peer import is required; operating-company peer valuation is excluded for ETF/index/fund monitor context."
    elif core_data_before_peers:
        peer_blocker_display = "blocked until fundamentals / DCF"
        mapping_status_display = "waiting for price, fundamentals, and DCF"
        peer_next_action_display = "Peer-relative valuation should wait until trusted price, fundamentals, and DCF inputs are ready."
    else:
        peer_blocker_display = _display_report_status(peer.get("peer_blocker_type"))
        mapping_status_display = _display_report_status(peer.get("mapping_status"))
        peer_next_action_display = _display_value(peer.get("next_peer_action") or peer.get("missing_peer_reason"))
        if (peer.get("peer_ready") or readiness.get("peer_ready")) and peer_blocker_display == "not available":
            peer_blocker_display = "ready"
        elif peer_blocker_display == "not available":
            peer_blocker_display = "waiting for source-backed peer inputs"
        if mapping_status_display == "not available":
            mapping_status_display = "not configured"
        if peer_next_action_display == "Not available":
            peer_next_action_display = "Add source-backed peer mappings and peer inputs before peer-relative valuation."
        if (peer.get("peer_ready") or readiness.get("peer_ready")) and peer_blocker_display == "not available":
            peer_blocker_display = "ready"
        elif peer_blocker_display == "not available":
            peer_blocker_display = "waiting for source-backed peer inputs"
        if mapping_status_display == "not available":
            mapping_status_display = "not configured"
        if peer_next_action_display == "Not available":
            peer_next_action_display = "Add source-backed peer mappings and peer inputs before peer-relative valuation."
    source_audit_lines = _stock_report_source_audit_lines(
        ticker=report.ticker,
        readiness=readiness,
        coverage=coverage,
        dcf=dcf,
        peer=peer,
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
        dcf_status_text=dcf_status_text,
    )
    valuation_lines = _stock_report_valuation_lines(
        valuation_snapshot=payload.get("valuation_snapshot", {}),
        valuation_readiness=valuation_readiness,
        dcf=dcf,
        dcf_status_text=dcf_status_text,
        monitor_context=monitor_context,
    )
    dcf_calculation_lines = _stock_report_dcf_calculation_path_lines(
        valuation_snapshot=payload.get("valuation_snapshot", {}),
        valuation_readiness=valuation_readiness,
        dcf=dcf,
        dcf_status_text=dcf_status_text,
        monitor_context=monitor_context,
    )
    dcf_input_triage_lines = _stock_report_dcf_input_triage_lines(
        ticker=report.ticker,
        dcf=dcf,
        valuation_readiness=valuation_readiness,
        dcf_status_text=dcf_status_text,
        monitor_context=monitor_context,
    )
    valuation_boundary_lines = _stock_report_valuation_boundary_checklist_lines(
        dcf_status_text=dcf_status_text,
        monitor_context=monitor_context,
        peer_ready=peer_ready,
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
    )
    peer_unlock_lines = _stock_report_peer_unlock_lines(
        ticker=report.ticker,
        peer=peer,
        dcf_status_text=dcf_status_text,
        monitor_context=monitor_context,
        peer_ready=peer_ready,
        next_peer_action=peer_next_action_display,
    )
    peer_evidence_ladder_lines = _stock_report_peer_evidence_ladder_lines(
        ticker=report.ticker,
        peer=peer,
        dcf_status_text=dcf_status_text,
        monitor_context=monitor_context,
        peer_ready=peer_ready,
    )
    ready_features = _display_report_list(readiness.get("ready_features"), "none yet")
    blocked_features = _display_report_list(readiness.get("blocked_features"), "none")
    excluded_features = _display_report_list(readiness.get("excluded_features"), "none")
    if monitor_context:
        supported_now = (
            "Monitor context is supported where local price, liquidity, correlation, and theme data are available. "
            "Operating-company DCF and peer valuation are excluded rather than treated as failed inputs."
        )
    elif dcf_status_text == "ready":
        supported_now = (
            "Company-level review can use local price context, fundamentals, and standalone DCF assumptions. "
            "Peer-relative valuation is shown only if trusted peer mappings and peer metrics are also ready."
        )
    else:
        supported_now = (
            "Use available price or setup context only. Company-level valuation stays blocked until trusted fundamentals, "
            "free cash flow or margin inputs, share count, and DCF fields are ready."
        )
    locked_now = (
        f"Blocked features: {blocked_features}. Excluded features: {excluded_features}. "
        "Unavailable sections are intentionally locked; missing data is not inferred."
    )
    analysis_quality_lines = _stock_report_analysis_quality_lines(
        readiness=readiness,
        dcf_status_text=dcf_status_text,
        peer_ready=peer_ready,
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
    )
    function_quality_lines = _stock_report_function_quality_lines(
        readiness=readiness,
        dcf_status_text=dcf_status_text,
        peer_ready=peer_ready,
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
    )
    methodology_lines = _stock_report_methodology_lines(
        readiness=readiness,
        dcf_status_text=dcf_status_text,
        peer_ready=peer_ready,
    )
    source_logic_lines = _stock_report_source_logic_lines(
        readiness=readiness,
        dcf_status_text=dcf_status_text,
        peer_ready=peer_ready,
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
    )
    executive_summary_lines = _stock_report_executive_summary_lines(
        ticker=report.ticker,
        analysis_quality_lines=analysis_quality_lines,
        supported_now=supported_now,
        locked_now=locked_now,
        next_action=one_minute_next,
    )
    evaluation_snapshot_lines = _stock_report_evaluation_snapshot_lines(
        supported_now=supported_now,
        locked_now=locked_now,
        next_action=one_minute_next,
        analysis_quality_lines=analysis_quality_lines,
        dcf_status_text=dcf_status_text,
        monitor_context=monitor_context,
        peer_ready=peer_ready,
    )
    report_mode = _stock_report_mode_from_quality_lines(analysis_quality_lines)
    at_a_glance_lines = _stock_report_at_a_glance_lines(
        mode=report_mode,
        decision=decision,
        dcf_status_text=dcf_status_text,
        dcf=dcf,
        readiness=readiness,
        peer_ready=peer_ready,
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
        next_action=one_minute_next,
        valuation_snapshot=payload.get("valuation_snapshot", {}),
    )
    proof_checklist_lines = _stock_report_proof_checklist_lines(
        ticker=report.ticker,
        report_mode=report_mode,
        dcf_status_text=dcf_status_text,
        monitor_context=monitor_context,
        price_ready=bool(readiness.get("price_ready")),
        peer_ready=peer_ready,
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
        next_action=one_minute_next,
        locked_now=locked_now,
    )
    mode_guide_lines = _stock_report_mode_guide_lines(report_mode)
    reader_guide_lines = _stock_report_reader_guide_lines(
        dcf_status_text=dcf_status_text,
        monitor_context=monitor_context,
        price_ready=bool(readiness.get("price_ready")),
        peer_ready=peer_ready,
    )
    reader_question_lines = _stock_report_reader_question_lines(
        ticker=report.ticker,
        supported_now=supported_now,
        locked_now=locked_now,
        next_action=one_minute_next,
        dcf_status_text=dcf_status_text,
        monitor_context=monitor_context,
        price_ready=bool(readiness.get("price_ready")),
        peer_ready=peer_ready,
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
    )
    next_layer_lines = _stock_report_next_layer_lines(
        ticker=report.ticker,
        dcf_status_text=dcf_status_text,
        monitor_context=monitor_context,
        price_ready=bool(readiness.get("price_ready")),
        peer_ready=peer_ready,
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
    )
    best_review_path_lines = _stock_report_best_review_path_lines(
        ticker=report.ticker,
        dcf_status_text=dcf_status_text,
        monitor_context=monitor_context,
        price_ready=bool(readiness.get("price_ready")),
        peer_ready=peer_ready,
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
    )
    data_unlock_lines = _stock_report_data_unlock_lines(
        ticker=report.ticker,
        readiness=readiness,
        coverage=coverage,
        dcf=dcf,
        peer=peer,
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
        dcf_status_text=dcf_status_text,
    )
    unlock_command_lines = _stock_report_unlock_command_lines(
        ticker=report.ticker,
        readiness=readiness,
        dcf_status_text=dcf_status_text,
        peer_ready=peer_ready,
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
    )
    optional_context_ladder_lines = _stock_report_optional_context_ladder_lines(
        ticker=report.ticker,
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
        earnings_summary=payload.get("earnings_summary", {}),
        analyst_estimate_summary=payload.get("analyst_estimate_summary", {}),
    )

    report_lines = [
        f"# {report.ticker} Single-Stock Research Report",
        "",
        "Research-only local report. It summarizes readiness and does not provide allocation instructions.",
        "Visitor scan: read At A Glance, Reader Guide, Evaluation Snapshot, and Proof Checklist first; deeper sections only explain the evidence behind those gates.",
        "",
        "## At A Glance",
        *at_a_glance_lines,
        "",
        "## Reader Guide",
        *reader_question_lines,
        "",
        "## Evaluation Snapshot",
        *evaluation_snapshot_lines,
        "",
        "## Proof Checklist",
        *proof_checklist_lines,
        "",
        "## Best Review Path",
        *best_review_path_lines,
        "",
        "## How To Read This Report",
        *reader_guide_lines,
        "",
        "## Executive Summary",
        *executive_summary_lines,
        "",
        "## Analysis Mode Guide",
        *mode_guide_lines,
        "",
        "## One-Minute Status",
        one_minute_summary,
        "",
        "## What We Can Analyze Now",
        f"- Ready inputs: {ready_features}.",
        f"- Supported now: {supported_now}",
        f"- Still locked or excluded: {locked_now}",
        "",
        "## Next Layer To Prove",
        *next_layer_lines,
        "",
        "## Data And App Method",
        *source_logic_lines,
        "",
        "## Analysis Quality",
        *analysis_quality_lines,
        "",
        "## Methodology",
        *methodology_lines,
        "",
        "## Evaluation Function Check",
        *function_quality_lines,
        "",
        "## What This Stock Is",
        f"- Ticker: {report.ticker}",
        f"- Asset type: {_display_value(readiness.get('asset_type'))}",
        f"- Current role: {_brief_value(purpose_fields.get('purpose_thesis'), 'Purpose:')}",
        "",
        "## Decision",
        f"- Bucket: {_display_value(decision.get('decision_bucket'))}",
        f"- Subtype: {_display_value(decision.get('decision_subtype'))}",
        f"- Boundary: {_stock_report_decision_boundary(readiness=readiness, decision=decision)}",
        f"- Primary blocker: {decision_primary_blocker}",
        f"- Main reason: {_humanize_schema_terms(_display_value(decision.get('main_reason')))}",
        f"- Next action: {_humanize_schema_terms(one_minute_next)}",
        "",
        "## Purpose Evaluation",
        "Research-only purpose brief. It separates what local data supports from what remains locked or excluded.",
        f"- Thesis: {_brief_value(purpose_fields.get('purpose_thesis'), 'Purpose:')}",
        f"- Alignment: {_public_report_brief(purpose_fields.get('purpose_alignment'), 'Purpose alignment:')}",
        f"- Research review summary: {_public_report_brief(operator_summary, 'Research review summary:')}",
        f"- Setup: {_public_report_brief(purpose_fields.get('setup_evaluation'), 'Setup status:')}",
        f"- Valuation boundary: {_display_value(purpose_fields.get('valuation_evaluation'))}",
        "",
        "## Supported Analysis",
        f"- Supported analysis: {_brief_value(_proof_language(purpose_fields.get('supported_analysis')), 'Supported analysis:')}",
        "",
        "## Locked Analysis",
        f"- Currently withheld: {_brief_value(purpose_fields.get('unsupported_analysis'), 'Unsupported analysis:', 'Currently withheld:')}",
        "",
        "## Setup / Momentum",
        f"- {_public_report_brief(purpose_fields.get('setup_evaluation'), 'Setup status:')}",
        f"- 1M performance: {_format_pct(payload.get('performance', {}).get('one_month'))}",
        f"- 3M performance: {_format_pct(payload.get('performance', {}).get('three_month'))}",
        f"- 1Y performance: {_format_pct(payload.get('performance', {}).get('one_year'))}",
        *_stock_report_volatility_lines(payload),
        "",
        "## Risk Notes",
        f"- Risk watchpoint: {_public_report_brief(purpose_fields.get('risk_watchpoint'), 'Risk watchpoint:')}",
        f"- Invalidation condition: {_public_report_brief(purpose_fields.get('invalidation_condition'))}",
        "",
        "## Next Research Step",
        f"- Next research question: {_display_value(purpose_fields.get('next_research_question'))}",
        f"- Review priority: {_proof_language(purpose_fields.get('review_priority_reason'))}",
        f"- Data-confidence explanation: {_proof_language(purpose_fields.get('confidence_explanation'))}",
        "",
        "## Data Readiness",
        f"- Overall state: {_display_value(readiness.get('overall_readiness_state'))}",
        f"- Price ready: {_display_report_status(readiness.get('price_ready'))}",
        f"- Momentum ready: {_display_report_status(readiness.get('momentum_ready'))}",
        f"- Liquidity ready: {_display_report_status(readiness.get('liquidity_ready'))}",
        f"- Correlation ready: {_display_report_status(readiness.get('correlation_ready'))}",
        f"- Fundamentals ready: {_display_report_status(readiness.get('fundamentals_ready'))}",
        f"- DCF ready: {_display_report_status(dcf_ready)}",
        f"- Peer ready: {_display_report_status(peer_ready)}",
        f"- Earnings ready: {_display_report_status(earnings_ready)}",
        f"- Analyst estimates ready: {_display_report_status(estimates_ready)}",
        f"- Blocked features: {_display_report_list(readiness.get('blocked_features'), 'none')}",
        f"- Excluded features: {_display_report_list(readiness.get('excluded_features'), 'none')}",
        "",
        "## Price Coverage",
        f"- Price rows: {_display_value(coverage.get('price_rows'))}",
        f"- First date: {_display_value(coverage.get('first_price_date'))}",
        f"- Last date: {_display_value(coverage.get('last_price_date'))}",
        f"- Missing price reason: {_display_report_list(coverage.get('missing_price_reason'), 'none')}",
        "",
        "## Valuation Readiness",
        *valuation_lines,
        "",
        "## DCF Calculation Path",
        *dcf_calculation_lines,
        "",
        "## DCF Input Triage",
        *dcf_input_triage_lines,
        "",
        "## Valuation Boundary Checklist",
        *valuation_boundary_lines,
        "",
        "## Peer Workflow",
        *peer_unlock_lines,
        *peer_evidence_ladder_lines,
        f"- Peer blocker type: {peer_blocker_display}",
        f"- Mapping status: {mapping_status_display}",
        f"- Peer count: {_display_value(peer.get('peer_count'))}",
        f"- Trend comparison ready: {_display_report_status(peer.get('peer_trend_comparison_ready'))}",
        f"- Valuation comparison ready: {_display_report_status(peer.get('peer_valuation_comparison_ready'))}",
        f"- DCF peer comparison ready: {_display_report_status(peer.get('peer_dcf_comparison_ready'))}",
        f"- Sample peers: {_display_report_list(peer.get('sample_peers'), 'none configured')}",
        f"- Next peer action: {peer_next_action_display}",
        "",
        "## Optional Context Workflow",
        *optional_context_ladder_lines,
        "",
        "## Missing Data",
        *missing_lines,
        "",
        "## Source Readiness",
        *source_lines,
        "",
        "## Missing-Data Proof Summary",
        *data_unlock_lines,
        "",
        "## Copyable Proof Commands",
        *unlock_command_lines,
        "",
        "## Source Readiness Check",
        *source_audit_lines,
    ]
    return "\n".join(report_lines)


def build_readiness_only_markdown(ticker: str, local_context: dict[str, Any], failure_reason: str = "") -> str:
    symbol = ticker.upper().strip()
    readiness = local_context.get("readiness", {})
    decision = local_context.get("decision", {})
    coverage = local_context.get("price_coverage", {})
    dcf = local_context.get("dcf", {})
    peer = local_context.get("peer", {})
    earnings = local_context.get("earnings", {})
    estimates = local_context.get("analyst_estimates", {})
    if not readiness:
        raise LookupError(f"No readiness row was found for {symbol}.")
    asset_type = _display_value(readiness.get("asset_type"))
    dcf_status_text = "excluded" if "dcf" in str(readiness.get("excluded_features", "")).lower() or asset_type.lower() in {"etf", "index_proxy", "fund"} else "ready" if readiness.get("dcf_ready") else "blocked"
    earnings_ready = readiness.get("earnings_ready")
    estimates_ready = readiness.get("analyst_estimates_ready")
    monitor_context = _stock_report_is_monitor_context(readiness=readiness, decision=decision, dcf_status_text=dcf_status_text)
    next_action = _stock_report_next_action(
        ticker=symbol,
        readiness=readiness,
        decision=decision,
        peer=peer,
        dcf_status_text=dcf_status_text,
    )
    purpose_fields = _stock_report_purpose_fields(
        ticker=symbol,
        readiness=readiness,
        decision=decision,
        dcf_status_text=dcf_status_text,
    )
    purpose_decision = {**decision, **purpose_fields}
    operator_summary = _stock_report_operator_summary(ticker=symbol, readiness=readiness, decision=purpose_decision)
    decision_primary_blocker = "monitor context" if monitor_context else _display_report_status(decision.get("primary_blocker"))
    core_data_before_peers = not monitor_context and dcf_status_text != "ready"
    if monitor_context:
        peer_blocker_display = "monitor context"
        mapping_status_display = "monitor context"
        peer_next_action_display = "No peer import is required; operating-company peer valuation is excluded for ETF/index/fund monitor context."
    elif core_data_before_peers:
        peer_blocker_display = "blocked until fundamentals / DCF"
        mapping_status_display = "waiting for price, fundamentals, and DCF"
        peer_next_action_display = "Peer-relative valuation should wait until trusted price, fundamentals, and DCF inputs are ready."
    else:
        peer_blocker_display = _display_report_status(peer.get("peer_blocker_type"))
        mapping_status_display = _display_report_status(peer.get("mapping_status"))
        peer_next_action_display = _display_value(peer.get("next_peer_action") or peer.get("missing_peer_reason"))
    one_minute_summary = " ".join(
        part
        for part in [
            _stock_report_one_minute_state_phrase(
                ticker=symbol,
                readiness=readiness,
                dcf_status_text=dcf_status_text,
                peer_ready=peer.get("peer_ready") or readiness.get("peer_ready"),
                optional_locked=True,
                monitor_context=monitor_context,
            ),
            f"Decision: {_display_value(decision.get('decision_subtype') or decision.get('decision_bucket'))}.",
            "Monitor context: operating-company DCF and peer valuation are excluded." if monitor_context else f"Primary blocker: {_display_report_status(decision.get('primary_blocker'))}.",
            f"DCF: {dcf_status_text}.",
            ""
            if monitor_context
            else "Peer workflow: ready for source-backed peer context."
            if bool(peer.get("peer_ready") or readiness.get("peer_ready"))
            else "Peer workflow: waits for trusted price, fundamentals, and DCF inputs first."
            if core_data_before_peers
            else f"Peer workflow: {_display_report_status(peer.get('peer_blocker_type') or peer.get('missing_peer_reason'))}.",
            "Optional earnings or analyst-estimate context is unavailable until trusted local CSV rows exist.",
            f"Next: {_sentence_value(next_action)}.",
        ]
        if part and "Not available" not in part
    )
    valuation_snapshot_for_report = {
        "status": "insufficient_data" if dcf_status_text == "blocked" else dcf_status_text,
        "dcf_result": {"status": "insufficient_data" if dcf_status_text == "blocked" else dcf_status_text},
        "relative_valuation": {
            "status": "insufficient_data",
            "peer_count": peer.get("peer_count"),
            "missing_fields": ["trusted_peer_inputs"],
        },
    }
    valuation_lines = _stock_report_valuation_lines(
        valuation_snapshot=valuation_snapshot_for_report,
        valuation_readiness={"dcf_missing_fields": []},
        dcf=dcf,
        dcf_status_text=dcf_status_text,
        monitor_context=monitor_context,
    )
    dcf_calculation_lines = _stock_report_dcf_calculation_path_lines(
        valuation_snapshot=valuation_snapshot_for_report,
        valuation_readiness={"dcf_missing_fields": []},
        dcf=dcf,
        dcf_status_text=dcf_status_text,
        monitor_context=monitor_context,
    )
    dcf_input_triage_lines = _stock_report_dcf_input_triage_lines(
        ticker=symbol,
        dcf=dcf,
        valuation_readiness={"dcf_missing_fields": []},
        dcf_status_text=dcf_status_text,
        monitor_context=monitor_context,
    )
    valuation_boundary_lines = _stock_report_valuation_boundary_checklist_lines(
        dcf_status_text=dcf_status_text,
        monitor_context=monitor_context,
        peer_ready=peer.get("peer_ready") or readiness.get("peer_ready"),
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
    )
    peer_unlock_lines = _stock_report_peer_unlock_lines(
        ticker=symbol,
        peer=peer,
        dcf_status_text=dcf_status_text,
        monitor_context=monitor_context,
        peer_ready=peer.get("peer_ready") or readiness.get("peer_ready"),
        next_peer_action=peer_next_action_display,
    )
    peer_evidence_ladder_lines = _stock_report_peer_evidence_ladder_lines(
        ticker=symbol,
        peer=peer,
        dcf_status_text=dcf_status_text,
        monitor_context=monitor_context,
        peer_ready=peer.get("peer_ready") or readiness.get("peer_ready"),
    )
    ready_features = _display_report_list(readiness.get("ready_features"), "none yet")
    blocked_features = _display_report_list(readiness.get("blocked_features"), "none")
    excluded_features = _display_report_list(readiness.get("excluded_features"), "none")
    if monitor_context:
        supported_now = (
            "Monitor context is supported where local price, liquidity, correlation, and theme data are available. "
            "Operating-company DCF and peer valuation are excluded rather than treated as failed inputs."
        )
    elif dcf_status_text == "ready":
        supported_now = (
            "Company-level review can use local price context, fundamentals, and standalone DCF assumptions. "
            "Peer-relative valuation is shown only if trusted peer mappings and peer metrics are also ready."
        )
    else:
        supported_now = (
            "Use available price or setup context only. Company-level valuation stays blocked until trusted fundamentals, "
            "free cash flow or margin inputs, share count, and DCF fields are ready."
        )
    locked_now = (
        f"Blocked features: {blocked_features}. Excluded features: {excluded_features}. "
        "Unavailable sections are intentionally locked; missing data is not inferred."
    )
    analysis_quality_lines = _stock_report_analysis_quality_lines(
        readiness=readiness,
        dcf_status_text=dcf_status_text,
        peer_ready=peer.get("peer_ready") or readiness.get("peer_ready"),
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
    )
    function_quality_lines = _stock_report_function_quality_lines(
        readiness=readiness,
        dcf_status_text=dcf_status_text,
        peer_ready=peer.get("peer_ready") or readiness.get("peer_ready"),
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
    )
    methodology_lines = _stock_report_methodology_lines(
        readiness=readiness,
        dcf_status_text=dcf_status_text,
        peer_ready=peer.get("peer_ready") or readiness.get("peer_ready"),
    )
    source_logic_lines = _stock_report_source_logic_lines(
        readiness=readiness,
        dcf_status_text=dcf_status_text,
        peer_ready=peer.get("peer_ready") or readiness.get("peer_ready"),
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
    )
    executive_summary_lines = _stock_report_executive_summary_lines(
        ticker=symbol,
        analysis_quality_lines=analysis_quality_lines,
        supported_now=supported_now,
        locked_now=locked_now,
        next_action=next_action,
    )
    evaluation_snapshot_lines = _stock_report_evaluation_snapshot_lines(
        supported_now=supported_now,
        locked_now=locked_now,
        next_action=next_action,
        analysis_quality_lines=analysis_quality_lines,
        dcf_status_text=dcf_status_text,
        monitor_context=monitor_context,
        peer_ready=peer.get("peer_ready") or readiness.get("peer_ready"),
    )
    report_mode = _stock_report_mode_from_quality_lines(analysis_quality_lines)
    at_a_glance_lines = _stock_report_at_a_glance_lines(
        mode=report_mode,
        decision=decision,
        dcf_status_text=dcf_status_text,
        dcf=dcf,
        readiness=readiness,
        peer_ready=peer.get("peer_ready") or readiness.get("peer_ready"),
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
        next_action=next_action,
        valuation_snapshot=valuation_snapshot_for_report,
    )
    proof_checklist_lines = _stock_report_proof_checklist_lines(
        ticker=symbol,
        report_mode=report_mode,
        dcf_status_text=dcf_status_text,
        monitor_context=monitor_context,
        price_ready=bool(readiness.get("price_ready")),
        peer_ready=peer.get("peer_ready") or readiness.get("peer_ready"),
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
        next_action=next_action,
        locked_now=locked_now,
    )
    mode_guide_lines = _stock_report_mode_guide_lines(report_mode)
    reader_guide_lines = _stock_report_reader_guide_lines(
        dcf_status_text=dcf_status_text,
        monitor_context=monitor_context,
        price_ready=bool(readiness.get("price_ready")),
        peer_ready=readiness.get("peer_ready"),
    )
    reader_question_lines = _stock_report_reader_question_lines(
        ticker=symbol,
        supported_now=supported_now,
        locked_now=locked_now,
        next_action=next_action,
        dcf_status_text=dcf_status_text,
        monitor_context=monitor_context,
        price_ready=bool(readiness.get("price_ready")),
        peer_ready=peer.get("peer_ready") or readiness.get("peer_ready"),
        earnings_ready=readiness.get("earnings_ready"),
        estimates_ready=readiness.get("analyst_estimates_ready"),
    )
    next_layer_lines = _stock_report_next_layer_lines(
        ticker=symbol,
        dcf_status_text=dcf_status_text,
        monitor_context=monitor_context,
        price_ready=bool(readiness.get("price_ready")),
        peer_ready=peer.get("peer_ready") or readiness.get("peer_ready"),
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
    )
    data_unlock_lines = _stock_report_data_unlock_lines(
        ticker=symbol,
        readiness=readiness,
        coverage=coverage,
        dcf=dcf,
        peer=peer,
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
        dcf_status_text=dcf_status_text,
    )
    unlock_command_lines = _stock_report_unlock_command_lines(
        ticker=symbol,
        readiness=readiness,
        dcf_status_text=dcf_status_text,
        peer_ready=peer.get("peer_ready") or readiness.get("peer_ready"),
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
    )
    optional_context_ladder_lines = _stock_report_optional_context_ladder_lines(
        ticker=symbol,
        earnings_ready=earnings_ready,
        estimates_ready=estimates_ready,
        earnings_summary=earnings,
        analyst_estimate_summary=estimates,
    )
    lines = [
        f"# {symbol} Single-Stock Research Report",
        "",
        "Research-only local report. It summarizes readiness and does not provide allocation instructions.",
        "Visitor scan: read At A Glance, Reader Guide, Evaluation Snapshot, and Proof Checklist first; deeper sections only explain the evidence behind those gates.",
        "",
        "## At A Glance",
        *at_a_glance_lines,
        "",
        "## Reader Guide",
        *reader_question_lines,
        "",
        "## Evaluation Snapshot",
        *evaluation_snapshot_lines,
        "",
        "## Proof Checklist",
        *proof_checklist_lines,
        "",
        "## How To Read This Report",
        *reader_guide_lines,
        "",
        "This report needs data before analysis because local price history is not ready for price-backed review yet.",
        f"First blocker to resolve: {_display_value(failure_reason)}",
        "",
        "## Executive Summary",
        *executive_summary_lines,
        "",
        "## Analysis Mode Guide",
        *mode_guide_lines,
        "",
        "## One-Minute Status",
        one_minute_summary,
        "",
        "## What We Can Analyze Now",
        f"- Ready inputs: {ready_features}.",
        f"- Supported now: {supported_now}",
        f"- Still locked or excluded: {locked_now}",
        "",
        "## Next Layer To Prove",
        *next_layer_lines,
        "",
        "## Data And App Method",
        *source_logic_lines,
        "",
        "## Analysis Quality",
        *analysis_quality_lines,
        "",
        "## Methodology",
        *methodology_lines,
        "",
        "## Evaluation Function Check",
        *function_quality_lines,
        "",
        "## What This Stock Is",
        f"- Ticker: {symbol}",
        f"- Asset type: {_display_value(readiness.get('asset_type'))}",
        f"- Current role: {_brief_value(purpose_fields.get('purpose_thesis'), 'Purpose:')}",
        "",
        "## Decision",
        f"- Bucket: {_display_value(decision.get('decision_bucket'))}",
        f"- Subtype: {_display_value(decision.get('decision_subtype'))}",
        f"- Boundary: {_stock_report_decision_boundary(readiness=readiness, decision=decision)}",
        f"- Primary blocker: {decision_primary_blocker}",
        f"- Main reason: {_humanize_schema_terms(_display_value(decision.get('main_reason') or readiness.get('missing_data')))}",
        f"- Next action: {next_action}",
        "",
        "## Purpose Evaluation",
        "Research-only purpose brief. It separates what local data supports from what remains locked or excluded.",
        f"- Thesis: {_brief_value(purpose_fields.get('purpose_thesis'), 'Purpose:')}",
        f"- Alignment: {_public_report_brief(purpose_fields.get('purpose_alignment'), 'Purpose alignment:')}",
        f"- Research review summary: {_public_report_brief(operator_summary, 'Research review summary:')}",
        f"- Setup: {_public_report_brief(purpose_fields.get('setup_evaluation'), 'Setup status:')}",
        f"- Valuation boundary: {_display_value(purpose_fields.get('valuation_evaluation'))}",
        "",
        "## Supported Analysis",
        f"- Supported analysis: {_brief_value(_proof_language(purpose_fields.get('supported_analysis')), 'Supported analysis:')}",
        "",
        "## Locked Analysis",
        f"- Currently withheld: {_brief_value(purpose_fields.get('unsupported_analysis'), 'Unsupported analysis:', 'Currently withheld:')}",
        "",
        "## Setup / Momentum",
        f"- {_public_report_brief(purpose_fields.get('setup_evaluation'), 'Setup status:')}",
        "",
        "## Risk Notes",
        f"- Risk watchpoint: {_public_report_brief(purpose_fields.get('risk_watchpoint'), 'Risk watchpoint:')}",
        f"- Invalidation condition: {_public_report_brief(purpose_fields.get('invalidation_condition'))}",
        "",
        "## Next Research Step",
        f"- Next research question: {_display_value(purpose_fields.get('next_research_question'))}",
        f"- Review priority: {_proof_language(purpose_fields.get('review_priority_reason'))}",
        f"- Data-confidence explanation: {_proof_language(purpose_fields.get('confidence_explanation'))}",
        "",
        "## Data Readiness",
        f"- Overall state: {_display_value(readiness.get('overall_readiness_state'))}",
        f"- Asset type: {_display_value(readiness.get('asset_type'))}",
        f"- Price ready: {_display_report_status(readiness.get('price_ready'))}",
        f"- Momentum ready: {_display_report_status(readiness.get('momentum_ready'))}",
        f"- Fundamentals ready: {_display_report_status(readiness.get('fundamentals_ready'))}",
        f"- DCF ready: {_display_report_status(readiness.get('dcf_ready'))}",
        f"- Peer ready: {_display_report_status(readiness.get('peer_ready'))}",
        f"- Earnings ready: {_display_report_status(readiness.get('earnings_ready'))}",
        f"- Analyst estimates ready: {_display_report_status(readiness.get('analyst_estimates_ready'))}",
        f"- Blocked features: {_display_report_list(readiness.get('blocked_features'), 'none')}",
        f"- Excluded features: {_display_report_list(readiness.get('excluded_features'), 'none')}",
        "",
        "## Price Coverage",
        f"- Price rows: {_display_value(coverage.get('price_rows'))}",
        f"- Missing price reason: {_display_report_list(coverage.get('missing_price_reason'), 'none')}",
        "",
        "## Valuation Readiness",
        *valuation_lines,
        "",
        "## DCF Calculation Path",
        *dcf_calculation_lines,
        "",
        "## DCF Input Triage",
        *dcf_input_triage_lines,
        "",
        "## Valuation Boundary Checklist",
        *valuation_boundary_lines,
        "",
        "## Peer Workflow",
        *peer_unlock_lines,
        *peer_evidence_ladder_lines,
        f"- Peer blocker type: {peer_blocker_display}",
        f"- Mapping status: {mapping_status_display}",
        f"- Peer count: {_display_value(peer.get('peer_count'))}",
        f"- Trend comparison ready: {_display_report_status(peer.get('peer_trend_comparison_ready'))}",
        f"- Valuation comparison ready: {_display_report_status(peer.get('peer_valuation_comparison_ready'))}",
        f"- Next peer action: {peer_next_action_display}",
        "",
        "## Optional Context Workflow",
        *optional_context_ladder_lines,
        "",
        "## Missing Data",
        f"- {_humanize_schema_terms(_display_value(readiness.get('missing_data')))}",
        "",
        "## Missing-Data Proof Summary",
        *data_unlock_lines,
        "",
        "## Copyable Proof Commands",
        *unlock_command_lines,
        "",
        "## Source Readiness Check",
        *_stock_report_source_audit_lines(
            ticker=symbol,
            readiness=readiness,
            coverage=coverage,
            dcf=dcf,
            peer=peer,
            earnings_ready=earnings_ready,
            estimates_ready=estimates_ready,
            dcf_status_text=dcf_status_text,
        ),
    ]
    return "\n".join(lines)


def export_readiness_only_markdown(
    ticker: str,
    output_path: Path,
    *,
    local_context: dict[str, Any],
    failure_reason: str = "",
) -> str:
    payload = build_readiness_only_markdown(ticker, local_context, failure_reason)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(payload + "\n", encoding="utf-8")
    return payload


def export_stock_report_markdown(
    report: StockReport,
    output_path: Path,
    *,
    local_context: dict[str, Any] | None = None,
) -> str:
    payload = build_stock_report_markdown(report, local_context)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(payload + "\n", encoding="utf-8")
    return payload


def build_provider(
    provider_name: str,
    base_dir: Path | None = None,
    data_dir: Path | None = None,
    output_dir: Path | None = None,
) -> MarketDataProvider:
    provider_name = provider_name.lower()
    if provider_name == "local":
        root = resolve_project_root(base_dir)
        return LocalCSVMarketDataProvider(
            base_dir=root,
            data_dir=resolve_data_dir(data_dir, root),
            outputs_dir=resolve_outputs_dir(output_dir, root),
        )
    if provider_name == "mock":
        source = make_source_metadata(
            provider="mock",
            freshness="demo snapshot",
            official=False,
            notes=["Demo-only mock data for smoke tests."],
        )
        history = pd.DataFrame(
            [{"date": pd.Timestamp("2025-05-12") + pd.Timedelta(days=day), "close": 100.0 + day} for day in range(260)]
        )
        return MockMarketDataProvider(
            quotes={
                "AAPL": QuoteSnapshot(
                    ticker="AAPL",
                    price=360.0,
                    previous_close=358.0,
                    open=359.0,
                    day_high=362.0,
                    day_low=357.0,
                    volume=1_000_000,
                    currency="USD",
                    market_time="2026-05-11T15:30:00Z",
                    source=source,
                )
            },
            histories={("AAPL", "1y", "1d"): history},
            financials={
                "AAPL": FinancialSnapshot(
                    ticker="AAPL",
                    revenue=1_000_000_000,
                    revenue_growth=0.10,
                    eps=12.0,
                    free_cash_flow=100_000_000,
                    fcf_margin=0.10,
                    operating_margin=0.22,
                    ebitda=180_000_000,
                    shares_outstanding=1_000_000,
                    cash=50_000_000,
                    debt=20_000_000,
                    source=source,
                )
            },
            earnings={"AAPL": EarningsSummary(ticker="AAPL", next_earnings_date="2026-07-20", source=source)},
            estimates={"AAPL": AnalystEstimateSummary(ticker="AAPL", current_quarter_eps=1.5, source=source)},
        )
    if provider_name == "yfinance":
        from src.providers.yfinance_provider import YFinanceProvider

        return YFinanceProvider()
    raise ValueError(f"Unsupported stock report provider: {provider_name}")


def create_stock_report_payload(
    ticker: str,
    provider_name: str = "local",
    base_dir: Path | None = None,
    data_dir: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    report = build_stock_report(ticker, build_provider(provider_name, base_dir=base_dir, data_dir=data_dir, output_dir=output_dir))
    return report.to_dict()


def _read_dataset_tickers(base_dir: Path, dataset_name: str, data_dir: Path | None = None, output_dir: Path | None = None) -> list[str]:
    provider = LocalCSVMarketDataProvider(base_dir=base_dir, data_dir=data_dir, outputs_dir=output_dir)
    frame = provider.catalog.load_dataframe(dataset_name)
    if frame is None or "ticker" not in frame.columns:
        return []
    return sorted(frame["ticker"].dropna().astype(str).str.upper().str.strip().unique().tolist())


def _resolve_sec_tickers(args: argparse.Namespace, base_dir: Path, data_dir: Path, output_dir: Path) -> list[str]:
    tickers: set[str] = set()
    if args.tickers:
        tickers.update(ticker.strip().upper() for ticker in args.tickers.split(",") if ticker.strip())
    if args.from_local_tickers:
        provider = LocalCSVMarketDataProvider(base_dir=base_dir, data_dir=data_dir, outputs_dir=output_dir)
        tickers.update(provider.list_local_tickers())
    if args.from_universe:
        tickers.update(_read_dataset_tickers(base_dir, "universe", data_dir, output_dir))
    if args.from_holdings:
        tickers.update(_read_dataset_tickers(base_dir, "holdings", data_dir, output_dir))
    return sorted(ticker for ticker in tickers if ticker)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a readable local single-stock research report.")
    parser.add_argument("--ticker", help="Ticker symbol to analyze")
    parser.add_argument("--provider", default="local", choices=["local", "mock", "yfinance"], help="Research data provider")
    parser.add_argument("--output", help="Optional JSON output path")
    parser.add_argument("--markdown-output", help="Optional Markdown report path. Defaults to outputs/stock_reports/{TICKER}.md for ticker reports.")
    parser.add_argument("--no-markdown", action="store_true", help="Do not write the default Markdown single-stock report.")
    parser.add_argument("--quiet", action="store_true", help="Print only paths/status for ticker reports instead of the optional report data.")
    parser.add_argument("--project-root", help="Project root for config.yaml and default data/output directories.")
    parser.add_argument("--data-dir", help="Optional data directory. Relative paths resolve from project root.")
    parser.add_argument("--output-dir", help="Optional output directory. Relative paths resolve from project root.")
    parser.add_argument("--list-local-tickers", action="store_true", help="List tickers discoverable from local CSV datasets.")
    parser.add_argument("--validate-local-data", action="store_true", help="Validate local CSV datasets and report schema coverage.")
    parser.add_argument("--write-local-data-templates", action="store_true", help="Write header-only local enrichment CSV templates under data/templates.")
    parser.add_argument("--write-import-staging", action="store_true", help="Write header-only staging CSV files under data/imports.")
    parser.add_argument("--validate-imports", action="store_true", help="Validate staged local import CSV files under data/imports.")
    parser.add_argument("--preview-import-merge", action="store_true", help="Preview local import CSV merge effects without changing canonical data files.")
    parser.add_argument("--apply-import-merge", action="store_true", help="Validate and merge local import CSV files into canonical local data files.")
    parser.add_argument("--sec-stage-fundamentals", action="store_true", help="Fetch official SEC Companyfacts data and stage candidate fundamentals under data/imports/fundamentals.csv.")
    parser.add_argument("--tickers", help="Comma-separated tickers for the SEC staging workflow.")
    parser.add_argument("--from-local-tickers", action="store_true", help="Use locally discoverable tickers for the SEC staging workflow.")
    parser.add_argument("--from-universe", action="store_true", help="Use tickers from data/universe.csv for the SEC staging workflow.")
    parser.add_argument("--from-holdings", action="store_true", help="Use tickers from data/holdings.csv for the SEC staging workflow.")
    parser.add_argument("--sec-user-agent", help="Identifying User-Agent required by the SEC, for example 'Name email@example.com'.")
    parser.add_argument("--sec-refresh", action="store_true", help="Refresh SEC ticker-map and Companyfacts cache entries instead of reusing local cache.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite the SEC fundamentals import file instead of upserting by ticker.")
    parser.add_argument("--template-dir", help="Optional destination directory for local CSV templates.")
    parser.add_argument("--json", action="store_true", help="Print CLI output as JSON for the supported validation/import/template commands.")
    args = parser.parse_args()
    cli_base_dir = resolve_project_root(args.project_root)
    cli_data_dir = resolve_data_dir(args.data_dir, cli_base_dir)
    cli_output_dir = resolve_outputs_dir(args.output_dir, cli_base_dir)

    def print_paths() -> None:
        print(format_path_context(cli_base_dir, cli_data_dir, cli_output_dir))

    def display_cli_path(path: Path) -> str:
        try:
            return str(path.relative_to(cli_base_dir))
        except ValueError:
            return str(path)

    if args.write_local_data_templates:
        template_results = write_local_data_templates(
            base_dir=cli_base_dir,
            template_dir=Path(args.template_dir) if args.template_dir else cli_data_dir / "templates",
        )
        if args.json:
            print(json.dumps(template_results, indent=2))
        else:
            print_paths()
            for item in template_results:
                print(
                    f"{item['dataset_name']}: {item['status']} -> {item['path']} "
                    f"columns={','.join(item['columns'])}"
                )
        return

    if args.write_import_staging:
        template_results = write_import_staging_files(base_dir=cli_base_dir, import_dir=cli_data_dir / "imports")
        if args.json:
            print(json.dumps(template_results, indent=2))
        else:
            print_paths()
            for item in template_results:
                print(
                    f"{item['dataset_name']}: {item['status']} -> {item['path']} "
                    f"columns={','.join(item['columns'])}"
                )
        return

    if args.validate_local_data:
        provider = LocalCSVMarketDataProvider(base_dir=cli_base_dir, data_dir=cli_data_dir, outputs_dir=cli_output_dir)
        validation = provider.get_local_data_validation()
        if args.json:
            print(json.dumps(validation, indent=2))
        else:
            print_paths()
            for item in validation:
                print(
                    f"{item['name']}: status={item['validation_status']} rows={item['row_count']} "
                    f"required_missing={','.join(item['missing_required_columns']) or '-'} "
                    f"warnings={'; '.join(item['validation_warnings']) or '-'}"
                )
        return

    if args.validate_imports:
        result = validate_imports(base_dir=cli_base_dir, data_dir=cli_data_dir)
        if args.json:
            print(json.dumps(result, indent=2))
        elif result["status"] == "no_staged_files":
            print_paths()
            print(f"{result['status']}: {result['warnings'][0]}")
        else:
            print_paths()
            for item in result["files"]:
                validation = item["validation"]
                print(
                    f"{item['file_name']}: status={validation['status']} "
                    f"rows={validation['row_count']} "
                    f"required_missing={','.join(validation['missing_required_columns']) or '-'} "
                    f"warnings={'; '.join(validation['warnings']) or '-'}"
                )
        return

    if args.preview_import_merge:
        result = preview_import_merge(base_dir=cli_base_dir, data_dir=cli_data_dir)
        if args.json:
            print(json.dumps(result, indent=2))
        elif result["status"] == "no_staged_files":
            print_paths()
            print(f"{result['status']}: {result['warnings'][0]}")
        else:
            print_paths()
            for item in result["preview"]:
                print(
                    f"{item['file_name']}: status={item['status']} "
                    f"new={item['new_rows']} updated={item['updated_rows']} unchanged={item['unchanged_rows']} "
                    f"skipped={item['skipped_rows']} "
                    f"warnings={'; '.join(item['warnings']) or '-'}"
                )
        return

    if args.apply_import_merge:
        result = apply_import_merge(base_dir=cli_base_dir, data_dir=cli_data_dir)
        if args.json:
            print(json.dumps(result, indent=2))
        elif result["status"] == "no_staged_files":
            print_paths()
            print(f"{result['status']}: {result['warnings'][0]}")
        elif result["status"] == "refused_invalid_imports":
            print_paths()
            print("refused_invalid_imports: staged files contain invalid required columns.")
            for item in result["preview"]:
                if item["status"] == "invalid":
                    print(
                        f"{item['file_name']}: invalid required_missing="
                        f"{','.join(item.get('missing_required_columns', [])) or '-'}"
                    )
        else:
            print_paths()
            for item in result["applied"]:
                print(
                    f"{item['file_name']}: applied={item['applied']} "
                    f"new={item['new_rows']} updated={item['updated_rows']} unchanged={item['unchanged_rows']} "
                    f"skipped={item['skipped_rows']} backup={item['backup_path'] or '-'}"
                )
        return

    if args.sec_stage_fundamentals:
        requested_tickers = _resolve_sec_tickers(args, cli_base_dir, cli_data_dir, cli_output_dir)
        if not requested_tickers:
            raise SystemExit(
                "SEC staging workflow requires at least one ticker source. Use --tickers, --from-local-tickers, "
                "--from-universe, or --from-holdings."
            )
        try:
            result = build_sec_fundamentals_rows(
                requested_tickers,
                user_agent=args.sec_user_agent,
                cache_dir=cli_data_dir / "cache" / "sec",
                refresh=args.sec_refresh,
            )
            write_result = write_sec_fundamentals_import(
                result["rows"],
                output_path=cli_data_dir / "imports" / "fundamentals.csv",
                overwrite=args.overwrite,
            )
        except (RuntimeError, ValueError) as exc:
            raise SystemExit(f"SEC staging workflow failed: {exc}") from exc
        payload = {
            **result,
            **write_result,
            "recommended_next_commands": [
                "make imports-validate",
                "make imports-preview",
                "make imports-apply",
            ],
        }
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_paths()
            print(f"requested_tickers: {', '.join(payload['requested_tickers']) or '-'}")
            print(f"resolved_tickers: {', '.join(payload['resolved_tickers']) or '-'}")
            print(f"unresolved_tickers: {', '.join(payload['unresolved_tickers']) or '-'}")
            print(f"rows_written: {payload['rows_written']}")
            print(f"staged_row_count: {payload.get('staged_row_count', 0)}")
            print(f"output_path: {payload['output_path']}")
            if payload["warnings"]:
                print(f"warnings: {'; '.join(payload['warnings'])}")
            for row in payload["row_summaries"]:
                print(
                    f"{row['ticker']}: populated={','.join(row['populated_fields']) or '-'} "
                    f"missing={','.join(row['missing_fields']) or '-'} "
                    f"warnings={'; '.join(row['warnings']) or '-'}"
                )
            print("next:")
            for command in payload["recommended_next_commands"]:
                print(f"- {command}")
        return

    if args.list_local_tickers:
        provider = LocalCSVMarketDataProvider(base_dir=cli_base_dir, data_dir=cli_data_dir, outputs_dir=cli_output_dir)
        tickers = provider.list_local_tickers()
        print_paths()
        print("\n".join(tickers))
        return

    if not args.ticker:
        raise SystemExit("--ticker is required unless --list-local-tickers is used.")

    markdown_path = None
    try:
        report = build_stock_report(
            args.ticker,
            build_provider(args.provider, base_dir=cli_base_dir, data_dir=cli_data_dir, output_dir=cli_output_dir),
        )
        output_path = None
        if args.output:
            raw_output = Path(args.output)
            output_path = (
                raw_output
                if raw_output.is_absolute()
                else cli_base_dir / raw_output
                if raw_output.parts and raw_output.parts[0] == "outputs"
                else cli_output_dir / raw_output
            )
        payload = export_stock_report_json(report, output_path)
        if not args.no_markdown:
            raw_markdown = Path(args.markdown_output) if args.markdown_output else Path("stock_reports") / f"{report.ticker.lower()}.md"
            markdown_path = (
                raw_markdown
                if raw_markdown.is_absolute()
                else cli_base_dir / raw_markdown
                if raw_markdown.parts and raw_markdown.parts[0] == "outputs"
                else cli_output_dir / raw_markdown
            )
            export_stock_report_markdown(
                report,
                markdown_path,
                local_context=_load_local_context(report.ticker, cli_output_dir, cli_data_dir),
            )
    except (FileNotFoundError, LookupError, RuntimeError, ValueError) as exc:
        local_context = _load_local_context(args.ticker, cli_output_dir, cli_data_dir)
        if (
            args.provider == "local"
            and isinstance(exc, LookupError)
            and "No local price rows were found" in str(exc)
            and local_context.get("readiness")
            and not args.no_markdown
        ):
            raw_markdown = Path(args.markdown_output) if args.markdown_output else Path("stock_reports") / f"{args.ticker.upper().lower()}.md"
            markdown_path = (
                raw_markdown
                if raw_markdown.is_absolute()
                else cli_base_dir / raw_markdown
                if raw_markdown.parts and raw_markdown.parts[0] == "outputs"
                else cli_output_dir / raw_markdown
            )
            export_readiness_only_markdown(
                args.ticker,
                markdown_path,
                local_context=local_context,
                failure_reason=str(exc),
            )
            if not args.quiet:
                print_paths()
            print(f"Data-needed Markdown report: {display_cli_path(markdown_path)}")
            print(f"First blocker to resolve: {exc}")
            return
        raise SystemExit(f"Stock report generation failed: {exc}") from exc
    if not args.quiet:
        print_paths()
    if markdown_path is not None:
        print(f"Markdown report: {display_cli_path(markdown_path)}")
    if not args.quiet:
        print(payload)


if __name__ == "__main__":
    main()
