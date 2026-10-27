import csv
import shutil

from src.commercial_source_rights import DEFAULT_REGISTRY_PATH

from src.cohort_field_evidence import build_report, compare_reports


def _write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


def _rights(tmp_path):
    destination = tmp_path / "config" / "source_rights.yml"
    destination.parent.mkdir(parents=True)
    shutil.copyfile(DEFAULT_REGISTRY_PATH, destination)


def test_report_keeps_rights_period_and_field_proof_independent(tmp_path):
    _rights(tmp_path)
    _write(tmp_path / "data" / "fundamentals.csv", [{
        "ticker": "NVDA", "revenue": "100", "free_cash_flow": "40", "source": "sec_companyfacts",
        "as_of_date": "2026-01-25", "sec_filed_date": "2026-02-25",
        "sec_accession": "0001045810-26-000021", "updated_at": "2026-03-01T00:00:00Z",
    }])
    _write(tmp_path / "data" / "prices.csv", [{"ticker": "NVDA", "date": "2026-05-22", "close": "100"}])
    _write(tmp_path / "data" / "reports" / "ticker_readiness_report.csv", [{
        "ticker": "NVDA", "price_ready": "True", "fundamentals_ready": "True", "updated_at": "2026-06-07"
    }])
    report = build_report(tmp_path, tickers=("NVDA", "QCOM"), as_of="2026-10-26")
    rows = {(x["ticker"], x["field"]): x for x in report["fields"]}
    revenue = rows["NVDA", "revenue"]
    assert revenue["value"] == "100"
    assert revenue["source_ref"] == "0001045810-26-000021"
    assert revenue["period_end"] == "2026-01-25"
    assert revenue["observation_date"] == "2026-03-01T00:00:00Z"
    assert revenue["rights_status"] == "approved"
    assert revenue["registered_field_scope"] is True
    assert "field_specific_proof_missing" in revenue["withheld_reasons"]
    assert "stale_observation" in revenue["withheld_reasons"]
    assert "field_not_registered" in rows["NVDA", "free_cash_flow"]["withheld_reasons"]
    assert "price_source_missing" in rows["NVDA", "latest_close"]["withheld_reasons"]
    assert rows["QCOM", "revenue"]["withheld_reasons"] == ["saved_field_missing"]
    assert report["readiness_snapshot"]["NVDA"]["fundamentals_ready"] == "True"
    assert report["inspection_only"] is True


def test_comparison_reports_real_changes_and_rejects_mismatched_scope(tmp_path):
    _rights(tmp_path)
    _write(tmp_path / "data" / "fundamentals.csv", [{"ticker": "NVDA", "revenue": "100", "source": "sec_companyfacts"}])
    before = build_report(tmp_path, tickers=("NVDA",), as_of="2026-10-26")
    _write(tmp_path / "data" / "fundamentals.csv", [{"ticker": "NVDA", "revenue": "101", "source": "sec_companyfacts"}])
    after = build_report(tmp_path, tickers=("NVDA",), as_of="2026-10-26")
    comparison = compare_reports(before, after)
    assert comparison["status"] == "changed"
    assert any(row["field"] == "revenue" and row["prior_value"] == "100" and row["current_value"] == "101" for row in comparison["changes"])
    assert compare_reports(before, before)["status"] == "unchanged"
    after["tickers"] = ["OTHER"]
    assert compare_reports(before, after)["status"] == "incompatible_scope"


def test_missing_rights_registry_never_inherits_another_workspace_approval(tmp_path):
    _write(tmp_path / "data" / "fundamentals.csv", [{
        "ticker": "NVDA", "revenue": "100", "source": "sec_companyfacts", "sec_accession": "example",
    }])
    report = build_report(tmp_path, tickers=("NVDA",), as_of="2026-10-26")
    revenue = next(row for row in report["fields"] if row["field"] == "revenue")
    assert revenue["registered_field_scope"] is False
    assert "source_rights_unverified" in revenue["withheld_reasons"]


def test_comparison_names_changed_evidence_dimensions_without_promoting_interpretation(tmp_path):
    _rights(tmp_path)
    _write(tmp_path / "data" / "fundamentals.csv", [{
        "ticker": "NVDA", "revenue": "100", "source": "sec_companyfacts",
        "sec_accession": "0001045810-26-000021", "as_of_date": "2026-01-25",
        "sec_filed_date": "2026-02-25",
    }])
    before = build_report(tmp_path, tickers=("NVDA",), as_of="2026-10-26")
    after = __import__("copy").deepcopy(before)
    after["snapshot_identity"] = "b" * 64
    row = next(item for item in after["fields"] if item["field"] == "revenue")
    row.update({
        "value": "101", "source_ref": "0001045810-26-000052",
        "period_end": "2026-04-26", "source_published_at": "2026-05-27",
        "rights_status": "review_required", "withheld_reasons": ["rights_review_required"],
    })

    result = compare_reports(before, after)

    assert result["status"] == "changed"
    change = next(item for item in result["changes"] if item["field"] == "revenue")
    assert change["changed_dimensions"] == [
        "value", "source_ref", "period_end", "source_published_at",
        "rights_status", "withheld_reasons",
    ]
    assert change["before"]["period_end"] == "2026-01-25"
    assert change["after"]["period_end"] == "2026-04-26"
    assert change["before"]["rights_status"] == "approved"
    assert change["after"]["rights_status"] == "review_required"
    assert change["current_value"] == "101"
    assert result["inspection_only"] is True


def test_same_input_review_date_aging_is_not_source_change(tmp_path):
    _rights(tmp_path)
    _write(tmp_path / "data" / "fundamentals.csv", [{
        "ticker": "NVDA", "revenue": "100", "source": "sec_companyfacts",
        "sec_accession": "0001045810-26-000021", "as_of_date": "2026-08-01",
        "sec_filed_date": "2026-08-02", "updated_at": "2026-08-02",
    }])
    before = build_report(tmp_path, tickers=("NVDA",), as_of="2026-10-28")
    after = build_report(tmp_path, tickers=("NVDA",), as_of="2026-11-02")

    result = compare_reports(before, after)

    assert before["snapshot_identity"] == after["snapshot_identity"]
    assert result["status"] == "review_date_reevaluation"
    assert result["input_changes"] == []
    assert result["changes"][0]["changed_dimensions"] == ["withheld_reasons"]


def test_same_input_digest_cannot_hide_rights_or_proof_change_as_aging(tmp_path):
    _rights(tmp_path)
    before = build_report(tmp_path, tickers=("NVDA",), as_of="2026-10-26")
    after = __import__("copy").deepcopy(before)
    after["as_of"] = "2026-10-27"
    after["fields"][0]["withheld_reasons"] = ["field_specific_proof_missing"]

    assert compare_reports(before, after)["status"] == "incompatible_scope"


def test_observation_date_basis_is_a_provenance_change(tmp_path):
    _rights(tmp_path)
    before = build_report(tmp_path, tickers=("NVDA",), as_of="2026-10-26")
    after = __import__("copy").deepcopy(before)
    after["snapshot_identity"] = "b" * 64
    after["fields"][0]["observation_date_basis"] = "source_response_timestamp"

    result = compare_reports(before, after)

    assert result["status"] == "changed"
    assert result["changes"][0]["changed_dimensions"] == ["observation_date_basis"]
    assert result["changes"][0]["before"]["observation_date_basis"] == "saved_row_updated_at"
    assert result["changes"][0]["after"]["observation_date_basis"] == "source_response_timestamp"

    after["snapshot_identity"] = before["snapshot_identity"]
    assert compare_reports(before, after)["status"] == "incompatible_scope"


def test_comparison_rejects_duplicate_or_malformed_field_rows(tmp_path):
    _rights(tmp_path)
    before = build_report(tmp_path, tickers=("NVDA",), as_of="2026-10-26")
    duplicate = __import__("copy").deepcopy(before)
    duplicate["fields"].append(duplicate["fields"][0].copy())
    malformed = __import__("copy").deepcopy(before)
    del malformed["fields"][0]["withheld_reasons"]
    bad_ticker = __import__("copy").deepcopy(before)
    bad_ticker["fields"][0]["ticker"] = []

    assert compare_reports(before, duplicate)["status"] == "incompatible_scope"
    assert compare_reports(before, malformed)["status"] == "incompatible_scope"
    assert compare_reports(before, bad_ticker)["status"] == "incompatible_scope"
