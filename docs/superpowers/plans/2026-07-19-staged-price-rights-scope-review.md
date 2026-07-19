# Staged Price Rights And Scope Review Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add independent exact-source commercial-rights and registered `prices` scope review to staged price validation and preview without changing technical OHLCV validity or authorizing apply.

**Architecture:** Reuse `SourceRights` and `commercial_eligibility` from the checked-in fail-closed registry. Evaluate only technically valid retained rows after normalization, aggregate exact-source decisions, and attach the result to existing validation/preview summaries. Allow explicit registry injection for deterministic tests; production uses the checked-in registry.

**Constraints:** Do not edit `config/source_rights.yml`; do not infer providers or split composite source strings; do not run repository normalize/apply/readiness/source commands; do not create or stage generated artifacts; do not make rights/scope review change valid-row counts, technical status, lineage state, merge counts, readiness, or apply authorization.

## Task 1: Specify fail-closed rights and scope states with tests

**Files:**

- Modify `tests/test_data_update.py`

- [ ] Add an injected approved source with `prices` and require approved/complete row counts and exact-source review detail.
- [ ] Add or extend a `yfinance` fixture and require `commercial_rights_unverified` with registered price scope complete.
- [ ] Add unknown and blank source cases and require `unknown_source`, incomplete price scope, and no alias inference.
- [ ] Add a mixed batch and require deterministic mixed states/counts.
- [ ] Assert technically invalid rows do not enter rights/scope counts.
- [ ] Run focused tests and confirm the new summary assertions fail before implementation.

## Task 2: Implement pure staged-source evidence review

**Files:**

- Modify `src/data_update.py`

- [ ] Import the existing immutable source-rights types and evaluator.
- [ ] Add a pure helper that reviews technically valid rows by exact trimmed source ID.
- [ ] Report independent aggregate states, row counts, status counts, and deterministic distinct-source details.
- [ ] Keep missing/blank source fail-closed and require exact `prices` membership in `supported_fields`.
- [ ] Add concise review-required warnings without changing technical validity.
- [ ] Make `validate_price_imports(...)` accept optional registry injection and default to the checked-in registry.
- [ ] Pass the same registry through `preview_price_import_merge(...)`; preserve all merge results.
- [ ] Run focused data-update tests and require them to pass.

## Task 3: Durable contracts

**Files:**

- Modify `ROADMAP.md`
- Modify `docs/METHODOLOGY.md`
- Modify `docs/PROVENANCE_CONTRACT.md`
- Modify `docs/DATA_STRATEGY.md`
- Modify `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify documentation contract tests only if required

- [ ] Record the independent staged rights/scope review and its exact non-activation boundary.
- [ ] Preserve the current 146-row canonical price-lineage audit and external dependency classification.
- [ ] Add the design/plan anchor and next external unblock condition to the continuation prompt.
- [ ] Run focused documentation and public wording checks.

## Task 4: Full verification and delivery

- [ ] Run focused changed-module tests.
- [ ] Run `python3 -m pytest tests -q`.
- [ ] Run dashboard smoke and all six research render routes.
- [ ] Run public wording/check, commercial beta/check release, pilot readiness, hygiene, and whitespace checks.
- [ ] Verify readiness remains stale and no repository data command or generated artifact ran.
- [ ] Stage exact product/code/docs/test paths only; never use `git add -A`.
- [ ] Run staged hygiene and cached whitespace checks.
- [ ] Commit one coherent implementation slice and push only `codex/personal-research-mode-mvp`.
- [ ] Update draft PR #113 and verify it remains open and draft.
- [ ] Re-audit remaining safe local tasks; keep the overall goal active while any applicable gate remains unproven.
