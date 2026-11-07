"""Private, mutable decisions for bounded pairs of immutable SEC receipts."""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import unicodedata
from uuid import uuid4

from src.company_sec_online_preview import _utc_timestamp
from src.sec_association_receipt import _json_object
from src.sec_research_review import CIK, COMPANY_SCHEMA, _hex, _validate, list_reviews


DISPOSITION_STATUSES = ("reviewed", "still_open")
MAX_REASON_LENGTH = 500
_MAX_RECORD_BYTES = 4096
_SCHEMA = "sec-review-disposition-v1"
SUPPORTED_DISPOSITION_COMPANIES = {"NEM": CIK, "AMD": "0000002488"}


def resolve_pair(
    packets: Sequence[dict], before_id: str, after_id: str, *, ticker: str = "NEM",
) -> tuple[dict, dict]:
    """Resolve full IDs in an ordered list of validated saved receipts."""
    if ticker not in SUPPORTED_DISPOSITION_COMPANIES:
        raise ValueError("unsupported_disposition_company")
    if not _hex(before_id) or not _hex(after_id) or before_id == after_id:
        raise ValueError("invalid_disposition_pair_ids")
    if not isinstance(packets, Sequence) or any(
        not isinstance(packet, dict) or not _hex(packet.get("receipt_id")) for packet in packets
    ):
        raise ValueError("invalid_disposition_pair_receipts")
    matches = [packet for packet in packets if packet["receipt_id"] in (before_id, after_id)]
    if [packet["receipt_id"] for packet in matches] != [before_id, after_id]:
        raise ValueError("disposition_pair_unavailable_or_unordered")
    before, after = matches
    before_at, after_at = (_utc_timestamp(packet.get("saved_at")) for packet in matches)
    if before_at is None or after_at is None or (before_at, before_id) >= (after_at, after_id):
        raise ValueError("disposition_pair_unavailable_or_unordered")
    profile = before.get("profile_key")
    if (
        not isinstance(profile, str) or not profile or profile != after.get("profile_key")
        or any(
            packet.get("ticker") != ticker
            or packet.get("sec_cik") != SUPPORTED_DISPOSITION_COMPANIES[ticker]
            for packet in matches
        )
    ):
        raise ValueError("invalid_disposition_pair_scope")
    if ticker == "AMD":
        for packet in matches:
            if packet.get("schema_version") != COMPANY_SCHEMA:
                raise ValueError("unsupported_disposition_receipt_schema")
            _validate(packet)
    return before, after


def _validate_reason(status: str, reason: str) -> str:
    if status not in DISPOSITION_STATUSES:
        raise ValueError("invalid_disposition_status")
    if not isinstance(reason, str):
        raise ValueError("invalid_disposition_reason")
    cleaned = reason.strip()
    if not 1 <= len(cleaned) <= MAX_REASON_LENGTH or any(
        char not in "\t\n\r" and unicodedata.category(char) in ("Cc", "Cs") for char in cleaned
    ):
        raise ValueError("invalid_disposition_reason")
    return cleaned


def _scope(root: Path, profile_key: str, before_id: str, after_id: str, *, ticker: str = "NEM") -> dict:
    if ticker not in SUPPORTED_DISPOSITION_COMPANIES:
        raise ValueError("unsupported_disposition_company")
    resolve_pair(list_reviews(root, profile_key, ticker), before_id, after_id, ticker=ticker)
    return dict(schema_version=_SCHEMA, profile_key=profile_key, ticker=ticker,
                sec_cik=SUPPORTED_DISPOSITION_COMPANIES[ticker],
                before_id=before_id, after_id=after_id)


@contextmanager
def _directory(root: Path, profile_key: str, *, ticker: str = "NEM", create: bool = False):
    # Walk through pinned directory descriptors so none of the components can redirect via symlink.
    if ticker not in SUPPORTED_DISPOSITION_COMPANIES:
        raise ValueError("unsupported_disposition_company")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open(root, flags)
    parts = ("outputs", "local", "sec-review-dispositions", hashlib.sha256(profile_key.encode()).hexdigest())
    if ticker != "NEM":
        parts += (ticker,)
    try:
        for name in parts:
            if create:
                try:
                    os.mkdir(name, mode=0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
                else:
                    os.fsync(descriptor)
            try:
                child = os.open(name, flags, dir_fd=descriptor)
            except FileNotFoundError:
                if create:
                    raise
                yield None
                return
            os.close(descriptor)
            descriptor = child
        yield descriptor
    finally:
        os.close(descriptor)


def _name(scope: dict) -> str:
    return f"{scope['before_id']}-{scope['after_id']}.json"


def _encode(record: dict) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _read(directory: int, scope: dict) -> dict | None:
    try:
        descriptor = os.open(_name(scope), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    except FileNotFoundError:
        return None
    with os.fdopen(descriptor, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink > 1 or metadata.st_size > _MAX_RECORD_BYTES:
            raise ValueError("invalid_disposition_file")
        raw = stream.read(_MAX_RECORD_BYTES + 1)
    if not 0 < len(raw) <= _MAX_RECORD_BYTES:
        raise ValueError("invalid_disposition_size")
    record = _json_object(raw, "invalid_disposition_json")
    checksum = record.pop("content_sha256", None)
    if (
        set(record) != scope.keys() | {"status", "reason", "reviewed_at"}
        or any(record[key] != value for key, value in scope.items())
        or _utc_timestamp(record["reviewed_at"]) is None
        or _validate_reason(record["status"], record["reason"]) != record["reason"]
        or checksum != hashlib.sha256(_encode(record)).hexdigest()
    ):
        raise ValueError("invalid_disposition_record")
    return record


def load_disposition(
    root: Path | str, profile_key: str, before_id: str, after_id: str, *, ticker: str = "NEM",
) -> dict | None:
    """Load a decision only while both exact receipts remain valid in the profile."""
    root = Path(root).resolve()
    scope = _scope(root, profile_key, before_id, after_id, ticker=ticker)
    with _directory(root, profile_key, ticker=ticker) as directory:
        return _read(directory, scope) if directory is not None else None


def save_disposition(
    root: Path | str, profile_key: str, before_id: str, after_id: str, status: str, reason: str,
    *, ticker: str = "NEM",
) -> dict:
    """Replace the latest decision for the exact pair, or return an identical saved decision."""
    reason = _validate_reason(status, reason)
    root = Path(root).resolve()
    scope = _scope(root, profile_key, before_id, after_id, ticker=ticker)
    with _directory(root, profile_key, ticker=ticker, create=True) as directory:
        # Serializes retries and updates for this profile across local processes.
        fcntl.flock(directory, fcntl.LOCK_EX)
        existing = _read(directory, scope)
        if existing and (existing["status"], existing["reason"]) == (status, reason):
            return existing
        reviewed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        record = dict(scope, status=status, reason=reason, reviewed_at=reviewed_at)
        raw = _encode(dict(record, content_sha256=hashlib.sha256(_encode(record)).hexdigest())) + b"\n"
        temporary = f".decision-{uuid4().hex}.tmp"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        descriptor = os.open(temporary, flags, 0o600, dir_fd=directory)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, _name(scope), src_dir_fd=directory, dst_dir_fd=directory)
            os.fsync(directory)
        finally:
            try:
                os.unlink(temporary, dir_fd=directory)
            except FileNotFoundError:
                pass
        return record
