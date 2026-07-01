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
    optional_policy = next(policy for policy in policies if policy.lane == "optional_earnings_estimates")
    assert "candidate_context_only" in optional_policy.source_boundary
    assert "EPS/revenue estimate fields" in optional_policy.source_boundary
    assert "research-only" in rendered.lower()
    assert "no broker integration" in rendered.lower()
    assert "auto_supported" in rendered
    assert "make session-source-preflight" in rendered
    assert "Free-tier fallback caps: fmp<=250/day and <=25/run" in rendered
    assert "alpha_vantage<=25/day and <=5/run" in rendered
    assert "finnhub<=60/day and <=10/run" in rendered
    assert "Do not repeat exhausted source-proof queues" in rendered
    assert "make coverage-expansion-loop TOP_N=10" in rendered


def test_schedule_specific_plans_only_render_selected_lane_policies():
    policies = build_default_lane_policies()

    daily = render_scheduler_plan(build_scheduler_plan(policies, schedule="daily"))
    assert "Daily Price Coverage" in daily
    assert "Daily SEC Filing Share Count" in daily
    assert "Daily Fundamentals / DCF Source Ladder" in daily
    assert "Weekly Peer Candidate Context" not in daily
    assert "Optional Earnings / Analyst Estimates" not in daily

    weekly = render_scheduler_plan(build_scheduler_plan(policies, schedule="weekly"))
    assert "Weekly Peer Candidate Context" in weekly
    assert "Daily Price Coverage" not in weekly
    assert "Optional Earnings / Analyst Estimates" not in weekly

    optional = render_scheduler_plan(build_scheduler_plan(policies, schedule="optional"))
    assert "Optional Earnings / Analyst Estimates" in optional
    assert "Daily Price Coverage" not in optional
    assert "Weekly Peer Candidate Context" not in optional
