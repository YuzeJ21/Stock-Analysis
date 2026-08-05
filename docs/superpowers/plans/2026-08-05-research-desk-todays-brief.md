# Research Desk Today's Brief Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Research Desk's overlapping weekly summary and four answer cards with one truthful Today's Research Brief that identifies the saved work needing attention, its most important reason, one next action, and the relevant freshness warning.

**Architecture:** Add one frozen, read-only composition contract in `src/research_workspace.py` and have the existing Streamlit route render it once. The composer uses only the already-loaded weekly summary, saved source-change state, and profile freshness; it does not inspect markets, rebuild readiness, persist a preview, or reproduce Monitor's detailed queue. Existing weekly, cohort, coverage, and source-change details remain available under Advanced.

**Tech Stack:** Python 3, frozen dataclasses, Streamlit, existing dashboard HTML/CSS helpers, pytest, existing render/performance/accessibility gates.

## Global Constraints

- Research-only; no recommendations, rankings, expected returns, transaction instructions, probabilities, portfolio actions, or market-complete event claims.
- Preserve independent actuals, consensus, Revenue, EPS, valuation, peer, catalyst, outcome, backtesting, and calibration states.
- A no-item state describes only saved evidence and cannot prove that no external event, risk, or research need exists.
- Do not alter source data, readiness, evidence identity, calculations, thresholds, route query parameters, or authoring persistence.
- Do not run readiness rebuilds, broad refreshes, or generated-report commands.
- Keep all pre-existing generated CSV/output modifications unstaged and byte-identical.
- Never use `git add -A`; stage only named code, test, and documentation files.
- Work test-first and observe each new behavioral test fail before production changes.

---

### Task 1: Compose one Desk brief

**Files:**
- Modify: `src/research_workspace.py`
- Modify: `tests/test_research_workspace.py`

**Interfaces:**
- Consumes: `WeeklyResearchSummary`, saved `change_status`, saved `review_items`, `freshness_state`, and `freshness_message`.
- Produces: `ResearchDeskBrief` and `build_research_desk_brief(...)` with `attention_count`, `answer`, `reason`, `freshness_warning`, one next-action label/URL, and a research-only external-event boundary.

- [x] Add a failing test for saved weekly/change work that routes to Monitor and chooses the first traceable saved reason.
- [x] Add a failing test for a no-item state that routes to Discover and preserves the external-event boundary.
- [x] Add a failing test proving blank or non-current freshness fails closed to an explicit warning, while a current state stays concise.
- [x] Run the focused tests and confirm they fail because the composer does not exist.
- [x] Implement the smallest immutable composer; deduplicate the weekly and change counts rather than adding them blindly.
- [x] Run the focused tests and mutation-check the route branch, deduplication branch, and blank-freshness fallback.
- [x] Stage only the composer and test files, run staged hygiene and whitespace checks, and commit.

### Task 2: Render one primary answer

**Files:**
- Modify: `src/dashboard.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`
- Modify: `tests/test_dashboard_render_smoke.py`

**Interfaces:**
- Consumes: `build_research_desk_brief(...)`.
- Produces: one `Today's Research Brief` primary section with one question, answer, reason, freshness warning, stop rule, and one action before Advanced.

- [x] Add failing route/render tests proving the old `Weekly research summary` and four-card grid are absent from the primary layer.
- [x] Add failing tests proving one primary action routes to Monitor when saved work exists and Discover otherwise.
- [x] Add failing tests proving weekly cards, cohort/coverage evidence, weekly rows, and detailed source-change evidence remain under Advanced.
- [x] Run focused tests and record the expected failures.
- [x] Render the brief once with the existing visual system, move weekly summary cards and the research-change route summary into `Advanced Evidence`, and remove primary use of the four-card helper.
- [x] Run focused workspace, dashboard-contract, and render-smoke tests.
- [x] Stage only the renderer and test files, run staged hygiene and whitespace checks, and commit.

### Task 3: Reconcile responsive/browser contracts

**Files:**
- Modify: `src/public_performance_gate.py`
- Modify: `src/research_accessibility_browser_gate.py`
- Modify: `tests/test_public_performance_gate.py`
- Modify: `tests/test_research_accessibility_browser_gate.py`

**Interfaces:**
- Produces: Research Desk route markers and direct-browser assertions for one brief, one action, visible stop rule, no horizontal overflow, and Advanced preservation at `1280x720` and `390x844`.

- [x] Add failing evaluator/performance tests for the new first-useful marker and one-brief contract.
- [x] Update only Research Desk route markers and geometry/visibility checks; keep the gate read-only.
- [x] Run focused evaluator and performance tests, then the direct browser matrix.
- [x] Stage only the gate and test files, run staged hygiene and whitespace checks, and commit.

### Task 4: Reconcile docs and release evidence

**Files:**
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `docs/PERSONAL_RESEARCH_MODE.md`
- Modify: `docs/DASHBOARD_QA.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: `docs/superpowers/plans/2026-08-05-research-desk-todays-brief.md`

- [x] Document the one-brief workflow, its no-external-event boundary, Advanced detail location, and unchanged readiness/evidence contracts.
- [x] Name shared-shell/navigation cleanup as the next separate local slice; do not claim the full answer-first program or external maturity gates complete.
- [ ] Run focused tests and `python3 -m pytest tests -q`.
- [ ] Run dashboard startup/render, accessibility-browser, public wording/performance/check, pilot-readiness, diff-hygiene, and whitespace checks.
- [ ] Recompute protected-artifact hashes and require byte identity for the same 18 excluded generated paths.
- [ ] Stage only named documentation files, run staged hygiene, and commit.
- [ ] Push only `codex/personal-research-mode-mvp`, update draft PR #113, keep it draft, and require exact-head CI before continuing.

## Plan Self-Review

- The plan covers the approved Desk question, one answer, one reason, one action, freshness warning, stop rule, Advanced evidence, no-write behavior, responsive evidence, documentation, and release closure.
- No source, readiness, ranking, calculation, authoring, or external-validation contract changes.
- The composer and renderer signatures are consistent across tasks; no placeholder implementation steps remain.
