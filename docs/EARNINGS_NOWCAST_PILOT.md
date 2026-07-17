# Earnings Nowcast Pilot

## Purpose

The pilot adds a conservative earnings-research lane: deterministic next-quarter Revenue/EPS ranges and a consensus-relative `higher`, `aligned`, or `lower` classification. It is research-only, not investment advice, and does not predict post-earnings price movement.

## Truthful States

| State | Meaning |
| --- | --- |
| `blocked` | Required quarterly history, exact-period point-in-time consensus, freshness, or provenance is missing. No numerical forecast is shown. |
| `baseline_ready` | A deterministic Revenue and/or EPS range can be reviewed. Unsupported metrics stay withheld. |
| `signal_context_ready` | Reviewed directional evidence exists, but it does not change the baseline numbers. |
| `backtest_insufficient` | Chronological events exist, but fewer than the documented minimum support a backtest-ready claim. |
| `backtest_ready` | Chronological evaluation exists, but numerical probability has not passed every calibration gate. |
| `calibrated` | At least 100 valid out-of-sample probability events pass Brier-score, bin-size, and benchmark-improvement gates. |
| `excluded` | The instrument is not an operating company eligible for this method. |

No numerical Beat/Miss probability is shown before calibration. Probability is a separate evidence gate, not a label inferred from the baseline range.

## Required Evidence

The baseline requires source-backed quarterly actuals, including the matching prior-year fiscal quarter, plus an append-only exact-period consensus snapshot that was available at the forecast cutoff. Duplicate rows for one fiscal period count once. Conflicting values require an explicit `supersedes_source_ref` or remain blocked. Revenue and EPS are canonicalized independently and must match the consensus definition for currency, scale, accounting basis, share basis, operations basis, and split treatment. Every row preserves source and timestamps. Every forecast preserves period, cutoff, expected report date, forecast horizon, model version, input-snapshot hash, freshness, readiness, and source IDs.

Post-cutoff actuals, later consensus revisions, and late news fail closed. Revenue and EPS readiness are independent so unstable EPS can remain withheld while Revenue is ready.

## Read-Only Evidence Onboarding

Blank tracked schemas live in `docs/templates/earnings_nowcast/`. Create a local staging copy and inspect it with:

```bash
make earnings-nowcast-templates OUTPUT_DIR=data/imports/earnings_nowcast
make earnings-nowcast-validate INPUT_DIR=data/imports/earnings_nowcast AS_OF=2026-01-31T23:59:59Z
make earnings-nowcast-preview INPUT_DIR=data/imports/earnings_nowcast EXISTING_DIR=data/earnings_nowcast AS_OF=2026-01-31T23:59:59Z
make earnings-nowcast-readiness INPUT_DIR=data/imports/earnings_nowcast TICKER=<ticker> AS_OF=<forecast-cutoff>
make earnings-nowcast-prospective-plan OUTPUT_DIR=data/imports/earnings_nowcast
```

Actuals and consensus files are required; reviewed signals are optional. The versioned schemas require source names, direct source references, fiscal periods, publication/retrieval timestamps, comparability definitions, and at least one supported metric. Exact duplicates, new rows, explicit append-only revisions, and unresolved conflicts are reported separately; a conflict makes the preview not packet-ready. Post-cutoff evidence is rejected. The prospective plan is scheduler-ready but does not fetch data or create its output directory. These commands never apply, overwrite, stage, commit, or push rows; there is intentionally no Earnings Nowcast apply command.

## SEC Quarterly Actuals Staging

The read-only SEC staging command is `make earnings-nowcast-sec-actuals-stage TICKERS=<comma-separated-tickers> OUTPUT_DIR=<generated-directory> AS_OF=<UTC-cutoff>`. It writes only the explicit output directory and reports `automatic_apply=false`; it neither changes canonical evidence nor provides an apply path. The five-company pilot scope is NVDA, AMD, AVGO, MU, and QCOM, but a successful staging run is not real Nowcast coverage.

Q1-Q3 lineage accepts only source-backed SEC Companyfacts duration facts with a 60-120 day quarter duration and a uniquely aligned fiscal identity. Cumulative facts, ambiguous concepts, conflicting fiscal identities, and post-cutoff rows are rejected. Q4 requires an explicit fiscal-Q4 result table in a SEC-filed primary-source exhibit. Annual-minus-nine-month arithmetic, derived Q4 disclosures, guidance, and cross-exhibit metric combinations are prohibited.

Historical actual evidence is append-only and cutoff-aware: later presentations remain separate revisions and never overwrite an earlier source-backed row. The stage summary surfaces accepted rows, rejected rows, missing Q4, direct source references, and detected fiscal-quarter continuity gaps; it never fabricates a missing period or metric. Revenue and EPS remain independent. EPS is withheld when its split-adjustment, share, operations, currency, or accounting basis cannot be kept within one source-backed comparable basis.

Real pilot output remains `awaiting_point_in_time_consensus` until permitted historical consensus snapshots are available at each forecast cutoff. Numerical Beat/Miss probability remains `awaiting_calibration_evidence` until at least 100 valid out-of-sample events pass the calibration gates.

## Signals

Company news, industry indicators, macro evidence, and trusted peer earnings may provide directional explanation. Candidate peers remain `candidate_context_only`. Trusted signals require reviewed source evidence and can move the lane to `signal_context_ready`; they cannot mutate Revenue/EPS ranges or create a numeric adjustment.

## Backtest And Calibration

Backtests are chronological walk-forward evaluations. Each event uses only actuals reported and consensus snapshots published by its cutoff. The target actual is used only afterward for scoring. Reports include valid and excluded event counts, exclusion reasons, leakage failures, MAE, median absolute error, WAPE where valid, directional accuracy, interval coverage, and consensus/prior-year benchmarks. Calibration diagnostics show each populated probability bin, bin size, mean probability, outcome rate, constant-rate benchmark, and the exact failed gate.

Numerical probability remains `awaiting_calibration_evidence` until at least 100 valid out-of-sample observations pass all gates. Empty, invalid, poorly calibrated, or benchmark-inferior evidence remains withheld.

## Synthetic Fixture Boundary

Run:

```bash
FIXTURE=1 make earnings-nowcast-pilot TICKER=SYN1 AS_OF=2026-01-31T23:59:59Z
make earnings-nowcast-walkthrough AS_OF=2026-01-31T23:59:59Z
```

The `SYN1`-`SYN5` cohort and `SYN5-BACKTEST` walkthrough label are synthetic test evidence only. The walkthrough demonstrates baseline ready, Revenue ready with EPS withheld, candidate-peer-only context, post-cutoff blocking, non-company exclusion, and backtest-insufficient/un-calibrated behavior. It proves deterministic contracts, readiness, ranges, signal separation, CLI output, and withholding behavior. It does not prove real-company coverage, current data, predictive accuracy, or investability.

Real semiconductor coverage is `awaiting_point_in_time_consensus`. The next legitimate data step is a narrow append-only cohort with licensed or otherwise permitted historical consensus snapshots and source-backed actuals. Generated packets remain local and unstaged unless an exact artifact is intentionally reviewed.
