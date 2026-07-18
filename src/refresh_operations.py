from __future__ import annotations

from dataclasses import dataclass


REFRESH_STAGES = (
    "fetch",
    "normalize",
    "validate",
    "quarantine",
    "preview",
    "publish_snapshot",
    "rebuild_readiness",
    "detect_changes",
)


@dataclass(frozen=True)
class RefreshStage:
    name: str
    state: str


@dataclass(frozen=True)
class ProviderAttempt:
    provider: str
    session_id: str
    outcome: str


@dataclass(frozen=True)
class RefreshOperationRequest:
    lane: str
    provider_order: tuple[str, ...]
    available_providers: tuple[str, ...]
    batch_limit: int
    freshness_policy: str
    retry_cap: int = 1
    session_id: str = "local-session"
    attempts: tuple[ProviderAttempt, ...] = ()


@dataclass(frozen=True)
class RefreshOperationPlan:
    lane: str
    status: str
    selected_provider: str | None
    skipped_providers: tuple[str, ...]
    failure_reason: str | None
    batch_limit: int
    freshness_policy: str
    automatic_apply_enabled: bool
    stages: tuple[RefreshStage, ...]


@dataclass(frozen=True)
class RefreshBatch:
    provider: str
    row_count: int
    expected_schema_identity: str
    received_schema_identity: str
    provenance_complete: bool
    duplicate_rows: int
    stale_rows: int
    partial_batch: bool


@dataclass(frozen=True)
class RefreshBatchDecision:
    status: str
    failure_reasons: tuple[str, ...]
    preview_allowed: bool
    publish_snapshot: bool
    rebuild_readiness: bool
    detect_changes: bool


def build_refresh_operation_plan(request: RefreshOperationRequest) -> RefreshOperationPlan:
    if not request.lane.strip():
        raise ValueError("lane is required")
    if not request.provider_order:
        raise ValueError("provider_order is required")
    if request.batch_limit < 1:
        raise ValueError("batch_limit must be positive")
    if request.retry_cap < 1:
        raise ValueError("retry_cap must be positive")

    available = set(request.available_providers)
    skipped: list[str] = []
    failure_reasons: list[str] = []
    for provider in request.provider_order:
        provider_attempts = tuple(attempt for attempt in request.attempts if attempt.provider == provider)
        failed_this_session = any(
            attempt.session_id == request.session_id and attempt.outcome == "failed"
            for attempt in provider_attempts
        )
        failed_attempts = sum(attempt.outcome == "failed" for attempt in provider_attempts)

        if provider not in available:
            skipped.append(provider)
            failure_reasons.append("provider_unavailable")
            continue
        if failed_this_session:
            skipped.append(provider)
            failure_reasons.append("identical_provider_attempt")
            continue
        if failed_attempts >= request.retry_cap:
            skipped.append(provider)
            failure_reasons.append("retry_cap_reached")
            continue

        return RefreshOperationPlan(
            lane=request.lane,
            status="planned",
            selected_provider=provider,
            skipped_providers=tuple(skipped),
            failure_reason=None,
            batch_limit=request.batch_limit,
            freshness_policy=request.freshness_policy,
            automatic_apply_enabled=False,
            stages=tuple(RefreshStage(name=stage, state="pending") for stage in REFRESH_STAGES),
        )

    if "retry_cap_reached" in failure_reasons:
        failure_reason = "retry_cap_reached"
    elif "identical_provider_attempt" in failure_reasons:
        failure_reason = "identical_provider_attempt"
    else:
        failure_reason = "provider_unavailable"
    return RefreshOperationPlan(
        lane=request.lane,
        status="blocked",
        selected_provider=None,
        skipped_providers=tuple(skipped),
        failure_reason=failure_reason,
        batch_limit=request.batch_limit,
        freshness_policy=request.freshness_policy,
        automatic_apply_enabled=False,
        stages=tuple(RefreshStage(name=stage, state="blocked") for stage in REFRESH_STAGES),
    )


def evaluate_refresh_batch(batch: RefreshBatch) -> RefreshBatchDecision:
    if batch.row_count < 0 or batch.duplicate_rows < 0 or batch.stale_rows < 0:
        raise ValueError("row counts cannot be negative")

    reasons: list[str] = []
    if batch.expected_schema_identity != batch.received_schema_identity:
        reasons.append("schema_changed")
    if not batch.provenance_complete:
        reasons.append("provenance_missing")
    if batch.duplicate_rows:
        reasons.append("duplicate_rows")
    if batch.stale_rows:
        reasons.append("stale_rows")

    if reasons:
        return RefreshBatchDecision(
            status="quarantine",
            failure_reasons=tuple(reasons),
            preview_allowed=False,
            publish_snapshot=False,
            rebuild_readiness=False,
            detect_changes=False,
        )
    if batch.partial_batch:
        return RefreshBatchDecision(
            status="partial",
            failure_reasons=("partial_batch",),
            preview_allowed=False,
            publish_snapshot=False,
            rebuild_readiness=False,
            detect_changes=False,
        )
    return RefreshBatchDecision(
        status="ready_for_preview",
        failure_reasons=(),
        preview_allowed=True,
        publish_snapshot=False,
        rebuild_readiness=False,
        detect_changes=False,
    )
