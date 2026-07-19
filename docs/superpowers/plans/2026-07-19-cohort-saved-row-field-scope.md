# Cohort Saved-Row Field-Scope Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task by task.

**Goal:** Prevent one source-level commercial approval from unlocking unrelated focused-cohort fields while preserving research-mode behavior and independent lane states.

**Architecture:** Replace the shared `_source_backed` commercial boolean in `focused_cohort_coverage.py` with pure per-row field review helpers using `review_commercial_field_scope`. Compose each saved-row lane from separate technical, provenance, rights, and exact-field decisions, while retaining the existing coverage frame and Advanced dashboard boundary.

**Tech Stack:** Python 3.12, pandas, pytest, immutable YAML source-rights registry

## Constraints

- Do not edit `config/source_rights.yml`, activate a provider, or fetch data.
- Do not change price readiness or canonical quarterly Revenue/EPS packets in this slice.
- Preserve candidate-only states and research-mode compatibility.
- Do not run `make readiness` or generate repository artifacts.

### Task 1: Prove the source-level permission leak

**Files:**
- Modify: `tests/test_focused_cohort_coverage.py`
- Modify: `src/focused_cohort_coverage.py`

1. Add a checked-registry regression showing an SEC Companyfacts row with margin, FCF, cash, debt, shares, and filing date keeps only shares and filing date commercially usable.
2. Add injected-registry tests showing one exact supported field cannot unlock sibling fields and cash/debt remain independent.
3. Run `python3 -m pytest tests/test_focused_cohort_coverage.py -q` and confirm the old source-level behavior fails.
4. Add a frozen row review result containing technical availability, provenance completeness, rights state, required fields, missing fields, and combined usability.
5. Use `review_commercial_field_scope` for exact populated fields and make commercial evidence text name independent blockers.
6. Rerun the focused file and confirm green.

### Task 2: Enforce earnings, consensus, and trusted-peer scope

**Files:**
- Modify: `tests/test_focused_cohort_coverage.py`
- Modify: `src/focused_cohort_coverage.py`

1. Add failing tests for missing `earnings_dates` scope, Revenue/EPS consensus scope independence, blocked date-only consensus, and a trusted row missing `trusted_peers` scope.
2. Review earnings dates with exact `earnings_dates` scope.
3. Require consensus values and review every populated metric with `revenue_consensus` or `eps_consensus`; retain cutoff/fiscal-period/provenance checks.
4. Require every trusted row to pass `trusted_peers`; leave candidate rows untouched.
5. Run `python3 -m pytest tests/test_focused_cohort_coverage.py -q` and confirm green.

### Task 3: Preserve dashboard and documentation contracts

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/METHODOLOGY.md`
- Modify: `docs/PROVENANCE_CONTRACT.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Test: `tests/test_dashboard_research_mode.py` or the narrow existing dashboard contract test if an assertion is needed

1. Add a dashboard contract assertion that field-scope blockers stay in Advanced cohort evidence and do not alter the primary research answer.
2. Document the saved-row lane mapping and truthful remaining Priority 2 gaps: prices and canonical quarterly Revenue/EPS.
3. Run focused cohort/dashboard/docs tests, public wording, and commercial beta checks.

### Task 4: Verify and publish the coherent slice

1. Run `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider tests -q`.
2. Run dashboard, six-route Personal Research render, public wording/check, commercial beta/release, pilot readiness, diff hygiene, and whitespace gates.
3. Confirm zero generated CSV/JSON/report/sample-report/screenshot/timing/canonical-data changes.
4. Stage exact implementation, tests, ROADMAP, methodology, provenance, continuation prompt, design, and plan paths only.
5. Run staged hygiene and cached whitespace checks, commit, and push only the feature branch.
6. Update draft PR #113 with red-green evidence and remaining audit boundaries; verify current-head hosted CI and keep the PR draft.
