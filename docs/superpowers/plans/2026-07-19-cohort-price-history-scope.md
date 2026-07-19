# Cohort Price-History Scope Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task by task.

**Goal:** Prevent saved price readiness from becoming commercially usable cohort evidence without row-level provenance, exact-source rights, and registered `prices` scope.

**Architecture:** Review grouped canonical price rows inside `derive_cohort_evidence`, pass the result into the existing coverage builder, and load `prices.csv` through the dashboard’s current read-only optional loader. Keep research mode and all mutation paths unchanged.

**Tech Stack:** Python 3.12, pandas, pytest, immutable source-rights registry

### Task 1: Add failing price-history evidence tests

**Files:** `tests/test_focused_cohort_coverage.py`, `tests/test_research_mode_dashboard_contract.py`

Test missing rows, missing lineage, approved scoped rows, missing scope, mixed histories, research compatibility, and the real dashboard loader contract. Run the two focused files and confirm failures against the saved-readiness-only behavior.

### Task 2: Implement row-group price review

**Files:** `src/focused_cohort_coverage.py`, `src/dashboard.py`

Add optional `prices` and injectable registry inputs. Normalize grouped rows, retain technically valid rows, require `source`, `source_ref`, and `retrieved_at` for every commercial row, review each exact source with `review_commercial_field_scope(..., ("prices",))`, and return a deterministic state/evidence message. Conjunct the commercial evidence with saved `price_ready`; preserve research mode.

### Task 3: Document and verify

**Files:** `ROADMAP.md`, `docs/METHODOLOGY.md`, `docs/PROVENANCE_CONTRACT.md`, `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`

Record only the verified cohort display boundary and keep Priority 5 chronology plus quarterly Revenue/EPS open. Run focused tests, full tests, dashboard/render, public, commercial, pilot, hygiene, and whitespace gates. Stage exact paths, commit, push, update draft PR #113, and require hosted CI on the exact head.
