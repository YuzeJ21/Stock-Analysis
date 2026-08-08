# Public Mobile Zero-Scroll Stop Rule Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the complete Public Home and selected NVDA Single-Stock Report research-only stop rules inside an explicitly zero-scroll `390x844` first viewport while preserving copy, 44-pixel actions, desktop layout, route behavior, and every research/data boundary.

**Architecture:** Keep the existing Public shell and route APIs unchanged. Home renders one local stop-copy fragment into mutually exclusive phone and desktop containers so semantic and visual order match each breakpoint; Single Stock changes only the existing Public phone selectors. Rendered HTML/CSS tests drive each change, and direct browser geometry is the authoritative acceptance gate.

**Tech Stack:** Python 3.12, Streamlit, HTML/CSS, pytest, Playwright/in-app browser, Make release gates, Git/GitHub CLI.

## Global Constraints

- Use `/Users/yjian070/Documents/New project/.worktrees/personal-research-mode-mvp` on `codex/personal-research-mode-mvp`; keep PR #113 open and draft.
- At `390x844`, require all of `window.scrollY == 0`, document scroll top `== 0`, body scroll top `== 0`, and Streamlit main scroll top `== 0` before accepting geometry.
- Home phone order is `primary -> phone stop -> metrics`; desktop remains primary/metrics on the first row and the desktop stop across the second row.
- Build both Home containers from one local `stop_copy` value and keep exactly one visible/in the accessibility tree at each breakpoint.
- Single Stock order remains `Selected ticker -> Use now -> Still withheld -> Open Data Health -> next-action explanation -> research-only stop rule`.
- Preserve all visible wording, state, colors, borders, routes, selected ticker, and the filled primary-action height of at least 44 pixels.
- Retain Single Stock phone `margin-top: -1rem`; do not make it more negative or consume the positive trust-strip-to-summary gap.
- Preserve desktop Home's two-column first row and Single Stock's four-column summary.
- Do not change readiness, source rights, evidence, forecast, probability, valuation, catalyst, outcome, backtest, calibration, hosted, reviewer, data, research, or quant state.
- Do not run readiness materialization, imports apply, provider refreshes, canonical-data writers, generated report commands, screenshot writers, or timing writers.
- Preserve the existing 18 generated CSV/report/output modifications exactly, unstaged and hash-verified.
- Never use `git add -A`; stage only exact intentional paths.
- Reject the implementation if either complete stop rule ends below `844px`, an action is shorter than `44px`, horizontal overflow appears, Home visual/DOM order differs, the trust-strip gap becomes negative, desktop layout changes, Advanced opens unexpectedly, or a traceback/console error appears.

## Execution Evidence Adjustment

The first direct zero-scroll Home measurement after Tasks 1-2 returned
`stop_bottom=845.203125` at `390x844`, while all four scroll offsets were zero,
the action remained exactly `44px`, one stop was visible before metrics,
`scroll_width=390`, and no browser error appeared. The initial `0.35rem`
phone stop padding therefore missed the authoritative criterion by
`1.203125px`. The already-approved selector-local stop-padding compaction is
refined to `0.3rem 0`; no negative margin, copy, font size, line height,
component order, or shared shell changes. A rendered-CSS RED/GREEN assertion
must protect the exact refined padding before final browser remeasurement.

---

### Task 1: Home Responsive Semantic Stop Placement

**Files:**
- Modify: `tests/test_dashboard_helpers.py:30233`
- Modify: `src/dashboard.py:6622-6647`
- Modify: `src/dashboard.py:6880-6960`
- Modify: `src/dashboard.py:7245-7270`

**Interfaces:**
- Consumes: `dashboard.public_home_overview_html(summary)` and `dashboard.render_public_shell_mode_styles()`.
- Produces: local `stop_copy: str`, `.public-home-stop-phone`, and `.public-home-stop-desktop` containers.
- Produces: base CSS that hides only `.public-home-stop-phone`; phone CSS that shows it, hides `.public-home-stop-desktop`, attaches it to the primary block, and restores separation before metrics.
- Produces for Task 3: observable phone DOM order `public-home-primary -> public-home-stop-phone -> public-home-metrics -> public-home-stop-desktop`, with only the first three visible.

- [ ] **Step 1: Write the failing rendered-HTML behavior test**

Add this test immediately after `test_public_home_overview_keeps_one_start_action_and_compact_readiness_snapshot`:

```python
def test_public_home_overview_exposes_breakpoint_stop_positions_from_identical_copy():
    rendered = dashboard.public_home_overview_html(
        {
            "master_universe": 3541,
            "price_ready": 3540,
            "dcf_ready": 2693,
            "peer_ready": 29,
        }
    )

    primary_index = rendered.index("class='public-home-primary'")
    phone_stop_index = rendered.index("class='public-home-stop public-home-stop-phone'")
    metrics_index = rendered.index("class='public-home-metrics'")
    desktop_stop_index = rendered.index("class='public-home-stop public-home-stop-desktop'")

    assert primary_index < phone_stop_index < metrics_index < desktop_stop_index
    assert rendered.count("No data, no conclusion.") == 2
    assert rendered.count("Missing inputs stay blocked instead of being inferred.") == 2
    assert rendered.count("Start with Stock Selector") == 1
    assert rendered.count("<dt>") == 4
```

This catches a missing phone placement, a CSS-only visual reorder, copy drift between placements, duplicated actions, or removed metrics. It exercises the real HTML returned to Streamlit.

- [ ] **Step 2: Run the Home HTML test and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_dashboard_helpers.py::test_public_home_overview_exposes_breakpoint_stop_positions_from_identical_copy -q
```

Expected: FAIL with `ValueError: substring not found` for `public-home-stop-phone`, because the current renderer has one stop container after metrics.

- [ ] **Step 3: Add the minimal Home markup implementation**

In `public_home_overview_html()`, define the shared fragment after `selector_href`:

```python
stop_copy = (
    "<strong>No data, no conclusion.</strong> "
    "Missing inputs stay blocked instead of being inferred."
)
```

Replace the one current stop container with these two interpolations, placing the phone container after `.public-home-primary` and the desktop container after `.public-home-metrics`:

```python
f"<div class='public-home-stop public-home-stop-phone'>{stop_copy}</div>"
```

```python
f"<div class='public-home-stop public-home-stop-desktop'>{stop_copy}</div>"
```

Do not change the primary block, link, metric names, metric formatting, section label, or href.

- [ ] **Step 4: Run the Home HTML test and verify GREEN**

Run the command from Step 2 again.

Expected: `1 passed` with no warning and no generated file change.

- [ ] **Step 5: Write the failing rendered-CSS breakpoint behavior test**

Add this test next to the Home HTML test:

```python
def test_public_home_stop_uses_mutually_exclusive_breakpoint_placement(monkeypatch):
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
    base_css = style[:mobile_start]
    mobile_css = style[mobile_start : style.index("</style>", mobile_start)]

    base_phone_start = base_css.index(".public-home-stop-phone {")
    base_phone_rule = base_css[base_phone_start : base_css.index("}", base_phone_start)]
    assert "display: none;" in base_phone_rule

    mobile_phone_start = mobile_css.index(".public-home-stop-phone {")
    mobile_phone_rule = mobile_css[
        mobile_phone_start : mobile_css.index("}", mobile_phone_start)
    ]
    assert "display: block;" in mobile_phone_rule
    assert "padding: 0.3rem 0;" in mobile_phone_rule

    mobile_desktop_start = mobile_css.index(".public-home-stop-desktop {")
    mobile_desktop_rule = mobile_css[
        mobile_desktop_start : mobile_css.index("}", mobile_desktop_start)
    ]
    assert "display: none;" in mobile_desktop_rule

    overview_start = mobile_css.index(".public-home-overview {")
    overview_rule = mobile_css[overview_start : mobile_css.index("}", overview_start)]
    assert "gap: 0;" in overview_rule

    metrics_start = mobile_css.index(".public-home-metrics {")
    metrics_rule = mobile_css[metrics_start : mobile_css.index("}", metrics_start)]
    assert "margin-top: 0.75rem;" in metrics_rule
```

This catches both stop placements becoming visible together, the phone stop remaining hidden, the desktop stop remaining exposed to the phone accessibility tree, or metrics losing their deliberate separation.

- [ ] **Step 6: Run the Home CSS test and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_dashboard_helpers.py::test_public_home_stop_uses_mutually_exclusive_breakpoint_placement -q
```

Expected: FAIL at the first `.public-home-stop-phone` assertion because neither breakpoint class exists in current CSS.

- [ ] **Step 7: Add the minimal Home breakpoint CSS**

Immediately after the base `.public-home-stop` rule, add:

```css
.public-home-stop-phone {
  display: none;
}
```

Inside the existing `@media (max-width: 640px)` block, replace the current Home overview and stop overrides with:

```css
.public-home-overview {
  grid-template-columns: 1fr;
  gap: 0;
  padding-top: 1rem;
}
.public-home-stop-phone {
  display: block;
  grid-column: auto;
  padding: 0.3rem 0;
  line-height: 1.25;
}
.public-home-stop-desktop {
  display: none;
}
.public-home-metrics {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-top: 0.75rem;
}
```

Keep the base `.public-home-stop { grid-column: 1 / -1; ... }` rule so desktop retains the full-width second row.

- [ ] **Step 8: Run the Home focused GREEN matrix**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_dashboard_helpers.py::test_public_home_overview_keeps_one_start_action_and_compact_readiness_snapshot \
  tests/test_dashboard_helpers.py::test_public_home_overview_exposes_breakpoint_stop_positions_from_identical_copy \
  tests/test_dashboard_helpers.py::test_public_home_stop_uses_mutually_exclusive_breakpoint_placement \
  tests/test_dashboard_helpers.py::test_public_app_shell_has_compact_mobile_rules \
  tests/test_dashboard_helpers.py::test_public_workflow_controls_reserve_accessible_touch_targets -q
```

Expected: `5 passed`; no copy, route, action-height, or shell regression.

- [ ] **Step 9: Run the Home mutation check**

Temporarily remove each of these in turn and rerun the matching new test: the phone container, the desktop container, base `display: none`, phone `display: block`, phone desktop `display: none`, zero overview gap, and metrics top margin. Confirm each removal fails the intended assertion, restore the production line, and finish with both new tests green.

- [ ] **Step 10: Commit the independently testable Home slice**

After `git diff --check`, protected-hash verification, and `make diff-hygiene-summary`, stage only:

```bash
git add src/dashboard.py tests/test_dashboard_helpers.py
git commit -m "Fix public Home mobile stop order"
```

---

### Task 2: Single-Stock Selector-Local Scheme A Compaction

**Files:**
- Modify: `tests/test_dashboard_helpers.py:30260-30320`
- Modify: `src/dashboard.py:7288-7310`

**Interfaces:**
- Consumes: emitted CSS from `dashboard.render_public_shell_mode_styles()` and existing `.public-ticker-summary` markup from `single_stock_public_summary_html()`.
- Produces: phone-only baseline-aligned ticker row, `0.2rem` summary gap, `0 0 0.25rem` summary padding, compact answer/context margins and line heights, and the existing action/stop spacing.
- Preserves: `margin-top: -1rem`, inherited `0.86rem` paragraph and `0.74rem` small-text fonts, action order, 44-pixel action, desktop grid, and all markup/copy.

- [ ] **Step 1: Replace the weak current phone CSS contract with the approved rendered behavior contract**

Update `test_public_single_stock_phone_keeps_evidence_handoff_in_first_view` so it captures emitted CSS through a monkeypatched `st.markdown` call and asserts these exact phone behaviors:

```python
def test_public_single_stock_phone_uses_selector_local_scheme_a(monkeypatch):
    rendered: list[str] = []
    monkeypatch.setattr(
        dashboard.st,
        "markdown",
        lambda body, **_kwargs: rendered.append(str(body)),
    )

    dashboard.render_public_shell_mode_styles()

    style = rendered[0]
    mobile_start = style.index("@media (max-width: 640px)")
    mobile_css = style[mobile_start : style.index("</style>", mobile_start)]

    summary_start = mobile_css.index(".public-ticker-summary {")
    summary_rule = mobile_css[summary_start : mobile_css.index("}", summary_start)]
    assert "grid-template-columns: 1fr;" in summary_rule
    assert "gap: 0.2rem;" in summary_rule
    assert "margin-top: -1rem;" in summary_rule
    assert "padding: 0 0 0.25rem;" in summary_rule

    name_start = mobile_css.index(".public-ticker-name {")
    name_rule = mobile_css[name_start : mobile_css.index("}", name_start)]
    assert "display: flex;" in name_rule
    assert "align-items: baseline;" in name_rule

    answer_p_start = mobile_css.index(".public-ticker-answer p {")
    answer_p_rule = mobile_css[answer_p_start : mobile_css.index("}", answer_p_start)]
    assert "margin-top: 0.12rem;" in answer_p_rule
    assert "line-height: 1.35;" in answer_p_rule

    answer_small_start = mobile_css.index(".public-ticker-answer small {")
    answer_small_rule = mobile_css[answer_small_start : mobile_css.index("}", answer_small_start)]
    assert "margin-top: 0.12rem;" in answer_small_rule
    assert "line-height: 1.25;" in answer_small_rule

    action_start = mobile_css.index(".public-ticker-action {")
    action_rule = mobile_css[action_start : mobile_css.index("}", action_start)]
    assert "gap: 0.2rem;" in action_rule

    action_p_start = mobile_css.index(".public-ticker-action p {")
    action_p_rule = mobile_css[action_p_start : mobile_css.index("}", action_p_start)]
    assert "line-height: 1.35;" in action_p_rule

    stop_start = mobile_css.index(".public-ticker-action small {")
    stop_rule = mobile_css[stop_start : mobile_css.index("}", stop_start)]
    assert "margin-top: 0;" in stop_rule
    assert "line-height: 1.25;" in stop_rule
```

This catches every realistic Scheme A regression in the emitted phone CSS while leaving geometry to Task 3.

- [ ] **Step 2: Run the Scheme A test and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_dashboard_helpers.py::test_public_single_stock_phone_uses_selector_local_scheme_a -q
```

Expected: FAIL because the current summary uses `gap: 0.25rem` and `padding: 0.125rem 0 0.5rem`, and no Public phone ticker flex or answer line-height overrides exist.

- [ ] **Step 3: Add the minimal phone-only Scheme A CSS**

Replace only the Public `.public-ticker-summary` phone declarations and add adjacent selector-local rules:

```css
.public-ticker-summary {
  grid-template-columns: 1fr;
  gap: 0.2rem;
  margin-top: -1rem;
  padding: 0 0 0.25rem;
}
.public-ticker-name {
  display: flex;
  align-items: baseline;
  gap: 0.35rem;
}
.public-ticker-answer p {
  margin-top: 0.12rem;
  line-height: 1.35;
}
.public-ticker-answer small {
  margin-top: 0.12rem;
  line-height: 1.25;
}
.public-ticker-action {
  gap: 0.2rem;
}
.public-ticker-action p {
  line-height: 1.35;
}
.public-ticker-action small {
  margin-top: 0;
  line-height: 1.25;
}
```

Keep `.public-ticker-action .public-primary-action { order: -1; }` and `.public-ticker-name strong { font-size: 1.3rem; }` unchanged. Do not edit `single_stock_public_summary_html()`.

- [ ] **Step 4: Run the focused Single-Stock GREEN matrix**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_dashboard_helpers.py::test_public_single_stock_phone_uses_selector_local_scheme_a \
  tests/test_dashboard_helpers.py::test_public_single_stock_phone_compacts_stop_rule_spacing \
  tests/test_dashboard_helpers.py::test_public_workflow_controls_reserve_accessible_touch_targets \
  tests/test_dashboard_helpers.py::test_single_stock_public_summary_keeps_the_data_health_handoff_visible \
  tests/test_dashboard_helpers.py::test_fast_public_single_stock_summary_keeps_answer_order_and_data_health_handoff \
  tests/test_dashboard_helpers.py::test_public_shell_collapses_sidebar_but_preserves_only_skip_wrapper -q
```

Expected: `6 passed`; all markup, route, handoff, stop-rule spacing, and 44-pixel contracts remain green.

- [ ] **Step 5: Run the Scheme A mutation check**

Temporarily restore the old gap or padding, remove the ticker flex, or remove each answer/stop line-height override one at a time. Confirm the new test fails for each mutation. Restore the approved declarations and rerun the six-test matrix to green.

- [ ] **Step 6: Commit the independently testable Single-Stock slice**

After `git diff --check`, protected-hash verification, and `make diff-hygiene-summary`, stage only:

```bash
git add src/dashboard.py tests/test_dashboard_helpers.py
git commit -m "Compact public Single Stock mobile answer"
```

---

### Task 3: Authoritative Browser Geometry And Evidence Reconciliation

**Files:**
- Modify after successful browser acceptance: `ROADMAP.md:33`
- Modify after successful browser acceptance: `docs/DASHBOARD_QA.md:263-350`
- Modify after successful browser acceptance: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md:129`
- Local-only, never stage: `/tmp/stock-command-center-public-ux-review/public-ux-review-notes.md`

**Interfaces:**
- Consumes: final Home/Single-Stock HTML/CSS from Tasks 1-2 and fresh Demo-profile browser routes.
- Produces: `home_phone`, `home_desktop`, `single_phone`, and `single_desktop` measurement records with explicit scroll offsets, geometry, DOM/visibility order, desktop grid tracks, overflow, Advanced, traceback, and console/page-error state.
- Produces: updated repository truth that replaces `blocked_with_evidence` only when direct acceptance passes; otherwise retains the blocked state and records the observed failure without further product compression.

- [ ] **Step 1: Start a fresh Demo-profile app without writing repository artifacts**

Run the existing dashboard launcher on a free loopback port and wait for a stable response. Use the feature worktree as the working directory and do not enable refresh, readiness materialization, screenshots, or performance output.

- [ ] **Step 2: Measure Home at phone and desktop sizes**

Open `/?mode=public&page=home` at `390x844`, explicitly reset the window and Streamlit main scroll positions to zero, wait for the route-owned Home answer, and evaluate:

```javascript
(() => {
  const main = document.querySelector('[data-testid="stMain"]');
  const overview = document.querySelector('.public-home-overview');
  const primary = overview.querySelector('.public-home-primary');
  const phoneStop = overview.querySelector('.public-home-stop-phone');
  const metrics = overview.querySelector('.public-home-metrics');
  const desktopStop = overview.querySelector('.public-home-stop-desktop');
  const action = overview.querySelector('.public-primary-action');
  const rect = (node) => ({
    top: node.getBoundingClientRect().top,
    bottom: node.getBoundingClientRect().bottom,
    height: node.getBoundingClientRect().height,
  });
  return {
    viewport: [innerWidth, innerHeight],
    scroll_offsets: [
      window.scrollY,
      document.documentElement.scrollTop,
      document.body.scrollTop,
      main.scrollTop,
    ],
    scroll_width: document.documentElement.scrollWidth,
    child_classes: [...overview.children].map((node) => node.className),
    visible_stops: [phoneStop, desktopStop].filter(
      (node) => getComputedStyle(node).display !== 'none'
    ).length,
    primary: rect(primary),
    action: rect(action),
    stop: rect(phoneStop),
    metrics: rect(metrics),
    traceback: document.body.innerText.includes('Traceback'),
    advanced_open_count: document.querySelectorAll('details[open]').length,
  };
})()
```

Require `[390,844]`, four zero scroll offsets, `scroll_width <= 390`, one visible stop, phone source/visual order before metrics, action height `>= 44`, stop bottom `<= 844`, metrics top after stop bottom, zero unexpected Advanced details, no traceback, and no console/page error.

Repeat at `1280x720`; require only the desktop stop visible, the Home grid computes two columns, primary and metrics share the first row, desktop stop follows across the second row, action height `>=44`, no overflow, and no runtime error.

- [ ] **Step 3: Measure Single Stock at phone and desktop sizes**

Open `/?mode=public&page=single-stock-report&ticker=NVDA&open=1` at `390x844`, explicitly reset all four scroll offsets to zero, wait for the selected NVDA answer, and evaluate:

```javascript
(() => {
  const main = document.querySelector('[data-testid="stMain"]');
  const trust = document.querySelector('.profile-trust-strip');
  const summary = document.querySelector('.public-ticker-summary');
  const action = summary.querySelector('.public-primary-action');
  const stop = summary.querySelector('.public-ticker-action small');
  const rect = (node) => ({
    top: node.getBoundingClientRect().top,
    bottom: node.getBoundingClientRect().bottom,
    height: node.getBoundingClientRect().height,
  });
  return {
    viewport: [innerWidth, innerHeight],
    scroll_offsets: [
      window.scrollY,
      document.documentElement.scrollTop,
      document.body.scrollTop,
      main.scrollTop,
    ],
    scroll_width: document.documentElement.scrollWidth,
    trust: rect(trust),
    summary: rect(summary),
    trust_gap: summary.getBoundingClientRect().top - trust.getBoundingClientRect().bottom,
    action: rect(action),
    stop: rect(stop),
    labels: [...summary.querySelectorAll('span,strong,a,p,small')]
      .map((node) => node.textContent.trim())
      .filter(Boolean),
    advanced_open_count: document.querySelectorAll('details[open]').length,
    traceback: document.body.innerText.includes('Traceback'),
  };
})()
```

Require `[390,844]`, four zero scroll offsets, `scroll_width <= 390`, `trust_gap >= 0`, action height `>=44`, stop bottom `<=844`, the complete approved content order/copy, zero unexpected Advanced details, no traceback, and no console/page error.

Repeat at `1280x720`; require four computed summary grid tracks, action height `>=44`, no overlap, no overflow, and no runtime error.

- [ ] **Step 4: Follow the fail-closed browser decision**

If any phone stop bottom exceeds `844`, Home has zero/two visible stops, a scroll offset is nonzero, the trust gap is negative, an action is shorter than `44`, desktop layout changes, or an error/overflow appears: stop product edits, retain or restore `blocked_with_evidence`, record the exact failed measurement locally, and return to design review rather than adding a more negative margin or removing content.

If all four measurement records pass, update the three tracked documents to state the exact tested commit and literal returned values for `stop.bottom`, `action.height`, `scroll_width`, `trust_gap`, visible-stop count, desktop grid tracks, and all four scroll offsets. Replace the two obsolete `blocked_with_evidence` claims with `resolved_post_fix`; keep the explicit local-only/non-hosted/non-market/non-readiness boundaries.

- [ ] **Step 5: Reconcile the local ten-row Public UX note**

Run the two reviewed note updates using the literal browser observations in `home_phone` and `single_phone`:

```bash
make public-ux-review-note PAGE='Home' VIEWPORT=phone FIRST_ANSWER=yes NEXT_ACTION=yes ADVANCED_COLLAPSED=yes OUTCOME=resolved_post_fix NOTES='Zero-scroll 390x844 Home review passed: one visible stop rule follows the 44px action and precedes metrics; exact geometry is recorded in docs/DASHBOARD_QA.md.'
make public-ux-review-note PAGE='Single-Stock Report' VIEWPORT=phone FIRST_ANSWER=yes NEXT_ACTION=yes ADVANCED_COLLAPSED=yes OUTCOME=resolved_post_fix NOTES='Zero-scroll 390x844 NVDA review passed: the complete stop rule fits, the action remains at least 44px, and the trust-strip gap stays non-negative; exact geometry is recorded in docs/DASHBOARD_QA.md.'
make public-ux-review-notes-check
```

Require `10/10`, zero pending/problem rows, and `share_review_ready`. Keep the `/tmp` note outside Git.

- [ ] **Step 6: Run focused and documentation tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_dashboard_helpers.py \
  tests/test_dashboard_render_smoke.py \
  tests/test_public_v1_release_docs.py \
  tests/test_public_ux_review_checklist.py -q
```

Expected: all pass with only previously documented third-party warnings, if any.

- [ ] **Step 7: Run the complete release matrix**

Run these independently and retain their exact results:

```bash
python3 -m pytest -q
make dashboard-smoke
make research-dashboard-render-smoke
make commercial-beta-release-check
make pilot-readiness-check TOP_N=10
make public-check
make diff-hygiene-summary
git diff --check
```

`pilot-readiness-check` may remain blocked by the known stale/uncommitted readiness and external/manual gates; that is truthful and does not fail this responsive slice. Do not run a readiness rebuild to change it.

- [ ] **Step 8: Verify exact protected-artifact identity**

Hash the same 18 pre-existing modified generated paths against the pre-implementation baseline. Require all 18 hashes to match and `git status --short` to show them unstaged. If any hash differs, stop and diagnose before staging.

- [ ] **Step 9: Commit evidence reconciliation with exact staging**

Stage only the three tracked evidence documents:

```bash
git add ROADMAP.md docs/DASHBOARD_QA.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md
make staged-hygiene-check
git diff --cached --check
git commit -m "Record public mobile zero-scroll evidence"
```

- [ ] **Step 10: Push and require exact-head GitHub verification**

Push only `codex/personal-research-mode-mvp`, update draft PR #113 with the four measurement records and release results, and verify:

```bash
git rev-list --left-right --count HEAD...@{upstream}
gh pr view 113 --json state,isDraft,mergeable,headRefOid,reviews,statusCheckRollup,url
```

Require `0 0`, PR open/draft/mergeable, no unauthorized merge/deploy, exact `headRefOid`, and successful `Commercial Research Beta / local-engineering-gate` for that exact head. Recheck all 18 protected hashes after CI.

---

## Completion Criteria

- Both phone routes pass direct zero-scroll `390x844` geometry with complete stop rules inside the viewport.
- Home has one visible stop and semantic/visual order `primary -> stop -> metrics`; desktop preserves primary/metrics then full-width stop.
- Single Stock preserves a non-negative trust gap, complete answer order/copy, 44-pixel action, and desktop four-column layout.
- Focused, full, release, render, public, hygiene, protected-artifact, branch-sync, and exact-head CI gates pass.
- The local Public UX review note reports `10/10` and `share_review_ready` but remains outside Git.
- PR #113 remains open and draft; no merge, deployment, readiness/data/source/quant mutation, generated artifact, screenshot, or timing artifact occurs.
