# Earnings Nowcast Pilot

## Purpose

The pilot adds a conservative earnings-research lane: deterministic next-quarter Revenue/EPS ranges and a consensus-relative `higher`, `aligned`, or `lower` classification. It is research-only, not investment advice, and does not predict post-earnings price movement.

## Truthful States

| State | Meaning |
| --- | --- |
| `blocked` | Required quarterly history, exact-period point-in-time consensus, freshness, or provenance is missing. No numerical forecast is shown. |
| `baseline_ready` | A deterministic Revenue and/or EPS range can be reviewed. Unsupported metrics stay withheld. |
| `signal_context_ready` | Reviewed directional evidence exists, but it does not change the baseline numbers. |
| `backtest_ready` | Chronological evaluation exists, but numerical probability has not passed every calibration gate. |
| `calibrated` | At least 100 valid out-of-sample probability events pass Brier-score, bin-size, and benchmark-improvement gates. |
| `excluded` | The instrument is not an operating company eligible for this method. |

No numerical Beat/Miss probability is shown before calibration. Probability is a separate evidence gate, not a label inferred from the baseline range.

## Required Evidence

The baseline requires source-backed quarterly actuals, including the matching prior-year fiscal quarter, plus an append-only exact-period consensus snapshot that was available at the forecast cutoff. Every row preserves source and timestamps. Every forecast preserves period, cutoff, model version, input-snapshot hash, freshness, readiness, and source IDs.

Post-cutoff actuals, later consensus revisions, and late news fail closed. Revenue and EPS readiness are independent so unstable EPS can remain withheld while Revenue is ready.

## Signals

Company news, industry indicators, macro evidence, and trusted peer earnings may provide directional explanation. Candidate peers remain `candidate_context_only`. Trusted signals require reviewed source evidence and can move the lane to `signal_context_ready`; they cannot mutate Revenue/EPS ranges or create a numeric adjustment.

## Backtest And Calibration

Backtests are chronological walk-forward evaluations. Each event uses only actuals reported and consensus snapshots published by its cutoff. The target actual is used only afterward for scoring. Reports include MAE, median absolute error, WAPE where valid, directional accuracy, interval coverage, exclusions, leakage failures, and consensus/prior-year benchmarks.

Numerical probability remains `awaiting_calibration_evidence` until at least 100 valid out-of-sample observations pass all gates. Empty, invalid, poorly calibrated, or benchmark-inferior evidence remains withheld.

## Synthetic Fixture Boundary

Run:

```bash
FIXTURE=1 make earnings-nowcast-pilot TICKER=SYN1 AS_OF=2026-01-31T23:59:59Z
```

The `SYN1`-`SYN5` cohort is synthetic test evidence only. It proves deterministic contracts, readiness, ranges, signal separation, CLI output, and withholding behavior. It does not prove real-company coverage, current data, predictive accuracy, or investability.

Real semiconductor coverage is `awaiting_point_in_time_consensus`. The next legitimate data step is a narrow append-only cohort with licensed or otherwise permitted historical consensus snapshots and source-backed actuals. Generated packets remain local and unstaged unless an exact artifact is intentionally reviewed.
