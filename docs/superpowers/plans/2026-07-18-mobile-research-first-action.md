# Mobile Research First-Action Density Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring each Personal Research route's first task into the 390x844 useful viewport while preserving profile truth, freshness, next action, and research-only boundaries.

**Architecture:** Keep the existing compact profile strip and research workspace header. Add semantic classes to the two route metadata rows, apply phone-only compaction through the existing research style block, and replace Company Workbench's long always-visible path caption with a collapsed native disclosure.

**Tech Stack:** Python 3.12, Streamlit, HTML/CSS strings, pytest, Streamlit AppTest, Git, Make.

## Global Constraints

- Desktop profile and route metadata remain unchanged; Company Workbench keeps the complete path available through the same collapsed disclosure.
- Data profile, Sources through, Freshness, Price-ready, DCF-ready, next action, and the research-only boundary remain visible or equivalently available.
- No readiness state, source date, source right, research input, forecast, valuation, peer, catalyst, outcome, backtest, or calibration state changes.
- No CSV, JSON, report, sample-report, committed screenshot, or timing artifact is created or staged.
- Candidate context remains untrusted and synthetic fixtures remain test-only.
- No investment advice, ranking, recommendation, price prediction, broker action, order routing, or trade instruction is added.
- Use exact staging only; never use `git add -A`.
- Keep PR #113 open and draft; do not merge or deploy.

---

### Task 1: Compact the shared research context at phone width

**Files:**
- Modify: `tests/test_research_workspace.py:353-368`
- Modify: `tests/test_research_mode_dashboard_contract.py:202-220`
- Modify: `src/research_workspace.py:376-398`
- Modify: `src/dashboard.py:33966-34057`

**Interfaces:**
- Consumes: `research_workspace_header_html(page_title, *, ticker, profile_label, freshness, primary_action) -> str` and the existing `.profile-trust-strip.compact` markup.
- Produces: `.research-workspace-freshness` and `.research-workspace-action` semantic hooks plus phone-only CSS that leaves desktop output unchanged.

- [ ] **Step 1: Write failing HTML and style contract tests**

Add these assertions to `test_research_workspace_header_keeps_scope_freshness_action_and_boundary_visible`:

```python
assert "class='research-workspace-meta-item research-workspace-freshness'" in rendered
assert "class='research-workspace-meta-item research-workspace-action'" in rendered
```

Add this test to `tests/test_research_mode_dashboard_contract.py`:

```python
def test_research_workspace_phone_styles_compact_profile_and_hide_only_duplicate_freshness():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    start = source.index("def render_research_workspace_styles()")
    end = source.index("\ndef render_research_workspace_header(", start)
    styles = source[start:end]

    assert ".profile-trust-strip.compact" in styles
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in styles
    assert ".research-workspace-freshness { display: none; }" in styles
    assert ".research-workspace-action" in styles
    assert "@media (max-width: 640px)" in styles
```

- [ ] **Step 2: Run focused tests and verify the red state**

Run:

```bash
python3 -m pytest tests/test_research_workspace.py::test_research_workspace_header_keeps_scope_freshness_action_and_boundary_visible tests/test_research_mode_dashboard_contract.py::test_research_workspace_phone_styles_compact_profile_and_hide_only_duplicate_freshness -q
```

Expected: both tests fail because the semantic classes and three-column phone CSS do not exist.

- [ ] **Step 3: Add semantic route metadata classes**

Change the metadata markup in `research_workspace_header_html` to:

```python
"<dl class='research-workspace-meta'>"
f"<div class='research-workspace-meta-item research-workspace-freshness'><dt>Freshness</dt><dd>{html.escape(str(freshness or 'Check saved readiness'))}</dd></div>"
f"<div class='research-workspace-meta-item research-workspace-action'><dt>Next action</dt><dd>{html.escape(str(primary_action or 'Review source-backed evidence'))}</dd></div>"
"</dl>"
```

- [ ] **Step 4: Add phone-only compaction to the existing research styles**

Replace the current phone block in `render_research_workspace_styles` with:

```css
@media (max-width: 640px) {
    .research-desk-grid { grid-template-columns: 1fr; }
    .research-workspace-header {
        padding: .72rem .78rem;
        margin-bottom: .65rem;
    }
    .research-workspace-heading h1 { font-size: 1.4rem; }
    .research-workspace-meta {
        grid-template-columns: 1fr;
        gap: 0;
        margin: .5rem 0 .4rem;
    }
    .research-workspace-freshness { display: none; }
    .research-workspace-action {
        border-top: 1px solid #e5e9e7;
        padding-top: .45rem;
    }
    .profile-trust-strip.compact {
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: .3rem;
        margin: .12rem 0 .6rem;
        padding: .45rem 0;
    }
    .profile-trust-strip.compact > span,
    .profile-trust-strip.compact .profile-trust-primary {
        padding: 0 .35rem;
    }
    .profile-trust-strip.compact > :nth-child(3n + 1) { border-left: 0; }
}
```

- [ ] **Step 5: Run focused tests and verify the green state**

Run:

```bash
python3 -m pytest tests/test_research_workspace.py tests/test_research_mode_dashboard_contract.py -q
```

Expected: all focused tests pass.

- [ ] **Step 6: Commit the semantic and responsive shell slice**

```bash
git add -- src/research_workspace.py src/dashboard.py tests/test_research_workspace.py tests/test_research_mode_dashboard_contract.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Compact mobile research context"
git push origin codex/personal-research-mode-mvp
```

---

### Task 2: Collapse the Company Workbench review path

**Files:**
- Modify: `tests/test_research_mode_dashboard_contract.py`
- Modify: `src/dashboard.py:34153-34185`

**Interfaces:**
- Consumes: `company_workbench_section_contract() -> list[dict[str, object]]` and Streamlit's existing `st.expander` API.
- Produces: a collapsed `Review path` disclosure immediately after the `Selected Company` heading and before technical coverage or detailed report content.

- [ ] **Step 1: Write the failing Workbench ordering test**

Add:

```python
def test_company_workbench_keeps_selected_company_before_collapsed_review_path_and_details():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    start = source.index("def render_company_workbench(")
    end = source.index("\ndef main()", start)
    workbench = source[start:end]

    selected = workbench.index('st.markdown("### Selected Company")')
    review = workbench.index('with st.expander("Review path", expanded=False):', selected)
    path = workbench.index('st.caption(" -> ".join(section_names[:-1]))', review)
    coverage = workbench.index('with st.expander("Advanced: selected-company lane coverage", expanded=False):', path)
    report = workbench.index("render_single_stock_report(", coverage)

    assert selected < review < path < coverage < report
    assert 'st.caption("Review path: "' not in workbench
```

- [ ] **Step 2: Run the test and verify the red state**

Run:

```bash
python3 -m pytest tests/test_research_mode_dashboard_contract.py::test_company_workbench_keeps_selected_company_before_collapsed_review_path_and_details -q
```

Expected: FAIL because the path is an always-visible caption before the `Selected Company` heading.

- [ ] **Step 3: Implement the collapsed disclosure**

Replace the Workbench path block with:

```python
st.markdown("### Selected Company")
section_names = [section["title"] for section in company_workbench_section_contract()]
with st.expander("Review path", expanded=False):
    st.caption(" -> ".join(section_names[:-1]))
```

Keep `Advanced: selected-company lane coverage` and `render_single_stock_report(...)` directly after this block.

- [ ] **Step 4: Run focused tests and verify the green state**

Run:

```bash
python3 -m pytest tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py -q
```

Expected: all focused tests pass and all four Personal Research routes still render.

- [ ] **Step 5: Commit the Workbench disclosure slice**

```bash
git add -- src/dashboard.py tests/test_research_mode_dashboard_contract.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Collapse the mobile Workbench review path"
git push origin codex/personal-research-mode-mvp
```

---

### Task 3: Verify the visual result and document the maturity boundary

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/PERSONAL_RESEARCH_MODE.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Test: `tests/test_public_v1_release_docs.py`

**Interfaces:**
- Consumes: verified implementation behavior and fresh 1280x720 plus 390x844 audit screenshots stored outside the repository.
- Produces: truthful roadmap and continuation claims that describe local usability maturity without claiming source, hosted, reviewer, calibration, or market validation.

- [ ] **Step 1: Re-capture the four routes outside the repository**

Capture Research Desk, Discover, Company Workbench, and Monitor at 1280x720 and 390x844 to `/tmp/stock-research-workflow-audit-after/`.

Expected visible results:

- desktop retains all existing profile and route metadata;
- the phone profile strip uses two rows;
- the phone route card omits only its duplicate freshness row;
- Discover search is fully visible in the first phone viewport;
- Company Workbench shows `Selected Company` and collapsed `Review path` in the first phone viewport;
- Monitor shows the weekly summary in the first phone viewport;
- no route shows a traceback, horizontal overflow, fabricated content, or missing research-only boundary.

- [ ] **Step 2: Add a failing documentation contract assertion**

Extend the Personal Research documentation test in `tests/test_public_v1_release_docs.py` to require these phrases:

```python
assert "mobile first-action density" in personal_mode.lower()
assert "does not change readiness" in personal_mode.lower()
```

- [ ] **Step 3: Run the documentation test and verify the red state**

Run:

```bash
python3 -m pytest tests/test_public_v1_release_docs.py -q
```

Expected: FAIL because the documentation does not yet describe this slice.

- [ ] **Step 4: Update roadmap, Personal Research documentation, and continuation truth**

Document:

- the four-route phone compaction is implemented locally;
- desktop profile and route metadata plus all evidence boundaries are unchanged; the Workbench path remains available in its collapsed disclosure;
- this improves usability and reviewer comprehension only;
- it does not change readiness or prove source activation, hosted operation, reviewer demand, calibration, commercial demand, or product-market fit;
- the next stage remains one permitted source path followed by controlled hosting and external reviewer validation.

- [ ] **Step 5: Run focused and full verification**

Run:

```bash
python3 -m pytest tests/test_research_workspace.py tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py tests/test_public_v1_release_docs.py -q
python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make public-wording-check
make public-check
make commercial-beta-check
make commercial-beta-release-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
```

Expected: every command exits zero; pilot readiness remains `pilot-ready with manual gates`; generated artifact churn remains zero.

- [ ] **Step 6: Stage exact files and verify the package**

```bash
git add -- ROADMAP.md docs/PERSONAL_RESEARCH_MODE.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md tests/test_public_v1_release_docs.py
make staged-hygiene-check
git diff --cached --check
```

Expected: only the four intentional documentation/test files are staged and generated CSV/JSON/report churn is zero.

- [ ] **Step 7: Commit, push, and update draft PR #113**

```bash
git commit -m "Document mobile research first-action maturity"
git push origin codex/personal-research-mode-mvp
gh pr comment 113 --body "Verified mobile Personal Research first-action density update: desktop profile and route metadata plus all readiness boundaries remain unchanged; the Workbench path stays available in a collapsed disclosure; phone routes expose their first task sooner; full local release gates passed; no generated CSV, JSON, report, sample-report, screenshot, or timing churn was staged. PR remains draft."
```

Expected: branch aligns with its remote, PR #113 remains open and draft, and the new comment records the verified boundary.
