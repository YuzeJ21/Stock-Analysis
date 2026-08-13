# EPS Split-Basis Enforcement Design

## Problem

SEC Companyfacts staging correctly labels Q1-Q3 EPS as
`companyfacts_split_basis_unverified`, and Earnings Nowcast readiness already
withholds that history. Two downstream paths do not yet enforce the same
sentinel:

- quarterly Business Trend can compare all-sentinel EPS rows and render a
  numeric EPS trend; and
- walk-forward backtesting can score a sentinel target EPS as ground truth.

Both behaviors overstate evidence without explicit primary split-basis proof.

## Decision

Define the sentinel once in the quarterly evidence contract and use it wherever
canonical EPS becomes a displayed comparison or evaluated outcome.

Quarterly Business Trend excludes sentinel EPS observations from every EPS
value and comparison. If none remain, EPS is blocked with an explicit split-basis
reason. If verified historical EPS remains beside withheld sentinel periods, the
trend stays partial and names those periods; Revenue remains independent.

Walk-forward backtesting replaces a sentinel target or prior-year EPS outcome
with `None` before error, interval, direction, or benchmark calculations. A
Revenue-bearing event remains eligible for Revenue evaluation. An event with no
other comparable target metric is excluded rather than counted as valid EPS
evidence.

The cohort lane inherits the Business Trend result, so commercial field-scope
approval cannot override an unverified EPS split basis. Synthetic fixtures may
exercise verified and unverified states in tests only.

## Boundaries

- No split basis is inferred from values, price history, provider metadata, or a
  matching sentinel in consensus.
- No existing canonical row, source-rights record, readiness artifact, nowcast,
  report, or ledger is rewritten.
- Explicit Q4 evidence, revision handling, source rights, consensus, calibration,
  and canonical loader integrity remain independent.

## Verification

- All-sentinel quarterly EPS blocks while Revenue remains usable.
- Mixed verified/sentinel history never renders or compares a sentinel value and
  remains partial.
- Commercial cohort EPS remains blocked even with an approved test-only EPS
  scope when its technical history uses the sentinel.
- Backtesting keeps Revenue evaluation but withholds sentinel EPS targets and
  prior-year EPS benchmarks.
- EPS-only sentinel target events are excluded from valid-event counts.
