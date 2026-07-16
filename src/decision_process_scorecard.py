"""Profile-scoped research-process checks without company scoring."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Iterable, Mapping

from src.research_thesis_journal import JournalState


@dataclass(frozen=True)
class ProcessCheck:
    key: str
    label: str
    state: str
    evidence: str
    next_action: str


@dataclass(frozen=True)
class DecisionProcessScorecard:
    ticker: str
    profile_key: str
    status: str
    scorecard_identity: str
    checks: tuple[ProcessCheck, ...]
    complete_count: int
    action_needed_count: int
    neutral_count: int
    boundary: str


def _text(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null", "<na>"} else text


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _check(key: str, label: str, state: str, evidence: str, next_action: str) -> ProcessCheck:
    return ProcessCheck(key, label, state, evidence, next_action)


def _conflict_check(state: JournalState) -> ProcessCheck:
    if not state.conflicting_evidence:
        return _check(
            "conflicting_evidence_reviewed",
            "Conflicting evidence reviewed",
            "not_observed",
            "No conflicting evidence is recorded for this profile and ticker.",
            "Revisit this check when conflicting evidence is recorded.",
        )
    latest_conflict = max(_timestamp(row.recorded_at) for row in state.conflicting_evidence)
    later_reviews = [
        row
        for row in state.entries
        if row.entry_type == "review" and _timestamp(row.recorded_at) > latest_conflict
    ]
    if later_reviews:
        return _check(
            "conflicting_evidence_reviewed",
            "Conflicting evidence reviewed",
            "complete",
            f"A later review follows {len(state.conflicting_evidence)} conflicting evidence item(s).",
            "Revisit when new conflicting evidence arrives.",
        )
    return _check(
        "conflicting_evidence_reviewed",
        "Conflicting evidence reviewed",
        "action_needed",
        f"{len(state.conflicting_evidence)} conflicting evidence item(s) have no later review entry.",
        "Record a later review that addresses the conflicting evidence.",
    )


def _dcf_check(report_payload: Mapping[str, object]) -> ProcessCheck:
    asset_type = _text(report_payload.get("asset_type")).lower()
    if asset_type in {"etf", "index_proxy", "fund"}:
        return _check(
            "dcf_assumptions_visible",
            "DCF assumptions visible",
            "not_applicable",
            "Operating-company DCF is excluded for this monitor-context asset.",
            "Use market, theme, liquidity, or risk context instead.",
        )
    readiness = report_payload.get("valuation_readiness") if isinstance(report_payload.get("valuation_readiness"), Mapping) else {}
    dcf_ready = bool((readiness or {}).get("dcf_ready"))
    valuation = report_payload.get("valuation_snapshot") if isinstance(report_payload.get("valuation_snapshot"), Mapping) else {}
    result = (valuation or {}).get("dcf_result") if isinstance((valuation or {}).get("dcf_result"), Mapping) else {}
    assumptions = (result or {}).get("assumptions") if isinstance((result or {}).get("assumptions"), Mapping) else {}
    if not dcf_ready:
        return _check(
            "dcf_assumptions_visible",
            "DCF assumptions visible",
            "blocked",
            "DCF readiness is blocked, so assumptions and numerical outputs stay withheld.",
            "Resolve trusted DCF inputs before reviewing assumptions.",
        )
    if assumptions:
        return _check(
            "dcf_assumptions_visible",
            "DCF assumptions visible",
            "complete",
            f"{len(assumptions)} DCF assumption field(s) are visible in the report.",
            "Review the assumptions and sensitivity before interpreting scenario math.",
        )
    return _check(
        "dcf_assumptions_visible",
        "DCF assumptions visible",
        "action_needed",
        "DCF is marked ready but no assumption fields are visible.",
        "Review the DCF payload and restore explicit assumptions before interpretation.",
    )


def build_decision_process_scorecard(
    report_payload: Mapping[str, object],
    *,
    profile_key: str,
    journal_state: JournalState,
    review_items: Iterable[object],
) -> DecisionProcessScorecard:
    """Build deterministic process checks from selected-profile evidence only."""

    ticker = _text(report_payload.get("ticker")).upper()
    if not ticker or journal_state.profile_key != profile_key or journal_state.ticker != ticker:
        raise ValueError("Decision-process evidence must match the selected profile and ticker.")

    readiness = report_payload.get("valuation_readiness") if isinstance(report_payload.get("valuation_readiness"), Mapping) else {}
    checks: list[ProcessCheck] = [
        _check(
            "readiness_checked",
            "Selected-profile readiness checked",
            "complete" if readiness else "unavailable",
            "The stock report carries selected-profile readiness evidence." if readiness else "No readiness payload is available.",
            "Continue to the documented research process." if readiness else "Rebuild and verify the selected-profile report.",
        )
    ]

    has_thesis = journal_state.current_thesis is not None
    checks.append(
        _check(
            "thesis_documented",
            "Current thesis documented",
            "complete" if has_thesis else "action_needed",
            journal_state.current_thesis.summary if has_thesis else "No reviewer-authored thesis is recorded.",
            "Review the current thesis." if has_thesis else "Record a reviewer-authored thesis and review date.",
        )
    )
    evidence_count = sum(
        len(rows)
        for rows in (
            journal_state.supporting_evidence,
            journal_state.conflicting_evidence,
            journal_state.contextual_evidence,
            journal_state.catalysts,
            journal_state.risks,
        )
    )
    checks.append(
        _check(
            "evidence_recorded",
            "Research evidence recorded",
            "complete" if evidence_count else "action_needed",
            f"{evidence_count} reviewed evidence, catalyst, or risk item(s) are recorded." if evidence_count else "No reviewed evidence, catalyst, or risk is recorded.",
            "Review source evidence for completeness." if evidence_count else "Record source-backed evidence before relying on the thesis.",
        )
    )
    checks.append(_conflict_check(journal_state))
    invalidation_count = len(journal_state.invalidation_conditions)
    checks.append(
        _check(
            "invalidation_documented",
            "Invalidation condition documented",
            "complete" if invalidation_count else "action_needed",
            f"{invalidation_count} source-backed invalidation condition(s) are recorded." if invalidation_count else "No invalidation condition is recorded.",
            "Revisit invalidation conditions when evidence changes." if invalidation_count else "Record what evidence would invalidate the thesis.",
        )
    )
    confidence_count = len(journal_state.confidence_history)
    checks.append(
        _check(
            "confidence_documented",
            "Confidence history documented",
            "complete" if confidence_count else "action_needed",
            f"{confidence_count} confidence observation(s) are recorded." if confidence_count else "No confidence history is recorded.",
            "Update confidence only when reviewed evidence changes." if confidence_count else "Record evidence-linked confidence without turning it into conviction advice.",
        )
    )
    if journal_state.overdue:
        review_state = "action_needed"
        review_evidence = f"The review date {journal_state.review_due_date} is overdue."
        review_action = "Review the thesis and newer evidence now."
    elif journal_state.review_due_date:
        review_state = "complete"
        review_evidence = f"Next review is scheduled for {journal_state.review_due_date}."
        review_action = "Revisit on the due date or when material evidence changes."
    else:
        review_state = "action_needed"
        review_evidence = "No next review date is scheduled."
        review_action = "Schedule the next evidence review."
    checks.append(_check("review_current", "Review date current", review_state, review_evidence, review_action))

    open_items = [
        item
        for item in review_items
        if _text(getattr(getattr(item, "event", None), "ticker", "")).upper() == ticker
    ]
    checks.append(
        _check(
            "evidence_changes_reviewed",
            "Evidence changes reviewed",
            "action_needed" if open_items else "complete",
            f"{len(open_items)} open evidence-change task(s) remain." if open_items else "No unresolved evidence-change task is queued for this ticker.",
            "Review or explicitly defer each open evidence change." if open_items else "Continue monitoring deterministic source changes.",
        )
    )
    checks.append(_dcf_check(report_payload))

    action_needed_count = sum(check.state in {"action_needed", "unavailable"} for check in checks)
    complete_count = sum(check.state == "complete" for check in checks)
    neutral_count = len(checks) - action_needed_count - complete_count
    status = "process_documented" if action_needed_count == 0 else "process_work_needed"
    boundary = "Research-process documentation only; no company grade, expected return, performance claim, or action is produced."
    identity_payload = {
        "ticker": ticker,
        "profile_key": profile_key,
        "checks": [asdict(check) for check in checks],
    }
    identity = hashlib.sha256(json.dumps(identity_payload, sort_keys=True).encode("utf-8")).hexdigest()
    return DecisionProcessScorecard(
        ticker=ticker,
        profile_key=profile_key,
        status=status,
        scorecard_identity=identity,
        checks=tuple(checks),
        complete_count=complete_count,
        action_needed_count=action_needed_count,
        neutral_count=neutral_count,
        boundary=boundary,
    )


def decision_process_rows(scorecard: DecisionProcessScorecard) -> list[dict[str, str]]:
    labels = {
        "complete": "Complete",
        "action_needed": "Action needed",
        "not_observed": "Not observed",
        "blocked": "Blocked by readiness",
        "not_applicable": "Not applicable",
        "unavailable": "Unavailable",
    }
    return [
        {
            "Process Check": check.label,
            "State": labels.get(check.state, check.state.replace("_", " ").title()),
            "Evidence": check.evidence,
            "Next Review Step": check.next_action,
        }
        for check in scorecard.checks
    ]
