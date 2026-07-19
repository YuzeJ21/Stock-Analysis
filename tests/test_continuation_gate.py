from pathlib import Path

import pytest

from src.continuation_gate import build_continuation_gate
from src.profile_context import CoverageCounts, ProfileContext


def _context(state: str) -> ProfileContext:
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
    )


def test_stale_readiness_routes_to_no_write_preview():
    gate = build_continuation_gate(_context("stale"))

    assert gate.state == "inspection_only"
    assert gate.next_safe_command == "make readiness-preview TOP_N=20"
    assert gate.rebuild_command == "make readiness"
    assert gate.suppress_execution is True
    assert "broad refresh" in gate.stop_rule


def test_current_readiness_does_not_override_source_routing():
    gate = build_continuation_gate(_context("current"))

    assert gate.state == "current"
    assert gate.next_safe_command == ""
    assert gate.rebuild_command == "make readiness"
    assert gate.suppress_execution is False
    assert gate.stop_rule == ""


@pytest.mark.parametrize("state", ["mixed", "missing", "unexpected"])
def test_incomplete_or_unknown_readiness_fails_closed_to_inspection(state: str):
    gate = build_continuation_gate(_context(state))

    assert gate.state == "inspection_required"
    assert gate.next_safe_command == "make readiness-preview TOP_N=20"
    assert gate.suppress_execution is True
    assert "readiness-rebuild" in gate.stop_rule
