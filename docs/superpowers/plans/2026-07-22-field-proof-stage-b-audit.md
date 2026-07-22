# Stage B Prospective Field-Proof Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic read-only field-proof history audit and clearer per-row preview explanations without adding any write, readiness, or Workbench mapping.

**Architecture:** Extend the pure `prospective_field_proof` module with immutable audit rows and an aggregate audit contract derived from the already validated append-only ledger. Expose stdout-only text/JSON through one Make target. Reuse the current source-rights registry only to explain active-head commercial blockers.

**Tech Stack:** Python 3.12, frozen dataclasses, argparse, Make, pytest.

---

### Task 1: Define the read-only audit contract test-first

**Files:** `src/prospective_field_proof.py`, `tests/test_prospective_field_proof.py`

- [ ] Add failing tests for absent, two-revision, rejected/follow-up, invalid, deterministic ordering, and no-write audits.
- [ ] Implement frozen audit row/summary contracts, active-head resolution, revision numbers, blocker aggregation, and text rendering.
- [ ] Add the `audit` CLI with controlled invalid-ledger errors and stable JSON.
- [ ] Run `python3 -m pytest tests/test_prospective_field_proof.py -q`.

### Task 2: Improve preview explanation and expose the Make target

**Files:** `src/prospective_field_proof.py`, `Makefile`, `tests/test_makefile_test_targets.py`

- [ ] Add failing tests for per-row preview answers, receipt-binding copy, and a read-only Make audit target.
- [ ] Render row state/reason/blockers and receipt persistence boundary.
- [ ] Add `prospective-field-proof-audit` without any output-file parameter or write command.
- [ ] Run focused module and Make-target tests.

### Task 3: Reconcile documentation and maturity status

**Files:** `README.md`, `ROADMAP.md`, `docs/OPERATOR_GUIDE.md`, `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`, `tests/test_public_v1_release_docs.py`

- [ ] Document the audit answer, receipt boundary, and no-mapping rule.
- [ ] Mark Stage B complete locally only after all direct tests pass and set Priority 3 authoring design as next.

### Task 4: Verify and release the slice

- [ ] Run focused tests, `python3 -m pytest tests -q`, dashboard/render/public/commercial-beta/pilot/hygiene gates, and `git diff --check`.
- [ ] Confirm audit and preview did not change any tracked or untracked scoped artifact.
- [ ] Stage exact code/test/docs/Makefile paths only; run staged hygiene.
- [ ] Commit, push only the feature branch, update draft PR #113, and require exact-head CI before Priority 3.
