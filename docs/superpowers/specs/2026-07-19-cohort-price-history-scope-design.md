# Cohort Price-History Scope Enforcement Design

## Status

Approved by the owner-supplied Priority 2 audit contract on 2026-07-19. This slice covers adjusted daily price history in focused-cohort Commercial Research coverage only. It does not change the direct refresh guard, staged-price apply, DCF lineage preview, canonical price schema, or quarterly actuals.

## Problem

`build_focused_cohort_coverage()` currently labels adjusted daily price history `usable_now` whenever saved readiness says `price_ready`. In Commercial Research mode, the dashboard passes no canonical price rows into the cohort evidence review, so the lane never checks technical row availability, row provenance, exact-source rights, or registered `prices` scope.

The current canonical `data/prices.csv` has OHLCV fields but no `source`, `source_ref`, or `retrieved_at`. That history can remain useful for local research, but it cannot truthfully become commercially supported price evidence.

## Design

Add an optional `prices` frame to `derive_cohort_evidence()` and load it through the existing read-only dashboard path. For each cohort ticker:

- technical history exists only when at least one row has a date and positive adjusted close or close;
- research mode preserves existing saved-readiness behavior;
- Commercial Research mode requires every technically retained history row to carry exact `source`, durable `source_ref`, and explicit `retrieved_at` provenance;
- every exact source must have approved commercial rights and literal `prices` scope;
- blank, unknown, composite, unapproved, scope-incomplete, or mixed-source rows fail the lane closed;
- the saved `price_ready` flag remains independent and necessary, but is no longer sufficient.

The result adds a price evidence state and explanation to the existing evidence map. `build_focused_cohort_coverage()` conjuncts it only when supplied. This preserves compatibility for direct research-mode callers while making the Commercial dashboard fail closed.

## Evidence Boundary

Advanced cohort evidence names whether the blocker is missing technical rows, missing row provenance, unapproved exact-source rights, or missing `prices` scope. It does not expose raw price rows in the primary answer.

This review does not infer a provider from a file name, adapter, warning, date, value shape, or earlier refresh. It does not validate retrieval chronology; timezone and cutoff enforcement belong to Priority 5. It does not approve a source, rewrite history, rebuild readiness, or invalidate local research use.

## Testing

Tests must prove:

- saved `price_ready=true` plus missing price rows blocks Commercial Research price coverage;
- canonical-shaped rows without lineage remain blocked;
- an injected approved exact source with `prices` scope and complete lineage can pass;
- an approved source without `prices` scope remains blocked;
- one unproven row makes a mixed history blocked;
- research mode retains the existing readiness-backed lane;
- dashboard loading uses the canonical price frame read-only and shows the blocker under Advanced evidence.

## Remaining Priority 2 Work

Canonical quarterly Revenue and EPS still require their own field-specific rights/scope integration, including partial-ledger and EPS split-basis behavior. This price slice does not address them.
