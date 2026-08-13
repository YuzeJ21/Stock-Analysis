# Commercial Research Beta Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the local, deterministic Commercial Research Beta foundation without activating unapproved sources or fabricating analysis evidence.

**Architecture:** Add focused contracts around the existing Personal Research Mode, quarterly actuals, Scenario Lab, thesis journal, source providers, and refresh orchestrator. Keep UI composition thin and fail closed whenever source, rights, freshness, or calibration evidence is absent.

**Tech Stack:** Python 3.12, dataclasses, pandas, CSV/JSON contracts, Streamlit, pytest, Make.

**Implementation status (2026-07-17):** Tasks 1-10 are implemented and locally verified; the desktop/mobile findings and corrected Workbench defect are recorded in [Dashboard QA Notes](../../DASHBOARD_QA.md). The unchecked boxes below preserve the original execution sequence; this status line is the current plan truth. The local package is not hosted, externally validated, merged, or commercially launched.

## Global Constraints

- Research-only; no investment advice, broker integration, trading, order routing, auto-trading, or direct buy/sell instructions.
- Do not fabricate data, forecasts, probabilities, sources, reviewers, or results.
- Candidate peers and qualitative signals never become trusted numerical inputs automatically.
- Commercial mode refuses sources with unverified commercial rights.
- Keep generated data, reports, screenshots, timing output, packets, caches, and rejected rows excluded.
- Never use `git add -A`; do not push or merge unless explicitly asked.

---

### Task 1: Commercial Source-Rights Registry

**Files:**
- Create: `config/source_rights.yml`
- Create: `src/commercial_source_rights.py`
- Create: `tests/test_commercial_source_rights.py`
- Modify: `Makefile`
- Modify: `docs/DATA_STRATEGY.md`

**Interfaces:**
- Produces immutable source-rights records, registry validation, commercial eligibility decisions, and a read-only CLI/status command.

- [ ] Write failing tests for complete records, unknown sources, unverified rights, commercial refusal, and approved-source acceptance.
- [ ] Run focused tests and confirm expected failures.
- [ ] Implement the minimal registry loader and commercial-mode gate.
- [ ] Add a read-only `make commercial-source-rights` command and documentation.
- [ ] Run focused tests and commit the coherent slice.

### Task 2: Focused Cohort Coverage Matrix

**Files:**
- Create: `src/focused_cohort_coverage.py`
- Create: `tests/test_focused_cohort_coverage.py`
- Modify: `src/research_workspace.py`
- Modify: `src/dashboard.py`
- Modify: `docs/PERSONAL_RESEARCH_MODE.md`

**Interfaces:**
- Consumes the deterministic cohort plus saved readiness/source metadata.
- Produces per-company, per-lane states without calculating new fundamentals or changing readiness.

- [ ] Write failing tests for usable, partial, candidate-only, blocked, excluded, missing, and maximum-50 behavior.
- [ ] Implement immutable coverage rows and matrix summaries.
- [ ] Show the concise answer in Discover/Workbench; keep the full matrix under Advanced.
- [ ] Run focused tests and commit the coherent slice.

### Task 3: Quarterly Actuals Review Contract

**Files:**
- Modify: `src/earnings_nowcast_onboarding.py`
- Modify: `src/quarterly_business_trend.py`
- Modify: `Makefile`
- Modify: `tests/test_earnings_nowcast_onboarding.py`
- Modify: `tests/test_quarterly_business_trend.py`
- Modify: `docs/EARNINGS_NOWCAST_PILOT.md`

**Interfaces:**
- Preserves existing append-only templates, validation, preview, duplicate/revision handling, rejected-row reporting, and readiness.

- [ ] Add failing tests for ambiguous periods, incompatible units, post-cutoff rows, unresolved revisions, inferred Q4, and preview-only behavior.
- [ ] Close only verified contract gaps; do not add automatic apply.
- [ ] Add or clarify canonical read-only commands and readiness output.
- [ ] Run focused tests and commit the coherent slice.

### Task 4: Deterministic Forward View V1

**Files:**
- Create: `src/forward_view.py`
- Create: `tests/test_forward_view.py`
- Modify: `src/research_workspace.py`
- Modify: `src/dashboard.py`
- Modify: `docs/METHODOLOGY.md`

**Interfaces:**
- Consumes quarterly trend, source-backed valuation readiness/scenarios, trusted-peer state, reviewer-authored thesis evidence, and Earnings Outlook readiness.
- Produces one immutable packet with trend, scenario, context, withholding, and next-task sections.

- [ ] Write failing tests for complete, partial, stale, candidate-peer-only, invalid-assumption, and calibration-withheld cases.
- [ ] Implement the packet without introducing a second valuation or nowcast calculation.
- [ ] Integrate it into Company Workbench in the required answer order.
- [ ] Keep raw provenance under Advanced and run focused tests.
- [ ] Commit the coherent slice.

### Task 5: Point-In-Time Validation Diagnostics

**Files:**
- Modify: `src/earnings_nowcast_backtest.py`
- Modify: `tests/test_earnings_nowcast_backtest.py`
- Modify: `docs/METHODOLOGY.md`

**Interfaces:**
- Preserves event snapshots, cutoff enforcement, benchmark comparisons, interval diagnostics, and probability calibration gates.

- [ ] Add failing tests for empty evidence, revised consensus, stale snapshots, mixed valid/invalid events, and benchmark non-improvement.
- [ ] Add only missing diagnostics and fail-closed reasons.
- [ ] Confirm synthetic fixtures never produce predictive-accuracy claims.
- [ ] Run focused tests and commit the coherent slice.

### Task 6: Controlled Refresh Operations Contract

**Files:**
- Create: `src/refresh_operations.py`
- Create: `tests/test_refresh_operations.py`
- Modify: `src/auto_refresh_orchestrator.py`
- Modify: `Makefile`
- Modify: `docs/SCHEDULER_ACTIVATION_CHECKLIST.md`

**Interfaces:**
- Produces read-only job plans/states for fetch, normalize, validate, quarantine, preview, snapshot publish, readiness rebuild, and change detection.

- [ ] Write failing tests for provider unavailability, retry caps, identical attempts, schema changes, provenance loss, duplicates, stale rows, partial batches, and quarantine.
- [ ] Implement deterministic plans and failure classifications with automatic apply disabled.
- [ ] Add read-only status/runbook commands.
- [ ] Run focused tests and commit the coherent slice.

### Task 7: Private-Beta Readiness Contract

**Files:**
- Create: `src/private_beta_readiness.py`
- Create: `tests/test_private_beta_readiness.py`
- Create: `docs/PRIVATE_BETA_ARCHITECTURE.md`
- Modify: `Makefile`
- Modify: `docs/HOSTED_DEMO_DEPLOYMENT.md`

**Interfaces:**
- Produces a read-only classification for authentication, workspaces, user data separation, secrets, audit, retention, entitlements, monitoring, and health checks.

- [ ] Write failing tests for local-ready, external-account-required, and unsafe-secret states.
- [ ] Implement the readiness checklist without claiming runtime authentication or hosting.
- [ ] Document data boundaries and exact external setup steps.
- [ ] Run focused tests and commit the coherent slice.

### Task 8: Commercial Beta Product Contract And Pilot Package

**Files:**
- Modify: `ROADMAP.md`
- Modify: `README.md`
- Modify: `docs/PILOT_RUNBOOK.md`
- Modify: `docs/PILOT_REVIEW_FEEDBACK_TEMPLATE.md`
- Modify: `docs/PRODUCT_DIRECTION_DECISION.md`
- Modify: `tests/test_launchers.py`
- Modify: `tests/test_pilot_review_feedback_template.py`

**Interfaces:**
- Makes `ROADMAP.md` the sole active plan and defines beta jobs, outcomes, safe claims, external classifications, and pilot measures.

- [ ] Write failing documentation-contract tests.
- [ ] Reconcile current-status wording without hard-coded changing coverage claims.
- [ ] Add the 10-20 user task-based runbook and measurement definitions.
- [ ] Keep absent users as `awaiting_external_review`.
- [ ] Run focused tests and commit the coherent slice.

### Task 9: Desktop And Mobile UX Hardening

**Files:**
- Modify only reproducibly affected product/test files after live review.

**Interfaces:**
- Preserves Research Desk -> Discover -> Company Workbench -> Monitor and Advanced Evidence boundaries.

- [ ] Review 1280x720 and 390x844 for all four primary pages plus supporting evidence links.
- [ ] Add a failing regression test before each reproducible fix.
- [ ] Fix first-answer order, overflow, premature raw evidence, blocked-output ambiguity, or missing next action only when observed.
- [ ] Run focused browser/UI tests and commit one coherent slice if changes exist.

### Task 10: Final Verification And Review

**Files:**
- No new scope; fix only findings from this plan.

- [ ] Run all focused tests.
- [ ] Run `python3 -m pytest tests -q`.
- [ ] Run dashboard, browser, wording, public, pilot, hygiene, and whitespace gates.
- [ ] Run a fresh broad branch review and fix Critical/Important findings.
- [ ] Confirm generated artifacts remain excluded and external dependencies are classified.
- [ ] Report safe push, host, pilot, and commercialization boundaries without pushing.
