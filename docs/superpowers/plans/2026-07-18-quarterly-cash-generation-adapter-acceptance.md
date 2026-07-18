# Quarterly Cash-Generation Adapter Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a pure one-company acceptance harness that fails closed on source rights, identity, cutoff, revision, Q4, component, and compatibility defects without reading or writing adapter files or activating production readiness.

**Architecture:** A focused adapter-governance module composes the immutable commercial source-rights registry with the existing quarterly cash-generation derivation. It returns one immutable acceptance result with deterministic blockers and an explicit non-activation boundary. Documentation and contract tests keep `accepted_for_review` distinct from real source review, production activation, and market validation.

**Tech Stack:** Python 3.12 dataclasses and immutable mappings, existing `src.commercial_source_rights` and `src.quarterly_cash_generation` contracts, pytest, Markdown contract tests, Make release gates.

## Global Constraints

- Accept only in-memory `QuarterlyBusinessObservation` and `QuarterlyActual` objects; add no file loader or writer.
- Add no CLI, Make target, network request, credential read, data directory, CSV, JSON, report, sample report, screenshot, timing output, template, or canonical row.
- The only successful status is `accepted_for_review`; it never means reviewed, production-ready, or commercially activated.
- `production_activation` is always `False`; `readiness_promotions` is always empty.
- Commercial rights and all three required source fields must be explicitly approved in the supplied registry.
- Q4 remains explicit filed-quarter only; annual-minus-nine-month derivation is forbidden.
- Capital expenditures preserve the reported sign; free cash flow remains cash from operations plus reported capital expenditures.
- Synthetic observations and synthetic rights records remain test-only.
- Stage exact intentional files only; never use `git add -A`; keep all generated churn excluded.
- Keep PR #113 open and draft; do not merge or deploy.

---

### Task 1: Pure One-Company Acceptance Contract

**Files:**
- Create: `src/quarterly_cash_generation_adapter.py`
- Create: `tests/test_quarterly_cash_generation_adapter.py`

**Interfaces:**
- Consumes: `Mapping[str, SourceRights]`, `Iterable[QuarterlyBusinessObservation]`, `Iterable[QuarterlyActual]`, and optional `as_of: str | None`.
- Produces: `QuarterlyAdapterAcceptance` and `assess_quarterly_cash_generation_adapter(ticker, source_id, observations, revenue_actuals, *, rights_registry, as_of=None)`.

- [ ] **Step 1: Add shared synthetic constructors and the first failing success-path test**

Create `tests/test_quarterly_cash_generation_adapter.py` with constructors for one `QuarterlyBusinessObservation`, one compatible `QuarterlyActual`, and an immutable registry built through `build_source_rights_registry`. The success test must assert the complete public result:

```python
def test_complete_one_company_batch_is_accepted_for_review_without_activation():
    observations = [
        _observation(metric="operating_income", value=50.0),
        _observation(metric="cash_from_operations", value=60.0),
        _observation(metric="capital_expenditures", value=-20.0),
    ]

    result = assess_quarterly_cash_generation_adapter(
        "SYN1",
        "synthetic_adapter",
        observations,
        [_actual(revenue=200.0)],
        rights_registry=_rights_registry(),
    )

    assert result.status == "accepted_for_review"
    assert result.blockers == ()
    assert result.accepted_observation_count == 3
    assert result.reviewed_metrics == (
        "capital_expenditures",
        "cash_from_operations",
        "operating_income",
    )
    assert result.derived_point_count == 3
    assert result.rights_status == "approved"
    assert result.production_activation is False
    assert result.readiness_promotions == ()
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
python3 -m pytest tests/test_quarterly_cash_generation_adapter.py::test_complete_one_company_batch_is_accepted_for_review_without_activation -q
```

Expected: collection fails because `src.quarterly_cash_generation_adapter` does not exist.

- [ ] **Step 3: Implement the immutable result and minimal success path**

Create `src/quarterly_cash_generation_adapter.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from src.commercial_source_rights import SourceRights, commercial_eligibility
from src.earnings_nowcast_contract import QuarterlyActual
from src.quarterly_cash_generation import (
    QuarterlyBusinessObservation,
    derive_quarterly_business_metrics,
)

REQUIRED_SOURCE_FIELDS = frozenset(
    {"operating_income", "cash_from_operations", "capital_expenditures"}
)


@dataclass(frozen=True)
class QuarterlyAdapterAcceptance:
    ticker: str
    source_id: str
    status: str
    blockers: tuple[str, ...]
    accepted_observation_count: int
    reviewed_metrics: tuple[str, ...]
    derived_point_count: int
    explicit_q4_periods: tuple[str, ...]
    rights_status: str
    production_activation: bool = False
    readiness_promotions: tuple[str, ...] = ()


def assess_quarterly_cash_generation_adapter(
    ticker: str,
    source_id: str,
    observations: Iterable[QuarterlyBusinessObservation],
    revenue_actuals: Iterable[QuarterlyActual],
    *,
    rights_registry: Mapping[str, SourceRights],
    as_of: str | None = None,
) -> QuarterlyAdapterAcceptance:
    symbol = str(ticker or "").strip().upper()
    normalized_source = str(source_id or "").strip()
    supplied = tuple(observations)
    revenues = tuple(revenue_actuals)
    decision = commercial_eligibility(rights_registry, normalized_source)
    derivation = derive_quarterly_business_metrics(symbol, supplied, revenues, as_of=as_of)
    reviewed_metrics = tuple(sorted({row.metric for row in supplied}))
    q4_periods = tuple(sorted({row.fiscal_period for row in supplied if row.fiscal_period.endswith("-Q4")}))
    return QuarterlyAdapterAcceptance(
        ticker=symbol,
        source_id=normalized_source,
        status="accepted_for_review",
        blockers=(),
        accepted_observation_count=len(supplied),
        reviewed_metrics=reviewed_metrics,
        derived_point_count=len(derivation.points),
        explicit_q4_periods=q4_periods,
        rights_status=decision.status,
    )
```

- [ ] **Step 4: Run the success-path test and verify GREEN**

Run the Step 2 command. Expected: 1 passed.

- [ ] **Step 5: Add failing identity, rights, and required-field tests**

Add separate tests asserting these exact blockers:

```python
@pytest.mark.parametrize(
    ("ticker", "source_id", "observations", "blocker"),
    [
        ("", "synthetic_adapter", (), "ticker_required"),
        ("SYN1", "", (), "source_id_required"),
        ("SYN1", "synthetic_adapter", (), "observations_required"),
    ],
)
def test_required_identity_and_observations_fail_closed(ticker, source_id, observations, blocker):
    result = assess_quarterly_cash_generation_adapter(
        ticker,
        source_id,
        observations,
        [_actual()],
        rights_registry=_rights_registry(),
    )
    assert result.status == "blocked"
    assert blocker in result.blockers
    assert result.accepted_observation_count == 0


def test_mixed_ticker_and_source_mismatch_are_reported_together():
    rows = [
        _observation(),
        _observation(ticker="OTHER"),
        _observation(metric="operating_income", source="other_source"),
    ]
    result = _assess(rows)
    assert "mixed_ticker:OTHER" in result.blockers
    assert "source_mismatch:other_source" in result.blockers


def test_unknown_or_unverified_rights_block_acceptance():
    unknown = _assess(_complete_rows(), source_id="unknown")
    assert "source_rights:unknown_source" in unknown.blockers
    unverified = _assess(_complete_rows(), rights_registry=_rights_registry(commercial_use="unverified"))
    assert "source_rights:commercial_rights_unverified" in unverified.blockers


def test_approved_source_must_explicitly_support_every_component():
    result = _assess(
        _complete_rows(),
        rights_registry=_rights_registry(supported_fields=["operating_income"]),
    )
    assert result.blockers == (
        "source_fields_missing:capital_expenditures,cash_from_operations",
    )
```

- [ ] **Step 6: Run the new tests and verify RED**

Run:

```bash
python3 -m pytest tests/test_quarterly_cash_generation_adapter.py -q
```

Expected: failures because the minimal implementation always accepts.

- [ ] **Step 7: Implement deterministic identity and source-rights blockers**

Add one blocker list, normalize identity before derivation, evaluate `commercial_eligibility`, compare `SourceRights.supported_fields` with `REQUIRED_SOURCE_FIELDS`, and collect sorted mixed ticker/source values. Return `blocked` whenever blockers are non-empty; blocked results set `accepted_observation_count=0`.

Use exact blocker formats:

```python
if not symbol:
    blockers.append("ticker_required")
if not normalized_source:
    blockers.append("source_id_required")
if not supplied:
    blockers.append("observations_required")
for other in sorted({row.ticker for row in supplied if row.ticker != symbol}):
    blockers.append(f"mixed_ticker:{other}")
for other in sorted({row.source for row in supplied if row.source != normalized_source}):
    blockers.append(f"source_mismatch:{other}")
if not decision.allowed:
    blockers.append(f"source_rights:{decision.status}")
record = rights_registry.get(normalized_source)
if record is not None:
    missing_fields = sorted(REQUIRED_SOURCE_FIELDS - set(record.supported_fields))
    if missing_fields:
        blockers.append(f"source_fields_missing:{','.join(missing_fields)}")
```

- [ ] **Step 8: Run the test module and verify GREEN**

Run the Step 6 command. Expected: all current tests pass.

- [ ] **Step 9: Add failing cutoff, revision, component, compatibility, and Q4 tests**

Add tests that prove:

- a post-cutoff observation returns its existing `YYYY-QN:metric:post_cutoff` blocker;
- one explicit revision leaf is accepted and increments only the derived revision behavior;
- conflicting capex leaves return `YYYY-QN:capital_expenditures:ambiguous_revision`;
- missing a required component returns `YYYY-QN:missing_component:<metric>`;
- missing or incompatible Revenue returns the existing operating-margin and FCF-margin blockers and prevents complete-period acceptance;
- incompatible cash-flow component definitions preserve the existing `free_cash_flow:incompatible_components` blocker;
- a complete Q4 batch with `explicit_filed_quarter` records `explicit_q4_periods == ("2025-Q4",)`;
- constructing a Q4 observation with `q4_evidence_state="not_q4"` still raises `ValueError` before the harness runs.

The incomplete-period assertion must be:

```python
assert "2025-Q1:missing_component:capital_expenditures" in result.blockers
assert "complete_derived_period_required" in result.blockers
```

- [ ] **Step 10: Run the test module and verify RED**

Run the Step 6 command. Expected: new blocker and complete-period assertions fail.

- [ ] **Step 11: Compose existing derivation blockers and enforce one complete derived period**

For observations matching the requested ticker and source, group supplied metric names by fiscal period and append missing-component blockers in fiscal-period and metric order. Derive only requested-ticker observations, append `derivation.blockers`, and calculate periods containing all three derived metrics:

```python
points_by_period: dict[str, set[str]] = {}
for point in derivation.points:
    points_by_period.setdefault(point.fiscal_period, set()).add(point.metric)
complete_periods = tuple(
    sorted(
        period
        for period, metrics in points_by_period.items()
        if {"operating_margin", "free_cash_flow", "fcf_margin"}.issubset(metrics)
    )
)
if not complete_periods:
    blockers.append("complete_derived_period_required")
```

Deduplicate blockers in insertion order with `tuple(dict.fromkeys(blockers))`. Set `derived_point_count` from the derivation even when blocked, but keep accepted observation count at zero.

- [ ] **Step 12: Run the test module and verify GREEN**

Run the Step 6 command. Expected: all acceptance tests pass.

- [ ] **Step 13: Add and satisfy no-persistence surface tests**

Add:

```python
def test_adapter_acceptance_module_has_no_file_network_or_cli_surface():
    source = Path("src/quarterly_cash_generation_adapter.py").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    for forbidden in (
        "argparse", "requests", "urllib", "Path(", ".open(", "read_text(",
        "write_text(", "csv", "json", "output_dir", "__main__",
    ):
        assert forbidden not in source
    assert "quarterly-cash-generation-adapter" not in makefile
```

Run:

```bash
python3 -m pytest tests/test_quarterly_cash_generation_adapter.py tests/test_quarterly_cash_generation.py -q
```

Expected: all tests pass.

- [ ] **Step 14: Commit the contract slice**

```bash
git add -- src/quarterly_cash_generation_adapter.py tests/test_quarterly_cash_generation_adapter.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Add quarterly adapter acceptance harness"
git push origin codex/personal-research-mode-mvp
```

---

### Task 2: Methodology, Roadmap, And Continuation Contract

**Files:**
- Modify: `docs/METHODOLOGY.md`
- Modify: `docs/PROVENANCE_CONTRACT.md`
- Modify: `docs/PERSONAL_RESEARCH_MODE.md`
- Modify: `ROADMAP.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: `tests/test_public_v1_release_docs.py`

**Interfaces:**
- Consumes: the Task 1 `accepted_for_review`, blocker, rights, and non-activation contract.
- Produces: durable maturity and continuation claims plus documentation regression coverage.

- [ ] **Step 1: Write the failing documentation contract test**

Add to `tests/test_public_v1_release_docs.py`:

```python
def test_quarterly_adapter_acceptance_docs_keep_review_and_activation_separate():
    methodology = _read("docs/METHODOLOGY.md")
    provenance = _read("docs/PROVENANCE_CONTRACT.md")
    personal_mode = _read("docs/PERSONAL_RESEARCH_MODE.md")
    roadmap = _read("ROADMAP.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    assert "accepted_for_review is not production activation" in methodology
    assert "production_activation=false" in provenance
    assert "readiness_promotions=()" in provenance
    assert "no adapter file is loaded or written" in personal_mode
    assert "one-company adapter acceptance harness" in roadmap
    assert "does not prove a real-company source payload" in roadmap
    assert "Quarterly adapter acceptance" in prompt
    assert "accepted_for_review" in prompt
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
python3 -m pytest tests/test_public_v1_release_docs.py::test_quarterly_adapter_acceptance_docs_keep_review_and_activation_separate -q
```

Expected: failure because the new acceptance distinctions are absent.

- [ ] **Step 3: Update methodology and provenance**

Document the one-company scope, explicit rights-field checks, complete compatible period requirement, deterministic blockers, and the exact statement `accepted_for_review is not production activation`. In provenance, record `production_activation=false`, `readiness_promotions=()`, no file/network/credential surface, and unchanged external review requirement.

- [ ] **Step 4: Update Personal Research guidance and ROADMAP**

State that no adapter file is loaded or written and Company Workbench remains withheld because production supplies no accepted observations. Add the implemented one-company adapter acceptance harness to the current foundation and state that it does not prove a real-company source payload, reviewed rights expansion, or market validation.

- [ ] **Step 5: Update the persistent continuation goal**

Add the local acceptance harness to implemented capabilities. Add a `Quarterly adapter acceptance` boundary that requires the checked source-rights record to explicitly support all three component fields and still classifies real activation as `external_source_and_review_required`. Preserve automatic continuation across safe local work and the strict no-generated-artifact rule.

- [ ] **Step 6: Run focused documentation and contract tests**

```bash
python3 -m pytest tests/test_public_v1_release_docs.py tests/test_quarterly_cash_generation_adapter.py tests/test_quarterly_cash_generation.py -q
```

Expected: all pass.

- [ ] **Step 7: Commit the documentation slice**

```bash
git add -- docs/METHODOLOGY.md docs/PROVENANCE_CONTRACT.md docs/PERSONAL_RESEARCH_MODE.md ROADMAP.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md tests/test_public_v1_release_docs.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Document quarterly adapter acceptance boundary"
git push origin codex/personal-research-mode-mvp
```

---

### Task 3: Full Release Verification And Draft PR Update

**Files:**
- No new product files.
- Update remote draft PR #113 only after all local evidence passes.

**Interfaces:**
- Consumes: committed Tasks 1-2.
- Produces: clean aligned branch, verified release evidence, updated draft PR, and next-goal prompt grounded in current truth.

- [ ] **Step 1: Run the full verification bundle**

```bash
python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make public-wording-check
make public-check
make commercial-beta-check
make commercial-beta-release-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
```

Expected: tests and static/runtime gates pass; pilot readiness may retain named manual external gates; no generated artifact candidate exists.

- [ ] **Step 2: Verify repository and PR truth**

```bash
git status --short --branch
git rev-list --left-right --count origin/codex/personal-research-mode-mvp...HEAD
gh pr view 113 --json state,isDraft,mergeStateStatus,headRefName,url
```

Expected: clean tree, `0 0` divergence, PR open and draft on the named branch.

- [ ] **Step 3: Update draft PR #113**

Add a verified comment covering:

- pure one-company acceptance behavior;
- deterministic rights, identity, cutoff, revision, component, compatibility, and Q4 blockers;
- `accepted_for_review` versus production activation;
- no file, CLI, network, credential, writer, or generated artifact;
- exact test and release-gate results;
- the current SEC rights-record field limitation;
- `external_source_and_review_required` as the real activation gate.

Keep the PR draft and do not merge or deploy.

- [ ] **Step 4: Produce the next-goal prompt**

Deliver a copy-ready prompt that starts from current repository truth, verifies the latest commit and draft PR, preserves no-file and independent-readiness boundaries, classifies the real adapter/source dependency once, and moves to the next safe local maturity gap without repeating broad source or generated-artifact loops.

