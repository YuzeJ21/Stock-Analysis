# Prospective Consensus Batch Preflight Design

## Purpose

The prospective consensus collector validates and appends one reviewed snapshot at a time. The CLI currently previews every proposed row only against the saved ledger, then records rows sequentially. A later duplicate, missing supersession target, same-period conflict, invalid row, or commercial-evidence failure can therefore appear only after earlier rows have already been appended. Preview and record also disagree about intra-batch lineage because preview does not simulate earlier proposed rows.

Add one deterministic whole-batch preflight contract. Preview and record must evaluate the same ordered virtual ledger before any filesystem mutation. This slice uses temporary test ledgers only and does not collect provider data, write repository CSV/JSON files, or rebuild readiness.

## Approaches Considered

### Selected: ordered virtual-ledger preflight plus one append handle

Evaluate proposed rows in input order. Every technically reviewable row is added to an in-memory virtual ledger before the next row is previewed. This detects duplicates, same-period conflicts, and explicit revision chains inside the input. Record writes the full reviewed batch through one append handle only after all applicable gates pass.

This is deterministic validation atomicity: a known row-level rejection cannot leave an earlier row recorded. It is not a claim of crash-safe filesystem transactionality or protection from a separate concurrent writer.

### Rejected: independent row preflight

Checking every proposed row against only the saved ledger would avoid some partial writes, but two proposed rows could still conflict or form an invalid lineage chain without preview detecting it. It would preserve the current preview/record mismatch.

### Rejected: temporary full-ledger replacement

Writing a new full file and replacing the ledger could improve crash behavior, but it changes the append-only operating model, rewrites existing bytes, and introduces permission and concurrency complexity beyond this local reliability gap.

## Batch Preview Contract

Add an immutable `BatchCollectionPreview` with:

- `mode="preview_only"`;
- `write_performed=false`;
- `state`, either `reviewable_batch`, `rejected_batch`, or `empty_batch`;
- `row_count` and `reviewable_count`;
- `technical_write_allowed`;
- `commercial_evidence_ready`;
- `commercial_write_allowed`;
- ordered `technical_blockers` and `commercial_blockers` with one-based row positions;
- ordered row-level `CollectionPreview` results.

Technical and commercial evidence remain independent. `technical_write_allowed` requires a non-empty batch and every row-level `write_allowed`. `commercial_evidence_ready` requires a non-empty batch and every row-level commercial evidence state. `commercial_write_allowed` requires both.

The batch preview always reports both decisions. It does not decide which operating mode the caller selected and never writes.

## Ordered Virtual Ledger

Rows are evaluated in input order because an append-only revision must reference evidence already present in the saved ledger or earlier in the same reviewed input.

For each proposed row:

1. call the existing row preview against the current virtual ledger;
2. retain the complete row-level technical, rights, Revenue-scope, and EPS-scope evidence;
3. add the row to the virtual ledger only when its technical `write_allowed` is true;
4. continue through all rows so reviewers receive the complete deterministic batch result.

A commercial-evidence failure does not erase an otherwise valid technical lineage from the virtual review. This preserves readiness independence: a later explicit revision can be technically valid even when the whole commercial batch remains blocked by an earlier rights failure.

Input order is authoritative. The collector does not sort by timestamp, repair a reversed revision chain, infer a supersession target, or select one conflicting row.

## Record Contract

Add `append_reviewed_batch(...)` with explicit review confirmation plus optional commercial-mode and rights-registry injection.

The function:

1. refuses missing confirmation;
2. loads the saved ledger and resolves the mode/rights registry once;
3. runs the same whole-batch preview used by the CLI;
4. rejects an empty or technically invalid batch before directory creation or ledger mutation;
5. in explicit Commercial Research mode, rejects any incomplete commercial evidence before mutation;
6. opens the destination once and appends the entire reviewed batch in input order, writing the header only for a new ledger.

The existing single-row `append_reviewed_snapshot(...)` delegates to the batch function so it retains confirmation, duplicate, commercial-rights, and append-only behavior without a second decision path.

The CLI `record` command loads its input once and calls the batch function once. It cannot loop through row-level writes.

## Error And Evidence Behavior

- Empty input: `empty_batch`; no directory or file creation.
- Any technical row rejection: `rejected_batch`; no rows written in research or commercial mode.
- Commercial evidence incomplete: research-mode technical batch can remain reviewable; explicit commercial record is blocked before mutation.
- Intra-batch exact duplicate: the later row is `duplicate`.
- Same ticker/period without explicit supersession: the later row is rejected.
- Valid ordered revision: the revision row is `reviewable_revision` because its target is already in the virtual ledger.
- Reversed revision: rejected because the target is not yet present; the collector does not reorder evidence.

Errors include stable one-based row positions and row-level state/blocker text so the reviewer can correct the supplied file without inspecting a partially changed ledger.

## Testing

Test-first temporary-fixture coverage will prove:

1. preview detects an intra-batch duplicate and keeps the saved ledger unchanged;
2. preview accepts an ordered new-snapshot plus explicit revision chain;
3. preview rejects a reversed revision chain without reordering it;
4. research-mode record leaves an existing ledger byte-identical when a later row is invalid;
5. commercial-mode record leaves a missing destination directory absent when a later row lacks rights or metric scope;
6. a fully valid research batch appends every row in order through one batch call;
7. a fully rights-approved commercial batch appends every row in order;
8. an empty batch is blocked without filesystem mutation;
9. single-row append compatibility remains covered;
10. no repository data, generated artifact, source-rights record, or readiness file changes.

## Completion Criteria

- Preview and record use one ordered whole-batch decision contract.
- A deterministic later rejection cannot leave an earlier proposed row appended.
- Intra-batch duplicates and revision lineage are visible before record.
- Technical eligibility, commercial rights, Revenue scope, and EPS scope remain independent.
- Research-only behavior stays explicit and reviewed; commercial mode remains fail-closed.
- The implementation does not claim concurrent-writer locking, crash-safe transactions, provider availability, payload correctness, nowcast readiness, calibration, hosting, reviewer validation, or market validation.
