# Research Comparison View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the existing selected-ticker tray into a readiness-first, non-ranking comparison for two or three companies.

**Architecture:** A focused comparison module validates selected rows and combines them with optional profile-scoped journal states. Stock Selector renders the resulting evidence matrix inside its existing collapsed operator tray; no new route or persisted output is added.

**Tech Stack:** Python dataclasses, pandas, Streamlit, pytest.

## Global Constraints

- Compare two or three unique tickers and preserve user order.
- No ranking, score, winner, recommendation, expected return, or transaction language.
- Candidate peers never satisfy trusted-peer readiness.
- Journal evidence must stay selected-profile and reviewer-authored.
- No data, readiness, report, proof, or journal writes.

---

### Task 1: Comparison Contract

**Files:**
- Create: `src/research_comparison.py`
- Create: `tests/test_research_comparison.py`

**Interfaces:**
- Produces: `ResearchComparison`, `build_research_comparison(selected_rows, journal_states)`, and `comparison_matrix_rows(comparison)`.

- [ ] Write failing tests for two-to-three selection, duplicate rejection, order, readiness mapping, journal evidence, and prohibited output language.
- [ ] Run the focused test and confirm missing-interface failures.
- [ ] Implement immutable comparison columns and matrix rows with explicit missing states.
- [ ] Re-run focused tests and commit the core slice.

### Task 2: Selector Evidence And UI

**Files:**
- Modify: `src/dashboard.py`
- Modify: `tests/test_dashboard_helpers.py`

**Interfaces:**
- Consumes: `build_research_comparison` and profile-scoped `JournalState` values.
- Produces: explicit selector readiness columns and a collapsed comparison matrix.

- [ ] Write failing tests for queue readiness fields, selected-order matrix, journal loading, max three selections, and placement inside the existing Advanced tray.
- [ ] Run exact tests and verify expected failures.
- [ ] Add readiness fields and render the evidence matrix only after two or three rows are selected.
- [ ] Run focused selector, journal, navigation, and dashboard tests; commit the UI slice.

### Task 3: Documentation And Release Verification

**Files:**
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `docs/METHODOLOGY.md`
- Modify: `docs/PROVENANCE_CONTRACT.md`
- Modify: `tests/test_public_v1_release_docs.py`

**Interfaces:**
- Documents the non-ranking, selected-profile, reviewed-evidence boundary.

- [ ] Add a failing documentation contract test.
- [ ] Update concise product and methodology wording without adding a page or expanding README length.
- [ ] Run focused comparison, selector, docs, and provenance tests.
- [ ] Run `make public-check`, `make pilot-readiness-check TOP_N=10`, `make diff-hygiene-summary`, and `git diff --check`.
- [ ] Commit exact source/docs/test files only after staged hygiene passes.
