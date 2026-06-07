from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.paths import format_path_context, resolve_project_root


STAGED_PRICE_COLUMNS = [
    "date",
    "ticker",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "adjusted_close",
    "source",
    "as_of_date",
    "notes",
]


@dataclass
class PriceNormalizationResult:
    input_files: list[str]
    output_path: str
    rows_read: int
    rows_written: int
    rows_skipped: int
    duplicate_rows: int
    invalid_rows: int
    affected_tickers: list[str]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize_header(value: str) -> str:
    normalized = (
        str(value)
        .strip()
        .replace("*", "")
        .replace("%", "pct")
        .replace("/", "_")
        .replace(" ", "_")
        .replace("-", "_")
        .lower()
    )
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized


def _read_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame.columns = [_normalize_header(column) for column in frame.columns]
    return frame


def _column_map_from_args(args: argparse.Namespace) -> dict[str, str]:
    mapping = {
        "date": args.date_col,
        "ticker": args.ticker_col,
        "open": args.open_col,
        "high": args.high_col,
        "low": args.low_col,
        "close": args.close_col,
        "volume": args.volume_col,
        "adjusted_close": args.adjusted_close_col,
    }
    return {target: _normalize_header(source) for target, source in mapping.items() if source}


def _resolve_source_column(frame: pd.DataFrame, target: str, explicit_mapping: dict[str, str]) -> str | None:
    if target in explicit_mapping:
        return explicit_mapping[target] if explicit_mapping[target] in frame.columns else None
    candidates = {
        "date": ("date",),
        "ticker": ("ticker", "symbol"),
        "open": ("open",),
        "high": ("high",),
        "low": ("low",),
        "close": ("close",),
        "volume": ("volume",),
        "adjusted_close": ("adjusted_close", "adj_close", "adj_close_adjusted", "adjusted"),
    }[target]
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate
    return None


def _input_paths(input_path: Path | None, input_dir: Path | None) -> list[Path]:
    paths: list[Path] = []
    if input_path is not None:
        paths.append(input_path)
    if input_dir is not None:
        paths.extend(sorted(path for path in input_dir.iterdir() if path.suffix.lower() == ".csv"))
    return paths


def _normalize_one_file(
    path: Path,
    *,
    ticker: str | None,
    source: str,
    as_of_date: str,
    explicit_mapping: dict[str, str],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = _read_csv(path)
    rows_read = len(frame)
    warnings: list[str] = []
    output = pd.DataFrame()
    required_targets = ("date", "open", "high", "low", "close", "volume")
    missing_required: list[str] = []
    for target in required_targets:
        source_column = _resolve_source_column(frame, target, explicit_mapping)
        if source_column is None:
            missing_required.append(target)
        else:
            output[target] = frame[source_column]

    ticker_column = _resolve_source_column(frame, "ticker", explicit_mapping)
    if ticker_column is not None:
        output["ticker"] = frame[ticker_column]
    elif ticker:
        output["ticker"] = ticker
    else:
        warnings.append(f"{path.name}: no ticker column found; pass --ticker for tickerless exports.")
        return pd.DataFrame(columns=STAGED_PRICE_COLUMNS), {
            "rows_read": rows_read,
            "rows_skipped": rows_read,
            "duplicate_rows": 0,
            "invalid_rows": rows_read,
            "warnings": warnings,
        }

    adjusted_column = _resolve_source_column(frame, "adjusted_close", explicit_mapping)
    output["adjusted_close"] = frame[adjusted_column] if adjusted_column is not None else output["close"]

    if missing_required:
        warnings.append(f"{path.name}: missing required columns: {', '.join(missing_required)}.")
        return pd.DataFrame(columns=STAGED_PRICE_COLUMNS), {
            "rows_read": rows_read,
            "rows_skipped": rows_read,
            "duplicate_rows": 0,
            "invalid_rows": rows_read,
            "warnings": warnings,
        }

    output["ticker"] = output["ticker"].astype("string").str.upper().str.strip()
    output["date"] = pd.to_datetime(output["date"], errors="coerce", format="mixed")
    for column in ("open", "high", "low", "close", "volume", "adjusted_close"):
        output[column] = pd.to_numeric(output[column], errors="coerce")

    valid_mask = pd.Series(True, index=output.index)
    valid_mask &= output["ticker"].notna() & output["ticker"].astype(str).str.strip().ne("")
    valid_mask &= output["date"].notna()
    for column in ("open", "high", "low", "close", "volume"):
        valid_mask &= output[column].notna()
    valid_mask &= output["high"].ge(output["low"])
    valid_mask &= output["close"].gt(0)
    valid_mask &= output["volume"].ge(0)
    invalid_rows = int((~valid_mask).sum())
    if invalid_rows:
        warnings.append(f"{path.name}: skipped {invalid_rows} invalid price row(s).")
    output = output.loc[valid_mask].copy()
    if output.empty:
        return pd.DataFrame(columns=STAGED_PRICE_COLUMNS), {
            "rows_read": rows_read,
            "rows_skipped": rows_read,
            "duplicate_rows": 0,
            "invalid_rows": invalid_rows,
            "warnings": warnings,
        }

    duplicate_rows = int(output.duplicated(subset=["date", "ticker"], keep="last").sum())
    if duplicate_rows:
        warnings.append(f"{path.name}: deduplicated {duplicate_rows} duplicate date+ticker row(s), keeping the last row.")
    output = output.drop_duplicates(subset=["date", "ticker"], keep="last")
    output["date"] = output["date"].dt.date.astype(str)
    output["source"] = source
    output["as_of_date"] = as_of_date
    output["notes"] = f"Normalized from {path.name}"
    output = output.reindex(columns=STAGED_PRICE_COLUMNS)
    rows_skipped = invalid_rows + duplicate_rows
    return output, {
        "rows_read": rows_read,
        "rows_skipped": rows_skipped,
        "duplicate_rows": duplicate_rows,
        "invalid_rows": invalid_rows,
        "warnings": warnings,
    }


def _load_existing_staged(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=STAGED_PRICE_COLUMNS)
    frame = pd.read_csv(path)
    frame.columns = [_normalize_header(column) for column in frame.columns]
    if "adj_close" in frame.columns and "adjusted_close" not in frame.columns:
        frame["adjusted_close"] = frame["adj_close"]
    for column in STAGED_PRICE_COLUMNS:
        if column not in frame.columns:
            frame[column] = pd.NA
    frame["ticker"] = frame["ticker"].astype("string").str.upper().str.strip()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce", format="mixed").dt.date.astype(str)
    return frame.reindex(columns=STAGED_PRICE_COLUMNS)


def normalize_price_imports(
    *,
    input_path: Path | None = None,
    input_dir: Path | None = None,
    output_path: Path,
    ticker: str | None = None,
    source: str = "generic_manual",
    as_of_date: str | None = None,
    column_mapping: dict[str, str] | None = None,
) -> PriceNormalizationResult:
    paths = _input_paths(input_path, input_dir)
    if not paths:
        raise ValueError("No input CSV files were provided.")
    as_of_date = as_of_date or datetime.now(timezone.utc).date().isoformat()
    column_mapping = column_mapping or {}
    normalized_frames: list[pd.DataFrame] = []
    rows_read = 0
    rows_skipped = 0
    duplicate_rows = 0
    invalid_rows = 0
    warnings: list[str] = []
    for path in paths:
        frame, summary = _normalize_one_file(
            path,
            ticker=ticker,
            source=source,
            as_of_date=as_of_date,
            explicit_mapping=column_mapping,
        )
        normalized_frames.append(frame)
        rows_read += int(summary["rows_read"])
        rows_skipped += int(summary["rows_skipped"])
        duplicate_rows += int(summary["duplicate_rows"])
        invalid_rows += int(summary["invalid_rows"])
        warnings.extend(summary["warnings"])

    staged_new = pd.concat(normalized_frames, ignore_index=True) if normalized_frames else pd.DataFrame(columns=STAGED_PRICE_COLUMNS)
    if not staged_new.empty:
        combined_duplicate_rows = int(staged_new.duplicated(subset=["date", "ticker"], keep="last").sum())
        if combined_duplicate_rows:
            warnings.append(f"Combined inputs: deduplicated {combined_duplicate_rows} duplicate date+ticker row(s), keeping the last row.")
            duplicate_rows += combined_duplicate_rows
            rows_skipped += combined_duplicate_rows
        staged_new = staged_new.drop_duplicates(subset=["date", "ticker"], keep="last")

    existing = _load_existing_staged(output_path)
    combined = pd.concat([existing, staged_new], ignore_index=True)
    if not combined.empty:
        combined = combined.drop_duplicates(subset=["date", "ticker"], keep="last")
        combined = combined.sort_values(["ticker", "date"]).reset_index(drop=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.reindex(columns=STAGED_PRICE_COLUMNS).to_csv(output_path, index=False)
    affected = sorted(staged_new["ticker"].dropna().astype(str).unique().tolist()) if not staged_new.empty else []
    return PriceNormalizationResult(
        input_files=[str(path) for path in paths],
        output_path=str(output_path),
        rows_read=rows_read,
        rows_written=len(staged_new),
        rows_skipped=rows_skipped,
        duplicate_rows=duplicate_rows,
        invalid_rows=invalid_rows,
        affected_tickers=affected,
        warnings=warnings,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize local user-provided OHLCV CSVs into data/imports/prices.csv.")
    parser.add_argument("--project-root", help="Project root. Defaults to this repository.")
    parser.add_argument("--input", help="Input CSV file, such as data/raw/prices/NVDA.csv.")
    parser.add_argument("--input-dir", help="Directory of input CSV files, such as data/raw/prices.")
    parser.add_argument("--output", default="data/imports/prices.csv", help="Staged output CSV path.")
    parser.add_argument("--ticker", help="Ticker to use when the input file has no ticker column.")
    parser.add_argument("--source", default="generic_manual", help="Source label to write into the import CSV.")
    parser.add_argument("--as-of-date", help="As-of date metadata. Defaults to today.")
    parser.add_argument("--date-col")
    parser.add_argument("--ticker-col")
    parser.add_argument("--open-col")
    parser.add_argument("--high-col")
    parser.add_argument("--low-col")
    parser.add_argument("--close-col")
    parser.add_argument("--volume-col")
    parser.add_argument("--adjusted-close-col")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args()

    project_root = resolve_project_root(args.project_root)
    input_path = Path(args.input) if args.input else None
    input_dir = Path(args.input_dir) if args.input_dir else None
    output_path = Path(args.output)
    if input_path is not None and not input_path.is_absolute():
        input_path = project_root / input_path
    if input_dir is not None and not input_dir.is_absolute():
        input_dir = project_root / input_dir
    if not output_path.is_absolute():
        output_path = project_root / output_path

    result = normalize_price_imports(
        input_path=input_path,
        input_dir=input_dir,
        output_path=output_path,
        ticker=args.ticker,
        source=args.source,
        as_of_date=args.as_of_date,
        column_mapping=_column_map_from_args(args),
    )
    payload = result.to_dict()
    if args.json:
        print(json.dumps(payload, indent=2))
        return
    print(format_path_context(project_root, project_root / "data", project_root / "outputs"))
    for key, value in payload.items():
        print(f"{key}: {value}")
    print("Next commands:")
    print("make price-validate")
    print("make price-preview")
    print("make price-apply")


if __name__ == "__main__":
    main()
