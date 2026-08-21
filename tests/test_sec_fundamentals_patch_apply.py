from __future__ import annotations

import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path

import pytest

from src.sec_fundamentals_patch_apply import (
    apply_sec_fundamentals_patch,
    build_sec_fundamentals_patch_apply,
    main,
    render_sec_fundamentals_patch_apply,
)


_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_HEAD = subprocess.run(
    ["git", "rev-parse", "HEAD"],
    cwd=_REPOSITORY_ROOT,
    check=True,
    capture_output=True,
    text=True,
).stdout.strip()
_SEC_SHA = "3" * 64


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical() -> bytes:
    return (
        "ticker,revenue,sec_filed_date,market_cap,source\n"
        "AMD,5329000000.0,2018-02-27,250000000000,legacy\n"
        "AAPL,265595000000.0,2018-11-05,3000000000000,legacy\n"
        "NVDA,215938000000.0,2026-02-25,4000000000000,reviewed\n"
        "MSFT,100,2025-01-01,999,untouched\n"
    ).encode()


def _source_ref(ticker: str, *, unit: str) -> dict[str, object]:
    cik = {"AAPL": "0000320193", "AMD": "0000002488"}[ticker]
    filed = {"AAPL": "2025-10-31", "AMD": "2026-02-04"}[ticker]
    accession = {
        "AAPL": "0000320193-25-000079",
        "AMD": "0000002488-26-000018",
    }[ticker]
    return {
        "accession": accession,
        "concept": "RevenueFromContractWithCustomerExcludingAssessedTax",
        "filed": filed,
        "fiscal_period": "FY",
        "fiscal_year": 2025,
        "form": "10-K",
        "period_end": "2025-09-27" if ticker == "AAPL" else "2025-12-27",
        "period_start": "2024-09-29" if ticker == "AAPL" else "2024-12-29",
        "retrieval_timestamp": "2026-08-20T18:28:53Z",
        "source_url": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
        "taxonomy": "us-gaap",
        "underlying_fact_unit": "USD" if unit == "date" else None,
        "unit": unit,
    }


def _cell(
    ticker: str,
    field: str,
    column: str,
    before: object,
    after: object,
) -> dict[str, object]:
    unit = "date" if field == "filing_dates" else "USD"
    ref = _source_ref(ticker, unit=unit)
    refs = [ref]
    return {
        "ticker": ticker,
        "field": field,
        "canonical_column": column,
        "canonical_precondition": before,
        "candidate_value": after,
        "unit": unit,
        "commercial_rights_approved": True,
        "source_rights_status": "approved",
        "field_scope_status": "approved",
        "schema_status": "existing_canonical",
        "retrieval_timestamp": "2026-08-20T18:28:53Z",
        "source_url": ref["source_url"],
        "period_start": ref["period_start"],
        "period_end": ref["period_end"],
        "filing_date": ref["filed"],
        "accession": ref["accession"],
        "concept": ref["concept"],
        "taxonomy": ref["taxonomy"],
        "form": ref["form"],
        "source_refs": refs,
        "provenance_sha256": _sha256(
            json.dumps(
                refs,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            ).encode()
        ),
    }


def _packet(
    canonical: bytes | None = None,
    *,
    canonical_path: str = "data/fundamentals.csv",
    repository_head: str = _HEAD,
) -> bytes:
    canonical = canonical or _canonical()
    cells = [
        _cell("AAPL", "revenue", "revenue", 265_595_000_000, 416_161_000_000),
        _cell("AAPL", "filing_dates", "sec_filed_date", "2018-11-05", "2025-10-31"),
        _cell("AMD", "revenue", "revenue", 5_329_000_000, 34_639_000_000),
        _cell("AMD", "filing_dates", "sec_filed_date", "2018-02-27", "2026-02-04"),
    ]
    coordinates = [[cell["ticker"], cell["canonical_column"]] for cell in cells]
    identity = _sha256(
        json.dumps(
            {
                "canonical_sha256": _sha256(canonical),
                "sec_preview_sha256": _SEC_SHA,
                "repository_head": repository_head,
                "patch_coordinates": coordinates,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode()
    )
    packet = {
        "status": "inspection_only",
        "canonical_apply_authorized": False,
        "repository_writes": [],
        "source_rights_mutated": False,
        "readiness_mutated": False,
        "materialization_performed": False,
        "changed_cell_count": 4,
        "patch_cells": cells,
        "preconditions": {
            "canonical_path": canonical_path,
            "canonical_sha256": _sha256(canonical),
            "sec_preview_sha256": _SEC_SHA,
            "repository_head": repository_head,
        },
        "projection_identity": identity,
        "in_memory_projection_proof": {
            "column_count_before": 5,
            "column_count_after": 5,
            "schema_added_columns": [],
            "schema_removed_columns": [],
            "row_count_before": 4,
            "row_count_after": 4,
            "row_order_unchanged": True,
            "full_row_replacement": False,
            "staged_input_used": False,
            "untouched_cells_unchanged": True,
            "untouched_cells_sha256_before": "a" * 64,
            "untouched_cells_sha256_after": "a" * 64,
            "untouched_rows_unchanged": True,
            "untouched_rows_sha256_before": "b" * 64,
            "untouched_rows_sha256_after": "b" * 64,
            "untouched_columns_unchanged": True,
            "untouched_columns_sha256_before": "c" * 64,
            "untouched_columns_sha256_after": "c" * 64,
            "projected_semantic_matrix_sha256": "d" * 64,
        },
        "next_owner_decision": "Separately authorize only these cells.",
    }
    return (json.dumps(packet, indent=2, sort_keys=True) + "\n").encode()


def _build(packet: bytes | None = None, canonical: bytes | None = None, **kwargs):
    canonical = canonical or _canonical()
    canonical_path = kwargs.pop("canonical_path", "data/fundamentals.csv")
    repository_head = kwargs.pop("repository_head", _HEAD)
    repository_root = kwargs.pop("repository_root", _REPOSITORY_ROOT)
    packet = packet or _packet(
        canonical,
        canonical_path=canonical_path,
        repository_head=repository_head,
    )
    return build_sec_fundamentals_patch_apply(
        packet,
        canonical,
        canonical_path=canonical_path,
        expected_patch_preview_sha256=_sha256(packet),
        expected_canonical_sha256=_sha256(canonical),
        repository_head=repository_head,
        repository_root=repository_root,
        authorization_confirmed=True,
        **kwargs,
    )


def test_apply_projection_changes_exactly_four_cells_and_preserves_all_other_bytes():
    result = _build()

    assert result.receipt["applied"] is False
    assert result.receipt["authorization_confirmed"] is True
    assert result.receipt["changed_cell_count"] == 4
    assert result.receipt["repository_writes"] == []
    assert result.receipt["readiness_mutated"] is False
    assert result.receipt["source_rights_mutated"] is False
    assert result.receipt["schema_unchanged"] is True
    assert result.receipt["row_order_unchanged"] is True
    assert result.receipt["untouched_bytes_unchanged"] is True
    assert [
        (cell["ticker"], cell["canonical_column"], cell["before"], cell["after"])
        for cell in result.receipt["changed_cells"]
    ] == [
        ("AAPL", "revenue", "265595000000.0", "416161000000.0"),
        ("AAPL", "sec_filed_date", "2018-11-05", "2025-10-31"),
        ("AMD", "revenue", "5329000000.0", "34639000000.0"),
        ("AMD", "sec_filed_date", "2018-02-27", "2026-02-04"),
    ]

    before_lines = _canonical().splitlines(keepends=True)
    after_lines = result.canonical_csv_bytes.splitlines(keepends=True)
    assert len(before_lines) == len(after_lines)
    assert before_lines[0] == after_lines[0]
    assert before_lines[3:] == after_lines[3:]
    assert after_lines[1] == b"AMD,34639000000.0,2026-02-04,250000000000,legacy\n"
    assert after_lines[2] == b"AAPL,416161000000.0,2025-10-31,3000000000000,legacy\n"


def test_apply_projection_is_deterministic_and_preserves_csv_schema_and_order():
    first = _build()
    second = _build()

    assert first.canonical_csv_bytes == second.canonical_csv_bytes
    assert render_sec_fundamentals_patch_apply(first.receipt) == render_sec_fundamentals_patch_apply(second.receipt)
    before = list(csv.reader(io.StringIO(_canonical().decode())))
    after = list(csv.reader(io.StringIO(first.canonical_csv_bytes.decode())))
    assert before[0] == after[0]
    assert [row[0] for row in before[1:]] == [row[0] for row in after[1:]]
    assert "currency" not in after[0]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda packet: packet.update(changed_cell_count=5), "exactly four"),
        (lambda packet: packet["patch_cells"].append(packet["patch_cells"][0]), "exactly four"),
        (lambda packet: packet["patch_cells"][0].update(ticker="MSFT"), "exact reviewed coordinates"),
        (lambda packet: packet["patch_cells"][0].update(canonical_column="market_cap"), "exact reviewed coordinates"),
        (lambda packet: packet["patch_cells"][0].update(source_rights_status="review_required"), "rights"),
        (lambda packet: packet["patch_cells"][0].update(field_scope_status="review_required"), "field scope"),
        (lambda packet: packet["patch_cells"][0].update(schema_status="candidate_extra"), "schema"),
        (lambda packet: packet["patch_cells"][0].update(provenance_sha256="0" * 64), "provenance"),
        (lambda packet: packet["in_memory_projection_proof"].update(full_row_replacement=True), "projection proof"),
        (lambda packet: packet["in_memory_projection_proof"].update(schema_added_columns=["currency"]), "projection proof"),
        (lambda packet: packet.update(canonical_apply_authorized=True), "inspection-only"),
        (lambda packet: packet.update(repository_writes=["data/fundamentals.csv"]), "inspection-only"),
    ],
)
def test_apply_projection_rejects_any_scope_rights_provenance_or_proof_expansion(mutation, message):
    packet = json.loads(_packet())
    mutation(packet)
    mutated = (json.dumps(packet, indent=2, sort_keys=True) + "\n").encode()

    with pytest.raises(ValueError, match=message):
        _build(packet=mutated)


def test_apply_projection_rejects_missing_authorization_or_any_hash_or_head_drift():
    packet = _packet()
    canonical = _canonical()

    with pytest.raises(ValueError, match="explicit authorization"):
        build_sec_fundamentals_patch_apply(
            packet,
            canonical,
            canonical_path="data/fundamentals.csv",
            expected_patch_preview_sha256=_sha256(packet),
            expected_canonical_sha256=_sha256(canonical),
            repository_head=_HEAD,
            repository_root=_REPOSITORY_ROOT,
            authorization_confirmed=False,
        )
    with pytest.raises(ValueError, match="patch preview hash"):
        build_sec_fundamentals_patch_apply(
            packet,
            canonical,
            canonical_path="data/fundamentals.csv",
            expected_patch_preview_sha256="0" * 64,
            expected_canonical_sha256=_sha256(canonical),
            repository_head=_HEAD,
            repository_root=_REPOSITORY_ROOT,
            authorization_confirmed=True,
        )
    with pytest.raises(ValueError, match="canonical hash"):
        _build(canonical=canonical.replace(b"999,untouched", b"998,untouched"), packet=packet)
    with pytest.raises(ValueError, match="repository HEAD"):
        _build(repository_head="f" * 40)


def test_apply_projection_rejects_caller_asserted_head_that_is_not_live_repository_head():
    stale_head = "f" * 40
    packet = _packet(repository_head=stale_head)

    with pytest.raises(ValueError, match="live repository HEAD"):
        _build(packet=packet, repository_head=stale_head)


def test_apply_projection_and_writer_are_bound_to_one_exact_canonical_path(tmp_path):
    alternate = tmp_path / "fundamentals.csv"
    alternate.write_bytes(_canonical())
    packet = _packet(canonical_path="data/fundamentals.csv")

    with pytest.raises(ValueError, match="canonical path precondition"):
        _build(packet=packet, canonical_path=str(alternate))


def test_apply_writer_rejects_head_drift_between_projection_and_materialization(tmp_path):
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repository, check=True)
    canonical_path = repository / "data" / "fundamentals.csv"
    canonical_path.parent.mkdir()
    canonical_path.write_bytes(_canonical())
    subprocess.run(["git", "add", "data/fundamentals.csv"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=repository, check=True)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    packet = _packet(
        canonical_path="data/fundamentals.csv",
        repository_head=head,
    )
    result = _build(
        packet=packet,
        canonical_path="data/fundamentals.csv",
        repository_head=head,
        repository_root=repository,
    )
    (repository / "drift.txt").write_text("drift", encoding="utf-8")
    subprocess.run(["git", "add", "drift.txt"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "drift"], cwd=repository, check=True)

    with pytest.raises(ValueError, match="HEAD changed before materialization"):
        apply_sec_fundamentals_patch(result)

    assert canonical_path.read_bytes() == _canonical()


def test_apply_projection_rejects_noncanonical_multiline_or_duplicate_ticker_csv():
    duplicate = _canonical().replace(
        b"MSFT,100,2025-01-01,999,untouched\n",
        b"AAPL,100,2025-01-01,999,untouched\n",
    )
    with pytest.raises(ValueError, match="duplicate canonical ticker"):
        _build(canonical=duplicate, packet=_packet(duplicate))

    multiline = _canonical().replace(b"legacy\n", b'"leg\nacy"\n', 1)
    with pytest.raises(ValueError, match="one physical line"):
        _build(canonical=multiline, packet=_packet(multiline))


def test_apply_function_writes_only_named_canonical_path_and_returns_auditable_receipt(tmp_path):
    canonical_path = tmp_path / "fundamentals.csv"
    canonical_path.write_bytes(_canonical())
    other = tmp_path / "keep.txt"
    other.write_text("keep", encoding="utf-8")
    result = _build(
        packet=_packet(canonical_path=str(canonical_path)),
        canonical_path=str(canonical_path),
    )

    receipt = apply_sec_fundamentals_patch(result)

    assert canonical_path.read_bytes() == result.canonical_csv_bytes
    assert other.read_text(encoding="utf-8") == "keep"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["fundamentals.csv", "keep.txt"]
    assert receipt["applied"] is True
    assert receipt["repository_writes"] == [str(canonical_path)]
    assert receipt["canonical_sha256_before"] == _sha256(_canonical())
    assert receipt["canonical_sha256_after"] == _sha256(result.canonical_csv_bytes)
    assert result.canonical_path == canonical_path.resolve()


def test_cli_requires_exact_confirmation_and_second_apply_fails_stale_hash(tmp_path, capsys):
    packet_path = tmp_path / "patch.json"
    canonical_path = tmp_path / "fundamentals.csv"
    packet = _packet(canonical_path=str(canonical_path))
    packet_path.write_bytes(packet)
    canonical_path.write_bytes(_canonical())
    arguments = [
        "--patch-preview-path",
        str(packet_path),
        "--canonical-path",
        str(canonical_path),
        "--expected-patch-preview-sha256",
        _sha256(packet),
        "--expected-canonical-sha256",
        _sha256(_canonical()),
        "--repository-head",
        _HEAD,
        "--authorize-exact-four-cell-apply",
    ]

    assert main(arguments) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["applied"] is True
    assert receipt["changed_cell_count"] == 4
    with pytest.raises(SystemExit):
        main(arguments)


def test_apply_receipt_contains_no_readiness_or_provider_materialization():
    text = render_sec_fundamentals_patch_apply(_build().receipt).lower()

    assert '"readiness_mutated": false' in text
    assert '"source_rights_mutated": false' in text
    for forbidden in ("yfinance", "yahoo", "stooq", "fmp_api_key", "alpha_vantage", "finnhub"):
        assert forbidden not in text
