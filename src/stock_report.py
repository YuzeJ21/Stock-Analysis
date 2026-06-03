from __future__ import annotations

import argparse
import json
import os
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
    warnings.extend([f"Valuation missing field: {field}" for field in valuation.missing_fields])
    for row in dataset_coverage:
        if row.get("dataset_name") in core_datasets and not row.get("ticker_present"):
            warnings.append(f"{row['dataset_name']} has no local row for this ticker.")
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


def _sentence_value(value: Any, fallback: str = "Not available") -> str:
    return _display_value(value, fallback).rstrip(".")


def _brief_value(value: Any, *prefixes: str, fallback: str = "Not available") -> str:
    text = _display_value(value, fallback)
    for prefix in prefixes:
        if text.lower().startswith(prefix.lower()):
            return text[len(prefix) :].strip()
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
        decision.get("purpose_alignment") or decision.get("purpose_thesis"),
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
            f"Operator summary: Monitor context; {subtype}. "
            "Monitor role: market, theme, liquidity, or risk proxy. "
            "Withheld: operating-company DCF and peer valuation are excluded. "
            "Invalidation: proxy usefulness weakens if liquidity, correlation, or theme trend no longer supports monitoring."
        )

    blocker = _display_value(decision.get("primary_blocker"), "none")
    unsupported = _brief_value(
        decision.get("unsupported_analysis") or decision.get("valuation_evaluation"),
        "Unsupported analysis:",
        fallback="Unavailable inputs remain withheld rather than inferred.",
    )
    invalidation = _display_value(
        decision.get("invalidation_condition"),
        f"Invalidate this research read if {ticker} no longer passes the required readiness checks.",
    )
    return (
        f"Operator summary: {purpose_status}; {subtype}. "
        f"Next blocker: {blocker}. Withheld: {unsupported} "
        f"Invalidation: {invalidation}"
    )


def _stock_report_purpose_fields(
    *,
    ticker: str,
    readiness: dict[str, Any],
    decision: dict[str, Any],
    dcf_status_text: str,
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
            "purpose_alignment": "Purpose alignment: monitor context is evaluated only from ready local price, momentum, liquidity, correlation, and theme signals.",
            "setup_evaluation": f"Setup status: {subtype}; treat setup as monitor context rather than an operating-company recommendation.",
            "valuation_evaluation": "Operating-company DCF and peer valuation are excluded for this asset type; use market/risk context instead of valuation conclusions.",
            "supported_analysis": f"Supported analysis: {ready}; ETF/index/fund monitoring context.",
            "unsupported_analysis": "Unsupported analysis: operating-company DCF and peer valuation are excluded, not failed inputs.",
            "risk_watchpoint": "Risk watchpoint: monitor liquidity, correlation, theme exposure, and whether the proxy still represents the intended market signal.",
            "invalidation_condition": "Invalidate market-proxy usefulness if liquidity, correlation, or theme trend no longer supports the intended monitoring role.",
            "next_research_question": f"What market, theme, liquidity, or risk signal should {ticker} monitor, and what would invalidate that proxy role?",
            "review_priority_reason": "Monitor priority: use this proxy for market, theme, liquidity, or risk context; do not treat it as operating-company valuation.",
            "confidence_explanation": f"Confidence is {confidence}: only ready local monitor inputs are used. Operating-company DCF and peer valuation are excluded.",
        }
    else:
        blocker_verb = "remain" if blocker.lower().endswith("s") else "remains"
        valuation = "Valuation interpretation is limited to the locally ready inputs; unavailable valuation inputs are not inferred."
        next_question = f"Which trusted local input would unlock the next supported analysis for {ticker}?"
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
            "unsupported_analysis": f"Unsupported analysis: {missing}; unavailable inputs remain withheld rather than inferred.",
            "risk_watchpoint": f"Risk watchpoint: conclusions are limited by {blocker}.",
            "invalidation_condition": f"Invalidate this research read if local readiness no longer supports the stated purpose or if {blocker} {blocker_verb} unresolved for the intended analysis.",
            "next_research_question": next_question,
            "review_priority_reason": f"{bucket} / {subtype}; primary blocker: {blocker}.",
            "confidence_explanation": f"Confidence is {confidence}: only ready local inputs are used; missing inputs are not inferred.",
        }

    return {key: _display_value(decision.get(key), value) for key, value in fallback.items()}


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
    primary_blocker = str(decision.get("primary_blocker", "")).strip().lower()
    peer_action = peer.get("next_peer_action") or peer.get("missing_peer_reason")
    if primary_blocker in {"peer", "peers"} and _display_value(peer_action) != "Not available":
        return _display_value(peer_action)
    return _display_value(decision.get("next_best_action") or decision.get("next_action") or readiness.get("next_action"))


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
        peer_status = _display_value(peer.get("peer_blocker_type") or peer.get("missing_peer_reason"), "ready")
        peer_action = _sentence_value(peer.get("next_peer_action") or peer.get("missing_peer_reason"))
    return [
        f"- Prices: {_display_value(readiness.get('price_ready'))}; local source `data/prices.csv`; coverage {price_window}; staged path `data/staged/prices/` or `data/imports/prices.csv`; rejected rows `data/rejected/price_import_rejected.csv`.",
        f"- Fundamentals / DCF: {dcf_status_text}; local source `data/fundamentals.csv`; reason {_display_value(dcf.get('reason_not_ready') or dcf.get('missing_dcf_fields'))}; SEC_USER_AGENT {sec_status}; staged path `data/staged/fundamentals/` or `data/imports/fundamentals.csv`; rejected rows `data/rejected/fundamentals_import_rejected.csv`.",
        f"- Peers: {peer_status}; local source `data/peers.csv`; staged path `data/imports/peers.csv`; next peer action {peer_action}.",
        f"- Earnings: {_display_value(earnings_ready)}; trusted local CSV only; staged path `data/staged/earnings/`; command `make import-earnings`; rejected rows `data/rejected/earnings_import_rejected.csv`.",
        f"- Analyst estimates: {_display_value(estimates_ready)}; trusted local CSV only; staged path `data/staged/analyst_estimates/`; command `make import-analyst-estimates`; rejected rows `data/rejected/analyst_estimates_import_rejected.csv`.",
        f"- Credentials: SEC_USER_AGENT {sec_status}; STOOQ_API_KEY {stooq_status}; missing remote credentials should not break local CSV reports or staged import workflows.",
        f"- Report command: `make stock-report TICKER={ticker}`. Research-only output; copyable command only.",
    ]


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
    readiness = local_context.get("readiness", {})
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
        retrieved = _display_value(item.get("retrieved_at"))
        notes = "; ".join(str(note) for note in item.get("notes", []) if str(note).strip())
        source_lines.append(f"- {provider}: {official}, retrieved {retrieved}" + (f"; {notes}" if notes else ""))
    if not source_lines:
        source_lines.append("- Not available")

    missing_lines = [f"- {warning}" for warning in payload.get("missing_data_warnings", [])[:20]]
    if not missing_lines:
        missing_lines.append("- None reported by the local provider.")

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
    one_minute_parts = [
        f"{report.ticker} state: {_display_value(readiness.get('overall_readiness_state'))}.",
        f"Decision: {_display_value(decision.get('decision_subtype') or decision.get('decision_bucket'))}.",
        f"DCF: {dcf_status_text}.",
    ]
    if monitor_context:
        one_minute_parts.append("Monitor context: operating-company DCF and peer valuation are excluded.")
    else:
        one_minute_parts.append(f"Primary blocker: {_display_value(decision.get('primary_blocker'))}.")
    peer_blocker = peer.get("peer_blocker_type") or peer.get("missing_peer_reason")
    core_data_before_peers = not monitor_context and dcf_status_text != "ready"
    if core_data_before_peers:
        one_minute_parts.append("Peer workflow: waits for trusted price, fundamentals, and DCF inputs first.")
    elif peer_blocker and not monitor_context:
        one_minute_parts.append(f"Peer workflow: {_display_value(peer_blocker)}.")
    if optional_locked:
        one_minute_parts.append("Optional earnings or analyst-estimate context is unavailable until trusted local CSV rows exist.")
    one_minute_next = _stock_report_next_action(
        ticker=report.ticker,
        readiness=readiness,
        decision=decision,
        peer=peer,
        dcf_status_text=dcf_status_text,
    )
    if one_minute_next != "Not available":
        one_minute_parts.append(f"Next: {_sentence_value(one_minute_next)}.")
    one_minute_summary = " ".join(part for part in one_minute_parts if part)
    purpose_fields = _stock_report_purpose_fields(
        ticker=report.ticker,
        readiness=readiness,
        decision=decision,
        dcf_status_text=dcf_status_text,
    )
    purpose_decision = {**decision, **purpose_fields}
    operator_summary = _stock_report_operator_summary(ticker=report.ticker, readiness=readiness, decision=purpose_decision)
    decision_primary_blocker = "monitor_context" if monitor_context else _display_value(decision.get("primary_blocker"))
    if monitor_context:
        peer_blocker_display = "monitor_context"
        mapping_status_display = "monitor_context"
        peer_next_action_display = "No peer import is required; operating-company peer valuation is excluded for ETF/index/fund monitor context."
    elif core_data_before_peers:
        peer_blocker_display = "blocked_until_fundamentals_dcf"
        mapping_status_display = "wait_for_core_data"
        peer_next_action_display = "Peer-relative valuation should wait until trusted price, fundamentals, and DCF inputs are ready."
    else:
        peer_blocker_display = _display_value(peer.get("peer_blocker_type"))
        mapping_status_display = _display_value(peer.get("mapping_status"))
        peer_next_action_display = _display_value(peer.get("next_peer_action") or peer.get("missing_peer_reason"))
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

    report_lines = [
        f"# {report.ticker} Single-Stock Research Report",
        "",
        "Research-only local report. It summarizes readiness and does not provide allocation instructions.",
        "",
        "## Executive Summary",
        one_minute_summary,
        "",
        "## One-Minute Status",
        one_minute_summary,
        "",
        "## What This Stock Is",
        f"- Ticker: {report.ticker}",
        f"- Asset type: {_display_value(readiness.get('asset_type'))}",
        f"- Current role: {_brief_value(purpose_fields.get('purpose_thesis'), 'Purpose:')}",
        "",
        "## Decision",
        f"- Bucket: {_display_value(decision.get('decision_bucket'))}",
        f"- Subtype: {_display_value(decision.get('decision_subtype'))}",
        f"- Primary blocker: {decision_primary_blocker}",
        f"- Main reason: {_display_value(decision.get('main_reason'))}",
        f"- Next action: {one_minute_next}",
        "",
        "## Purpose Evaluation",
        "Research-only purpose brief. It separates what local data supports from what remains locked or excluded.",
        f"- Thesis: {_brief_value(purpose_fields.get('purpose_thesis'), 'Purpose:')}",
        f"- Alignment: {_brief_value(purpose_fields.get('purpose_alignment'), 'Purpose alignment:')}",
        f"- Operator summary: {_brief_value(operator_summary, 'Operator summary:')}",
        f"- Setup: {_brief_value(purpose_fields.get('setup_evaluation'), 'Setup status:')}",
        f"- Valuation boundary: {_display_value(purpose_fields.get('valuation_evaluation'))}",
        "",
        "## Supported Analysis",
        f"- Supported analysis: {_brief_value(purpose_fields.get('supported_analysis'), 'Supported analysis:')}",
        "",
        "## Blocked Analysis",
        f"- Unsupported analysis: {_brief_value(purpose_fields.get('unsupported_analysis'), 'Unsupported analysis:')}",
        "",
        "## Setup / Momentum",
        f"- {_brief_value(purpose_fields.get('setup_evaluation'), 'Setup status:')}",
        f"- 1M performance: {_display_value(payload.get('performance', {}).get('one_month'))}",
        f"- 3M performance: {_display_value(payload.get('performance', {}).get('three_month'))}",
        f"- 1Y performance: {_display_value(payload.get('performance', {}).get('one_year'))}",
        "",
        "## Risk Notes",
        f"- Risk watchpoint: {_brief_value(purpose_fields.get('risk_watchpoint'), 'Risk watchpoint:')}",
        f"- Invalidation condition: {_display_value(purpose_fields.get('invalidation_condition'))}",
        "",
        "## Next Research Step",
        f"- Next research question: {_display_value(purpose_fields.get('next_research_question'))}",
        f"- Review priority: {_display_value(purpose_fields.get('review_priority_reason'))}",
        f"- Confidence explanation: {_display_value(purpose_fields.get('confidence_explanation'))}",
        "",
        "## Data Readiness",
        f"- Overall state: {_display_value(readiness.get('overall_readiness_state'))}",
        f"- Price ready: {_display_value(readiness.get('price_ready'))}",
        f"- Momentum ready: {_display_value(readiness.get('momentum_ready'))}",
        f"- Liquidity ready: {_display_value(readiness.get('liquidity_ready'))}",
        f"- Correlation ready: {_display_value(readiness.get('correlation_ready'))}",
        f"- Fundamentals ready: {_display_value(readiness.get('fundamentals_ready'))}",
        f"- DCF ready: {_display_value(dcf_ready)}",
        f"- Peer ready: {_display_value(peer_ready)}",
        f"- Earnings ready: {_display_value(earnings_ready)}",
        f"- Analyst estimates ready: {_display_value(estimates_ready)}",
        f"- Blocked features: {_display_value(readiness.get('blocked_features'))}",
        f"- Excluded features: {_display_value(readiness.get('excluded_features'))}",
        "",
        "## Price Coverage",
        f"- Price rows: {_display_value(coverage.get('price_rows'))}",
        f"- First date: {_display_value(coverage.get('first_price_date'))}",
        f"- Last date: {_display_value(coverage.get('last_price_date'))}",
        f"- Missing price reason: {_display_value(coverage.get('missing_price_reason'))}",
        "",
        "## Valuation Readiness",
        f"- DCF status: {_display_value(payload.get('valuation_snapshot', {}).get('status'))}",
        f"- DCF missing fields: {_display_value(dcf.get('missing_dcf_fields') or ', '.join(valuation_readiness.get('dcf_missing_fields', [])))}",
        f"- Reason not ready: {_display_value(dcf.get('reason_not_ready'))}",
        f"- Relative valuation status: {_display_value(payload.get('valuation_snapshot', {}).get('relative_valuation', {}).get('status'))}",
        "- Valuation conclusion is shown only when trusted DCF and peer inputs support it; missing valuation inputs are not inferred.",
        "",
        "## Peer Workflow",
        f"- Peer blocker type: {peer_blocker_display}",
        f"- Mapping status: {mapping_status_display}",
        f"- Peer count: {_display_value(peer.get('peer_count'))}",
        f"- Trend comparison ready: {_display_value(peer.get('peer_trend_comparison_ready'))}",
        f"- Valuation comparison ready: {_display_value(peer.get('peer_valuation_comparison_ready'))}",
        f"- DCF peer comparison ready: {_display_value(peer.get('peer_dcf_comparison_ready'))}",
        f"- Sample peers: {_display_value(peer.get('sample_peers'))}",
        f"- Next peer action: {peer_next_action_display}",
        "",
        "## Missing Data",
        *missing_lines,
        "",
        "## Source / Freshness",
        *source_lines,
        "",
        "## Source/Freshness Audit",
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
    decision_primary_blocker = "monitor_context" if monitor_context else _display_value(decision.get("primary_blocker"))
    core_data_before_peers = not monitor_context and dcf_status_text != "ready"
    if monitor_context:
        peer_blocker_display = "monitor_context"
        mapping_status_display = "monitor_context"
        peer_next_action_display = "No peer import is required; operating-company peer valuation is excluded for ETF/index/fund monitor context."
    elif core_data_before_peers:
        peer_blocker_display = "blocked_until_fundamentals_dcf"
        mapping_status_display = "wait_for_core_data"
        peer_next_action_display = "Peer-relative valuation should wait until trusted price, fundamentals, and DCF inputs are ready."
    else:
        peer_blocker_display = _display_value(peer.get("peer_blocker_type"))
        mapping_status_display = _display_value(peer.get("mapping_status"))
        peer_next_action_display = _display_value(peer.get("next_peer_action") or peer.get("missing_peer_reason"))
    one_minute_summary = " ".join(
        part
        for part in [
            f"{symbol} state: {_display_value(readiness.get('overall_readiness_state'))}.",
            f"Decision: {_display_value(decision.get('decision_subtype') or decision.get('decision_bucket'))}.",
            "Monitor context: operating-company DCF and peer valuation are excluded." if monitor_context else f"Primary blocker: {_display_value(decision.get('primary_blocker'))}.",
            f"DCF: {dcf_status_text}.",
            ""
            if monitor_context
            else "Peer workflow: waits for trusted price, fundamentals, and DCF inputs first."
            if core_data_before_peers
            else f"Peer workflow: {_display_value(peer.get('peer_blocker_type') or peer.get('missing_peer_reason'))}.",
            "Optional earnings or analyst-estimate context is unavailable until trusted local CSV rows exist.",
            f"Next: {_sentence_value(next_action)}.",
        ]
        if part and "Not available" not in part
    )
    lines = [
        f"# {symbol} Single-Stock Research Report",
        "",
        "Research-only local report. It summarizes readiness and does not provide allocation instructions.",
        "",
        "This is a readiness-only report because the full stock-report provider could not assemble price-backed analysis.",
        f"Provider blocker: {_display_value(failure_reason)}",
        "",
        "## Executive Summary",
        one_minute_summary,
        "",
        "## One-Minute Status",
        one_minute_summary,
        "",
        "## What This Stock Is",
        f"- Ticker: {symbol}",
        f"- Asset type: {_display_value(readiness.get('asset_type'))}",
        f"- Current role: {_brief_value(purpose_fields.get('purpose_thesis'), 'Purpose:')}",
        "",
        "## Decision",
        f"- Bucket: {_display_value(decision.get('decision_bucket'))}",
        f"- Subtype: {_display_value(decision.get('decision_subtype'))}",
        f"- Primary blocker: {decision_primary_blocker}",
        f"- Main reason: {_display_value(decision.get('main_reason') or readiness.get('missing_data'))}",
        f"- Next action: {next_action}",
        "",
        "## Purpose Evaluation",
        "Research-only purpose brief. It separates what local data supports from what remains locked or excluded.",
        f"- Thesis: {_brief_value(purpose_fields.get('purpose_thesis'), 'Purpose:')}",
        f"- Alignment: {_brief_value(purpose_fields.get('purpose_alignment'), 'Purpose alignment:')}",
        f"- Operator summary: {_brief_value(operator_summary, 'Operator summary:')}",
        f"- Setup: {_brief_value(purpose_fields.get('setup_evaluation'), 'Setup status:')}",
        f"- Valuation boundary: {_display_value(purpose_fields.get('valuation_evaluation'))}",
        "",
        "## Supported Analysis",
        f"- Supported analysis: {_brief_value(purpose_fields.get('supported_analysis'), 'Supported analysis:')}",
        "",
        "## Blocked Analysis",
        f"- Unsupported analysis: {_brief_value(purpose_fields.get('unsupported_analysis'), 'Unsupported analysis:')}",
        "",
        "## Setup / Momentum",
        f"- {_brief_value(purpose_fields.get('setup_evaluation'), 'Setup status:')}",
        "",
        "## Risk Notes",
        f"- Risk watchpoint: {_brief_value(purpose_fields.get('risk_watchpoint'), 'Risk watchpoint:')}",
        f"- Invalidation condition: {_display_value(purpose_fields.get('invalidation_condition'))}",
        "",
        "## Next Research Step",
        f"- Next research question: {_display_value(purpose_fields.get('next_research_question'))}",
        f"- Review priority: {_display_value(purpose_fields.get('review_priority_reason'))}",
        f"- Confidence explanation: {_display_value(purpose_fields.get('confidence_explanation'))}",
        "",
        "## Data Readiness",
        f"- Overall state: {_display_value(readiness.get('overall_readiness_state'))}",
        f"- Asset type: {_display_value(readiness.get('asset_type'))}",
        f"- Price ready: {_display_value(readiness.get('price_ready'))}",
        f"- Momentum ready: {_display_value(readiness.get('momentum_ready'))}",
        f"- Fundamentals ready: {_display_value(readiness.get('fundamentals_ready'))}",
        f"- DCF ready: {_display_value(readiness.get('dcf_ready'))}",
        f"- Peer ready: {_display_value(readiness.get('peer_ready'))}",
        f"- Earnings ready: {_display_value(readiness.get('earnings_ready'))}",
        f"- Analyst estimates ready: {_display_value(readiness.get('analyst_estimates_ready'))}",
        f"- Blocked features: {_display_value(readiness.get('blocked_features'))}",
        f"- Excluded features: {_display_value(readiness.get('excluded_features'))}",
        "",
        "## Price Coverage",
        f"- Price rows: {_display_value(coverage.get('price_rows'))}",
        f"- Missing price reason: {_display_value(coverage.get('missing_price_reason'))}",
        "",
        "## Valuation Readiness",
        f"- Missing fields: {_display_value(dcf.get('missing_dcf_fields'))}",
        f"- Reason not ready: {_display_value(dcf.get('reason_not_ready'))}",
        "- Valuation conclusion is shown only when trusted DCF and peer inputs support it; missing valuation inputs are not inferred.",
        "",
        "## Peer Workflow",
        f"- Peer blocker type: {peer_blocker_display}",
        f"- Mapping status: {mapping_status_display}",
        f"- Peer count: {_display_value(peer.get('peer_count'))}",
        f"- Trend comparison ready: {_display_value(peer.get('peer_trend_comparison_ready'))}",
        f"- Valuation comparison ready: {_display_value(peer.get('peer_valuation_comparison_ready'))}",
        f"- Next peer action: {peer_next_action_display}",
        "",
        "## Missing Data",
        f"- {_display_value(readiness.get('missing_data'))}",
        "",
        "## Source/Freshness Audit",
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
    parser = argparse.ArgumentParser(description="Generate a structured stock report.")
    parser.add_argument("--ticker", help="Ticker symbol to analyze")
    parser.add_argument("--provider", default="local", choices=["local", "mock", "yfinance"], help="Research data provider")
    parser.add_argument("--output", help="Optional JSON output path")
    parser.add_argument("--markdown-output", help="Optional Markdown report path. Defaults to outputs/stock_reports/{TICKER}.md for ticker reports.")
    parser.add_argument("--no-markdown", action="store_true", help="Do not write the default Markdown single-stock report.")
    parser.add_argument("--project-root", help="Project root for config.yaml and default data/output directories.")
    parser.add_argument("--data-dir", help="Optional data directory. Relative paths resolve from project root.")
    parser.add_argument("--output-dir", help="Optional output directory. Relative paths resolve from project root.")
    parser.add_argument("--list-local-tickers", action="store_true", help="List tickers discoverable from local CSV datasets.")
    parser.add_argument("--validate-local-data", action="store_true", help="Validate local CSV datasets and report schema coverage.")
    parser.add_argument("--write-local-data-templates", action="store_true", help="Write header-only local enrichment CSV templates under data/templates.")
    parser.add_argument("--write-import-staging", action="store_true", help="Write header-only staging CSV files under data/imports.")
    parser.add_argument("--validate-imports", action="store_true", help="Validate staged CSV imports under data/imports.")
    parser.add_argument("--preview-import-merge", action="store_true", help="Preview staged CSV merge effects without changing canonical data files.")
    parser.add_argument("--apply-import-merge", action="store_true", help="Validate and merge staged CSV imports into canonical local data files.")
    parser.add_argument("--sec-stage-fundamentals", action="store_true", help="Fetch official SEC Companyfacts data and stage candidate fundamentals under data/imports/fundamentals.csv.")
    parser.add_argument("--tickers", help="Comma-separated tickers for SEC staging.")
    parser.add_argument("--from-local-tickers", action="store_true", help="Use locally discoverable tickers for SEC staging.")
    parser.add_argument("--from-universe", action="store_true", help="Use tickers from data/universe.csv for SEC staging.")
    parser.add_argument("--from-holdings", action="store_true", help="Use tickers from data/holdings.csv for SEC staging.")
    parser.add_argument("--sec-user-agent", help="Identifying User-Agent required by the SEC, for example 'Name email@example.com'.")
    parser.add_argument("--sec-refresh", action="store_true", help="Refresh SEC ticker-map and Companyfacts cache entries instead of reusing local cache.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite staged SEC fundamentals.csv instead of upserting by ticker.")
    parser.add_argument("--template-dir", help="Optional destination directory for local CSV templates.")
    parser.add_argument("--json", action="store_true", help="Print CLI output as JSON for the supported validation/import/template commands.")
    args = parser.parse_args()
    cli_base_dir = resolve_project_root(args.project_root)
    cli_data_dir = resolve_data_dir(args.data_dir, cli_base_dir)
    cli_output_dir = resolve_outputs_dir(args.output_dir, cli_base_dir)

    def print_paths() -> None:
        print(format_path_context(cli_base_dir, cli_data_dir, cli_output_dir))

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
                "SEC staging requires at least one ticker source. Use --tickers, --from-local-tickers, "
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
            raise SystemExit(f"SEC staging failed: {exc}") from exc
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
            print_paths()
            print(f"Readiness-only Markdown report: {markdown_path}")
            print(f"Full stock report blocked: {exc}")
            return
        raise SystemExit(f"Stock report generation failed: {exc}") from exc
    print_paths()
    if markdown_path is not None:
        print(f"Markdown report: {markdown_path}")
    print(payload)


if __name__ == "__main__":
    main()
