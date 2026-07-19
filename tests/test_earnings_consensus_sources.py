from pathlib import Path

import pytest

from src.commercial_source_rights import build_source_rights_registry
from src.earnings_consensus_sources import consensus_source_statuses, validate_source_rows


REVIEW_CUTOFF = "2026-07-18T06:00:00Z"


def _rights_registry(
    *,
    source_id: str = "licensed_consensus",
    commercial_use: str = "approved",
    supported_fields: tuple[str, ...] | None = None,
):
    return build_source_rights_registry(
        [
            {
                "source_id": source_id,
                "display_name": "Licensed consensus fixture",
                "permitted_use": "test_only",
                "commercial_use": commercial_use,
                "redistribution": "test_only",
                "storage_limits": "temporary in-memory tests only",
                "attribution": "fixture",
                "rate_limits": "not applicable",
                "authentication": "not applicable",
                "expected_freshness": "fixture cutoff",
                "supported_fields": list(
                    supported_fields or ("revenue_consensus", "eps_consensus")
                ),
                "fallback_priority": 1,
            }
        ]
    )


def _current_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "ticker": "NVDA",
        "fiscal_period": "2027-Q1",
        "snapshot_at": "2026-07-18T05:00:00Z",
        "retrieved_at": "2026-07-18T05:00:01Z",
        "source_ref": "provider://consensus/current/NVDA/2027-Q1",
        "revenue_consensus": "1",
        "eps_consensus": "1",
        "history_scope": "current_only",
    }
    row.update(overrides)
    return row


def _historical_row(**overrides: object) -> dict[str, object]:
    row = _current_row(
        history_scope="point_in_time",
        source_ref="provider://consensus/history/NVDA/2027-Q1/20260718",
        revenue_currency="USD",
        revenue_unit_scale="1",
        revenue_basis="reported",
        eps_currency="USD",
        eps_basis="gaap",
        eps_share_basis="diluted",
        eps_operations_basis="reported",
        split_adjustment_basis="as_reported",
    )
    row.update(overrides)
    return row


def test_source_status_uses_deterministic_order_and_fails_closed_without_keys(tmp_path: Path):
    statuses = consensus_source_statuses(env={}, generic_csv=tmp_path / "missing.csv")

    assert [row.provider for row in statuses] == ["alpha_vantage", "fmp", "finnhub", "reviewed_csv"]
    assert [row.status for row in statuses[:3]] == ["external_key_required"] * 3
    assert statuses[-1].status == "external_data_required"
    assert all(row.auto_apply is False for row in statuses)


def test_current_only_estimate_payload_is_candidate_context_not_history():
    result = validate_source_rows(
        "alpha_vantage",
        [_current_row()],
        as_of=REVIEW_CUTOFF,
    )

    assert result.accepted_count == 1
    assert result.review_cutoff == REVIEW_CUTOFF
    assert result.state == "candidate_context_only"
    assert result.historical_snapshot_count == 0
    assert result.rights_status == "unknown_source"
    assert result.commercial_rights_approved is False
    assert result.commercial_ready_count == 0
    assert result.commercial_review_required_count == 1
    assert result.commercial_evidence_ready is False
    assert result.commercial_review_rows[0].missing_supported_fields == (
        "revenue_consensus",
        "eps_consensus",
    )
    assert result.commercial_review_rows[0].commercial_blockers == (
        "commercial_rights:unknown_source",
        "registered_consensus_scope_missing:revenue_consensus",
        "registered_consensus_scope_missing:eps_consensus",
    )
    assert result.auto_apply is False


def test_caller_cannot_supply_a_source_rights_label():
    with pytest.raises(TypeError, match="rights_status"):
        validate_source_rows(
            "alpha_vantage",
            (),
            as_of=REVIEW_CUTOFF,
            rights_status="approved_for_project_use",  # type: ignore[call-arg]
        )


def test_historical_rows_require_source_and_comparability_fields():
    result = validate_source_rows(
        "reviewed_csv",
        [{"ticker": "NVDA", "fiscal_period": "2026-Q4", "history_scope": "point_in_time"}],
        as_of=REVIEW_CUTOFF,
    )

    assert result.accepted_count == 0
    assert result.rejected_count == 1
    assert "snapshot_at" in result.rejected_rows[0]["reason"]
    assert "revenue_currency" in result.rejected_rows[0]["reason"]
    assert result.commercial_ready_count == 0
    assert result.commercial_review_required_count == 0
    assert result.commercial_review_rows == ()


def test_historical_rows_are_reviewable_and_not_declared_ready():
    result = validate_source_rows(
        "licensed_consensus",
        [_historical_row()],
        as_of=REVIEW_CUTOFF,
        rights_registry=_rights_registry(),
    )

    assert result.accepted_count == 1
    assert result.historical_snapshot_count == 1
    assert result.state == "historical_evidence_reviewable"
    assert result.rights_status == "approved"
    assert result.commercial_evidence_ready is True
    assert result.commercial_ready_count == 1
    assert result.commercial_review_required_count == 0


def test_source_rows_require_only_populated_revenue_and_eps_scope():
    revenue_registry = _rights_registry(supported_fields=("revenue_consensus",))
    eps_registry = _rights_registry(supported_fields=("eps_consensus",))
    revenue_only = validate_source_rows(
        "licensed_consensus",
        [_current_row(eps_consensus="")],
        as_of=REVIEW_CUTOFF,
        rights_registry=revenue_registry,
    )
    eps_only = validate_source_rows(
        "licensed_consensus",
        [_current_row(revenue_consensus="")],
        as_of=REVIEW_CUTOFF,
        rights_registry=eps_registry,
    )
    mixed = validate_source_rows(
        "licensed_consensus",
        [_current_row()],
        as_of=REVIEW_CUTOFF,
        rights_registry=revenue_registry,
    )

    assert revenue_only.commercial_review_rows[0].required_supported_fields == (
        "revenue_consensus",
    )
    assert revenue_only.commercial_review_rows[0].missing_supported_fields == ()
    assert revenue_only.commercial_evidence_ready is True
    assert eps_only.commercial_review_rows[0].required_supported_fields == (
        "eps_consensus",
    )
    assert eps_only.commercial_review_rows[0].missing_supported_fields == ()
    assert eps_only.commercial_evidence_ready is True
    assert mixed.commercial_rights_approved is True
    assert mixed.commercial_review_rows[0].required_supported_fields == (
        "revenue_consensus",
        "eps_consensus",
    )
    assert mixed.commercial_review_rows[0].missing_supported_fields == ("eps_consensus",)
    assert mixed.commercial_review_required_count == 1
    assert mixed.commercial_evidence_ready is False
    assert mixed.commercial_blockers == (
        "registered_consensus_scope_missing:eps_consensus",
    )


def test_source_rows_do_not_split_or_infer_a_composite_provider():
    result = validate_source_rows(
        "licensed_consensus + reviewed_csv",
        [_current_row()],
        as_of=REVIEW_CUTOFF,
        rights_registry=_rights_registry(),
    )

    assert result.provider == "licensed_consensus + reviewed_csv"
    assert result.accepted_count == 1
    assert result.rights_status == "unknown_source"
    assert result.commercial_rights_approved is False
    assert result.commercial_review_rows[0].missing_supported_fields == (
        "revenue_consensus",
        "eps_consensus",
    )
    assert result.commercial_evidence_ready is False


def test_source_rows_reject_invalid_fiscal_period_even_when_fields_are_present():
    row = _historical_row(fiscal_period="next-quarter", eps_consensus="")
    result = validate_source_rows("reviewed_csv", [row], as_of=REVIEW_CUTOFF)

    assert result.rejected_count == 1
    assert "fiscal_period" in result.rejected_rows[0]["reason"]


def test_source_rows_require_a_valid_review_cutoff():
    with pytest.raises(ValueError, match="review cutoff"):
        validate_source_rows("reviewed_csv", (), as_of="not-a-cutoff")


@pytest.mark.parametrize("scope", ["", "historical", "latest"])
def test_source_rows_require_an_explicit_supported_history_scope(scope: str):
    result = validate_source_rows(
        "licensed_consensus",
        [_current_row(history_scope=scope)],
        as_of=REVIEW_CUTOFF,
        rights_registry=_rights_registry(),
    )

    assert result.accepted_count == 0
    assert result.state == "still_blocked"
    assert "history_scope must be current_only or point_in_time" in result.rejected_rows[0]["reason"]
    assert result.commercial_rights_approved is True
    assert result.commercial_ready_count == 0
    assert result.commercial_review_rows == ()


def test_source_rows_reject_snapshot_after_retrieval():
    result = validate_source_rows(
        "licensed_consensus",
        [_current_row(snapshot_at="2026-07-18T05:00:02Z")],
        as_of=REVIEW_CUTOFF,
        rights_registry=_rights_registry(),
    )

    assert result.accepted_count == 0
    assert "snapshot_at cannot be after retrieved_at" in result.rejected_rows[0]["reason"]
    assert result.commercial_rights_approved is True
    assert result.commercial_ready_count == 0
    assert result.commercial_review_rows == ()


def test_source_rows_reject_snapshot_after_review_cutoff():
    result = validate_source_rows(
        "licensed_consensus",
        [
            _current_row(
                snapshot_at="2026-07-18T06:00:01Z",
                retrieved_at="2026-07-18T06:00:02Z",
            )
        ],
        as_of=REVIEW_CUTOFF,
        rights_registry=_rights_registry(),
    )

    assert result.accepted_count == 0
    assert "snapshot_at is after review cutoff" in result.rejected_rows[0]["reason"]
    assert result.commercial_review_rows == ()


def test_source_rows_reject_retrieval_after_review_cutoff():
    result = validate_source_rows(
        "licensed_consensus",
        [_current_row(retrieved_at="2026-07-18T06:00:01Z")],
        as_of=REVIEW_CUTOFF,
        rights_registry=_rights_registry(),
    )

    assert result.accepted_count == 0
    assert "retrieved_at is after review cutoff" in result.rejected_rows[0]["reason"]
    assert result.commercial_review_rows == ()


def test_source_rows_accept_timestamp_equality_at_retrieval_and_cutoff():
    result = validate_source_rows(
        "licensed_consensus",
        [
            _current_row(
                snapshot_at=REVIEW_CUTOFF,
                retrieved_at=REVIEW_CUTOFF,
            )
        ],
        as_of=REVIEW_CUTOFF,
        rights_registry=_rights_registry(),
    )

    assert result.accepted_count == 1
    assert result.state == "candidate_context_only"
    assert result.commercial_ready_count == 1


def test_source_rows_preserve_original_row_numbers_after_temporal_rejection():
    result = validate_source_rows(
        "licensed_consensus",
        [
            _current_row(retrieved_at="2026-07-18T06:00:01Z"),
            _current_row(source_ref="provider://consensus/current/NVDA/2027-Q1/second"),
        ],
        as_of=REVIEW_CUTOFF,
        rights_registry=_rights_registry(),
    )

    assert result.accepted_count == 1
    assert result.rejected_count == 1
    assert result.rejected_rows[0]["row_number"] == 1
    assert result.commercial_review_rows[0].row_number == 2
