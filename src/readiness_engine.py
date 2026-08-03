from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Any, Final

import pandas as pd
try:
    import yaml
except ImportError:  # pragma: no cover - exercised only in stripped-down environments.
    yaml = None

from src.company_analysis_scope import excludes_company_dcf_for_inputs as company_dcf_excluded
from src.loader import normalize_columns
from src.paths import PROJECT_ROOT, resolve_data_dir, resolve_outputs_dir, resolve_project_root
from src.peer_evidence_quality import assess_peer_evidence
from src.readiness_source_boundary import (
    ReadinessSourceBoundaryError,
    readiness_input_identity,
    validate_readiness_source_boundary,
)
from src.universe_model import ASSET_TYPES, build_universe_coverage_report, ensure_universe_files, infer_asset_type

ALLOWED_CANDIDATE_STATES = {"candidate", "fallback_context", "research_only"}
COMPANY_PEER_EXCLUDED_ASSET_TYPES = {"etf", "index_proxy", "fund"}

READINESS_REPORT_NAMES: tuple[str, ...] = (
    "universe_coverage_report",
    "price_coverage_report",
    "fundamentals_coverage_report",
    "dcf_readiness_report",
    "peer_readiness_report",
    "earnings_readiness_report",
    "analyst_estimates_readiness_report",
    "ticker_readiness_report",
    "feature_readiness_summary",
    "peer_unlock_worklist",
    "data_source_status",
)


TICKER_READINESS_COLUMNS = [
    "ticker",
    "name",
    "exchange",
    "asset_type",
    "sector",
    "industry",
    "theme",
    "in_master_universe",
    "in_active_universe",
    "price_ready",
    "momentum_ready",
    "market_direction_ready",
    "liquidity_ready",
    "correlation_ready",
    "fundamentals_ready",
    "dcf_ready",
    "peer_ready",
    "earnings_ready",
    "analyst_estimates_ready",
    "portfolio_ready",
    "overall_readiness_state",
    "ready_features",
    "partial_features",
    "blocked_features",
    "excluded_features",
    "missing_data",
    "next_action",
    "updated_at",
]
DATA_SOURCE_STATUS_COLUMNS = [
    "source_name",
    "source_type",
    "status",
    "credential_required",
    "credential_present",
    "last_attempted_at",
    "last_success_at",
    "rows_available",
    "failure_reason",
    "manual_fallback_available",
    "manual_import_path",
    "updated_at",
]
PRICE_COVERAGE_COLUMNS = [
    "ticker",
    "name",
    "asset_type",
    "exchange",
    "price_rows",
    "first_price_date",
    "last_price_date",
    "has_recent_price",
    "price_ready",
    "momentum_ready",
    "risk_ready",
    "missing_price_reason",
    "next_action",
    "updated_at",
]
FUNDAMENTALS_COVERAGE_COLUMNS = [
    "ticker",
    "has_fundamentals",
    "fundamentals_ready",
    "missing_fundamentals_fields",
    "source",
    "updated_at",
]
PEER_READINESS_COLUMNS = [
    "ticker",
    "peer_group",
    "peer_count",
    "sample_peers",
    "mapping_status",
    "candidate_peer_group",
    "candidate_peer_count",
    "candidate_sample_peers",
    "candidate_mapping_status",
    "candidate_states",
    "peer_blocker_type",
    "peer_price_ready",
    "peer_momentum_ready",
    "peer_fundamentals_ready",
    "peer_valuation_ready",
    "peer_trend_comparison_ready",
    "peer_valuation_comparison_ready",
    "peer_dcf_comparison_ready",
    "peer_price_ready_count",
    "peer_momentum_ready_count",
    "peer_fundamentals_ready_count",
    "peer_valuation_ready_count",
    "peer_valuation_anchor_eligible_count",
    "peer_valuation_anchor_blockers",
    "ready_peer_count",
    "peer_missing_price_tickers",
    "peer_missing_momentum_tickers",
    "peer_missing_fundamentals_tickers",
    "peer_missing_valuation_tickers",
    "peer_ready",
    "missing_peer_reason",
    "next_peer_action",
    "updated_at",
]
FEATURE_READINESS_COLUMNS = [
    "feature",
    "ready_count",
    "partial_count",
    "blocked_count",
    "excluded_count",
    "total_count",
    "top_blocker",
    "sample_ready_tickers",
    "sample_blocked_tickers",
    "next_action",
    "unlock_command",
    "dashboard_section",
    "updated_at",
]
PEER_UNLOCK_WORKLIST_COLUMNS = [
    "priority",
    "ticker",
    "peer_blocker_type",
    "unlock_stage",
    "workflow_group",
    "workflow_scope",
    "next_action_summary",
    "peer_trend_status",
    "peer_valuation_status",
    "peer_count",
    "ready_peer_count",
    "peer_price_ready_count",
    "peer_momentum_ready_count",
    "peer_fundamentals_ready_count",
    "peer_valuation_ready_count",
    "sample_peers",
    "missing_peer_reason",
    "next_peer_action",
    "next_input_file",
    "validation_sequence",
    "focus_command",
    "example_command",
    "copy_only_note",
    "updated_at",
]
READINESS_SNAPSHOT_FILENAME = "ticker_readiness_report.previous.csv"
READINESS_SNAPSHOT_TEMP_FILENAME = ".ticker_readiness_report.previous.csv.tmp"
READINESS_SNAPSHOT_SCHEMA_VERSION: Final[str] = "1"
# Bump this whenever readiness methodology can change comparison fields.
READINESS_METHOD_VERSION: Final[str] = "1"


class ReadinessSnapshotError(RuntimeError):
    """Raised when a profile-bound prior snapshot cannot be published safely."""


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


def _write(frame: pd.DataFrame, path: Path, columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if columns:
        for column in columns:
            if column not in frame.columns:
                frame[column] = pd.NA
        frame = frame.reindex(columns=columns)
    frame.to_csv(path, index=False)


def _lstat(path: Path):
    try:
        return path.lstat()
    except FileNotFoundError:
        return None


def _path_identity(path: Path) -> tuple[int, int] | None:
    metadata = _lstat(path)
    if metadata is None:
        return None
    return (metadata.st_dev, metadata.st_ino)


def _validate_snapshot_directory(path: Path, *, allow_missing: bool) -> bool:
    metadata = _lstat(path)
    if metadata is None:
        if allow_missing:
            return False
        raise ReadinessSnapshotError(f"Snapshot reports directory is missing: {path}")
    if stat.S_ISLNK(metadata.st_mode):
        raise ReadinessSnapshotError(f"Snapshot path must not be a symbolic link: {path}")
    if not stat.S_ISDIR(metadata.st_mode):
        raise ReadinessSnapshotError(f"Snapshot reports path must be a directory: {path}")
    return True


def _validate_optional_snapshot_file(path: Path) -> tuple[int, int] | None:
    metadata = _lstat(path)
    if metadata is None:
        return None
    if stat.S_ISLNK(metadata.st_mode):
        raise ReadinessSnapshotError(f"Snapshot path must not be a symbolic link: {path}")
    if not stat.S_ISREG(metadata.st_mode):
        raise ReadinessSnapshotError(f"Snapshot path must be a regular file: {path}")
    return (metadata.st_dev, metadata.st_ino)


def _read_snapshot_bytes(path: Path, expected_identity: tuple[int, int]) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        metadata = os.fstat(descriptor)
        if (metadata.st_dev, metadata.st_ino) != expected_identity or not stat.S_ISREG(metadata.st_mode):
            raise ReadinessSnapshotError("Prior readiness snapshot changed after validation.")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_bytes_to_new_file(path: Path, payload: bytes) -> tuple[int, int]:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o666)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        metadata = os.fstat(descriptor)
        return (metadata.st_dev, metadata.st_ino)
    finally:
        os.close(descriptor)


def _restore_snapshot_after_failed_publication(
    reports_path: Path,
    snapshot_path: Path,
    temporary_path: Path,
    *,
    prior_bytes: bytes | None,
    published_identity: tuple[int, int],
) -> None:
    if _path_identity(snapshot_path) != published_identity:
        raise ReadinessSnapshotError(
            "Published snapshot changed before rollback; operator recovery is required."
        )
    if prior_bytes is None:
        snapshot_path.unlink()
    else:
        if _lstat(temporary_path) is not None:
            raise ReadinessSnapshotError(
                "Snapshot temporary path changed before rollback; operator recovery is required."
            )
        _write_bytes_to_new_file(temporary_path, prior_bytes)
        os.replace(temporary_path, snapshot_path)
    try:
        _fsync_directory(reports_path)
    except OSError:
        pass


def _publish_profile_snapshot(
    reports_path: Path,
    frame: pd.DataFrame,
) -> Path:
    snapshot_path = reports_path / READINESS_SNAPSHOT_FILENAME
    temporary_path = reports_path / READINESS_SNAPSHOT_TEMP_FILENAME
    reports_created = False
    if not _validate_snapshot_directory(reports_path, allow_missing=True):
        reports_path.mkdir()
        reports_created = True
    _validate_snapshot_directory(reports_path, allow_missing=False)
    reports_identity = _path_identity(reports_path)
    if reports_identity is None:
        raise ReadinessSnapshotError("Snapshot reports directory identity is unavailable.")
    prior_identity = _validate_optional_snapshot_file(snapshot_path)
    prior_bytes = _read_snapshot_bytes(snapshot_path, prior_identity) if prior_identity is not None else None
    if _lstat(temporary_path) is not None:
        _validate_optional_snapshot_file(temporary_path)
        raise ReadinessSnapshotError(f"Snapshot temporary path already exists: {temporary_path}")

    temporary_identity: tuple[int, int] | None = None
    published = False
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(temporary_path, flags, 0o666)
        try:
            metadata = os.fstat(descriptor)
            temporary_identity = (metadata.st_dev, metadata.st_ino)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="", closefd=False) as handle:
                frame.to_csv(handle, index=False)
                handle.flush()
                os.fsync(handle.fileno())
        finally:
            os.close(descriptor)
        if _path_identity(reports_path) != reports_identity:
            raise ReadinessSnapshotError("Snapshot reports directory changed after validation.")
        if _path_identity(temporary_path) != temporary_identity:
            raise ReadinessSnapshotError("Snapshot temporary file changed after serialization.")
        if _path_identity(snapshot_path) != prior_identity:
            raise ReadinessSnapshotError("Prior readiness snapshot changed after validation.")
        _fsync_directory(reports_path)
        os.replace(temporary_path, snapshot_path)
        published = True
        if _path_identity(snapshot_path) != temporary_identity:
            raise ReadinessSnapshotError("Published readiness snapshot identity is unavailable.")
        _fsync_directory(reports_path)
        return snapshot_path
    except Exception as error:
        if published and temporary_identity is not None:
            _restore_snapshot_after_failed_publication(
                reports_path,
                snapshot_path,
                temporary_path,
                prior_bytes=prior_bytes,
                published_identity=temporary_identity,
            )
        elif temporary_identity is None or _path_identity(temporary_path) == temporary_identity:
            if _lstat(temporary_path) is not None:
                temporary_path.unlink()
        if reports_created and _lstat(reports_path) is not None and not any(reports_path.iterdir()):
            reports_path.rmdir()
        raise ReadinessSnapshotError(
            "Readiness snapshot publication failed; the prior baseline was preserved."
        ) from error


def _load_thresholds(root: Path) -> dict[str, Any]:
    defaults = {
        "price_ready": {"min_rows": 5, "require_positive_close": True},
        "momentum_ready": {"min_rows": 20},
        "risk_ready": {"min_rows": 60},
        "market_direction_ready": {"min_rows": 20},
        "peer_ready": {"min_peers": 2},
    }
    path = root / "config" / "readiness.yml"
    if not path.exists() or yaml is None:
        return defaults
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for key, values in defaults.items():
        if key not in loaded or not isinstance(loaded[key], dict):
            loaded[key] = values
        else:
            for value_key, value in values.items():
                loaded[key].setdefault(value_key, value)
    return loaded


def _ticker_set(frame: pd.DataFrame) -> set[str]:
    if frame.empty or "ticker" not in frame.columns:
        return set()
    return set(frame["ticker"].dropna().astype(str).str.upper().str.strip())


def _latest_date_text(values: pd.Series) -> str:
    parsed = pd.to_datetime(values, errors="coerce", format="mixed").dropna()
    if parsed.empty:
        return ""
    return parsed.max().date().isoformat()


def _has_number(row: pd.Series, *columns: str) -> bool:
    for column in columns:
        if column not in row:
            continue
        value = pd.to_numeric(pd.Series([row[column]]), errors="coerce").iloc[0]
        if pd.notna(value):
            return True
    return False


FUNDAMENTALS_SIGNAL_FIELDS = (
    "revenue",
    "revenue_growth",
    "eps",
    "free_cash_flow",
    "fcf",
    "fcf_margin",
    "profit_margin",
    "operating_margin",
    "gross_margin",
    "ebitda",
    "cash",
    "debt",
    "net_debt",
    "shares_outstanding",
    "pe_ratio",
    "trailing_pe",
    "forward_pe",
    "price_to_book",
    "market_cap",
    "enterprise_value",
    "debt_to_equity",
)


def _has_meaningful_fundamentals(row: pd.Series) -> bool:
    if row.empty:
        return False
    if _text_value(row.get("source", "")):
        return True
    return _has_number(row, *FUNDAMENTALS_SIGNAL_FIELDS)


def _has_dcf_fundamentals(row: pd.Series) -> bool:
    return (
        _has_number(row, "revenue")
        and _has_number(row, "free_cash_flow", "fcf")
        and _has_number(row, "fcf_margin")
        and _has_number(row, "shares_outstanding")
    )


def _price_metric_map(prices: pd.DataFrame, *, min_rows: int) -> dict[str, bool]:
    if prices.empty or "ticker" not in prices.columns or "close" not in prices.columns:
        return {}
    frame = prices.copy()
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    counts = frame.loc[frame["close"].gt(0)].groupby("ticker")["close"].count()
    return {str(ticker).upper(): int(count) >= min_rows for ticker, count in counts.items()}


def _text_value(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "nat"} else text


def _peer_mapping_next_action(ticker: str) -> str:
    return (
        f"Add at least 2 source-backed peer mappings for {ticker} in data/imports/peers.csv; "
        f"then run make imports-validate IMPORT_TICKERS={ticker}, "
        f"make imports-preview IMPORT_TICKERS={ticker}, and "
        f"make imports-apply IMPORT_TICKERS={ticker} after scope review."
    )


def _peer_readiness_next_action(ticker: str, peer: pd.Series) -> str:
    action = _text_value(peer.get("next_peer_action", ""))
    blocker_type = _text_value(peer.get("peer_blocker_type", ""))
    if not action:
        return _peer_mapping_next_action(ticker)
    if blocker_type == "missing_peer_mapping":
        return (
            f"{action} Then run make imports-validate IMPORT_TICKERS={ticker}, "
            f"make imports-preview IMPORT_TICKERS={ticker}, and "
            f"make imports-apply IMPORT_TICKERS={ticker} after scope review."
        )
    if blocker_type in {"peer_price_missing", "peer_momentum_missing"}:
        return (
            f"{action} Run make focus-peers TICKER={ticker} to review mapped peers, "
            "then use capped price refresh or verified OHLCV import file rows."
        )
    if blocker_type in {"peer_fundamentals_missing", "peer_valuation_blocked"}:
        return (
            f"{action} Run make focus-peers TICKER={ticker}, then use the SEC staging workflow "
            "or the manual fundamentals import file workflow for the mapped peers."
        )
    return action


def _select_row(frame: pd.DataFrame, ticker: str) -> pd.Series:
    if frame.empty or "ticker" not in frame.columns:
        return pd.Series(dtype=object)
    rows = frame.loc[frame["ticker"] == ticker]
    return rows.iloc[-1] if not rows.empty else pd.Series(dtype=object)


def _index_by_ticker(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "ticker" not in frame.columns:
        return pd.DataFrame()
    return frame.set_index("ticker", drop=False)


def _active_theme(active: pd.DataFrame, ticker: str) -> str:
    row = _select_row(active, ticker)
    return str(row.get("theme", "") or "")


def _metadata_row(master: pd.DataFrame, legacy: pd.DataFrame, ticker: str) -> pd.Series:
    row = _select_row(master, ticker)
    if not row.empty:
        return row
    return _select_row(legacy, ticker)


def _state(ready: bool, partial: bool = False, excluded: bool = False) -> str:
    if excluded:
        return "excluded"
    if ready:
        return "ready"
    if partial:
        return "partial"
    return "blocked"


def _asset_excludes_company_peer_context(asset_type: object) -> bool:
    return str(asset_type or "").strip().lower() in COMPANY_PEER_EXCLUDED_ASSET_TYPES


def build_price_coverage_report(root: Path, data_path: Path, master: pd.DataFrame, active: pd.DataFrame, thresholds: dict[str, Any]) -> pd.DataFrame:
    prices = _read_csv(data_path / "prices.csv")
    active_tickers = _ticker_set(active)
    master_tickers = _ticker_set(master)
    all_tickers = sorted(master_tickers | active_tickers)
    min_price_rows = int(thresholds["price_ready"].get("min_rows", 5))
    min_momentum_rows = int(thresholds["momentum_ready"].get("min_rows", 20))
    min_risk_rows = int(thresholds["risk_ready"].get("min_rows", 60))
    rows: list[dict[str, Any]] = []
    for ticker in all_tickers:
        ticker_prices = prices.loc[prices["ticker"] == ticker].copy() if not prices.empty and "ticker" in prices.columns else pd.DataFrame()
        if not ticker_prices.empty:
            ticker_prices["date"] = pd.to_datetime(ticker_prices["date"], errors="coerce", format="mixed")
            ticker_prices["close"] = pd.to_numeric(ticker_prices.get("close"), errors="coerce")
            ticker_prices = ticker_prices.loc[ticker_prices["date"].notna()]
        positive_close = bool((ticker_prices.get("close", pd.Series(dtype=float)).dropna() > 0).all()) if not ticker_prices.empty else False
        price_rows = int(len(ticker_prices))
        price_ready = price_rows >= min_price_rows and positive_close
        momentum_ready = price_rows >= min_momentum_rows and price_ready
        risk_ready = price_rows >= min_risk_rows and price_ready
        metadata = _metadata_row(master, pd.DataFrame(), ticker)
        missing_reason = "" if price_ready else f"needs at least {min_price_rows} valid price rows with positive close"
        rows.append(
            {
                "ticker": ticker,
                "name": metadata.get("name", ""),
                "asset_type": metadata.get("asset_type", infer_asset_type(ticker, metadata)),
                "exchange": metadata.get("exchange", ""),
                "price_rows": price_rows,
                "first_price_date": _latest_date_text(ticker_prices["date"].sort_values().head(1)) if price_rows else "",
                "last_price_date": _latest_date_text(ticker_prices["date"]) if price_rows else "",
                "has_recent_price": False,
                "price_ready": price_ready,
                "momentum_ready": momentum_ready,
                "risk_ready": risk_ready,
                "missing_price_reason": missing_reason,
                "next_action": "" if price_ready else f"Import price rows through the preview-first workflow or refresh the price provider for {ticker}.",
                "updated_at": _now(),
            }
        )
    return pd.DataFrame(rows, columns=PRICE_COVERAGE_COLUMNS)


def build_fundamentals_coverage_report(root: Path, data_path: Path, master: pd.DataFrame) -> pd.DataFrame:
    fundamentals = _read_csv(data_path / "fundamentals.csv")
    rows: list[dict[str, Any]] = []
    for ticker in sorted(_ticker_set(master)):
        row = _select_row(fundamentals, ticker)
        has_row = _has_meaningful_fundamentals(row)
        missing = []
        for field in ("revenue", "free_cash_flow", "fcf", "fcf_margin", "shares_outstanding"):
            if field in {"free_cash_flow", "fcf"}:
                continue
            if not _has_number(row, field):
                missing.append(field)
        if not _has_number(row, "free_cash_flow", "fcf"):
            missing.insert(0, "free_cash_flow")
        fundamentals_ready = has_row and bool(_text_value(row.get("source", ""))) and not missing
        rows.append(
            {
                "ticker": ticker,
                "has_fundamentals": has_row,
                "fundamentals_ready": fundamentals_ready,
                "missing_fundamentals_fields": ", ".join(dict.fromkeys(missing)),
                "source": row.get("source", "") if has_row else "",
                "updated_at": _now(),
            }
        )
    return pd.DataFrame(rows, columns=FUNDAMENTALS_COVERAGE_COLUMNS)


def build_peer_readiness_report(root: Path, data_path: Path, master: pd.DataFrame, thresholds: dict[str, Any]) -> pd.DataFrame:
    peers = _read_csv(data_path / "peers.csv")
    peer_candidates = _read_csv(data_path / "peer_candidates.csv")
    fundamentals = _read_csv(data_path / "fundamentals.csv")
    prices = _read_csv(data_path / "prices.csv")
    universe_tickers = _ticker_set(master)
    peer_price_ready_by_ticker = _price_metric_map(prices, min_rows=int(thresholds["price_ready"].get("min_rows", 5)))
    peer_momentum_ready_by_ticker = _price_metric_map(prices, min_rows=int(thresholds["momentum_ready"].get("min_rows", 20)))
    min_peers = int(thresholds["peer_ready"].get("min_peers", 2))
    rows = []
    for ticker in sorted(universe_tickers):
        metadata = _metadata_row(master, pd.DataFrame(), ticker)
        asset_type = str(metadata.get("asset_type", infer_asset_type(ticker, metadata)) or "").strip().lower()
        if _asset_excludes_company_peer_context(asset_type):
            reason = "operating-company peer mapping is excluded for ETF/index/fund monitor context"
            rows.append(
                {
                    "ticker": ticker,
                    "peer_group": "",
                    "peer_count": 0,
                    "sample_peers": "",
                    "mapping_status": "excluded",
                    "candidate_peer_group": "",
                    "candidate_peer_count": 0,
                    "candidate_sample_peers": "",
                    "candidate_mapping_status": "excluded",
                    "candidate_states": "",
                    "peer_blocker_type": "excluded_asset_type",
                    "peer_price_ready": False,
                    "peer_momentum_ready": False,
                    "peer_fundamentals_ready": False,
                    "peer_valuation_ready": False,
                    "peer_trend_comparison_ready": False,
                    "peer_valuation_comparison_ready": False,
                    "peer_dcf_comparison_ready": False,
                    "peer_price_ready_count": 0,
                    "peer_momentum_ready_count": 0,
                    "peer_fundamentals_ready_count": 0,
                    "peer_valuation_ready_count": 0,
                    "peer_valuation_anchor_eligible_count": 0,
                    "peer_valuation_anchor_blockers": "",
                    "ready_peer_count": 0,
                    "peer_missing_price_tickers": "",
                    "peer_missing_momentum_tickers": "",
                    "peer_missing_fundamentals_tickers": "",
                    "peer_missing_valuation_tickers": "",
                    "peer_ready": False,
                    "missing_peer_reason": reason,
                    "next_peer_action": (
                        f"No peer import is required for {ticker}; monitor context remains excluded from "
                        "operating-company peer valuation."
                    ),
                    "updated_at": _now(),
                }
            )
            continue
        ticker_peers = peers.loc[peers["ticker"] == ticker].copy() if not peers.empty and "ticker" in peers.columns else pd.DataFrame()
        if not ticker_peers.empty and "peer_ticker" in ticker_peers.columns:
            ticker_peers["peer_ticker"] = ticker_peers["peer_ticker"].astype(str).str.upper().str.strip()
            valid_peers = sorted(set(ticker_peers["peer_ticker"]) & universe_tickers - {ticker})
        else:
            valid_peers = []
        ticker_candidate_peers = (
            peer_candidates.loc[peer_candidates["ticker"] == ticker].copy()
            if not peer_candidates.empty and "ticker" in peer_candidates.columns
            else pd.DataFrame()
        )
        if not ticker_candidate_peers.empty and "peer_ticker" in ticker_candidate_peers.columns:
            ticker_candidate_peers["peer_ticker"] = ticker_candidate_peers["peer_ticker"].astype(str).str.upper().str.strip()
            candidate_states = (
                ticker_candidate_peers.get("candidate_state", pd.Series(dtype=object))
                .fillna("")
                .astype(str)
                .str.strip()
                .str.lower()
            )
            ticker_candidate_peers["candidate_state"] = candidate_states
            valid_candidate_peers = sorted(set(ticker_candidate_peers["peer_ticker"]) & universe_tickers - {ticker})
            valid_candidate_states = sorted(
                {
                    state
                    for state in candidate_states.tolist()
                    if state in ALLOWED_CANDIDATE_STATES
                }
            )
        else:
            valid_candidate_peers = []
            valid_candidate_states = []
        price_ready_peers = []
        momentum_ready_peers = []
        fundamentals_ready_peers = []
        valuation_ready_peers = []
        valuation_anchor_eligible_peers: list[str] = []
        valuation_anchor_blockers: list[str] = []
        peer_rows_by_ticker = {
            str(row.get("peer_ticker") or "").strip().upper(): row
            for row in ticker_peers.to_dict("records")
        }
        for peer in valid_peers:
            fundamental_row = _select_row(fundamentals, peer)
            quality = assess_peer_evidence(peer_rows_by_ticker.get(peer, {}))
            if quality.valuation_anchor_state == "eligible":
                valuation_anchor_eligible_peers.append(peer)
            else:
                valuation_anchor_blockers.append(f"{peer}: {', '.join(quality.blockers)}")
            if peer_price_ready_by_ticker.get(peer, False):
                price_ready_peers.append(peer)
            if peer_momentum_ready_by_ticker.get(peer, False):
                momentum_ready_peers.append(peer)
            if _has_meaningful_fundamentals(fundamental_row):
                fundamentals_ready_peers.append(peer)
            if quality.valuation_anchor_state == "eligible" and _has_dcf_fundamentals(fundamental_row):
                valuation_ready_peers.append(peer)
        missing_price_peers = sorted(set(valid_peers) - set(price_ready_peers))
        missing_momentum_peers = sorted(set(valid_peers) - set(momentum_ready_peers))
        missing_fundamentals_peers = sorted(set(valid_peers) - set(fundamentals_ready_peers))
        missing_valuation_peers = sorted(set(valid_peers) - set(valuation_ready_peers))
        peer_price_ready = len(valid_peers) >= min_peers and len(price_ready_peers) >= min_peers
        peer_momentum_ready = len(valid_peers) >= min_peers and len(momentum_ready_peers) >= min_peers
        peer_fundamentals_ready = len(valid_peers) >= min_peers and len(fundamentals_ready_peers) >= min_peers
        peer_valuation_ready = (
            len(valid_peers) >= min_peers
            and len(valuation_anchor_eligible_peers) >= min_peers
            and len(valuation_ready_peers) >= min_peers
        )
        peer_ready = peer_momentum_ready
        mapping_status = "mapped" if len(valid_peers) >= min_peers else "missing_mapping" if not valid_peers else "insufficient_mapping"
        blocker_type = ""
        if len(valid_peers) < min_peers:
            blocker_type = "missing_peer_mapping"
        elif not peer_price_ready:
            blocker_type = "peer_price_missing"
        elif not peer_momentum_ready:
            blocker_type = "peer_momentum_missing"
        elif not peer_fundamentals_ready:
            blocker_type = "peer_fundamentals_missing"
        elif len(valuation_anchor_eligible_peers) < min_peers:
            blocker_type = "peer_comparability_unreviewed"
        elif not peer_valuation_ready:
            blocker_type = "peer_valuation_blocked"
        group = ""
        if not ticker_peers.empty and "peer_group" in ticker_peers.columns:
            values = ticker_peers["peer_group"].dropna().astype(str).str.strip()
            group = values.iloc[-1] if not values.empty else ""
        candidate_group = ""
        if not ticker_candidate_peers.empty and "peer_group" in ticker_candidate_peers.columns:
            values = ticker_candidate_peers["peer_group"].dropna().astype(str).str.strip()
            candidate_group = values.iloc[-1] if not values.empty else ""
        if len(valid_candidate_peers) >= min_peers and valid_candidate_states:
            candidate_mapping_status = "candidate_available"
        elif len(valid_candidate_peers) and not valid_candidate_states:
            candidate_mapping_status = "candidate_unlabeled"
        elif len(valid_candidate_peers):
            candidate_mapping_status = "candidate_insufficient"
        else:
            candidate_mapping_status = "candidate_missing"
        if peer_ready:
            reason = "peer trend comparison ready; peer valuation still requires peer_valuation_ready" if not peer_valuation_ready else ""
        elif len(valid_peers) < min_peers:
            reason = f"needs at least {min_peers} source-backed peer mappings"
        elif not peer_momentum_ready:
            reason = f"needs at least {min_peers} peers with momentum-ready price history"
        else:
            reason = f"needs at least {min_peers} valid peers with local metrics"
        if blocker_type == "missing_peer_mapping":
            if len(valid_candidate_peers) >= min_peers and valid_candidate_states:
                reason = (
                    f"{reason}; {len(valid_candidate_peers)} candidate peer(s) are available in data/peer_candidates.csv "
                    f"with states {', '.join(valid_candidate_states)}"
                )
                next_peer_action = (
                    f"Review {len(valid_candidate_peers)} candidate peer(s) for {ticker} in data/peer_candidates.csv, "
                    f"then promote at least {min_peers} reviewed rows into data/imports/peers.csv."
                )
            elif len(valid_candidate_peers):
                reason = (
                    f"{reason}; {len(valid_candidate_peers)} candidate peer(s) exist in data/peer_candidates.csv but need explicit "
                    "candidate_state labels before they can guide promotion"
                )
                next_peer_action = (
                    f"Label candidate rows for {ticker} in data/peer_candidates.csv as candidate, fallback_context, or research_only, "
                    f"then promote reviewed peers into data/imports/peers.csv."
                )
            else:
                next_peer_action = f"Add at least {min_peers} source-backed peer mappings for {ticker} in data/imports/peers.csv."
        elif blocker_type == "peer_price_missing":
            next_peer_action = f"Add trusted price history for mapped peers: {', '.join(missing_price_peers[:5])}."
        elif blocker_type == "peer_momentum_missing":
            next_peer_action = f"Add enough local price history for mapped peers: {', '.join(missing_momentum_peers[:5])}."
        elif blocker_type == "peer_fundamentals_missing":
            next_peer_action = f"Import trusted fundamentals for mapped peers: {', '.join(missing_fundamentals_peers[:5])}."
        elif blocker_type == "peer_comparability_unreviewed":
            next_peer_action = (
                "Review peer role, relationship rationale, economic comparability basis, and explicit valuation-anchor "
                f"eligibility for mapped peers: {', '.join(sorted(set(valid_peers) - set(valuation_anchor_eligible_peers))[:5])}."
            )
        elif blocker_type == "peer_valuation_blocked":
            next_peer_action = f"Import DCF-ready fundamentals for mapped peers: {', '.join(missing_valuation_peers[:5])}."
        else:
            next_peer_action = f"Peer trend and valuation comparison are ready for {ticker}."
        rows.append(
            {
                "ticker": ticker,
                "peer_group": group,
                "peer_count": len(valid_peers),
                "sample_peers": ", ".join(valid_peers[:5]),
                "mapping_status": mapping_status,
                "candidate_peer_group": candidate_group,
                "candidate_peer_count": len(valid_candidate_peers),
                "candidate_sample_peers": ", ".join(valid_candidate_peers[:5]),
                "candidate_mapping_status": candidate_mapping_status,
                "candidate_states": ", ".join(valid_candidate_states),
                "peer_blocker_type": blocker_type,
                "peer_price_ready": peer_price_ready,
                "peer_momentum_ready": peer_momentum_ready,
                "peer_fundamentals_ready": peer_fundamentals_ready,
                "peer_valuation_ready": peer_valuation_ready,
                "peer_trend_comparison_ready": peer_momentum_ready,
                "peer_valuation_comparison_ready": peer_valuation_ready,
                "peer_dcf_comparison_ready": peer_valuation_ready,
                "peer_price_ready_count": len(price_ready_peers),
                "peer_momentum_ready_count": len(momentum_ready_peers),
                "peer_fundamentals_ready_count": len(fundamentals_ready_peers),
                "peer_valuation_ready_count": len(valuation_ready_peers),
                "peer_valuation_anchor_eligible_count": len(valuation_anchor_eligible_peers),
                "peer_valuation_anchor_blockers": "; ".join(valuation_anchor_blockers),
                "ready_peer_count": len(momentum_ready_peers),
                "peer_missing_price_tickers": ", ".join(missing_price_peers[:10]),
                "peer_missing_momentum_tickers": ", ".join(missing_momentum_peers[:10]),
                "peer_missing_fundamentals_tickers": ", ".join(missing_fundamentals_peers[:10]),
                "peer_missing_valuation_tickers": ", ".join(missing_valuation_peers[:10]),
                "peer_ready": peer_ready,
                "missing_peer_reason": reason,
                "next_peer_action": next_peer_action,
                "updated_at": _now(),
            }
        )
    return pd.DataFrame(rows, columns=PEER_READINESS_COLUMNS)


def build_data_source_status(root: Path, data_path: Path) -> pd.DataFrame:
    now = _now()

    def rows_available(path: Path) -> int:
        frame = _read_csv(path)
        return int(len(frame))

    specs = [
        ("local_prices", "local_csv", data_path / "prices.csv", "", "data/staged/prices/"),
        ("staged_prices", "manual_staged_csv", data_path / "staged" / "prices", "", "data/staged/prices/"),
        ("remote_price_provider", "remote_api", None, "STOOQ_API_KEY", "data/staged/prices/"),
        ("auto_price_ladder", "remote_api", None, "", "make price-refresh PROVIDER=auto"),
        ("local_fundamentals", "local_csv", data_path / "fundamentals.csv", "", "data/staged/fundamentals/"),
        ("sec_fundamentals", "remote_api", None, "SEC_USER_AGENT", "data/staged/fundamentals/"),
        ("staged_fundamentals", "manual_staged_csv", data_path / "staged" / "fundamentals", "", "data/staged/fundamentals/"),
        ("local_earnings", "local_csv", data_path / "earnings.csv", "", "data/staged/earnings/"),
        ("staged_earnings", "manual_staged_csv", data_path / "staged" / "earnings", "", "data/staged/earnings/"),
        ("local_analyst_estimates", "local_csv", data_path / "analyst_estimates.csv", "", "data/staged/analyst_estimates/"),
        ("staged_analyst_estimates", "manual_staged_csv", data_path / "staged" / "analyst_estimates", "", "data/staged/analyst_estimates/"),
        ("local_peers", "local_csv", data_path / "peers.csv", "", "data/imports/peers.csv"),
        ("local_peer_candidates", "local_csv", data_path / "peer_candidates.csv", "", "data/imports/peer_candidates.csv"),
        ("universe_master", "local_csv", data_path / "universe_master.csv", "", "data/staged/universe/"),
        ("universe_active", "local_csv", data_path / "universe_active.csv", "", "data/universe_active.csv"),
    ]
    rows = []
    for source_name, source_type, path, credential, manual_path in specs:
        credential_present = bool(os.environ.get(credential, "").strip()) if credential else True
        credential_required = bool(credential)
        failure_reason = ""
        available = 0
        if path is None:
            status = "available" if credential_present else "credential_missing"
            if not credential_present:
                failure_reason = f"missing {credential}"
        elif path.is_dir():
            available = len(list(path.glob("*.csv"))) if path.exists() else 0
            status = "available" if available else "empty"
        else:
            available = rows_available(path) if path.exists() else 0
            status = "available" if available else "missing_file"
        rows.append(
            {
                "source_name": source_name,
                "source_type": source_type,
                "status": status,
                "credential_required": credential,
                "credential_present": credential_present,
                "last_attempted_at": now if credential_required else "",
                "last_success_at": now if status == "available" else "",
                "rows_available": available,
                "failure_reason": failure_reason,
                "manual_fallback_available": bool(manual_path),
                "manual_import_path": manual_path,
                "updated_at": now,
            }
        )
    return pd.DataFrame(rows, columns=DATA_SOURCE_STATUS_COLUMNS)


def _copy_if_exists(source: Path, destination: Path) -> None:
    if source.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _feature_state_count(frame: pd.DataFrame, feature: str, state: str) -> int:
    column = f"{state}_features"
    if frame.empty or column not in frame.columns:
        return 0
    return int(
        frame[column]
        .fillna("")
        .astype(str)
        .str.contains(rf"(?:^|,\s*){feature}(?:$|,)", case=False, regex=True)
        .sum()
    )


def _top_feature_blocker(frame: pd.DataFrame, feature: str) -> str:
    if frame.empty:
        return ""
    blocked_mask = (
        frame.get("blocked_features", pd.Series("", index=frame.index))
        .fillna("")
        .astype(str)
        .str.contains(rf"(?:^|,\s*){feature}(?:$|,)", case=False, regex=True)
    )
    excluded_mask = (
        frame.get("excluded_features", pd.Series("", index=frame.index))
        .fillna("")
        .astype(str)
        .str.contains(rf"(?:^|,\s*){feature}(?:$|,)", case=False, regex=True)
    )
    missing = frame.loc[blocked_mask | excluded_mask, "missing_data"] if "missing_data" in frame.columns else pd.Series(dtype=object)
    tokens: list[str] = []
    for raw_value in missing.dropna().astype(str):
        parts = [part.strip() for part in raw_value.split(";") if part.strip()]
        if feature == "price":
            selected = [part for part in parts if "price" in part.lower() or "valid price rows" in part.lower()]
        elif feature in {"momentum", "market_direction", "liquidity", "correlation"}:
            selected = [part for part in parts if "price" in part.lower() or "valid price rows" in part.lower()]
        elif feature in {"fundamentals", "dcf"}:
            selected = [part for part in parts if part.lower().startswith("dcf:") or "fundamental" in part.lower()]
        elif feature == "peer":
            selected = [part for part in parts if part.lower().startswith("peers:") or "peer" in part.lower()]
        elif feature == "earnings":
            selected = [part for part in parts if part.lower().startswith("earnings:")]
        elif feature == "analyst_estimates":
            selected = [part for part in parts if part.lower().startswith("analyst_estimates:")]
        else:
            selected = parts
        tokens.extend(selected[:1])
    values = pd.Series(tokens, dtype=object).dropna().astype(str).str.strip()
    values = values.loc[values.ne("")]
    if values.empty:
        if excluded_mask.any():
            return f"{feature} excluded where not applicable"
        if blocked_mask.any():
            return f"{feature} input missing"
        return ""
    return str(values.value_counts().index[0])


def _sample_feature_tickers(frame: pd.DataFrame, feature: str, state: str, *, limit: int = 5) -> str:
    if frame.empty or "ticker" not in frame.columns:
        return ""
    column = f"{state}_features"
    if column not in frame.columns:
        return ""
    mask = (
        frame[column]
        .fillna("")
        .astype(str)
        .str.contains(rf"(?:^|,\s*){feature}(?:$|,)", case=False, regex=True)
    )
    tickers = frame.loc[mask, "ticker"].dropna().astype(str).str.upper().str.strip()
    return ", ".join(tickers.head(limit))


def build_feature_readiness_summary(ticker_readiness: pd.DataFrame) -> pd.DataFrame:
    features = [
        ("price", "Price Coverage", "make price-refresh-loop DRY_RUN=1"),
        ("momentum", "Momentum", "make price-refresh-loop DRY_RUN=1"),
        ("market_direction", "Market Direction", "make price-refresh-loop DRY_RUN=1"),
        ("liquidity", "Risk / Liquidity", "make research-health TOP_N=10"),
        ("correlation", "Risk / Correlation", "make research-health TOP_N=10"),
        ("fundamentals", "Fundamentals", "make fundamentals-source-ladder-queue TOP_N=25"),
        ("dcf", "Value / Re-rating", "make dcf-readiness"),
        ("peer", "Peer Readiness", "make peer-mapping-queue TOP_N=25"),
        ("earnings", "Optional Context", "make import-earnings"),
        ("analyst_estimates", "Optional Context", "make import-analyst-estimates"),
        ("portfolio", "Portfolio Review", "make pipeline"),
    ]
    total = int(len(ticker_readiness))
    rows = []
    for feature, section, action in features:
        rows.append(
            {
                "feature": feature,
                "ready_count": _feature_state_count(ticker_readiness, feature, "ready"),
                "partial_count": _feature_state_count(ticker_readiness, feature, "partial"),
                "blocked_count": _feature_state_count(ticker_readiness, feature, "blocked"),
                "excluded_count": _feature_state_count(ticker_readiness, feature, "excluded"),
                "total_count": total,
                "top_blocker": _top_feature_blocker(ticker_readiness, feature),
                "sample_ready_tickers": _sample_feature_tickers(ticker_readiness, feature, "ready"),
                "sample_blocked_tickers": _sample_feature_tickers(ticker_readiness, feature, "blocked"),
                "next_action": action,
                "unlock_command": action,
                "dashboard_section": section,
                "updated_at": _now(),
            }
        )
    return pd.DataFrame(rows, columns=FEATURE_READINESS_COLUMNS)


def build_peer_unlock_worklist(peer_report: pd.DataFrame, ticker_readiness: pd.DataFrame) -> pd.DataFrame:
    if peer_report.empty:
        return pd.DataFrame(columns=PEER_UNLOCK_WORKLIST_COLUMNS)
    readiness = _index_by_ticker(ticker_readiness)
    rows: list[dict[str, Any]] = []
    for _, peer_row in peer_report.iterrows():
        ticker = str(peer_row.get("ticker", "")).upper().strip()
        if not ticker:
            continue
        peer_trend_ready = bool(peer_row.get("peer_trend_comparison_ready", False))
        peer_valuation_ready = bool(peer_row.get("peer_valuation_ready", peer_row.get("peer_valuation_comparison_ready", False)))
        if bool(peer_row.get("peer_ready", False)) and peer_valuation_ready:
            continue
        readiness_row = readiness.loc[ticker] if ticker in readiness.index else pd.Series(dtype=object)
        blocked_features = str(readiness_row.get("blocked_features", "") or "")
        if "peer" not in blocked_features.lower() and not (peer_trend_ready and not peer_valuation_ready):
            continue
        dcf_ready = bool(readiness_row.get("dcf_ready", False))
        price_ready = bool(readiness_row.get("price_ready", False))
        active_universe = bool(readiness_row.get("in_active_universe", False))
        priority = 1 if dcf_ready else 2 if price_ready else 3
        blocker_type = _text_value(peer_row.get("peer_blocker_type")) or "peer_blocked"
        peer_trend_status = "peer_trend_possible" if peer_trend_ready else "peer_trend_blocked"
        peer_valuation_status = "peer_valuation_ready" if peer_valuation_ready else "peer_valuation_blocked"
        workflow_scope = "active_universe" if active_universe else "master_universe"
        if blocker_type == "missing_peer_mapping":
            unlock_stage = "add_source_backed_peer_mappings"
            workflow_group = "dcf_ready_peer_mapping" if dcf_ready else "price_ready_peer_mapping" if price_ready else "peer_mapping_after_price"
            candidate_count = int(peer_row.get("candidate_peer_count") or 0)
            candidate_states = _text_value(peer_row.get("candidate_states"))
            if candidate_count:
                next_action_summary = (
                    f"Review {candidate_count} candidate peer row(s) in data/peer_candidates.csv"
                    + (f" ({candidate_states})" if candidate_states else "")
                    + "; then promote only reviewed source-backed peers into data/imports/peers.csv."
                )
            else:
                next_action_summary = "Add at least two trusted, source-backed peer rows; fallback sector/industry context is not trusted peer data."
            next_input_file = "data/imports/peers.csv"
            validation_sequence = (
                "make templates -> fill source-backed peers -> "
                "make imports-validate IMPORT_TICKERS=<ticker> -> "
                "make imports-preview IMPORT_TICKERS=<ticker> -> "
                "make imports-apply IMPORT_TICKERS=<ticker>"
            )
        elif blocker_type in {"peer_price_missing", "peer_momentum_missing"}:
            unlock_stage = "add_peer_price_history"
            workflow_group = "peer_trend_unlock"
            next_action_summary = "Add verified peer OHLCV history before treating peer trend comparison as ready."
            next_input_file = "data/imports/prices.csv or data/staged/prices/"
            validation_sequence = "make focus-price TICKER=<peer> -> make price-refresh TICKERS=<peer> or prepare trusted OHLCV import file rows -> make imports-validate"
        elif blocker_type in {"peer_fundamentals_missing", "peer_valuation_blocked"}:
            unlock_stage = "add_peer_fundamentals"
            workflow_group = "peer_valuation_unlock"
            next_action_summary = "Add trusted peer fundamentals before showing peer valuation conclusions."
            next_input_file = "data/imports/fundamentals.csv or data/staged/fundamentals/"
            validation_sequence = "make focus-fundamentals TICKER=<peer> -> make sec-stage TICKERS=<peer> or prepare trusted fundamentals import file rows -> make imports-validate"
        else:
            unlock_stage = "review_peer_context"
            workflow_group = "peer_context_review"
            next_action_summary = "Review peer readiness details and keep valuation blocked until required peer inputs are present."
            next_input_file = "data/peers.csv"
            validation_sequence = f"make readiness -> make stock-report-md TICKER={ticker}"
        rows.append(
            {
                "priority": priority,
                "ticker": ticker,
                "peer_blocker_type": blocker_type,
                "unlock_stage": unlock_stage,
                "workflow_group": workflow_group,
                "workflow_scope": workflow_scope,
                "next_action_summary": next_action_summary,
                "peer_trend_status": peer_trend_status,
                "peer_valuation_status": peer_valuation_status,
                "peer_count": int(peer_row.get("peer_count") or 0),
                "ready_peer_count": int(peer_row.get("ready_peer_count") or 0),
                "peer_price_ready_count": int(peer_row.get("peer_price_ready_count") or 0),
                "peer_momentum_ready_count": int(peer_row.get("peer_momentum_ready_count") or 0),
                "peer_fundamentals_ready_count": int(peer_row.get("peer_fundamentals_ready_count") or 0),
                "peer_valuation_ready_count": int(peer_row.get("peer_valuation_ready_count") or 0),
                "sample_peers": peer_row.get("sample_peers", ""),
                "missing_peer_reason": peer_row.get("missing_peer_reason", ""),
                "next_peer_action": peer_row.get("next_peer_action", ""),
                "next_input_file": next_input_file,
                "validation_sequence": validation_sequence,
                "focus_command": f"make focus-peers TICKER={ticker}",
                "example_command": "make peer-mapping-queue TOP_N=25",
                "copy_only_note": "Copy commands only; review import file rows before applying local CSV changes.",
                "updated_at": _now(),
            }
        )
    frame = pd.DataFrame(rows, columns=PEER_UNLOCK_WORKLIST_COLUMNS)
    if frame.empty:
        return frame
    frame["workflow_scope_rank"] = frame["workflow_scope"].map({"active_universe": 0, "master_universe": 1}).fillna(2).astype(int)
    frame = frame.sort_values(["priority", "workflow_scope_rank", "workflow_group", "ticker"], kind="stable").reset_index(drop=True)
    return frame.drop(columns=["workflow_scope_rank"])


def build_ticker_readiness_report(
    base_dir: Path | str | None = None,
    *,
    data_dir: Path | str | None = None,
    output_dir: Path | str | None = None,
    write_outputs: bool = False,
) -> dict[str, pd.DataFrame]:
    root = resolve_project_root(base_dir)
    data_path = resolve_data_dir(data_dir, root)
    outputs_path = resolve_outputs_dir(output_dir, root)
    reports_path = data_path / "reports"
    master, active = ensure_universe_files(root, data_dir=data_path, write_outputs=False)
    thresholds = _load_thresholds(root)
    legacy = _read_csv(data_path / "universe.csv")
    holdings = _read_csv(data_path / "holdings.csv")
    prices = _read_csv(data_path / "prices.csv")
    fundamentals = _read_csv(data_path / "fundamentals.csv")
    earnings = _read_csv(data_path / "earnings.csv")
    estimates = _read_csv(data_path / "analyst_estimates.csv")

    universe_report = build_universe_coverage_report(root, data_dir=data_path, write_output=False)
    price_report = build_price_coverage_report(root, data_path, master, active, thresholds)
    fundamentals_report = build_fundamentals_coverage_report(root, data_path, master)
    peer_report = build_peer_readiness_report(root, data_path, master, thresholds)

    from src.dcf_readiness import build_dcf_readiness_frame
    from src.optional_context_readiness import build_analyst_estimates_readiness_frame, build_earnings_readiness_frame

    dcf_report = build_dcf_readiness_frame(universe=master, fundamentals=fundamentals, prices=prices)
    earnings_report = build_earnings_readiness_frame(master, earnings)
    estimates_report = build_analyst_estimates_readiness_frame(master, estimates)
    source_status = build_data_source_status(root, data_path)

    active_tickers = _ticker_set(active)
    portfolio_tickers = _ticker_set(holdings)
    price_lookup = _index_by_ticker(price_report)
    fundamentals_lookup = _index_by_ticker(fundamentals_report)
    raw_fundamentals_lookup = _index_by_ticker(fundamentals)
    dcf_lookup = _index_by_ticker(dcf_report)
    peer_lookup = _index_by_ticker(peer_report)
    earnings_lookup = _index_by_ticker(earnings_report)
    estimates_lookup = _index_by_ticker(estimates_report)

    rows: list[dict[str, Any]] = []
    for ticker in sorted(_ticker_set(master) | active_tickers | portfolio_tickers):
        metadata = _metadata_row(master, legacy, ticker)
        asset_type = str(metadata.get("asset_type", infer_asset_type(ticker, metadata)) or "unknown").lower()
        excludes_company_peer = _asset_excludes_company_peer_context(asset_type)
        raw_fundamentals = (
            raw_fundamentals_lookup.loc[ticker] if ticker in raw_fundamentals_lookup.index else pd.Series(dtype=object)
        )
        excludes_company_dcf = company_dcf_excluded(asset_type, metadata, raw_fundamentals)
        price = price_lookup.loc[ticker] if ticker in price_lookup.index else pd.Series(dtype=object)
        fund = fundamentals_lookup.loc[ticker] if ticker in fundamentals_lookup.index else pd.Series(dtype=object)
        dcf = dcf_lookup.loc[ticker] if ticker in dcf_lookup.index else pd.Series(dtype=object)
        peer = peer_lookup.loc[ticker] if ticker in peer_lookup.index else pd.Series(dtype=object)
        earn = earnings_lookup.loc[ticker] if ticker in earnings_lookup.index else pd.Series(dtype=object)
        est = estimates_lookup.loc[ticker] if ticker in estimates_lookup.index else pd.Series(dtype=object)

        feature_states = {
            "price": _state(bool(price.get("price_ready", False)), partial=int(price.get("price_rows", 0) or 0) > 0),
            "momentum": _state(bool(price.get("momentum_ready", False)), partial=bool(price.get("price_ready", False))),
            "market_direction": _state(bool(price.get("momentum_ready", False)), partial=bool(price.get("price_ready", False))),
            "liquidity": _state(bool(price.get("risk_ready", False)), partial=bool(price.get("price_ready", False))),
            "correlation": _state(bool(price.get("risk_ready", False)), partial=bool(price.get("price_ready", False))),
            "fundamentals": _state(bool(fund.get("fundamentals_ready", False)), partial=bool(fund.get("has_fundamentals", False))),
            "dcf": _state(bool(dcf.get("is_dcf_ready", False)), partial=False, excluded=excludes_company_dcf),
            "peer": _state(
                bool(peer.get("peer_ready", False)),
                partial=int(peer.get("peer_count", 0) or 0) > 0,
                excluded=excludes_company_peer,
            ),
            "earnings": _state(bool(earn.get("has_trusted_earnings", False))),
            "analyst_estimates": _state(bool(est.get("has_trusted_analyst_estimates", False))),
            "portfolio": _state(ticker in portfolio_tickers and bool(price.get("price_ready", False)), partial=ticker in portfolio_tickers, excluded=ticker not in portfolio_tickers),
        }
        ready = [name for name, state in feature_states.items() if state == "ready"]
        partial = [name for name, state in feature_states.items() if state == "partial"]
        blocked = [name for name, state in feature_states.items() if state == "blocked"]
        excluded = [name for name, state in feature_states.items() if state == "excluded"]
        missing_data = []
        if not bool(price.get("price_ready", False)):
            missing_data.append(str(price.get("missing_price_reason", "price")))
        dcf_missing = str(dcf.get("missing_dcf_fields", "") or "").strip()
        if dcf_missing and not excludes_company_dcf:
            missing_data.append(f"dcf: {dcf_missing}")
        peer_missing = str(peer.get("missing_peer_reason", "") or "").strip()
        if peer_missing and not excludes_company_peer:
            missing_data.append(f"peers: {peer_missing}")
        if "earnings" in blocked:
            missing_data.append("earnings: trusted local CSV input")
        if "analyst_estimates" in blocked:
            missing_data.append("analyst_estimates: trusted local CSV input")
        if "price" in blocked:
            next_action = str(
                price.get("next_action")
                or f"Import price rows through the preview-first workflow or refresh the price provider for {ticker}."
            )
        elif "dcf" in blocked:
            missing_fundamentals = str(fund.get("missing_fundamentals_fields", "") or "").strip()
            if bool(fund.get("has_fundamentals", False)) and missing_fundamentals:
                next_action = (
                    f"Complete trusted fundamentals for {ticker}; missing fields: {missing_fundamentals}. "
                    f"Run make focus-fundamentals TICKER={ticker}, then use the SEC staging workflow or the manual fundamentals import file workflow."
                )
            else:
                next_action = (
                    f"Import trusted fundamentals for {ticker}. If SEC_USER_AGENT is configured, use the SEC staging workflow; "
                    "otherwise use the manual fundamentals import file workflow."
                )
        elif "peer" in blocked or "peer" in partial:
            next_action = _peer_readiness_next_action(ticker, peer)
        elif blocked:
            next_action = f"Optional context missing for {ticker}; leave unavailable unless trusted local CSVs exist."
        else:
            next_action = f"Review ready analysis outputs for {ticker}."
        if "price" in blocked:
            overall = "blocked"
        elif ready:
            overall = "ready" if not blocked else "partial"
        elif excluded and not ready and not partial:
            overall = "excluded"
        elif partial:
            overall = "partial"
        else:
            overall = "blocked"
        rows.append(
            {
                "ticker": ticker,
                "name": metadata.get("name", ""),
                "exchange": metadata.get("exchange", ""),
                "asset_type": asset_type if asset_type in ASSET_TYPES else "unknown",
                "sector": metadata.get("sector", metadata.get("sectoretf", "")),
                "industry": metadata.get("industry", ""),
                "theme": _active_theme(active, ticker) or metadata.get("theme", ""),
                "in_master_universe": ticker in _ticker_set(master),
                "in_active_universe": ticker in active_tickers,
                "price_ready": feature_states["price"] == "ready",
                "momentum_ready": feature_states["momentum"] == "ready",
                "market_direction_ready": feature_states["market_direction"] == "ready",
                "liquidity_ready": feature_states["liquidity"] == "ready",
                "correlation_ready": feature_states["correlation"] == "ready",
                "fundamentals_ready": feature_states["fundamentals"] == "ready",
                "dcf_ready": feature_states["dcf"] == "ready",
                "peer_ready": feature_states["peer"] == "ready",
                "earnings_ready": feature_states["earnings"] == "ready",
                "analyst_estimates_ready": feature_states["analyst_estimates"] == "ready",
                "portfolio_ready": feature_states["portfolio"] == "ready",
                "overall_readiness_state": overall,
                "ready_features": ", ".join(ready),
                "partial_features": ", ".join(partial),
                "blocked_features": ", ".join(blocked),
                "excluded_features": ", ".join(excluded),
                "missing_data": "; ".join(dict.fromkeys(item for item in missing_data if item)),
                "next_action": next_action,
                "updated_at": _now(),
            }
        )
    ticker_readiness = pd.DataFrame(rows, columns=TICKER_READINESS_COLUMNS)
    feature_summary = build_feature_readiness_summary(ticker_readiness)
    peer_unlock_worklist = build_peer_unlock_worklist(peer_report, ticker_readiness)

    reports = dict(
        zip(
            READINESS_REPORT_NAMES,
            (
                universe_report,
                price_report,
                fundamentals_report,
                dcf_report.rename(columns={"is_dcf_ready": "dcf_ready"}),
                peer_report,
                earnings_report,
                estimates_report,
                ticker_readiness,
                feature_summary,
                peer_unlock_worklist,
                source_status,
            ),
            strict=True,
        )
    )
    if write_outputs:
        for name, frame in reports.items():
            _write(frame, reports_path / f"{name}.csv")
        # Compatibility copies for existing dashboard/helpers.
        _write(price_report, data_path / "price_coverage_report.csv")
        _write(dcf_report, data_path / "dcf_readiness.csv")
        _write(earnings_report, data_path / "earnings_readiness.csv")
        _write(estimates_report, data_path / "analyst_estimates_readiness.csv")
        outputs_path.mkdir(parents=True, exist_ok=True)
        _write(feature_summary, outputs_path / "feature_readiness_summary.csv")
        _write(peer_unlock_worklist, outputs_path / "peer_unlock_worklist.csv")
    return reports


def _deprecated_readiness_boundary() -> None:
    print(
        "Deprecated no-write guard: use make readiness-preview TOP_N=20 for inspection.",
        file=sys.stderr,
    )
    print(
        "For an intentional ignored snapshot: CONFIRM_MATERIALIZE=1 "
        "make readiness-materialize PROFILE=<default|demo|local>",
        file=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Guard legacy readiness writes or capture one explicit baseline.")
    parser.add_argument("--project-root", help="Project root. Defaults to this repository.")
    parser.add_argument("--data-dir", help="Optional data directory. Relative paths resolve from project root.")
    parser.add_argument("--output-dir", help="Optional output directory. Relative paths resolve from project root.")
    parser.add_argument("--profile", choices=("default", "demo", "local"))
    parser.add_argument(
        "--save-previous",
        action="store_true",
        help="Deprecated compatibility flag; always fails closed without reading or writing readiness artifacts.",
    )
    parser.add_argument(
        "--snapshot-only",
        action="store_true",
        help=(
            "Compose one profile-bound prior snapshot from readiness in memory; "
            "never read the tracked current readiness report."
        ),
    )
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:
        return int(error.code)
    if not args.snapshot_only:
        _deprecated_readiness_boundary()
        return 2
    if args.save_previous:
        _deprecated_readiness_boundary()
        return 2
    if args.profile is None:
        print("--profile is required with --snapshot-only: default, demo, or local.", file=sys.stderr)
        return 2
    if args.data_dir or args.output_dir:
        print("--snapshot-only accepts only the fixed selected --profile paths.", file=sys.stderr)
        return 2

    lexical_root = Path(
        os.path.abspath(
            os.fspath((Path(args.project_root) if args.project_root else PROJECT_ROOT).expanduser())
        )
    )
    try:
        selected = validate_readiness_source_boundary(lexical_root, args.profile)
        reports_path = selected.data_dir / "reports"
        _validate_snapshot_directory(reports_path, allow_missing=True)
        _validate_optional_snapshot_file(reports_path / READINESS_SNAPSHOT_FILENAME)
        if _lstat(reports_path / READINESS_SNAPSHOT_TEMP_FILENAME) is not None:
            _validate_optional_snapshot_file(reports_path / READINESS_SNAPSHOT_TEMP_FILENAME)
            raise ReadinessSnapshotError(
                f"Snapshot temporary path already exists: {reports_path / READINESS_SNAPSHOT_TEMP_FILENAME}"
            )
        input_identity = readiness_input_identity(lexical_root, selected.name)
        reports = build_ticker_readiness_report(
            lexical_root.resolve(strict=True),
            data_dir=selected.data_dir,
            output_dir=selected.outputs_dir,
            write_outputs=False,
        )
        readiness = reports.get("ticker_readiness_report")
        if not isinstance(readiness, pd.DataFrame):
            raise ReadinessSnapshotError("Readiness builder did not return a ticker readiness DataFrame.")
        if readiness.empty:
            raise ReadinessSnapshotError("Empty in-memory readiness cannot become a prior baseline.")
        if readiness_input_identity(lexical_root, selected.name) != input_identity:
            raise ReadinessSnapshotError("Named readiness inputs changed during baseline composition.")
        captured_at = pd.Timestamp.now(tz="UTC").isoformat()
        snapshot_frame = readiness.copy(deep=True)
        snapshot_frame["snapshot_profile"] = selected.name
        snapshot_frame["snapshot_input_identity"] = input_identity
        snapshot_frame["snapshot_captured_at"] = captured_at
        snapshot_frame["snapshot_schema_version"] = READINESS_SNAPSHOT_SCHEMA_VERSION
        snapshot_frame["snapshot_method_version"] = READINESS_METHOD_VERSION
        snapshot_path = _publish_profile_snapshot(reports_path, snapshot_frame)
    except (ReadinessSourceBoundaryError, ReadinessSnapshotError, OSError, ValueError, KeyError) as error:
        print(f"Readiness snapshot refused: {error}", file=sys.stderr)
        return 2

    payload = {
        "status": "written",
        "profile": selected.name,
        "snapshot_path": str(snapshot_path),
        "rows": int(len(snapshot_frame)),
        "input_identity": input_identity,
        "method_version": READINESS_METHOD_VERSION,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
