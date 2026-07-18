from src.refresh_operations import (
    REFRESH_STAGES,
    ProviderAttempt,
    RefreshBatch,
    RefreshOperationRequest,
    build_refresh_operation_plan,
    evaluate_refresh_batch,
)
from src.auto_refresh_orchestrator import build_default_lane_policies, build_scheduler_plan


def test_plan_is_read_only_and_uses_the_first_available_provider():
    plan = build_refresh_operation_plan(
        RefreshOperationRequest(
            lane="quarterly_actuals",
            provider_order=("primary", "fallback"),
            available_providers=("fallback",),
            batch_limit=25,
            freshness_policy="current_filing_only",
        )
    )

    assert plan.status == "planned"
    assert plan.selected_provider == "fallback"
    assert plan.automatic_apply_enabled is False
    assert tuple(stage.name for stage in plan.stages) == REFRESH_STAGES
    assert all(stage.state == "pending" for stage in plan.stages)


def test_plan_blocks_unavailable_or_exhausted_provider_paths_without_repeating_them():
    unavailable = build_refresh_operation_plan(
        RefreshOperationRequest(
            lane="prices",
            provider_order=("primary",),
            available_providers=(),
            batch_limit=10,
            freshness_policy="daily",
        )
    )
    repeated = build_refresh_operation_plan(
        RefreshOperationRequest(
            lane="prices",
            provider_order=("primary", "fallback"),
            available_providers=("primary", "fallback"),
            batch_limit=10,
            freshness_policy="daily",
            retry_cap=2,
            session_id="refresh-01",
            attempts=(
                ProviderAttempt("primary", "refresh-01", "failed"),
                ProviderAttempt("fallback", "prior-session", "failed"),
                ProviderAttempt("fallback", "prior-session", "failed"),
            ),
        )
    )

    assert unavailable.status == "blocked"
    assert unavailable.failure_reason == "provider_unavailable"
    assert repeated.status == "blocked"
    assert repeated.failure_reason == "retry_cap_reached"
    assert repeated.skipped_providers == ("primary", "fallback")


def test_plan_skips_a_failed_provider_already_attempted_in_this_session():
    plan = build_refresh_operation_plan(
        RefreshOperationRequest(
            lane="fundamentals",
            provider_order=("primary", "fallback"),
            available_providers=("primary", "fallback"),
            batch_limit=10,
            freshness_policy="filing_date",
            retry_cap=3,
            session_id="refresh-01",
            attempts=(ProviderAttempt("primary", "refresh-01", "failed"),),
        )
    )

    assert plan.status == "planned"
    assert plan.selected_provider == "fallback"
    assert plan.skipped_providers == ("primary",)


def test_batch_quarantines_schema_provenance_duplicates_and_stale_rows():
    result = evaluate_refresh_batch(
        RefreshBatch(
            provider="sec",
            row_count=4,
            expected_schema_identity="quarterly_actuals/v1",
            received_schema_identity="quarterly_actuals/v2",
            provenance_complete=False,
            duplicate_rows=1,
            stale_rows=2,
            partial_batch=False,
        )
    )

    assert result.status == "quarantine"
    assert result.publish_snapshot is False
    assert result.rebuild_readiness is False
    assert result.failure_reasons == (
        "schema_changed",
        "provenance_missing",
        "duplicate_rows",
        "stale_rows",
    )


def test_partial_batch_is_withheld_from_preview_and_publish():
    result = evaluate_refresh_batch(
        RefreshBatch(
            provider="sec",
            row_count=3,
            expected_schema_identity="quarterly_actuals/v1",
            received_schema_identity="quarterly_actuals/v1",
            provenance_complete=True,
            duplicate_rows=0,
            stale_rows=0,
            partial_batch=True,
        )
    )

    assert result.status == "partial"
    assert result.failure_reasons == ("partial_batch",)
    assert result.preview_allowed is False
    assert result.publish_snapshot is False


def test_scheduler_lanes_keep_automatic_apply_disabled_and_expose_read_only_plans():
    policies = build_default_lane_policies()
    scheduler_plan = build_scheduler_plan(policies, schedule="daily")

    assert all(policy.auto_apply is False for policy in policies)
    assert scheduler_plan.refresh_operations
    assert all(plan.automatic_apply_enabled is False for plan in scheduler_plan.refresh_operations)
