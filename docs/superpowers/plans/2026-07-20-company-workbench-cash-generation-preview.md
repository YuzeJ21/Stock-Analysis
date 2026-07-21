# Company Workbench Cash-Generation Activation Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an explicit, read-only Company Workbench route that shows one accepted NVIDIA SEC quarterly cash-generation packet as a clearly non-production review preview while leaving the ordinary Workbench and every readiness state unchanged.

**Architecture:** Add a pure activation-preview composer that converts only an `accepted_for_review` SEC pilot result into an immutable, fail-closed Workbench view model. Add a separate bounded live loader for the exact NVIDIA filing and reviewed cutoff, then pass the result into the existing Business Trend renderer only when `cash_preview=1`; raw lineage stays under Advanced and normal Workbench rendering never fetches preview data.

**Tech Stack:** Python 3.12, frozen dataclasses, the existing SEC Companyfacts/submissions/inline-XBRL parser, existing quarterly trend composition, Streamlit, pytest, and Make-based repository gates.

## Global Constraints

- Research-only; no investment advice, broker integration, order routing, auto-trading, direct buy/sell instructions, or post-earnings price prediction.
- Consume only `SecQuarterlyPilotPreview.status == "accepted_for_review"` with an accepted adapter result.
- Keep `production_activation=False`, `readiness_promotions=()`, and `persistence=False` immutable.
- Accept only the `cash_preview=1` route flag; add no arbitrary ticker, accession, filing, or cutoff input.
- Use NVIDIA Q1 FY2027 accession `0001045810-26-000052`, document `nvda-20260426.htm`, and cutoff `2026-07-20T23:59:59-04:00`.
- Withhold all three preview metrics when evidence is missing, rejected, ambiguous, mismatched, post-cutoff, incompatible, incomplete, or has invalid capex-sign proof.
- Leave the ordinary Company Workbench canonical packet and all readiness states unchanged.
- EPS split basis remains unverified without explicit proof; Q4 requires an explicit filed three-month quarter.
- Generate and stage no CSV, JSON, report, sample-report, screenshot, timing, canonical-data, readiness, cache, or manual-review artifact.
- Never run `make readiness`, readiness writers, broad refreshes, canonical writers, screenshot regeneration, consensus apply, production activation, deployment, or PR merge.
- Stage exact files only; never use `git add -A`. Push only `codex/personal-research-mode-mvp`; keep PR #113 draft.

## File Structure

- Create `src/company_workbench_cash_generation_preview.py` for immutable types, query parsing, blocked construction, and pure composition.
- Create `src/company_workbench_cash_generation_preview_loader.py` for exact in-memory NVIDIA loading.
- Modify `src/research_workspace.py` for primary preview cards and Advanced lineage rows.
- Modify `src/dashboard.py` for explicit route gating and optional Business Trend rendering.
- Create `tests/test_company_workbench_cash_generation_preview.py` and `tests/test_company_workbench_cash_generation_preview_loader.py`.
- Modify `tests/test_research_workspace.py`, `tests/test_research_mode_dashboard_contract.py`, and `tests/test_dashboard_render_smoke.py`.
- Modify `ROADMAP.md`, `docs/PERSONAL_RESEARCH_MODE.md`, `docs/METHODOLOGY.md`, `docs/PROVENANCE.md`, `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`, and `tests/test_public_v1_release_docs.py`.

---

### Task 1: Pure Activation-Preview Contract

**Files:**
- Create: `src/company_workbench_cash_generation_preview.py`
- Create: `tests/test_company_workbench_cash_generation_preview.py`

**Interfaces:**
- Consumes: `SecQuarterlyPilotPreview`, `build_quarterly_trend_packet(...)`, and `parse_utc_timestamp(...)`.
- Produces: `CashGenerationPreviewMetric`, `CashGenerationPreviewComponent`, `CompanyWorkbenchCashGenerationPreview`, `company_workbench_cash_preview_requested(value: object) -> bool`, `blocked_company_workbench_cash_generation_preview(...)`, and `compose_company_workbench_cash_generation_preview(...)`.

- [ ] **Step 1: Write the failing accepted-result test**

Construct all evidence in memory. The fixture must contain Revenue `81_615_000_000`, operating income `53_536_000_000`, CFO `50_344_000_000`, capex `-1_757_000_000`, exact SEC lineage, accepted time `2026-05-20T20:35:52+00:00`, `accepted_for_review`, false activation, and empty promotions.

```python
AS_OF = "2026-07-20T23:59:59-04:00"

def test_accepted_sec_packet_composes_complete_non_activation_preview():
    result = compose_company_workbench_cash_generation_preview(
        _accepted_sec_preview(), selected_ticker="NVDA", as_of=AS_OF
    )
    assert result.status == "accepted_for_review"
    assert result.operating_margin.value == pytest.approx(53_536_000_000 / 81_615_000_000)
    assert result.free_cash_flow.value == 48_587_000_000
    assert result.fcf_margin.value == pytest.approx(48_587_000_000 / 81_615_000_000)
    assert result.production_activation is False
    assert result.readiness_promotions == ()
    assert result.persistence is False
    assert result.accession == "0001045810-26-000052"
    assert result.capex_sign_evidence == "explicit_filed_table_outflow"
    assert result.blockers == ()
```

- [ ] **Step 2: Verify the test fails before implementation**

Run `python3 -m pytest tests/test_company_workbench_cash_generation_preview.py::test_accepted_sec_packet_composes_complete_non_activation_preview -q`.

Expected: collection fails because the module does not exist.

- [ ] **Step 3: Add immutable types and strict query parsing**

Implement these exact public shapes:

```python
@dataclass(frozen=True)
class CashGenerationPreviewMetric:
    metric: str
    status: str
    value: float | None
    fiscal_period: str
    source_refs: tuple[str, ...]
    withheld_reason: str

@dataclass(frozen=True)
class CashGenerationPreviewComponent:
    metric: str
    value: float
    currency: str
    fiscal_period: str
    source_ref: str
    published_at: str
    retrieved_at: str
    accounting_basis: str
    duration_basis: str
    q4_evidence_state: str

@dataclass(frozen=True)
class CompanyWorkbenchCashGenerationPreview:
    ticker: str
    fiscal_period: str
    status: str
    message: str
    operating_margin: CashGenerationPreviewMetric
    free_cash_flow: CashGenerationPreviewMetric
    fcf_margin: CashGenerationPreviewMetric
    blockers: tuple[str, ...]
    withheld_metrics: tuple[str, ...]
    accession: str
    source_url: str
    accepted_at: str
    cutoff: str
    capex_sign_evidence: str
    components: tuple[CashGenerationPreviewComponent, ...]
    production_activation: bool = False
    readiness_promotions: tuple[str, ...] = ()
    persistence: bool = False

def company_workbench_cash_preview_requested(value: object) -> bool:
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ""
    return str(value or "").strip() == "1"
```

- [ ] **Step 4: Implement the pure composer**

Implement:

```python
def compose_company_workbench_cash_generation_preview(
    pilot: SecQuarterlyPilotPreview,
    *,
    selected_ticker: str,
    as_of: str,
) -> CompanyWorkbenchCashGenerationPreview:
```

Validate timezone-aware cutoff/acceptance timestamps, both acceptance statuses, false activation flags, empty promotions, selected/extracted ticker identity, no extraction blockers, exact metadata, `sec_companyfacts` source identity, accepted observation count, acceptance before cutoff, all observations before cutoff, explicit Q4 evidence, and `explicit_filed_table_outflow`. Compose through `build_quarterly_trend_packet(..., business_observations=...)`. Expose success only when all three metrics have values for the extraction period. Any blocker returns three withheld metrics and `components=()`.

- [ ] **Step 5: Verify the success test passes**

Run the Step 2 command. Expected: `1 passed`.

- [ ] **Step 6: Add fail-closed and query tests**

Parameterize pilot-blocked, missing/blocked acceptance, mixed ticker, extraction blockers, activation true, promotions non-empty, missing accession/source/accepted time, post-cutoff time, wrong capex proof, incomplete components, ambiguous revisions, incompatible definitions, and Q4 without explicit proof. Every result must be `withheld`, carry the expected stable blocker, have three `None` values, and expose no components. Prove only scalar/list/tuple `"1"` enables the route; `None`, `""`, `"0"`, `"true"`, `"yes"`, and `"1,other"` do not.

- [ ] **Step 7: Run and commit the pure contract**

```bash
python3 -m pytest tests/test_company_workbench_cash_generation_preview.py -q
git add -- src/company_workbench_cash_generation_preview.py tests/test_company_workbench_cash_generation_preview.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Add Workbench cash preview contract"
```

Expected: all focused tests and hygiene checks pass.

---

### Task 2: Exact In-Memory NVIDIA Loader

**Files:**
- Create: `src/company_workbench_cash_generation_preview_loader.py`
- Create: `tests/test_company_workbench_cash_generation_preview_loader.py`

**Interfaces:**
- Consumes: the existing exact SEC fetch/extract/accept helpers and Task 1 composer.
- Produces: exact identity constants and `load_company_workbench_cash_generation_preview(ticker: str, *, user_agent: str | None = None, fetcher=None, retrieved_at: str | None = None)`.

- [ ] **Step 1: Write the failing bounded-loader test**

Monkeypatch fetch, extraction, acceptance, and rights loading. Assert fetch receives only CIK `0001045810`, accession `0001045810-26-000052`, and `nvda-20260426.htm`; extraction receives fiscal period `2027-Q1`, dates `2026-01-26` through `2026-04-26`, and cutoff `2026-07-20T23:59:59-04:00`. Assert the returned result is accepted and non-persistent.

- [ ] **Step 2: Verify the loader test fails**

Run `python3 -m pytest tests/test_company_workbench_cash_generation_preview_loader.py::test_loader_uses_only_reviewed_nvidia_identity_and_composes_in_memory -q`.

Expected: collection fails because the loader module does not exist.

- [ ] **Step 3: Implement the bounded loader**

Define:

```python
PREVIEW_TICKER = "NVDA"
PREVIEW_CIK = "0001045810"
PREVIEW_FISCAL_PERIOD = "2027-Q1"
PREVIEW_PERIOD_START = "2026-01-26"
PREVIEW_PERIOD_END = "2026-04-26"
PREVIEW_ACCESSION = "0001045810-26-000052"
PREVIEW_PRIMARY_DOCUMENT = "nvda-20260426.htm"
PREVIEW_AS_OF = "2026-07-20T23:59:59-04:00"
```

Return `unsupported_preview_ticker:<symbol>` before fetching non-NVDA. Otherwise fetch the exact three endpoints in memory, extract using the fixed identity and cutoff, assess with the source-rights registry, and compose. Catch `SECUserAgentError`, `SecQuarterlyPreviewFetchError`, `TypeError`, and `ValueError` as `preview_load_blocked:<ExceptionClass>` without secrets or raw payloads. Add no paths, cache, argparse, output, apply, readiness, refresh, or fallback surface.

- [ ] **Step 4: Add blocked and surface tests**

Prove non-NVDA never invokes fetch; missing SEC user agent, fetch error, malformed extraction, and blocked acceptance withhold all values. Inspect the function signature and module source to reject output/apply/refresh/readiness/accession/CIK/filing/cutoff parameters and `Path`, `open(`, `to_csv`, `to_json`, alternate providers, or fixture fallback.

- [ ] **Step 5: Run and commit the loader**

```bash
python3 -m pytest tests/test_company_workbench_cash_generation_preview_loader.py -q
git add -- src/company_workbench_cash_generation_preview_loader.py tests/test_company_workbench_cash_generation_preview_loader.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Load bounded Workbench cash preview"
```

Expected: all tests pass without network or file writes.

---

### Task 3: Answer-First Workbench Rendering

**Files:**
- Modify: `src/research_workspace.py`
- Modify: `src/dashboard.py`
- Modify: `tests/test_research_workspace.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`
- Modify: `tests/test_dashboard_render_smoke.py`

**Interfaces:**
- Consumes: Task 1 view model/query helper and Task 2 loader.
- Produces: `cash_generation_preview_cards(preview)`, `cash_generation_preview_rows(preview)`, and optional `cash_generation_preview` on `render_single_stock_report(...)`.

- [ ] **Step 1: Write failing presentation tests**

Assert accepted cards appear in this order: boundary, Operating Margin, Free Cash Flow, FCF Margin. Require title `Cash-generation review preview — not production evidence`, one-decimal margin percentages, comma-formatted FCF, `preview_available` rather than `ready`, blank commands, and non-activation badges. Require accession, timestamps, capex sign, definitions, values, and source refs only in Advanced rows. Withheld input must show three `Withheld` cards and no component rows.

- [ ] **Step 2: Verify presentation tests fail**

Run `python3 -m pytest tests/test_research_workspace.py -k cash_generation_preview -q`.

Expected: missing helper imports or attributes.

- [ ] **Step 3: Implement presentation helpers**

In `src/research_workspace.py`, build four answer-first cards without lineage identifiers. Build Advanced rows for accession, source URL, accepted time, cutoff, capex sign, non-activation fields, and each component's value, definition, timestamps, and source ref. Do not add commands, advice, scores, recommendations, or readiness claims.

- [ ] **Step 4: Write failing dashboard route tests**

Require `render_company_workbench` to call the strict query helper before the loader and pass `None` otherwise. Require the ordinary `load_dashboard_quarterly_trend(ticker)` call to remain independent. Within Business Trend, require canonical cards first, preview cards second, then collapsed `Advanced: cash-generation preview evidence` rows. Require no preview flag in normal navigation or Discover links.

- [ ] **Step 5: Verify dashboard tests fail**

Run `python3 -m pytest tests/test_research_mode_dashboard_contract.py -k "cash_preview or cash_generation" -q`.

Expected: failures because the route is not integrated.

- [ ] **Step 6: Integrate the explicit route**

Add `cash_generation_preview: CompanyWorkbenchCashGenerationPreview | None = None` to `render_single_stock_report(...)`. After ordinary `quarterly_trend_cards(trend_packet)`, render preview cards only when supplied, followed by a collapsed Advanced preview-evidence dataframe and non-activation caption. In `render_company_workbench`, use exactly:

```python
cash_generation_preview = (
    load_company_workbench_cash_generation_preview(ticker)
    if company_workbench_cash_preview_requested(st.query_params.get("cash_preview"))
    else None
)
```

Pass it separately while retaining `quarterly_trend_packet=load_dashboard_quarterly_trend(ticker)`. Do not change other routes.

- [ ] **Step 7: Add explicit-route render smoke**

Keep the normal Workbench smoke route with no loader call. Add an explicit preview route whose loader is patched to a complete in-memory view model and require `Cash-generation review preview`, `not production evidence`, `Operating Margin`, `Free Cash Flow`, and `FCF Margin`. No test may contact SEC or write an artifact.

- [ ] **Step 8: Run focused rendering verification**

```bash
python3 -m pytest tests/test_research_workspace.py tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py -q
make dashboard-smoke
make research-dashboard-render-smoke
git status --short
```

Expected: all tests and smokes pass; status lists only intentional source/test changes.

- [ ] **Step 9: Commit the rendering slice**

```bash
git add -- src/research_workspace.py src/dashboard.py tests/test_research_workspace.py tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Render explicit Workbench cash preview"
```

---

### Task 4: Documentation and Roadmap Truth

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/PERSONAL_RESEARCH_MODE.md`
- Modify: `docs/METHODOLOGY.md`
- Modify: `docs/PROVENANCE.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: `tests/test_public_v1_release_docs.py`

**Interfaces:**
- Consumes: verified Tasks 1–3 behavior.
- Produces: durable capability, boundary, maturity, and next-stage evidence.

- [ ] **Step 1: Write failing documentation tests**

Require the guide to contain `cash_preview=1`, `Cash-generation review preview`, and `not production evidence`; provenance to contain `production_activation=false`, `readiness_promotions=()`, and `no canonical persistence`; roadmap to say `one explicit user-flow composition` and `does not prove a second company`; methodology to state complete withholding on any required-metric failure and Advanced-only technical lineage; continuation prompt to retain the NVIDIA stop rule and identify a bounded second-company proof as the next assessment.

- [ ] **Step 2: Verify documentation tests fail**

Run `python3 -m pytest tests/test_public_v1_release_docs.py -k "cash_generation or quarterly" -q`.

Expected: failure on new preview wording.

- [ ] **Step 3: Update exact documentation**

Document the explicit local route, fixed cutoff, accepted-only composer, unchanged normal Workbench, all-or-nothing preview metrics, Advanced lineage, false activation, empty promotions, no persistence/readiness/artifacts, and no proof of another company, historical depth, Q4, hosting, reviewer adoption, calibration, demand, or product-market fit. Retain exact unblock conditions for point-in-time consensus, calibration, hosting/identity/operations, external review, and market evidence. Set the continuation prompt's expected HEAD only after the verified documentation commit.

- [ ] **Step 4: Run and commit documentation**

```bash
python3 -m pytest tests/test_public_v1_release_docs.py -q
make public-wording-check
git diff --check
git add -- ROADMAP.md docs/PERSONAL_RESEARCH_MODE.md docs/METHODOLOGY.md docs/PROVENANCE.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md tests/test_public_v1_release_docs.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Document Workbench cash preview evidence"
```

Expected: documentation and wording checks pass with zero generated files staged.

---

### Task 5: Full Verification, GitHub Sync, and Next-Stage Assessment

**Files:**
- Modify only if verification reveals an in-scope defect: files already named above.
- External update: draft PR #113 body only; no merge or deployment.

**Interfaces:**
- Consumes: all committed preview changes.
- Produces: complete local gate evidence, clean range hygiene, exact-head CI, updated draft PR, and next-stage classification.

- [ ] **Step 1: Run focused and full tests**

```bash
python3 -m pytest tests/test_company_workbench_cash_generation_preview.py tests/test_company_workbench_cash_generation_preview_loader.py tests/test_research_workspace.py tests/test_research_mode_dashboard_contract.py tests/test_dashboard_render_smoke.py tests/test_public_v1_release_docs.py -q
python3 -m pytest tests -q
```

Expected: all tests pass; no new warning is accepted without review.

- [ ] **Step 2: Run every required product and hygiene gate**

```bash
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

Expected: all engineering gates pass; pilot readiness may remain truthfully blocked on stale saved readiness; hygiene reports zero generated churn.

- [ ] **Step 3: Verify scope and push only the feature branch**

```bash
git status --short --branch
git log -8 --oneline --decorate
git diff origin/codex/personal-research-mode-mvp...HEAD --stat
make diff-hygiene-summary
git push origin codex/personal-research-mode-mvp
```

Expected: the clean branch advances with only intentional commits.

- [ ] **Step 4: Update and verify draft PR #113**

Update the PR body with route behavior, accepted-only/non-activation/no-persistence boundaries, tests, full gates, zero generated churn, exact head, and remaining stale-readiness, consensus, calibration, hosting, reviewer, portability, and market gates. Verify with:

```bash
gh pr view 113 --json state,isDraft,mergeable,headRefName,headRefOid,statusCheckRollup,url
```

Expected: open, draft, correct feature branch/head, no merge. Wait for `local-engineering-gate` success at the exact pushed SHA; do not reuse earlier CI evidence.

- [ ] **Step 5: Assess the bounded next maturity slice**

Classify a second-company SEC portability proof as the next local lane only if one exact non-Q4 official filing can test a materially different parser structure without broad discovery or refresh. Otherwise record `external_source_selection_required` and stop broad source loops. Retain `permitted_dataset_required` for point-in-time consensus, `calibration_cohort_required` for probabilities, `hosted_account_identity_operations_required` for hosted beta, and `external_reviewer_and_demand_evidence_required` for market maturity.

- [ ] **Step 6: Complete the requirement-by-requirement handoff audit**

Verify source, tests, rendered behavior, Git history, PR state, and hygiene evidence against every design requirement. Report repository/PR status, product stage, roadmap item, changes, tests, commits/push, excluded artifacts, external dependencies, remaining gaps, exact next step, review safety, and whether the overall goal remains active. Do not call the overall product complete merely because this local slice passes.
