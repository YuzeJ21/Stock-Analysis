# Peer Lane Readiness Source Precedence Design

**Status:** Approved for bounded local implementation; no remote synchronization or generated-artifact mutation is authorized.

## Problem

The selected Data Health peer lane can display a stale count from
`outputs/project_status.json` even when the selected profile's saved readiness
summary contains a newer authoritative peer-readiness count. The current local
case renders `29 tickers have trusted peer context` from an older 3,541-row
project-status snapshot while the saved readiness report records 9 peer-ready
rows across 3,538 tickers.

This conflicts with the product contract that current saved readiness is
authoritative for current lane availability. Project status remains useful for
operating context, source setup, and next-step routing, but it must not widen a
readiness-owned count over a present saved readiness value.

## Decision

`data_health_selected_lane_answer_cards()` will resolve readiness-owned counts
in this order:

1. Use the selected saved readiness summary when any requested canonical or
   alias key is present, parseable, and backed by the corresponding source
   column. The summary adapter records count-level evidence keys so a missing
   column cannot become authoritative zero. A source-backed saved value of zero
   is authoritative; it must not be treated as missing.
2. Fall back to the saved project-status summary only when the selected saved
   readiness summary does not provide the requested count.
3. Report the count as unavailable when neither source provides it.

The rule applies to the readiness-owned values displayed by the selected-lane
answer: price, fundamentals/input, DCF, peer, and blocked/locked-input counts.
Project-status-only source availability counts, lane inspection notes, and
recommended next-step context retain their current behavior.

## Route Behavior

Personal Research and Operator Data Health use the same source-precedence
contract. With the current local artifacts, both peer lanes must display the
saved peer-ready count of 9 rather than the stale project-status count of 29.
Candidate peers remain context only, and the answer must continue to avoid
recommendation, ranking, allocation, sizing, transaction, or performance
language.

If saved readiness is missing, the route may use a complete available
project-status count. If both are missing or malformed, it must fail closed to
an unavailable count. No route may refresh, rebuild, materialize, or mutate
readiness to resolve the disagreement.

## Implementation Boundary

- Modify the selected-lane count-resolution helper, the readiness-summary
  adapter that supplies count-level provenance, and focused tests only.
- Do not edit `data/`, `outputs/`, source-rights decisions, thresholds, or
  readiness calculations.
- Do not refactor unrelated Data Health presentation or navigation.
- Do not push, deploy, publish, tag, or release.

## Verification

Focused regressions must prove:

- a conflicting project-status peer count cannot override a present saved
  readiness peer count;
- a saved zero remains zero and cannot fall through to a larger project count;
- a nonempty saved report missing the requested count column falls back instead
  of promoting its synthesized zero;
- project status remains a fallback when saved readiness omits the count;
- missing counts remain unavailable rather than becoming factual zeroes;
- Personal and Operator selected peer-lane rendering use the same corrected
  behavior;
- existing source-context and no-advice boundaries remain intact.

Run the focused helper and route-render tests first. Run only the smallest
affected browser proof for the Personal and Operator peer routes unless the
final diff changes shared layout, navigation, or browser-gate code.
