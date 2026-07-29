# Discover And Monitor Workflow Maturity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Discover explain why a company is reviewable and make Monitor expose deterministic research-process attention without company ranking.

**Architecture:** Discover renders three existing saved-evidence fields with truthful fallbacks. A pure attention adapter composes the immutable six-lane Decision Lab state with optional validated catalyst evidence, preserves focused-cohort order, and gives the dashboard ready-to-render process labels without embedding logic in Streamlit.

**Tech Stack:** Python 3.12, frozen dataclasses, pandas, existing catalyst/outcome/Decision Lab contracts, pytest, Streamlit AppTest, Playwright browser gate.

## Global Constraints

- Discover uses only existing `Why Included`, `Supported Now`, and `Blocked / Missing` saved fields.
- Monitor attention precedence is exactly unresolved evidence change, conflicting evidence, overdue review, invalidation follow-up, outcome evidence follow-up, scheduled catalyst, scheduled review, then monitor.
- Attention labels describe research-process timing only; they are not company rank, attractiveness, severity, expected return, or investment priority.
- Preserve focused-cohort order and the immutable six-lane Decision Lab contract.
- Price, volatility, technical indicators, valuation upside/downside, market capitalization, and candidate context cannot affect attention.
- Empty catalyst/outcome ledgers remain neutral and fabricate no due state.
- Upcoming catalyst evidence is scheduled context only, never urgent or price-predictive.
- Technical identity, exact source metadata, rights blockers, and raw lane detail remain under Advanced.
- No recommendation, score, allocation, holdings, broker, order-routing, auto-trading, or transaction behavior.
- No generated data, broad refresh, readiness rebuild, or ledger write.

---

### Task 1: Discover Three-Question Rows

**Files:**
- Modify: `src/dashboard.py`
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`

**Interfaces:**
- Preserves: `stock_selector_result_table_html(...) -> str`.
- Adds pure helper: `discover_research_answer(row: Mapping[str, object]) -> dict[str, str]` with keys `why_reviewable`, `usable_now`, and `principal_blocker`.

- [ ] **Step 1: Write failing literal row tests**

```python
def test_discover_row_answers_three_saved_research_questions():
    rendered = stock_selector_result_table_html(
        pd.DataFrame(
            [{
                "Ticker": "NVDA",
                "Readiness": "partial",
                "Why Included": "Core company data is ready.",
                "Supported Now": "Price and DCF review.",
                "Blocked / Missing": "Peer evidence remains unavailable.",
            }]
        ),
        total_count=1,
        target_mode="research",
        target_page="company-workbench",
    )
    assert "Why reviewable" in rendered
    assert "Core company data is ready." in rendered
    assert "Usable now" in rendered
    assert "Price and DCF review." in rendered
    assert "Principal blocker" in rendered
    assert "Peer evidence remains unavailable." in rendered
    assert rendered.count("Open NVDA review") == 1
```

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_dashboard_helpers.py tests/test_research_mode_dashboard_contract.py -q`

Expected: FAIL because current compact rows omit why and blocker.

- [ ] **Step 2: Implement escaped fallbacks and compact labelled stack**

Fallbacks:

```python
{
    "why_reviewable": "Saved readiness does not record why this company is reviewable.",
    "usable_now": "No usable research lane is recorded in saved readiness.",
    "principal_blocker": "No principal blocker is recorded in saved readiness; this does not mean no risk or external research need exists.",
}
```

Map blank/NaN values to fallbacks. Normalize exact `no blocker` to the principal-blocker fallback. Escape all values, keep one action, and do not add source commands or scores.

- [ ] **Step 3: Add responsive style assertions**

Require visible labels, text wrapping, one-column phone layout, no clipped text, and a minimum 44-pixel action target. Do not hide any of the three answers on phone.

- [ ] **Step 4: Run focused tests and commit**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_dashboard_helpers.py tests/test_research_mode_dashboard_contract.py -q
git diff --check
git add -- src/dashboard.py tests/test_dashboard_helpers.py tests/test_research_mode_dashboard_contract.py
make staged-hygiene-check
git commit -m "Clarify Discover research routing"
```

### Task 2: Pure Process-Attention Contract

**Files:**
- Modify: `src/research_decision_lab.py`
- Modify: `tests/test_research_decision_lab.py`

**Interfaces:**
- Produces: `ResearchProcessAttention(state: str, label: str, reason: str, source: str)`.
- Produces: `derive_research_process_attention(state: ResearchDecisionLabState, catalyst_timeline: CatalystTimeline | None = None, catalyst_error: str = "") -> ResearchProcessAttention`.
- Extends: `ResearchDisciplineRow` with `attention_state`, `attention_label`, `attention_reason`, and `attention_source`.
- Preserves: `cohort_order`, `ticker`, `status`, `due_lanes`, `next_process_step`, and `identity`.

- [ ] **Step 1: Write failing precedence tests with hand-built lane literals**

```python
def test_unresolved_change_precedes_overdue_and_invalidation():
    state = _decision_state(
        evidence_state="current",
        invalidation_state="missing",
        review_trigger_state="evidence_change_due",
    )
    attention = derive_research_process_attention(state)
    assert attention.state == "evidence_change_due"
    assert attention.label == "Needs review"
    assert attention.source == "review_trigger"
```

Add separate literal tests for conflict, overdue, invalidation, commercial outcome blocker, scheduled catalyst, scheduled review, monitor, and unavailable.

- [ ] **Step 2: Run focused tests and verify missing contract**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_research_decision_lab.py -q`

Expected: FAIL because the attention types and helper do not exist.

- [ ] **Step 3: Implement fixed precedence without sorting**

Read exact lane keys/states. For `scheduled_catalyst`, require
`CatalystTimeline.upcoming` and use the first validated event's exact
`effective_at`; do not use recent events or candidate context to claim an
outstanding review. Apply valid journal/outcome/source-change precedence first;
if none matches and `catalyst_error` is non-empty, return `unavailable` rather
than `monitor`. Never inspect metric or price fields.

- [ ] **Step 4: Extend discipline rows while preserving order and identity**

Pass optional `catalyst_timelines_by_ticker: Mapping[str, CatalystTimeline] | None` into `build_research_discipline_rows`. Do not add attention to Decision Lab identity or mutate its six lanes. Assert input order is unchanged even when later rows need review.

- [ ] **Step 5: Run focused tests and commit**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_research_decision_lab.py -q
git diff --check
git add -- src/research_decision_lab.py tests/test_research_decision_lab.py
make staged-hygiene-check
git commit -m "Add deterministic research process attention"
```

### Task 3: Monitor Read-Only Catalyst Composition and Presentation

**Files:**
- Modify: `src/dashboard.py`
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `tests/test_dashboard_render_smoke.py`

**Interfaces:**
- Extends: `load_dashboard_research_discipline_rows(...)` with read-only catalyst loading.
- Produces: `research_discipline_summary_cards(rows: Iterable[ResearchDisciplineRow]) -> list[dict[str, object]]`.
- Preserves: saved focused-cohort order in `research_discipline_rows(...)`.

- [ ] **Step 1: Write failing empty-ledger and scheduled-catalyst tests**

```python
def test_empty_catalyst_and_outcome_ledgers_do_not_create_attention(tmp_path, monkeypatch):
    rows = load_dashboard_research_discipline_rows(
        _context(tmp_path),
        _cohort("NVDA"),
        (),
        as_of="2026-07-28T12:00:00Z",
    )
    assert rows[0].attention_state in {"monitor", "invalidation_follow_up", "scheduled_review"}
    assert "catalyst" not in rows[0].attention_reason.lower()
    assert "outcome" not in rows[0].attention_reason.lower()
```

Add a validated upcoming catalyst fixture and assert `Scheduled`, exact effective date, no `urgent`, no price language, and no state for a different ticker.

- [ ] **Step 2: Run focused tests and confirm current loader ignores catalyst evidence**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_dashboard_helpers.py tests/test_dashboard_render_smoke.py -q`

Expected: FAIL because catalyst timelines are not passed into discipline composition.

- [ ] **Step 3: Load existing catalyst ledger once and fail per scope**

Use `load_catalyst_events(DATA_DIR / "catalyst_evidence.csv")` once. Build each
timeline with the explicit Monitor `as_of`, selected profile, selected ticker,
and `commercial_mode=True`. A missing ledger is empty. If the shared ledger is
malformed, pass one deterministic `catalyst_error` to every cohort attention
derivation; earlier valid journal/outcome/source-change states still win, but a
row with no earlier state becomes `unavailable`, never `monitor`.

- [ ] **Step 4: Render one summary and preserved-order table**

Place count cards for `Needs review`, `Scheduled`, and `Monitor` above the table. Add `Process attention` and `Why` columns. Keep exact source metadata, catalyst details, rights blockers, identity, and raw lanes under `Advanced: Research Discipline evidence`.

- [ ] **Step 5: Run focused tests and commit**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_research_decision_lab.py tests/test_dashboard_helpers.py tests/test_dashboard_render_smoke.py -q
git diff --check
git add -- src/dashboard.py tests/test_dashboard_helpers.py tests/test_dashboard_render_smoke.py
make staged-hygiene-check
git commit -m "Improve Monitor process attention"
```

### Task 4: Responsive Workflow Evidence and Closeout

**Files:**
- Modify: `src/research_accessibility_browser_gate.py`
- Modify: `tests/test_research_accessibility_browser_gate.py`
- Modify: `ROADMAP.md`
- Modify: `docs/NEXT_STAGE_ROADMAP.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: `docs/superpowers/specs/2026-07-28-discover-monitor-workflow-maturity-design.md`

**Interfaces:**
- Extends direct Research Discover and Monitor browser assertions without screenshots or repository writes.

- [ ] **Step 1: Add failing direct workflow assertions**

For every actual Discover row, require three labels, non-empty values, a unique ticker-bound action, and a 44-pixel target. For Monitor, require preserved displayed cohort order, one process-attention label/reason per row, no rank/score/return columns, and Advanced identity separation.

- [ ] **Step 2: Run desktop and phone browser evidence**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_research_accessibility_browser_gate.py -q
make research-accessibility-browser-check
```

Require Discover and Monitor at `1280x720` and `390x844`, exact route/query retention, zero overflow, zero console/page error, zero traceback, and no fabricated ledger content.

- [ ] **Step 3: Update roadmap and design evidence**

Record exact implementation commit and direct evidence. Keep market validation, independent sessions, source rights, hosted controls, assistive technology, and calibration open.

- [ ] **Step 4: Run full release and hygiene gates**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make public-wording-check
make public-check
make commercial-beta-release-check
make pilot-readiness-check TOP_N=10
make research-accessibility-browser-check
make diff-hygiene-summary
git diff --check
```

- [ ] **Step 5: Stage exact files, commit, push, update PR, and require exact-head CI**

```bash
git add -- src/research_accessibility_browser_gate.py tests/test_research_accessibility_browser_gate.py ROADMAP.md docs/NEXT_STAGE_ROADMAP.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md docs/superpowers/specs/2026-07-28-discover-monitor-workflow-maturity-design.md
make staged-hygiene-check
git diff --cached --check
git commit -m "Verify Discover and Monitor workflow maturity"
git push origin codex/personal-research-mode-mvp
gh pr checks 113 --watch
```

Expected: PR #113 remains open/draft, exact-head CI passes, and the 18 existing generated differences remain unstaged.
