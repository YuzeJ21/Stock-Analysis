# Discover Answer-First Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put Discover's readiness-backed company selector before cohort evidence while preserving all cohort and readiness context under Advanced.

**Architecture:** Reorder existing Streamlit composition calls in the Discover branch of `src/dashboard.py`. Keep the existing selector, focused-cohort cards, coverage cards, routes, and data contracts unchanged; only move the cards into a collapsed route-specific expander after the selector.

**Tech Stack:** Python 3.12, Streamlit, pytest, source-level dashboard contract tests, Markdown documentation.

## Global Constraints

- Research-only; no recommendation, expected-return ranking, broker integration, order routing, auto-trading, or direct buy/sell instruction.
- Preserve independent readiness states and deterministic focused-cohort membership.
- Do not refresh, import, apply, or fabricate source data.
- Keep generated CSV, JSON, report, sample-report, screenshot, and timing churn unstaged.
- Keep PR #113 draft; do not merge or deploy.

---

### Task 1: Make Discover selection-first

**Files:**
- Modify: `tests/test_research_mode_dashboard_contract.py`
- Modify: `src/dashboard.py`
- Modify: `tests/test_public_performance_gate.py`
- Modify: `src/public_performance_gate.py`
- Modify: `docs/PERSONAL_RESEARCH_MODE.md`
- Modify: `docs/DASHBOARD_QA.md`
- Modify: `ROADMAP.md`

**Interfaces:**
- Consumes: existing `render_stock_selector`, `focused_cohort_cards`, `focused_cohort_coverage_cards`, `focused_cohort`, and `focused_cohort_coverage` contracts.
- Produces: Discover route order `header -> selector -> collapsed cohort readiness context`, with unchanged Company Workbench links and readiness semantics.

- [ ] **Step 1: Write the failing route-order contract test**

```python
def test_research_discover_renders_selector_before_advanced_cohort_context():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    discover_start = source.index('elif research_mode and selected_page == "Discover":')
    discover_end = source.index('elif research_mode and selected_page == "Company Workbench":', discover_start)
    discover = source[discover_start:discover_end]

    heading = discover.index('st.markdown("### Which stock can I review?")')
    selector = discover.index("render_stock_selector(", heading)
    advanced = discover.index('with st.expander("Advanced: cohort readiness context", expanded=False):')
    cohort = discover.index("focused_cohort_cards(focused_cohort)", advanced)
    coverage = discover.index("focused_cohort_coverage_cards(focused_cohort_coverage)", advanced)

    assert heading < selector < advanced < cohort < coverage
```

- [ ] **Step 2: Run the test and verify the expected failure**

Run: `python3 -m pytest tests/test_research_mode_dashboard_contract.py::test_research_discover_renders_selector_before_advanced_cohort_context -q`

Expected: FAIL because `Advanced: cohort readiness context` does not exist and the cohort cards currently render before the selector.

- [ ] **Step 3: Implement the minimal route reordering**

```python
        st.markdown("### Which stock can I review?")
        render_stock_selector(
            output_frames,
            public_mode=True,
            target_mode=RESEARCH_MODE,
            target_page="company-workbench",
            allowed_tickers=tuple(member.ticker for member in focused_cohort.members),
        )
        with st.expander("Advanced: cohort readiness context", expanded=False):
            render_signal_cards(focused_cohort_cards(focused_cohort), show_commands=False, variant="queue")
            render_signal_cards(
                focused_cohort_coverage_cards(focused_cohort_coverage),
                show_commands=False,
                variant="queue",
            )
            st.caption(
                "Cohort membership and lane coverage remain evidence context only; "
                "they do not rank expected return or create a recommendation."
            )
```

- [ ] **Step 4: Run focused tests and verify green**

Run: `python3 -m pytest tests/test_research_mode_dashboard_contract.py tests/test_research_workspace.py tests/test_dashboard_render_smoke.py tests/test_public_performance_gate.py -q`

Expected: all focused tests pass with no new warnings or failures.

- [ ] **Step 4a: Align the real-browser visible-marker contract test-first**

Require Discover's performance contract to use `Which stock can I review?` as the first useful marker and `Search this review queue`, `Advanced: cohort readiness context`, and `Research-only` as visible full-settle evidence. Run the focused performance-contract test red against the stale `Focused cohort` marker, update `RESEARCH_ROUTE_SPECS`, then rerun the focused performance and route suite green.

- [ ] **Step 5: Update the workflow, QA, and roadmap documentation**

Document the selector-first Discover order, collapsed cohort context, unchanged readiness boundaries, and first-viewport acceptance rule. Record the slice as implemented only after focused verification passes.

- [ ] **Step 6: Run the full release verification bundle**

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

Expected: every command exits zero; generated churn remains excluded.

- [ ] **Step 7: Stage exact files, verify staged hygiene, commit, and push**

```text
git add -- src/dashboard.py src/public_performance_gate.py tests/test_research_mode_dashboard_contract.py tests/test_public_performance_gate.py ROADMAP.md docs/PERSONAL_RESEARCH_MODE.md docs/DASHBOARD_QA.md docs/superpowers/specs/2026-07-18-discover-answer-first-design.md docs/superpowers/plans/2026-07-18-discover-answer-first.md
make staged-hygiene-check
git diff --cached --check
git commit -m "Prioritize Discover company selection"
git push origin codex/personal-research-mode-mvp
```

Expected: exact reviewed files only are committed and pushed; PR #113 remains draft.
