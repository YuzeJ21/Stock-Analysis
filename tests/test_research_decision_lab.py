from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace

import pytest

from src.catalyst_evidence_timeline import CatalystEvent, CatalystTimeline
from src.decision_process_scorecard import build_decision_process_scorecard
from src.research_decision_lab import (
    build_research_decision_lab_state,
    build_research_discipline_rows,
    decision_lab_cards,
    decision_lab_rows,
    derive_research_process_attention,
    research_discipline_rows,
    unavailable_research_decision_lab_state,
)
from src.research_outcome_review import OutcomeStatus
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


def _report(
    *,
    dcf_ready: bool = True,
    asset_type: str = "company",
    assumptions: bool = True,
) -> dict[str, object]:
    return {
        "ticker": "ALFA",
        "asset_type": asset_type,
        "valuation_readiness": {"dcf_ready": dcf_ready},
        "valuation_snapshot": {
            "dcf_result": {
                "status": "calculated" if dcf_ready else "insufficient_data",
                "assumptions": (
                    {"wacc": 0.09, "terminal_growth": 0.03}
                    if dcf_ready and assumptions
                    else {}
                ),
            }
        },
    }


def _journal(*, variant: str = "complete"):
    rows: list[JournalEntry] = []
    if variant != "empty":
        due = "2026-07-10" if variant == "overdue" else "" if variant == "unscheduled" else "2026-08-01"
        rows.append(_entry("t1", "thesis", "2026-07-01T12:00:00Z", review_due_date=due))
    if variant not in {"empty", "missing_evidence"}:
        rows.append(_entry("e1", "evidence", "2026-07-02T12:00:00Z", direction="supporting"))
    if variant in {"conflict", "conflict_reviewed"}:
        rows.append(_entry("e2", "evidence", "2026-07-03T12:00:00Z", direction="conflicting"))
    if variant not in {"empty", "missing_invalidation"}:
        rows.append(_entry("i1", "invalidation", "2026-07-04T12:00:00Z"))
    if variant not in {"empty", "unscheduled"}:
        rows.append(_entry("c1", "confidence", "2026-07-05T12:00:00Z", confidence="0.6"))
    if variant == "conflict_reviewed":
        rows.append(_entry("r1", "review", "2026-07-06T12:00:00Z", review_due_date="2026-08-01"))
    return derive_journal_state(
        tuple(rows),
        profile_key="demo",
        ticker="ALFA",
        as_of="2026-07-15T12:00:00Z",
    )


def _outcome(state: str = "not_started") -> OutcomeStatus:
    if state == "reviewed":
        return OutcomeStatus("reviewed", 1, "mixed", "Review the source boundary.", "Use it at the next review.", 0, ())
    if state == "commercial_evidence_blocked":
        return OutcomeStatus(
            "commercial_evidence_blocked",
            0,
            "",
            "",
            "Review source rights before using this learning record.",
            1,
            ("outcome-1: exact-source rights are unverified",),
        )
    return OutcomeStatus("not_started", 0, "", "", "Review only after the observation window closes.", 0, ())


def _state(
    *,
    journal_variant: str = "complete",
    outcome_state: str = "not_started",
    dcf_ready: bool = True,
    asset_type: str = "company",
    assumptions: bool = True,
    open_change: bool = False,
):
    journal = _journal(variant=journal_variant)
    review_items = (
        (SimpleNamespace(event=SimpleNamespace(ticker="ALFA"), review_status="open"),)
        if open_change
        else ()
    )
    scorecard = build_decision_process_scorecard(
        _report(dcf_ready=dcf_ready, asset_type=asset_type, assumptions=assumptions),
        profile_key="demo",
        journal_state=journal,
        review_items=review_items,
    )
    return build_research_decision_lab_state(
        profile_key="demo",
        journal_state=journal,
        scorecard=scorecard,
        outcome_status=_outcome(outcome_state),
        review_items=review_items,
    )


def _lane_states(state) -> dict[str, str]:
    return {lane.key: lane.state for lane in state.lanes}


def _state_with_lane_states(**lane_states):
    state = _state()
    return replace(
        state,
        lanes=tuple(
            replace(lane, state=lane_states.get(lane.key, lane.state))
            for lane in state.lanes
        ),
    )


def _upcoming_catalyst(ticker: str = "ALFA") -> CatalystTimeline:
    event = CatalystEvent(
        "catalyst-evidence-v1",
        "event-1",
        "demo",
        ticker,
        "earnings",
        "Synthetic scheduled evidence",
        "2026-08-20T21:00:00Z",
        "2026-07-20T09:00:00Z",
        "2026-07-20T10:00:00Z",
        "fixture",
        "fixture:event-1",
        "candidate_context_only",
        "fixture-reviewer",
        "Synthetic context only.",
    )
    return CatalystTimeline(
        ticker,
        "candidate_context_only",
        (event,),
        (),
        0,
        0,
        (),
        "Research context only.",
    )


def test_empty_history_keeps_six_lanes_independent_and_not_started():
    state = _state(journal_variant="empty", dcf_ready=False)

    assert [lane.key for lane in state.lanes] == [
        "plan",
        "evidence",
        "invalidation",
        "scenario",
        "review_trigger",
        "learning",
    ]
    assert _lane_states(state) == {
        "plan": "not_started",
        "evidence": "not_started",
        "invalidation": "not_started",
        "scenario": "blocked",
        "review_trigger": "not_started",
        "learning": "not_started",
    }
    assert state.next_process_step == "Record a current reviewer-authored thesis."
    assert state.status == "process_work_needed"


def test_complete_history_maps_each_lane_without_creating_a_company_score():
    state = _state(outcome_state="reviewed")

    assert _lane_states(state) == {
        "plan": "documented",
        "evidence": "current",
        "invalidation": "documented",
        "scenario": "reviewable",
        "review_trigger": "scheduled",
        "learning": "reviewed",
    }
    assert state.status == "process_documented"
    assert state.next_process_step.startswith("Continue monitoring")
    assert "score" not in str(decision_lab_rows(state)).lower()


def test_conflicting_evidence_requires_later_review_and_only_changes_evidence_lane():
    unresolved = _state(journal_variant="conflict")
    reviewed = _state(journal_variant="conflict_reviewed")

    assert _lane_states(unresolved)["evidence"] == "conflict_review_needed"
    assert _lane_states(reviewed)["evidence"] == "current"
    assert unresolved.next_process_step.startswith("Review recorded conflicting evidence")
    assert _lane_states(unresolved)["scenario"] == _lane_states(reviewed)["scenario"] == "reviewable"
    assert _lane_states(unresolved)["learning"] == _lane_states(reviewed)["learning"] == "not_started"


def test_overdue_and_unscheduled_review_states_remain_distinct():
    overdue = _state(journal_variant="overdue")
    unscheduled = _state(journal_variant="unscheduled")

    assert _lane_states(overdue)["review_trigger"] == "overdue"
    assert overdue.next_process_step.startswith("Review the overdue thesis")
    assert _lane_states(unscheduled)["review_trigger"] == "unscheduled"
    assert unscheduled.next_process_step.startswith("Schedule the next evidence review")


def test_open_evidence_change_sets_review_trigger_without_promoting_other_lanes():
    regular = _state()
    changed = _state(open_change=True)

    assert _lane_states(changed)["review_trigger"] == "evidence_change_due"
    assert _lane_states(changed)["plan"] == _lane_states(regular)["plan"]
    assert _lane_states(changed)["scenario"] == _lane_states(regular)["scenario"]
    assert changed.status == "process_work_needed"


def test_scenario_states_preserve_ready_blocked_excluded_and_missing_assumptions():
    reviewable = _state()
    blocked = _state(dcf_ready=False)
    excluded = _state(dcf_ready=False, asset_type="etf")
    unavailable = _state(assumptions=False)

    assert _lane_states(reviewable)["scenario"] == "reviewable"
    assert _lane_states(blocked)["scenario"] == "blocked"
    assert _lane_states(excluded)["scenario"] == "excluded"
    assert _lane_states(unavailable)["scenario"] == "unavailable"
    assert unavailable.next_process_step.startswith("Restore visible DCF assumptions")


def test_learning_commercial_blocker_does_not_change_plan_or_scenario():
    regular = _state()
    blocked = _state(outcome_state="commercial_evidence_blocked")

    assert _lane_states(blocked)["learning"] == "commercial_evidence_blocked"
    assert _lane_states(blocked)["plan"] == _lane_states(regular)["plan"] == "documented"
    assert _lane_states(blocked)["scenario"] == _lane_states(regular)["scenario"] == "reviewable"


def test_profile_or_ticker_mismatch_fails_closed():
    journal = _journal()
    scorecard = build_decision_process_scorecard(
        _report(), profile_key="demo", journal_state=journal, review_items=()
    )

    with pytest.raises(ValueError, match="selected profile and ticker"):
        build_research_decision_lab_state(
            profile_key="other",
            journal_state=journal,
            scorecard=scorecard,
            outcome_status=_outcome(),
        )


def test_invalid_journal_can_render_one_compact_unavailable_contract():
    state = unavailable_research_decision_lab_state(
        profile_key="demo",
        ticker="ALFA",
        reason="Research thesis journal header does not match the append-only contract.",
    )

    assert state.status == "unavailable"
    assert set(_lane_states(state).values()) == {"unavailable"}
    assert "header does not match" in decision_lab_rows(state)[0]["Evidence"]


def test_identity_and_contracts_are_deterministic_and_immutable():
    first = _state()
    second = _state()

    assert first.identity == second.identity
    assert decision_lab_cards(first) == decision_lab_cards(second)
    with pytest.raises(FrozenInstanceError):
        first.status = "changed"


def test_cohort_rows_preserve_focused_order_and_never_sort_by_process_severity():
    alpha = _state(journal_variant="empty", dcf_ready=False)
    beta = replace(_state(), ticker="BETA", identity="beta-identity")

    rows = build_research_discipline_rows(
        {"ALFA": alpha, "BETA": beta},
        focused_tickers=("BETA", "ALFA"),
    )

    assert [row.ticker for row in rows] == ["BETA", "ALFA"]
    assert [row.cohort_order for row in rows] == [0, 1]
    assert "Plan" in rows[1].due_lanes
    assert "Evidence" in rows[1].due_lanes
    assert [row["Ticker"] for row in research_discipline_rows(rows)] == ["BETA", "ALFA"]
    assert "rank" not in str(rows).lower()
    assert "market value" not in str(rows).lower()


def test_unresolved_change_precedes_overdue_and_invalidation_attention():
    state = _state_with_lane_states(
        evidence="current",
        invalidation="missing",
        review_trigger="evidence_change_due",
    )

    attention = derive_research_process_attention(state)

    assert attention.state == "evidence_change_due"
    assert attention.label == "Needs review"
    assert attention.source == "review_trigger"


@pytest.mark.parametrize(
    ("lane_states", "expected_state", "expected_label", "expected_source"),
    [
        (
            {"evidence": "conflict_review_needed", "review_trigger": "overdue"},
            "conflicting_evidence",
            "Needs review",
            "evidence",
        ),
        (
            {"review_trigger": "overdue", "invalidation": "missing"},
            "overdue_review",
            "Needs review",
            "review_trigger",
        ),
        (
            {"invalidation": "missing"},
            "invalidation_follow_up",
            "Needs review",
            "invalidation",
        ),
        (
            {"learning": "commercial_evidence_blocked"},
            "outcome_follow_up",
            "Needs review",
            "learning",
        ),
        (
            {"review_trigger": "scheduled"},
            "scheduled_review",
            "Scheduled",
            "review_trigger",
        ),
    ],
)
def test_attention_uses_fixed_non_market_precedence(
    lane_states, expected_state, expected_label, expected_source
):
    attention = derive_research_process_attention(
        _state_with_lane_states(**lane_states)
    )

    assert attention.state == expected_state
    assert attention.label == expected_label
    assert attention.source == expected_source


def test_scheduled_catalyst_uses_exact_date_after_saved_followups():
    state = _state_with_lane_states(review_trigger="unscheduled")

    attention = derive_research_process_attention(
        state,
        catalyst_timeline=_upcoming_catalyst(),
    )

    assert attention.state == "scheduled_catalyst"
    assert attention.label == "Scheduled"
    assert "2026-08-20T21:00:00Z" in attention.reason
    assert "urgent" not in attention.reason.lower()
    assert "price" not in attention.reason.lower()
    assert attention.source == "catalyst"


def test_monitor_and_unavailable_attention_fail_closed_without_ranking():
    monitor = derive_research_process_attention(
        _state_with_lane_states(review_trigger="unscheduled")
    )
    unavailable = derive_research_process_attention(
        _state_with_lane_states(review_trigger="unscheduled"),
        catalyst_error="Catalyst ledger header is invalid.",
    )

    assert (monitor.state, monitor.label) == ("monitor", "Monitor")
    assert (unavailable.state, unavailable.label) == ("unavailable", "Unavailable")
    assert "rank" not in str((monitor, unavailable)).lower()


def test_independent_scenario_unavailability_does_not_override_scheduled_review():
    attention = derive_research_process_attention(
        _state_with_lane_states(
            scenario="unavailable",
            review_trigger="scheduled",
        )
    )

    assert attention.state == "scheduled_review"
    assert attention.source == "review_trigger"


def test_discipline_rows_add_attention_without_changing_cohort_order_or_identity():
    alpha = _state_with_lane_states(review_trigger="overdue")
    beta = replace(
        _state_with_lane_states(review_trigger="unscheduled"),
        ticker="BETA",
        identity="beta-identity",
    )

    rows = build_research_discipline_rows(
        {"ALFA": alpha, "BETA": beta},
        focused_tickers=("BETA", "ALFA"),
        catalyst_timelines_by_ticker={"BETA": _upcoming_catalyst("BETA")},
    )

    assert [row.ticker for row in rows] == ["BETA", "ALFA"]
    assert [row.identity for row in rows] == ["beta-identity", alpha.identity]
    assert [row.attention_state for row in rows] == [
        "scheduled_catalyst",
        "overdue_review",
    ]


def test_primary_display_copy_contains_no_transaction_or_allocation_language():
    state = _state(outcome_state="reviewed")
    display = str(decision_lab_cards(state)).lower()

    for forbidden in (
        "buy",
        "sell",
        "position size",
        "allocation",
        "stop loss",
        "take profit",
        "entry price",
        "exit price",
    ):
        assert forbidden not in display
