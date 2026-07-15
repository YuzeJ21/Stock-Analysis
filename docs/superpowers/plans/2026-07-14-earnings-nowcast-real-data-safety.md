# Earnings Nowcast Real-Data Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Earnings Nowcast safe to activate with real point-in-time evidence by fixing release-state truth, fiscal-period canonicalization, metric comparability, methodology diagnostics, public wording, and read-only onboarding.

**Architecture:** Keep immutable source rows at the contract boundary, canonicalize them into metric-specific effective quarterly observations at a forecast cutoff, and fail closed on unresolved conflicts or incompatible definitions. Preserve the current deterministic baseline and separate software-test evidence, real-data readiness, backtest sufficiency, and calibration readiness.

**Tech Stack:** Python 3.12, dataclasses, CSV/JSON read-only onboarding, pytest, Streamlit, Make.

## Global Constraints

- Research-only; no investment advice, trading, order routing, auto-trading, or direct buy/sell instructions.
- No fabricated values, evidence, probabilities, sources, performance, or reviewers.
- No broad refresh, real-data apply path, generated-artifact staging, `git add -A`, or push.
- Synthetic fixtures may use explicit test defaults; real onboarding rows must use complete comparability metadata.

---

### Task 1: Branch Sync Truth

**Files:** `src/pilot_readiness.py`, `tests/test_pilot_readiness.py`

- [x] Add failing tests for aligned, ahead, behind, diverged, and no-upstream branches.
- [x] Replace status-line-only inference with explicit upstream/origin comparison.
- [x] Verify focused readiness tests and the live no-upstream branch result.

### Task 2: Canonical Quarterly Evidence

**Files:** `src/earnings_nowcast_contract.py`, `src/earnings_nowcast_readiness.py`, `src/earnings_nowcast_model.py`, relevant tests.

- [x] Add failing tests proving duplicate periods cannot satisfy history.
- [x] Add immutable metric-definition fields and deterministic cutoff-aware canonicalization.
- [x] Fail Revenue and EPS independently on unresolved conflicts.
- [x] Verify exact duplicates, revisions, post-cutoff rows, and metric independence.

### Task 3: Metric Comparability

**Files:** contract, readiness, model, onboarding, CSV templates, tests.

- [x] Add failing tests for currency, unit-scale, EPS-basis, share-basis, and restatement mismatches.
- [x] Require explicit metadata for real onboarding while preserving explicit synthetic defaults.
- [x] Withhold only the incompatible metric and expose precise missing/conflict reasons.

### Task 4: Methodology Diagnostics

**Files:** `src/earnings_nowcast_backtest.py`, `src/earnings_nowcast_report.py`, tests.

- [x] Add failing tests for separate Revenue/EPS classifications and interval coverage.
- [x] Add prior-year EPS benchmark, expected report date, forecast horizon, and backtest sample sufficiency.
- [x] Keep probability unavailable without a documented model and 100 valid events.

### Task 5: Public UI Truth

**Files:** `src/earnings_nowcast_ui.py`, dashboard integration, UI tests.

- [x] Add failing tests for `synthetic_test_only` and `eligibility_unverified` first-view states.
- [x] Show metric-specific readiness, range, classification, definition, freshness, and horizon for real packets.
- [x] Keep conflicts, hashes, source IDs, and revisions under Advanced.

### Task 6: Read-Only Onboarding And Prospective Collection

**Files:** `src/earnings_nowcast_onboarding.py`, Makefile, templates, launcher/onboarding tests.

- [x] Add failing tests for schema version, required columns, conflicts, revisions, rejected rows, and no-write behavior.
- [x] Upgrade templates and preview output for comparability and conflict states.
- [x] Add a scheduler-ready, append-only prospective snapshot plan/status command without fetching or applying unapproved data.

### Task 7: Documentation And Roadmap

**Files:** README, ROADMAP, Earnings Nowcast, methodology, provenance, LinkedIn, walkthrough, milestones.

- [x] Move local performance completion to regression history.
- [x] Make real-data safety the active stage and separate synthetic proof, real coverage, predictive validation, and calibration.
- [x] Keep hosting and external reviewer evidence pending.

### Task 8: Feasibility And Release Closeout

- [x] Inspect local inputs for permitted comparable point-in-time evidence without printing secrets.
- [x] Run validate/preview/readiness for one ticker only if such evidence exists; otherwise classify the exact dependency.
- [x] Run focused tests, full tests, fixture packet, walkthrough, browser/public/performance gates, hygiene, and whitespace checks.
- [x] Stage exact product/code/docs/test/template files, run staged hygiene, and commit locally without pushing.
