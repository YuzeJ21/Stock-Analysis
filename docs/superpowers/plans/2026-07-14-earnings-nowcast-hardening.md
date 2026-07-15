# Earnings Nowcast Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing Earnings Nowcast pilot clear to reviewers and ready for append-only real-data onboarding without weakening point-in-time or calibration gates.

**Architecture:** Preserve the existing contracts and deterministic model. Add a public presentation model, an isolated read-only onboarding validator, explicit diagnostic summaries, and a synthetic scenario catalog; integrate those boundaries into the existing UI, CLI, tests, and documentation.

**Tech Stack:** Python 3.12, dataclasses, CSV/JSON, Streamlit, pytest, Make.

## Global Constraints

- Research-only; no investment advice, trading, order routing, auto-trading, or direct buy/sell instructions.
- Do not predict post-earnings price movement or fabricate any input, forecast, probability, source, or result.
- Candidate peer and news signals remain evidence-only and cannot mutate forecast numbers.
- Synthetic fixtures are test evidence only and never real-company proof.
- Numerical probability remains unavailable until at least 100 valid out-of-sample observations pass every calibration gate.
- Onboarding is append-only, preview-only, and never applies rows automatically.
- Generated packets, reports, screenshots, and rejected-row artifacts remain excluded.

---

### Task 1: Reviewer presentation model

**Files:** `src/earnings_nowcast_ui.py`, `tests/test_earnings_nowcast_ui.py`

- [x] Add failing tests for ordered eligibility, baseline, range, consensus, context, withheld, and next-action answers.
- [x] Add plain-English state labels and a structured public answer model.
- [x] Ensure blocked rows expose no numerical forecast and technical evidence stays collapsed.
- [x] Run `python3 -m pytest tests/test_earnings_nowcast_ui.py -q`.

### Task 2: Append-only evidence onboarding

**Files:** `src/earnings_nowcast_onboarding.py`, `tests/test_earnings_nowcast_onboarding.py`, `Makefile`, template CSV files.

- [x] Add failing tests for templates, provenance, duplicate/revision handling, cutoff rejection, preview, and no-write behavior.
- [x] Implement read-only template, validation, preview, and readiness commands.
- [x] Add Make targets without an apply target.
- [x] Run `python3 -m pytest tests/test_earnings_nowcast_onboarding.py -q`.

### Task 3: Backtest and calibration diagnostics

**Files:** `src/earnings_nowcast_backtest.py`, `tests/test_earnings_nowcast_backtest.py`

- [x] Add failing tests for exclusion reasons, valid/invalid counts, calibration-bin diagnostics, and exact failed gates.
- [x] Extend report payloads without changing forecast calculations.
- [x] Run `python3 -m pytest tests/test_earnings_nowcast_backtest.py -q`.

### Task 4: Reviewer fixture catalog

**Files:** `src/earnings_nowcast_report.py`, fixture CSVs, `tests/test_earnings_nowcast_report.py`.

- [x] Add failing tests for six explicitly synthetic reviewer scenarios.
- [x] Implement scenario metadata and fail-closed fixture packet behavior.
- [x] Run `python3 -m pytest tests/test_earnings_nowcast_report.py -q`.

### Task 5: UI integration and browser contract

**Files:** `src/dashboard.py`, browser/UI tests.

- [x] Add failing integration tests for ordered answers and collapsed technical evidence.
- [x] Render the presentation model in Single-Stock Report and Data Health.
- [x] Verify desktop and mobile browser routes.

### Task 6: Documentation and final verification

**Files:** `README.md`, `ROADMAP.md`, `docs/EARNINGS_NOWCAST_PILOT.md`, `docs/METHODOLOGY.md`, `docs/PROVENANCE_CONTRACT.md`.

- [x] Separate software proof, synthetic proof, real-company readiness, calibration readiness, and deferred price-reaction scope.
- [x] Run focused tests, full tests, public/browser/performance gates, hygiene, and diff checks.
- [x] Commit only exact product/code/docs/test/template files; do not push.
