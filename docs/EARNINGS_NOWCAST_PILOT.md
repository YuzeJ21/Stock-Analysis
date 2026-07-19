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

The read-only SEC staging command is `make earnings-nowcast-sec-actuals-stage TICKERS=<comma-separated-tickers> OUTPUT_DIR=<generated-directory> AS_OF=<UTC-cutoff>`. `OUTPUT_DIR` must be a new temporary/review directory or an existing directory marked by this generated stage; canonical `data/` and `data/imports/` paths and existing non-generated evidence directories are rejected. The command reports `automatic_apply=false`; it neither changes canonical evidence nor provides an apply path. The five-company pilot scope is NVDA, AMD, AVGO, MU, and QCOM, but a successful staging run is not real Nowcast coverage.

Q1-Q3 lineage accepts only source-backed SEC Companyfacts duration facts with a 60-120 day quarter duration and a one-to-one fiscal identity/period-end mapping. Cumulative facts, ambiguous concepts, conflicting fiscal identities, and post-cutoff rows are rejected. Companyfacts EPS uses `companyfacts_split_basis_unverified`, so it cannot become EPS-ready without separate source-backed comparability. Q4 requires an explicit fiscal-Q4 result table and one period-end date in its selected value column; filing timestamps and submission report dates are not substitutes. Annual-minus-nine-month arithmetic, derived Q4 disclosures, guidance, and cross-exhibit metric combinations are prohibited.

Historical actual evidence is append-only and cutoff-aware: later presentations remain separate revisions and never overwrite an earlier source-backed row. The stage summary surfaces accepted rows, rejected rows, missing Q4, direct source references, and detected fiscal-quarter continuity gaps; it never fabricates a missing period or metric. Revenue and EPS remain independent. EPS is withheld when its split-adjustment, share, operations, currency, or accounting basis cannot be kept within one source-backed comparable basis.

Real pilot output remains `awaiting_point_in_time_consensus` until permitted historical consensus snapshots are available at each forecast cutoff. Numerical Beat/Miss probability remains `awaiting_calibration_evidence` until at least 100 valid out-of-sample events pass the calibration gates.

## Cohort Readiness And Prospective Collection

Use `make earnings-nowcast-cohort-readiness AS_OF=<timestamp>` to review NVDA, AMD, AVGO, MU, and QCOM as one evidence board. The board reports the latest actual period, next forecast period, Revenue/EPS history, explicit Q4 evidence, split-basis readiness, exact-period consensus count, backtest count, calibration count, state, blocker, and next action. It does not create a forecast.

Use `make earnings-consensus-source-status` to inspect Alpha Vantage, FMP, Finnhub, and reviewed-CSV activation in deterministic order. A configured key is only `configured_unverified`; it is not evidence that historical snapshots, use rights, or comparable definitions are available. Current-only estimates remain `candidate_context_only` and cannot be used as reconstructed historical snapshots.

Use `make earnings-consensus-collection-plan AS_OF=<timestamp>` for a weekly or pre-earnings plan and `make earnings-consensus-collection-status` for the append-only ledger status. The prospective record preserves snapshot identity, source reference, publication/retrieval cutoff, metric definitions, explicit revisions, and review state. Duplicate snapshots are rejected, cooldown is explicit, prior snapshots are never overwritten, and no automatic apply or readiness promotion exists.

For prospective collection, start from `docs/templates/earnings_nowcast/prospective_consensus.csv` and set `COLLECTION_INPUT=<prospective_consensus.csv>`. Preview with `make earnings-consensus-collection-preview INPUT=$COLLECTION_INPUT AS_OF=<timestamp>`. Recording requires the separately reviewed `CONFIRM_REVIEWED=1 make earnings-consensus-collection-record INPUT=$COLLECTION_INPUT` command; it appends evidence only and does not create a forecast or promote readiness automatically.

Preview keeps the append-only technical decision separate from commercial evidence. Each exact source is checked without aliases or composite-source inference; a populated Revenue value requires registered `revenue_consensus` scope and a populated EPS value independently requires `eps_consensus` scope. In ordinary research mode, the existing explicit reviewed append path remains available. In explicit Commercial Research mode, unapproved rights or any required missing scope blocks before the ledger or its parent directory is changed. The checked-in registry currently approves no prospective-consensus source or scope, so this guard does not unlock a real-company packet.

The upstream source-row validator uses the same evidence separation before a row reaches collection review. Callers cannot supply a rights label: the exact provider ID is joined to the checked-in registry, and each technically accepted row reports only the scopes required by its populated Revenue and EPS values. Technically invalid rows stay rejected without entering commercial-ready counts; current-only rows remain candidate context, and valid point-in-time rows are `historical_evidence_reviewable`, not activated evidence. This review result cannot collect, append, approve a payload, establish historical depth, or change nowcast, backtest, or calibration readiness.

Both consensus paths now derive that exact-source rights-and-scope decision from one immutable helper. Ordered required and missing metric fields stay inspectable, blank or duplicate requirements fail locally, and composite source IDs remain unknown rather than being expanded. Each consumer still owns its technical status, blocker wording, and write decision. The shared result is registry metadata, not evidence that a payload, timestamp, comparability definition, reviewer decision, historical snapshot, or readiness gate is valid.

Before collection preview, set `SOURCE_INPUT=<reviewed_source_export.csv>` and review the upstream export with `make earnings-consensus-source-review INPUT=$SOURCE_INPUT PROVIDER=<source_id> AS_OF=<timestamp>`. This read-only command requires the explicit provider and cutoff, rejects missing/duplicate headers and extra row values, preserves one-based row evidence, and renders technical, temporal, rights, and populated Revenue/EPS scope states in human or JSON form. Every result retains `auto_apply=false`; even a historical-reviewable, commercially complete row is not collected or activated. `SOURCE_INPUT` and `COLLECTION_INPUT` are distinct input contracts: the former requires explicit `history_scope`; the latter uses the existing prospective collection schema with `review_state`. Only after separate human payload/evidence review and explicit evidence-preserving mapping should collection preview run. The product performs no automatic mapping or file write, and recording remains a later explicitly confirmed mutation.

That source-row review also requires an explicit UTC cutoff and a literal `current_only` or `point_in_time` scope. Both candidate and historical rows must satisfy `snapshot_at <= retrieved_at <= review_cutoff`; unknown scope, reversed timestamps, or post-cutoff evidence are rejected before rights/scope review. Cutoff passage proves only timestamp ordering against the supplied boundary. It does not prove publication availability, payload correctness, source permission, freshness, collection, activation, backtesting, or calibration.

Multi-row preview and record use the same ordered virtual-ledger preflight. Each technically reviewable row becomes visible to the next proposed row in input order, so a valid explicit revision can reference an earlier row in the reviewed file while duplicates, reversed revisions, and same-period conflicts fail before record. Any deterministic technical blocker rejects the whole batch in every mode; any commercial-evidence blocker rejects the whole batch in explicit Commercial Research mode. Record then uses one append handle only after the applicable batch gate passes. This prevents known later rejections from causing partial input writes, but it is not concurrent-writer locking or crash-safe filesystem transactionality.

## Signals

Company news, industry indicators, macro evidence, and trusted peer earnings may provide directional explanation. Candidate peers remain `candidate_context_only`. Trusted signals require reviewed source evidence and can move the lane to `signal_context_ready`; they cannot mutate Revenue/EPS ranges or create a numeric adjustment.

## Backtest And Calibration

Backtests are chronological walk-forward evaluations. Each event uses only actuals reported and consensus snapshots published by its cutoff. The target actual is used only afterward for scoring. Reports include valid and excluded event counts, exclusion reasons, leakage failures, MAE, median absolute error, WAPE where valid, directional accuracy, interval coverage, and consensus/prior-year benchmarks. Calibration diagnostics show each populated probability bin, bin size, mean probability, outcome rate, constant-rate benchmark, and the exact failed gate.

Numerical probability remains `awaiting_calibration_evidence` until at least 100 valid out-of-sample observations pass all gates. Empty, invalid, poorly calibrated, or benchmark-inferior evidence remains withheld.

## Synthetic Fixture Boundary

Run:

```bash
FIXTURE=1 make earnings-nowcast-pilot TICKER=SYN1 AS_OF=2026-01-31T23:59:59Z
FIXTURE=1 make earnings-nowcast-readiness TICKER=SYN1 AS_OF=2026-01-31T23:59:59Z
make earnings-nowcast-walkthrough AS_OF=2026-01-31T23:59:59Z
```

The `SYN1`-`SYN5` cohort and `SYN5-BACKTEST` walkthrough label are synthetic test evidence only. The walkthrough demonstrates baseline ready, Revenue ready with EPS withheld, candidate-peer-only context, post-cutoff blocking, non-company exclusion, and backtest-insufficient/un-calibrated behavior. It proves deterministic contracts, readiness, ranges, signal separation, CLI output, and withholding behavior. It does not prove real-company coverage, current data, predictive accuracy, or investability.

The fixture readiness command uses a schema-valid synthetic onboarding fixture and should report `baseline_ready`. The same readiness command without `FIXTURE=1` reads local real-data onboarding rows and must remain blocked until source-backed point-in-time consensus and actuals pass validation.

Real semiconductor coverage is `awaiting_point_in_time_consensus`. The next legitimate data step is a narrow append-only cohort with licensed or otherwise permitted historical consensus snapshots and source-backed actuals. Generated packets remain local and unstaged unless an exact artifact is intentionally reviewed.
