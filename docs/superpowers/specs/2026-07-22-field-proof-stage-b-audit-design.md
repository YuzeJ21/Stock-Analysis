# Stage B Prospective Field-Proof Audit Design

**Date:** 2026-07-22
**Status:** Approved by the Next-Stage Maturity Program
**Scope:** Read-only operator audit and explanation only

## Problem

Stage A validates an append-only per-field proof ledger, previews proposed rows, binds a receipt, and permits an explicitly confirmed append. Its safety contract is strong, but its operator answer is too compressed:

- status reports only absent/valid/invalid and a record count;
- preview text reports batch counts and blocker lists but hides per-row state and reason unless JSON is requested;
- no read-only command explains the current revision heads, superseded history, reviewer dispositions, or current commercial blocker categories;
- preview receipts are deliberately not persisted, but the operator output does not explain that a receipt must be retained externally and revalidated at record time.

## Selected Approach

Add one read-only `audit` command and enrich preview text. Do not add a dashboard route, persistence, receipt store, readiness mapping, generated report, or automatic record operation.

Other approaches were rejected:

- Persisting preview receipts would create a new write path and stale-receipt lifecycle.
- Mapping accepted proof into readiness or Company Workbench would exceed the approved Stage B boundary.
- A dashboard authoring flow belongs to Priority 3 and must not be smuggled into this operator slice.

## Audit Contract

`make prospective-field-proof-audit` returns:

- ledger integrity and absent/valid/invalid state;
- total records, normalized scopes, active revision heads, and superseded records;
- accepted, rejected, and needs-follow-up counts;
- latest reviewed timestamp;
- one append-order history row per record with scope, revision number, current/superseded state, reviewer disposition, source/payload/rights state, proof ID, and parent ID;
- current blocker categories derived only from active heads and the current source-rights registry;
- `preview_receipt_persisted=false` and `receipt_revalidation_required=true`.

An absent ledger is a valid empty audit. A present empty, malformed, forked, cyclic, or otherwise invalid ledger fails closed with a controlled explanation and nonzero exit.

## Preview Explanation

Human-readable preview output adds one line per proposed row with state, technical eligibility, commercial eligibility, reason, and blocker categories. It also states which inputs the receipt binds and that the receipt is not saved by the tool.

## Boundaries

- Audit and preview write no ledger, input, readiness, canonical data, legacy proof, report, JSON file, screenshot, timing artifact, or dashboard state.
- Audit status cannot prove payload truth, reviewer independence, source rights, commercial permission, freshness, or readiness.
- A current active accepted record remains evidence history only. It cannot feed proof-readiness reconciliation, Company Workbench, Research Decision Lab, forecasts, calibration, recommendations, sizing, ranking, or transaction behavior.
- JSON is stdout only. No artifact is created.
- Recording remains available only through the existing explicit preview-receipt and confirmation command.

## Acceptance Evidence

Tests must prove absent, valid multi-revision, blocked active-head, and invalid-ledger audits; stable append order; normalized scope counts; current-head blocker aggregation; per-row preview explanations; controlled CLI errors; and byte-for-byte no-write behavior across scoped sentinels. Full release and hygiene checks must show zero generated files staged.
