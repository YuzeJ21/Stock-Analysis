# Research Decision Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only six-lane Research Decision Lab to Company Workbench and a no-ranking Research Discipline Review to Monitor.

**Architecture:** A new pure-Python `src/research_decision_lab.py` composes existing immutable journal, decision-process, outcome, change-review, and valuation results into immutable display contracts. `src/dashboard.py` only loads those existing results and renders cards/tables; it adds no persistence, readiness field, route, provider, or generated artifact.

**Tech Stack:** Python 3.12, frozen dataclasses, pandas display frames, Streamlit, pytest, Streamlit AppTest, Chrome performance gate.

## Global Constraints

- Research-only; no investment advice, recommendation, transaction direction, position size, allocation, stop-loss, take-profit, expected return, company score, or broker action.
- Do not import or surface `src/portfolio_review.py` action states.
- Candidate context cannot populate a trusted lane or change forecasts, DCF, readiness, conclusions, or process states.
- Empty, blocked, excluded, invalid, and commercially blocked inputs remain explicit and independent.
- Add no ledger, readiness state, route, provider, generated report, CSV, JSON, screenshot, or timing artifact.
- Preserve the Company Workbench first handoff and uppercase `USE NOW` performance marker.
- Preserve Weekly Research Summary as Monitor's first useful answer and stable focused-cohort order without ranking.
- Keep technical identities, source rows, timestamps, and raw evidence under collapsed Advanced sections.
- Never run `make readiness`, broad refreshes, imports, or apply commands for this feature.
- Never use `git add -A`; stage exact reviewed code, test, and documentation paths only.
- Keep draft PR #113 draft; push only `codex/personal-research-mode-mvp`; do not merge or deploy.

---

### Task 1: Read-only Decision Lab composition contract

**Files:**
- Create: `src/research_decision_lab.py`
- Create: `tests/test_research_decision_lab.py`

**Interfaces:**
- Consumes: `JournalState`, `DecisionProcessScorecard`, `OutcomeStatus`, and an iterable of research-review items.
- Produces: `DecisionLabLane`, `ResearchDecisionLabState`, `ResearchDisciplineRow`, `build_research_decision_lab_state(...)`, `unavailable_research_decision_lab_state(...)`, `build_research_discipline_rows(...)`, `decision_lab_cards(...)`, and `research_discipline_rows(...)`.

- [ ] **Step 1: Write failing immutable-contract and lane-order tests**

```python
def test_empty_history_keeps_six_lanes_independent_and_not_started():
    state = build_research_decision_lab_state(
        profile_key="demo",
        journal_state=empty_journal(),
        scorecard=empty_scorecard(),
        outcome_status=OutcomeStatus("not_started", 0, "", "", "Review later.", 0, ()),
        review_items=(),
    )
    assert [lane.key for lane in state.lanes] == [
        "plan", "evidence", "invalidation", "scenario", "review_trigger", "learning"
    ]
    assert {lane.key: lane.state for lane in state.lanes} == {
        "plan": "not_started", "evidence": "not_started", "invalidation": "missing",
        "scenario": "blocked", "review_trigger": "not_started", "learning": "not_started",
    }
```

- [ ] **Step 2: Run the new module tests and verify RED**

Run: `python3 -m pytest tests/test_research_decision_lab.py -q`

Expected: collection fails because `src.research_decision_lab` does not exist.

- [ ] **Step 3: Implement frozen contracts and deterministic mapping**

```python
@dataclass(frozen=True)
class DecisionLabLane:
    key: str
    label: str
    state: str
    answer: str
    evidence: str
    next_step: str


@dataclass(frozen=True)
class ResearchDecisionLabState:
    profile_key: str
    ticker: str
    status: str
    lanes: tuple[DecisionLabLane, ...]
    next_process_step: str
    boundary: str
    identity: str


@dataclass(frozen=True)
class ResearchDisciplineRow:
    cohort_order: int
    ticker: str
    status: str
    due_lanes: tuple[str, ...]
    next_process_step: str
    identity: str
```

Use the existing scorecard checks by key. Map Plan from `thesis_documented`; Evidence from `evidence_recorded` plus `conflicting_evidence_reviewed`; Invalidation from `invalidation_documented`; Scenario from `dcf_assumptions_visible`; Review trigger from matching open review items plus the journal due state; and Learning from `OutcomeStatus`. Hash the normalized contract with SHA-256 for deterministic identity.

- [ ] **Step 4: Run lane tests and verify GREEN**

Run: `python3 -m pytest tests/test_research_decision_lab.py -q`

Expected: the empty-state and immutable-contract tests pass.

- [ ] **Step 5: Add failing priority, fail-closed, and language tests**

```python
@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("conflict", "Review recorded conflicting evidence"),
        ("overdue", "Review the overdue thesis"),
        ("missing_thesis", "Record a current reviewer-authored thesis"),
        ("missing_invalidation", "Record a source-backed invalidation condition"),
        ("missing_evidence", "Record source-backed research evidence"),
        ("unscheduled", "Schedule the next evidence review"),
        ("missing_dcf_assumptions", "Restore visible DCF assumptions"),
    ],
)
def test_next_process_step_uses_approved_priority(mutation, expected):
    assert build_state(mutation).next_process_step.startswith(expected)


def test_contract_contains_no_transaction_or_allocation_language():
    rendered = str(build_state("complete")).lower()
    for forbidden in ("buy", "sell", "position size", "allocation", "stop loss", "take profit"):
        assert forbidden not in rendered
```

Also cover later review clearing only the conflict gap, DCF blocked/excluded/ready, commercial learning blocker, mismatch `ValueError`, invalid-journal unavailable state, lane independence, deterministic identity, stable cohort ordering, and no severity sorting.

- [ ] **Step 6: Implement the approved priority and cohort composition**

Select the first applicable gap in this exact order: conflict without later review; overdue thesis; missing thesis; missing invalidation; missing evidence; unscheduled review; DCF ready without visible assumptions; otherwise continue monitoring. `build_research_discipline_rows` must preserve the caller's focused-cohort order and use ticker only as a deterministic tie-break, never process severity or market value.

- [ ] **Step 7: Verify the complete composition slice**

Run:

```bash
python3 -m pytest tests/test_research_decision_lab.py tests/test_decision_process_scorecard.py tests/test_research_thesis_journal.py tests/test_research_outcome_review.py -q
python3 -m pytest tests -q
make dashboard-smoke research-dashboard-render-smoke public-wording-check public-check
make pilot-readiness-check TOP_N=10
make pr-range-hygiene-check diff-hygiene-summary
git diff --check
```

Expected: all commands exit zero except pilot readiness may remain truthfully blocked by excluded generated churn or external gates; no generated artifact is added.

- [ ] **Step 8: Stage, verify, commit, push, update PR, and require exact-head CI**

```bash
git add -- src/research_decision_lab.py tests/test_research_decision_lab.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Add research decision lab composition"
git push origin codex/personal-research-mode-mvp
```

Update draft PR #113 with the slice evidence and wait for the `local-engineering-gate` check on the pushed SHA to pass before Task 2.

---

### Task 2: Company Workbench integration

**Files:**
- Modify: `src/dashboard.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`
- Modify: `tests/test_dashboard_render_smoke.py`
- Modify: `tests/test_public_performance_gate.py`

**Interfaces:**
- Consumes: `build_research_decision_lab_state`, `unavailable_research_decision_lab_state`, and `decision_lab_cards` from Task 1.
- Produces: one Workbench `Research Decision Lab` section and one collapsed `Advanced: Decision Lab evidence` disclosure.

- [ ] **Step 1: Write failing source-order and render tests**

```python
def test_workbench_places_one_decision_lab_after_what_changed_before_business_trend():
    render = report_renderer_source()
    what_changed = render.index('st.markdown("### What Changed")')
    decision_lab = render.index('st.markdown("### Research Decision Lab")')
    business_trend = render.index('st.markdown("### Business Trend")')
    assert what_changed < decision_lab < business_trend
    assert render.count('st.markdown("### Research Decision Lab")') == 1
```

Add AppTest assertions that the route contains all six lane labels, `Next process step`, Research Conclusion, and Next Research Task; that `USE NOW` occurs first; and that technical identity is inside a collapsed Advanced disclosure.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python3 -m pytest tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py tests/test_public_performance_gate.py -q`

Expected: failures show the missing Workbench section and markers.

- [ ] **Step 3: Compose state once and render the compact summary**

Build the existing `DecisionProcessScorecard` once after the journal/outcome payloads load. If the journal is invalid, build one compact unavailable Decision Lab state using the existing verification error. After `What Changed`, render six compact cards and the next process step. Reuse the same scorecard in the existing collapsed scorecard section; do not replace Research Conclusion or Next Research Task.

- [ ] **Step 4: Keep technical evidence collapsed**

```python
with st.expander("Advanced: Decision Lab evidence", expanded=False):
    st.dataframe(decision_lab_frame(decision_lab_state), width="stretch", hide_index=True)
    st.caption(f"Decision Lab identity: {decision_lab_state.identity}")
    st.caption(decision_lab_state.boundary)
```

- [ ] **Step 5: Verify Workbench behavior and responsive performance**

Run:

```bash
python3 -m pytest tests/test_research_decision_lab.py tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py tests/test_public_performance_gate.py -q
python3 -m pytest tests -q
make dashboard-smoke research-dashboard-render-smoke public-wording-check public-check browser-qa-evidence
make commercial-beta-performance-gate commercial-beta-release-check
make pilot-readiness-check TOP_N=10
make pr-range-hygiene-check diff-hygiene-summary
git diff --check
```

Expected: desktop and `390x844` Workbench cases pass, uppercase `USE NOW` remains first useful evidence under three seconds, and no horizontal-overflow or duplicate-section failure appears.

- [ ] **Step 6: Stage, verify, commit, push, update PR, and require exact-head CI**

```bash
git add -- src/dashboard.py tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py tests/test_public_performance_gate.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Integrate decision lab into company workbench"
git push origin codex/personal-research-mode-mvp
```

Update draft PR #113 with Workbench placement, responsive, and performance evidence; require exact-head CI before Task 3.

---

### Task 3: Monitor Research Discipline Review

**Files:**
- Modify: `src/dashboard.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`
- Modify: `tests/test_dashboard_render_smoke.py`
- Modify: `tests/test_public_performance_gate.py`

**Interfaces:**
- Consumes: `FocusedCohort`, existing saved journal/outcome ledgers, existing research-review items, and Task 1 cohort rows.
- Produces: `load_dashboard_research_discipline_rows(...)`, a compact `Research Discipline Review`, and collapsed Advanced evidence.

- [ ] **Step 1: Write failing cohort-load, order, empty-state, and placement tests**

```python
def test_monitor_places_discipline_review_after_weekly_summary_before_change_monitor():
    monitor = monitor_renderer_source()
    weekly = monitor.index("weekly_summary_cards(weekly_summary)")
    discipline = monitor.index('st.markdown("### Research Discipline Review")')
    changes = monitor.index('st.markdown("### Research change monitor")')
    assert weekly < discipline < changes


def test_monitor_discipline_rows_preserve_focused_cohort_order_without_rank():
    assert [row.ticker for row in rows] == ["BBB", "AAA"]
    assert "rank" not in str(rows).lower()
```

Add an empty-state assertion that says no process item is due from saved reviewer-authored evidence and does not claim no risk, no research need, or no market event.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python3 -m pytest tests/test_research_decision_lab.py tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py -q`

Expected: failures show the missing Monitor loader and section.

- [ ] **Step 3: Implement one read-only cohort loader**

Load journal and outcome ledgers once, derive each focused ticker independently, construct only saved readiness context needed by the existing scorecard, and convert failures for one ticker to an unavailable state without promoting another ticker. Do not fetch, refresh, build generated reports, or pad the cohort.

- [ ] **Step 4: Render the review after Weekly Research Summary**

Render a compact table with `Ticker`, `Process state`, `Due lanes`, and `Next process step`. Keep identity and evidence rows under `Advanced: Research Discipline evidence`. Render the existing Research change monitor afterward so market/source-change state stays independent.

- [ ] **Step 5: Verify Monitor behavior and responsive performance**

Run:

```bash
python3 -m pytest tests/test_research_decision_lab.py tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py tests/test_public_performance_gate.py -q
python3 -m pytest tests -q
make dashboard-smoke research-dashboard-render-smoke public-wording-check public-check browser-qa-evidence
make commercial-beta-performance-gate commercial-beta-release-check
make pilot-readiness-check TOP_N=10
make pr-range-hygiene-check diff-hygiene-summary
git diff --check
```

Expected: Monitor remains within desktop/phone thresholds, Weekly Research Summary remains first useful evidence, stable cohort order is preserved, and empty process evidence creates no market or risk claim.

- [ ] **Step 6: Stage, verify, commit, push, update PR, and require exact-head CI**

```bash
git add -- src/dashboard.py tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py tests/test_public_performance_gate.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Add monitor research discipline review"
git push origin codex/personal-research-mode-mvp
```

Update draft PR #113 with Monitor ordering, empty-state, and no-ranking evidence; require exact-head CI before Task 4.

---

### Task 4: Documentation and release evidence

**Files:**
- Modify: `README.md` only if the current public feature summary materially omits the implemented workflow
- Modify: `ROADMAP.md`
- Modify: `docs/METHODOLOGY.md`
- Modify: `docs/PROVENANCE_CONTRACT.md`
- Modify: `docs/PERSONAL_RESEARCH_MODE.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: `docs/internal/RESEARCH_DECISION_LAB_CONTINUATION_GOAL_PROMPT.md`
- Modify: browser-QA contract source and its focused tests only if current markers require Decision Lab coverage
- Test: `tests/test_public_v1_release_docs.py`

**Interfaces:**
- Consumes: verified Task 1-3 behavior and exact current command outputs.
- Produces: acceptance-criterion evidence map, current roadmap state, continuation contract, public-safe product explanation, and exact-head draft-PR evidence.

- [ ] **Step 1: Write failing documentation contract tests**

```python
def test_personal_research_docs_define_decision_lab_without_trading_scope():
    text = Path("docs/PERSONAL_RESEARCH_MODE.md").read_text(encoding="utf-8")
    assert "Research Decision Lab" in text
    assert "Research Discipline Review" in text
    assert "no new ledger" in text.lower()
```

Add assertions for six lane names, independent fail-closed states, Company Workbench and Monitor placement, and the broader external maturity boundary.

- [ ] **Step 2: Run docs tests and verify RED**

Run: `python3 -m pytest tests/test_public_v1_release_docs.py tests/test_launchers.py -q`

Expected: failures identify missing implemented-status and methodology/provenance wording.

- [ ] **Step 3: Update docs and roadmap with verified evidence only**

Mark the Decision Lab local implementation complete only after Tasks 1-3 are committed and pushed. Document that it composes saved evidence read-only; it does not prove source coverage, predictive accuracy, investment performance, independent adoption, hosted reliability, commercial demand, competitive superiority, or product-market fit. Update the dedicated continuation prompt to route to the next locally executable or external gate without repeating completed Decision Lab work.

- [ ] **Step 4: Audit README and browser-QA markers**

Change README only if the answer-first public workflow materially benefits from one concise Decision Lab sentence. Update browser-QA markers without replacing screenshots; existing screenshots remain route/product evidence only until explicitly recaptured and reviewed.

- [ ] **Step 5: Run the complete release matrix**

Run:

```bash
python3 -m pytest tests/test_public_v1_release_docs.py tests/test_launchers.py tests/test_research_decision_lab.py tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py tests/test_public_performance_gate.py -q
python3 -m pytest tests -q
make dashboard-smoke research-dashboard-render-smoke public-wording-check public-check browser-qa-evidence
make commercial-beta-performance-gate commercial-beta-release-check
make pilot-readiness-check TOP_N=10
make pr-range-hygiene-check diff-hygiene-summary
git diff --check
```

Expected: local code, full tests, route renders, wording, browser contract, performance, release, and hygiene pass; pilot or external gates remain blocked only where current evidence says so.

- [ ] **Step 6: Map every acceptance criterion to current evidence**

Record each design criterion as `proven`, `contradicted`, `incomplete`, `indirect`, or `missing`. Evidence must name the exact test/gate and current revision; screenshot-only, fixture-only, local-only, stale, or indirect evidence cannot prove a broader gate.

- [ ] **Step 7: Stage exact docs/tests, verify, commit, and push**

```bash
git add -- ROADMAP.md docs/METHODOLOGY.md docs/PROVENANCE_CONTRACT.md docs/PERSONAL_RESEARCH_MODE.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md docs/internal/RESEARCH_DECISION_LAB_CONTINUATION_GOAL_PROMPT.md tests/test_public_v1_release_docs.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Document research decision lab evidence"
git push origin codex/personal-research-mode-mvp
```

Add README or browser-QA files to the exact staging command only if Step 4 required and verified them.

- [ ] **Step 8: Update draft PR and require exact-head CI**

Update PR #113 with the final acceptance map, exact local verification, generated-artifact exclusion, and external dependency classifications. Keep it draft. Confirm `headRefOid` equals local HEAD and `local-engineering-gate` succeeds on that exact SHA. Do not merge or deploy.
