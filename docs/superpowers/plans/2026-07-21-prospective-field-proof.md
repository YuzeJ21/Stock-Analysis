# Prospective Per-Ticker Field Proof Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a prospective, append-only, per-ticker/per-field proof ledger with fail-closed validation, linear revisions, source-rights review, preview receipts, and explicit record commands without activating readiness or upgrading legacy proof.

**Architecture:** Introduce one isolated module and ledger contract modeled on the repository's prospective consensus collector. The module carries independent technical and commercial evidence decisions, validates proposed rows against a virtual ledger, and permits all-or-nothing append only after exact preview-receipt revalidation. Existing readiness, canonical data, dashboard, and proof-reconciliation paths remain untouched.

**Tech Stack:** Python 3.12, immutable dataclasses, CSV, SHA-256, argparse, pytest, Make, GitHub Actions.

## Global Constraints

- The new ledger is prospective only; never infer, migrate, or upgrade legacy narrative proof.
- A proof row, source reference, rights reference, or payload digest does not prove truth, licensing, commercial usability, readiness, or market validation.
- Keep technical write eligibility and commercial evidence eligibility independent.
- Do not integrate this contract with current readiness, canonical data, Company Workbench, proof reconciliation, or dashboards in this slice.
- Status and preview are filesystem read-only and network-free.
- Do not create `data/prospective_field_proofs.csv`, sample proof rows, CSV/JSON reports, screenshots, timing evidence, or bytecode artifacts during implementation verification.
- Preserve the existing 18 generated-file modifications as unstaged and uncommitted.
- Stage exact files only; never use `git add -A`.
- Push only `codex/personal-research-mode-mvp`; keep PR #113 open and draft; do not merge or deploy.
- Preserve all research-only, no-investment-advice, no-trading, explicit-Q4, EPS split-basis, synthetic-fixture, candidate-context, consensus, and calibration boundaries.

---

## File Structure

- Create `src/prospective_field_proof.py`: schema, records, validation, identity, revision integrity, preview/receipt, append, render, and CLI.
- Create `tests/test_prospective_field_proof.py`: unit and CLI contract coverage.
- Modify `Makefile`: status, preview, and record targets.
- Modify `tests/test_makefile_test_targets.py`: durable Make target contract.
- Modify `ROADMAP.md`: completed Stage A evidence primitive and explicit non-activation boundary.
- Modify `docs/OPERATOR_GUIDE.md`: preview-before-record operating contract.
- Modify `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`: next executable stage and external classifications.
- Modify `tests/test_public_v1_release_docs.py`: durable documentation contract.

---

### Task 1: Strict Record Schema And Ledger Integrity

**Files:**
- Create: `tests/test_prospective_field_proof.py`
- Create: `src/prospective_field_proof.py`

**Interfaces:**
- `SCHEMA_VERSION = "prospective-field-proof-v1"`
- `FIELDS` in the exact order specified by the design
- immutable `ProspectiveFieldProofRecord`
- `field_proof_identity`, `load_field_proofs`, `load_proposed_field_proofs`, `validate_field_proof_ledger`

- [ ] **Step 1: Write schema and normalization tests**

Create fixture helpers for a valid accepted record and exact CSV writer. Test exact header enforcement, missing/extra/reordered fields, ticker/field normalization, required non-placeholder values, controlled enums, lowercase SHA-256 payload digest, semantic proof ID, UTC timestamps, cutoff-independent timestamp ordering, and row-numbered errors.

- [ ] **Step 2: Run schema tests and confirm RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_prospective_field_proof.py -q
```

Expected: import failure because `src.prospective_field_proof` does not exist.

- [ ] **Step 3: Implement the minimum immutable schema and loaders**

Use `csv.DictReader`, strict header equality, `parse_utc_timestamp`, canonical normalization, semantic JSON serialization, and SHA-256. A missing ledger loads as an empty tuple; a present empty or malformed ledger fails closed.

- [ ] **Step 4: Write revision-integrity tests**

Cover one root per normalized scope, one child per parent, global unique IDs and identities, parent-before-child append order, same-scope parent, current-leaf revision, strictly later `reviewed_at`, missing parent, cross-scope parent, fork, cycle/disconnected cycle, stale-leaf revision, duplicate root, and valid independent scopes.

- [ ] **Step 5: Run revision tests and confirm RED**

Expected: failures for the unimplemented chain validation.

- [ ] **Step 6: Implement linear revision integrity and rerun focused tests**

Keep validation deterministic and report the ledger/input row number and precise invariant.

- [ ] **Step 7: Verify, stage exact files, and commit**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_prospective_field_proof.py -q
git diff --check
git add -- src/prospective_field_proof.py tests/test_prospective_field_proof.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Add prospective field proof ledger integrity"
```

---

### Task 2: Preview Receipt, Rights Review, And Atomic Append

**Files:**
- Modify: `tests/test_prospective_field_proof.py`
- Modify: `src/prospective_field_proof.py`

**Interfaces:**
- immutable `FieldProofPreview` and `BatchFieldProofPreview`
- `preview_field_proof_batch`
- `append_reviewed_field_proof_batch`

- [ ] **Step 1: Write independent eligibility tests**

Test accepted/rejected/follow-up records; source identified/unavailable/disputed; payload reviewed/unavailable/rejected; unknown source; unapproved commercial rights; unsupported field; missing rights-decision reference; approved exact source/field; and research-mode technical eligibility independent from commercial eligibility.

- [ ] **Step 2: Run the new tests and confirm RED**

Expected: missing preview interfaces or eligibility fields.

- [ ] **Step 3: Implement row and virtual-batch previews**

Reuse `review_commercial_field_scope`. Validate every proposed row against a virtual ledger so a same-batch revision can follow its parent. Return explicit technical and commercial blockers; never collapse one into the other.

- [ ] **Step 4: Write receipt and append tests**

Test deterministic receipt over schema, normalized cutoff, commercial mode, existing-ledger digest, input digest, and source-rights-registry digest. Test invalidation after ledger/input/cutoff/mode/registry changes, missing confirmation, missing receipt, empty batch, mixed-validity all-or-nothing behavior, one header, ordered append, and commercial-mode fail-closed behavior.

- [ ] **Step 5: Run receipt tests and confirm RED**

Expected: append and receipt behavior is missing.

- [ ] **Step 6: Implement receipt revalidation and append**

Re-read and revalidate the destination ledger immediately before append. Require exact receipt and explicit confirmation. Write nothing unless every dependent gate passes. Append rows once; do not rewrite prior bytes.

- [ ] **Step 7: Verify, stage exact files, and commit**

Run the focused file, `git diff --check`, exact add of the two task files, staged hygiene, cached diff check, and commit:

```bash
git commit -m "Add reviewed field proof preview and append"
```

---

### Task 3: Read-Only Status/Preview And Explicit Record Commands

**Files:**
- Modify: `tests/test_prospective_field_proof.py`
- Modify: `src/prospective_field_proof.py`
- Modify: `Makefile`
- Modify: `tests/test_makefile_test_targets.py`

- [ ] **Step 1: Write CLI and Make contract tests**

Prove:

- `status` reports absent/empty-valid/valid/invalid without creating or changing files;
- `preview` emits stable JSON including receipt, both eligibility states, blockers, and `write_performed=false`;
- `record` refuses absent confirmation or receipt and records only a fully revalidated batch;
- CLI errors are specific and nonzero;
- Make targets forward `INPUT`, `LEDGER`, `AS_OF`, and `PREVIEW_RECEIPT` exactly;
- the default ledger is `data/prospective_field_proofs.csv` and no default file is created by status/preview.

- [ ] **Step 2: Run CLI/Make tests and confirm RED**

Run the CLI-focused tests plus `tests/test_makefile_test_targets.py`.

- [ ] **Step 3: Implement renderers, argparse commands, and Make targets**

Add `.PHONY` entries and these targets:

```make
prospective-field-proof-status
prospective-field-proof-preview
prospective-field-proof-record
```

The record target must reject blank `INPUT`, `AS_OF`, or `PREVIEW_RECEIPT` before Python execution. Wording must distinguish read-only preview from explicit append.

- [ ] **Step 4: Prove filesystem non-mutation**

Use test temporary directories and byte snapshots before/after status and preview. Assert no ledger, output, readiness, canonical, or legacy-proof file appears or changes.

- [ ] **Step 5: Verify, stage exact files, and commit**

Run focused tests, `git diff --check`, exact add of the four task files, staged hygiene, cached diff check, and commit:

```bash
git commit -m "Expose prospective field proof workflow"
```

---

### Task 4: Operating Documentation And Release Evidence

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/OPERATOR_GUIDE.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: `tests/test_public_v1_release_docs.py`

- [ ] **Step 1: Write failing documentation-contract tests**

Require the three commands, prospective-only boundary, legacy non-upgrade boundary, independent technical/commercial status, preview receipt, no readiness activation, absent-ledger empty state, and exact next external unblock conditions.

- [ ] **Step 2: Run documentation tests and confirm RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_public_v1_release_docs.py -q
```

- [ ] **Step 3: Update operating documentation truthfully**

Document the implemented contract and examples without creating example ledger rows. Correct these current documentation contradictions while in the same truth-maintenance slice:

- the committed PR readiness snapshot is older than the excluded local generated snapshot;
- `make pilot-readiness-packet` writes a Markdown output and is not read-only;
- reviewer target is consistently 10–20 sessions;
- Stage A–G labels are maturity lanes, not replacements for numbered release stages.

Classify external dependencies once: permitted point-in-time consensus and rights review, hosted account and operated controls, independent reviewers, peer evidence, and calibration cohort.

- [ ] **Step 4: Run focused documentation and proof tests**

Run the new module tests, Make target tests, release-doc tests, and `git diff --check`.

- [ ] **Step 5: Stage exact docs/tests and commit**

Run staged hygiene and cached diff check, then commit:

```bash
git commit -m "Document prospective field proof operations"
```

---

### Task 5: Whole-Slice Verification, Independent Review, And Draft PR Update

**Files:** No intended product edits unless a reviewer finds a concrete defect.

- [ ] **Step 1: Run focused changed-module tests**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_prospective_field_proof.py \
  tests/test_makefile_test_targets.py \
  tests/test_public_v1_release_docs.py -q
```

- [ ] **Step 2: Run the complete local release matrix**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make public-wording-check
make commercial-beta-check
make public-check
make commercial-beta-release-check
make pilot-readiness-check TOP_N=10
make pr-range-hygiene-check
make diff-hygiene-summary
git diff --check
```

Interpret expected fail-closed pilot results as product truth, not test failure. Do not rebuild readiness or stage the existing generated files.

- [ ] **Step 3: Request independent whole-slice review**

Review from the design commit through current HEAD for spec compliance, overclaims, append integrity, receipt completeness, source-rights independence, filesystem writes, regression risk, and generated-artifact hygiene. Fix concrete findings test-first and rerun affected gates.

- [ ] **Step 4: Verify exact staged/unstaged scope**

Ensure no product changes remain unstaged, no generated files are staged, and the only remaining worktree changes are the pre-existing 18 generated files. Run staged hygiene if any correction is staged.

- [ ] **Step 5: Push and update PR #113**

Push only `codex/personal-research-mode-mvp`. Update the draft PR with implemented contract, explicit non-activation boundary, tests/checks, generated-artifact exclusion, current committed-vs-local readiness distinction, external blockers, and next executable slice. Keep the PR draft and wait for exact-head CI.

- [ ] **Step 6: Continue to the next safe maturity lane**

After exact-head CI passes, select the next safe local slice from current evidence. Prefer correcting the verified responsive first-viewport handoff regression or strengthening Company Workbench proof activation preview. Do not connect structured proof to readiness without a separately approved design and tests.
