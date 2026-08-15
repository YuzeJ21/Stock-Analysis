# Company Workbench Document Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild Personal Research Company Workbench in the approved document-first visual direction while preserving every current route, evidence, analysis, authoring, scenario, and download function.

**Architecture:** Keep all existing data and behavior in the current Streamlit renderers. Add one pure escaped evidence-status projection, one optional renderer target, a bounded two-column overview, and Workbench-scoped presentation-only CSS. Existing detailed modules stay behind their ticker-scoped explicit-open gate.

**Tech Stack:** Python 3.12, Streamlit 1.59, escaped server-rendered HTML, CSS, pytest, Streamlit AppTest, the repository browser gates, and Product Design visual QA.

## Global Constraints

- Selected visual target: `/Users/yjian070/.codex/generated_images/019fe1a2-ef19-73c0-8e1a-069060f28b90/exec-a7444f21-6213-40f5-b4c0-cfb6bcb75797.png`, SHA-256 `0f4105b35445cf11c1397b6e2d5b422a023723be9c828dc43438c8df446f0d7f`.
- Preserve the Company Workbench entry-route allowlist (`mode`, `page`,
  `ticker`, `open`, and `cash_preview`). Preserve the existing authoritative
  Data Health deep-link unchanged, including its existing `lane` and `drawer`
  query parameters.
- Do not expose detailed modules before `Open evidence and analysis modules`.
- Do not add loaders, provider calls, refreshes, writes, generated artifacts, session keys, calculations, or readiness promotion.
- Do not invent dates, notes, evidence, scores, recommendations, ranking, probability, sizing, allocation, entry/exit, or trading language.
- Keep all protected data and output paths byte-identical and unstaged.
- Use the existing Personal Research DOM for navigation; never render a duplicate desktop/mobile nav.
- Keep Public and Operator rendering behavior unchanged.

---

### Task 1: Pure Company Brief And Evidence Rail Contract

**Files:**
- Modify: `src/research_workspace.py`
- Modify: `tests/test_research_workspace.py`

**Interfaces:**
- Consumes: existing `company_workbench_primary_brief(...)` mapping and its `data_health_href`.
- Produces: `company_workbench_evidence_status_html(*, ticker: str, readiness: Mapping[str, object] | None, freshness_label: str) -> str`.
- Preserves: existing `company_workbench_primary_brief_html(...)` selectors, four ordered answer lanes, action, and stop rule.

- [ ] **Step 1: Write failing pure-render tests**

Add literal assertions that prove:

```python
rendered = company_workbench_evidence_status_html(
    ticker="AVGO",
    readiness={
        "fundamentals_ready": True,
        "dcf_ready": False,
        "peer_ready": False,
        "earnings_available": True,
        "analyst_estimates_available": False,
    },
    freshness_label="Stale",
)
assert canonical_lane_states(rendered) == {
    "fundamentals": "Reviewable",
    "dcf": "Withheld",
    "peers": "Withheld",
    "earnings": "Reviewable",
    "estimates": "Withheld",
}
assert "Company evidence status" in rendered
assert "href=" not in rendered
```

Also prove:

- `None` renders all five lanes `Unavailable`, while an empty present mapping
  renders all five `Withheld`;
- each lane becomes `Reviewable` independently and only for the exact boolean
  `True`; unrelated truthy values such as `1` and `"true"` stay `Withheld`;
- the earnings and estimates aliases use exact-boolean OR semantics, including
  conflicting aliases;
- the five lane IDs are unique and canonical, every dynamic value is escaped,
  and malicious text cannot create extra markup or attributes; and
- the existing Company Brief contains the visible title `AVGO Company Brief`
  while retaining all four current lane labels, exactly one primary Data Health
  action, and its exact authoritative href.

- [ ] **Step 2: Run RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_research_workspace.py -k 'company_workbench_primary_brief or company_workbench_evidence_status'
```

Expected: fail because the new evidence-status renderer and editorial title do not exist.

- [ ] **Step 3: Implement the minimal pure HTML projection**

Implement five literal lane definitions with independent readiness predicates. Use `html.escape` for ticker, freshness, labels, and href attributes. Use text states `Reviewable`, `Withheld`, and `Unavailable`; never infer partial state. Keep existing Company Brief classes and add an `h2` display title without changing the four article nodes.

- [ ] **Step 4: Run GREEN**

Run the Task 1 test command and confirm it passes.

- [ ] **Step 5: Commit Task 1**

```bash
git add -- src/research_workspace.py tests/test_research_workspace.py
git commit -m "Add Workbench evidence status projection"
```

### Task 2: Document Layout And Workbench-Scoped Horizontal Navigation

**Files:**
- Modify: `src/dashboard.py`
- Modify: `src/dashboard_visual_system.py`
- Modify: `tests/test_dashboard_visual_system.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`

**Interfaces:**
- Consumes: the existing single `research-workflow-navigation` DOM and existing Company Brief classes.
- Produces: horizontal desktop navigation only when the keyed Workbench container is present; keyed `company-workbench-document` overview container; desktop main/aside and mobile single-column layout.
- Preserves: route hrefs, `aria-current`, disabled tickerless Workbench, workspace-mode links, skip link, and focus order.

- [ ] **Step 1: Write failing layout-contract tests**

Add a focused CSS-output contract for the exact Workbench-scoped selector
`.stApp:has(.st-key-company-workbench-document)`,
horizontal desktop grid, sticky (never fixed) evidence aside, and the
`<=1099px`/`<=640px` one-column resets. Treat the generated CSS string as the
public output under test; extract and assert the exact scoped rules rather than
searching globally for `position: fixed`, because the unchanged shells may
legitimately retain that declaration.

Add a behavioral renderer test with a recording Streamlit double. Invoke
`render_company_workbench(...)` and assert the real calls include exactly one
`st.container(key="company-workbench-document")`, one numeric
`st.columns([3, 1])` overview, and one evidence placeholder. Do not use
`inspect.getsource(...)` as the acceptance seam.

The navigation render contract must also assert the existing HTML still has the
same four labels, canonical hrefs, active state, disabled Workbench behavior,
and Public/Operator mode links.

- [ ] **Step 2: Run RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_dashboard_visual_system.py \
  tests/test_research_mode_dashboard_contract.py -k 'navigation or company_workbench'
```

Expected: fail on the current fixed left rail and absent document container.

- [ ] **Step 3: Implement minimal CSS and overview structure**

When the keyed Workbench container is present, use the stable containing
`.stApp:has(.st-key-company-workbench-document)` scope to move the existing Personal
Research nav into normal flow at desktop, using one three-part grid: brand,
route links, and workspace-mode links. Other Personal routes retain their
current shell. Keep the existing phone route grid at `640px` and force
one-column reflow at `1099px` so desktop zoom and narrow tablets use the same
safe order. In
`render_company_workbench`, place only the primary-answer, supporting timeline,
review-path, lane-coverage, and status placeholders inside `st.columns([3, 1])`.
Render all detailed modules after the overview so phone order is brief, rail,
then module gate.

Add scoped CSS for system-serif company display title, open four-lane strip,
dark status rail, thin document rules, 44-pixel actions, forced colors, and
mobile stacking. Do not add external fonts, icons, images, gradients, fixed
overlays, or horizontal scrolling.

- [ ] **Step 4: Run GREEN**

Run Task 2 tests and the complete baseline unit set:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_research_workspace.py \
  tests/test_dashboard_visual_system.py \
  tests/test_research_mode_dashboard_contract.py \
  tests/test_research_accessibility_browser_gate.py \
  tests/test_workspace_visual_browser_gate.py
```

- [ ] **Step 5: Commit Task 2**

```bash
git add -- src/dashboard.py src/dashboard_visual_system.py \
  tests/test_dashboard_visual_system.py tests/test_research_mode_dashboard_contract.py
git commit -m "Build document-first Workbench layout"
```

### Task 3: Wire Authoritative Readiness Without Functional Regression

**Files:**
- Modify: `src/dashboard.py`
- Modify: `tests/test_dashboard_render_smoke.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`

**Interfaces:**
- Adds optional `selected_evidence_target=None` to `render_single_stock_report(...)`.
- Populates the target from the existing `_stock_report_payload_readiness(report_payload)` result after report construction.
- Populates an unavailable rail when no report payload exists.
- Does not build, fetch, or inspect a second report.

- [ ] **Step 1: Write failing renderer and preservation tests**

Add a real AppTest/renderer contract that captures the evidence target and
asserts five lanes reflect a controlled complete readiness payload. Add a
missing-payload case with five `Unavailable` states. Prove report construction
is still called once and no refresh/write path is entered. Patch the dashboard
boundaries `build_stock_report`,
`load_company_workbench_cash_generation_preview`, and
`render_research_record_authoring`: the default closed render must call the
builder once, fill the evidence target once, and call neither the preview loader
nor the authoring renderer.

Add closed/open Workbench checks that retain:

```text
Review path
Advanced: selected-company lane coverage
Full Company Brief evidence
Open evidence and analysis modules
What Changed
Research Decision Lab
Business Trend
Valuation
Forward View
What Remains Withheld
Add a reviewed research record
Research Conclusion
HTML Research Brief
Download HTML Research Brief
```

The closed state must explicitly omit only the gated module headings (`Research
Decision Lab`, `Business Trend`, `Valuation`, `Forward View`, `What Remains
Withheld`, `Research Conclusion`, and `HTML Research Brief`). It must retain the
Company Brief's `What changed` lane, complete research-only stop rule, truthful
no-change/observation-recency evidence, Review path, lane coverage, and Full
Company Brief disclosures. The opened state must retain every gated module in
the current semantic order.

Run the existing focused behavior contracts, adding regressions only where an
invariant is otherwise unproved, for this preservation matrix:

- tickerless and unregistered routes fail closed without inferred selection;
- `cash_preview` absent/false never loads preview, while exact
  `cash_preview=1` retains its accepted and withheld states;
- thesis/evidence journal, outcome review, validate-preview-confirm authoring,
  decision-process scorecard, session/rerun behavior, Scenario Lab, HTML brief
  download, and audit download keep their existing contracts; and
- the default remains no-write and report construction remains single-pass.

- [ ] **Step 2: Run RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_dashboard_render_smoke.py -k 'company_workbench'
```

Expected: fail because the renderer does not accept or fill the new target.

- [ ] **Step 3: Implement minimal target wiring**

Fill the target once from the same readiness map already used by Company Brief
composition. Do not render a second Data Health control. Keep
`selected_answer_target` and `selected_detail_target` behavior unchanged.

- [ ] **Step 4: Run GREEN and affected behavior suite**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_dashboard_render_smoke.py \
  tests/test_research_workspace.py \
  tests/test_research_mode_dashboard_contract.py
```

- [ ] **Step 5: Commit Task 3**

```bash
git add -- src/dashboard.py tests/test_dashboard_render_smoke.py \
  tests/test_research_mode_dashboard_contract.py
git commit -m "Preserve Workbench behavior in document layout"
```

### Task 4: Browser Acceptance And Design QA

**Files:**
- Modify: `src/research_accessibility_browser_gate.py` only if new visible region geometry is not observable through existing fields.
- Modify: `tests/test_research_accessibility_browser_gate.py` only for the matching non-tautological evaluator contract.
- Modify: `src/workspace_visual_browser_gate.py` only if the shared horizontal nav needs a new fail-closed geometry check.
- Modify: `tests/test_workspace_visual_browser_gate.py` only for the matching evaluator contract.
- Create: `design-qa.md`

**Interfaces:**
- Consumes: current loopback browser gates and final selected image.
- Produces: exact desktop/phone/zoom evidence and a Product Design QA result.

- [ ] **Step 1: Add browser RED only for an unobserved acceptance requirement**

Require one visible `Company evidence status` region with five rows, brief left
of rail at desktop, brief above rail and above the module gate at phone and
desktop 200% zoom, four stacked brief lanes at phone, no overflow, and
unchanged Company Brief action/module activation. Require one H1, one H2 display
title, one labelled navigation, one labelled brief region, one labelled aside,
no positive tabindex, and a 44-pixel primary action. Add a non-Workbench
Personal Research desktop cell proving its existing shell geometry is
unchanged. Do not loosen existing focus, target, runtime, or request checks.

- [ ] **Step 2: Run the focused browser matrix**

```bash
output_dir=$(mktemp -d /tmp/company-workbench-document-browser.XXXXXX)
python3 -m src.workspace_visual_browser_gate \
  --routes company-workbench \
  --viewports 1440x1024,1280x720,390x844 \
  --zooms 1,2 \
  --output-dir "$output_dir"
```

Also run the existing Company Workbench accessibility route at desktop and
phone widths. Run the full ordered 90-cell matrix only if final selectors cease
to be Workbench-scoped or a focused result demonstrates cross-route impact.

- [ ] **Step 3: Compare target and implementation in one visual input**

Capture the light-theme saved-company route
`?mode=research&page=company-workbench&ticker=AAPL` at `1440x1024`, 100% zoom,
DPR 1, in both closed and opened states. Combine the opened implementation side
by side with the selected target and inspect the combined image. Repeat with
focused primary-brief and evidence-rail crops when full-view text is too small.

- [ ] **Step 4: Write and iterate `design-qa.md`**

Record target and implementation dimensions, viewport, density, theme, route
state, target and screenshot paths/checksums, typography, spacing, colors,
assets, copy, interaction evidence, console errors, comparison history,
remaining P3 notes, and `final result: passed` or `final result: blocked`.
Include a target-to-product-truth deviation table for invented mock prose,
dates, notes, and positive states that were intentionally not copied. Grade
P0/P1/P2 against the four approved direction characteristics, responsive
hierarchy, function preservation, and prohibited invented content rather than
subjective pixel identity. Fix every P0/P1/P2 and repeat the comparison before
handoff.

- [ ] **Step 5: Run final verification and protected-artifact checks**

Run the affected unit/render suites, `git diff --check`, and prove both
`git diff --exit-code 13e7e383bee8ca51f462749c91a3dc992d92ea94 -- data outputs`
and `git status --short -- data outputs` are empty. Record those commands and
results in `design-qa.md`; that QA file is an intentional source artifact, not
a protected generated artifact. Run the smallest full suite justified by final
changed bytes. Do not rerun unchanged broad gates after a byte-identical pass.

- [ ] **Step 6: Request independent review**

Ask a reviewer to assess functional preservation, fail-closed readiness, query
and state boundaries, responsive/accessibility behavior, and target fidelity.
Fix every Critical or Important finding before handoff.

- [ ] **Step 7: Commit verified final bytes**

Stage named source, test, plan, and QA paths only. Never use `git add -A` and
never stage generated data/output paths.
