from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from src.earnings_nowcast_backtest import (
    CALIBRATION_OUTCOME_DEFINITIONS,
    BacktestEvent,
    BacktestReport,
    CalibrationBin,
    ProbabilityObservation,
    assess_probability_calibration,
)
from src.earnings_nowcast_cohort import _calibration_backtest_semantics_verified
from src.earnings_nowcast_contract import parse_utc_timestamp
from src.earnings_nowcast_model import NowcastConfig, classify_consensus_gap


BUNDLE_SCHEMA_VERSION = "calibration-evidence-bundle-v1"
PREVIEW_SCHEMA_VERSION = "calibration-evidence-bundle-preview-v1"
MAX_BUNDLE_BYTES = 16 * 1024 * 1024
_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "bundle_id",
        "created_at",
        "cohort",
        "observations",
        "backtest_report",
        "evidence_references",
    }
)
_PLACEHOLDERS = frozenset(
    {"unknown", "tbd", "todo", "placeholder", "example", "sample"}
)
_FISCAL_PERIOD = re.compile(r"^[0-9]{4}-Q[1-4]$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COHORT_KEYS = frozenset(
    {
        "cohort_id",
        "outcome_definition",
        "minimum_events",
        "selection_rule",
        "period_start",
        "period_end",
        "expected_event_identities",
        "excluded_events",
    }
)
_IDENTITY_KEYS = frozenset({"ticker", "fiscal_period", "as_of_timestamp"})
_OBSERVATION_KEYS = frozenset(
    _IDENTITY_KEYS | {"outcome_definition", "probability", "outcome"}
)
_EXCLUSION_KEYS = frozenset(_IDENTITY_KEYS | {"reason", "detail"})
_REFERENCE_KEYS = frozenset(
    {"source_id", "source_ref", "rights_decision_ref", "review_status"}
)
_EVENT_KEYS = frozenset(
    {
        "ticker",
        "fiscal_period",
        "as_of_timestamp",
        "latest_input_timestamp",
        "target_reported_at",
        "input_source_ids",
        "revenue_forecast",
        "revenue_low",
        "revenue_high",
        "revenue_actual",
        "eps_forecast",
        "eps_low",
        "eps_high",
        "eps_actual",
        "consensus_revenue",
        "consensus_eps",
        "prior_year_revenue",
        "prior_year_eps",
        "relative_classification",
        "model_version",
        "input_snapshot_hash",
    }
)
_REPORT_KEYS = frozenset(
    {
        "verdict",
        "event_count",
        "valid_event_count",
        "excluded_count",
        "exclusion_reasons",
        "excluded_events",
        "revenue_mae",
        "revenue_median_absolute_error",
        "revenue_wape",
        "eps_mae",
        "eps_median_absolute_error",
        "directional_accuracy",
        "interval_coverage",
        "revenue_interval_coverage",
        "eps_interval_coverage",
        "joint_interval_coverage",
        "benchmark_metrics",
        "benchmark_failures",
        "leakage_failures",
        "failures",
        "events",
    }
)


class CalibrationEvidenceBundleError(ValueError):
    pass


@dataclass(frozen=True)
class _LoadedCalibrationEvidenceBundle:
    path: Path
    raw_bytes: bytes
    bundle_sha256: str
    payload: Mapping[str, object]


@dataclass(frozen=True)
class CalibrationEvidenceBlocker:
    gate: str
    detail: str


@dataclass(frozen=True)
class CalibrationEvidenceBundlePreview:
    schema_version: str
    state: str
    bundle_id: str
    bundle_sha256: str
    outcome_definition: str
    expected_event_count: int
    observation_count: int
    backtest_event_count: int
    excluded_event_count: int
    brier_score: float | None
    benchmark_brier_score: float | None
    calibration_error: float | None
    calibration_bins: tuple[CalibrationBin, ...]
    passed_gates: tuple[str, ...]
    blocked_gates: tuple[CalibrationEvidenceBlocker, ...]
    evidence_digest: str | None
    backtest_evidence_digest: str | None
    probability_state: str = "withheld"
    probability_exposure: bool = False
    readiness_promotions: tuple[str, ...] = ()
    persistence: bool = False
    preview_receipt_persisted: bool = False
    external_source_review_required: bool = True
    independent_review_required: bool = True
    boundary: str = (
        "Read-only internal consistency preview; no readiness activation, "
        "probability exposure, source attestation, or investment advice."
    )


@dataclass(frozen=True)
class _Cohort:
    cohort_id: str
    outcome_definition: str
    minimum_events: int
    selection_rule: str
    period_start: str
    period_end: str
    expected_event_identities: tuple[tuple[str, str, str], ...]
    excluded_events: tuple["_DeclaredExclusion", ...]


@dataclass(frozen=True)
class _DeclaredExclusion:
    identity: tuple[str, str, str]
    reason: str
    detail: str


@dataclass(frozen=True)
class _EvidenceReference:
    source_id: str
    source_ref: str
    rights_decision_ref: str
    review_status: str


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    output: dict[str, object] = {}
    for key, value in pairs:
        if key in output:
            raise CalibrationEvidenceBundleError(f"duplicate JSON key: {key}")
        output[key] = value
    return output


def load_calibration_evidence_bundle(
    path: Path | str,
) -> _LoadedCalibrationEvidenceBundle:
    resolved = Path(path).expanduser().resolve()
    if not resolved.exists():
        raise CalibrationEvidenceBundleError(f"bundle does not exist: {resolved}")
    if not resolved.is_file():
        raise CalibrationEvidenceBundleError("bundle path must be a regular file")
    if resolved.stat().st_size > MAX_BUNDLE_BYTES:
        raise CalibrationEvidenceBundleError("bundle exceeds the 16 MiB limit")

    raw = resolved.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CalibrationEvidenceBundleError("bundle must be valid UTF-8") from exc
    try:
        payload = json.loads(text, object_pairs_hook=_unique_object)
    except CalibrationEvidenceBundleError:
        raise
    except json.JSONDecodeError as exc:
        raise CalibrationEvidenceBundleError("bundle contains malformed JSON") from exc

    if not isinstance(payload, dict):
        raise CalibrationEvidenceBundleError("bundle root must be a JSON object")
    keys = set(payload)
    missing = sorted(_TOP_LEVEL_KEYS - keys)
    unknown = sorted(keys - _TOP_LEVEL_KEYS)
    if missing:
        raise CalibrationEvidenceBundleError(
            f"missing top-level keys: {', '.join(missing)}"
        )
    if unknown:
        raise CalibrationEvidenceBundleError(
            f"unknown top-level keys: {', '.join(unknown)}"
        )
    if payload["schema_version"] != BUNDLE_SCHEMA_VERSION:
        raise CalibrationEvidenceBundleError(
            "unsupported calibration evidence bundle schema"
        )

    return _LoadedCalibrationEvidenceBundle(
        path=resolved,
        raw_bytes=raw,
        bundle_sha256=hashlib.sha256(raw).hexdigest(),
        payload=payload,
    )


def _expect_object(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise CalibrationEvidenceBundleError(f"{path} must be an object")
    return value


def _expect_exact_keys(
    value: Mapping[str, object],
    keys: frozenset[str],
    path: str,
) -> None:
    present = set(value)
    missing = sorted(keys - present)
    unknown = sorted(present - keys)
    if missing:
        raise CalibrationEvidenceBundleError(
            f"{path} missing keys: {', '.join(missing)}"
        )
    if unknown:
        raise CalibrationEvidenceBundleError(
            f"{path} unknown keys: {', '.join(unknown)}"
        )


def _expect_list(value: object, path: str) -> list[object]:
    if not isinstance(value, list):
        raise CalibrationEvidenceBundleError(f"{path} must be an array")
    return value


def _expect_text(
    value: object,
    path: str,
    *,
    allow_placeholder: bool = False,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CalibrationEvidenceBundleError(f"{path} must be non-empty text")
    cleaned = value.strip()
    if not allow_placeholder and cleaned.casefold() in _PLACEHOLDERS:
        raise CalibrationEvidenceBundleError(f"{path} must not be a placeholder")
    return cleaned


def _expect_int(value: object, path: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise CalibrationEvidenceBundleError(
            f"{path} must be an integer greater than or equal to {minimum}"
        )
    return value


def _expect_finite_number(value: object, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalibrationEvidenceBundleError(f"{path} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise CalibrationEvidenceBundleError(f"{path} must be a finite number")
    return number


def _optional_number(value: object, path: str) -> float | None:
    return None if value is None else _expect_finite_number(value, path)


def _expect_timestamp(value: object, path: str) -> str:
    try:
        return parse_utc_timestamp(value, label=path).isoformat()
    except (TypeError, ValueError) as exc:
        raise CalibrationEvidenceBundleError(str(exc)) from exc


def _expect_period(value: object, path: str) -> str:
    period = _expect_text(value, path).upper()
    if not _FISCAL_PERIOD.fullmatch(period):
        raise CalibrationEvidenceBundleError(f"{path} must use YYYY-Q[1-4]")
    return period


def _period_key(period: str) -> tuple[int, int]:
    year, quarter = period.split("-Q", 1)
    return int(year), int(quarter)


def _parse_identity(value: object, path: str) -> tuple[str, str, str]:
    row = _expect_object(value, path)
    _expect_exact_keys(row, _IDENTITY_KEYS, path)
    ticker = _expect_text(row["ticker"], f"{path}.ticker").upper()
    period = _expect_period(row["fiscal_period"], f"{path}.fiscal_period")
    as_of = _expect_timestamp(row["as_of_timestamp"], f"{path}.as_of_timestamp")
    return ticker, period, as_of


def _parse_exclusion(value: object, index: int) -> _DeclaredExclusion:
    path = f"cohort.excluded_events[{index}]"
    row = _expect_object(value, path)
    _expect_exact_keys(row, _EXCLUSION_KEYS, path)
    identity = _parse_identity(
        {key: row[key] for key in _IDENTITY_KEYS},
        path,
    )
    return _DeclaredExclusion(
        identity=identity,
        reason=_expect_text(row["reason"], f"{path}.reason"),
        detail=_expect_text(row["detail"], f"{path}.detail"),
    )


def _parse_cohort(value: object) -> _Cohort:
    row = _expect_object(value, "cohort")
    _expect_exact_keys(row, _COHORT_KEYS, "cohort")
    outcome_definition = _expect_text(
        row["outcome_definition"], "cohort.outcome_definition"
    ).lower()
    if outcome_definition not in CALIBRATION_OUTCOME_DEFINITIONS:
        raise CalibrationEvidenceBundleError(
            "cohort.outcome_definition is not supported"
        )
    expected_rows = _expect_list(
        row["expected_event_identities"], "cohort.expected_event_identities"
    )
    excluded_rows = _expect_list(row["excluded_events"], "cohort.excluded_events")
    return _Cohort(
        cohort_id=_expect_text(row["cohort_id"], "cohort.cohort_id"),
        outcome_definition=outcome_definition,
        minimum_events=_expect_int(
            row["minimum_events"], "cohort.minimum_events", minimum=1
        ),
        selection_rule=_expect_text(row["selection_rule"], "cohort.selection_rule"),
        period_start=_expect_period(row["period_start"], "cohort.period_start"),
        period_end=_expect_period(row["period_end"], "cohort.period_end"),
        expected_event_identities=tuple(
            _parse_identity(item, f"cohort.expected_event_identities[{index}]")
            for index, item in enumerate(expected_rows)
        ),
        excluded_events=tuple(
            _parse_exclusion(item, index) for index, item in enumerate(excluded_rows)
        ),
    )


def _parse_observation(value: object, index: int) -> ProbabilityObservation:
    path = f"observations[{index}]"
    row = _expect_object(value, path)
    _expect_exact_keys(row, _OBSERVATION_KEYS, path)
    identity = _parse_identity({key: row[key] for key in _IDENTITY_KEYS}, path)
    outcome_definition = _expect_text(
        row["outcome_definition"], f"{path}.outcome_definition"
    ).lower()
    if outcome_definition not in CALIBRATION_OUTCOME_DEFINITIONS:
        raise CalibrationEvidenceBundleError(
            f"{path}.outcome_definition is not supported"
        )
    probability = _expect_finite_number(row["probability"], f"{path}.probability")
    if not 0 <= probability <= 1:
        raise CalibrationEvidenceBundleError(
            f"{path}.probability must be between 0 and 1"
        )
    if not isinstance(row["outcome"], bool):
        raise CalibrationEvidenceBundleError(f"{path}.outcome must be Boolean")
    return ProbabilityObservation(
        ticker=identity[0],
        fiscal_period=identity[1],
        as_of_timestamp=identity[2],
        outcome_definition=outcome_definition,
        probability=probability,
        outcome=row["outcome"],
    )


def _parse_backtest_event(value: object, index: int) -> BacktestEvent:
    path = f"backtest_report.events[{index}]"
    row = _expect_object(value, path)
    _expect_exact_keys(row, _EVENT_KEYS, path)
    identity = _parse_identity({key: row[key] for key in _IDENTITY_KEYS}, path)
    source_rows = _expect_list(row["input_source_ids"], f"{path}.input_source_ids")
    source_ids = tuple(
        _expect_text(item, f"{path}.input_source_ids[{source_index}]")
        for source_index, item in enumerate(source_rows)
    )
    if not source_ids:
        raise CalibrationEvidenceBundleError(
            f"{path}.input_source_ids must not be empty"
        )
    model_version = _expect_text(row["model_version"], f"{path}.model_version")
    input_snapshot_hash = _expect_text(
        row["input_snapshot_hash"], f"{path}.input_snapshot_hash"
    )
    if not _SHA256.fullmatch(input_snapshot_hash):
        raise CalibrationEvidenceBundleError(
            f"{path}.input_snapshot_hash must be a lowercase SHA-256 digest"
        )
    classification = _expect_text(
        row["relative_classification"], f"{path}.relative_classification"
    ).lower()
    if classification not in {"higher", "aligned", "lower", "withheld"}:
        raise CalibrationEvidenceBundleError(
            f"{path}.relative_classification is not supported"
        )
    return BacktestEvent(
        ticker=identity[0],
        fiscal_period=identity[1],
        as_of_timestamp=identity[2],
        latest_input_timestamp=_expect_timestamp(
            row["latest_input_timestamp"], f"{path}.latest_input_timestamp"
        ),
        target_reported_at=_expect_timestamp(
            row["target_reported_at"], f"{path}.target_reported_at"
        ),
        input_source_ids=source_ids,
        revenue_forecast=_optional_number(
            row["revenue_forecast"], f"{path}.revenue_forecast"
        ),
        revenue_low=_optional_number(row["revenue_low"], f"{path}.revenue_low"),
        revenue_high=_optional_number(row["revenue_high"], f"{path}.revenue_high"),
        revenue_actual=_optional_number(
            row["revenue_actual"], f"{path}.revenue_actual"
        ),
        eps_forecast=_optional_number(row["eps_forecast"], f"{path}.eps_forecast"),
        eps_low=_optional_number(row["eps_low"], f"{path}.eps_low"),
        eps_high=_optional_number(row["eps_high"], f"{path}.eps_high"),
        eps_actual=_optional_number(row["eps_actual"], f"{path}.eps_actual"),
        consensus_revenue=_optional_number(
            row["consensus_revenue"], f"{path}.consensus_revenue"
        ),
        consensus_eps=_optional_number(row["consensus_eps"], f"{path}.consensus_eps"),
        prior_year_revenue=_optional_number(
            row["prior_year_revenue"], f"{path}.prior_year_revenue"
        ),
        prior_year_eps=_optional_number(
            row["prior_year_eps"], f"{path}.prior_year_eps"
        ),
        relative_classification=classification,
        model_version=model_version,
        input_snapshot_hash=input_snapshot_hash,
    )


def _parse_string_tuple(value: object, path: str) -> tuple[str, ...]:
    rows = _expect_list(value, path)
    return tuple(
        _expect_text(item, f"{path}[{index}]", allow_placeholder=True)
        for index, item in enumerate(rows)
    )


def _parse_count_mapping(value: object, path: str) -> dict[str, int]:
    row = _expect_object(value, path)
    output: dict[str, int] = {}
    for key, count in row.items():
        normalized = _expect_text(key, f"{path}.key")
        output[normalized] = _expect_int(count, f"{path}.{normalized}", minimum=1)
    return output


def _parse_number_mapping(value: object, path: str) -> dict[str, float]:
    row = _expect_object(value, path)
    output: dict[str, float] = {}
    for key, number in row.items():
        normalized = _expect_text(key, f"{path}.key")
        output[normalized] = _expect_finite_number(number, f"{path}.{normalized}")
    return output


def _parse_backtest_report(value: object) -> BacktestReport:
    row = _expect_object(value, "backtest_report")
    _expect_exact_keys(row, _REPORT_KEYS, "backtest_report")
    event_rows = _expect_list(row["events"], "backtest_report.events")
    return BacktestReport(
        verdict=_expect_text(row["verdict"], "backtest_report.verdict"),
        event_count=_expect_int(
            row["event_count"], "backtest_report.event_count", minimum=0
        ),
        valid_event_count=_expect_int(
            row["valid_event_count"],
            "backtest_report.valid_event_count",
            minimum=0,
        ),
        excluded_count=_expect_int(
            row["excluded_count"], "backtest_report.excluded_count", minimum=0
        ),
        exclusion_reasons=_parse_count_mapping(
            row["exclusion_reasons"], "backtest_report.exclusion_reasons"
        ),
        excluded_events=_parse_string_tuple(
            row["excluded_events"], "backtest_report.excluded_events"
        ),
        revenue_mae=_optional_number(row["revenue_mae"], "backtest_report.revenue_mae"),
        revenue_median_absolute_error=_optional_number(
            row["revenue_median_absolute_error"],
            "backtest_report.revenue_median_absolute_error",
        ),
        revenue_wape=_optional_number(
            row["revenue_wape"], "backtest_report.revenue_wape"
        ),
        eps_mae=_optional_number(row["eps_mae"], "backtest_report.eps_mae"),
        eps_median_absolute_error=_optional_number(
            row["eps_median_absolute_error"],
            "backtest_report.eps_median_absolute_error",
        ),
        directional_accuracy=_optional_number(
            row["directional_accuracy"], "backtest_report.directional_accuracy"
        ),
        interval_coverage=_optional_number(
            row["interval_coverage"], "backtest_report.interval_coverage"
        ),
        revenue_interval_coverage=_optional_number(
            row["revenue_interval_coverage"],
            "backtest_report.revenue_interval_coverage",
        ),
        eps_interval_coverage=_optional_number(
            row["eps_interval_coverage"], "backtest_report.eps_interval_coverage"
        ),
        joint_interval_coverage=_optional_number(
            row["joint_interval_coverage"],
            "backtest_report.joint_interval_coverage",
        ),
        benchmark_metrics=_parse_number_mapping(
            row["benchmark_metrics"], "backtest_report.benchmark_metrics"
        ),
        benchmark_failures=_parse_string_tuple(
            row["benchmark_failures"], "backtest_report.benchmark_failures"
        ),
        leakage_failures=_parse_string_tuple(
            row["leakage_failures"], "backtest_report.leakage_failures"
        ),
        failures=_parse_string_tuple(row["failures"], "backtest_report.failures"),
        events=tuple(
            _parse_backtest_event(item, index) for index, item in enumerate(event_rows)
        ),
    )


def _parse_evidence_reference(value: object, index: int) -> _EvidenceReference:
    path = f"evidence_references[{index}]"
    row = _expect_object(value, path)
    _expect_exact_keys(row, _REFERENCE_KEYS, path)
    review_status = _expect_text(row["review_status"], f"{path}.review_status").lower()
    if review_status not in {"unreviewed", "review_required", "reviewed"}:
        raise CalibrationEvidenceBundleError(f"{path}.review_status is not supported")
    return _EvidenceReference(
        source_id=_expect_text(row["source_id"], f"{path}.source_id"),
        source_ref=_expect_text(row["source_ref"], f"{path}.source_ref"),
        rights_decision_ref=_expect_text(
            row["rights_decision_ref"], f"{path}.rights_decision_ref"
        ),
        review_status=review_status,
    )


_CONTRACT_GATES = (
    "fixed_minimum_100_events",
    "cohort_identity_unique",
    "cohort_period_bounds",
    "expected_observation_identity_match",
    "expected_backtest_identity_match",
    "excluded_identity_disjoint",
    "exclusion_accounting_match",
    "source_reference_coverage",
    "event_chronology",
    "strict_declared_outcome_match",
    "relative_classification_match",
    "backtest_report_semantics_match",
    "calibration_evidence_digest_present",
    "backtest_evidence_digest_present",
)


def _append_blocker(
    blockers: list[CalibrationEvidenceBlocker], gate: str, detail: str
) -> None:
    if gate not in {item.gate for item in blockers}:
        blockers.append(CalibrationEvidenceBlocker(gate=gate, detail=detail))


def _identity(event: BacktestEvent) -> tuple[str, str, str]:
    return event.ticker, event.fiscal_period, event.as_of_timestamp


def _classification_matches(event: BacktestEvent) -> bool:
    tolerance = NowcastConfig().aligned_tolerance_pct
    if (
        event.revenue_forecast is not None
        and event.consensus_revenue is not None
        and event.revenue_low is not None
        and event.revenue_high is not None
    ):
        expected = classify_consensus_gap(
            event.consensus_revenue,
            event.revenue_low,
            event.revenue_high,
            tolerance_pct=tolerance,
        )
    elif (
        event.eps_forecast is not None
        and event.consensus_eps is not None
        and event.eps_low is not None
        and event.eps_high is not None
    ):
        expected = classify_consensus_gap(
            event.consensus_eps,
            event.eps_low,
            event.eps_high,
            tolerance_pct=tolerance,
        )
    else:
        expected = "withheld"
    return event.relative_classification == expected


def preview_calibration_evidence_bundle(
    path: Path | str,
) -> CalibrationEvidenceBundlePreview:
    loaded = load_calibration_evidence_bundle(path)
    payload = loaded.payload
    bundle_id = _expect_text(payload["bundle_id"], "bundle_id")
    _expect_timestamp(payload["created_at"], "created_at")
    cohort = _parse_cohort(payload["cohort"])
    observation_rows = _expect_list(payload["observations"], "observations")
    observations = tuple(
        _parse_observation(item, index) for index, item in enumerate(observation_rows)
    )
    report = _parse_backtest_report(payload["backtest_report"])
    reference_rows = _expect_list(payload["evidence_references"], "evidence_references")
    if not reference_rows:
        raise CalibrationEvidenceBundleError("evidence_references must not be empty")
    references = tuple(
        _parse_evidence_reference(item, index)
        for index, item in enumerate(reference_rows)
    )

    blockers: list[CalibrationEvidenceBlocker] = []
    expected = cohort.expected_event_identities
    excluded = tuple(item.identity for item in cohort.excluded_events)
    observation_identities = tuple(
        observation.event_identity for observation in observations
    )
    backtest_identities = tuple(_identity(event) for event in report.events)

    if cohort.minimum_events != 100:
        _append_blocker(
            blockers,
            "fixed_minimum_100_events",
            "The bundle must use the fixed 100-event minimum.",
        )
    if (
        len(set(expected)) != len(expected)
        or len(set(excluded)) != len(excluded)
        or len(set(observation_identities)) != len(observation_identities)
        or len(set(backtest_identities)) != len(backtest_identities)
    ):
        _append_blocker(
            blockers,
            "cohort_identity_unique",
            "Expected, excluded, observation, and retained-event identities must be unique.",
        )

    period_start = _period_key(cohort.period_start)
    period_end = _period_key(cohort.period_end)
    bounded_periods = tuple(identity[1] for identity in expected + excluded)
    if period_start > period_end or any(
        not period_start <= _period_key(period) <= period_end
        for period in bounded_periods
    ):
        _append_blocker(
            blockers,
            "cohort_period_bounds",
            "Cohort period bounds must be ordered and contain every declared identity.",
        )
    if set(expected) != set(observation_identities):
        _append_blocker(
            blockers,
            "expected_observation_identity_match",
            "Expected cohort identities must exactly match observation identities.",
        )
    if set(expected) != set(backtest_identities):
        _append_blocker(
            blockers,
            "expected_backtest_identity_match",
            "Expected cohort identities must exactly match retained backtest identities.",
        )
    if set(expected) & set(excluded):
        _append_blocker(
            blockers,
            "excluded_identity_disjoint",
            "Expected and excluded identities must be disjoint.",
        )

    declared_reason_counts: dict[str, int] = {}
    for item in cohort.excluded_events:
        declared_reason_counts[item.reason] = (
            declared_reason_counts.get(item.reason, 0) + 1
        )
    if (
        report.excluded_count != len(cohort.excluded_events)
        or dict(report.exclusion_reasons) != declared_reason_counts
        or len(report.excluded_events) != len(cohort.excluded_events)
        or set(report.excluded_events)
        != {item.detail for item in cohort.excluded_events}
    ):
        _append_blocker(
            blockers,
            "exclusion_accounting_match",
            "Declared exclusions must match report counts, reasons, and details.",
        )

    reference_ids = tuple(item.source_id for item in references)
    required_source_ids = {
        source_id for event in report.events for source_id in event.input_source_ids
    }
    if (
        len(set(reference_ids)) != len(reference_ids)
        or required_source_ids != set(reference_ids)
        or any(
            len(set(event.input_source_ids)) != len(event.input_source_ids)
            for event in report.events
        )
    ):
        _append_blocker(
            blockers,
            "source_reference_coverage",
            "Evidence references must uniquely and exactly cover ordered event source IDs.",
        )

    chronology_valid = True
    for event in report.events:
        try:
            latest_input = parse_utc_timestamp(event.latest_input_timestamp)
            as_of = parse_utc_timestamp(event.as_of_timestamp)
            target = parse_utc_timestamp(event.target_reported_at)
        except (TypeError, ValueError):
            chronology_valid = False
            break
        if not latest_input <= as_of < target:
            chronology_valid = False
            break
    if not chronology_valid:
        _append_blocker(
            blockers,
            "event_chronology",
            "Every retained event must satisfy latest input <= cutoff < target report time.",
        )

    observations_by_identity = {
        observation.event_identity: observation for observation in observations
    }
    strict_outcomes_valid = all(
        observation.outcome_definition == cohort.outcome_definition
        for observation in observations
    )
    for event in report.events:
        observation = observations_by_identity.get(_identity(event))
        if observation is None:
            strict_outcomes_valid = False
            continue
        if cohort.outcome_definition == "revenue_actual_strictly_above_consensus":
            actual, consensus = event.revenue_actual, event.consensus_revenue
        else:
            actual, consensus = event.eps_actual, event.consensus_eps
        if (
            actual is None
            or consensus is None
            or observation.outcome is not (actual > consensus)
        ):
            strict_outcomes_valid = False
    if not strict_outcomes_valid:
        _append_blocker(
            blockers,
            "strict_declared_outcome_match",
            "Observation outcomes must match the declared strict actual-above-consensus rule.",
        )
    if not all(_classification_matches(event) for event in report.events):
        _append_blocker(
            blockers,
            "relative_classification_match",
            "Stored classifications must match the existing interval-derived contract.",
        )

    status = None
    try:
        status = assess_probability_calibration(
            observations,
            backtest_report=report,
        )
    except (TypeError, ValueError):
        status = None
    semantics_valid = False
    if status is not None:
        try:
            semantics_valid = _calibration_backtest_semantics_verified(report, status)
        except Exception:
            semantics_valid = False
    if not semantics_valid:
        _append_blocker(
            blockers,
            "backtest_report_semantics_match",
            "The supplied report does not match the existing deep backtest semantics.",
        )
    if status is None or not status.evidence_digest:
        _append_blocker(
            blockers,
            "calibration_evidence_digest_present",
            "A canonical calibration evidence digest is required.",
        )
    if status is None or not status.backtest_evidence_digest:
        _append_blocker(
            blockers,
            "backtest_evidence_digest_present",
            "A canonical backtest evidence digest is required.",
        )
    if status is not None:
        for gate in status.failed_gates:
            _append_blocker(
                blockers,
                gate,
                status.failed_gate_details.get(gate, "Calibration gate did not pass."),
            )

    blocked_names = {item.gate for item in blockers}
    return CalibrationEvidenceBundlePreview(
        schema_version=PREVIEW_SCHEMA_VERSION,
        state=("contract_consistent_review_required" if not blockers else "blocked"),
        bundle_id=bundle_id,
        bundle_sha256=loaded.bundle_sha256,
        outcome_definition=cohort.outcome_definition,
        expected_event_count=len(expected),
        observation_count=len(observations),
        backtest_event_count=len(report.events),
        excluded_event_count=len(cohort.excluded_events),
        brier_score=status.brier_score if status is not None else None,
        benchmark_brier_score=(
            status.benchmark_brier_score if status is not None else None
        ),
        calibration_error=status.calibration_error if status is not None else None,
        calibration_bins=status.calibration_bins if status is not None else (),
        passed_gates=tuple(
            gate for gate in _CONTRACT_GATES if gate not in blocked_names
        ),
        blocked_gates=tuple(blockers),
        evidence_digest=status.evidence_digest if status is not None else None,
        backtest_evidence_digest=(
            status.backtest_evidence_digest if status is not None else None
        ),
    )


def calibration_evidence_bundle_payload(
    preview: CalibrationEvidenceBundlePreview,
) -> dict[str, object]:
    return {
        "schema_version": preview.schema_version,
        "state": preview.state,
        "bundle_id": preview.bundle_id,
        "bundle_sha256": preview.bundle_sha256,
        "outcome_definition": preview.outcome_definition,
        "expected_event_count": preview.expected_event_count,
        "observation_count": preview.observation_count,
        "backtest_event_count": preview.backtest_event_count,
        "excluded_event_count": preview.excluded_event_count,
        "brier_score": preview.brier_score,
        "benchmark_brier_score": preview.benchmark_brier_score,
        "calibration_error": preview.calibration_error,
        "calibration_bins": [
            {
                "lower_bound": item.lower_bound,
                "upper_bound": item.upper_bound,
                "event_count": item.event_count,
                "mean_probability": item.mean_probability,
                "outcome_rate": item.outcome_rate,
                "meets_minimum_size": item.meets_minimum_size,
            }
            for item in preview.calibration_bins
        ],
        "passed_gates": list(preview.passed_gates),
        "blocked_gates": [
            {"gate": item.gate, "detail": item.detail} for item in preview.blocked_gates
        ],
        "evidence_digest": preview.evidence_digest,
        "backtest_evidence_digest": preview.backtest_evidence_digest,
        "probability_state": preview.probability_state,
        "probability_exposure": preview.probability_exposure,
        "readiness_promotions": list(preview.readiness_promotions),
        "persistence": preview.persistence,
        "preview_receipt_persisted": preview.preview_receipt_persisted,
        "external_source_review_required": preview.external_source_review_required,
        "independent_review_required": preview.independent_review_required,
        "boundary": preview.boundary,
    }


def _percent(value: float | None) -> str:
    return "withheld" if value is None else f"{value * 100:.2f}%"


def render_calibration_evidence_bundle_preview(
    preview: CalibrationEvidenceBundlePreview,
) -> str:
    lines = [
        "Calibration Evidence-Bundle Preview",
        (
            "Read-only: validates one supplied immutable evidence bundle; it "
            "does not write files, activate readiness, persist evidence, or "
            "expose a Beat/Miss probability."
        ),
        (
            "Research-only: this is internal consistency evidence, not source "
            "attestation, investment advice, ranking, or a transaction instruction."
        ),
        "",
        f"State: {preview.state}",
        f"Bundle: {preview.bundle_id}",
        f"Bundle SHA-256: {preview.bundle_sha256}",
        f"Outcome definition: {preview.outcome_definition}",
        (
            "Counts: "
            f"expected={preview.expected_event_count}, "
            f"observations={preview.observation_count}, "
            f"backtest={preview.backtest_event_count}, "
            f"excluded={preview.excluded_event_count}"
        ),
        f"Brier score: {_percent(preview.brier_score)}",
        f"Constant-rate benchmark: {_percent(preview.benchmark_brier_score)}",
        f"Calibration error: {_percent(preview.calibration_error)}",
        f"Calibration bins: {len(preview.calibration_bins)} aggregate bins",
        f"Probability state: {preview.probability_state}",
        "Readiness promotions: none",
        "",
        "Passed gates:",
    ]
    lines.extend(f"- {gate}" for gate in preview.passed_gates)
    lines.append("Blocked gates:")
    if preview.blocked_gates:
        lines.extend(f"- {item.gate}: {item.detail}" for item in preview.blocked_gates)
    else:
        lines.append("- none; external and independent review are still required")
    lines.extend(("", f"Boundary: {preview.boundary}"))
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preview one calibration evidence bundle."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    preview_parser = subparsers.add_parser("preview")
    preview_parser.add_argument("--bundle", required=True)
    preview_parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        preview = preview_calibration_evidence_bundle(args.bundle)
    except CalibrationEvidenceBundleError as exc:
        print(f"invalid calibration evidence bundle: {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(
            json.dumps(
                calibration_evidence_bundle_payload(preview),
                indent=2,
                sort_keys=False,
            )
        )
    else:
        print(render_calibration_evidence_bundle_preview(preview))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
