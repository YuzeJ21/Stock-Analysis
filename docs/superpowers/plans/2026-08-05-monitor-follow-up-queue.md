# Monitor Follow-up Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to execute this plan task by task.

**Goal:** Replace Monitor's three competing primary summaries with one truthful, answer-first Follow-up Queue while retaining full saved identities and technical evidence under Advanced.

**Architecture:** Extend the existing read-only Monitor composition helper instead of adding a route or calculation engine. The pure composer will separate verification, evidence-wait, scheduled, saved-change, and freshness states, expose one fail-closed actionable-state contract, and leave canonical data/readiness untouched. The Streamlit renderer will consume that contract once in the primary layer and move detailed process/source-change tables into existing Advanced disclosure.

**Tech Stack:** Python 3, frozen dataclasses, pandas, Streamlit, existing dashboard HTML/CSS helpers, pytest, existing direct-browser accessibility gate.

## Global Constraints

- Research-only: no recommendations, rankings, return scores, transaction language, probabilities, or portfolio instructions.
- Never infer that an empty saved queue proves no external event, risk, or research need exists.
- Do not modify source, readiness, evidence identity, authoring, calculation, or persistence contracts.
- Do not run readiness rebuilds, broad refreshes, or generated-report commands.
- Keep all pre-existing generated CSV/output modifications unstaged and byte-identical.
- Never use `git add -A`; stage only the named code, test, and documentation files.
- Work test-first and observe every new behavioral test fail before production changes.

## Task 0: Protect the Starting State

**Files:** No repository edits.

1. Verify branch, HEAD, remote divergence, PR state, and the exact list of existing generated modifications.
2. Record SHA-256 hashes for every protected generated path.
3. Run focused Monitor composition, dashboard-contract, render-smoke, and browser-gate tests as a non-writing baseline.
4. Stop if an intentional product/code/docs/test file is already dirty or if a protected hash changes.

## Task 1: Compose One Follow-up Queue Contract

**Files:**

- Modify: `src/research_workspace.py`
- Modify: `tests/test_research_workspace.py`

1. Add failing tests that prove the composition exposes five question keys in this order: `since_last_review`, `needs_verification`, `waiting_on_evidence`, `scheduled_context`, `evidence_freshness`.
2. Add failing tests that independently classify needs-review and unavailable rows, preserve saved cohort order, keep candidate-only wording truthful, and fail closed on blank freshness inputs.
3. Add failing tests for the actionable-state boundary:
   - weekly/source-change/process/scheduled evidence makes the queue non-empty;
   - monitor-only rows do not;
   - a truly empty saved state exposes one explicit external-event boundary and one Discover return action contract.
4. Run the focused tests and record the expected failures.
5. Implement the smallest frozen composition contract that passes without changing saved data or calculations.
6. Run focused tests and mutation-check the wrong-key order, unavailable classification, and false empty-state branches.
7. Stage only these two files, run staged hygiene and whitespace checks, and commit the coherent composition slice.

## Task 2: Render One Primary Follow-up Queue

**Files:**

- Modify: `src/dashboard.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`
- Modify: `tests/test_dashboard_render_smoke.py`

1. Add failing renderer-contract tests proving Monitor has one `Follow-up Queue` primary heading and no primary `Evidence Monitor Brief`, `Research Discipline Review`, or `Research change monitor` headings.
2. Add failing tests for one zero state containing the external-event boundary and exactly one `Open Discover` action.
3. Add failing tests that actionable states render the compact five-panel queue once while process/source-change details remain inside Advanced.
4. Run the focused tests and record the expected failures.
5. Recompose `render_research_monitor` around the pure queue contract:
   - render one five-panel grid when actionable saved evidence exists;
   - otherwise render one concise neutral state and one Discover action;
   - move full discipline rows, identities, and raw source-change rows under one logical Advanced disclosure;
   - retain the five-company nowcast and evidence drawers as Advanced only.
6. Run focused composition, dashboard-contract, and route-render tests.
7. Stage only the named renderer/test files, run staged hygiene and whitespace checks, and commit.

## Task 3: Update Direct-Browser Monitor Evidence

**Files:**

- Modify: `src/research_accessibility_browser_gate.py`
- Modify: `tests/test_research_accessibility_browser_gate.py`

1. Add failing browser-evaluator tests for the five-card desktop/phone geometry, one primary queue, one zero-state maximum, and Advanced identity preservation.
2. Replace the old four-card Monitor selectors/assertions with the Follow-up Queue contract.
3. Keep the gate repository/data read-only and fail closed on missing route markers, overflow, duplicate headings, hidden return action, or missing external-event boundary.
4. Run focused evaluator tests, then the direct browser matrix at `1280x720` and `390x844`.
5. Stage only the gate and its tests, run staged hygiene and whitespace checks, and commit.

## Task 4: Reconcile Documentation and Release Evidence

**Files:**

- Modify: `ROADMAP.md`
- Modify: `docs/PERSONAL_RESEARCH_MODE.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: `docs/superpowers/plans/2026-08-05-monitor-follow-up-queue.md`

1. Record the exact implemented Monitor question, zero-state boundary, Advanced evidence location, and unchanged research/readiness contracts.
2. Name Research Desk simplification as the next local slice; do not claim the full answer-first program complete.
3. Run focused tests plus:
   - `python3 -m pytest tests -q`
   - `make dashboard-smoke`
   - `make research-dashboard-render-smoke`
   - `make research-accessibility-browser-check`
   - `make public-wording-check`
   - `make public-performance-gate`
   - `make public-check`
   - `make pilot-readiness-check TOP_N=10`
   - `make diff-hygiene-summary`
   - `git diff --check`
4. Recompute protected-artifact hashes and require byte identity.
5. Stage only the named documentation files, run staged hygiene, and commit.
6. Push only `codex/personal-research-mode-mvp`, update draft PR #113, keep it draft, and require exact-head CI.
7. Continue automatically to Research Desk simplification only after the Monitor slice has local and exact-head evidence.

## Current Execution Evidence

- Tasks 0-3 are implemented and committed through `199fa94b266a8bb325bfc4a4df1742158282d47a`.
- Focused composition, dashboard, render, and browser-evaluator tests pass.
- The clean direct-browser gate passed all 12 six-route/two-viewport cases at `1280x720` and `390x844`; Monitor had no horizontal overflow, rendered the expected five-panel responsive grid, and preserved complete Advanced identities.
- Exactly 18 pre-existing generated CSV/output modifications remained unstaged and were classified as excluded.
- Task 4 local release verification passed at `05173ab3d1d2ace16add1c190a1362ef4c39459a`: 6,328 tests, dashboard/render/public gates, 60/60 performance, `public-check`, and all 12 clean desktop/phone accessibility-browser cases passed.
- Pilot readiness remained truthfully blocked on working readiness evidence, source proof, and pending GitHub synchronization.
- Push, draft-PR update, and exact-head CI remain pending; the answer-first program is not complete.
