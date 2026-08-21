"""Hash-guarded apply path for exactly four reviewed SEC canonical cells."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping


_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_HEAD_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_COORDINATES = (
    ("AAPL", "revenue", "revenue"),
    ("AAPL", "filing_dates", "sec_filed_date"),
    ("AMD", "revenue", "revenue"),
    ("AMD", "filing_dates", "sec_filed_date"),
)
_CIKS = {"AAPL": "0000320193", "AMD": "0000002488"}
_SEC_URL_PREFIX = "https://data.sec.gov/api/xbrl/companyfacts/CIK"


@dataclass(frozen=True)
class SecFundamentalsPatchApply:
    canonical_csv_bytes: bytes
    receipt: dict[str, Any]
    canonical_path: Path
    repository_root: Path
    authorized_repository_head: str


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _parse_packet(value: bytes) -> Mapping[str, Any]:
    try:
        packet = json.loads(value)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("patch preview must be valid JSON") from exc
    if not isinstance(packet, Mapping):
        raise ValueError("patch preview must be a JSON object")
    return packet


def _live_repository_head(repository_root: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError("live repository HEAD could not be resolved") from exc


def _canonical_lines(value: bytes) -> tuple[list[str], list[bytes], list[list[str]]]:
    try:
        physical_lines = value.splitlines(keepends=True)
        decoded = value.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("canonical CSV must be UTF-8") from exc
    if not physical_lines or not decoded.endswith("\n"):
        raise ValueError("canonical CSV must be newline-terminated")
    if any(not line.endswith(b"\n") or b"\r" in line for line in physical_lines):
        raise ValueError("canonical CSV must use one physical line per record")
    rows: list[list[str]] = []
    for line in physical_lines:
        try:
            parsed = list(csv.reader(io.StringIO(line.decode("utf-8"), newline=""), strict=True))
        except (UnicodeDecodeError, csv.Error) as exc:
            raise ValueError("canonical CSV must use one physical line per record") from exc
        if len(parsed) != 1:
            raise ValueError("canonical CSV must use one physical line per record")
        rows.append(parsed[0])
    header = rows[0]
    if not header or len(header) != len(set(header)) or "ticker" not in header:
        raise ValueError("canonical CSV header is invalid")
    if "currency" in header:
        raise ValueError("canonical schema expansion is not authorized")
    for column in ("revenue", "sec_filed_date"):
        if column not in header:
            raise ValueError(f"canonical schema is missing reviewed column: {column}")
    if any(len(row) != len(header) for row in rows[1:]):
        raise ValueError("canonical CSV must use one physical line per record")
    return header, physical_lines, rows


def _values_equal(current: str, expected: Any) -> bool:
    if isinstance(expected, bool):
        return False
    if isinstance(expected, (int, float)):
        try:
            return Decimal(current) == Decimal(str(expected))
        except InvalidOperation:
            return False
    return current == str(expected)


def _candidate_text(current: str, candidate: Any) -> str:
    if isinstance(candidate, bool) or candidate is None:
        raise ValueError("candidate value type is not authorized")
    if isinstance(candidate, (int, float)):
        try:
            number = Decimal(str(candidate))
        except InvalidOperation as exc:
            raise ValueError("candidate numeric value is invalid") from exc
        if not number.is_finite():
            raise ValueError("candidate numeric value is invalid")
        if current.endswith(".0") and number == number.to_integral_value():
            return f"{number.quantize(Decimal('1'))}.0"
        return str(candidate)
    if not isinstance(candidate, str) or "\n" in candidate or "\r" in candidate:
        raise ValueError("candidate value type is not authorized")
    return candidate


def _validate_proof(packet: Mapping[str, Any]) -> None:
    if packet.get("status") != "inspection_only":
        raise ValueError("patch preview must remain inspection-only")
    if packet.get("canonical_apply_authorized") is not False:
        raise ValueError("patch preview must remain inspection-only")
    if packet.get("repository_writes") != []:
        raise ValueError("patch preview must remain inspection-only")
    if packet.get("source_rights_mutated") is not False:
        raise ValueError("patch preview source rights contract is invalid")
    if packet.get("readiness_mutated") is not False:
        raise ValueError("patch preview readiness contract is invalid")
    if packet.get("materialization_performed") is not False:
        raise ValueError("patch preview materialization contract is invalid")
    proof = packet.get("in_memory_projection_proof")
    if not isinstance(proof, Mapping):
        raise ValueError("patch preview projection proof is required")
    exact = {
        "schema_added_columns": [],
        "schema_removed_columns": [],
        "row_order_unchanged": True,
        "full_row_replacement": False,
        "staged_input_used": False,
        "untouched_cells_unchanged": True,
        "untouched_rows_unchanged": True,
        "untouched_columns_unchanged": True,
    }
    if any(proof.get(key) != expected for key, expected in exact.items()):
        raise ValueError("patch preview projection proof is unsafe")
    for prefix in ("untouched_cells", "untouched_rows", "untouched_columns"):
        before = proof.get(f"{prefix}_sha256_before")
        after = proof.get(f"{prefix}_sha256_after")
        if not isinstance(before, str) or before != after or not _SHA256_PATTERN.fullmatch(before):
            raise ValueError("patch preview projection proof is unsafe")
    if proof.get("column_count_before") != proof.get("column_count_after"):
        raise ValueError("patch preview projection proof is unsafe")
    if proof.get("row_count_before") != proof.get("row_count_after"):
        raise ValueError("patch preview projection proof is unsafe")


def _validate_cell(cell: Mapping[str, Any], expected: tuple[str, str, str]) -> None:
    ticker, field, column = expected
    if (cell.get("ticker"), cell.get("field"), cell.get("canonical_column")) != expected:
        raise ValueError("patch cells do not match the exact reviewed coordinates")
    if cell.get("commercial_rights_approved") is not True or cell.get("source_rights_status") != "approved":
        raise ValueError("patch cell rights are not approved")
    if cell.get("field_scope_status") != "approved":
        raise ValueError("patch cell field scope is not approved")
    if cell.get("schema_status") != "existing_canonical":
        raise ValueError("patch cell schema is not existing canonical")
    unit = "date" if field == "filing_dates" else "USD"
    if cell.get("unit") != unit:
        raise ValueError("patch cell unit is invalid")
    cik = _CIKS[ticker]
    source_url = f"{_SEC_URL_PREFIX}{cik}.json"
    if cell.get("source_url") != source_url:
        raise ValueError("patch cell must use the reviewed official SEC source")
    refs = cell.get("source_refs")
    if not isinstance(refs, list) or not refs:
        raise ValueError("patch cell provenance is required")
    if cell.get("provenance_sha256") != _sha256(_json_bytes(refs)):
        raise ValueError("patch cell provenance hash mismatch")
    for ref in refs:
        if not isinstance(ref, Mapping) or ref.get("source_url") != source_url:
            raise ValueError("patch cell provenance source is invalid")
        if ref.get("unit") != unit:
            raise ValueError("patch cell provenance unit is invalid")
        if ref.get("retrieval_timestamp") != cell.get("retrieval_timestamp"):
            raise ValueError("patch cell provenance timestamp mismatch")
        for key in ("accession", "concept", "filed", "form", "period_end", "taxonomy"):
            if not ref.get(key):
                raise ValueError(f"patch cell provenance is missing {key}")
        if field == "filing_dates" and ref.get("underlying_fact_unit") != "USD":
            raise ValueError("filing date must preserve underlying fact unit")
    primary = refs[0]
    projected = {
        "period_start": primary.get("period_start"),
        "period_end": primary.get("period_end"),
        "filing_date": primary.get("filed"),
        "accession": primary.get("accession"),
        "concept": primary.get("concept"),
        "taxonomy": primary.get("taxonomy"),
        "form": primary.get("form"),
    }
    if any(cell.get(key) != value for key, value in projected.items()):
        raise ValueError("patch cell provenance projection mismatch")
    if column == "sec_filed_date" and cell.get("candidate_value") != cell.get("filing_date"):
        raise ValueError("filing date candidate does not match SEC provenance")


def build_sec_fundamentals_patch_apply(
    patch_preview_bytes: bytes,
    canonical_csv_bytes: bytes,
    *,
    canonical_path: str,
    expected_patch_preview_sha256: str,
    expected_canonical_sha256: str,
    repository_head: str,
    repository_root: Path,
    authorization_confirmed: bool,
) -> SecFundamentalsPatchApply:
    if authorization_confirmed is not True:
        raise ValueError("explicit authorization for the exact four-cell apply is required")
    if not _SHA256_PATTERN.fullmatch(expected_patch_preview_sha256):
        raise ValueError("expected patch preview SHA-256 is invalid")
    if not _SHA256_PATTERN.fullmatch(expected_canonical_sha256):
        raise ValueError("expected canonical SHA-256 is invalid")
    if not _GIT_HEAD_PATTERN.fullmatch(repository_head):
        raise ValueError("repository HEAD must be a full lowercase Git hash")
    repository_root = repository_root.resolve()
    live_head = _live_repository_head(repository_root)
    if live_head != repository_head:
        raise ValueError("live repository HEAD does not match the authorized preview")
    patch_sha = _sha256(patch_preview_bytes)
    canonical_sha = _sha256(canonical_csv_bytes)
    if patch_sha != expected_patch_preview_sha256:
        raise ValueError("patch preview hash precondition mismatch")
    if canonical_sha != expected_canonical_sha256:
        raise ValueError("canonical hash precondition mismatch")
    packet = _parse_packet(patch_preview_bytes)
    _validate_proof(packet)
    preconditions = packet.get("preconditions")
    if not isinstance(preconditions, Mapping):
        raise ValueError("patch preview preconditions are required")
    packet_canonical_path = preconditions.get("canonical_path")
    if not isinstance(packet_canonical_path, str) or not packet_canonical_path:
        raise ValueError("patch preview canonical path is not authorized")
    if packet_canonical_path != canonical_path:
        raise ValueError("canonical path precondition mismatch")
    authorized_canonical_path = Path(canonical_path)
    if not authorized_canonical_path.is_absolute():
        authorized_canonical_path = repository_root / authorized_canonical_path
    authorized_canonical_path = authorized_canonical_path.resolve()
    if preconditions.get("canonical_sha256") != canonical_sha:
        raise ValueError("patch preview canonical hash precondition mismatch")
    if preconditions.get("repository_head") != repository_head:
        raise ValueError("patch preview repository HEAD precondition mismatch")
    sec_sha = preconditions.get("sec_preview_sha256")
    if not isinstance(sec_sha, str) or not _SHA256_PATTERN.fullmatch(sec_sha):
        raise ValueError("patch preview SEC evidence hash is invalid")
    identity = _sha256(
        _json_bytes(
            {
                "canonical_sha256": canonical_sha,
                "sec_preview_sha256": sec_sha,
                "repository_head": repository_head,
                "patch_coordinates": [[ticker, column] for ticker, _, column in _COORDINATES],
            }
        )
    )
    if packet.get("projection_identity") != identity:
        raise ValueError("patch preview projection identity mismatch")
    cells = packet.get("patch_cells")
    if packet.get("changed_cell_count") != 4 or not isinstance(cells, list) or len(cells) != 4:
        raise ValueError("patch preview must contain exactly four cells")
    for cell, expected in zip(cells, _COORDINATES, strict=True):
        if not isinstance(cell, Mapping):
            raise ValueError("patch cell must be an object")
        _validate_cell(cell, expected)

    header, physical_lines, parsed_rows = _canonical_lines(canonical_csv_bytes)
    proof = packet["in_memory_projection_proof"]
    if proof.get("column_count_before") != len(header) or proof.get("row_count_before") != len(parsed_rows) - 1:
        raise ValueError("patch preview projection proof does not match canonical bytes")
    ticker_index = header.index("ticker")
    by_ticker: dict[str, tuple[int, list[str]]] = {}
    for index, row in enumerate(parsed_rows[1:], start=1):
        ticker = row[ticker_index].strip().upper()
        if ticker in by_ticker:
            raise ValueError(f"duplicate canonical ticker row: {ticker}")
        by_ticker[ticker] = (index, row)

    changed_cells: list[dict[str, Any]] = []
    touched_lines: set[int] = set()
    after_lines = list(physical_lines)
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for cell in cells:
        grouped.setdefault(str(cell["ticker"]), []).append(cell)
    for ticker in ("AAPL", "AMD"):
        if ticker not in by_ticker:
            raise ValueError(f"canonical ticker row is missing: {ticker}")
        line_index, row = by_ticker[ticker]
        projected = list(row)
        for cell in grouped[ticker]:
            column = str(cell["canonical_column"])
            column_index = header.index(column)
            current = row[column_index]
            if not _values_equal(current, cell.get("canonical_precondition")):
                raise ValueError(f"canonical cell precondition mismatch: {ticker}:{column}")
            candidate = _candidate_text(current, cell.get("candidate_value"))
            if _values_equal(current, cell.get("candidate_value")):
                raise ValueError(f"candidate does not change canonical cell: {ticker}:{column}")
            projected[column_index] = candidate
            changed_cells.append(
                {
                    "ticker": ticker,
                    "canonical_column": column,
                    "before": current,
                    "after": candidate,
                    "provenance_sha256": cell["provenance_sha256"],
                }
            )
        output = io.StringIO(newline="")
        csv.writer(output, lineterminator="\n").writerow(projected)
        original = io.StringIO(newline="")
        csv.writer(original, lineterminator="\n").writerow(row)
        if original.getvalue().encode("utf-8") != physical_lines[line_index]:
            raise ValueError("canonical target row is not in byte-preserving CSV form")
        after_lines[line_index] = output.getvalue().encode("utf-8")
        touched_lines.add(line_index)

    if [
        (cell["ticker"], cell["canonical_column"])
        for cell in changed_cells
    ] != [(ticker, column) for ticker, _, column in _COORDINATES]:
        raise ValueError("applied cells do not match the exact reviewed coordinates")
    canonical_after = b"".join(after_lines)
    for index, (before, after) in enumerate(zip(physical_lines, after_lines, strict=True)):
        if index not in touched_lines and before != after:
            raise ValueError("unrelated canonical bytes changed")
    after_header, _, after_rows = _canonical_lines(canonical_after)
    if after_header != header or [row[ticker_index] for row in after_rows[1:]] != [
        row[ticker_index] for row in parsed_rows[1:]
    ]:
        raise ValueError("canonical schema or row order changed")
    receipt = {
        "status": "authorized_exact_four_cell_projection",
        "applied": False,
        "authorization_confirmed": True,
        "canonical_path": canonical_path,
        "canonical_sha256_before": canonical_sha,
        "canonical_sha256_after": _sha256(canonical_after),
        "patch_preview_sha256": patch_sha,
        "projection_identity": identity,
        "repository_head": repository_head,
        "changed_cell_count": 4,
        "changed_cells": changed_cells,
        "schema_unchanged": True,
        "row_order_unchanged": True,
        "untouched_bytes_unchanged": True,
        "source_rights_mutated": False,
        "readiness_mutated": False,
        "readiness_materialized": False,
        "repository_writes": [],
    }
    return SecFundamentalsPatchApply(
        canonical_csv_bytes=canonical_after,
        receipt=receipt,
        canonical_path=authorized_canonical_path,
        repository_root=repository_root,
        authorized_repository_head=repository_head,
    )


def apply_sec_fundamentals_patch(
    result: SecFundamentalsPatchApply,
) -> dict[str, Any]:
    canonical_path = result.canonical_path
    if _live_repository_head(result.repository_root) != result.authorized_repository_head:
        raise ValueError("repository HEAD changed before materialization")
    current = canonical_path.read_bytes()
    if _sha256(current) != result.receipt["canonical_sha256_before"]:
        raise ValueError("canonical hash changed before materialization")
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{canonical_path.name}.",
            suffix=".tmp",
            dir=canonical_path.parent,
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(result.canonical_csv_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, canonical_path.stat().st_mode & 0o777)
        if _live_repository_head(result.repository_root) != result.authorized_repository_head:
            raise ValueError("repository HEAD changed before materialization")
        os.replace(temporary_path, canonical_path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    receipt = dict(result.receipt)
    receipt["status"] = "authorized_exact_four_cell_apply_complete"
    receipt["applied"] = True
    receipt["repository_writes"] = [str(canonical_path)]
    return receipt


def render_sec_fundamentals_patch_apply(result: Mapping[str, Any]) -> str:
    return json.dumps(result, indent=2, sort_keys=True, allow_nan=False)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply exactly four reviewed SEC canonical cells.")
    parser.add_argument("--patch-preview-path", type=Path, required=True)
    parser.add_argument("--canonical-path", type=Path, default=Path("data/fundamentals.csv"))
    parser.add_argument("--expected-patch-preview-sha256", required=True)
    parser.add_argument("--expected-canonical-sha256", required=True)
    parser.add_argument("--repository-head", required=True)
    parser.add_argument("--authorize-exact-four-cell-apply", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        result = build_sec_fundamentals_patch_apply(
            args.patch_preview_path.read_bytes(),
            args.canonical_path.read_bytes(),
            canonical_path=str(args.canonical_path),
            expected_patch_preview_sha256=args.expected_patch_preview_sha256,
            expected_canonical_sha256=args.expected_canonical_sha256,
            repository_head=args.repository_head,
            repository_root=Path.cwd(),
            authorization_confirmed=args.authorize_exact_four_cell_apply,
        )
        receipt = apply_sec_fundamentals_patch(result)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(render_sec_fundamentals_patch_apply(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
