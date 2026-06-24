from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Callable, Iterable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from src.providers.local_schemas import LOCAL_DATASET_SCHEMAS


FMP_API_KEY_ENV = "FMP_API_KEY"
ALPHA_VANTAGE_API_KEY_ENV = "ALPHA_VANTAGE_API_KEY"
FINNHUB_API_KEY_ENV = "FINNHUB_API_KEY"


def _requested_tickers(tickers: Iterable[str]) -> list[str]:
    return sorted({str(ticker).upper().strip() for ticker in tickers if str(ticker).strip()})


def _empty_result(requested_tickers: list[str], warning: str) -> dict[str, Any]:
    return {
        "requested_tickers": requested_tickers,
        "resolved_tickers": [],
        "unresolved_tickers": requested_tickers,
        "rows": [],
        "row_summaries": [],
        "warnings": [warning],
    }


def _clean_float(value: Any) -> float | None:
    try:
        if value in (None, "") or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _clean_str(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def _millions_to_units(value: Any) -> float | None:
    parsed = _clean_float(value)
    if parsed is None:
        return None
    return parsed * 1_000_000.0


def _first_row(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        return payload[0]
    if isinstance(payload, dict):
        return payload
    return {}


def _annual_report(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    reports = payload.get("annualReports") or []
    if reports and isinstance(reports[0], dict):
        return reports[0]
    return {}


def _fetch_json(url: str, *, opener: Callable[..., Any] = urlopen) -> Any:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "stock-research-command-center/1.0"})
    with opener(request, timeout=20) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def _allowed_fundamentals_row(row: dict[str, Any]) -> dict[str, Any]:
    schema = LOCAL_DATASET_SCHEMAS["fundamentals"]
    allowed = {"ticker", *schema.optional_columns}
    return {key: value for key, value in row.items() if key in allowed}


def _row_summary(row: dict[str, Any], *, source: str) -> dict[str, Any]:
    populated = sorted(key for key, value in row.items() if key not in {"ticker", "source"} and value not in (None, ""))
    missing = sorted(key for key, value in row.items() if key not in {"ticker", "source"} and value in (None, ""))
    return {
        "ticker": row["ticker"],
        "source": source,
        "populated_fields": populated,
        "missing_fields": missing,
        "warnings": [],
    }


def _has_material_values(row: dict[str, Any]) -> bool:
    material_fields = {
        "revenue",
        "free_cash_flow",
        "fcf_margin",
        "shares_outstanding",
        "market_cap",
        "eps",
        "cash",
        "debt",
    }
    return any(row.get(field) not in (None, "") for field in material_fields)


def build_fmp_fundamentals_rows(
    tickers: Iterable[str],
    *,
    api_key: str | None = None,
    base_url: str = "https://financialmodelingprep.com/api/v3",
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    requested = _requested_tickers(tickers)
    if not requested:
        return _empty_result([], "No tickers were provided for FMP staging workflow.")
    resolved_key = (api_key or os.environ.get(FMP_API_KEY_ENV, "")).strip()
    if not resolved_key:
        return _empty_result(requested, f"{FMP_API_KEY_ENV} is not configured.")

    rows: list[dict[str, Any]] = []
    row_summaries: list[dict[str, Any]] = []
    unresolved: list[str] = []
    warnings: list[str] = []
    updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    root = base_url.rstrip("/")

    def fetch(path: str) -> dict[str, Any]:
        url = f"{root}/{path}?{urlencode({'limit': 1, 'apikey': resolved_key})}"
        return _first_row(_fetch_json(url, opener=opener))

    for ticker in requested:
        try:
            profile = fetch(f"profile/{ticker}")
            income = fetch(f"income-statement/{ticker}")
            cash_flow = fetch(f"cash-flow-statement/{ticker}")
            balance = fetch(f"balance-sheet-statement/{ticker}")
            metrics = fetch(f"key-metrics-ttm/{ticker}")
        except Exception as exc:  # pragma: no cover - network/provider dependent
            unresolved.append(ticker)
            warnings.append(f"{ticker}: FMP request failed: {exc}")
            continue

        revenue = _clean_float(income.get("revenue"))
        free_cash_flow = _clean_float(cash_flow.get("freeCashFlow"))
        if free_cash_flow is None:
            operating_cash_flow = _clean_float(cash_flow.get("operatingCashFlow") or cash_flow.get("netCashProvidedByOperatingActivities"))
            capex = _clean_float(cash_flow.get("capitalExpenditure") or cash_flow.get("capitalExpenditures"))
            if operating_cash_flow is not None and capex is not None:
                free_cash_flow = operating_cash_flow - abs(capex)
        fcf_margin = free_cash_flow / revenue if free_cash_flow is not None and revenue not in (None, 0) else None
        cash = _clean_float(balance.get("cashAndCashEquivalents") or balance.get("cashAndShortTermInvestments"))
        debt = _clean_float(balance.get("totalDebt"))
        net_debt = debt - cash if debt is not None and cash is not None else None
        row = _allowed_fundamentals_row(
            {
                "ticker": ticker,
                "sector": _clean_str(profile.get("sector")),
                "revenue": revenue,
                "net_income": _clean_float(income.get("netIncome")),
                "eps": _clean_float(income.get("eps") or income.get("epsdiluted")),
                "free_cash_flow": free_cash_flow,
                "fcf": free_cash_flow,
                "fcf_margin": fcf_margin,
                "profit_margin": _clean_float(income.get("netIncomeRatio")),
                "operating_margin": _clean_float(income.get("operatingIncomeRatio")),
                "gross_margin": _clean_float(income.get("grossProfitRatio")),
                "ebitda": _clean_float(income.get("ebitda")),
                "cash": cash,
                "debt": debt,
                "net_debt": net_debt,
                "shares_outstanding": _clean_float(profile.get("sharesOutstanding") or income.get("weightedAverageShsOut")),
                "pe_ratio": _clean_float(metrics.get("peRatioTTM")),
                "trailing_pe": _clean_float(metrics.get("peRatioTTM")),
                "price_to_book": _clean_float(metrics.get("pbRatioTTM")),
                "market_cap": _clean_float(profile.get("mktCap") or metrics.get("marketCapTTM")),
                "enterprise_value": _clean_float(metrics.get("enterpriseValueTTM")),
                "debt_to_equity": _clean_float(metrics.get("debtToEquityTTM")),
                "source": "fmp_research_api",
                "as_of_date": _clean_str(income.get("date") or balance.get("date")),
                "updated_at": updated_at,
            }
        )
        if not _has_material_values(row):
            unresolved.append(ticker)
            warnings.append(f"{ticker}: FMP returned no usable fundamentals fields.")
            continue
        rows.append(row)
        row_summaries.append(_row_summary(row, source="fmp_research_api"))

    return {
        "requested_tickers": requested,
        "resolved_tickers": [row["ticker"] for row in rows],
        "unresolved_tickers": unresolved,
        "rows": rows,
        "row_summaries": row_summaries,
        "warnings": sorted(set(warnings)),
    }


def build_alpha_vantage_fundamentals_rows(
    tickers: Iterable[str],
    *,
    api_key: str | None = None,
    base_url: str = "https://www.alphavantage.co/query",
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    requested = _requested_tickers(tickers)
    if not requested:
        return _empty_result([], "No tickers were provided for Alpha Vantage staging workflow.")
    resolved_key = (api_key or os.environ.get(ALPHA_VANTAGE_API_KEY_ENV, "")).strip()
    if not resolved_key:
        return _empty_result(requested, f"{ALPHA_VANTAGE_API_KEY_ENV} is not configured.")

    rows: list[dict[str, Any]] = []
    row_summaries: list[dict[str, Any]] = []
    unresolved: list[str] = []
    warnings: list[str] = []
    updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def fetch(function: str, ticker: str) -> Any:
        url = f"{base_url}?{urlencode({'function': function, 'symbol': ticker, 'apikey': resolved_key})}"
        return _fetch_json(url, opener=opener)

    for ticker in requested:
        try:
            overview = fetch("OVERVIEW", ticker)
            income = _annual_report(fetch("INCOME_STATEMENT", ticker))
            cash_flow = _annual_report(fetch("CASH_FLOW", ticker))
            balance = _annual_report(fetch("BALANCE_SHEET", ticker))
        except Exception as exc:  # pragma: no cover - network/provider dependent
            unresolved.append(ticker)
            warnings.append(f"{ticker}: Alpha Vantage request failed: {exc}")
            continue

        if not isinstance(overview, dict) or "Note" in overview or "Information" in overview:
            unresolved.append(ticker)
            warnings.append(f"{ticker}: Alpha Vantage returned no usable overview fields.")
            continue

        revenue = _clean_float(income.get("totalRevenue"))
        operating_cash_flow = _clean_float(cash_flow.get("operatingCashflow"))
        capex = _clean_float(cash_flow.get("capitalExpenditures"))
        free_cash_flow = operating_cash_flow - abs(capex) if operating_cash_flow is not None and capex is not None else None
        fcf_margin = free_cash_flow / revenue if free_cash_flow is not None and revenue not in (None, 0) else None
        cash = _clean_float(balance.get("cashAndCashEquivalentsAtCarryingValue") or balance.get("cashAndShortTermInvestments"))
        debt = _clean_float(balance.get("shortLongTermDebtTotal"))
        if debt is None:
            short_debt = _clean_float(balance.get("shortTermDebt"))
            long_debt = _clean_float(balance.get("longTermDebt"))
            if short_debt is not None or long_debt is not None:
                debt = (short_debt or 0.0) + (long_debt or 0.0)
        net_debt = debt - cash if debt is not None and cash is not None else None

        row = _allowed_fundamentals_row(
            {
                "ticker": ticker,
                "sector": _clean_str(overview.get("Sector")),
                "revenue": revenue,
                "net_income": _clean_float(income.get("netIncome")),
                "eps": _clean_float(overview.get("EPS")),
                "free_cash_flow": free_cash_flow,
                "fcf": free_cash_flow,
                "fcf_margin": fcf_margin,
                "profit_margin": _clean_float(overview.get("ProfitMargin")),
                "operating_margin": _clean_float(overview.get("OperatingMarginTTM")),
                "gross_margin": _clean_float(overview.get("GrossMarginTTM")),
                "ebitda": _clean_float(overview.get("EBITDA") or income.get("ebitda")),
                "cash": cash,
                "debt": debt,
                "net_debt": net_debt,
                "shares_outstanding": _clean_float(overview.get("SharesOutstanding")),
                "pe_ratio": _clean_float(overview.get("PERatio")),
                "trailing_pe": _clean_float(overview.get("PERatio")),
                "forward_pe": _clean_float(overview.get("ForwardPE")),
                "price_to_book": _clean_float(overview.get("PriceToBookRatio")),
                "market_cap": _clean_float(overview.get("MarketCapitalization")),
                "source": "alpha_vantage_research_api",
                "as_of_date": _clean_str(overview.get("LatestQuarter") or income.get("fiscalDateEnding")),
                "updated_at": updated_at,
            }
        )
        if not _has_material_values(row):
            unresolved.append(ticker)
            warnings.append(f"{ticker}: Alpha Vantage returned no usable fundamentals fields.")
            continue
        rows.append(row)
        row_summaries.append(_row_summary(row, source="alpha_vantage_research_api"))

    return {
        "requested_tickers": requested,
        "resolved_tickers": [row["ticker"] for row in rows],
        "unresolved_tickers": unresolved,
        "rows": rows,
        "row_summaries": row_summaries,
        "warnings": sorted(set(warnings)),
    }


def build_finnhub_fundamentals_rows(
    tickers: Iterable[str],
    *,
    api_key: str | None = None,
    base_url: str = "https://finnhub.io/api/v1",
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    requested = _requested_tickers(tickers)
    if not requested:
        return _empty_result([], "No tickers were provided for Finnhub staging workflow.")
    resolved_key = (api_key or os.environ.get(FINNHUB_API_KEY_ENV, "")).strip()
    if not resolved_key:
        return _empty_result(requested, f"{FINNHUB_API_KEY_ENV} is not configured.")

    rows: list[dict[str, Any]] = []
    row_summaries: list[dict[str, Any]] = []
    unresolved: list[str] = []
    warnings: list[str] = []
    updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    root = base_url.rstrip("/")

    def fetch(path: str, ticker: str, **extra_params: str) -> Any:
        params = {"symbol": ticker, "token": resolved_key}
        params.update(extra_params)
        url = f"{root}/{path}?{urlencode(params)}"
        return _fetch_json(url, opener=opener)

    for ticker in requested:
        try:
            profile = fetch("stock/profile2", ticker)
            metric_payload = fetch("stock/metric", ticker, metric="all")
        except Exception as exc:  # pragma: no cover - network/provider dependent
            unresolved.append(ticker)
            warnings.append(f"{ticker}: Finnhub request failed: {exc}")
            continue

        if not isinstance(profile, dict):
            profile = {}
        metrics = metric_payload.get("metric", {}) if isinstance(metric_payload, dict) else {}
        metrics = metrics if isinstance(metrics, dict) else {}

        revenue = _clean_float(metrics.get("revenueTTM"))
        shares_outstanding = _millions_to_units(profile.get("shareOutstanding"))
        free_cash_flow = _clean_float(metrics.get("freeCashFlowTTM") or metrics.get("freeCashFlowPerShareTTM"))
        if (
            free_cash_flow is not None
            and "freeCashFlowPerShareTTM" in metrics
            and "freeCashFlowTTM" not in metrics
            and shares_outstanding is not None
        ):
            free_cash_flow = free_cash_flow * shares_outstanding
        fcf_margin = _clean_float(metrics.get("fcfMarginTTM"))
        if fcf_margin is None and free_cash_flow is not None and revenue not in (None, 0):
            fcf_margin = free_cash_flow / revenue

        row = _allowed_fundamentals_row(
            {
                "ticker": ticker,
                "sector": _clean_str(profile.get("finnhubIndustry")),
                "revenue": revenue,
                "eps": _clean_float(metrics.get("epsTTM")),
                "free_cash_flow": free_cash_flow,
                "fcf": free_cash_flow,
                "fcf_margin": fcf_margin,
                "profit_margin": _clean_float(metrics.get("netProfitMarginTTM")),
                "operating_margin": _clean_float(metrics.get("operatingMarginTTM")),
                "gross_margin": _clean_float(metrics.get("grossMarginTTM")),
                "ebitda": _clean_float(metrics.get("ebitdaTTM")),
                "shares_outstanding": shares_outstanding,
                "pe_ratio": _clean_float(metrics.get("peTTM")),
                "trailing_pe": _clean_float(metrics.get("peTTM")),
                "price_to_book": _clean_float(metrics.get("pbAnnual") or metrics.get("pbQuarterly")),
                "market_cap": _millions_to_units(profile.get("marketCapitalization")),
                "debt_to_equity": _clean_float(
                    metrics.get("totalDebt/totalEquityAnnual") or metrics.get("totalDebt/totalEquityQuarterly")
                ),
                "source": "finnhub_research_api",
                "updated_at": updated_at,
            }
        )
        if not _has_material_values(row):
            unresolved.append(ticker)
            warnings.append(f"{ticker}: Finnhub returned no usable fundamentals fields.")
            continue
        rows.append(row)
        row_summaries.append(_row_summary(row, source="finnhub_research_api"))

    return {
        "requested_tickers": requested,
        "resolved_tickers": [row["ticker"] for row in rows],
        "unresolved_tickers": unresolved,
        "rows": rows,
        "row_summaries": row_summaries,
        "warnings": sorted(set(warnings)),
    }


def build_alternative_fundamentals_rows(provider: str, tickers: Iterable[str], **kwargs: Any) -> dict[str, Any]:
    normalized = str(provider or "").strip().lower().replace("-", "_")
    if normalized in {"fmp", "financial_modeling_prep"}:
        return build_fmp_fundamentals_rows(tickers, **kwargs)
    if normalized in {"alpha_vantage", "alphavantage"}:
        return build_alpha_vantage_fundamentals_rows(tickers, **kwargs)
    if normalized == "finnhub":
        return build_finnhub_fundamentals_rows(tickers, **kwargs)
    raise ValueError(f"Unsupported alternative fundamentals provider: {provider}")
