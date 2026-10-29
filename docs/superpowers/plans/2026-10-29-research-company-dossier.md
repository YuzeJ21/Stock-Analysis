# Research Company Dossier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the research flow compact, source-aware, and useful at first glance.

**Architecture:** Keep the existing Streamlit routes and source contracts. Change pure HTML presenters for Discover and Company Workbench, wire saved report provenance into the evidence map, and apply a scoped research-only visual layer. Keep existing SEC fetch and canonical data untouched.

**Tech Stack:** Python, Streamlit, pure HTML/CSS presenters, pytest, local browser gates.

**Spec:** `docs/superpowers/specs/2026-10-29-research-company-dossier-design.md`

## Global Constraints

- Saved local report state, online SEC inspection, and source-rights status remain distinct.
- No new financial values or eligibility claims from listing identity alone.
- Escape all text at HTML boundaries and preserve canonical same-app routes.
- Desktop 1280x720, phone 390x844, and 200% zoom require live checks.

## Review Focus

- Missing saved report: show unavailable rather than a reviewable lane.
- Same ticker from another provider or profile: discard the cached report before presenting saved evidence.
- Missing source or period: show unknown, not an invented date.
- SEC fetch failure: retain a visible reason and no readiness change.
- Long ticker/theme/blocker strings: escape and wrap without horizontal overflow.
- Keyboard search and company-opening links: remain operable with clear focus.
- A 200% phone zoom must keep each primary navigation target at least 44px wide.

---

### Task 1: Compact Discover results

**Files:** Modify `src/dashboard.py` in `stock_selector_result_table_html` and `discover_primary_answer_html`; test `tests/test_dashboard_helpers.py`.

**Interfaces:** Preserve `stock_selector_result_table_html(frame, *, total_count, limit, target_mode, target_page) -> str`. Research mode gets concise rows; public mode keeps its existing result contract.

- [x] Write a failing test for a research row with saved state, one gap, a closed details disclosure, and direct company action.
- [x] Confirm the test fails for the existing verbose row.
- [x] Implement the bounded research row while escaping all user or data strings.
- [x] Run the focused tests and review long/missing-text behavior.

### Task 2: Company evidence map

**Files:** Modify `src/research_workspace.py`; test `tests/test_research_workspace.py`.

**Interfaces:** Preserve `company_workbench_primary_brief_html(brief) -> str`. Extend `company_workbench_evidence_status_html` with optional `report_payload` while preserving existing callers.

- [x] Write failing tests for compact summary, five-lane table, known source/period, and unknown metadata.
- [x] Confirm failures reflect missing presentation behavior.
- [x] Implement escaped summary and evidence map without new numeric claims.
- [x] Run focused tests and check navigation semantics.

### Task 3: Integrate the first-read flow and visual system

**Files:** Modify `src/dashboard.py` in `render_company_workbench` and `render_research_workspace_styles`; modify `src/dashboard_visual_system.py`; test dashboard contracts and visual CSS tests.

**Interfaces:** Pass the loaded saved report payload to the evidence map. Keep explicit `Check SEC annual facts` and existing source/rights validation unchanged.

- [x] Add failing route/DOM assertions for one-column first-read order and visible SEC action/evidence map.
- [x] Wire placeholders in the new order, preserving loading and unavailable states.
- [x] Add scoped desktop/phone CSS for compact navigation, results, summary, evidence table, and online action.
- [x] Run focused tests, then desktop/phone browser checks and inspect screenshots.

### Task 4: Closeout

**Files:** Update roadmap and local release evidence; commit reviewed code/docs/tests.

- [ ] Run the settled test set, import/render smoke, browser accessibility and visual checks, staged hygiene, and `git diff --check`.
- [ ] Confirm no canonical data, source-rights registry, raw captures, or generated reports entered the commit.
- [ ] Record exact head, results, remaining rights and hosted gates, and local screenshots.
