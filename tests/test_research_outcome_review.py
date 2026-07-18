from pathlib import Path

import pytest

from src.research_outcome_review import (
    ResearchOutcome,
    append_reviewed_outcome,
    derive_outcome_status,
    load_outcomes,
    preview_outcome,
)


def _outcome(**overrides) -> ResearchOutcome:
    values = {
        "schema_version": "research-outcome-review-v1",
        "outcome_id": "outcome-001",
        "profile_key": "default",
        "ticker": "NVDA",
        "thesis_id": "thesis-001",
        "original_thesis_entry_id": "entry-001",
        "reviewed_at": "2026-07-18T05:00:00Z",
        "observation_start": "2026-04-01T00:00:00Z",
        "observation_end": "2026-07-17T23:59:59Z",
        "reviewer": "owner",
        "outcome_state": "mixed",
        "summary": "Some operating evidence supported the thesis and some did not.",
        "source": "reviewed_research_record",
        "source_ref": "journal://entry-001",
        "source_published_at": "2026-07-17T23:00:00Z",
        "learning": "Separate demand evidence from margin evidence next review.",
    }
    values.update(overrides)
    return ResearchOutcome(**values)


def test_outcome_preview_is_read_only_and_forbids_performance_scoring():
    preview = preview_outcome(_outcome(), existing=())

    assert preview.state == "reviewable"
    assert preview.write_performed is False
    assert "return" not in preview.fields
    assert "skill" not in preview.fields


def test_outcome_append_requires_confirmation_and_is_immutable(tmp_path: Path):
    ledger = tmp_path / "outcomes.csv"
    with pytest.raises(ValueError, match="confirm_reviewed"):
        append_reviewed_outcome(ledger, _outcome(), confirm_reviewed=False)

    append_reviewed_outcome(ledger, _outcome(), confirm_reviewed=True)
    with pytest.raises(ValueError, match="already exists"):
        append_reviewed_outcome(ledger, _outcome(), confirm_reviewed=True)

    assert load_outcomes(ledger) == (_outcome(),)


def test_outcome_rejects_future_source_and_invalid_observation_window():
    future = preview_outcome(
        _outcome(source_published_at="2026-07-19T00:00:00Z"),
        existing=(),
    )
    invalid_window = preview_outcome(
        _outcome(observation_start="2026-07-18T00:00:00Z", observation_end="2026-07-17T00:00:00Z"),
        existing=(),
    )

    assert future.state == "rejected"
    assert invalid_window.state == "rejected"


def test_derived_status_reports_learning_loop_without_grading_company():
    status = derive_outcome_status((_outcome(),), profile_key="default", ticker="NVDA")
    assert status.state == "reviewed"
    assert status.review_count == 1
    assert status.latest_outcome_state == "mixed"
    assert status.next_action == "Use the recorded learning when the thesis is next reviewed."


def test_same_underlying_outcome_cannot_be_duplicated_under_a_new_id():
    duplicate = preview_outcome(_outcome(outcome_id="outcome-002"), existing=(_outcome(),))
    assert duplicate.state == "rejected"
    assert "duplicate outcome evidence" in duplicate.reason
