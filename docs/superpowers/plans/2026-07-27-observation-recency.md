# Observation Recency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an independent, read-only market-observation recency contract that keeps saved readiness separate from the selected ticker, profile price lane, SPY, and QQQ dates.

**Architecture:** A focused `src/observation_recency.py` module parses caller-supplied CSV rows or one explicitly selected `prices.csv` without fallback or writes. Dashboard presentation consumes immutable results and shows exact dates in the primary answer while keeping policy, path, and excluded-row diagnostics under Advanced evidence.

**Tech Stack:** Python 3, standard-library `csv`, frozen dataclasses, Streamlit HTML helpers, pytest, Streamlit AppTest.

## Global Constraints

- Seven calendar days is the exact local threshold: `current` when `age_days <= 7`, otherwise `stale_review_only`.
- Valid observations must be on or before the explicit review date; malformed and future dates are excluded and counted.
- Missing files, unreadable files, and absent tickers fail closed as `unavailable`.
- `ProfileContext.freshness_state` remains saved-readiness state and must not be derived from observation recency.
- No provider fetch, refresh, import, readiness rebuild, canonical write, generated artifact, or ledger mutation.
- No forecast, probability, ranking, expected-return score, recommendation, allocation, or transaction direction.
- Primary copy shows exact dates and state; file path, threshold, and excluded counts stay under Advanced evidence.
- Generated CSV, JSON, report, sample-report, screenshot, timing, canonical-data, and manual-review churn remain unstaged.

---

### Task 1: Pure Observation-Recency Evaluator

**Files:**
- Create: `src/observation_recency.py`
- Create: `tests/test_observation_recency.py`

**Interfaces:**
- Consumes: iterable CSV-shaped mappings with `ticker` and `date`; explicit `as_of: datetime.date`.
- Produces: `ObservationRecency(scope: str, through_date: str, age_days: int | None, state: str, message: str, excluded_date_count: int)`.
- Produces: `ObservationRecencySet(selected_ticker: ObservationRecency, profile_price_lane: ObservationRecency, benchmarks: tuple[ObservationRecency, ...], policy_days: int, source_path: str, as_of: str)`.
- Produces: `evaluate_observation_rows(rows: Iterable[Mapping[str, object]], *, selected_ticker: str, benchmark_tickers: tuple[str, ...] = ("SPY", "QQQ"), as_of: date, source_path: str = "") -> ObservationRecencySet`.
- Produces: `load_observation_recency(prices_path: Path, *, selected_ticker: str, benchmark_tickers: tuple[str, ...] = ("SPY", "QQQ"), as_of: date) -> ObservationRecencySet`.

- [ ] **Step 1: Write evaluator tests that fail before the module exists**

```python
from datetime import date

from src.observation_recency import evaluate_observation_rows


def test_observation_recency_keeps_scopes_independent_and_excludes_bad_dates():
    result = evaluate_observation_rows(
        [
            {"ticker": "AVGO", "date": "2026-07-20"},
            {"ticker": "AVGO", "date": "2026-08-01"},
            {"ticker": "SPY", "date": "2026-07-19"},
            {"ticker": "QQQ", "date": "not-a-date"},
        ],
        selected_ticker="AVGO",
        as_of=date(2026, 7, 27),
    )
    assert (result.selected_ticker.state, result.selected_ticker.age_days) == ("current", 7)
    assert result.selected_ticker.excluded_date_count == 1
    assert result.benchmarks[0].state == "stale_review_only"
    assert result.benchmarks[1].state == "unavailable"
    assert result.profile_price_lane.through_date == "2026-07-20"
```

- [ ] **Step 2: Run the new focused test and confirm the expected import failure**

Run: `python3 -m pytest tests/test_observation_recency.py -q`

Expected: FAIL because `src.observation_recency` does not exist.

- [ ] **Step 3: Implement frozen result types, strict date parsing, and pure scope evaluation**

```python
CURRENT_MAX_AGE_DAYS = 7


@dataclass(frozen=True)
class ObservationRecency:
    scope: str
    through_date: str
    age_days: int | None
    state: str
    message: str
    excluded_date_count: int = 0


def _result(scope: str, dates: list[date], excluded: int, as_of: date) -> ObservationRecency:
    if not dates:
        return ObservationRecency(
            scope, "", None, "unavailable",
            "No valid observation is available on or before the review date.", excluded
        )
    latest = max(dates)
    age_days = (as_of - latest).days
    state = "current" if age_days <= CURRENT_MAX_AGE_DAYS else "stale_review_only"
    message = (
        "Observation is within the seven-calendar-day local review policy."
        if state == "current"
        else "Historical context only; do not use for a current-market interpretation."
    )
    return ObservationRecency(scope, latest.isoformat(), age_days, state, message, excluded)
```

Complete `evaluate_observation_rows` by normalizing tickers to uppercase, evaluating the selected ticker, the entire profile lane, and each exact benchmark separately. Complete `load_observation_recency` using `csv.DictReader`; catch `OSError`, `UnicodeError`, and `csv.Error` and return unavailable results instead of raising.

- [ ] **Step 4: Add boundary, file-failure, missing-scope, and current-fixture tests**

```python
def test_existing_profile_prices_are_stale_or_unavailable_without_writes():
    project_root = Path(__file__).resolve().parents[1]
    result = load_observation_recency(
        project_root / "data" / "prices.csv",
        selected_ticker="AVGO",
        as_of=date(2026, 7, 27),
    )
    assert result.selected_ticker.state in {"stale_review_only", "unavailable"}
    assert {row.scope: row.state for row in result.benchmarks}["SPY"] == "stale_review_only"
    assert {row.scope: row.state for row in result.benchmarks}["QQQ"] == "stale_review_only"
```

Also assert an exactly seven-day-old value is current, an eight-day-old value is stale, a missing file returns all scopes unavailable, and one missing benchmark does not alter the selected ticker.

- [ ] **Step 5: Run focused tests**

Run: `python3 -m pytest tests/test_observation_recency.py -q`

Expected: PASS.

- [ ] **Step 6: Commit the evaluator**

```bash
git add src/observation_recency.py tests/test_observation_recency.py
git commit -m "Add independent observation recency evaluator"
```

### Task 2: Truthful Dashboard Presentation

**Files:**
- Modify: `src/dashboard.py`
- Modify: `src/research_workspace.py`
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `tests/test_research_workspace.py`

**Interfaces:**
- Consumes: `ObservationRecencySet` from Task 1.
- Produces: `observation_recency_strip_html(result: ObservationRecencySet, *, include_selected: bool) -> str`.
- Produces: `observation_recency_advanced_details(result: ObservationRecencySet) -> dict[str, object]`.
- Preserves: existing `research_workspace_header_html(...)` call compatibility and `ProfileContext.freshness_state`.

- [ ] **Step 1: Write failing helper tests for exact labels and withheld wording**

```python
def test_profile_strip_labels_saved_readiness_not_generic_freshness(profile_context):
    rendered = profile_trust_strip_html(profile_context)
    assert "<small>Saved readiness</small>" in rendered
    assert "<small>Freshness</small>" not in rendered


def test_stale_observation_strip_exposes_date_without_current_market_claim(stale_recency):
    rendered = observation_recency_strip_html(stale_recency, include_selected=True)
    assert "2026-05-22" in rendered
    assert "Historical context only" in rendered
    assert "current-market" not in rendered.lower().replace("no current-market", "")
```

- [ ] **Step 2: Run the helper tests and confirm they fail**

Run: `python3 -m pytest tests/test_dashboard_helpers.py tests/test_research_workspace.py -q`

Expected: FAIL on the old `Freshness` label and missing observation helpers.

- [ ] **Step 3: Implement one shared HTML renderer and Advanced diagnostics**

Render the profile lane on all four Personal Research routes. On Company Workbench, also render the selected ticker, SPY, and QQQ. Each item must contain scope, exact `through_date` or `Unavailable`, state, and the approved fail-closed message. Escape every value with `html.escape`.

Advanced details must use these exact keys:

```python
{
    "Policy threshold": "7 calendar days",
    "Source path": result.source_path or "Unavailable",
    "Review date": result.as_of,
    "Excluded dates": {
        row.scope: row.excluded_date_count
        for row in (result.selected_ticker, result.profile_price_lane, *result.benchmarks)
    },
}
```

Relabel profile trust-strip copy to `Saved readiness`, its `aria-label` to `Selected data profile and saved readiness`, and Advanced `Freshness detail` to `Saved readiness detail`.

- [ ] **Step 4: Run the focused helper tests**

Run: `python3 -m pytest tests/test_dashboard_helpers.py tests/test_research_workspace.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the presentation helpers**

```bash
git add src/dashboard.py src/research_workspace.py tests/test_dashboard_helpers.py tests/test_research_workspace.py
git commit -m "Show truthful market observation recency"
```

### Task 3: Four-Route Integration and Evidence Boundaries

**Files:**
- Modify: `src/dashboard.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`
- Modify: `tests/test_dashboard_render_smoke.py`
- Modify: `ROADMAP.md`
- Modify: `docs/METHODOLOGY.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`

**Interfaces:**
- Consumes: `load_observation_recency(context.data_dir / "prices.csv", selected_ticker=ticker, as_of=review_date)`.
- Produces: one recency evaluation per dashboard run, passed read-only into Research Desk, Discover, Company Workbench, and Monitor renderers.

- [ ] **Step 1: Add failing route and no-write contract tests**

```python
def test_personal_research_routes_do_not_render_ambiguous_freshness_label():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")
    assert "<small>Freshness</small>" not in source
    assert "Saved readiness" in source
    assert "load_observation_recency" in source
```

Extend render-smoke fixtures so Company Workbench includes AVGO, SPY, and QQQ independently and every route contains the profile-lane observation state.

- [ ] **Step 2: Run the focused contract tests and confirm failure**

Run: `python3 -m pytest tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py -q`

Expected: FAIL until all four routes receive the new result.

- [ ] **Step 3: Integrate the evaluator once per dashboard run**

Use one explicit review date derived from the existing dashboard clock, never file modification time. Do not add a fallback data profile. Pass the result through render function parameters rather than recomputing it inside each route. Put policy, source path, and excluded counts in the existing Advanced evidence expander.

- [ ] **Step 4: Update durable truth documentation**

Record that observation recency is locally implemented and independently fail-closed, while permitted market-data source rights and hosted freshness remain external gates. Record the exact seven-calendar-day policy and state that it is not an exchange-session SLA.

- [ ] **Step 5: Run focused and full verification**

Run:

```bash
python3 -m pytest tests/test_observation_recency.py tests/test_dashboard_helpers.py tests/test_research_workspace.py tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py -q
python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make public-wording-check
make public-check
make commercial-beta-release-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
```

Expected: all checks pass without creating or staging new CSV, JSON, report, sample-report, screenshot, or timing churn.

- [ ] **Step 6: Stage exact files, run staged hygiene, commit, push, and verify exact-head CI**

```bash
git add src/observation_recency.py src/dashboard.py src/research_workspace.py tests/test_observation_recency.py tests/test_dashboard_helpers.py tests/test_research_workspace.py tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py ROADMAP.md docs/METHODOLOGY.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md
make staged-hygiene-check
git commit -m "Integrate observation recency across research routes"
git push origin codex/personal-research-mode-mvp
gh pr checks 113 --watch
```

Expected: PR #113 remains open and draft; exact-head CI passes; pre-existing generated working-data churn remains unstaged.
