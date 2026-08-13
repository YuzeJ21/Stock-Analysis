# Company Workbench Cash-Generation Portability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add AMD Q1 FY2026 as the second immutable, explicit, preview-only Company Workbench quarterly cash-generation filing while preserving the existing NVIDIA route and every no-activation boundary.

**Architecture:** Replace the NVIDIA-only loader constants with a frozen filing specification and a read-only two-entry ticker registry. Keep the loader signature, SEC fetcher, extractor, source-rights review, acceptance contract, preview composition, query gate, and presentation contract unchanged; only the registry may select exact reviewed filing identity. Prove AMD through fixtures, explicit route rendering, one bounded live no-write check, documentation contracts, full local gates, and exact-head GitHub CI.

**Tech Stack:** Python 3.12, frozen dataclasses, `types.MappingProxyType`, pytest, Streamlit AppTest render smoke, existing SEC Companyfacts/submissions/primary-filing clients, Make release gates, GitHub Actions.

## Global Constraints

- Research-only; no investment advice, recommendation, broker integration, order routing, auto-trading, direct buy/sell instruction, or post-earnings price prediction.
- The registry contains exactly `NVDA` and `AMD`; do not add a broad company loop or accept caller-supplied CIK, accession, filing, dates, fiscal period, or cutoff.
- Both previews retain `production_activation=false`, `readiness_promotions=()`, `persistence=false`, complete withholding, and Advanced-only technical lineage.
- Keep Revenue, EPS, operating margin, free cash flow, FCF margin, valuation, catalysts, outcomes, consensus, backtesting, and calibration readiness independent.
- Do not run `make readiness`, refresh broad coverage, persist a source row, or generate/stage CSV, JSON, report, sample-report, screenshot, timing, readiness, canonical-data, or manual-review churn.
- Q4 requires explicit SEC-filed three-month Q4 table evidence and is never derived; this slice uses Q1 only.
- Stage exact intentional paths only; never use `git add -A`.
- Push only `codex/personal-research-mode-mvp`; keep PR #113 open and draft; do not merge or deploy.

---

### Task 1: Immutable two-company filing registry and bounded loader

**Files:**
- Modify: `tests/test_company_workbench_cash_generation_preview_loader.py`
- Modify: `src/company_workbench_cash_generation_preview_loader.py`

**Interfaces:**
- Consumes: `fetch_sec_quarterly_pilot_payloads(...)`, `extract_sec_quarterly_cash_generation(...)`, `preview_sec_quarterly_cash_generation(...)`, and `compose_company_workbench_cash_generation_preview(...)`.
- Produces: frozen `CashGenerationPreviewFiling`, read-only `CASH_GENERATION_PREVIEW_FILINGS`, and the unchanged `load_company_workbench_cash_generation_preview(ticker, *, user_agent=None, fetcher=None, retrieved_at=None)` signature.

- [ ] **Step 1: Add failing registry and AMD loader tests**

Replace the NVIDIA constant imports with the registry import and add exact AMD fixtures and assertions:

```python
from src.company_workbench_cash_generation_preview_loader import (
    CASH_GENERATION_PREVIEW_FILINGS,
    load_company_workbench_cash_generation_preview,
)

AMD_START = "2025-12-28"
AMD_END = "2026-03-28"
AMD_ACCESSION = "0000002488-26-000076"


def _amd_fact(value: float) -> dict[str, object]:
    return {
        "start": AMD_START,
        "end": AMD_END,
        "val": value,
        "accn": AMD_ACCESSION,
        "fy": 2026,
        "fp": "Q1",
        "form": "10-Q",
        "filed": "2026-05-06",
    }


def _amd_companyfacts() -> dict[str, object]:
    return {
        "cik": 2488,
        "entityName": "ADVANCED MICRO DEVICES INC",
        "facts": {"us-gaap": {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "units": {"USD": [_amd_fact(10_253_000_000)]}
            },
            "OperatingIncomeLoss": {"units": {"USD": [_amd_fact(1_476_000_000)]}},
            "NetCashProvidedByUsedInOperatingActivities": {
                "units": {"USD": [_amd_fact(2_955_000_000)]}
            },
            "PaymentsToAcquirePropertyPlantAndEquipment": {
                "units": {"USD": [_amd_fact(389_000_000)]}
            },
        }},
    }


def _amd_submissions() -> dict[str, object]:
    return {"cik": "0000002488", "filings": {"recent": {
        "accessionNumber": [AMD_ACCESSION],
        "filingDate": ["2026-05-06"],
        "acceptanceDateTime": ["2026-05-05T18:06:27.000-04:00"],
        "form": ["10-Q"],
        "primaryDocument": ["amd-20260328.htm"],
    }}}


def _amd_filing() -> str:
    return f"""
    <html><body><xbrli:context id="amd-q1"><xbrli:period>
      <xbrli:startDate>{AMD_START}</xbrli:startDate>
      <xbrli:endDate>{AMD_END}</xbrli:endDate>
    </xbrli:period></xbrli:context><table>
      <tr><td>Net revenue</td><td><ix:nonFraction id="amd-revenue" name="us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax" contextRef="amd-q1" scale="6">10,253</ix:nonFraction></td></tr>
      <tr><td>Operating income</td><td><ix:nonFraction id="amd-operating" name="us-gaap:OperatingIncomeLoss" contextRef="amd-q1" scale="6">1,476</ix:nonFraction></td></tr>
      <tr><td>Net cash provided by operating activities</td><td><ix:nonFraction id="amd-cfo" name="us-gaap:NetCashProvidedByUsedInOperatingActivities" contextRef="amd-q1" scale="6">2,955</ix:nonFraction></td></tr>
      <tr><td>Purchases of property and equipment</td><td>(</td><td><ix:nonFraction id="amd-capex" name="us-gaap:PaymentsToAcquirePropertyPlantAndEquipment" contextRef="amd-q1" scale="6">389</ix:nonFraction></td><td>)</td></tr>
    </table></body></html>
    """


def _amd_fetcher(calls: list[tuple[str, str]]):
    def fetch(url: str, user_agent: str) -> bytes:
        calls.append((url, user_agent))
        if "companyfacts" in url:
            return json.dumps(_amd_companyfacts()).encode("utf-8")
        if "submissions" in url:
            return json.dumps(_amd_submissions()).encode("utf-8")
        return _amd_filing().encode("utf-8")
    return fetch


def test_registry_contains_only_two_exact_reviewed_filings():
    assert tuple(CASH_GENERATION_PREVIEW_FILINGS) == ("NVDA", "AMD")
    nvda = CASH_GENERATION_PREVIEW_FILINGS["NVDA"]
    amd = CASH_GENERATION_PREVIEW_FILINGS["AMD"]
    assert (nvda.cik, nvda.accession, nvda.primary_document) == (
        "0001045810", "0001045810-26-000052", "nvda-20260426.htm"
    )
    assert (amd.cik, amd.fiscal_period, amd.period_start, amd.period_end) == (
        "0000002488", "2026-Q1", "2025-12-28", "2026-03-28"
    )
    assert (amd.accession, amd.primary_document, amd.as_of) == (
        "0000002488-26-000076", "amd-20260328.htm", "2026-07-20T23:59:59-04:00"
    )


def test_amd_loader_uses_exact_reviewed_identity_and_composes_in_memory():
    calls: list[tuple[str, str]] = []
    result = load_company_workbench_cash_generation_preview(
        "AMD",
        user_agent="Researcher research@example.com",
        fetcher=_amd_fetcher(calls),
        retrieved_at="2026-07-20T23:00:00+00:00",
    )
    assert [url for url, _agent in calls] == [
        "https://data.sec.gov/api/xbrl/companyfacts/CIK0000002488.json",
        "https://data.sec.gov/submissions/CIK0000002488.json",
        "https://www.sec.gov/Archives/edgar/data/2488/000000248826000076/amd-20260328.htm",
    ]
    assert result.status == "accepted_for_review"
    assert result.fiscal_period == "2026-Q1"
    assert result.free_cash_flow.value == 2_566_000_000
    assert result.operating_margin.status == "preview_available"
    assert result.fcf_margin.status == "preview_available"
    assert result.production_activation is False
    assert result.readiness_promotions == ()
    assert result.persistence is False
```

Strengthen the unsupported-ticker test with:

```python
assert result.fiscal_period == ""
assert result.accession == ""
assert result.source_url == ""
assert result.cutoff == ""
```

Add the unsigned AMD filing test:

```python
def test_unsigned_amd_capex_withholds_complete_preview():
    calls: list[tuple[str, str]] = []
    base_fetcher = _amd_fetcher(calls)

    def unsigned_fetch(url: str, user_agent: str) -> bytes:
        payload = base_fetcher(url, user_agent)
        if url.endswith("amd-20260328.htm"):
            return payload.replace(b"<td>(</td>", b"<td></td>").replace(
                b"<td>)</td>", b"<td></td>"
            )
        return payload

    result = load_company_workbench_cash_generation_preview(
        "AMD",
        user_agent="Researcher research@example.com",
        fetcher=unsigned_fetch,
        retrieved_at="2026-07-20T23:00:00+00:00",
    )
    assert result.status == "withheld"
    assert result.operating_margin.value is None
    assert result.free_cash_flow.value is None
    assert result.fcf_margin.value is None
    assert result.components == ()
```

- [ ] **Step 2: Run the focused loader tests and verify the expected failure**

Run:

```bash
python3 -m pytest tests/test_company_workbench_cash_generation_preview_loader.py -q
```

Expected: FAIL during import because `CASH_GENERATION_PREVIEW_FILINGS` does not exist.

- [ ] **Step 3: Implement the immutable registry and registry-driven loader**

Replace the NVIDIA-only constants and field substitutions with:

```python
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class CashGenerationPreviewFiling:
    ticker: str
    cik: str
    fiscal_period: str
    period_start: str
    period_end: str
    accession: str
    primary_document: str
    as_of: str


CASH_GENERATION_PREVIEW_FILINGS: Mapping[str, CashGenerationPreviewFiling] = (
    MappingProxyType({
        "NVDA": CashGenerationPreviewFiling(
            ticker="NVDA",
            cik="0001045810",
            fiscal_period="2027-Q1",
            period_start="2026-01-26",
            period_end="2026-04-26",
            accession="0001045810-26-000052",
            primary_document="nvda-20260426.htm",
            as_of="2026-07-20T23:59:59-04:00",
        ),
        "AMD": CashGenerationPreviewFiling(
            ticker="AMD",
            cik="0000002488",
            fiscal_period="2026-Q1",
            period_start="2025-12-28",
            period_end="2026-03-28",
            accession="0000002488-26-000076",
            primary_document="amd-20260328.htm",
            as_of="2026-07-20T23:59:59-04:00",
        ),
    })
)
```

At the beginning of the loader, resolve `filing = CASH_GENERATION_PREVIEW_FILINGS.get(symbol)`. When absent, call `blocked_company_workbench_cash_generation_preview` with only `symbol` and the unsupported blocker. When present, replace every previous `PREVIEW_*` argument with the matching `filing` property. In the exception path, retain only that selected filing's `fiscal_period`, `as_of`, and `accession`.

- [ ] **Step 4: Run focused cash-generation tests**

Run:

```bash
python3 -m pytest tests/test_company_workbench_cash_generation_preview_loader.py tests/test_company_workbench_cash_generation_preview.py tests/test_sec_quarterly_cash_generation_pilot.py tests/test_quarterly_cash_generation_adapter.py tests/test_quarterly_cash_generation.py -q
```

Expected: PASS with no live network access.

- [ ] **Step 5: Verify the loader has no write or broad-source surface**

Run:

```bash
make diff-hygiene-summary
git diff --check
```

Expected: only the loader and its focused test are changed; no generated artifact is reported.

- [ ] **Step 6: Commit the loader slice**

```bash
git add src/company_workbench_cash_generation_preview_loader.py tests/test_company_workbench_cash_generation_preview_loader.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Add bounded AMD cash preview filing"
```

### Task 2: Explicit AMD Workbench route proof

**Files:**
- Modify: `tests/test_dashboard_render_smoke.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`

**Interfaces:**
- Consumes: the unchanged dashboard query gate and loader import, plus `CompanyWorkbenchCashGenerationPreview` presentation contract.
- Produces: runtime-contract evidence that explicit AMD preview works and normal AMD navigation never loads preview evidence.

- [ ] **Step 1: Add an explicit AMD render-smoke test**

Add an accepted AMD preview fixture using:

```python
preview = CompanyWorkbenchCashGenerationPreview(
    ticker="AMD",
    fiscal_period="2026-Q1",
    status="accepted_for_review",
    message="Accepted SEC evidence supports a cash-generation review preview.",
    operating_margin=CashGenerationPreviewMetric(
        "operating_margin", "preview_available", 1_476_000_000 / 10_253_000_000,
        "2026-Q1", (), ""
    ),
    free_cash_flow=CashGenerationPreviewMetric(
        "free_cash_flow", "preview_available", 2_566_000_000, "2026-Q1", (), ""
    ),
    fcf_margin=CashGenerationPreviewMetric(
        "fcf_margin", "preview_available", 2_566_000_000 / 10_253_000_000,
        "2026-Q1", (), ""
    ),
    blockers=(),
    withheld_metrics=(),
    accession="0000002488-26-000076",
    source_url="https://www.sec.gov/Archives/edgar/data/2488/000000248826000076/amd-20260328.htm",
    accepted_at="2026-05-05T22:06:27+00:00",
    cutoff="2026-07-21T03:59:59+00:00",
    capex_sign_evidence="explicit_filed_table_outflow",
    components=(),
)
```

Use route parameters `ticker=AMD`, `open=1`, and `cash_preview=1`. Require `Cash-generation review preview`, `not production evidence`, `14.4%`, `2,566,000,000`, and `25.0%`. Patch only the external loader boundary and assert no exception, missing marker, forbidden marker, or expanded Advanced section.

- [ ] **Step 2: Add a normal AMD route non-invocation test**

Add the normal-route guard:

```python
def test_normal_amd_company_workbench_route_never_loads_cash_preview():
    from src.dashboard_render_smoke import DashboardRenderRoute, render_public_routes

    route = DashboardRenderRoute(
        name="Normal AMD Company Workbench",
        query_params=(
            ("mode", "research"),
            ("page", "company-workbench"),
            ("ticker", "AMD"),
            ("open", "1"),
        ),
        required_markers=("Company Workbench", "Business Trend", "Research-only"),
    )
    with patch(
        "src.company_workbench_cash_generation_preview_loader."
        "load_company_workbench_cash_generation_preview",
        side_effect=AssertionError("normal AMD Workbench must not load cash preview"),
    ):
        result = render_public_routes(Path("."), routes=(route,))[0]
    assert result.exceptions == ()
    assert result.missing_markers == ()
```

- [ ] **Step 3: Strengthen the static route contract**

In `test_company_workbench_loads_cash_preview_only_for_explicit_flag`, keep:

```python
assert 'company_workbench_cash_preview_requested(st.query_params.get("cash_preview"))' in source
assert "load_company_workbench_cash_generation_preview(ticker)" in source
```

In the default-navigation test, add:

```python
assert "ticker=NVDA&open=1&cash_preview=1" not in source
assert "ticker=AMD&open=1&cash_preview=1" not in source
```

- [ ] **Step 4: Run the focused dashboard contracts**

Run:

```bash
python3 -m pytest tests/test_dashboard_render_smoke.py tests/test_research_mode_dashboard_contract.py tests/test_research_workspace.py -q
make research-dashboard-render-smoke
```

Expected: PASS; all standard and Advanced Evidence routes remain unchanged, and the AMD explicit route renders only through the patched loader boundary.

- [ ] **Step 5: Commit the route-proof slice**

```bash
git add tests/test_dashboard_render_smoke.py tests/test_research_mode_dashboard_contract.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Prove explicit AMD cash preview route"
```

### Task 3: Documentation truth and continuation contract

**Files:**
- Modify: `tests/test_public_v1_release_docs.py`
- Modify: `ROADMAP.md`
- Modify: `docs/PERSONAL_RESEARCH_MODE.md`
- Modify: `docs/METHODOLOGY.md`
- Modify: `docs/PROVENANCE_CONTRACT.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`

**Interfaces:**
- Consumes: the verified two-entry registry, AMD live evidence, focused tests, and unchanged product boundaries.
- Produces: durable product-stage and next-lane truth for reviewers and later continuations.

- [ ] **Step 1: Add a failing documentation contract**

Add:

```python
def test_two_company_cash_preview_docs_preserve_bounded_portability_boundary():
    methodology = _read("docs/METHODOLOGY.md")
    provenance = _read("docs/PROVENANCE_CONTRACT.md")
    personal = _read("docs/PERSONAL_RESEARCH_MODE.md")
    roadmap = _read("ROADMAP.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    for text in (methodology, provenance, personal, roadmap, prompt):
        assert "AMD Q1 FY2026" in text
        assert "0000002488-26-000076" in text
        assert "bounded two-company portability" in text.lower()
    assert "cash_preview=1" in personal
    assert "production_activation=false" in provenance
    assert "readiness_promotions=()" in provenance
    assert "does not prove broad company coverage" in roadmap.lower()
    assert "do not add a third company" in prompt.lower()
```

- [ ] **Step 2: Run the documentation test and verify failure**

Run:

```bash
python3 -m pytest tests/test_public_v1_release_docs.py -q
```

Expected: FAIL because the AMD portability evidence is not yet documented.

- [ ] **Step 3: Update the six truth documents**

Add this product-stage statement to `ROADMAP.md`:

```markdown
**Implemented locally and live-source verified:** AMD Q1 FY2026 accession `0000002488-26-000076` now joins NVIDIA in one immutable, shared loader and explicit `cash_preview=1` Company Workbench path. The AMD filing supplied Revenue USD 10.253B, operating income USD 1.476B, cash from operations USD 2.955B, capital expenditures USD -0.389B, and `explicit_filed_table_outflow` evidence before free cash flow USD 2.566B was displayed. This is bounded two-company portability; it does not prove broad company coverage, arbitrary-filing support, historical depth, Q4 support, production activation, current readiness, hosting, reviewer validation, calibration, demand, or product-market fit.
```

Add this route statement to `docs/PERSONAL_RESEARCH_MODE.md`:

```markdown
AMD Q1 FY2026 accession `0000002488-26-000076` is the second exact filing available through the explicit `cash_preview=1` route. NVIDIA and AMD now provide bounded two-company portability through the same immutable loader, complete-withholding contract, preview-only cards, and Advanced lineage. Normal Company Workbench routes remain canonical and never load the preview.
```

Add this method statement to `docs/METHODOLOGY.md`:

```markdown
The AMD Q1 FY2026 result proves bounded two-company portability for the same exact-filing method: one immutable identity, three official SEC endpoints, compatible quarterly components, timezone-aware acceptance, explicit filed-table capex outflow, exact rights scope, and complete withholding. It does not prove broad company coverage, and no third company is inferred from cohort membership.
```

Add this evidence statement to `docs/PROVENANCE_CONTRACT.md`:

```markdown
AMD Q1 FY2026 accession `0000002488-26-000076` uses the same bounded two-company portability contract as NVIDIA. Both results retain `production_activation=false`, `readiness_promotions=()`, `persistence=false`, exact component references, and no canonical write. Unsupported tickers fail before fetch and expose no configured filing identity.
```

In `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`, add a lineage navigation anchor using the already committed design SHA, which every implementation commit must descend from:

```markdown
- Bounded two-company cash-preview design anchor: commit `11ac530ae` or a later verified descendant.
```

Replace the quarterly portability classification with:

```markdown
- Quarterly cash-generation portability: `bounded_two_company_preview_implemented`; NVIDIA Q1 FY2027 and AMD Q1 FY2026 use one immutable exact-filing loader and explicit preview-only Workbench path. This proves bounded two-company portability only. Do not add a third company, run broad coverage, infer filing identity, persist observations, or promote readiness without a separately justified exact-source design and review.
```

Keep all normal-route, complete-withholding, Advanced-only, no-persistence, stale-readiness, Q4, EPS, consensus, calibration, hosted, reviewer, demand, and market-validation boundaries unchanged.

- [ ] **Step 4: Run documentation, wording, and whitespace checks**

Run:

```bash
python3 -m pytest tests/test_public_v1_release_docs.py -q
make public-wording-check
git diff --check
```

Expected: PASS.

- [ ] **Step 5: Commit documentation truth**

```bash
git add ROADMAP.md docs/PERSONAL_RESEARCH_MODE.md docs/METHODOLOGY.md docs/PROVENANCE_CONTRACT.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md tests/test_public_v1_release_docs.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Document bounded cash preview portability"
```

### Task 4: Live proof, complete verification, push, and PR update

**Files:**
- No new repository files.
- Update draft PR #113 through GitHub after all local evidence passes.

**Interfaces:**
- Consumes: Tasks 1-3 and configured `SEC_USER_AGENT`.
- Produces: current live no-write AMD proof, complete local release evidence, aligned remote branch, updated draft PR, and exact-head hosted CI evidence.

- [ ] **Step 1: Run one bounded live loader proof**

Run:

```bash
python3 -c 'from src.company_workbench_cash_generation_preview_loader import load_company_workbench_cash_generation_preview as load; result = load("AMD"); print(result.status, result.fiscal_period, result.free_cash_flow.value, result.production_activation, result.readiness_promotions, result.persistence); assert result.status == "accepted_for_review"; assert result.free_cash_flow.value == 2566000000; assert result.production_activation is False; assert result.readiness_promotions == (); assert result.persistence is False'
```

Expected: `accepted_for_review 2026-Q1 2566000000.0 False () False`. Immediately run `git status --short` and require no artifact change.

- [ ] **Step 2: Run focused and full verification**

Run:

```bash
python3 -m pytest tests/test_company_workbench_cash_generation_preview_loader.py tests/test_company_workbench_cash_generation_preview.py tests/test_sec_quarterly_cash_generation_pilot.py tests/test_quarterly_cash_generation_adapter.py tests/test_quarterly_cash_generation.py tests/test_dashboard_render_smoke.py tests/test_research_mode_dashboard_contract.py tests/test_research_workspace.py tests/test_public_v1_release_docs.py -q
python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make public-wording-check
make public-check
make commercial-beta-check
make commercial-beta-release-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
make pr-range-hygiene-check BASE_SHA=origin/main HEAD_SHA=HEAD
git diff --check
```

Expected: all code and release gates pass; pilot readiness remains truthfully blocked by stale saved readiness; PR-range hygiene reports zero generated CSV/JSON and manual-review churn.

- [ ] **Step 3: Verify repository package before push**

Run:

```bash
git status --short --branch
git log -8 --oneline --decorate
git rev-list --left-right --count HEAD...origin/codex/personal-research-mode-mvp
```

Expected: clean working tree and a finite intentional ahead count containing only the design, plan, loader, route-proof, and documentation commits.

- [ ] **Step 4: Push only the approved feature branch**

```bash
git push origin codex/personal-research-mode-mvp
```

- [ ] **Step 5: Update draft PR #113**

Update the PR body with the exact new HEAD, AMD identity and values, bounded two-company claim, full test count, local gate results, generated-artifact exclusion, live no-write evidence, remaining external dependencies, and exact next maturity lane. Keep it open and draft; do not merge.

- [ ] **Step 6: Verify exact-head GitHub CI**

Run:

```bash
gh pr view 113 --json isDraft,state,mergeable,headRefOid,statusCheckRollup,url
```

Wait until the `local-engineering-gate` for the exact pushed `headRefOid` completes successfully. Do not reuse prior-head CI.

- [ ] **Step 7: Final completion audit for this slice**

Map each design completion criterion to current code, tests, live result, documentation, Git status, PR state, range hygiene, and exact-head CI. Report this portability slice complete only if all ten criteria are directly proven. Keep the overall commercial-maturity goal active because point-in-time consensus, hosting, external reviewers, calibration, broader evidence depth, and operated-platform controls remain incomplete.
