# Readiness Release Evidence Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an exact-receipt-bound review, record, and staging-guard workflow for the named default-profile readiness artifacts without changing readiness decisions or granting source rights.

**Architecture:** One focused `src.readiness_release_review` module owns immutable evidence types, bounded Git/file reads, canonical receipt calculation, CLI rendering, append-only records, and guard evaluation. It composes the existing readiness preview, rights registry, DCF price-lineage, readiness engine, and repository path policies; Make and documentation expose the three operator commands.

**Tech Stack:** Python 3 standard library, pandas, PyYAML through existing rights helpers, pytest, GNU Make, Git CLI.

## Global Constraints

- Default-profile readiness release evidence only.
- Do not alter readiness calculations, thresholds, exclusions, or current ready/partial/blocked states.
- Technical readiness and commercial eligibility remain independent.
- Exact source IDs are authoritative; never split composite source strings.
- Review and guard are write-free; record is the only write and only appends `data/readiness_release_reviews.csv` under an exclusive lock.
- Never stage automatically and never print `git add -A`.
- Never infer human, legal, commercial, accessibility, or distribution approval.
- Preserve the existing 18 protected generated artifacts byte-for-byte and keep them unstaged throughout engineering verification.
- Keep PR #113 open and draft; do not merge, deploy, or publish.

---

## File Map

- Create `src/readiness_release_review.py`: domain objects, review composition, canonical receipt, record writer/reader, guard evaluator, CLI, deterministic text/JSON renderers.
- Create `tests/test_readiness_release_review.py`: pure and temporary-Git-repository behavior tests for review, receipt, record, guard, CLI, and no-write guarantees.
- Modify `Makefile`: add three targets and concise help entries.
- Modify `tests/test_launchers.py`: exercise Make target contracts through the real CLI.
- Modify `ROADMAP.md`, `docs/NEXT_STAGE_ROADMAP.md`, `docs/DATA_STRATEGY.md`, and `docs/OPERATOR_GUIDE.md`: operator boundary and exact command sequence.
- Modify `tests/test_public_v1_release_docs.py`: assert user-visible workflow promises through the documents that operators read.

### Task 1: Deterministic candidate and receipt core

**Files:**
- Create: `src/readiness_release_review.py`
- Create: `tests/test_readiness_release_review.py`

**Interfaces:**
- Produces: `CandidatePathSpec(path: str, category: str)`, `FileEvidence(path: str, category: str, head_sha256: str, working_sha256: str, status: str)`, and `ReviewAxis(name: str, status: str, blockers: tuple[str, ...])`.
- Produces initially: `ReleaseReviewPacket(overall_status: str, preview_receipt: str, git_head: str, branch: str, candidate_manifest_digest: str, canonical_source_digest: str, rights_registry_digest: str, proof_ledger_digest: str, candidate_paths: tuple[FileEvidence, ...], axes: tuple[ReviewAxis, ...], blockers: tuple[str, ...], top_n: int)`.
- `ReleaseReviewPacket.axis(name: str) -> ReviewAxis` returns exactly one named axis and raises `KeyError` for an unknown axis.
- Produces: `build_release_review(project_root: Path | str, *, top_n: int = 20, allow_record_path_change: bool = False) -> ReleaseReviewPacket`.
- Produces: `canonical_receipt(payload: Mapping[str, object]) -> str` using sorted-key, compact UTF-8 JSON and SHA-256.
- Consumes later: `ReleaseReviewPacket.preview_receipt`, `candidate_manifest_digest`, `canonical_source_digest`, `rights_registry_digest`, `proof_ledger_digest`, `axes`, and `blockers`.

- [ ] **Step 1: Write failing manifest and receipt tests**

```python
def test_candidate_manifest_is_exact_ordered_and_digest_is_deterministic(tmp_path):
    repo = build_release_fixture(tmp_path)
    first = release.build_release_review(repo, top_n=1)
    second = release.build_release_review(repo, top_n=50)
    assert tuple(item.path for item in first.candidate_paths) == EXPECTED_CANDIDATE_PATHS
    assert first.candidate_manifest_digest == second.candidate_manifest_digest
    assert first.preview_receipt == second.preview_receipt

def test_review_rejects_unexpected_modified_or_staged_path(tmp_path):
    repo = build_release_fixture(tmp_path)
    (repo / "data/reports/unexpected.csv").write_text("x\n1\n", encoding="utf-8")
    run_git(repo, "add", "data/reports/unexpected.csv")
    packet = release.build_release_review(repo)
    assert "unexpected_changed_path:data/reports/unexpected.csv" in packet.blockers
    assert packet.axis("staging_hygiene_review").status == "blocked"
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_readiness_release_review.py -q`

Expected: collection fails because `src.readiness_release_review` does not exist.

- [ ] **Step 3: Implement bounded path evidence and canonical receipt**

```python
CANDIDATE_PATHS = (
    CandidatePathSpec("data/analyst_estimates_readiness.csv", "compatibility_copy"),
    CandidatePathSpec("data/dcf_readiness.csv", "compatibility_copy"),
    CandidatePathSpec("data/earnings_readiness.csv", "compatibility_copy"),
    CandidatePathSpec("data/price_coverage_report.csv", "compatibility_copy"),
    CandidatePathSpec("data/reports/analyst_estimates_readiness_report.csv", "primary_readiness_output"),
    CandidatePathSpec("data/reports/data_source_status.csv", "source_status_metadata"),
    CandidatePathSpec("data/reports/dcf_readiness_report.csv", "primary_readiness_output"),
    CandidatePathSpec("data/reports/earnings_readiness_report.csv", "primary_readiness_output"),
    CandidatePathSpec("data/reports/feature_readiness_summary.csv", "derived_summary"),
    CandidatePathSpec("data/reports/fundamentals_coverage_report.csv", "primary_readiness_output"),
    CandidatePathSpec("data/reports/peer_readiness_report.csv", "primary_readiness_output"),
    CandidatePathSpec("data/reports/peer_unlock_worklist.csv", "derived_worklist"),
    CandidatePathSpec("data/reports/price_coverage_report.csv", "primary_readiness_output"),
    CandidatePathSpec("data/reports/ticker_readiness_report.csv", "primary_readiness_output"),
    CandidatePathSpec("data/reports/universe_coverage_report.csv", "primary_readiness_output"),
    CandidatePathSpec("data/universe_master.csv", "canonical_readiness_input"),
    CandidatePathSpec("outputs/feature_readiness_summary.csv", "derived_summary"),
    CandidatePathSpec("outputs/peer_unlock_worklist.csv", "derived_worklist"),
)

def canonical_receipt(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
```

The implementation must use `git show HEAD:<named-path>` and `git status --porcelain=v1 -z` without shell execution, reject symlinks/non-regular files, cap file size and CSV rows, and classify every changed path before calculating the receipt.

The canonical source digest is an ordered digest of these named inputs, with an explicit missing marker where an optional file is absent:

```python
READINESS_SOURCE_PATHS = (
    "config/readiness.yml",
    "data/universe.csv",
    "data/universe_active.csv",
    "data/holdings.csv",
    "data/prices.csv",
    "data/fundamentals.csv",
    "data/peers.csv",
    "data/peer_candidates.csv",
    "data/earnings.csv",
    "data/analyst_estimates.csv",
)
RIGHTS_REGISTRY_PATH = "config/source_rights.yml"
PROOF_LEDGER_PATHS = ("data/reviewed_batch_proofs.csv", "data/reviewed_data_proofs.csv")
```

`data/universe_master.csv` is bound in the candidate manifest because it is part of the reviewed 18-file materialization; the remaining canonical inputs above are bound in `canonical_source_digest`. The rights registry and proof ledgers retain separate digests so their changes produce specific blocker codes.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_readiness_release_review.py -q`

Expected: manifest, unexpected-path, staged-path, symlink, size, duplicate-row, and receipt determinism cases pass.

- [ ] **Step 5: Commit Task 1**

```bash
git add -- src/readiness_release_review.py tests/test_readiness_release_review.py
git diff --cached --check
make staged-hygiene-check
git commit -m "Add deterministic readiness release review core"
```

### Task 2: Three-way readiness and independent evidence axes

**Files:**
- Modify: `src/readiness_release_review.py`
- Modify: `tests/test_readiness_release_review.py`

**Interfaces:**
- Extends `ReleaseReviewPacket` with `head_to_working: ReadinessImpactPreview`, `working_to_proposed: ReadinessImpactPreview`, and `transitions: tuple[TransitionEvidence, ...]`; receipt serialization includes the complete, untruncated transition rows but excludes `top_n`.
- Produces: `TransitionEvidence(ticker: str, fields: tuple[str, ...], source_id: str, source_reference: str, as_of_date: str, changed_input_identity: str, review_cutoff: str, before_snapshot_identity: str, after_snapshot_identity: str)`.
- Produces: `review_historical_binding(transitions: Sequence[TransitionEvidence], batch_rows: Sequence[Mapping[str, str]], data_rows: Sequence[Mapping[str, str]]) -> ReviewAxis`.
- Uses: `compare_readiness_frames`, `review_readiness_promotions`, `review_dcf_price_lineage`, `load_source_rights_registry`, and `build_ticker_readiness_report(..., write_outputs=False)`.

- [ ] **Step 1: Write failing three-way and axis tests**

```python
def test_review_compares_head_working_and_fresh_in_memory_frames(tmp_path):
    repo = build_release_fixture(tmp_path, head_ready=False, working_ready=True, proposed_ready=True)
    packet = release.build_release_review(repo)
    assert packet.head_to_working.changed_ticker_count == 1
    assert packet.working_to_proposed.changed_ticker_count == 0
    assert packet.axis("technical_transition_review").status == "passed"

def test_composite_source_and_missing_registered_fields_fail_independently(tmp_path):
    repo = build_release_fixture(tmp_path, promotion_source="sec_companyfacts + yfinance")
    packet = release.build_release_review(repo)
    assert packet.axis("commercial_rights_review").status == "blocked"
    assert packet.axis("registered_field_scope_review").status == "blocked"
    assert "commercial_rights:unknown_source" in packet.blockers

def test_ticker_mention_without_exact_historical_binding_is_not_proof(tmp_path):
    transition = transition_fixture("AAA", source_id="sec_companyfacts")
    row = proof_row_fixture(tickers="AAA", source_files="data/fundamentals.csv", post_run_readiness_snapshot="different")
    axis = release.review_historical_binding((transition,), (row,), ())
    assert axis.status == "blocked"
    assert axis.blockers == ("historical_proof_binding_missing:AAA",)

def test_exact_historical_binding_passes_for_matching_lane_source_inputs_and_snapshots():
    transition = transition_fixture(
        "AAA",
        source_id="sec_companyfacts",
        changed_input_identity="sha256:input",
        before_snapshot_identity="sha256:before",
        after_snapshot_identity="sha256:after",
    )
    row = proof_row_fixture(
        lane="fundamentals",
        tickers="AAA",
        source_files="sec_companyfacts; sha256:input",
        pre_run_readiness_snapshot="sha256:before",
        post_run_readiness_snapshot="sha256:after",
    )
    assert release.review_historical_binding((transition,), (row,), ()).status == "passed"

def test_review_blocks_a_broken_compatibility_mirror(tmp_path):
    repo = build_release_fixture(tmp_path)
    (repo / "outputs/feature_readiness_summary.csv").write_text("different\n", encoding="utf-8")
    packet = release.build_release_review(repo)
    assert "mirror_mismatch:feature_readiness_summary" in packet.blockers
    assert packet.axis("candidate_integrity").status == "blocked"

@pytest.mark.parametrize(
    "mutation",
    ["candidate", "source", "rights", "proof", "head", "staged_state"],
)
def test_receipt_changes_for_every_bound_dependency(tmp_path, mutation):
    repo = build_release_fixture(tmp_path)
    before = release.build_release_review(repo).preview_receipt
    mutate_bound_dependency(repo, mutation)
    after = release.build_release_review(repo).preview_receipt
    assert after != before
```

- [ ] **Step 2: Run new tests and verify RED**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_readiness_release_review.py -q`

Expected: fails because three-way fields and historical binding are absent.

- [ ] **Step 3: Implement three-way review and all independent axes**

Map the Head CSV bytes, working CSV, and in-memory frame through the existing readiness comparison API. Promotions must be evaluated from Head to working, never working to itself. Construct axes in the exact spec order:

```python
AXIS_NAMES = (
    "candidate_integrity",
    "technical_transition_review",
    "provenance_review",
    "commercial_rights_review",
    "registered_field_scope_review",
    "price_lineage_review",
    "historical_proof_binding_review",
    "distribution_review",
    "staging_hygiene_review",
)
```

Mirror checks compare analyst-estimates, earnings, price, feature-summary, and peer-worklist pairs byte-for-byte. DCF compatibility compares normalized CSV rows after renaming `is_dcf_ready` to `dcf_ready`. `distribution_review` remains `review_required` in preview until a named record supplies a decision. Overall state is `invalid` for malformed evidence, `blocked` for failed technical axes, `technical_snapshot_reviewable_commercial_claims_withheld` when technical axes pass but commercial/distribution axes do not, and `release_reviewable` only when every pre-record gate is satisfied except the pending named distribution decision.

- [ ] **Step 4: Run focused and related tests**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_readiness_release_review.py tests/test_readiness_preview.py tests/test_commercial_source_rights.py tests/test_dcf_price_lineage.py tests/test_readiness_engine.py -q`

Expected: all pass; mutations that split composite IDs, reuse working as Head, ignore price lineage, or accept ticker-only proof each fail at least one focused test.

- [ ] **Step 5: Commit Task 2**

```bash
git add -- src/readiness_release_review.py tests/test_readiness_release_review.py
git diff --cached --check
make staged-hygiene-check
git commit -m "Review readiness release evidence axes"
```

### Task 3: Exact append-only reviewed records

**Files:**
- Modify: `src/readiness_release_review.py`
- Modify: `tests/test_readiness_release_review.py`

**Interfaces:**
- Produces: `RecordedDecision` with the exact `REVIEW_RECORD_COLUMNS` schema.
- Produces: `record_review(project_root, *, preview_receipt, reviewer, review_date, technical_decision, distribution_decision, confirm_reviewed, ledger_path=None) -> RecordedDecision`.
- Produces: `load_review_records(path: Path) -> tuple[RecordedDecision, ...]` with duplicate-ID and duplicate-receipt rejection.

- [ ] **Step 1: Write failing validation, locking, and atomic-write tests**

```python
def test_record_requires_exact_current_receipt_and_writes_one_row(tmp_path):
    repo = build_release_fixture(tmp_path)
    receipt = release.build_release_review(repo).preview_receipt
    record = release.record_review(
        repo,
        preview_receipt=receipt,
        reviewer="Y. Jian",
        review_date="2026-08-09",
        technical_decision="approved",
        distribution_decision="external_review_required",
        confirm_reviewed=True,
    )
    rows = release.load_review_records(repo / "data/readiness_release_reviews.csv")
    assert rows == (record,)
    assert record.preview_receipt == receipt

def test_record_revalidates_after_lock_and_refuses_stale_receipt(tmp_path):
    repo = build_release_fixture(tmp_path)
    receipt = release.build_release_review(repo).preview_receipt
    mutate_candidate_after_lock(repo)
    with pytest.raises(release.ReleaseReviewError, match="preview_receipt_mismatch"):
        record_with_lock_hook(repo, receipt)
    assert not (repo / "data/readiness_release_reviews.csv").exists()
```

Add literal cases for placeholders, control characters, malformed date, unsupported decisions, missing confirmation, duplicate receipt/ID, replace failure before publication, and post-write reload failure.

- [ ] **Step 2: Run new record tests and verify RED**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_readiness_release_review.py -q -k record`

Expected: fails because the record API is absent.

- [ ] **Step 3: Implement exact record validation and atomic append**

Use `research_ledger_lock.ledger_lock` for process/thread serialization. Inside the lock: rebuild the full review, compare the supplied receipt, validate the existing CSV header and unique rows, append one normalized row in memory, write a sibling temporary file with `newline=""`, flush and `fsync`, `os.replace`, fsync the parent directory, then reload by immutable record ID. Derive the ID as `RRR-<review-date-without-dashes>-<first-12-receipt-chars>`; timestamps are record metadata and never receipt input.

Validation rejects empty or placeholder reviewer values, `\r`, `\n`, NUL/control characters, dates other than strict ISO `YYYY-MM-DD`, and decisions outside the enumerated values. A failed post-write reload raises `record_write_outcome_uncertain:<record_id>:reload_by_record_id`.

- [ ] **Step 4: Run record and lock-related tests**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_readiness_release_review.py tests/test_research_ledger_lock.py -q`

Expected: all pass, including exact revalidation, no-write-on-validation-failure, atomic replace, duplicate prevention, and uncertain-outcome guidance.

- [ ] **Step 5: Commit Task 3**

```bash
git add -- src/readiness_release_review.py tests/test_readiness_release_review.py
git diff --cached --check
make staged-hygiene-check
git commit -m "Record exact readiness release reviews"
```

### Task 4: Guard, CLI, and Make operator boundary

**Files:**
- Modify: `src/readiness_release_review.py`
- Modify: `tests/test_readiness_release_review.py`
- Modify: `Makefile`
- Modify: `tests/test_launchers.py`

**Interfaces:**
- Produces: `GuardResult(status: str, record_id: str, blockers: tuple[str, ...], stage_paths: tuple[str, ...], resume_command: str)`.
- Produces: `evaluate_guard(project_root, *, record_id: str, ledger_path=None) -> GuardResult`.
- CLI: `review --project-root . --top-n 20 [--json]`, `record ...`, and `guard --record-id ...`.

- [ ] **Step 1: Write failing guard, CLI, and Make tests**

```python
def test_guard_refuses_external_review_required_and_is_write_free(tmp_path):
    repo, record = fixture_with_record(tmp_path, distribution_decision="external_review_required")
    before = tree_snapshot(repo)
    result = release.evaluate_guard(repo, record_id=record.record_id)
    assert result.status == "blocked"
    assert result.blockers == ("distribution_decision_not_approved",)
    assert tree_snapshot(repo) == before

def test_guard_prints_only_exact_named_stage_paths_for_approved_record(tmp_path):
    repo, record = fixture_with_record(tmp_path, distribution_decision="approved", all_axes_pass=True)
    result = release.evaluate_guard(repo, record_id=record.record_id)
    rendered = release.render_guard(result)
    assert result.status == "passed"
    assert rendered.endswith("git add -- " + " ".join(shlex.quote(path) for path in result.stage_paths))
    assert "git add -A" not in rendered
```

Make tests invoke the real targets with a temporary fixture and assert exit codes, JSON receipt, stable blocker codes, absence of traceback, and no file-tree changes for review/guard.

- [ ] **Step 2: Run CLI/Make tests and verify RED**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_readiness_release_review.py tests/test_launchers.py -q -k 'readiness_release'`

Expected: fails because guard and Make targets do not exist.

- [ ] **Step 3: Implement guard, parser, renderers, and Make targets**

```make
readiness-release-review:
	@PYTHONDONTWRITEBYTECODE=1 python3 -m src.readiness_release_review review --project-root . --top-n $(or $(TOP_N),20) $(if $(JSON),--json,)

readiness-release-record:
	@PYTHONDONTWRITEBYTECODE=1 python3 -m src.readiness_release_review record --project-root . --preview-receipt "$(PREVIEW_RECEIPT)" --reviewer "$(REVIEWER)" --review-date "$(REVIEW_DATE)" --technical-decision "$(TECHNICAL_DECISION)" --distribution-decision "$(DISTRIBUTION_DECISION)" $(if $(filter 1,$(CONFIRM_REVIEWED)),--confirm-reviewed,)

readiness-release-guard:
	@PYTHONDONTWRITEBYTECODE=1 python3 -m src.readiness_release_review guard --project-root . --record-id "$(RECORD_ID)"
```

The Makefile must fail early with concise required-variable messages for record and guard. CLI errors catch `ReleaseReviewError`, print one stable line to stderr, return 2, and never emit a traceback. Review may return 0 while accurately reporting a blocked assessment; guard returns 0 only on `passed`.

- [ ] **Step 4: Run focused CLI/Make and no-write tests**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_readiness_release_review.py tests/test_launchers.py -q -k 'readiness_release or release_review'`

Expected: all pass; real review and guard calls leave an exact before/after tree snapshot unchanged.

- [ ] **Step 5: Commit Task 4**

```bash
git add -- src/readiness_release_review.py tests/test_readiness_release_review.py Makefile tests/test_launchers.py
git diff --cached --check
make staged-hygiene-check
git commit -m "Expose readiness release review workflow"
```

### Task 5: Operator documentation and full release verification

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/NEXT_STAGE_ROADMAP.md`
- Modify: `docs/DATA_STRATEGY.md`
- Modify: `docs/OPERATOR_GUIDE.md`
- Modify: `tests/test_public_v1_release_docs.py`

**Interfaces:**
- Consumes: the exact Make commands and blocker meanings implemented in Task 4.
- Produces: one consistent operator sequence and explicit stop rules across all four documents.

- [ ] **Step 1: Write failing document behavior tests**

```python
def test_release_docs_keep_technical_and_distribution_decisions_separate():
    for path in RELEASE_WORKFLOW_DOCS:
        text = _read(path)
        assert "make readiness-release-review TOP_N=20" in text
        assert "make readiness-release-record" in text
        assert "make readiness-release-guard RECORD_ID=<record_id>" in text
        assert "does not grant source rights" in text.lower()
        assert "does not change readiness" in text.lower()
        assert "independent review" in text.lower()
```

- [ ] **Step 2: Run document tests and verify RED**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_public_v1_release_docs.py -q -k readiness_release`

Expected: fails because the operator workflow is not documented.

- [ ] **Step 3: Add concise operator sequence and stop rules**

Each document must state: review first; record only the exact receipt; allow rejected or `external_review_required` records as evidence; run guard only for a named record; stop if any digest, Git head, path, source, proof, rights, field-scope, price-lineage, decision, or staged state changes; stage only the exact paths printed by a passing guard. State that the current package is expected to remain commercially withheld until external evidence exists.

- [ ] **Step 4: Run focused, related, and full gates with fresh evidence**

Run in order:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_readiness_release_review.py tests/test_readiness_preview.py tests/test_commercial_source_rights.py tests/test_dcf_price_lineage.py tests/test_readiness_engine.py tests/test_launchers.py tests/test_public_v1_release_docs.py -q
make test
make dashboard-smoke
make demo-dashboard-render-smoke
make public-wording-check
make public-check
make pilot-readiness-check
make readiness-ops-center
make readiness-preview TOP_N=20
make proof-readiness-reconciliation TOP_N=20
make browser-qa-evidence
make diff-hygiene-summary
make staged-hygiene-check
git diff --check
```

Also compare the stored SHA-256 manifest for all 18 protected paths before and after the matrix. The expected pilot/readiness-release verdict may remain blocked; engineering success must not be restated as data, commercial, reviewer, hosting, or pilot approval.

- [ ] **Step 5: Commit Task 5**

```bash
git add -- ROADMAP.md docs/NEXT_STAGE_ROADMAP.md docs/DATA_STRATEGY.md docs/OPERATOR_GUIDE.md tests/test_public_v1_release_docs.py
git diff --cached --check
make staged-hygiene-check
git commit -m "Document readiness release evidence workflow"
```

- [ ] **Step 6: Finish the branch without crossing owner gates**

Use `superpowers:verification-before-completion`, then `superpowers:finishing-a-development-branch`. Recheck branch, exact Head, upstream divergence, PR #113 draft state, and protected hashes. Push only after all local gates pass; do not mark the PR ready, merge, deploy, publish, or claim external review.
