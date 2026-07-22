# Legacy Research Utility Quarantine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make legacy portfolio, ranking, and action-language surfaces unmistakably operator-only compatibility utilities while preserving the supported Personal Research workflow.

**Architecture:** Add a pure navigation contract for quarantined canonical page titles, safe mode-specific route resolution, and operator display labels. Reuse the dashboard renderers only inside a shared collapsed compatibility shell. Keep all calculations and historical filenames unchanged, then lock isolation with route, source, wording, documentation, and release tests.

**Tech Stack:** Python 3.12, Streamlit, pytest, Streamlit render smoke tests, Markdown contract tests.

## Global Constraints

- Preserve Research Desk -> Discover -> Company Workbench -> Monitor as the supported workflow.
- Keep legacy calculations only for compatibility; do not promote them into current product capability.
- Do not change readiness, canonical data, forecasts, calibration, sources, or generated report schemas.
- Do not run readiness rebuilds, broad refreshes, or generated CSV/JSON/report/screenshot/timing commands.
- Never stage generated working-data churn and never use `git add -A`.
- Keep draft PR #113 draft; push only `codex/personal-research-mode-mvp`; do not merge or deploy.

---

### Task 1: Lock the quarantine and route contract

**Files:**
- Modify: `src/dashboard_navigation.py`
- Modify: `src/dashboard.py`
- Modify: `tests/test_dashboard_navigation.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`

- [ ] **Step 1: Write failing tests for the exact quarantine set, labels, and mode-specific deep-link resolution**

Assert that Public resolves every quarantined page to `Home`, Personal Research resolves it to `Research Desk`, and Operator preserves it. Assert historical aliases still parse to canonical titles.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python3 -m pytest tests/test_dashboard_navigation.py tests/test_research_mode_dashboard_contract.py -q`

- [ ] **Step 3: Implement the pure quarantine helpers and use them before route-rail selection**

Add immutable `LEGACY_RESEARCH_UTILITY_PAGES`, `legacy_research_utility_label(...)`, and `workspace_page_for_mode(...)`. Keep Streamlit out of the navigation module.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `python3 -m pytest tests/test_dashboard_navigation.py tests/test_research_mode_dashboard_contract.py -q`

---

### Task 2: Quarantine rendered legacy output

**Files:**
- Modify: `src/dashboard.py`
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`

- [ ] **Step 1: Write failing source and render-helper tests**

Require the exact boundary copy and one collapsed `Advanced: legacy compatibility output` wrapper. Prove legacy page renderers use the wrapper and do not render their detailed tables before it.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python3 -m pytest tests/test_dashboard_helpers.py tests/test_research_mode_dashboard_contract.py -q`

- [ ] **Step 3: Implement the shared legacy shell**

Render the compatibility boundary first. Move Monthly Picks details and the five quarantined output-tab branches inside the collapsed disclosure. Preserve explicit missing-output states without generating data.

- [ ] **Step 4: Add and pass isolation tests**

Prove `src/research_decision_lab.py` and the Company Workbench composition path do not import or consume `portfolio_review`, `monthly_picks`, `final_watchlist`, or legacy dashboard output frames.

---

### Task 3: Reconcile product documentation and roadmap truth

**Files:**
- Modify: `README.md`
- Modify: `PRODUCT_SPEC.md`
- Modify: `READINESS_MODEL.md`
- Modify: `ROADMAP.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: `tests/test_public_v1_release_docs.py`

- [ ] **Step 1: Write failing documentation-contract tests**

Require the supported workflow, exact legacy boundary, operator-only compatibility classification, and explicit exclusion from readiness, Decision Lab, recommendations, sizing, and transactions.

- [ ] **Step 2: Update the documents without rewriting historical evidence**

Mark Priority 1 complete only after code and direct tests pass. Set Priority 2 Stage B as the next local executable lane.

- [ ] **Step 3: Run focused documentation and action-language checks**

Run: `python3 -m pytest tests/test_public_v1_release_docs.py tests/test_public_wording.py tests/test_action_language_contract.py -q`

---

### Task 4: Verify, stage exactly, synchronize the draft PR, and require exact-head CI

- [ ] **Step 1: Run the complete verification matrix**

```bash
python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make public-wording-check
make public-check
make commercial-beta-release-check
make pilot-readiness-check TOP_N=10
make pr-range-hygiene-check
make diff-hygiene-summary
git diff --check
```

Pilot readiness may remain truthfully blocked by stale saved readiness or external evidence; it must not be regenerated in this slice.

- [ ] **Step 2: Review and stage exact intentional paths only**

Run `git diff --stat`, inspect every intentional diff, stage only the code/test/docs paths listed above, then run `make staged-hygiene-check` and `git diff --cached --check`.

- [ ] **Step 3: Commit and push the coherent slice**

Commit with `Quarantine legacy research utilities`, push only the existing feature branch, update draft PR #113 with evidence and remaining gates, keep it draft, and wait for exact-head `local-engineering-gate` success.

- [ ] **Step 4: Continue automatically**

Re-scan the ordered maturity program. Begin Priority 2 Stage B if a safe local task remains; otherwise classify its exact external unblock condition once and move to the next executable priority.
