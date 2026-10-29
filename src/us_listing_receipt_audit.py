"""Validate a saved Nasdaq Trader directory pair without importing listing rows.

The receipt is dated inspection evidence. It does not establish issuer identity,
domicile, current listing status, analysis eligibility, or redistribution rights.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path


_SOURCES = (
    (
        "nasdaq",
        "nasdaqlisted.txt",
        "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt",
        ("Symbol", "Security Name", "Market Category", "Test Issue", "Financial Status", "Round Lot Size", "ETF", "NextShares"),
    ),
    (
        "other",
        "otherlisted.txt",
        "https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt",
        ("ACT Symbol", "Security Name", "Exchange", "CQS Symbol", "ETF", "Round Lot Size", "Test Issue", "NASDAQ Symbol"),
    ),
)
_EXCHANGE_CODES = frozenset({"A", "N", "P", "Z", "V", "F", "M"})
_MARKET_CATEGORIES = frozenset({"Q", "G", "S"})
_FINANCIAL_STATUSES = frozenset({"D", "E", "Q", "N", "G", "H", "J", "K"})
_SYMBOL = re.compile(r"[A-Z0-9][A-Z0-9.$-]{0,13}\Z")
_FOOTER = re.compile(r"File Creation Time: (\d{8})(\d{2}:\d{2})\|*\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _regular_bytes(path: Path, reason: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError(reason)
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ValueError(reason) from exc


def _created_at(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("date_invalid")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M")
    except ValueError as exc:
        raise ValueError("date_invalid") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M") != value:
        raise ValueError("date_invalid")
    return value


def _observed_at(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("date_invalid")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError("date_invalid") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise ValueError("date_invalid")
    return parsed.replace(tzinfo=timezone.utc)


def _last_modified(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("date_invalid")
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError) as exc:
        raise ValueError("date_invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("date_invalid")
    return parsed.astimezone(timezone.utc)


def _parse_directory(raw: bytes, source: str, columns: tuple[str, ...]) -> tuple[int, int, set[str], str]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("source_encoding_invalid") from exc
    lines = text.splitlines()
    if len(lines) < 3:
        raise ValueError("source_rows_invalid")
    footer = _FOOTER.fullmatch(lines[-1].strip())
    if footer is None:
        raise ValueError("creation_time_invalid")
    try:
        created = datetime.strptime("".join(footer.groups()), "%m%d%Y%H:%M").strftime("%Y-%m-%dT%H:%M")
    except ValueError as exc:
        raise ValueError("date_invalid") from exc
    rows = csv.reader(lines[:-1], delimiter="|", strict=True)
    try:
        header = tuple(next(rows))
        if header != columns:
            raise ValueError("schema_invalid")
        seen: set[str] = set()
        excluded = 0
        for fields in rows:
            if len(fields) != len(columns):
                raise ValueError("source_rows_invalid")
            row = dict(zip(columns, fields))
            test_issue = row["Test Issue"].strip().upper()
            etf = row["ETF"].strip().upper()
            if test_issue not in {"Y", "N"} or etf not in {"Y", "N"}:
                raise ValueError("source_flags_invalid")
            lot = row["Round Lot Size"].strip()
            if re.fullmatch(r"[0-9]{1,6}", lot) is None or int(lot) < 1:
                raise ValueError("round_lot_size_invalid")
            if source == "nasdaq":
                if row["Market Category"].strip().upper() not in _MARKET_CATEGORIES:
                    raise ValueError("market_category_invalid")
                if row["Financial Status"].strip().upper() not in _FINANCIAL_STATUSES:
                    raise ValueError("financial_status_invalid")
                if row["NextShares"].strip().upper() not in {"Y", "N"}:
                    raise ValueError("nextshares_flag_invalid")
            if source == "other" and row["Exchange"].strip().upper() not in _EXCHANGE_CODES:
                raise ValueError("exchange_code_unrecognized")
            if test_issue == "Y":
                excluded += 1
                continue
            symbol = row["Symbol" if source == "nasdaq" else "ACT Symbol"].strip().upper()
            if _SYMBOL.fullmatch(symbol) is None or not row["Security Name"].strip():
                raise ValueError("source_rows_invalid")
            if symbol in seen:
                raise ValueError("symbol_duplicate")
            seen.add(symbol)
    except (csv.Error, StopIteration) as exc:
        raise ValueError("source_rows_invalid") from exc
    if not seen:
        raise ValueError("source_rows_invalid")
    return len(seen), excluded, seen, created


def build_us_listing_receipt_audit(snapshot_dir: Path) -> dict[str, object]:
    """Verify two local receipt files and return only aggregate, held evidence."""

    snapshot_dir = Path(snapshot_dir)
    absolute_dir = snapshot_dir.absolute()
    if (".." in snapshot_dir.parts or not snapshot_dir.is_dir()
            or any(path.is_symlink() for path in (absolute_dir, *absolute_dir.parents))):
        raise ValueError("snapshot_dir_invalid")
    manifest_bytes = _regular_bytes(snapshot_dir / "manifest.json", "manifest_invalid")
    try:
        manifest = json.loads(manifest_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("manifest_invalid") from exc
    if not isinstance(manifest, dict) or manifest.get("inspection_only") is not True:
        raise ValueError("manifest_invalid")
    items = manifest.get("sources")
    if not isinstance(items, list) or len(items) != 2 or any(not isinstance(item, dict) for item in items):
        raise ValueError("source_identity_invalid")
    if any(not isinstance(item.get("source"), str) for item in items):
        raise ValueError("source_identity_invalid")
    by_source = {item.get("source"): item for item in items}
    if set(by_source) != {"nasdaq", "other"}:
        raise ValueError("source_identity_invalid")

    results: list[dict[str, object]] = []
    seen: set[str] = set()
    pair_created: set[str] = set()
    pair_observed: set[str] = set()
    pair_modified: set[str] = set()
    for source, name, url, columns in _SOURCES:
        item = by_source[source]
        if item.get("file") != name or item.get("url") != url:
            raise ValueError("source_identity_invalid")
        digest = item.get("sha256")
        if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
            raise ValueError("digest_invalid")
        created = _created_at(item.get("source_created_at"))
        observed = _observed_at(item.get("observed_at_utc"))
        modified = _last_modified(item.get("last_modified"))
        # The directory footer has no timezone, so only the HTTP/UTC timestamps
        # can be ordered against one another.
        if modified > observed:
            raise ValueError("date_order_invalid")
        pair_created.add(created)
        pair_observed.add(item["observed_at_utc"])
        pair_modified.add(modified.isoformat())

        raw = _regular_bytes(snapshot_dir / name, "source_file_invalid")
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("digest_mismatch")
        count, excluded, symbols, footer_created = _parse_directory(raw, source, columns)
        if footer_created != created:
            raise ValueError("creation_time_mismatch")
        if seen.intersection(symbols):
            raise ValueError("symbol_duplicate")
        seen.update(symbols)
        if type(item.get("rows_excluding_test_issues")) is not int or item["rows_excluding_test_issues"] != count:
            raise ValueError("manifest_count_mismatch")
        if type(item.get("excluded_test_issues")) is not int or item["excluded_test_issues"] != excluded:
            raise ValueError("manifest_count_mismatch")
        results.append(
            {"source": source, "url": url, "file": name, "sha256": digest,
             "source_created_at": created, "last_modified": item["last_modified"],
             "observed_at_utc": item["observed_at_utc"],
             "rows_excluding_test_issues": count, "excluded_test_issues": excluded}
        )
    if len(pair_created) != 1 or len(pair_observed) != 1 or len(pair_modified) != 1:
        raise ValueError("pair_time_mismatch")
    return {
        "status": "validated_receipts",
        "inspection_only": True,
        "import_status": "held",
        "rights_status": "unreviewed",
        "source_created_at": next(iter(pair_created)),
        "source_time_zone": "not specified by directory",
        "observed_at_utc": next(iter(pair_observed)),
        "total_non_test_symbols": len(seen),
        "excluded_test_issues": sum(entry["excluded_test_issues"] for entry in results),
        "sources": results,
        "boundary": "Listing-symbol receipts do not establish issuer domicile, security identity, current active status, analysis eligibility, or redistribution rights.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate saved U.S. listing receipts without import")
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build_us_listing_receipt_audit(args.snapshot_dir)
    except ValueError as exc:
        print(json.dumps({"status": "invalid", "import_status": "held", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
