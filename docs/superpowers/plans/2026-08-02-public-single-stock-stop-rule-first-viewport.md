# Public Single-Stock Stop Rule First-Viewport Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the complete research-only stop rule inside the first `390x844` Public Single-Stock Report viewport without changing copy, reading order, desktop layout, data, readiness, or quant behavior.

**Architecture:** Reuse the current Public shell and selected-ticker markup. Add two selector-local declarations inside the existing `max-width: 640px` media query, protect the rendered CSS contract with a strict red-green test, and use direct browser geometry as the authoritative layout proof.

**Tech Stack:** Python 3.12, Streamlit, HTML/CSS, pytest, the existing dashboard and browser gates, GitHub CLI.

## Execution Evidence Adjustment

The initial two-declaration implementation did not satisfy the authoritative
live criterion: at `390x844`, the complete stop rule still ended at
`871.90625px`. Execution stopped and remeasured as required. The remaining
cause was the phone summary inheriting the desktop `margin-top: 0.78rem`, not a
data, markup, or action-order change. A second red-green and mutation cycle
added `margin-top: -1rem` to the existing phone `.public-ticker-summary` rule.
Final live evidence reports `stop_bottom=843.4296875`,
`stop_clearance=0.5703125`, and a positive 2.2265625px gap after the trust
strip. This addendum supersedes steps that describe the two declarations as
the complete implementation; all other constraints and release steps remain
unchanged.

## Global Constraints

- Preserve the order `Selected ticker -> Use now -> Still withheld -> Open Data Health -> explanation -> stop rule`.
- Preserve every visible word, state, color, border, and the `Open Data Health` target height of at least 44 pixels.
- Change phone CSS only; the `1280x720` four-column Public summary stays unchanged.
- Do not change readiness, source rights, evidence, forecasts, probabilities, valuation, catalysts, outcomes, backtests, calibration, routes, or Python interfaces.
- Do not run `make readiness`, broad refreshes, canonical-data writers, report generators, sample-report generators, screenshot writers, or timing writers.
- Preserve the existing 18 generated CSV/report/output modifications exactly, unstaged and hash-verified.
- Never use `git add -A`; stage only exact intentional paths.
- Keep PR #113 open and draft; do not merge or deploy.

---

### Task 1: Test And Repair The Phone Action Spacing

**Files:**
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `src/dashboard.py`

**Interfaces:**
- Consumes: `dashboard.render_public_shell_mode_styles()`, the emitted Public CSS, `.public-ticker-action`, and `.public-ticker-action small`.
- Produces: phone-only summary `margin-top: -1rem`, action `gap: 0.2rem`, and stop-rule `margin-top: 0` declarations; no Python API or markup change.
- Produces for Task 2: `phone_measurement` with `viewport_width`, `viewport_height`, `scroll_width`, `action_height`, `stop_top`, `stop_bottom`, `stop_clearance`, `dom_order`, `advanced_open_count`, and `traceback_visible`; `desktop_measurement` with `summary_columns`, `action_height`, `scroll_width`, and `traceback_visible`.

- [ ] **Step 1: Add the failing rendered-CSS contract**

Add this test next to `test_public_single_stock_phone_keeps_evidence_handoff_in_first_view`:

```python
def test_public_single_stock_phone_compacts_stop_rule_spacing(monkeypatch):
    rendered: list[str] = []
    monkeypatch.setattr(
        dashboard.st,
        "markdown",
        lambda body, **_kwargs: rendered.append(str(body)),
    )

    dashboard.render_public_shell_mode_styles()

    assert len(rendered) == 1
    style = rendered[0]
    mobile_start = style.index("@media (max-width: 640px)")
    mobile_end = style.index("</style>", mobile_start)
    mobile_css = style[mobile_start:mobile_end]

    assert ".public-ticker-summary {" in mobile_css
    summary_start = mobile_css.index(".public-ticker-summary {")
    summary_rule = mobile_css[summary_start : mobile_css.index("}", summary_start)]
    assert "margin-top: -1rem;" in summary_rule

    assert ".public-ticker-action {" in mobile_css
    action_start = mobile_css.index(".public-ticker-action {")
    action_rule = mobile_css[action_start : mobile_css.index("}", action_start)]
    assert "gap: 0.2rem;" in action_rule

    assert ".public-ticker-action small {" in mobile_css
    stop_start = mobile_css.index(".public-ticker-action small {")
    stop_rule = mobile_css[stop_start : mobile_css.index("}", stop_start)]
    assert "margin-top: 0;" in stop_rule
```

This test catches either phone override being removed. It captures the actual CSS emitted by the production renderer instead of reading the source file directly.

- [ ] **Step 2: Run the new test and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_dashboard_helpers.py::test_public_single_stock_phone_compacts_stop_rule_spacing -q
```

Expected: one assertion failure at `assert ".public-ticker-action {" in mobile_css`, because the current phone block has only the primary-action ordering override and inherits the desktop action gap and stop-rule margin.

- [ ] **Step 3: Add the minimal phone-only implementation**

Inside the existing `@media (max-width: 640px)` block in `render_public_shell_mode_styles()`, add the measured summary override to the existing summary rule and place the action overrides immediately before `.public-ticker-action .public-primary-action`:

```css
.public-ticker-summary {
  margin-top: -1rem;
}
.public-ticker-action {
  gap: 0.2rem;
}
.public-ticker-action small {
  margin-top: 0;
}
```

Do not change the base action rule, existing summary padding, markup, copy, or the desktop media-independent CSS.

- [ ] **Step 4: Run the focused GREEN matrix**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_dashboard_helpers.py::test_public_single_stock_phone_compacts_stop_rule_spacing \
  tests/test_dashboard_helpers.py::test_public_single_stock_phone_keeps_evidence_handoff_in_first_view \
  tests/test_dashboard_helpers.py::test_public_workflow_controls_reserve_accessible_touch_targets \
  tests/test_dashboard_helpers.py::test_single_stock_public_summary_keeps_the_data_health_handoff_visible \
  tests/test_dashboard_helpers.py::test_fast_public_single_stock_summary_keeps_answer_order_and_data_health_handoff \
  tests/test_dashboard_helpers.py::test_public_shell_collapses_sidebar_but_preserves_only_skip_wrapper -q
```

Expected: six passed tests and no new warnings or generated files.

- [ ] **Step 5: Run the mutation check**

Temporarily revert each new declaration one at a time in the working tree and rerun only the new test. Confirm removing summary `margin-top: -1rem`, action `gap: 0.2rem`, or stop-rule `margin-top: 0` fails its matching assertion. Restore all three declarations and rerun the test to green before continuing.

- [ ] **Step 6: Verify live phone and desktop geometry without writing an artifact**

Use the in-app browser if it supports the required viewport; otherwise use the already approved Chrome fallback. Open:

```text
http://127.0.0.1:8501/?mode=public&page=single-stock-report&ticker=NVDA&open=1
```

At `390x844`, wait for the stable selected answer and evaluate:

```javascript
(() => {
  const summary = document.querySelector('.public-ticker-summary');
  const action = document.querySelector('.public-primary-action');
  const stop = document.querySelector('.public-ticker-action small');
  const labels = [...summary.querySelectorAll('span,strong,a,p,small')]
    .map((node) => node.textContent.trim())
    .filter(Boolean);
  const actionRect = action.getBoundingClientRect();
  const stopRect = stop.getBoundingClientRect();
  return {
    viewport_width: innerWidth,
    viewport_height: innerHeight,
    scroll_width: document.documentElement.scrollWidth,
    action_height: actionRect.height,
    stop_top: stopRect.top,
    stop_bottom: stopRect.bottom,
    stop_clearance: innerHeight - stopRect.bottom,
    dom_order: labels,
    advanced_open_count: document.querySelectorAll('details[open]').length,
    traceback_visible: document.body.innerText.includes('Traceback'),
  };
})()
```

Require `viewport_width=390`, `viewport_height=844`, `scroll_width<=390`, `action_height>=44`, `stop_bottom<=844`, `stop_clearance>=0`, zero open Advanced details, no traceback, and the approved content order. Inspect the live screen, but do not write a screenshot file.

At `1280x720`, evaluate the same route and require no overflow or traceback, `action_height>=44`, and four computed tracks from `getComputedStyle(summary).gridTemplateColumns`. Record the exact returned values as `phone_measurement` and `desktop_measurement` for Task 2.

- [ ] **Step 7: Verify protected artifacts and commit the product repair**

Run:

```bash
shasum -a 256 -c \
  .superpowers/sdd/2026-08-01-portable-html-action-policy-repair/protected-artifacts.sha256
git diff --check
git add -- src/dashboard.py tests/test_dashboard_helpers.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Keep mobile stop rule in first viewport"
```

Expected: all 18 protected hashes report `OK`; only the two named product/test files are staged; staged hygiene passes.

---

### Task 2: Reconcile Current QA, Roadmap, And Continuation Truth

**Files:**
- Modify: `docs/DASHBOARD_QA.md`
- Modify: `ROADMAP.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`

**Interfaces:**
- Consumes: `phone_measurement`, `desktop_measurement`, and the exact Task 1 commit from `git rev-parse HEAD`.
- Produces: current, non-duplicative release evidence that supersedes the stale first-viewport claim without claiming data freshness, hosted behavior, accessibility conformance, external review, demand, or market validation.

- [ ] **Step 1: Update the dashboard QA record**

In `docs/DASHBOARD_QA.md`, extend the `2026-07-21 Public Desktop And Phone Workflow Review` section with a dated `2026-08-02` regression note stating:

```text
A current-head 2026-08-02 recapture found a narrower follow-up regression: the
44px handoff still fit, but the complete research-only stop rule began 13.9px
below the 390x844 first viewport. The phone action block inherited both its
desktop grid gap and stop-rule top margin. The phone-only correction removes
that duplicate spacing without changing copy or order. Fresh live geometry at
the implementation commit recorded the exact stop_bottom, stop_clearance,
action_height, and scroll_width values returned in Task 1. Desktop retained
four summary columns.
```

Insert the four exact numeric values returned in Task 1 rather than copying the
field names literally. State that no screenshot file was created and that the
evidence remains local product-layout evidence only.

- [ ] **Step 2: Update ROADMAP current truth**

In the Public visitor-flow paragraph near the top of `ROADMAP.md`, add the verified first-viewport stop-rule result and exact Task 1 implementation commit. Preserve the existing statement that phone evidence does not prove market validation, readiness, source rights, hosted behavior, accessibility conformance, reviewer validation, demand, or product-market fit.

Do not mark Priority 7 or any external gate complete.

- [ ] **Step 3: Update the continuation contract once**

In the existing `Public mobile workflow audit` entry in `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`, append the exact Task 1 commit and Task 1 phone measurements. State that the complete stop rule, not only the action, is inside the first `390x844` viewport; the implementation changes only phone spacing and no research state.

Do not create a second mobile-audit history section and do not change the Priority 9 calibration boundary.

- [ ] **Step 4: Record the local review outcome without staging it**

If `/tmp/stock-command-center-public-ux-review/public-ux-review-notes.md` still contains the matching ten-row current audit, run:

```bash
python3 -m src.public_ux_review_checklist --record-note \
  --page "Single-Stock Report" \
  --viewport phone \
  --first-answer-visible yes \
  --primary-next-action-visible yes \
  --advanced-details-collapsed yes \
  --classification resolved_post_fix \
  --note-text "Fresh 390x844 recapture keeps the complete research-only stop rule inside the first viewport; exact geometry is recorded in docs/DASHBOARD_QA.md."
make public-ux-review-notes-check
```

Require `pending_rows: 0`, `share_review_gate: share_review_ready`, and separate raw counts for `resolved` and `resolved_post_fix`. The `/tmp` note remains local review evidence and must not be staged. If the matching ten-row audit is absent, classify the note as unavailable once and rely on the fresh direct geometry plus repository gates; do not fabricate or rebuild review rows.

- [ ] **Step 5: Run focused documentation and Public workflow tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_dashboard_helpers.py \
  tests/test_public_ux_review_checklist.py \
  tests/test_project_status.py \
  tests/test_public_v1_release_docs.py \
  tests/test_browser_qa_evidence.py \
  tests/test_dashboard_render_smoke.py -q
make research-dashboard-render-smoke
```

Expected: all selected tests and the Research render smoke pass without writing repository artifacts.

- [ ] **Step 6: Stage and commit exact documentation paths**

Run:

```bash
git diff --check
git add -- \
  docs/DASHBOARD_QA.md \
  ROADMAP.md \
  docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md
make staged-hygiene-check
git diff --cached --check
git commit -m "Record mobile stop-rule viewport evidence"
```

Expected: only the three named documentation files are staged; no generated or `/tmp` path enters the commit.

---

### Task 3: Full Verification, Push, PR Update, And Exact-Head CI

**Files:**
- Verify only; do not create generated repository artifacts.
- External update: draft PR #113 status comment only.

**Interfaces:**
- Consumes: the two Task 1–2 commits, the design commit `da757f466de8df29936b045d723a158a982746e9`, and the protected-artifact manifest.
- Produces: a locally verified and GitHub-synchronized exact head while keeping PR #113 open and draft.

- [ ] **Step 1: Run the full local verification matrix**

Run in this order:

```bash
python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make research-accessibility-browser-check TIMEOUT_SECONDS=90
make public-wording-check
make commercial-beta-check
make commercial-beta-release-check
make public-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
shasum -a 256 -c \
  .superpowers/sdd/2026-08-01-portable-html-action-policy-repair/protected-artifacts.sha256
```

Do not run `commercial-beta-performance-gate`; it is a timing writer and is outside this slice. `commercial-beta-release-check` uses the read-only performance contract, not the writer.

- [ ] **Step 2: Verify branch-range and staging hygiene**

Run:

```bash
BASE_SHA=$(git merge-base origin/main HEAD)
HEAD_SHA=$(git rev-parse HEAD)
make pr-range-hygiene-check BASE_SHA="$BASE_SHA" HEAD_SHA="$HEAD_SHA"
make staged-hygiene-check
git status --short --branch
```

Require an empty index, only the same 18 protected generated modifications, and no unexpected product, report, screenshot, timing, canonical-data, or manual-review path.

- [ ] **Step 3: Push only the approved branch**

Run:

```bash
git push origin codex/personal-research-mode-mvp
```

Then require:

```bash
git rev-list --left-right --count HEAD...origin/codex/personal-research-mode-mvp
```

Expected: `0 0`.

- [ ] **Step 4: Update draft PR #113**

Add one concise PR comment containing:

- exact pushed HEAD;
- phone stop-rule bottom, clearance, action height, and overflow result;
- focused and full test counts;
- required gate results;
- confirmation that the same 18 generated paths remain excluded;
- the unchanged external gates and next Priority 9 design candidate.

After copying the exact verified values into the four shell variables, post the
comment with:

```bash
HEAD_SHA=$(git rev-parse HEAD)
STOP_BOTTOM='exact verified numeric value'
STOP_CLEARANCE='exact verified numeric value'
ACTION_HEIGHT='exact verified numeric value'
FULL_TEST_RESULT='exact pytest passed count'
gh pr comment 113 --body "Mobile first-viewport repair verified at exact HEAD ${HEAD_SHA}.

- 390x844 stop rule: bottom=${STOP_BOTTOM}px; clearance=${STOP_CLEARANCE}px
- Open Data Health target height: ${ACTION_HEIGHT}px; no horizontal overflow or traceback
- Full tests: ${FULL_TEST_RESULT}; required dashboard, render, accessibility, Public, beta, pilot, and hygiene gates passed
- Generated artifacts: the same 18 protected CSV/report/output paths remain unstaged and excluded
- External gates remain incomplete; next local design candidate is the read-only Priority 9 calibration evidence-bundle preview

PR #113 remains draft. This is local engineering evidence only; it does not prove data freshness, source rights, hosted behavior, human accessibility, independent validation, market fit, or calibrated probability."
```

The quoted assignments must contain the exact current-run values; do not post
the descriptive strings shown above.

Verify with:

```bash
gh pr view 113 --json state,isDraft,mergeable,headRefOid,url
```

Require `state=OPEN`, `isDraft=true`, and `headRefOid` equal to local `HEAD`.

- [ ] **Step 5: Require exact-head GitHub Actions success**

Find the newest `Commercial Research Beta` run whose `headSha` equals local `HEAD`, wait for completion, and inspect its conclusion:

```bash
HEAD_SHA=$(git rev-parse HEAD)
RUN_ID=$(gh run list --workflow "Commercial Research Beta" \
  --branch codex/personal-research-mode-mvp --limit 10 \
  --json databaseId,headSha,status,conclusion,url \
  --jq ".[] | select(.headSha == \"${HEAD_SHA}\") | .databaseId" | head -1)
test -n "$RUN_ID"
gh run watch "$RUN_ID" --exit-status
gh run view "$RUN_ID" --json headSha,status,conclusion,url,jobs
```

Require `status=completed`, `conclusion=success`, and exact SHA equality before reporting synchronization.

- [ ] **Step 6: Final completion audit and next-stage routing**

Re-read the approved design and check every acceptance criterion against direct evidence. Report the branch safe for code review only if all criteria pass. Keep merge, public deployment, hosted beta, independent accessibility, external source, independent-user, and probability-calibration gates incomplete.

The exact next design lane is the read-only, no-write Priority 9 calibration evidence-bundle preview over operator-supplied immutable evidence. It must never activate readiness, append evidence, or expose a probability, and it requires a separate approved design before implementation.
