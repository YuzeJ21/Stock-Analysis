# SEC Quarterly Cash-Generation Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove one real NVIDIA quarter can pass the existing quarterly cash-generation adapter review from exact SEC Companyfacts, submissions, and filed-table evidence without persisting data or changing readiness.

**Architecture:** A pure parser selects one exact accession and three-month context from already-retrieved SEC payloads, matches each structured fact to its inline XBRL filing fact, and requires explicit filed-table outflow presentation before making capex negative. A separate read-only client/CLI fetches only the three exact SEC endpoints, renders a human review summary, and composes the existing acceptance contract; source field scope and production activation remain independent.

**Tech Stack:** Python 3.12 standard library (`dataclasses`, `html.parser`, `json`, `urllib`), existing immutable earnings/cash-generation/source-rights contracts, pytest, YAML source registry, Make read-only operator target.

## Global Constraints

- Research-only; no investment advice, broker integration, order routing, auto-trading, buy/sell instruction, or post-earnings price prediction.
- The pilot is one exact NVIDIA Q1 FY2027 evidence path, not broad coverage.
- Use `sec_companyfacts` as the exact registered source ID; do not split, alias, or compose source IDs.
- Require accession `0001045810-26-000052`, period `2027-Q1`, start `2026-01-26`, end `2026-04-26`, and exact SEC submissions acceptance time for the first live proof.
- Companyfacts supplies fact identity and magnitude; the exact filed inline XBRL table must independently prove the capex outflow presentation.
- Never infer capex sign from concept name, taxonomy balance, history, or an unsigned Companyfacts magnitude.
- Never derive Q4 from annual or nine-month values; the initial live pilot is Q1 only.
- Never substitute filing-date midnight or retrieval time for publication time.
- `accepted_for_review` never means production activation, readiness promotion, source-wide coverage, reviewer validation, or market validation.
- `production_activation` remains `False`; `readiness_promotions` remains `()`.
- Do not run `make readiness`, broad refresh, apply, or generated report commands.
- Do not create or modify CSV, JSON, report, sample-report, screenshot, timing, canonical-data, or manual-review artifacts.
- Unit tests use minimal in-memory SEC-shaped fixtures and make no network request.
- Stage exact intentional paths only; never use `git add -A`.
- Push only `codex/personal-research-mode-mvp`; keep PR #113 draft; do not merge or deploy.

---

### Task 1: Pure Exact-Accession SEC Parser

**Files:**
- Create: `src/sec_quarterly_cash_generation_pilot.py`
- Create: `tests/test_sec_quarterly_cash_generation_pilot.py`

**Interfaces:**
- Consumes: `ticker: str`, `cik: str`, `fiscal_period: str`, `period_start_date: str`, `period_end_date: str`, `accession: str`, in-memory Companyfacts/submissions/filing HTML payloads, `retrieved_at: str`, `as_of: str`, and an explicit source-rights registry.
- Produces: frozen `SecQuarterlyPilotExtraction`, frozen `SecQuarterlyPilotPreview`, `extract_sec_quarterly_cash_generation(...)`, and `preview_sec_quarterly_cash_generation(...)`.

- [ ] **Step 1: Write the first failing exact-quarter test**

Create minimal Companyfacts, submissions, and inline-XBRL fixtures in `tests/test_sec_quarterly_cash_generation_pilot.py`. Use the real concept names and NVIDIA-shaped values while labeling the payload as a test fixture:

```python
def test_exact_q1_payload_builds_source_backed_components_and_revenue():
    result = extract_sec_quarterly_cash_generation(
        ticker="NVDA",
        cik="0001045810",
        fiscal_period="2027-Q1",
        period_start_date="2026-01-26",
        period_end_date="2026-04-26",
        accession="0001045810-26-000052",
        companyfacts_payload=_companyfacts_fixture(),
        submissions_payload=_submissions_fixture(),
        filing_html=_filing_fixture(capex_outflow=True),
        retrieved_at="2026-07-20T15:00:00+00:00",
        as_of="2026-07-20T15:00:00+00:00",
    )

    assert result.blockers == ()
    assert result.accepted_at == "2026-05-20T20:35:52+00:00"
    assert [row.metric for row in result.observations] == [
        "operating_income",
        "cash_from_operations",
        "capital_expenditures",
    ]
    assert [row.value for row in result.observations] == [
        53_536_000_000.0,
        50_344_000_000.0,
        -1_757_000_000.0,
    ]
    assert result.revenue_actuals[0].revenue_actual == 81_615_000_000.0
    assert result.capex_sign_evidence == "explicit_filed_table_outflow"
    assert result.source_url.endswith("/nvda-20260426.htm")
```

Fixture facts must use `form="10-Q"`, `fy=2027`, `fp="Q1"`, unit `USD`, the exact accession/start/end dates, and unique inline fact IDs. The submissions fixture must expose `acceptanceDateTime="2026-05-20T20:35:52.000Z"` for the same accession.

- [ ] **Step 2: Run the exact-quarter test and verify RED**

Run:

```bash
python3 -m pytest tests/test_sec_quarterly_cash_generation_pilot.py::test_exact_q1_payload_builds_source_backed_components_and_revenue -q
```

Expected: test collection fails because `src.sec_quarterly_cash_generation_pilot` does not exist.

- [ ] **Step 3: Add frozen result types and exact concept maps**

Create `src/sec_quarterly_cash_generation_pilot.py` with these public shapes:

```python
@dataclass(frozen=True)
class SecQuarterlyPilotExtraction:
    ticker: str
    cik: str
    fiscal_period: str
    period_start_date: str
    period_end_date: str
    accession: str
    filing_date: str
    accepted_at: str
    source_url: str
    observations: tuple[QuarterlyBusinessObservation, ...]
    revenue_actuals: tuple[QuarterlyActual, ...]
    capex_sign_evidence: str
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class SecQuarterlyPilotPreview:
    extraction: SecQuarterlyPilotExtraction
    acceptance: QuarterlyAdapterAcceptance | None
    status: str
    blockers: tuple[str, ...]
    production_activation: bool = False
    readiness_promotions: tuple[str, ...] = ()
```

Use these ordered concept maps:

```python
REVENUE_CONCEPTS = (
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
    "SalesRevenueGoodsNet",
)
OPERATING_INCOME_CONCEPTS = ("OperatingIncomeLoss",)
CASH_FROM_OPERATIONS_CONCEPTS = (
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
)
CAPEX_CONCEPTS = (
    "PaymentsToAcquireProductiveAssets",
    "PaymentsToAcquirePropertyPlantAndEquipment",
)
```

- [ ] **Step 4: Implement exact Companyfacts and submissions selection**

Add helpers that:

1. inspect only `facts.us-gaap.<concept>.units.USD`;
2. retain rows matching exact accession, start, end, `10-Q`/`10-Q/A`, fiscal year, and fiscal-quarter code;
3. choose the first ordered concept containing one unique exact value;
4. return `<metric>:fact_missing` or `<metric>:fact_ambiguous` rather than guessing;
5. locate the exact accession in aligned `filings.recent` arrays;
6. require matching form, filing date, primary document, and timezone-aware `acceptanceDateTime`;
7. block `acceptance_after_cutoff` when the SEC acceptance time exceeds `as_of`.

Use `parse_utc_timestamp` for both `accepted_at` and cutoff. Normalize the SEC `Z` time through that existing function. Do not synthesize a time from `filingDate`.

- [ ] **Step 5: Implement inline XBRL context and row parsing**

Use only `html.parser.HTMLParser`. Track:

- each `xbrli:context` ID and its `xbrli:startdate`/`xbrli:enddate`;
- each table row's ordered text tokens;
- every `ix:nonfraction` fact's `name`, `contextref`, `scale`, `id`, and displayed magnitude; and
- the nearest non-empty text token before and after each fact.

An inline fact matches only when concept, exact context start/end, absolute scaled magnitude, and primary filing all match. For capex, require the immediately surrounding displayed tokens to be `(` and `)`. Return `capital_expenditures:explicit_outflow_evidence_missing` if magnitude exists but that presentation proof does not.

Construct source references as `f"{source_url}#{inline_fact_id}"`. Create three `QuarterlyBusinessObservation` values with source `sec_companyfacts`, currency `USD`, scale `1.0`, accounting basis `reported`, duration basis `three_months`, exact acceptance time as `published_at`, exact retrieval time, and `q4_evidence_state="not_q4"`. Create one Revenue-only `QuarterlyActual` with the same definition and source lineage.

- [ ] **Step 6: Run the exact-quarter test and verify GREEN**

Run the Step 2 command. Expected: 1 passed.

- [ ] **Step 7: Add failing sign, identity, ambiguity, and temporal tests**

Add parameterized tests asserting these exact blockers:

```python
@pytest.mark.parametrize(
    ("mutation", "blocker"),
    [
        ("missing_parentheses", "capital_expenditures:explicit_outflow_evidence_missing"),
        ("wrong_accession", "operating_income:fact_missing"),
        ("wrong_context", "capital_expenditures:inline_fact_missing"),
        ("wrong_magnitude", "capital_expenditures:inline_fact_missing"),
        ("ytd_context", "operating_income:fact_missing"),
        ("duplicate_value", "cash_from_operations:fact_ambiguous"),
        ("missing_acceptance", "submissions:accession_missing"),
        ("naive_acceptance", "submissions:acceptance_time_invalid"),
        ("post_cutoff", "acceptance_after_cutoff"),
    ],
)
def test_extraction_failures_are_deterministic(mutation, blocker):
    result = _extract_with_mutation(mutation)
    assert blocker in result.blockers
    assert result.observations == ()
    assert result.revenue_actuals == ()
```

Add a Q4/YTD test that requests `2027-Q4` with a nine-month fact and asserts `q4_explicit_three_month_filing_required`. Add an unsupported currency test that asserts `<metric>:usd_fact_missing`. Add a filing primary-document mismatch test that asserts `filing:primary_document_mismatch`.

- [ ] **Step 8: Run the failure tests and verify RED**

Run:

```bash
python3 -m pytest tests/test_sec_quarterly_cash_generation_pilot.py -q
```

Expected: new cases fail until blocker aggregation and fail-closed empty outputs are implemented.

- [ ] **Step 9: Complete deterministic fail-closed extraction**

Aggregate safely knowable blockers in insertion order with `tuple(dict.fromkeys(blockers))`. If any blocker exists, return empty observations and Revenue actuals, `capex_sign_evidence="blocked"`, and no partially usable values. Reject Q4 unless an exact three-month Companyfacts context and matching filed-table context exist; never difference annual or YTD values.

- [ ] **Step 10: Add and satisfy preview-composition tests**

Add:

```python
def test_preview_composes_existing_acceptance_without_activation():
    preview = preview_sec_quarterly_cash_generation(
        extraction=_successful_extraction(),
        rights_registry=_sec_rights_fixture(include_cash_fields=True),
        as_of="2026-07-20T15:00:00+00:00",
    )

    assert preview.status == "accepted_for_review"
    assert preview.blockers == ()
    assert preview.acceptance is not None
    assert preview.acceptance.accepted_observation_count == 3
    assert preview.production_activation is False
    assert preview.readiness_promotions == ()


def test_extraction_or_rights_blocker_never_returns_accepted_preview():
    extraction_blocked = preview_sec_quarterly_cash_generation(
        extraction=_blocked_extraction(),
        rights_registry=_sec_rights_fixture(include_cash_fields=True),
    )
    rights_blocked = preview_sec_quarterly_cash_generation(
        extraction=_successful_extraction(),
        rights_registry=_sec_rights_fixture(include_cash_fields=False),
    )
    assert extraction_blocked.acceptance is None
    assert extraction_blocked.status == "blocked"
    assert rights_blocked.status == "blocked"
    assert "source_fields_missing:" in " ".join(rights_blocked.blockers)
```

Run:

```bash
python3 -m pytest tests/test_sec_quarterly_cash_generation_pilot.py tests/test_quarterly_cash_generation_adapter.py tests/test_quarterly_cash_generation.py -q
```

Expected: all focused contract tests pass.

- [ ] **Step 11: Commit the pure parser slice**

```bash
git add -- src/sec_quarterly_cash_generation_pilot.py tests/test_sec_quarterly_cash_generation_pilot.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Parse exact SEC quarterly cash evidence"
git push origin codex/personal-research-mode-mvp
```

---

### Task 2: Explicit SEC Field-Scope Review

**Files:**
- Modify: `config/source_rights.yml:12-16`
- Modify: `tests/test_quarterly_cash_generation_adapter.py`
- Modify: `tests/test_sec_quarterly_cash_generation_pilot.py`

**Interfaces:**
- Consumes: existing exact-source `commercial_eligibility` and `REQUIRED_SOURCE_FIELDS` contracts.
- Produces: explicit checked-in `sec_companyfacts` support for `operating_income`, `cash_from_operations`, and `capital_expenditures`; no change to another source or to commercial-use status.

- [ ] **Step 1: Change the existing blocker test to require exact SEC acceptance**

Replace `test_checked_in_sec_rights_do_not_silently_claim_component_support` with:

```python
def test_checked_in_sec_rights_explicitly_support_reviewed_cash_components():
    rows = [
        _observation(
            metric=row.metric,
            value=row.value,
            source="sec_companyfacts",
            source_ref=f"https://www.sec.gov/Archives/edgar/data/1/example.htm#{row.metric}",
        )
        for row in _complete_rows()
    ]

    result = _assess(
        rows,
        source_id="sec_companyfacts",
        rights_registry=load_source_rights_registry(),
    )

    assert result.status == "accepted_for_review"
    assert result.rights_status == "approved"
    assert result.production_activation is False
    assert result.readiness_promotions == ()
```

- [ ] **Step 2: Run the changed test and verify RED**

Run:

```bash
python3 -m pytest tests/test_quarterly_cash_generation_adapter.py::test_checked_in_sec_rights_explicitly_support_reviewed_cash_components -q
```

Expected: FAIL with the three existing `source_fields_missing` values.

- [ ] **Step 3: Extend only the exact SEC supported-field list**

Add these literal entries under `sec_companyfacts.supported_fields`:

```yaml
      - operating_income
      - cash_from_operations
      - capital_expenditures
```

Do not change `commercial_use`, redistribution, storage, attribution, authentication, rate limits, fallback priority, or any other source.

- [ ] **Step 4: Prove scope independence and verify GREEN**

Add a test that builds a separate approved registry missing `capital_expenditures` and asserts acceptance remains blocked with `source_fields_missing:capital_expenditures`. Run:

```bash
python3 -m pytest tests/test_quarterly_cash_generation_adapter.py tests/test_commercial_source_rights.py tests/test_sec_quarterly_cash_generation_pilot.py -q
```

Expected: all focused rights and pilot tests pass.

- [ ] **Step 5: Commit the field-scope decision**

```bash
git add -- config/source_rights.yml tests/test_quarterly_cash_generation_adapter.py tests/test_sec_quarterly_cash_generation_pilot.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Review SEC cash generation field scope"
git push origin codex/personal-research-mode-mvp
```

---

### Task 3: Read-Only Live Preview Command

**Files:**
- Create: `src/sec_quarterly_cash_generation_preview.py`
- Create: `tests/test_sec_quarterly_cash_generation_preview.py`
- Modify: `Makefile`

**Interfaces:**
- Consumes: Task 1 parser/preview, checked-in rights registry, exact SEC Companyfacts URL, exact SEC submissions URL, and exact accession primary-document URL.
- Produces: `fetch_sec_quarterly_pilot_payloads(...)`, `render_sec_quarterly_pilot_preview(...)`, `main(argv=None) -> int`, and read-only Make target `sec-quarterly-cash-preview`.

- [ ] **Step 1: Write failing client and renderer tests**

Create `tests/test_sec_quarterly_cash_generation_preview.py` with an injected fetcher that records URLs and returns in-memory bytes. Assert:

```python
def test_client_fetches_only_three_exact_sec_endpoints_without_cache(tmp_path, monkeypatch):
    seen = []
    payloads = fetch_sec_quarterly_pilot_payloads(
        cik="0001045810",
        accession="0001045810-26-000052",
        primary_document="nvda-20260426.htm",
        user_agent="Research Test test@example.com",
        fetcher=_recording_fetcher(seen),
    )
    assert seen == [
        "https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json",
        "https://data.sec.gov/submissions/CIK0001045810.json",
        "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000052/nvda-20260426.htm",
    ]
    assert not list(tmp_path.iterdir())
    assert set(payloads) == {"companyfacts", "submissions", "filing_html"}


def test_renderer_is_human_readable_and_keeps_non_activation_visible():
    text = render_sec_quarterly_pilot_preview(_accepted_preview())
    assert "status: accepted_for_review" in text
    assert "NVIDIA Q1 FY2027" in text
    assert "capex sign evidence: explicit_filed_table_outflow" in text
    assert "production activation: false" in text
    assert "readiness promotions: none" in text
    assert "generated artifacts: none" in text
    assert not text.lstrip().startswith("{")
```

- [ ] **Step 2: Run the preview tests and verify RED**

Run:

```bash
python3 -m pytest tests/test_sec_quarterly_cash_generation_preview.py -q
```

Expected: collection fails because the preview module does not exist.

- [ ] **Step 3: Implement the no-cache SEC client**

Use `urllib.request.Request`/`urlopen`, 30-second timeout, `User-Agent`, `Accept`, and no filesystem API. Require a non-blank explicit argument or `SEC_USER_AGENT`; otherwise raise the existing `SECUserAgentError`. Decode Companyfacts and submissions through `json.loads`; keep filing HTML as text. Convert HTTP, URL, decode, and JSON failures into one stable `SecQuarterlyPreviewFetchError` naming only the failed endpoint class, not credentials.

- [ ] **Step 4: Implement deterministic rendering and CLI arguments**

The CLI must require or default to these exact pilot values:

```text
--ticker NVDA
--cik 0001045810
--fiscal-period 2027-Q1
--period-start 2026-01-26
--period-end 2026-04-26
--accession 0001045810-26-000052
--primary-document nvda-20260426.htm
--as-of <required timezone-aware cutoff>
```

The command loads `config/source_rights.yml`, fetches the exact three endpoints, parses and assesses them, prints only the human renderer, and returns `0` for `accepted_for_review` or `2` for blocked/fetch-error states. It must expose no output-file, JSON, apply, activation, refresh, readiness, or fallback argument.

- [ ] **Step 5: Add the read-only Make target and prove its surface**

Add:

```make
.PHONY: sec-quarterly-cash-preview
sec-quarterly-cash-preview:
	@python3 -m src.sec_quarterly_cash_generation_preview \
		--ticker "$(or $(TICKER),NVDA)" \
		--cik "$(or $(CIK),0001045810)" \
		--fiscal-period "$(or $(FISCAL_PERIOD),2027-Q1)" \
		--period-start "$(or $(PERIOD_START),2026-01-26)" \
		--period-end "$(or $(PERIOD_END),2026-04-26)" \
		--accession "$(or $(ACCESSION),0001045810-26-000052)" \
		--primary-document "$(or $(PRIMARY_DOCUMENT),nvda-20260426.htm)" \
		--as-of "$(AS_OF)"
```

Add a test requiring `AS_OF` and scanning the module/target for the absence of `write_text`, `open(`, `Path(`, `--output`, `make readiness`, `apply`, cache paths, and provider fallbacks.

- [ ] **Step 6: Verify preview behavior with injected payloads**

Run:

```bash
python3 -m pytest tests/test_sec_quarterly_cash_generation_preview.py tests/test_sec_quarterly_cash_generation_pilot.py tests/test_sec_companyfacts.py -q
```

Expected: all preview, parser, and SEC provider regression tests pass without network access.

- [ ] **Step 7: Run the one permitted live NVIDIA preview**

Run only after confirming `SEC_USER_AGENT` is configured:

```bash
make sec-quarterly-cash-preview AS_OF=2026-07-20T23:59:59-04:00
```

Expected evidence:

```text
status: accepted_for_review
accession: 0001045810-26-000052
accepted at: 2026-05-20T20:35:52+00:00
operating income: 53536000000.0 USD
cash from operations: 50344000000.0 USD
capital expenditures: -1757000000.0 USD
capex sign evidence: explicit_filed_table_outflow
production activation: false
readiness promotions: none
generated artifacts: none
```

Immediately run `git status --short` and `make diff-hygiene-summary`. Any newly written generated artifact is a failure; do not stage it.

- [ ] **Step 8: Commit the live-preview capability**

```bash
git add -- src/sec_quarterly_cash_generation_preview.py tests/test_sec_quarterly_cash_generation_preview.py Makefile
make staged-hygiene-check
git diff --cached --check
git commit -m "Add read-only SEC cash generation preview"
git push origin codex/personal-research-mode-mvp
```

---

### Task 4: Documentation, Roadmap, Continuation, And PR Evidence

**Files:**
- Modify: `docs/METHODOLOGY.md`
- Modify: `docs/PROVENANCE_CONTRACT.md`
- Modify: `docs/DATA_STRATEGY.md`
- Modify: `docs/PERSONAL_RESEARCH_MODE.md`
- Modify: `ROADMAP.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: `tests/test_public_v1_release_docs.py`

**Interfaces:**
- Consumes: verified parser, field-scope, command, and live-preview evidence from Tasks 1–3.
- Produces: truthful public/internal boundaries, next-stage instructions, and draft PR #113 evidence.

- [ ] **Step 1: Write the failing documentation contract test**

Add a test asserting all of these literal distinctions:

```python
def test_sec_cash_generation_pilot_docs_preserve_review_boundary():
    methodology = _read("docs/METHODOLOGY.md")
    provenance = _read("docs/PROVENANCE_CONTRACT.md")
    strategy = _read("docs/DATA_STRATEGY.md")
    personal = _read("docs/PERSONAL_RESEARCH_MODE.md")
    roadmap = _read("ROADMAP.md")
    prompt = _read("docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md")

    assert "explicit_filed_table_outflow" in methodology
    assert "acceptanceDateTime" in provenance
    assert "sec_companyfacts" in strategy
    assert "accepted_for_review is not production activation" in personal
    assert "NVIDIA Q1 FY2027" in roadmap
    assert "does not activate Company Workbench" in roadmap
    assert "sec-quarterly-cash-preview" in prompt
    assert "do not repeat the NVIDIA pilot" in prompt
```

- [ ] **Step 2: Run the documentation test and verify RED**

Run:

```bash
python3 -m pytest tests/test_public_v1_release_docs.py::test_sec_cash_generation_pilot_docs_preserve_review_boundary -q
```

Expected: failure because the pilot evidence and continuation boundary are not documented.

- [ ] **Step 3: Update methodology, provenance, and source strategy**

Document the exact-quarter/accession selection, exact submissions acceptance timestamp, inline-XBRL fact/context/magnitude match, filed-table parentheses requirement, negative capex only after explicit outflow proof, and existing FCF formula. State that the source-rights edit is a field-scope review under the existing SEC record, not a new legal opinion or entitlement.

- [ ] **Step 4: Update user guidance and ROADMAP**

Record NVIDIA Q1 FY2027 as one official-source adapter preview accepted for review. State exactly that it does not activate Company Workbench, rebuild readiness, prove other companies/quarters, supply point-in-time consensus, calibrate probabilities, establish hosted reliability, replace an independent reviewer, or validate product-market fit.

Move the quarterly adapter roadmap state from `external_source_and_review_required` to `one_company_source_preview_accepted_for_review`; retain separate `production_activation_required` and `broader_coverage_unproven` gates.

- [ ] **Step 5: Update the persistent continuation prompt**

Set expected HEAD to the latest verified descendant. Add the completed pilot evidence and the stop rule `do not repeat the NVIDIA pilot unless its source filing changes or a regression is suspected`. Set the exact next executable stage to a separately designed Company Workbench activation preview or a second-company portability proof; do not authorize either automatically, generated writes, readiness rebuild, broad refresh, consensus fabrication, or hosted deployment.

- [ ] **Step 6: Run documentation and focused product checks**

Run:

```bash
python3 -m pytest tests/test_public_v1_release_docs.py tests/test_sec_quarterly_cash_generation_pilot.py tests/test_sec_quarterly_cash_generation_preview.py tests/test_quarterly_cash_generation_adapter.py tests/test_quarterly_cash_generation.py tests/test_sec_companyfacts.py -q
make public-wording-check
git diff --check
```

Expected: all checks pass.

- [ ] **Step 7: Run the complete non-writing verification matrix**

Run in this order:

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
make pr-range-hygiene-check BASE_SHA=origin/main HEAD_SHA=HEAD
git diff --check
```

Do not run `make readiness`. If a gate writes an unexpected generated artifact, stop, classify it, and keep it unstaged.

- [ ] **Step 8: Stage exact documentation and commit**

```bash
git add -- docs/METHODOLOGY.md docs/PROVENANCE_CONTRACT.md docs/DATA_STRATEGY.md docs/PERSONAL_RESEARCH_MODE.md ROADMAP.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md tests/test_public_v1_release_docs.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Document SEC cash generation pilot evidence"
git push origin codex/personal-research-mode-mvp
```

- [ ] **Step 9: Update draft PR #113 without changing draft state**

Confirm exact-head PR state first:

```bash
gh pr view 113 --json number,state,isDraft,mergeable,headRefName,headRefOid,statusCheckRollup,url
```

Update the PR body with a concise section naming the three source endpoints, NVIDIA accession/period, exact accepted values, capex-sign evidence, focused/full check results, zero generated artifacts, and remaining activation/coverage/consensus/calibration/hosted/reviewer/market gates. Keep `isDraft=true`; do not merge.

- [ ] **Step 10: Final repository truth check**

Run:

```bash
git status --short --branch
git rev-list --left-right --count origin/codex/personal-research-mode-mvp...HEAD
gh pr view 113 --json state,isDraft,mergeable,headRefOid,statusCheckRollup,url
```

Expected: clean worktree, `0 0` branch alignment, PR open/draft, exact head equal to local HEAD, and no generated artifacts staged.
