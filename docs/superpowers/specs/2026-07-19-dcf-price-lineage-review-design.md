# DCF Price Lineage Review Design

## Purpose

`make readiness-preview TOP_N=20` already separates proposed technical fundamentals and DCF promotions from fundamentals provenance, exact-source commercial rights, and registered field scope. DCF also requires a saved price row, but the current promotion review stops at an explicit statement that price-source provenance remains unproven.

Extend the same no-write preview with an independent, fail-closed DCF price-lineage review. The review must explain the exact latest price row selected for each proposed DCF promotion without changing technical readiness, canonical price data, source rights, valuation math, or the separately reviewed readiness rebuild.

## Approaches Considered

1. **Extend the existing preview with a pure price-lineage component (selected).** Preserve `make readiness-preview` as the only continuation-safe command while keeping price evidence in its own data structures and output section.
2. **Add a second price-lineage command.** This would isolate the command surface, but it would weaken the existing stale-readiness rule by creating a second safe command and an ordering problem for operators.
3. **Migrate the canonical price schema now.** This could support future row-level lineage, but it would write broad generated price churn and still could not reconstruct missing historical provider evidence truthfully.

## Selection Contract

The review examines only tickers moving from false to true for `dcf_ready` between the saved and proposed in-memory readiness frames.

For each promoted ticker it applies the same practical row-selection rule used by the local report provider:

1. normalize the ticker and parse the canonical observation `date`;
2. keep rows with a valid date and positive numeric `close`;
3. identify the greatest observation date;
4. require exactly one row at that latest date;
5. inspect that selected row without inferring values from older rows or file metadata.

A missing usable row fails closed as `missing_latest_price_row`. More than one row at the latest date fails closed as `ambiguous_latest_price_row`. The audit does not silently choose the last duplicate because duplicate grain is evidence ambiguity even though a downstream provider may currently select by row order.

## Evidence Model

For each proposed DCF promotion the review records:

- ticker;
- selected latest observation date;
- number of valid price rows and latest-date candidates;
- exact row-level `source` value;
- durable row-level source reference from `source_ref`;
- row-level retrieval or review timestamp from `retrieved_at`;
- exact commercial-rights status for the complete source identifier;
- whether the rights record explicitly supports `prices`;
- missing provenance fields and blockers.

The observation date is market-data evidence, not a retrieval timestamp. `as_of_date`, a file modification time, a `local:prices.csv` provider label, refresh warnings, or knowledge that an adapter exists cannot substitute for `retrieved_at` or `source_ref`. The source identifier is evaluated exactly; composite, missing, or unregistered values are not split or mapped to a guessed provider.

## Independent States

The output keeps five questions separate:

1. **Technical DCF promotion:** would production readiness move `dcf_ready` from false to true?
2. **Latest price selection:** is there exactly one usable latest row?
3. **Lineage completeness:** does that row carry `source`, `source_ref`, and `retrieved_at`?
4. **Commercial rights:** is the exact source explicitly approved?
5. **Registered field scope:** does that rights record explicitly support `prices`?

The technical promotion remains untouched even when every price-lineage evidence gate is blocked. Conversely, complete lineage would not establish fundamentals evidence, reviewer acceptance, data freshness, or rebuild approval.

## Statuses

- `no_dcf_promotions`: no ticker moves from false to true for `dcf_ready`.
- `price_lineage_review_complete`: every promoted ticker has one usable latest row, complete row-level lineage, approved exact-source commercial rights, and registered `prices` support.
- `price_lineage_review_required`: at least one promoted ticker lacks one of those gates.

Even `price_lineage_review_complete` is inspection evidence only. It cannot make saved readiness current or authorize `make readiness`.

## Failure Behavior

- Missing price columns fail closed rather than inventing a source, reference, timestamp, date, or close.
- Missing price files are treated as empty evidence and leave the review required when DCF promotions exist.
- Invalid dates and nonpositive or nonnumeric closes are not usable latest-price evidence.
- Duplicate latest-date rows fail closed even if their values match.
- A missing or invalid rights registry keeps the command on its existing concise no-write error path.
- `TOP_N` caps rendered evidence rows but never changes aggregate counts.
- Missing saved readiness preserves the existing `missing_saved_snapshot` result and does not start the price review.

## Architecture

Add a small pure module, `src/dcf_price_lineage.py`, containing frozen evidence/review structures and `review_dcf_price_lineage(...)`. `src/readiness_preview.py` will:

- reuse the existing saved and proposed readiness frames;
- read `data/prices.csv` only after a saved snapshot is available;
- pass the already loaded immutable rights registry into the pure review;
- attach the result independently to `ReadinessImpactPreview`;
- render a `DCF Price Lineage Review` section after the fundamentals promotion review.

No readiness engine, local provider, canonical schema, import, refresh, or valuation code changes are part of this slice.

## Output

The new stdout section reports:

- DCF promotion count;
- usable and ambiguous latest-row counts;
- complete and review-required lineage counts;
- approved and review-required rights counts;
- complete and review-required registered price-field scope counts;
- exact source and rights-status counts;
- capped per-ticker evidence rows;
- explicit no-inference, no-readiness-change, and no-rebuild-authorization boundaries.

No CSV, JSON, report, sample-report, screenshot, timing, cache, directory, or output-path mode is added.

## Testing

Test-first coverage will prove:

1. only false-to-true DCF promotions enter the review;
2. one unique latest valid row is selected deterministically;
3. missing rows, invalid rows, duplicate latest dates, missing provenance, unknown/composite sources, unapproved rights, and missing `prices` field support fail closed independently;
4. exact approved source evidence can complete the local audit without changing readiness;
5. detail capping preserves totals;
6. integrated preview output preserves technical, lineage, rights, field-scope, and rebuild boundaries;
7. the complete filesystem manifest is unchanged by the command.

## Completion Criteria

- `make readiness-preview TOP_N=20` explains DCF price evidence for every proposed DCF promotion.
- Current canonical rows are truthfully reported as lacking complete row-level lineage; no provider is inferred.
- The command remains byte-for-byte no-write.
- Technical readiness and every evidence/readiness state remain independent.
- ROADMAP, methodology, provenance/data strategy, the continuation prompt, and draft PR #113 record the verified result and exact next gate.
- No generated artifact is staged or committed.
