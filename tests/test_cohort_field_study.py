"""Behavioral checks for the bounded, inspection-only six-company study."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from src.cohort_field_evidence import DEFAULT_TICKERS, FIELDS, SCHEMA_VERSION
from src.cohort_field_study import (
    load_bounded_field_study,
    study_company_html,
    study_company_detail_html,
    study_discover_html,
    study_monitor_html,
)


def _report(as_of: str = "2026-10-26", digest: str = "a" * 64) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "as_of": as_of,
        "tickers": list(DEFAULT_TICKERS),
        "snapshot_identity": digest,
        "fields": [
            {
                "ticker": ticker, "field": field, "value": "",
                "source": "", "source_ref": "", "period_end": "",
                "source_published_at": "", "observation_date": "",
                "observation_date_basis": "saved_row_updated_at",
                "rights_status": "source_unidentified", "registered_field_scope": False,
                "withheld_reasons": ["saved_field_missing"],
                "interpretation_state": "withheld",
            }
            for ticker in DEFAULT_TICKERS for field in FIELDS
        ],
        "readiness_snapshot": {ticker: {} for ticker in DEFAULT_TICKERS},
        "inspection_only": True,
        "canonical_writes": False,
    }


def _save_pair(root: Path, prior: dict, current: dict) -> None:
    saved = root / "outputs" / "local"
    saved.mkdir(parents=True, exist_ok=True)
    (saved / "cohort_field_evidence_2026-10-26.json").write_text(json.dumps(prior))
    (saved / "cohort_field_evidence_2026-10-27.json").write_text(json.dumps(current))


def test_real_shape_study_links_all_six_and_keeps_qcom_blocked(tmp_path: Path):
    prior = _report()
    current = _report(as_of="2026-10-27")
    _save_pair(tmp_path, prior, current)

    study = load_bounded_field_study(tmp_path, profile_key="default", data_dir=tmp_path / "data")
    discover = study_discover_html(study)
    company = study_company_html(study, "QCOM")
    monitor = study_monitor_html(study)

    assert study.status == "unchanged"
    assert study.field_count == 54
    assert study.withheld_count == 54
    assert study.same_input_digest is True
    for ticker in DEFAULT_TICKERS:
        assert f"ticker={ticker}" in discover
    assert "QCOM" in discover and "blocked" in discover.lower()
    assert company.count("No saved value") == 9
    assert "Evidence review blocked" in company
    assert "No saved period" in company
    assert "saved_field_missing" not in company
    assert "No field difference" in monitor
    assert "same underlying inputs" in monitor
    assert "source-backed change" not in monitor


def test_other_profile_and_missing_or_malformed_saved_pair_fail_closed(tmp_path: Path):
    prior = _report()
    current = _report(as_of="2026-10-27")
    _save_pair(tmp_path, prior, current)

    other = load_bounded_field_study(tmp_path, profile_key="demo", data_dir=tmp_path / "data" / "demo")
    assert other.status == "unavailable"
    assert "QCOM" not in study_discover_html(other)
    assert "Unavailable" in study_company_html(other, "QCOM")
    assert study_company_html(other, "AAPL") == ""

    wrong_directory = load_bounded_field_study(tmp_path, profile_key="default", data_dir=tmp_path / "data" / "demo")
    assert wrong_directory.status == "unavailable"

    current["fields"].append(deepcopy(current["fields"][0]))
    _save_pair(tmp_path, prior, current)
    invalid = load_bounded_field_study(tmp_path, profile_key="default", data_dir=tmp_path / "data")
    assert invalid.status == "unavailable"
    assert invalid.field_count == 0
    assert "Unavailable" in study_monitor_html(invalid)

    current = _report(as_of="2026-10-27")
    current["fields"][0]["ticker"] = []
    _save_pair(tmp_path, prior, current)
    malformed_identity = load_bounded_field_study(tmp_path, profile_key="default", data_dir=tmp_path / "data")
    assert malformed_identity.status == "unavailable"

    (tmp_path / "outputs" / "local" / "cohort_field_evidence_2026-10-27.json").unlink()
    missing = load_bounded_field_study(tmp_path, profile_key="default", data_dir=tmp_path / "data")
    assert missing.status == "unavailable"
    assert "QCOM" not in study_discover_html(missing)


def test_study_comparison_names_field_dimensions_without_monitor_events(tmp_path: Path):
    prior = _report()
    current = _report(as_of="2026-10-27", digest="b" * 64)
    prior_row = next(row for row in prior["fields"] if row["ticker"] == "NVDA" and row["field"] == "revenue")
    current_row = next(row for row in current["fields"] if row["ticker"] == "NVDA" and row["field"] == "revenue")
    prior_row["value"] = "100"
    current_row.update({
        "value": "101", "period_end": "2026-04-26",
        "source_ref": "0001045810-26-012345",
        "observation_date_basis": "source_response_timestamp",
        "withheld_reasons": ["field_specific_proof_missing"],
    })
    _save_pair(tmp_path, prior, current)

    study = load_bounded_field_study(tmp_path, profile_key="default", data_dir=tmp_path / "data")
    company = study_company_html(study, "NVDA")
    monitor = study_monitor_html(study)

    assert study.status == "changed"
    assert "Value" in company and "100" in company and "101" in company
    assert "Period end" in company and "2026-04-26" in company
    assert "Observation date basis" in company
    assert "Source response timestamp" in company
    assert "Saved row updated at" in company
    assert "Reasons withheld" in company
    assert "field_specific_proof_missing" not in company
    assert "0001045810-26-012345" not in company
    assert "Source reference" in company
    assert "0001045810-26-012345" in study_company_detail_html(study, "NVDA")
    assert "field_specific_proof_missing" in study_company_detail_html(study, "NVDA")
    assert "NVDA" in monitor and "1 field difference" in monitor
    assert "inspection only" in monitor.lower()


def test_saved_real_pair_has_same_digest_and_all_interpretations_withheld():
    root = Path(__file__).resolve().parent.parent
    if not all((root / "outputs" / "local" / name).is_file() for name in (
        "cohort_field_evidence_2026-10-26.json", "cohort_field_evidence_2026-10-27.json",
    )):
        pytest.skip("ignored local receipts are not present in this checkout")
    study = load_bounded_field_study(root, profile_key="default", data_dir=root / "data")

    assert study.status == "unchanged"
    assert study.same_input_digest is True
    assert study.field_count == 54
    assert study.withheld_count == 54
    assert len(study.snapshot_identity) == 64
