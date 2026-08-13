# Commercial Field-Scope Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give consensus source validation and prospective collection one immutable exact-source commercial-rights and required-field scope decision without changing either consumer's public behavior.

**Architecture:** Add a domain-neutral frozen result and pure function to the existing source-rights module. Keep consumer-specific blocker strings, technical states, cutoff/lineage checks, preview states, and write authorization in the two consensus modules while replacing their duplicate registry and missing-field calculations.

**Tech Stack:** Python 3.12, frozen dataclasses, immutable source-rights registry, pytest, Make product gates, Git/GitHub draft PR workflow.

## Global Constraints

- Research-only; no investment advice, broker integration, order routing, auto-trading, direct buy/sell instructions, or post-earnings price prediction.
- Preserve exact source IDs; do not split composite labels, infer aliases, or borrow rights.
- Keep commercial rights and required-field scope independently visible.
- Keep technical validity, candidate/history state, collection, Revenue, EPS, write authorization, nowcast readiness, backtesting, and calibration independent.
- Preserve existing collector and validator result fields, blocker strings, and state transitions.
- Do not modify price, DCF, fundamentals, cash-generation, or other domain evidence models in this slice.
- Do not run `make readiness` or create/stage CSV, JSON, report, sample-report, screenshot, browser timing, or bytecode churn.
- Stage exact intentional product/code/docs/test files only; never use `git add -A`.

---

### Task 1: Pure commercial field-scope decision

**Files:**
- Modify: `tests/test_commercial_source_rights.py`
- Modify: `src/commercial_source_rights.py`

**Interfaces:**
- Consumes: `commercial_eligibility(registry, source_id) -> CommercialEligibility` and exact `SourceRights.supported_fields`.
- Produces: `review_commercial_field_scope(registry, source_id, required_fields) -> CommercialFieldScopeReview`.

- [ ] **Step 1: Write failing approved and missing-scope tests**

Use the checked-in immutable registry. Assert stable supplied order, exact missing fields, and combined readiness:

```python
complete = module.review_commercial_field_scope(
    _registry(), "sec_companyfacts", ("revenue", "shares_outstanding")
)
missing = module.review_commercial_field_scope(
    _registry(), "sec_companyfacts", ("revenue", "free_cash_flow")
)
assert complete.required_supported_fields == ("revenue", "shares_outstanding")
assert complete.missing_supported_fields == ()
assert complete.commercial_evidence_ready is True
assert missing.missing_supported_fields == ("free_cash_flow",)
assert missing.commercial_rights_approved is True
assert missing.commercial_evidence_ready is False
```

- [ ] **Step 2: Write failing independence and exact-source tests**

Assert that `yfinance` has supported `prices` scope but unverified rights, and a composite source remains unknown with every required field missing:

```python
unverified = module.review_commercial_field_scope(_registry(), "yfinance", ("prices",))
unknown = module.review_commercial_field_scope(
    _registry(), "sec_companyfacts + yfinance", ("revenue", "prices")
)
assert unverified.missing_supported_fields == ()
assert unverified.rights_status == "commercial_rights_unverified"
assert unverified.commercial_evidence_ready is False
assert unknown.rights_status == "unknown_source"
assert unknown.missing_supported_fields == ("revenue", "prices")
```

- [ ] **Step 3: Write failing immutability and caller-contract tests**

Assert an approved empty-field decision is rights-ready, the result is frozen, and blank or duplicate required fields raise:

```python
rights_only = module.review_commercial_field_scope(_registry(), "sec_companyfacts", ())
assert rights_only.commercial_evidence_ready is True
with pytest.raises(FrozenInstanceError):
    rights_only.commercial_evidence_ready = False
with pytest.raises(ValueError, match="non-empty unique strings"):
    module.review_commercial_field_scope(_registry(), "sec_companyfacts", ("revenue", ""))
with pytest.raises(ValueError, match="non-empty unique strings"):
    module.review_commercial_field_scope(_registry(), "sec_companyfacts", ("revenue", "revenue"))
```

- [ ] **Step 4: Run the source-rights tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_commercial_source_rights.py -q
```

Expected: failures because `CommercialFieldScopeReview` and `review_commercial_field_scope` do not exist.

- [ ] **Step 5: Add the frozen result**

Add after `CommercialEligibility`:

```python
@dataclass(frozen=True)
class CommercialFieldScopeReview:
    source_id: str
    rights_status: str
    commercial_rights_approved: bool
    required_supported_fields: tuple[str, ...]
    missing_supported_fields: tuple[str, ...]
    commercial_evidence_ready: bool
```

- [ ] **Step 6: Implement the pure exact-source review**

Add after `commercial_eligibility`:

```python
def review_commercial_field_scope(
    registry: Mapping[str, SourceRights],
    source_id: str,
    required_fields: Sequence[str],
) -> CommercialFieldScopeReview:
    normalized_source_id = str(source_id or "").strip()
    normalized_fields = tuple(str(field or "").strip() for field in required_fields)
    if any(not field for field in normalized_fields) or len(set(normalized_fields)) != len(normalized_fields):
        raise ValueError("required fields must be non-empty unique strings")
    rights = commercial_eligibility(registry, normalized_source_id)
    record = registry.get(normalized_source_id)
    supported_fields = set(record.supported_fields) if record is not None else set()
    missing_fields = tuple(field for field in normalized_fields if field not in supported_fields)
    return CommercialFieldScopeReview(
        source_id=normalized_source_id,
        rights_status=rights.status,
        commercial_rights_approved=rights.allowed,
        required_supported_fields=normalized_fields,
        missing_supported_fields=missing_fields,
        commercial_evidence_ready=rights.allowed and not missing_fields,
    )
```

- [ ] **Step 7: Run the source-rights tests and verify GREEN**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_commercial_source_rights.py -q
```

Expected: all source-rights tests pass.

### Task 2: Migrate consensus consumers without behavior changes

**Files:**
- Modify: `src/earnings_consensus_collector.py`
- Modify: `src/earnings_consensus_sources.py`
- Test: `tests/test_earnings_consensus_collector.py`
- Test: `tests/test_earnings_consensus_sources.py`

**Interfaces:**
- Consumes: `review_commercial_field_scope(...) -> CommercialFieldScopeReview` from Task 1.
- Produces: unchanged `CollectionPreview`, `SourceCommercialReview`, and `SourceValidationResult` public behavior.

- [ ] **Step 1: Refactor collector commercial evidence**

Replace the collector's direct `commercial_eligibility`, exact-record lookup, supported-field set, and missing-field calculation with one shared review call. Map the shared fields into existing blocker strings and `CollectionPreview`:

```python
commercial_review = review_commercial_field_scope(
    rights_registry, proposed.source, required_supported_fields
)
if not commercial_review.commercial_rights_approved:
    commercial_blockers.append(f"commercial_rights:{commercial_review.rights_status}")
commercial_blockers.extend(
    f"registered_consensus_scope_missing:{field}"
    for field in commercial_review.missing_supported_fields
)
```

Do not change technical `write_allowed`, `commercial_write_allowed`, state, reason, identity, batch, or mutation behavior.

- [ ] **Step 2: Refactor source-validator commercial evidence**

Use an empty-field shared review for source-level rights. For each technically accepted row, pass its populated Revenue/EPS tuple to the shared review and map the result into `SourceCommercialReview`. Preserve all cutoff, scope, timestamp, schema, comparability, state, count, row-number, and aggregate behavior.

- [ ] **Step 3: Run consumer regression tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_commercial_source_rights.py tests/test_earnings_consensus_sources.py tests/test_earnings_consensus_collector.py -q
```

Expected: all source-rights, source-validator, and collector tests pass with unchanged public evidence.

- [ ] **Step 4: Review duplication removal**

Use `rg` and the diff to confirm both consensus modules call `review_commercial_field_scope` and no longer independently read `supported_fields` or calculate `missing_supported_fields`. Confirm their domain-specific blocker strings remain local. Run `git diff --check`.

### Task 3: Documentation and release verification

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/DATA_STRATEGY.md`
- Modify: `docs/EARNINGS_NOWCAST_PILOT.md`
- Modify: `docs/METHODOLOGY.md`
- Modify: `docs/PROVENANCE_CONTRACT.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`

**Interfaces:**
- Consumes: the verified shared field-scope decision and unchanged consumer evidence.
- Produces: truthful roadmap, methodology, provenance, continuation, and PR evidence for the reliability slice.

- [ ] **Step 1: Document the implemented roadmap item**

Add item 33 and maturity commentary: both consensus paths now share one exact-source rights/field-scope decision, reducing semantic drift without changing readiness or providing source evidence. State explicitly that price, DCF, fundamentals, and cash-generation domain reviews remain separate.

- [ ] **Step 2: Update source strategy, pilot, method, and provenance**

Document the shared decision fields and the retained separation: consumer technical states and blocker copy remain local; registry metadata cannot prove payloads, timestamps, comparability, review intent, collection, activation, backtesting, or calibration.

- [ ] **Step 3: Update the continuation contract**

Add the committed design/plan lineage anchor, shared-decision capability, truthful boundary, and Stage 2 instruction. Preserve stale-readiness, external dependency, and no-generated-write rules.

- [ ] **Step 4: Run focused and full verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_commercial_source_rights.py tests/test_earnings_consensus_sources.py tests/test_earnings_consensus_collector.py -q
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests -q
```

Expected: zero failures; the existing third-party `dateutil` warning may remain.

- [ ] **Step 5: Run required non-writing product gates**

Run:

```bash
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

Expected: executable gates pass, pilot readiness remains stale, and generated churn remains zero.

- [ ] **Step 6: Stage exact files and verify hygiene**

Stage only the three source modules, the three named test modules if changed, the six named product documents, and this plan if corrected during execution. Run `make staged-hygiene-check` and `git diff --cached --check`.

- [ ] **Step 7: Commit, push, and update draft PR #113**

Commit with message `Unify consensus commercial evidence review`, push only `codex/personal-research-mode-mvp`, confirm 0/0 alignment, and post verified scope, red-green evidence, full gates, unchanged outputs, external dependencies, and next step to PR #113. Keep it draft.

- [ ] **Step 8: Re-audit the handoff state**

Verify clean status, pushed HEAD, draft PR state, artifact hygiene, stale readiness, remaining stage gates, review safety, and active overall goal.
