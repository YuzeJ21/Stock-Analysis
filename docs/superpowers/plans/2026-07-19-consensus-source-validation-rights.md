# Consensus Source Validation Rights Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace caller-declared consensus source rights with exact registry-derived commercial rights and independent Revenue/EPS scope evidence while preserving technically valid research review.

**Architecture:** Keep schema/comparability validation in `earnings_consensus_sources.py`, inject or load the existing immutable source-rights registry, and add immutable row-level commercial reviews plus aggregate counts to the result. Commercial evidence never changes technical acceptance, candidate-context classification, or the non-writing boundary.

**Tech Stack:** Python 3.12, frozen dataclasses, PyYAML-backed `commercial_source_rights`, pytest, Make product gates, Git/GitHub draft PR workflow.

## Global Constraints

- Research-only; no investment advice, broker integration, order routing, auto-trading, direct buy/sell instructions, or post-earnings price prediction.
- Do not add, infer, or approve a provider, entitlement, source-rights record, consensus value, source, timestamp, or recommendation.
- Candidate context cannot modify deterministic forecasts or become trusted evidence.
- Keep technical acceptance, historical availability, exact-source rights, Revenue scope, EPS scope, nowcast readiness, backtesting, and calibration independent.
- Historical rows are reviewable evidence only; they are not activated evidence or nowcast readiness.
- Do not run `make readiness` or create/stage CSV, JSON, report, sample-report, screenshot, browser timing, or bytecode churn.
- Stage exact intentional product/code/docs/test files only; never use `git add -A`.

---

### Task 1: Registry-derived validator contract

**Files:**
- Modify: `tests/test_earnings_consensus_sources.py`
- Modify: `src/earnings_consensus_sources.py`

**Interfaces:**
- Consumes: `commercial_eligibility(registry: Mapping[str, SourceRights], source_id: str) -> CommercialEligibility` and `load_source_rights_registry() -> Mapping[str, SourceRights]`.
- Produces: `SourceCommercialReview` and `validate_source_rows(provider, rows, *, rights_registry=None) -> SourceValidationResult` with registry-derived aggregate evidence.

- [ ] **Step 1: Add test-only exact-source rights fixtures**

Add a `_rights_registry` helper using `build_source_rights_registry` with explicit `source_id`, `commercial_use`, and `supported_fields`. Add `_current_row` and `_historical_row` helpers that populate real validator fields but use only synthetic values and references.

```python
def _rights_registry(*, source_id="licensed_consensus", commercial_use="approved", supported_fields=None):
    return build_source_rights_registry(
        [{
            "source_id": source_id,
            "display_name": "Licensed consensus fixture",
            "permitted_use": "test_only",
            "commercial_use": commercial_use,
            "redistribution": "test_only",
            "storage_limits": "temporary in-memory tests only",
            "attribution": "fixture",
            "rate_limits": "not applicable",
            "authentication": "not applicable",
            "expected_freshness": "fixture cutoff",
            "supported_fields": supported_fields or ["revenue_consensus", "eps_consensus"],
            "fallback_priority": 1,
        }]
    )
```

- [ ] **Step 2: Write failing tests for default fail-closed evidence and removed caller approval**

Update existing calls to omit `rights_status`. Assert that a technically valid Alpha Vantage current-only row remains accepted candidate context while its exact source is unknown, both populated scopes are missing, `commercial_ready_count == 0`, and `auto_apply is False`. Add a test proving `rights_status=` is no longer accepted by the function signature.

```python
assert result.state == "candidate_context_only"
assert result.rights_status == "unknown_source"
assert result.commercial_review_rows[0].missing_supported_fields == ("revenue_consensus", "eps_consensus")
assert result.commercial_evidence_ready is False
with pytest.raises(TypeError, match="rights_status"):
    validate_source_rows("alpha_vantage", (), rights_status="approved_for_project_use")
```

- [ ] **Step 3: Write failing tests for historical state and metric-specific scope**

Assert that a technically valid point-in-time row is `historical_evidence_reviewable`. Cover approved Revenue-only, EPS-only, and mixed rows; a source approved only for Revenue must report EPS as the sole missing scope for a mixed row. Assert commercial counts and ordered row numbers.

```python
assert historical.state == "historical_evidence_reviewable"
assert revenue_only.commercial_review_rows[0].required_supported_fields == ("revenue_consensus",)
assert eps_only.commercial_review_rows[0].required_supported_fields == ("eps_consensus",)
assert mixed.commercial_review_rows[0].missing_supported_fields == ("eps_consensus",)
assert mixed.commercial_rights_approved is True
assert mixed.commercial_review_required_count == 1
```

- [ ] **Step 4: Write a failing exact composite-source test**

Inject a registry that approves `licensed_consensus` and validate a row whose provider is `licensed_consensus + reviewed_csv`. Assert `unknown_source`, missing populated scopes, and no inferred identity.

- [ ] **Step 5: Run the focused tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_earnings_consensus_sources.py -q
```

Expected: failures because the old function still requires `rights_status`, lacks registry-derived fields, and returns `historical_evidence_ready`.

- [ ] **Step 6: Add immutable commercial-review result types**

Import `SourceRights`, `commercial_eligibility`, and `load_source_rights_registry`. Add:

```python
@dataclass(frozen=True)
class SourceCommercialReview:
    row_number: int
    required_supported_fields: tuple[str, ...]
    missing_supported_fields: tuple[str, ...]
    commercial_evidence_ready: bool
    commercial_blockers: tuple[str, ...]
```

Extend `SourceValidationResult` with `commercial_rights_approved`, `commercial_ready_count`, `commercial_review_required_count`, `commercial_evidence_ready`, `commercial_blockers`, and `commercial_review_rows`. Keep `rights_status` registry-derived and `auto_apply=False`.

- [ ] **Step 7: Implement independent exact-source commercial evidence**

Change the function signature to optional injected rights registry, normalize the provider once, and calculate the source decision once. For every technically accepted row, derive populated metric scopes in stable order, exact-record missing scopes, and stable blockers.

```python
source_id = str(provider).strip().lower()
registry = load_source_rights_registry() if rights_registry is None else rights_registry
rights = commercial_eligibility(registry, source_id)
rights_record = registry.get(source_id)
supported_fields = set(rights_record.supported_fields) if rights_record else set()
required_supported_fields = tuple(
    field for field in ("revenue_consensus", "eps_consensus")
    if str(row.get(field) or "").strip()
)
missing_supported_fields = tuple(
    field for field in required_supported_fields if field not in supported_fields
)
```

Technical reasons must no longer include source rights. Count only technically accepted rows in the row-level commercial evidence. Aggregate readiness is true only when at least one row is accepted and every accepted row is commercially ready. Return `historical_evidence_reviewable` when any accepted point-in-time row exists.

- [ ] **Step 8: Run the focused tests and verify GREEN**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_earnings_consensus_sources.py tests/test_earnings_consensus_collector.py -q
```

Expected: all source-validator and collector contract tests pass.

- [ ] **Step 9: Review the production diff**

Confirm there is no provider call, file writer, source-rights config change, readiness mutation, automatic apply path, or generated artifact change. Run `git diff --check`.

### Task 2: Product contract documentation and release verification

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/EARNINGS_NOWCAST_PILOT.md`
- Modify: `docs/DATA_STRATEGY.md`
- Modify: `docs/METHODOLOGY.md`
- Modify: `docs/PROVENANCE_CONTRACT.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`

**Interfaces:**
- Consumes: the verified `SourceValidationResult` evidence contract from Task 1.
- Produces: truthful product-stage, boundary, continuation-anchor, and next-step documentation for draft PR #113.

- [ ] **Step 1: Document the completed local slice without activation claims**

Add ROADMAP implemented item 31 and maturity commentary. State that upstream source rows now use exact registry-derived rights and row-specific Revenue/EPS scope while technical acceptance and candidate context remain independent. Explicitly state that the checked-in registry still unlocks no prospective consensus source, no real snapshot was added, and nowcast/calibration readiness did not change.

- [ ] **Step 2: Update method, provenance, strategy, and pilot guidance**

Document these exact boundaries:

- caller labels cannot grant rights;
- invalid technical rows do not enter commercial-ready counts;
- `historical_evidence_reviewable` is not activation;
- composite IDs remain unknown exact sources;
- commercial evidence readiness is not payload approval, collection, history depth, nowcast readiness, backtesting, or calibration.

- [ ] **Step 3: Update the continuation contract**

Add the committed design/plan lineage anchor, add the upstream validation capability and its truthful boundary, retain the stale-readiness no-write instruction, and set the exact next executable local lane from the re-audited roadmap. Do not change external dependency classifications without new evidence.

- [ ] **Step 4: Run focused and full verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_earnings_consensus_sources.py tests/test_earnings_consensus_collector.py -q
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests -q
```

Expected: zero test failures; the existing third-party `dateutil` deprecation warning may remain.

- [ ] **Step 5: Run every required non-writing product gate**

Run:

```bash
make dashboard-smoke
make dashboard-render-smoke
make public-wording-check
make public-check
make commercial-beta-check
make commercial-release-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
```

Expected: all executable gates pass; pilot readiness truthfully reports the known stale saved readiness rather than regenerating it; no generated artifact changes appear.

- [ ] **Step 6: Stage exact files and run staged hygiene**

Stage only the source module, its test, and the six named product documents. The design and plan have separate reviewed commits. Run `make staged-hygiene-check` and `git diff --cached --check`. Expected: no staged generated CSV/JSON/report/sample-report/screenshot/timing churn.

- [ ] **Step 7: Commit, push, and update draft PR #113**

Commit the coherent implementation/docs slice with message `Derive consensus source validation rights`, push only `codex/personal-research-mode-mvp`, confirm 0/0 remote alignment, and post the verified scope, tests, truthful boundaries, generated-artifact exclusion, external dependency status, and next executable step to PR #113. Keep the PR open and draft.

- [ ] **Step 8: Re-audit the handoff state**

Verify clean status, pushed HEAD, draft PR state, generated-artifact hygiene, current external dependency ledger, review safety, and that the overall `/goal` remains active because hosted, reviewer, real-source, evidence-depth, backtesting, calibration, and operating gates remain incomplete or unproven.
