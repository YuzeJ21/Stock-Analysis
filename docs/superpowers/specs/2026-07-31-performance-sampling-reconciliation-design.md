# Commercial Beta Performance Sampling Reconciliation Design

## Problem

The Commercial Research performance gate records one cold and five warm samples for each route and viewport. Before this repair, its `shell_p90_seconds` and `first_useful_p90_seconds` combined all six samples. Nearest-rank p90 of six values selected rank six, so each reported p90 was actually the maximum of a mixed cold-and-warm population. A single cold observation therefore determined metrics labelled p90, while the gate already treated full-settle cold and warm evidence separately.

This is a measurement-classification defect. It does not prove that current page startup cost is acceptable, and it must not be repaired by lowering the three-second limit, selecting a fastest run, retrying until green, or discarding cold evidence.

## Approved Boundary

The continuation contract requires deterministic sampling, explicit cold/warm separation, and an unchanged three-second first-useful threshold. The repair stays inside that boundary:

- `warm_shell_p90_seconds` measures successful warm shell samples only.
- `cold_shell_max_seconds` measures successful cold shell samples only.
- `warm_first_useful_p90_seconds` measures successful warm samples only.
- `cold_first_useful_max_seconds` measures successful cold samples only.
- shell metrics are independently enforced against `shell_seconds = 1.0`;
- first-useful metrics are independently enforced against `first_useful_seconds = 3.0`;
- warm full-settle p90 and cold full-settle maximum remain unchanged;
- missing required warm or cold samples continue to fail closed;
- raw samples remain available in the temporary performance payload for diagnosis;
- no automatic retry, outlier deletion, fastest-run selection, threshold relaxation, or generated repository artifact is introduced.

The existing combined `shell_p90_seconds` and `first_useful_p90_seconds` fields are removed from the summary and documented payload rather than retained as ambiguous compatibility aliases. Repository consumers are limited to the gate, its tests, and documentation, so an explicit contract change is safer than preserving misleading metrics.

## Data Flow

`run_browser_performance_gate()` continues to collect one cold and five warm samples by default. `summarize_route_timings()` partitions shell and first-useful values by `run_kind`, exactly as it already partitions full-settle values. `evaluate_performance_gate()` checks all warm/cold categories independently and names the failing category in its evidence message.

This slice changes measurement semantics only. It does not optimize the Streamlit routes. After the repair, a controlled browser run determines whether the product has a reproducible cold or warm page-cost failure. Only category-specific failing evidence can justify a later startup optimization.

## Error Handling and Truth Boundaries

Failed browser samples remain failures. Required sample counts remain enforced. A health-check failure remains a gate failure and is not silently converted into a timing sample. The result remains performance evidence only and does not prove data freshness, source rights, reviewer validation, hosted operation, or investment usefulness.

The daily momentum and valuation queue remains fail closed. This performance repair cannot activate a ticker, change readiness, generate a recommendation, or alter any deterministic research calculation.

## Verification

Tests must first demonstrate the current defect with cold shell and first-useful values above their limits and five warm values below them. The implementation must then expose and enforce the separate warm p90 and cold maximum for both measurement stages. Focused tests, full pytest, dashboard and research render checks, public wording/package checks, commercial-beta performance and release checks, pilot readiness, accessibility checks, diff hygiene, whitespace checks, and staged hygiene remain required as applicable.

The browser result is written only to the existing `/tmp` evidence location and is never staged. Existing generated CSV, JSON, report, sample-report, screenshot, timing, canonical-data, and manual-review churn remains excluded.

## Acceptance Criteria

1. The summary contains `warm_shell_p90_seconds`, `cold_shell_max_seconds`, `warm_first_useful_p90_seconds`, and `cold_first_useful_max_seconds` for every route and viewport with successful samples.
2. Warm and cold shell or first-useful values never share a percentile population.
3. Either shell category exceeding 1.0 seconds or either first-useful category exceeding 3.0 seconds fails the gate with an explicit category label.
4. Missing warm or cold samples continue to fail closed through the existing count contract.
5. Warm full-settle p90 and cold full-settle maximum semantics do not change.
6. No threshold, route marker, retry policy, readiness state, research output, or source-rights behavior changes.
7. A current controlled browser run provides category-specific evidence before any page startup optimization is considered.
