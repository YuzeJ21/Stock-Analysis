from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from src.loader import normalize_columns
from src.providers.alternative_fundamentals import ALPHA_VANTAGE_API_KEY_ENV, FMP_API_KEY_ENV, FINNHUB_API_KEY_ENV
from src.providers.local_schemas import LOCAL_DATASET_SCHEMAS, validate_local_dataset
from src.providers.yfinance_provider import YFinanceProvider


def _requested_tickers(tickers: Iterable[str]) -> list[str]:
    return sorted({str(ticker).upper().strip() for ticker in tickers if str(ticker).strip()})


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


def _first_row(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        return payload[0]
    if isinstance(payload, dict):
        return payload
    return {}


def _fetch_json(url: str, *, opener: Callable[..., Any] = urlopen) -> Any:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "stock-research-command-center/1.0"})
    with opener(request, timeout=20) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def _allowed_optional_row(dataset_name: str, row: dict[str, Any]) -> dict[str, Any]:
    schema = LOCAL_DATASET_SCHEMAS[dataset_name]
    allowed = {*schema.required_columns, *schema.optional_columns}
    return {key: value for key, value in row.items() if key in allowed}


def _has_material_earnings(row: dict[str, Any]) -> bool:
    material = {
        "next_earnings_date",
        "last_earnings_date",
        "report_date",
        "eps_estimate",
        "eps_actual",
        "revenue_estimate",
        "revenue_actual",
        "surprise_pct",
    }
    return any(row.get(field) not in (None, "") for field in material)


def _has_material_estimates(row: dict[str, Any]) -> bool:
    material = {
        "eps_estimate",
        "revenue_estimate",
        "current_quarter_eps",
        "next_quarter_eps",
        "current_year_eps",
        "next_year_eps",
        "current_quarter_revenue",
        "next_quarter_revenue",
        "current_year_revenue",
        "next_year_revenue",
        "target_mean_price",
        "target_high_price",
        "target_low_price",
        "revision_trend",
    }
    return any(row.get(field) not in (None, "") for field in material)


def _empty_result(requested_tickers: list[str], warning: str) -> dict[str, Any]:
    return {
        "requested_tickers": requested_tickers,
        "resolved_tickers": [],
        "unresolved_tickers": requested_tickers,
        "earnings_rows": [],
        "analyst_estimate_rows": [],
        "row_summaries": [],
        "warnings": [warning],
    }


def _build_result(
    *,
    requested: list[str],
    earnings_rows: list[dict[str, Any]],
    analyst_estimate_rows: list[dict[str, Any]],
    warnings: list[str],
) -> dict[str, Any]:
    resolved = sorted(
        {
            str(row.get("ticker", "")).upper().strip()
            for row in [*earnings_rows, *analyst_estimate_rows]
            if str(row.get("ticker", "")).strip()
        }
    )
    row_summaries = []
    for dataset_name, rows in (("earnings", earnings_rows), ("analyst_estimates", analyst_estimate_rows)):
        for row in rows:
            populated = sorted(key for key, value in row.items() if key not in {"ticker", "source"} and value not in (None, ""))
            row_summaries.append(
                {
                    "ticker": row["ticker"],
                    "dataset_name": dataset_name,
                    "source": row.get("source", ""),
                    "populated_fields": populated,
                    "warnings": [],
                }
            )
    return {
        "requested_tickers": requested,
        "resolved_tickers": resolved,
        "unresolved_tickers": [ticker for ticker in requested if ticker not in resolved],
        "earnings_rows": earnings_rows,
        "analyst_estimate_rows": analyst_estimate_rows,
        "row_summaries": row_summaries,
        "warnings": sorted(set(warnings)),
    }


def build_alpha_vantage_optional_context_rows(
    tickers: Iterable[str],
    *,
    api_key: str | None = None,
    base_url: str = "https://www.alphavantage.co/query",
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    requested = _requested_tickers(tickers)
    if not requested:
        return _empty_result([], "No tickers were provided for Alpha Vantage optional-context staging workflow.")
    resolved_key = (api_key or os.environ.get(ALPHA_VANTAGE_API_KEY_ENV, "")).strip()
    if not resolved_key:
        return _empty_result(requested, f"{ALPHA_VANTAGE_API_KEY_ENV} is not configured.")

    earnings_rows: list[dict[str, Any]] = []
    analyst_rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for ticker in requested:
        url = f"{base_url}?{urlencode({'function': 'EARNINGS', 'symbol': ticker, 'apikey': resolved_key})}"
        try:
            payload = _fetch_json(url, opener=opener)
        except Exception as exc:  # pragma: no cover - network/provider dependent
            warnings.append(f"{ticker}: Alpha Vantage optional-context request failed: {exc}")
            continue
        if not isinstance(payload, dict) or "Note" in payload or "Information" in payload:
            warnings.append(f"{ticker}: Alpha Vantage returned no usable optional-context fields.")
            continue
        quarterly = payload.get("quarterlyEarnings") or []
        latest = quarterly[0] if quarterly and isinstance(quarterly[0], dict) else {}
        if not latest:
            warnings.append(f"{ticker}: Alpha Vantage returned no quarterly earnings rows.")
            continue

        reported_date = _clean_str(latest.get("reportedDate"))
        fiscal_period = _clean_str(latest.get("fiscalDateEnding"))
        eps_estimate = _clean_float(latest.get("estimatedEPS"))
        earnings_row = _allowed_optional_row(
            "earnings",
            {
                "ticker": ticker,
                "last_earnings_date": reported_date,
                "report_date": reported_date,
                "fiscal_period": fiscal_period,
                "eps_actual": _clean_float(latest.get("reportedEPS")),
                "eps_estimate": eps_estimate,
                "surprise_pct": _clean_float(latest.get("surprisePercentage")),
                "source": "alpha_vantage_research_api",
                "as_of_date": reported_date or fiscal_period,
                "updated_at": updated_at,
            },
        )
        estimate_row = _allowed_optional_row(
            "analyst_estimates",
            {
                "ticker": ticker,
                "period": fiscal_period,
                "current_quarter_eps": eps_estimate,
                "eps_estimate": eps_estimate,
                "source": "alpha_vantage_research_api",
                "as_of_date": fiscal_period or reported_date,
                "updated_at": updated_at,
            },
        )
        if _has_material_earnings(earnings_row):
            earnings_rows.append(earnings_row)
        if _has_material_estimates(estimate_row):
            analyst_rows.append(estimate_row)
        if not _has_material_earnings(earnings_row) and not _has_material_estimates(estimate_row):
            warnings.append(f"{ticker}: Alpha Vantage returned no usable optional-context values.")

    return _build_result(requested=requested, earnings_rows=earnings_rows, analyst_estimate_rows=analyst_rows, warnings=warnings)


def build_fmp_optional_context_rows(
    tickers: Iterable[str],
    *,
    api_key: str | None = None,
    base_url: str = "https://financialmodelingprep.com/api/v3",
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    requested = _requested_tickers(tickers)
    if not requested:
        return _empty_result([], "No tickers were provided for FMP optional-context staging workflow.")
    resolved_key = (api_key or os.environ.get(FMP_API_KEY_ENV, "")).strip()
    if not resolved_key:
        return _empty_result(requested, f"{FMP_API_KEY_ENV} is not configured.")

    root = base_url.rstrip("/")
    updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    earnings_rows: list[dict[str, Any]] = []
    analyst_rows: list[dict[str, Any]] = []
    warnings: list[str] = []

    for ticker in requested:
        try:
            earnings_payload = _fetch_json(
                f"{root}/historical/earning_calendar/{ticker}?{urlencode({'limit': 1, 'apikey': resolved_key})}",
                opener=opener,
            )
            estimates_payload = _fetch_json(
                f"{root}/analyst-estimates/{ticker}?{urlencode({'limit': 1, 'apikey': resolved_key})}",
                opener=opener,
            )
        except Exception as exc:  # pragma: no cover - network/provider dependent
            warnings.append(f"{ticker}: FMP optional-context request failed: {exc}")
            continue

        earnings = _first_row(earnings_payload)
        estimates = _first_row(estimates_payload)
        report_date = _clean_str(earnings.get("date"))
        fiscal_period = _clean_str(earnings.get("fiscalDateEnding") or estimates.get("date"))
        eps_estimate = _clean_float(earnings.get("epsEstimated") or estimates.get("estimatedEpsAvg"))
        revenue_estimate = _clean_float(earnings.get("revenueEstimated") or estimates.get("estimatedRevenueAvg"))

        earnings_row = _allowed_optional_row(
            "earnings",
            {
                "ticker": ticker,
                "last_earnings_date": report_date,
                "report_date": report_date,
                "fiscal_period": fiscal_period,
                "eps_actual": _clean_float(earnings.get("eps")),
                "eps_estimate": eps_estimate,
                "revenue_actual": _clean_float(earnings.get("revenue")),
                "revenue_estimate": revenue_estimate,
                "source": "fmp_research_api",
                "as_of_date": report_date or fiscal_period,
                "updated_at": updated_at,
            },
        )
        estimate_row = _allowed_optional_row(
            "analyst_estimates",
            {
                "ticker": ticker,
                "period": _clean_str(estimates.get("date") or fiscal_period),
                "current_quarter_eps": _clean_float(estimates.get("estimatedEpsAvg") or eps_estimate),
                "current_quarter_revenue": _clean_float(estimates.get("estimatedRevenueAvg") or revenue_estimate),
                "eps_estimate": _clean_float(estimates.get("estimatedEpsAvg") or eps_estimate),
                "revenue_estimate": _clean_float(estimates.get("estimatedRevenueAvg") or revenue_estimate),
                "source": "fmp_research_api",
                "as_of_date": _clean_str(estimates.get("date") or fiscal_period or report_date),
                "updated_at": updated_at,
            },
        )
        if _has_material_earnings(earnings_row):
            earnings_rows.append(earnings_row)
        if _has_material_estimates(estimate_row):
            analyst_rows.append(estimate_row)
        if not _has_material_earnings(earnings_row) and not _has_material_estimates(estimate_row):
            warnings.append(f"{ticker}: FMP returned no usable optional-context values.")

    return _build_result(requested=requested, earnings_rows=earnings_rows, analyst_estimate_rows=analyst_rows, warnings=warnings)


def build_yfinance_optional_context_rows(
    tickers: Iterable[str],
    *,
    provider_factory: Callable[[], Any] = YFinanceProvider,
) -> dict[str, Any]:
    requested = _requested_tickers(tickers)
    if not requested:
        return _empty_result([], "No tickers were provided for yfinance optional-context staging workflow.")
    try:
        provider = provider_factory()
    except Exception as exc:
        return _empty_result(requested, f"yfinance optional-context provider is unavailable: {exc}")

    updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    earnings_rows: list[dict[str, Any]] = []
    analyst_rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    for ticker in requested:
        try:
            earnings = provider.get_earnings(ticker).to_dict()
            estimates = provider.get_analyst_estimates(ticker).to_dict()
        except Exception as exc:  # pragma: no cover - upstream/network dependent
            warnings.append(f"{ticker}: yfinance optional-context request failed: {exc}")
            continue
        earnings_source = (earnings.get("source") or {}).get("provider", "yfinance")
        estimates_source = (estimates.get("source") or {}).get("provider", "yfinance")
        earnings_row = _allowed_optional_row(
            "earnings",
            {
                "ticker": ticker,
                "next_earnings_date": _clean_str(earnings.get("next_earnings_date")),
                "last_earnings_date": _clean_str(earnings.get("last_earnings_date")),
                "fiscal_period": _clean_str(earnings.get("fiscal_period")),
                "eps_estimate": _clean_float(earnings.get("eps_estimate")),
                "eps_actual": _clean_float(earnings.get("eps_actual")),
                "revenue_estimate": _clean_float(earnings.get("revenue_estimate")),
                "revenue_actual": _clean_float(earnings.get("revenue_actual")),
                "surprise_pct": _clean_float(earnings.get("surprise_pct")),
                "source": f"{earnings_source}_research_api",
                "updated_at": updated_at,
            },
        )
        estimate_row = _allowed_optional_row(
            "analyst_estimates",
            {
                "ticker": ticker,
                "current_quarter_eps": _clean_float(estimates.get("current_quarter_eps")),
                "next_quarter_eps": _clean_float(estimates.get("next_quarter_eps")),
                "current_year_eps": _clean_float(estimates.get("current_year_eps")),
                "next_year_eps": _clean_float(estimates.get("next_year_eps")),
                "current_quarter_revenue": _clean_float(estimates.get("current_quarter_revenue")),
                "next_quarter_revenue": _clean_float(estimates.get("next_quarter_revenue")),
                "current_year_revenue": _clean_float(estimates.get("current_year_revenue")),
                "next_year_revenue": _clean_float(estimates.get("next_year_revenue")),
                "target_mean_price": _clean_float(estimates.get("target_mean_price")),
                "target_high_price": _clean_float(estimates.get("target_high_price")),
                "target_low_price": _clean_float(estimates.get("target_low_price")),
                "revision_trend": _clean_str(estimates.get("revision_trend")),
                "source": f"{estimates_source}_research_api",
                "updated_at": updated_at,
            },
        )
        if _has_material_earnings(earnings_row):
            earnings_rows.append(earnings_row)
        if _has_material_estimates(estimate_row):
            analyst_rows.append(estimate_row)
        if not _has_material_earnings(earnings_row) and not _has_material_estimates(estimate_row):
            warnings.append(f"{ticker}: yfinance returned no usable optional-context values.")

    return _build_result(requested=requested, earnings_rows=earnings_rows, analyst_estimate_rows=analyst_rows, warnings=warnings)


def build_finnhub_optional_context_rows(
    tickers: Iterable[str],
    *,
    api_key: str | None = None,
    base_url: str = "https://finnhub.io/api/v1",
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    requested = _requested_tickers(tickers)
    if not requested:
        return _empty_result([], "No tickers were provided for Finnhub optional-context staging workflow.")
    resolved_key = (api_key or os.environ.get(FINNHUB_API_KEY_ENV, "")).strip()
    if not resolved_key:
        return _empty_result(requested, f"{FINNHUB_API_KEY_ENV} is not configured.")

    root = base_url.rstrip("/")
    now = datetime.now(timezone.utc)
    date_from = (now - timedelta(days=365)).date().isoformat()
    date_to = (now + timedelta(days=365)).date().isoformat()
    updated_at = now.isoformat(timespec="seconds")
    earnings_rows: list[dict[str, Any]] = []
    analyst_rows: list[dict[str, Any]] = []
    warnings: list[str] = []

    for ticker in requested:
        try:
            earnings_payload = _fetch_json(
                f"{root}/calendar/earnings?{urlencode({'symbol': ticker, 'from': date_from, 'to': date_to, 'token': resolved_key})}",
                opener=opener,
            )
            eps_payload = _fetch_json(
                f"{root}/stock/eps-estimate?{urlencode({'symbol': ticker, 'token': resolved_key})}",
                opener=opener,
            )
            revenue_payload = _fetch_json(
                f"{root}/stock/revenue-estimate?{urlencode({'symbol': ticker, 'token': resolved_key})}",
                opener=opener,
            )
            target_payload = _fetch_json(
                f"{root}/stock/price-target?{urlencode({'symbol': ticker, 'token': resolved_key})}",
                opener=opener,
            )
        except Exception as exc:  # pragma: no cover - network/provider dependent
            warnings.append(f"{ticker}: Finnhub optional-context request failed: {exc}")
            continue

        earnings_items = earnings_payload.get("earningsCalendar", []) if isinstance(earnings_payload, dict) else []
        earnings = earnings_items[0] if earnings_items and isinstance(earnings_items[0], dict) else {}
        eps_estimate = _first_row(eps_payload.get("data", [])) if isinstance(eps_payload, dict) else {}
        revenue_estimate = _first_row(revenue_payload.get("data", [])) if isinstance(revenue_payload, dict) else {}
        target = target_payload if isinstance(target_payload, dict) else {}
        period = _clean_str(eps_estimate.get("period") or revenue_estimate.get("period"))

        earnings_row = _allowed_optional_row(
            "earnings",
            {
                "ticker": ticker,
                "last_earnings_date": _clean_str(earnings.get("date")),
                "report_date": _clean_str(earnings.get("date")),
                "fiscal_period": _clean_str(earnings.get("period") or period),
                "eps_actual": _clean_float(earnings.get("epsActual")),
                "eps_estimate": _clean_float(earnings.get("epsEstimate")),
                "revenue_actual": _clean_float(earnings.get("revenueActual")),
                "revenue_estimate": _clean_float(earnings.get("revenueEstimate")),
                "source": "finnhub_research_api",
                "as_of_date": _clean_str(earnings.get("date") or period),
                "updated_at": updated_at,
            },
        )
        estimate_row = _allowed_optional_row(
            "analyst_estimates",
            {
                "ticker": ticker,
                "period": period,
                "current_quarter_eps": _clean_float(eps_estimate.get("epsAvg")),
                "current_quarter_revenue": _clean_float(revenue_estimate.get("revenueAvg")),
                "eps_estimate": _clean_float(eps_estimate.get("epsAvg")),
                "revenue_estimate": _clean_float(revenue_estimate.get("revenueAvg")),
                "target_mean_price": _clean_float(target.get("targetMean")),
                "target_high_price": _clean_float(target.get("targetHigh")),
                "target_low_price": _clean_float(target.get("targetLow")),
                "source": "finnhub_research_api",
                "as_of_date": _clean_str(target.get("lastUpdated") or period),
                "updated_at": updated_at,
            },
        )
        if _has_material_earnings(earnings_row):
            earnings_rows.append(earnings_row)
        if _has_material_estimates(estimate_row):
            analyst_rows.append(estimate_row)
        if not _has_material_earnings(earnings_row) and not _has_material_estimates(estimate_row):
            warnings.append(f"{ticker}: Finnhub returned no usable optional-context values.")

    return _build_result(requested=requested, earnings_rows=earnings_rows, analyst_estimate_rows=analyst_rows, warnings=warnings)


def _attempt_payload(
    *,
    provider: str,
    status: str,
    reason_code: str,
    requested_tickers: list[str],
    resolved_tickers: list[str] | None = None,
    unresolved_tickers: list[str] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    resolved = resolved_tickers or []
    return {
        "provider": provider,
        "status": status,
        "reason_code": reason_code,
        "requested_tickers": requested_tickers,
        "resolved_tickers": resolved,
        "unresolved_tickers": unresolved_tickers
        if unresolved_tickers is not None
        else [ticker for ticker in requested_tickers if ticker not in resolved],
        "warnings": warnings or [],
    }


def _source_unavailable(session_preflight: dict[str, Any] | None, source_key: str, blocked_paths: set[str]) -> str | None:
    if not isinstance(session_preflight, dict):
        return None
    sources = session_preflight.get("sources", {})
    sources = sources if isinstance(sources, dict) else {}
    source = sources.get(source_key, {})
    source = source if isinstance(source, dict) else {}
    do_not_retry = {
        str(path).strip().lower()
        for path in session_preflight.get("do_not_retry_paths", [])
        if str(path).strip()
    }
    status = str(source.get("status") or "").strip().lower()
    reason = str(source.get("reason_code") or "").strip()
    if do_not_retry.intersection(blocked_paths) or (status and status != "available"):
        return reason or "session_preflight_unavailable"
    return None


def build_optional_context_source_ladder_rows(
    tickers: Iterable[str],
    *,
    fmp_api_key: str | None = None,
    alpha_vantage_api_key: str | None = None,
    finnhub_api_key: str | None = None,
    session_preflight: dict[str, Any] | None = None,
    yfinance_builder: Callable[..., dict[str, Any]] = build_yfinance_optional_context_rows,
    fmp_builder: Callable[..., dict[str, Any]] = build_fmp_optional_context_rows,
    alpha_vantage_builder: Callable[..., dict[str, Any]] = build_alpha_vantage_optional_context_rows,
    finnhub_builder: Callable[..., dict[str, Any]] = build_finnhub_optional_context_rows,
) -> dict[str, Any]:
    requested = _requested_tickers(tickers)
    if not requested:
        return {
            **_empty_result([], "No tickers were provided for optional-context source ladder."),
            "provider_attempts": [],
        }

    rows_by_ticker: dict[str, dict[str, dict[str, Any]]] = {}
    warnings: list[str] = []
    attempts: list[dict[str, Any]] = []
    remaining = list(requested)

    def incomplete_tickers() -> list[str]:
        return [
            ticker
            for ticker in requested
            if "earnings" not in rows_by_ticker.get(ticker, {})
            or "analyst_estimates" not in rows_by_ticker.get(ticker, {})
        ]

    def filled_datasets(ticker: str) -> set[str]:
        return set(rows_by_ticker.get(ticker, {}))

    def ingest(result: dict[str, Any], prior_remaining: list[str]) -> None:
        for dataset_key, rows_key in (("earnings", "earnings_rows"), ("analyst_estimates", "analyst_estimate_rows")):
            for row in result.get(rows_key, []):
                ticker = str(row.get("ticker", "")).upper().strip()
                if ticker in prior_remaining:
                    rows_by_ticker.setdefault(ticker, {}).setdefault(dataset_key, row)

    yfinance_skip = _source_unavailable(
        session_preflight,
        "yfinance_stage",
        {"yfinance", "yfinance_fundamentals", "yahoo", "yahoo_fundamentals"},
    )
    if yfinance_skip:
        attempts.append(
            _attempt_payload(
                provider="yfinance",
                status="skipped",
                reason_code="session_preflight_unavailable",
                requested_tickers=list(remaining),
                warnings=[f"Yahoo/yfinance skipped because session preflight marks it unavailable ({yfinance_skip})."],
            )
        )
    elif remaining:
        result = yfinance_builder(remaining)
        warnings.extend(result.get("warnings", []))
        before = {ticker: filled_datasets(ticker) for ticker in remaining}
        prior_remaining = list(remaining)
        ingest(result, prior_remaining)
        remaining = incomplete_tickers()
        resolved = sorted(ticker for ticker in prior_remaining if filled_datasets(ticker) - before.get(ticker, set()))
        attempts.append(
            _attempt_payload(
                provider="yfinance",
                status="resolved_rows" if resolved else "no_rows",
                reason_code="ok" if resolved else "no_source_rows",
                requested_tickers=prior_remaining,
                resolved_tickers=resolved,
                unresolved_tickers=list(remaining),
                warnings=result.get("warnings", []),
            )
        )

    provider_specs = [
        ("fmp", FMP_API_KEY_ENV, fmp_api_key, fmp_builder),
        ("alpha_vantage", ALPHA_VANTAGE_API_KEY_ENV, alpha_vantage_api_key, alpha_vantage_builder),
        ("finnhub", FINNHUB_API_KEY_ENV, finnhub_api_key, finnhub_builder),
    ]
    for provider_name, env_var, explicit_key, builder in provider_specs:
        resolved_key = (explicit_key or os.environ.get(env_var, "")).strip()
        if not remaining:
            attempts.append(
                _attempt_payload(
                    provider=provider_name,
                    status="skipped",
                    reason_code="no_remaining_tickers",
                    requested_tickers=[],
                )
            )
            continue
        if not resolved_key:
            attempts.append(
                _attempt_payload(
                    provider=provider_name,
                    status="skipped",
                    reason_code="provider_key_missing",
                    requested_tickers=list(remaining),
                    warnings=[f"{env_var} is not configured."],
                )
            )
            continue
        result = builder(remaining, api_key=resolved_key)
        warnings.extend(result.get("warnings", []))
        before = {ticker: filled_datasets(ticker) for ticker in remaining}
        prior_remaining = list(remaining)
        ingest(result, prior_remaining)
        remaining = incomplete_tickers()
        resolved = sorted(ticker for ticker in prior_remaining if filled_datasets(ticker) - before.get(ticker, set()))
        attempts.append(
            _attempt_payload(
                provider=provider_name,
                status="resolved_rows" if resolved else "no_rows",
                reason_code="ok" if resolved else "no_source_rows",
                requested_tickers=prior_remaining,
                resolved_tickers=resolved,
                unresolved_tickers=list(remaining),
                warnings=result.get("warnings", []),
            )
        )

    earnings_rows = [
        rows_by_ticker[ticker]["earnings"]
        for ticker in requested
        if ticker in rows_by_ticker and "earnings" in rows_by_ticker[ticker]
    ]
    analyst_rows = [
        rows_by_ticker[ticker]["analyst_estimates"]
        for ticker in requested
        if ticker in rows_by_ticker and "analyst_estimates" in rows_by_ticker[ticker]
    ]
    return {
        **_build_result(
            requested=requested,
            earnings_rows=earnings_rows,
            analyst_estimate_rows=analyst_rows,
            warnings=warnings,
        ),
        "provider_attempts": attempts,
    }


def _import_columns(dataset_name: str) -> list[str]:
    schema = LOCAL_DATASET_SCHEMAS[dataset_name]
    columns = list(schema.required_columns)
    for column in schema.optional_columns:
        if column not in columns:
            columns.append(column)
    return columns


def write_optional_context_import(
    dataset_name: str,
    rows: list[dict[str, Any]],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    if dataset_name not in {"earnings", "analyst_estimates"}:
        raise ValueError(f"Unsupported optional context import dataset: {dataset_name}")
    output = Path(output_path)
    expected_name = f"{dataset_name}.csv"
    if output.name != expected_name or output.parent.name != "imports":
        raise ValueError(f"Optional context staging workflow may only write to data/imports/{expected_name}.")
    canonical_like = output.parent.parent / expected_name
    if output.resolve() == canonical_like.resolve():
        raise ValueError(f"Optional context staging workflow must not write directly to canonical data/{expected_name}.")

    columns = _import_columns(dataset_name)
    frame = pd.DataFrame(rows)
    if frame.empty:
        output.parent.mkdir(parents=True, exist_ok=True)
        if overwrite or not output.exists():
            pd.DataFrame(columns=columns).to_csv(output, index=False)
        return {"output_path": str(output), "rows_written": 0, "staged_row_count": 0, "status": "no_rows", "tickers_written": []}

    frame.columns = normalize_columns(list(frame.columns))
    for column in columns:
        if column not in frame.columns:
            frame[column] = pd.NA
    frame = frame[columns].copy()
    frame["ticker"] = frame["ticker"].astype("string").str.upper().str.strip()
    frame = frame.dropna(subset=["ticker"])
    frame = frame.drop_duplicates(subset=["ticker"], keep="last")

    output.parent.mkdir(parents=True, exist_ok=True)
    merged = frame
    if output.exists() and not overwrite:
        existing_validation, existing_frame = validate_local_dataset(dataset_name, output)
        if existing_validation.status == "invalid":
            raise ValueError(f"Existing {dataset_name} import file is invalid. Fix or remove it before provider staging.")
        existing = existing_frame.copy() if existing_frame is not None else pd.DataFrame(columns=columns)
        for column in columns:
            if column not in existing.columns:
                existing[column] = pd.NA
        existing = existing[columns].copy()
        existing["ticker"] = existing["ticker"].astype("string").str.upper().str.strip()
        existing = existing.dropna(subset=["ticker"])
        existing = existing.drop_duplicates(subset=["ticker"], keep="last")
        existing = existing.set_index("ticker", drop=False)
        incoming = frame.set_index("ticker", drop=False)
        overlap = existing.index.intersection(incoming.index)
        if not overlap.empty:
            for column in [column for column in columns if column != "ticker"]:
                existing[column] = existing[column].astype("object")
                existing.loc[overlap, column] = incoming.loc[overlap, column].astype("object")
        additions = incoming.loc[incoming.index.difference(existing.index)]
        merged = pd.concat([existing.reset_index(drop=True), additions.reset_index(drop=True)], ignore_index=True)
        merged = merged[columns].drop_duplicates(subset=["ticker"], keep="last")

    merged.to_csv(output, index=False)
    return {
        "output_path": str(output),
        "rows_written": int(len(frame)),
        "staged_row_count": int(len(merged)),
        "status": "staged",
        "tickers_written": sorted(frame["ticker"].dropna().astype(str).unique().tolist()),
    }


def write_optional_context_imports(
    *,
    earnings_rows: list[dict[str, Any]],
    analyst_estimate_rows: list[dict[str, Any]],
    import_dir: str | Path = "data/imports",
    overwrite: bool = False,
) -> dict[str, Any]:
    import_path = Path(import_dir)
    return {
        "earnings_write": write_optional_context_import(
            "earnings",
            earnings_rows,
            import_path / "earnings.csv",
            overwrite=overwrite,
        ),
        "analyst_estimates_write": write_optional_context_import(
            "analyst_estimates",
            analyst_estimate_rows,
            import_path / "analyst_estimates.csv",
            overwrite=overwrite,
        ),
    }
