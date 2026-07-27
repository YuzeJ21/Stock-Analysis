# Observation Recency Design

## Decision

Implement an independent, read-only observation-recency contract. Saved-readiness
freshness and market-observation recency remain different facts everywhere.

The approved approach is a typed, provider-neutral evaluator over the selected
profile's existing `prices.csv`. It does not refresh prices, infer a provider,
change readiness, mutate a ledger, or create a generated artifact.

## Problem

The selected profile can truthfully report that saved readiness is current for
the saved source files while its latest market observations are old. On
2026-07-27 the current worktree reported:

- saved readiness: `current`;
- latest profile price observation: `2026-06-05`;
- NVDA, AMD, AVGO, and MU: `2026-05-22`;
- QCOM: no price observation;
- SPY and QQQ: `2026-03-14`.

The current UI labels the saved-readiness state as `Freshness: Current`. That can
be misread as current-market evidence. Calculation availability must not create
that implication.

## Goals

1. Preserve saved readiness exactly as its own state.
2. Evaluate selected-company and benchmark observation dates independently.
3. Display the exact `through_date` beside every recency state.
4. Fail closed when a usable observation date is absent.
5. Keep stale observations available only as historical research context.
6. Prevent stale or missing observations from supporting a current-market
   conclusion.
7. Keep the implementation read-only and deterministic.

## Non-Goals

- No provider fetch, refresh, import, readiness rebuild, or canonical write.
- No exchange-calendar or intraday-latency claim.
- No forecast, probability, company ranking, expected-return score, position
  sizing, allocation, recommendation, or transaction direction.
- No change to actuals, consensus, Revenue, EPS, valuation, catalyst, outcome,
  backtesting, or calibration readiness.
- No claim that a recent price has complete provenance, rights, or source proof.

## Approaches Considered

### 1. Typed independent recency contract — approved

Use one pure evaluator for selected securities and benchmarks and make every UI
consumer use its result. This gives one testable policy without coupling it to
saved readiness.

### 2. UI-only relabeling — rejected

Changing `Freshness` to `Saved readiness` would remove one misleading label but
would not provide a fail-closed observation state or protect downstream views.

### 3. Provider-specific exchange-calendar logic — deferred

This could model holidays and intraday publication latency, but it would add
external dependencies and source-specific behavior before the product has one
permitted operating market-data source.

## State Contract

`ObservationRecency` contains:

- `scope`: selected ticker, profile price lane, or exact benchmark ticker;
- `through_date`: latest valid observation date not after the explicit review
  date;
- `age_days`: calendar-day difference from the explicit review date;
- `state`: `current`, `stale_review_only`, or `unavailable`;
- `message`: concise user-facing explanation;
- `excluded_date_count`: malformed or future-dated values excluded from the
  decision.

Policy:

- `current`: a valid observation exists and is at most seven calendar days old;
- `stale_review_only`: a valid observation exists and is more than seven
  calendar days old;
- `unavailable`: no valid observation exists on or before the review date.

Seven calendar days is a conservative local review policy, not a statement
about exchange sessions or provider service levels. The exact date remains
visible so a reviewer can judge context directly.

A future or malformed value never becomes current. If a scope contains both a
valid value and excluded values, the valid value determines the state and the
excluded count remains visible in Advanced evidence. If no valid value remains,
the state is `unavailable`.

## Architecture

Create `src/observation_recency.py` with:

- immutable result dataclasses;
- CSV-row evaluation that accepts an explicit `as_of` date;
- one selected-ticker result;
- one profile-price-lane result;
- one result per exact benchmark ticker, initially `SPY` and `QQQ`;
- deterministic display helpers.

The evaluator accepts rows or a path supplied by the caller. It opens the
selected profile file read-only and never falls back to another profile.

`ProfileContext.freshness_state` remains the saved-readiness state for
compatibility. Dashboard copy relabels it `Saved readiness`. Observation
recency is built separately so no consumer can promote one state from the
other.

## UI Contract

Across Research Desk, Discover, Company Workbench, and Monitor:

- replace the ambiguous `Freshness` label with `Saved readiness`;
- show the latest profile price observation and its state;
- never write `current-market` when the observation is stale or unavailable.

Company Workbench additionally shows:

- selected ticker `through_date` and state;
- SPY and QQQ `through_date` and state independently;
- stale values as `Historical context only`;
- unavailable values as `No current-market interpretation`.

The primary answer shows the date and state. Excluded-date counts, policy
threshold, file path, and raw date diagnostics stay under Advanced evidence.

Forward View and quantitative review copy may continue to say that saved
evidence/readiness is current only when clearly labelled as saved state. It
must not use that state as market-observation freshness.

## Error Handling

- Missing `prices.csv`: all observation scopes are `unavailable`.
- Missing ticker: only that ticker is `unavailable`.
- Missing benchmark: only that benchmark is `unavailable`.
- Invalid or future date: exclude it and retain the diagnostic count.
- File read error: return fail-closed unavailable results with no exception
  exposed in the primary research answer.

No error path writes a file or changes readiness.

## Testing

Focused tests must prove:

- current, stale, unavailable, malformed, and future-date behavior;
- exact seven-day boundary;
- selected ticker and each benchmark remain independent;
- one missing benchmark cannot change the selected ticker state;
- selected profile isolation;
- saved readiness remains unchanged;
- primary UI exposes exact dates and truthful labels;
- Advanced evidence contains policy and exclusion diagnostics;
- stale data cannot produce current-market wording.

The local fixture test must demonstrate that the existing worktree data is
classified stale or unavailable as of 2026-07-27 without modifying it.

Full release, render, public-wording, hygiene, and exact-head CI gates remain
required.

## Acceptance Criteria

1. No Personal Research route displays ambiguous `Freshness: Current`.
2. Saved readiness and observation recency are visibly independent.
3. Selected ticker, SPY, and QQQ show exact, independently evaluated dates.
4. Stale observations are labelled `stale_review_only` and historical context
   only.
5. Missing observations fail closed.
6. No generated file or research ledger changes.
7. Full verification and exact-head CI pass.
