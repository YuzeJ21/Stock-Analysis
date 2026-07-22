"""Read-only composition of saved research-process evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Iterable, Mapping

from src.decision_process_scorecard import DecisionProcessScorecard, ProcessCheck
from src.research_outcome_review import OutcomeStatus
from src.research_thesis_journal import JournalState


LANE_ORDER = (
    ("plan", "Plan"),
    ("evidence", "Evidence"),
    ("invalidation", "Invalidation"),
    ("scenario", "Scenario"),
    ("review_trigger", "Review trigger"),
    ("learning", "Learning"),
)

BOUNDARY = (
    "Research-process documentation only; no company grade, expected-return score, "
    "performance claim, recommendation, or transaction action is produced."
)


@dataclass(frozen=True)
class DecisionLabLane:
    key: str
    label: str
    state: str
    answer: str
    evidence: str
    next_step: str


@dataclass(frozen=True)
class ResearchDecisionLabState:
    profile_key: str
    ticker: str
    status: str
    lanes: tuple[DecisionLabLane, ...]
    next_process_step: str
    boundary: str
    identity: str


@dataclass(frozen=True)
class ResearchDisciplineRow:
    cohort_order: int
    ticker: str
    status: str
    due_lanes: tuple[str, ...]
    next_process_step: str
    identity: str


def _text(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null", "<na>"} else text


def _check_map(scorecard: DecisionProcessScorecard) -> dict[str, ProcessCheck]:
    return {check.key: check for check in scorecard.checks}


def _lane(
    key: str,
    label: str,
    state: str,
    answer: str,
    evidence: str,
    next_step: str,
) -> DecisionLabLane:
    return DecisionLabLane(key, label, state, answer, evidence, next_step)


def _identity(
    *,
    profile_key: str,
    ticker: str,
    status: str,
    lanes: tuple[DecisionLabLane, ...],
    next_process_step: str,
) -> str:
    payload = {
        "profile_key": profile_key,
        "ticker": ticker,
        "status": status,
        "lanes": [asdict(lane) for lane in lanes],
        "next_process_step": next_process_step,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _matching_open_change_count(review_items: Iterable[object], ticker: str) -> int:
    return sum(
        1
        for item in review_items
        if _text(getattr(getattr(item, "event", None), "ticker", "")).upper() == ticker
        and _text(getattr(item, "review_status", "open")).lower() not in {"resolved", "closed"}
    )


def _plan_lane(journal_state: JournalState, checks: Mapping[str, ProcessCheck]) -> DecisionLabLane:
    check = checks["thesis_documented"]
    if journal_state.current_thesis is None:
        return _lane(
            "plan",
            "Plan",
            "not_started",
            "No current reviewer-authored thesis",
            check.evidence,
            "Record a current reviewer-authored thesis and a review date.",
        )
    return _lane(
        "plan",
        "Plan",
        "documented",
        "Current reviewer-authored thesis is documented",
        check.evidence,
        "Revisit the thesis when reviewed evidence changes.",
    )


def _evidence_lane(journal_state: JournalState, checks: Mapping[str, ProcessCheck]) -> DecisionLabLane:
    recorded = checks["evidence_recorded"]
    conflict = checks["conflicting_evidence_reviewed"]
    if recorded.state != "complete":
        return _lane(
            "evidence",
            "Evidence",
            "not_started",
            "No reviewed research evidence is recorded",
            recorded.evidence,
            "Record source-backed evidence before relying on the thesis.",
        )
    if conflict.state == "action_needed":
        return _lane(
            "evidence",
            "Evidence",
            "conflict_review_needed",
            "Recorded conflicting evidence needs a later review",
            conflict.evidence,
            conflict.next_action,
        )
    return _lane(
        "evidence",
        "Evidence",
        "current",
        "Reviewed research evidence is recorded",
        recorded.evidence,
        "Revisit this lane when new source-backed evidence arrives.",
    )


def _invalidation_lane(journal_state: JournalState, checks: Mapping[str, ProcessCheck]) -> DecisionLabLane:
    check = checks["invalidation_documented"]
    if journal_state.current_thesis is None:
        return _lane(
            "invalidation",
            "Invalidation",
            "not_started",
            "No current thesis exists to invalidate",
            "No invalidation condition is synthesized from risks or price movement.",
            "Record the thesis before documenting its invalidation condition.",
        )
    if check.state != "complete":
        return _lane(
            "invalidation",
            "Invalidation",
            "missing",
            "No source-backed invalidation condition is documented",
            check.evidence,
            "Record what source-backed evidence would invalidate the thesis.",
        )
    return _lane(
        "invalidation",
        "Invalidation",
        "documented",
        "Source-backed invalidation condition is documented",
        check.evidence,
        "Revisit the condition when reviewed evidence changes.",
    )


def _scenario_lane(checks: Mapping[str, ProcessCheck]) -> DecisionLabLane:
    check = checks["dcf_assumptions_visible"]
    if check.state == "complete":
        return _lane(
            "scenario",
            "Scenario",
            "reviewable",
            "Scenario assumptions are reviewable",
            check.evidence,
            "Review visible assumptions and sensitivity before interpreting scenario math.",
        )
    if check.state == "blocked":
        return _lane(
            "scenario",
            "Scenario",
            "blocked",
            "Scenario review is blocked by valuation readiness",
            check.evidence,
            "Resolve trusted DCF inputs before reviewing scenario math.",
        )
    if check.state == "not_applicable":
        return _lane(
            "scenario",
            "Scenario",
            "excluded",
            "Operating-company scenario review is excluded for this asset",
            check.evidence,
            "Use the existing market-context research method for this asset type.",
        )
    return _lane(
        "scenario",
        "Scenario",
        "unavailable",
        "Scenario assumptions are unavailable",
        check.evidence,
        "Restore explicit assumptions before interpreting scenario math.",
    )


def _review_trigger_lane(
    journal_state: JournalState,
    checks: Mapping[str, ProcessCheck],
    *,
    open_change_count: int,
) -> DecisionLabLane:
    review = checks["review_current"]
    if journal_state.current_thesis is None:
        return _lane(
            "review_trigger",
            "Review trigger",
            "not_started",
            "No reviewer-authored review trigger is scheduled",
            "An empty journal cannot create a review date or evidence trigger.",
            "Record a thesis and its next evidence-review date.",
        )
    if open_change_count:
        return _lane(
            "review_trigger",
            "Review trigger",
            "evidence_change_due",
            "Source-backed evidence change needs review",
            f"{open_change_count} unresolved evidence-change item(s) match this ticker.",
            "Review or explicitly defer each source-backed evidence change.",
        )
    if journal_state.overdue:
        return _lane(
            "review_trigger",
            "Review trigger",
            "overdue",
            "The reviewer-authored thesis review is overdue",
            review.evidence,
            "Review the thesis and newer evidence now.",
        )
    if journal_state.review_due_date:
        return _lane(
            "review_trigger",
            "Review trigger",
            "scheduled",
            f"Next evidence review is scheduled for {journal_state.review_due_date}",
            review.evidence,
            "Revisit on the due date or when material source evidence changes.",
        )
    return _lane(
        "review_trigger",
        "Review trigger",
        "unscheduled",
        "No next evidence review is scheduled",
        review.evidence,
        "Schedule the next evidence review.",
    )


def _learning_lane(outcome_status: OutcomeStatus) -> DecisionLabLane:
    if outcome_status.state == "reviewed":
        return _lane(
            "learning",
            "Learning",
            "reviewed",
            "A prior research outcome and learning were reviewed",
            f"{outcome_status.review_count} reviewed learning record(s) are available.",
            outcome_status.next_action,
        )
    if outcome_status.state == "commercial_evidence_blocked":
        return _lane(
            "learning",
            "Learning",
            "commercial_evidence_blocked",
            "Outcome learning is blocked for commercial use",
            f"{outcome_status.commercial_blocker_count} exact-source blocker(s) remain.",
            outcome_status.next_action,
        )
    return _lane(
        "learning",
        "Learning",
        "not_started",
        "No prior research outcome learning is recorded",
        "No learning is synthesized from technical history or price movement.",
        outcome_status.next_action,
    )


def _next_process_step(
    lanes: Mapping[str, DecisionLabLane],
    checks: Mapping[str, ProcessCheck],
) -> str:
    if lanes["evidence"].state == "conflict_review_needed":
        return "Review recorded conflicting evidence before relying on the thesis."
    if lanes["review_trigger"].state == "overdue":
        return "Review the overdue thesis and newer evidence."
    if lanes["plan"].state == "not_started":
        return "Record a current reviewer-authored thesis."
    if lanes["invalidation"].state == "missing":
        return "Record a source-backed invalidation condition."
    if lanes["evidence"].state == "not_started":
        return "Record source-backed research evidence."
    if lanes["review_trigger"].state == "unscheduled":
        return "Schedule the next evidence review."
    if checks["dcf_assumptions_visible"].state == "action_needed":
        return "Restore visible DCF assumptions before scenario review."
    return "Continue monitoring for new source-backed evidence or the next review date."


def _lane_needs_process_work(lane: DecisionLabLane) -> bool:
    work_states = {
        "plan": {"not_started", "unavailable"},
        "evidence": {"not_started", "conflict_review_needed", "unavailable"},
        "invalidation": {"missing", "unavailable"},
        "scenario": {"unavailable"},
        "review_trigger": {"overdue", "unscheduled", "evidence_change_due", "unavailable"},
        "learning": {"commercial_evidence_blocked", "unavailable"},
    }
    return lane.state in work_states[lane.key]


def build_research_decision_lab_state(
    *,
    profile_key: str,
    journal_state: JournalState,
    scorecard: DecisionProcessScorecard,
    outcome_status: OutcomeStatus,
    review_items: Iterable[object] = (),
) -> ResearchDecisionLabState:
    """Compose six independent research-process lanes from existing results."""

    ticker = _text(scorecard.ticker).upper()
    selected_profile = _text(profile_key)
    if (
        not ticker
        or not selected_profile
        or journal_state.ticker != ticker
        or journal_state.profile_key != selected_profile
        or scorecard.profile_key != selected_profile
    ):
        raise ValueError("Decision Lab evidence must match the selected profile and ticker.")

    checks = _check_map(scorecard)
    required_checks = {
        "thesis_documented",
        "evidence_recorded",
        "conflicting_evidence_reviewed",
        "invalidation_documented",
        "review_current",
        "dcf_assumptions_visible",
    }
    if not required_checks.issubset(checks):
        raise ValueError("Decision Lab requires the complete decision-process check contract.")

    open_change_count = _matching_open_change_count(tuple(review_items), ticker)
    lanes = (
        _plan_lane(journal_state, checks),
        _evidence_lane(journal_state, checks),
        _invalidation_lane(journal_state, checks),
        _scenario_lane(checks),
        _review_trigger_lane(journal_state, checks, open_change_count=open_change_count),
        _learning_lane(outcome_status),
    )
    lane_map = {lane.key: lane for lane in lanes}
    next_process_step = _next_process_step(lane_map, checks)
    status = "process_work_needed" if any(_lane_needs_process_work(lane) for lane in lanes) else "process_documented"
    identity = _identity(
        profile_key=selected_profile,
        ticker=ticker,
        status=status,
        lanes=lanes,
        next_process_step=next_process_step,
    )
    return ResearchDecisionLabState(
        profile_key=selected_profile,
        ticker=ticker,
        status=status,
        lanes=lanes,
        next_process_step=next_process_step,
        boundary=BOUNDARY,
        identity=identity,
    )


def unavailable_research_decision_lab_state(
    *,
    profile_key: str,
    ticker: str,
    reason: str,
) -> ResearchDecisionLabState:
    """Return one compact fail-closed contract for invalid saved evidence."""

    selected_profile = _text(profile_key)
    selected_ticker = _text(ticker).upper()
    explanation = _text(reason) or "The saved research-process evidence could not be verified."
    if not selected_profile or not selected_ticker:
        raise ValueError("Decision Lab requires a selected profile and ticker.")
    lanes = tuple(
        _lane(
            key,
            label,
            "unavailable",
            f"{label} is unavailable",
            explanation,
            "Verify the saved research-process evidence before using this lane.",
        )
        for key, label in LANE_ORDER
    )
    next_process_step = "Verify the saved research-process evidence before continuing."
    identity = _identity(
        profile_key=selected_profile,
        ticker=selected_ticker,
        status="unavailable",
        lanes=lanes,
        next_process_step=next_process_step,
    )
    return ResearchDecisionLabState(
        profile_key=selected_profile,
        ticker=selected_ticker,
        status="unavailable",
        lanes=lanes,
        next_process_step=next_process_step,
        boundary=BOUNDARY,
        identity=identity,
    )


def decision_lab_cards(state: ResearchDecisionLabState) -> list[dict[str, object]]:
    cards = [
        {
            "kicker": lane.label.upper(),
            "title": lane.answer,
            "body": lane.next_step,
            "badges": [lane.state.replace("_", " "), "research process"],
            "command": "",
        }
        for lane in state.lanes
    ]
    cards.append(
        {
            "kicker": "NEXT PROCESS STEP",
            "title": state.next_process_step,
            "body": "This process step does not replace the authoritative company research task.",
            "badges": [state.status.replace("_", " "), "documentation workflow"],
            "command": "",
        }
    )
    return cards


def decision_lab_rows(state: ResearchDecisionLabState) -> list[dict[str, str]]:
    return [
        {
            "Lane": lane.label,
            "State": lane.state.replace("_", " "),
            "Answer": lane.answer,
            "Evidence": lane.evidence,
            "Next process step": lane.next_step,
        }
        for lane in state.lanes
    ]


def build_research_discipline_rows(
    states_by_ticker: Mapping[str, ResearchDecisionLabState],
    *,
    focused_tickers: Iterable[str],
) -> tuple[ResearchDisciplineRow, ...]:
    """Preserve focused-cohort order without severity or market-value sorting."""

    normalized = {_text(ticker).upper(): state for ticker, state in states_by_ticker.items()}
    rows: list[ResearchDisciplineRow] = []
    for cohort_order, raw_ticker in enumerate(focused_tickers):
        ticker = _text(raw_ticker).upper()
        state = normalized.get(ticker)
        if state is None:
            continue
        if state.ticker != ticker:
            raise ValueError("Research discipline state must match the focused ticker.")
        due_lanes = tuple(lane.label for lane in state.lanes if _lane_needs_process_work(lane))
        rows.append(
            ResearchDisciplineRow(
                cohort_order=cohort_order,
                ticker=ticker,
                status=state.status,
                due_lanes=due_lanes,
                next_process_step=state.next_process_step,
                identity=state.identity,
            )
        )
    return tuple(rows)


def research_discipline_rows(rows: Iterable[ResearchDisciplineRow]) -> list[dict[str, str]]:
    return [
        {
            "Ticker": row.ticker,
            "Process state": row.status.replace("_", " "),
            "Due lanes": ", ".join(row.due_lanes) or "none due from saved evidence",
            "Next process step": row.next_process_step,
        }
        for row in rows
    ]
