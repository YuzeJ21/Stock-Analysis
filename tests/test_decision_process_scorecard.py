from dataclasses import replace
from types import SimpleNamespace

import pytest

from src.decision_process_scorecard import build_decision_process_scorecard, decision_process_rows
from src.research_thesis_journal import JournalEntry, derive_journal_state


def _entry(
    entry_id: str,
    entry_type: str,
    recorded_at: str,
    *,
    direction: str = "",
    confidence: str = "",
    review_due_date: str = "",
) -> JournalEntry:
    requires_source = entry_type in {"evidence", "catalyst", "risk", "invalidation"}
    return JournalEntry(
        schema_version="research-thesis-journal-v1",
        entry_id=entry_id,
        profile_key="demo",
        ticker="ALFA",
        thesis_id="thesis-1",
        entry_type=entry_type,
        recorded_at=recorded_at,
        effective_at=recorded_at,
        reviewer="fixture-reviewer",
        summary=f"{entry_type} fixture",
        evidence_direction=direction,
        source="fixture" if requires_source else "",
        source_ref=f"fixture:{entry_id}" if requires_source else "",
        source_published_at=recorded_at if requires_source else "",
        confidence=confidence,
        review_due_date=review_due_date,
        supersedes_entry_id="",
    )


def _report(*, dcf_ready: bool = True, asset_type: str = "company") -> dict[str, object]:
    return {
        "ticker": "ALFA",
        "asset_type": asset_type,
        "valuation_readiness": {"dcf_ready": dcf_ready},
        "valuation_snapshot": {
            "dcf_result": {
                "status": "calculated" if dcf_ready else "insufficient_data",
                "assumptions": {"wacc": 0.09, "terminal_growth": 0.03} if dcf_ready else {},
            }
        },
    }


def _complete_state():
    entries = (
        _entry("t1", "thesis", "2026-07-01T12:00:00Z", review_due_date="2026-08-01"),
        _entry("e1", "evidence", "2026-07-02T12:00:00Z", direction="supporting"),
        _entry("e2", "evidence", "2026-07-03T12:00:00Z", direction="conflicting"),
        _entry("i1", "invalidation", "2026-07-04T12:00:00Z"),
        _entry("c1", "confidence", "2026-07-05T12:00:00Z", confidence="0.6"),
        _entry("r1", "review", "2026-07-06T12:00:00Z", review_due_date="2026-08-01"),
    )
    return derive_journal_state(entries, profile_key="demo", ticker="ALFA", as_of="2026-07-15T12:00:00Z")


def test_complete_process_history_is_ready_for_review_without_a_company_score():
    scorecard = build_decision_process_scorecard(
        _report(),
        profile_key="demo",
        journal_state=_complete_state(),
        review_items=(),
    )

    assert scorecard.status == "process_documented"
    assert scorecard.action_needed_count == 0
    assert scorecard.complete_count == 9
    assert "return" in scorecard.boundary.lower()
    assert "score" not in str(decision_process_rows(scorecard)).lower()


def test_missing_journal_history_is_action_needed_not_synthesized():
    state = derive_journal_state((), profile_key="demo", ticker="ALFA", as_of="2026-07-15T12:00:00Z")

    scorecard = build_decision_process_scorecard(_report(), profile_key="demo", journal_state=state, review_items=())

    checks = {check.key: check for check in scorecard.checks}
    assert checks["thesis_documented"].state == "action_needed"
    assert checks["evidence_recorded"].state == "action_needed"
    assert checks["conflicting_evidence_reviewed"].state == "not_observed"
    assert scorecard.status == "process_work_needed"


def test_conflicting_evidence_requires_a_later_review_entry():
    state = _complete_state()
    without_review = replace(state, entries=tuple(row for row in state.entries if row.entry_type != "review"))

    scorecard = build_decision_process_scorecard(_report(), profile_key="demo", journal_state=without_review, review_items=())

    check = next(row for row in scorecard.checks if row.key == "conflicting_evidence_reviewed")
    assert check.state == "action_needed"
    assert "later review" in check.next_action.lower()


def test_no_conflicting_evidence_is_not_observed_not_automatically_complete():
    state = _complete_state()
    no_conflict = replace(
        state,
        entries=tuple(row for row in state.entries if row.evidence_direction != "conflicting"),
        conflicting_evidence=(),
    )

    scorecard = build_decision_process_scorecard(_report(), profile_key="demo", journal_state=no_conflict, review_items=())

    check = next(row for row in scorecard.checks if row.key == "conflicting_evidence_reviewed")
    assert check.state == "not_observed"


def test_open_change_item_remains_action_needed():
    item = SimpleNamespace(event=SimpleNamespace(ticker="ALFA"), review_status="open")

    scorecard = build_decision_process_scorecard(
        _report(), profile_key="demo", journal_state=_complete_state(), review_items=(item,)
    )

    check = next(row for row in scorecard.checks if row.key == "evidence_changes_reviewed")
    assert check.state == "action_needed"
    assert "1 open" in check.evidence.lower()


def test_dcf_block_and_exclusion_do_not_become_documentation_failures():
    blocked = build_decision_process_scorecard(
        _report(dcf_ready=False), profile_key="demo", journal_state=_complete_state(), review_items=()
    )
    excluded = build_decision_process_scorecard(
        _report(dcf_ready=False, asset_type="etf"), profile_key="demo", journal_state=_complete_state(), review_items=()
    )

    blocked_check = next(row for row in blocked.checks if row.key == "dcf_assumptions_visible")
    excluded_check = next(row for row in excluded.checks if row.key == "dcf_assumptions_visible")
    assert blocked_check.state == "blocked"
    assert excluded_check.state == "not_applicable"


def test_profile_or_ticker_mismatch_fails_closed():
    with pytest.raises(ValueError, match="selected profile and ticker"):
        build_decision_process_scorecard(
            _report(), profile_key="other", journal_state=_complete_state(), review_items=()
        )


def test_scorecard_identity_is_deterministic():
    first = build_decision_process_scorecard(
        _report(), profile_key="demo", journal_state=_complete_state(), review_items=()
    )
    second = build_decision_process_scorecard(
        _report(), profile_key="demo", journal_state=_complete_state(), review_items=()
    )

    assert first.scorecard_identity == second.scorecard_identity
