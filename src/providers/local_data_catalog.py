from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.providers.market_data import make_source_metadata


DATASET_CANDIDATES: dict[str, tuple[str, ...]] = {
    "prices": ("data/prices.csv",),
    "fundamentals": ("data/fundamentals.csv",),
    "earnings": ("data/earnings.csv", "data/earnings_calendar.csv", "data/earnings_history.csv"),
    "analyst_estimates": ("data/analyst_estimates.csv", "data/estimates.csv"),
    "holdings": ("data/holdings.csv",),
    "universe": ("data/universe.csv",),
    "theme_map": ("data/theme_map.csv",),
    "purpose_classification": ("outputs/purpose_classification.csv",),
    "market_direction": ("outputs/market_direction.csv",),
    "momentum_leaders": ("outputs/momentum_leaders.csv",),
    "portfolio_review": ("outputs/portfolio_review.csv",),
    "undervalued_candidates": ("outputs/undervalued_candidates.csv",),
    "final_watchlist": ("outputs/final_watchlist.csv",),
}


def normalize_columns(columns: list[str]) -> list[str]:
    return [
        column.strip()
        .replace("%", "pct")
        .replace("/", "_")
        .replace(" ", "_")
        .replace("-", "_")
        .lower()
        for column in columns
    ]


def _detect_date_column(columns: list[str]) -> str | None:
    for column in (
        "date",
        "as_of_date",
        "market_time",
        "reported_date",
        "earnings_date",
        "last_earnings_date",
        "next_earnings_date",
        "timestamp",
    ):
        if column in columns:
            return column
    return None


def _detect_ticker_column(columns: list[str]) -> str | None:
    for column in ("ticker", "symbol"):
        if column in columns:
            return column
    return None


@dataclass
class LocalDatasetMetadata:
    name: str
    file_path: str
    row_count: int
    available_columns: list[str]
    date_column: str | None
    ticker_column: str | None
    latest_data_timestamp: str | None
    source: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LocalTickerDatasetCoverage:
    dataset_name: str
    file_path: str | None
    ticker_present: bool
    row_count_for_ticker: int
    latest_data_timestamp: str | None
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LocalDataCatalog:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
        self._path_cache: dict[str, Path | None] = {}
        self._frame_cache: dict[str, pd.DataFrame | None] = {}

    def dataset_names(self) -> list[str]:
        return list(DATASET_CANDIDATES.keys())

    def resolve_path(self, dataset_name: str) -> Path | None:
        if dataset_name not in self._path_cache:
            path = None
            for candidate in DATASET_CANDIDATES.get(dataset_name, ()):
                candidate_path = self.base_dir / candidate
                if candidate_path.exists():
                    path = candidate_path
                    break
            self._path_cache[dataset_name] = path
        return self._path_cache[dataset_name]

    def load_dataframe(self, dataset_name: str) -> pd.DataFrame | None:
        if dataset_name in self._frame_cache:
            return self._frame_cache[dataset_name]

        path = self.resolve_path(dataset_name)
        if path is None:
            self._frame_cache[dataset_name] = None
            return None

        frame = pd.read_csv(path)
        frame.columns = normalize_columns(list(frame.columns))

        date_column = _detect_date_column(list(frame.columns))
        if date_column is not None:
            frame[date_column] = pd.to_datetime(frame[date_column], errors="coerce", format="mixed")

        ticker_column = _detect_ticker_column(list(frame.columns))
        if ticker_column is not None:
            frame[ticker_column] = frame[ticker_column].astype("string").str.upper().str.strip()

        self._frame_cache[dataset_name] = frame
        return frame

    def dataset_metadata(self, dataset_name: str) -> LocalDatasetMetadata | None:
        path = self.resolve_path(dataset_name)
        if path is None:
            return None

        frame = self.load_dataframe(dataset_name)
        if frame is None:
            return None

        columns = list(frame.columns)
        date_column = _detect_date_column(columns)
        latest_timestamp = None
        if date_column is not None and date_column in frame.columns and frame[date_column].notna().any():
            latest_value = frame[date_column].dropna().max()
            latest_timestamp = latest_value.isoformat() if hasattr(latest_value, "isoformat") else str(latest_value)

        freshness = f"local CSV through {latest_timestamp}" if latest_timestamp else "local CSV file"
        notes = ["Generated screener output CSV."] if "outputs" in path.parts else ["Local CSV-backed research data."]

        return LocalDatasetMetadata(
            name=dataset_name,
            file_path=str(path),
            row_count=len(frame),
            available_columns=columns,
            date_column=date_column,
            ticker_column=_detect_ticker_column(columns),
            latest_data_timestamp=latest_timestamp,
            source=make_source_metadata(
                provider=f"local:{path.name}",
                freshness=freshness,
                official=False,
                notes=notes,
                retrieved_at=pd.Timestamp(path.stat().st_mtime, unit="s", tz="UTC").isoformat(),
            ).to_dict(),
        )

    def discover(self) -> list[LocalDatasetMetadata]:
        datasets: list[LocalDatasetMetadata] = []
        for dataset_name in self.dataset_names():
            metadata = self.dataset_metadata(dataset_name)
            if metadata is not None:
                datasets.append(metadata)
        return datasets

    def list_tickers(self, dataset_names: list[str] | None = None) -> list[str]:
        tickers: set[str] = set()
        for dataset_name in dataset_names or self.dataset_names():
            frame = self.load_dataframe(dataset_name)
            if frame is None:
                continue
            ticker_column = _detect_ticker_column(list(frame.columns))
            if ticker_column is None:
                continue
            tickers.update(frame[ticker_column].dropna().astype(str).str.upper().str.strip())
        return sorted(ticker for ticker in tickers if ticker)

    def describe_ticker(self, ticker: str, dataset_names: list[str] | None = None) -> list[LocalTickerDatasetCoverage]:
        ticker = ticker.upper().strip()
        coverage_rows: list[LocalTickerDatasetCoverage] = []
        for dataset_name in dataset_names or self.dataset_names():
            metadata = self.dataset_metadata(dataset_name)
            if metadata is None:
                coverage_rows.append(
                    LocalTickerDatasetCoverage(
                        dataset_name=dataset_name,
                        file_path=None,
                        ticker_present=False,
                        row_count_for_ticker=0,
                        latest_data_timestamp=None,
                        notes=["Local CSV dataset is not present."],
                    )
                )
                continue

            frame = self.load_dataframe(dataset_name)
            assert frame is not None
            if metadata.ticker_column is None:
                coverage_rows.append(
                    LocalTickerDatasetCoverage(
                        dataset_name=dataset_name,
                        file_path=metadata.file_path,
                        ticker_present=False,
                        row_count_for_ticker=0,
                        latest_data_timestamp=metadata.latest_data_timestamp,
                        notes=["Dataset does not contain a ticker/symbol column."],
                    )
                )
                continue

            matches = frame.loc[frame[metadata.ticker_column] == ticker].copy()
            latest_timestamp = None
            if metadata.date_column is not None and metadata.date_column in matches.columns and matches[metadata.date_column].notna().any():
                latest_value = matches[metadata.date_column].dropna().max()
                latest_timestamp = latest_value.isoformat() if hasattr(latest_value, "isoformat") else str(latest_value)
            notes = ["Ticker rows found in local dataset."] if not matches.empty else ["Ticker is absent from this local dataset."]
            coverage_rows.append(
                LocalTickerDatasetCoverage(
                    dataset_name=dataset_name,
                    file_path=metadata.file_path,
                    ticker_present=not matches.empty,
                    row_count_for_ticker=len(matches),
                    latest_data_timestamp=latest_timestamp or metadata.latest_data_timestamp,
                    notes=notes,
                )
            )
        return coverage_rows
