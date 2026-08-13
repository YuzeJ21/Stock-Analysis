# Nowcast Calibration Identity Binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make numerical-probability calibration promotable only when its exact immutable observations are mathematically reproducible and bound one-for-one to the same leakage-safe backtest events.

**Architecture:** Extend the existing frozen probability observation and calibration status contracts without breaking identity-less standalone calibration calls. Bound observations carry canonical ticker, fiscal period, cutoff, and one explicit Beat definition; `assess_probability_calibration` retains a canonical immutable tuple and SHA-256 digest. Cohort promotion recomputes calibration from those observations, checks the digest and exact event-identity set, verifies each Boolean outcome from the matching report event, requires that declared metric's own model and consensus benchmark evidence, and rederives stored relative classifications from forecast intervals. A separate canonical digest binds the full supplied backtest package, including normalized chronology, ordered source IDs, model/input identity, scored fields, exclusions, failures, summaries, and benchmarks. That digest is internal-integrity evidence only, not source or rights attestation.

**Tech Stack:** Python frozen dataclasses, SHA-256/JSON canonicalization, pytest, existing Earnings Nowcast contracts.

## Global Constraints

- Strict red-green TDD; every production change follows an observed failing regression.
- Preserve identity-less standalone calibration behavior, but identity-less evidence is never promotable.
- Keep numerical probability out of UI/output contracts.
- Do not weaken Q4, EPS split-basis, source-rights, retrieval-cutoff, or leakage gates.
- Do not stage, commit, push, or modify protected generated artifacts.

---

### Task 1: Immutable observation evidence and exact metric reconstruction

**Files:**
- Modify: `src/earnings_nowcast_backtest.py`
- Test: `tests/test_earnings_nowcast_backtest.py`

**Interfaces:**
- Consumes: existing `ProbabilityObservation(probability, outcome)` and `assess_probability_calibration(...)` calls.
- Produces: optional bound observation fields `ticker`, `fiscal_period`, `as_of_timestamp`, and `outcome_definition`; `CalibrationStatus.observations`, `outcome_definition`, and `evidence_digest` with backward-compatible defaults.

- [ ] **Step 1: Write failing exact-evidence tests**

Add tests proving identity-less observations still assess normally, bound observations are normalized and retained immutably, malformed/partially bound or duplicate identities are rejected, and a deterministic digest is created only for a complete bound cohort.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `python3 -m pytest tests/test_earnings_nowcast_backtest.py -q -k 'observation or identity or digest'`

Expected: failures because the fields and immutable derived evidence do not exist.

- [ ] **Step 3: Implement the minimal compatible contract**

Add the optional fields at the end of frozen dataclasses, canonicalize complete identities as `(TICKER, YYYY-QN, UTC cutoff)`, require one declared definition across a bound cohort, sort bound observations by identity, reject duplicates, and hash canonical probability/outcome/identity payloads. Retain identity-less observation tuples without creating an authorization digest.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `python3 -m pytest tests/test_earnings_nowcast_backtest.py -q`

Expected: all backtest tests pass; legacy identity-less assertions remain unchanged.

### Task 2: Exact recomputation and report-event binding

**Files:**
- Modify: `src/earnings_nowcast_cohort.py`
- Test: `tests/test_earnings_nowcast_cohort.py`

**Interfaces:**
- Consumes: bound `CalibrationStatus.observations`, `CalibrationStatus.evidence_digest`, and `BacktestReport.events`.
- Produces: fail-closed promotion requiring exact recomputed calibration fields, exact canonical identity-set equality, outcome equality under `revenue_actual_strictly_above_consensus` or `eps_actual_strictly_above_consensus` (equality is not a Beat), matching-metric benchmark improvement, rederived event classification, and exact full-report digest equality.

- [ ] **Step 1: Write failing promotion regressions**

Add tests for an impossible forged Brier, identity-less same-count status, unrelated same-count bound status, mutated digest, mismatched cutoff identity, duplicate identity, and an outcome that contradicts its matched report event. Update the positive synthetic and real 100-event cases so each probability observation is genuinely bound to its report event.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `python3 -m pytest tests/test_earnings_nowcast_cohort.py -q -k 'brier or identity or digest or paired or real_walk'`

Expected: forged summaries and unrelated same-count evidence still promote, while wished-for bound observation construction is not yet supported.

- [ ] **Step 3: Implement exact verification**

Re-run `assess_probability_calibration(status.observations)` under the default policy and require every status field, canonical observation tuple, outcome definition, and digest to match the derived status. Require unique observation/report identities to be exactly equal, then derive the declared Beat Boolean from the matched event's actual and consensus field and compare it to each observation.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `python3 -m pytest tests/test_earnings_nowcast_cohort.py tests/test_earnings_nowcast_backtest.py -q`

Expected: all identity, digest, Brier, outcome, and legacy fail-closed tests pass.

### Task 3: Evidence report and verification boundary

**Files:**
- Modify: `.superpowers/sdd/2026-08-01-portable-html-action-policy-repair/fixwave-nowcast-report.md`
- Verify: protected artifact manifest and Git state

**Interfaces:**
- Consumes: completed Task 1 and Task 2 behavior.
- Produces: a precise evidence handoff documenting the strict Beat definition, retained-observation boundary, red/green evidence, and unchanged research-only/UI gates.

- [ ] **Step 1: Run focused and related matrices**

Run the six-module Nowcast matrix and the established related 22-module matrix. Record exact pass/warning counts.

- [ ] **Step 2: Update the ignored evidence report**

Document exact observation reconstruction, digest and event identity matching, strict Revenue/EPS Beat semantics, identity-less non-promotion, and any remaining truthful limitation.

- [ ] **Step 3: Verify hygiene without mutation**

Run `git diff --check`, the protected SHA-256 manifest, `git diff --cached --quiet`, and `git status --short`. Confirm no staging, commit, or push occurred and all 18 protected paths remain hash-identical.
