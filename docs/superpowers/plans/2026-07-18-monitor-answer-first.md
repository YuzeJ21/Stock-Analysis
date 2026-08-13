# Monitor Answer-First Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put Monitor's research-change answer and truthful empty-state action before technical Earnings Nowcast readiness evidence while preserving every queue and readiness contract.

**Architecture:** Reorder existing calls inside `render_research_monitor()` so the weekly summary is followed by the deduplicated queue answer. Add the existing Discover link only for an empty queue, use the neutral context-note treatment, and move unchanged five-company readiness cards into their existing collapsed Advanced drawer.

**Tech Stack:** Python 3.12, Streamlit, pytest, source-level dashboard contract tests, Markdown documentation.

## Global Constraints

- Research-only; no recommendation, expected-return ranking, broker integration, order routing, auto-trading, or direct buy/sell instruction.
- Preserve independent actuals, consensus, Revenue, EPS, valuation, catalyst, outcome, backtesting, and calibration readiness states.
- An empty queue means no saved comparable source-backed change is queued; it never proves that nothing changed in the real world.
- Do not refresh, import, apply, or fabricate source data.
- Keep candidate context unable to modify deterministic scenarios or become trusted evidence.
- Keep generated CSV, JSON, report, sample-report, screenshot, and timing churn unstaged.
- Keep PR #113 draft; do not merge or deploy.

---

### Task 1: Make Monitor answer-first

**Files:**
- Modify: `tests/test_research_mode_dashboard_contract.py`
- Modify: `tests/test_public_performance_gate.py`
- Modify: `src/dashboard.py`
- Modify: `src/public_performance_gate.py`
- Modify: `docs/PERSONAL_RESEARCH_MODE.md`
- Modify: `docs/DASHBOARD_QA.md`
- Modify: `ROADMAP.md`

**Interfaces:**
- Consumes: existing `weekly_summary_cards`, `research_monitor_frame`, `render_context_note`, `load_dashboard_nowcast_cohort`, `cohort_readiness_cards`, and `RESEARCH_ROUTE_SPECS` contracts.
- Produces: Monitor order `header -> weekly summary -> change answer -> empty Discover action when applicable -> collapsed readiness evidence`, with unchanged queue rows and readiness payloads.

- [ ] **Step 1: Write the failing Monitor route-order contract**

Add a complete order contract alongside the existing Monitor integration assertions:

```python
def test_monitor_renders_change_answer_before_advanced_readiness():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    monitor_start = source.index("def render_research_monitor(")
    monitor_end = source.index("def render_company_workbench(", monitor_start)
    monitor = source[monitor_start:monitor_end]

    weekly = monitor.index("weekly_summary_cards(weekly_summary)")
    answer = monitor.index('st.markdown("### Research change monitor")', weekly)
    frame = monitor.index("research_monitor_frame(state.get", answer)
    empty = monitor.index("if frame.empty:", frame)
    note = monitor.index("render_context_note(", empty)
    discover = monitor.index('st.link_button("Open Discover"', note)
    cohort = monitor.index("nowcast_cohort = load_dashboard_nowcast_cohort()", discover)
    advanced = monitor.index(
        'with st.expander("Advanced: five-company Earnings Nowcast readiness", expanded=False):',
        cohort,
    )
    readiness_heading = monitor.index('st.markdown("### Earnings evidence readiness")', advanced)
    readiness_cards = monitor.index("cohort_readiness_cards(nowcast_cohort)", readiness_heading)
    readiness_frame = monitor.index("pd.DataFrame([asdict(row) for row in nowcast_cohort])", readiness_cards)

    assert weekly < answer < frame < empty < note < discover < cohort < advanced
    assert advanced < readiness_heading < readiness_cards < readiness_frame
    assert 'tone="success"' not in monitor[empty:discover]
```

Add a theme contract for the new primary action:

```python
def test_dashboard_theme_keeps_primary_link_button_text_white():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")

    assert '[data-testid="stLinkButton"] a[kind="primary"],' in source
    assert '[data-testid="stLinkButton"] a[kind="primary"] * {' in source
    assert "color: #ffffff !important;" in source[source.index('[data-testid="stLinkButton"] a[kind="primary"],'):]
```

- [ ] **Step 2: Run the route test and verify the expected failure**

Run: `python3 -m pytest tests/test_research_mode_dashboard_contract.py::test_monitor_renders_change_answer_before_advanced_readiness -q`

Expected: FAIL because `Research change monitor` currently occurs after the Nowcast readiness card and there is no empty-state Discover link.

- [ ] **Step 3: Write the failing performance-marker contract**

Extend `test_research_performance_contract_covers_the_commercial_beta_workflow` with:

```python
    assert RESEARCH_ROUTE_SPECS[3].first_useful_marker == "WEEKLY RESEARCH SUMMARY"
    assert RESEARCH_ROUTE_SPECS[3].full_markers == (
        "WEEKLY RESEARCH SUMMARY",
        "Research change monitor",
        "No unresolved evidence change is queued.",
        "Open Discover",
        "Advanced: five-company Earnings Nowcast readiness",
        "Research-only",
    )
```

Run: `python3 -m pytest tests/test_public_performance_gate.py::test_research_performance_contract_covers_the_commercial_beta_workflow -q`

Expected: FAIL because Monitor currently treats the route title as first useful and does not require the primary answer or action.

- [ ] **Step 4: Implement the minimal Monitor hierarchy**

Change `render_research_monitor()` to this composition:

```python
    render_signal_cards(weekly_summary_cards(weekly_summary), show_commands=False, variant="queue")
    st.markdown("### Research change monitor")
    frame = research_monitor_frame(state.get("queue") or ())
    if frame.empty:
        render_context_note(
            "No unresolved evidence change is queued.",
            "This is a monitoring state, not a stock ranking. Continue with Discover or wait for a comparable source-backed change.",
        )
        st.link_button("Open Discover", "?mode=research&page=discover", type="primary")
    else:
        st.dataframe(frame, width="stretch", hide_index=True)
    nowcast_cohort = load_dashboard_nowcast_cohort()
    with st.expander("Advanced: five-company Earnings Nowcast readiness", expanded=False):
        st.markdown("### Earnings evidence readiness")
        render_signal_cards(cohort_readiness_cards(nowcast_cohort), show_commands=False, variant="queue")
        st.dataframe(pd.DataFrame([asdict(row) for row in nowcast_cohort]), width="stretch", hide_index=True)
        st.caption("This board creates no forecast. Missing consensus, Q4, split, backtest, and calibration evidence remain separate blockers.")
```

Update Monitor's `PublicRouteSpec` to:

```python
    PublicRouteSpec(
        "Monitor",
        "/?mode=research&page=monitor",
        "WEEKLY RESEARCH SUMMARY",
        (
            "WEEKLY RESEARCH SUMMARY",
            "Research change monitor",
            "No unresolved evidence change is queued.",
            "Open Discover",
            "Advanced: five-company Earnings Nowcast readiness",
            "Research-only",
        ),
        True,
    ),
```

Keep nested Streamlit Markdown text readable on primary link buttons:

```css
[data-testid="stLinkButton"] a[kind="primary"],
[data-testid="stLinkButton"] a[kind="primary"] * {
  color: #ffffff !important;
}
```

- [ ] **Step 5: Run focused tests and verify green**

Run: `python3 -m pytest tests/test_research_mode_dashboard_contract.py tests/test_research_workspace.py tests/test_dashboard_render_smoke.py tests/test_public_performance_gate.py -q`

Expected: all focused tests pass with no new warnings or failures.

- [ ] **Step 6: Update workflow, QA, and roadmap documentation**

Document the Monitor answer-first order, neutral wait state, conditional Discover action, collapsed five-company readiness evidence, unchanged readiness boundaries, desktop and phone acceptance, and completion of local Stage 1 workflow hardening. Move the next executable roadmap step to one permitted prospective point-in-time consensus source path without claiming that an external dependency is available.

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
git add -- ROADMAP.md docs/DASHBOARD_QA.md docs/PERSONAL_RESEARCH_MODE.md src/dashboard.py src/public_performance_gate.py tests/test_public_performance_gate.py tests/test_research_mode_dashboard_contract.py docs/superpowers/plans/2026-07-18-monitor-answer-first.md docs/superpowers/specs/2026-07-18-monitor-answer-first-design.md
make staged-hygiene-check
git diff --cached --check
git commit -m "Prioritize Monitor answers"
git push origin codex/personal-research-mode-mvp
```

Expected: exact reviewed files only are committed and pushed; PR #113 remains open and draft.
