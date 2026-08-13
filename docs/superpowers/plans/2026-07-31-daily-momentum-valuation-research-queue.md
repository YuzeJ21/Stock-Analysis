# Daily Momentum And Valuation Research Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only, fail-closed Discover queue for companies that satisfy the approved momentum, own-history valuation, and minimum fundamental-safeguard intersection.

**Architecture:** A new pure module owns immutable evidence/result contracts, deterministic gate evaluation, comparison, and presentation payloads. A narrow dashboard adapter reads the selected profile, builds existing indicators and valuation packets in memory, and renders an answer-first Discover section without reading legacy ranking outputs or writing artifacts.

**Tech Stack:** Python 3, dataclasses, pandas, existing indicator/valuation/source-rights/observation-recency modules, Streamlit, pytest.

## Global Constraints

- Research-only; no investment advice, recommendation, company rank, composite score, target price, probability, expected return, position sizing, transaction direction, broker integration, order routing, or auto-trading.
- Evaluate only saved `momentum_ready=true` rows.
- Require `close > SMA50 > SMA200`, positive three- and six-month returns, and positive SPY-relative return.
- Require a commercial-eligible, current Historical Valuation Regime at or below percentile `40.0`.
- Require positive free cash flow, non-negative revenue growth, and debt to equity at or below the configured quality-value threshold.
- Missing, non-finite, stale, unverified, restricted, malformed, or source-rights-ineligible evidence fails closed.
- Do not read legacy Monthly Picks, Momentum Leaders, Final Watchlist, portfolio, or action-language outputs.
- Do not write or generate CSV, JSON, reports, sample reports, screenshots, timing files, readiness, canonical data, or ledgers.
- Synthetic eligible evidence is test-only.
- Preserve independent actuals, consensus, Revenue, EPS, valuation, catalysts, outcomes, backtesting, calibration, indicator, review-metric, and readiness states.
- Stage exact intentional files only; never use `git add -A`.

---

### Task 1: Pure Daily Queue Contract

**Files:**
- Create: `src/daily_research_queue.py`
- Create: `tests/test_daily_research_queue.py`

**Interfaces:**
- Consumes: caller-supplied `DailyQueueEvidence` records and optional prior eligible ticker strings.
- Produces: `DailyQueuePolicy`, `DailyQueueEvidence`, `DailyQueueItem`, `DailyQueueResult`, `DailyQueueComparison`, `evaluate_daily_queue(...)`, `compare_daily_queues(...)`, `daily_queue_display_rows(...)`, and `daily_queue_summary_cards(...)`.

- [ ] **Step 1: Write failing tests for the exact approved intersection**

Create fixture evidence with finite values and assert that one row is eligible
only when every momentum, valuation, fundamental, recency, provenance, rights,
and field-scope condition passes. Parameterize each individual false, missing,
non-finite, stale, or restricted input and assert the stable blocker code.

```python
def test_exact_intersection_requires_every_approved_gate():
    result = evaluate_daily_queue((_eligible_evidence(),))
    assert result.eligible[0].ticker == "ALFA"
    assert result.eligible[0].blockers == ()


@pytest.mark.parametrize(
    ("changes", "blocker"),
    [
        ({"momentum_ready": False}, "momentum_not_ready"),
        ({"close": 99.0}, "price_not_above_sma50"),
        ({"sma_50": 89.0, "sma_200": 90.0}, "sma50_not_above_sma200"),
        ({"return_3m": 0.0}, "three_month_return_not_positive"),
        ({"return_6m": float("nan")}, "six_month_return_missing"),
        ({"relative_return_vs_spy": -0.01}, "spy_relative_return_not_positive"),
        ({"valuation_percentile": 40.01}, "valuation_percentile_above_threshold"),
        ({"free_cash_flow": 0.0}, "free_cash_flow_not_positive"),
        ({"revenue_growth": -0.001}, "revenue_growth_negative"),
        ({"debt_to_equity": 2.01}, "debt_above_threshold"),
        ({"current_market_eligible": False}, "current_market_evidence_ineligible"),
        ({"price_provenance_eligible": False}, "price_provenance_ineligible"),
        ({"price_rights_eligible": False}, "price_rights_ineligible"),
    ],
)
def test_each_failed_gate_withholds(changes, blocker):
    item = evaluate_daily_queue((replace(_eligible_evidence(), **changes),)).withheld[0]
    assert blocker in item.blockers
```

- [ ] **Step 2: Run the new tests and verify red**

Run: `python3 -m pytest tests/test_daily_research_queue.py -q`

Expected: FAIL because `src.daily_research_queue` does not exist.

- [ ] **Step 3: Implement immutable contracts and deterministic evaluation**

Use frozen dataclasses. Keep blocker order fixed in code rather than deriving it
from sets. Normalize tickers to uppercase, reject duplicate tickers
deterministically, and sort output by ticker.

```python
@dataclass(frozen=True)
class DailyQueuePolicy:
    valuation_percentile_max: float = 40.0
    maximum_debt_to_equity: float = 2.0


def evaluate_daily_queue(
    evidence: Iterable[DailyQueueEvidence],
    *,
    policy: DailyQueuePolicy = DailyQueuePolicy(),
) -> DailyQueueResult:
    items = tuple(sorted((_evaluate(row, policy) for row in evidence), key=lambda row: row.ticker))
    return DailyQueueResult(
        status="eligible" if any(row.state == "eligible" for row in items) else "withheld",
        eligible=tuple(row for row in items if row.state == "eligible"),
        withheld=tuple(row for row in items if row.state == "withheld"),
        boundary=QUEUE_BOUNDARY,
    )
```

- [ ] **Step 4: Add comparison, display, and prohibited-field tests**

Assert `baseline_missing`, `new_today`, `still_qualifies`, and `exited_today`
behavior; alphabetic ordering; exact ticker-bound Company Workbench URLs; and
the absence of score/rank/recommendation/probability/action keys and copy.

- [ ] **Step 5: Run focused tests**

Run: `python3 -m pytest tests/test_daily_research_queue.py -q`

Expected: PASS.

- [ ] **Step 6: Commit the pure contract**

```bash
git add -- src/daily_research_queue.py tests/test_daily_research_queue.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Add fail-closed daily research queue"
```

### Task 2: Selected-Profile Evidence Adapter

**Files:**
- Create: `src/daily_research_queue_adapter.py`
- Create: `tests/test_daily_research_queue_adapter.py`

**Interfaces:**
- Consumes: explicit `project_root: Path`, `data_dir: Path`, `as_of: date`, and optional `DailyQueuePolicy`.
- Produces: `build_daily_research_queue_from_files(...) -> DailyQueueResult` and `DailyQueueBuildStatus` with source/coverage diagnostics.
- Uses from Task 1: `DailyQueueEvidence`, `DailyQueuePolicy`, and `evaluate_daily_queue`.

- [ ] **Step 1: Write failing adapter tests with temporary files**

Build temporary readiness, prices, fundamentals, universe, historical
valuation, config, and source-rights inputs. Assert the adapter:

- reads only `momentum_ready=true` tickers;
- uses `build_indicator_snapshot`, not legacy outputs;
- creates eligible synthetic evidence only when every lineage/right is present;
- returns an empty/withheld result for an absent valuation ledger;
- withholds stale ticker, profile, or SPY observations;
- withholds missing price lineage fields;
- withholds unsupported fundamental field scope;
- isolates malformed ticker evidence; and
- leaves a byte snapshot of the temporary tree unchanged.

- [ ] **Step 2: Run the adapter tests and verify red**

Run: `python3 -m pytest tests/test_daily_research_queue_adapter.py -q`

Expected: FAIL because the adapter does not exist.

- [ ] **Step 3: Implement defensive read-only loading**

Read CSVs with one `optional_csv()` helper that returns an empty frame on
missing, malformed, encoding, or OS errors. Normalize tickers and numeric
fields. Build the indicator snapshot once. Group valuation observations by
ticker before building packets. Evaluate recency from explicit `as_of`; never
use file mtimes.

Price commercial eligibility requires explicit row-level `source`,
`source_ref`, and `retrieved_at`, an approved source-rights entry, and supported
`prices` scope. Fundamental eligibility requires explicit source/reference
evidence and approved registered scope for every required fundamental input.

- [ ] **Step 4: Run adapter tests**

Run: `python3 -m pytest tests/test_daily_research_queue_adapter.py tests/test_daily_research_queue.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the adapter**

```bash
git add -- src/daily_research_queue_adapter.py tests/test_daily_research_queue_adapter.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Build daily queue from reviewed evidence"
```

### Task 3: Discover Integration

**Files:**
- Modify: `src/dashboard.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`
- Modify: `tests/test_dashboard_helpers.py`

**Interfaces:**
- Consumes from Task 2: `build_daily_research_queue_from_files(...)`.
- Consumes from Task 1: `daily_queue_display_rows(...)`, `daily_queue_summary_cards(...)`.
- Produces: `load_dashboard_daily_research_queue(...)` and `render_daily_research_queue(...)`.

- [ ] **Step 1: Write failing dashboard contract tests**

Assert that Discover:

- renders `Daily Momentum & Valuation Research Queue` before the general stock
  selector;
- renders current eligible rows or a truthful empty/withheld state;
- places blocker detail under `Advanced: daily queue evidence`;
- uses `?mode=research&page=company-workbench&ticker=<TICKER>`;
- contains no rank, score, recommendation, target, probability, expected
  return, buy/sell, or portfolio-action language; and
- does not call a writer or legacy output loader.

- [ ] **Step 2: Run dashboard tests and verify red**

Run:

```bash
python3 -m pytest \
  tests/test_research_mode_dashboard_contract.py \
  tests/test_dashboard_helpers.py \
  -q
```

Expected: FAIL because the Discover queue functions and markers are absent.

- [ ] **Step 3: Add the dashboard loader and renderer**

The loader passes `review_date` explicitly and returns a fail-closed result on
adapter exceptions. The renderer leads with current eligibility, uses
alphabetical rows, limits first-screen copy, and keeps technical blockers in a
collapsed Advanced expander. It renders one ticker-bound Workbench action per
eligible row and does not expose a company score.

- [ ] **Step 4: Integrate before the stock selector**

Call the queue loader and renderer immediately after
`## Which stock can I review?`, then retain the existing general selector and
cohort context unchanged.

- [ ] **Step 5: Run focused dashboard and queue tests**

Run:

```bash
python3 -m pytest \
  tests/test_daily_research_queue.py \
  tests/test_daily_research_queue_adapter.py \
  tests/test_research_mode_dashboard_contract.py \
  tests/test_dashboard_helpers.py \
  -q
```

Expected: PASS.

- [ ] **Step 6: Commit Discover integration**

```bash
git add -- src/dashboard.py tests/test_research_mode_dashboard_contract.py tests/test_dashboard_helpers.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Show daily research queue in Discover"
```

### Task 4: Methodology, Roadmap, And Continuation Contract

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/METHODOLOGY.md`
- Modify: `docs/PERSONAL_RESEARCH_MODE.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`

**Interfaces:**
- Documents the exact contract and current empty/withheld real-data state.
- Does not change runtime behavior or generated data.

- [ ] **Step 1: Update methodology and user workflow documentation**

Document the strict intersection, alphabetical non-ranking, no-baseline
behavior, exact-source/current-observation gates, empty-state truth, and
Company Workbench handoff.

- [ ] **Step 2: Update roadmap truth**

Record the local feature implementation separately from its external
operational gates. State that an absent historical valuation ledger and
unapproved commercial price history prevent real daily candidates.

- [ ] **Step 3: Update continuation instructions**

Set the next executable lane to direct browser verification and one bounded
permitted price/valuation evidence activation path. Require skipping unavailable
providers once and forbid generated data churn.

- [ ] **Step 4: Run wording and whitespace checks**

Run:

```bash
make public-wording-check
git diff --check
```

Expected: PASS.

- [ ] **Step 5: Commit documentation**

```bash
git add -- ROADMAP.md docs/METHODOLOGY.md docs/PERSONAL_RESEARCH_MODE.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md
make staged-hygiene-check
git diff --cached --check
git commit -m "Document daily research queue boundaries"
```

### Task 5: Full Verification And PR Synchronization

**Files:**
- Modify only if a verified defect is found in the intentional feature scope.

**Interfaces:**
- Produces exact-tree local and GitHub evidence.

- [ ] **Step 1: Run focused verification**

```bash
python3 -m pytest \
  tests/test_daily_research_queue.py \
  tests/test_daily_research_queue_adapter.py \
  tests/test_research_mode_dashboard_contract.py \
  tests/test_dashboard_helpers.py \
  -q
```

- [ ] **Step 2: Run the complete suite and product gates**

```bash
python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make public-wording-check
make public-check
make commercial-beta-check
make commercial-beta-performance-gate
make commercial-beta-release-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
```

- [ ] **Step 3: Run direct browser verification**

Run:

```bash
make research-accessibility-browser-check TIMEOUT_SECONDS=90
```

The queue must render at desktop and phone widths without traceback,
horizontal overflow, duplicate ticker actions, or non-ticker-bound Workbench
links. If the managed browser cannot launch, classify that environment once;
do not claim browser completion.

- [ ] **Step 4: Verify staged and generated-artifact hygiene**

Confirm only the pre-existing 18 generated CSV/output paths remain unstaged.
Run `make staged-hygiene-check` if anything is staged. Never stage them.

- [ ] **Step 5: Push and update draft PR**

Push only `codex/personal-research-mode-mvp`, update PR #113 with the feature,
truthful withheld-data state, verification, and external unblock conditions,
keep it draft, and require exact-head CI.

- [ ] **Step 6: Record the handoff**

Report repository/PR state, product stage, feature behavior, current real-data
result, tests, commit/push status, generated exclusions, external dependencies,
remaining gates, exact next step, and review safety.
