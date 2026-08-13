# Staged Price Rights And Scope Review Design

## Purpose

The prospective price-lineage path now preserves explicit `source`, `source_ref`, and `retrieved_at` evidence, but its validation and preview summaries stop at lineage completeness. A reviewer still has to inspect the source-rights registry separately to learn whether each exact source is commercially approved and explicitly supports `prices`. That separation is methodologically correct, but the missing joined review makes it too easy to mistake complete provenance for permitted commercial evidence.

Add a read-only, fail-closed rights and field-scope review to the existing staged price validation and preview results. This slice evaluates checked-in registry truth only. It does not edit rights, fetch a payload, apply rows, rebuild readiness, or make technical local-research validity depend on commercial evidence.

## Approaches Considered

1. **Attach independent rights/scope summaries to validation and preview (selected).** Reuse the exact source-rights contract, evaluate each technically valid staged row, and expose aggregate and row-level decisions without changing technical validity.
2. **Block all staged rows lacking approved rights.** This would protect commercial use but would incorrectly reject legitimate local research imports and couple two readiness states.
3. **Evaluate rights only during apply.** This would fail too late and keep preview unable to answer whether a staged batch is commercially reviewable.

## Evaluation Contract

For every technically valid staged row:

- use the exact trimmed `source` string as the registry key;
- never split composite values, infer aliases, map file names, or guess a provider;
- use `commercial_eligibility(...)` for the rights decision;
- require the exact registry record to include `prices` in `supported_fields` for field-scope completeness;
- keep missing source identity as `unknown_source` with incomplete field scope.

The checked-in registry is authoritative for this local review. Tests may inject an immutable registry so approved, unverified, unknown, mixed, and empty-source behavior is deterministic without changing `config/source_rights.yml`.

## Independent Summary States

Validation and preview add:

- `commercial_rights_status`: `no_valid_rows`, `rights_approved`, `rights_review_required`, or `mixed_rights`;
- `rights_approved_rows` and `rights_review_required_rows`;
- `rights_status_counts`, keyed by the exact eligibility status;
- `price_scope_status`: `no_valid_rows`, `price_scope_complete`, `price_scope_review_required`, or `mixed_price_scope`;
- `price_scope_complete_rows` and `price_scope_review_required_rows`;
- `source_review_rows`, a deterministic capped-independent list containing exact source ID, rights status, price-scope completeness, and blockers for each distinct exact source.

Technical `status`, valid/skipped counts, lineage status, and merge counts remain unchanged. Rights or scope review requirements may add warnings, but they do not invalidate an otherwise valid local-research row.

## Failure Behavior

- Unknown and blank sources fail closed as `unknown_source` and lack registered `prices` scope.
- A registered source with unverified commercial rights remains review-required even if it supports `prices`.
- A commercially approved source remains scope-review-required when its record does not list `prices`.
- Mixed batches report mixed states instead of collapsing to approved or blocked.
- Invalid or missing registry input raises the existing registry error; the workflow does not synthesize a permissive fallback.
- Complete lineage does not change rights or scope decisions.

## Testing

Test-first coverage will prove:

1. an injected approved source with `prices` produces complete independent rights and scope states;
2. `yfinance` remains commercial-rights-review-required while retaining registered price scope;
3. unknown and blank exact sources fail closed without alias inference;
4. a mixed batch reports mixed rights/scope counts deterministically;
5. validation and preview inherit the same review without changing technical or merge results;
6. invalid technical rows are excluded from commercial-evidence counts;
7. no repository data or generated artifact is written.

## Completion Criteria

- One staged batch can answer technical validity, lineage completeness, exact-source rights, and registered price scope independently in one read-only result.
- Existing local research import behavior remains compatible.
- No source is approved, aliased, inferred, fetched, applied, or promoted.
- ROADMAP, methodology, provenance, data strategy, continuation prompt, and draft PR #113 record the capability and its boundaries.
- No CSV, JSON, report, sample-report, screenshot, or timing artifact is generated, staged, or committed.
