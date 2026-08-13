# Commercial Beta Performance Sampling Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Commercial Research shell and first-useful performance evidence category-correct by independently measuring and enforcing warm p90 and cold maximum at the unchanged one-second and three-second thresholds.

**Architecture:** Keep the existing browser runner and raw samples. Partition shell and first-useful timings by `run_kind` in the summary, then make the evaluator enforce all category-specific fields while preserving existing sample-count and full-settle rules.

**Tech Stack:** Python 3.12, pytest, Playwright, Streamlit, Make.

## Global Constraints

- Keep `shell_seconds = 1.0` and `first_useful_seconds = 3.0`; do not weaken any threshold.
- Do not add retries, fastest-run selection, outlier deletion, or discarded required samples.
- Do not change route markers, readiness, research calculations, or source-rights behavior.
- Keep generated CSV, JSON, report, sample-report, screenshot, timing, canonical-data, and manual-review churn unstaged.
- Stage exact paths only; never use `git add -A`.
- Keep PR #113 open and draft; do not merge or deploy.

---

### Task 1: Separate and enforce first-useful evidence

**Files:**
- Modify: `src/public_performance_gate.py`
- Test: `tests/test_public_performance_gate.py`

**Interfaces:**
- Consumes: `RouteTimingSample`, `_timing_values()`, `nearest_rank_percentile()`, `PerformanceThresholds.first_useful_seconds`.
- Produces: summary fields `warm_shell_p90_seconds: float | None`, `cold_shell_max_seconds: float | None`, `warm_first_useful_p90_seconds: float | None`, and `cold_first_useful_max_seconds: float | None` consumed by `evaluate_performance_gate()` and the JSON payload.

- [x] **Step 1: Write the failing aggregation and evaluation test**

Add one test with one cold shell value of `1.1` seconds, one cold first-useful value of `3.1` seconds, and five warm values below both limits. Assert the summary exposes `warm_shell_p90_seconds == 0.3`, `cold_shell_max_seconds == 1.1`, `warm_first_useful_p90_seconds == 1.5`, and `cold_first_useful_max_seconds == 3.1`, with neither ambiguous combined field. Assert the unchanged thresholds fail specifically with `cold shell max 1.100s exceeds 1.000s` and `cold first-useful max 3.100s exceeds 3.000s`.

- [x] **Step 2: Run the focused test and confirm the red state**

Run `python3 -m pytest tests/test_public_performance_gate.py -q`.

Expected: fail because the two category-specific summary fields do not yet exist.

- [x] **Step 3: Implement the minimal category split**

In `summarize_route_timings()`, collect warm and cold shell and first-useful values independently. Emit nearest-rank p90 for warm values and maximum for cold values. In `evaluate_performance_gate()`, replace both combined checks with independent warm-p90 and cold-max checks using the existing shell and first-useful thresholds.

- [x] **Step 4: Run focused tests green**

Run `python3 -m pytest tests/test_public_performance_gate.py -q`.

Expected: all focused tests pass.

- [x] **Step 5: Run a controlled browser performance result**

Run `make commercial-beta-performance-gate TIMEOUT_SECONDS=90` once from the verified worktree. Inspect all category-specific failures. Do not rerun an unchanged failure.

Expected: the result truthfully passes or identifies a reproducible warm or cold category for later optimization; the temporary JSON remains outside the repository.

Verified result: commit `6328c8cea` recorded 48 successful category-separated samples with zero failures on local Chrome. The temporary JSON stayed under `/tmp` and out of Git.

### Task 2: Reconcile documentation and release evidence

**Files:**
- Modify: `docs/PERFORMANCE_RELEASE_GATE.md`
- Modify: `ROADMAP.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Test: `tests/test_public_performance_gate.py`

**Interfaces:**
- Consumes: the Task 1 metric names and current controlled-browser verdict.
- Produces: one unambiguous operator contract and truthful roadmap/continuation state.

- [x] **Step 1: Protect documentation terminology**

Update the existing documentation-contract test to require `warm first-useful p90`, `cold first-useful max`, and the unchanged three-second threshold in `docs/PERFORMANCE_RELEASE_GATE.md`.

- [x] **Step 2: Run the documentation test red**

Run `python3 -m pytest tests/test_public_performance_gate.py -q`.

Expected: fail until the performance document uses the new terms.

- [x] **Step 3: Update current truth**

Document the category split, the controlled-browser result, and its exact limits in `docs/PERFORMANCE_RELEASE_GATE.md`. Update `ROADMAP.md` and the continuation contract with the verified performance status. Preserve all external data, reviewer, hosted, calibration, and operating blockers.

- [x] **Step 4: Run complete verification**

Run focused tests, `python3 -m pytest tests -q`, dashboard and research render checks, public wording and package checks, commercial-beta performance/release checks, pilot readiness, accessibility checks, `make diff-hygiene-summary`, and `git diff --check`.

Expected: all applicable local gates pass, or a category-specific product performance failure remains explicitly open without retry loops.

Verified result: the focused contract, 4,474-test full suite, dashboard startup and render checks, research render checks, public wording/package checks, category-separated performance gate, aggregate Commercial Research Beta release check, pilot classification, six-route/two-viewport accessibility browser gate, state harness, diff hygiene, and whitespace checks passed. Exactly 18 generated differences remained excluded.

- [x] **Step 5: Stage exact paths, verify hygiene, commit, and push**

Stage only the intentional source, test, specification, plan, roadmap, and documentation paths. Run `make staged-hygiene-check` and `git diff --cached --check`. Commit one coherent slice, push only `codex/personal-research-mode-mvp`, update draft PR #113, and require exact-head CI.

Expected: the branch is aligned with origin, PR #113 remains draft, exact-head CI passes, and all 18 pre-existing generated differences remain unstaged.

Verified result: exact staging and hygiene passed, commit `6328c8cea` was pushed only to `codex/personal-research-mode-mvp`, PR #113 remained open/draft/mergeable, exact-head GitHub Actions run `30634355602` passed, and all 18 generated differences remained unstaged.
