# Evidence Monitor Brief Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the repetitive Monitor summary/table presentation with one compact, read-only four-question Evidence Monitor Brief while preserving every existing evidence, ordering, readiness, research-only, accessibility, and no-write contract.

**Architecture:** A pure view composer in `src/research_workspace.py` receives already-built weekly-summary and discipline-row objects plus existing freshness interpretations. `src/dashboard.py` renders that immutable result, filters only exact `monitor` rows from the primary table, and keeps the complete discipline evidence under Advanced; browser and release contracts prove the responsive layout and repository no-write boundary.

**Tech Stack:** Python 3.12, frozen dataclasses, pandas, Streamlit, existing `WeeklyResearchSummary`, `ResearchDisciplineRow`, `ProfileContext`, and `ObservationRecencySet` contracts, pytest, Streamlit AppTest/render smoke, Playwright accessibility browser gate.

## Global Constraints

- The implementation is one Monitor presentation slice; do not change Research Desk, Discover, or Company Workbench behavior.
- Reuse the existing one-pass journal, outcome, catalyst, change-queue, cohort, profile, and observation-recency loads; do not add a second loader or source of truth.
- Preserve the fixed seven-day `WeeklyResearchSummary`; do not add `7D / 30D / 90D` controls.
- Preserve existing Research Decision Lab attention precedence and saved `cohort_order`; filtering exact `monitor` rows is not ranking.
- `Unavailable` stays visible in the primary view and remains distinct from `Needs review`.
- Scheduled context is research-process context, not a comprehensive catalyst watch, urgency signal, forecast, or verified-catalyst claim.
- Saved-readiness freshness and market-observation recency remain independent and visibly labelled.
- No probability, confidence percentage, rank, score, expected return, recommendation, portfolio action, allocation, position size, entry/exit, risk budget, trade trigger, buy/sell instruction, broker integration, order routing, or auto-trading.
- No market-regime, liquidity, rates, cross-asset, news, or risk-appetite composite.
- Candidate context cannot modify deterministic forecasts or become trusted evidence; synthetic fixtures remain test-only.
- Actuals, consensus, Revenue, EPS, valuation, catalysts, outcomes, backtesting, calibration, readiness, and observation recency remain independent.
- Q4 requires explicit SEC-filed Q4 table evidence; EPS split basis remains unverified without explicit proof.
- Ordinary Monitor use performs no refresh, import, apply, materialization, append, export, network, provider, or persistence operation.
- Do not create or stage CSV, JSON, Excel, HTML-report, PDF, report, sample-report, screenshot, timing, readiness, canonical-data, manual-review, journal, catalyst, outcome, or proof artifacts.
- Keep the existing 18 dirty generated CSV/report/output paths byte-for-byte unchanged and unstaged; never use `git add -A`.
- Technical identities, raw timestamps, sources, lane detail, and complete `Monitor` rows stay under Advanced.
- Keep `WEEKLY RESEARCH SUMMARY` as the Monitor first-useful marker.
- Desktop renders an exact two-by-two card grid; `390x844` renders one column with visible text labels and no horizontal overflow.
- Do not push, update PR #113, merge, or deploy until the full local matrix passes and the final exact file set is reviewed.

---

### Task 1: Pure Evidence Monitor Brief View Contract

**Files:**
- Modify: `src/research_workspace.py`
- Modify: `tests/test_research_workspace.py`

**Interfaces:**
- Consumes: `WeeklyResearchSummary` and `Iterable[ResearchDisciplineRow]` plus four already-derived freshness strings.
- Produces: `EvidenceMonitorCard(key: str, kicker: str, title: str, body: str, badges: tuple[str, ...])`.
- Produces: `EvidenceMonitorBrief(cards: tuple[EvidenceMonitorCard, ...], primary_rows: tuple[ResearchDisciplineRow, ...], monitor_count: int)`.
- Produces: `build_evidence_monitor_brief(summary: WeeklyResearchSummary, rows: Iterable[ResearchDisciplineRow], *, readiness_state: str, readiness_message: str, observation_state: str, observation_message: str) -> EvidenceMonitorBrief`.
- Preserves: `weekly_summary_cards(...)`, `research_monitor_frame(...)`, every `ResearchDisciplineRow` field, and input order.

- [ ] **Step 1: Reconfirm the clean implementation baseline and protected dirty set**

Run:

```bash
git status --short --branch
git rev-parse HEAD
git rev-list --left-right --count origin/codex/personal-research-mode-mvp...HEAD
git diff --cached --name-only
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_research_workspace.py tests/test_research_decision_lab.py -q
make diff-hygiene-summary
```

Expected: focused tests pass; the index is empty; only the approved design/plan commits may be ahead of origin; exactly the pre-existing 18 generated paths remain unstaged. Stop if product/code/test/doc changes other than the approved design and plan are present.

- [ ] **Step 2: Write the failing immutable-composition tests**

Add these imports and fixtures to `tests/test_research_workspace.py`:

```python
from src.research_decision_lab import ResearchDisciplineRow
from src.research_workspace import build_evidence_monitor_brief
from src.weekly_research_summary import WeeklyResearchSummary, WeeklySummaryItem


def _discipline_row(order: int, ticker: str, state: str, label: str, reason: str):
    return ResearchDisciplineRow(
        cohort_order=order,
        ticker=ticker,
        status="ready",
        due_lanes=(),
        next_process_step=reason,
        identity=f"identity-{ticker}",
        attention_state=state,
        attention_label=label,
        attention_reason=reason,
        attention_source="research_process",
    )


def _weekly_summary(*items: WeeklySummaryItem) -> WeeklyResearchSummary:
    return WeeklyResearchSummary(
        status="review_required" if items else "no_changes",
        as_of="2026-08-04T00:00:00+00:00",
        cohort_size=4,
        unique_event_count=len(items),
        items=tuple(items),
        message=(
            f"{len(items)} traceable cohort research item(s) require review or monitoring."
            if items
            else "No traceable cohort evidence change requires review this week."
        ),
    )
```

Add an order/filter/card test:

```python
def test_evidence_monitor_brief_composes_four_questions_without_ranking():
    rows = (
        _discipline_row(0, "AAA", "monitor", "Monitor", "No saved process item is due."),
        _discipline_row(1, "BBB", "conflict_review_needed", "Needs review", "Conflicting saved evidence needs review."),
        _discipline_row(2, "CCC", "scheduled_review", "Scheduled", "Reviewer-authored review is scheduled for 2026-08-20."),
        _discipline_row(3, "DDD", "unavailable", "Unavailable", "Catalyst evidence could not be verified."),
    )
    result = build_evidence_monitor_brief(
        _weekly_summary(),
        rows,
        readiness_state="current",
        readiness_message="Saved readiness is current.",
        observation_state="stale",
        observation_message="Market observations are historical context only.",
    )

    assert [card.key for card in result.cards] == [
        "weekly",
        "follow_up",
        "scheduled",
        "freshness",
    ]
    assert result.cards[0].kicker == "WEEKLY RESEARCH SUMMARY"
    assert "0 traceable" in result.cards[0].title
    assert "1 needs review" in result.cards[1].title
    assert "1 unavailable" in result.cards[1].title
    assert "1 scheduled" in result.cards[2].title
    assert result.cards[3].badges == (
        "saved readiness: current",
        "market observation: stale",
    )
    assert [row.ticker for row in result.primary_rows] == ["BBB", "CCC", "DDD"]
    assert result.monitor_count == 1
```

Add evidence-language and empty-input tests:

```python
def test_evidence_monitor_brief_keeps_candidate_and_freshness_states_truthful():
    candidate = _discipline_row(
        0,
        "AAA",
        "scheduled_catalyst",
        "Scheduled",
        "Candidate-only catalyst context is scheduled for review.",
    )
    result = build_evidence_monitor_brief(
        _weekly_summary(),
        (candidate,),
        readiness_state="working_artifact_uncommitted",
        readiness_message="Saved readiness is not release evidence.",
        observation_state="unavailable",
        observation_message="No current market observation is available.",
    )
    rendered = " ".join(
        " ".join((card.kicker, card.title, card.body, *card.badges))
        for card in result.cards
    )
    assert "candidate-only" in rendered.lower()
    assert "verified catalyst" not in rendered.lower()
    assert "source-backed catalyst" not in rendered.lower()
    assert "working_artifact_uncommitted" in rendered
    assert "market observation: unavailable" in rendered.lower()


def test_evidence_monitor_brief_empty_rows_do_not_invent_monitoring_evidence():
    result = build_evidence_monitor_brief(
        _weekly_summary(),
        (),
        readiness_state="unavailable",
        readiness_message="Saved readiness is unavailable.",
        observation_state="unavailable",
        observation_message="Market observation is unavailable.",
    )
    assert result.primary_rows == ()
    assert result.monitor_count == 0
    assert "0 needs review" in result.cards[1].title
    assert "0 scheduled" in result.cards[2].title
    assert "no saved" in result.cards[1].body.lower()
```

- [ ] **Step 3: Run the focused tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_research_workspace.py::test_evidence_monitor_brief_composes_four_questions_without_ranking \
  tests/test_research_workspace.py::test_evidence_monitor_brief_keeps_candidate_and_freshness_states_truthful \
  tests/test_research_workspace.py::test_evidence_monitor_brief_empty_rows_do_not_invent_monitoring_evidence -q
```

Expected: collection fails because `build_evidence_monitor_brief` does not exist.

- [ ] **Step 4: Implement the minimal pure view composer**

In `src/research_workspace.py`, import `dataclass` and `ResearchDisciplineRow`, then add:

```python
@dataclass(frozen=True)
class EvidenceMonitorCard:
    key: str
    kicker: str
    title: str
    body: str
    badges: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceMonitorBrief:
    cards: tuple[EvidenceMonitorCard, ...]
    primary_rows: tuple[ResearchDisciplineRow, ...]
    monitor_count: int


def build_evidence_monitor_brief(
    summary: WeeklyResearchSummary,
    rows: Iterable[ResearchDisciplineRow],
    *,
    readiness_state: str,
    readiness_message: str,
    observation_state: str,
    observation_message: str,
) -> EvidenceMonitorBrief:
    ordered = tuple(rows)
    primary_rows = tuple(row for row in ordered if row.attention_state != "monitor")
    monitor_count = sum(row.attention_state == "monitor" for row in ordered)
    needs_review = tuple(row for row in ordered if row.attention_label == "Needs review")
    unavailable = tuple(row for row in ordered if row.attention_state == "unavailable")
    scheduled = tuple(row for row in ordered if row.attention_label == "Scheduled")

    follow_up_body = (
        needs_review[0].attention_reason
        if needs_review
        else unavailable[0].attention_reason
        if unavailable
        else "No saved research-process follow-up is currently due."
    )
    scheduled_body = (
        scheduled[0].attention_reason
        if scheduled
        else "No saved research-process context is currently scheduled."
    )
    normalized_readiness = str(readiness_state or "unavailable").strip()
    normalized_observation = str(observation_state or "unavailable").strip()
    readiness_body = str(readiness_message or "Saved readiness is unavailable.").strip()
    observation_body = str(observation_message or "Market observation is unavailable.").strip()

    cards = (
        EvidenceMonitorCard(
            "weekly",
            "WEEKLY RESEARCH SUMMARY",
            f"{len(summary.items)} traceable item{'s' if len(summary.items) != 1 else ''}",
            summary.message,
            (summary.status.replace("_", " "), "7-day saved window", f"{summary.cohort_size} companies"),
        ),
        EvidenceMonitorCard(
            "follow_up",
            "RESEARCH FOLLOW-UP",
            f"{len(needs_review)} needs review; {len(unavailable)} unavailable",
            follow_up_body,
            ("process timing", "not a company score", f"{monitor_count} monitor"),
        ),
        EvidenceMonitorCard(
            "scheduled",
            "SCHEDULED CONTEXT",
            f"{len(scheduled)} scheduled",
            scheduled_body,
            ("saved process context", "not urgency"),
        ),
        EvidenceMonitorCard(
            "freshness",
            "EVIDENCE FRESHNESS",
            f"Readiness {normalized_readiness}; observation {normalized_observation}",
            f"Saved readiness: {readiness_body} Market observation: {observation_body}",
            (
                f"saved readiness: {normalized_readiness}",
                f"market observation: {normalized_observation}",
            ),
        ),
    )
    return EvidenceMonitorBrief(cards, primary_rows, monitor_count)
```

Do not add I/O, pandas, sorting, scoring, dates, provider calls, or a second attention derivation to this function.

- [ ] **Step 5: Run GREEN, regression, hygiene, and commit**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_research_workspace.py tests/test_research_decision_lab.py -q
git diff --check
git add -- src/research_workspace.py tests/test_research_workspace.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Add evidence monitor brief contract"
```

Expected: focused tests and hygiene pass; only the two exact files enter the commit; all 18 generated paths remain unstaged.

### Task 2: Monitor Presentation Recomposition

**Files:**
- Modify: `src/dashboard.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`
- Modify: `tests/test_dashboard_render_smoke.py`

**Interfaces:**
- Consumes: `build_evidence_monitor_brief(...) -> EvidenceMonitorBrief` from Task 1.
- Extends: `render_signal_cards(..., variant="evidence-monitor")` with exact desktop two-column and phone one-column styling.
- Preserves: `render_research_monitor(...)`, `research_monitor_frame(...)`, `research_discipline_table_html(...)`, `research_discipline_rows(...)`, and Advanced identity rendering.
- Removes: the now-unused dashboard-only `research_discipline_summary_cards(...)` after `rg` confirms it has no remaining caller.

- [ ] **Step 1: Write failing source-order, filtering, and responsive-class tests**

Replace the current Monitor order assertion in `tests/test_research_mode_dashboard_contract.py` with:

```python
def test_monitor_recomposes_existing_answers_before_advanced_readiness():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    monitor_start = source.index("def render_research_monitor(")
    monitor_end = source.index("def render_company_workbench(", monitor_start)
    monitor = source[monitor_start:monitor_end]

    brief_heading = monitor.index('st.markdown("## Evidence Monitor Brief")')
    brief_build = monitor.index("build_evidence_monitor_brief(", brief_heading)
    brief_render = monitor.index('variant="evidence-monitor"', brief_build)
    discipline = monitor.index('st.markdown("## Research Discipline Review")', brief_render)
    primary_rows = monitor.index("brief.primary_rows", discipline)
    change = monitor.index('st.markdown("## Research change monitor")', primary_rows)
    advanced_discipline = monitor.index(
        'with st.expander("Advanced: Research Discipline evidence", expanded=False):',
        change,
    )
    complete_frame = monitor.index("st.dataframe(discipline_frame", advanced_discipline)
    identity_table = monitor.index("research_discipline_identity_table_html(discipline)", complete_frame)
    advanced_nowcast = monitor.index(
        'with st.expander("Advanced: five-company Earnings Nowcast readiness", expanded=False):',
        identity_table,
    )

    assert brief_heading < brief_build < brief_render < discipline < primary_rows
    assert primary_rows < change < advanced_discipline < complete_frame < identity_table < advanced_nowcast
    assert "weekly_summary_cards(weekly_summary)" not in monitor
    assert "research_discipline_summary_cards(discipline)" not in monitor
    assert "research_discipline_table_html(discipline)" not in monitor[:change]
```

Add exact class and mobile override assertions:

```python
def test_evidence_monitor_grid_is_two_by_two_then_one_column_on_phone():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    assert '"evidence-monitor": "signal-grid evidence-monitor-grid"' in source
    assert ".signal-grid.evidence-monitor-grid {" in source
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in source
    phone = source[source.index("@media (max-width: 760px)") :]
    assert ".signal-grid.evidence-monitor-grid" in phone
    assert "grid-template-columns: 1fr;" in phone
```

Delete `test_research_discipline_summary_counts_process_labels_without_ranking`;
Task 1's pure composer tests replace that dashboard-only summary contract.
Replace `test_monitor_discipline_empty_state_is_process_only` with:

```python
def test_monitor_discipline_empty_state_is_process_only():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    monitor_start = source.index("def render_research_monitor(")
    monitor_end = source.index("def render_company_workbench(", monitor_start)
    monitor = source[monitor_start:monitor_end]

    assert "remain in saved monitoring state" in monitor
    assert "no saved process transition is currently due" in monitor
    assert "This does not claim that no market event, risk, or external research need exists." in monitor
    assert "research-monitor-neutral" in monitor
    assert "research_discipline_summary_cards" not in monitor
    assert '"Process attention"' in Path("src/research_decision_lab.py").read_text(encoding="utf-8")
```

Update `tests/test_dashboard_render_smoke.py` so the Monitor route requires, in order:

```python
required_markers=(
    "Evidence Monitor Brief",
    "WEEKLY RESEARCH SUMMARY",
    "RESEARCH FOLLOW-UP",
    "SCHEDULED CONTEXT",
    "EVIDENCE FRESHNESS",
    "Research Discipline Review",
    "Research change monitor",
    "Advanced: Research Discipline evidence",
    "Research-only",
)
```

Rename its focused test to
`test_monitor_renders_evidence_brief_before_filtered_discipline_without_ranking`
and assert:

```python
assert rendered.index("Evidence Monitor Brief") < rendered.index("WEEKLY RESEARCH SUMMARY")
assert rendered.index("WEEKLY RESEARCH SUMMARY") < rendered.index("RESEARCH FOLLOW-UP")
assert rendered.index("RESEARCH FOLLOW-UP") < rendered.index("SCHEDULED CONTEXT")
assert rendered.index("SCHEDULED CONTEXT") < rendered.index("EVIDENCE FRESHNESS")
assert rendered.index("EVIDENCE FRESHNESS") < rendered.index("Research Discipline Review")
assert rendered.index("Research Discipline Review") < rendered.index("Research change monitor")
assert "company rank" not in rendered.lower()
assert "expected return" not in rendered.lower()
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_research_mode_dashboard_contract.py::test_monitor_recomposes_existing_answers_before_advanced_readiness \
  tests/test_research_mode_dashboard_contract.py::test_evidence_monitor_grid_is_two_by_two_then_one_column_on_phone \
  tests/test_dashboard_render_smoke.py::test_monitor_renders_evidence_brief_before_filtered_discipline_without_ranking -q
```

Expected: FAIL because the route still renders separate weekly/discipline cards and no evidence-monitor grid exists.

- [ ] **Step 3: Add the dedicated card-grid variant**

Change `render_signal_cards` to select classes without changing existing variants:

```python
grid_class = {
    "queue": "signal-grid queue-grid",
    "evidence-monitor": "signal-grid evidence-monitor-grid",
}.get(variant, "signal-grid")
```

Add the desktop rule beside the existing signal-grid CSS:

```css
.signal-grid.evidence-monitor-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
```

Add `.signal-grid.evidence-monitor-grid` to the existing phone selector that sets `grid-template-columns: 1fr`. Do not change other signal-card grids.

- [ ] **Step 4: Recompose `render_research_monitor` from existing objects**

After the existing one-pass discipline load, build and render the brief:

```python
profile_observation = (
    observation_recency.profile_price_lane
    if observation_recency is not None
    else None
)
brief = build_evidence_monitor_brief(
    weekly_summary,
    discipline,
    readiness_state=context.freshness_state,
    readiness_message=context.freshness_message,
    observation_state=(profile_observation.state if profile_observation else "unavailable"),
    observation_message=(
        _observation_recency_message(profile_observation)
        if profile_observation is not None
        else "Market observation is unavailable."
    ),
)
st.markdown("## Evidence Monitor Brief")
render_signal_cards(
    [asdict(card) for card in brief.cards],
    show_commands=False,
    variant="evidence-monitor",
)
```

Then render only non-`monitor` primary rows:

```python
st.markdown("## Research Discipline Review")
discipline_frame = pd.DataFrame(research_discipline_rows(discipline))
if brief.primary_rows:
    st.markdown(
        research_discipline_table_html(brief.primary_rows),
        unsafe_allow_html=True,
    )
elif discipline:
    company_word = "company" if brief.monitor_count == 1 else "companies"
    st.markdown(
        "<div class='research-monitor-neutral'>"
        + context_note_html(
            f"{brief.monitor_count} {company_word} remain in saved monitoring state; "
            "no saved process transition is currently due.",
            "This does not claim that no market event, risk, or external research need exists.",
        )
        + "</div>",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        "<div class='research-monitor-neutral'>"
        + context_note_html(
            "Saved research-process evidence is unavailable.",
            "No company state is inferred from missing evidence.",
        )
        + "</div>",
        unsafe_allow_html=True,
    )
```

Move `Advanced: Research Discipline evidence` below the existing Research
change monitor. Inside it, render `discipline_frame` as the complete stable-
order table before the existing identity table. Keep raw columns and identities
out of the primary view.

Remove the old standalone weekly card call, the three-card discipline summary
call, and the dashboard-only `research_discipline_summary_cards(...)`
definition. Confirm the removed name has no remaining source or test reference:

```bash
if rg -n "research_discipline_summary_cards" src tests; then exit 1; fi
```

- [ ] **Step 5: Run GREEN, render regression, hygiene, and commit**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_research_workspace.py \
  tests/test_research_decision_lab.py \
  tests/test_research_mode_dashboard_contract.py \
  tests/test_dashboard_render_smoke.py -q
PYTHONDONTWRITEBYTECODE=1 python3 -m src.no_write_artifact_guard \
  --project-root . -- python3 -m src.dashboard_render_smoke --routes research
git diff --check
git add -- src/dashboard.py tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Recompose Monitor evidence brief"
```

Expected: focused/render checks pass; the no-write guard reports no protected mutation; only the three exact files enter this commit; the existing 18 generated paths stay byte-identical and unstaged.

### Task 3: Direct Responsive, Accessibility, And No-Write Evidence

**Files:**
- Modify: `src/research_accessibility_browser_gate.py`
- Modify: `src/public_performance_gate.py`
- Modify: `tests/test_research_accessibility_browser_gate.py`
- Modify: `tests/test_public_performance_gate.py`
- Modify: `tests/test_dashboard_render_smoke.py`

**Interfaces:**
- Changes the Monitor browser answer selector to `.signal-grid.evidence-monitor-grid`.
- Extends: `evaluate_monitor_rows(...)` to validate a filtered ordered subsequence or a truthful all-monitor empty state while keeping Advanced identity evidence complete.
- Adds: `_monitor_brief_assertion(page, viewport_width: int) -> dict[str, object]` for exact four-card labels and two-column/one-column geometry.
- Preserves: exact route/query retention, semantic main, skip link, focus, media preferences, runtime warnings, no-overflow, and repository-content snapshots.

- [ ] **Step 1: Write failing evaluator tests for filtered and all-monitor states**

Replace the existing Monitor evaluator test with:

```python
def test_monitor_row_contract_accepts_filtered_order_and_rejects_monitor_or_rank_fields():
    from src.research_accessibility_browser_gate import evaluate_monitor_rows

    passed = evaluate_monitor_rows(
        (
            {
                "cohort_order": 1,
                "ticker": "BBB",
                "attention": "Needs review",
                "reason": "Conflicting saved evidence needs review.",
            },
            {
                "cohort_order": 4,
                "ticker": "EEE",
                "attention": "Scheduled",
                "reason": "Reviewer-authored review is scheduled.",
            },
        ),
        primary_columns=("TICKER", "PROCESS ATTENTION", "WHY"),
        advanced_identity_count=5,
        neutral_visible=False,
    )
    all_monitor = evaluate_monitor_rows(
        (),
        primary_columns=(),
        advanced_identity_count=5,
        neutral_visible=True,
    )
    leaked_monitor = evaluate_monitor_rows(
        ({"cohort_order": 0, "ticker": "AAA", "attention": "Monitor", "reason": "Wait."},),
        primary_columns=("Ticker", "Process attention", "Why"),
        advanced_identity_count=5,
        neutral_visible=False,
    )
    ranked = evaluate_monitor_rows(
        ({"cohort_order": 2, "ticker": "CCC", "attention": "Scheduled", "reason": "Saved review."},),
        primary_columns=("Ticker", "Process attention", "Return score"),
        advanced_identity_count=5,
        neutral_visible=False,
    )

    assert passed["passed"] is True
    assert all_monitor["passed"] is True
    assert leaked_monitor["passed"] is False
    assert "monitor row" in str(leaked_monitor["detail"]).lower()
    assert ranked["passed"] is False
    assert "rank/score/return" in str(ranked["detail"])
```

Add a pure geometry evaluator so unit tests do not depend on Playwright objects:

```python
def test_monitor_brief_geometry_requires_two_columns_on_desktop_and_one_on_phone():
    from src.research_accessibility_browser_gate import evaluate_monitor_brief

    desktop = evaluate_monitor_brief(
        kickers=("WEEKLY RESEARCH SUMMARY", "RESEARCH FOLLOW-UP", "SCHEDULED CONTEXT", "EVIDENCE FRESHNESS"),
        boxes=((0, 0), (500, 0), (0, 180), (500, 180)),
        viewport_width=1280,
    )
    phone = evaluate_monitor_brief(
        kickers=("WEEKLY RESEARCH SUMMARY", "RESEARCH FOLLOW-UP", "SCHEDULED CONTEXT", "EVIDENCE FRESHNESS"),
        boxes=((0, 0), (0, 180), (0, 360), (0, 540)),
        viewport_width=390,
    )
    wrong_phone = evaluate_monitor_brief(
        kickers=("WEEKLY RESEARCH SUMMARY", "RESEARCH FOLLOW-UP", "SCHEDULED CONTEXT", "EVIDENCE FRESHNESS"),
        boxes=((0, 0), (180, 0), (0, 180), (180, 180)),
        viewport_width=390,
    )
    assert desktop["passed"] is True
    assert phone["passed"] is True
    assert wrong_phone["passed"] is False
```

- [ ] **Step 2: Run the focused evaluator tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_research_accessibility_browser_gate.py::test_monitor_row_contract_accepts_filtered_order_and_rejects_monitor_or_rank_fields \
  tests/test_research_accessibility_browser_gate.py::test_monitor_brief_geometry_requires_two_columns_on_desktop_and_one_on_phone -q
```

Expected: FAIL because the evaluator still requires contiguous complete primary rows and the brief evaluator does not exist.

- [ ] **Step 3: Update the pure browser evaluators and live Monitor assertion**

Change `evaluate_monitor_rows` to:

- accept `neutral_visible: bool`;
- allow zero primary rows only when the neutral state is visible and Advanced has at least one identity row;
- require strictly increasing, unique `cohort_order` values rather than a contiguous range;
- reject any primary row labelled `Monitor`;
- require exact primary columns only when a primary table exists;
- require `advanced_identity_count >= len(primary_rows)` and never equality; and
- reject a simultaneous non-empty primary table and neutral all-monitor message.

Add `evaluate_monitor_brief(...)` with the exact four kicker sequence. Treat x/y coordinates within two CSS pixels as the same column/row. Require two x positions and two y positions for viewports wider than 760 pixels; require one x position and four increasing y positions at 760 pixels or narrower.

Change the Monitor `ResearchRoute` primary selector to:

```python
".signal-grid.evidence-monitor-grid"
```

Add `_monitor_brief_assertion(page, viewport_width)` to read the four visible cards, non-empty titles/bodies/badges, and bounding-box coordinates before calling the pure evaluator. Update `_monitor_rows_assertion(page)` to accept zero or one primary table, inspect `.research-monitor-neutral`, open Advanced, count complete identity rows, and call the revised evaluator.

In the initial Monitor route branch, append both assertions:

```python
assertions.append(_monitor_brief_assertion(page, viewport[0]))
assertions.append(_monitor_rows_assertion(page))
```

- [ ] **Step 4: Update performance and render markers without changing thresholds**

Keep `RESEARCH_ROUTE_SPECS[3].first_useful_marker == "WEEKLY RESEARCH SUMMARY"`. Replace its full markers with:

```python
(
    "WEEKLY RESEARCH SUMMARY",
    "RESEARCH FOLLOW-UP",
    "SCHEDULED CONTEXT",
    "EVIDENCE FRESHNESS",
    "Research Discipline Review",
    "Research change monitor",
    "No unresolved evidence change is queued.",
    "Open Discover",
    "Advanced: five-company Earnings Nowcast readiness",
    "Research-only",
)
```

Update `tests/test_public_performance_gate.py` and the Monitor render-smoke assertions to require the new markers in order. Do not relax the existing one-second warm shell, three-second first-useful, or settle thresholds.

- [ ] **Step 5: Run focused, guarded render, direct browser, hygiene, and commit**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_research_accessibility_browser_gate.py \
  tests/test_public_performance_gate.py \
  tests/test_dashboard_render_smoke.py \
  tests/test_research_mode_dashboard_contract.py -q
PYTHONDONTWRITEBYTECODE=1 python3 -m src.no_write_artifact_guard \
  --project-root . -- python3 -m src.dashboard_render_smoke --routes research
make research-accessibility-browser-check TIMEOUT_SECONDS=90
make commercial-beta-performance-gate TIMEOUT_SECONDS=90
git diff --check
git add -- \
  src/research_accessibility_browser_gate.py \
  src/public_performance_gate.py \
  tests/test_research_accessibility_browser_gate.py \
  tests/test_public_performance_gate.py \
  tests/test_dashboard_render_smoke.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Verify evidence monitor workflow"
```

Expected: both viewports pass exact four-card geometry, route/focus/runtime/no-overflow assertions, filtered-or-neutral row behavior, and repository-content snapshots; performance writes only its explicit `/tmp` evidence; no repository artifact changes.

### Task 4: Documentation, Full Release Matrix, And Draft-PR Evidence

**Files:**
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `docs/PERSONAL_RESEARCH_MODE.md`
- Modify: `docs/DASHBOARD_QA.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: `docs/superpowers/specs/2026-08-04-evidence-monitor-brief-design.md`
- Modify: `tests/test_public_v1_release_docs.py`

**Interfaces:**
- Documents the verified Monitor presentation without changing roadmap priority state or external unblock conditions.
- Preserves: local Commercial Research Beta release-candidate positioning, research-only boundaries, current external blockers, and draft PR #113.

- [ ] **Step 1: Write the failing documentation contract**

Add to `tests/test_public_v1_release_docs.py`:

```python
def test_release_docs_describe_the_evidence_monitor_brief_without_market_or_trade_claims():
    readme = Path("README.md").read_text(encoding="utf-8")
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")
    personal = Path("docs/PERSONAL_RESEARCH_MODE.md").read_text(encoding="utf-8")
    qa = Path("docs/DASHBOARD_QA.md").read_text(encoding="utf-8")
    combined = "\n".join((readme, roadmap, personal, qa)).lower()

    assert "evidence monitor brief" in readme.lower()
    assert "weekly research summary" in personal.lower()
    assert "research follow-up" in personal.lower()
    assert "scheduled context" in personal.lower()
    assert "evidence freshness" in personal.lower()
    assert "monitor rows remain under advanced" in personal.lower()
    assert "evidence monitor brief" in roadmap.lower()
    assert "evidence monitor brief" in qa.lower()
    assert "confidence percentage" not in combined
    assert "risk budget" not in combined
    assert "trade trigger" not in combined
```

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_public_v1_release_docs.py::test_release_docs_describe_the_evidence_monitor_brief_without_market_or_trade_claims -q
```

Expected: FAIL because the verified feature wording is not yet present.

- [ ] **Step 2: Update public and operator documentation with exact evidence level**

Use this public-safe README sentence:

```text
Monitor begins with a read-only Evidence Monitor Brief covering the saved weekly summary, research follow-up, scheduled process context, and independent readiness/observation freshness; non-actionable Monitor rows stay available under Advanced instead of filling the primary page.
```

Update `docs/PERSONAL_RESEARCH_MODE.md` to replace the old Monitor order with:

```text
Evidence Monitor Brief -> Research Discipline Review -> Research change monitor
```

State explicitly that the brief reuses the fixed seven-day summary and existing discipline precedence, only filters exact `Monitor` rows from the primary table, preserves full rows under Advanced, and writes nothing during ordinary route use.

Add a dated `docs/DASHBOARD_QA.md` entry only after the direct desktop/phone gate passes. Record the exact tested commit, both `1280x720` and `390x844`, four visible labels, desktop two-by-two, phone one-column, filtered-or-neutral rows, full Advanced identities, no overflow/traceback/runtime errors, and protected repository content unchanged. Label it automated local engineering evidence, not human accessibility or market validation.

Add one bounded completed-local sentence to `ROADMAP.md` without renumbering Priorities 4-10 or changing any external blocker. Update the continuation prompt with the exact implementation anchor and the same no-write/research-only boundaries. Change the design spec status from approved design to verified implementation only after every local gate in Step 4 passes.

- [ ] **Step 3: Run documentation and focused product checks**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_public_v1_release_docs.py \
  tests/test_research_workspace.py \
  tests/test_research_mode_dashboard_contract.py \
  tests/test_dashboard_render_smoke.py \
  tests/test_public_performance_gate.py \
  tests/test_research_accessibility_browser_gate.py -q
make public-wording-check
make research-dashboard-render-smoke
git diff --check
```

Expected: all focused tests and wording/render checks pass; no protected artifact changes.

- [ ] **Step 4: Run the full local release and protected-artifact matrix once**

Capture the current 18 protected dirty-path hashes before the matrix, then run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make public-wording-check
make public-check
make commercial-beta-performance-gate TIMEOUT_SECONDS=90
make commercial-beta-release-check
make pilot-readiness-check TOP_N=10
make research-accessibility-browser-check TIMEOUT_SECONDS=90
make diff-hygiene-summary
git diff --check
```

Expected: every applicable gate passes. Compare protected hashes after the matrix and require exact equality. Do not rerun an unchanged environment failure; classify it once, retain all completed local evidence, and continue with any remaining safe verification.

- [ ] **Step 5: Stage exact documentation/test files and commit the verified closeout**

Run:

```bash
git add -- \
  README.md \
  ROADMAP.md \
  docs/PERSONAL_RESEARCH_MODE.md \
  docs/DASHBOARD_QA.md \
  docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md \
  docs/superpowers/specs/2026-08-04-evidence-monitor-brief-design.md \
  tests/test_public_v1_release_docs.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Document evidence monitor brief"
```

Expected: only the seven exact files enter this commit; no generated, manual-review, screenshot, timing, or sample-report path is staged.

- [ ] **Step 6: Push the exact branch, update the draft PR, and require exact-head CI**

Before pushing, verify:

```bash
git status --short --branch
git diff --cached --name-only
git log -6 --oneline --decorate
git rev-list --left-right --count origin/codex/personal-research-mode-mvp...HEAD
```

Then:

```bash
git push origin codex/personal-research-mode-mvp
gh pr view 113 --json number,state,isDraft,headRefName,headRefOid,mergeable,url
gh pr checks 113 --watch
gh run list --branch codex/personal-research-mode-mvp --limit 5
```

Before the comment command, use `apply_patch` to create
`/tmp/pr-113-evidence-monitor-brief.md` with these exact sections populated
from the just-completed evidence: `Evidence Monitor Brief`, `Verified local
checks`, `No-write and generated-artifact evidence`, and `Still not proven`.
List only commands that actually passed, write the literal current HEAD and CI
run rather than a placeholder, state that the same 18 protected generated paths
remain unstaged, and preserve the external source, hosted, human-accessibility,
independent-session, and calibration gates as incomplete.

Post the reviewed evidence comment, then re-read the PR state:

```bash
gh pr comment 113 --body-file /tmp/pr-113-evidence-monitor-brief.md
gh pr view 113 --json number,state,isDraft,headRefName,headRefOid,mergeable,url
git rev-list --left-right --count origin/codex/personal-research-mode-mvp...HEAD
```

Expected final state: PR #113 remains open and draft, `headRefOid` equals local
HEAD, exact-head CI passes, branch divergence is `0 0`, and the only working-
tree changes are the same byte-identical 18 unstaged generated paths. Do not
merge or deploy.

## Plan Self-Review Result

- Every design acceptance criterion maps to Tasks 1-4.
- The pure composer formats existing objects only; it defines no second evidence, catalyst, attention, readiness, or freshness semantics.
- Candidate-only scheduled context is never called verified.
- Primary filtering preserves an ordered subsequence and keeps `Unavailable`; complete rows and identities remain under Advanced.
- Desktop/phone geometry, non-color labels, route/focus behavior, no overflow, no-write, performance, and release evidence have direct tests or gates.
- No placeholder, broad provider work, new persistence, generated report, market-regime model, probability, ranking, recommendation, or transaction behavior is included.
