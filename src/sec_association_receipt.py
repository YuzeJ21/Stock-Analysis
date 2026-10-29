"""Read one saved SEC ticker/CIK search-association receipt without import.

The SEC map is a search aid. Even a digest-checked association does not prove
security identity, issuer domicile, listing lifecycle, or analysis eligibility.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import unicodedata
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime, parsedate_to_datetime
from pathlib import Path


SEC_MAP_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
SEC_MAP_FILE = "company_tickers_exchange.json"
_FIELDS = ["cik", "name", "ticker", "exchange"]
_MAP_ENTRY_KEYS = {"file", "url", "sha256", "last_modified", "observed_at_utc"}
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_TICKER = re.compile(r"[A-Z0-9][A-Z0-9.$-]{0,20}\Z")
_OBSERVED = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
_MAX_MANIFEST_BYTES = 1 * 1024 * 1024
_MAX_MAP_BYTES = 8 * 1024 * 1024
_MAX_ROWS = 100_000


def _no_duplicate_keys(items: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in items:
        if key in result:
            raise ValueError("json_duplicate_key")
        result[key] = value
    return result


def _invalid_constant(value: str) -> object:
    raise ValueError("json_nonfinite_value")


def _json_object(raw: bytes, reason: str) -> dict[str, object]:
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_no_duplicate_keys,
            parse_constant=_invalid_constant,
        )
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError(reason) from exc
    if not isinstance(value, dict):
        raise ValueError(reason)
    return value


def _capture_directory_fd(capture_dir: Path) -> int:
    path = Path(capture_dir)
    absolute = path.absolute()
    if ".." in path.parts or any(part.is_symlink() for part in (absolute, *absolute.parents)):
        raise ValueError("sec_capture_dir_invalid")
    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory = getattr(os, "O_DIRECTORY", None)
    if not isinstance(nofollow, int) or not isinstance(directory, int):
        raise ValueError("sec_capture_dir_invalid")
    try:
        descriptor = os.open(
            absolute,
            os.O_RDONLY | nofollow | directory | getattr(os, "O_CLOEXEC", 0),
        )
    except OSError as exc:
        raise ValueError("sec_capture_dir_invalid") from exc
    if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise ValueError("sec_capture_dir_invalid")
    return descriptor


def _bounded_regular_bytes(directory_fd: int, name: str, maximum: int, reason: str) -> bytes:
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0)
            | getattr(os, "O_CLOEXEC", 0),
            dir_fd=directory_fd,
        )
    except OSError as exc:
        raise ValueError(reason) from exc
    try:
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
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        ):
            raise ValueError(reason)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _receipt_times(entry: dict[str, object]) -> tuple[str, str]:
    observed_value = entry.get("observed_at_utc")
    modified_value = entry.get("last_modified")
    if not isinstance(observed_value, str) or _OBSERVED.fullmatch(observed_value) is None:
        raise ValueError("sec_observation_time_invalid")
    try:
        observed = datetime.strptime(observed_value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError("sec_observation_time_invalid") from exc
    if not isinstance(modified_value, str) or not modified_value:
        raise ValueError("sec_last_modified_invalid")
    try:
        modified = parsedate_to_datetime(modified_value)
        if (
            modified.tzinfo is None
            or modified.utcoffset() != timedelta(0)
            or format_datetime(modified, usegmt=True) != modified_value
        ):
            raise ValueError("sec_last_modified_invalid")
    except (TypeError, ValueError, IndexError) as exc:
        raise ValueError("sec_last_modified_invalid") from exc
    if modified > observed:
        raise ValueError("sec_last_modified_after_observation")
    return modified.strftime("%Y-%m-%dT%H:%M:%SZ"), observed_value


def _clean_display(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and value == value.strip()
        and not any(unicodedata.category(character) in {"Cc", "Cf"} for character in value)
    )


def _rows(payload: dict[str, object]) -> list[dict[str, object]]:
    if set(payload) != {"fields", "data"} or payload["fields"] != _FIELDS:
        raise ValueError("sec_map_schema_invalid")
    data = payload["data"]
    if not isinstance(data, list) or len(data) > _MAX_ROWS:
        raise ValueError("sec_map_schema_invalid")
    rows: list[dict[str, object]] = []
    for values in data:
        if not isinstance(values, list) or len(values) != 4:
            raise ValueError("sec_map_row_invalid")
        cik, name, ticker, exchange = values
        if type(cik) is not int or cik <= 0:
            raise ValueError("sec_map_row_invalid")
        if not _clean_display(name):
            raise ValueError("sec_map_row_invalid")
        if not isinstance(ticker, str) or _TICKER.fullmatch(ticker) is None:
            raise ValueError("sec_map_row_invalid")
        if exchange is not None and exchange != "" and not _clean_display(exchange):
            raise ValueError("sec_map_row_invalid")
        rows.append({"cik": cik, "name": name, "ticker": ticker, "exchange": exchange or ""})
    return rows


def load_sec_association_receipt(
    capture_dir: Path,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    """Return verified receipt metadata and internal search-association rows.

    Duplicate ticker rows are retained so the caller can classify ambiguity.
    No file is written or fetched.
    """

    directory_fd = _capture_directory_fd(capture_dir)
    try:
        manifest_bytes = _bounded_regular_bytes(
            directory_fd, "manifest.json", _MAX_MANIFEST_BYTES, "sec_manifest_invalid"
        )
        manifest = _json_object(manifest_bytes, "sec_manifest_invalid")
        entry = manifest.get("map")
        if manifest.get("inspection_only") is not True or not isinstance(entry, dict):
            raise ValueError("sec_manifest_invalid")
        if set(entry) != _MAP_ENTRY_KEYS or entry.get("file") != SEC_MAP_FILE or entry.get("url") != SEC_MAP_URL:
            raise ValueError("sec_source_identity_invalid")
        digest = entry.get("sha256")
        if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
            raise ValueError("sec_digest_invalid")
        last_modified, observed_at = _receipt_times(entry)
        map_bytes = _bounded_regular_bytes(
            directory_fd, SEC_MAP_FILE, _MAX_MAP_BYTES, "sec_map_file_invalid"
        )
    finally:
        os.close(directory_fd)
    if hashlib.sha256(map_bytes).hexdigest() != digest:
        raise ValueError("sec_digest_mismatch")
    rows = _rows(_json_object(map_bytes, "sec_map_schema_invalid"))
    report: dict[str, object] = {
        "status": "validated_receipt",
        "inspection_only": True,
        "safe_to_import": False,
        "rights_status": "unreviewed",
        "file": SEC_MAP_FILE,
        "url": SEC_MAP_URL,
        "sha256": digest,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "last_modified_at_utc": last_modified,
        "observed_at_utc": observed_at,
        "row_count": len(rows),
        "distinct_cik_count": len({row["cik"] for row in rows}),
        "boundary": (
            "SEC ticker/CIK search associations do not establish exact security identity, "
            "issuer domicile, current listing status, or analysis eligibility."
        ),
    }
    return report, rows
