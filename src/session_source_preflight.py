from __future__ import annotations

import argparse
import importlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd

from src.paths import format_path_context, resolve_data_dir, resolve_outputs_dir, resolve_project_root
from src.providers.yfinance_provider import build_yfinance_fundamentals_rows


SEC_TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
DEFAULT_YFINANCE_SAMPLE_TICKER = "MSFT"
SESSION_SOURCE_PREFLIGHT_FILENAME = "session_source_preflight.json"
ALWAYS_EXECUTABLE_LANES = [
    "peer_mapping_proof",
    "peer_valuation_local_reviewed",
    "earnings_optional_manual",
    "analyst_estimates_optional_manual",
    "coverage_workflow_evidence",
]


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
            fundamentals_mask = missing_data.str.contains("revenue|free cash flow|fcf margin", regex=True)
            local_fundamentals_present = (
                merged.get("revenue", pd.Series(index=merged.index)).notna()
                | merged.get("free_cash_flow", pd.Series(index=merged.index)).notna()
                | merged.get("fcf_margin", pd.Series(index=merged.index)).notna()
            )
            fundamentals_fixable_ticker_count = int((fundamentals_mask & local_fundamentals_present).sum())

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
    yfinance_import_probe: Callable[[], dict[str, Any]] = probe_yfinance_import,
    yfinance_stage_probe: Callable[[], dict[str, Any]] | None = None,
    sample_ticker: str = DEFAULT_YFINANCE_SAMPLE_TICKER,
) -> dict[str, Any]:
    root = resolve_project_root(base_dir)
    data_path = resolve_data_dir(data_dir, root)

    sec_status = sec_probe(sec_user_agent)
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
    local_fundamentals_status = inspect_local_fundamentals(root, data_dir=data_path)

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
    if sec_status["status"] == "available":
        source_lanes.append("sec_fundamentals_share_count")
        preferred_lane_order.append("sec_fundamentals_share_count")
    if local_fundamentals_status["status"] == "available":
        source_lanes.append("local_reviewed_fundamentals_share_count")
        local_can_fix_shares = int(local_fundamentals_status.get("share_count_fixable_ticker_count", 0)) > 0
        local_can_fix_fundamentals = int(local_fundamentals_status.get("fundamentals_fixable_ticker_count", 0)) > 0
        if (
            "local_reviewed_fundamentals_share_count" not in preferred_lane_order
            and sec_status["status"] != "available"
            and (local_can_fix_shares or local_can_fix_fundamentals)
        ):
            preferred_lane_order.append("local_reviewed_fundamentals_share_count")
    if yfinance_stage_status["status"] == "available":
        source_lanes.append("yfinance_fundamentals_share_count")
        if (
            "yfinance_fundamentals_share_count" not in preferred_lane_order
            and sec_status["status"] != "available"
            and local_fundamentals_status["status"] != "available"
        ):
            preferred_lane_order.append("yfinance_fundamentals_share_count")

    preferred_lane_order.extend(ALWAYS_EXECUTABLE_LANES)
    available_lanes = _dedupe_preserve_order(source_lanes + ALWAYS_EXECUTABLE_LANES)
    preferred_lane_order = _dedupe_preserve_order(preferred_lane_order)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "project_root": str(root),
        "data_dir": str(data_path),
        "session_flags": session_flags,
        "do_not_retry_paths": do_not_retry_paths,
        "available_lanes": available_lanes,
        "preferred_lane_order": preferred_lane_order,
        "sources": {
            "sec": sec_status,
            "yfinance_import": yfinance_import_status,
            "yfinance_stage": yfinance_stage_status,
            "local_fundamentals": local_fundamentals_status,
        },
    }


def render_session_source_preflight(preflight: dict[str, Any]) -> str:
    sources = preflight["sources"]
    lines = [
        "Session source preflight",
        f"project_root: {preflight['project_root']}",
        f"data_dir: {preflight['data_dir']}",
        f"generated_at: {preflight['generated_at']}",
        f"session_flags: {', '.join(preflight['session_flags']) or '-'}",
        f"do_not_retry_paths: {', '.join(preflight['do_not_retry_paths']) or '-'}",
        "preferred_lane_order:",
        *[f"- {lane}" for lane in preflight["preferred_lane_order"]],
        "source_status:",
    ]
    for source_name in ("sec", "yfinance_import", "yfinance_stage", "local_fundamentals"):
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
    data_path = resolve_data_dir(Path(args.data_dir) if args.data_dir else None, root)
    preflight = build_session_source_preflight(
        root,
        data_dir=data_path,
        sec_user_agent=args.sec_user_agent,
        sec_probe=probe_sec_access,
        yfinance_import_probe=probe_yfinance_import,
        sample_ticker=args.sample_ticker,
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
