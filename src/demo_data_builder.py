from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.paths import resolve_data_profile, resolve_project_root
from src.readiness_engine import build_ticker_readiness_report


DEMO_TICKERS = ("NVDA", "AMD", "AVGO", "MU", "SNDK", "WDC", "ACIC", "AACI", "SPY", "QQQ", "SMH")
PRICE_BACKED_BENCHMARK_TYPES = {"SPY": "index_proxy", "QQQ": "etf", "SMH": "etf"}
PROFILE_LIMITATIONS = (
    "This compact snapshot is product demonstration data, not a claim of current market freshness.",
    "Readiness states remain source-gated; absent inputs stay blocked or excluded.",
    "No holdings, credentials, tokens, account data, refresh caches, or provider responses are included.",
)
_TICKER_FILTERED_FILES = (
    "universe.csv",
    "universe_master.csv",
    "universe_active.csv",
    "prices.csv",
    "fundamentals.csv",
    "peers.csv",
    "earnings.csv",
    "analyst_estimates.csv",
)
_COPY_UNFILTERED_FILES = ("theme_map.csv",)


@dataclass(frozen=True)
class DemoDataBuildResult:
    profile: str
    data_dir: Path
    outputs_dir: Path
    manifest_path: Path
    tickers: tuple[str, ...]
    snapshot_date: str
    files_written: int


def _normalize_tickers(tickers: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    normalized = tuple(dict.fromkeys(str(ticker).upper().strip() for ticker in tickers if str(ticker).strip()))
    if not normalized:
        raise ValueError("Choose at least one demo ticker.")
    return normalized


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _ticker_mask(frame: pd.DataFrame, tickers: set[str]) -> pd.Series:
    mask = pd.Series(True, index=frame.index)
    ticker_columns = [column for column in ("ticker", "symbol", "peer_ticker") if column in frame.columns]
    if not ticker_columns:
        return mask
    for column in ticker_columns:
        values = frame[column].fillna("").astype(str).str.upper().str.strip()
        mask = mask & values.isin(tickers)
    return mask


def _copy_filtered_source(source: Path, destination: Path, tickers: set[str]) -> int:
    frame = _read_csv(source)
    if frame.empty:
        return 0
    filtered = frame.loc[_ticker_mask(frame, tickers)].copy()
    destination.parent.mkdir(parents=True, exist_ok=True)
    filtered.to_csv(destination, index=False)
    return len(filtered)


def _copy_unfiltered_source(source: Path, destination: Path) -> int:
    if not source.exists():
        return 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return len(_read_csv(destination))


def _write_empty_holdings(source: Path, destination: Path) -> int:
    if source.exists():
        columns = list(_read_csv(source).columns)
    else:
        columns = [
            "Ticker",
            "Shares",
            "CostBasis",
            "PositionPercent",
            "PrimaryPurpose",
            "SecondaryTags",
            "OriginalThesis",
            "MaxPositionPercent",
            "InvalidationOverride",
        ]
    destination.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns=columns).to_csv(destination, index=False)
    return 0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_names(frame: pd.DataFrame) -> list[str]:
    if "source" not in frame.columns:
        return []
    return sorted({value for value in frame["source"].dropna().astype(str).str.strip() if value})


def _date_bounds(frame: pd.DataFrame) -> tuple[str | None, str | None]:
    for column in ("date", "as_of_date", "source_updated_at", "updated_at"):
        if column not in frame.columns:
            continue
        parsed = pd.to_datetime(frame[column], errors="coerce", format="mixed").dropna()
        if not parsed.empty:
            return parsed.min().date().isoformat(), parsed.max().date().isoformat()
    return None, None


def _manifest_file_entry(path: Path, root: Path) -> dict[str, Any]:
    frame = _read_csv(path)
    minimum_date, maximum_date = _date_bounds(frame)
    return {
        "path": str(path.relative_to(root)),
        "row_count": int(len(frame)),
        "sha256": _sha256(path),
        "source_names": _source_names(frame),
        "minimum_date": minimum_date,
        "maximum_date": maximum_date,
    }


def _normalize_generated_timestamps(directory: Path, snapshot_date: str) -> None:
    timestamp = f"{snapshot_date}T00:00:00+00:00"
    for path in sorted(directory.rglob("*.csv")):
        frame = _read_csv(path)
        changed = False
        for column in ("updated_at", "created_at"):
            if column in frame.columns:
                frame[column] = timestamp
                changed = True
        if changed:
            frame.to_csv(path, index=False)


def _derived_snapshot_date(prices_path: Path) -> str:
    prices = _read_csv(prices_path)
    if "date" not in prices.columns:
        raise ValueError("Demo price data needs a date column to derive its snapshot date.")
    dates = pd.to_datetime(prices["date"], errors="coerce", format="mixed").dropna()
    if dates.empty:
        raise ValueError("Demo price data needs at least one valid date to derive its snapshot date.")
    return dates.max().date().isoformat()


def _scenario_roles(readiness_path: Path) -> dict[str, list[str]]:
    readiness = _read_csv(readiness_path)
    if readiness.empty:
        return {
            "dcf_ready_company": [],
            "peer_ready_company": [],
            "dcf_blocked_company": [],
            "fundamentals_blocked_company": [],
            "excluded_asset_context": [],
        }
    ticker = readiness.get("ticker", pd.Series("", index=readiness.index)).fillna("").astype(str).str.upper().str.strip()
    asset_type = readiness.get("asset_type", pd.Series("", index=readiness.index)).fillna("").astype(str).str.lower()
    company = asset_type.eq("company")

    def tickers_for(mask: pd.Series) -> list[str]:
        return sorted(ticker.loc[mask].tolist())

    return {
        "dcf_ready_company": tickers_for(company & readiness.get("dcf_ready", pd.Series(False, index=readiness.index)).fillna(False).astype(bool)),
        "peer_ready_company": tickers_for(company & readiness.get("peer_ready", pd.Series(False, index=readiness.index)).fillna(False).astype(bool)),
        "dcf_blocked_company": tickers_for(company & ~readiness.get("dcf_ready", pd.Series(False, index=readiness.index)).fillna(False).astype(bool)),
        "fundamentals_blocked_company": tickers_for(
            company & ~readiness.get("fundamentals_ready", pd.Series(False, index=readiness.index)).fillna(False).astype(bool)
        ),
        "excluded_asset_context": tickers_for(asset_type.ne("company")),
    }


def _price_backed_benchmark_tickers(source_prices: Path, missing_tickers: set[str]) -> tuple[str, ...]:
    prices = _read_csv(source_prices)
    if "ticker" not in prices.columns:
        return ()
    available_prices = set(prices["ticker"].dropna().astype(str).str.upper().str.strip())
    return tuple(
        ticker
        for ticker in sorted(missing_tickers)
        if ticker in PRICE_BACKED_BENCHMARK_TYPES and ticker in available_prices
    )


def _append_price_backed_benchmark_metadata(
    demo_data: Path,
    tickers: tuple[str, ...],
    snapshot_date: str,
) -> None:
    master_path = demo_data / "universe_master.csv"
    master = _read_csv(master_path)
    rows: list[dict[str, Any]] = []
    for ticker in tickers:
        row = {column: "" for column in master.columns}
        row.update(
            {
                "ticker": ticker,
                "asset_type": PRICE_BACKED_BENCHMARK_TYPES[ticker],
                "security_type": "benchmark_context",
                "country": "US",
                "currency": "USD",
                "is_active_listing": True,
                "source": "demo_profile_price_history",
                "source_updated_at": snapshot_date,
            }
        )
        rows.append(row)
    if rows:
        pd.concat([master, pd.DataFrame(rows)], ignore_index=True).to_csv(master_path, index=False)

    legacy_path = demo_data / "universe.csv"
    if not legacy_path.exists():
        return
    legacy = _read_csv(legacy_path)
    legacy_rows: list[dict[str, Any]] = []
    for ticker in tickers:
        row = {column: "" for column in legacy.columns}
        row.update(
            {
                "ticker": ticker,
                "theme": "Benchmark context",
                "sector_etf": "ETF / Index",
                "default_purpose": "ETF / Defensive / Hedge",
                "market_cap_bucket": "ETF",
                "company_name": "",
                "universe_source": "demo_profile_price_history",
                "source_detail": "Price-backed benchmark metadata only; not operating-company analysis input.",
                "is_etf": PRICE_BACKED_BENCHMARK_TYPES[ticker] == "etf",
                "as_of_date": snapshot_date,
            }
        )
        legacy_rows.append(row)
    if legacy_rows:
        pd.concat([legacy, pd.DataFrame(legacy_rows)], ignore_index=True).to_csv(legacy_path, index=False)


def build_demo_data_profile(
    base_dir: Path | str | None = None,
    *,
    tickers: tuple[str, ...] | list[str] = DEMO_TICKERS,
    snapshot_date: str | None = None,
    overwrite: bool = False,
) -> DemoDataBuildResult:
    """Build a compact, profile-local, source-attributed public demo snapshot."""

    root = resolve_project_root(base_dir)
    selected_tickers = _normalize_tickers(tickers)
    ticker_set = set(selected_tickers)
    source_data = root / "data"
    profile = resolve_data_profile("demo", root)
    if profile.data_dir.exists() and any(profile.data_dir.iterdir()) and not overwrite:
        raise FileExistsError(f"Demo data profile already exists at {profile.data_dir}; pass overwrite=True to replace it.")
    if profile.data_dir.exists():
        shutil.rmtree(profile.data_dir)
    if profile.outputs_dir.exists():
        shutil.rmtree(profile.outputs_dir)
    profile.data_dir.mkdir(parents=True)
    profile.outputs_dir.mkdir(parents=True)

    source_master = _read_csv(source_data / "universe_master.csv")
    available_tickers = set(source_master.get("ticker", pd.Series(dtype=str)).dropna().astype(str).str.upper().str.strip())
    missing_tickers = set(ticker_set - available_tickers)
    derived_metadata_tickers = _price_backed_benchmark_tickers(source_data / "prices.csv", missing_tickers)
    unsupported_missing = sorted(missing_tickers - set(derived_metadata_tickers))
    if unsupported_missing:
        raise ValueError(
            "Demo ticker(s) are absent from data/universe_master.csv and have no supported price-backed benchmark path: "
            + ", ".join(unsupported_missing)
        )

    for filename in _TICKER_FILTERED_FILES:
        source = source_data / filename
        if source.exists():
            _copy_filtered_source(source, profile.data_dir / filename, ticker_set)
    for filename in _COPY_UNFILTERED_FILES:
        source = source_data / filename
        if source.exists():
            _copy_unfiltered_source(source, profile.data_dir / filename)
    _write_empty_holdings(source_data / "holdings.csv", profile.data_dir / "holdings.csv")

    prices_path = profile.data_dir / "prices.csv"
    if not prices_path.exists() or _read_csv(prices_path).empty:
        raise ValueError("Demo profile cannot be built without selected price rows.")
    resolved_snapshot_date = snapshot_date or _derived_snapshot_date(prices_path)
    _append_price_backed_benchmark_metadata(profile.data_dir, derived_metadata_tickers, resolved_snapshot_date)

    build_ticker_readiness_report(root, data_dir=profile.data_dir, output_dir=profile.outputs_dir)
    _normalize_generated_timestamps(profile.data_dir, resolved_snapshot_date)
    _normalize_generated_timestamps(profile.outputs_dir, resolved_snapshot_date)

    tracked_paths = sorted(
        path for path in [*profile.data_dir.rglob("*.csv"), *profile.outputs_dir.rglob("*.csv")] if path.is_file()
    )
    manifest = {
        "profile": "demo",
        "snapshot_date": resolved_snapshot_date,
        "tickers": list(selected_tickers),
        "derived_metadata_tickers": list(derived_metadata_tickers),
        "scenario_roles": _scenario_roles(profile.data_dir / "reports" / "ticker_readiness_report.csv"),
        "known_limitations": list(PROFILE_LIMITATIONS),
        "files": {
            str(path.relative_to(profile.data_dir if path.is_relative_to(profile.data_dir) else profile.outputs_dir)): _manifest_file_entry(
                path, root
            )
            for path in tracked_paths
        },
    }
    manifest_path = profile.data_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return DemoDataBuildResult(
        profile="demo",
        data_dir=profile.data_dir,
        outputs_dir=profile.outputs_dir,
        manifest_path=manifest_path,
        tickers=selected_tickers,
        snapshot_date=resolved_snapshot_date,
        files_written=len(tracked_paths) + 1,
    )


def verify_demo_data_profile(base_dir: Path | str | None = None) -> dict[str, Any]:
    """Verify tracked demo files against their committed source manifest."""

    root = resolve_project_root(base_dir)
    profile = resolve_data_profile("demo", root)
    manifest_path = profile.data_dir / "manifest.json"
    if not manifest_path.exists():
        return {"status": "missing_manifest", "files_checked": 0, "errors": [str(manifest_path)]}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if manifest.get("profile") != "demo":
        errors.append("manifest profile is not demo")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        errors.append("manifest has no file entries")
        files = {}
    for entry in files.values():
        if not isinstance(entry, dict):
            errors.append("manifest file entry is invalid")
            continue
        relative_path = str(entry.get("path") or "")
        path = root / relative_path
        if not path.exists():
            errors.append(f"missing file: {relative_path}")
            continue
        if entry.get("sha256") != _sha256(path):
            errors.append(f"checksum mismatch: {relative_path}")
    return {
        "status": "valid" if not errors else "invalid",
        "files_checked": len(files),
        "errors": errors,
        "manifest_path": str(manifest_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the compact tracked Stock Research Command Center demo data profile.")
    parser.add_argument("--root", help="Project root. Defaults to this repository.")
    parser.add_argument("--tickers", default=",".join(DEMO_TICKERS), help="Comma-separated demo tickers.")
    parser.add_argument("--snapshot-date", help="Explicit ISO snapshot date; otherwise derive it from selected prices.")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing demo profile.")
    parser.add_argument("--check", action="store_true", help="Validate the existing demo manifest without rebuilding it.")
    args = parser.parse_args()
    if args.check:
        verification = verify_demo_data_profile(args.root)
        print(json.dumps(verification, indent=2, sort_keys=True))
        if verification["status"] != "valid":
            raise SystemExit(1)
        return
    result = build_demo_data_profile(
        args.root,
        tickers=tuple(args.tickers.split(",")),
        snapshot_date=args.snapshot_date,
        overwrite=args.overwrite,
    )
    print(f"Built profile: {result.profile}")
    print(f"Tickers: {', '.join(result.tickers)}")
    print(f"Snapshot date: {result.snapshot_date}")
    print(f"Manifest: {result.manifest_path}")
    print(f"Files written: {result.files_written}")


if __name__ == "__main__":
    main()
