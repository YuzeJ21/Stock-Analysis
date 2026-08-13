# Quarterly Cash-Generation Evidence Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add source-bound quarterly operating-margin, free-cash-flow, and FCF-margin trend readiness without adding a data file, changing Earnings Nowcast, or fabricating real-company evidence.

**Architecture:** A focused domain module validates immutable in-memory component observations and derives metric points from compatible evidence. The existing quarterly trend composer accepts observations optionally and keeps metric readiness independent; production callers supply none until a reviewed adapter exists, so real output remains withheld. Existing answer-first cards show conclusions while component lineage stays Advanced.

**Tech Stack:** Python 3.12 dataclasses, existing `parse_utc_timestamp` and quarterly trend contracts, pytest, Streamlit AppTest.

## Global Constraints

- Do not add, generate, modify, or stage any CSV, JSON, report, sample report, screenshot, browser timing, canonical data, template, writer, or Make target.
- Keep `QuarterlyActual`, Earnings Nowcast input hashes, Revenue/EPS readiness, consensus readiness, ranges, backtesting, and calibration unchanged.
- Q4 requires `explicit_filed_quarter`; annual-minus-nine-month derivation is forbidden.
- Free cash flow is exactly `cash_from_operations + capital_expenditures`, preserving the reported capex cash-flow sign.
- Do not infer capex sign, accounting basis, duration basis, source time, fiscal identity, or metric compatibility.
- Supplemental readiness cannot unlock DCF, peers, catalysts, outcomes, Nowcast, backtesting, calibration, rankings, recommendations, or actions.
- Synthetic observations are test-only and use `source="synthetic_test_fixture"`.
- Empty production input stays visibly withheld.
- Stage exact code, documentation, and test paths only; never use `git add -A`.

## File Map

- Create `src/quarterly_cash_generation.py`: observation validation, revision resolution, compatibility, derived metric points, and blockers.
- Create `tests/test_quarterly_cash_generation.py`: pure in-memory domain tests.
- Modify `src/quarterly_business_trend.py` and `tests/test_quarterly_business_trend.py`: optional observations and independent trends.
- Modify `src/research_workspace.py`, `tests/test_research_workspace.py`, and `tests/test_dashboard_helpers.py`: answer-first cards and Advanced evidence boundary.
- Modify `docs/METHODOLOGY.md`, `docs/PROVENANCE_CONTRACT.md`, `docs/PERSONAL_RESEARCH_MODE.md`, `ROADMAP.md`, `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`, and `tests/test_public_v1_release_docs.py`: durable claims and maturity boundary.

---

### Task 1: Immutable Quarterly Component Evidence

**Files:**
- Create: `src/quarterly_cash_generation.py`
- Create: `tests/test_quarterly_cash_generation.py`

**Interfaces:**
- Produces: `QuarterlyBusinessObservation`, `QuarterlyBusinessMetricPoint`, `QuarterlyBusinessDerivation`, and `derive_quarterly_business_metrics(ticker, observations, revenue_actuals, *, as_of=None)`.
- Consumes: `QuarterlyActual` and `parse_utc_timestamp` from `src.earnings_nowcast_contract`.

- [ ] **Step 1: Write failing constructor tests**

Use this fixture and add parameterized failures for unsupported metric, invalid fiscal period, non-finite value, non-positive scale, naive timestamps, and invalid Q4 evidence:

```python
def observation(period="2025-Q1", metric="cash_from_operations", value=100.0, **overrides):
    values = {
        "ticker": "syn1", "fiscal_period": period, "period_end_date": "2025-03-31",
        "metric": metric, "value": value, "currency": "usd", "unit_scale": 1.0,
        "accounting_basis": "gaap", "duration_basis": "three_months",
        "source": "synthetic_test_fixture", "source_ref": f"fixture:{period}:{metric}",
        "published_at": "2025-05-15T12:00:00+00:00",
        "retrieved_at": "2026-07-18T12:00:00+00:00", "q4_evidence_state": "not_q4",
    }
    values.update(overrides)
    return QuarterlyBusinessObservation(**values)

def test_observation_requires_explicit_q4_evidence():
    with pytest.raises(ValueError, match="Q4 requires explicit filed-quarter evidence"):
        observation(period="2025-Q4", period_end_date="2025-12-31")
```

- [ ] **Step 2: Verify the tests fail**

Run: `python3 -m pytest tests/test_quarterly_cash_generation.py -q`

Expected: import failure because the module does not exist.

- [ ] **Step 3: Implement immutable types and validation**

Implement these exact public types:

```python
SUPPORTED_COMPONENT_METRICS = frozenset({"operating_income", "cash_from_operations", "capital_expenditures"})

@dataclass(frozen=True)
class QuarterlyBusinessObservation:
    ticker: str
    fiscal_period: str
    period_end_date: str
    metric: str
    value: float
    currency: str
    unit_scale: float
    accounting_basis: str
    duration_basis: str
    source: str
    source_ref: str
    published_at: str
    retrieved_at: str
    q4_evidence_state: str = "not_q4"
    supersedes_source_ref: str | None = None

@dataclass(frozen=True)
class QuarterlyBusinessMetricPoint:
    metric: str
    fiscal_period: str
    period_end_date: str
    value: float
    definition: tuple[object, ...]
    source_refs: tuple[str, ...]

@dataclass(frozen=True)
class QuarterlyBusinessDerivation:
    points: tuple[QuarterlyBusinessMetricPoint, ...]
    blockers: tuple[str, ...]
    revision_count: int
    supplied_observation_count: int
```

Validate ISO dates with `date.fromisoformat`, fiscal periods with `^\d{4}-Q[1-4]$`, numeric values with `math.isfinite`, timestamps with `parse_utc_timestamp`, and required text after normalization. Permit `not_q4` only for Q1-Q3 and `explicit_filed_quarter` only for Q4.

- [ ] **Step 4: Verify constructor tests pass**

Run: `python3 -m pytest tests/test_quarterly_cash_generation.py -q`

Expected: constructor tests pass.

- [ ] **Step 5: Write failing derivation tests**

Test the exact formulas and source lineage:

```python
def test_derivation_uses_explicit_components():
    result = derive_quarterly_business_metrics(
        "SYN1",
        [observation(metric="operating_income", value=50.0),
         observation(metric="cash_from_operations", value=60.0),
         observation(metric="capital_expenditures", value=-20.0)],
        [actual("2025-Q1", revenue=200.0)],
    )
    points = {point.metric: point for point in result.points}
    assert points["operating_margin"].value == 0.25
    assert points["free_cash_flow"].value == 40.0
    assert points["fcf_margin"].value == 0.20
    assert points["free_cash_flow"].source_refs == (
        "fixture:2025-Q1:cash_from_operations", "fixture:2025-Q1:capital_expenditures"
    )
```

Also assert cutoff filtering, explicit revision resolution, affected-component ambiguity, and incompatibility across currency, scale, accounting basis, duration basis, fiscal period, and period end.

- [ ] **Step 6: Implement revision resolution and derivation**

Group by `(fiscal_period, metric)`, deduplicate source references, accept exact duplicates, and resolve only one explicit revision leaf. Record stable blockers such as `2025-Q1:capital_expenditures:ambiguous_revision`. Require compatible Revenue and a non-zero denominator for margin points. Calculate:

```python
operating_margin = operating_income.value / revenue.revenue_actual
free_cash_flow = cash_from_operations.value + capital_expenditures.value
fcf_margin = free_cash_flow / revenue.revenue_actual
```

- [ ] **Step 7: Verify domain behavior and absence of persistence**

Run:

```bash
python3 -m pytest tests/test_quarterly_cash_generation.py -q
rg -n "open\(|write_text|write_bytes|to_csv|json\.dump|csv\.writer|argparse|output_dir" src/quarterly_cash_generation.py
```

Expected: tests pass and the persistence scan returns no matches.

- [ ] **Step 8: Commit Task 1**

```bash
git add -- src/quarterly_cash_generation.py tests/test_quarterly_cash_generation.py
git commit -m "Add quarterly cash generation evidence contract"
```

---

### Task 2: Independent Trend Composition

**Files:**
- Modify: `src/quarterly_business_trend.py:13-345`
- Modify: `tests/test_quarterly_business_trend.py`

**Interfaces:**
- Consumes Task 1 types and derivation.
- Produces `QuarterlyTrendPacket.operating_margin`, `.free_cash_flow`, `.fcf_margin`, and the `business_observations` builder argument.

- [ ] **Step 1: Write failing integration tests**

```python
def test_supplemental_metrics_stay_withheld_without_observations():
    packet = build_quarterly_trend_packet("SYN1", [_actual("2025-Q1", revenue=120, eps=1.2)])
    assert packet.operating_margin.status == "withheld"
    assert packet.free_cash_flow.status == "withheld"
    assert packet.fcf_margin.status == "withheld"

def test_supplemental_metric_trends_are_independent():
    packet = build_quarterly_trend_packet(
        "SYN1", actual_history(), business_observations=business_history()
    )
    assert packet.operating_margin.status == "ready"
    assert packet.free_cash_flow.status == "ready"
    assert packet.fcf_margin.status == "ready"
    assert packet.revenue.latest_value == 120
    assert packet.eps.latest_value == 1.2
```

- [ ] **Step 2: Verify integration tests fail**

Run: `python3 -m pytest tests/test_quarterly_business_trend.py -q`

Expected: missing fields and keyword argument.

- [ ] **Step 3: Extend the packet and builder**

Add three `QuarterlyMetricTrend` fields after `eps`, plus:

```python
def _withheld_metric(metric: str, reason: str) -> QuarterlyMetricTrend:
    return QuarterlyMetricTrend(metric, "withheld", None, "", "", None, None, (), (), reason)

def build_quarterly_trend_packet(
    ticker: str,
    actuals: Iterable[QuarterlyActual],
    *,
    as_of: str | None = None,
    business_observations: Iterable[QuarterlyBusinessObservation] = (),
) -> QuarterlyTrendPacket:
```

Materialize the optional iterable once. Zero observations yield three withheld trends. Otherwise derive points from the resolved Revenue rows and reuse exact previous-quarter, prior-year-quarter, definition-compatibility, and percent-change behavior. Keep packet-level status based on Revenue/EPS exactly as before.

- [ ] **Step 4: Render all five rows from packet state**

Replace hard-coded supplemental placeholders with one loop over Revenue, EPS, operating margin, free cash flow, and FCF margin. Format margin display values as percentages while retaining decimal values in the domain packet. Preserve component references joined with `;` only in the Advanced row.

- [ ] **Step 5: Run focused and Nowcast regressions**

```bash
python3 -m pytest tests/test_quarterly_cash_generation.py tests/test_quarterly_business_trend.py -q
python3 -m pytest tests/test_earnings_nowcast_contract.py tests/test_earnings_nowcast_readiness.py tests/test_earnings_nowcast_report.py -q
```

Expected: all pass with no schema or input-hash change.

- [ ] **Step 6: Commit Task 2**

```bash
git add -- src/quarterly_business_trend.py tests/test_quarterly_business_trend.py
git commit -m "Compose independent quarterly cash generation trends"
```

---

### Task 3: Answer-First Workbench Rendering

**Files:**
- Modify: `src/research_workspace.py:238-266`
- Modify: `tests/test_research_workspace.py:91-115`
- Modify: `tests/test_dashboard_helpers.py`

**Interfaces:**
- Consumes Task 2 packet fields.
- Produces truthful supported or withheld cards without a loader, writer, or source promotion.

- [ ] **Step 1: Write failing card tests**

Assert `OPERATING MARGIN`, `FREE CASH FLOW`, and `FCF MARGIN` cards are `Withheld` without observations and say a reviewed quarterly source adapter is required. With ready in-memory observations, assert values and comparison changes appear, but raw source references and formula internals do not appear in primary card text.

- [ ] **Step 2: Verify card tests fail**

Run: `python3 -m pytest tests/test_research_workspace.py -q`

Expected: supplemental cards are missing.

- [ ] **Step 3: Extend the existing card loop**

Use five entries with `number` display for Revenue/EPS/FCF and `percent` for operating margin/FCF margin. Card bodies contain comparison changes or a concise boundary only. Source references, component values, formula details, and commands remain outside primary cards.

- [ ] **Step 4: Add dashboard boundary assertions**

Assert the dashboard still loads no supplemental file and keeps the table inside the existing collapsed quarterly source-evidence expander. Assert no new writer, template, output path, or Make target exists for this feature.

- [ ] **Step 5: Verify workspace and Research routes**

```bash
python3 -m pytest tests/test_research_workspace.py tests/test_dashboard_helpers.py -q
make research-dashboard-render-smoke
```

Expected: tests and all four Research routes pass; production supplemental output remains withheld.

- [ ] **Step 6: Commit Task 3**

```bash
git add -- src/research_workspace.py tests/test_research_workspace.py tests/test_dashboard_helpers.py
git commit -m "Render cash generation evidence without file output"
```

---

### Task 4: Methodology, Maturity Boundary, And Release Verification

**Files:**
- Modify: `docs/METHODOLOGY.md:41-49`
- Modify: `docs/PROVENANCE_CONTRACT.md:38-48`
- Modify: `docs/PERSONAL_RESEARCH_MODE.md:55-62`
- Modify: `ROADMAP.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: `tests/test_public_v1_release_docs.py`

**Interfaces:**
- Consumes verified Tasks 1-3.
- Produces durable methodology and maturity claims.

- [ ] **Step 1: Write failing documentation tests**

```python
def test_quarterly_cash_generation_docs_preserve_no_file_boundary():
    methodology = _read("docs/METHODOLOGY.md")
    provenance = _read("docs/PROVENANCE_CONTRACT.md")
    roadmap = _read("ROADMAP.md")
    assert "cash from operations + reported capital expenditures" in methodology
    assert "explicit_filed_quarter" in provenance
    assert "no new data file, writer, template, or generated artifact" in provenance
    assert "methodology maturity" in roadmap
    assert "does not prove real-company coverage or market validation" in roadmap
```

- [ ] **Step 2: Verify documentation tests fail**

Run: `python3 -m pytest tests/test_public_v1_release_docs.py -q`

Expected: new claims are absent.

- [ ] **Step 3: Update methodology, provenance, mode guide, roadmap, and continuation prompt**

Document formulas, source timestamps, revision behavior, compatibility, Q4 evidence, independent readiness, no persistence surface, unchanged downstream readiness, and withheld production state. Record that this improves methodology completeness, cash-conversion transparency, adapter extensibility, and reviewer trust—but does not prove real-company coverage, licensed source operation, hosted reliability, external reviewer success, calibration, commercial demand, or product-market fit.

- [ ] **Step 4: Run focused tests**

```bash
python3 -m pytest tests/test_quarterly_cash_generation.py tests/test_quarterly_business_trend.py tests/test_research_workspace.py tests/test_public_v1_release_docs.py -q
```

Expected: all pass.

- [ ] **Step 5: Run the complete verification bundle**

```bash
python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make public-wording-check
make public-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
```

Expected: every gate passes; before commit only intentional code/docs/tests appear, with zero generated artifact candidates.

- [ ] **Step 6: Stage exact implementation paths and verify**

```bash
git add -- src/quarterly_cash_generation.py src/quarterly_business_trend.py src/research_workspace.py tests/test_quarterly_cash_generation.py tests/test_quarterly_business_trend.py tests/test_research_workspace.py tests/test_dashboard_helpers.py tests/test_public_v1_release_docs.py docs/METHODOLOGY.md docs/PROVENANCE_CONTRACT.md docs/PERSONAL_RESEARCH_MODE.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md ROADMAP.md
make staged-hygiene-check
git diff --cached --check
```

Expected: product/code/docs/test paths only; zero generated, canonical-data, report, sample-report, or manual-review paths.

- [ ] **Step 7: Commit, push, and update PR #113**

```bash
git commit -m "Add quarterly cash generation evidence contract"
git push origin codex/personal-research-mode-mvp
```

Update PR #113 with independent readiness, no-file boundary, results, maturity assessment, and the external reviewed-adapter dependency. Keep it draft.

- [ ] **Step 8: Verify final truth**

```bash
git status --short --branch
git rev-list --left-right --count HEAD...origin/codex/personal-research-mode-mvp
gh pr view 113 --json state,isDraft,mergeStateStatus,headRefOid,url
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
```

Expected: clean tree, `0 0`, PR open and draft at HEAD, pilot-ready with manual gates, clean hygiene.

## Plan Self-Review

- Every spec field, formula, cutoff, revision, Q4, readiness, rendering, no-file, documentation, and verification requirement maps to Tasks 1-4.
- Scope is one domain contract and existing-workflow integration; no adapter, extraction, persistence, new route, scheduler, or external activation.
- Task 1 type names and Task 2-3 consumers are consistent.
- The plan creates Python code/tests and edits docs/tests only; it introduces no generated artifact path.
- Maturity claims distinguish methodology and trust gains from market validation, hosting, licensed operation, calibration, and product-market fit.
