# Public UX Post-Fix Outcome Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a verified `resolved_post_fix` public UX audit row satisfy the local share-review gate while preserving separate audit counts and fail-closed handling for every incomplete or unknown outcome.

**Architecture:** `src/public_ux_review_checklist.py` remains the owner of the public UX outcome vocabulary and status decision. It will publish an explicit successful-outcome set used by both the checklist parser and `src/project_status.py`, avoiding duplicated strings and unsafe prefix matching. Tests first prove the current false-limited state and the project-status undercount, then documentation records the corrected local-only maturity claim.

**Tech Stack:** Python 3, pytest, Make, Markdown, GitHub Actions.

## Global Constraints

- Research-only; this slice cannot change research conclusions, readiness, data, forecasts, probabilities, or recommendations.
- `resolved` and `resolved_post_fix` are the only successful public UX outcomes.
- Raw classification counts remain separate.
- `pending`, `intentionally_deferred`, `environment_limited`, `skipped`, `blocked_with_evidence`, and unknown outcomes remain fail closed.
- Do not edit or stage `/tmp` review notes or screenshots.
- Do not run `make readiness` or generate/stage CSV, JSON, report, sample-report, screenshot, timing, readiness, canonical-data, or manual-review churn.
- Stage exact files only; never use `git add -A`.
- Keep PR #113 open and draft; do not merge or deploy.

---

### Task 1: Prove the post-fix classification defect

**Files:**
- Modify: `tests/test_public_ux_review_checklist.py`
- Modify: `tests/test_project_status.py`

**Interfaces:**
- Consumes: `public_ux_review_notes_status(notes_path)` and `project_status._public_ux_stage_from_status(status)`.
- Produces: regression coverage requiring an explicit successful post-fix outcome and a combined resolved-row count.

- [ ] **Step 1: Add the failing checklist regression test**

Add a test beside `test_public_ux_review_notes_status_marks_share_review_ready_when_all_rows_resolved` that writes all ten review rows, uses `resolved_post_fix` only for Single-Stock Report phone, and asserts:

```python
assert status["status"] == "review_complete"
assert status["share_review_gate"] == "share_review_ready"
assert status["pending_rows"] == 0
assert status["problem_rows"] == []
assert status["classification_counts"]["resolved"] == 9
assert status["classification_counts"]["resolved_post_fix"] == 1
```

- [ ] **Step 2: Add the failing project-status regression test**

Extend `test_project_status_stage_map_reports_completed_public_ux_review` with this status input:

```python
"classification_counts": {"resolved": 9, "resolved_post_fix": 1},
```

Keep the existing assertion that the evidence contains:

```python
"10/10 public desktop/mobile review rows resolved"
```

- [ ] **Step 3: Run the focused tests and verify the red state**

Run:

```bash
python3 -m pytest \
  tests/test_public_ux_review_checklist.py::test_public_ux_review_notes_status_marks_share_review_ready_after_verified_fix \
  tests/test_project_status.py::test_project_status_stage_map_reports_completed_public_ux_review -q
```

Expected: both tests fail for the intended reasons—the parser reports `review_limited`, and project status reports `9/10`.

- [ ] **Step 4: Confirm no production file changed during red**

Run:

```bash
git status --short
```

Expected: only the two test files and this plan are changed or committed; no data or generated artifact appears.

---

### Task 2: Implement the explicit successful-outcome contract

**Files:**
- Modify: `src/public_ux_review_checklist.py`
- Modify: `src/project_status.py`
- Test: `tests/test_public_ux_review_checklist.py`
- Test: `tests/test_project_status.py`

**Interfaces:**
- Produces: `SUCCESSFUL_REVIEW_CLASSIFICATIONS`, an immutable explicit set containing `resolved` and `resolved_post_fix`.
- Consumes: raw `classification_counts` without collapsing keys.

- [ ] **Step 1: Add the explicit vocabulary**

Near the existing public UX review constants, add:

```python
SUCCESSFUL_REVIEW_CLASSIFICATIONS = frozenset({"resolved", "resolved_post_fix"})
```

Add `resolved_post_fix` to the rendered review-log classification vocabulary, describing it as a fresh verified recapture after a fix.

- [ ] **Step 2: Use the vocabulary in problem-row classification**

Change the status loop condition from the literal two-value comparison to:

```python
if classification != "pending" and classification not in SUCCESSFUL_REVIEW_CLASSIFICATIONS:
```

Do not use prefix matching and do not modify raw classification counts.

- [ ] **Step 3: Sum successful outcomes in project status**

Import `SUCCESSFUL_REVIEW_CLASSIFICATIONS` into `src/project_status.py` and replace the literal `resolved` count with:

```python
resolved = sum(int(counts.get(classification) or 0) for classification in SUCCESSFUL_REVIEW_CLASSIFICATIONS)
```

- [ ] **Step 4: Run the red tests and verify green**

Run the exact focused command from Task 1 Step 3.

Expected: 2 passed.

- [ ] **Step 5: Run both complete focused modules**

Run:

```bash
python3 -m pytest tests/test_public_ux_review_checklist.py tests/test_project_status.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Prove unknown outcomes still fail closed**

Add or extend a checklist test to record `resolved_typo` for one completed row and assert:

```python
assert status["status"] == "review_has_deferred_or_limited_items"
assert status["share_review_gate"] == "review_limited"
assert status["problem_rows"][0]["classification"] == "resolved_typo"
```

Run the complete focused modules again and expect all tests to pass.

---

### Task 3: Record the corrected maturity state

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/DASHBOARD_QA.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`

**Interfaces:**
- Consumes: focused green evidence and the existing ten-row `/tmp` audit status.
- Produces: truthful local-only roadmap and continuation language.

- [ ] **Step 1: Verify the live local notes status without editing it**

Run:

```bash
make public-ux-review-notes-check
make project-status-check
```

Expected:

- `status: review_complete`
- `share_review_gate: share_review_ready`
- raw counts `resolved: 9, resolved_post_fix: 1`
- project status evidence `10/10 public desktop/mobile review rows resolved`

- [ ] **Step 2: Update ROADMAP.md**

Record that the ten desktop/phone rows are locally `share_review_ready`, with nine direct resolutions and one verified post-fix recapture. Preserve the boundary that this is screenshot-based local QA, not hosted, accessibility-conformance, external-reviewer, freshness, demand, or market evidence.

- [ ] **Step 3: Update docs/DASHBOARD_QA.md**

Document the explicit meaning of `resolved_post_fix`, the final 390x844 recapture, and the fail-closed treatment of unknown or incomplete labels.

- [ ] **Step 4: Update the continuation contract**

Add the implementation anchor and corrected public UX status to `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`. Keep the exact next external maturity lane as one permitted point-in-time consensus snapshot and source review.

- [ ] **Step 5: Run documentation and focused contract tests**

Run:

```bash
python3 -m pytest \
  tests/test_public_ux_review_checklist.py \
  tests/test_project_status.py \
  tests/test_launchers.py \
  tests/test_pilot_review_feedback_template.py \
  tests/test_public_v1_release_docs.py -q
```

Expected: all tests pass.

---

### Task 4: Verify, package, and synchronize the slice

**Files:**
- No planned repository modifications; stop and return to the relevant earlier task if verification exposes a slice-related defect.

**Interfaces:**
- Consumes: completed implementation and documentation.
- Produces: one clean coherent commit, synchronized draft PR, and exact-head CI evidence.

- [ ] **Step 1: Run full local verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make public-wording-check
make commercial-beta-check
make public-check
make commercial-beta-release-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
make pr-range-hygiene-check
git diff --check
```

Expected: commands exit zero. The pilot product verdict may remain truthfully blocked only because readiness is stale.

- [ ] **Step 2: Review and stage exact files**

Run `git diff --` for the two production files, two test files, and three documentation files. Stage only those exact intentional paths. Do not stage `/tmp`, data, outputs, screenshots, or generated artifacts.

- [ ] **Step 3: Verify the staged package**

Run:

```bash
make staged-hygiene-check
git diff --cached --check
```

Expected: only product/code/docs/test files; zero generated or manual-review paths.

- [ ] **Step 4: Commit and push**

Commit with:

```bash
git commit -m "Recognize verified public UX post-fix outcomes"
git push origin codex/personal-research-mode-mvp
```

- [ ] **Step 5: Update draft PR #113**

Post a concise PR update covering the root cause, explicit successful-outcome contract, raw-count preservation, fail-closed unknown labels, tests, generated-artifact exclusion, and unchanged external gates. Keep the PR draft.

- [ ] **Step 6: Verify exact-head GitHub CI and final repository state**

Wait for the Commercial Research Beta workflow on the exact pushed SHA. Require success, then verify:

```bash
git status --short --branch
git rev-list --left-right --count @{upstream}...HEAD
gh pr view 113 --json state,isDraft,mergeable,headRefOid,statusCheckRollup,url
```

Expected: clean, `0 0`, PR open/draft/mergeable, exact head, successful CI.
