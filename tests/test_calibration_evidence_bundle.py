from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from src.calibration_evidence_bundle import (
    CalibrationEvidenceBundleError,
    calibration_evidence_bundle_payload,
    load_calibration_evidence_bundle,
    main,
    preview_calibration_evidence_bundle,
    render_calibration_evidence_bundle_preview,
)
from src.earnings_nowcast_backtest import BacktestEvent, BacktestReport


def _envelope() -> dict[str, object]:
    return {
        "schema_version": "calibration-evidence-bundle-v1",
        "bundle_id": "calibration-review-2026-q2",
        "created_at": "2026-08-02T12:00:00Z",
        "cohort": {},
        "observations": [],
        "backtest_report": {},
        "evidence_references": [],
    }


def test_loader_binds_preview_to_the_exact_input_bytes(tmp_path: Path):
    path = tmp_path / "bundle.json"
    raw = json.dumps(_envelope(), indent=2).encode("utf-8")
    path.write_bytes(raw)

    loaded = load_calibration_evidence_bundle(path)

    assert loaded.path == path.resolve()
    assert loaded.bundle_sha256 == hashlib.sha256(raw).hexdigest()
    assert loaded.payload["bundle_id"] == "calibration-review-2026-q2"
    assert path.read_bytes() == raw


def test_loader_digest_changes_when_any_input_byte_changes(tmp_path: Path):
    path = tmp_path / "bundle.json"
    raw = json.dumps(_envelope(), separators=(",", ":")).encode("utf-8")
    path.write_bytes(raw)
    original = load_calibration_evidence_bundle(path)

    path.write_bytes(raw + b"\n")
    changed = load_calibration_evidence_bundle(path)

    assert changed.bundle_sha256 != original.bundle_sha256
    assert changed.raw_bytes == raw + b"\n"


def test_loader_rejects_missing_input(tmp_path: Path):
    with pytest.raises(CalibrationEvidenceBundleError, match="does not exist"):
        load_calibration_evidence_bundle(tmp_path / "missing.json")


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (b'{"schema_version":"calibration-evidence-bundle-v1",', "malformed JSON"),
        (b"\xff", "UTF-8"),
        (
            b'{"schema_version":"calibration-evidence-bundle-v1",'
            b'"schema_version":"calibration-evidence-bundle-v1"}',
            "duplicate JSON key",
        ),
    ],
)
def test_loader_rejects_malformed_or_ambiguous_json(
    tmp_path: Path,
    raw: bytes,
    message: str,
):
    path = tmp_path / "bundle.json"
    path.write_bytes(raw)

    with pytest.raises(CalibrationEvidenceBundleError, match=message):
        load_calibration_evidence_bundle(path)


def test_loader_rejects_unknown_or_oversized_input(tmp_path: Path):
    unknown = _envelope() | {"probability_available": True}
    path = tmp_path / "unknown.json"
    path.write_text(json.dumps(unknown), encoding="utf-8")
    with pytest.raises(CalibrationEvidenceBundleError, match="unknown top-level keys"):
        load_calibration_evidence_bundle(path)

    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b" " * (16 * 1024 * 1024 + 1))
    with pytest.raises(CalibrationEvidenceBundleError, match="16 MiB"):
        load_calibration_evidence_bundle(oversized)


def _report() -> BacktestReport:
    events = tuple(
        BacktestEvent(
            ticker=f"SYN{index:03d}",
            fiscal_period="2026-Q1",
            as_of_timestamp="2026-01-31T23:59:59Z",
            latest_input_timestamp="2026-01-31T23:59:59Z",
            target_reported_at="2026-02-15T21:00:00Z",
            input_source_ids=(
                f"fixture://event/{index}/history",
                f"fixture://event/{index}/consensus",
            ),
            revenue_forecast=102.0 if index % 2 == 0 else 100.0,
            revenue_low=101.0 if index % 2 == 0 else 95.0,
            revenue_high=105.0,
            revenue_actual=101.0,
            eps_forecast=1.02 if index % 2 == 0 else 1.0,
            eps_low=1.01 if index % 2 == 0 else 0.9,
            eps_high=1.1,
            eps_actual=1.01,
            consensus_revenue=99.0 if index % 2 == 0 else 103.0,
            consensus_eps=0.99 if index % 2 == 0 else 1.03,
            prior_year_revenue=90.0,
            prior_year_eps=0.9,
            relative_classification="higher" if index % 2 == 0 else "aligned",
            model_version="synthetic-test-only-v1",
            input_snapshot_hash=hashlib.sha256(
                f"synthetic-test-input/{index}".encode("utf-8")
            ).hexdigest(),
        )
        for index in range(100)
    )
    return BacktestReport(
        verdict="passed",
        event_count=100,
        valid_event_count=100,
        excluded_count=0,
        exclusion_reasons={},
        excluded_events=(),
        revenue_mae=1.0,
        revenue_median_absolute_error=1.0,
        revenue_wape=1.0 / 101.0,
        eps_mae=0.01,
        eps_median_absolute_error=0.01,
        directional_accuracy=1.0,
        interval_coverage=1.0,
        revenue_interval_coverage=1.0,
        eps_interval_coverage=1.0,
        joint_interval_coverage=1.0,
        benchmark_metrics={
            "consensus_revenue_mae": 2.0,
            "prior_year_revenue_mae": 11.0,
            "consensus_eps_mae": 0.02,
            "prior_year_eps_mae": 0.11,
        },
        benchmark_failures=(),
        leakage_failures=(),
        failures=(),
        events=events,
    )


def _report_payload(report: BacktestReport) -> dict[str, object]:
    return asdict(report)


def _bundle_payload() -> dict[str, object]:
    report = _report()
    observations = []
    expected = []
    references: dict[str, dict[str, str]] = {}
    for event in report.events:
        outcome = bool(event.revenue_actual > event.consensus_revenue)
        observations.append(
            {
                "ticker": event.ticker,
                "fiscal_period": event.fiscal_period,
                "as_of_timestamp": event.as_of_timestamp,
                "outcome_definition": "revenue_actual_strictly_above_consensus",
                "probability": 0.9 if outcome else 0.1,
                "outcome": outcome,
            }
        )
        expected.append(
            {
                "ticker": event.ticker,
                "fiscal_period": event.fiscal_period,
                "as_of_timestamp": event.as_of_timestamp,
            }
        )
        for source_id in event.input_source_ids:
            references[source_id] = {
                "source_id": source_id,
                "source_ref": source_id,
                "rights_decision_ref": f"review-required:{source_id}",
                "review_status": "review_required",
            }
    return {
        "schema_version": "calibration-evidence-bundle-v1",
        "bundle_id": "synthetic-calibration-contract-test",
        "created_at": "2026-08-02T12:00:00Z",
        "cohort": {
            "cohort_id": "synthetic-test-only-100",
            "outcome_definition": "revenue_actual_strictly_above_consensus",
            "minimum_events": 100,
            "selection_rule": "Synthetic alternating outcomes for contract tests only.",
            "period_start": "2026-Q1",
            "period_end": "2026-Q1",
            "expected_event_identities": expected,
            "excluded_events": [],
        },
        "observations": observations,
        "backtest_report": _report_payload(report),
        "evidence_references": list(references.values()),
    }


def test_internally_consistent_bundle_remains_review_required_and_withheld(
    tmp_path: Path,
):
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(_bundle_payload()), encoding="utf-8")

    preview = preview_calibration_evidence_bundle(path)

    assert preview.state == "contract_consistent_review_required"
    assert preview.observation_count == 100
    assert preview.probability_state == "withheld"
    assert preview.probability_exposure is False
    assert preview.readiness_promotions == ()
    assert preview.persistence is False
    assert preview.preview_receipt_persisted is False
    assert preview.external_source_review_required is True
    assert preview.independent_review_required is True


@pytest.mark.parametrize(
    ("mutate", "gate"),
    [
        (
            lambda payload: payload["cohort"].__setitem__("minimum_events", 99),
            "fixed_minimum_100_events",
        ),
        (
            lambda payload: payload["observations"].__setitem__(
                1, dict(payload["observations"][0])
            ),
            "cohort_identity_unique",
        ),
        (
            lambda payload: payload["observations"][0].__setitem__(
                "outcome", not payload["observations"][0]["outcome"]
            ),
            "strict_declared_outcome_match",
        ),
        (
            lambda payload: payload["backtest_report"]["events"][0].__setitem__(
                "latest_input_timestamp", "2026-02-16T00:00:00Z"
            ),
            "event_chronology",
        ),
        (
            lambda payload: payload.__setitem__(
                "evidence_references", payload["evidence_references"][1:]
            ),
            "source_reference_coverage",
        ),
        (
            lambda payload: payload["backtest_report"].__setitem__(
                "revenue_mae", 999.0
            ),
            "backtest_report_semantics_match",
        ),
    ],
)
def test_bundle_mutations_fail_closed_with_stable_gate(
    tmp_path: Path,
    mutate,
    gate: str,
):
    payload = _bundle_payload()
    mutate(payload)
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    preview = preview_calibration_evidence_bundle(path)

    assert preview.state == "blocked"
    assert gate in {item.gate for item in preview.blocked_gates}
    assert preview.probability_state == "withheld"
    assert preview.readiness_promotions == ()


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda payload: payload["cohort"].__setitem__("override_policy", True),
            "cohort unknown keys",
        ),
        (
            lambda payload: payload["observations"][0].pop("ticker"),
            r"observations\[0\] missing keys",
        ),
        (
            lambda payload: payload["backtest_report"]["events"][0].__setitem__(
                "input_snapshot_hash", "not-a-digest"
            ),
            "input_snapshot_hash",
        ),
        (
            lambda payload: payload["observations"][0].__setitem__("probability", True),
            "finite number",
        ),
    ],
)
def test_nested_schema_errors_are_rejected(
    tmp_path: Path,
    mutate,
    message: str,
):
    payload = _bundle_payload()
    mutate(payload)
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CalibrationEvidenceBundleError, match=message):
        preview_calibration_evidence_bundle(path)


def test_mixed_outcome_definitions_fail_closed(tmp_path: Path):
    payload = _bundle_payload()
    payload["observations"][0]["outcome_definition"] = (
        "eps_actual_strictly_above_consensus"
    )
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    preview = preview_calibration_evidence_bundle(path)

    assert preview.state == "blocked"
    assert "strict_declared_outcome_match" in {
        item.gate for item in preview.blocked_gates
    }


def test_equality_is_not_treated_as_strictly_above_consensus(tmp_path: Path):
    payload = _bundle_payload()
    payload["backtest_report"]["events"][0]["revenue_actual"] = 99.0
    payload["observations"][0]["outcome"] = False
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    preview = preview_calibration_evidence_bundle(path)

    assert "strict_declared_outcome_match" not in {
        item.gate for item in preview.blocked_gates
    }


def test_period_overlap_exclusions_and_duplicate_sources_fail_closed(tmp_path: Path):
    payload = _bundle_payload()
    payload["cohort"]["period_end"] = "2025-Q4"
    payload["cohort"]["excluded_events"] = [
        {
            **payload["cohort"]["expected_event_identities"][0],
            "reason": "test exclusion",
            "detail": "test-only overlap",
        }
    ]
    source_ids = payload["backtest_report"]["events"][0]["input_source_ids"]
    payload["backtest_report"]["events"][0]["input_source_ids"] = (
        *source_ids,
        source_ids[0],
    )
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    preview = preview_calibration_evidence_bundle(path)
    gates = {item.gate for item in preview.blocked_gates}

    assert "cohort_period_bounds" in gates
    assert "excluded_identity_disjoint" in gates
    assert "exclusion_accounting_match" in gates
    assert "source_reference_coverage" in gates


@pytest.mark.parametrize(
    ("probabilities", "gate"),
    [
        ([0.9, 0.1] * 50, "maximum_brier_score"),
        ([0.5] * 100, "must_improve_constant_rate_benchmark"),
    ],
)
def test_calibration_quality_gates_remain_blocking(
    tmp_path: Path,
    probabilities: list[float],
    gate: str,
):
    payload = _bundle_payload()
    if gate == "maximum_brier_score":
        probabilities = list(reversed(probabilities))
    for observation, probability in zip(
        payload["observations"], probabilities, strict=True
    ):
        observation["probability"] = probability
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    preview = preview_calibration_evidence_bundle(path)

    assert gate in {item.gate for item in preview.blocked_gates}


def test_small_new_probability_bin_and_below_minimum_cohort_are_blocked(
    tmp_path: Path,
):
    payload = _bundle_payload()
    payload["observations"][0]["probability"] = 0.5
    payload["observations"].pop()
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    preview = preview_calibration_evidence_bundle(path)
    gates = {item.gate for item in preview.blocked_gates}

    assert "minimum_calibration_bin_size" in gates
    assert "minimum_100_events" in gates


def test_public_payload_and_text_are_aggregate_only(tmp_path: Path):
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(_bundle_payload()), encoding="utf-8")
    preview = preview_calibration_evidence_bundle(path)

    payload = calibration_evidence_bundle_payload(preview)
    text = render_calibration_evidence_bundle_preview(preview)
    serialized = json.dumps(payload, sort_keys=True)

    assert "observations" not in payload
    assert "events" not in payload
    assert "forecast" not in serialized.lower()
    assert "0.9" not in text
    assert "0.1" not in text
    assert payload["probability_state"] == "withheld"
    assert payload["probability_exposure"] is False
    assert payload["readiness_promotions"] == []
    assert "Read-only" in text
    assert "no readiness activation" in text


def test_cli_json_is_stdout_only_and_invalid_input_exits_two(
    tmp_path: Path,
    capsys,
):
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(_bundle_payload()), encoding="utf-8")
    before = {
        item.relative_to(tmp_path): item.read_bytes()
        for item in tmp_path.rglob("*")
        if item.is_file()
    }

    assert main(["preview", "--bundle", str(path), "--format", "json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["state"] == "contract_consistent_review_required"
    assert {
        item.relative_to(tmp_path): item.read_bytes()
        for item in tmp_path.rglob("*")
        if item.is_file()
    } == before

    invalid = tmp_path / "invalid.json"
    invalid.write_text("{}", encoding="utf-8")
    assert main(["preview", "--bundle", str(invalid)]) == 2
    captured = capsys.readouterr()
    assert "invalid calibration evidence bundle" in captured.err.lower()
