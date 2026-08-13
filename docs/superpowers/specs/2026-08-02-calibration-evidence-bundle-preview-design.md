# Calibration Evidence-Bundle Preview Design

**Date:** 2026-08-02

**Status:** Scheme A approved; written specification pending owner review

## Purpose

Add a provider-neutral, read-only operator contract that validates one supplied
calibration evidence bundle without recording evidence, modifying readiness, or
exposing a numerical Beat/Miss probability. The preview answers whether the
bundle is structurally complete and internally consistent enough for later
independent review. It does not authorize calibration, establish source
authenticity or rights, or make a company conclusion.

This is a narrow Priority 9 software slice. It does not create the missing real
calibration cohort. Valid real leakage-safe calibration events remain at zero
until permitted point-in-time evidence is supplied and independently reviewed.

## Current Evidence And Boundary

`src/earnings_nowcast_backtest.py` already provides immutable probability
observations, a walk-forward `BacktestReport`, fixed calibration policy,
canonical observation digests, exact backtest-package digests, Brier score,
constant-rate benchmark comparison, calibration bins, and fail-closed gates.
`src/earnings_nowcast_cohort.py` additionally verifies that a calibration status
and backtest report match one another before any cohort row can say
`calibrated`.

Those interfaces currently consume trusted in-memory dataclasses. They do not
provide an operator-facing parser for an external evidence package, strict
package schema validation, predeclared cohort-membership validation, or a
redacted no-write preview. Direct use of `assess_probability_calibration` can
also return `probability_available=True` for internally passing evidence. The
new preview must therefore compose the existing calculations behind a stricter
boundary and must never project that internal result as product authorization.

## Alternatives Considered

### 1. Add a standalone read-only bundle preview

Selected. A focused `src/calibration_evidence_bundle.py` module owns parsing,
schema validation, exact-byte identity, internal recomputation, redaction, CLI
rendering, and the no-write contract. It reuses the existing calibration and
backtest integrity logic without changing their public behavior.

### 2. Extend `src/earnings_nowcast_backtest.py` with file and CLI behavior

This would reduce the file count but mix core model assessment with untrusted
file parsing and operator presentation. It would also make it easier to confuse
an internally passing `CalibrationStatus` with a readiness or probability
authorization. Rejected because the trust boundary should remain explicit.

### 3. Add the preview directly to Data Health or Company Workbench

This could improve discoverability, but it would introduce upload, session,
rendering, and accessibility scope before the evidence contract is stable.
Rejected for this slice. A later UI design may consume the immutable preview
result, but it must not reimplement validation or add persistence.

## Architecture

Add `src/calibration_evidence_bundle.py` with four isolated responsibilities:

1. read one explicitly supplied JSON file once as bytes and bind the preview to
   the SHA-256 digest of those exact bytes;
2. parse a strict versioned schema into immutable internal records;
3. rebuild existing `ProbabilityObservation`, `BacktestEvent`, and
   `BacktestReport` objects and independently reconcile the cohort, outcomes,
   exclusions, chronology, calibration assessment, and report package;
4. return and render an immutable, redacted `CalibrationEvidenceBundlePreview`.

No default input path exists. The operator must name the bundle explicitly.
The module performs no network access and does not read or write a calibration
ledger. It does not call readiness builders, dashboard loaders, source refresh,
or any record/append interface.

## Input Contract

Schema version: `calibration-evidence-bundle-v1`.

The top-level JSON object has these exact ordered-independent keys and rejects
unknown keys:

- `schema_version`
- `bundle_id`
- `created_at`
- `cohort`
- `observations`
- `backtest_report`
- `evidence_references`

`bundle_id` is a non-placeholder operator label and is not treated as trusted
identity. Blank strings and case-insensitive `unknown`, `tbd`, `todo`,
`placeholder`, `example`, and `sample` values are prohibited wherever the
contract requires a non-placeholder label or reference. `created_at` is a
timezone-aware timestamp normalized to UTC. It is package metadata only and
cannot establish the chronology of any observation or source. The exact-file
SHA-256 is the technical package identity reported by the preview.

### Cohort contract

`cohort` has exactly:

- `cohort_id`
- `outcome_definition`
- `minimum_events`
- `selection_rule`
- `period_start`
- `period_end`
- `expected_event_identities`
- `excluded_events`

`minimum_events` must equal the repository policy value of `100`; an operator
cannot lower or override it. `outcome_definition` must be exactly one of:

- `revenue_actual_strictly_above_consensus`
- `eps_actual_strictly_above_consensus`

Each event identity is the exact tuple of normalized ticker, fiscal period, and
UTC cutoff. Each `excluded_events` item contains exactly `ticker`,
`fiscal_period`, `as_of_timestamp`, `reason`, and `detail`. Expected and excluded
identities must each be unique and mutually disjoint. Exclusion reasons and
details must be non-placeholder text. `selection_rule` must be non-empty and is
preserved as untrusted operator context; the preview cannot prove that the rule
was correctly applied to the market universe. Period bounds must be valid
fiscal periods and every declared identity must fall inside them.

### Observation contract

Every observation has exactly:

- `ticker`
- `fiscal_period`
- `as_of_timestamp`
- `outcome_definition`
- `probability`
- `outcome`

Every observation must be fully identity-bound. Identity-less or partially
bound observations are rejected. All observations must use the cohort's one
declared outcome definition and have unique identities. Probability must be a
finite JSON number in `[0, 1]`; Boolean and string representations are rejected.
Outcome must be a JSON Boolean.

Observation probabilities are sensitive research evidence. They are used for
recomputation but never emitted row-by-row in text or JSON preview output.

### Backtest report contract

`backtest_report` carries every field required to reconstruct the existing
`BacktestReport`, including its full `events` collection. Every event carries
the existing `BacktestEvent` fields, ordered non-empty `input_source_ids`,
non-placeholder `model_version`, lowercase SHA-256 `input_snapshot_hash`, input
and target chronology, forecasts, intervals, actuals, consensus, prior-year
benchmarks, and relative classification.

The preview does not trust stored report counts, aggregate metrics, failure
arrays, benchmark arrays, classifications, or outcomes merely because they are
present. It recalculates or reconciles every value supported by the existing
contracts and fails closed on a mismatch.

### Evidence-reference contract

`evidence_references` is a non-empty array of exact operator-provided reference
objects containing:

- `source_id`
- `source_ref`
- `rights_decision_ref`
- `review_status`

References are normalized and included in the preview digest. They are not
source attestation. `review_status` may be `unreviewed`, `review_required`, or
`reviewed`, but even `reviewed` cannot prove authenticity, rights, or accurate
field mapping. The preview always keeps external source review required.

## Validation And Reconciliation

The parser rejects malformed JSON, duplicate JSON object keys at any depth,
unknown or missing keys, wrong scalar types, non-finite numbers, blank values,
placeholder references, malformed periods or timestamps, invalid hashes, and
unsupported enum values. Errors include a stable field path without echoing
probability values.

After parsing, the preview performs these independent checks:

1. package schema and exact-byte digest;
2. fixed policy and cohort declaration;
3. unique, bounded, mutually disjoint cohort identities;
4. observation identity and declared-outcome consistency;
5. exact equality between expected cohort identities, observation identities,
   and retained backtest-event identities;
6. exclusion accounting between the structured declared exclusions, report
   exclusion count, per-reason counts, and excluded-event details;
7. `latest_input_timestamp <= as_of_timestamp < target_reported_at` for every
   retained event;
8. complete ordered source IDs plus model and input-snapshot identity;
9. the declared strict outcome rederived from the event's actual and matching
   consensus value, with equality treated as not above consensus;
10. stored observation outcome equality with that rederived outcome;
11. stored relative classification equality with the existing interval-derived
    classification contract;
12. report event counts, valid counts, exclusion counts, failures, leakage
    failures, benchmark failures, summary metrics, and benchmark metrics;
13. fresh calibration assessment using the repository's fixed policy;
14. exact calibration-observation and backtest-package digests;
15. matching metric-model benchmark improvement for the declared Revenue or EPS
    outcome.

Aggregate calibration diagnostics may be reported because they evaluate the
historical evidence package rather than exposing a company Beat/Miss
probability. Allowed aggregate values are event count, Brier score,
constant-rate benchmark Brier score, calibration error, bin counts and sizes,
and named failed gates. Per-event probability, per-event forecast, and company
ranking output are forbidden.

## Preview States

The result uses one of three technical states:

- `invalid`: the file cannot be parsed or violates the strict package schema;
- `blocked`: the package is valid enough to inspect but one or more internal
  reconciliation or calibration gates fail;
- `contract_consistent_review_required`: all supported internal checks pass,
  but external source, rights, independent review, and real-event sufficiency
  remain outside local software proof.

The state name `calibrated`, `ready`, or `probability_available` is never used as
the preview verdict. Every result, including an internally consistent bundle,
sets these immutable boundaries:

- `probability_state="withheld"`
- `probability_exposure=False`
- `readiness_promotions=()`
- `persistence=False`
- `preview_receipt_persisted=False`
- `external_source_review_required=True`
- `independent_review_required=True`

Actuals, consensus, Revenue, EPS, valuation, catalysts, outcomes, backtesting,
calibration, peers, and quant interpretation readiness remain independent and
unchanged.

### Result contract

`CalibrationEvidenceBundlePreview` contains exactly:

- `schema_version="calibration-evidence-bundle-preview-v1"`
- `state`
- `bundle_id`
- `bundle_sha256`
- `outcome_definition`
- `expected_event_count`
- `observation_count`
- `backtest_event_count`
- `excluded_event_count`
- `brier_score`
- `benchmark_brier_score`
- `calibration_error`
- `calibration_bins`
- `passed_gates`
- `blocked_gates`
- `evidence_digest`
- `backtest_evidence_digest`
- `probability_state="withheld"`
- `probability_exposure=False`
- `readiness_promotions=()`
- `persistence=False`
- `preview_receipt_persisted=False`
- `external_source_review_required=True`
- `independent_review_required=True`
- `boundary`

`calibration_bins` exposes only bin bounds, event count, mean historical input
probability, historical outcome rate, and minimum-size result. It never carries
event identities or row-level values. `passed_gates` and `blocked_gates` use
stable machine-readable names in deterministic order. A blocked gate includes
one redacted human-readable explanation in the JSON payload and text renderer.

## Interfaces

### Python

- `CalibrationEvidenceBundleError`
- `CalibrationEvidenceBundlePreview`
- `load_calibration_evidence_bundle(path)`
- `preview_calibration_evidence_bundle(path)`
- `calibration_evidence_bundle_payload(preview)`
- `render_calibration_evidence_bundle_preview(preview)`

The load function returns immutable parsed evidence plus exact input bytes or an
internal exact-byte digest. The preview is deterministic for the same byte
input and repository policy. Public payload and text renderers expose only the
redacted contract described above.

### CLI And Make

- `python3 -m src.calibration_evidence_bundle preview --bundle <path>`
- `python3 -m src.calibration_evidence_bundle preview --bundle <path> --format json`
- `make calibration-evidence-bundle-preview BUNDLE=<path>`

Text is the default human-readable output. JSON is stdout only and exists for
automation; neither format writes a file. A valid `blocked` preview exits zero
because the tool completed and reported a truthful gate result. Invalid schema,
missing input, I/O failure, or parser failure exits two with a concise redacted
error on stderr.

The CLI opening copy states that it is read-only, research-only, and cannot
activate readiness or expose a probability. No status, record, apply, refresh,
or append subcommand is added.

## Error And Race Handling

The module opens and reads the explicit input once, parses only those captured
bytes, and computes identity from the same bytes. A path replacement after the
read cannot change the assessed snapshot. The preview never writes a receipt or
persists a digest, so no confirmation or append race exists.

Missing files, directories supplied as files, unreadable inputs, inputs larger
than exactly 16 MiB (`16 * 1024 * 1024` bytes), malformed UTF-8, malformed JSON,
and duplicate JSON keys fail closed. Parser and validation messages do not echo
raw rows, source secrets, or probability values. Unexpected exceptions remain
nonzero failures rather than being converted into a reviewable state.

## Testing Strategy

Implementation must use strict red-green TDD. Focused tests will prove:

1. missing, unreadable, oversized, non-UTF-8, malformed, and duplicate-key JSON
   inputs fail closed without repository writes;
2. exact schema, type, enum, placeholder, timestamp, fiscal-period, digest, and
   finite-number validation;
3. fixed 100-event policy cannot be weakened by the bundle;
4. identity-less, partially bound, duplicated, mixed-outcome, out-of-period,
   and expected/excluded-overlap evidence is rejected;
5. cohort, observation, and backtest event identity sets must match exactly;
6. strict Revenue and EPS outcomes are rederived, including equality as not
   strictly above consensus;
7. chronology, leakage, exclusion accounting, model version, source order, and
   input hash gates fail closed independently;
8. report summaries, classifications, benchmark metrics, calibration metrics,
   bins, and canonical digests are recomputed rather than trusted;
9. below-100, poor-Brier, weak-bin, non-improving-benchmark, and missing-metric
   bundles return `blocked` with named gates;
10. a synthetic internally consistent 100-event fixture returns only
    `contract_consistent_review_required`, never calibrated readiness;
11. text and JSON output redact per-event probabilities and forecasts and never
    contain a Beat/Miss probability;
12. every preview preserves the immutable no-write, no-persistence,
    no-readiness-promotion, external-review-required boundary;
13. Make and CLI targets are read-only and create no CSV, JSON, report,
    screenshot, timing, ledger, or sample-report artifact;
14. repeated preview of identical bytes is deterministic, while any byte change
    changes the exact-file digest;
15. existing nowcast, cohort, dashboard, public wording, and generated-artifact
    gates remain green.

Synthetic fixtures remain test-only and cannot be checked in as real product
evidence or cited as calibration progress.

## Documentation And Delivery

After verified implementation:

- update `ROADMAP.md`, operator documentation, Make help, release-document tests,
  and `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`;
- state that valid real leakage-safe events remain zero unless direct permitted
  evidence proves otherwise;
- run focused tests, the full suite, dashboard and Research render smokes,
  accessibility browser checks, commercial beta/release, public, pilot, diff,
  PR-range, staged, whitespace, and protected-artifact checks;
- keep the existing 18 generated readiness/report/output paths unstaged and
  unchanged;
- stage exact code, test, Make, and documentation files only;
- commit coherently, push only `codex/personal-research-mode-mvp`, update draft
  PR #113, and require exact-head GitHub Actions success;
- do not merge or deploy publicly.

## Acceptance Criteria

The slice is complete only when direct current evidence proves all of these:

1. an operator can preview one explicit bundle in text or JSON without any file
   write or network access;
2. untrusted package data is strictly parsed and internally recalculated;
3. cohort, observation, backtest, chronology, outcome, exclusion, benchmark, and
   calibration mismatches fail closed with stable named blockers;
4. an internally consistent bundle remains review-required and probability is
   withheld;
5. no per-event probability, forecast, recommendation, rank, expected return, or
   transaction instruction is rendered;
6. no readiness state, ledger, canonical data, or generated artifact changes;
7. synthetic fixtures remain test-only;
8. focused, full, release, browser, public, pilot, and hygiene verification pass
   at the exact pushed HEAD;
9. PR #113 remains open and draft.

## Deferred Work

Separate approved designs are required before:

- uploading or previewing bundles in the dashboard;
- persisting preview receipts, validation packets, or calibration ledgers;
- activating calibration readiness or exposing a numerical probability;
- onboarding a real point-in-time consensus provider or claiming source rights;
- accumulating or publishing a real calibration cohort;
- setting or changing calibration thresholds after observing outcomes;
- ranking companies, estimating expected return, or adding any paper or live
  transaction workflow.
