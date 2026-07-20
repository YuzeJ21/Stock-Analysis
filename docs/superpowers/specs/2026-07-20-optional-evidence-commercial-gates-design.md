# Optional Evidence Commercial Gates Design

## Problem

Historical valuation, catalyst, and research-outcome ledgers preserve a source
identifier but currently do not join that exact identifier to the commercial
source-rights registry. A future non-empty ledger could therefore appear
supported or reviewed in the Commercial Research dashboard without permission
for that evidence lane.

## Contract

- Keep technical validity, chronology, exact-source commercial rights, and
  registered lane scope independent.
- In explicit Commercial Research composition, require every row used for a
  supported/reviewed result to pass the checked-in registry for its exact source
  ID and one literal lane scope:
  - `valuation_history` for historical valuation observations;
  - `catalyst_evidence` for supported catalyst events;
  - `research_outcomes` for reviewed outcome evidence.
- Do not infer aliases, split composite source IDs, or borrow permission from a
  different source or lane.
- One unapproved or scope-incomplete row blocks the supported/reviewed result
  for that scoped packet and remains visible only as blocker evidence.
- Candidate catalyst context remains candidate-only and cannot satisfy the
  supported-evidence gate.
- Empty ledgers retain their existing empty/blocked states and display no
  fabricated content.
- Research-mode builders retain their existing evidence-review behavior.

## Boundaries

This slice does not approve any source, edit the rights registry, populate a
ledger, validate payload truth, change readiness, or activate forecasts. It
adds no provider call and no generated artifact.
