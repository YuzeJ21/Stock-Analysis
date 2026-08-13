# Public Packaging Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the public README, LinkedIn Featured package, curated visual, and Workbench performance evidence tell one accurate answer-first Personal Research story.

**Architecture:** Reuse the existing four-step Personal Research workflow and read-only public packaging checks. Tighten documentation and test contracts, bind Workbench first-useful timing to the rendered `Use now` answer, and replace the stale count-heavy social image with one reviewed real-app Workbench capture. No research data, forecasts, readiness state, or routing behavior changes.

**Tech Stack:** Markdown, Python 3.12, pytest, Make, Streamlit, in-app browser QA, GitHub draft PR.

## Global Constraints

- Research-only; no investment advice, trading, orders, or price prediction.
- Do not fabricate research, readiness, source, rights, validation, hosting, or market evidence.
- Generated research CSV, JSON, report, sample-report, screenshot, timing, canonical-data, and readiness churn remains excluded.
- The one intentional `1200x627` LinkedIn thumbnail is reviewed before it replaces the committed curated asset.
- Stage exact files only; never use `git add -A`.
- Keep PR #113 draft; do not merge or deploy.

---

### Task 1: Red Tests for the Public Story and Evidence Contracts

**Files:**
- Modify: `tests/test_public_v1_release_docs.py`
- Modify: `tests/test_public_performance_gate.py`
- Modify: `tests/test_browser_qa_evidence.py`

- [ ] Add contracts requiring one README reviewer entry point, the four-step Personal Research workflow as primary, and the five-page Public demo as secondary.
- [ ] Add LinkedIn contracts for the evidence-first title, default-branch/draft-preview link boundary, Workbench visual, and no stale readiness-count guidance.
- [ ] Require `Use now` as the Company Workbench first-useful performance marker.
- [ ] Require the browser-QA asset contract to describe a `1200x627` Company Workbench answer-first visual and its visible evidence markers.
- [ ] Run the focused tests and confirm they fail only because the old packaging contracts remain.

---

### Task 2: Reconcile README, LinkedIn, Share Check, and Performance Marker

**Files:**
- Modify: `README.md`
- Modify: `docs/LINKEDIN_PROJECT_BRIEF.md`
- Modify: `docs/PUBLIC_RELEASE_CHECKLIST.md`
- Modify: `Makefile` or the existing LinkedIn share-check source located during implementation
- Modify: `src/public_performance_gate.py`
- Modify: `src/browser_qa_evidence.py`

- [ ] Consolidate the README opening into one `External Reviewer Start Here` section.
- [ ] Make Research Desk -> Discover -> Company Workbench -> Monitor the primary product path and keep the controlled five-page Public demo secondary.
- [ ] Replace LinkedIn title, description, visual guidance, and link guidance with maturity-accurate copy.
- [ ] Update the read-only share check to print the same title, link boundary, visual rule, and research-only stop rules.
- [ ] Bind Workbench first-useful timing to `Use now`, retaining route identity as a full-settle marker.
- [ ] Update the browser-QA asset record to the Workbench answer-first visual.
- [ ] Run focused tests and confirm they pass.

---

### Task 3: Capture and Review the Curated Workbench Thumbnail

**Files:**
- Modify: `docs/assets/linkedin-public-dashboard.png`

- [ ] Open the current Company Workbench route for one selected ticker and wait for the final answer state.
- [ ] Capture an intentional `1200x627` frame showing Company Workbench, `Use now`, `Still withheld`, Data Health handoff, stop condition, and the research-only boundary.
- [ ] Exclude numerical readiness/source-date claims, loading states, errors, operator controls, raw tables, and generated artwork.
- [ ] Inspect the candidate beside the current app reference, verify readable composition, then replace the curated asset.
- [ ] Verify exact pixel dimensions and run the focused asset/browser-QA contracts.

---

### Task 4: Record Verified Truth and Complete Release Gates

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: other narrowly relevant QA documentation only if an existing contract requires it

- [ ] Record the packaging slice without claiming new research readiness, hosting, reviewer, source-rights, consensus, calibration, or market validation evidence.
- [ ] Run focused tests, full pytest, dashboard and research render smokes, public wording/checks, LinkedIn share check, browser-QA evidence, public and Commercial Research performance gates, Commercial Research release check, pilot readiness, PR-range/diff/staged hygiene, and whitespace checks.
- [ ] Confirm generated research churn remains unstaged and the intentional curated thumbnail is the only staged PNG.
- [ ] Commit the coherent verified implementation, push only `codex/personal-research-mode-mvp`, and update PR #113 with the slice and verification evidence.
- [ ] Keep PR #113 open and draft, then require exact-head CI success before handoff.
