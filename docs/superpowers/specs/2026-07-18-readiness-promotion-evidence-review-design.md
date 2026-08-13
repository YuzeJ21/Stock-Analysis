# Readiness Promotion Evidence Review Design

## Purpose

`make readiness-preview TOP_N=20` truthfully shows substantial proposed fundamentals and DCF readiness movement without writing generated artifacts. The current preview does not explain whether those promotions have complete provenance, an exact source-rights decision, or explicit field support in the checked-in rights registry. A reviewed readiness rebuild must not be authorized from numerical completeness alone.

Extend the existing no-write preview with a fail-closed promotion-evidence review. The review remains inspection evidence only: it does not change technical readiness, source rights, canonical inputs, or the separate rebuild boundary.

## Approaches Considered

1. **Extend the existing preview (selected).** Keep `make readiness-preview` as the only stale-readiness continuation command and add an independently labeled evidence section. This preserves the operating contract and makes the large proposed movement explainable in one place.
2. **Add a second provenance-preview command.** This would keep modules smaller, but it would create two continuation commands and require every stale-state surface to explain their ordering.
3. **Document a manual join.** This avoids code but produces non-repeatable evidence and leaves reviewers to reconcile hundreds of rows by hand.

## Evidence Model

The review examines only tickers moving from false to true for `fundamentals_ready` or `dcf_ready` between the saved and proposed in-memory readiness frames.

For each promoted ticker it records:

- which technical readiness flags would promote;
- the exact canonical fundamentals `source` value;
- the canonical `as_of_date`;
- a durable SEC accession when present;
- the exact commercial-rights decision for the complete source value;
- required fundamentals fields not listed in that exact rights record;
- missing provenance fields;
- a capped sample for review.

The source string is treated as one exact source identifier. Composite or unregistered values are not split, normalized into a different provider, or silently granted the rights of one component. That preserves the existing fail-closed registry contract.

## Independent States

The output keeps four questions separate:

1. **Technical promotion:** would production readiness logic move the saved flag?
2. **Provenance completeness:** are source, as-of date, and a durable source reference present?
3. **Commercial rights:** is the exact source identifier explicitly approved?
4. **Field scope:** does that exact approved record list every required field for the promoted fundamentals gate?

A technically complete row can therefore remain `evidence_review_required`. The review never changes the proposed readiness frame. DCF also depends on price evidence; because the canonical price table has no row-level provider/source columns, the output explicitly states that this review does not establish complete DCF commercial provenance.

## Required Field Contract

The current fundamentals readiness gate requires:

- `revenue`;
- `free_cash_flow` (or `fcf`);
- `fcf_margin`;
- `shares_outstanding`.

The evidence review uses the canonical names `revenue`, `free_cash_flow`, `fcf_margin`, and `shares_outstanding` when checking the registry. It reports missing registry support without editing the registry or inferring that a derived value is licensed.

## Statuses

- `no_promotions`: neither named readiness flag promotes.
- `evidence_review_complete`: every promoted row has complete provenance, approved exact-source rights, and complete registered field scope.
- `evidence_review_required`: at least one promoted row lacks one of those gates.

Even `evidence_review_complete` is not rebuild authorization. Reviewer approval, full readiness review, price-source review for DCF, and the separately authorized write boundary remain open.

## Failure Behavior

- Missing canonical fundamentals columns fail closed as missing evidence; no fallback value is invented.
- Duplicate canonical ticker rows fail closed for that ticker instead of selecting an arbitrary row.
- A missing or invalid rights registry makes the command fail with its existing concise no-write error path.
- Missing saved readiness keeps the existing `missing_saved_snapshot` result and does not attempt the evidence review.
- `TOP_N` caps row details but never changes total counts.

## Output

The existing saved-versus-proposed counts remain first. A new `Promotion Evidence Review` section then prints:

- total unique promotions, fundamentals promotions, and DCF promotions;
- exact source-value counts;
- rights-status counts;
- complete/incomplete provenance counts;
- complete/incomplete registered field-scope counts;
- capped ticker evidence rows and blockers;
- the separate rebuild, DCF price-provenance, research-only, and no-write boundaries.

No JSON, CSV, report, screenshot, timing, cache, or output-path mode is added.

## Testing

Test-first coverage will prove:

1. only false-to-true fundamentals/DCF changes enter the review;
2. exact registered approved sources remain distinct from composite and unknown labels;
3. missing as-of date, durable reference, required field support, duplicate ticker rows, and missing columns fail closed;
4. detail is capped without changing totals;
5. the integrated preview builds in memory and leaves the filesystem manifest unchanged;
6. wording never equates technical readiness movement with source correctness, commercial permission, current readiness, or rebuild approval.

## Completion Criteria

- `make readiness-preview TOP_N=20` explains the current proposed promotions with exact source/provenance/rights/field-scope evidence.
- The current repository remains byte-for-byte unchanged by the command.
- Technical readiness and commercial/evidence review states remain independent.
- ROADMAP, methodology/provenance documentation, the continuation prompt, and draft PR #113 record the verified boundary.
- No generated artifact is staged or committed.
