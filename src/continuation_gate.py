"""Fail-closed continuation routing for selected-profile readiness."""

from __future__ import annotations

from dataclasses import dataclass

from src.profile_context import ProfileContext


READINESS_PREVIEW_COMMAND = "make readiness-preview TOP_N=20"


@dataclass(frozen=True)
class ContinuationGate:
    state: str
    next_safe_command: str
    reason: str
    rebuild_command: str
    stop_rule: str
    suppress_execution: bool


def build_continuation_gate(context: ProfileContext) -> ContinuationGate:
    """Return the one safe continuation action for the selected profile."""

    rebuild_command = context.refresh_command or "make readiness"
    evidence_state = getattr(context, "readiness_evidence_state", "not_applicable")
    evidence_is_uncommitted = evidence_state == "working_artifact_uncommitted"
    evidence_is_unverified = evidence_state == "unverified"
    if (
        context.freshness_state == "current"
        and not evidence_is_uncommitted
        and not evidence_is_unverified
    ):
        return ContinuationGate(
            state="current",
            next_safe_command="",
            reason=context.freshness_message,
            rebuild_command=rebuild_command,
            stop_rule="",
            suppress_execution=False,
        )

    state = "inspection_only" if context.freshness_state == "stale" or evidence_is_uncommitted else "inspection_required"
    evidence_blocks = evidence_is_uncommitted or evidence_is_unverified
    reason = (
        getattr(context, "readiness_evidence_message", "Readiness evidence origin is unavailable.")
        if evidence_blocks
        else context.freshness_message
    )
    return ContinuationGate(
        state=state,
        next_safe_command=READINESS_PREVIEW_COMMAND,
        reason=reason,
        rebuild_command=rebuild_command,
        stop_rule=(
            "Do not start broad refresh, source-proof, apply, or readiness-rebuild work from stale, "
            "incomplete, or uncommitted working readiness counts."
        ),
        suppress_execution=True,
    )
