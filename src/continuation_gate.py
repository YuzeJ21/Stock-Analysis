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
    if context.freshness_state == "current":
        return ContinuationGate(
            state="current",
            next_safe_command="",
            reason=context.freshness_message,
            rebuild_command=rebuild_command,
            stop_rule="",
            suppress_execution=False,
        )

    state = "inspection_only" if context.freshness_state == "stale" else "inspection_required"
    return ContinuationGate(
        state=state,
        next_safe_command=READINESS_PREVIEW_COMMAND,
        reason=context.freshness_message,
        rebuild_command=rebuild_command,
        stop_rule=(
            "Do not start broad refresh, source-proof, apply, or readiness-rebuild work from stale or "
            "incomplete readiness counts."
        ),
        suppress_execution=True,
    )
