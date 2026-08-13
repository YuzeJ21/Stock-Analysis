# Discover Answer-First Truth Separation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Personal Research Discover clearly separate strict screen eligibility from alphabetical saved-company evidence browsing without reading legacy ranking outputs or changing any research threshold.

**Architecture:** Keep the current `?mode=research&page=discover` route and strict daily-queue engine. Add one pure readiness-to-browse adapter in `src/dashboard.py`, then make the existing selector renderer choose that adapter only for the Research Discover target while preserving the public selector path unchanged. Presentation uses saved readiness fields, alphabetical ticker order, and explicit inspectability/usable-evidence/evidence-gap copy; it never imports ranking order or ranking reasons.

**Tech Stack:** Python 3.12, pandas, Streamlit, pytest, existing dashboard HTML/CSS helpers, existing no-write artifact guard and Make release gates.

## Global Constraints

- Research-only; no investment advice, buy/sell instruction, expected-return ranking, best-stock list, recommendation, portfolio instruction, broker action, or post-earnings price prediction.
- Keep the current route URLs and query compatibility.
- Do not change strict Momentum + Valuation thresholds or daily-queue calculations.
- Do not read `outputs/research_decisions.csv` or `final_watchlist.csv` for Personal Research saved-company browsing.
- Actuals, consensus, Revenue, EPS, valuation, peers, catalysts, outcomes, backtesting, and calibration remain independent.
- Candidate context cannot alter deterministic output or trusted evidence.
- Synthetic fixtures remain test-only; empty states remain truthful.
- EPS split basis stays unverified without explicit proof; Q4 actuals require explicit SEC-filed Q4 table evidence.
- Ordinary route use stays in-memory/no-write; do not rebuild readiness or generate CSV, JSON, reports, screenshots, timing, output, or canonical-data artifacts.
- Preserve all 18 pre-existing protected generated paths unstaged and byte-identical.
- Never use `git add -A`; stage exact intentional files only.

---

## File Structure

- `src/dashboard.py` remains the Discover composition owner. It gains one pure saved-readiness browse adapter and narrow mode-specific copy/ordering branches; public selector behavior stays unchanged.
- `tests/test_dashboard_helpers.py` protects pure browse construction, alphabetical order, fail-closed copy, action labels, and legacy-ranking-copy exclusion.
- `tests/test_research_mode_dashboard_contract.py` protects route order, strict/browse separation, compatibility, and the no-legacy-output composition contract.
- `docs/PERSONAL_RESEARCH_MODE.md` documents the two distinct Discover capabilities and stop rule.
- `ROADMAP.md` records the verified Discover slice without promoting external source, hosted, human, or calibration gates.
- `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md` records the exact next executable route slice after Discover verification.

---

### Task 1: Build an alphabetical readiness-only saved-company adapter

**Files:**
- Modify: `src/dashboard.py:29506-29640`
- Test: `tests/test_dashboard_helpers.py:2070-2205`

**Interfaces:**
- Consumes: `ticker_readiness_frame: pd.DataFrame | None` and `allowed_tickers: tuple[str, ...] | None`.
- Produces: `discover_saved_company_browse_frame(ticker_readiness_frame, *, allowed_tickers=None, limit=120) -> pd.DataFrame` with the selector-compatible columns `Ticker`, `Asset Type`, `Research State`, `Readiness`, four independent readiness booleans, `Review Detail`, `Sector / Theme`, `Why Inspectable`, `Supported Now`, `Blocked / Missing`, `Next Proof Step`, and `Proof Freshness`.
- Invariant: output order is case-insensitive alphabetical ticker order and does not contain `Why Included`, rank, score, priority, or recommendation fields.

- [x] **Step 1: Write the failing readiness-only browse tests**

Add these tests near the existing selector-frame tests:

```python
def test_discover_saved_company_browse_frame_uses_readiness_only_and_sorts_alphabetically():
    readiness = pd.DataFrame(
        [
            {
                "ticker": "ZZZ",
                "asset_type": "company",
                "overall_readiness_state": "partial",
                "price_ready": True,
                "fundamentals_ready": False,
                "dcf_ready": False,
                "peer_ready": False,
                "ready_features": "price history and trend context",
                "missing_data": "fundamentals need trusted source proof",
                "next_action": "Review fundamentals proof.",
                "updated_at": "2026-07-31T00:00:00+00:00",
                "review_priority_reason": "High review priority: must never render.",
                "decision_score": 99,
            },
            {
                "ticker": "AAA",
                "asset_type": "company",
                "overall_readiness_state": "ready",
                "price_ready": True,
                "fundamentals_ready": True,
                "dcf_ready": True,
                "peer_ready": False,
                "ready_features": "price, fundamentals, and DCF evidence",
                "missing_data": "peer evidence remains unavailable",
                "next_action": "Review peer evidence requirements.",
                "updated_at": "2026-07-30T00:00:00+00:00",
                "review_priority_reason": "High review priority: must never render.",
                "decision_score": 1,
            },
            {
                "ticker": "QQQ",
                "asset_type": "etf",
                "overall_readiness_state": "monitor",
                "price_ready": True,
            },
        ]
    )

    frame = dashboard.discover_saved_company_browse_frame(
        readiness,
        allowed_tickers=("ZZZ", "AAA", "QQQ"),
    )

    assert frame["Ticker"].tolist() == ["AAA", "ZZZ"]
    assert frame.loc[0, "Why Inspectable"] == (
        "Saved evidence is available for price, fundamentals, and DCF review."
    )
    assert frame.loc[1, "Why Inspectable"] == "Saved evidence is available for price review."
    assert frame.loc[0, "Blocked / Missing"] == "peer evidence remains unavailable"
    assert "Why Included" not in frame.columns
    assert not any("high review priority" in str(value).lower() for value in frame.to_numpy().flat)
    assert not any("decision_score" == column for column in frame.columns)


def test_discover_saved_company_browse_frame_fails_closed_without_saved_readiness():
    assert dashboard.discover_saved_company_browse_frame(None).empty
    assert dashboard.discover_saved_company_browse_frame(pd.DataFrame()).empty
    assert dashboard.discover_saved_company_browse_frame(
        pd.DataFrame([{"asset_type": "company"}])
    ).empty
```

- [x] **Step 2: Run the focused tests and verify RED**

Run:

```bash
python3 -m pytest \
  tests/test_dashboard_helpers.py::test_discover_saved_company_browse_frame_uses_readiness_only_and_sorts_alphabetically \
  tests/test_dashboard_helpers.py::test_discover_saved_company_browse_frame_fails_closed_without_saved_readiness -q
```

Expected: both tests fail because `discover_saved_company_browse_frame` does not exist.

- [x] **Step 3: Implement the pure adapter**

Add the helper before `stock_selector_queue_frame`:

```python
def discover_saved_company_browse_frame(
    ticker_readiness_frame: pd.DataFrame | None,
    *,
    allowed_tickers: tuple[str, ...] | None = None,
    limit: int = 120,
) -> pd.DataFrame:
    """Build alphabetical saved-company browsing from readiness only."""

    if ticker_readiness_frame is None or ticker_readiness_frame.empty:
        return pd.DataFrame()
    ticker_col = _selector_column(ticker_readiness_frame, "ticker", "Ticker")
    if not ticker_col:
        return pd.DataFrame()

    frame = ticker_readiness_frame.copy()
    asset_col = _selector_column(frame, "asset_type", "Asset Type")
    if asset_col:
        frame = frame.loc[
            frame[asset_col].fillna("").astype(str).str.strip().str.lower().eq("company")
        ].copy()
    if allowed_tickers is not None:
        allowed = {str(value).strip().upper() for value in allowed_tickers if str(value).strip()}
        frame = frame.loc[
            frame[ticker_col].fillna("").astype(str).str.strip().str.upper().isin(allowed)
        ].copy()
    if frame.empty:
        return pd.DataFrame()

    readiness_col = _selector_column(frame, "overall_readiness_state", "Readiness")
    supported_col = _selector_column(frame, "ready_features", "supported_analysis")
    blocker_col = _selector_column(frame, "missing_data", "missing_data_summary")
    next_col = _selector_column(frame, "next_action", "next_research_step")
    freshness_col = _selector_column(frame, "updated_at", "source_freshness_summary")
    sector_col = _selector_column(frame, "sector", "SectorETF")
    theme_col = _selector_column(frame, "theme", "industry")
    lane_fields = (
        ("price_ready", "price"),
        ("fundamentals_ready", "fundamentals"),
        ("dcf_ready", "DCF"),
        ("peer_ready", "peer"),
    )

    rows: list[dict[str, object]] = []
    for _, row in frame.iterrows():
        ticker = str(row.get(ticker_col, "")).strip().upper()
        if not ticker:
            continue
        lanes = [
            label
            for column, label in lane_fields
            if str(row.get(column, "")).strip().lower() in {"true", "1", "yes", "y"}
            or row.get(column) is True
        ]
        if lanes:
            if len(lanes) == 1:
                lane_copy = lanes[0]
            else:
                lane_copy = ", ".join(lanes[:-1]) + f", and {lanes[-1]}"
            why_inspectable = f"Saved evidence is available for {lane_copy} review."
        else:
            why_inspectable = (
                "This saved company can be opened for evidence inspection; "
                "no usable research lane is currently recorded."
            )
        sector = _selector_text(row, sector_col, fallback="")
        theme = _selector_text(row, theme_col, fallback="")
        rows.append(
            {
                "Ticker": ticker,
                "Asset Type": _selector_text(row, asset_col, fallback="company"),
                "Research State": "Saved company",
                "Readiness": _selector_text(row, readiness_col, fallback="Needs readiness check"),
                "Price Ready": "price" in lanes,
                "Fundamentals Ready": "fundamentals" in lanes,
                "DCF Ready": "DCF" in lanes,
                "Trusted Peer Ready": "peer" in lanes,
                "Review Detail": "Evidence inspection",
                "Sector / Theme": " / ".join(value for value in (sector, theme) if value)
                or "Not available",
                "Why Inspectable": why_inspectable,
                "Supported Now": _selector_text(
                    row, supported_col, fallback="No usable research lane is recorded."
                ),
                "Blocked / Missing": _selector_text(
                    row,
                    blocker_col,
                    fallback=(
                        "No principal evidence gap is recorded; this does not mean "
                        "no external research need exists."
                    ),
                ),
                "Next Proof Step": _selector_text(
                    row, next_col, fallback="Review saved readiness before deeper research."
                ),
                "Proof Freshness": _selector_text(
                    row, freshness_col, fallback="Saved readiness freshness is unavailable."
                ),
            }
        )

    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return result.sort_values("Ticker", key=lambda values: values.str.upper(), kind="mergesort").head(
        max(limit, 1)
    ).reset_index(drop=True)
```

- [x] **Step 4: Run the focused tests and verify GREEN**

Run the Step 2 command again.

Expected: both tests pass and no file is written.

- [x] **Step 5: Commit Task 1 exactly**

```bash
git add -- src/dashboard.py tests/test_dashboard_helpers.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Build readiness-only Discover browsing"
```

---

### Task 2: Replace ranking-adjacent Discover row copy with evidence answers

**Files:**
- Modify: `src/dashboard.py:29760-29900`
- Test: `tests/test_dashboard_helpers.py:2290-2405`
- Test: `tests/test_research_mode_dashboard_contract.py:225-255`

**Interfaces:**
- Consumes: one normalized saved-company row from Task 1.
- Produces: `discover_research_answer(row) -> dict[str, str]` with `why_inspectable`, `usable_evidence`, and `main_evidence_gap`; research-only HTML labels; `Open <TICKER> Company Brief` action.
- Public selector output keeps `Open <TICKER> review`, current state pills, and current URLs.

- [x] **Step 1: Replace the existing tests with the answer-first contract**

Update the research-mode HTML tests and add the explicit legacy-copy mutation:

```python
def test_discover_row_answers_three_saved_evidence_questions_without_ranking_copy():
    rendered = dashboard.stock_selector_result_table_html(
        pd.DataFrame(
            [
                {
                    "Ticker": "NVDA",
                    "Readiness": "partial",
                    "Why Inspectable": "Saved evidence is available for price and DCF review.",
                    "Why Included": "High review priority: should never appear.",
                    "Supported Now": "Price and DCF evidence.",
                    "Blocked / Missing": "Peer evidence remains unavailable.",
                }
            ]
        ),
        total_count=1,
        target_mode="research",
        target_page="company-workbench",
    )

    assert "Why inspectable" in rendered
    assert "Saved evidence is available for price and DCF review." in rendered
    assert "Usable evidence" in rendered
    assert "Price and DCF evidence." in rendered
    assert "Main evidence gap" in rendered
    assert "Peer evidence remains unavailable." in rendered
    assert "High review priority" not in rendered
    assert rendered.count("Open NVDA Company Brief") == 1


def test_discover_research_answer_fails_closed_for_missing_saved_fields():
    answers = dashboard.discover_research_answer(
        {
            "Why Inspectable": float("nan"),
            "Supported Now": " ",
            "Blocked / Missing": "no blocker",
        }
    )

    assert answers == {
        "why_inspectable": "Saved readiness does not record why this company is inspectable.",
        "usable_evidence": "No usable research lane is recorded in saved readiness.",
        "main_evidence_gap": (
            "No principal evidence gap is recorded in saved readiness; this does not mean "
            "no risk or external research need exists."
        ),
    }
```

Extend `test_research_selector_links_open_company_workbench_without_changing_public_default`:

```python
assert "Open NVDA review" in public_html
assert "Open NVDA Company Brief" in research_html
assert "High review priority" not in research_html
```

- [x] **Step 2: Run the focused HTML tests and verify RED**

```bash
python3 -m pytest \
  tests/test_dashboard_helpers.py::test_discover_row_answers_three_saved_evidence_questions_without_ranking_copy \
  tests/test_dashboard_helpers.py::test_discover_research_answer_fails_closed_for_missing_saved_fields \
  tests/test_research_mode_dashboard_contract.py::test_research_selector_links_open_company_workbench_without_changing_public_default -q
```

Expected: failures show the old `Why reviewable`, `Usable now`, `Principal blocker`, and `Open NVDA review` research copy.

- [x] **Step 3: Implement the research-only answer and action copy**

Change `discover_review_action_label` to accept a mode-specific keyword while retaining the public default:

```python
def discover_review_action_label(ticker: str, *, company_brief: bool = False) -> str:
    symbol = str(ticker or "").strip().upper()
    if not symbol:
        return "Open Company Brief" if company_brief else "Open review"
    return f"Open {symbol} Company Brief" if company_brief else f"Open {symbol} review"
```

Change the answer fallbacks and field mapping:

```python
def discover_research_answer(row: Mapping[str, object]) -> dict[str, str]:
    """Answer saved-company evidence questions without importing ranking semantics."""

    fallbacks = {
        "why_inspectable": "Saved readiness does not record why this company is inspectable.",
        "usable_evidence": "No usable research lane is recorded in saved readiness.",
        "main_evidence_gap": (
            "No principal evidence gap is recorded in saved readiness; this does not mean "
            "no risk or external research need exists."
        ),
    }

    def saved_text(field: str, fallback_key: str) -> str:
        text = format_missing(row.get(field), "").strip()
        if not text:
            return fallbacks[fallback_key]
        if fallback_key == "main_evidence_gap" and text.lower() == "no blocker":
            return fallbacks[fallback_key]
        return text

    return {
        "why_inspectable": saved_text("Why Inspectable", "why_inspectable"),
        "usable_evidence": saved_text("Supported Now", "usable_evidence"),
        "main_evidence_gap": saved_text("Blocked / Missing", "main_evidence_gap"),
    }
```

In the `research_discover` HTML branch, render these exact labels and keys:

```python
"<span class='research-discover-answer-label'>Why inspectable</span>"
f"<span class='research-discover-answer-value'>{html.escape(answers['why_inspectable'])}</span>"
"<span class='research-discover-answer-label'>Usable evidence</span>"
f"<span class='research-discover-answer-value'>{html.escape(answers['usable_evidence'])}</span>"
"<span class='research-discover-answer-label'>Main evidence gap</span>"
f"<span class='research-discover-answer-value'>{html.escape(answers['main_evidence_gap'])}</span>"
```

Pass `company_brief=research_discover` to `discover_review_action_label`.

- [x] **Step 4: Run the focused tests and verify GREEN**

Run the Step 2 command again.

Expected: all three tests pass; public and research actions remain distinct.

- [x] **Step 5: Commit Task 2 exactly**

```bash
git add -- src/dashboard.py tests/test_dashboard_helpers.py tests/test_research_mode_dashboard_contract.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Clarify saved-company evidence answers"
```

---

### Task 3: Compose strict eligibility and saved-company browsing as separate truths

**Files:**
- Modify: `src/dashboard.py:6295-6345`
- Modify: `src/dashboard.py:30019-30175`
- Modify: `src/dashboard.py:35860-35895`
- Test: `tests/test_research_mode_dashboard_contract.py:280-455`
- Test: `tests/test_dashboard_helpers.py:2405-2460`

**Interfaces:**
- Consumes: existing `DailyQueueBuildStatus`, Task 1 browse frame, current Research route parameters.
- Produces: Discover order `Find a Company` -> `Screen eligibility — when supported` -> `Browse saved companies` -> cohort evidence under Advanced.
- Produces: `stock_selector_source_frames(output_frames, *, research_discover)` so the no-legacy-read branch is behavior-testable without inspecting source text.
- Invariant: the research path never calls `load_output(OUTPUTS_DIR / "research_decisions.csv")` and never consumes `final_watchlist.csv`; public mode still does.

- [x] **Step 1: Write failing route and renderer contract tests**

Update the route-order test to capture visible headings and ensure no output-frame loader is used:

```python
from contextlib import nullcontext


def test_research_discover_separates_strict_eligibility_from_saved_company_browsing(monkeypatch):
    calls: list[str] = []
    headings: list[str] = []
    context = SimpleNamespace(data_dir=Path("/selected-profile/data"))

    class Expander:
        def __enter__(self):
            calls.append("advanced")
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(dashboard, "load_observation_recency", lambda *args, **kwargs: object())
    monkeypatch.setattr(dashboard, "render_research_workspace_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard, "load_dashboard_daily_research_queue", lambda *args, **kwargs: object())
    monkeypatch.setattr(dashboard, "render_daily_research_queue", lambda status: calls.append("strict eligibility"))
    monkeypatch.setattr(dashboard, "render_stock_selector", lambda *args, **kwargs: calls.append("saved browsing"))
    monkeypatch.setattr(
        dashboard,
        "dashboard_output_frames_for_page",
        lambda page: pytest.fail("Research Discover must not load legacy selector outputs"),
    )
    monkeypatch.setattr(dashboard, "render_signal_cards", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard, "focused_cohort_cards", lambda cohort: [])
    monkeypatch.setattr(dashboard, "focused_cohort_coverage_cards", lambda coverage: [])
    monkeypatch.setattr(dashboard.st, "markdown", lambda value, **kwargs: headings.append(value))
    monkeypatch.setattr(dashboard.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard.st, "expander", lambda *args, **kwargs: Expander())

    dashboard.render_personal_research_route(
        selected_page="Discover",
        provider=object(),
        context=context,
        state={},
        cohort=SimpleNamespace(members=()),
        coverage=object(),
        weekly_summary=object(),
        ticker="ALFA",
        review_date=date(2026, 7, 31),
    )

    assert "## Find a Company" in headings
    assert calls[:2] == ["strict eligibility", "saved browsing"]
    assert calls[2:] == ["advanced"]
```

Update the daily-queue renderer assertion to require `Screen eligibility — when supported`, and add an empty-state test:

```python
def test_empty_strict_screen_preserves_browsing_boundary(monkeypatch):
    rendered: list[str] = []
    status = DailyQueueBuildStatus(
        result=evaluate_daily_queue(()),
        considered_count=0,
        readiness_row_count=0,
        price_row_count=0,
        valuation_observation_count=0,
        blocker_counts=(("current_market_evidence", 1),),
        message="No eligible records.",
    )
    monkeypatch.setattr(dashboard.st, "markdown", lambda value, **kwargs: rendered.append(value))
    monkeypatch.setattr(dashboard.st, "caption", lambda value, **kwargs: rendered.append(value))
    monkeypatch.setattr(dashboard, "render_signal_cards", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        dashboard,
        "render_notice_card",
        lambda title, body, *args, **kwargs: rendered.extend([title, body]),
    )
    monkeypatch.setattr(dashboard.st, "expander", lambda *args, **kwargs: nullcontext())
    monkeypatch.setattr(dashboard.st, "dataframe", lambda *args, **kwargs: None)

    dashboard.render_daily_research_queue(status)

    copy = " ".join(rendered)
    assert "Screen eligibility — when supported" in copy
    assert "No company currently has complete evidence for the strict screen" in copy
    assert "This does not prevent browsing saved companies" in copy
    assert "thresholds were not relaxed" in copy.lower()
```

Add a source-selection behavior test:

```python
def test_stock_selector_source_frames_skip_legacy_outputs_for_research_discover(monkeypatch):
    calls: list[Path] = []
    decisions = pd.DataFrame([{"ticker": "RANKED"}])
    final = pd.DataFrame([{"Ticker": "FINAL"}])

    def load_saved(path):
        calls.append(path)
        return decisions, "saved decisions"

    monkeypatch.setattr(dashboard, "load_output", load_saved)

    research = dashboard.stock_selector_source_frames(
        {"final_watchlist.csv": (final, "saved final")},
        research_discover=True,
    )
    assert research == (None, None, None, None)
    assert calls == []

    public = dashboard.stock_selector_source_frames(
        {"final_watchlist.csv": (final, "saved final")},
        research_discover=False,
    )
    assert calls == [dashboard.OUTPUTS_DIR / "research_decisions.csv"]
    assert public[0] is decisions
    assert public[2] is final
```

- [x] **Step 2: Run the focused route tests and verify RED**

```bash
python3 -m pytest \
  tests/test_research_mode_dashboard_contract.py::test_research_discover_separates_strict_eligibility_from_saved_company_browsing \
  tests/test_research_mode_dashboard_contract.py::test_daily_queue_renderer_is_ticker_bound_and_keeps_blockers_in_advanced \
  tests/test_research_mode_dashboard_contract.py::test_empty_strict_screen_preserves_browsing_boundary \
  tests/test_dashboard_helpers.py::test_stock_selector_source_frames_skip_legacy_outputs_for_research_discover -q
```

Expected: failures show the old page title, old strict-queue title/copy, output-frame loader call, and missing mode branch.

- [x] **Step 3: Implement strict eligibility copy and mode-specific source selection**

Make these exact composition changes:

1. Rename the daily queue heading to `### Screen eligibility — when supported`.
2. Rename its eligible action to `Open <TICKER> Company Brief`.
3. Replace its empty notice with:

```python
render_notice_card(
    "No company currently has complete evidence for the strict screen",
    (
        "Current-market, momentum, historical valuation, fundamental, provenance, "
        "or source-rights evidence is incomplete. Thresholds were not relaxed. "
        "This does not prevent browsing saved companies for evidence inspection."
    ),
    tone="warning",
)
```

4. At the start of `render_stock_selector`, calculate:

```python
research_discover = (
    str(target_mode).strip().lower() == RESEARCH_MODE
    and str(target_page).strip().lower() == "company-workbench"
)
```

5. Add the tested source helper:

```python
def stock_selector_source_frames(
    output_frames: dict[str, tuple[pd.DataFrame | None, str | None]],
    *,
    research_discover: bool,
) -> tuple[
    pd.DataFrame | None,
    str | None,
    pd.DataFrame | None,
    str | None,
]:
    if research_discover:
        return None, None, None, None
    decisions_frame, decisions_message = load_output(
        OUTPUTS_DIR / "research_decisions.csv"
    )
    final_frame, final_message = output_frames.get(
        "final_watchlist.csv", (None, None)
    )
    return decisions_frame, decisions_message, final_frame, final_message
```

6. Load `ticker_readiness_frame` for both modes, call the source helper, then branch:

```python
decisions_frame, decisions_message, final_frame, final_message = (
    stock_selector_source_frames(
        output_frames,
        research_discover=research_discover,
    )
)
if research_discover:
    selector_frame = discover_saved_company_browse_frame(
        ticker_readiness_frame,
        allowed_tickers=allowed_tickers,
        limit=120,
    )
else:
    decisions_frame, decisions_message = load_output(OUTPUTS_DIR / "research_decisions.csv")
    final_frame, final_message = output_frames.get("final_watchlist.csv", (None, None))
    selector_frame = stock_selector_queue_frame(
        decisions_frame, final_frame, ticker_readiness_frame, limit=120
    )
    selector_frame = filter_selector_to_tickers(selector_frame, allowed_tickers)
```

7. For the research branch, render `### Browse saved companies`, search label `Search saved companies`, empty title `No saved companies are available to browse`, and this boundary before the rows:

```python
render_context_note(
    "Saved-company browsing is not strict screen eligibility.",
    (
        "Rows are alphabetical evidence-access paths. Availability does not mean the company "
        "passed momentum and valuation screening, has attractive valuation, or is a recommendation."
    ),
)
```

8. Add `discover_browse_result_summary_html(filtered_count, total_count)` with copy `<strong>N</strong> of M saved companies match the current search and filters.` and use it only for `research_discover`.
9. In `render_personal_research_route`, change the H2 to `## Find a Company` and pass `{}` to `render_stock_selector` instead of calling `dashboard_output_frames_for_page`.

- [x] **Step 4: Run focused Discover tests and verify GREEN**

Run:

```bash
python3 -m pytest \
  tests/test_research_mode_dashboard_contract.py \
  tests/test_dashboard_helpers.py \
  tests/test_daily_research_queue.py \
  tests/test_daily_research_queue_adapter.py -q
```

Expected: all tests pass; public selector compatibility tests remain green.

- [x] **Step 5: Commit Task 3 exactly**

```bash
git add -- src/dashboard.py tests/test_dashboard_helpers.py tests/test_research_mode_dashboard_contract.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Separate Discover eligibility from browsing"
```

---

### Task 4: Close responsive, documentation, and release evidence for Discover

**Files:**
- Modify: `tests/test_dashboard_helpers.py:2370-2405`
- Modify: `tests/test_research_mode_dashboard_contract.py:1325-1360`
- Modify: `docs/PERSONAL_RESEARCH_MODE.md`
- Modify: `ROADMAP.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`

**Interfaces:**
- Consumes: verified Discover behavior from Tasks 1–3.
- Produces: responsive contract evidence, current product documentation, current roadmap truth, and the exact next Workbench slice.
- Invariant: documentation states Discover completion only after direct browser and release gates pass.

- [x] **Step 1: Update responsive and heading tests first**

Change the expected Research H2 from `Which stock can I review?` to `Find a Company`. Extend the phone-row test:

```python
assert "Why inspectable" in source
assert "Usable evidence" in source
assert "Main evidence gap" in source
assert "Open {symbol} Company Brief" in source
assert "min-height: 2.75rem" in source
```

Use the rendered-row behavior test as the copy guard. Its input contains a
`Why Included` ranking-adjacent mutation and the assertion proves that value
cannot reach the research answer:

```python
assert "High review priority: should never appear." not in rendered
```

- [x] **Step 2: Run the focused behavior tests and verify their current result**

```bash
python3 -m pytest \
  tests/test_dashboard_helpers.py::test_research_discover_rows_keep_all_answers_on_phone_and_one_large_action \
  tests/test_dashboard_helpers.py::test_discover_row_answers_three_saved_evidence_questions_without_ranking_copy \
  tests/test_research_mode_dashboard_contract.py::test_research_primary_sections_follow_route_h1_with_level_two_headings -q
```

Expected: pass after Tasks 1–3; if any fail, repair the Discover source before documentation.

- [x] **Step 3: Reconcile Discover documentation truthfully**

Update the three documents with these exact facts:

- Personal Research flow remains `Research Desk -> Discover -> Company Workbench -> Monitor`.
- Discover now presents `Screen eligibility — when supported` separately from alphabetical `Browse saved companies`.
- Saved-company rows explain inspectability, usable evidence, and the main evidence gap; they are not screened opportunities or recommendations.
- The route reads saved readiness for browsing and does not read legacy ranking outputs.
- Workbench, Monitor, and Desk answer-first recomposition remain next local UX work.
- External Priority 4–9 gates remain incomplete and independent.

- [ ] **Step 4: Run direct browser review at both required viewports**

Using the already-open local app and the user's in-app browser, verify `?mode=research&page=discover` at `1280x720` and `390x844` with the fully settled route.

Record direct evidence for:

- `Find a Company` appears before technical profile/readiness detail;
- strict eligibility and saved browsing are visually distinct;
- the empty strict screen and non-empty alphabetical browsing coexist without contradiction;
- row order is alphabetical;
- one `Open <TICKER> Company Brief` action is at least 44px high on phone;
- all three evidence answers remain visible;
- the stop rule is visible before Advanced;
- no `High review priority`, ranking, opportunity, expected-return, or recommendation language appears;
- no horizontal overflow, traceback, broken link, duplicate H1, or hidden safety boundary appears.

Do not save screenshots into the repository. Temporary browser evidence stays outside the worktree.

- [ ] **Step 5: Run the complete required verification matrix**

```bash
python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make public-wording-check
make public-check
make public-performance-gate
make pilot-readiness-check TOP_N=10
make research-accessibility-browser-check
make diff-hygiene-summary
git diff --check
git status --short | awk '{print $2}' | rg '^(data|outputs)/' | sort | xargs shasum -a 256
```

Expected:

- tests, dashboard/render smoke, wording, public, performance, accessibility engineering, diff, and whitespace gates pass;
- pilot readiness executes with its truthful overall blocked verdict;
- only intentional code/test/docs files are product candidates;
- protected generated paths remain byte-identical.

Compare the final protected-path hash list byte-for-byte with the captured Stage 0 baseline before staging. Stop and investigate if a path, count, or digest differs.

- [ ] **Step 6: Stage and commit the exact documentation/closure package**

```bash
git add -- \
  tests/test_dashboard_helpers.py \
  tests/test_research_mode_dashboard_contract.py \
  docs/PERSONAL_RESEARCH_MODE.md \
  ROADMAP.md \
  docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md
make staged-hygiene-check
git diff --cached --check
git commit -m "Document answer-first Discover workflow"
```

- [ ] **Step 7: Push, update PR #113, and require exact-head CI**

```bash
git push origin codex/personal-research-mode-mvp
```

Update the draft PR description and add exact-head evidence covering the user question resolved, files changed, focused/full tests, browser viewports, release gates, protected hashes, excluded generated artifacts, and remaining external gates. Keep the PR open and draft. Wait for `local-engineering-gate` success on the pushed exact HEAD before calling the Discover slice complete.

- [ ] **Step 8: Select the next executable slice**

After exact-head success, begin a separate Company Workbench implementation plan from the committed answer-first design. Do not mix Workbench code into the Discover commits.
