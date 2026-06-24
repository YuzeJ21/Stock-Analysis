from __future__ import annotations

import os
from typing import Any, Callable, Iterable

from src.providers.alternative_fundamentals import (
    ALPHA_VANTAGE_API_KEY_ENV,
    FMP_API_KEY_ENV,
    FINNHUB_API_KEY_ENV,
    build_alpha_vantage_fundamentals_rows,
    build_fmp_fundamentals_rows,
    build_finnhub_fundamentals_rows,
)
from src.providers.sec_companyfacts import build_sec_fundamentals_rows
from src.providers.yfinance_provider import build_yfinance_fundamentals_rows


def _requested_tickers(tickers: Iterable[str]) -> list[str]:
    return sorted({str(ticker).upper().strip() for ticker in tickers if str(ticker).strip()})


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
    return {
        "provider": provider,
        "status": status,
        "reason_code": reason_code,
        "requested_tickers": requested_tickers,
        "resolved_tickers": resolved_tickers or [],
        "unresolved_tickers": unresolved_tickers or requested_tickers,
        "warnings": warnings or [],
    }


def _ingest_result(
    *,
    result: dict[str, Any],
    remaining: list[str],
    rows_by_ticker: dict[str, dict[str, Any]],
    row_summaries: list[dict[str, Any]],
) -> list[str]:
    allowed = set(remaining)
    for row in result.get("rows", []):
        ticker = str(row.get("ticker", "")).upper().strip()
        if ticker and ticker in allowed and ticker not in rows_by_ticker:
            rows_by_ticker[ticker] = row
    for summary in result.get("row_summaries", []):
        ticker = str(summary.get("ticker", "")).upper().strip()
        if ticker and ticker in rows_by_ticker:
            row_summaries.append(summary)
    return [ticker for ticker in remaining if ticker not in rows_by_ticker]


def _session_preflight_skip_reason(session_preflight: dict[str, Any] | None, provider: str) -> str | None:
    if not isinstance(session_preflight, dict):
        return None
    sources = session_preflight.get("sources", {})
    if not isinstance(sources, dict):
        return None
    do_not_retry = {
        str(path).strip().lower()
        for path in session_preflight.get("do_not_retry_paths", [])
        if str(path).strip()
    }

    if provider == "sec":
        source_key = "sec"
        blocked_paths = {"sec"}
        label = "SEC"
    elif provider == "yfinance":
        source_key = "yfinance_stage"
        blocked_paths = {"yfinance", "yfinance_fundamentals", "yahoo", "yahoo_fundamentals"}
        label = "Yahoo/yfinance"
    else:
        return None

    source = sources.get(source_key, {})
    source = source if isinstance(source, dict) else {}
    status = str(source.get("status") or "").strip().lower()
    reason = str(source.get("reason_code") or "").strip()
    if do_not_retry.intersection(blocked_paths) or (status and status != "available"):
        detail = f" ({reason})" if reason else ""
        return f"{label} skipped because session preflight marks it unavailable{detail}."
    return None


def build_fundamentals_source_ladder_rows(
    tickers: Iterable[str],
    *,
    sec_user_agent: str | None = None,
    sec_refresh: bool = False,
    sec_cache_dir: str | os.PathLike[str] = "data/cache/sec",
    fmp_api_key: str | None = None,
    alpha_vantage_api_key: str | None = None,
    finnhub_api_key: str | None = None,
    session_preflight: dict[str, Any] | None = None,
    sec_builder: Callable[..., dict[str, Any]] = build_sec_fundamentals_rows,
    yfinance_builder: Callable[..., dict[str, Any]] = build_yfinance_fundamentals_rows,
    fmp_builder: Callable[..., dict[str, Any]] = build_fmp_fundamentals_rows,
    alpha_vantage_builder: Callable[..., dict[str, Any]] = build_alpha_vantage_fundamentals_rows,
    finnhub_builder: Callable[..., dict[str, Any]] = build_finnhub_fundamentals_rows,
) -> dict[str, Any]:
    requested = _requested_tickers(tickers)
    if not requested:
        return {
            "requested_tickers": [],
            "resolved_tickers": [],
            "unresolved_tickers": [],
            "rows": [],
            "row_summaries": [],
            "warnings": ["No tickers were provided for fundamentals source ladder."],
            "provider_attempts": [],
        }

    rows_by_ticker: dict[str, dict[str, Any]] = {}
    row_summaries: list[dict[str, Any]] = []
    warnings: list[str] = []
    attempts: list[dict[str, Any]] = []
    remaining = list(requested)

    resolved_sec_user_agent = (sec_user_agent or os.environ.get("SEC_USER_AGENT", "")).strip()
    sec_skip_reason = _session_preflight_skip_reason(session_preflight, "sec")
    if sec_skip_reason and remaining:
        warnings.append(sec_skip_reason)
        attempts.append(
            _attempt_payload(
                provider="sec",
                status="skipped",
                reason_code="session_preflight_unavailable",
                requested_tickers=list(remaining),
                warnings=[sec_skip_reason],
            )
        )
    elif resolved_sec_user_agent and remaining:
        try:
            result = sec_builder(
                remaining,
                user_agent=resolved_sec_user_agent,
                cache_dir=sec_cache_dir,
                refresh=sec_refresh,
            )
            warnings.extend(result.get("warnings", []))
            prior_remaining = list(remaining)
            remaining = _ingest_result(result=result, remaining=remaining, rows_by_ticker=rows_by_ticker, row_summaries=row_summaries)
            attempts.append(
                _attempt_payload(
                    provider="sec",
                    status="resolved_rows" if len(remaining) < len(prior_remaining) else "no_rows",
                    reason_code="ok" if len(remaining) < len(prior_remaining) else "no_source_rows",
                    requested_tickers=prior_remaining,
                    resolved_tickers=result.get("resolved_tickers", []),
                    unresolved_tickers=remaining,
                    warnings=result.get("warnings", []),
                )
            )
        except Exception as exc:  # pragma: no cover - network/provider dependent
            warnings.append(f"sec: {exc}")
            attempts.append(
                _attempt_payload(
                    provider="sec",
                    status="unavailable",
                    reason_code="provider_failed",
                    requested_tickers=list(remaining),
                    warnings=[str(exc)],
                )
            )
    else:
        attempts.append(
            _attempt_payload(
                provider="sec",
                status="skipped",
                reason_code="missing_user_agent",
                requested_tickers=list(remaining),
                warnings=["SEC_USER_AGENT is not configured."],
            )
        )

    if remaining:
        yfinance_skip_reason = _session_preflight_skip_reason(session_preflight, "yfinance")
        if yfinance_skip_reason:
            warnings.append(yfinance_skip_reason)
            attempts.append(
                _attempt_payload(
                    provider="yfinance",
                    status="skipped",
                    reason_code="session_preflight_unavailable",
                    requested_tickers=list(remaining),
                    warnings=[yfinance_skip_reason],
                )
            )
        else:
            try:
                result = yfinance_builder(remaining)
                warnings.extend(result.get("warnings", []))
                prior_remaining = list(remaining)
                remaining = _ingest_result(result=result, remaining=remaining, rows_by_ticker=rows_by_ticker, row_summaries=row_summaries)
                attempts.append(
                    _attempt_payload(
                        provider="yfinance",
                        status="resolved_rows" if len(remaining) < len(prior_remaining) else "no_rows",
                        reason_code="ok" if len(remaining) < len(prior_remaining) else "no_source_rows",
                        requested_tickers=prior_remaining,
                        resolved_tickers=result.get("resolved_tickers", []),
                        unresolved_tickers=remaining,
                        warnings=result.get("warnings", []),
                    )
                )
            except Exception as exc:
                warnings.append(f"yfinance: {exc}")
                attempts.append(
                    _attempt_payload(
                        provider="yfinance",
                        status="unavailable",
                        reason_code="provider_failed",
                        requested_tickers=list(remaining),
                        warnings=[str(exc)],
                    )
                )

    resolved_fmp_key = (fmp_api_key or os.environ.get(FMP_API_KEY_ENV, "")).strip()
    if remaining and resolved_fmp_key:
        result = fmp_builder(remaining, api_key=resolved_fmp_key)
        warnings.extend(result.get("warnings", []))
        prior_remaining = list(remaining)
        remaining = _ingest_result(result=result, remaining=remaining, rows_by_ticker=rows_by_ticker, row_summaries=row_summaries)
        attempts.append(
            _attempt_payload(
                provider="fmp",
                status="resolved_rows" if len(remaining) < len(prior_remaining) else "no_rows",
                reason_code="ok" if len(remaining) < len(prior_remaining) else "no_source_rows",
                requested_tickers=prior_remaining,
                resolved_tickers=result.get("resolved_tickers", []),
                unresolved_tickers=remaining,
                warnings=result.get("warnings", []),
            )
        )
    else:
        attempts.append(
            _attempt_payload(
                provider="fmp",
                status="skipped",
                reason_code="provider_key_missing" if not resolved_fmp_key else "no_remaining_tickers",
                requested_tickers=list(remaining),
                warnings=[] if not remaining else [f"{FMP_API_KEY_ENV} is not configured."],
            )
        )

    resolved_alpha_key = (alpha_vantage_api_key or os.environ.get(ALPHA_VANTAGE_API_KEY_ENV, "")).strip()
    if remaining and resolved_alpha_key:
        result = alpha_vantage_builder(remaining, api_key=resolved_alpha_key)
        warnings.extend(result.get("warnings", []))
        prior_remaining = list(remaining)
        remaining = _ingest_result(result=result, remaining=remaining, rows_by_ticker=rows_by_ticker, row_summaries=row_summaries)
        attempts.append(
            _attempt_payload(
                provider="alpha_vantage",
                status="resolved_rows" if len(remaining) < len(prior_remaining) else "no_rows",
                reason_code="ok" if len(remaining) < len(prior_remaining) else "no_source_rows",
                requested_tickers=prior_remaining,
                resolved_tickers=result.get("resolved_tickers", []),
                unresolved_tickers=remaining,
                warnings=result.get("warnings", []),
            )
        )
    else:
        attempts.append(
            _attempt_payload(
                provider="alpha_vantage",
                status="skipped",
                reason_code="provider_key_missing" if not resolved_alpha_key else "no_remaining_tickers",
                requested_tickers=list(remaining),
                warnings=[] if not remaining else [f"{ALPHA_VANTAGE_API_KEY_ENV} is not configured."],
            )
        )

    resolved_finnhub_key = (finnhub_api_key or os.environ.get(FINNHUB_API_KEY_ENV, "")).strip()
    if remaining and resolved_finnhub_key:
        result = finnhub_builder(remaining, api_key=resolved_finnhub_key)
        warnings.extend(result.get("warnings", []))
        prior_remaining = list(remaining)
        remaining = _ingest_result(result=result, remaining=remaining, rows_by_ticker=rows_by_ticker, row_summaries=row_summaries)
        attempts.append(
            _attempt_payload(
                provider="finnhub",
                status="resolved_rows" if len(remaining) < len(prior_remaining) else "no_rows",
                reason_code="ok" if len(remaining) < len(prior_remaining) else "no_source_rows",
                requested_tickers=prior_remaining,
                resolved_tickers=result.get("resolved_tickers", []),
                unresolved_tickers=remaining,
                warnings=result.get("warnings", []),
            )
        )
    else:
        attempts.append(
            _attempt_payload(
                provider="finnhub",
                status="skipped",
                reason_code="provider_key_missing" if not resolved_finnhub_key else "no_remaining_tickers",
                requested_tickers=list(remaining),
                warnings=[] if not remaining else [f"{FINNHUB_API_KEY_ENV} is not configured."],
            )
        )

    rows = [rows_by_ticker[ticker] for ticker in requested if ticker in rows_by_ticker]
    return {
        "requested_tickers": requested,
        "resolved_tickers": [row["ticker"] for row in rows],
        "unresolved_tickers": [ticker for ticker in requested if ticker not in rows_by_ticker],
        "rows": rows,
        "row_summaries": row_summaries,
        "warnings": sorted(set(warnings)),
        "provider_attempts": attempts,
    }
