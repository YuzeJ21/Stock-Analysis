from pathlib import Path

from src.earnings_consensus_sources import consensus_source_statuses, validate_source_rows


def test_source_status_uses_deterministic_order_and_fails_closed_without_keys(tmp_path: Path):
    statuses = consensus_source_statuses(env={}, generic_csv=tmp_path / "missing.csv")

    assert [row.provider for row in statuses] == ["alpha_vantage", "fmp", "finnhub", "reviewed_csv"]
    assert [row.status for row in statuses[:3]] == ["external_key_required"] * 3
    assert statuses[-1].status == "external_data_required"
    assert all(row.auto_apply is False for row in statuses)


def test_current_only_estimate_payload_is_candidate_context_not_history():
    result = validate_source_rows(
        "alpha_vantage",
        [
            {
                "ticker": "NVDA",
                "fiscal_period": "2027-Q1",
                "snapshot_at": "2026-07-18T05:00:00Z",
                "retrieved_at": "2026-07-18T05:00:01Z",
                "source_ref": "provider://alpha/current/NVDA/2027-Q1",
                "revenue_consensus": "1",
                "eps_consensus": "1",
                "history_scope": "current_only",
            }
        ],
        rights_status="research_review_only",
    )

    assert result.accepted_count == 1
    assert result.state == "candidate_context_only"
    assert result.historical_snapshot_count == 0
    assert result.auto_apply is False


def test_historical_rows_require_source_and_comparability_fields():
    result = validate_source_rows(
        "reviewed_csv",
        [{"ticker": "NVDA", "fiscal_period": "2026-Q4", "history_scope": "point_in_time"}],
        rights_status="reviewed_local_evidence",
    )

    assert result.accepted_count == 0
    assert result.rejected_count == 1
    assert "snapshot_at" in result.rejected_rows[0]["reason"]
    assert "revenue_currency" in result.rejected_rows[0]["reason"]


def test_source_rows_reject_invalid_fiscal_period_even_when_fields_are_present():
    row = {
        "ticker": "NVDA",
        "fiscal_period": "next-quarter",
        "snapshot_at": "2026-07-18T05:00:00Z",
        "retrieved_at": "2026-07-18T05:00:01Z",
        "source_ref": "file://reviewed/invalid",
        "history_scope": "point_in_time",
        "revenue_currency": "USD",
        "revenue_unit_scale": "1",
        "revenue_basis": "reported",
        "eps_currency": "USD",
        "eps_basis": "gaap",
        "eps_share_basis": "diluted",
        "eps_operations_basis": "reported",
        "split_adjustment_basis": "as_reported",
        "revenue_consensus": "1",
    }
    result = validate_source_rows("reviewed_csv", [row], rights_status="reviewed_local_evidence")

    assert result.rejected_count == 1
    assert "fiscal_period" in result.rejected_rows[0]["reason"]
