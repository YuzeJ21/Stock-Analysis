# Research Desk Answer-First Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put Research Desk's weekly summary, four direct answers, and Discover action before cohort technical context while preserving all cohort evidence under Advanced.

**Architecture:** Move existing focused-cohort and cohort-coverage cards into the top of the existing collapsed Advanced Evidence drawer. Keep all helper outputs and full evidence frames unchanged, and make the browser performance gate measure the weekly summary as the first useful answer.

**Tech Stack:** Python 3.12, Streamlit, pytest, source-level dashboard contract tests, Markdown documentation.

## Global Constraints

- Research-only; no recommendation, expected-return ranking, broker integration, order routing, auto-trading, or direct buy/sell instruction.
- Preserve independent actuals, consensus, Revenue, EPS, valuation, catalyst, outcome, backtesting, and calibration readiness states.
- Do not refresh, import, apply, or fabricate source data.
- Keep candidate context unable to modify deterministic scenarios or become trusted evidence.
- Keep generated CSV, JSON, report, sample-report, screenshot, and timing churn unstaged.
- Keep PR #113 draft; do not merge or deploy.

---

### Task 1: Make Research Desk answer-first

**Files:**
- Modify: `tests/test_research_mode_dashboard_contract.py`
- Modify: `tests/test_public_performance_gate.py`
- Modify: `src/dashboard.py`
- Modify: `src/public_performance_gate.py`
- Modify: `docs/PERSONAL_RESEARCH_MODE.md`
- Modify: `docs/DASHBOARD_QA.md`
- Modify: `ROADMAP.md`

**Interfaces:**
- Consumes: existing `weekly_summary_cards`, `research_desk_cards`, `research_desk_cards_html`, `focused_cohort_cards`, `focused_cohort_coverage_cards`, and `RESEARCH_ROUTE_SPECS` contracts.
- Produces: Research Desk order `header -> weekly summary -> direct answers -> Discover action -> collapsed cohort evidence`, with unchanged data and readiness semantics.

- [ ] **Step 1: Write the failing route-order contract test**

```python
def test_research_desk_renders_answers_before_advanced_cohort_context():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    desk_start = source.index("def render_research_desk(")
    desk_end = source.index("def render_research_monitor(", desk_start)
    desk = source[desk_start:desk_end]

    weekly = desk.index('st.markdown("### Weekly research summary")')
    weekly_cards = desk.index("weekly_summary_cards(weekly_summary)", weekly)
    answers = desk.index("cards = research_desk_cards(", weekly_cards)
    answers_html = desk.index("research_desk_cards_html(cards)", answers)
    discover = desk.index('st.link_button("Open Discover"', answers_html)
    advanced = desk.index('with st.expander("Advanced Evidence", expanded=False):', discover)
    cohort = desk.index("focused_cohort_cards(cohort)", advanced)
    coverage = desk.index("focused_cohort_coverage_cards(coverage)", cohort)
    cohort_frame = desk.index("focused_cohort_frame(cohort)", coverage)
    coverage_frame = desk.index("focused_cohort_coverage_frame(coverage)", cohort_frame)

    assert weekly < weekly_cards < answers < answers_html < discover < advanced
    assert advanced < cohort < coverage < cohort_frame < coverage_frame
```

- [ ] **Step 2: Run the route test and verify the expected failure**

Run: `python3 -m pytest tests/test_research_mode_dashboard_contract.py::test_research_desk_renders_answers_before_advanced_cohort_context -q`

Expected: FAIL because the concise cohort calls occur before the weekly summary and cannot be found after Advanced.

- [ ] **Step 3: Write the failing performance-marker contract**

Require Research Desk's first-useful marker to be `Weekly research summary` and its full markers to be `Weekly research summary`, `What should I review next?`, `Open Discover`, `Advanced Evidence`, and `Research-only`.

Run: `python3 -m pytest tests/test_public_performance_gate.py::test_research_performance_contract_covers_the_commercial_beta_workflow -q`

Expected: FAIL because the existing route spec still uses `Research Desk` as first useful and `Focused cohort` as a visible full marker.

- [ ] **Step 4: Implement the minimal route hierarchy**

Remove the two concise cohort-card calls above `Weekly research summary`. Add them at the top of the existing Advanced Evidence block:

```python
    with st.expander("Advanced Evidence", expanded=False):
        render_signal_cards(focused_cohort_cards(cohort), show_commands=False, variant="queue")
        render_signal_cards(focused_cohort_coverage_cards(coverage), show_commands=False, variant="queue")
        cohort_frame = focused_cohort_frame(cohort)
```

Update the Research Desk `PublicRouteSpec` to:

```python
    PublicRouteSpec(
        "Research Desk",
        "/?mode=research&page=research-desk",
        "Weekly research summary",
        (
            "Weekly research summary",
            "What should I review next?",
            "Open Discover",
            "Advanced Evidence",
            "Research-only",
        ),
        True,
    ),
```

- [ ] **Step 5: Run focused tests and verify green**

Run: `python3 -m pytest tests/test_research_mode_dashboard_contract.py tests/test_research_workspace.py tests/test_dashboard_render_smoke.py tests/test_public_performance_gate.py -q`

Expected: all focused tests pass with no new warnings or failures.

- [ ] **Step 6: Update workflow, QA, and roadmap documentation**

Document the weekly-answer-first order, collapsed cohort context, unchanged evidence boundaries, desktop and phone first-view acceptance, and Monitor as the remaining Stage 1 route audit.

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
git add -- src/dashboard.py src/public_performance_gate.py tests/test_research_mode_dashboard_contract.py tests/test_public_performance_gate.py ROADMAP.md docs/PERSONAL_RESEARCH_MODE.md docs/DASHBOARD_QA.md docs/superpowers/specs/2026-07-18-research-desk-answer-first-design.md docs/superpowers/plans/2026-07-18-research-desk-answer-first.md
make staged-hygiene-check
git diff --cached --check
git commit -m "Prioritize Research Desk answers"
git push origin codex/personal-research-mode-mvp
```

Expected: exact reviewed files only are committed and pushed; PR #113 remains open and draft.
