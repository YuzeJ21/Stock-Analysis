# Quarterly Cash-Generation Evidence Contract Design

## Decision

Add a supplemental in-memory quarterly business-metric contract for operating margin, free cash flow, and FCF margin. Do not add, generate, modify, or stage a CSV, JSON, report, sample report, screenshot, or timing artifact for this slice.

The existing Earnings Nowcast `QuarterlyActual` Revenue/EPS contract remains unchanged. The new contract is descriptive business-trend evidence only and cannot affect Nowcast ranges, consensus readiness, DCF inputs, peer valuation, research rankings, or recommendations.

## Why This Still Makes Sense

The current Company Workbench explicitly withholds operating margin, free cash flow, and FCF margin because those metrics have no versioned quarterly contract. A narrow domain contract closes that methodology gap without pretending that real-company evidence exists.

The repository currently has no canonical `data/earnings_nowcast/` evidence directory. Adding another generated file would therefore create synthetic-only persistence rather than activate reviewed evidence. Keeping the contract in memory preserves a future source-adapter boundary while honoring generated-artifact hygiene.

This slice proves calculation and readiness behavior only. It does not prove SEC extraction, source rights, real-company metric availability, or broader evidence depth.

## Alternatives Considered

### Extend the existing Revenue/EPS `QuarterlyActual`

Rejected. It would couple descriptive cash-generation analysis to the stable Earnings Nowcast evidence schema and force unrelated SEC staging and onboarding paths to carry optional fields.

### Add `quarterly_business_metrics.csv`

Rejected for this slice. It would introduce a new generated artifact and persistence workflow before a reviewed source path exists.

### Derive quarterly metrics from annual fundamentals

Rejected. Annual or trailing fundamentals cannot establish exact fiscal-quarter identity, cutoff availability, definition comparability, revision lineage, or explicit Q4 evidence.

## Domain Contract

Add an immutable `QuarterlyBusinessObservation` with:

- ticker;
- fiscal period and explicit period-end date;
- metric: `operating_income`, `cash_from_operations`, or `capital_expenditures`;
- finite reported value;
- currency, positive unit scale, accounting basis, and duration basis;
- source and durable source reference;
- timezone-aware publication and retrieval timestamps;
- Q4 evidence state;
- optional superseded source reference.

Capital expenditures retain their reported cash-flow sign. Free cash flow uses one explicit formula: `cash_from_operations + capital_expenditures`. No alternative issuer-defined FCF is silently substituted.

The constructor rejects missing identity, invalid periods, naive timestamps, non-finite values, unsupported metrics, non-positive scale, and Q4 rows without explicit filed-quarter evidence.

## Composition And Readiness

`build_quarterly_trend_packet` accepts supplemental observations as an optional iterable. Existing callers remain valid and continue to receive withheld supplemental metrics when no observations are supplied.

For each fiscal period:

1. Deduplicate exact source references.
2. Resolve revisions only through explicit `supersedes_source_ref` lineage.
3. Mark conflicting unversioned leaves ambiguous for the affected component only.
4. Exclude observations published after the requested cutoff.
5. Keep each metric independent; a blocked cash-flow component does not block Revenue or EPS.

Derived metrics require:

- operating margin: compatible operating income and Revenue for the same fiscal period;
- free cash flow: compatible cash from operations and capital expenditures for the same fiscal period;
- FCF margin: compatible free cash flow and Revenue for the same fiscal period.

Compatibility requires matching currency, unit scale, accounting basis, duration basis, fiscal period, and period-end date. Sequential and year-over-year changes use the existing exact-period comparison rules and remain withheld when a matching period or compatible definition is unavailable.

Readiness states remain independent:

- `ready`: latest value plus compatible sequential and year-over-year comparisons;
- `partial`: a source-backed latest value exists but one or both comparisons are unavailable;
- `blocked`: required components are missing, ambiguous, post-cutoff, or incompatible;
- `withheld`: no supplemental evidence was supplied.

## Product Integration

Company Workbench keeps the answer-first Business Trend section. When explicit observations are supplied by a future reviewed adapter, the existing trend table and cards may show operating margin, free cash flow, and FCF margin beside Revenue and EPS.

Without such observations, production behavior remains unchanged: all three supplemental metrics display `withheld`, no numeric placeholder appears, and the next step states that a reviewed quarterly source adapter is required.

Raw components, formula lineage, definitions, ambiguity reasons, and source references remain under Advanced Evidence. No new route, data writer, command, template, or generated artifact is added.

## Failure Boundaries

- Never derive Q4 from annual minus nine-month values.
- Never infer capital expenditure sign or issuer-defined FCF treatment.
- Never combine currencies, scales, period ends, duration bases, or accounting definitions.
- Never use retrieval time as publication time.
- Never let supplemental observations satisfy Earnings Nowcast, consensus, DCF, peer, catalyst, outcome, backtest, or calibration readiness.
- Synthetic observations remain test-only and must identify themselves as fixtures.
- Empty input remains visibly withheld rather than fabricated.

## Testing

Tests use in-memory synthetic dataclasses only; they do not write temporary or repository CSV/JSON files.

Cover:

- constructor validation and Q4 evidence enforcement;
- exact revision resolution and affected-component ambiguity;
- cutoff filtering;
- operating-margin, FCF, and FCF-margin formula lineage;
- currency, scale, accounting-basis, duration-basis, fiscal-period, and period-end incompatibility;
- independent ready, partial, blocked, and withheld states;
- sequential and year-over-year comparison behavior;
- unchanged Revenue/EPS results and Nowcast contracts;
- Company Workbench rows/cards for ready and withheld supplemental evidence;
- no writer, template, CLI target, or generated-artifact path introduced by the slice.

After implementation, run the focused modules, full test suite, dashboard smoke, Research route render smoke, public wording, public check, pilot readiness, diff hygiene, whitespace checks, and staged hygiene. Stage exact code, documentation, and test paths only.

## Completion Boundary

This slice is complete when the in-memory contract, independent readiness, answer-first rendering, documentation, and regression tests pass with no generated artifact created or staged.

Real-company operating margin, free cash flow, and FCF margin remain unproven and withheld until a separately reviewed source adapter supplies compatible observations with appropriate rights and lineage.
