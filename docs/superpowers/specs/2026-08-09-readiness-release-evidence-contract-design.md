# Readiness Release Evidence Contract

**Date:** 2026-08-09
**Status:** Option A approved by the owner; written-spec review pending
**Scope:** Default-profile readiness release evidence only

## Problem

The default profile currently has two truths that must remain separate:

1. the saved working readiness snapshot is technically current for the saved local source files; and
2. the 18 generated readiness/report/output paths differ from Git `HEAD`, so they are not tracked release evidence.

The current no-write preview correctly reports zero stable readiness changes against the saved working snapshot. That does not answer whether the working snapshot is an intentionally reviewed release package. The existing 18-file audit found a technically coherent materialization, but no exact materialization-level receipt binding the candidate artifacts, source inputs, source-rights registry, technical transitions, provenance review, distribution review, and reviewer decision.

The missing contract must be closed without changing technical readiness, granting source rights, inferring composite providers, fabricating review, or treating research-only data as commercially approved.

## Decision

Add an evidence-bound readiness release workflow with three explicit phases:

1. **Review:** build a deterministic, read-only assessment of the exact working candidate against tracked `HEAD` and current in-memory readiness.
2. **Record:** append a reviewed decision only after the exact preview receipt is supplied and every candidate input is revalidated.
3. **Guard:** verify that a recorded decision still matches the working candidate and print an exact staging handoff. The workflow never stages files itself.

Technical readiness and release eligibility remain independent. A technically correct row may remain commercially withheld. A release record may describe a blocked candidate, but only an exact eligible record can pass the staging guard.

## Non-goals

- Do not alter readiness calculations, thresholds, exclusions, or current ready/partial/blocked states.
- Do not filter or demote technical readiness because commercial rights are missing.
- Do not add provider keys, fetch data, apply imports, rebuild canonical data, or refresh markets.
- Do not approve SEC derived-field scope, yfinance commercial use, StockAnalysis redistribution, composite sources, or any other rights decision.
- Do not merge, mark PR #113 ready, deploy, publish, or contact reviewers.
- Do not count automated or Codex review as independent-human, legal, commercial, or distribution approval.
- Do not create a general artifact release framework; this contract covers the named default-profile readiness family only.

## Candidate package

The candidate package is the exact set of modified default-profile readiness paths classified by repository policy. For the current worktree this is the protected 18-file set. The reviewer must not discover the package through a broad `git add` or unrestricted filesystem walk.

The implementation will use one canonical ordered path manifest shared by review, record, guard, tests, and documentation. Every path is classified as one of:

- canonical readiness input;
- primary readiness output;
- compatibility copy;
- derived summary;
- derived worklist; or
- source-status metadata.

Unexpected added, missing, renamed, staged, or modified product/manual-review paths block the candidate.

## Phase 1 — read-only review

Add:

```text
make readiness-release-review TOP_N=20
make readiness-release-review TOP_N=20 JSON=1
```

The command performs no writes and does not create caches, bytecode, snapshots, receipts, reports, or directories.

It binds:

- current Git `HEAD` and branch;
- tracked `HEAD` blobs for every candidate path;
- current working bytes and SHA-256 for every candidate path;
- staged-diff state;
- current canonical source-file identity and SHA-256;
- current source-rights registry SHA-256;
- current reviewed-proof-ledger SHA-256;
- current in-memory proposed stable readiness state;
- exact technical transitions from tracked `HEAD` to the working candidate;
- exact source/provenance/field-scope review for every fundamentals or DCF promotion;
- exact DCF price-lineage review for every DCF promotion;
- compatibility-copy and mirror consistency;
- unexpected path or schema drift; and
- a canonical preview receipt covering every normalized decision input.

The review must compare the working candidate with both tracked `HEAD` and a fresh in-memory readiness composition. Comparing only working saved output with the same current sources is insufficient.

### Independent review axes

The output reports these axes independently:

- `candidate_integrity`
- `technical_transition_review`
- `provenance_review`
- `commercial_rights_review`
- `registered_field_scope_review`
- `price_lineage_review`
- `historical_proof_binding_review`
- `distribution_review`
- `staging_hygiene_review`

No aggregate status may hide a failed axis. The overall state is one of:

- `invalid`
- `blocked`
- `technical_snapshot_reviewable_commercial_claims_withheld`
- `release_reviewable`

The current repository is expected to remain `blocked` or `technical_snapshot_reviewable_commercial_claims_withheld` until direct evidence resolves the yfinance/composite-source, SEC field-scope, StockAnalysis fallback, provenance, proof-binding, and distribution questions. Tests must not hard-code a green current-repository verdict.

### Source identity

Exact source IDs are authoritative. Composite strings are not split and do not borrow rights from a component. Missing or ambiguous fundamentals rows fail closed. `source`, `as_of_date`, and a durable source reference remain distinct required provenance fields.

Commercial permission and registered field support remain independent. SEC commercial approval does not automatically register `free_cash_flow` or `fcf_margin`; yfinance field support does not create commercial permission.

### Historical proof binding

Historical proof rows may explain a ticker transition, but ticker mention alone is not a release binding. A proof match requires the exact lane, ticker, source identity, changed-input identity, review cutoff, and before/after snapshot identity when those fields are applicable. Missing historical linkage remains visible and does not rewrite the proof ledger.

## Phase 2 — exact reviewed record

Add:

```text
make readiness-release-record \
  PREVIEW_RECEIPT=<exact_receipt> \
  REVIEWER=<named_reviewer> \
  REVIEW_DATE=<yyyy-mm-dd> \
  TECHNICAL_DECISION=<approved|rejected> \
  DISTRIBUTION_DECISION=<approved|rejected|external_review_required> \
  CONFIRM_REVIEWED=1
```

The record command re-runs the complete review under one process-level lock. Any changed byte, Git head, registry, proof ledger, staged state, path set, or normalized decision invalidates the receipt.

Records are append-only in `data/readiness_release_reviews.csv`. A record contains:

- immutable record ID;
- preview receipt;
- Git head;
- candidate-manifest digest;
- canonical-source digest;
- rights-registry digest;
- proof-ledger digest;
- technical transition summary;
- every independent review-axis status;
- technical and distribution decisions;
- reviewer and review date;
- exact blocker codes;
- research-only boundary; and
- timestamp.

`CONFIRM_REVIEWED=1` confirms only that the named reviewer reviewed the exact receipt. It does not certify that the reviewer is independent, legal counsel, a source owner, or an accessibility/product reviewer. Empty, placeholder, control-character, malformed, or inconsistent review fields fail nonzero and write nothing.

A rejected or external-review-required record is valid evidence of a blocked decision. It cannot pass the staging guard.

## Phase 3 — staging guard

Add:

```text
make readiness-release-guard RECORD_ID=<record_id>
```

The guard is read-only. It re-runs candidate review and verifies the selected append-only record. It passes only when:

- technical decision is approved;
- distribution decision is approved;
- every mandatory review axis satisfies its gate;
- the record receipt and every digest still match;
- the staged diff is empty before handoff;
- no unexpected product, generated, or manual-review path is present; and
- the exact candidate package remains byte-identical to the reviewed package.

On success it prints exact named `git add` arguments for the reviewed record and candidate paths. It never runs Git staging itself and never suggests `git add -A`.

On failure it prints stable blocker codes, the exact changed dependency, and the safe resume command. It does not modify files.

## Data model and component boundaries

Add one focused module, `src/readiness_release_review.py`, with immutable value objects for:

- candidate path evidence;
- source input evidence;
- review-axis decisions;
- transition evidence;
- preview packet;
- recorded decision; and
- guard result.

Reuse existing functionality from:

- `src.readiness_preview` for stable transitions, promotion evidence, and DCF price lineage;
- `src.commercial_source_rights` for exact rights and field-scope decisions;
- `src.readiness_engine` for in-memory proposed readiness;
- `src.profile_context` for profile identity; and
- repository hygiene helpers for path classification.

Do not duplicate source-rights parsing, readiness calculation, or proof interpretation. Small pure helpers may be extracted only when required to avoid two incompatible implementations.

The module owns CLI parsing, deterministic rendering, receipt calculation, append-only record validation, and guard evaluation. The dashboard does not consume the new workflow in this slice; operator commands and documentation are the public boundary.

## Determinism and safety

- Canonical JSON uses sorted keys, stable ordered rows, normalized booleans/text, and UTF-8.
- Timestamps are excluded from preview-receipt inputs unless they are source evidence.
- Git reads are bounded and capture only named paths.
- Regular files, symlink rejection, file-size limits, row limits, duplicate-key rejection, duplicate-ticker detection, and duplicate-record detection fail closed.
- Errors are stable, traceback-free at the CLI boundary, and write-free.
- Record writes use an exclusive lock, exact revalidation, atomic replace, and one-shot post-write verification.
- An uncertain post-write outcome never invites blind retry; it requires read-side reload by record ID.
- No command prints secrets or reads provider credential values.

## Testing

Use focused RED-GREEN TDD for every behavior. Required coverage includes:

1. exact current candidate path manifest and unexpected-path rejection;
2. tracked `HEAD` versus working versus in-memory three-way comparison;
3. compatibility-copy and mirror consistency;
4. exact-source handling and composite-source fail-closed behavior;
5. independent commercial-rights and field-scope outcomes;
6. missing/duplicate fundamentals evidence and provenance fields;
7. DCF price-lineage independence;
8. historical proof exact-match versus ticker-mention-only behavior;
9. deterministic receipt generation;
10. receipt invalidation for any input, registry, proof, head, staged-state, or artifact change;
11. append-only record validation, locking, atomicity, duplicate receipt handling, and uncertain-write reload;
12. guard refusal for rejected or external-review-required distribution decisions;
13. exact named staging handoff with no automatic staging;
14. CLI/Make success and stable nonzero failure behavior;
15. no-write verification for review and guard; and
16. preservation of the existing 18 protected artifact hashes throughout implementation verification.

After focused and related tests pass, run the full repository suite, dashboard and Research route smokes, public wording/check, Commercial Beta release check, pilot readiness, readiness operations/preview/reconciliation, browser evidence, diff/staged hygiene, whitespace checks, protected hashes, branch synchronization, draft-PR update, and exact-head GitHub CI.

The expected pilot result may remain blocked. A green engineering matrix proves the contract implementation only; it does not approve the current data package or any external gate.

## Documentation

Update:

- `ROADMAP.md`
- `docs/NEXT_STAGE_ROADMAP.md`
- `docs/DATA_STRATEGY.md`
- `docs/OPERATOR_GUIDE.md`
- the Make help text; and
- focused design/acceptance evidence.

Documentation must state that this workflow can record a blocked decision, does not grant rights, does not change readiness, and cannot substitute for independent review or external data.

## Acceptance

The implementation is complete when:

- all three commands exist with the contracts above;
- review and guard are demonstrably write-free;
- record is exact-receipt-bound and append-only;
- technical readiness is unchanged;
- current unsupported claims remain withheld;
- the current 18 files remain unstaged and byte-identical during engineering verification;
- focused, related, full, release, browser, readiness, hygiene, and exact-head CI gates pass; and
- PR #113 remains open and draft.

Completion of this local contract does not complete source rights, current-market coverage, hosted operation, manual accessibility, independent workflow validation, calibration, or paper-position approval.
