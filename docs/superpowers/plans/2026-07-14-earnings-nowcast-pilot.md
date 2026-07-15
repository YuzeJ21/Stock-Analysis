# Earnings Nowcast Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a readiness-gated semiconductor Earnings Nowcast pilot that produces deterministic Revenue/EPS ranges and consensus-relative classifications, accepts evidence-only directional signals, and withholds numerical Beat/Miss probability until leakage-safe calibration gates pass.

**Architecture:** Add an isolated nowcast domain with immutable point-in-time contracts, fail-closed readiness, deterministic model math, chronological backtesting, and a separate probability calibration gate. Integrate structured read-only packets into Single-Stock Report and Data Health without changing existing DCF, peer, earnings, or analyst-estimate readiness semantics.

**Tech Stack:** Python 3.12, dataclasses, pandas, NumPy, Streamlit, pytest, CSV/JSON fixtures, existing Makefile/public gates.

## Global Constraints

- Research-only: no investment advice, broker integration, order routing, auto-trading, or direct buy/sell instructions.
- Never fabricate prices, actuals, consensus, shares, peers, forecasts, probabilities, sources, or recommendations.
- Numerical Beat/Miss probability is unavailable until at least 100 valid out-of-sample events pass leakage, Brier-score, calibration, and benchmark gates.
- LLM or text extraction may create evidence-only directional signals; it may not create a numeric adjustment or mutate a forecast.
- Candidate peers remain `candidate_context_only`; only reviewed trusted peers may provide evidence signals.
- Generated nowcast CSV/JSON/report/backtest outputs remain excluded unless an exact artifact is intentionally reviewed.
- Existing generated CSV/report/sample-report churn remains unstaged.
- Every implementation task follows red-green-refactor and commits only exact product/code/docs/test files.

---

### Task 1: Point-In-Time Domain Contracts

**Files:**
- Create: `src/earnings_nowcast_contract.py`
- Create: `tests/test_earnings_nowcast_contract.py`

**Interfaces:**
- Produces: `QuarterlyActual`, `ConsensusSnapshot`, `EvidenceSignal`, `ForecastSnapshot`, `NowcastState`, `FreshnessState`, `parse_utc_timestamp()`, `validate_cutoff()`, and `input_snapshot_hash()`.
- Consumes: standard-library dataclasses, enums, datetime, hashlib, and JSON only.

- [ ] **Step 1: Write failing contract tests**

```python
from datetime import datetime, timezone

import pytest

from src.earnings_nowcast_contract import (
    ConsensusSnapshot,
    EvidenceSignal,
    QuarterlyActual,
    input_snapshot_hash,
)


def test_contract_rejects_evidence_published_after_cutoff():
    with pytest.raises(ValueError, match="after forecast cutoff"):
        QuarterlyActual(
            ticker="SYN1",
            fiscal_period="2025-Q4",
            period_end_date="2025-12-31",
            reported_at="2026-02-01T21:00:00Z",
            revenue_actual=100.0,
            eps_actual=1.0,
            source="synthetic_test_fixture",
            source_ref="fixture://actual/1",
            retrieved_at="2026-02-02T00:00:00Z",
        ).available_at("2026-01-31T23:59:59Z")


def test_consensus_snapshot_hash_is_deterministic_and_order_independent():
    snapshot = ConsensusSnapshot(
        ticker="SYN1",
        fiscal_period="2026-Q1",
        snapshot_at="2026-01-15T12:00:00Z",
        revenue_consensus=110.0,
        eps_consensus=1.1,
        source="synthetic_test_fixture",
        retrieved_at="2026-01-15T12:01:00Z",
    )
    assert input_snapshot_hash([snapshot]) == input_snapshot_hash([snapshot])


def test_signal_contract_has_no_numeric_impact_field():
    assert "estimated_impact_bps" not in EvidenceSignal.__dataclass_fields__
```

- [ ] **Step 2: Run the tests and verify the missing module failure**

Run: `python3 -m pytest tests/test_earnings_nowcast_contract.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'src.earnings_nowcast_contract'`.

- [ ] **Step 3: Implement immutable validated contracts**

```python
class NowcastState(StrEnum):
    BLOCKED = "blocked"
    BASELINE_READY = "baseline_ready"
    SIGNAL_CONTEXT_READY = "signal_context_ready"
    BACKTEST_READY = "backtest_ready"
    CALIBRATED = "calibrated"
    EXCLUDED = "excluded"


@dataclass(frozen=True)
class ConsensusSnapshot:
    ticker: str
    fiscal_period: str
    snapshot_at: str
    revenue_consensus: float | None
    eps_consensus: float | None
    source: str
    retrieved_at: str

    def available_at(self, cutoff: str) -> bool:
        validate_cutoff(self.snapshot_at, cutoff, label="consensus snapshot")
        return True
```

Implement equivalent immutable contracts for actuals, signals, and forecast snapshots. Normalize tickers and fiscal periods, require non-empty provenance, parse UTC-aware timestamps, reject non-finite numeric values, and hash sorted canonical `asdict()` payloads.

- [ ] **Step 4: Run focused tests**

Run: `python3 -m pytest tests/test_earnings_nowcast_contract.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the contract slice**

```bash
git add -- src/earnings_nowcast_contract.py tests/test_earnings_nowcast_contract.py
git commit -m "Add earnings nowcast point-in-time contracts"
```

### Task 2: Independent Nowcast Readiness Gate

**Files:**
- Create: `src/earnings_nowcast_readiness.py`
- Create: `tests/test_earnings_nowcast_readiness.py`

**Interfaces:**
- Consumes: contract dataclasses from Task 1.
- Produces: `NowcastReadiness`, `assess_nowcast_readiness()`, and `readiness_payload()`.

- [ ] **Step 1: Write failing readiness tests**

```python
def test_generic_optional_context_does_not_unlock_nowcast():
    result = assess_nowcast_readiness(
        ticker="SYN1",
        fiscal_period="2026-Q1",
        as_of_timestamp="2026-01-31T23:59:59Z",
        actuals=[],
        consensus=[],
    )
    assert result.state == NowcastState.BLOCKED
    assert "quarterly_actual_history" in result.missing_evidence
    assert "point_in_time_consensus" in result.missing_evidence


def test_revenue_can_be_ready_while_invalid_eps_is_withheld():
    actuals = [
        QuarterlyActual(
            ticker="SYN1",
            fiscal_period=period,
            period_end_date=period_end,
            reported_at=reported_at,
            revenue_actual=revenue,
            eps_actual=eps,
            source="synthetic_test_fixture",
            source_ref=f"fixture://actual/{period}",
            retrieved_at=reported_at,
        )
        for period, period_end, reported_at, revenue, eps in (
            ("2024-Q4", "2024-12-31", "2025-02-01T21:00:00Z", 90.0, 0.8),
            ("2025-Q1", "2025-03-31", "2025-05-01T21:00:00Z", 92.0, -2.0),
            ("2025-Q2", "2025-06-30", "2025-08-01T21:00:00Z", 95.0, 3.5),
            ("2025-Q3", "2025-09-30", "2025-11-01T21:00:00Z", 98.0, -4.0),
            ("2025-Q4", "2025-12-31", "2026-01-15T21:00:00Z", 101.0, 6.0),
        )
    ]
    consensus = [
        ConsensusSnapshot(
            ticker="SYN1",
            fiscal_period="2026-Q1",
            snapshot_at="2026-01-20T12:00:00Z",
            revenue_consensus=104.0,
            eps_consensus=1.2,
            source="synthetic_test_fixture",
            retrieved_at="2026-01-20T12:01:00Z",
        )
    ]
    result = assess_nowcast_readiness(
        ticker="SYN1",
        fiscal_period="2026-Q1",
        as_of_timestamp="2026-01-31T23:59:59Z",
        actuals=actuals,
        consensus=consensus,
    )
    assert result.revenue_ready is True
    assert result.eps_ready is False
    assert "stable_eps_history" in result.missing_evidence
```

- [ ] **Step 2: Verify red tests**

Run: `python3 -m pytest tests/test_earnings_nowcast_readiness.py -q`

Expected: FAIL because the readiness module does not exist.

- [ ] **Step 3: Implement fail-closed readiness**

```python
@dataclass(frozen=True)
class NowcastReadiness:
    ticker: str
    fiscal_period: str
    state: NowcastState
    revenue_ready: bool
    eps_ready: bool
    consensus_ready: bool
    freshness_state: FreshnessState
    missing_evidence: tuple[str, ...]
    source_ids: tuple[str, ...]
    next_action: str
```

Require at least five prior quarterly actual rows for a baseline, exact forecast-period consensus, all source timestamps at or before the cutoff, non-empty provenance, and consistent period identity. Exclude ETFs/index/funds. Keep metric-level readiness separate so revenue may be ready while EPS is withheld.

- [ ] **Step 4: Run focused tests**

Run: `python3 -m pytest tests/test_earnings_nowcast_readiness.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the readiness slice**

```bash
git add -- src/earnings_nowcast_readiness.py tests/test_earnings_nowcast_readiness.py
git commit -m "Add earnings nowcast readiness gate"
```

### Task 3: Deterministic Revenue/EPS Baseline

**Files:**
- Create: `src/earnings_nowcast_model.py`
- Create: `tests/test_earnings_nowcast_model.py`

**Interfaces:**
- Consumes: validated actuals, one consensus snapshot, readiness result, and `NowcastConfig`.
- Produces: `build_baseline_nowcast() -> ForecastSnapshot`.

- [ ] **Step 1: Write failing deterministic-model tests**

```python
def test_identical_inputs_produce_identical_forecast_and_hash():
    first = build_baseline_nowcast(actuals, consensus, cutoff, config)
    second = build_baseline_nowcast(list(reversed(actuals)), consensus, cutoff, config)
    assert first == second
    assert first.input_snapshot_hash == second.input_snapshot_hash


def test_classification_uses_range_overlap_and_tolerance():
    assert classify_consensus_gap(105.0, 100.0, 110.0, tolerance_pct=0.02) == "aligned"
    assert classify_consensus_gap(90.0, 110.0, 120.0, tolerance_pct=0.02) == "higher"
    assert classify_consensus_gap(130.0, 100.0, 110.0, tolerance_pct=0.02) == "lower"


def test_blocked_eps_never_renders_a_numeric_eps_forecast():
    result = build_baseline_nowcast(actuals_with_invalid_eps, consensus, cutoff, config)
    assert result.eps_midpoint is None
    assert result.eps_low is None
    assert result.eps_high is None
```

- [ ] **Step 2: Verify red tests**

Run: `python3 -m pytest tests/test_earnings_nowcast_model.py -q`

Expected: FAIL because model functions are missing.

- [ ] **Step 3: Implement versioned deterministic math**

```python
@dataclass(frozen=True)
class NowcastConfig:
    model_version: str = "deterministic-v1"
    minimum_history_quarters: int = 5
    recent_growth_weight: float = 0.5
    seasonal_growth_weight: float = 0.5
    minimum_revenue_half_width_pct: float = 0.05
    minimum_eps_half_width: float = 0.10
    aligned_tolerance_pct: float = 0.02
```

Revenue midpoint is the average of a recent sequential-growth estimate and a same-quarter seasonal-growth estimate. Revenue range uses observed growth dispersion with the configured minimum width. EPS uses sequential and seasonal absolute changes only when readiness marks EPS stable. Sort all inputs before calculation, reject impossible range ordering, and store every configuration value through the model version and input hash.

- [ ] **Step 4: Run focused tests**

Run: `python3 -m pytest tests/test_earnings_nowcast_model.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the model slice**

```bash
git add -- src/earnings_nowcast_model.py tests/test_earnings_nowcast_model.py
git commit -m "Add deterministic earnings nowcast baseline"
```

### Task 4: Walk-Forward Backtest and Calibration Gate

**Files:**
- Create: `src/earnings_nowcast_backtest.py`
- Create: `tests/test_earnings_nowcast_backtest.py`

**Interfaces:**
- Consumes: ordered actuals, point-in-time consensus snapshots, config, and optional probability observations.
- Produces: `BacktestReport`, `walk_forward_backtest()`, and `assess_probability_calibration()`.

- [ ] **Step 1: Write failing chronology and calibration tests**

```python
def test_walk_forward_never_uses_target_actual_or_later_consensus():
    report = walk_forward_backtest(actuals, consensus_snapshots, config)
    assert report.leakage_failures == ()
    assert all(event.latest_input_timestamp <= event.as_of_timestamp for event in report.events)


def test_probability_is_withheld_below_100_out_of_sample_events():
    status = assess_probability_calibration(probability_events[:99])
    assert status.state == NowcastState.BACKTEST_READY
    assert status.probability_available is False
    assert "minimum_100_events" in status.failed_gates


def test_empty_backtest_evidence_fails_closed():
    report = walk_forward_backtest([], [], NowcastConfig())
    assert report.verdict == "failed"
    assert "No valid out-of-sample events" in report.failures
```

- [ ] **Step 2: Verify red tests**

Run: `python3 -m pytest tests/test_earnings_nowcast_backtest.py -q`

Expected: FAIL because the backtest module does not exist.

- [ ] **Step 3: Implement chronological evaluation and benchmarks**

```python
@dataclass(frozen=True)
class CalibrationPolicy:
    minimum_events: int = 100
    maximum_brier_score: float = 0.25
    minimum_bin_size: int = 10


@dataclass(frozen=True)
class BacktestReport:
    verdict: str
    event_count: int
    excluded_count: int
    revenue_mae: float | None
    revenue_wape: float | None
    eps_mae: float | None
    directional_accuracy: float | None
    interval_coverage: float | None
    benchmark_metrics: dict[str, float]
    leakage_failures: tuple[str, ...]
    failures: tuple[str, ...]
    events: tuple[BacktestEvent, ...]
```

Create forecast events in chronological order. At each cutoff, pass only earlier reported actuals and snapshots no later than cutoff into the model. Report MAE, median absolute error, WAPE where valid, directional accuracy, interval coverage, latest-consensus benchmark, prior-year benchmark, exclusions, and leakage failures. Probability calibration must separately validate event count, finite probabilities, Brier score, non-empty probability bins, and improvement over a constant-rate benchmark.

- [ ] **Step 4: Run focused tests**

Run: `python3 -m pytest tests/test_earnings_nowcast_backtest.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the backtest slice**

```bash
git add -- src/earnings_nowcast_backtest.py tests/test_earnings_nowcast_backtest.py
git commit -m "Add leakage-safe earnings nowcast backtest"
```

### Task 5: Evidence-Only Peer and Company Signals

**Files:**
- Create: `src/earnings_nowcast_signals.py`
- Create: `tests/test_earnings_nowcast_signals.py`

**Interfaces:**
- Consumes: `EvidenceSignal`, forecast cutoff, and accepted trusted-peer relationship IDs.
- Produces: `SignalReview`, `review_evidence_signals()`, and `signal_context_payload()`.

- [ ] **Step 1: Write failing signal-boundary tests**

```python
def test_candidate_peer_signal_cannot_become_supported_or_change_numbers():
    review = review_evidence_signals([candidate_signal], cutoff, trusted_peer_ids=set())
    assert review.supported == ()
    assert review.candidate_context_only == (candidate_signal,)
    assert not hasattr(review, "revenue_adjustment")


def test_post_cutoff_signal_is_still_blocked():
    review = review_evidence_signals([late_signal], cutoff, trusted_peer_ids={"peer-1"})
    assert review.supported == ()
    assert "published_after_cutoff" in review.blockers
```

- [ ] **Step 2: Verify red tests**

Run: `python3 -m pytest tests/test_earnings_nowcast_signals.py -q`

Expected: FAIL because signal review functions are missing.

- [ ] **Step 3: Implement evidence-only review**

Accept only allowlisted signal types, directions, metrics, source references, timestamps, and review states. A trusted source signal can raise lane state from `baseline_ready` to `signal_context_ready`; it cannot mutate `ForecastSnapshot` numeric fields. Preserve candidate, blocked, skipped, and excluded outcomes in separate collections.

- [ ] **Step 4: Run focused tests**

Run: `python3 -m pytest tests/test_earnings_nowcast_signals.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the signal slice**

```bash
git add -- src/earnings_nowcast_signals.py tests/test_earnings_nowcast_signals.py
git commit -m "Add evidence-only earnings signal review"
```

### Task 6: Offline Fixture Pilot and Read-Only CLI Packet

**Files:**
- Create: `src/earnings_nowcast_report.py`
- Create: `tests/test_earnings_nowcast_report.py`
- Create: `tests/fixtures/earnings_nowcast/quarterly_actuals.csv`
- Create: `tests/fixtures/earnings_nowcast/consensus_snapshots.csv`
- Create: `tests/fixtures/earnings_nowcast/signals.csv`
- Modify: `Makefile`

**Interfaces:**
- Consumes: CSV rows mapped into Tasks 1-5 contracts.
- Produces: `build_nowcast_packet()`, `render_nowcast_packet()`, and `make earnings-nowcast-pilot`.

- [ ] **Step 1: Add explicitly synthetic fixture rows and failing report tests**

Use tickers `SYN1` through `SYN5`, source `synthetic_test_fixture`, and `fixture://` references. Include at least eight historical quarters per ticker, exact forecast-period consensus snapshots, one post-cutoff row that must be rejected, candidate peer signals, and supported signals.

```python
def test_fixture_packet_is_reproducible_and_never_claims_real_company_evidence():
    first = build_nowcast_packet(fixture_root, ticker="SYN1", as_of_timestamp=CUTOFF)
    second = build_nowcast_packet(fixture_root, ticker="SYN1", as_of_timestamp=CUTOFF)
    assert first == second
    rendered = render_nowcast_packet(first)
    assert "synthetic test evidence" in rendered.lower()
    assert "investment advice" in rendered.lower()
    assert "beat probability" not in rendered.lower()
```

- [ ] **Step 2: Verify red tests**

Run: `python3 -m pytest tests/test_earnings_nowcast_report.py -q`

Expected: FAIL because report functions and fixture files are missing.

- [ ] **Step 3: Implement packet loading, rendering, and CLI**

The CLI accepts `--root`, `--ticker`, `--as-of`, and optional explicit input paths. Default repository data paths may be inspected read-only, but no missing file may be generated. JSON output includes readiness, forecast, signals, backtest state, calibration state, provenance, and boundaries. Exit code is 0 for a valid ready or truthfully blocked packet, 1 for invalid evidence, and 2 for environment/input unavailability.

- [ ] **Step 4: Add the Make target**

```make
earnings-nowcast-pilot:
	python3 -m src.earnings_nowcast_report --root . --ticker $(or $(TICKER),SYN1) --as-of $(or $(AS_OF),2026-01-31T23:59:59Z) $(if $(FIXTURE),--fixture,)
```

- [ ] **Step 5: Run focused tests and fixture CLI**

Run: `python3 -m pytest tests/test_earnings_nowcast_report.py -q`

Run: `FIXTURE=1 make earnings-nowcast-pilot TICKER=SYN1 AS_OF=2026-01-31T23:59:59Z`

Expected: tests pass and CLI reports a deterministic synthetic packet with no numerical probability.

- [ ] **Step 6: Commit the fixture/CLI slice**

```bash
git add -- Makefile src/earnings_nowcast_report.py tests/test_earnings_nowcast_report.py tests/fixtures/earnings_nowcast
git commit -m "Add offline earnings nowcast pilot packet"
```

### Task 7: Single-Stock and Data Health Integration

**Files:**
- Create: `src/earnings_nowcast_ui.py`
- Create: `tests/test_earnings_nowcast_ui.py`
- Modify: `src/dashboard.py`
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `src/browser_qa_evidence.py`
- Modify: `tests/test_browser_qa_evidence.py`

**Interfaces:**
- Consumes: read-only packet payload from Task 6.
- Produces: `nowcast_summary_cards()`, `nowcast_blocked_card()`, `render_earnings_nowcast_section()`, and browser-QA markers.

- [ ] **Step 1: Write failing UI contract tests**

```python
def test_blocked_nowcast_shows_no_numeric_forecast():
    cards = nowcast_summary_cards(blocked_packet)
    rendered = json.dumps(cards)
    assert "Open Data Health" in rendered
    assert "revenue_midpoint" not in rendered
    assert "eps_midpoint" not in rendered


def test_ready_nowcast_keeps_evidence_and_model_details_advanced():
    cards = nowcast_summary_cards(ready_packet)
    assert cards[0]["title"] == "Earnings Outlook"
    assert cards[0]["state"] == "baseline_ready"
    assert cards[0]["advanced_default_open"] is False
    assert "price reaction" not in json.dumps(cards).lower()
```

- [ ] **Step 2: Verify red tests**

Run: `python3 -m pytest tests/test_earnings_nowcast_ui.py -q`

Expected: FAIL because the UI helper does not exist.

- [ ] **Step 3: Implement isolated UI helpers**

Return simple view models rather than embedding model logic in `dashboard.py`. Render the section after existing selected-ticker readiness, usable-now, blocked-input, and next-action answers. Show readiness, period, as-of timestamp, revenue/EPS range, consensus classification, confidence, and freshness. Keep source IDs, model version, input hash, signals, and backtest metrics under a collapsed `Advanced: nowcast evidence` expander.

- [ ] **Step 4: Add Data Health lane answer**

The lane card states what is usable, what is missing, whether evidence is candidate-only, and whether calibration is withheld. It links back to the selected ticker but does not expose raw snapshot tables or commands by default.

- [ ] **Step 5: Update browser QA markers without requiring generated screenshots**

Add route expectations for `Earnings Outlook`, `baseline_ready` or the blocked explanation, and the research-only boundary. Existing screenshot assets remain route-marker evidence; do not replace them unless a separately reviewed real screenshot is captured.

- [ ] **Step 6: Run focused UI tests**

Run: `python3 -m pytest tests/test_earnings_nowcast_ui.py tests/test_dashboard_helpers.py tests/test_browser_qa_evidence.py -q`

Expected: PASS.

- [ ] **Step 7: Commit the UI slice**

```bash
git add -- src/earnings_nowcast_ui.py src/dashboard.py src/browser_qa_evidence.py tests/test_earnings_nowcast_ui.py tests/test_dashboard_helpers.py tests/test_browser_qa_evidence.py
git commit -m "Add readiness-gated earnings outlook UI"
```

### Task 8: Roadmap, Methodology, and Public Boundary

**Files:**
- Modify: `ROADMAP.md`
- Modify: `README.md`
- Modify: `docs/METHODOLOGY.md`
- Modify: `docs/PROVENANCE_CONTRACT.md`
- Create: `docs/EARNINGS_NOWCAST_PILOT.md`
- Modify: `tests/test_public_v1_release_docs.py`
- Modify: `tests/test_launchers.py`

**Interfaces:**
- Documents the exact implemented states and commands from Tasks 1-7.
- Does not claim real semiconductor coverage, calibration, hosted availability, or predictive accuracy.

- [ ] **Step 1: Write failing documentation-contract tests**

```python
def test_public_docs_keep_nowcast_probability_withheld_until_calibrated():
    text = Path("docs/EARNINGS_NOWCAST_PILOT.md").read_text()
    assert "baseline_ready" in text
    assert "signal_context_ready" in text
    assert "backtest_ready" in text
    assert "calibrated" in text
    assert "No numerical Beat/Miss probability is shown before calibration" in text
    assert "does not predict post-earnings price movement" in text
```

- [ ] **Step 2: Verify red tests**

Run: `python3 -m pytest tests/test_public_v1_release_docs.py tests/test_launchers.py -q`

Expected: FAIL because the pilot documentation is missing.

- [ ] **Step 3: Document truthful capability and roadmap state**

Move the nowcast pilot into `Next` until fixture, model, backtest, and UI gates pass. After implementation, mark infrastructure complete while keeping real semiconductor data `awaiting_point_in_time_consensus` and numerical probability `awaiting_calibration_evidence`. Explain source precedence, synthetic fixture boundary, leakage controls, commands, states, and generated-artifact policy.

- [ ] **Step 4: Run documentation and wording tests**

Run: `python3 -m pytest tests/test_public_v1_release_docs.py tests/test_launchers.py -q`

Run: `make public-wording-check`

Expected: PASS.

- [ ] **Step 5: Commit the documentation slice**

```bash
git add -- ROADMAP.md README.md docs/METHODOLOGY.md docs/PROVENANCE_CONTRACT.md docs/EARNINGS_NOWCAST_PILOT.md tests/test_public_v1_release_docs.py tests/test_launchers.py
git commit -m "Document earnings nowcast pilot boundaries"
```

### Task 9: Full Verification and Completion Audit

**Files:**
- Review only: all files changed in Tasks 1-8.
- Do not stage: generated CSV/JSON/reports, nowcast output packets, existing sample reports, or local provider data.

**Interfaces:**
- Proves the implemented product matches the approved specification.

- [ ] **Step 1: Run all focused nowcast tests**

Run:

```bash
python3 -m pytest \
  tests/test_earnings_nowcast_contract.py \
  tests/test_earnings_nowcast_readiness.py \
  tests/test_earnings_nowcast_model.py \
  tests/test_earnings_nowcast_backtest.py \
  tests/test_earnings_nowcast_signals.py \
  tests/test_earnings_nowcast_report.py \
  tests/test_earnings_nowcast_ui.py -q
```

Expected: PASS.

- [ ] **Step 2: Run the deterministic fixture packet twice and compare output**

Run:

```bash
FIXTURE=1 make earnings-nowcast-pilot TICKER=SYN1 AS_OF=2026-01-31T23:59:59Z > /tmp/nowcast-1.json
FIXTURE=1 make earnings-nowcast-pilot TICKER=SYN1 AS_OF=2026-01-31T23:59:59Z > /tmp/nowcast-2.json
diff -u /tmp/nowcast-1.json /tmp/nowcast-2.json
```

Expected: no diff; artifacts remain under `/tmp`.

- [ ] **Step 3: Run full product gates**

Run separately and verify exit code 0:

```bash
python3 -m pytest tests -q
make dashboard-smoke
make browser-qa-evidence
make public-performance-contract
make public-wording-check
make public-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
```

- [ ] **Step 4: Audit every acceptance criterion**

Confirm from current code, tests, CLI output, and UI markers:

- Deterministic fixture cohort produces reproducible ranges.
- Period, cutoff, provenance, model version, input hash, freshness, and readiness are present.
- Missing and post-cutoff evidence fail closed.
- Historical consensus snapshots are append-only inputs.
- Walk-forward report contains benchmarked errors and exclusions.
- Probability is unavailable without calibration evidence.
- UI separates baseline forecast, evidence-only signals, and withheld analysis.
- No trading, advice, price-reaction, or fabricated-data behavior exists.

- [ ] **Step 5: Verify commit and generated-artifact boundaries**

Run:

```bash
git status --short --branch
make diff-hygiene-summary
make staged-hygiene-check
git log --oneline --decorate -10
```

Expected: only pre-existing generated churn remains dirty; no product package is staged; coherent task commits exist on `codex/earnings-nowcast-pilot`; nothing is pushed unless the user separately authorizes it.
