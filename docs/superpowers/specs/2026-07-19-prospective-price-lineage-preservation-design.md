# Prospective Price Lineage Preservation Design

## Purpose

The DCF price-lineage review proves that canonical price availability is independent from provider provenance. The current manual price workflow can record `source` and `as_of_date`, but it cannot accept or preserve the required durable `source_ref` and `retrieved_at`. Validation currently treats those fields as unknown, so a prospectively reviewed row cannot satisfy the lineage contract even when the user has the evidence.

Extend the existing price normalization, validation, preview, and apply contracts so one prospectively sourced row can carry complete row-level lineage. This slice changes schemas and summaries only; it does not create a repository data file, run a repository apply, edit source rights, or make a source commercially approved.

## Approaches Considered

1. **Extend the existing staged-row contract (selected).** Accept explicit source reference and retrieval timestamp metadata in the normalizer, preserve them through validation/preview/apply, and report lineage completeness independently from technical row validity.
2. **Require complete lineage for every local price import.** This would fail closed for commercial evidence, but it would incorrectly couple technical local-research price usability to a separate rights/provenance gate and break existing imports.
3. **Create a separate price-provenance sidecar.** This could avoid widening the canonical schema, but it would introduce another file, merge key, drift risk, and generated-artifact surface before a single reviewed source path exists.

## Explicit Input Contract

The normalizer adds optional arguments:

- `source_ref`: a durable reviewed reference for the exact source payload or row batch;
- `retrieved_at`: the source retrieval timestamp supplied by the reviewer.

Neither value receives a generated default. The workflow must not turn normalization time, file modification time, observation date, `as_of_date`, input file name, or source label into either field. Existing `source` and `as_of_date` behavior remains unchanged for compatibility.

CLI and Make routing add `--source-ref`, `--retrieved-at`, `SOURCE_REF`, and `RETRIEVED_AT`. Arguments are optional so existing local-research commands continue to work. Documentation must show that both are required before claiming complete row-level lineage.

## Staged Schema

The staged price schema becomes:

`date,ticker,open,high,low,close,volume,adjusted_close,source,source_ref,retrieved_at,as_of_date,notes`

Validation retains `source_ref` and `retrieved_at` as optional evidence columns. Apply logic already widens canonical output to retained optional staged columns; tests will prove both fields survive new and updated rows. No production apply is run in this slice.

## Independent Validation States

Technical OHLCV validity remains based on the existing date, ticker, numeric columns, positive close, nonnegative volume, high/low, and duplicate rules.

For valid rows, validation separately reports:

- `lineage_status`: `no_valid_rows`, `lineage_complete`, or `lineage_review_required`;
- `lineage_complete_rows`;
- `lineage_review_required_rows`;
- `lineage_missing_fields`: any of `source`, `source_ref`, or `retrieved_at` missing or invalid across reviewed rows.

A parseable retrieval timestamp is required for lineage completeness. The original supplied timestamp is normalized to a UTC ISO-8601 string for deterministic output. A missing or invalid value remains blank and is reported; it is not replaced with the current time.

Lineage completeness does not establish exact-source commercial rights, registered `prices` scope, freshness, reviewer approval, or readiness. Those remain independent gates in the DCF price-lineage review and source-rights registry.

## Preview And Apply Behavior

`price-validate` and `price-preview` expose the lineage summary alongside existing technical merge counts. The preview remains read-only.

`price-apply` retains the two new fields when an explicitly reviewed apply is later authorized. It does not become automatically authorized by a complete lineage summary. Existing backup, merge-key, scope-review, and no-delete behavior remains unchanged.

## Failure Behavior

- Missing evidence fields do not invalidate otherwise valid local-research OHLCV rows; they set `lineage_review_required`.
- Invalid `retrieved_at` is blanked for retained evidence and reported as missing rather than preserved as a credible timestamp.
- Empty source references remain missing.
- Duplicate date+ticker handling remains unchanged and keeps the last staged row; its lineage fields travel with that exact row.
- Unknown columns continue to warn and remain excluded.
- No source ID is split, normalized into another provider, or granted commercial rights.

## Testing

Test-first coverage will prove:

1. explicit source reference and retrieval timestamp survive normalization;
2. no timestamp or reference is invented when arguments are absent;
3. validation distinguishes complete from review-required lineage without changing technical validity;
4. invalid retrieval timestamps fail closed;
5. preview preserves the fields and exposes the same counts;
6. a temporary-fixture apply preserves both fields on updated and new rows without deleting unrelated rows;
7. existing normalization and price import tests remain compatible;
8. repository data and generated-artifact hygiene remain unchanged.

## Completion Criteria

- One temporary prospective row can retain `source`, `source_ref`, and `retrieved_at` through normalize, validate, preview, and apply tests.
- Missing evidence remains explicit and non-fabricated.
- Technical validity, lineage completeness, source rights, field scope, reviewer decision, and readiness remain independent.
- ROADMAP, methodology/data strategy, continuation prompt, Make help, and draft PR #113 record the boundary.
- No repository CSV, JSON, report, sample-report, screenshot, or timing artifact is generated, staged, or committed.
