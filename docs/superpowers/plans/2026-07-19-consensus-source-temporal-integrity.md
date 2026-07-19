# Consensus Source Temporal Integrity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require an explicit review cutoff, valid history scope, and ordered source timestamps before consensus rows can become candidate or historical-reviewable evidence.

**Architecture:** Parse one mandatory cutoff before row processing, keep one ordered row-validation path, and add the normalized cutoff to the immutable result. Temporal failures remain technical rejections; exact-source rights and Revenue/EPS scope are calculated only for technically accepted rows and remain independent.

**Tech Stack:** Python 3.12, frozen dataclasses, existing UTC timestamp parser, pytest, Make product gates, Git/GitHub draft PR workflow.

## Global Constraints

- Research-only; no investment advice, broker integration, order routing, auto-trading, direct buy/sell instructions, or post-earnings price prediction.
- Every accepted source row must prove `snapshot_at <= retrieved_at <= review_cutoff`.
- `history_scope` must be exactly `current_only` or `point_in_time`; unknown values cannot become candidate context.
- Keep technical acceptance, source rights, Revenue scope, EPS scope, historical availability, collection, nowcast readiness, backtesting, and calibration independent.
- Candidate context cannot modify deterministic forecasts or become trusted evidence.
- Do not run `make readiness` or create/stage CSV, JSON, report, sample-report, screenshot, browser timing, or bytecode churn.
- Stage exact intentional product/code/docs/test files only; never use `git add -A`.

---

### Task 1: Mandatory source-row temporal contract

**Files:**
- Modify: `tests/test_earnings_consensus_sources.py`
- Modify: `src/earnings_consensus_sources.py`

**Interfaces:**
- Consumes: `parse_utc_timestamp(value, *, label) -> datetime` and the existing registry-derived commercial-review contract.
- Produces: `validate_source_rows(provider, rows, *, as_of, rights_registry=None) -> SourceValidationResult` with normalized `review_cutoff`.

- [ ] **Step 1: Update valid test calls to use one explicit cutoff**

Add:

```python
REVIEW_CUTOFF = "2026-07-18T06:00:00Z"
```

Pass `as_of=REVIEW_CUTOFF` to every valid or row-focused validator call. Keep the caller-rights-label signature test focused on `rights_status` by also supplying `as_of`.

- [ ] **Step 2: Write failing cutoff contract tests**

Assert that a valid result exposes `review_cutoff == REVIEW_CUTOFF`, and invalid cutoff input raises before reviewing rows:

```python
with pytest.raises(ValueError, match="review cutoff"):
    validate_source_rows("reviewed_csv", (), as_of="not-a-cutoff")
```

- [ ] **Step 3: Write failing explicit-scope tests**

Parametrize missing and unknown values and assert rejection, zero accepted rows, `still_blocked`, and no commercial-review rows:

```python
@pytest.mark.parametrize("scope", ["", "historical", "latest"])
def test_source_rows_require_an_explicit_supported_history_scope(scope):
    result = validate_source_rows(
        "licensed_consensus",
        [_current_row(history_scope=scope)],
        as_of=REVIEW_CUTOFF,
        rights_registry=_rights_registry(),
    )
    assert "history_scope must be current_only or point_in_time" in result.rejected_rows[0]["reason"]
    assert result.commercial_review_rows == ()
```

- [ ] **Step 4: Write failing ordering and cutoff tests**

Add separate tests for snapshot after retrieval, snapshot after cutoff, and retrieval after cutoff. Assert the field-specific technical reason and that approved source rights remain source-level evidence while no row becomes commercially ready.

```python
result = validate_source_rows(
    "licensed_consensus",
    [_current_row(snapshot_at="2026-07-18T05:00:02Z")],
    as_of=REVIEW_CUTOFF,
    rights_registry=_rights_registry(),
)
assert "snapshot_at cannot be after retrieved_at" in result.rejected_rows[0]["reason"]
assert result.commercial_rights_approved is True
assert result.commercial_ready_count == 0
```

- [ ] **Step 5: Write failing equality and mixed-batch tests**

Prove equality at retrieval/cutoff is allowed. In a two-row batch with the first row after cutoff and the second valid, assert one rejection, one accepted candidate, and `commercial_review_rows[0].row_number == 2`.

- [ ] **Step 6: Run the focused tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_earnings_consensus_sources.py -q
```

Expected: failures because `as_of` is not accepted, `review_cutoff` is absent, invalid scopes are still candidates, and reversed/future timestamps are accepted.

- [ ] **Step 7: Add the normalized cutoff to the result**

Add `review_cutoff: str` to `SourceValidationResult`. Change the signature to require `as_of`, parse it once, and normalize UTC:

```python
cutoff = parse_utc_timestamp(as_of, label="review cutoff")
review_cutoff = cutoff.isoformat().replace("+00:00", "Z")
```

Return `review_cutoff` for every result, including a result whose rows are all rejected.

- [ ] **Step 8: Implement explicit scope and row-time validation**

Before `ConsensusSnapshot` construction, reject an unsupported scope. Parse the two row timestamps into a dictionary only when present; after successful parsing enforce ordering and cutoff:

```python
if scope not in {"current_only", "point_in_time"}:
    reasons.append("history_scope must be current_only or point_in_time")

parsed_timestamps = {}
for timestamp in ("snapshot_at", "retrieved_at"):
    if str(row.get(timestamp) or "").strip():
        try:
            parsed_timestamps[timestamp] = parse_utc_timestamp(row[timestamp], label=timestamp)
        except ValueError as exc:
            reasons.append(str(exc))

snapshot_at = parsed_timestamps.get("snapshot_at")
retrieved_at = parsed_timestamps.get("retrieved_at")
if snapshot_at is not None and retrieved_at is not None and snapshot_at > retrieved_at:
    reasons.append("snapshot_at cannot be after retrieved_at")
for field, timestamp in parsed_timestamps.items():
    if timestamp > cutoff:
        reasons.append(f"{field} is after review cutoff")
```

Do not add a commercial review for any row with temporal or other technical reasons.

- [ ] **Step 9: Run focused tests and verify GREEN**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_earnings_consensus_sources.py tests/test_earnings_consensus_collector.py -q
```

Expected: all source-validator and collector tests pass.

- [ ] **Step 10: Review the production diff**

Confirm there is no provider call, file writer, source-rights edit, ledger mutation, readiness mutation, or automatic apply path. Run `git diff --check`.

### Task 2: Evidence-governance documentation and release verification

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/EARNINGS_NOWCAST_PILOT.md`
- Modify: `docs/DATA_STRATEGY.md`
- Modify: `docs/METHODOLOGY.md`
- Modify: `docs/PROVENANCE_CONTRACT.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`

**Interfaces:**
- Consumes: the verified mandatory-cutoff `SourceValidationResult` contract from Task 1.
- Produces: truthful roadmap, method, provenance, pilot, continuation, and draft-PR evidence for the temporal boundary.

- [ ] **Step 1: Add the implemented roadmap item and maturity boundary**

Add item 32 stating that source validation requires explicit scope and `snapshot_at <= retrieved_at <= review_cutoff`. State that this improves leakage resistance and review reliability but does not supply a provider, real snapshot, source rights, history depth, readiness, calibration, reviewers, or market validation.

- [ ] **Step 2: Update pilot, strategy, method, and provenance contracts**

Document that both candidate and historical source rows require the same cutoff truth; invalid scopes and reversed/future timestamps are technical rejections; only accepted rows enter commercial review. Make clear that cutoff passage does not prove publication availability, payload correctness, rights, freshness, collection, activation, backtesting, or calibration.

- [ ] **Step 3: Update the continuation contract**

Add the committed design/plan lineage anchor, implemented capability, truthful boundary, and Stage 2 review instruction. Preserve the stale-readiness no-write instruction and all external dependency classifications.

- [ ] **Step 4: Run focused and full verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_earnings_consensus_sources.py tests/test_earnings_consensus_collector.py -q
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests -q
```

Expected: zero failures; the existing third-party `dateutil` deprecation warning may remain.

- [ ] **Step 5: Run every required non-writing product gate**

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

Expected: executable gates pass; pilot readiness still reports stale saved readiness; no readiness build or generated artifact appears.

- [ ] **Step 6: Stage exact files and verify hygiene**

Stage only the source module, its test, the six named product documents, and this plan if corrected during execution. Run `make staged-hygiene-check` and `git diff --cached --check`. Expected: zero staged generated CSV/JSON/report/sample-report/screenshot/timing churn.

- [ ] **Step 7: Commit, push, and update draft PR #113**

Commit with message `Enforce consensus source review cutoff`, push only `codex/personal-research-mode-mvp`, confirm 0/0 remote alignment, and post verified scope, red-green evidence, full gates, truthful boundaries, generated-artifact exclusion, unchanged dependencies, and the next executable step to PR #113. Keep it open and draft.

- [ ] **Step 8: Re-audit the handoff state**

Verify clean status, pushed HEAD, draft PR state, artifact hygiene, stale readiness, review safety, remaining stage gates, and that the overall goal remains active.
