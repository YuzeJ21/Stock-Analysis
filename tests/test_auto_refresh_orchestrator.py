from src.auto_refresh_orchestrator import (
    AutoGateInput,
    build_default_lane_policies,
    build_scheduler_plan,
    evaluate_auto_apply_gate,
    render_scheduler_plan,
)


def test_auto_gate_allows_source_backed_narrow_valid_preview():
    decision = evaluate_auto_apply_gate(
        AutoGateInput(
            lane="fundamentals_dcf",
            changed_rows=3,
            max_batch_size=25,
            validation_status="valid",
            preview_status="valid",
            rejected_rows=0,
            source_provenance_present=True,
            fabricated_values_detected=False,
            unexpected_scope_change=False,
            provider_available=True,
        )
    )

    assert decision.status == "auto_apply_ready"
    assert decision.outcome == "auto_supported"
    assert "make imports-apply" in " ".join(decision.required_next_commands)


def test_auto_gate_blocks_rejected_rows_and_missing_provenance():
    decision = evaluate_auto_apply_gate(
        AutoGateInput(
            lane="share_count",
            changed_rows=1,
            max_batch_size=10,
            validation_status="valid",
            preview_status="valid",
            rejected_rows=2,
            source_provenance_present=False,
            fabricated_values_detected=False,
            unexpected_scope_change=False,
            provider_available=True,
        )
    )

    assert decision.status == "blocked"
    assert decision.outcome == "still_blocked"
    assert "rejected rows are present" in "; ".join(decision.reasons)
    assert "source provenance is missing" in "; ".join(decision.reasons)


def test_scheduler_plan_separates_daily_weekly_and_optional_lanes():
    policies = build_default_lane_policies()
    plan = build_scheduler_plan(policies, schedule="all")
    rendered = render_scheduler_plan(plan)

    assert policies[0].lane == "daily_price_refresh"
    assert plan.daily_commands[0].startswith("make price-refresh-loop")
    assert any("sec-filing-share-stage" in command for command in plan.daily_commands)
    assert "make auto-apply-gate" in rendered
    assert any("peer" in command for command in plan.weekly_commands)
    assert any("optional" in command for command in plan.optional_commands)
    assert "research-only" in rendered.lower()
    assert "no broker integration" in rendered.lower()
    assert "auto_supported" in rendered
