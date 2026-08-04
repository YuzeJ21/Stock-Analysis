# Minimal No-Write Primary Workflow Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the no-write boundary for the primary Company Workbench and default automatic-policy workflow without migrating secondary operator and Advanced surfaces.

**Architecture:** One strict primary-only command boundary validates and composes every primary reviewed-write proof. Company Workbench and automatic-policy builders consume that boundary; the pre-existing legacy helper remains unchanged for Advanced callers. A separate runtime scanner removes the final actionable legacy readiness command. Secondary queues and explicit exports remain outside the slice and cannot expand it.

**Tech Stack:** Python 3.12, pandas, frozen dataclasses, pathlib, pytest, Make, Streamlit dashboard helpers.

## Global Constraints

- Work only in `/Users/yjian070/Documents/New project/.worktrees/personal-research-mode-mvp` on `codex/personal-research-mode-mvp`.
- Approved design: `docs/superpowers/specs/2026-08-03-minimal-no-write-primary-workflow-closure-design.md`.
- Implementation base: commit `4dd5ffef0` or its verified plan-only descendant.
- Do not apply, pop, stage, commit, or push stash `afabc7a397de8a9434e9da90e2a6cf028d76618f`.
- Modify no more than the 5 production and 7 test files named below. A thirteenth file or another production function is a stop condition, not an invitation to expand.
- Do not modify, restore, regenerate, stage, or commit the 18 protected generated/canonical paths.
- Do not run readiness rebuilds, broad refreshes, source applies, generated reports, screenshots, timing capture, or `make readiness`.
- Never use `git add -A`.
- Preserve the research-only, no-recommendation, no-trading, source-rights, explicit-Q4, EPS split-basis, synthetic-fixture, and calibration boundaries.
- Keep PR #113 open and draft. Do not merge or deploy.

## File Map

Production files, and no others:

- `src/reviewed_batch_proof.py` — validate and compose primary profile-bound proof commands.
- `src/dashboard.py` — update only `single_stock_reader_guide_frame()` and `single_stock_quick_read_cards()`.
- `src/auto_refresh_orchestrator.py` — update only `build_default_lane_policies()`, `evaluate_auto_apply_gate()`, `build_scheduler_plan()`, and private helpers they require.
- `src/readiness_engine.py` — replace the final actionable standalone legacy readiness command.
- `Makefile` — update only the readiness help block.

Test files, and no others:

- `tests/test_reviewed_batch_proof.py`
- `tests/test_readiness_proof_copy.py`
- `tests/test_dashboard_helpers.py`
- `tests/test_auto_refresh_orchestrator.py`
- `tests/test_readiness_command_copy.py` (new)
- `tests/test_launchers.py`
- `tests/test_public_v1_release_docs.py`

## Preflight for every task

Run these read-only checks before editing:

```bash
git status --short --branch
git diff --cached --name-only
git stash list --format='%gd %H %s' | head -n 3
base=.superpowers/sdd/2026-08-02-no-write-derived-artifact-boundary
shasum -a 256 -c "$base/artifact-hashes.sha256"
git status --porcelain=v1 -- data outputs docs/assets \
  | awk '{print $2}' | LC_ALL=C sort \
  | diff -u "$base/protected-dirty-paths.txt" -
```

Expected: branch is correct; the index is empty; stash `afabc7a...` exists; all 124 hashes pass; exactly the same 18 protected paths remain dirty.

---

### Task 1: Harden the central primary proof boundary

**Files:**
- Modify: `tests/test_reviewed_batch_proof.py`
- Modify: `src/reviewed_batch_proof.py`

**Interfaces:**
- Produces: `primary_profile_scoped_reviewed_step(*, profile: str, step: str) -> str`.
- Produces: `primary_profile_bound_reviewed_write_proof_sequence(*, profile: str, lane: str, reviewed_steps: Iterable[str], after_compare_steps: Iterable[str] = ()) -> str`.
- Preserves: the existing `profile_bound_reviewed_write_proof_sequence()` byte-for-byte for out-of-scope Advanced callers.
- A non-local price proof returns a truthful unavailable string and contains no price validate, preview, or apply command.

- [ ] **Step 1: Replace the stale success assertions with failing boundary tests**

Add tests that name the behavior directly:

```python
@pytest.mark.parametrize(
    "unsafe_step",
    (
        "make status-check && make pipeline",
        "make status-check; make pipeline",
        "make status-check | tee /tmp/x",
        "make status-check>/tmp/x",
        "make status-check > /tmp/x",
        "make status-check OUTPUT=/tmp/x",
        "make imports-apply IMPORT_TICKERS=AAA",
        "make stock-report-md TICKER=AAA",
        "make readiness-materialize PROFILE=local",
    ),
)
def test_primary_profile_scoped_reviewed_step_rejects_apply_writers_and_shell_composition(unsafe_step):
    with pytest.raises(ValueError):
        primary_profile_scoped_reviewed_step(profile="local", step=unsafe_step)
```

Add one exact positive proof assertion:

```python
def test_reviewed_write_proof_is_same_profile_and_apply_immediately_precedes_compare():
    proof = primary_profile_bound_reviewed_write_proof_sequence(
        profile="local",
        lane="fundamentals",
        reviewed_steps=(
            "make imports-validate IMPORT_TICKERS=AAA",
            "make imports-preview IMPORT_TICKERS=AAA",
            "make imports-apply IMPORT_TICKERS=AAA",
        ),
        after_compare_steps=("make status-check TOP_N=5",),
    )
    assert proof.split(" && ") == [
        "make readiness-snapshot PROFILE=local",
        "STOCK_RESEARCH_DATA_PROFILE=local make imports-validate IMPORT_TICKERS=AAA",
        "STOCK_RESEARCH_DATA_PROFILE=local make imports-preview IMPORT_TICKERS=AAA",
        "STOCK_RESEARCH_DATA_PROFILE=local make imports-apply IMPORT_TICKERS=AAA",
        "make reviewed-batch-compare PROFILE=local LANE=fundamentals BATCH_ID=<reviewed_batch_id> REVIEW_DATE=<yyyy-mm-dd>",
        "STOCK_RESEARCH_DATA_PROFILE=local make status-check TOP_N=5",
    ]
```

Add mutation cases proving that readiness/DCFs, optional-context readiness, reports, pipeline, materialization, output arguments, proof-record writers, an extra command before validate, and any writer after compare are rejected. Add default/demo/local price cases; only local may return an executable price proof.

- [ ] **Step 2: Run RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider \
  tests/test_reviewed_batch_proof.py -q
```

Expected: failures show that both new primary-only helpers are absent. Existing legacy-helper tests remain green and are not rewritten.

- [ ] **Step 3: Implement the minimal parser and composer**

In `src/reviewed_batch_proof.py`, add the two new primary-only helpers without changing `profile_bound_reviewed_write_proof_sequence()` or `POST_APPLY_READINESS_TOKENS`:

- parse exactly one `make` target after temporarily removing product placeholders such as `<ticker>`;
- reject shell composition, attached/spaced redirection, output arguments, apply targets in the single-step helper, readiness/report/pipeline/materialization/record writers, and unapproved tails;
- require exactly one validate, one preview, and one apply in that order, with apply as the final reviewed step;
- bind every reviewed and approved read-only tail step to the selected profile;
- put comparison immediately after apply;
- return unavailable for default/demo price-write lanes.

Use explicit target sets; do not execute commands or infer writability from subprocess output.

- [ ] **Step 4: Run GREEN and preservation checks**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider \
  tests/test_reviewed_batch_proof.py -q
git diff --check -- src/reviewed_batch_proof.py tests/test_reviewed_batch_proof.py
base=.superpowers/sdd/2026-08-02-no-write-derived-artifact-boundary
shasum -a 256 -c "$base/artifact-hashes.sha256"
```

- [ ] **Step 5: Stage and commit exactly Task 1**

```bash
git add -- src/reviewed_batch_proof.py tests/test_reviewed_batch_proof.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Harden primary proof command boundary"
```

---

### Task 2: Bind the primary Company Workbench and automatic policies

**Files:**
- Modify: `tests/test_readiness_proof_copy.py`
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `tests/test_auto_refresh_orchestrator.py`
- Modify: `src/dashboard.py`
- Modify: `src/auto_refresh_orchestrator.py`

**Interfaces:**
- Consumes: Task 1's two primary-only proof helpers.
- Produces: primary Dashboard proof fields that are complete, selected-profile proofs or truthful unavailable text.
- Produces: automatic policies and ready-gate decisions bound to one selected profile.

- [ ] **Step 1: Add a failing rendered-primary-object table**

In `tests/test_readiness_proof_copy.py`, render only:

- `single_stock_reader_guide_frame()`;
- `single_stock_quick_read_cards()`;
- `build_default_lane_policies(profile=...)`;
- ready `evaluate_auto_apply_gate(..., profile=...)` decisions.

Exercise default, demo, and local with five Company Workbench states: missing price, blocked fundamentals, peer valuation blocked, optional context blocked, and ETF monitor context. Recursively inspect only the returned strings.

The test fails when:

- an apply appears without snapshot, same-profile validate/preview/apply, and immediate comparison;
- a validate/preview step lacks `STOCK_RESEARCH_DATA_PROFILE=<selected>`;
- default/demo contains price validate/preview/apply or refresh commands;
- a proof contains `make readiness`, `dcf-readiness`, `optional-context-readiness`, `price-coverage`, report/export, pipeline, materialization, or proof-record writers;
- a primary Company Workbench object offers `stock-report-md` as its next action.

Add direct tests in `tests/test_auto_refresh_orchestrator.py` for:

- ready fundamentals returns one complete proof command;
- default/demo price gate is blocked with the local-profile unblock condition;
- local price gate returns the complete proof;
- `build_scheduler_plan(profile="demo")` creates demo policies without ambient fallback.

Update only the existing reader-guide/quick-read assertions in `tests/test_dashboard_helpers.py` that describe the old unscoped/import/report behavior.

- [ ] **Step 2: Run RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider \
  tests/test_readiness_proof_copy.py \
  tests/test_dashboard_helpers.py \
  tests/test_auto_refresh_orchestrator.py -q
```

Expected: failures identify current unscoped Dashboard proof prose, primary Markdown-report actions, hard-coded default automatic policies, isolated apply commands, and non-local price writes.

- [ ] **Step 3: Implement only the approved primary builders**

In `src/dashboard.py`, change only `single_stock_reader_guide_frame()` and `single_stock_quick_read_cards()`:

- resolve one active profile once per builder;
- use the complete helper for fundamentals, peers, optional context, and local price proof fields;
- render default/demo price proof as unavailable;
- keep focus/status inspection commands profile-scoped and read-only;
- remove `stock-report-md` from primary next actions and proof prose; do not change the explicit Advanced export implementation.

In `src/auto_refresh_orchestrator.py`:

- add `profile: str | None = None` to `build_default_lane_policies()`, `evaluate_auto_apply_gate()`, and `build_scheduler_plan()`;
- resolve the profile once and forward it;
- use profile-scoped read-only dry-run/queue commands;
- set every runnable `gated_apply_command` to the complete helper proof;
- block default/demo price write policies and ready-gate decisions;
- return only the complete proof in a ready decision; do not append proof-ledger or report writers.

Do not change refresh-provider selection, retry logic, readiness semantics, or any other Dashboard function.

- [ ] **Step 4: Run GREEN, neighboring suites, and preservation checks**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider \
  tests/test_readiness_proof_copy.py \
  tests/test_dashboard_helpers.py \
  tests/test_auto_refresh_orchestrator.py -q
git diff --check -- \
  src/dashboard.py src/auto_refresh_orchestrator.py \
  tests/test_readiness_proof_copy.py tests/test_dashboard_helpers.py \
  tests/test_auto_refresh_orchestrator.py
base=.superpowers/sdd/2026-08-02-no-write-derived-artifact-boundary
shasum -a 256 -c "$base/artifact-hashes.sha256"
```

- [ ] **Step 5: Stage and commit exactly Task 2**

```bash
git add -- \
  src/dashboard.py src/auto_refresh_orchestrator.py \
  tests/test_readiness_proof_copy.py tests/test_dashboard_helpers.py \
  tests/test_auto_refresh_orchestrator.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Bind primary research actions to no-write proof"
```

---

### Task 3: Enforce runtime command copy and complete verification

**Files:**
- Create: `tests/test_readiness_command_copy.py`
- Modify: `tests/test_launchers.py`
- Modify: `tests/test_public_v1_release_docs.py`
- Modify: `src/readiness_engine.py`
- Modify: `Makefile`

**Interfaces:**
- Produces: a scanner that permits the standalone legacy readiness command only on its own deprecated no-write guard help line.
- Produces: grouped Make help for preview, snapshot, comparison, guard, and confirmed Advanced materialization.

- [ ] **Step 1: Write the failing runtime scanner and help assertions**

Create `tests/test_readiness_command_copy.py` with a standalone-token regex that scans `src/**/*.py` and `Makefile`, excludes hyphenated targets, and reports path, line, and source text. Permit exactly the `Makefile` help line containing both `make readiness` and `Deprecated no-write guard; exits 2`.

The current RED offender must be `src/readiness_engine.py`'s peer-unlock sequence. `readiness-preview`, `readiness-snapshot`, `readiness-materialize`, and `reviewed-batch-compare` must not match.

Extend `tests/test_launchers.py` and `tests/test_public_v1_release_docs.py` to require all five help boundaries:

- in-memory preview;
- required-profile snapshot;
- required-profile in-memory comparison;
- deprecated no-write guard that exits 2;
- confirmed ignored local materialization under Advanced.

- [ ] **Step 2: Run RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider \
  tests/test_readiness_command_copy.py \
  tests/test_launchers.py \
  tests/test_public_v1_release_docs.py -q
```

Expected: the scanner reports `src/readiness_engine.py`; help assertions report the missing comparison description. If the two previously classified launcher assertions fail, update only their stale expectations to the already committed no-write behavior; do not change unrelated production code.

- [ ] **Step 3: Make the minimal runtime/help changes**

- Replace the peer-unlock `make readiness` action with `make readiness-preview TOP_N=20`; retain any explicit report action as a separate later action, not proof of refreshed state.
- Add one `reviewed-batch-compare PROFILE=<default|demo|local>` help line stating that current readiness is composed in memory and no current report is written.
- Keep the existing deprecated guard and confirmed materializer wording.

- [ ] **Step 4: Run focused GREEN**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider \
  tests/test_readiness_command_copy.py \
  tests/test_launchers.py \
  tests/test_public_v1_release_docs.py -q
git diff --check -- \
  src/readiness_engine.py Makefile \
  tests/test_readiness_command_copy.py tests/test_launchers.py \
  tests/test_public_v1_release_docs.py
```

- [ ] **Step 5: Run the complete acceptance suite without writers**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider tests -q
make dashboard-smoke
make public-wording-check
make public-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
base=.superpowers/sdd/2026-08-02-no-write-derived-artifact-boundary
shasum -a 256 -c "$base/artifact-hashes.sha256"
git status --porcelain=v1 -- data outputs docs/assets \
  | awk '{print $2}' | LC_ALL=C sort \
  | diff -u "$base/protected-dirty-paths.txt" -
```

Expected: all commands pass; 124 protected hashes remain exact; exactly the original 18 generated/canonical paths remain dirty and unstaged.

- [ ] **Step 6: Enforce the file ceiling, stage, and commit exactly Task 3**

```bash
diff -u \
  <(printf '%s\n' \
    Makefile \
    src/auto_refresh_orchestrator.py \
    src/dashboard.py \
    src/readiness_engine.py \
    src/reviewed_batch_proof.py \
    tests/test_auto_refresh_orchestrator.py \
    tests/test_dashboard_helpers.py \
    tests/test_launchers.py \
    tests/test_public_v1_release_docs.py \
    tests/test_readiness_command_copy.py \
    tests/test_readiness_proof_copy.py \
    tests/test_reviewed_batch_proof.py \
    | LC_ALL=C sort) \
  <({ git diff --name-only 4dd5ffef0..HEAD; git diff --name-only; } \
    | rg '^(Makefile|src/|tests/)' | LC_ALL=C sort -u)
git add -- \
  src/readiness_engine.py Makefile \
  tests/test_readiness_command_copy.py tests/test_launchers.py \
  tests/test_public_v1_release_docs.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Enforce primary no-write command copy"
```

- [ ] **Step 7: Final handoff only after exact current evidence**

Re-run `git status --short --branch`, the 124-hash check, exact-18 comparison, and focused command-copy test after the commit. Do not push or update PR #113 until those post-commit checks are current and clean. Then push only `codex/personal-research-mode-mvp`, update the draft PR with the three exact commits and test evidence, and require exact-head CI before calling the slice review-safe.
