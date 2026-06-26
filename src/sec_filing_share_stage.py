from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

import pandas as pd

from src.providers.local_schemas import LOCAL_DATASET_SCHEMAS, normalize_columns, validate_local_dataset
from src.providers.sec_companyfacts import load_sec_ticker_map
from src.providers.sec_submissions import build_sec_filing_share_count_evidence


SOURCE_LABEL = "sec_filing_document"
SHARE_COUNT_WARNING = (
    "Shares outstanding staged from explicit SEC filing document fact "
    "dei:EntityCommonStockSharesOutstanding."
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _allowed_fundamentals_columns() -> list[str]:
    schema = LOCAL_DATASET_SCHEMAS["fundamentals"]
    columns = list(schema.required_columns)
    for column in schema.optional_columns:
        if column not in columns:
            columns.append(column)
    return columns


def _clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null", "<na>"} else text


def _has_value(value: object) -> bool:
    return bool(_clean(value))


def _merge_label(existing: object, label: str) -> str:
    values = [part.strip() for part in _clean(existing).replace("+", ";").split(";") if part.strip()]
    if label not in values:
        values.append(label)
    return "; ".join(values)


def _merge_warning(existing: object, warning: str) -> str:
    values = [part.strip() for part in _clean(existing).split("|") if part.strip()]
    if warning not in values:
        values.append(warning)
    return " | ".join(values)


def _cached_sec_ticker_map(cache_dir: Path) -> dict[str, dict[str, object]]:
    path = cache_dir / "company_tickers.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    rows = payload.values() if isinstance(payload, dict) else payload if isinstance(payload, list) else []
    ticker_map: dict[str, dict[str, object]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker") or "").upper().strip()
        cik = row.get("cik") or row.get("cik_str") or row.get("cikStr")
        if ticker and cik not in (None, ""):
            ticker_map[ticker] = {"ticker": ticker, "cik": cik, "title": row.get("title") or row.get("name")}
    return ticker_map


def _local_sec_ticker_map(data_dir: Path) -> dict[str, dict[str, object]]:
    ticker_map: dict[str, dict[str, object]] = {}
    for path in (data_dir / "fundamentals.csv", data_dir / "imports" / "fundamentals.csv"):
        for row in _read_csv(path):
            ticker = str(row.get("ticker") or "").upper().strip()
            cik = row.get("sec_cik")
            if ticker and cik not in (None, ""):
                ticker_map.setdefault(
                    ticker,
                    {
                        "ticker": ticker,
                        "cik": cik,
                        "title": row.get("sec_entity_name") or row.get("name") or row.get("company_name"),
                    },
                )
    return ticker_map


def build_sec_filing_share_ticker_map(
    *,
    data_dir: str | Path = "data",
    cache_dir: str | Path = "data/cache/sec",
    user_agent: str | None = None,
    refresh: bool = False,
    ticker_map_fetcher: Callable[[str, str, float], Any] | None = None,
) -> dict[str, dict[str, object]]:
    data_path = Path(data_dir)
    cache_path = Path(cache_dir)
    ticker_map = _local_sec_ticker_map(data_path)
    ticker_map.update(_cached_sec_ticker_map(cache_path))
    if user_agent:
        try:
            sec_map = load_sec_ticker_map(
                cache_dir=cache_path,
                user_agent=user_agent,
                refresh=refresh,
                fetcher=ticker_map_fetcher,
            )
            ticker_map.update(sec_map)
        except Exception:
            if not ticker_map:
                raise
    return ticker_map


def _existing_row(data_dir: Path, ticker: str) -> dict[str, object]:
    ticker_text = ticker.upper().strip()
    for path in (data_dir / "imports" / "fundamentals.csv", data_dir / "fundamentals.csv"):
        for row in _read_csv(path):
            if str(row.get("ticker") or "").upper().strip() == ticker_text:
                return dict(row)
    return {"ticker": ticker_text}


def _stage_row_from_evidence(data_dir: Path, ticker: str, evidence: dict[str, Any]) -> dict[str, object]:
    row = {column: _existing_row(data_dir, ticker).get(column, "") for column in _allowed_fundamentals_columns()}
    row["ticker"] = ticker.upper().strip()
    row["shares_outstanding"] = evidence.get("shares_outstanding")
    row["source"] = _merge_label(row.get("source"), SOURCE_LABEL)
    row["as_of_date"] = evidence.get("as_of_date")
    row["sec_cik"] = evidence.get("sec_cik")
    row["sec_form"] = evidence.get("sec_form")
    row["sec_filed_date"] = evidence.get("sec_filed_date")
    row["sec_accession"] = evidence.get("sec_accession")
    row["sec_entity_name"] = evidence.get("sec_entity_name")
    row["sec_fact_warnings"] = _merge_warning(row.get("sec_fact_warnings"), SHARE_COUNT_WARNING)
    row["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return row


def _write_fundamentals_import_rows(rows: list[dict[str, object]], output_path: Path) -> dict[str, Any]:
    columns = _allowed_fundamentals_columns()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    incoming = pd.DataFrame(rows)
    for column in columns:
        if column not in incoming.columns:
            incoming[column] = pd.NA
    incoming = incoming[columns].copy()
    incoming["ticker"] = incoming["ticker"].astype("string").str.upper().str.strip()
    incoming = incoming.dropna(subset=["ticker"]).drop_duplicates(subset=["ticker"], keep="last")

    if output_path.exists():
        validation, existing_frame = validate_local_dataset("fundamentals", output_path)
        if validation.status == "invalid":
            raise ValueError("Existing fundamentals import file is invalid. Fix it before SEC filing share-count staging.")
        existing = existing_frame.copy() if existing_frame is not None else pd.DataFrame(columns=columns)
    else:
        existing = pd.DataFrame(columns=columns)
    existing.columns = normalize_columns(list(existing.columns))
    for column in columns:
        if column not in existing.columns:
            existing[column] = pd.NA
    existing = existing[columns].copy()
    existing["ticker"] = existing["ticker"].astype("string").str.upper().str.strip()
    existing = existing.dropna(subset=["ticker"]).drop_duplicates(subset=["ticker"], keep="last")

    existing = existing.set_index("ticker", drop=False).astype(object)
    incoming = incoming.set_index("ticker", drop=False).astype(object)
    overlap = existing.index.intersection(incoming.index)
    if not overlap.empty:
        for column in [column for column in columns if column != "ticker"]:
            values = incoming.loc[overlap, column]
            mask = values.map(_has_value)
            if mask.any():
                existing.loc[values.index[mask], column] = values.loc[mask]
    new_rows = incoming.loc[~incoming.index.isin(existing.index)]
    merged = pd.concat([existing, new_rows], axis=0).reset_index(drop=True)[columns]
    merged.to_csv(output_path, index=False)
    return {
        "status": "written",
        "output_path": str(output_path),
        "rows_written": int(len(incoming)),
        "staged_row_count": int(len(merged)),
        "tickers_written": sorted(incoming["ticker"].dropna().astype(str).tolist()),
    }


def stage_sec_filing_share_count_rows(
    tickers: Iterable[str],
    *,
    root: str | Path = ".",
    data_dir: str | Path | None = None,
    user_agent: str | None = None,
    allow_network: bool = True,
    refresh: bool = False,
    ticker_map: dict[str, dict[str, Any]] | None = None,
    ticker_map_fetcher: Callable[[str, str, float], Any] | None = None,
    submission_fetcher: Callable[[str, str, float], Any] | None = None,
    document_fetcher: Callable[[str, str, float], str] | None = None,
) -> dict[str, Any]:
    root_path = Path(root)
    data_path = Path(data_dir) if data_dir is not None else root_path / "data"
    cache_dir = data_path / "cache" / "sec"
    requested = sorted({str(ticker).upper().strip() for ticker in tickers if str(ticker).strip()})
    resolved: list[str] = []
    unresolved: list[str] = []
    rows: list[dict[str, object]] = []
    row_summaries: list[dict[str, Any]] = []
    warnings: list[str] = []
    if not requested:
        return {
            "requested_tickers": [],
            "resolved_tickers": [],
            "unresolved_tickers": [],
            "rows": [],
            "row_summaries": [],
            "warnings": ["No tickers were provided for SEC filing share-count staging."],
            "rows_written": 0,
        }

    resolved_map = ticker_map or build_sec_filing_share_ticker_map(
        data_dir=data_path,
        cache_dir=cache_dir,
        user_agent=user_agent,
        refresh=refresh,
        ticker_map_fetcher=ticker_map_fetcher,
    )
    for ticker in requested:
        evidence = build_sec_filing_share_count_evidence(
            ticker,
            ticker_map=resolved_map,
            cache_dir=cache_dir,
            user_agent=user_agent,
            allow_network=allow_network,
            submission_fetcher=submission_fetcher,
            document_fetcher=document_fetcher,
        )
        if evidence.get("status") != "available":
            unresolved.append(ticker)
            warnings.append(f"{ticker}: {evidence.get('reason_code') or 'unavailable'} - {evidence.get('detail') or 'no share-count evidence'}")
            row_summaries.append(
                {
                    "ticker": ticker,
                    "status": "unavailable",
                    "reason_code": evidence.get("reason_code"),
                    "detail": evidence.get("detail"),
                    "warnings": [evidence.get("detail")] if evidence.get("detail") else [],
                }
            )
            continue
        row = _stage_row_from_evidence(data_path, ticker, evidence)
        rows.append(row)
        resolved.append(ticker)
        row_summaries.append(
            {
                "ticker": ticker,
                "status": "available",
                "shares_outstanding": evidence.get("shares_outstanding"),
                "sec_cik": evidence.get("sec_cik"),
                "sec_form": evidence.get("sec_form"),
                "sec_filed_date": evidence.get("sec_filed_date"),
                "sec_accession": evidence.get("sec_accession"),
                "sec_primary_document": evidence.get("sec_primary_document"),
                "source": SOURCE_LABEL,
                "warnings": [],
            }
        )

    write_result = {"rows_written": 0, "staged_row_count": 0, "output_path": str(data_path / "imports" / "fundamentals.csv")}
    if rows:
        write_result = _write_fundamentals_import_rows(rows, data_path / "imports" / "fundamentals.csv")
    return {
        "requested_tickers": requested,
        "resolved_tickers": resolved,
        "unresolved_tickers": unresolved,
        "rows": rows,
        "row_summaries": row_summaries,
        "warnings": sorted(set(warnings)),
        **write_result,
        "recommended_next_commands": [
            "make imports-validate IMPORT_TICKERS=<resolved_tickers>",
            "make imports-preview IMPORT_TICKERS=<resolved_tickers>",
            "make imports-apply IMPORT_TICKERS=<resolved_tickers>",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage SEC filing-document share-count evidence into data/imports/fundamentals.csv.")
    parser.add_argument("--tickers", required=True, help="Comma-separated ticker list.")
    parser.add_argument("--project-root", default=".", help="Project root. Defaults to current directory.")
    parser.add_argument("--data-dir", help="Optional data directory.")
    parser.add_argument("--sec-user-agent", help="Identifying SEC User-Agent. Defaults to SEC_USER_AGENT.")
    parser.add_argument("--sec-refresh", action="store_true", help="Refresh SEC ticker-map and filing caches.")
    parser.add_argument("--no-network", action="store_true", help="Use cached SEC submissions and filing documents only.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args()
    tickers = [ticker.strip() for ticker in args.tickers.split(",") if ticker.strip()]
    payload = stage_sec_filing_share_count_rows(
        tickers,
        root=args.project_root,
        data_dir=args.data_dir,
        user_agent=args.sec_user_agent,
        allow_network=not args.no_network,
        refresh=args.sec_refresh,
    )
    if args.json:
        print(json.dumps(payload, indent=2))
        return
    print(f"requested_tickers: {', '.join(payload['requested_tickers']) or '-'}")
    print(f"resolved_tickers: {', '.join(payload['resolved_tickers']) or '-'}")
    print(f"unresolved_tickers: {', '.join(payload['unresolved_tickers']) or '-'}")
    print(f"rows_written: {payload.get('rows_written', 0)}")
    print(f"staged_row_count: {payload.get('staged_row_count', 0)}")
    print(f"output_path: {payload.get('output_path')}")
    if payload["warnings"]:
        print(f"warnings: {'; '.join(payload['warnings'])}")
    for row in payload["row_summaries"]:
        if row["status"] == "available":
            print(
                f"{row['ticker']}: shares_outstanding={row['shares_outstanding']} "
                f"source={row['source']} filing={row['sec_form']} filed={row['sec_filed_date']} "
                f"accession={row['sec_accession']} document={row['sec_primary_document']}"
            )
        else:
            print(f"{row['ticker']}: unavailable reason={row.get('reason_code') or '-'} detail={row.get('detail') or '-'}")
    print("next:")
    for command in payload["recommended_next_commands"]:
        print(f"- {command}")


if __name__ == "__main__":
    main()
