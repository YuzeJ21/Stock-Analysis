# Earnings Nowcast Pilot Design

## Decision

Build a readiness-gated Earnings Nowcast pilot for a small semiconductor cohort. The first release produces deterministic next-quarter revenue and EPS ranges and compares them with a point-in-time consensus snapshot. It does not predict post-earnings price movement, issue investment advice, or publish numerical Beat/Miss probabilities before an out-of-sample calibration gate passes.

The feature follows the product principle: **data readiness first, analysis second, research decision last**.

## Scope

### Initial cohort

- Five to ten operating semiconductor companies selected from the active universe.
- Each company must have source-backed quarterly actuals and a point-in-time consensus snapshot for the forecast period.
- Trusted peer relationships are optional for the deterministic baseline and required before peer read-through signals can influence a forecast.

### Initial outputs

- Revenue forecast midpoint and range.
- EPS forecast midpoint and range.
- Consensus revenue and EPS captured as of the forecast cutoff.
- Absolute and percentage gap between the model midpoint and consensus.
- Consensus-relative classification: `higher`, `aligned`, or `lower`.
- Readiness state, confidence band, freshness state, source references, model version, and key uncertainties.
- An analytically withheld explanation whenever required evidence is missing or stale.

### Explicitly deferred

- Post-earnings stock-price direction or magnitude.
- Direct investment conclusions or trade instructions.
- Full-universe coverage.
- LLM-generated numeric forecast adjustments.
- Numerical Beat/Miss probability before calibration.
- Promotion of candidate peers into trusted peers without reviewed source evidence.

## Approaches Considered

### 1. Deterministic baseline first - selected

Use source-backed historical quarterly actuals, seasonal change, recent trend, and point-in-time consensus. This is auditable, deterministic, compatible with the existing readiness model, and testable without an LLM or provider dependency.

### 2. Hybrid evidence overlay - second release

Extract structured directional signals from source-backed peer filings, earnings releases, transcripts, and company disclosures. Signals can explain or qualify a deterministic forecast, but cannot change a number until a reviewed deterministic rule or trained model maps the signal to a bounded adjustment.

### 3. End-to-end machine-learning probability - deferred

Train a model directly on historical features and output Beat/Miss probability. This requires a sufficiently large point-in-time event set, leakage-safe walk-forward evaluation, and calibrated probabilities. The current repository does not yet contain that evidence.

## Architecture

The feature is a separate lane rather than an extension of generic optional-context readiness.

```text
Source-backed quarterly actuals
          +
Point-in-time consensus snapshot
          +
Forecast cutoff and fiscal-period identity
          |
          v
Earnings Nowcast Readiness Gate
          |
          +---- blocked / excluded / baseline_ready
          |
          v
Deterministic Baseline Model
          |
          v
Forecast Snapshot + Consensus Gap
          |
          +---- optional evidence-only peer/company signals
          |
          v
Walk-forward Backtest and Calibration Gate
          |
          +---- backtest_ready
          +---- calibrated (only after threshold evidence)
```

### Components

1. `earnings_nowcast_contract.py`
   - Owns schemas, enums, validation, period identity, source timestamps, and cutoff enforcement.
2. `earnings_nowcast_readiness.py`
   - Produces one readiness answer per ticker and forecast period.
3. `earnings_nowcast_model.py`
   - Produces deterministic baseline ranges and consensus-relative classification.
4. `earnings_nowcast_backtest.py`
   - Runs expanding-window or walk-forward evaluation using only records available at each historical cutoff.
5. `earnings_nowcast_signals.py`
   - Validates evidence-only directional signals; no numeric forecast mutation in the initial release.
6. `earnings_nowcast_report.py`
   - Produces a read-only packet for the single-stock workflow and CLI.
7. Dashboard helper integration
   - Adds a collapsed `Earnings Outlook` section to Single-Stock Report and a separate Data Health lane answer.

Each component accepts structured inputs and returns structured results. Provider access, file writes, UI rendering, and forecasting remain separate ownership boundaries.

## Data Contracts

### Quarterly actual

Required fields:

```text
ticker
fiscal_period
period_end_date
reported_at
revenue_actual
eps_actual
source
source_url_or_accession
retrieved_at
```

`reported_at` must be the public release timestamp. A record cannot be used as a feature for a cutoff earlier than that timestamp.

### Consensus snapshot

Required fields:

```text
ticker
fiscal_period
snapshot_at
revenue_consensus
eps_consensus
source
retrieved_at
```

Optional fields include analyst count, high, low, and standard deviation. A later consensus value may not overwrite an earlier snapshot needed for backtesting.

### Forecast snapshot

```text
forecast_id
ticker
fiscal_period
as_of_timestamp
model_version
input_snapshot_hash
revenue_midpoint
revenue_low
revenue_high
eps_midpoint
eps_low
eps_high
consensus_revenue
consensus_eps
revenue_gap_pct
eps_gap_pct
relative_classification
confidence_band
readiness_state
freshness_state
source_ids
created_at
```

Forecast snapshots are append-only evidence. Re-running a model creates a new versioned snapshot rather than rewriting historical evidence.

### Evidence signal

```text
signal_id
target_ticker
source_ticker
fiscal_period
as_of_timestamp
signal_type
direction
affected_metric
confidence_band
evidence_source
evidence_published_at
evidence_excerpt_hash
peer_relationship_state
review_state
```

Allowed directions are `positive`, `neutral`, `negative`, and `unclear`. Allowed review states preserve `candidate_context_only`, `supported`, `still_blocked`, `skipped`, and `excluded`.

The initial release contains no `estimated_impact_bps` field. Numeric impact is prohibited until a deterministic mapping or trained model is separately validated.

## Readiness Model

The nowcast lane uses these states:

| State | Meaning | Allowed output |
| --- | --- | --- |
| `blocked` | Required actuals, period identity, consensus, provenance, or cutoff evidence is absent or invalid. | Missing-evidence explanation only. |
| `baseline_ready` | Deterministic inputs pass provenance, period, freshness, and cutoff gates. | Revenue/EPS range and consensus-relative classification. |
| `signal_context_ready` | Baseline is ready and reviewed source-backed directional signals exist. | Baseline plus qualitative evidence context; no unvalidated numeric adjustment. |
| `backtest_ready` | Walk-forward evaluation has sufficient valid events and reports error metrics. | Historical performance evidence; no probability claim. |
| `calibrated` | Probability model passes sample-size, leakage, discrimination, and calibration gates. | Numerical Beat/Miss probability with calibration disclosure. |
| `excluded` | Instrument or fiscal structure is outside the operating-company pilot. | Not-applicable explanation. |

The lane cannot inherit readiness merely because generic earnings or analyst-estimate context is available.

## Deterministic Baseline

### Revenue

The initial baseline combines only observable historical values:

1. Same-quarter year-over-year growth.
2. Recent sequential growth trend.
3. Median growth across a bounded trailing window.
4. Seasonal dispersion used to create a forecast range.

The exact weights are configuration values stored with the model version. They are not chosen dynamically by an LLM. The range uses historical forecast residual or growth dispersion with a documented minimum width.

### EPS

EPS uses historical diluted EPS only when the accounting basis is consistent and source-backed. If negative, discontinuous, split-affected, or otherwise invalid observations make the baseline unstable, EPS stays blocked while revenue can remain ready.

### Consensus-relative classification

- `higher`: model range is materially above consensus under the configured tolerance.
- `lower`: model range is materially below consensus.
- `aligned`: ranges overlap or the gap is inside the tolerance.

Tolerance is versioned and tested. Classification is research context, not a prediction of market reaction.

## Leakage Controls

Every training, backtest, and live record must satisfy:

1. `source_published_at <= as_of_timestamp`.
2. `consensus_snapshot_at <= as_of_timestamp`.
3. The target-quarter actual is unavailable to feature construction.
4. Later provider revisions cannot replace the point-in-time snapshot.
5. Time zones are normalized to UTC while preserving source timestamps.
6. Train/test splitting is chronological; random row splitting is prohibited.
7. Peer signals require both a trusted relationship as of the cutoff and evidence published before the cutoff.
8. The forecast stores an input hash so a result can be reproduced.

Any violation fails closed and records the ticker/period as `blocked` for that run.

## Backtest and Calibration Gates

### Baseline evaluation

Report by metric and cohort:

- MAE and median absolute error.
- WAPE for revenue where the denominator is valid.
- Directional accuracy relative to consensus.
- Coverage rate of the forecast interval.
- Event count and excluded-event reasons.

Compare against simple benchmarks: latest consensus, prior-year same quarter, and trailing seasonal baseline.

### Numerical probability gate

Beat/Miss probability remains unavailable until all are true:

- At least 100 valid out-of-sample company-quarter events across the pilot cohort or a later approved cohort.
- Walk-forward evaluation only.
- No leakage test failures.
- Brier score and calibration curve reported.
- Probability bins have enough observations to avoid unsupported precision.
- The model improves on a constant-rate and consensus-only benchmark under the documented metric.
- Limitations and sample period are displayed with every probability output.

Failure of this gate keeps the state `backtest_ready`, not `calibrated`.

## Source Policy

Preferred source order:

1. SEC filings and company investor-relations releases for actuals and published company evidence.
2. Trusted provider or reviewed point-in-time export for consensus.
3. Trusted peer mappings already accepted by the peer-proof workflow.
4. Company or peer earnings releases and transcripts with publication timestamps for evidence signals.

Generic web articles, search snippets, untimestamped summaries, and LLM memory cannot supply numeric inputs. Public-source use must respect licensing and redistribution boundaries. Source availability is not field-level proof.

## UI and Workflow

### Single-Stock Report

Add `Earnings Outlook` after the existing usable-now and blocked-input answers. It shows:

1. Lane state and as-of timestamp.
2. Revenue/EPS range only when ready.
3. Consensus gap and `higher/aligned/lower` classification.
4. Confidence, freshness, and key uncertainty.
5. Evidence list and model details under `Advanced`.
6. One Data Health action when blocked.

It must not become a primary recommendation card or displace existing readiness answers.

### Data Health

Add one lane answer explaining:

- What can be used now.
- Which required evidence is missing.
- Whether signals are candidate-only or reviewed.
- Whether backtest/calibration gates pass.
- The next safe source-proof action.

Raw snapshots, feature rows, and backtest events remain collapsed/operator-only.

## Failure Handling

- Missing consensus: `blocked`; do not substitute a price target or model estimate.
- Missing actual history: metric-level block; do not fabricate quarters.
- Mismatched fiscal period: `blocked` with period-identity evidence.
- Stale consensus: `blocked` or `review_due` according to configured freshness.
- Insufficient EPS history: revenue may remain ready while EPS is withheld.
- Provider outage: preserve the last timestamped snapshot but do not call it current.
- Untrusted peer: signal remains `candidate_context_only` and cannot affect numbers.
- Empty browser or backtest evidence: fail closed, never pass by absence.

## Testing Strategy

### Contract tests

- Required fields and enum values.
- Fiscal-period normalization.
- Source and timestamp requirements.
- Append-only snapshot identity.

### Leakage tests

- Reject actuals, consensus, peer evidence, and news published after cutoff.
- Reject random split configuration.
- Preserve historical consensus snapshots against later revisions.
- Verify UTC normalization around market-close and earnings-release boundaries.

### Model tests

- Deterministic output for identical input hashes.
- Range ordering and minimum width.
- Metric-level withholding for invalid EPS.
- Correct consensus-relative classification at tolerance boundaries.
- No LLM or provider call in deterministic model code.

### Backtest tests

- Expanding-window chronology.
- Benchmark calculations.
- Excluded-event accounting.
- Calibration state withheld below the event threshold.

### Product tests

- Nowcast section remains below readiness answers.
- Blocked inputs never render as numeric forecasts.
- Evidence and raw records remain collapsed.
- Research-only and no-price-reaction boundaries remain visible.
- Existing five-page workflow and performance gate do not regress.

## Delivery Slices

1. Contracts, readiness, fixture dataset, and CLI packet.
2. Deterministic revenue/EPS baseline and consensus comparison.
3. Leakage-safe walk-forward backtest and benchmark report.
4. Single-stock and Data Health integration.
5. Evidence-only signal schema and source-backed fixture extraction.
6. Probability calibration only after sufficient real point-in-time evidence exists.

Each slice must pass focused tests, the full suite, public wording, dashboard smoke, browser QA, performance contract, diff hygiene, and staged hygiene. Generated forecasts, snapshots, backtests, CSVs, JSON, reports, and screenshots stay excluded unless an exact reviewed evidence artifact is intentionally selected.

## Acceptance Criteria

The initial pilot is complete when:

1. A deterministic fixture-backed semiconductor cohort can produce reproducible Revenue/EPS ranges without network access.
2. Every result includes period, cutoff, source, model version, input hash, freshness, and readiness.
3. Missing or post-cutoff evidence fails closed.
4. The model compares against point-in-time consensus without overwriting snapshots.
5. Walk-forward backtest reports benchmarked errors and exclusions.
6. Numerical probability remains unavailable unless calibration gates pass.
7. The public UI clearly separates usable forecast context, evidence-only signals, and withheld analysis.
8. No broker, trading, recommendation, fabricated-data, or price-reaction behavior is introduced.
