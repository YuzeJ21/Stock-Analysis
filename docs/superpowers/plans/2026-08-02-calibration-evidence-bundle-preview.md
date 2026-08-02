# Calibration Evidence-Bundle Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a provider-neutral, read-only CLI that strictly validates one operator-supplied calibration evidence bundle, recomputes its internal calibration/backtest contract, and always withholds probability and readiness activation.

**Architecture:** A new focused `src/calibration_evidence_bundle.py` module owns exact-byte loading, strict JSON parsing, immutable reconstruction, internal reconciliation, redacted rendering, and CLI behavior. It composes the existing `ProbabilityObservation`, `BacktestEvent`, `BacktestReport`, `assess_probability_calibration`, and deep cohort pairing verifier instead of creating a second calculation or readiness engine. The Make target is a thin no-write launcher; documentation records local software evidence without claiming any real calibration event.

**Tech Stack:** Python 3.12 standard library, frozen dataclasses, existing nowcast/backtest contracts, argparse, JSON, pytest, Make, GitHub Actions.

## Global Constraints

- Schema versions are exactly `calibration-evidence-bundle-v1` and `calibration-evidence-bundle-preview-v1`.
- Input is one explicitly supplied UTF-8 JSON file no larger than `16 * 1024 * 1024` bytes.
- Missing and unknown keys, duplicate JSON keys at any depth, Boolean-as-number values, non-finite numbers, identity-less observations, mixed outcome definitions, and operator policy overrides fail closed.
- The fixed minimum calibration cohort remains exactly 100 events.
- Input is read once; the assessed bytes and SHA-256 bytes must be identical.
- No network, ledger, readiness, canonical data, dashboard state, provider fetch, refresh, append, record, apply, or persistence operation is permitted.
- Text and JSON output go to stdout only and never write a CSV, JSON, report, sample report, screenshot, timing, readiness, canonical-data, or ledger artifact.
- Per-event probabilities and forecasts are never rendered.
- Every preview returns `probability_state="withheld"`, `probability_exposure=False`, `readiness_promotions=()`, `persistence=False`, `preview_receipt_persisted=False`, `external_source_review_required=True`, and `independent_review_required=True`.
- An internally passing package is only `contract_consistent_review_required`; it is never `calibrated`, `ready`, or `probability_available`.
- Actuals, consensus, Revenue, EPS, valuation, catalysts, outcomes, backtesting, calibration, peers, and quant interpretation readiness remain independent.
- Synthetic fixtures are test-only and cannot count as real calibration evidence.
- Keep the existing 18 generated readiness/report/output paths unstaged and byte-identical.
- Never use `git add -A`; stage the exact files named by each task.
- Keep PR #113 open and draft; do not merge or deploy publicly.

---

## File Map

- Create `src/calibration_evidence_bundle.py`: exact-byte loader, strict parser, immutable preview, reconciliation, renderers, and CLI.
- Create `tests/test_calibration_evidence_bundle.py`: strict loader, parser, reconciliation, redaction, CLI, and no-write tests using only temporary synthetic bundles.
- Modify `Makefile`: help text, `.PHONY`, required `BUNDLE`, and the thin preview launcher.
- Modify `tests/test_launchers.py`: structural Make target and no-write wording checks.
- Modify `tests/test_public_v1_release_docs.py`: roadmap/operator/continuation boundary assertions.
- Modify `docs/OPERATOR_GUIDE.md`: bounded command and interpretation guide.
- Modify `ROADMAP.md`: record the local preview contract while keeping valid real events at zero.
- Modify `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`: preserve and route the Priority 9 boundary.

---

### Task 1: Exact-byte loader and strict JSON envelope

**Files:**
- Create: `src/calibration_evidence_bundle.py`
- Create: `tests/test_calibration_evidence_bundle.py`

**Interfaces:**
- Consumes: an explicit `Path | str` supplied by the operator.
- Produces: `CalibrationEvidenceBundleError`, internal frozen `_LoadedCalibrationEvidenceBundle`, and `load_calibration_evidence_bundle(path)`.

- [ ] **Step 1: Write failing loader tests**

Add these imports and tests to `tests/test_calibration_evidence_bundle.py`:

```python
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from src.calibration_evidence_bundle import (
    CalibrationEvidenceBundleError,
    load_calibration_evidence_bundle,
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


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (b'{"schema_version":"calibration-evidence-bundle-v1",', "malformed JSON"),
        (b'\xff', "UTF-8"),
        (
            b'{"schema_version":"calibration-evidence-bundle-v1",'
            b'"schema_version":"calibration-evidence-bundle-v1"}',
            "duplicate JSON key",
        ),
    ],
)
def test_loader_rejects_malformed_or_ambiguous_json(tmp_path: Path, raw: bytes, message: str):
    path = tmp_path / "bundle.json"
    path.write_bytes(raw)

    with pytest.raises(CalibrationEvidenceBundleError, match=message):
        load_calibration_evidence_bundle(path)


def test_loader_rejects_missing_unknown_or_oversized_input(tmp_path: Path):
    with pytest.raises(CalibrationEvidenceBundleError, match="does not exist"):
        load_calibration_evidence_bundle(tmp_path / "missing.json")

    unknown = _envelope() | {"probability_available": True}
    path = tmp_path / "unknown.json"
    path.write_text(json.dumps(unknown), encoding="utf-8")
    with pytest.raises(CalibrationEvidenceBundleError, match="unknown top-level keys"):
        load_calibration_evidence_bundle(path)

    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b" " * (16 * 1024 * 1024 + 1))
    with pytest.raises(CalibrationEvidenceBundleError, match="16 MiB"):
        load_calibration_evidence_bundle(oversized)
```

- [ ] **Step 2: Run the loader tests and confirm RED**

Run:

```bash
python3 -m pytest tests/test_calibration_evidence_bundle.py -q
```

Expected: collection fails because `src.calibration_evidence_bundle` does not exist.

- [ ] **Step 3: Implement the minimal exact-byte loader**

Create `src/calibration_evidence_bundle.py` with these concrete primitives:

```python
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


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


class CalibrationEvidenceBundleError(ValueError):
    pass


@dataclass(frozen=True)
class _LoadedCalibrationEvidenceBundle:
    path: Path
    raw_bytes: bytes
    bundle_sha256: str
    payload: Mapping[str, object]


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    output: dict[str, object] = {}
    for key, value in pairs:
        if key in output:
            raise CalibrationEvidenceBundleError(f"duplicate JSON key: {key}")
        output[key] = value
    return output


def load_calibration_evidence_bundle(path: Path | str) -> _LoadedCalibrationEvidenceBundle:
    resolved = Path(path).expanduser().resolve()
    if not resolved.exists():
        raise CalibrationEvidenceBundleError(f"bundle does not exist: {resolved}")
    if not resolved.is_file():
        raise CalibrationEvidenceBundleError("bundle path must be a regular file")
    size = resolved.stat().st_size
    if size > MAX_BUNDLE_BYTES:
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
        raise CalibrationEvidenceBundleError(f"missing top-level keys: {', '.join(missing)}")
    if unknown:
        raise CalibrationEvidenceBundleError(f"unknown top-level keys: {', '.join(unknown)}")
    if payload["schema_version"] != BUNDLE_SCHEMA_VERSION:
        raise CalibrationEvidenceBundleError("unsupported calibration evidence bundle schema")
    return _LoadedCalibrationEvidenceBundle(
        path=resolved,
        raw_bytes=raw,
        bundle_sha256=hashlib.sha256(raw).hexdigest(),
        payload=payload,
    )
```

- [ ] **Step 4: Run the focused loader tests and confirm GREEN**

Run:

```bash
python3 -m pytest tests/test_calibration_evidence_bundle.py -q
```

Expected: all Task 1 tests pass and no repository file is created.

- [ ] **Step 5: Verify mutation sensitivity**

Temporarily remove `object_pairs_hook=_unique_object`, rerun
`test_loader_rejects_malformed_or_ambiguous_json`, and require the duplicate-key
case to fail. Restore the hook and rerun the file to green.

- [ ] **Step 6: Commit Task 1 exactly**

```bash
git add -- src/calibration_evidence_bundle.py tests/test_calibration_evidence_bundle.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Add strict calibration bundle loader"
```

---

### Task 2: Immutable reconstruction and fail-closed reconciliation

**Files:**
- Modify: `src/calibration_evidence_bundle.py`
- Modify: `tests/test_calibration_evidence_bundle.py`

**Interfaces:**
- Consumes: `_LoadedCalibrationEvidenceBundle`, existing `ProbabilityObservation`, `BacktestEvent`, `BacktestReport`, `CalibrationBin`, `assess_probability_calibration`, and `_calibration_backtest_semantics_verified`.
- Produces: frozen `CalibrationEvidenceBlocker`, frozen `CalibrationEvidenceBundlePreview`, and `preview_calibration_evidence_bundle(path)`.

- [ ] **Step 1: Add a complete synthetic bundle builder and failing happy-path test**

In `tests/test_calibration_evidence_bundle.py`, add the complete deterministic
100-event report helper below. It uses tickers `SYN000` through `SYN099`, one
fixed fiscal period and cutoff, exact source tuples, a test-only model identity,
and one SHA-256 input hash per event:

```python
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
```

Build the JSON bundle from the report's exact event identities:

```python
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


def test_internally_consistent_bundle_remains_review_required_and_withheld(tmp_path: Path):
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(_bundle_payload()), encoding="utf-8")

    preview = preview_calibration_evidence_bundle(path)

    assert preview.state == "contract_consistent_review_required"
    assert preview.observation_count == 100
    assert preview.probability_state == "withheld"
    assert preview.probability_exposure is False
    assert preview.readiness_promotions == ()
    assert preview.persistence is False
    assert preview.external_source_review_required is True
    assert preview.independent_review_required is True
```

`json.dumps` converts the tuple values produced by `asdict` into JSON arrays;
the helper emits every `BacktestReport` and `BacktestEvent` field and does not
precompute any new product data.

- [ ] **Step 2: Run the happy-path test and confirm RED**

Run:

```bash
python3 -m pytest tests/test_calibration_evidence_bundle.py::test_internally_consistent_bundle_remains_review_required_and_withheld -q
```

Expected: fail because `preview_calibration_evidence_bundle` and the preview
dataclasses do not exist.

- [ ] **Step 3: Add strict nested parsing and immutable result contracts**

Implement these concrete result types:

```python
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
```

Add strict helpers `_expect_object`, `_expect_exact_keys`, `_expect_list`,
`_expect_text`, `_expect_int`, `_expect_finite_number`, `_optional_number`,
`_parse_identity`, `_parse_observation`, `_parse_backtest_event`,
`_parse_backtest_report`, `_parse_exclusion`, and `_parse_evidence_reference`.
Every helper receives a field path and raises `CalibrationEvidenceBundleError`
with that path. `_expect_int` rejects Boolean values; numeric helpers reject
Boolean and non-finite values. Timestamps use `parse_utc_timestamp`, periods use
`YYYY-Q[1-4]`, SHA-256 values require 64 lowercase hexadecimal characters, and
all required labels reject the exact placeholder set from the design.

- [ ] **Step 4: Implement reconciliation by composing existing semantics**

`preview_calibration_evidence_bundle(path)` must:

```python
loaded = load_calibration_evidence_bundle(path)
cohort = _parse_cohort(loaded.payload["cohort"])
observations = tuple(_parse_observation(row, index) for index, row in enumerate(...))
report = _parse_backtest_report(loaded.payload["backtest_report"])
references = tuple(_parse_evidence_reference(row, index) for index, row in enumerate(...))
status = assess_probability_calibration(observations, backtest_report=report)
```

Then append stable blockers in this exact order when applicable:

```python
(
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
```

After these contract blockers, append `status.failed_gates` in their existing
deterministic order with `status.failed_gate_details`. Use
`_calibration_backtest_semantics_verified(report, status)` for the deep report
metrics, benchmark, classification, observation pairing, and digest gate. Do
not expose `status.state` or `status.probability_available` through the preview.

State is `contract_consistent_review_required` only when no blocker exists;
otherwise it is `blocked`. Parser failures raise
`CalibrationEvidenceBundleError` and are rendered by the CLI as `invalid`.

- [ ] **Step 5: Add parameterized fail-closed reconciliation tests**

Add tests that mutate exactly one reviewed input at a time and assert the named
blocker, including:

```python
@pytest.mark.parametrize(
    ("mutate", "gate"),
    [
        (lambda p: p["cohort"].__setitem__("minimum_events", 99), "fixed_minimum_100_events"),
        (lambda p: p["observations"].__setitem__(1, dict(p["observations"][0])), "cohort_identity_unique"),
        (lambda p: p["observations"][0].__setitem__("outcome", not p["observations"][0]["outcome"]), "strict_declared_outcome_match"),
        (lambda p: p["backtest_report"]["events"][0].__setitem__("latest_input_timestamp", "2026-02-16T00:00:00Z"), "event_chronology"),
        (lambda p: p.__setitem__("evidence_references", p["evidence_references"][1:]), "source_reference_coverage"),
        (lambda p: p["backtest_report"].__setitem__("revenue_mae", 999.0), "backtest_report_semantics_match"),
    ],
)
def test_bundle_mutations_fail_closed_with_stable_gate(tmp_path: Path, mutate, gate: str):
    payload = _bundle_payload()
    mutate(payload)
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    preview = preview_calibration_evidence_bundle(path)

    assert preview.state == "blocked"
    assert gate in {item.gate for item in preview.blocked_gates}
    assert preview.probability_state == "withheld"
    assert preview.readiness_promotions == ()
```

Add separate tests for duplicate JSON keys, unknown nested keys, identity-less or
partially bound rows, mixed Revenue/EPS outcomes, equality producing `False`,
out-of-period identities, expected/excluded overlap, exclusion reason totals,
duplicate source IDs, malformed input hashes, missing declared-metric inputs,
below-100 observations, poor Brier score, undersized bins, and failure to improve
the constant-rate benchmark.

- [ ] **Step 6: Run all focused reconciliation tests and confirm GREEN**

```bash
python3 -m pytest tests/test_calibration_evidence_bundle.py tests/test_earnings_nowcast_backtest.py tests/test_earnings_nowcast_cohort.py -q
```

Expected: exit zero with no failed focused test.

- [ ] **Step 7: Verify the authorization mutation**

Temporarily set `probability_state="available"` in the preview constructor and
rerun the happy-path and boundary tests. Require failure. Restore `withheld` and
rerun focused tests to green.

- [ ] **Step 8: Commit Task 2 exactly**

```bash
git add -- src/calibration_evidence_bundle.py tests/test_calibration_evidence_bundle.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Validate calibration evidence bundles"
```

---

### Task 3: Redacted payload, CLI, and Make preview

**Files:**
- Modify: `src/calibration_evidence_bundle.py`
- Modify: `tests/test_calibration_evidence_bundle.py`
- Modify: `Makefile`
- Modify: `tests/test_launchers.py`

**Interfaces:**
- Consumes: `CalibrationEvidenceBundlePreview` from Task 2.
- Produces: `calibration_evidence_bundle_payload(preview)`, `render_calibration_evidence_bundle_preview(preview)`, `main(argv=None)`, and `make calibration-evidence-bundle-preview BUNDLE=<path>`.

- [ ] **Step 1: Write failing redaction and CLI tests**

Add:

```python
from src.calibration_evidence_bundle import (
    calibration_evidence_bundle_payload,
    main,
    render_calibration_evidence_bundle_preview,
)


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


def test_cli_json_is_stdout_only_and_invalid_input_exits_two(tmp_path: Path, capsys):
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(_bundle_payload()), encoding="utf-8")
    before = {item.relative_to(tmp_path): item.read_bytes() for item in tmp_path.rglob("*") if item.is_file()}

    assert main(["preview", "--bundle", str(path), "--format", "json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["state"] == "contract_consistent_review_required"
    assert {item.relative_to(tmp_path): item.read_bytes() for item in tmp_path.rglob("*") if item.is_file()} == before

    invalid = tmp_path / "invalid.json"
    invalid.write_text("{}", encoding="utf-8")
    assert main(["preview", "--bundle", str(invalid)]) == 2
    captured = capsys.readouterr()
    assert "invalid calibration evidence bundle" in captured.err.lower()
```

- [ ] **Step 2: Run the renderer/CLI tests and confirm RED**

```bash
python3 -m pytest tests/test_calibration_evidence_bundle.py -q
```

Expected: fail because payload, renderer, and CLI interfaces do not exist.

- [ ] **Step 3: Implement redacted payload and text rendering**

Return an insertion-ordered dictionary with the exact result fields from the
spec. Convert bins to aggregate dictionaries and blockers to `gate`/`detail`
dictionaries. Do not serialize observations, events, evidence references,
per-event probabilities, per-event forecasts, or the internal
`probability_available` value.

The text renderer starts with:

```text
Calibration Evidence-Bundle Preview
Read-only: validates one supplied immutable evidence bundle; it does not write files, activate readiness, persist evidence, or expose a Beat/Miss probability.
Research-only: this is internal consistency evidence, not source attestation, investment advice, ranking, or a transaction instruction.
```

It prints state, bundle identity, aggregate counts, aggregate calibration
diagnostics, passed gates, blocked gates, and the immutable boundary. It never
prints observation or event rows.

- [ ] **Step 4: Implement the preview-only CLI**

Use argparse with exactly one subcommand:

```python
parser = argparse.ArgumentParser(description="Preview one calibration evidence bundle.")
subparsers = parser.add_subparsers(dest="command", required=True)
preview_parser = subparsers.add_parser("preview")
preview_parser.add_argument("--bundle", required=True)
preview_parser.add_argument("--format", choices=("text", "json"), default="text")
```

On `CalibrationEvidenceBundleError`, print only
`invalid calibration evidence bundle: <redacted message>` to stderr and return
2. On success, print one text or JSON payload and return 0 for both blocked and
contract-consistent previews. Add the standard `if __name__ == "__main__"`
entry point.

- [ ] **Step 5: Write the failing Make contract test**

Add to `tests/test_launchers.py`:

```python
def test_calibration_evidence_bundle_preview_is_explicit_and_read_only():
    makefile = Path("Makefile").read_text(encoding="utf-8")
    assert "calibration-evidence-bundle-preview" in _makefile_targets()
    block = makefile.split("calibration-evidence-bundle-preview:", 1)[1].split("\n\n", 1)[0]
    assert "BUNDLE is required" in block
    assert "python3 -m src.calibration_evidence_bundle preview" in block
    assert '--bundle "$${CALIBRATION_EVIDENCE_BUNDLE}"' in block
    assert "record" not in block
    assert "apply" not in block
```

Run:

```bash
python3 -m pytest tests/test_launchers.py::test_calibration_evidence_bundle_preview_is_explicit_and_read_only -q
```

Expected: fail because the target is absent.

- [ ] **Step 6: Add the thin Make launcher**

Add the target to `.PHONY`, `help`, and `help-full`, then add:

```make
calibration-evidence-bundle-preview: export CALIBRATION_EVIDENCE_BUNDLE := $(value BUNDLE)

calibration-evidence-bundle-preview:
	@case "$${CALIBRATION_EVIDENCE_BUNDLE}" in *[![:space:]]*) ;; *) echo "BUNDLE is required" >&2; exit 2;; esac
	@PYTHONDONTWRITEBYTECODE=1 python3 -m src.calibration_evidence_bundle preview \
		--bundle "$${CALIBRATION_EVIDENCE_BUNDLE}"
```

- [ ] **Step 7: Run CLI, launcher, and no-write tests**

```bash
python3 -m pytest tests/test_calibration_evidence_bundle.py tests/test_launchers.py -q
```

Expected: all pass and no repository file changes beyond the four intentional
Task 3 files.

- [ ] **Step 8: Commit Task 3 exactly**

```bash
git add -- src/calibration_evidence_bundle.py tests/test_calibration_evidence_bundle.py Makefile tests/test_launchers.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Expose read-only calibration bundle preview"
```

---

### Task 4: Roadmap truth, operator guidance, and release evidence

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/OPERATOR_GUIDE.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: `tests/test_public_v1_release_docs.py`

**Interfaces:**
- Consumes: the verified CLI/Make contract from Task 3.
- Produces: durable Priority 9 routing and release-document assertions.

- [ ] **Step 1: Write failing release-document tests**

Add assertions that all three documents name:

```python
def test_calibration_bundle_preview_docs_preserve_the_priority_9_boundary():
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")
    operator = Path("docs/OPERATOR_GUIDE.md").read_text(encoding="utf-8")
    prompt = Path("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md").read_text(encoding="utf-8")
    for text in (roadmap, operator, prompt):
        assert "make calibration-evidence-bundle-preview BUNDLE=<path>" in text
        assert "contract_consistent_review_required" in text
        assert "probability remains withheld" in text.lower()
        assert "does not activate readiness" in text.lower()
    assert "Valid real leakage-safe calibration events: zero" in roadmap
    assert "Synthetic fixtures remain test-only" in prompt
```

- [ ] **Step 2: Run the documentation test and confirm RED**

```bash
python3 -m pytest tests/test_public_v1_release_docs.py::test_calibration_bundle_preview_docs_preserve_the_priority_9_boundary -q
```

Expected: fail because the new command and state are not documented.

- [ ] **Step 3: Update the documents without overstating maturity**

Document the exact command, accepted input boundary, three technical states,
aggregate-only output, exit-code behavior, and no-write contract. In
`ROADMAP.md`, add a Priority 9 local-software-evidence paragraph but leave the
external blocker row unchanged: valid real events remain zero and probability
remains withheld. In the continuation prompt, route a supplied bundle through
the preview once, classify absence once, and move to another executable lane;
do not create synthetic evidence or retry an unchanged missing bundle.

- [ ] **Step 4: Run focused product and documentation tests**

```bash
python3 -m pytest \
  tests/test_calibration_evidence_bundle.py \
  tests/test_earnings_nowcast_backtest.py \
  tests/test_earnings_nowcast_cohort.py \
  tests/test_launchers.py \
  tests/test_public_v1_release_docs.py -q
```

Expected: all focused tests pass.

- [ ] **Step 5: Run the complete required local verification**

Run each command and require exit zero, while preserving the truthful blocked
pilot verdict and the same 18 excluded generated paths:

```bash
python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make research-accessibility-browser-check TIMEOUT_SECONDS=90
make public-wording-check
make commercial-beta-check
make commercial-beta-release-check
make public-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
shasum -a 256 -c .superpowers/sdd/2026-08-01-portable-html-action-policy-repair/protected-artifacts.sha256
```

- [ ] **Step 6: Commit Task 4 exactly**

```bash
git add -- ROADMAP.md docs/OPERATOR_GUIDE.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md tests/test_public_v1_release_docs.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Document calibration bundle review boundary"
```

---

### Task 5: Final range audit, GitHub synchronization, and exact-head CI

**Files:**
- No new files.
- Inspect all commits created by Tasks 1-4 plus the approved design and this plan.

**Interfaces:**
- Consumes: exact local commits and verification evidence.
- Produces: synchronized draft PR #113 with exact-head CI evidence.

- [ ] **Step 1: Audit the complete feature range**

```bash
BASE_SHA=$(git merge-base origin/main HEAD)
HEAD_SHA=$(git rev-parse HEAD)
make pr-range-hygiene-check BASE_SHA="$BASE_SHA" HEAD_SHA="$HEAD_SHA"
make staged-hygiene-check
git diff --cached --check
git status --short --branch
```

Require zero generated CSV/JSON paths in the PR range, an empty index, and only
the same 18 protected local generated paths in the working tree.

- [ ] **Step 2: Push only the approved branch**

```bash
git push origin codex/personal-research-mode-mvp
git rev-list --left-right --count HEAD...origin/codex/personal-research-mode-mvp
```

Require `0 0`.

- [ ] **Step 3: Update draft PR #113**

Post exact HEAD, focused/full counts, gate results, input/output boundary,
generated-artifact exclusion, and the unchanged external Priority 9 blocker.
Verify `state=OPEN`, `isDraft=true`, `mergeable=MERGEABLE`, and PR head equals
local HEAD.

- [ ] **Step 4: Require exact-head GitHub Actions success**

```bash
HEAD_SHA=$(git rev-parse HEAD)
gh run list --workflow "Commercial Research Beta" \
  --branch codex/personal-research-mode-mvp --limit 10 \
  --json databaseId,headSha,status,conclusion,url
```

Select only the newest run whose `headSha` equals `HEAD_SHA`, then run:

```bash
RUN_ID=$(gh run list --workflow "Commercial Research Beta" \
  --branch codex/personal-research-mode-mvp --limit 10 \
  --json databaseId,headSha \
  --jq ".[] | select(.headSha == \"${HEAD_SHA}\") | .databaseId" | head -1)
test -n "$RUN_ID"
gh run watch "$RUN_ID" --exit-status
gh run view "$RUN_ID" --json headSha,status,conclusion,url,jobs
```

Require exact SHA equality and `conclusion=success`.

- [ ] **Step 5: Final acceptance audit**

Re-read the approved specification and prove every acceptance criterion from
fresh output. Report the branch safe for code review only. Keep the PR draft;
do not merge or deploy. Report valid real calibration events as zero unless
direct permitted evidence supplied during this implementation proves otherwise.

## Execution Choice

The owner explicitly approved Scheme A and requested execution in the same
message. Use **Inline Execution** with `superpowers:executing-plans`; do not ask
for the execution choice again.
