"""Fail-closed continuation routing for selected-profile readiness."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.profile_context import (
    READINESS_PREVIEW_COMMAND,
    READINESS_PREVIEW_NOTE,
    ProfileContext,
    readiness_inspection_route,
)


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

    inspection_action, inspection_note = readiness_inspection_route(
        getattr(context, "profile_key", "default"),
        getattr(context, "profile_label", "Default"),
        getattr(context, "data_dir", Path("data")),
    )
    rebuild_command = inspection_action
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
        next_safe_command=inspection_action,
        reason=f"{reason} {inspection_note}" if READINESS_PREVIEW_NOTE not in reason else reason,
        rebuild_command=rebuild_command,
        stop_rule=(
            "Do not start broad refresh, source-proof, apply, or readiness-rebuild work from stale, "
            "incomplete, or uncommitted working readiness counts."
        ),
        suppress_execution=True,
    )
