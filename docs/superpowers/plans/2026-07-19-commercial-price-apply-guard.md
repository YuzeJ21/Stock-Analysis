# Commercial Price Apply Guard Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fail closed before staged-price mutation in explicit commercial mode unless lineage, exact-source commercial rights, and registered `prices` scope are complete for every valid row.

**Architecture:** Extend `apply_price_import_merge(...)` with optional explicit mode and registry injection. Reuse the existing preview summary as the guard input, return a deterministic non-writing blocked result before validation replay, backup, or canonical merge, and preserve the existing research-mode path.

**Constraints:** Use temporary pytest paths only; do not run repository `price-apply`, normalize, refresh, or readiness commands; do not edit source rights; do not infer providers; do not make guard passage automatic apply authorization or readiness evidence.

## Task 1: Add failing guard tests

**Files:**

- Modify `tests/test_data_update.py`

- [ ] Assert explicit research mode retains existing unregistered-source apply behavior.
- [ ] Assert explicit commercial mode blocks the same fixture with rights and price-scope blockers and leaves canonical bytes unchanged with no backup.
- [ ] Add approved-price fixtures proving missing lineage and missing registered price scope block independently.
- [ ] Add a complete approved-price fixture proving the existing merge path can run after the guard passes.
- [ ] Run focused tests and confirm the new signature/guard assertions fail before implementation.

## Task 2: Implement the pre-mutation commercial guard

**Files:**

- Modify `src/data_update.py`

- [ ] Import and reuse `commercial_mode_enabled`.
- [ ] Add optional `commercial_mode` and `rights_registry` parameters to apply.
- [ ] Pass the same registry into preview and later validation.
- [ ] Build the ordered blocker list from lineage, rights, and price-scope summaries.
- [ ] Return before backup/write when explicit commercial mode has blockers.
- [ ] Preserve existing missing/invalid and research-mode behavior.
- [ ] Run focused tests and require them to pass.

## Task 3: Durable contracts

**Files:**

- Modify `ROADMAP.md`
- Modify `docs/DATA_STRATEGY.md`
- Modify `docs/METHODOLOGY.md`
- Modify `docs/PROVENANCE_CONTRACT.md`
- Modify `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`

- [ ] Record the explicit commercial-mode mutation guard and local-research compatibility.
- [ ] Preserve the unchanged canonical 146-row audit and external source requirement.
- [ ] Record that tests use temporary fixtures and no repository apply or readiness write occurred.

## Task 4: Full verification and delivery

- [ ] Run focused changed-module/docs tests and public wording.
- [ ] Run the full test suite, dashboard smoke, six research-route render smoke, public check, commercial beta/release checks, pilot readiness, hygiene, and whitespace checks.
- [ ] Verify zero generated churn and no repository apply/readiness write.
- [ ] Stage exact files only and pass staged hygiene.
- [ ] Commit and push only the feature branch.
- [ ] Update draft PR #113 and verify it remains open and draft.
- [ ] Reassess remaining executable gates without claiming source, hosted, reviewer, calibration, or market completion.
