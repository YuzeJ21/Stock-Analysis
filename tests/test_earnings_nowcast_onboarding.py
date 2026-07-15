from __future__ import annotations

import csv
import json
from pathlib import Path

from src.earnings_nowcast_onboarding import (
    onboarding_readiness,
    preview_onboarding,
    validate_onboarding,
    write_templates,
)


ACTUAL = {
    "ticker": "SYNX",
    "fiscal_period": "2025-Q4",
    "period_end_date": "2025-12-31",
    "reported_at": "2026-01-20T21:00:00Z",
    "revenue_actual": "100",
    "eps_actual": "1.25",
    "source": "reviewed_source",
    "source_ref": "https://example.test/filing",
    "retrieved_at": "2026-01-20T22:00:00Z",
}

CONSENSUS = {
    "ticker": "SYNX",
    "fiscal_period": "2026-Q1",
    "snapshot_at": "2026-01-25T12:00:00Z",
    "revenue_consensus": "110",
    "eps_consensus": "1.30",
    "source": "licensed_snapshot_source",
    "source_ref": "provider://snapshot/123",
    "retrieved_at": "2026-01-25T12:01:00Z",
}

SIGNAL = {
    "signal_id": "signal-1",
    "target_ticker": "SYNX",
    "source_ticker": "SYNY",
    "fiscal_period": "2026-Q1",
    "as_of_timestamp": "2026-01-31T23:59:59Z",
    "signal_type": "peer_earnings_readthrough",
    "direction": "positive",
    "affected_metric": "revenue",
    "confidence_band": "medium",
    "evidence_source": "reviewed_source",
    "evidence_source_ref": "https://example.test/evidence",
    "evidence_published_at": "2026-01-20T12:00:00Z",
    "evidence_excerpt_hash": "a" * 64,
    "peer_relationship_state": "candidate",
    "review_state": "candidate_context_only",
}


def _write(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _input_dir(tmp_path: Path) -> Path:
    root = tmp_path / "incoming"
    _write(root / "quarterly_actuals.csv", [ACTUAL])
    _write(root / "consensus_snapshots.csv", [CONSENSUS])
    return root


def test_templates_include_provenance_and_create_no_apply_artifact(tmp_path):
    written = write_templates(tmp_path / "templates")

    assert {path.name for path in written} == {
        "quarterly_actuals.csv",
        "consensus_snapshots.csv",
        "signals.csv",
    }
    assert "source_ref" in (tmp_path / "templates" / "consensus_snapshots.csv").read_text()
    assert "evidence_source_ref" in (tmp_path / "templates" / "signals.csv").read_text()
    assert not (tmp_path / "templates" / "apply.json").exists()


def test_validation_accepts_source_backed_rows_without_writing_reports(tmp_path):
    input_dir = _input_dir(tmp_path)

    result = validate_onboarding(input_dir, cutoff="2026-01-31T23:59:59Z")

    assert result["valid"] is True
    assert result["accepted_count"] == 2
    assert result["rejected_rows"] == []
    consensus_value = next(
        item["value"] for item in result["accepted_rows"] if item["file"] == "consensus_snapshots.csv"
    )
    assert consensus_value.source_ref == CONSENSUS["source_ref"]
    assert list(input_dir.iterdir()) == [
        input_dir / "quarterly_actuals.csv",
        input_dir / "consensus_snapshots.csv",
    ]


def test_validation_rejects_missing_source_reference_and_post_cutoff_rows(tmp_path):
    input_dir = _input_dir(tmp_path)
    bad = dict(CONSENSUS, source_ref="", snapshot_at="2026-02-01T12:00:00Z")
    _write(input_dir / "consensus_snapshots.csv", [bad])

    result = validate_onboarding(input_dir, cutoff="2026-01-31T23:59:59Z")

    assert result["valid"] is False
    assert result["accepted_count"] == 1
    assert result["rejected_count"] == 1
    assert "source_ref is required" in result["rejected_rows"][0]["reasons"]
    assert "after forecast cutoff" in result["rejected_rows"][0]["reasons"]


def test_preview_separates_exact_duplicates_from_append_only_revisions(tmp_path):
    input_dir = _input_dir(tmp_path)
    existing = tmp_path / "existing"
    _write(existing / "quarterly_actuals.csv", [ACTUAL])
    _write(existing / "consensus_snapshots.csv", [CONSENSUS])
    revision = dict(CONSENSUS, revenue_consensus="111", retrieved_at="2026-01-26T12:01:00Z")
    _write(input_dir / "consensus_snapshots.csv", [revision])

    result = preview_onboarding(
        input_dir,
        existing_dir=existing,
        cutoff="2026-01-31T23:59:59Z",
    )

    assert result["apply_performed"] is False
    assert result["duplicate_count"] == 1
    assert result["revision_count"] == 1
    assert result["new_count"] == 0
    assert result["revision_rows"][0]["revision_of"]["source_ref"] == CONSENSUS["source_ref"]
    assert json.loads(json.dumps(result))["valid"] is True


def test_signal_onboarding_preserves_evidence_reference(tmp_path):
    input_dir = _input_dir(tmp_path)
    _write(input_dir / "signals.csv", [SIGNAL])

    result = validate_onboarding(input_dir, cutoff="2026-01-31T23:59:59Z")
    signal = next(item["value"] for item in result["accepted_rows"] if item["file"] == "signals.csv")

    assert result["valid"] is True
    assert signal.evidence_source_ref == SIGNAL["evidence_source_ref"]


def test_validation_fails_closed_when_required_input_files_are_absent(tmp_path):
    result = validate_onboarding(tmp_path / "missing", cutoff="2026-01-31T23:59:59Z")

    assert result["valid"] is False
    assert result["accepted_count"] == 0
    assert result["rejected_count"] == 2
    assert {row["file"] for row in result["rejected_rows"]} == {
        "quarterly_actuals.csv",
        "consensus_snapshots.csv",
    }


def test_readiness_fails_closed_when_any_onboarding_row_is_rejected(tmp_path):
    input_dir = _input_dir(tmp_path)
    _write(input_dir / "signals.csv", [dict(SIGNAL, evidence_source_ref="")])

    result = onboarding_readiness(
        input_dir,
        ticker="SYNX",
        cutoff="2026-01-31T23:59:59Z",
    )

    assert result["state"] == "blocked"
    assert result["missing_evidence"] == ["invalid_onboarding_rows"]
    assert result["validation"]["rejected_count"] == 1
