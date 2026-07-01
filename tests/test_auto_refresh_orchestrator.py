from src.auto_refresh_orchestrator import (
    AutoGateInput,
    build_auto_refresh_status_payload,
    build_default_lane_policies,
    build_scheduler_plan,
    evaluate_auto_apply_gate,
    main,
    render_auto_refresh_status,
    render_scheduler_runbook,
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


def test_blocked_gate_can_be_report_only_for_scheduler_pivot(capsys):
    exit_code = main(
        [
            "--gate-lane",
            "fundamentals_dcf",
            "--changed-rows",
            "0",
            "--validation-status",
            "not_run",
            "--preview-status",
            "not_run",
            "--source-provenance",
            "missing",
            "--provider-status",
            "unavailable",
            "--blocked-exit-zero",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "status: blocked" in output
    assert "outcome: still_blocked" in output
    assert "pivot to the next executable lane" in output


def test_scheduler_runbook_is_compact_and_pivot_oriented():
    preflight = {
        "source_activation": {"status": "not_required", "reason": "queues_reviewed"},
        "source_activation_console_v2": {
            "next_executable_lane": "coverage_workflow_evidence",
            "next_executable_command": "make project-status",
            "operator_summary": {
                "needs_setup": "fmp, alpha_vantage, finnhub",
                "avoid_repeating": "fundamentals_share_count_source_ladder",
                "next_step_reason": "Use provider setup before reopening broad ticker proof loops.",
            },
        },
    }
    runbook = render_scheduler_runbook(build_scheduler_plan(schedule="daily"), preflight)

    assert "Auto Refresh Daily Runbook" in runbook
    assert "make session-source-preflight" in runbook
    assert "Current source gate:" in runbook
    assert "can_run_now: coverage_workflow_evidence" in runbook
    assert "needs_setup: fmp, alpha_vantage, finnhub" in runbook
    assert "avoid_repeating: fundamentals_share_count_source_ladder" in runbook
    assert "next_executable_command: make project-status" in runbook
    assert "do not open broad lane loops" in runbook
    assert "1. Daily Price Coverage" in runbook
    assert "2. Daily SEC Filing Share Count" in runbook
    assert "3. Daily Fundamentals / DCF Source Ladder" in runbook
    assert "ALLOW_BLOCKED_GATE=1 make auto-apply-gate" in runbook
    assert "record still_blocked and pivot" in runbook
    assert "Weekly Peer Candidate Context" not in runbook
    assert "Optional Earnings / Analyst Estimates" not in runbook


def test_auto_refresh_status_combines_source_activation_and_next_runbook():
    preflight = {
        "source_activation": {
            "status": "not_required",
            "reason": "executable_source_available",
            "next_action": "Use the relevant reviewed dry-run, validate, preview, and apply gate.",
        },
        "source_categories": {
            "free_public_available": ["stooq", "yahoo", "sec", "sec_submissions"],
            "keyed_free_tier_available": [],
            "optional_broker_disabled": ["ibkr"],
            "paid_or_locked": ["fmp", "alpha_vantage", "finnhub"],
        },
        "source_activation_console_v2": {
            "next_executable_lane": "coverage_workflow_evidence",
            "next_executable_command": "make project-status",
            "free_tier_batch_limits": {
                "fmp": {"recommended_daily_request_limit": 250, "recommended_batch_size": 25},
                "alpha_vantage": {"recommended_daily_request_limit": 25, "recommended_batch_size": 5},
                "finnhub": {"recommended_daily_request_limit": 60, "recommended_batch_size": 10},
            },
            "operator_summary": {
                "can_run_now": "coverage_workflow_evidence",
                "needs_setup": "fmp, alpha_vantage, finnhub",
                "avoid_repeating": "fundamentals_share_count_source_ladder",
                "next_step": "make project-status",
                "next_step_reason": "Wait for new source data or improve workflow evidence.",
            },
        },
    }

    status = render_auto_refresh_status(preflight, build_scheduler_plan(schedule="daily"))

    assert "Auto Refresh Status" in status
    assert "source_activation: not_required" in status
    assert "can_run_now: coverage_workflow_evidence" in status
    assert "needs_setup: fmp, alpha_vantage, finnhub" in status
    assert "avoid_repeating: fundamentals_share_count_source_ladder" in status
    assert "next_executable_command: make project-status" in status
    assert "next_runbook: make auto-refresh-runbook SCHEDULE=daily" in status
    assert "free_public_available: stooq, yahoo, sec, sec_submissions" in status
    assert "free_tier_batch_limits: fmp<=250/day and <=25/run; alpha_vantage<=25/day and <=5/run; finnhub<=60/day and <=10/run" in status
    assert "generated CSV/JSON/report churn stays excluded" in status


def test_auto_refresh_status_payload_is_scheduler_parseable():
    preflight = {
        "source_activation": {"status": "not_required", "reason": "executable_source_available"},
        "source_categories": {
            "free_public_available": ["stooq", "sec"],
            "keyed_free_tier_available": [],
            "optional_broker_disabled": ["ibkr"],
            "paid_or_locked": ["fmp"],
        },
        "source_activation_console_v2": {
            "next_executable_lane": "coverage_workflow_evidence",
            "next_executable_command": "make project-status",
            "operator_summary": {
                "needs_setup": "fmp",
                "avoid_repeating": "fundamentals_share_count_source_ladder",
                "next_step_reason": "No unreviewed source-backed rows.",
            },
        },
    }

    payload = build_auto_refresh_status_payload(preflight, build_scheduler_plan(schedule="weekly"))

    assert payload["source_activation"] == "not_required"
    assert payload["can_run_now"] == "coverage_workflow_evidence"
    assert payload["needs_setup"] == "fmp"
    assert payload["avoid_repeating"] == "fundamentals_share_count_source_ladder"
    assert payload["next_executable_command"] == "make project-status"
    assert payload["next_runbook"] == "make auto-refresh-runbook SCHEDULE=weekly"
    assert payload["source_categories"]["free_public_available"] == "stooq, sec"
    assert payload["artifact_policy"] == "generated CSV/JSON/report churn stays excluded unless intentionally reviewed evidence."
