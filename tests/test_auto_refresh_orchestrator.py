import ast
import inspect
import json
import subprocess
from pathlib import Path

import pytest

from src.auto_refresh_orchestrator import (
    AutoGateInput,
    available_refresh_providers,
    build_auto_refresh_status_payload,
    build_default_lane_policies,
    build_scheduler_plan,
    evaluate_auto_apply_gate,
    main,
    render_auto_refresh_status,
    render_scheduler_runbook,
    render_scheduler_plan,
)
from src.refresh_operations import ProviderAttempt
from src.continuation_gate import ContinuationGate


def test_primary_auto_orchestrator_logic_stays_inside_the_three_approved_functions():
    source_path = Path(__file__).resolve().parents[1] / "src" / "auto_refresh_orchestrator.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    top_level_function_names = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert "_profile_scoped_read_only_command" not in top_level_function_names
    assert "_primary_lane_proof" not in top_level_function_names


def test_auto_apply_gate_profile_is_keyword_only():
    assert inspect.signature(evaluate_auto_apply_gate).parameters["profile"].kind is inspect.Parameter.KEYWORD_ONLY


def test_auto_refresh_status_routes_stale_readiness_to_inspection_only():
    preflight = {
        "source_activation": {"status": "not_required", "reason": "executable_source_available"},
        "source_categories": {"free_public_available": ["sec"]},
        "source_activation_console_v2": {
            "next_executable_lane": "sec_fundamentals_share_count",
            "next_executable_command": "make coverage-frontier TOP_N=10",
        },
    }
    gate = ContinuationGate(
        state="inspection_only",
        next_safe_command="make readiness-preview TOP_N=20",
        reason="Selected-profile source dates are newer than saved readiness.",
        rebuild_command="make readiness",
        stop_rule="Do not start broad refresh or source-proof work.",
        suppress_execution=True,
    )
    plan = build_scheduler_plan(schedule="daily")

    payload = build_auto_refresh_status_payload(preflight, plan, continuation_gate=gate)
    status = render_auto_refresh_status(preflight, plan, continuation_gate=gate)
    runbook = render_scheduler_runbook(plan, preflight, continuation_gate=gate)

    assert payload["can_run_now"] == "inspection_only"
    assert payload["next_executable_command"] == "make readiness-preview TOP_N=20"
    assert payload["continuation_gate"]["suppress_execution"] is True
    assert "Readiness continuation gate: inspection_only" in status
    assert "Stale readiness continuation gate" not in status
    assert "refresh_operations below are planning context only" in status
    assert "next_executable_command: make coverage-frontier TOP_N=10" not in status
    assert "Start:\n- make readiness-preview TOP_N=20" in runbook
    assert "- make coverage-frontier TOP_N=10" not in runbook.split("Lane loop:", 1)[0]


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


def test_auto_gate_ready_fundamentals_returns_one_complete_selected_profile_proof():
    decision = evaluate_auto_apply_gate(
        AutoGateInput(
            lane="fundamentals_dcf", changed_rows=3, max_batch_size=25, validation_status="valid", preview_status="valid",
            rejected_rows=0, source_provenance_present=True, fabricated_values_detected=False,
            unexpected_scope_change=False, provider_available=True,
        ),
        profile="local",
    )

    assert decision.required_next_commands == (
        "make readiness-snapshot PROFILE=local && STOCK_RESEARCH_DATA_PROFILE=local make imports-validate IMPORT_TICKERS=<ticker-or-reviewed-batch> IMPORT_FILES=fundamentals.csv && STOCK_RESEARCH_DATA_PROFILE=local make imports-preview IMPORT_TICKERS=<ticker-or-reviewed-batch> IMPORT_FILES=fundamentals.csv && STOCK_RESEARCH_DATA_PROFILE=local make imports-apply IMPORT_TICKERS=<ticker-or-reviewed-batch> IMPORT_FILES=fundamentals.csv && make reviewed-batch-compare PROFILE=local LANE=fundamentals BATCH_ID=<reviewed_batch_id> REVIEW_DATE=<yyyy-mm-dd>",
    )


@pytest.mark.parametrize("lane", ("daily_sec_filing_share_count", "daily_fundamentals_dcf"))
def test_default_fundamentals_and_share_count_proofs_scope_imports_to_fundamentals_csv(lane):
    policy = next(policy for policy in build_default_lane_policies(profile="local") if policy.lane == lane)

    assert policy.gated_apply_command.count("IMPORT_FILES=fundamentals.csv") == 3
    assert policy.proof_command.count("IMPORT_FILES=fundamentals.csv") == 3


@pytest.mark.parametrize("profile", ("default", "demo"))
def test_auto_gate_blocks_non_local_price_writes_with_local_profile_unblock(profile):
    decision = evaluate_auto_apply_gate(
        AutoGateInput(
            lane="daily_price_refresh", changed_rows=1, max_batch_size=25, validation_status="valid", preview_status="valid",
            rejected_rows=0, source_provenance_present=True, fabricated_values_detected=False,
            unexpected_scope_change=False, provider_available=True,
        ),
        profile=profile,
    )

    assert decision.status == "blocked"
    assert decision.required_next_commands == ("Price writes are unavailable outside local profile; rerun with PROFILE=local.",)


def test_non_local_price_gate_keeps_existing_blocker_reasons():
    decision = evaluate_auto_apply_gate(
        AutoGateInput(
            lane="daily_price_refresh", changed_rows=0, max_batch_size=25, validation_status="invalid", preview_status="invalid",
            rejected_rows=1, source_provenance_present=False, fabricated_values_detected=True,
            unexpected_scope_change=True, provider_available=False,
        ),
        profile="demo",
    )

    assert decision.status == "blocked"
    assert decision.required_next_commands == ("Price writes are unavailable outside local profile; rerun with PROFILE=local.",)
    assert decision.reasons == (
        "provider or source path is unavailable",
        "validation did not pass",
        "preview did not pass",
        "rejected rows are present",
        "source provenance is missing",
        "fabricated values were detected",
        "preview changed an unexpected scope",
        "no changed rows to apply",
        "price writes require the local profile",
    )


def test_auto_gate_returns_complete_local_price_proof():
    decision = evaluate_auto_apply_gate(
        AutoGateInput(
            lane="daily_price_refresh", changed_rows=1, max_batch_size=25, validation_status="valid", preview_status="valid",
            rejected_rows=0, source_provenance_present=True, fabricated_values_detected=False,
            unexpected_scope_change=False, provider_available=True,
        ),
        profile="local",
    )

    assert decision.required_next_commands == (
        "make readiness-snapshot PROFILE=local && STOCK_RESEARCH_DATA_PROFILE=local make price-validate && STOCK_RESEARCH_DATA_PROFILE=local make price-preview && STOCK_RESEARCH_DATA_PROFILE=local make price-apply && make reviewed-batch-compare PROFILE=local LANE=daily_price_refresh BATCH_ID=<reviewed_batch_id> REVIEW_DATE=<yyyy-mm-dd>",
    )


def test_scheduler_plan_builds_demo_policies_without_ambient_profile_fallback(monkeypatch):
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "local")

    plan = build_scheduler_plan(profile="demo")

    assert all("PROFILE=demo" in policy.proof_command or policy.proof_command.startswith("Price writes are unavailable") for policy in plan.policies)
    assert all(
        "STOCK_RESEARCH_DATA_PROFILE=demo" in policy.dry_run_command
        or policy.dry_run_command.startswith("Price writes are unavailable")
        for policy in plan.policies
    )


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
    assert plan.daily_commands[0] == "Price writes are unavailable outside local profile; rerun with PROFILE=local."
    assert all(
        "DRY_RUN=1" in command or "queue" in command or command.startswith("Price writes are unavailable")
        for command in plan.daily_commands
    )
    assert "sec-filing-share-stage" not in rendered
    assert "imports-apply" not in rendered
    assert "make auto-apply-gate" not in rendered
    assert "SLEEP_SECONDS" not in rendered
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


def test_scheduler_plan_uses_provider_availability_and_bounded_attempt_history():
    plan = build_scheduler_plan(
        schedule="daily",
        available_providers=("yahoo", "sec_submissions"),
        session_id="run-01",
        retry_cap=1,
        attempts=(ProviderAttempt("yahoo", "run-01", "failed"),),
    )
    operations = {operation.lane: operation for operation in plan.refresh_operations}

    assert operations["daily_price_refresh"].status == "blocked"
    assert operations["daily_price_refresh"].selected_provider is None
    assert operations["daily_price_refresh"].failure_reason == "identical_provider_attempt"
    assert operations["daily_sec_filing_share_count"].status == "planned"
    assert operations["daily_sec_filing_share_count"].selected_provider == "sec_submissions"
    assert operations["daily_fundamentals_dcf"].status == "blocked"
    assert plan.retry_cap == 1
    assert plan.session_id == "run-01"


def test_scheduler_cli_accepts_provider_state_and_attempts(capsys):
    exit_code = main(
        [
            "--schedule",
            "daily",
            "--available-providers",
            "yahoo,sec_submissions",
            "--session-id",
            "run-01",
            "--retry-cap",
            "1",
            "--provider-attempt",
            "yahoo:run-01:failed",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    operations = {item["lane"]: item for item in payload["refresh_operations"]}
    assert exit_code == 0
    assert operations["daily_price_refresh"]["status"] == "blocked"
    assert operations["daily_price_refresh"]["failure_reason"] == "identical_provider_attempt"
    assert operations["daily_sec_filing_share_count"]["selected_provider"] == "sec_submissions"


def test_preflight_availability_maps_to_refresh_provider_contracts():
    preflight = {
        "sources": {
            "sec": {"status": "available"},
            "sec_submissions": {"status": "unavailable"},
            "yfinance_stage": {"status": "unavailable"},
            "price_ladder": {"status": "unavailable"},
            "fmp": {"status": "available"},
            "alpha_vantage": {"status": "unavailable"},
            "finnhub": {"status": "unavailable"},
        }
    }

    available = available_refresh_providers(preflight)

    assert "sec_companyfacts" in available
    assert "sec_submissions" not in available
    assert "sec_filing_document" not in available
    assert "stooq" not in available
    assert "yahoo" not in available
    assert "fmp" in available
    assert {"local_industry", "sic", "sector"}.issubset(available)


def test_status_cli_derives_fail_closed_provider_plans_from_preflight(monkeypatch, capsys):
    preflight = {
        "source_activation": {"status": "required", "reason": "providers_unavailable"},
        "source_categories": {},
        "source_activation_console_v2": {},
        "sources": {
            "sec": {"status": "unavailable"},
            "sec_submissions": {"status": "unavailable"},
            "yfinance_stage": {"status": "unavailable"},
            "price_ladder": {"status": "unavailable"},
            "fmp": {"status": "unavailable"},
            "alpha_vantage": {"status": "unavailable"},
            "finnhub": {"status": "unavailable"},
        },
    }
    monkeypatch.setattr(
        "src.auto_refresh_orchestrator.build_session_source_preflight",
        lambda _root: preflight,
    )

    exit_code = main(["--schedule", "daily", "--status", "--json"])

    payload = json.loads(capsys.readouterr().out)
    operations = {item["lane"]: item for item in payload["refresh_operations"]}
    assert exit_code == 0
    assert operations["daily_price_refresh"]["status"] == "blocked"
    assert operations["daily_sec_filing_share_count"]["status"] == "blocked"
    assert operations["daily_fundamentals_dcf"]["status"] == "blocked"
    assert all(item["selected_provider"] is None for item in operations.values())


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
    assert "can_run_now: workflow evidence only; current source-proof queues are exhausted" in runbook
    assert "needs_setup: fmp, alpha_vantage, finnhub" in runbook
    assert "avoid_repeating: fundamentals/share-count source ladder" in runbook
    assert "coverage_workflow_evidence" not in runbook
    assert "fundamentals_share_count_source_ladder" not in runbook
    assert "next_executable_command: make project-status" in runbook
    assert "do not open broad lane loops" in runbook
    assert "1. Daily Price Coverage" in runbook
    assert "2. Daily SEC Filing Share Count" in runbook
    assert "3. Daily Fundamentals / DCF Source Ladder" in runbook
    assert "imports-apply" not in runbook
    assert "sec-filing-share-stage" not in runbook
    assert "make auto-apply-gate" not in runbook
    assert "gated apply:" not in runbook
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
    assert "can_run_now: workflow evidence only; current source-proof queues are exhausted" in status
    assert "needs_setup: fmp, alpha_vantage, finnhub" in status
    assert "avoid_repeating: fundamentals/share-count source ladder" in status
    assert "coverage_workflow_evidence" not in status
    assert "fundamentals_share_count_source_ladder" not in status
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
    assert payload["refresh_operations"][0]["automatic_apply_enabled"] is False


def test_status_payload_reconciles_an_unverified_plan_with_preflight_availability():
    preflight = {
        "source_activation": {"status": "not_required"},
        "source_categories": {},
        "source_activation_console_v2": {},
        "sources": {
            "sec": {"status": "available"},
            "sec_submissions": {"status": "available"},
            "yfinance_stage": {"status": "unavailable"},
            "price_ladder": {"status": "unavailable"},
            "fmp": {"status": "unavailable"},
            "alpha_vantage": {"status": "unavailable"},
            "finnhub": {"status": "unavailable"},
        },
    }

    payload = build_auto_refresh_status_payload(preflight, build_scheduler_plan(schedule="daily"))
    operations = {item["lane"]: item for item in payload["refresh_operations"]}

    assert operations["daily_sec_filing_share_count"]["selected_provider"] == "sec_submissions"
    assert operations["daily_fundamentals_dcf"]["selected_provider"] == "sec_companyfacts"
    assert operations["daily_price_refresh"]["status"] == "blocked"


def test_refresh_operations_make_targets_are_read_only_cli_contracts():
    root = Path(__file__).resolve().parents[1]
    for target, flag in (
        ("refresh-operations-status", "--status"),
        ("refresh-operations-runbook", "--runbook"),
    ):
        result = subprocess.run(
            ["make", "-n", target, "SCHEDULE=daily"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0
        assert "src.auto_refresh_orchestrator" in result.stdout
        assert flag in result.stdout
        assert "imports-apply" not in result.stdout
        assert "price-refresh-loop MAX_CANDIDATES" not in result.stdout
