from pathlib import Path

import pytest

from src.continuation_gate import build_continuation_gate
from src.profile_context import CoverageCounts, ProfileContext


def _context(state: str, *, evidence_state: str = "tracked") -> ProfileContext:
    return ProfileContext(
        profile_key="default",
        profile_label="Default",
        data_dir=Path("data"),
        outputs_dir=Path("outputs"),
        source_as_of="2026-06-26",
        readiness_built_at="2026-06-07T03:00:43+00:00",
        snapshot_identity="abc",
        snapshot_identity_short="abc",
        freshness_state=state,
        freshness_message=f"Readiness is {state}.",
        refresh_command="make readiness",
        coverage=CoverageCounts(),
        lane_source_dates=(),
        snapshot_inputs=(),
        readiness_evidence_state=evidence_state,
        readiness_evidence_message=(
            "Readiness artifacts differ from HEAD and are not tracked release evidence."
            if evidence_state == "working_artifact_uncommitted"
            else "Readiness artifacts match HEAD."
        ),
    )


def test_stale_readiness_routes_to_no_write_preview():
    gate = build_continuation_gate(_context("stale"))

    assert gate.state == "inspection_only"
    assert gate.next_safe_command == "make readiness-preview TOP_N=20"
    assert gate.rebuild_command == ""
    assert gate.suppress_execution is True
    assert "broad refresh" in gate.stop_rule


def test_current_readiness_does_not_override_source_routing():
    gate = build_continuation_gate(_context("current"))

    assert gate.state == "current"
    assert gate.next_safe_command == ""
    assert gate.rebuild_command == ""
    assert gate.suppress_execution is False
    assert gate.stop_rule == ""


def test_current_dates_with_uncommitted_readiness_evidence_fail_closed():
    gate = build_continuation_gate(_context("current", evidence_state="working_artifact_uncommitted"))

    assert gate.state == "inspection_only"
    assert gate.next_safe_command == "make readiness-preview TOP_N=20"
    assert gate.suppress_execution is True
    assert "not tracked release evidence" in gate.reason.lower()


def test_current_dates_with_unverified_default_evidence_fail_closed():
    context = _context("current", evidence_state="unverified")
    context = ProfileContext(
        **{
            **context.__dict__,
            "readiness_evidence_message": "Readiness artifacts could not be compared with tracked HEAD evidence.",
        }
    )

    gate = build_continuation_gate(context)

    assert gate.state == "inspection_required"
    assert gate.next_safe_command == "make readiness-preview TOP_N=20"
    assert gate.suppress_execution is True
    assert "could not be compared" in gate.reason.lower()


@pytest.mark.parametrize("state", ["mixed", "missing", "unexpected"])
def test_incomplete_or_unknown_readiness_fails_closed_to_inspection(state: str):
    gate = build_continuation_gate(_context(state))

    assert gate.state == "inspection_required"
    assert gate.next_safe_command == "make readiness-preview TOP_N=20"
    assert gate.suppress_execution is True
    assert "readiness-rebuild" in gate.stop_rule
