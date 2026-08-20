"""Pure, no-write preview for a reviewed SEC fundamentals cell patch."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping


_EXPECTED_TICKERS = ("AAPL", "NVDA", "AMD")
_EXPECTED_CIKS = {
    "AAPL": "0000320193",
    "NVDA": "0001045810",
    "AMD": "0000002488",
}
_ALLOWED_FIELDS = {
    "revenue": "revenue",
    "filing_dates": "sec_filed_date",
}
_SEC_URL_PREFIX = "https://data.sec.gov/api/xbrl/companyfacts/CIK"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_HEAD_PATTERN = re.compile(r"^[0-9a-f]{40}$")


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
        raise ValueError("SEC preview packet must be valid JSON") from exc
    if not isinstance(packet, Mapping):
        raise ValueError("SEC preview packet must be a JSON object")
    return packet


def _parse_canonical(value: bytes) -> tuple[list[str], list[list[str]]]:
    try:
        decoded = value.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("canonical CSV must be UTF-8") from exc
    rows = list(csv.reader(io.StringIO(decoded, newline="")))
    if not rows or not rows[0]:
        raise ValueError("canonical CSV header is required")
    header = rows[0]
    if len(header) != len(set(header)):
        raise ValueError("canonical CSV columns must be unique")
    for row in rows[1:]:
        if len(row) != len(header):
            raise ValueError("canonical row width must match the header")
    if "ticker" not in header:
        raise ValueError("canonical CSV requires ticker")
    for column in _ALLOWED_FIELDS.values():
        if column not in header:
            raise ValueError(f"canonical schema is missing reviewed column: {column}")
    return header, rows[1:]


def _values_equal(canonical: str, expected: Any) -> bool:
    if expected is None:
        return canonical == ""
    if isinstance(expected, bool):
        return canonical.lower() == str(expected).lower()
    if isinstance(expected, (int, float)):
        try:
            return Decimal(canonical) == Decimal(str(expected))
        except InvalidOperation:
            return False
    return canonical == str(expected)


def _official_sec_url(value: Any) -> bool:
    return (
        isinstance(value, str)
        and value.startswith(_SEC_URL_PREFIX)
        and value.endswith(".json")
        and "?" not in value
        and "#" not in value
    )


def _validate_field(
    field: Mapping[str, Any],
    ticker: str,
    name: str,
    *,
    sec_cik: str,
    retrieval_timestamp: str,
) -> None:
    if field.get("ticker") != ticker or field.get("field") != name:
        raise ValueError("candidate field scope does not match its ticker")
    if field.get("canonical_column") != _ALLOWED_FIELDS[name]:
        raise ValueError("candidate field does not map to the reviewed canonical column")
    required = {
        "classification": "approved_direct",
        "commercial_rights_approved": True,
        "field_scope_status": "approved",
        "schema_status": "existing_canonical",
        "publishability_blocker": "none",
        "value_kind": "direct",
        "value_status": "changed",
        "source_rights_status": "approved",
    }
    for key, expected in required.items():
        if field.get(key) != expected:
            if key == "field_scope_status":
                raise ValueError("candidate requires approved field scope")
            raise ValueError(f"candidate field failed reviewed evidence contract: {key}")
    expected_source_url = f"{_SEC_URL_PREFIX}{sec_cik}.json"
    if field.get("sec_cik") != sec_cik:
        raise ValueError("candidate field does not match the reviewed SEC CIK")
    if field.get("source_url") != expected_source_url:
        raise ValueError("candidate must use an official SEC source URL")
    if field.get("retrieval_timestamp") != retrieval_timestamp:
        raise ValueError("candidate retrieval timestamp does not match the SEC packet")
    refs = field.get("source_refs")
    if not isinstance(refs, list) or not refs:
        raise ValueError("candidate must include SEC provenance")
    for ref in refs:
        if not isinstance(ref, Mapping) or not _official_sec_url(ref.get("source_url")):
            raise ValueError("candidate must use official SEC source references")
        if ref.get("source_url") != expected_source_url:
            raise ValueError("candidate source reference does not match the reviewed SEC CIK")
        if ref.get("retrieval_timestamp") != retrieval_timestamp:
            raise ValueError("candidate source reference retrieval timestamp mismatch")
        for key in ("accession", "concept", "taxonomy", "form", "filed", "period_end"):
            if not ref.get(key):
                raise ValueError(f"candidate SEC provenance is missing {key}")
    if name == "filing_dates":
        if field.get("unit") != "date" or field.get("source_units") != ["date"]:
            raise ValueError("filing date provenance must use date units")
        if any(ref.get("unit") != "date" for ref in refs):
            raise ValueError("filing date source references must use date units")
        if any(ref.get("underlying_fact_unit") != "USD" for ref in refs):
            raise ValueError("filing date provenance must preserve the underlying fact unit")
    elif field.get("unit") != "USD" or field.get("source_units") != ["USD"]:
        raise ValueError("revenue provenance must use USD units")
    elif any(ref.get("unit") != "USD" for ref in refs):
        raise ValueError("revenue source references must use USD units")


def _cell_hash_payload(
    header: list[str], rows: list[list[str]], excluded: set[tuple[int, int]]
) -> list[list[Any]]:
    return [
        [row_index, header[column_index], value]
        for row_index, row in enumerate(rows)
        for column_index, value in enumerate(row)
        if (row_index, column_index) not in excluded
    ]


def build_sec_fundamentals_patch_preview(
    sec_preview_bytes: bytes,
    canonical_csv_bytes: bytes,
    *,
    canonical_path: str,
    expected_sec_preview_sha256: str,
    expected_canonical_sha256: str,
    repository_head: str,
) -> dict[str, Any]:
    if not _SHA256_PATTERN.fullmatch(expected_sec_preview_sha256):
        raise ValueError("expected SEC preview SHA-256 is invalid")
    if not _SHA256_PATTERN.fullmatch(expected_canonical_sha256):
        raise ValueError("expected canonical SHA-256 is invalid")
    if not _GIT_HEAD_PATTERN.fullmatch(repository_head):
        raise ValueError("repository HEAD must be a full lowercase Git hash")
    sec_preview_sha256 = _sha256(sec_preview_bytes)
    canonical_sha256 = _sha256(canonical_csv_bytes)
    if sec_preview_sha256 != expected_sec_preview_sha256:
        raise ValueError("SEC preview hash precondition mismatch")
    if canonical_sha256 != expected_canonical_sha256:
        raise ValueError("canonical hash precondition mismatch")
    packet = _parse_packet(sec_preview_bytes)
    if packet.get("status") != "inspection_only":
        raise ValueError("SEC preview must remain inspection_only")
    if packet.get("canonical_apply_authorized") is not False:
        raise ValueError("SEC preview must not carry apply authorization")
    if packet.get("repository_writes") != []:
        raise ValueError("SEC preview must report no repository writes")
    if packet.get("source") != "sec_companyfacts":
        raise ValueError("SEC preview must use sec_companyfacts only")
    if packet.get("source_rights_mutated") is not False:
        raise ValueError("SEC preview must not mutate source rights")
    if packet.get("requested_tickers") != list(_EXPECTED_TICKERS):
        raise ValueError("SEC preview must use the reviewed AAPL,NVDA,AMD cohort")
    retrieval_timestamp = packet.get("retrieval_timestamp")
    if not isinstance(retrieval_timestamp, str) or not retrieval_timestamp:
        raise ValueError("SEC preview retrieval timestamp is required")

    ticker_rows = packet.get("tickers")
    if not isinstance(ticker_rows, list):
        raise ValueError("SEC preview ticker rows are required")
    by_ticker: dict[str, Mapping[str, Any]] = {}
    for row in ticker_rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("ticker"), str):
            raise ValueError("SEC preview ticker row is invalid")
        ticker = row["ticker"]
        if ticker in by_ticker:
            raise ValueError(f"duplicate ticker row: {ticker}")
        by_ticker[ticker] = row
    if set(by_ticker) != set(_EXPECTED_TICKERS):
        raise ValueError("SEC preview ticker rows do not match the reviewed cohort")

    header, rows = _parse_canonical(canonical_csv_bytes)
    ticker_column = header.index("ticker")
    canonical_by_ticker: dict[str, tuple[int, list[str]]] = {}
    for index, row in enumerate(rows):
        ticker = row[ticker_column].strip().upper()
        if ticker in canonical_by_ticker:
            raise ValueError(f"duplicate canonical ticker row: {ticker}")
        canonical_by_ticker[ticker] = (index, row)

    patch_cells: list[dict[str, Any]] = []
    coordinates: set[tuple[int, int]] = set()
    projected_rows = [list(row) for row in rows]
    for ticker in _EXPECTED_TICKERS:
        row = by_ticker[ticker]
        sec_cik = row.get("sec_cik")
        if not isinstance(sec_cik, str) or not sec_cik.isdigit() or len(sec_cik) != 10:
            raise ValueError(f"reviewed SEC CIK is invalid for {ticker}")
        if sec_cik != _EXPECTED_CIKS[ticker]:
            raise ValueError(f"reviewed ticker-to-CIK mapping mismatch for {ticker}")
        candidates = row.get("future_apply_candidate_fields")
        if not isinstance(candidates, list) or len(candidates) != len(set(candidates)):
            raise ValueError(f"invalid future candidate fields for {ticker}")
        unexpected = sorted(set(candidates) - set(_ALLOWED_FIELDS))
        if unexpected:
            raise ValueError(f"unexpected candidate field: {unexpected[0]}")
        if ticker == "NVDA" and candidates:
            raise ValueError("NVDA must not have changed future candidates")
        if ticker in {"AAPL", "AMD"} and candidates != ["revenue", "filing_dates"]:
            raise ValueError(f"{ticker} must have exactly the reviewed candidate fields")
        fields = row.get("fields")
        if not isinstance(fields, list):
            raise ValueError(f"field evidence is required for {ticker}")
        field_lookup: dict[str, Mapping[str, Any]] = {}
        for field in fields:
            if not isinstance(field, Mapping) or not isinstance(field.get("field"), str):
                raise ValueError(f"invalid field evidence for {ticker}")
            name = field["field"]
            if name in field_lookup:
                raise ValueError(f"duplicate field evidence: {ticker}:{name}")
            field_lookup[name] = field
        if ticker not in canonical_by_ticker:
            raise ValueError(f"canonical ticker row is missing: {ticker}")
        row_index, canonical_row = canonical_by_ticker[ticker]
        for name in candidates:
            field = field_lookup.get(name)
            if field is None:
                raise ValueError(f"candidate field evidence is missing: {ticker}:{name}")
            _validate_field(
                field,
                ticker,
                name,
                sec_cik=sec_cik,
                retrieval_timestamp=retrieval_timestamp,
            )
            column = _ALLOWED_FIELDS[name]
            column_index = header.index(column)
            coordinate = (row_index, column_index)
            if coordinate in coordinates:
                raise ValueError(f"duplicate patch cell: {ticker}:{column}")
            current_value = canonical_row[column_index]
            if not _values_equal(current_value, field.get("canonical_value")):
                raise ValueError(f"canonical precondition mismatch: {ticker}:{column}")
            candidate_value = field.get("candidate_value")
            if _values_equal(current_value, candidate_value):
                raise ValueError(f"changed candidate does not change canonical value: {ticker}:{column}")
            refs = field["source_refs"]
            primary_ref = refs[0]
            provenance_sha256 = _sha256(_json_bytes(refs))
            patch_cells.append(
                {
                    "ticker": ticker,
                    "field": name,
                    "canonical_column": column,
                    "canonical_precondition": field.get("canonical_value"),
                    "candidate_value": candidate_value,
                    "unit": field.get("unit"),
                    "commercial_rights_approved": field.get(
                        "commercial_rights_approved"
                    ),
                    "source_rights_status": field.get("source_rights_status"),
                    "field_scope_status": field.get("field_scope_status"),
                    "schema_status": field.get("schema_status"),
                    "retrieval_timestamp": field.get("retrieval_timestamp"),
                    "source_url": field.get("source_url"),
                    "period_start": primary_ref.get("period_start"),
                    "period_end": primary_ref.get("period_end"),
                    "filing_date": primary_ref.get("filed"),
                    "accession": primary_ref.get("accession"),
                    "concept": primary_ref.get("concept"),
                    "taxonomy": primary_ref.get("taxonomy"),
                    "form": primary_ref.get("form"),
                    "source_refs": refs,
                    "provenance_sha256": provenance_sha256,
                }
            )
            projected_rows[row_index][column_index] = str(candidate_value)
            coordinates.add(coordinate)

    before_untouched = _sha256(_json_bytes(_cell_hash_payload(header, rows, coordinates)))
    after_untouched = _sha256(
        _json_bytes(_cell_hash_payload(header, projected_rows, coordinates))
    )
    if before_untouched != after_untouched:
        raise ValueError("unrelated canonical cells changed in memory")
    touched_row_indexes = {row_index for row_index, _ in coordinates}
    touched_column_indexes = {column_index for _, column_index in coordinates}
    before_untouched_rows = _sha256(
        _json_bytes(
            [
                [row_index, row]
                for row_index, row in enumerate(rows)
                if row_index not in touched_row_indexes
            ]
        )
    )
    after_untouched_rows = _sha256(
        _json_bytes(
            [
                [row_index, row]
                for row_index, row in enumerate(projected_rows)
                if row_index not in touched_row_indexes
            ]
        )
    )
    before_untouched_columns = _sha256(
        _json_bytes(
            [
                [header[column_index], [row[column_index] for row in rows]]
                for column_index in range(len(header))
                if column_index not in touched_column_indexes
            ]
        )
    )
    after_untouched_columns = _sha256(
        _json_bytes(
            [
                [
                    header[column_index],
                    [row[column_index] for row in projected_rows],
                ]
                for column_index in range(len(header))
                if column_index not in touched_column_indexes
            ]
        )
    )
    if before_untouched_rows != after_untouched_rows:
        raise ValueError("unrelated canonical rows changed in memory")
    if before_untouched_columns != after_untouched_columns:
        raise ValueError("unrelated canonical columns changed in memory")
    identity_inputs = {
        "canonical_sha256": canonical_sha256,
        "sec_preview_sha256": sec_preview_sha256,
        "repository_head": repository_head,
        "patch_coordinates": [
            [cell["ticker"], cell["canonical_column"]] for cell in patch_cells
        ],
    }
    return {
        "status": "inspection_only",
        "canonical_apply_authorized": False,
        "repository_writes": [],
        "source_rights_mutated": False,
        "readiness_mutated": False,
        "materialization_performed": False,
        "changed_cell_count": len(patch_cells),
        "patch_cells": patch_cells,
        "preconditions": {
            "canonical_path": canonical_path,
            "canonical_sha256": canonical_sha256,
            "sec_preview_sha256": sec_preview_sha256,
            "repository_head": repository_head,
        },
        "projection_identity": _sha256(_json_bytes(identity_inputs)),
        "in_memory_projection_proof": {
            "column_count_before": len(header),
            "column_count_after": len(header),
            "schema_added_columns": [],
            "schema_removed_columns": [],
            "row_count_before": len(rows),
            "row_count_after": len(rows),
            "row_order_unchanged": True,
            "full_row_replacement": False,
            "staged_input_used": False,
            "untouched_cells_unchanged": True,
            "untouched_cells_sha256_before": before_untouched,
            "untouched_cells_sha256_after": after_untouched,
            "untouched_rows_unchanged": True,
            "untouched_rows_sha256_before": before_untouched_rows,
            "untouched_rows_sha256_after": after_untouched_rows,
            "untouched_columns_unchanged": True,
            "untouched_columns_sha256_before": before_untouched_columns,
            "untouched_columns_sha256_after": after_untouched_columns,
            "projected_semantic_matrix_sha256": _sha256(
                _json_bytes({"header": header, "rows": projected_rows})
            ),
        },
        "next_owner_decision": (
            "Separately authorize or reject only these four hash-bound cells; "
            "regenerate this inspection-only preview if repository, canonical, or SEC evidence bytes drift."
        ),
    }


def render_sec_fundamentals_patch_preview(result: Mapping[str, Any]) -> str:
    return json.dumps(result, indent=2, sort_keys=True, allow_nan=False)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Project a reviewed SEC direct-field patch in memory without writes."
    )
    parser.add_argument("--sec-preview-path", type=Path, required=True)
    parser.add_argument(
        "--canonical-path",
        type=Path,
        default=Path("data/fundamentals.csv"),
    )
    parser.add_argument("--expected-sec-preview-sha256", required=True)
    parser.add_argument("--expected-canonical-sha256", required=True)
    parser.add_argument("--repository-head", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        result = build_sec_fundamentals_patch_preview(
            args.sec_preview_path.read_bytes(),
            args.canonical_path.read_bytes(),
            canonical_path=str(args.canonical_path),
            expected_sec_preview_sha256=args.expected_sec_preview_sha256,
            expected_canonical_sha256=args.expected_canonical_sha256,
            repository_head=args.repository_head,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(render_sec_fundamentals_patch_preview(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
