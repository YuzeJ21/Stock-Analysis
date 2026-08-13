# Focused Cohort Research Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic 25-50 company personal-research cohort with source-backed quarterly trend packets, deduplicated monitoring, and a traceable weekly summary.

**Architecture:** Add three focused read-only domain modules and compose them through the existing research workspace. Reuse ticker readiness, universe classifications, quarterly actuals, change-event identities, and thesis records; never write canonical data or weaken readiness gates.

**Tech Stack:** Python 3.12, pandas, dataclasses, pytest, Streamlit AppTest, existing CSV-first profile and readiness contracts.

## Global Constraints

- Research-only; no recommendations, trading, broker, or order-routing behavior.
- No fabricated or inferred quarterly data, peers, consensus, or valuation inputs.
- Public and Operator routes remain regression-protected.
- Generated data and reports remain unstaged.
- Every production behavior begins with a failing focused test.

---

### Task 1: Deterministic Focused Cohort

**Files:**
- Create: `src/focused_research_cohort.py`
- Create: `tests/test_focused_research_cohort.py`

**Interfaces:**
- Consumes: ticker-readiness and universe-master `pandas.DataFrame` inputs.
- Produces: `FocusedCohortMember`, `FocusedCohort`, `build_focused_cohort(...)`, and `focused_cohort_frame(...)`.

- [x] Write tests for deterministic order, operating-company eligibility, exclusions, duplicate tickers, missing inputs, truthful sub-25 state, and recommendation-free fields.
- [x] Run `python3 -m pytest tests/test_focused_research_cohort.py -q` and confirm the missing-module failure.
- [x] Implement immutable cohort contracts and deterministic selection.
- [x] Rerun the focused tests and commit the coherent cohort slice.

### Task 2: Quarterly Business Trend

**Files:**
- Create: `src/quarterly_business_trend.py`
- Create: `tests/test_quarterly_business_trend.py`

**Interfaces:**
- Consumes: iterable `QuarterlyActual` rows and ticker.
- Produces: `QuarterlyMetricTrend`, `QuarterlyTrendPacket`, `build_quarterly_trend_packet(...)`, and display-row helpers.

- [x] Write tests for sequential and year-over-year comparisons, revisions, missing periods, incompatible metric definitions, ambiguous rows, and explicit Q4-only behavior.
- [x] Run the focused test and confirm RED.
- [x] Implement revision resolution and metric-by-metric fail-closed comparisons.
- [x] Rerun tests and commit the coherent trend slice.

### Task 3: Monitor Detail and Deduplication

**Files:**
- Modify: `src/research_workspace.py`
- Modify: `tests/test_research_workspace.py`

**Interfaces:**
- Consumes: existing `ResearchReviewItem` rows.
- Produces: one deterministic monitor row per event identity with previous/current state, source/effective dates, affected section, next task, and wait condition.

- [x] Add failing tests for duplicate event identities and detailed monitor columns.
- [x] Implement minimal deduplication and field mapping.
- [x] Run focused monitor tests and commit with the Workbench composition slice.

### Task 4: Weekly Research Summary

**Files:**
- Create: `src/weekly_research_summary.py`
- Create: `tests/test_weekly_research_summary.py`

**Interfaces:**
- Consumes: `FocusedCohort`, unresolved research review items, optional reviewer-authored journal summaries, and an as-of timestamp.
- Produces: `WeeklyResearchSummary`, traceable section items, and display rows.

- [x] Add failing tests for empty weeks, duplicate events, excluded tickers, blocked lanes, stale reviews, and prohibited recommendation wording.
- [x] Implement deterministic grouping and traceable source references.
- [x] Run focused tests and commit with workspace integration.

### Task 5: Personal Research Workspace Integration

**Files:**
- Modify: `src/dashboard.py`
- Modify: `src/research_workspace.py`
- Modify: `src/dashboard_render_smoke.py`
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `tests/test_dashboard_render_smoke.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`

**Interfaces:**
- Consumes: cohort, quarterly trend, monitor, and weekly summary contracts.
- Produces: Research Desk, Discover, Company Workbench, and Monitor first-answer UI with Advanced Evidence collapsed.

- [x] Add failing page-contract tests for cohort scope, Workbench answer order, unavailable quarterly evidence, weekly summary, and preserved Public/Operator routes.
- [x] Implement small composition helpers before changing dashboard rendering.
- [x] Run focused dashboard tests and render smoke.
- [x] Commit the coherent workspace slice.

### Task 6: Documentation and Release Verification

**Files:**
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `docs/PERSONAL_RESEARCH_MODE.md`
- Modify only if contracts change: `docs/METHODOLOGY.md`, `docs/PROVENANCE_CONTRACT.md`

**Interfaces:**
- Documents verified cohort size, supported quarterly metrics, withheld states, daily/weekly workflow, automation boundary, and owner-authored review work.

- [x] Update documentation tests before public wording.
- [x] Run focused and full pytest.
- [x] Run dashboard smoke, browser QA, public wording, public check, pilot readiness, diff hygiene, and whitespace checks.
- [x] Review desktop and mobile Research routes plus the Public Single-Stock regression route.
- [x] Stage exact product/code/docs/test files, run staged hygiene, and create a local commit without pushing.
