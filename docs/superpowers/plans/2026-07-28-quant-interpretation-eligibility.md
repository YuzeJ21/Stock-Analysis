# Quant Interpretation Eligibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one provider-neutral, fail-closed interpretation overlay for valuation, indicators, and review/risk metrics without changing their calculations or readiness.

**Architecture:** A new pure module owns immutable evidence and decision contracts. Thin adapters in the three existing calculation modules translate existing statuses plus explicitly supplied recency, provenance, rights, and field-scope states; stock-report and dashboard presentation consume the decisions without mutating calculation results.

**Tech Stack:** Python 3.12, frozen dataclasses, pandas, existing observation-recency contracts, pytest, Streamlit AppTest.

## Global Constraints

- Keep calculation, readiness, observation recency, provenance, rights, field scope, display eligibility, and commercial eligibility independent.
- Allowed interpretation states are exactly `current_context_eligible`, `historical_review_only`, and `withheld`.
- `current_context_eligible` requires an available calculation, current accepted observation, verified provenance, and permitted or genuinely not-applicable rights and field scope.
- Partial calculations never become current-context eligible.
- Stale or incompletely proven calculations may remain historical/review-only only when provenance is not invalid and rights/field scope are not restricted.
- Missing, malformed, future, invalid, restricted, or unavailable evidence fails closed.
- Do not infer `verified` or `permitted` from non-empty free text or provider class names.
- Do not modify formulas, readiness, forecasts, scenarios, consensus, Revenue, EPS, peers, catalysts, outcomes, backtesting, calibration, or ledgers.
- Do not expose a nowcast, probability, ranking, recommendation, allocation, transaction direction, or expected-return score.
- Tests use synthetic fixtures and write no repository CSV, JSON, report, screenshot, timing, canonical-data, or ledger artifact.

---

### Task 1: Pure Interpretation Evaluator

**Files:**
- Create: `src/quant_interpretation_eligibility.py`
- Create: `tests/test_quant_interpretation_eligibility.py`

**Interfaces:**
- Produces: `QuantEvidenceAssessment(family: str, scope: str, calculation_state: str, observation_state: str, observation_through_date: str, provenance_state: str, rights_state: str, field_scope_state: str, evidence_notes: tuple[str, ...])`.
- Produces: `QuantInterpretationEligibility(family: str, scope: str, interpretation_state: str, commercial_eligible: bool, reasons: tuple[str, ...], summary: str, boundary: str)`.
- Produces: `evaluate_quant_interpretation(assessment: QuantEvidenceAssessment) -> QuantInterpretationEligibility`.

- [ ] **Step 1: Write the failing literal decision-table tests**

```python
import pytest

from src.quant_interpretation_eligibility import (
    QuantEvidenceAssessment,
    evaluate_quant_interpretation,
)


@pytest.mark.parametrize(
    ("overrides", "state", "commercial", "reasons"),
    [
        ({}, "current_context_eligible", True, ()),
        ({"observation_state": "stale_review_only"}, "historical_review_only", False, ("observation_stale",)),
        ({"provenance_state": "unverified"}, "historical_review_only", False, ("provenance_unverified",)),
        ({"rights_state": "unverified"}, "historical_review_only", False, ("rights_unverified",)),
        ({"calculation_state": "partial"}, "historical_review_only", False, ("calculation_partial",)),
        ({"observation_state": "unavailable"}, "withheld", False, ("observation_unavailable",)),
        ({"provenance_state": "invalid"}, "withheld", False, ("provenance_invalid",)),
        ({"rights_state": "restricted"}, "withheld", False, ("rights_restricted",)),
    ],
)
def test_interpretation_table(overrides, state, commercial, reasons):
    values = {
        "family": "valuation",
        "scope": "NVDA:dcf",
        "calculation_state": "available",
        "observation_state": "current",
        "observation_through_date": "2026-07-27",
        "provenance_state": "verified",
        "rights_state": "permitted",
        "field_scope_state": "permitted",
        "evidence_notes": (),
    }
    result = evaluate_quant_interpretation(
        QuantEvidenceAssessment(**(values | overrides))
    )
    assert (result.interpretation_state, result.commercial_eligible) == (
        state,
        commercial,
    )
    assert result.reasons == reasons
```

- [ ] **Step 2: Run the new test and verify the expected import failure**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_quant_interpretation_eligibility.py -q`

Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement closed vocabularies, validation, and ordered additive reasons**

```python
INTERPRETATION_BOUNDARY = (
    "Research interpretation only; this does not change readiness, create a "
    "forecast or probability, rank a company, or provide an investment action."
)


def evaluate_quant_interpretation(
    assessment: QuantEvidenceAssessment,
) -> QuantInterpretationEligibility:
    assessment.validate()
    reasons = _ordered_reasons(assessment)
    if _must_withhold(assessment):
        state = "withheld"
    elif _can_be_current(assessment):
        state = "current_context_eligible"
    else:
        state = "historical_review_only"
    return QuantInterpretationEligibility(
        family=assessment.family,
        scope=assessment.scope,
        interpretation_state=state,
        commercial_eligible=state == "current_context_eligible"
        and assessment.rights_state == "permitted"
        and assessment.field_scope_state == "permitted",
        reasons=reasons,
        summary=_summary(state, assessment.observation_through_date),
        boundary=INTERPRETATION_BOUNDARY,
    )
```

Reject unknown or empty family/scope/state values with `ValueError`. Deduplicate reasons in a fixed order without dropping independent blockers. Treat `not_applicable` as sufficient only for a genuinely non-applicable rights or field-scope dimension; it does not make `commercial_eligible=True`.

- [ ] **Step 4: Add constructor and multi-blocker boundary tests**

Add literal cases proving unknown tokens raise, future/malformed observations are supplied as unavailable and withheld, two blockers remain two ordered reasons, `not_applicable` cannot make a commercial result, and original tuples/objects are not mutated.

- [ ] **Step 5: Run focused tests and commit**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_quant_interpretation_eligibility.py -q
git diff --check
git add -- src/quant_interpretation_eligibility.py tests/test_quant_interpretation_eligibility.py
make staged-hygiene-check
git commit -m "Add quant interpretation eligibility contract"
```

Expected: focused tests and staged hygiene pass; only the new module and tests are committed.

### Task 2: Three Thin Family Adapters

**Files:**
- Modify: `src/valuation.py`
- Modify: `src/indicators.py`
- Modify: `src/review_metrics.py`
- Modify: `tests/test_valuation.py`
- Modify: `tests/test_indicators.py`
- Modify: `tests/test_review_metrics.py`

**Interfaces:**
- Consumes: `ObservationRecency` from `src.observation_recency`.
- Produces: `valuation_quant_assessment(result: ValuationResult | DCFResult | RelativeValuationResult, *, scope: str, observation: ObservationRecency, provenance_state: str, rights_state: str, field_scope_state: str) -> QuantEvidenceAssessment`.
- Produces: `indicator_quant_assessment(row: Mapping[str, object], *, metric_name: str, observation: ObservationRecency, benchmark_observation: ObservationRecency | None, provenance_state: str, rights_state: str, field_scope_state: str) -> QuantEvidenceAssessment`.
- Produces: `review_metric_quant_assessment(metric: ReviewMetric, *, ticker: str, observation: ObservationRecency, benchmark_observation: ObservationRecency | None, provenance_state: str, rights_state: str, field_scope_state: str) -> QuantEvidenceAssessment`.

- [ ] **Step 1: Write failing valuation adapter tests**

```python
def test_calculated_valuation_with_stale_observation_is_historical_only():
    result = build_valuation_result(_complete_valuation_input())
    assessment = valuation_quant_assessment(
        result,
        scope="NVDA:valuation",
        observation=_recency("NVDA", "stale_review_only", "2026-05-22"),
        provenance_state="verified",
        rights_state="permitted",
        field_scope_state="permitted",
    )
    decision = evaluate_quant_interpretation(assessment)
    assert result.status == "calculated"
    assert decision.interpretation_state == "historical_review_only"
```

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_valuation.py -q`

Expected: FAIL because `valuation_quant_assessment` does not exist.

- [ ] **Step 2: Implement valuation status mapping without touching result objects**

Map `calculated` to `available`, `partial` and `peer_data_unavailable` to `partial`, `not_applicable` to `excluded`, and every insufficient/unknown result to `unavailable`. Require a non-empty matching scope and copy only deterministic notes; do not parse free-text source metadata into proof states.

- [ ] **Step 3: Write failing indicator dependency tests**

```python
def test_relative_indicator_requires_both_ticker_and_benchmark_observations():
    assessment = indicator_quant_assessment(
        {"ticker": "NVDA", "relative_return_vs_spy": 0.12},
        metric_name="relative_return_vs_spy",
        observation=_recency("NVDA", "current", "2026-07-27"),
        benchmark_observation=_recency("SPY", "stale_review_only", "2026-06-01"),
        provenance_state="verified",
        rights_state="permitted",
        field_scope_state="permitted",
    )
    assert evaluate_quant_interpretation(
        assessment
    ).interpretation_state == "historical_review_only"
```

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_indicators.py -q`

Expected: FAIL because the adapter does not exist.

- [ ] **Step 4: Implement indicator mapping and benchmark composition**

Use `pd.to_numeric(..., errors="coerce")` and `math.isfinite` for the selected metric. Combine recency by the strictest state: unavailable beats stale, stale beats current. Require a benchmark observation for `relative_return_vs_spy`, `relative_return_vs_qqq`, and `relative_return_vs_sector_etf`; reject ticker or benchmark scope mismatches.

- [ ] **Step 5: Write failing review-metric tests and implement its adapter**

```python
def test_ready_review_metric_does_not_imply_current_context():
    metric = ReviewMetric("max_drawdown", "ready", -0.22, "percent")
    assessment = review_metric_quant_assessment(
        metric,
        ticker="NVDA",
        observation=_recency("NVDA", "current", "2026-07-27"),
        benchmark_observation=None,
        provenance_state="unverified",
        rights_state="unverified",
        field_scope_state="unverified",
    )
    assert assessment.calculation_state == "available"
    assert evaluate_quant_interpretation(
        assessment
    ).interpretation_state == "historical_review_only"
```

Map `ready`, `partial`, `blocked`, and `excluded` exactly. Require benchmark evidence only when `metric.benchmark` is non-empty. Do not treat `source_context` as structured provenance.

- [ ] **Step 6: Run all adapter tests and commit**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_valuation.py tests/test_indicators.py tests/test_review_metrics.py tests/test_quant_interpretation_eligibility.py -q
git diff --check
git add -- src/valuation.py src/indicators.py src/review_metrics.py tests/test_valuation.py tests/test_indicators.py tests/test_review_metrics.py
make staged-hygiene-check
git commit -m "Adapt quant results to evidence eligibility"
```

Expected: focused tests pass and existing numerical outputs remain unchanged.

### Task 3: Stock-Report and Dashboard Consumption

**Files:**
- Modify: `src/stock_report.py`
- Modify: `src/dashboard.py`
- Modify: `tests/test_stock_report.py`
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `tests/test_dashboard_render_smoke.py`

**Interfaces:**
- Produces: `StockReport.quant_interpretation: dict[str, object]` with `valuation`, `indicators`, and `review_metrics` keys.
- Produces: `stock_report_quant_interpretation_cards(report_payload: Mapping[str, object]) -> list[dict[str, object]]`.
- Consumes: explicit selected-ticker/SPY/QQQ `ObservationRecency` results; explicit unverified proof states remain unverified until a caller supplies structured proof.

- [ ] **Step 1: Write failing stock-report contract tests**

```python
def test_stock_report_keeps_quant_values_but_adds_independent_eligibility(provider):
    report = build_stock_report("NVDA", provider)
    payload = report.to_dict()
    assert payload["valuation_snapshot"]["status"] == "calculated"
    assert payload["quant_interpretation"]["valuation"]["interpretation_state"] in {
        "historical_review_only",
        "withheld",
    }
    assert payload["quant_interpretation"]["valuation"]["commercial_eligible"] is False
```

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_stock_report.py -q`

Expected: FAIL because `quant_interpretation` is absent.

- [ ] **Step 2: Compose decisions without inferring proof**

Add a default-empty `quant_interpretation` field to `StockReport`. Build exact observation results from the already loaded price histories and explicit report cutoff. Until structured source proof is supplied, pass `provenance_state="unverified"`, `rights_state="unverified"`, and `field_scope_state="unverified"`; do not inspect provider class names or source prose.

Persist only decision dictionaries in the in-memory report object. Do not write a JSON report or regenerate samples in tests.

- [ ] **Step 3: Write failing presentation tests**

```python
def test_quant_cards_label_historical_values_and_hide_technical_detail():
    cards = stock_report_quant_interpretation_cards(_historical_payload())
    rendered = str(cards)
    assert "Historical review only" in rendered
    assert "Current market" not in rendered
    assert "provenance_unverified" not in rendered
```

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_dashboard_helpers.py tests/test_dashboard_render_smoke.py -q`

Expected: FAIL because the cards and Advanced detail do not exist.

- [ ] **Step 4: Add one concise answer plus Advanced evidence**

Show one primary limitation only when an otherwise visible quant result is historical/review-only or withheld. Put family, scope, calculation state, observation date/state, provenance, rights, field scope, and reason codes in the existing Advanced quantitative evidence section. Escape every value and preserve empty states.

- [ ] **Step 5: Run focused render tests and commit**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_stock_report.py tests/test_dashboard_helpers.py tests/test_dashboard_render_smoke.py tests/test_quant_interpretation_eligibility.py -q
git diff --check
git add -- src/stock_report.py src/dashboard.py tests/test_stock_report.py tests/test_dashboard_helpers.py tests/test_dashboard_render_smoke.py
make staged-hygiene-check
git commit -m "Expose quant interpretation boundaries"
```

Expected: focused tests pass; no current-market claim appears from stale or unverified evidence.

### Task 4: Release Evidence and Exact-Head Closeout

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/METHODOLOGY.md`
- Modify: `docs/analysis_capability_audit.md`
- Modify: `docs/NEXT_STAGE_ROADMAP.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: `docs/superpowers/specs/2026-07-28-quant-interpretation-eligibility-design.md`

**Interfaces:**
- Records the exact implementation commit, verification commands, limitations, and remaining external proof gates.

- [ ] **Step 1: Update documentation after implementation evidence exists**

Record that the shared overlay is implemented, not that external provenance or source rights are complete. State that current local results remain historical/review-only or withheld wherever structured proof is absent.

- [ ] **Step 2: Run focused and full verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_quant_interpretation_eligibility.py tests/test_valuation.py tests/test_indicators.py tests/test_review_metrics.py tests/test_stock_report.py tests/test_dashboard_helpers.py tests/test_dashboard_render_smoke.py -q
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make public-wording-check
make public-check
make commercial-beta-release-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
```

Expected: all automated gates pass; pilot may remain truthfully blocked on external or uncommitted-package gates.

- [ ] **Step 3: Stage exact files, commit, push, update PR, and require exact-head CI**

```bash
git add -- ROADMAP.md docs/METHODOLOGY.md docs/analysis_capability_audit.md docs/NEXT_STAGE_ROADMAP.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md docs/superpowers/specs/2026-07-28-quant-interpretation-eligibility-design.md
make staged-hygiene-check
git diff --cached --check
git commit -m "Document quant interpretation eligibility"
git push origin codex/personal-research-mode-mvp
gh pr checks 113 --watch
```

Expected: PR #113 stays open and draft, exact-head CI succeeds, and all generated working-data churn remains unstaged.
