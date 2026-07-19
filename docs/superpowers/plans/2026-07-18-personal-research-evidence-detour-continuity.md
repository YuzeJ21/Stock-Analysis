# Personal Research Evidence Detour Continuity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep Company Workbench evidence detours inside Personal Research mode and provide one direct return action without adding routes or changing evidence state.

**Architecture:** Pure helpers in `src/research_workspace.py` own same-mode evidence URLs and the deterministic return destination. `src/dashboard.py` renders the return action only for research-mode Data Health and Proof History, before existing evidence content. AppTest render smoke expands from four primary routes to those four plus the two secondary evidence detours.

**Tech Stack:** Python 3, Streamlit, pandas, pytest, AppTest, Markdown.

## Global Constraints

- Do not run `make readiness`.
- Do not create or stage CSV, JSON, report, sample-report, screenshot, timing, or bytecode churn.
- Do not add a route, alias, session state, persistence layer, or data mutation.
- Data Health and Proof History remain secondary Advanced evidence routes.
- Public and Operator mode behavior remains unchanged.
- Missing ticker returns to Research Desk; never infer a company.
- Navigation cannot mutate readiness, source, valuation, consensus, forecast, catalyst, outcome, backtest, or calibration state.
- Preserve research-only, candidate-context, source-rights, explicit-Q4, EPS split-basis, synthetic-fixture, and no-investment-advice boundaries.

---

### Task 1: Same-mode evidence and return-link helpers

**Files:**
- Modify: `src/research_workspace.py:359-376`
- Test: `tests/test_research_workspace.py:336-351`

**Interfaces:**
- Consumes: existing URL quoting and ticker normalization in `src.research_workspace`.
- Produces: `advanced_evidence_links(ticker: str) -> list[dict[str, str]]` with research-mode URLs and `research_evidence_return_link(ticker: str) -> dict[str, str]`.

- [ ] **Step 1: Write failing route-helper tests**

Replace the cross-mode expectation and add return-destination coverage:

```python
def test_advanced_evidence_links_preserve_personal_research_mode_and_ticker():
    links = advanced_evidence_links("NVDA")

    assert links[0]["href"] == "?mode=research&page=data-health&ticker=NVDA"
    assert links[1]["href"] == "?mode=research&page=proof-history&ticker=NVDA"


def test_research_evidence_return_link_preserves_ticker_or_falls_back_to_desk():
    assert research_evidence_return_link("BRK/B") == {
        "label": "Return to Company Workbench",
        "href": "?mode=research&page=company-workbench&ticker=BRK%2FB&open=1",
        "purpose": "Continue the selected-company review without changing evidence state.",
    }
    assert research_evidence_return_link("")["href"] == "?mode=research&page=research-desk"
```

Use a URL-encoding assertion for a ticker such as `BRK/B`. The implementation must call `quote(..., safe="")`, so the expected query value is `BRK%2FB`.

- [ ] **Step 2: Run the tests and verify red**

Run: `python3 -m pytest tests/test_research_workspace.py -q`

Expected: FAIL because Advanced Evidence still switches modes and `research_evidence_return_link` does not exist.

- [ ] **Step 3: Implement minimal pure routing helpers**

Import `research_evidence_return_link` in the test and implement:

```python
def _quoted_ticker(ticker: str) -> str:
    return quote(str(ticker or "").strip().upper(), safe="")


def advanced_evidence_links(ticker: str) -> list[dict[str, str]]:
    symbol = _quoted_ticker(ticker)
    suffix = f"&ticker={symbol}" if symbol else ""
    return [
        {
            "label": "Open Data Health",
            "href": f"?mode=research&page=data-health{suffix}",
            "purpose": "Inspect blocked inputs and source-proof paths.",
        },
        {
            "label": "Open Proof History",
            "href": f"?mode=research&page=proof-history{suffix}",
            "purpose": "Review evidence that changed a readiness state.",
        },
    ]


def research_evidence_return_link(ticker: str) -> dict[str, str]:
    symbol = _quoted_ticker(ticker)
    if symbol:
        return {
            "label": "Return to Company Workbench",
            "href": f"?mode=research&page=company-workbench&ticker={symbol}&open=1",
            "purpose": "Continue the selected-company review without changing evidence state.",
        }
    return {
        "label": "Return to Research Desk",
        "href": "?mode=research&page=research-desk",
        "purpose": "Return to the primary research workflow without changing evidence state.",
    }
```

- [ ] **Step 4: Verify helper behavior**

Run: `python3 -m pytest tests/test_research_workspace.py -q`

Expected: PASS, including command-free Advanced Evidence HTML tests.

- [ ] **Step 5: Commit the helper slice**

```bash
git add -- src/research_workspace.py tests/test_research_workspace.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Keep research evidence links in workspace"
```

### Task 2: Evidence-page return action and render coverage

**Files:**
- Modify: `src/dashboard.py:330-345,34470-34493`
- Modify: `src/dashboard_render_smoke.py:84-127`
- Test: `tests/test_research_mode_dashboard_contract.py`
- Test: `tests/test_dashboard_render_smoke.py`

**Interfaces:**
- Consumes: `research_evidence_return_link(ticker) -> dict[str, str]` from Task 1.
- Produces: a primary `st.link_button` on research-mode Data Health and Proof History, plus AppTest route contracts for both detours.

- [ ] **Step 1: Write failing dashboard source-order tests**

Add source-contract assertions that each research evidence branch obtains the current ticker, renders the research header, renders `research_evidence_return_link`, then renders the existing page:

```python
def test_research_evidence_detours_offer_return_before_evidence_content():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    data_start = source.index('elif content_page == "Data Health":')
    data_end = source.index('elif content_page == PROOF_HISTORY_PATH_TITLE:', data_start)
    data = source[data_start:data_end]
    proof_start = data_end
    proof_end = source.index('elif content_page == "Universe Manager":', proof_start)
    proof = source[proof_start:proof_end]

    for branch, renderer in ((data, "render_data_health("), (proof, "render_proof_history(")):
        header = branch.index("render_research_workspace_header(")
        return_link = branch.index("research_evidence_return_link(", header)
        button = branch.index("st.link_button(", return_link)
        content = branch.index(renderer, button)
        assert header < return_link < button < content
```

- [ ] **Step 2: Add failing render-route contracts**

Append two `DashboardRenderRoute` entries to `RESEARCH_RENDER_ROUTES`:

```python
DashboardRenderRoute(
    name="Research Data Health",
    query_params=(("mode", "research"), ("page", "data-health"), ("ticker", "NVDA")),
    required_markers=("Data Health", "Return to Company Workbench", "Research-only"),
),
DashboardRenderRoute(
    name="Research Proof History",
    query_params=(("mode", "research"), ("page", "proof-history"), ("ticker", "NVDA")),
    required_markers=("Proof History", "Return to Company Workbench", "Research-only"),
),
```

Extend `tests/test_dashboard_render_smoke.py` to expect the six research route names in order.

- [ ] **Step 3: Run focused tests and verify red**

Run:

```bash
python3 -m pytest tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py -q
```

Expected: FAIL because the return action is not integrated or rendered.

- [ ] **Step 4: Implement the return action in existing branches**

Import `research_evidence_return_link` beside the existing research workspace helpers. In each research-mode evidence branch:

```python
ticker = str(st.query_params.get("ticker") or "").strip().upper()
render_research_workspace_header(..., ticker=ticker, ...)
return_link = research_evidence_return_link(ticker)
st.link_button(return_link["label"], return_link["href"], type="primary")
```

Do not render the button for Public or Operator modes. Leave `render_data_health(..., public_mode=not operator_mode)` and `render_proof_history(public_mode=not operator_mode)` unchanged.

- [ ] **Step 5: Verify route contracts and render smoke**

Run:

```bash
python3 -m pytest tests/test_research_workspace.py tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py -q
make research-dashboard-render-smoke
```

Expected: all six research routes pass; no screenshots or output files are created.

- [ ] **Step 6: Commit the dashboard integration**

```bash
git add -- src/dashboard.py src/dashboard_render_smoke.py tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Add return path for research evidence detours"
```

### Task 3: Documentation, complete verification, and draft PR

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/PERSONAL_RESEARCH_MODE.md`
- Modify: `docs/DASHBOARD_QA.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: `tests/test_public_v1_release_docs.py`
- Update: draft PR #113 comment only after verification.

**Interfaces:**
- Consumes: verified same-mode evidence detours and return action.
- Produces: durable workflow and QA claims bounded to local route continuity.

- [ ] **Step 1: Write failing documentation assertions**

Require ROADMAP, Personal Research Mode, Dashboard QA, and the continuation prompt to state that Data Health and Proof History preserve Personal Research mode and expose a return path without changing readiness or evidence state.

- [ ] **Step 2: Run the documentation contract and verify red**

Run: `python3 -m pytest tests/test_public_v1_release_docs.py -q`

Expected: FAIL because the continuity claim is not yet documented.

- [ ] **Step 3: Update documentation without overstating maturity**

Record that the slice improves local workflow continuity and evidence-review usability. State explicitly that it does not prove source rights, hosted behavior, accessibility compliance, reviewer adoption, market demand, calibration, or product-market fit. Preserve the four primary route hierarchy and secondary Advanced evidence boundary.

- [ ] **Step 4: Run focused and full verification**

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

Expected: executable local gates pass; pilot remains blocked by stale saved readiness; zero generated artifact candidates.

- [ ] **Step 5: Commit and push exact documentation paths**

```bash
git add -- ROADMAP.md docs/PERSONAL_RESEARCH_MODE.md docs/DASHBOARD_QA.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md tests/test_public_v1_release_docs.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Document research evidence detour continuity"
git push origin codex/personal-research-mode-mvp
```

- [ ] **Step 6: Update draft PR #113 and reassess the active goal**

Comment with the behavior, exact test evidence, no-artifact proof, screenshot-audit limitation, and remaining external gates. Verify the PR remains open and draft, branch divergence is zero, and the worktree is clean. Continue the overall goal unless every source, hosted, reviewer, evidence-depth, calibration, and operating gate has direct evidence.
