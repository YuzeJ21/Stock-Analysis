"""Validate a saved Nasdaq Trader directory pair without importing listing rows.

The receipt is dated inspection evidence. It does not establish issuer identity,
domicile, current listing status, analysis eligibility, or redistribution rights.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import stat
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
_MAX_MANIFEST_BYTES = 1 * 1024 * 1024
_MAX_DIRECTORY_BYTES = 8 * 1024 * 1024


def _unique_manifest_keys(items: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in items:
        if key in result:
            raise ValueError("manifest_invalid")
        result[key] = value
    return result


def _invalid_json_constant(_value: str) -> object:
    raise ValueError("manifest_invalid")


def _regular_bytes(path: Path, reason: str, maximum: int) -> bytes:
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if not isinstance(nofollow, int) or nofollow == 0:
        raise ValueError(reason)
    descriptor: int | None = None
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | nofollow | getattr(os, "O_NONBLOCK", 0)
            | getattr(os, "O_CLOEXEC", 0),
        )
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
            raise ValueError(reason)
        chunks: list[bytes] = []
        remaining = maximum + 1
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(descriptor)
        if (
            sum(len(chunk) for chunk in chunks) > maximum
            or sum(len(chunk) for chunk in chunks) != after.st_size
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        ):
            raise ValueError(reason)
        return b"".join(chunks)
    except OSError as exc:
        raise ValueError(reason) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


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


def _parse_directory(
    raw: bytes, source: str, columns: tuple[str, ...], *, allow_unknown_venues: bool = False
) -> tuple[int, int, set[str], str, list[dict[str, str]]]:
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
        verified_rows: list[dict[str, str]] = []
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
            if source == "other" and row["Exchange"].strip().upper() not in _EXCHANGE_CODES and (not allow_unknown_venues or re.fullmatch(r"[A-Z0-9]{1,8}", row["Exchange"].strip().upper()) is None):
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
            verified_rows.append(
                {
                    "act_symbol": symbol,
                    "cqs_symbol": row["CQS Symbol"].strip().upper() if source == "other" else "",
                    "nasdaq_symbol": row["NASDAQ Symbol"].strip().upper() if source == "other" else "",
                    "source": source,
                    "exchange_code": row["Exchange"].strip().upper() if source == "other" else "",
                    "market_category": row["Market Category"].strip().upper() if source == "nasdaq" else "",
                    "etf": etf,
                    "security_name": row["Security Name"].strip(),
                }
            )
    except (csv.Error, StopIteration) as exc:
        raise ValueError("source_rows_invalid") from exc
    if not seen:
        raise ValueError("source_rows_invalid")
    return len(seen), excluded, seen, created, verified_rows


def load_us_listing_rows(snapshot_dir: Path) -> tuple[dict[str, object], list[dict[str, str]]]:
    """Return validated aggregate evidence and internal non-test directory rows."""

    snapshot_dir = Path(snapshot_dir)
    absolute_dir = snapshot_dir.absolute()
    if (".." in snapshot_dir.parts or not snapshot_dir.is_dir()
            or any(path.is_symlink() for path in (absolute_dir, *absolute_dir.parents))):
        raise ValueError("snapshot_dir_invalid")
    manifest_bytes = _regular_bytes(
        snapshot_dir / "manifest.json", "manifest_invalid", _MAX_MANIFEST_BYTES
    )
    try:
        manifest = json.loads(
            manifest_bytes,
            object_pairs_hook=_unique_manifest_keys,
            parse_constant=_invalid_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
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
    verified_rows: list[dict[str, str]] = []
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

        raw = _regular_bytes(
            snapshot_dir / name, "source_file_invalid", _MAX_DIRECTORY_BYTES
        )
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("digest_mismatch")
        count, excluded, symbols, footer_created, parsed_rows = _parse_directory(raw, source, columns)
        if footer_created != created:
            raise ValueError("creation_time_mismatch")
        if seen.intersection(symbols):
            raise ValueError("symbol_duplicate")
        seen.update(symbols)
        verified_rows.extend(parsed_rows)
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
    report = {
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
    return report, verified_rows


def build_us_listing_receipt_audit(snapshot_dir: Path) -> dict[str, object]:
    """Verify two local receipt files and return only aggregate, held evidence."""
    report, _rows = load_us_listing_rows(snapshot_dir)
    return report


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
