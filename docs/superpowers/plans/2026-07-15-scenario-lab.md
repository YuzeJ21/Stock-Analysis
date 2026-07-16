# Scenario Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a session-local, readiness-gated DCF Scenario Lab that reuses canonical valuation formulas and never mutates source data.

**Architecture:** `src/scenario_lab.py` validates bounded reviewer assumptions, delegates DCF and sensitivity calculations to `src.valuation`, and returns an immutable result contract. Dashboard helpers reconstruct the existing report's source-backed `ValuationInput`; Streamlit controls appear only inside the detailed Valuation tab.

**Tech Stack:** Python 3.12, dataclasses, hashlib/JSON identity, existing valuation engine, Streamlit, pandas, pytest.

## Global Constraints

- Research-only; no target prices, investment advice, rankings, transaction instructions, broker integration, or portfolio sizing.
- DCF readiness and operating-company eligibility are mandatory.
- Canonical source-backed facts are immutable.
- Scenario parameters remain session-local and create no files.
- Existing valuation formulas and conservative normalization remain authoritative.

---

### Task 1: Scenario contract and fail-closed eligibility

**Files:**
- Create: `src/scenario_lab.py`
- Create: `tests/test_scenario_lab.py`

**Interfaces:**
- Produces `ScenarioParameters`, `ScenarioLabResult`, `validate_scenario_parameters`, and `run_scenario_lab`.

- [ ] Write failing tests for DCF-not-ready, non-company, missing per-share baseline, invalid bounds, and immutable source facts.
- [ ] Run the focused tests and confirm expected failures.
- [ ] Implement minimal validation and delegated DCF calculations.
- [ ] Re-run focused tests and commit `Add readiness-gated Scenario Lab`.

### Task 2: Sensitivity, identity, and result explanation

**Files:**
- Modify: `src/scenario_lab.py`
- Modify: `tests/test_scenario_lab.py`

**Interfaces:**
- Adds deterministic input identity, changed-assumption rows, sensitivity range, terminal-value contribution, and plain-language rendering.

- [ ] Write failing tests for stable identity, directional sensitivity, exact deltas, terminal contribution, and prohibited language.
- [ ] Run tests to verify red, implement the result details, then verify green.
- [ ] Commit `Add explainable scenario sensitivity results`.

### Task 3: Single-Stock Valuation-tab integration

**Files:**
- Modify: `src/dashboard.py`
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `src/browser_qa_evidence.py`
- Modify: `tests/test_browser_qa_evidence.py`

**Interfaces:**
- Produces `scenario_lab_input_from_report`, `scenario_lab_status_cards`, and `render_scenario_lab`.

- [ ] Write failing tests for report-input mapping, readiness gating, control bounds, collapsed technical evidence, and no first-viewport regression.
- [ ] Run focused tests, implement controls in the detailed Valuation tab, and rerun focused tests plus dashboard/browser smoke.
- [ ] Commit `Integrate Scenario Lab into valuation review`.

### Task 4: Documentation and completion audit

**Files:**
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `docs/METHODOLOGY.md`
- Modify: `docs/PROVENANCE_CONTRACT.md`

**Interfaces:**
- Documents eligibility, bounds, session-local state, and explicit interpretation limits.

- [ ] Add or update documentation assertions first.
- [ ] Update docs and mark the Scenario Lab regression gate only after implementation verification.
- [ ] Run focused and full tests, dashboard smoke, browser QA, public wording, public check, pilot readiness, diff hygiene, and whitespace checks.
- [ ] Commit only after all gates pass.
