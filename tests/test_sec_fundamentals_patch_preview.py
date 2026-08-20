from __future__ import annotations

import csv
import hashlib
import io
import json

import pytest

from src.sec_fundamentals_patch_preview import (
    build_sec_fundamentals_patch_preview,
    main,
    render_sec_fundamentals_patch_preview,
)


_REPOSITORY_HEAD = "08fa35efb2759ca86785b1c2c95bc5cbfae4a9f4"


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _coherently_replace_aapl_cik_with_amd(packet: dict[str, object]) -> None:
    row = packet["tickers"][0]
    row["sec_cik"] = "0000002488"
    source_url = "https://data.sec.gov/api/xbrl/companyfacts/CIK0000002488.json"
    for field in row["fields"]:
        field["sec_cik"] = "0000002488"
        field["source_url"] = source_url
        for ref in field["source_refs"]:
            ref["source_url"] = source_url


def _field(
    ticker: str,
    field: str,
    canonical_column: str,
    canonical_value: object,
    candidate_value: object,
    *,
    value_status: str = "changed",
) -> dict[str, object]:
    cik = {"AAPL": "0000320193", "NVDA": "0001045810", "AMD": "0000002488"}[ticker]
    accession = {
        "AAPL": "0000320193-25-000079",
        "NVDA": "0001045810-26-000021",
        "AMD": "0000002488-26-000018",
    }[ticker]
    filing_date = {"AAPL": "2025-10-31", "NVDA": "2026-02-25", "AMD": "2026-02-04"}[ticker]
    unit = "date" if field == "filing_dates" else "USD"
    return {
        "ticker": ticker,
        "sec_cik": cik,
        "field": field,
        "canonical_column": canonical_column,
        "canonical_value": canonical_value,
        "candidate_value": candidate_value,
        "classification": "approved_direct",
        "commercial_rights_approved": True,
        "field_scope_status": "approved",
        "schema_status": "existing_canonical",
        "publishability_blocker": "none",
        "value_kind": "direct",
        "value_status": value_status,
        "unit": unit,
        "source_units": [unit],
        "source_rights_status": "approved",
        "retrieval_timestamp": "2026-08-20T18:28:53Z",
        "source_url": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
        "source_refs": [
            {
                "accession": accession,
                "concept": "RevenueFromContractWithCustomerExcludingAssessedTax",
                "filed": filing_date,
                "fiscal_period": "FY",
                "fiscal_year": 2025,
                "form": "10-K",
                "period_end": "2025-12-27" if ticker == "AMD" else "2025-09-27",
                "period_start": "2024-12-29" if ticker == "AMD" else "2024-09-29",
                "retrieval_timestamp": "2026-08-20T18:28:53Z",
                "source_url": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
                "taxonomy": "us-gaap",
                "underlying_fact_unit": "USD" if field == "filing_dates" else None,
                "unit": unit,
            }
        ],
    }


def _sec_packet() -> bytes:
    rows = [
        {
            "ticker": "AAPL",
            "sec_cik": "0000320193",
            "future_apply_candidate_fields": ["revenue", "filing_dates"],
            "fields": [
                _field("AAPL", "revenue", "revenue", 265_595_000_000, 416_161_000_000),
                _field("AAPL", "filing_dates", "sec_filed_date", "2018-11-05", "2025-10-31"),
            ],
        },
        {
            "ticker": "NVDA",
            "sec_cik": "0001045810",
            "future_apply_candidate_fields": [],
            "fields": [
                _field(
                    "NVDA",
                    "revenue",
                    "revenue",
                    215_938_000_000,
                    215_938_000_000,
                    value_status="unchanged",
                ),
                _field(
                    "NVDA",
                    "filing_dates",
                    "sec_filed_date",
                    "2026-02-25",
                    "2026-02-25",
                    value_status="unchanged",
                ),
            ],
        },
        {
            "ticker": "AMD",
            "sec_cik": "0000002488",
            "future_apply_candidate_fields": ["revenue", "filing_dates"],
            "fields": [
                _field("AMD", "revenue", "revenue", 5_329_000_000, 34_639_000_000),
                _field("AMD", "filing_dates", "sec_filed_date", "2018-02-27", "2026-02-04"),
            ],
        },
    ]
    packet = {
        "status": "inspection_only",
        "source": "sec_companyfacts",
        "source_rights_mutated": False,
        "canonical_apply_authorized": False,
        "repository_writes": [],
        "requested_tickers": ["AAPL", "NVDA", "AMD"],
        "retrieval_timestamp": "2026-08-20T18:28:53Z",
        "schema_delta": {
            "staged_extra_columns": ["currency"],
            "canonical_columns_not_produced": ["market_cap"],
            "full_row_rewrite_risk": True,
        },
        "tickers": rows,
    }
    return (json.dumps(packet, indent=2, sort_keys=True) + "\n").encode()


def _canonical() -> bytes:
    return (
        "ticker,revenue,sec_filed_date,market_cap,source\n"
        "AAPL,265595000000,2018-11-05,3000000000000,legacy\n"
        "NVDA,215938000000,2026-02-25,4000000000000,reviewed\n"
        "AMD,5329000000,2018-02-27,250000000000,legacy\n"
        "MSFT,100,2025-01-01,999,untouched\n"
    ).encode()


def _build(sec_packet: bytes | None = None, canonical: bytes | None = None, **kwargs):
    sec_packet = sec_packet or _sec_packet()
    canonical = canonical or _canonical()
    return build_sec_fundamentals_patch_preview(
        sec_packet,
        canonical,
        canonical_path="data/fundamentals.csv",
        expected_sec_preview_sha256=_sha256(sec_packet),
        expected_canonical_sha256=_sha256(canonical),
        repository_head=_REPOSITORY_HEAD,
        **kwargs,
    )


def test_patch_preview_selects_only_four_reviewed_changed_cells():
    result = _build()

    assert [(cell["ticker"], cell["field"]) for cell in result["patch_cells"]] == [
        ("AAPL", "revenue"),
        ("AAPL", "filing_dates"),
        ("AMD", "revenue"),
        ("AMD", "filing_dates"),
    ]
    assert result["changed_cell_count"] == 4
    assert result["status"] == "inspection_only"
    assert result["canonical_apply_authorized"] is False
    assert result["repository_writes"] == []
    assert result["preconditions"]["repository_head"] == _REPOSITORY_HEAD
    assert result["next_owner_decision"].startswith("Separately authorize or reject")
    for cell in result["patch_cells"]:
        assert cell["commercial_rights_approved"] is True
        assert cell["source_rights_status"] == "approved"
        assert cell["field_scope_status"] == "approved"
        assert cell["schema_status"] == "existing_canonical"


def test_patch_preview_proves_schema_rows_order_and_unrelated_cells_unchanged():
    result = _build()
    proof = result["in_memory_projection_proof"]

    assert proof == {
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
        "untouched_cells_sha256_before": proof["untouched_cells_sha256_after"],
        "untouched_cells_sha256_after": proof["untouched_cells_sha256_after"],
        "untouched_rows_unchanged": True,
        "untouched_rows_sha256_before": proof["untouched_rows_sha256_after"],
        "untouched_rows_sha256_after": proof["untouched_rows_sha256_after"],
        "untouched_columns_unchanged": True,
        "untouched_columns_sha256_before": proof["untouched_columns_sha256_after"],
        "untouched_columns_sha256_after": proof["untouched_columns_sha256_after"],
        "projected_semantic_matrix_sha256": proof["projected_semantic_matrix_sha256"],
    }


def test_patch_preview_binds_canonical_and_sec_packet_bytes_and_is_deterministic():
    first = _build()
    second = _build()

    assert len(first["preconditions"]["canonical_sha256"]) == 64
    assert len(first["preconditions"]["sec_preview_sha256"]) == 64
    assert len(first["projection_identity"]) == 64
    assert render_sec_fundamentals_patch_preview(first) == render_sec_fundamentals_patch_preview(second)

    semantically_equal_bytes = _sec_packet().replace(b"{\n", b"{ \n", 1)
    with pytest.raises(ValueError, match="SEC preview hash precondition"):
        build_sec_fundamentals_patch_preview(
            semantically_equal_bytes,
            _canonical(),
            canonical_path="data/fundamentals.csv",
            expected_sec_preview_sha256=_sha256(_sec_packet()),
            expected_canonical_sha256=_sha256(_canonical()),
            repository_head=_REPOSITORY_HEAD,
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda packet: packet.update(status="ready"), "inspection_only"),
        (lambda packet: packet.update(canonical_apply_authorized=True), "apply authorization"),
        (
            lambda packet: packet["tickers"][0]["future_apply_candidate_fields"].append("shares_outstanding"),
            "unexpected candidate field",
        ),
        (
            lambda packet: packet["tickers"][0]["fields"][0].update(field_scope_status="review_required"),
            "approved field scope",
        ),
        (
            lambda packet: packet["tickers"][0]["fields"][0]["source_refs"][0].update(
                source_url="https://query1.finance.yahoo.com/x"
            ),
            "official SEC",
        ),
        (
            lambda packet: packet["tickers"][0]["fields"][0]["source_refs"][0].update(
                source_url="https://data.sec.gov/api/xbrl/companyfacts/CIK0000002488.json"
            ),
            "reviewed SEC CIK",
        ),
        (
            lambda packet: packet["tickers"][0]["fields"][0]["source_refs"][0].update(
                retrieval_timestamp="2026-08-20T18:28:54Z"
            ),
            "retrieval timestamp",
        ),
        (
            lambda packet: packet["tickers"][0]["fields"][0].update(
                unit="shares", source_units=["shares"]
            ),
            "USD units",
        ),
        (_coherently_replace_aapl_cik_with_amd, "ticker-to-CIK"),
    ],
)
def test_patch_preview_fails_closed_for_unreviewed_or_untrusted_evidence(mutation, message):
    packet = json.loads(_sec_packet())
    mutation(packet)

    with pytest.raises(ValueError, match=message):
        mutated = (json.dumps(packet, sort_keys=True) + "\n").encode()
        _build(sec_packet=mutated)


def test_patch_preview_rejects_stale_canonical_preconditions():
    canonical = _canonical().replace(b"265595000000", b"265595000001")

    with pytest.raises(ValueError, match="canonical hash precondition"):
        build_sec_fundamentals_patch_preview(
            _sec_packet(),
            canonical,
            canonical_path="data/fundamentals.csv",
            expected_sec_preview_sha256=_sha256(_sec_packet()),
            expected_canonical_sha256=_sha256(_canonical()),
            repository_head=_REPOSITORY_HEAD,
        )


def test_patch_preview_rejects_duplicate_ticker_rows_and_schema_expansion():
    packet = json.loads(_sec_packet())
    packet["tickers"].append(packet["tickers"][0])
    with pytest.raises(ValueError, match="duplicate ticker"):
        _build(sec_packet=(json.dumps(packet, sort_keys=True) + "\n").encode())

    canonical = _canonical().replace(b"source\n", b"source,currency\n")
    with pytest.raises(ValueError, match="canonical row width"):
        _build(canonical=canonical)


def test_patch_preview_does_not_write_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = _build()

    assert result["repository_writes"] == []
    assert list(tmp_path.iterdir()) == []


def test_canonical_fixture_is_well_formed():
    rows = list(csv.DictReader(io.StringIO(_canonical().decode())))
    assert [row["ticker"] for row in rows] == ["AAPL", "NVDA", "AMD", "MSFT"]


def test_cli_reads_exact_inputs_and_writes_only_json_to_stdout(tmp_path, capsys):
    sec_path = tmp_path / "sec-preview.json"
    canonical_path = tmp_path / "fundamentals.csv"
    sec_path.write_bytes(_sec_packet())
    canonical_path.write_bytes(_canonical())
    before = sorted(path.name for path in tmp_path.iterdir())

    assert main(
        [
            "--sec-preview-path",
            str(sec_path),
            "--canonical-path",
            str(canonical_path),
            "--expected-sec-preview-sha256",
            _sha256(_sec_packet()),
            "--expected-canonical-sha256",
            _sha256(_canonical()),
            "--repository-head",
            _REPOSITORY_HEAD,
        ]
    ) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["changed_cell_count"] == 4
    assert output["preconditions"]["canonical_path"] == str(canonical_path)
    assert sorted(path.name for path in tmp_path.iterdir()) == before
