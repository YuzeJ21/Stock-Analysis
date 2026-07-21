# Prospective Per-Ticker Field Proof Design

**Date:** 2026-07-21

**Status:** Approved Stage A direction; implementation pending

## Purpose

Add a prospective, append-only proof contract that can preserve what was reviewed for one exact ticker and field without retroactively upgrading narrative batch history. The contract records evidence identity and reviewer disposition; it never claims that a referenced payload is true, licensed, commercially usable, or readiness-eligible merely because a row exists.

This Stage A slice is deliberately isolated from current readiness. It creates a testable evidence primitive before any future mapping into Company Workbench, reconciliation, canonical data, or a readiness lane.

## Current Evidence And Boundary

The existing reviewed-data and reviewed-batch ledgers preserve batch scope, outcomes, and narrative notes. They do not preserve a structured per-ticker/per-field payload digest, an exact source-rights decision reference, or a linear revision chain for that field proof. Current proof-readiness reconciliation therefore truthfully reports `structured_payload_not_recorded` for legacy history.

The new ledger is prospective only. Existing rows are not migrated, inferred, or upgraded. An absent or empty ledger produces an explicit unavailable/empty status and no fabricated content. No sample or synthetic proof row is checked in as product evidence.

## Alternatives Considered

### 1. Extend the narrative batch-proof ledger

This would minimize file count, but it would mix batch outcomes with field-level payload identity and make old narrative rows appear structurally equivalent to new evidence. Rejected because it invites retroactive overclaiming and weakens the current reconciliation boundary.

### 2. Store structured details inside narrative notes or JSON text

This would avoid a schema addition, but free text cannot safely enforce identity, scope, revision lineage, rights references, or deterministic receipts. Rejected because narrative text must not become trusted evidence.

### 3. Add an isolated prospective field-proof ledger

Selected. A separate strict schema can fail closed, preserve append-only revisions, support preview-before-record receipts, and remain disconnected from readiness until a separately designed activation contract exists.

## Architecture

Add `src/prospective_field_proof.py` with immutable record, preview, batch-preview, validation, receipt, append, rendering, and CLI interfaces. The implementation reuses proven repository mechanics rather than sharing mutable state:

- strict CSV headers and append-only ledger validation from `src/earnings_consensus_collector.py`;
- UTC timestamp parsing from `src/earnings_nowcast_contract.py`;
- exact source and supported-field review from `src/commercial_source_rights.py`;
- semantic SHA-256 identities, ledger/input digests, and preview receipts;
- all-or-nothing append after revalidating the approved preview against current ledger and input bytes.

The default ledger path is `data/prospective_field_proofs.csv`. The file is not created by status or preview commands. Recording is an explicit write action requiring an exact preview receipt.

## Record Contract

Schema version: `prospective-field-proof-v1`.

Strict ordered fields:

- `schema_version`
- `proof_id`
- `ticker`
- `field_key`
- `readiness_contract_version`
- `observed_at`
- `retrieved_at`
- `source_id`
- `source_ref`
- `source_status`
- `rights_status`
- `rights_decision_ref`
- `payload_status`
- `payload_sha256`
- `reviewer_id`
- `reviewer_decision`
- `reviewed_at`
- `supersedes_proof_id`

The normalized scope key is `(ticker, field_key, readiness_contract_version)`. Ticker and field keys are normalized before comparison. Every row must have a semantic `proof_id` equal to its deterministic identity digest. A payload digest must be exactly 64 lowercase hexadecimal characters; the payload itself is not stored.

Allowed controlled values are independent:

- `source_status`: `identified`, `unavailable`, `disputed`;
- `rights_status`: `approved`, `unverified`, `restricted`, `not_applicable`;
- `payload_status`: `reviewed`, `unavailable`, `rejected`;
- `reviewer_decision`: `accepted`, `rejected`, `needs_follow_up`.

An accepted record requires identified source, reviewed payload, a non-placeholder source reference, a payload digest, and a non-placeholder reviewer. It does not by itself require `rights_status=approved`, because technical evidence review and commercial-rights review remain independent. Commercial eligibility is reported separately and fails closed unless the exact registered source and field scope are approved and the record carries an explicit rights-decision reference.

Timestamps must be timezone-aware UTC. `observed_at <= retrieved_at <= reviewed_at`, and every timestamp must be at or before the explicit review cutoff. Future-dated or malformed rows fail closed.

## Revision And Integrity Contract

Each scope has exactly one root and at most one child per revision. A revision must:

- name an existing parent in the same normalized scope;
- be appended after its parent;
- have a strictly later `reviewed_at` timestamp;
- preserve a linear chain with no forks or cycles;
- supersede the current leaf, not an older revision;
- have a distinct semantic identity and `proof_id`.

Proof IDs and semantic identities must be globally unique. A source reference or payload digest is evidence identity only; neither proves factual correctness, source rights, provenance completeness, readiness, or commercial usability.

## Preview-Before-Record Contract

`preview_field_proof_batch` validates the existing ledger, proposed rows, cutoff, revision chains, and source-rights field scope without writing. It returns immutable row previews plus:

- normalized cutoff;
- current ledger digest;
- proposed input digest;
- source-rights registry digest;
- technical and commercial blockers;
- technical write eligibility;
- commercial evidence eligibility;
- deterministic preview receipt.

`append_reviewed_field_proof_batch` repeats all validation and requires the exact receipt. Any change to ledger contents, proposed input, cutoff, commercial mode, or source-rights registry invalidates the receipt. The append is all-or-nothing and uses one header only. It does not update readiness, canonical data, proof reconciliation, dashboards, reports, or other ledgers.

Technical recording remains available in research mode when the technical contract passes. Explicit commercial mode additionally requires exact source registration, approved commercial rights, supported `field_key`, and a non-placeholder `rights_decision_ref`. An unavailable provider, rights review, or hosted account blocks only its dependent commercial lane.

## Interfaces

### Python

- `ProspectiveFieldProofRecord`
- `FieldProofPreview`
- `BatchFieldProofPreview`
- `field_proof_identity(record)`
- `load_field_proofs(path)`
- `load_proposed_field_proofs(path)`
- `validate_field_proof_ledger(records)`
- `preview_field_proof_batch(...)`
- `append_reviewed_field_proof_batch(...)`

### CLI And Make

- `make prospective-field-proof-status`: read-only summary of absent, empty, valid, or invalid ledger state.
- `make prospective-field-proof-preview INPUT=... AS_OF=...`: read-only batch validation and receipt generation.
- `make prospective-field-proof-record INPUT=... AS_OF=... PREVIEW_RECEIPT=...`: explicit append after receipt revalidation.

All commands state their read/write boundary. Status and preview must not create the ledger, rewrite input, refresh data, produce generated reports, or touch network services.

## Error Handling

- Missing ledger: valid empty state for status/preview.
- Empty existing ledger file: invalid because a present ledger must contain the exact header.
- Wrong, reordered, duplicated, or extra headers: fail closed.
- Blank required fields, placeholders, invalid enum values, malformed digests, or non-UTC timestamps: fail closed with row number.
- Duplicate identity or proof ID, missing/cross-scope parent, root fork, child fork, cycle, non-leaf revision, or non-monotonic review time: fail closed.
- Unknown source or unsupported field: technical evidence may remain separately reviewable in research mode, but commercial eligibility is false.
- Stale receipt or partially invalid batch: append nothing.

## Testing Strategy

Tests must be written and observed failing before implementation. Focused coverage will prove:

1. strict schema, normalization, enum, digest, placeholder, and UTC validation;
2. missing-ledger status is empty and read-only;
3. deterministic identity and unique ID enforcement;
4. exactly one linear revision chain per scope;
5. cross-scope, missing-parent, fork, cycle, stale-leaf, and time-order rejection;
6. independent technical and commercial eligibility;
7. exact source-rights and supported-field review;
8. deterministic preview receipts over ledger, input, cutoff, mode, and registry;
9. stale receipt rejection after any relevant change;
10. all-or-nothing append with one exact header;
11. CLI/Make wording and filesystem read-only behavior for status/preview;
12. no readiness, canonical, dashboard, or legacy-proof mutation.

After focused tests, the complete repository test suite and all dashboard, render, public, commercial, pilot, PR-range, and hygiene gates must run before delivery.

## Documentation And Delivery

After verified implementation:

- update `ROADMAP.md`, `docs/OPERATOR_GUIDE.md`, the continuation goal prompt, and release-document tests;
- state explicitly that legacy proof remains non-upgraded and the new ledger does not activate readiness;
- keep all existing generated CSV/report churn unstaged;
- stage exact code/test/docs/Make files only;
- commit coherently, push only `codex/personal-research-mode-mvp`, and keep PR #113 draft;
- update PR #113 with exact verification evidence and await exact-head CI.

## Deferred Work

Separate designs are required before:

- mapping structured field proof into reconciliation;
- activating Company Workbench or any readiness lane from proof;
- storing or ingesting an actual source payload;
- collecting real point-in-time consensus;
- claiming commercial source rights, hosted operation, reviewer validation, calibration, or market validation.
