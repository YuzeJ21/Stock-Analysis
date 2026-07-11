# Proof Workflow Correction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make price-history proof work finite and truthful while making `ROADMAP.md` the only active roadmap.

**Architecture:** The queue module will return a queue view containing executable rows, optionally visible reviewed rows, and summary counts. A separate read-only closeout module will turn reviewed source-limited rows into a single copy-only proof scaffold. Existing Make targets remain read-only and do not touch data files.

**Tech Stack:** Python 3.12, stdlib dataclasses/csv/argparse, GNU Make, pytest, Markdown.

## Global Constraints

- Research-only; no trading, broker, recommendation, or fabricated-data behavior.
- Do not run provider refresh, import, apply, or readiness rebuild commands.
- Do not modify or stage generated CSV, report, output, or sample-report artifacts.
- Default queue output must show only executable unreviewed candidates.
- Reviewed source-limited rows may be shown only in explicit audit mode and remain wait-only.
- Batch closeout must not write proof rows, stage, commit, push, or expose secrets.
- `ROADMAP.md` is the sole active roadmap.

---

### Task 1: Test queue separation and summary counts

**Files:**
- Modify: `tests/test_price_history_proof_queue.py`
- Modify: `src/price_history_proof_queue.py`

**Interfaces:**
- Consumes: `build_price_history_proof_queue_from_files(root, top_n, tickers)`.
- Produces: queue output where reviewed rows are excluded by default and visible with `include_reviewed=True`.

- [ ] **Step 1: Write failing tests**

```python
rows = build_price_history_proof_queue_from_files(tmp_path, top_n=10)
assert [row.ticker for row in rows] == ["NVDA"]

audit_rows = build_price_history_proof_queue_from_files(tmp_path, top_n=10, include_reviewed=True)
assert [row.ticker for row in audit_rows] == ["NVDA", "AMD"]
assert audit_rows[1].next_safe_command.startswith("wait for")
```

- [ ] **Step 2: Run the new tests and verify RED**

Run: `python3 -m pytest tests/test_price_history_proof_queue.py -q`

Expected: failure because `include_reviewed` and the default exclusion behavior do not exist.

- [ ] **Step 3: Implement minimal queue view and CLI flag**

```python
@dataclass(frozen=True)
class PriceHistoryProofSummary:
    momentum_not_ready_count: int
    unreviewed_preferred_history_count: int
    reviewed_source_limited_count: int

def build_price_history_proof_queue_from_files(..., include_reviewed: bool = False) -> list[PriceHistoryProofRow]:
    ...
```

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `python3 -m pytest tests/test_price_history_proof_queue.py -q`

Expected: all queue tests pass.

### Task 2: Add a read-only reviewed batch-closeout command

**Files:**
- Create: `src/price_history_batch_closeout.py`
- Modify: `Makefile`
- Modify: `tests/test_launchers.py`
- Create: `tests/test_price_history_batch_closeout.py`

**Interfaces:**
- Consumes: proof ledger and current price-history queue state.
- Produces: `render_price_history_batch_closeout(...) -> str`, a copy-only grouped proof-record scaffold.

- [ ] **Step 1: Write failing tests**

```python
rendered = render_price_history_batch_closeout(rows, top_n=25)
assert "Read-only" in rendered
assert "does not record proof rows, stage files, commit, or push" in rendered
assert "DRY_RUN=1 make reviewed-batch-proof-record" in rendered
```

- [ ] **Step 2: Run the new test and verify RED**

Run: `python3 -m pytest tests/test_price_history_batch_closeout.py -q`

Expected: import failure because the module does not exist.

- [ ] **Step 3: Implement the renderer and Make target**

```make
price-history-batch-closeout:
	@python3 -m src.price_history_batch_closeout --top-n "$(TOP_N)"
```

- [ ] **Step 4: Run focused tests and command output**

Run: `python3 -m pytest tests/test_price_history_batch_closeout.py tests/test_launchers.py -q`

Expected: all pass and the command prints no mutating action.

### Task 3: Consolidate roadmap and runtime stop rules

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/NEXT_STAGE_ROADMAP.md`
- Modify: `docs/COVERAGE_CONTINUITY_GOAL_PROMPT.md`
- Modify: `README.md`
- Modify: `tests/test_public_v1_release_docs.py`

**Interfaces:**
- Consumes: current roadmap and queue terminology.
- Produces: one active roadmap, pointer-only handoffs, and documented stop rules.

- [ ] **Step 1: Write failing documentation assertions**

```python
assert "The active roadmap is ROADMAP.md" in next_stage
assert "never commit or push one proof row per ticker by default" in roadmap
assert "make price-history-batch-closeout" in readme
```

- [ ] **Step 2: Run targeted docs tests and verify RED**

Run: `python3 -m pytest tests/test_public_v1_release_docs.py -q`

Expected: failure because the authority and new command are not documented.

- [ ] **Step 3: Update docs minimally**

Keep exact readiness counts dynamic. Replace duplicate static status with pointers to:

```text
make project-status-check
make readiness-ops-center
make price-history-proof-queue TOP_N=25
make price-history-batch-closeout TOP_N=25
```

- [ ] **Step 4: Run docs tests and public wording gate**

Run: `python3 -m pytest tests/test_public_v1_release_docs.py -q && make public-wording-check`

Expected: tests and wording gate pass.

### Task 4: Full verification and reviewed commit

**Files:**
- Review: only intentional code, Makefile, docs, and tests.

- [ ] **Step 1: Run requested focused verification**

Run: `python3 -m pytest tests/test_price_history_proof_queue.py tests/test_project_status.py tests/test_launchers.py -q`

- [ ] **Step 2: Run full product verification**

Run: `python3 -m pytest tests -q`, `make public-check`, `make pilot-readiness-check TOP_N=10`, `make diff-hygiene-summary`, and `git diff --check`.

- [ ] **Step 3: Inspect staged scope**

Run: `git add -- <intentional files>`, `make staged-hygiene-check`, `git diff --cached --check`, and `git diff --cached --name-only`.

- [ ] **Step 4: Commit only after every gate passes**

Run: `git commit -m "Consolidate price-history proof workflow"`.

Do not push unless the user explicitly asks.
