# Company Workbench Answer-First Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep selected-company lane coverage available under Advanced while making the existing Company Workbench report answer the first expanded research content.

**Architecture:** Wrap the existing selected-ticker coverage cards in a collapsed route-level Streamlit expander before the unchanged single-stock report renderer. Extend source-order and real-browser marker contracts without changing report data, readiness, routes, or helper signatures.

**Tech Stack:** Python 3.12, Streamlit, pytest, source-level dashboard contract tests, Markdown documentation.

## Global Constraints

- Research-only; no recommendation, expected-return ranking, broker integration, order routing, auto-trading, or direct buy/sell instruction.
- Preserve independent actuals, consensus, Revenue, EPS, valuation, catalyst, outcome, backtesting, and calibration readiness states.
- Do not refresh, import, apply, or fabricate source data.
- Keep candidate context unable to modify deterministic scenarios or become trusted evidence.
- Keep generated CSV, JSON, report, sample-report, screenshot, and timing churn unstaged.
- Keep PR #113 draft; do not merge or deploy.

---

### Task 1: Make Company Workbench answer-first

**Files:**
- Modify: `tests/test_research_mode_dashboard_contract.py`
- Modify: `tests/test_public_performance_gate.py`
- Modify: `src/dashboard.py`
- Modify: `src/public_performance_gate.py`
- Modify: `docs/PERSONAL_RESEARCH_MODE.md`
- Modify: `docs/DASHBOARD_QA.md`
- Modify: `ROADMAP.md`

**Interfaces:**
- Consumes: existing `render_company_workbench`, `focused_ticker_coverage_cards`, `render_single_stock_report`, and `RESEARCH_ROUTE_SPECS` contracts.
- Produces: Company Workbench order `header -> selected-company heading -> collapsed lane coverage -> expanded report answer`, with unchanged report and readiness semantics.

- [ ] **Step 1: Write the failing route-order contract test**

```python
def test_company_workbench_keeps_lane_coverage_collapsed_before_report_answer():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    workbench_start = source.index("def render_company_workbench(")
    workbench_end = source.index("\ndef main()", workbench_start)
    workbench = source[workbench_start:workbench_end]

    selected = workbench.index('st.markdown("### Selected Company")')
    advanced = workbench.index(
        'with st.expander("Advanced: selected-company lane coverage", expanded=False):'
    )
    coverage = workbench.index("focused_ticker_coverage_cards(coverage, ticker)", advanced)
    report = workbench.index("render_single_stock_report(", coverage)

    assert selected < advanced < coverage < report
```

- [ ] **Step 2: Run the route test and verify the expected failure**

Run: `python3 -m pytest tests/test_research_mode_dashboard_contract.py::test_company_workbench_keeps_lane_coverage_collapsed_before_report_answer -q`

Expected: FAIL because `Advanced: selected-company lane coverage` does not exist and the cards currently render expanded.

- [ ] **Step 3: Write the failing performance-marker contract**

Add `Advanced: selected-company lane coverage` to the expected Company Workbench full markers in `test_research_performance_contract_covers_the_commercial_beta_workflow`.

Run: `python3 -m pytest tests/test_public_performance_gate.py::test_research_performance_contract_covers_the_commercial_beta_workflow -q`

Expected: FAIL because the Company Workbench route spec does not yet include the new visible label.

- [ ] **Step 4: Implement the minimal route hierarchy**

```python
    st.markdown("### Selected Company")
    with st.expander("Advanced: selected-company lane coverage", expanded=False):
        render_signal_cards(
            focused_ticker_coverage_cards(coverage, ticker),
            show_commands=False,
            variant="queue",
        )
        st.caption(
            "Lane coverage is technical evidence only; blocked and candidate-only states remain separate."
        )
    render_single_stock_report(
```

Add the same Advanced label to the Company Workbench `full_markers` tuple in `src/public_performance_gate.py`.

- [ ] **Step 5: Run focused tests and verify green**

Run: `python3 -m pytest tests/test_research_mode_dashboard_contract.py tests/test_research_workspace.py tests/test_dashboard_render_smoke.py tests/test_public_performance_gate.py -q`

Expected: all focused tests pass with no new warnings or failures.

- [ ] **Step 6: Update workflow, QA, and roadmap documentation**

Document the collapsed selected-company lane context, unchanged report/readiness contracts, desktop and phone first-view acceptance, and this locally implemented Stage 1 slice.

- [ ] **Step 7: Run the full release verification bundle**

Run:

```text
python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make commercial-beta-performance-gate
make public-wording-check
make public-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
```

Expected: every command exits zero; generated churn remains excluded. The pilot checklist may retain truthful manual source, hosting, or review gates while the command succeeds.

- [ ] **Step 8: Stage exact files, verify staged hygiene, commit, and push**

```text
git add -- src/dashboard.py src/public_performance_gate.py tests/test_research_mode_dashboard_contract.py tests/test_public_performance_gate.py ROADMAP.md docs/PERSONAL_RESEARCH_MODE.md docs/DASHBOARD_QA.md docs/superpowers/specs/2026-07-18-company-workbench-answer-first-design.md docs/superpowers/plans/2026-07-18-company-workbench-answer-first.md
make staged-hygiene-check
git diff --cached --check
git commit -m "Prioritize Company Workbench answers"
git push origin codex/personal-research-mode-mvp
```

Expected: exact reviewed files only are committed and pushed; PR #113 remains open and draft.
