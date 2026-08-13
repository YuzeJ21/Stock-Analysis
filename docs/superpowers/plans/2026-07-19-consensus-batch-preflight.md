# Prospective Consensus Batch Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make prospective consensus preview and record evaluate one ordered whole-batch contract so a later deterministic rejection cannot leave earlier proposed rows appended.

**Architecture:** Add an immutable batch preview composed from the existing row preview and an in-memory virtual ledger. Add one batch append function that runs preflight once, selects the research/commercial gate without coupling their evidence states, and writes all accepted rows through one append handle only after the whole batch passes. Keep the single-row API by delegating it to the batch path.

**Tech Stack:** Python 3.12, frozen dataclasses, standard-library CSV/JSON/path handling, pytest, Make-based repository gates.

## Global Constraints

- Research-only; no investment advice, broker integration, order routing, auto-trading, direct buy/sell instructions, or post-earnings price prediction.
- No provider fetch, source-rights edit, readiness rebuild, or repository CSV/JSON/report/sample-report/screenshot/timing write.
- Technical append eligibility, commercial rights, Revenue scope, EPS scope, actuals, consensus, backtesting, and calibration remain independent.
- Input order is authoritative; do not sort rows, infer providers, repair revision chains, invent supersession, or select a conflicting row.
- Promise deterministic preflight all-or-none behavior only; do not claim crash-safe transactionality or concurrent-writer locking.
- Use temporary pytest paths for every write test.
- Stage exact intentional files only; never use `git add -A`.

---

### Task 1: Prove the current partial-write and preview mismatch

**Files:**
- Modify: `tests/test_earnings_consensus_collector.py`
- Test: `tests/test_earnings_consensus_collector.py`

**Interfaces:**
- Consumes: existing `FIELDS`, `ProspectiveConsensusRecord`, `main(...)`, and `load_snapshots(...)`.
- Produces: failing behavioral evidence for whole-batch preview and record.

- [ ] **Step 1: Add temporary CSV and revision helpers**

Add `csv`, `json`, and `asdict` imports, import `FIELDS` and `main`, and add helpers equivalent to:

```python
def _write_records(path: Path, records: tuple[ProspectiveConsensusRecord, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(asdict(record) for record in records)


def _revision(record: ProspectiveConsensusRecord, *, snapshot_id: str = "snap-002") -> ProspectiveConsensusRecord:
    return replace(
        record,
        snapshot_id=snapshot_id,
        snapshot_at="2026-07-25T05:00:00Z",
        retrieved_at="2026-07-25T05:00:01Z",
        source_ref=f"file://reviewed/{record.ticker}/{record.fiscal_period}/20260725",
        revenue_consensus="102",
        supersedes_snapshot_id=record.snapshot_id,
    )
```

- [ ] **Step 2: Add a failing record test for a later duplicate**

```python
def test_record_preflights_whole_batch_before_any_append(tmp_path: Path):
    input_path = tmp_path / "input.csv"
    ledger = tmp_path / "ledger.csv"
    first = _record()
    _write_records(input_path, (first, first))

    with pytest.raises(ValueError, match="duplicate"):
        main(["record", "--input", str(input_path), "--ledger", str(ledger), "--confirm-reviewed"])

    assert not ledger.exists()
```

- [ ] **Step 3: Add failing preview tests for virtual-ledger lineage**

Capture stdout with `capsys`, parse JSON, and assert:

```python
payload = json.loads(capsys.readouterr().out)
assert payload.get("state") == "reviewable_batch"
assert [row["state"] for row in payload["rows"]] == ["reviewable_new", "reviewable_revision"]
assert payload["technical_write_allowed"] is True
```

Add a second input containing the same row twice and assert the later row is `duplicate`, `state` is `rejected_batch`, and `technical_write_allowed` is false.

- [ ] **Step 4: Add a failing empty-input record test**

Write only the header and assert `main(record...)` raises `ValueError` containing `empty_batch` while the destination and its missing parent remain absent.

- [ ] **Step 5: Run the focused tests and verify RED**

Run:

```bash
python3 -m pytest tests/test_earnings_consensus_collector.py -q
```

Expected: assertion failures proving current preview misses intra-batch lineage/conflicts, record leaves a partial ledger, and empty record is silently accepted.

---

### Task 2: Add the pure ordered batch preview

**Files:**
- Modify: `src/earnings_consensus_collector.py`
- Modify: `tests/test_earnings_consensus_collector.py`

**Interfaces:**
- Consumes: `CollectionPreview`, `preview_collection(...)`, `SourceRights`, and the immutable source-rights registry.
- Produces: `BatchCollectionPreview` and `preview_collection_batch(...)`.

- [ ] **Step 1: Add the immutable batch result**

```python
@dataclass(frozen=True)
class BatchCollectionPreview:
    mode: str
    write_performed: bool
    state: str
    row_count: int
    reviewable_count: int
    technical_write_allowed: bool
    commercial_evidence_ready: bool
    commercial_write_allowed: bool
    technical_blockers: tuple[str, ...]
    commercial_blockers: tuple[str, ...]
    rows: tuple[CollectionPreview, ...]
```

- [ ] **Step 2: Implement ordered virtual-ledger evaluation**

Add:

```python
def preview_collection_batch(
    existing: Sequence[ProspectiveConsensusRecord],
    proposed: Sequence[ProspectiveConsensusRecord],
    *,
    as_of: str | None = None,
    cooldown_hours: int = 0,
    rights_registry: Mapping[str, SourceRights] | None = None,
) -> BatchCollectionPreview:
```

Resolve the registry once. For every one-based row position, call `preview_collection(...)` with `as_of` when supplied or that row's `retrieved_at`. Append technically reviewable rows to a mutable virtual ledger. Build blockers as:

```python
f"row_{index}:{preview.state}:{preview.reason}"
f"row_{index}:{blocker}"
```

For no proposed rows, return `state="empty_batch"`, false gates, and `("batch:empty_input",)` technical and commercial blockers. Otherwise return `reviewable_batch` only when every row is technically writeable, and compute commercial evidence independently across every row.

- [ ] **Step 3: Route CLI preview through the batch function**

Replace the independent list comprehension with:

```python
result = preview_collection_batch(existing, proposed, as_of=args.as_of)
print(json.dumps(asdict(result), indent=2, sort_keys=True))
```

- [ ] **Step 4: Add and verify reversed-revision behavior**

Preview a revision before its target and assert `rejected_batch`, first-row reason contains `supersedes_snapshot_id does not exist`, and input order is unchanged in the returned row results.

- [ ] **Step 5: Run focused tests and verify the preview tests are GREEN**

Run:

```bash
python3 -m pytest tests/test_earnings_consensus_collector.py -q
```

Expected: preview/empty tests pass; the partial-write test still fails until Task 3.

---

### Task 3: Add one preflighted batch append path

**Files:**
- Modify: `src/earnings_consensus_collector.py`
- Modify: `tests/test_earnings_consensus_collector.py`

**Interfaces:**
- Consumes: `preview_collection_batch(...)` and `commercial_mode_enabled()`.
- Produces: `append_reviewed_batch(...)`; `append_reviewed_snapshot(...)` delegates to it.

- [ ] **Step 1: Add failing API tests for research and commercial batches**

Use `getattr(collector, "append_reviewed_batch", None)` and first assert it is callable so the pre-implementation run fails as an assertion rather than a collection error. Then prove:

- an existing ledger remains byte-identical when a later same-period row is rejected;
- a later unregistered commercial row leaves a missing destination parent absent;
- a valid new row followed by its explicit revision appends both rows in order in research mode;
- the same ordered batch appends in commercial mode with an injected approved registry;
- an empty batch is rejected without filesystem mutation.

- [ ] **Step 2: Run the focused tests and verify RED for the missing batch API**

Run:

```bash
python3 -m pytest tests/test_earnings_consensus_collector.py -q
```

Expected: failures identify the missing `append_reviewed_batch` behavior.

- [ ] **Step 3: Implement `append_reviewed_batch(...)`**

Use this signature:

```python
def append_reviewed_batch(
    path: Path | str,
    records: Sequence[ProspectiveConsensusRecord],
    *,
    confirm_reviewed: bool,
    commercial_mode: bool | None = None,
    rights_registry: Mapping[str, SourceRights] | None = None,
) -> Path:
```

Convert records to a tuple, validate confirmation, load the existing ledger and registry once, run batch preview with `as_of=None`, reject technical blockers first, resolve commercial mode once, reject commercial blockers second, then create the parent and append every row using one `csv.DictWriter` and `writerows(...)` call.

Use stable errors:

```python
raise ValueError(f"{preview.state}: " + "; ".join(preview.technical_blockers))
raise ValueError("batch_commercial_evidence_review_required: " + "; ".join(preview.commercial_blockers))
```

- [ ] **Step 4: Delegate single-row append and CLI record**

Make `append_reviewed_snapshot(...)` call `append_reviewed_batch(path, (record,), ...)`. Replace the CLI record loop with one `append_reviewed_batch(...)` call over the loaded tuple.

- [ ] **Step 5: Run focused collector and rights tests and verify GREEN**

Run:

```bash
python3 -m pytest tests/test_earnings_consensus_collector.py tests/test_earnings_consensus_sources.py tests/test_commercial_source_rights.py -q
```

Expected: all focused tests pass with only the existing dependency warning.

---

### Task 4: Update durable operating contracts

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/EARNINGS_NOWCAST_PILOT.md`
- Modify: `docs/DATA_STRATEGY.md`
- Modify: `docs/METHODOLOGY.md`
- Modify: `docs/PROVENANCE_CONTRACT.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`

**Interfaces:**
- Consumes: verified batch preview/record behavior.
- Produces: roadmap item 30 and a continuation anchor for this design/plan lineage.

- [ ] **Step 1: Document the preview/record convergence**

State that preview simulates proposed rows in input order against a virtual append-only ledger and record uses that exact result before mutation.

- [ ] **Step 2: Preserve independent evidence and truthful limits**

State that technical and commercial batch gates remain independent; research mode does not satisfy Commercial Research activation; no source, rights, snapshot, readiness, calibration, hosted, reviewer, or market gate changed.

- [ ] **Step 3: Document the transaction boundary**

State explicitly that deterministic preflight prevents known later rejections from causing partial writes but does not provide concurrent-writer locking or crash-safe filesystem transactions.

- [ ] **Step 4: Update the continuation prompt**

Add the design/plan commit anchor, implemented capability, truth boundary, and exact next-stage meaning without changing the external dependency classifications.

- [ ] **Step 5: Run wording and whitespace checks**

Run:

```bash
make public-wording-check
git diff --check
```

Expected: both pass.

---

### Task 5: Full verification, exact delivery, and clean-state audit

**Files:**
- Stage only the exact changed code/test/docs paths from Tasks 1-4.

**Interfaces:**
- Consumes: the completed implementation and durable contracts.
- Produces: one verified implementation commit, pushed draft PR update, and a clean aligned branch.

- [ ] **Step 1: Run full tests**

```bash
python3 -m pytest tests -q
```

Expected: zero failures; record the exact pass count and warnings.

- [ ] **Step 2: Run product and release gates**

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

Expected: local code/render/public/commercial gates pass; pilot readiness may remain blocked only by the already documented stale-readiness or external gates.

- [ ] **Step 3: Verify zero generated churn**

Confirm `git status --short` lists only the exact intended code/test/docs paths and no CSV, JSON, report, sample-report, screenshot, timing, readiness, or canonical-data path.

- [ ] **Step 4: Stage exact files and verify staged hygiene**

Run `git add --` with the explicit paths, then:

```bash
git diff --cached --check
make staged-hygiene-check
```

Expected: product/code/docs/test files only; zero generated or manual-review paths.

- [ ] **Step 5: Commit, push, and update PR #113**

Commit with `Guard prospective consensus batches`, push only `codex/personal-research-mode-mvp`, and post the behavior, verification, maturity boundary, artifact boundary, and external dependency status to the existing draft PR. Do not merge or deploy.

- [ ] **Step 6: Reverify final truth**

Confirm clean 0/0 alignment, HEAD ancestry, PR open/draft/mergeable state, zero generated churn, stale-readiness truth, and the next executable local gate. Keep the overall goal active.
