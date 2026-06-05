from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any, Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

import pandas as pd

from src.providers.local_schemas import validate_local_dataset


CANONICAL_UNIVERSE_COLUMNS = [
    "ticker",
    "theme",
    "sector_etf",
    "default_purpose",
    "market_cap_bucket",
    "notes",
    "company_name",
    "universe_source",
    "source_detail",
    "index_membership",
    "etf_membership",
    "exchange",
    "is_etf",
    "as_of_date",
    "in_local_sample",
    "in_sp500",
    "in_nasdaq",
    "in_smh",
    "in_holdings",
    "in_custom",
]
MEMBERSHIP_COLUMNS = ["in_local_sample", "in_sp500", "in_nasdaq", "in_smh", "in_holdings", "in_custom"]
TEXT_FALLBACKS = {
    "theme": "Unclassified",
    "market_cap_bucket": "Unknown",
}
SOURCE_URLS = {
    "sp500": "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv",
    "nasdaq": "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt",
    "smh": "https://www.vaneck.com/us/en/investments/semiconductor-etf-smh/",
}
SOURCE_PRESETS = {
    "core": ["local", "holdings"],
    "sp500_smh": ["sp500", "smh", "holdings"],
    "broad": ["sp500", "nasdaq", "smh", "holdings"],
}
SOURCE_PRIORITY = {
    "local": 0,
    "holdings": 1,
    "custom": 2,
    "smh": 3,
    "sp500": 4,
    "nasdaq": 5,
}
SourceLoader = Callable[[str], str]


@dataclass
class UniverseSourceResult:
    source_name: str
    status: str
    row_count: int
    warnings: list[str] = field(default_factory=list)
    source_url: str | None = None
    retrieved_at: str | None = None
    available_columns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize_columns(columns: list[str]) -> list[str]:
    return [
        column.strip()
        .replace("%", "pct")
        .replace("/", "_")
        .replace(" ", "_")
        .replace("-", "_")
        .lower()
        for column in columns
    ]


def _normalize_ticker(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).upper().strip()


def _normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _normalize_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_text_loader(url: str) -> str:
    request = Request(url, headers={"User-Agent": "StockResearchCommandCenter/1.0 research-only"})
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def _meaningful_value(value: Any, field_name: str) -> bool:
    if value is None or pd.isna(value):
        return False
    text = str(value).strip()
    if not text:
        return False
    if field_name == "theme" and text == "Unclassified":
        return False
    if field_name == "market_cap_bucket" and text == "Unknown":
        return False
    return True


def _make_row(
    *,
    ticker: str,
    source_name: str,
    company_name: str = "",
    theme: str = "",
    sector_etf: str = "",
    default_purpose: str = "",
    market_cap_bucket: str = "",
    notes: str = "",
    source_detail: str = "",
    index_membership: str = "",
    etf_membership: str = "",
    exchange: str = "",
    is_etf: bool = False,
    as_of_date: str = "",
    in_local_sample: bool = False,
    in_sp500: bool = False,
    in_nasdaq: bool = False,
    in_smh: bool = False,
    in_holdings: bool = False,
    in_custom: bool = False,
) -> dict[str, Any]:
    ticker = _normalize_ticker(ticker)
    default_purpose = _normalize_text(default_purpose)
    if not default_purpose:
        default_purpose = "ETF / Defensive / Hedge" if is_etf else "Core Compounder"
        notes = " ".join(
            part
            for part in [
                notes,
                "Default purpose was assigned conservatively for universe compatibility; review before relying on purpose-based outputs.",
            ]
            if part
        )
    theme = _normalize_text(theme) or TEXT_FALLBACKS["theme"]
    market_cap_bucket = _normalize_text(market_cap_bucket) or TEXT_FALLBACKS["market_cap_bucket"]
    row = {
        "ticker": ticker,
        "theme": theme,
        "sector_etf": _normalize_ticker(sector_etf),
        "default_purpose": default_purpose,
        "market_cap_bucket": market_cap_bucket,
        "notes": _normalize_text(notes),
        "company_name": _normalize_text(company_name),
        "universe_source": source_name,
        "source_detail": _normalize_text(source_detail),
        "index_membership": _normalize_text(index_membership),
        "etf_membership": _normalize_text(etf_membership),
        "exchange": _normalize_text(exchange),
        "is_etf": bool(is_etf),
        "as_of_date": _normalize_text(as_of_date),
        "in_local_sample": bool(in_local_sample),
        "in_sp500": bool(in_sp500),
        "in_nasdaq": bool(in_nasdaq),
        "in_smh": bool(in_smh),
        "in_holdings": bool(in_holdings),
        "in_custom": bool(in_custom),
        "_source_priority": SOURCE_PRIORITY[source_name],
    }
    return row


def _canonicalize_universe_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=CANONICAL_UNIVERSE_COLUMNS + ["_source_priority"])
    frame = frame.copy()
    frame.columns = _normalize_columns(list(frame.columns))
    frame = frame.rename(
        columns={
            "sectoretf": "sector_etf",
            "defaultpurpose": "default_purpose",
            "marketcapbucket": "market_cap_bucket",
        }
    )
    for column in CANONICAL_UNIVERSE_COLUMNS:
        if column not in frame.columns:
            if column in MEMBERSHIP_COLUMNS:
                frame[column] = False
            else:
                frame[column] = ""
    frame["ticker"] = frame["ticker"].map(_normalize_ticker)
    frame["sector_etf"] = frame["sector_etf"].map(_normalize_ticker)
    for column in MEMBERSHIP_COLUMNS + ["is_etf"]:
        frame[column] = frame[column].map(_normalize_bool)
    for column in CANONICAL_UNIVERSE_COLUMNS:
        if column in {"ticker", "sector_etf", "is_etf", *MEMBERSHIP_COLUMNS}:
            continue
        frame[column] = frame[column].map(_normalize_text)
    if "_source_priority" not in frame.columns:
        frame["_source_priority"] = SOURCE_PRIORITY.get("local", 0)
    return frame[CANONICAL_UNIVERSE_COLUMNS + ["_source_priority"]].copy()


def _read_local_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _read_local_source(base_dir: Path) -> tuple[pd.DataFrame, UniverseSourceResult]:
    path = base_dir / "data" / "universe.csv"
    if not path.exists():
        return pd.DataFrame(columns=CANONICAL_UNIVERSE_COLUMNS + ["_source_priority"]), UniverseSourceResult(
            source_name="local",
            status="missing_file",
            row_count=0,
            warnings=["data/universe.csv is not present."],
        )
    frame = _canonicalize_universe_frame(_read_local_csv(path))
    frame["in_local_sample"] = True
    frame["universe_source"] = frame["universe_source"].where(frame["universe_source"].ne(""), "local")
    result = UniverseSourceResult(
        source_name="local",
        status="loaded",
        row_count=len(frame),
        available_columns=[column for column in frame.columns if column != "_source_priority"],
        retrieved_at=_now_iso(),
    )
    return frame, result


def _read_holdings_source(base_dir: Path) -> tuple[pd.DataFrame, UniverseSourceResult]:
    path = base_dir / "data" / "holdings.csv"
    if not path.exists():
        return pd.DataFrame(columns=CANONICAL_UNIVERSE_COLUMNS + ["_source_priority"]), UniverseSourceResult(
            source_name="holdings",
            status="missing_file",
            row_count=0,
            warnings=["data/holdings.csv is not present."],
        )
    frame = _read_local_csv(path)
    frame.columns = _normalize_columns(list(frame.columns))
    rows = []
    for _, row in frame.iterrows():
        ticker = _normalize_ticker(row.get("ticker"))
        if not ticker:
            continue
        rows.append(
            _make_row(
                ticker=ticker,
                source_name="holdings",
                default_purpose=_normalize_text(row.get("primarypurpose") or row.get("primary_purpose")),
                notes="Added from holdings.csv.",
                in_holdings=True,
            )
        )
    result_frame = pd.DataFrame(rows, columns=CANONICAL_UNIVERSE_COLUMNS + ["_source_priority"])
    result = UniverseSourceResult(
        source_name="holdings",
        status="loaded",
        row_count=len(result_frame),
        available_columns=list(frame.columns),
        retrieved_at=_now_iso(),
    )
    return result_frame, result


def _read_custom_source(base_dir: Path) -> tuple[pd.DataFrame, UniverseSourceResult]:
    path = base_dir / "data" / "custom_universe.csv"
    if not path.exists():
        return pd.DataFrame(columns=CANONICAL_UNIVERSE_COLUMNS + ["_source_priority"]), UniverseSourceResult(
            source_name="custom",
            status="missing_file",
            row_count=0,
            warnings=["data/custom_universe.csv is not present."],
        )
    frame = _read_local_csv(path)
    frame.columns = _normalize_columns(list(frame.columns))
    rows = []
    for _, row in frame.iterrows():
        ticker = _normalize_ticker(row.get("ticker"))
        if not ticker:
            continue
        rows.append(
            _make_row(
                ticker=ticker,
                source_name="custom",
                company_name=_normalize_text(row.get("company_name")),
                theme=_normalize_text(row.get("theme")),
                sector_etf=_normalize_text(row.get("sector_etf")),
                notes=_normalize_text(row.get("notes")),
                source_detail=_normalize_text(row.get("source")),
                in_custom=True,
            )
        )
    result_frame = pd.DataFrame(rows, columns=CANONICAL_UNIVERSE_COLUMNS + ["_source_priority"])
    result = UniverseSourceResult(
        source_name="custom",
        status="loaded",
        row_count=len(result_frame),
        available_columns=list(frame.columns),
        retrieved_at=_now_iso(),
    )
    return result_frame, result


def _load_remote_text(source_name: str, url: str, loader: SourceLoader) -> tuple[str | None, list[str]]:
    fallback_hint = ""
    if source_name == "smh":
        fallback_hint = (
            " VanEck may require browser cookies or location handling from this runtime; "
            "use data/custom_universe.csv or stage data/imports/universe.csv as the manual SMH fallback."
        )
    try:
        return loader(url), []
    except URLError as exc:
        return None, [f"{source_name}: remote source unavailable ({exc}).{fallback_hint}"]
    except Exception as exc:  # pragma: no cover - defensive runtime path
        return None, [f"{source_name}: source fetch failed ({exc}).{fallback_hint}"]


def _parse_sp500_source(text: str) -> pd.DataFrame:
    frame = pd.read_csv(StringIO(text))
    frame.columns = _normalize_columns(list(frame.columns))
    rows = []
    for _, row in frame.iterrows():
        ticker = _normalize_ticker(row.get("symbol"))
        if not ticker:
            continue
        rows.append(
            _make_row(
                ticker=ticker,
                source_name="sp500",
                company_name=_normalize_text(row.get("security")),
                source_detail=_normalize_text(row.get("gics_sector")),
                index_membership="S&P 500",
                notes="Theme and sector ETF metadata were not provided by the constituent source.",
                in_sp500=True,
            )
        )
    return pd.DataFrame(rows, columns=CANONICAL_UNIVERSE_COLUMNS + ["_source_priority"])


def _looks_like_non_common_equity(security_name: str) -> bool:
    lowered = security_name.lower()
    blocked_terms = [
        "warrant",
        "right",
        "unit",
        "preferred",
        "depositary",
        "notes",
        "bond",
    ]
    return any(term in lowered for term in blocked_terms)


def _parse_nasdaq_source(
    text: str,
    *,
    include_etfs: bool,
    include_nasdaq_all: bool,
    exclude_test_issues: bool,
) -> pd.DataFrame:
    frame = pd.read_csv(StringIO(text), sep="|", dtype=str)
    frame.columns = _normalize_columns(list(frame.columns))
    if "symbol" not in frame.columns:
        return pd.DataFrame(columns=CANONICAL_UNIVERSE_COLUMNS + ["_source_priority"])
    frame = frame.loc[frame["symbol"].notna()].copy()
    if "symbol" in frame.columns:
        frame["symbol"] = frame["symbol"].astype(str).str.strip()
    frame = frame.loc[~frame["symbol"].str.startswith("File Creation Time", na=False)].copy()
    if exclude_test_issues and "test_issue" in frame.columns:
        frame = frame.loc[frame["test_issue"].astype(str).str.upper() != "Y"].copy()
    if not include_etfs and "etf" in frame.columns:
        frame = frame.loc[frame["etf"].astype(str).str.upper() != "Y"].copy()
    if not include_nasdaq_all and "security_name" in frame.columns:
        frame = frame.loc[~frame["security_name"].astype(str).map(_looks_like_non_common_equity)].copy()

    rows = []
    for _, row in frame.iterrows():
        ticker = _normalize_ticker(row.get("symbol"))
        if not ticker:
            continue
        is_etf = str(row.get("etf", "")).upper() == "Y"
        rows.append(
            _make_row(
                ticker=ticker,
                source_name="nasdaq",
                company_name=_normalize_text(row.get("security_name")),
                exchange="NASDAQ",
                is_etf=is_etf,
                index_membership="Nasdaq-listed",
                notes="Theme and sector ETF metadata were not provided by the Nasdaq directory.",
                in_nasdaq=True,
            )
        )
    return pd.DataFrame(rows, columns=CANONICAL_UNIVERSE_COLUMNS + ["_source_priority"])


def _parse_smh_source(text: str) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    try:
        csv_frame = pd.read_csv(StringIO(text))
        frames.append(csv_frame)
    except Exception:
        pass
    try:
        html_frames = pd.read_html(StringIO(text))
        frames.extend(html_frames)
    except Exception:
        pass

    selected: pd.DataFrame | None = None
    for frame in frames:
        normalized = frame.copy()
        normalized.columns = _normalize_columns(list(normalized.columns))
        if any(column in normalized.columns for column in ("ticker", "symbol", "holding_ticker")):
            selected = normalized
            break

    if selected is None:
        return pd.DataFrame(columns=CANONICAL_UNIVERSE_COLUMNS + ["_source_priority"])

    ticker_column = next(column for column in ("ticker", "symbol", "holding_ticker") if column in selected.columns)
    name_column = next((column for column in ("company_name", "name", "holding_name", "security_name") if column in selected.columns), None)
    weight_column = next((column for column in ("weight", "portfolio_weight", "holding_weight") if column in selected.columns), None)
    date_column = next((column for column in ("as_of_date", "date") if column in selected.columns), None)

    rows = []
    for _, row in selected.iterrows():
        ticker = _normalize_ticker(row.get(ticker_column))
        if not ticker:
            continue
        weight_note = ""
        if weight_column and pd.notna(row.get(weight_column)):
            weight_note = f"SMH weight: {row.get(weight_column)}"
        rows.append(
            _make_row(
                ticker=ticker,
                source_name="smh",
                company_name=_normalize_text(row.get(name_column)) if name_column else "",
                etf_membership="SMH",
                source_detail=weight_note,
                notes="Theme and sector ETF metadata were not provided by the SMH holdings source.",
                as_of_date=_normalize_text(row.get(date_column)) if date_column else "",
                in_smh=True,
            )
        )
    return pd.DataFrame(rows, columns=CANONICAL_UNIVERSE_COLUMNS + ["_source_priority"])


def _read_remote_source(
    source_name: str,
    *,
    loader: SourceLoader,
    include_etfs: bool,
    include_nasdaq_all: bool,
    exclude_test_issues: bool,
) -> tuple[pd.DataFrame, UniverseSourceResult]:
    url = SOURCE_URLS[source_name]
    text, warnings = _load_remote_text(source_name, url, loader)
    if text is None:
        return pd.DataFrame(columns=CANONICAL_UNIVERSE_COLUMNS + ["_source_priority"]), UniverseSourceResult(
            source_name=source_name,
            status="source_unavailable",
            row_count=0,
            warnings=warnings,
            source_url=url,
        )
    if source_name == "sp500":
        frame = _parse_sp500_source(text)
    elif source_name == "nasdaq":
        frame = _parse_nasdaq_source(
            text,
            include_etfs=include_etfs,
            include_nasdaq_all=include_nasdaq_all,
            exclude_test_issues=exclude_test_issues,
        )
    else:
        frame = _parse_smh_source(text)
    status = "loaded" if not frame.empty else "empty"
    if frame.empty:
        warnings.append(f"{source_name}: source returned no usable ticker rows after filtering.")
    return frame, UniverseSourceResult(
        source_name=source_name,
        status=status,
        row_count=len(frame),
        warnings=warnings,
        source_url=url,
        retrieved_at=_now_iso(),
        available_columns=[column for column in frame.columns if column != "_source_priority"],
    )


def _resolve_sources(sources: str | list[str] | None = None, preset: str | None = None) -> list[str]:
    requested: list[str] = []
    if preset:
        requested.extend(SOURCE_PRESETS.get(preset, []))
    if isinstance(sources, str):
        requested.extend(part.strip() for part in sources.split(",") if part.strip())
    elif sources:
        requested.extend(sources)
    if not requested:
        requested = SOURCE_PRESETS["core"].copy()
    ordered = []
    seen = set()
    for source in requested:
        if source not in {"local", "holdings", "custom", "sp500", "nasdaq", "smh"}:
            continue
        if source not in seen:
            seen.add(source)
            ordered.append(source)
    return ordered


def _merge_universe_rows(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=CANONICAL_UNIVERSE_COLUMNS)
    frame = frame.sort_values(["ticker", "_source_priority"]).reset_index(drop=True)
    merged_rows: list[dict[str, Any]] = []
    for ticker, rows in frame.groupby("ticker", sort=True):
        base = rows.iloc[0].to_dict()
        for column in MEMBERSHIP_COLUMNS + ["is_etf"]:
            base[column] = bool(rows[column].fillna(False).astype(bool).any())
        for column in ("universe_source", "index_membership", "etf_membership"):
            values = [value for value in rows[column].map(_normalize_text).tolist() if value]
            base[column] = ", ".join(dict.fromkeys(values))
        for column in ("notes", "source_detail"):
            values = [value for value in rows[column].map(_normalize_text).tolist() if value]
            base[column] = " | ".join(dict.fromkeys(values))
        for column in ("company_name", "theme", "sector_etf", "default_purpose", "market_cap_bucket", "exchange", "as_of_date"):
            if _meaningful_value(base.get(column), column):
                continue
            for value in rows[column].tolist():
                if _meaningful_value(value, column):
                    base[column] = value
                    break
        for field_name, fallback in TEXT_FALLBACKS.items():
            if not _meaningful_value(base.get(field_name), field_name):
                base[field_name] = fallback
        if not _meaningful_value(base.get("default_purpose"), "default_purpose"):
            base["default_purpose"] = "ETF / Defensive / Hedge" if base["is_etf"] else "Core Compounder"
        if not _meaningful_value(base.get("market_cap_bucket"), "market_cap_bucket"):
            base["market_cap_bucket"] = "Unknown"
        merged_rows.append({column: base.get(column, "") for column in CANONICAL_UNIVERSE_COLUMNS})
    return pd.DataFrame(merged_rows, columns=CANONICAL_UNIVERSE_COLUMNS).sort_values("ticker").reset_index(drop=True)


def _load_source_frame(
    source_name: str,
    *,
    base_dir: Path,
    loader: SourceLoader,
    include_etfs: bool,
    include_nasdaq_all: bool,
    exclude_test_issues: bool,
) -> tuple[pd.DataFrame, UniverseSourceResult]:
    if source_name == "local":
        return _read_local_source(base_dir)
    if source_name == "holdings":
        return _read_holdings_source(base_dir)
    if source_name == "custom":
        return _read_custom_source(base_dir)
    return _read_remote_source(
        source_name,
        loader=loader,
        include_etfs=include_etfs,
        include_nasdaq_all=include_nasdaq_all,
        exclude_test_issues=exclude_test_issues,
    )


def validate_universe_sources(
    *,
    base_dir: Path | None = None,
    sources: str | list[str] | None = None,
    preset: str | None = None,
    include_etfs: bool = False,
    include_nasdaq_all: bool = False,
    exclude_test_issues: bool = True,
    loader: SourceLoader | None = None,
) -> dict[str, Any]:
    base_dir = base_dir or Path(__file__).resolve().parent.parent
    loader = loader or _default_text_loader
    resolved_sources = _resolve_sources(sources=sources, preset=preset)
    results = []
    for source_name in resolved_sources:
        _frame, result = _load_source_frame(
            source_name,
            base_dir=base_dir,
            loader=loader,
            include_etfs=include_etfs,
            include_nasdaq_all=include_nasdaq_all,
            exclude_test_issues=exclude_test_issues,
        )
        results.append(result.to_dict())
    statuses = {item["status"] for item in results}
    overall = "valid"
    if results and all(item["status"] in {"source_unavailable", "missing_file", "empty"} for item in results):
        overall = "no_available_sources"
    elif any(item["status"] in {"source_unavailable"} for item in results):
        overall = "partial"
    return {
        "status": overall,
        "sources": results,
    }


def build_universe_preview(
    *,
    base_dir: Path | None = None,
    sources: str | list[str] | None = None,
    preset: str | None = None,
    include_etfs: bool = False,
    include_nasdaq_all: bool = False,
    exclude_test_issues: bool = True,
    max_tickers: int | None = None,
    loader: SourceLoader | None = None,
) -> dict[str, Any]:
    base_dir = base_dir or Path(__file__).resolve().parent.parent
    loader = loader or _default_text_loader
    resolved_sources = _resolve_sources(sources=sources, preset=preset)

    frames: list[pd.DataFrame] = []
    source_results: list[dict[str, Any]] = []
    build_warnings: list[str] = []
    for source_name in resolved_sources:
        frame, result = _load_source_frame(
            source_name,
            base_dir=base_dir,
            loader=loader,
            include_etfs=include_etfs,
            include_nasdaq_all=include_nasdaq_all,
            exclude_test_issues=exclude_test_issues,
        )
        if not frame.empty:
            frames.append(frame)
        source_results.append(result.to_dict())
        build_warnings.extend(result.warnings)

    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=CANONICAL_UNIVERSE_COLUMNS + ["_source_priority"])
    duplicate_count = int(combined.duplicated(subset=["ticker"]).sum()) if not combined.empty else 0
    merged = _merge_universe_rows(combined)
    if max_tickers is not None and max_tickers > 0:
        merged = merged.head(max_tickers).copy()
    current_universe = _canonicalize_universe_frame(_read_local_csv(base_dir / "data" / "universe.csv"))
    current_universe = current_universe.drop(columns=["_source_priority"], errors="ignore")
    current_lookup = current_universe.set_index("ticker") if not current_universe.empty else pd.DataFrame()

    new_tickers = 0
    updated_tickers = 0
    unchanged_tickers = 0
    for _, row in merged.iterrows():
        ticker = row["ticker"]
        if current_lookup.empty or ticker not in current_lookup.index:
            new_tickers += 1
            continue
        current_row = current_lookup.loc[ticker]
        if isinstance(current_row, pd.DataFrame):
            current_row = current_row.iloc[-1]
        changed = False
        for column in CANONICAL_UNIVERSE_COLUMNS:
            if column == "ticker":
                continue
            left = row.get(column)
            right = current_row.get(column)
            if pd.isna(left) and pd.isna(right):
                continue
            if left != right:
                changed = True
                break
        if changed:
            updated_tickers += 1
        else:
            unchanged_tickers += 1

    membership_counts = {column: int(merged[column].fillna(False).astype(bool).sum()) for column in MEMBERSHIP_COLUMNS if column in merged.columns}
    return {
        "status": "ok" if not merged.empty else "empty",
        "sources": source_results,
        "rows": merged.to_dict(orient="records"),
        "summary": {
            "requested_sources": resolved_sources,
            "row_count": len(merged),
            "duplicate_tickers_before_merge": duplicate_count,
            "new_tickers": new_tickers,
            "updated_tickers": updated_tickers,
            "unchanged_tickers": unchanged_tickers,
            "membership_counts": membership_counts,
            "warnings": sorted(set(build_warnings)),
        },
    }


def _universe_import_path(base_dir: Path) -> Path:
    return base_dir / "data" / "imports" / "universe.csv"


def write_universe_import(
    *,
    base_dir: Path | None = None,
    sources: str | list[str] | None = None,
    preset: str | None = None,
    include_etfs: bool = False,
    include_nasdaq_all: bool = False,
    exclude_test_issues: bool = True,
    max_tickers: int | None = None,
    overwrite: bool = False,
    loader: SourceLoader | None = None,
) -> dict[str, Any]:
    base_dir = base_dir or Path(__file__).resolve().parent.parent
    preview = build_universe_preview(
        base_dir=base_dir,
        sources=sources,
        preset=preset,
        include_etfs=include_etfs,
        include_nasdaq_all=include_nasdaq_all,
        exclude_test_issues=exclude_test_issues,
        max_tickers=max_tickers,
        loader=loader,
    )
    output_path = _universe_import_path(base_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if preview["status"] == "empty":
        return {
            "status": "no_rows",
            "output_path": str(output_path),
            "summary": preview["summary"],
            "sources": preview["sources"],
        }
    if output_path.exists() and not overwrite:
        return {
            "status": "staged_file_exists",
            "output_path": str(output_path),
            "summary": preview["summary"],
            "sources": preview["sources"],
            "warnings": ["Staged universe import already exists. Re-run with --overwrite to replace it."],
        }

    pd.DataFrame(preview["rows"], columns=CANONICAL_UNIVERSE_COLUMNS).to_csv(output_path, index=False)
    return {
        "status": "written",
        "output_path": str(output_path),
        "row_count": len(preview["rows"]),
        "summary": preview["summary"],
        "sources": preview["sources"],
    }


def apply_universe_import(*, base_dir: Path | None = None, backup: bool = True) -> dict[str, Any]:
    base_dir = base_dir or Path(__file__).resolve().parent.parent
    staged_path = _universe_import_path(base_dir)
    canonical_path = base_dir / "data" / "universe.csv"
    validation, staged_frame = validate_local_dataset("universe", staged_path)
    if validation.status == "missing_file":
        return {
            "status": "no_staged_file",
            "staged_path": str(staged_path),
            "warnings": validation.warnings,
        }
    if validation.status == "invalid":
        return {
            "status": "refused_invalid_import",
            "staged_path": str(staged_path),
            "validation": validation.to_dict(),
        }

    staged_frame = _canonicalize_universe_frame(staged_frame if staged_frame is not None else pd.DataFrame())
    canonical_frame = _canonicalize_universe_frame(_read_local_csv(canonical_path))
    staged_lookup = staged_frame.drop(columns=["_source_priority"], errors="ignore").set_index("ticker")
    canonical_lookup = canonical_frame.drop(columns=["_source_priority"], errors="ignore").set_index("ticker") if not canonical_frame.empty else pd.DataFrame()

    merged_rows: list[dict[str, Any]] = []
    updated = 0
    unchanged = 0
    new_rows = 0
    all_tickers = sorted(set(canonical_lookup.index.tolist() if not canonical_lookup.empty else []) | set(staged_lookup.index.tolist()))
    for ticker in all_tickers:
        staged_row = staged_lookup.loc[ticker] if ticker in staged_lookup.index else None
        if isinstance(staged_row, pd.DataFrame):
            staged_row = staged_row.iloc[-1]
        canonical_row = canonical_lookup.loc[ticker] if not canonical_lookup.empty and ticker in canonical_lookup.index else None
        if isinstance(canonical_row, pd.DataFrame):
            canonical_row = canonical_row.iloc[-1]
        if canonical_row is None:
            merged_rows.append({"ticker": ticker, **staged_row.to_dict()})
            new_rows += 1
            continue
        merged = canonical_row.to_dict()
        changed = False
        if staged_row is not None:
            for column in CANONICAL_UNIVERSE_COLUMNS:
                if column == "ticker":
                    continue
                staged_value = staged_row.get(column)
                if column in MEMBERSHIP_COLUMNS + ["is_etf"]:
                    new_value = _normalize_bool(staged_value) or _normalize_bool(merged.get(column))
                else:
                    new_value = staged_value if _meaningful_value(staged_value, column) else merged.get(column, "")
                if merged.get(column) != new_value:
                    changed = True
                    merged[column] = new_value
        merged_rows.append({"ticker": ticker, **merged})
        if changed:
            updated += 1
        else:
            unchanged += 1

    merged_frame = pd.DataFrame(merged_rows, columns=CANONICAL_UNIVERSE_COLUMNS).sort_values("ticker").reset_index(drop=True)
    backup_path = None
    if backup and canonical_path.exists():
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_dir = base_dir / "data" / "backups" / f"universe_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / "universe.csv"
        shutil.copy2(canonical_path, backup_path)
    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    merged_frame.to_csv(canonical_path, index=False)
    return {
        "status": "applied",
        "staged_path": str(staged_path),
        "canonical_path": str(canonical_path),
        "backup_path": str(backup_path) if backup_path is not None else None,
        "new_rows": new_rows,
        "updated_rows": updated,
        "unchanged_rows": unchanged,
        "row_count": len(merged_frame),
    }


def summarize_universe_manager(base_dir: Path | None = None) -> dict[str, Any]:
    base_dir = base_dir or Path(__file__).resolve().parent.parent
    validation, frame = validate_local_dataset("universe", base_dir / "data" / "universe.csv")
    frame = _canonicalize_universe_frame(frame if frame is not None else pd.DataFrame())
    staged_validation, staged_frame = validate_local_dataset("universe", _universe_import_path(base_dir))
    duplicate_count = int(frame["ticker"].duplicated().sum()) if not frame.empty else 0
    membership_counts = {
        column: int(frame[column].fillna(False).astype(bool).sum())
        for column in MEMBERSHIP_COLUMNS
        if column in frame.columns
    }
    missing_theme_count = int(frame["theme"].fillna("").eq("").sum()) if not frame.empty else 0
    unclassified_theme_count = int(frame["theme"].fillna("").eq("Unclassified").sum()) if not frame.empty else 0
    missing_sector_etf_count = int(frame["sector_etf"].fillna("").eq("").sum()) if not frame.empty else 0
    return {
        "current_universe": {
            "validation": validation.to_dict(),
            "row_count": len(frame),
            "duplicate_ticker_count": duplicate_count,
            "membership_counts": membership_counts,
            "missing_theme_count": missing_theme_count,
            "unclassified_theme_count": unclassified_theme_count,
            "missing_sector_etf_count": missing_sector_etf_count,
            "rows": frame.to_dict(orient="records"),
        },
        "staged_universe": {
            "validation": staged_validation.to_dict(),
            "row_count": len(staged_frame) if staged_frame is not None else 0,
            "path": str(_universe_import_path(base_dir)),
        },
        "presets": SOURCE_PRESETS,
    }


def _print_result(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, default=str))
        return
    print(json.dumps(payload, indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and stage a larger local stock universe.")
    parser.add_argument("--validate-sources", action="store_true", help="Validate configured universe sources.")
    parser.add_argument("--preview", action="store_true", help="Preview a staged merged universe without writing it.")
    parser.add_argument("--write-import", action="store_true", help="Write a universe import draft to data/imports/universe.csv.")
    parser.add_argument("--apply-import", action="store_true", help="Apply the universe import draft to data/universe.csv with backup.")
    parser.add_argument("--sources", help="Comma-separated sources: local,holdings,custom,sp500,nasdaq,smh")
    parser.add_argument("--preset", choices=sorted(SOURCE_PRESETS.keys()), help="Safe preset source group.")
    parser.add_argument("--include-etfs", action="store_true", help="Include ETF rows from the Nasdaq directory.")
    parser.add_argument("--include-nasdaq-all", action="store_true", help="Keep a broader Nasdaq directory set instead of common-stock-focused filtering.")
    parser.add_argument("--exclude-test-issues", action="store_true", default=True, help="Exclude Nasdaq test issues (default: on).")
    parser.add_argument("--max-tickers", type=int, help="Limit preview/write row count for safer smoke runs.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing universe import draft file.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args()

    if args.apply_import:
        payload = apply_universe_import()
    elif args.write_import:
        payload = write_universe_import(
            sources=args.sources,
            preset=args.preset,
            include_etfs=args.include_etfs,
            include_nasdaq_all=args.include_nasdaq_all,
            exclude_test_issues=args.exclude_test_issues,
            max_tickers=args.max_tickers,
            overwrite=args.overwrite,
        )
    elif args.preview:
        payload = build_universe_preview(
            sources=args.sources,
            preset=args.preset,
            include_etfs=args.include_etfs,
            include_nasdaq_all=args.include_nasdaq_all,
            exclude_test_issues=args.exclude_test_issues,
            max_tickers=args.max_tickers,
        )
    else:
        payload = validate_universe_sources(
            sources=args.sources,
            preset=args.preset,
            include_etfs=args.include_etfs,
            include_nasdaq_all=args.include_nasdaq_all,
            exclude_test_issues=args.exclude_test_issues,
        )
    _print_result(payload, args.json)


if __name__ == "__main__":
    main()
