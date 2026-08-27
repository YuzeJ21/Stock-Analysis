# Journey Repair v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Discover evidence-access first, preserve selected-company return context through Monitor and Advanced Evidence, and show only a neutral report state until authoritative saved evidence is ready.

**Architecture:** Keep the existing Streamlit routes and research engines. Add small pure presentation/route helpers around the current Discover readiness frame, Personal Research navigation, and shared single-stock lifecycle; reuse the current report builder and evidence routes unchanged. Route state distinguishes selected-company analysis (`ticker`) from Monitor return context (`return_ticker`).

**Tech Stack:** Python 3.12, Streamlit, pandas, deterministic HTML/CSS helpers, pytest, repository browser gates, in-app Browser.

**Spec:** `docs/superpowers/specs/2026-08-26-journey-repair-v1-design.md`

## Global Constraints

- Work only in `/Users/yjian070/Documents/New project/.worktrees/journey-repair-v1` on `codex/journey-repair-v1`.
- The implementation base is `19d59bea64d2a37f69024d60ab195c0b50467d27` unless a ledgered ruling says otherwise.
- Preserve all seven pre-existing auxiliary worktrees; do not delete, clean, reset, or modify them.
- Preserve `data/`, `outputs/`, readiness artifacts, proof ledgers, `docs/assets/`, and generated research outputs byte-for-byte.
- Never use `git add -A`; stage only named files for each commit.
- Follow TDD: every production behavior starts with a focused failing test whose failure is observed and recorded.
- Reuse the current design system, route vocabulary, and HTML helpers. Do not use Figma or create a new app/template.
- Discover availability remains alphabetical readiness-only evidence access, not strict eligibility, a ranking, expected return, or a recommendation.
- Monitor remains the existing focused-cohort/workspace follow-up surface; `return_ticker` never filters Monitor data.
- Missing, invalid, stale, candidate-only, rights-blocked, or unsupported evidence remains fail-closed.
- `build_stock_report()` remains the sole authority for a rendered report answer. No pre-payload readiness claim may be shown.
- No data/source/provider/rights/readiness calculation, canonical row, proof record, session persistence contract, or report content changes.
- No merge, push, deploy, publication, GitHub setting change, or external side effect.
- Research-only: no broker integration, auto-trading, fabricated evidence, recommendation, or direct buy/sell instruction.

---

### Task 1: Make Discover evidence-access first

**Files:**
- Modify: `src/dashboard.py:6355-6386,30190-30342,30918-31200,37395-37448`
- Modify: `tests/test_research_mode_dashboard_contract.py:412-559,1690-1729`
- Modify: `tests/test_dashboard_helpers.py:2196-2540`

**Interfaces:**
- Consumes: existing `DailyQueueBuildStatus.result.eligible` and the readiness-only frame returned by `discover_saved_company_browse_frame(...)`.
- Produces: `discover_primary_answer_html(saved_company_count: int, strict_eligible_count: int) -> str` and `discover_quick_company_links_html(frame: pd.DataFrame, *, limit: int = 4) -> str`.
- Produces: optional `strict_eligible_count` input on `render_stock_selector(...)`; public selector behavior is unchanged when it is absent.

- [ ] **Step 1: Write failing pure-helper tests**

Add tests with literal expectations:

```python
def test_discover_primary_answer_separates_saved_access_from_strict_eligibility():
    rendered = dashboard.discover_primary_answer_html(8, 0)

    assert "8 saved companies are available for evidence review" in rendered
    assert "0 currently pass the strict screen" in rendered
    assert "alphabetical" in rendered.lower()
    assert "not a ranking" in rendered.lower()


def test_discover_quick_links_are_alphabetical_non_ranked_company_briefs():
    frame = dashboard.pd.DataFrame({"Ticker": ["NVDA", "AMD", "AVGO", "COHR", "TSLA"]})

    rendered = dashboard.discover_quick_company_links_html(frame, limit=4)

    assert [rendered.index(ticker) for ticker in ("AMD", "AVGO", "COHR", "NVDA")] == sorted(
        rendered.index(ticker) for ticker in ("AMD", "AVGO", "COHR", "NVDA")
    )
    assert "TSLA" not in rendered
    assert rendered.count("page=company-workbench") == 4
    assert "ranking" in rendered.lower()
```

- [ ] **Step 2: Run the helper tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_dashboard_helpers.py \
  -k 'discover_primary_answer or discover_quick_links'
```

Expected: collection failures because the two helpers do not exist.

- [ ] **Step 3: Implement the minimal pure helpers**

Add helpers beside the existing Discover browser helpers. Use
`answer_panel_html(...)`, `SafeRouteAction`, `html.escape`, `_quoted_ticker`,
and the existing Company Workbench route. Singular/plural copy must remain
grammatical for 0, 1, and many saved companies. Sort a copied ticker series
case-insensitively, remove blanks and duplicates, and cap at `max(limit, 0)`.

The primary answer must use this exact semantic copy:

```python
saved_count = max(int(saved_company_count), 0)
eligible_count = max(int(strict_eligible_count), 0)
saved_noun = "saved company" if saved_count == 1 else "saved companies"
answer = (
    f"{saved_count:,} {saved_noun} {'is' if saved_count == 1 else 'are'} "
    f"available for evidence review; {eligible_count:,} currently pass the strict screen."
)
reason = (
    "Saved-company availability and strict-screen eligibility are separate. "
    "The links below are alphabetical evidence paths, not a ranking; strict thresholds remain unchanged."
)
```

Every quick link label is `Open {TICKER} Company Brief` and targets
`?mode=research&page=company-workbench&ticker={encoded}&open=1`.

- [ ] **Step 4: Run helper tests and verify GREEN**

Run the Step 2 command. Expected: the new tests pass with pristine output.

- [ ] **Step 5: Write a failing Discover integration contract**

Add a test that drives `render_personal_research_route(selected_page="Discover", ...)`
with eight saved cohort members and an empty strict queue. Capture Markdown
and widget calls in one ordered `events` list and assert:

```python
primary_index = next(
    index for index, event in enumerate(events)
    if event[0] == "markdown" and "8 saved companies are available" in event[1]
)
search_index = events.index(("text_input", "Search saved companies"))
assert "0 currently pass the strict screen" in events[primary_index][1]
assert primary_index < search_index
assert all(ticker in " ".join(event[1] for event in events if event[0] == "markdown")
           for ticker in ("AMD", "AVGO", "COHR", "NVDA"))
```

Also assert the strict queue detail remains available inside
`Advanced: cohort readiness context` and the selector receives the live
strict count rather than a literal.

- [ ] **Step 6: Run the integration test and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_research_mode_dashboard_contract.py \
  -k 'discover and evidence_access_first'
```

Expected: failure because strict-screen messaging still owns the first answer
and no compact quick-link row exists.

- [ ] **Step 7: Integrate the live counts and quick links**

Pass `len(daily_queue.result.eligible)` into `render_stock_selector(...)` as
`strict_eligible_count`. In the exact Research Discover branch, render the
new primary answer and compact quick links immediately after the selector
frame is calculated, before search, filters, and the full result cards.

Do not call `render_daily_research_queue(... include_details=False)` as a
second first-screen answer. Keep `render_daily_research_queue_details(...)`
inside the existing advanced cohort expander so strict evidence is preserved.
Public Stock Selector and Operator paths must not render the new Discover
answer.

- [ ] **Step 8: Run focused and adjacent tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_dashboard_helpers.py \
  tests/test_research_mode_dashboard_contract.py \
  -k 'discover or saved_company or stock_selector'
```

Expected: all selected tests pass with no warnings.

- [ ] **Step 9: Commit Task 1**

```bash
git add src/dashboard.py tests/test_dashboard_helpers.py tests/test_research_mode_dashboard_contract.py
git commit -m "Improve Discover evidence access"
```

---

### Task 2: Preserve Monitor return context and mark Advanced Evidence location

**Files:**
- Modify: `src/dashboard_navigation.py:77-89,201-279`
- Modify: `src/research_workspace.py:1388-1470,1570-1585`
- Modify: `src/dashboard.py:36700-36820,37093-37239,37457-37758`
- Modify: `tests/test_dashboard_navigation.py:171-248`
- Modify: `tests/test_research_workspace.py:1606-1685`
- Modify: `tests/test_research_mode_dashboard_contract.py:70-115,1155-1252,2089-2181`
- Modify if behavior text changes: `docs/PERSONAL_RESEARCH_MODE.md`

**Interfaces:**
- Consumes: registered local tickers from the existing provider.
- Produces: Monitor route key `return_ticker`; `validated_research_return_ticker(value: object, registered_tickers: Iterable[object]) -> str`; `research_monitor_return_link(ticker: str) -> dict[str, str]`.
- Extends: `research_workflow_navigation_html(active_page: str, ticker: str = "")` with a secondary current-location marker for evidence routes.

- [ ] **Step 1: Write failing route and helper tests**

Add literal behavior tests:

```python
def test_research_monitor_canonical_query_preserves_return_ticker_only():
    query = {
        "mode": "research",
        "page": "monitor",
        "return_ticker": "BRK/B",
        "ticker": "NVDA",
        "open": "1",
    }
    assert nav.canonical_workspace_query("research", "Monitor", query) == {
        "mode": "research",
        "page": "monitor",
        "return_ticker": "BRK/B",
    }


def test_validated_monitor_return_ticker_fails_closed():
    registered = ("NVDA", "BRK/B")
    assert research_workspace.validated_research_return_ticker("brk/b", registered) == "BRK/B"
    assert research_workspace.validated_research_return_ticker("UNKNOWN", registered) == ""
    assert research_workspace.validated_research_return_ticker("", registered) == ""


def test_monitor_return_link_is_explicitly_context_only():
    link = research_workspace.research_monitor_return_link("NVDA")
    assert link["label"] == "Return to NVDA Company Workbench"
    assert link["href"] == "?mode=research&page=company-workbench&ticker=NVDA&open=1"
    assert "does not filter Monitor" in link["purpose"]
```

- [ ] **Step 2: Run route/helper tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_dashboard_navigation.py tests/test_research_workspace.py \
  -k 'monitor and (return or canonical)'
```

Expected: Monitor strips `return_ticker` and the new helpers do not exist.

- [ ] **Step 3: Implement canonical return context**

Change only the Research Monitor allowlist:

```python
(RESEARCH_MODE, "Monitor"): ("return_ticker",),
```

Implement validation by normalizing to uppercase and returning the symbol only
when it exactly matches the normalized registered set. The helper performs no
provider call. Implement the return link with URL quoting through `_quoted_ticker`.

In `main()`, after the local provider is available, validate Monitor's
`return_ticker`. If invalid, remove only that query key from `st.query_params`.
Use the validated value for Personal Research navigation and the Monitor return
action. Do not pass it into any Monitor data loader, queue builder, frame, or
count function.

- [ ] **Step 4: Run route/helper tests and verify GREEN**

Run the Step 2 command. Expected: all selected tests pass.

- [ ] **Step 5: Write failing navigation and Monitor rendering tests**

Add assertions that:

```python
active = research_workspace.research_workflow_navigation_html(
    active_page="Monitor", ticker="BRK/B"
)
assert "page=monitor&amp;return_ticker=BRK%2FB" in active
assert "page=company-workbench&amp;ticker=BRK%2FB&amp;open=1" in active
assert active.count("aria-current='page'") == 1

for page in ("Data Health", "Proof History"):
    evidence = research_workspace.research_workflow_navigation_html(
        active_page=page, ticker="AVGO"
    )
    assert f"Advanced Evidence · {page}" in evidence
    assert evidence.count("aria-current='page'") == 1
```

Drive `render_research_monitor(...)` with a return ticker and assert the return
action is rendered once while the exact existing monitor cards/rows are
unchanged versus the no-context call.

- [ ] **Step 6: Run navigation/render tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_research_workspace.py tests/test_research_mode_dashboard_contract.py \
  -k 'workflow_navigation or monitor_return or active_evidence'
```

Expected: the Monitor URL drops context and evidence pages have zero current
markers.

- [ ] **Step 7: Implement navigation, marker, and return action**

Append `return_ticker` only to the Monitor link. Add a secondary evidence
context element after the four primary route links when the active page is
Data Health or Proof History:

```html
<div class='research-workflow-evidence-current'>
  <span>Advanced Evidence</span>
  <strong aria-current='page'>Advanced Evidence · Data Health</strong>
</div>
```

Use escaped labels and exactly one `aria-current`. Extend the existing Research
navigation CSS with the current typography, border, focus, and mobile-wrap
tokens; do not invent a new color system.

Render the Monitor return action below its primary answer when valid, followed
by this exact clarification:

> `Monitor remains focused-cohort-wide; {TICKER} is only the return destination and does not filter these follow-up items.`

- [ ] **Step 8: Run focused and adjacent tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_dashboard_navigation.py \
  tests/test_research_workspace.py \
  tests/test_research_mode_dashboard_contract.py
```

Expected: all tests pass with no warnings and the previous route/mode contracts
remain intact.

- [ ] **Step 9: Update behavior documentation if needed**

If `docs/PERSONAL_RESEARCH_MODE.md` describes Monitor as losing company
context or evidence pages as having no location cue, update only those
sentences. Do not add deployment, data freshness, or market-completeness claims.

- [ ] **Step 10: Commit Task 2**

```bash
git add src/dashboard_navigation.py src/research_workspace.py src/dashboard.py \
  tests/test_dashboard_navigation.py tests/test_research_workspace.py \
  tests/test_research_mode_dashboard_contract.py docs/PERSONAL_RESEARCH_MODE.md
git commit -m "Preserve research journey context"
```

If the documentation file has no relevant diff, omit it from `git add`.

---

### Task 3: Stabilize the cold report loading state

**Files:**
- Modify: `src/dashboard.py:7500-7585,8530-8610,32111-32520,37480-37770`
- Modify: `tests/test_dashboard_helpers.py:31947-32043,32267-32460`
- Modify: `tests/test_dashboard_render_smoke.py:880-990`
- Modify if the pure loading contract changes: `tests/test_single_stock_workflow.py:1-35`

**Interfaces:**
- Consumes: existing `single_stock_loading_contract_cards(ticker)` and completed `report_payload`.
- Produces: `single_stock_loading_state_html(ticker: object) -> str`, built from existing `signal_card_html(...)`, with no readiness inference.
- Preserves: `build_stock_report()`, provider calls, session payload keys, report export, and every completed-report renderer.

- [ ] **Step 1: Write failing pure and lifecycle tests**

Add a pure loading-state assertion:

```python
def test_single_stock_loading_state_is_neutral_and_accessible():
    rendered = dashboard.single_stock_loading_state_html("NVDA")

    assert "NVDA: preparing saved review" in rendered
    assert "does not state that any analysis section is ready or blocked" in rendered
    assert "No data is being refreshed or changed" in rendered
    assert "role='status'" in rendered
    assert "aria-live='polite'" in rendered
    assert "aria-busy='true'" in rendered
```

Replace the source-order test that currently requires the unsafe fast summary.
The new test must assert that the cold compact-open branch does not call
`single_stock_fast_readiness_snapshot`, `single_stock_one_answer_frame`, or
`render_single_stock_public_summary` before `open_selected_report()`.

Add controlled failure and success renderer tests:

- failure: report construction raises; neutral loading is rendered first, no
  Company Brief readiness answer is rendered, and the evidence rail is
  unavailable;
- success: neutral loading precedes report construction, completed payload is
  the first rendered readiness answer, and the neutral placeholder is cleared
  once.

- [ ] **Step 2: Run lifecycle tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_dashboard_helpers.py tests/test_dashboard_render_smoke.py \
  tests/test_single_stock_workflow.py \
  -k 'loading or cold or preparing_saved_review or fast_readiness'
```

Expected: the pure helper is missing and existing cold code renders the fast
summary before the authoritative payload.

- [ ] **Step 3: Implement one neutral loading renderer**

Build `single_stock_loading_state_html(...)` from the existing loading card,
`signal_card_html(...)`, and a context note. It must contain no ready, blocked,
supported, valuation, peer, price, or DCF conclusion beyond the explicit phrase
that it states neither ready nor blocked.

In the cold compact-open branch:

- remove the fast snapshot and fast public summary calls;
- render only the neutral HTML;
- when `selected_answer_target` exists, write the HTML directly to that empty
  slot; otherwise use a dedicated `st.empty()` placeholder;
- keep the existing synchronous report build and spinner;
- clear/replace the neutral state only after success or a fail-closed error;
- never alter report payload/session keys or report calculations.

- [ ] **Step 4: Keep the public route bootstrap visible through report work**

In `main()`, do not clear the public `Single-Stock Report` bootstrap in the
early public-shell branch. Let the existing final cleanup clear it after route
rendering. Other public routes keep their current early-clear behavior.

- [ ] **Step 5: Run lifecycle tests and verify GREEN**

Run the Step 2 command. Expected: all selected tests pass with pristine output.

- [ ] **Step 6: Run adjacent report and Workbench tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_dashboard_helpers.py \
  tests/test_dashboard_render_smoke.py \
  tests/test_single_stock_workflow.py \
  tests/test_research_mode_dashboard_contract.py \
  -k 'single_stock or company_workbench or loading or bootstrap'
```

Expected: all selected tests pass, including tickerless and non-open public
routes.

- [ ] **Step 7: Commit Task 3**

```bash
git add src/dashboard.py tests/test_dashboard_helpers.py \
  tests/test_dashboard_render_smoke.py tests/test_single_stock_workflow.py
git commit -m "Stabilize saved report loading"
```

Omit unchanged test files from `git add`.

---

### Task 4: Verify the complete journey and preservation contract

**Files:**
- Modify only if a behavior assertion is missing: `tests/test_research_accessibility_browser_gate.py`
- Modify only if a behavior assertion is missing: `tests/test_workspace_visual_browser_gate.py`
- Create screenshots only under a fresh `/tmp/stock-command-center-journey-repair-*` directory.
- Modify only if current behavior documentation is inaccurate: `README.md`, `docs/PERSONAL_RESEARCH_MODE.md`

**Interfaces:**
- Consumes: Tasks 1-3 behavior.
- Produces: fresh browser evidence, preservation matrix, final verification record, and documentation aligned to implemented behavior.

- [ ] **Step 1: Add any missing browser behavior assertions first**

The browser gates must verify observable behavior, not grep source text:

- Discover first answer contains both live counts and at least four unique
  Company Brief links before advanced filters;
- Monitor with `return_ticker=NVDA` shows one return action while its card/row
  counts equal the no-context Monitor state;
- Data Health and Proof History each expose exactly one `aria-current` cue;
- a cold report immediately exposes the neutral live status and no readiness
  answer, then exposes exactly one completed answer after stabilization;
- no `[aria-busy='true']` remains after the stable result.

- [ ] **Step 2: Run new browser assertions and verify RED if tests changed**

Run the exact changed test node(s). Expected before the corresponding browser
implementation adjustment: a behavior assertion fails for the missing cue,
ordering, or stable-state transition.

- [ ] **Step 3: Make only the minimal browser-facing adjustment and verify GREEN**

If the implementation already satisfies the behavior, do not add production
code. If a real gap is observed, change the smallest existing HTML/CSS helper
and rerun the exact failing browser node.

- [ ] **Step 4: Run the preservation suite**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_dashboard_navigation.py \
  tests/test_research_workspace.py \
  tests/test_research_mode_dashboard_contract.py \
  tests/test_data_health_console.py \
  tests/test_single_stock_workflow.py \
  tests/test_company_workbench_html.py \
  tests/test_stock_report.py \
  tests/test_scenario_lab.py \
  tests/test_research_thesis_journal.py
```

Expected: all tests pass. Record counts and warnings exactly.

- [ ] **Step 5: Run render, accessibility, and visual gates**

Run the repository-native targets for:

```bash
make research-dashboard-render-smoke
make research-accessibility-browser-check
make workspace-visual-browser-check
```

If the exact target spelling differs, use `make help`/Makefile truth and record
the actual target. Do not silently substitute a weaker check.

- [ ] **Step 6: Capture and inspect the eight required states**

Use the in-app Browser only. At 1280 x 720 and 390 x 844, save and inspect:

1. Research Desk;
2. Discover with saved companies and zero strict eligibility;
3. Company Workbench with a selected ticker;
4. Monitor with return context;
5. Data Health current-location state;
6. Proof History current-location state;
7. immediate report loading; and
8. resolved report.

Reject blank, loading-only (except state 7), cropped, wrong-route, or unstable
captures. Verify focus visibility, focus order, accessible names, reflow, and
overflow separately; screenshots alone do not prove accessibility.

- [ ] **Step 7: Verify protected paths and functional preservation**

Run:

```bash
git diff --name-only 19d59bea64d2a37f69024d60ab195c0b50467d27...HEAD
git diff --check
make diff-hygiene-summary
git status --short --branch
```

The diff must contain no `data/`, `outputs/`, readiness, proof-ledger,
generated research output, or `docs/assets/` path. Produce a preservation
matrix covering every function named in the approved goal.

- [ ] **Step 8: Run the full final gate**

Run:

```bash
make public-check
```

Wait for completion. Do not claim success from a partial, timed-out, or older
run.

- [ ] **Step 9: Commit only real Task 4 changes**

If tests or docs changed:

```bash
git add tests/test_research_accessibility_browser_gate.py \
  tests/test_workspace_visual_browser_gate.py README.md docs/PERSONAL_RESEARCH_MODE.md
git commit -m "Verify Journey Repair behavior"
```

Omit every unchanged path. Screenshots and temporary evidence remain outside
the repository.

- [ ] **Step 10: Complete review and handoff**

Run a task review after every task and one whole-branch review over
`19d59bea64d2a37f69024d60ab195c0b50467d27..HEAD`. Resolve Critical and
Important findings through the bounded review loop. Finish with a clean
worktree and provide integration choices without merging or pushing.
