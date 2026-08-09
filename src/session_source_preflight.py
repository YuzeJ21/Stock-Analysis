from __future__ import annotations

import argparse
import copy
import csv
import importlib
import json
import os
import socket
from datetime import datetime, timezone
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd

from src.continuation_gate import (
    READINESS_CONTINUATION_GATE_HEADING,
    ContinuationGate,
    build_continuation_gate,
)
from src.paths import format_path_context, resolve_data_dir, resolve_outputs_dir, resolve_project_root
from src.profile_context import build_profile_context
from src.profile_context import READINESS_PREVIEW_NOTE
from src.provider_env import load_provider_environment
from src.providers.alternative_fundamentals import ALPHA_VANTAGE_API_KEY_ENV, FMP_API_KEY_ENV, FINNHUB_API_KEY_ENV
from src.data_update import DEFAULT_IBKR_CLIENT_ID, DEFAULT_IBKR_HOST, DEFAULT_IBKR_PORT, IBKR_CLIENT_ID_ENV, IBKR_HOST_ENV, IBKR_PORT_ENV
from src.providers.sec_submissions import build_sec_submission_metadata, fetch_sec_submission
from src.providers.yfinance_provider import build_yfinance_fundamentals_rows


SEC_TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
DEFAULT_YFINANCE_SAMPLE_TICKER = "MSFT"
DEFAULT_SEC_SUBMISSIONS_SAMPLE_CIK = "0000789019"
SESSION_SOURCE_PREFLIGHT_FILENAME = "session_source_preflight.json"
STOOQ_API_KEY_ENV = "STOOQ_API_KEY"
PRICE_PROVIDER_ORDER = ["stooq", "yahoo", "ibkr", "fmp", "alpha_vantage", "finnhub"]
FREE_TIER_BATCH_LIMITS = {
    "fmp": {"recommended_daily_request_limit": 250, "recommended_batch_size": 25},
    "alpha_vantage": {"recommended_daily_request_limit": 25, "recommended_batch_size": 5},
    "finnhub": {"recommended_daily_request_limit": 60, "recommended_batch_size": 10},
}
ALWAYS_EXECUTABLE_LANES = [
    "peer_mapping_proof",
    "peer_valuation_local_reviewed",
    "earnings_optional_manual",
    "analyst_estimates_optional_manual",
    "coverage_workflow_evidence",
]


def _human_source_gate_label(value: object) -> str:
    text = str(value or "-").strip() or "-"
    labels = {
        "coverage_workflow_evidence": "workflow evidence only; current source-proof queues are exhausted",
        "fundamentals_share_count_source_ladder": "fundamentals/share-count source ladder",
        "workflow_evidence_only": "workflow evidence only",
    }
    for token, label in labels.items():
        text = text.replace(token, label)
    return text


def _human_source_gate_list(values: object) -> str:
    if isinstance(values, (list, tuple, set)):
        labels = [_human_source_gate_label(value) for value in values if str(value or "").strip()]
    else:
        labels = [_human_source_gate_label(values)] if str(values or "").strip() else []
    return ", ".join(labels) or "-"


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _status_payload(
    *,
    status: str,
    reason_code: str,
    detail: str,
    next_action: str = "",
    **extra: Any,
) -> dict[str, Any]:
    payload = {
        "status": status,
        "reason_code": reason_code,
        "detail": detail,
        "next_action": next_action,
    }
    payload.update(extra)
    return payload


def probe_sec_access(
    sec_user_agent: str | None = None,
    *,
    opener: Callable[..., Any] = urlopen,
    timeout: int = 20,
) -> dict[str, Any]:
    user_agent = str(sec_user_agent or os.environ.get("SEC_USER_AGENT", "")).strip()
    if not user_agent:
        return _status_payload(
            status="unavailable",
            reason_code="missing_user_agent",
            detail="SEC_USER_AGENT is not configured for this session.",
            next_action="export SEC_USER_AGENT='Name email@example.com'",
        )

    request = Request(
        SEC_TICKER_MAP_URL,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json",
        },
    )
    try:
        with opener(request, timeout=timeout) as response:
            status_code = getattr(response, "status", None)
            if status_code is None and hasattr(response, "getcode"):
                status_code = response.getcode()
    except HTTPError as exc:
        return _status_payload(
            status="unavailable",
            reason_code="http_error",
            detail=f"SEC request failed with HTTP {exc.code}: {exc.reason}",
            next_action="Do not retry SEC-backed fundamentals/share-count work in this session.",
        )
    except URLError as exc:
        return _status_payload(
            status="unavailable",
            reason_code="network_error",
            detail=f"SEC request failed: {exc}",
            next_action="Do not retry SEC-backed fundamentals/share-count work in this session.",
        )
    except Exception as exc:  # pragma: no cover - defensive runtime path
        return _status_payload(
            status="unavailable",
            reason_code="request_failed",
            detail=f"SEC request failed: {exc}",
            next_action="Do not retry SEC-backed fundamentals/share-count work in this session.",
        )

    return _status_payload(
        status="available",
        reason_code="ok",
        detail=f"Reached SEC ticker map with HTTP {status_code or 200}.",
        next_action="",
        user_agent=user_agent,
    )


def probe_sec_submissions_access(
    sec_user_agent: str | None = None,
    *,
    sample_cik: str = DEFAULT_SEC_SUBMISSIONS_SAMPLE_CIK,
    fetcher: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    try:
        payload = fetch_sec_submission(
            sample_cik,
            sec_user_agent,
            cache=False,
            sleep_seconds=0,
            fetcher=fetcher,
        )
        metadata = build_sec_submission_metadata(payload)
    except ValueError as exc:
        return _status_payload(
            status="unavailable",
            reason_code="missing_user_agent",
            detail=str(exc),
            next_action="export SEC_USER_AGENT='Name email@example.com'",
            source_usage="metadata_evidence_only",
        )
    except Exception as exc:
        return _status_payload(
            status="unavailable",
            reason_code="request_failed",
            detail=f"SEC submissions request failed: {exc}",
            next_action="Use existing ticker map or reviewed local files; do not treat metadata as DCF/share-count proof.",
            source_usage="metadata_evidence_only",
        )

    entity = str(metadata.get("sec_entity_name") or "").strip()
    latest_form = str(metadata.get("sec_latest_form") or "").strip()
    latest_date = str(metadata.get("sec_latest_filing_date") or "").strip()
    detail_parts = [f"Reached SEC submissions metadata for sample CIK {metadata['sec_cik']}"]
    if entity:
        detail_parts.append(entity)
    if latest_form and latest_date:
        detail_parts.append(f"latest filing {latest_form} filed {latest_date}")
    return _status_payload(
        status="available",
        reason_code="ok",
        detail="; ".join(detail_parts) + ".",
        next_action="Use SEC submissions metadata for ticker/entity/SIC/filing-recency evidence only.",
        source_usage="metadata_evidence_only",
        sample_cik=metadata["sec_cik"],
        sample_entity_name=metadata.get("sec_entity_name"),
        sample_sic=metadata.get("sec_sic"),
        sample_sic_description=metadata.get("sec_sic_description"),
        sample_latest_form=metadata.get("sec_latest_form"),
        sample_latest_filing_date=metadata.get("sec_latest_filing_date"),
    )


def probe_yfinance_import() -> dict[str, Any]:
    try:
        module = importlib.import_module("yfinance")
    except ImportError as exc:
        return _status_payload(
            status="unavailable",
            reason_code="missing_dependency",
            detail=str(exc),
            next_action="python3 -m pip install -e '.[research]'",
        )

    version = str(getattr(module, "__version__", "") or "")
    return _status_payload(
        status="available",
        reason_code="installed",
        detail=f"yfinance {version}".strip(),
        next_action="",
        version=version,
    )


def probe_yfinance_stage(
    sample_ticker: str = DEFAULT_YFINANCE_SAMPLE_TICKER,
    *,
    builder: Callable[[list[str]], dict[str, Any]] = build_yfinance_fundamentals_rows,
) -> dict[str, Any]:
    ticker = str(sample_ticker or DEFAULT_YFINANCE_SAMPLE_TICKER).upper().strip()
    try:
        result = builder([ticker])
    except Exception as exc:  # pragma: no cover - upstream/network dependent
        return _status_payload(
            status="unavailable",
            reason_code="probe_failed",
            detail=str(exc),
            next_action="Do not retry Yahoo-backed fundamentals in this session.",
            sample_ticker=ticker,
        )

    resolved = {str(value).upper().strip() for value in result.get("resolved_tickers", [])}
    warnings = [str(item).strip() for item in result.get("warnings", []) if str(item).strip()]
    if ticker in resolved and result.get("rows"):
        detail = f"Resolved {ticker} through the yfinance fundamentals path."
        if warnings:
            detail = f"{detail} warnings={'; '.join(warnings[:2])}"
        return _status_payload(
            status="available",
            reason_code="probe_succeeded",
            detail=detail,
            next_action="",
            sample_ticker=ticker,
            warnings=warnings,
        )

    warning_detail = "; ".join(warnings[:2]) if warnings else f"{ticker} did not resolve."
    return _status_payload(
        status="unavailable",
        reason_code="probe_failed",
        detail=warning_detail,
        next_action="Do not retry Yahoo-backed fundamentals in this session.",
        sample_ticker=ticker,
        warnings=warnings,
    )


def probe_provider_api_key(env_var: str, *, provider_label: str) -> dict[str, Any]:
    if os.environ.get(env_var, "").strip():
        return _status_payload(
            status="available",
            reason_code="configured",
            detail=f"{env_var} is configured for {provider_label} fallback staging and price fallback.",
            next_action="",
        )
    return _status_payload(
        status="unavailable",
        reason_code="provider_key_missing",
        detail=f"{env_var} is not configured.",
        next_action=f"Set {env_var} to enable {provider_label} fallback fundamentals/share-count staging and price fallback.",
    )


def probe_stooq_key() -> dict[str, Any]:
    if os.environ.get(STOOQ_API_KEY_ENV, "").strip():
        return _status_payload(
            status="available",
            reason_code="configured",
            detail=f"{STOOQ_API_KEY_ENV} is configured for Stooq price fallback.",
            next_action="",
        )
    return _status_payload(
        status="unavailable",
        reason_code="provider_key_missing",
        detail=f"{STOOQ_API_KEY_ENV} is not configured; Stooq may still be attempted, but some environments require a key.",
        next_action=f"Set {STOOQ_API_KEY_ENV} to enable keyed Stooq price fallback when the unauthenticated CSV path is unavailable.",
    )


def probe_ibkr_price(
    *,
    module_loader: Callable[[str], Any] = importlib.import_module,
    socket_connector: Callable[[tuple[str, int], float], Any] = socket.create_connection,
    timeout: float = 2.0,
) -> dict[str, Any]:
    host = str(os.environ.get(IBKR_HOST_ENV) or "").strip()
    port_text = str(os.environ.get(IBKR_PORT_ENV) or "").strip()
    client_id_text = str(os.environ.get(IBKR_CLIENT_ID_ENV) or "").strip()
    if not host or not port_text or not client_id_text:
        return _status_payload(
            status="unavailable",
            reason_code="not_configured",
            detail=f"{IBKR_HOST_ENV}, {IBKR_PORT_ENV}, and {IBKR_CLIENT_ID_ENV} are not fully configured.",
            next_action=(
                "Leave IBKR disabled unless explicitly choosing optional read-only daily OHLCV; if intentionally enabled, "
                f"configure {IBKR_HOST_ENV}, {IBKR_PORT_ENV}, and {IBKR_CLIENT_ID_ENV} and run Gateway/TWS."
            ),
            source_usage="read_only_daily_ohlcv",
            host=host or DEFAULT_IBKR_HOST,
            port=int(port_text) if port_text.isdigit() else DEFAULT_IBKR_PORT,
            client_id_configured=bool(client_id_text),
        )
    try:
        port = int(port_text)
    except ValueError:
        return _status_payload(
            status="unavailable",
            reason_code="invalid_port",
            detail=f"{IBKR_PORT_ENV} must be an integer port.",
            next_action=f"Set {IBKR_PORT_ENV}=7497 for TWS paper or the port configured in IBKR Gateway/TWS.",
            source_usage="read_only_daily_ohlcv",
            host=host,
            port=DEFAULT_IBKR_PORT,
            client_id_configured=bool(client_id_text),
        )
    try:
        module_loader("ib_insync")
    except ImportError:
        return _status_payload(
            status="unavailable",
            reason_code="missing_dependency",
            detail="ib_insync is not installed for IBKR read-only daily price refresh.",
            next_action="Do not retry IBKR in this session until ib_insync is installed and IBKR Gateway/TWS is running.",
            source_usage="read_only_daily_ohlcv",
            host=host,
            port=port,
            client_id_configured=True,
        )
    try:
        connection = socket_connector((host, port), timeout)
        try:
            connection.close()
        except Exception:
            pass
    except OSError as exc:
        return _status_payload(
            status="unavailable",
            reason_code="gateway_unavailable",
            detail=f"IBKR Gateway/TWS is not reachable at {host}:{port} ({exc}).",
            next_action="Start IBKR Gateway/TWS with API socket enabled before using PROVIDER=ibkr.",
            source_usage="read_only_daily_ohlcv",
            host=host,
            port=port,
            client_id_configured=True,
        )
    return _status_payload(
        status="available",
        reason_code="configured",
        detail=f"IBKR read-only daily bars appear configured at {host}:{port}; client id is configured.",
        next_action="Use make price-refresh TICKERS=<ticker> PROVIDER=ibkr for a one-ticker validate/preview path.",
        source_usage="read_only_daily_ohlcv",
        host=host,
        port=port,
        client_id_configured=True,
        default_client_id=DEFAULT_IBKR_CLIENT_ID,
    )


def probe_fmp_key() -> dict[str, Any]:
    return probe_provider_api_key(FMP_API_KEY_ENV, provider_label="FMP")


def probe_alpha_vantage_key() -> dict[str, Any]:
    return probe_provider_api_key(ALPHA_VANTAGE_API_KEY_ENV, provider_label="Alpha Vantage")


def probe_finnhub_key() -> dict[str, Any]:
    return probe_provider_api_key(FINNHUB_API_KEY_ENV, provider_label="Finnhub")


def build_price_ladder_status(
    *,
    ibkr_status: dict[str, Any],
    stooq_status: dict[str, Any],
    fmp_status: dict[str, Any],
    alpha_vantage_status: dict[str, Any],
    finnhub_status: dict[str, Any],
) -> dict[str, Any]:
    keyed_providers = {
        "stooq": (STOOQ_API_KEY_ENV, stooq_status),
        "fmp": (FMP_API_KEY_ENV, fmp_status),
        "alpha_vantage": (ALPHA_VANTAGE_API_KEY_ENV, alpha_vantage_status),
        "finnhub": (FINNHUB_API_KEY_ENV, finnhub_status),
    }
    required_keyed_providers = {
        "fmp": (FMP_API_KEY_ENV, fmp_status),
        "alpha_vantage": (ALPHA_VANTAGE_API_KEY_ENV, alpha_vantage_status),
        "finnhub": (FINNHUB_API_KEY_ENV, finnhub_status),
    }
    configured = [
        provider
        for provider, (_env_var, status) in keyed_providers.items()
        if str(status.get("status") or "").strip() == "available"
    ]
    available_readonly = []
    if str(ibkr_status.get("status") or "").strip() == "available":
        available_readonly.append("ibkr")
    missing_envs = [
        env_var
        for _provider, (env_var, status) in required_keyed_providers.items()
        if str(status.get("status") or "").strip() != "available"
    ]
    if configured or available_readonly:
        status = "available"
        reason_code = "configured_price_fallbacks" if available_readonly else "configured_keyed_fallbacks"
        next_action = "make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=auto"
    else:
        status = "planned"
        reason_code = "dry_run_first_no_keyed_fallbacks"
        next_action = (
            "Use make coverage-expansion-loop TOP_N=10 for the source-activation gate; "
            "configure a keyed provider before broad price coverage batches if Stooq/Yahoo are unavailable."
        )
    return _status_payload(
        status=status,
        reason_code=reason_code,
        detail=(
            "PROVIDER=auto tries Stooq, Yahoo, configured IBKR read-only daily bars, then configured FMP/Alpha Vantage/Finnhub price fallbacks. "
            "This preflight records configuration only; the refresh status records provider fetch results."
        ),
        next_action=next_action,
        provider_order=PRICE_PROVIDER_ORDER,
        available_readonly_providers=available_readonly,
        configured_keyed_providers=configured,
        missing_keyed_provider_envs=missing_envs,
        free_tier_batch_limits=FREE_TIER_BATCH_LIMITS,
    )


def build_source_activation_status(
    *,
    sec_status: dict[str, Any],
    yfinance_stage_status: dict[str, Any],
    price_ladder_status: dict[str, Any],
    fmp_status: dict[str, Any],
    alpha_vantage_status: dict[str, Any],
    finnhub_status: dict[str, Any],
    local_fundamentals_status: dict[str, Any],
    source_actionability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    local_fixable = int(local_fundamentals_status.get("share_count_fixable_ticker_count", 0) or 0) + int(
        local_fundamentals_status.get("fundamentals_fixable_ticker_count", 0) or 0
    )
    has_executable_source = any(
        (
            sec_status.get("status") == "available",
            yfinance_stage_status.get("status") == "available",
            fmp_status.get("status") == "available",
            alpha_vantage_status.get("status") == "available",
            finnhub_status.get("status") == "available",
            price_ladder_status.get("status") == "available",
            local_fixable > 0,
        )
    )
    missing_keys = [
        str(item).strip()
        for item in price_ladder_status.get("missing_keyed_provider_envs", [])
        if str(item).strip()
    ]
    actionability = source_actionability if isinstance(source_actionability, dict) else {}
    if has_executable_source and actionability.get("do_not_repeat_without_new_source"):
        return _status_payload(
            status="not_required",
            reason_code="workflow_evidence_only",
            detail=(
                "Sources are reachable, but current fundamentals/share-count blockers already have reviewed non-actionable proof; "
                "do not treat source reachability as a coverage unlock."
            ),
            next_action=(
                "Use make provider-setup-checklist after project-status confirms source-proof queues are exhausted; wait for new provider data, keyed sources, reviewed manual rows, "
                "or changed blockers create an executable source-backed slice."
            ),
            activation_commands=(),
            missing_keyed_provider_envs=missing_keys,
        )
    if has_executable_source:
        return _status_payload(
            status="not_required",
            reason_code="executable_source_available",
            detail="At least one source path or local reviewed row can be used before broad coverage expansion.",
            next_action="Use the relevant reviewed dry-run, validate, preview, and apply gate.",
            activation_commands=(),
            missing_keyed_provider_envs=missing_keys,
        )
    return _status_payload(
        status="required",
        reason_code="no_executable_source_path",
        detail=(
            "SEC/Stooq/Yahoo are unavailable or unusable, no keyed fallback provider is configured, "
            "and local reviewed rows do not fix current blockers; do not run broad coverage batches."
        ),
        next_action="Configure at least one provider key or add reviewed local source rows, then rerun make session-source-preflight.",
        activation_commands=(
            "cp config/provider_keys.env.example config/provider_keys.env",
            "chmod 600 config/provider_keys.env",
            "open -e config/provider_keys.env",
            "make session-source-preflight",
        ),
        missing_keyed_provider_envs=missing_keys,
    )


def inspect_local_fundamentals(root: Path, *, data_dir: Path | None = None) -> dict[str, Any]:
    data_path = resolve_data_dir(data_dir, root)
    path = data_path / "fundamentals.csv"
    if not path.exists():
        return _status_payload(
            status="missing_file",
            reason_code="missing_file",
            detail="Canonical local fundamentals file is not present.",
            next_action="",
            path=str(path),
            row_count=0,
            ticker_count=0,
        )

    try:
        frame = pd.read_csv(path)
    except Exception as exc:
        return _status_payload(
            status="unreadable",
            reason_code="read_failed",
            detail=f"Could not read local fundamentals: {exc}",
            next_action="Inspect data/fundamentals.csv before using local fallback rows.",
            path=str(path),
            row_count=0,
            ticker_count=0,
        )

    if frame.empty or "ticker" not in frame.columns:
        return _status_payload(
            status="no_rows",
            reason_code="no_rows",
            detail="Canonical local fundamentals exist but do not contain usable ticker rows.",
            next_action="",
            path=str(path),
            row_count=0,
            ticker_count=0,
        )

    tickers = (
        frame["ticker"]
        .dropna()
        .astype(str)
        .str.upper()
        .str.strip()
    )
    tickers = tickers.loc[tickers.ne("")]
    row_count = int(len(tickers))
    ticker_count = int(tickers.nunique())
    if row_count == 0:
        return _status_payload(
            status="no_rows",
            reason_code="no_rows",
            detail="Canonical local fundamentals file has no non-empty ticker rows.",
            next_action="",
            path=str(path),
            row_count=0,
            ticker_count=0,
        )

    shares_series = frame["shares_outstanding"] if "shares_outstanding" in frame.columns else pd.Series(dtype="object")
    revenue_series = frame["revenue"] if "revenue" in frame.columns else pd.Series(dtype="object")
    free_cash_flow_series = frame["free_cash_flow"] if "free_cash_flow" in frame.columns else pd.Series(dtype="object")
    fcf_margin_series = frame["fcf_margin"] if "fcf_margin" in frame.columns else pd.Series(dtype="object")

    populated_shares = int(shares_series.notna().sum()) if not shares_series.empty else 0
    populated_revenue = int(revenue_series.notna().sum()) if not revenue_series.empty else 0
    populated_free_cash_flow = int(free_cash_flow_series.notna().sum()) if not free_cash_flow_series.empty else 0
    populated_fcf_margin = int(fcf_margin_series.notna().sum()) if not fcf_margin_series.empty else 0

    share_count_fixable_ticker_count = 0
    fundamentals_fixable_ticker_count = 0
    readiness_path = data_path / "reports" / "ticker_readiness_report.csv"
    if readiness_path.exists():
        try:
            readiness = pd.read_csv(readiness_path)
        except Exception:
            readiness = pd.DataFrame()
        if not readiness.empty and "ticker" in readiness.columns:
            local_by_ticker = frame.copy()
            local_by_ticker["ticker"] = (
                local_by_ticker["ticker"].fillna("").astype(str).str.upper().str.strip()
            )
            readiness["ticker"] = readiness["ticker"].fillna("").astype(str).str.upper().str.strip()
            merged = readiness.merge(local_by_ticker, on="ticker", how="left", suffixes=("_readiness", ""))
            missing_data = merged.get("missing_data", pd.Series("", index=merged.index)).fillna("").astype(str).str.lower()
            share_mask = missing_data.str.contains("shares_outstanding|shares outstanding", regex=True)
            share_count_fixable_ticker_count = int(
                (share_mask & merged.get("shares_outstanding", pd.Series(index=merged.index)).notna()).sum()
            )
            fundamentals_mask = missing_data.str.contains(
                "revenue|free cash flow|free_cash_flow|fcf margin|fcf_margin", regex=True
            )

            def has_value(row: pd.Series, columns: list[str]) -> bool:
                for column in columns:
                    if column not in row.index:
                        continue
                    value = row.get(column)
                    if pd.notna(value) and str(value).strip() != "":
                        return True
                return False

            def missing_fundamental_fields(text: str) -> list[str]:
                lowered = str(text or "").lower()
                fields: list[str] = []
                if "revenue" in lowered:
                    fields.append("revenue")
                if "free cash flow" in lowered or "free_cash_flow" in lowered:
                    fields.append("free_cash_flow")
                if "fcf margin" in lowered or "fcf_margin" in lowered:
                    fields.append("fcf_margin")
                return fields

            field_columns = {
                "revenue": ["revenue"],
                "free_cash_flow": ["free_cash_flow", "fcf"],
                "fcf_margin": ["fcf_margin"],
            }
            fundamentals_fixable_ticker_count = int(
                sum(
                    all(has_value(row, field_columns[field]) for field in missing_fundamental_fields(row.get("missing_data", "")))
                    for _, row in merged.loc[fundamentals_mask].iterrows()
                    if missing_fundamental_fields(row.get("missing_data", ""))
                )
            )

    return _status_payload(
        status="available",
        reason_code="ok",
        detail=f"Found {row_count} local fundamentals row(s) across {ticker_count} ticker(s).",
        next_action="Use reviewed local fundamentals rows before retrying unavailable remote paths.",
        path=str(path),
        row_count=row_count,
        ticker_count=ticker_count,
        populated_shares_row_count=populated_shares,
        populated_revenue_row_count=populated_revenue,
        populated_free_cash_flow_row_count=populated_free_cash_flow,
        populated_fcf_margin_row_count=populated_fcf_margin,
        share_count_fixable_ticker_count=share_count_fixable_ticker_count,
        fundamentals_fixable_ticker_count=fundamentals_fixable_ticker_count,
    )


def build_source_actionability(root: Path) -> dict[str, Any]:
    fundamentals_rows = _read_csv(root / "outputs" / "fundamentals_peer_worklist.csv")
    readiness_rows = {
        str(row.get("ticker") or "").upper().strip(): row
        for row in _read_csv(root / "data" / "reports" / "ticker_readiness_report.csv")
        if str(row.get("ticker") or "").strip()
    }

    def is_operating_company_candidate(ticker: str) -> bool:
        if ticker in {"QQQ", "SMH"}:
            return False
        row = readiness_rows.get(ticker, {})
        asset_type = str(row.get("asset_type") or "company").strip().lower()
        if asset_type != "company":
            return False
        if _truthy(row.get("dcf_ready")):
            return False
        name = str(row.get("name") or "").strip().lower()
        return not any(marker in name for marker in ("acquisition", "spac", "blank check"))

    candidate_tickers = {
        str(row.get("ticker") or "").upper().strip()
        for row in fundamentals_rows
        if str(row.get("ticker") or "").strip()
        and str(row.get("missing_required_for_dcf") or "").strip()
        and not _truthy(row.get("dcf_ready"))
    }
    candidate_tickers = {ticker for ticker in candidate_tickers if is_operating_company_candidate(ticker)}
    reviewed_rows = _read_csv(root / "data" / "reviewed_batch_proofs.csv")
    relevant_lanes = {"fundamentals", "fundamentals_dcf", "share_count"}
    non_actionable_outcomes = {"candidate_context_only", "still_blocked", "skipped", "excluded"}
    reviewed_non_actionable: set[str] = set()
    for row in reviewed_rows:
        lane = str(row.get("lane") or "").lower().strip()
        outcome = str(row.get("final_outcome") or "").lower().strip()
        if lane not in relevant_lanes or outcome not in non_actionable_outcomes:
            continue
        tickers = str(row.get("tickers") or "").replace("|", ",").replace(";", ",")
        for part in tickers.split(","):
            ticker = part.upper().strip()
            if ticker and ticker != "-":
                reviewed_non_actionable.add(ticker)
    reviewed_candidates = candidate_tickers & reviewed_non_actionable
    unreviewed_candidates = candidate_tickers - reviewed_non_actionable
    dcf_queue_reviewed_non_actionable = False
    try:
        from src.dcf_input_proof_queue import build_dcf_input_proof_queue_from_files

        dcf_rows = build_dcf_input_proof_queue_from_files(root, top_n=25)
        dcf_queue_reviewed_non_actionable = bool(dcf_rows) and all(
            "reviewed proof ledger already records" in str(getattr(row, "source_note", "") or "").lower()
            for row in dcf_rows
        )
    except Exception:
        dcf_queue_reviewed_non_actionable = False
    if dcf_queue_reviewed_non_actionable:
        reviewed_candidates = set(candidate_tickers)
        unreviewed_candidates = set()
    exhausted = bool(candidate_tickers) and not unreviewed_candidates
    return {
        "fundamentals_share_count_candidates": len(candidate_tickers),
        "reviewed_non_actionable_fundamentals_share_count": len(reviewed_candidates),
        "unreviewed_fundamentals_share_count_candidates": len(unreviewed_candidates),
        "do_not_repeat_without_new_source": exhausted,
        "dcf_queue_reviewed_non_actionable": dcf_queue_reviewed_non_actionable,
        "next_action": (
            "Wait for new provider data, keyed sources, reviewed manual source rows, or changed blockers before repeating fundamentals/share-count paths."
            if exhausted
            else "Use the relevant reviewed dry-run, validate, preview, and apply gate for unreviewed source-backed candidates."
        ),
        "sample_unreviewed_tickers": sorted(unreviewed_candidates)[:10],
        "sample_reviewed_non_actionable_tickers": sorted(reviewed_candidates)[:10],
    }


def build_source_categories(
    *,
    sec_status: dict[str, Any],
    sec_submissions_status: dict[str, Any],
    yfinance_import_status: dict[str, Any],
    yfinance_stage_status: dict[str, Any],
    ibkr_status: dict[str, Any],
    fmp_status: dict[str, Any],
    alpha_vantage_status: dict[str, Any],
    finnhub_status: dict[str, Any],
) -> dict[str, list[str]]:
    free_public_available = ["stooq", "yahoo"]
    if sec_status.get("status") == "available":
        free_public_available.append("sec")
    if sec_submissions_status.get("status") == "available":
        free_public_available.append("sec_submissions")
    if yfinance_import_status.get("status") == "available":
        free_public_available.append("yfinance_import")
    if yfinance_stage_status.get("status") == "available":
        free_public_available.append("yfinance_stage")

    keyed_free_tier_available = [
        provider
        for provider, status in (
            ("fmp", fmp_status),
            ("alpha_vantage", alpha_vantage_status),
            ("finnhub", finnhub_status),
        )
        if status.get("status") == "available"
    ]
    paid_or_locked = [
        provider
        for provider, status in (
            ("fmp", fmp_status),
            ("alpha_vantage", alpha_vantage_status),
            ("finnhub", finnhub_status),
        )
        if status.get("status") != "available"
    ]
    optional_broker_disabled = [] if ibkr_status.get("status") == "available" else ["ibkr"]
    return {
        "free_public_available": free_public_available,
        "optional_broker_disabled": optional_broker_disabled,
        "keyed_free_tier_available": keyed_free_tier_available,
        "paid_or_locked": paid_or_locked,
    }


def build_source_activation_console_v2(
    *,
    sources: dict[str, dict[str, Any]],
    source_categories: dict[str, list[str]],
    do_not_retry_paths: list[str],
    preferred_lane_order: list[str],
    source_actionability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    def reason(source_name: str) -> str:
        source = sources.get(source_name, {})
        return str(source.get("reason_code") or "unknown").strip()

    yfinance_reason = reason("yfinance_stage")
    if yfinance_reason == "dependency_unavailable":
        yfinance_reason = reason("yfinance_import")
    source_path_last_tried = {
        "sec": reason("sec"),
        "sec_submissions": reason("sec_submissions"),
        "yfinance_fundamentals": yfinance_reason,
        "price_ladder": reason("price_ladder"),
        "fmp": reason("fmp"),
        "alpha_vantage": reason("alpha_vantage"),
        "finnhub": reason("finnhub"),
        "ibkr": reason("ibkr_price"),
    }
    provider_capabilities = {
        "sec": {
            "can_cover": ["fundamentals", "share_count"],
            "usage": "source_backed_companyfacts",
            "default_state": "free_public_available" if sources["sec"].get("status") == "available" else "unavailable",
        },
        "sec_submissions": {
            "can_cover": ["metadata"],
            "usage": "metadata_evidence_only",
            "default_state": (
                "free_public_available" if sources["sec_submissions"].get("status") == "available" else "unavailable"
            ),
        },
        "yfinance": {
            "can_cover": ["price", "fundamentals", "optional_context"],
            "usage": "provider_assisted_research_data",
            "default_state": (
                "free_public_available" if sources["yfinance_stage"].get("status") == "available" else "unavailable"
            ),
        },
        "stooq": {
            "can_cover": ["price"],
            "usage": "free_public_daily_ohlcv",
            "default_state": "free_public_available",
        },
        "fmp": {
            "can_cover": ["price", "fundamentals", "share_count"],
            "usage": "keyed_free_tier_fallback",
            "default_state": (
                "keyed_free_tier_available" if sources["fmp"].get("status") == "available" else "keyed_free_tier_missing"
            ),
        },
        "alpha_vantage": {
            "can_cover": ["price", "fundamentals", "share_count"],
            "usage": "keyed_free_tier_fallback",
            "default_state": (
                "keyed_free_tier_available"
                if sources["alpha_vantage"].get("status") == "available"
                else "keyed_free_tier_missing"
            ),
        },
        "finnhub": {
            "can_cover": ["price", "fundamentals", "share_count"],
            "usage": "keyed_free_tier_fallback",
            "default_state": (
                "keyed_free_tier_available"
                if sources["finnhub"].get("status") == "available"
                else "keyed_free_tier_missing"
            ),
        },
        "ibkr": {
            "can_cover": ["price"],
            "usage": "read_only_daily_ohlcv",
            "default_state": (
                "optional_broker_configured"
                if sources["ibkr_price"].get("status") == "available"
                else "optional_broker_disabled"
            ),
        },
    }
    setup_commands = {
        "provider_env_file": "cp config/provider_keys.env.example config/provider_keys.env && chmod 600 config/provider_keys.env",
        "fmp": "Set FMP_API_KEY in config/provider_keys.env; rerun make session-source-preflight.",
        "alpha_vantage": "Set ALPHA_VANTAGE_API_KEY in config/provider_keys.env; rerun make session-source-preflight.",
        "finnhub": "Set FINNHUB_API_KEY in config/provider_keys.env; rerun make session-source-preflight.",
        "stooq": "Set STOOQ_API_KEY only if unauthenticated Stooq CSV access is unavailable; rerun make session-source-preflight.",
        "ibkr": (
            "Optional read-only broker data only; leave disabled unless explicitly choosing IBKR daily OHLCV. "
            "If intentionally enabled, configure IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID and run Gateway/TWS."
        ),
    }
    next_executable_lane = preferred_lane_order[0] if preferred_lane_order else "coverage_workflow_evidence"
    next_executable_command = "make coverage-frontier TOP_N=10"
    if source_actionability and source_actionability.get("do_not_repeat_without_new_source"):
        next_executable_lane = "coverage_workflow_evidence"
        next_executable_command = "make provider-setup-checklist"
    avoid_repeating = list(do_not_retry_paths)
    next_step_reason = "Use the next executable lane; unavailable source paths are recorded for this session."
    if source_actionability and source_actionability.get("do_not_repeat_without_new_source"):
        avoid_repeating = ["fundamentals_share_count_source_ladder"]
        next_step_reason = (
            "Current fundamentals/share-count blockers already have reviewed non-actionable proof; "
            "review provider setup before repeating source ladders."
        )

    return {
        "free_public_available": source_categories.get("free_public_available", []),
        "optional_broker_disabled": source_categories.get("optional_broker_disabled", []),
        "keyed_free_tier_missing": source_categories.get("paid_or_locked", []),
        "keyed_free_tier_available": source_categories.get("keyed_free_tier_available", []),
        "paid_or_locked": source_categories.get("paid_or_locked", []),
        "source_path_last_tried": source_path_last_tried,
        "do_not_retry_this_session": do_not_retry_paths,
        "setup_commands": setup_commands,
        "free_tier_batch_limits": FREE_TIER_BATCH_LIMITS,
        "provider_capabilities": provider_capabilities,
        "next_executable_lane": next_executable_lane,
        "next_executable_command": next_executable_command,
        "operator_summary": {
            "can_run_now": [next_executable_lane],
            "needs_setup": source_categories.get("paid_or_locked", []),
            "avoid_repeating": avoid_repeating,
            "next_step": next_executable_command,
            "next_step_reason": next_step_reason,
        },
        "non_retry_rule": "Record unavailable source paths once, then pivot to the next executable lane in this session.",
    }


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def build_session_source_preflight(
    base_dir: Path | str | None = None,
    *,
    data_dir: Path | None = None,
    sec_user_agent: str | None = None,
    sec_probe: Callable[[str | None], dict[str, Any]] = probe_sec_access,
    sec_submissions_probe: Callable[[str | None], dict[str, Any]] = probe_sec_submissions_access,
    yfinance_import_probe: Callable[[], dict[str, Any]] = probe_yfinance_import,
    yfinance_stage_probe: Callable[[], dict[str, Any]] | None = None,
    stooq_key_probe: Callable[[], dict[str, Any]] = probe_stooq_key,
    ibkr_price_probe: Callable[[], dict[str, Any]] = probe_ibkr_price,
    fmp_key_probe: Callable[[], dict[str, Any]] = probe_fmp_key,
    alpha_vantage_key_probe: Callable[[], dict[str, Any]] = probe_alpha_vantage_key,
    finnhub_key_probe: Callable[[], dict[str, Any]] = probe_finnhub_key,
    sample_ticker: str = DEFAULT_YFINANCE_SAMPLE_TICKER,
) -> dict[str, Any]:
    root = resolve_project_root(base_dir)
    data_path = resolve_data_dir(data_dir, root)

    sec_status = sec_probe(sec_user_agent)
    sec_submissions_status = sec_submissions_probe(sec_user_agent)
    yfinance_import_status = yfinance_import_probe()
    if yfinance_import_status["status"] == "available":
        yfinance_stage_status = (
            yfinance_stage_probe()
            if yfinance_stage_probe is not None
            else probe_yfinance_stage(sample_ticker=sample_ticker)
        )
    else:
        yfinance_stage_status = _status_payload(
            status="skipped",
            reason_code="dependency_unavailable",
            detail="Skipped the yfinance fundamentals probe because the dependency is unavailable.",
            next_action=yfinance_import_status.get("next_action", ""),
            sample_ticker=str(sample_ticker or DEFAULT_YFINANCE_SAMPLE_TICKER).upper().strip(),
        )
    stooq_status = stooq_key_probe()
    ibkr_status = ibkr_price_probe()
    fmp_status = fmp_key_probe()
    alpha_vantage_status = alpha_vantage_key_probe()
    finnhub_status = finnhub_key_probe()
    price_ladder_status = build_price_ladder_status(
        ibkr_status=ibkr_status,
        stooq_status=stooq_status,
        fmp_status=fmp_status,
        alpha_vantage_status=alpha_vantage_status,
        finnhub_status=finnhub_status,
    )
    local_fundamentals_status = inspect_local_fundamentals(root, data_dir=data_path)
    source_categories = build_source_categories(
        sec_status=sec_status,
        sec_submissions_status=sec_submissions_status,
        yfinance_import_status=yfinance_import_status,
        yfinance_stage_status=yfinance_stage_status,
        ibkr_status=ibkr_status,
        fmp_status=fmp_status,
        alpha_vantage_status=alpha_vantage_status,
        finnhub_status=finnhub_status,
    )
    source_actionability = build_source_actionability(root)
    source_activation_status = build_source_activation_status(
        sec_status=sec_status,
        yfinance_stage_status=yfinance_stage_status,
        price_ladder_status=price_ladder_status,
        fmp_status=fmp_status,
        alpha_vantage_status=alpha_vantage_status,
        finnhub_status=finnhub_status,
        local_fundamentals_status=local_fundamentals_status,
        source_actionability=source_actionability,
    )

    session_flags: list[str] = []
    do_not_retry_paths: list[str] = []
    if sec_status["status"] != "available":
        session_flags.append("session_sec_unavailable")
        do_not_retry_paths.append("sec")
    if yfinance_import_status["status"] != "available" or yfinance_stage_status["status"] != "available":
        session_flags.append("session_yfinance_unavailable")
        do_not_retry_paths.append("yfinance_fundamentals")

    source_lanes: list[str] = []
    preferred_lane_order: list[str] = []
    local_can_fix_shares = False
    local_can_fix_fundamentals = False
    local_can_fix_current_blocker = False
    if sec_status["status"] == "available":
        source_lanes.append("sec_fundamentals_share_count")
        preferred_lane_order.append("sec_fundamentals_share_count")
    if local_fundamentals_status["status"] == "available":
        source_lanes.append("local_reviewed_fundamentals_share_count")
        local_can_fix_shares = int(local_fundamentals_status.get("share_count_fixable_ticker_count", 0)) > 0
        local_can_fix_fundamentals = int(local_fundamentals_status.get("fundamentals_fixable_ticker_count", 0)) > 0
        local_can_fix_current_blocker = local_can_fix_shares or local_can_fix_fundamentals
        if (
            "local_reviewed_fundamentals_share_count" not in preferred_lane_order
            and sec_status["status"] != "available"
            and local_can_fix_current_blocker
        ):
            preferred_lane_order.append("local_reviewed_fundamentals_share_count")
    if yfinance_stage_status["status"] == "available":
        source_lanes.append("yfinance_fundamentals_share_count")
        if (
            "yfinance_fundamentals_share_count" not in preferred_lane_order
            and sec_status["status"] != "available"
            and not local_can_fix_current_blocker
        ):
            preferred_lane_order.append("yfinance_fundamentals_share_count")
    if fmp_status["status"] == "available":
        source_lanes.append("fmp_fundamentals_share_count")
        if (
            "fmp_fundamentals_share_count" not in preferred_lane_order
            and sec_status["status"] != "available"
            and not local_can_fix_current_blocker
            and yfinance_stage_status["status"] != "available"
        ):
            preferred_lane_order.append("fmp_fundamentals_share_count")
    if alpha_vantage_status["status"] == "available":
        source_lanes.append("alpha_vantage_fundamentals_share_count")
        if (
            "alpha_vantage_fundamentals_share_count" not in preferred_lane_order
            and sec_status["status"] != "available"
            and not local_can_fix_current_blocker
            and yfinance_stage_status["status"] != "available"
            and fmp_status["status"] != "available"
        ):
            preferred_lane_order.append("alpha_vantage_fundamentals_share_count")
    if finnhub_status["status"] == "available":
        source_lanes.append("finnhub_fundamentals_share_count")
        if (
            "finnhub_fundamentals_share_count" not in preferred_lane_order
            and sec_status["status"] != "available"
            and not local_can_fix_current_blocker
            and yfinance_stage_status["status"] != "available"
            and fmp_status["status"] != "available"
            and alpha_vantage_status["status"] != "available"
        ):
            preferred_lane_order.append("finnhub_fundamentals_share_count")
    if price_ladder_status["status"] == "available":
        source_lanes.append("price_coverage_provider_ladder")
        if not preferred_lane_order:
            preferred_lane_order.append("price_coverage_provider_ladder")
    if ibkr_status["status"] == "available":
        source_lanes.append("ibkr_price_coverage")
    if sec_submissions_status["status"] == "available":
        source_lanes.append("sec_submissions_metadata")

    preferred_lane_order.extend(ALWAYS_EXECUTABLE_LANES)
    available_lanes = _dedupe_preserve_order(source_lanes + ALWAYS_EXECUTABLE_LANES)
    preferred_lane_order = _dedupe_preserve_order(preferred_lane_order)
    sources = {
        "sec": sec_status,
        "sec_submissions": sec_submissions_status,
        "yfinance_import": yfinance_import_status,
        "yfinance_stage": yfinance_stage_status,
        "price_ladder": price_ladder_status,
        "ibkr_price": ibkr_status,
        "fmp": fmp_status,
        "alpha_vantage": alpha_vantage_status,
        "finnhub": finnhub_status,
        "local_fundamentals": local_fundamentals_status,
    }
    source_activation_console_v2 = build_source_activation_console_v2(
        sources=sources,
        source_categories=source_categories,
        do_not_retry_paths=do_not_retry_paths,
        preferred_lane_order=preferred_lane_order,
        source_actionability=source_actionability,
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "project_root": str(root),
        "data_dir": str(data_path),
        "session_flags": session_flags,
        "do_not_retry_paths": do_not_retry_paths,
        "available_lanes": available_lanes,
        "preferred_lane_order": preferred_lane_order,
        "source_categories": source_categories,
        "source_activation_console_v2": source_activation_console_v2,
        "sources": sources,
        "source_activation": source_activation_status,
        "source_actionability": source_actionability,
    }


def apply_continuation_gate(
    preflight: dict[str, Any],
    continuation_gate: ContinuationGate,
) -> dict[str, Any]:
    """Overlay continuation routing without changing source availability evidence."""

    overlaid = copy.deepcopy(preflight)
    overlaid["continuation_gate"] = asdict(continuation_gate)
    if not continuation_gate.suppress_execution:
        return overlaid

    console = overlaid.get("source_activation_console_v2", {})
    if not isinstance(console, dict):
        console = {}
        overlaid["source_activation_console_v2"] = console
    console["next_executable_lane"] = continuation_gate.state
    console["next_executable_command"] = continuation_gate.next_safe_command
    operator_summary = console.get("operator_summary", {})
    if not isinstance(operator_summary, dict):
        operator_summary = {}
        console["operator_summary"] = operator_summary
    existing_avoid = operator_summary.get("avoid_repeating", [])
    if not isinstance(existing_avoid, list):
        existing_avoid = [str(existing_avoid)] if str(existing_avoid).strip() else []
    avoid_repeating = _dedupe_preserve_order(
        [
            *[str(item) for item in existing_avoid if str(item).strip()],
            "broad_refresh",
            "source_proof",
            "readiness_rebuild",
        ]
    )
    operator_summary.update(
        {
            "can_run_now": [continuation_gate.state],
            "avoid_repeating": avoid_repeating,
            "next_step": continuation_gate.next_safe_command,
            "next_step_reason": continuation_gate.reason,
        }
    )
    return overlaid


def render_session_source_preflight(preflight: dict[str, Any]) -> str:
    sources = preflight["sources"]
    categories = preflight.get("source_categories", {})
    lines = [
        "Session source preflight",
        f"project_root: {preflight['project_root']}",
        f"data_dir: {preflight['data_dir']}",
        f"generated_at: {preflight['generated_at']}",
        f"session_flags: {', '.join(preflight['session_flags']) or '-'}",
        f"do_not_retry_paths: {_human_source_gate_list(preflight['do_not_retry_paths'])}",
        "preferred_lane_order:",
        *[f"- {_human_source_gate_label(lane)}" for lane in preflight["preferred_lane_order"]],
        "source_categories:",
        f"  free_public_available: {', '.join(categories.get('free_public_available', [])) or '-'}",
        f"  optional_broker_disabled: {', '.join(categories.get('optional_broker_disabled', [])) or '-'}",
        f"  keyed_free_tier_available: {', '.join(categories.get('keyed_free_tier_available', [])) or '-'}",
        f"  paid_or_locked: {', '.join(categories.get('paid_or_locked', [])) or '-'}",
        "source_status:",
    ]
    continuation_gate = preflight.get("continuation_gate", {})
    if isinstance(continuation_gate, dict) and continuation_gate.get("suppress_execution"):
        lines[1:1] = [
            f"{READINESS_CONTINUATION_GATE_HEADING}: {continuation_gate.get('state', '-')}",
            f"- Next safe preview: {continuation_gate.get('next_safe_command', '-')}",
            f"- Reason: {continuation_gate.get('reason', '-')}",
            "- Source availability and lane details below are planning context only; they do not authorize execution.",
            f"- Inspection boundary: {continuation_gate.get('next_safe_command', '-')}. {READINESS_PREVIEW_NOTE}",
            f"- Stop rule: {continuation_gate.get('stop_rule', '-')}",
        ]
    for source_name in (
        "sec",
        "sec_submissions",
        "yfinance_import",
        "yfinance_stage",
        "price_ladder",
        "ibkr_price",
        "fmp",
        "alpha_vantage",
        "finnhub",
        "local_fundamentals",
    ):
        source = sources[source_name]
        lines.extend(
            [
                f"- {source_name}: status={source['status']} reason={source['reason_code']}",
                f"  detail: {source['detail']}",
            ]
        )
        next_action = str(source.get("next_action", "")).strip()
        if next_action:
            lines.append(f"  next_action: {next_action}")
        if source_name == "sec_submissions":
            lines.append(f"  source_usage: {source.get('source_usage', 'metadata_evidence_only')}")
            sample_bits = [
                str(source.get("sample_cik") or "").strip(),
                str(source.get("sample_entity_name") or "").strip(),
                str(source.get("sample_sic_description") or "").strip(),
            ]
            sample_detail = " | ".join(bit for bit in sample_bits if bit)
            if sample_detail:
                lines.append(f"  sample_metadata: {sample_detail}")
        if source_name == "price_ladder":
            lines.append(f"  provider_order: {', '.join(source.get('provider_order', [])) or '-'}")
            lines.append(
                "  available_readonly_providers: "
                f"{', '.join(source.get('available_readonly_providers', [])) or '-'}"
            )
            lines.append(
                "  configured_price_fallbacks: "
                f"{', '.join(source.get('configured_keyed_providers', [])) or '-'}"
            )
            lines.append(
                "  missing_price_keys: "
                f"{', '.join(source.get('missing_keyed_provider_envs', [])) or '-'}"
            )
            limits = source.get("free_tier_batch_limits", {})
            if isinstance(limits, dict) and limits:
                rendered_limits = []
                for provider in ("fmp", "alpha_vantage", "finnhub"):
                    payload = limits.get(provider, {})
                    if not isinstance(payload, dict):
                        continue
                    daily_limit = payload.get("recommended_daily_request_limit")
                    if daily_limit:
                        rendered_limits.append(f"{provider}<={daily_limit}/day")
                if rendered_limits:
                    lines.append(f"  free_tier_batch_limits: {', '.join(rendered_limits)}")
        if source_name == "ibkr_price":
            lines.append(f"  source_usage: {source.get('source_usage', 'read_only_daily_ohlcv')}")
            lines.append(
                "  connection: "
                f"host={source.get('host', DEFAULT_IBKR_HOST)} port={source.get('port', DEFAULT_IBKR_PORT)} "
                f"client_id_configured={bool(source.get('client_id_configured', False))}"
            )
        if source_name == "local_fundamentals":
            lines.append(
                "  row_count: "
                f"{source.get('row_count', 0)} ticker_count: {source.get('ticker_count', 0)} path: {source.get('path', '')}"
            )
            lines.append(
                "  populated_rows: "
                f"shares={source.get('populated_shares_row_count', 0)} "
                f"revenue={source.get('populated_revenue_row_count', 0)} "
                f"free_cash_flow={source.get('populated_free_cash_flow_row_count', 0)} "
                f"fcf_margin={source.get('populated_fcf_margin_row_count', 0)}"
            )
            lines.append(
                "  fixable_blockers: "
                f"share_count={source.get('share_count_fixable_ticker_count', 0)} "
                f"fundamentals={source.get('fundamentals_fixable_ticker_count', 0)}"
            )
    activation = preflight.get("source_activation", {})
    if isinstance(activation, dict):
        lines.extend(
            [
                f"source_activation: {activation.get('status', 'unknown')}",
                f"  reason: {_human_source_gate_label(activation.get('reason_code', ''))}",
                f"  detail: {_human_source_gate_label(activation.get('detail', ''))}",
            ]
        )
        next_action = str(activation.get("next_action", "")).strip()
        if next_action:
            lines.append(f"  next_action: {next_action}")
        commands = [str(item).strip() for item in activation.get("activation_commands", []) if str(item).strip()]
        if commands:
            lines.append("  activation_commands:")
            lines.extend(f"  - {command}" for command in commands)
    actionability = preflight.get("source_actionability", {})
    if isinstance(actionability, dict) and actionability:
        lines.extend(
            [
                "source_actionability:",
                f"  fundamentals_share_count_candidates: {actionability.get('fundamentals_share_count_candidates', 0)}",
                (
                    "  reviewed_non_actionable_fundamentals_share_count: "
                    f"{actionability.get('reviewed_non_actionable_fundamentals_share_count', 0)}"
                ),
                (
                    "  unreviewed_fundamentals_share_count_candidates: "
                    f"{actionability.get('unreviewed_fundamentals_share_count_candidates', 0)}"
                ),
                (
                    "  dcf_queue_reviewed_non_actionable: "
                    f"{'yes' if actionability.get('dcf_queue_reviewed_non_actionable') else 'no'}"
                ),
                (
                    "  do_not_repeat_without_new_source: "
                    f"{'yes' if actionability.get('do_not_repeat_without_new_source') else 'no'}"
                ),
                f"  next_action: {actionability.get('next_action', '-')}",
            ]
        )
    console = preflight.get("source_activation_console_v2", {})
    if isinstance(console, dict) and console:
        lines.extend(
            [
                "source_activation_console_v2:",
                f"  next_executable_lane: {_human_source_gate_label(console.get('next_executable_lane', 'coverage_workflow_evidence'))}",
                f"  next_executable_command: {console.get('next_executable_command', 'make coverage-frontier TOP_N=10')}",
                "  source_path_last_tried:",
            ]
        )
        source_path_last_tried = console.get("source_path_last_tried", {})
        if isinstance(source_path_last_tried, dict):
            for source_name in ("sec", "sec_submissions", "yfinance_fundamentals", "price_ladder", "fmp", "alpha_vantage", "finnhub", "ibkr"):
                if source_name in source_path_last_tried:
                    lines.append(f"    {source_name}: {source_path_last_tried[source_name]}")
        lines.append(
            "  do_not_retry_this_session: "
            f"{', '.join(console.get('do_not_retry_this_session', [])) or '-'}"
        )
        lines.append("  setup_commands:")
        setup_commands = console.get("setup_commands", {})
        if isinstance(setup_commands, dict):
            for source_name in ("provider_env_file", "fmp", "alpha_vantage", "finnhub", "stooq", "ibkr"):
                command = str(setup_commands.get(source_name, "")).strip()
                if command:
                    lines.append(f"    {source_name}: {command}")
        limits = console.get("free_tier_batch_limits", {})
        if isinstance(limits, dict):
            limit_pieces = []
            for provider in ("fmp", "alpha_vantage", "finnhub"):
                policy = limits.get(provider, {})
                if not isinstance(policy, dict):
                    continue
                daily = policy.get("recommended_daily_request_limit")
                batch = policy.get("recommended_batch_size")
                if daily in (None, "") or batch in (None, ""):
                    continue
                limit_pieces.append(f"{provider}<={daily}/day and <={batch}/run")
            if limit_pieces:
                lines.append(f"  free_tier_batch_limits: {'; '.join(limit_pieces)}")
        lines.append("  provider_capabilities:")
        capabilities = console.get("provider_capabilities", {})
        if isinstance(capabilities, dict):
            for source_name in ("sec", "sec_submissions", "yfinance", "stooq", "fmp", "alpha_vantage", "finnhub", "ibkr"):
                capability = capabilities.get(source_name, {})
                if not isinstance(capability, dict):
                    continue
                can_cover = ", ".join(capability.get("can_cover", [])) or "-"
                usage = str(capability.get("usage", "")).strip() or "-"
                default_state = str(capability.get("default_state", "")).strip() or "-"
                lines.append(
                    f"    {source_name}: can_cover={can_cover} usage={usage} default={default_state}"
                )
        non_retry_rule = str(console.get("non_retry_rule", "")).strip()
        if non_retry_rule:
            lines.append(f"  non_retry_rule: {non_retry_rule}")
        operator_summary = console.get("operator_summary", {})
        if isinstance(operator_summary, dict) and operator_summary:
            lines.extend(
                [
                    "  operator_summary:",
                    f"    can_run_now: {_human_source_gate_list(operator_summary.get('can_run_now', []))}",
                    f"    needs_setup: {', '.join(operator_summary.get('needs_setup', [])) or '-'}",
                    f"    avoid_repeating: {_human_source_gate_list(operator_summary.get('avoid_repeating', []))}",
                    f"    next_step: {operator_summary.get('next_step', 'make coverage-frontier TOP_N=10')}",
                    f"    next_step_reason: {_human_source_gate_label(operator_summary.get('next_step_reason', '-'))}",
                ]
            )
    lines.append(
        "non_blocking_rule: if a remote path is unavailable in this session, record the lane outcome and continue to the next executable lane."
    )
    return "\n".join(lines)


def session_source_preflight_output_path(
    base_dir: Path | str | None = None,
    *,
    output_dir: Path | str | None = None,
) -> Path:
    root = resolve_project_root(base_dir)
    return resolve_outputs_dir(output_dir, root) / SESSION_SOURCE_PREFLIGHT_FILENAME


def write_session_source_preflight_output(
    preflight: dict[str, Any],
    base_dir: Path | str | None = None,
    *,
    output_dir: Path | str | None = None,
) -> Path:
    path = session_source_preflight_output_path(base_dir, output_dir=output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(preflight, indent=2), encoding="utf-8")
    return path


def load_session_source_preflight(
    base_dir: Path | str | None = None,
    *,
    output_dir: Path | str | None = None,
) -> dict[str, Any] | None:
    path = session_source_preflight_output_path(base_dir, output_dir=output_dir)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check current-session SEC, yfinance, and local fundamentals availability before retrying coverage work."
    )
    parser.add_argument("--root", default=".", help="Project root.")
    parser.add_argument("--data-dir", help="Optional data directory override.")
    parser.add_argument("--sec-user-agent", help="Explicit SEC User-Agent for the current session.")
    parser.add_argument("--sample-ticker", default=DEFAULT_YFINANCE_SAMPLE_TICKER, help="Ticker to probe through yfinance.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of the readable summary.")
    parser.add_argument("--write-output", action="store_true", help="Write outputs/session_source_preflight.json for other commands to reuse in this session.")
    args = parser.parse_args()

    root = resolve_project_root(args.root)
    load_provider_environment(root)
    data_path = resolve_data_dir(Path(args.data_dir) if args.data_dir else None, root)
    preflight = build_session_source_preflight(
        root,
        data_dir=data_path,
        sec_user_agent=args.sec_user_agent,
        sec_probe=probe_sec_access,
        yfinance_import_probe=probe_yfinance_import,
        sample_ticker=args.sample_ticker,
    )
    preflight = apply_continuation_gate(
        preflight,
        build_continuation_gate(
            build_profile_context(
                project_root=root,
                data_dir=data_path,
                output_dir=resolve_outputs_dir(project_root=root),
            )
        ),
    )
    if args.write_output:
        write_session_source_preflight_output(preflight, root)

    if args.json:
        print(json.dumps(preflight, indent=2))
        return

    print(format_path_context(root, data_path, None))
    print(render_session_source_preflight(preflight))


if __name__ == "__main__":
    main()
