# Readiness Impact Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic stdout-only preview of saved-versus-proposed readiness changes without creating or modifying any file.

**Architecture:** Existing universe and readiness builders gain explicit no-write flags whose defaults preserve current write behavior. A focused preview module loads the saved readiness CSV, builds the proposed frames in memory, compares only stable readiness fields, and renders capped human-readable output. The pilot gate routes stale operators to the preview while keeping the intentional readiness rebuild as a separate approval boundary.

**Tech Stack:** Python 3, pandas, argparse, pytest, GNU Make, Markdown.

## Global Constraints

- Do not run `make readiness` during this slice.
- Do not generate or stage CSV, JSON, report, sample-report, screenshot, or timing churn.
- Default write-mode behavior must remain unchanged for existing callers.
- The preview must not create directories, expose an output-path option, or offer JSON/file output.
- Stable comparison fields are `overall_readiness_state`, `price_ready`, `momentum_ready`, `fundamentals_ready`, `dcf_ready`, `peer_ready`, `earnings_ready`, `analyst_estimates_ready`, `ready_features`, `partial_features`, `blocked_features`, and `excluded_features`.
- Missing saved readiness fails closed; no stable changes do not make stale readiness current.
- Preserve research-only, source-rights, candidate-context, synthetic-fixture, Q4, EPS split-basis, and independent readiness boundaries.

---

### Task 1: No-write universe preparation

**Files:**
- Modify: `src/universe_model.py:170-217,299-339`
- Test: `tests/test_universe_model.py`

**Interfaces:**
- Consumes: existing `_read_csv`, `_write_csv`, `_legacy_universe_to_master`, and `_legacy_universe_to_active` helpers.
- Produces: `ensure_universe_files(base_dir=None, *, data_dir=None, write_outputs: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]` and `build_universe_coverage_report(base_dir=None, *, data_dir=None, output_path=None, write_output: bool = True) -> pd.DataFrame`.

- [ ] **Step 1: Write failing no-write universe tests**

Add tests that create only `data/universe.csv`, capture a manifest of all relative file paths and bytes, call both no-write helpers, and assert the frames contain the legacy ticker while the manifest is identical:

```python
from src.universe_model import build_universe_coverage_report


def _file_manifest(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_ensure_universe_files_no_write_builds_frames_without_creating_canonical_files(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    pd.DataFrame([{"Ticker": "NVDA", "CompanyName": "NVIDIA", "DefaultPurpose": "Core Compounder"}]).to_csv(
        data_dir / "universe.csv", index=False
    )
    before = _file_manifest(tmp_path)

    master, active = ensure_universe_files(tmp_path, write_outputs=False)

    assert set(master["ticker"]) == {"NVDA"}
    assert set(active["ticker"]) == {"NVDA"}
    assert _file_manifest(tmp_path) == before


def test_universe_coverage_no_write_creates_no_report_or_directory(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    pd.DataFrame([{"Ticker": "NVDA", "CompanyName": "NVIDIA", "DefaultPurpose": "Core Compounder"}]).to_csv(
        data_dir / "universe.csv", index=False
    )
    before = _file_manifest(tmp_path)

    report = build_universe_coverage_report(tmp_path, write_output=False)

    assert set(report["ticker"]) == {"NVDA"}
    assert _file_manifest(tmp_path) == before
```

- [ ] **Step 2: Run the tests and confirm the new keyword arguments fail**

Run: `python3 -m pytest tests/test_universe_model.py -q`

Expected: FAIL because `write_outputs` and `write_output` are not accepted.

- [ ] **Step 3: Add guarded universe writes**

Change the signatures and guard all `_write_csv` and coverage output operations:

```python
def ensure_universe_files(
    base_dir: Path | str | None = None,
    *,
    data_dir: Path | str | None = None,
    write_outputs: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
```

For each existing universe write use `if write_outputs: _write_csv(...)`. Add `write_output: bool = True` to the coverage signature, call `ensure_universe_files(..., write_outputs=write_output)`, and wrap `output.parent.mkdir(...)` plus `report.to_csv(...)` in `if write_output:`. Always return the in-memory coverage frame.

- [ ] **Step 4: Verify focused universe behavior**

Run: `python3 -m pytest tests/test_universe_model.py -q`

Expected: PASS, including existing write-mode tests.

- [ ] **Step 5: Commit the universe boundary**

Run:

```bash
git add -- src/universe_model.py tests/test_universe_model.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Add no-write universe preparation"
```

### Task 2: No-write readiness engine

**Files:**
- Modify: `src/readiness_engine.py:988-1174`
- Test: `tests/test_readiness_engine.py`

**Interfaces:**
- Consumes: Task 1 no-write universe interfaces.
- Produces: `build_ticker_readiness_report(base_dir=None, *, data_dir=None, output_dir=None, write_outputs: bool = True) -> dict[str, pd.DataFrame]`.

- [ ] **Step 1: Write a failing filesystem-preservation test**

Reuse the existing readiness fixture setup, call the builder with `write_outputs=False`, and assert all expected in-memory report keys exist while the complete file manifest is byte-for-byte unchanged and no output directory appears:

```python
def test_ticker_readiness_no_write_returns_reports_without_mutating_files(tmp_path: Path, monkeypatch):
    # Arrange the same minimal canonical inputs used by the main readiness-state test.
    data_dir = tmp_path / "data"
    _write_minimal_readiness_inputs(data_dir)
    before = _file_manifest(tmp_path)

    reports = build_ticker_readiness_report(
        tmp_path,
        data_dir=data_dir,
        output_dir=tmp_path / "outputs",
        write_outputs=False,
    )

    assert "ticker_readiness_report" in reports
    assert "data_source_status" in reports
    assert not reports["ticker_readiness_report"].empty
    assert _file_manifest(tmp_path) == before
    assert not (tmp_path / "outputs").exists()
```

Factor the existing minimal input rows into `_write_minimal_readiness_inputs(data_dir: Path) -> None`; do not reduce existing write-mode assertions.

- [ ] **Step 2: Run the focused test and confirm failure**

Run: `python3 -m pytest tests/test_readiness_engine.py -q`

Expected: FAIL because `write_outputs` is not accepted.

- [ ] **Step 3: Guard every readiness write**

Add `write_outputs: bool = True` to the builder. Call `ensure_universe_files(..., write_outputs=write_outputs)` and `build_universe_coverage_report(..., write_output=write_outputs)`. Use the returned universe frames instead of re-reading files that no-write preparation may intentionally not create. Wrap the report loop, compatibility copies, output-directory creation, and output copies in one `if write_outputs:` block. Return the same report dictionary in both modes.

- [ ] **Step 4: Verify no-write and regression behavior**

Run: `python3 -m pytest tests/test_readiness_engine.py tests/test_universe_model.py -q`

Expected: PASS; existing write-mode files are still created and no-write mode leaves the manifest unchanged.

- [ ] **Step 5: Commit the readiness boundary**

Run:

```bash
git add -- src/readiness_engine.py tests/test_readiness_engine.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Add no-write readiness build mode"
```

### Task 3: Stable readiness impact comparison and CLI

**Files:**
- Create: `src/readiness_preview.py`
- Create: `tests/test_readiness_preview.py`

**Interfaces:**
- Consumes: `build_ticker_readiness_report(..., write_outputs=False)` from Task 2.
- Produces: `STABLE_READINESS_FIELDS: tuple[str, ...]`, `build_readiness_impact_preview(root: Path, *, data_dir: Path | None = None, top_n: int = 20) -> ReadinessImpactPreview`, `render_readiness_impact_preview(preview: ReadinessImpactPreview) -> str`, and CLI `main() -> int`.

- [ ] **Step 1: Write failing pure comparison tests**

Define two small readiness frames and require timestamp-only differences to produce `no_readiness_changes`, stable state changes to produce `changes_detected`, and details to cap at `top_n` while retaining the total changed count. Include added and removed ticker rows with changed field `row_presence`.

```python
def test_compare_ignores_updated_at_but_reports_stable_fields():
    saved = pd.DataFrame([_row("AAA", price_ready=False, updated_at="2026-01-01")])
    timestamp_only = pd.DataFrame([_row("AAA", price_ready=False, updated_at="2026-07-18")])
    changed = pd.DataFrame([_row("AAA", price_ready=True, updated_at="2026-07-18")])

    assert compare_readiness_frames(saved, timestamp_only, top_n=20).status == "no_readiness_changes"
    preview = compare_readiness_frames(saved, changed, top_n=20)
    assert preview.status == "changes_detected"
    assert preview.changed_ticker_count == 1
    assert preview.changed_tickers[0].fields == ("price_ready",)
```

- [ ] **Step 2: Run the new test module and confirm import failure**

Run: `python3 -m pytest tests/test_readiness_preview.py -q`

Expected: FAIL because `src.readiness_preview` does not exist.

- [ ] **Step 3: Implement immutable comparison structures and normalization**

Create frozen dataclasses for `ReadinessTickerChange` and `ReadinessImpactPreview`. Normalize tickers to uppercase, booleans to strict booleans, missing feature strings to `""`, and compare the union of ticker keys in sorted order. Summarize overall-state counts and true counts for the seven named readiness flags. Do not inspect `updated_at`, source attempt times, or explanatory command text.

- [ ] **Step 4: Write failing integration tests for missing snapshots, output wording, and no writes**

Monkeypatch `build_ticker_readiness_report` to return an in-memory proposed frame. Assert a missing `data/reports/ticker_readiness_report.csv` returns `missing_saved_snapshot`, renders a non-unlock explanation, and does not create the path. With a saved fixture, capture a byte manifest before calling `build_readiness_impact_preview` and assert it is unchanged. Require rendered output to include:

```text
Read-only: no files were created, modified, or deleted.
This preview does not make saved readiness current.
An intentional reviewed make readiness run remains the separate rebuild boundary.
```

- [ ] **Step 5: Implement the preview loader, renderer, and CLI**

The CLI accepts only `--project-root`, `--data-dir`, and `--top-n`; validates `top_n >= 1`; calls the no-write builder; prints the human-readable result; returns `0` for `changes_detected` or `no_readiness_changes`, `2` for `missing_saved_snapshot`, and `1` for a concise in-memory build error. It must not accept `--output` or `--json`.

- [ ] **Step 6: Verify preview unit and integration coverage**

Run: `python3 -m pytest tests/test_readiness_preview.py tests/test_readiness_engine.py tests/test_universe_model.py -q`

Expected: PASS.

- [ ] **Step 7: Commit the preview module**

Run:

```bash
git add -- src/readiness_preview.py tests/test_readiness_preview.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Add no-write readiness impact preview"
```

### Task 4: Command, pilot routing, and user contract

**Files:**
- Modify: `Makefile:1,315-317,1287-1291`
- Modify: `src/pilot_readiness.py:304-315`
- Modify: `tests/test_pilot_readiness.py:450-480`
- Modify: `tests/test_public_v1_release_docs.py`

**Interfaces:**
- Consumes: `python3 -m src.readiness_preview --top-n N`.
- Produces: `make readiness-preview TOP_N=20` and stale pilot routing to that command without changing the blocked verdict.

- [ ] **Step 1: Write failing command-contract assertions**

Add tests requiring `readiness-preview` in `.PHONY`, help text describing it as stdout-only/no-write, and the recipe:

```make
readiness-preview:
	@python3 -m src.readiness_preview --top-n $(or $(TOP_N),20)
```

Change the stale freshness pilot expectation to `make readiness-preview TOP_N=20`, while asserting status remains `blocked` and the stop rule still prevents quoting final counts or proof deltas.

- [ ] **Step 2: Run focused contract tests and confirm failure**

Run: `python3 -m pytest tests/test_pilot_readiness.py tests/test_public_v1_release_docs.py -q`

Expected: FAIL because the target and stale route do not exist.

- [ ] **Step 3: Add the Make target and safe pilot route**

Add the target to `.PHONY`, help, and the readiness target block. In `_freshness_check`, use `make readiness-preview TOP_N=20` when stale or missing. Extend the stop rule to say the preview is inspection evidence only and the reviewed write rebuild remains separately gated.

- [ ] **Step 4: Prove the real command changes no project files**

Capture `git status --porcelain=v1`, a SHA-256/size/mtime manifest for all tracked and untracked files, run `make readiness-preview TOP_N=20`, and compare the manifests. Expected: command prints saved/proposed counts and the explicit no-write/non-unlock boundary; both manifests remain identical.

- [ ] **Step 5: Run command and pilot focused tests**

Run:

```bash
python3 -m pytest tests/test_readiness_preview.py tests/test_readiness_engine.py tests/test_universe_model.py tests/test_pilot_readiness.py tests/test_public_v1_release_docs.py -q
make pilot-readiness-check TOP_N=10
```

Expected: tests PASS; pilot remains blocked because saved readiness is stale and names the preview as the next inspection command.

- [ ] **Step 6: Commit the command surface**

Run:

```bash
git add -- Makefile src/pilot_readiness.py tests/test_pilot_readiness.py tests/test_public_v1_release_docs.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Route stale readiness to no-write preview"
```

### Task 5: Documentation, complete verification, and draft PR

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/DATA_STRATEGY.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: draft PR #113 body/comment only after local verification.

**Interfaces:**
- Consumes: verified no-write preview and unchanged blocked freshness gate.
- Produces: durable operator guidance and PR evidence for the coherent slice.

- [ ] **Step 1: Update the durable operating contract**

Document that `make readiness-preview TOP_N=20` computes proposed stable readiness in memory, writes nothing, cannot make the saved snapshot current, and does not authorize `make readiness`. ROADMAP must distinguish implemented preview inspection from the still-open intentional rebuild/review gate. The continuation prompt must preserve the current no-generated-artifact boundary and name the next executable lanes after preview.

- [ ] **Step 2: Run focused documentation and feature checks**

Run:

```bash
python3 -m pytest tests/test_readiness_preview.py tests/test_readiness_engine.py tests/test_universe_model.py tests/test_pilot_readiness.py tests/test_public_v1_release_docs.py -q
git diff --check
make diff-hygiene-summary
```

Expected: PASS; zero generated CSV/JSON/report/sample-report/screenshot/timing candidates.

- [ ] **Step 3: Run the full approved verification bundle**

Run:

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
git diff --check
```

Expected: all executable local gates PASS; pilot remains truthfully blocked only by stale saved readiness and other already-classified external/manual gates. Do not run `make readiness`.

- [ ] **Step 4: Stage exact documentation and verify hygiene**

Run:

```bash
git add -- ROADMAP.md docs/DATA_STRATEGY.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md
make staged-hygiene-check
git diff --cached --check
git commit -m "Document readiness impact preview"
```

- [ ] **Step 5: Push only the approved branch and update draft PR #113**

Run `git push origin codex/personal-research-mode-mvp`, verify zero divergence, then update PR #113 with the slice summary, exact test counts/gates, explicit no-artifact evidence, and remaining stale-readiness boundary. Confirm the PR remains open and draft; do not merge.

- [ ] **Step 6: Continue the active goal**

Re-read ROADMAP and the continuation prompt from current HEAD. Select the next highest-value safe local/source/hosted-preview/beta/evidence/calibration/operating slice. If no safe local task remains, classify the exact external unblock conditions once and leave the overall goal active rather than claiming completion.
