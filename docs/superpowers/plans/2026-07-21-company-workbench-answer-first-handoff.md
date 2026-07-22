# Company Workbench Answer-First Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put the truthful selected-company answer and ticker-specific Data Health handoff inside the first `390x844` Company Workbench viewport without changing readiness, evidence, or report content.

**Architecture:** Extend the existing research workspace header with an opt-in compact form used only by Company Workbench. Create a Streamlit answer placeholder directly after that header and pass it to `render_single_stock_report`, whose existing fast and final summary paths will render through one target-aware helper while all other callers keep the current direct-render behavior.

**Tech Stack:** Python 3, Streamlit, pandas, pytest, HTML/CSS contracts, local browser QA, GitHub draft PR checks.

## Global Constraints

- Research-only; no investment advice or direct buy/sell instruction.
- No broker integration, order routing, auto-trading, or post-earnings price prediction.
- Candidate context cannot alter deterministic forecasts or become trusted evidence.
- Actuals, consensus, Revenue, EPS, operating margin, free cash flow, FCF margin, valuation, peer, catalyst, outcome, backtest, and calibration readiness remain independent.
- Missing evidence remains withheld.
- EPS split basis remains unverified without explicit proof.
- Q4 requires explicit SEC-filed three-month table evidence.
- Synthetic fixtures remain test-only.
- Empty valuation, catalyst, outcome, consensus, and field-proof ledgers remain empty.
- Do not run `make readiness` or introduce generated CSV, JSON, report, sample-report, screenshot, timing, or canonical-data artifacts.
- Keep PR #113 open and draft; push only `codex/personal-research-mode-mvp`; do not merge or deploy publicly.
- Stage exact intentional files only; never use `git add -A`.

---

## File Map

- `src/research_workspace.py`: builds the semantic Personal Research workspace header HTML and owns the opt-in compact-header contract.
- `src/dashboard.py`: owns header styling, Company Workbench route order, and fast/final selected-answer rendering.
- `src/public_performance_gate.py`: defines the route markers used by the non-writing performance contract.
- `tests/test_research_workspace.py`: verifies full and compact header semantics.
- `tests/test_research_mode_dashboard_contract.py`: verifies answer-slot placement, report wiring, compact route scope, and navigation order.
- `tests/test_dashboard_helpers.py`: verifies both fast and final summaries use the target-aware renderer without duplicate direct output.
- `tests/test_dashboard_render_smoke.py`: verifies one final selected answer and the ticker-preserving Data Health handoff in a rendered Workbench run.
- `tests/test_public_performance_gate.py`: verifies the Workbench gate uses the retained semantic page identity rather than the removed redundant heading.
- `src/dashboard_render_smoke.py`: updates the rendered-route marker to the retained `Company Workbench` heading if the smoke contract depends on `Selected Company`.
- `src/browser_qa_evidence.py` and `tests/test_browser_qa_evidence.py`: update only static Workbench first-view wording that refers to the removed heading; do not claim screenshot evidence from these contracts.
- `ROADMAP.md`: records the verified answer-first usability slice and preserves external blockers.
- `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`: advances exact-HEAD continuation truth and next executable lane.
- `docs/superpowers/specs/2026-07-21-company-workbench-answer-first-handoff-design.md`: changes the design status from pending review to approved and records implementation evidence after verification.

## Execution Note

Live desktop verification exposed one inaccurate design assumption: Personal Research mode did not load the Public-mode CSS that supplied the selected answer's multi-column layout. The unstyled answer remained semantic but rendered as a block. A test-first correction adds an explicit `research` summary class and scoped Personal Research desktop/phone styles in `src/dashboard.py`; it does not load the Public shell, change other routes, or alter answer data. The final phone layout is shorter than the unstyled baseline and keeps the Data Health link, stop condition, Review path, and lane-coverage control inside the first `390x844` viewport.

### Task 1: Compact Workbench Header Contract

**Files:**
- Modify: `src/research_workspace.py:632-656`
- Modify: `src/dashboard.py:34190-34335`
- Test: `tests/test_research_workspace.py:665-690`
- Test: `tests/test_research_mode_dashboard_contract.py:398-435`

**Interfaces:**
- Consumes: `research_workspace_header_html(page_title, *, ticker, profile_label, freshness, primary_action)`.
- Produces: `research_workspace_header_html(..., compact: bool = False) -> str` and `render_research_workspace_header(..., compact: bool = False) -> None`.

- [ ] **Step 1: Add the failing compact-header unit contract**

```python
def test_compact_research_workspace_header_keeps_identity_scope_and_boundary_without_duplicate_meta():
    rendered = research_workspace_header_html(
        "Company Workbench",
        ticker="NVDA",
        profile_label="Local Research",
        freshness="Current through 2026-07-16",
        primary_action="Review source-backed sections",
        compact=True,
    )

    assert "research-workspace-header compact" in rendered
    assert "<h1>Company Workbench</h1>" in rendered
    assert "NVDA" in rendered
    assert "Local Research" in rendered
    assert "Research-only" in rendered
    assert "investment advice" in rendered
    assert "Current through 2026-07-16" not in rendered
    assert "Review source-backed sections" not in rendered
    assert "research-workspace-meta" not in rendered
```

- [ ] **Step 2: Run the focused header tests and verify the new test fails**

Run: `python3 -m pytest tests/test_research_workspace.py -q`

Expected: FAIL because `research_workspace_header_html` does not accept `compact`.

- [ ] **Step 3: Implement the opt-in compact HTML contract**

Add `compact: bool = False`. Build the opening class as `research-workspace-header compact` only when requested, and make the existing `<dl class='research-workspace-meta'>...</dl>` an empty string in compact mode. Preserve the current output byte-for-byte for the default full header except for local expression assembly.

```python
def research_workspace_header_html(
    page_title: str,
    *,
    ticker: str = "",
    profile_label: str,
    freshness: str,
    primary_action: str,
    compact: bool = False,
) -> str:
    scope = str(ticker or "Focused research scope").strip().upper() if ticker else "Focused research scope"
    header_class = "research-workspace-header compact" if compact else "research-workspace-header"
    meta_html = "" if compact else (
        "<dl class='research-workspace-meta'>"
        f"<div class='research-workspace-meta-item research-workspace-freshness'><dt>Freshness</dt><dd>{html.escape(str(freshness or 'Check saved readiness'))}</dd></div>"
        f"<div class='research-workspace-meta-item research-workspace-action'><dt>Next action</dt><dd>{html.escape(str(primary_action or 'Review source-backed evidence'))}</dd></div>"
        "</dl>"
    )
    return (
        f"<section class='{header_class}' aria-label='Personal research workspace'>"
        "<div class='research-workspace-heading'>"
        "<span>Personal research mode</span>"
        f"<h1>{html.escape(str(page_title or 'Research Desk'))}</h1>"
        f"<p>{html.escape(scope)} · {html.escape(str(profile_label or 'Local research'))}</p>"
        "</div>"
        f"{meta_html}"
        "<p class='research-workspace-boundary'>Research-only. Not investment advice; no trade instruction is produced.</p>"
        "</section>"
    )
```

- [ ] **Step 4: Wire the dashboard wrapper and compact CSS without changing other routes**

Add `compact: bool = False` to `render_research_workspace_header`, pass it to the pure helper, and add only these scoped rules to the existing style block:

```css
.research-workspace-header.compact { padding: .72rem .9rem; margin-bottom: .55rem; }
.research-workspace-header.compact .research-workspace-boundary { margin-top: .35rem; }
```

The Company Workbench call will opt in during Task 2. Research Desk, Discover, Monitor, Data Health, and Proof History keep the default.

- [ ] **Step 5: Run focused tests and verify they pass**

Run: `python3 -m pytest tests/test_research_workspace.py tests/test_research_mode_dashboard_contract.py -q`

Expected: PASS for the compact helper and all unchanged full-header contracts.

### Task 2: Anchored Selected-Answer Renderer

**Files:**
- Modify: `src/dashboard.py:30178-30420`
- Test: `tests/test_dashboard_helpers.py:30195-30245`
- Test: `tests/test_dashboard_helpers.py:30625-30650`

**Interfaces:**
- Consumes: an optional Streamlit DeltaGenerator compatible with `.markdown(body, unsafe_allow_html=True)`.
- Produces: `render_single_stock_public_summary(frame: pd.DataFrame, *, research_mode: bool, selected_answer_target=None) -> None` and `render_single_stock_report(..., selected_answer_target=None) -> None`.

- [ ] **Step 1: Add failing source contracts for fast and final target use**

Update the existing direct-route summary tests to require:

```python
assert "selected_answer_target=None" in report_signature
assert "render_single_stock_public_summary(" in report_chunk
assert "selected_answer_target=selected_answer_target" in report_chunk
assert report_chunk.count("single_stock_public_summary_html(") == 0
```

Add an isolated helper contract using a fake target and monkeypatched `st.markdown`:

```python
def test_single_stock_public_summary_uses_selected_target_when_supplied(monkeypatch):
    calls = []
    target = SimpleNamespace(markdown=lambda body, **kwargs: calls.append(("target", body, kwargs)))
    monkeypatch.setattr(dashboard.st, "markdown", lambda body, **kwargs: calls.append(("global", body, kwargs)))

    dashboard.render_single_stock_public_summary(
        dashboard.single_stock_one_answer_frame({"ticker": "NVDA", "status": "partial"}),
        research_mode=True,
        selected_answer_target=target,
    )

    assert [kind for kind, _, _ in calls] == ["target"]
    assert "mode=research&amp;page=data-health&amp;ticker=NVDA" in calls[0][1]
```

- [ ] **Step 2: Run the focused helper tests and verify the new contracts fail**

Run: `python3 -m pytest tests/test_dashboard_helpers.py -q -k 'fast_public_single_stock or public_summary_uses_selected_target or simplified_review_sections'`

Expected: FAIL because the target-aware helper and report parameter do not exist.

- [ ] **Step 3: Add the target-aware renderer and optional report argument**

Place this helper immediately after `single_stock_public_summary_html`:

```python
def render_single_stock_public_summary(
    frame: pd.DataFrame,
    *,
    research_mode: bool,
    selected_answer_target=None,
) -> None:
    rendered = single_stock_public_summary_html(
        frame,
        target_mode=RESEARCH_MODE if research_mode else "public",
    )
    target = selected_answer_target if selected_answer_target is not None else st
    target.markdown(rendered, unsafe_allow_html=True)
```

Add `selected_answer_target=None` to `render_single_stock_report`. Replace both the fast and final `st.markdown(single_stock_public_summary_html(...))` branches with:

```python
render_single_stock_public_summary(
    fast_answer_frame,
    research_mode=research_mode,
    selected_answer_target=selected_answer_target,
)
```

and:

```python
render_single_stock_public_summary(
    single_answer_frame,
    research_mode=research_mode,
    selected_answer_target=selected_answer_target,
)
```

- [ ] **Step 4: Run focused helper tests and verify they pass**

Run: `python3 -m pytest tests/test_dashboard_helpers.py -q -k 'fast_public_single_stock or public_summary_uses_selected_target or simplified_review_sections'`

Expected: PASS; public/operator callers without a target still render through `st.markdown`.

### Task 3: Company Workbench Answer-First Route

**Files:**
- Modify: `src/dashboard.py:34404-34448`
- Test: `tests/test_research_mode_dashboard_contract.py:138-155`
- Test: `tests/test_research_mode_dashboard_contract.py:417-435`
- Test: `tests/test_dashboard_render_smoke.py`

**Interfaces:**
- Consumes: `render_research_workspace_header(..., compact=True)` and `render_single_stock_report(..., selected_answer_target=selected_answer_target)`.
- Produces: one `st.empty()` answer slot declared before both collapsed controls; no redundant `Selected Company` heading.

- [ ] **Step 1: Replace the obsolete order tests with failing answer-first contracts**

```python
def test_company_workbench_anchors_answer_before_collapsed_navigation_and_passes_target_to_report():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    start = source.index("def render_company_workbench(")
    end = source.index("\ndef main()", start)
    workbench = source[start:end]

    header = workbench.index("render_research_workspace_header(")
    target = workbench.index("selected_answer_target = st.empty()", header)
    review = workbench.index('with st.expander("Review path", expanded=False):', target)
    coverage = workbench.index('with st.expander("Advanced: selected-company lane coverage", expanded=False):', review)
    report = workbench.index("render_single_stock_report(", coverage)

    assert header < target < review < coverage < report
    assert "compact=True" in workbench[header:target]
    assert "selected_answer_target=selected_answer_target" in workbench[report:]
    assert 'st.markdown("### Selected Company")' not in workbench
```

Update the render smoke to assert the generated HTML contains exactly one `aria-label='Selected ticker answer'` or its double-quoted equivalent and the ticker-specific `?mode=research&page=data-health&ticker=AVGO` handoff.

- [ ] **Step 2: Run route and smoke tests and verify the new order contract fails**

Run: `python3 -m pytest tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py -q`

Expected: FAIL because the route has no answer placeholder, still includes the redundant heading, and does not pass a target.

- [ ] **Step 3: Implement the approved Workbench placement**

Change only the Workbench route:

```python
render_research_workspace_header(
    "Company Workbench",
    context,
    ticker=ticker,
    primary_action="Review usable evidence, then record what remains uncertain",
    compact=True,
)
selected_answer_target = st.empty()
section_names = [section["title"] for section in company_workbench_section_contract()]
with st.expander("Review path", expanded=False):
    st.caption(" -> ".join(section_names[:-1]))
with st.expander("Advanced: selected-company lane coverage", expanded=False):
    ...
render_single_stock_report(
    ...,
    selected_answer_target=selected_answer_target,
)
```

Do not move or alter `What Changed`, Business Trend, Valuation, Forward View, withheld states, Advanced evidence, or report data loading.

- [ ] **Step 4: Run focused route, workspace, helper, and smoke tests**

Run: `python3 -m pytest tests/test_research_workspace.py tests/test_research_mode_dashboard_contract.py tests/test_dashboard_helpers.py tests/test_dashboard_render_smoke.py -q`

Expected: PASS.

### Task 4: Performance And Browser-QA Contract Alignment

**Files:**
- Modify: `src/public_performance_gate.py:135-155`
- Modify: `tests/test_public_performance_gate.py:35-80`
- Modify if required: `src/dashboard_render_smoke.py:95-115`
- Modify if required: `src/browser_qa_evidence.py:290-360`
- Modify if required: `tests/test_browser_qa_evidence.py`

**Interfaces:**
- Consumes: retained semantic marker `Company Workbench` and selected-answer ARIA label.
- Produces: non-writing gates that no longer depend on the removed `Selected Company` heading.

- [ ] **Step 1: Add failing marker expectations**

Update the Workbench performance contract expectation to:

```python
assert RESEARCH_ROUTE_SPECS[2].first_useful_marker == "Company Workbench"
assert RESEARCH_ROUTE_SPECS[2].full_markers[0] == "Company Workbench"
assert "Selected Company" not in RESEARCH_ROUTE_SPECS[2].full_markers
```

Update render-smoke/browser-QA static marker expectations only where they require the removed heading; retain all readiness and Advanced lane-coverage markers.

- [ ] **Step 2: Run performance and browser-QA contract tests and verify they fail before source updates**

Run: `python3 -m pytest tests/test_public_performance_gate.py tests/test_browser_qa_evidence.py -q`

Expected: FAIL on obsolete `Selected Company` route markers.

- [ ] **Step 3: Replace only obsolete markers in source contracts**

In `RESEARCH_ROUTE_SPECS`, set the Workbench first-useful marker and first full marker to `Company Workbench`. Make the same narrow change in render-smoke or browser-QA contracts only if focused failures prove they rely on the removed heading.

- [ ] **Step 4: Run focused gate tests and verify they pass**

Run: `python3 -m pytest tests/test_public_performance_gate.py tests/test_browser_qa_evidence.py -q`

Expected: PASS without generating timing or screenshot artifacts.

### Task 5: Live Responsive Acceptance And Documentation

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: `docs/superpowers/specs/2026-07-21-company-workbench-answer-first-handoff-design.md`

**Interfaces:**
- Consumes: locally running Streamlit dashboard and current AVGO route.
- Produces: measured desktop and `390x844` acceptance evidence stored only under `/tmp`, plus current roadmap/continuation truth.

- [ ] **Step 1: Run the dashboard locally without refreshing data**

Run the existing dashboard launch command documented by the repository, using the current saved local artifacts only. Do not run readiness, broad refresh, source import, report generation, or timing artifact commands.

Expected: the Company Workbench route opens at `/?mode=research&page=company-workbench&ticker=AVGO&open=1`.

- [ ] **Step 2: Measure phone acceptance in the configured in-app browser**

At `390x844`, record DOM bounding boxes for:

```text
[aria-label="Selected ticker answer"]
the "Open Data Health" link inside that answer
the "Review path" details summary
the "Advanced: selected-company lane coverage" details summary
```

Expected:

```text
selected_answer.top < review_path.top < lane_coverage.top
data_health_link.bottom <= 844
document.documentElement.scrollWidth <= document.documentElement.clientWidth
exactly one selected-ticker answer
zero browser console errors
```

Save screenshots only under `/tmp/stock-research-workflow-audit-2026-07-22/`; never stage them.

- [ ] **Step 3: Measure desktop acceptance**

At `1280x720`, verify the selected-answer cards retain their existing multi-column layout, the Data Health handoff is visible, both navigation expanders follow the answer, and there is no horizontal overflow or browser error.

- [ ] **Step 4: Make at most one scoped CSS correction if measurement fails**

If the phone Data Health link extends below `844`, adjust only `.research-workspace-header.compact` padding/margin or the compact boundary margin. Do not hide the global profile strip, research boundary, withheld state, or Data Health handoff. Re-run focused tests and both viewport measurements after the correction.

- [ ] **Step 5: Update product truth**

In `ROADMAP.md`, record the measured answer-first Workbench improvement as locally verified while leaving consensus, calibration, source-rights, hosted preview, external reviewer, and operating gates incomplete. In the continuation prompt, record the new verified HEAD only after commit/push, keep readiness stale, forbid generated artifact churn, and set the exact next safe executable lane. Change the design status to `Approved and implemented` only after all acceptance checks pass.

### Task 6: Full Verification, Exact Commit, Draft PR, And Exact-Head CI

**Files:**
- Stage only the intentional code, test, plan, specification, roadmap, and continuation-prompt files changed by Tasks 1-5.
- Exclude all pre-existing generated CSV/report changes and all `/tmp` browser evidence.

**Interfaces:**
- Consumes: verified local implementation and documentation.
- Produces: one coherent commit on `codex/personal-research-mode-mvp`, pushed draft PR #113 update, and exact-head CI evidence.

- [ ] **Step 1: Run focused and full local verification**

Run:

```bash
python3 -m pytest tests/test_research_workspace.py tests/test_research_mode_dashboard_contract.py tests/test_dashboard_helpers.py tests/test_dashboard_render_smoke.py tests/test_public_performance_gate.py tests/test_browser_qa_evidence.py -q
python3 -m pytest tests -q
make dashboard-smoke
make public-wording-check
make public-check
make commercial-beta-release-check
make pilot-readiness-check TOP_N=10
make pr-range-hygiene-check
make diff-hygiene-summary
git diff --check
```

Expected: all commands pass. `pilot-readiness-check` must remain truthfully blocked/stale if current evidence is stale; that expected product state must not be converted into a false pass by rebuilding generated artifacts.

- [ ] **Step 2: Review the exact diff and generated-artifact boundary**

Run:

```bash
git diff -- src/research_workspace.py src/dashboard.py src/public_performance_gate.py src/dashboard_render_smoke.py src/browser_qa_evidence.py tests ROADMAP.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md docs/superpowers/specs/2026-07-21-company-workbench-answer-first-handoff-design.md docs/superpowers/plans/2026-07-21-company-workbench-answer-first-handoff.md
git status --short
```

Expected: intentional product/test/docs changes plus exactly the pre-existing 18 unstaged generated CSV/report files; no generated file is staged.

- [ ] **Step 3: Stage exact intentional files and run staged hygiene**

Use `git add` with the explicit paths that actually changed. Never use a wildcard or `git add -A`.

Run: `make staged-hygiene-check`

Expected: PASS and staged diff contains no CSV, JSON, report, sample-report, screenshot, timing, or canonical-data artifact.

- [ ] **Step 4: Commit and push the coherent slice**

Run:

```bash
git commit -m "Improve Workbench answer-first handoff"
git push origin codex/personal-research-mode-mvp
```

Expected: local HEAD equals `origin/codex/personal-research-mode-mvp`; generated working-tree changes remain unstaged.

- [ ] **Step 5: Update draft PR #113 and wait for exact-head CI**

Keep the PR draft. Add a concise evidence comment covering the approved design, responsive measurements, tests, generated-artifact exclusion, and external blockers. Wait for GitHub Actions on the exact pushed SHA and report the run URL and conclusion. Do not merge or deploy.

- [ ] **Step 6: Final audit**

Verify branch, HEAD, upstream divergence, staged area, PR draft/mergeability, exact-head CI, and the generated-artifact exclusion. Report the branch safe for draft review only if there are no unresolved Critical or Important engineering findings and every local acceptance check passed.
