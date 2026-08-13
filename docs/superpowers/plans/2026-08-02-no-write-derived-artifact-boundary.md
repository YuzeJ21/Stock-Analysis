# No-Write Derived-Artifact Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every default readiness, universe, pipeline, status, onboarding, daily, dashboard-smoke, test, and verification path compute or validate in memory without changing repository data or generated artifacts, while retaining one explicit confirmed readiness materializer under ignored local storage.

**Architecture:** Keep canonical source CSVs as read-only inputs for this slice. Separate pure DataFrame composition from every writer, make the readiness and universe builders no-write by default, and route the only approved readiness materialization through a fixed `outputs/local/derived/<profile>/` adapter. Pure-function/writer-spy tests prove that default code paths do not invoke artifact writers; a before/after byte-manifest command guard independently rejects any persistent protected-path mutation left by default Make targets. Explicit source mutation commands such as universe apply and price refresh remain separate operator actions; they cannot be invoked transitively by validation or dashboard commands.

**Tech Stack:** Python 3.12, pandas, frozen dataclasses, pathlib, argparse, subprocess, pytest, Make, Streamlit smoke scripts, GitHub Actions.

## Global Constraints

- Work only in `/Users/yjian070/Documents/New project/.worktrees/personal-research-mode-mvp` on `codex/personal-research-mode-mvp`.
- Start every task by rechecking branch, HEAD, upstream divergence, draft PR #113, staged files, and the protected-artifact baseline.
- The 18 currently modified generated/canonical working-data paths are outside this implementation. At execution start, capture their exact current hashes and never restore, delete, stage, commit, replace, or normalize them during a task.
- Capture every existing file and directory under `data/`, `outputs/`, and `docs/assets/` outside the repository before Task 1 and compare after every task. This broader baseline includes the 18 dirty paths, `data/universe_active.csv`, all other canonical inputs, local/operator files, screenshots, reports, and timing evidence:

```bash
REPO_ARTIFACT_PATHS=/tmp/stock-research-slice1-artifact-paths.txt
REPO_ARTIFACT_DIRS=/tmp/stock-research-slice1-artifact-dirs.txt
REPO_ARTIFACT_LINK_PATHS=/tmp/stock-research-slice1-artifact-link-paths.txt
REPO_ARTIFACT_LINK_TARGETS=/tmp/stock-research-slice1-artifact-link-targets.txt
REPO_ARTIFACT_HASHES=/tmp/stock-research-slice1-artifact-hashes.sha256
find data outputs docs/assets -type f -print | LC_ALL=C sort > "$REPO_ARTIFACT_PATHS"
find data outputs docs/assets -type d -print | LC_ALL=C sort > "$REPO_ARTIFACT_DIRS"
find data outputs docs/assets -type l -print | LC_ALL=C sort > "$REPO_ARTIFACT_LINK_PATHS"
: > "$REPO_ARTIFACT_LINK_TARGETS"
while IFS= read -r artifact_link; do
  printf '%s\t%s\n' "$artifact_link" "$(readlink "$artifact_link")" >> "$REPO_ARTIFACT_LINK_TARGETS"
done < "$REPO_ARTIFACT_LINK_PATHS"
: > "$REPO_ARTIFACT_HASHES"
while IFS= read -r artifact_file; do
  shasum -a 256 "$artifact_file" >> "$REPO_ARTIFACT_HASHES"
done < "$REPO_ARTIFACT_PATHS"
```

- `make readiness-preview TOP_N=20` remains stdout-only and must not create a directory, bytecode, CSV, JSON, report, screenshot, or timing artifact.
- `make readiness` becomes a non-writing deprecated guard. It must exit nonzero and direct the operator to preview or explicit local materialization.
- `CONFIRM_MATERIALIZE=1 make readiness-materialize PROFILE=<default|demo|local>` is the only normal writer of a full current 11-report readiness package.
- `make readiness-snapshot PROFILE=<default|demo|local>` remains a temporary explicit proof-only compatibility writer for the selected profile's `ticker_readiness_report.previous.csv`; it composes the baseline in memory, binds profile/input identity, writes only that one file, and is never invoked by a default or composite command.
- `make reviewed-batch-compare PROFILE=<default|demo|local>` compares that saved prior row set with a newly composed in-memory current row set; it never needs a regenerated tracked current report.
- The materializer accepts no arbitrary output path and writes exactly one copy of each of the 11 readiness frames under `outputs/local/derived/<profile>/`.
- `make demo-data-build` is the only synthetic fixture-package exception: it is explicit, can target only the demo profile's existing fixture directories, and is never invoked by an ordinary, composite, validation, dashboard, or release command.
- Readiness composition must never repair or write `universe_master.csv`, `universe_active.csv`, or another canonical input.
- `refresh_universe` remains an explicit canonical-source maintenance operation. Nothing in this plan runs it.
- Default `status`, `pipeline`, `onboarding`, `daily`, `dashboard-smoke`, `test`, `verify`, and `validate-all` paths must leave every guarded repository artifact byte-for-byte unchanged, including `outputs/local/` and `outputs/staging/`. Direct writer-spy tests separately prove that default implementations never invoke artifact-writing interfaces; the manifest guard alone claims only detection of persistent end-state mutation.
- Source refresh, import apply, monthly materialization, track-record materialization, report export, screenshot capture, and timing capture remain explicit standalone operations; no composite validation target may invoke them.
- Preserve independent readiness for actuals, consensus, Revenue, EPS, valuation, catalysts, outcomes, backtesting, calibration, peers, and quant interpretation.
- Do not change any forecast, score, probability, recommendation, ranking, or source-rights contract. Numerical Beat/Miss probability stays withheld.
- Do not run readiness rebuilds, broad refreshes, generated report commands, or source apply commands while implementing this slice.
- Never use `git add -A`. Stage only the exact code, tests, scripts, Makefile, and documentation named by a task.
- Keep PR #113 open and draft. Do not merge or deploy.

---

## File Map

- Modify `src/universe_model.py`: no-write defaults and explicit canonical-writer separation.
- Modify `src/readiness_engine.py`: no-write default composition and deprecated direct CLI behavior.
- Create `src/readiness_materializer.py`: fixed-path, confirmed, non-duplicating readiness materialization.
- Create `src/readiness_source_boundary.py`: lexical profile-source confinement and the exact readiness-input identity contract.
- Create `src/no_write_artifact_guard.py`: in-memory before/after byte manifest that rejects persistent protected-path mutations from approved commands.
- Modify `src/report_generator.py`: compose the complete legacy pipeline result in memory and return frames.
- Modify `src/dashboard.py`: consume an in-memory pipeline result when an explicit refresh is requested instead of waiting for files.
- Modify `src/action_queue.py`: make read-only queue construction incapable of refreshing research-health files.
- Modify `src/research_health.py`: make research-health computation no-write by default.
- Modify `src/data_onboarding.py`: accept current in-memory analysis-output tickers instead of reading stale generated watchlists.
- Modify `src/research_decisions.py`: label in-memory decision lineage truthfully.
- Modify `src/dcf_readiness.py`: add an explicit read-only CLI path for composite onboarding.
- Modify `src/demo_data_builder.py`: make the explicit demo-package writer opt in deliberately without restoring an implicit readiness writer.
- Modify `src/readiness_comparison.py`: compare the saved prior snapshot with an explicitly selected current profile composed in memory.
- Modify `src/profile_context.py` and `src/project_status.py`: route stale-readiness recovery to no-write preview/materialization boundaries.
- Modify `Makefile`, `scripts/daily.sh`, `scripts/validate_all.sh`, `scripts/price_refresh_loop.sh`, and `scripts/smoke_dashboard.sh`: remove transitive generated writers from default/composite paths.
- Modify focused tests, including data-onboarding, research-health, research-decision, comparison, profile-context, and project-status suites; add `tests/test_readiness_materializer.py` and `tests/test_no_write_artifact_guard.py`.
- Modify `ROADMAP.md`, current operator/data documentation, and the continuation prompt only after the behavior is verified.

---

### Task 1: Make universe, readiness, and queue composition no-write by default

**Files:**
- Modify: `tests/test_universe_model.py`
- Modify: `tests/test_readiness_engine.py`
- Modify: `tests/test_action_queue.py`
- Modify: `src/universe_model.py`
- Modify: `src/readiness_engine.py`
- Modify: `src/action_queue.py`
- Modify: `src/research_health.py`
- Modify: `src/demo_data_builder.py`

**Interfaces:**
- `ensure_universe_files(..., write_outputs: bool = False)`
- `build_universe_coverage_report(..., write_output: bool = False)`
- `build_ticker_readiness_report(..., write_outputs: bool = False)`
- `build_action_queue_payload(...)` has no refresh/write parameter and is structurally read-only.
- `research_health.run(..., write_output: bool = False)`
- Explicit writers must pass their write choice; no writer may inherit it from a default.

- [ ] **Step 1: Write failing default-no-write universe tests**

Rename the two existing no-write tests so they omit the flags. Add a repairable canonical fixture and prove that writing only a coverage report cannot repair it:

```python
def test_ensure_universe_files_defaults_to_no_write(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    pd.DataFrame(
        [{"Ticker": "NVDA", "CompanyName": "NVIDIA", "DefaultPurpose": "Core Compounder"}]
    ).to_csv(data_dir / "universe.csv", index=False)
    before = _file_manifest(tmp_path)

    master, active = ensure_universe_files(tmp_path)

    assert set(master["ticker"]) == {"NVDA"}
    assert set(active["ticker"]) == {"NVDA"}
    assert _file_manifest(tmp_path) == before


def test_explicit_coverage_write_never_repairs_canonical_universe(tmp_path: Path):
    data_dir = tmp_path / "data"
    reports_dir = data_dir / "reports"
    reports_dir.mkdir(parents=True)
    pd.DataFrame([{"ticker": "A", "name": "Agilent", "asset_type": "etf"}]).to_csv(
        data_dir / "universe_master.csv", index=False
    )
    pd.DataFrame([{"ticker": "A", "company_name": "Agilent", "default_purpose": "Core Compounder"}]).to_csv(
        data_dir / "universe.csv", index=False
    )
    canonical_before = (data_dir / "universe_master.csv").read_bytes()

    report = build_universe_coverage_report(tmp_path, write_output=True)

    assert not report.empty
    assert (reports_dir / "universe_coverage_report.csv").exists()
    assert (data_dir / "universe_master.csv").read_bytes() == canonical_before
```

Update existing tests that intentionally exercise `refresh_universe` so only that operation is allowed to write canonical master/active files.

After each fixture is fully created, monkeypatch `src.universe_model._write_csv`
to raise if called and invoke both default universe builders. These writer-spy
assertions must fail on the current implementation and pass only when the
default composition paths cannot reach the canonical or coverage writer.

- [ ] **Step 2: Write failing readiness default/canonical-isolation tests**

Change `test_ticker_readiness_no_write_returns_reports_without_mutating_files` to omit `write_outputs=False`. Add a second test that calls `build_ticker_readiness_report(..., write_outputs=True)` with a repairable `universe_master.csv`, then verifies that any explicit derived write leaves canonical universe bytes unchanged. Keep the derived-write assertion only until Task 2 replaces it with the fixed materializer.

Add a default-path writer-spy test that monkeypatches
`src.readiness_engine._write` to raise and wraps both imported universe helpers
to assert `write_outputs=False` / `write_output=False`. The default builder must
return the complete frame mapping without reaching any of those writers.

- [ ] **Step 3: Write the hidden action-queue refresh regression**

In `tests/test_action_queue.py`, monkeypatch `run_research_health` to raise and call `build_action_queue_payload(...)`. The test must pass only when queue composition has no code path or parameter that invokes a refresh. Add a separate explicit-writer test proving `write_action_queue_output(..., refresh_research_health=True)` performs the deliberate refresh before it calls the pure builder.

In `tests/test_research_health.py`, omit `write_output` and compare the complete temporary-tree manifest before and after `run(...)`. The current repository default is `True`, so this test must fail until the default becomes `False`.

In that same default test, create all input fixtures before installing spies,
then monkeypatch `pandas.DataFrame.to_csv`,
`build_dcf_readiness_report`,
`build_optional_context_readiness_reports`, and
`build_ticker_readiness_report` in `src.research_health` to raise if invoked.
This directly proves the default research-health path cannot reach its current
derived-writer interfaces; the manifest remains independent end-state evidence.

In `tests/test_demo_data_builder.py`, prove the explicit synthetic package build targets only `data/demo/` and `outputs/demo/`, rejects any attempt to resolve the default or local profile, and is never referenced by an ordinary or composite Make target.

- [ ] **Step 4: Run the focused tests and confirm RED**

```bash
python3 -m pytest tests/test_universe_model.py tests/test_readiness_engine.py tests/test_action_queue.py tests/test_research_health.py tests/test_demo_data_builder.py -q
```

Expected: failures show the three unsafe defaults and coverage-to-canonical coupling.

- [ ] **Step 5: Implement the minimum default and call-site changes**

In `src/universe_model.py`:

- set both write defaults to `False`;
- make `build_universe_coverage_report` always call `ensure_universe_files(..., write_outputs=False)`;
- make `refresh_universe` explicitly call `ensure_universe_files(..., write_outputs=True)` and explicitly persist its coverage report; and
- make `--report-only` a stdout/read-only report preview;
- preserve `--ensure-only` as an explicit canonical-maintenance writer by passing `write_outputs=True`, and add a test that it truthfully reports the files it ensured; and
- leave canonical mutation only on the explicit refresh/apply and ensure-only maintenance paths.

In `src/readiness_engine.py`:

- set `write_outputs=False`;
- always call both universe helpers with their no-write setting, regardless of readiness output choice; and
- keep the temporary derived-write branch isolated from canonical files until Task 2 removes it from public reach.

In `src/action_queue.py`, remove `refresh_research_health` and every `run_research_health` call from `build_action_queue_payload`. `write_action_queue_output` may retain `refresh_research_health=False`; when a deliberate writer passes `True`, it calls `run_research_health(..., write_output=True)` explicitly before calling the pure builder. Add an assertion on that exact argument so the refresh cannot silently become a no-op after the research-health default changes. The builder itself can never trigger that side effect.

In `src/research_health.py`, change `run(..., write_output=False)` to the safe default and pass an explicit setting to any readiness call. In `src/demo_data_builder.py`, keep the curated synthetic demo build's write behavior explicit and validate that its resolved profile name is exactly `demo` before any removal, directory creation, or readiness write. This is the specification's fixture/package-build exception, not a normal readiness command, and it cannot target default/local real data.

- [ ] **Step 6: Run focused tests and confirm GREEN**

```bash
python3 -m pytest tests/test_universe_model.py tests/test_readiness_engine.py tests/test_action_queue.py tests/test_research_health.py tests/test_demo_data_builder.py tests/test_readiness_preview.py -q
```

- [ ] **Step 7: Check protected bytes and commit exactly Task 1**

```bash
shasum -a 256 -c "$REPO_ARTIFACT_HASHES"
find data outputs docs/assets -type f -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_PATHS" -
find data outputs docs/assets -type d -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_DIRS" -
find data outputs docs/assets -type l -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_LINK_PATHS" -
while IFS= read -r artifact_link; do printf '%s\t%s\n' "$artifact_link" "$(readlink "$artifact_link")"; done < "$REPO_ARTIFACT_LINK_PATHS" | diff -u "$REPO_ARTIFACT_LINK_TARGETS" -
git diff --check
git add -- src/universe_model.py src/readiness_engine.py src/action_queue.py src/research_health.py src/demo_data_builder.py tests/test_universe_model.py tests/test_readiness_engine.py tests/test_action_queue.py tests/test_research_health.py tests/test_demo_data_builder.py tests/test_readiness_preview.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Make readiness composition no-write by default"
```

---

### Task 2: Add the single explicit readiness materializer

**Files:**
- Create: `src/readiness_materializer.py`
- Create: `src/readiness_source_boundary.py`
- Create: `tests/test_readiness_materializer.py`
- Create: `tests/test_readiness_source_boundary.py`
- Modify: `src/readiness_engine.py`
- Modify: `tests/test_readiness_engine.py`

**Interfaces:**

```python
READINESS_REPORT_NAMES: tuple[str, ...] = (
    "universe_coverage_report",
    "price_coverage_report",
    "fundamentals_coverage_report",
    "dcf_readiness_report",
    "peer_readiness_report",
    "earnings_readiness_report",
    "analyst_estimates_readiness_report",
    "ticker_readiness_report",
    "feature_readiness_summary",
    "peer_unlock_worklist",
    "data_source_status",
)


@dataclass(frozen=True)
class ReadinessMaterializationResult:
    profile: str
    output_dir: Path
    files: tuple[Path, ...]
    row_counts: Mapping[str, int]


```

Implement `materialize_readiness_snapshot(base_dir: Path | str | None = None, *, profile: str, confirm_materialize: bool = False) -> ReadinessMaterializationResult`.

Implement `validate_readiness_source_boundary(project_root: Path, profile_name: str) -> DataProfile` in `src.readiness_source_boundary`. It validates the lexical named-profile directory and exact named readiness inputs before returning resolved paths; neither caller may call `resolve_data_profile` first and lose lexical symlink evidence.

- [ ] **Step 1: Write failing confirmation and path-confinement tests**

In `tests/test_readiness_materializer.py`, build a compact default/demo/local fixture and assert:

- missing confirmation raises `ReadinessMaterializationError` before creating `outputs/`;
- an empty or unknown profile fails closed;
- there is no `output_dir` parameter and no environment variable can redirect the destination;
- a confirmed run writes exactly the 11 expected `*.csv` files under `outputs/local/derived/<profile>/`;
- no compatibility copy appears in `data/`, `data/reports/`, or top-level tracked `outputs/`;
- the exact manifest delta is limited to the required `outputs/`, `outputs/local/`, `outputs/local/derived/`, and profile directories plus the 11 expected files; every path and byte outside that allowlisted destination is unchanged; and
- a second run reuses the same 11 paths and creates no suffixed, timestamped, report-copy, backup, or duplicate file.

In `tests/test_readiness_source_boundary.py`, cover symlinks at repository `data`, `data/demo`, `data/local`, every named source file, and an intermediate component. Test both links that remain inside the repository and links that escape it; both fail before any source read, builder call, output-directory creation, or write. Reject existing named inputs that are directories, devices, or other non-regular types. Missing optional named files remain explicit absent inputs rather than errors.

Add a fail-closed test for an unexpected pre-existing file inside the fixed destination. The materializer must refuse to overwrite or remove an unknown operator file.

Add symlink-escape tests for every destination path component and entry. Add fault/crash-injection tests before the backup rename, after the backup rename, immediately before publish, immediately after publish, and during cleanup. This is a crash-consistent, fail-closed two-phase directory publication, not a continuously visible atomic exchange: after the prior destination is renamed to backup, the canonical destination can be temporarily absent. A handled failure restores the prior complete snapshot; an unhandled interruption leaves explicit staging/backup evidence and a missing or complete canonical destination. The next run must fail closed instead of guessing. No test may ever expose a mixed old/new set, and readers must treat a missing canonical destination plus staging/backup evidence as unavailable pending operator recovery.

- [ ] **Step 2: Run the new tests and confirm RED**

```bash
python3 -m pytest tests/test_readiness_materializer.py tests/test_readiness_source_boundary.py -q
```

Expected: collection fails because `src.readiness_materializer` does not exist.

- [ ] **Step 3: Implement fixed-path materialization**

The implementation must:

1. validate only the named `default`, `demo`, or `local` input profile through `validate_readiness_source_boundary(root, profile)` before resolving or reading any source path;
2. reject `confirm_materialize is not True` before creating any directory;
3. call `build_ticker_readiness_report(root, data_dir=selected.data_dir, output_dir=selected.outputs_dir, write_outputs=False)`;
4. verify that the returned key set exactly equals `READINESS_REPORT_NAMES`;
5. resolve the repository root and derived root independently, prove the resolved derived root is beneath the resolved repository root, and reject any symlink in `outputs`, `outputs/local`, `outputs/local/derived`, the selected profile directory, staging, backup, or an expected file by checking each component with `lstat` before mutation;
6. set the destination to the fixed `<resolved derived root>/<selected.name>` path; refuse any existing snapshot unless it is exactly 11 regular, non-symlink files with the expected names and contains no subdirectories or extra entries;
7. serialize and fsync all 11 files inside one fixed-path sibling staging directory, then fsync that staging directory before publishing anything;
8. publish by a guarded, crash-consistent two-phase directory swap: fsync the derived parent, move the prior validated destination to a fixed sibling backup, fsync the parent, move the complete staging directory into place, fsync the parent again, restore and fsync the backup on any handled publication failure, and remove only the materializer-owned backup after durable success; do not describe this as a continuously visible atomic exchange because the destination can be absent between the two renames;
9. fail closed on a leftover staging/backup directory and provide a recovery message instead of guessing which set is authoritative; and
10. return deterministic sorted paths and row counts without writing a second manifest or compatibility copy.

Move the report-name tuple into `src/readiness_engine.py` so builder and materializer share one exact contract. Retain `write_outputs=True` only for the deliberately invoked curated demo-package builder during this transitional slice; no CLI, dashboard, default builder, composite target, or normal operator path may use it. The materializer itself always requests in-memory frames and writes only its fixed ignored destination.

- [ ] **Step 4: Run focused materializer and readiness tests**

```bash
python3 -m pytest tests/test_readiness_materializer.py tests/test_readiness_source_boundary.py tests/test_readiness_engine.py tests/test_universe_model.py tests/test_readiness_preview.py -q
```

- [ ] **Step 5: Prove ignored-path and duplicate-copy behavior**

```bash
git check-ignore -v outputs/local/derived/default/example.csv
python3 -m pytest tests/test_readiness_materializer.py -q -k "canonical or duplicate or fixed or confirm or publication or failure"
shasum -a 256 -c "$REPO_ARTIFACT_HASHES"
find data outputs docs/assets -type f -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_PATHS" -
find data outputs docs/assets -type d -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_DIRS" -
find data outputs docs/assets -type l -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_LINK_PATHS" -
while IFS= read -r artifact_link; do printf '%s\t%s\n' "$artifact_link" "$(readlink "$artifact_link")"; done < "$REPO_ARTIFACT_LINK_PATHS" | diff -u "$REPO_ARTIFACT_LINK_TARGETS" -
```

- [ ] **Step 6: Commit exactly Task 2**

```bash
git diff --check
git add -- src/readiness_engine.py src/readiness_materializer.py src/readiness_source_boundary.py tests/test_readiness_engine.py tests/test_readiness_materializer.py tests/test_readiness_source_boundary.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Add explicit local readiness materializer"
```

---

### Task 3: Replace readiness commands with fail-closed guards

**Files:**
- Modify: `src/readiness_engine.py`
- Modify: `src/readiness_materializer.py`
- Modify: `src/readiness_source_boundary.py`
- Modify: `Makefile`
- Modify: `tests/test_readiness_engine.py`
- Modify: `tests/test_readiness_materializer.py`
- Modify: `tests/test_readiness_source_boundary.py`
- Modify: `tests/test_launchers.py`
- Modify: `tests/test_public_v1_release_docs.py`

**Interfaces:**
- `src.readiness_engine.main(argv: list[str] | None = None) -> int`
- `READINESS_METHOD_VERSION: Final[str]`
- `src.readiness_source_boundary.readiness_input_identity(project_root: Path, profile_name: str) -> str`
- `src.readiness_materializer.main(argv: list[str] | None = None) -> int`
- `make readiness` returns `2` without writing; `make readiness-snapshot PROFILE=<name>` remains the explicit one-file, in-memory-baseline proof writer; the confirmed materializer is the only normal full-package writer.

- [ ] **Step 1: Write failing CLI and Make boundary tests**

Add tests that run the commands against a temporary project and compare the full file manifest before and after:

```python
def test_readiness_cli_default_is_a_nonwriting_deprecated_guard(tmp_path: Path, capsys):
    before = _file_manifest(tmp_path)
    exit_code = main(["--project-root", str(tmp_path)])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "deprecated" in captured.err.lower()
    assert "make readiness-preview TOP_N=20" in captured.err
    assert "CONFIRM_MATERIALIZE=1 make readiness-materialize PROFILE=" in captured.err
    assert _file_manifest(tmp_path) == before
```

Add equivalent subprocess tests for:

- `make readiness`;
- `make readiness-materialize` without `PROFILE`;
- `make readiness-materialize PROFILE=default` without confirmation; and
- `make readiness-snapshot` without `PROFILE`; and
- the confirmed target with a temporary project root through the Python CLI.

Run each module through `python3 -m`, not only by calling `main()` in process. Assert that `src.readiness_engine` and `src.readiness_materializer` propagate validation failures as shell exit `2`, and that no failed invocation changes the temporary tree. These tests fail if an `if __name__ == "__main__"` block calls `main()` without `raise SystemExit(main())`.

Add separate proof-compatibility tests for `make readiness-snapshot PROFILE=<name>`:

- it resolves the selected profile and writes only that profile's `reports/ticker_readiness_report.previous.csv`;
- it composes the baseline with `build_ticker_readiness_report(..., write_outputs=False)` and does not require or read a tracked current readiness report;
- a deliberately stale or contradictory tracked current report cannot affect the snapshot;
- every row carries one exact `snapshot_profile`, `snapshot_input_identity`, `snapshot_captured_at`, `snapshot_schema_version`, and `snapshot_method_version` value;
- the method version equals the current `READINESS_METHOD_VERSION`, and a method change must deliberately bump that constant;
- an empty in-memory readiness frame fails before serialization and leaves any existing baseline byte-identical;
- the input identity hashes the exact named readiness source/config inputs, their relative paths, bytes or absent markers, and the selected profile name in deterministic order;
- default, demo, and local snapshots cannot resolve into another profile's directory; and
- symlinks in lexical `data`, `data/demo`, `data/local`, every named readiness input, the selected profile, reports directory, snapshot path, or temporary path are rejected with `lstat` before any source read or write; and
- serialization, fsync, or replace failure leaves an existing baseline byte-identical and never exposes a partial file; and
- every canonical and current report path remains unchanged.

The Makefile structural test must assert that none of `status`, `pipeline`, `onboarding`, `daily`, `dashboard-smoke`, `test`, `verify`, `validate-all`, or `public-check` contains or transitively invokes either `readiness-materialize` or `readiness-snapshot`.

- [ ] **Step 2: Run focused tests and confirm RED**

```bash
python3 -m pytest tests/test_readiness_engine.py tests/test_readiness_materializer.py tests/test_readiness_source_boundary.py tests/test_launchers.py tests/test_public_v1_release_docs.py -q
```

- [ ] **Step 3: Implement the direct CLI guard**

Change `src.readiness_engine.main` to `main(argv: list[str] | None = None) -> int`. The default path and `--save-previous` regeneration path print the non-writing deprecation boundary to stderr and return `2`; they never call a builder. Define and document a fixed `READINESS_METHOD_VERSION`; any methodology change that can affect comparison fields must bump it. Preserve `--snapshot-only` only with a required `--profile`. It first calls the lexical source-boundary validator, then composes current readiness in memory with `write_outputs=False`, rejects an empty frame, binds the five snapshot metadata columns, writes and fsyncs a fixed sibling temporary file, atomically replaces only the selected profile's prior-snapshot proof file, fsyncs the reports directory, and exits after reporting its path, input identity, and method version. On a handled failure it removes only its own temporary file and preserves the prior baseline byte-for-byte. It never reads or regenerates the tracked current readiness report.

Extend `src.readiness_source_boundary` with `READINESS_SOURCE_FILENAMES` and `readiness_input_identity`. The exact tuple contains `config/readiness.yml` plus the selected profile's `universe_master.csv`, `universe_active.csv`, `universe.csv`, `holdings.csv`, `prices.csv`, `fundamentals.csv`, `peers.csv`, `peer_candidates.csv`, `earnings.csv`, and `analyst_estimates.csv`. Validate lexical confinement first, then hash the profile name, normalized repository-relative path, explicit missing marker, and existing regular-file bytes in sorted constant order. Tests mutate every input independently and prove the digest changes; adding an unrelated generated report must not change it.

Add `src.readiness_materializer.main(argv)` with `--project-root`, a required `--profile` choice, and an explicit `--confirm-materialize` flag. Confirmation must be checked in Python even when Make already checked it. Both modules end with `raise SystemExit(main())` so returned error codes reach subprocess and Make callers.

- [ ] **Step 4: Update the Make targets and help text**

Add `readiness-materialize` to `.PHONY`, keep the existing preview recipe byte-for-byte, and use this boundary:

```make
readiness:
	@echo "Deprecated no-write guard: use make readiness-preview TOP_N=20 for inspection." >&2
	@echo "For an intentional ignored snapshot: CONFIRM_MATERIALIZE=1 make readiness-materialize PROFILE=<default|demo|local>" >&2
	@exit 2

readiness-materialize:
ifndef PROFILE
	$(error PROFILE is required: default, demo, or local)
endif
ifneq ($(CONFIRM_MATERIALIZE),1)
	$(error CONFIRM_MATERIALIZE=1 is required)
endif
	@PYTHONDONTWRITEBYTECODE=1 python3 -m src.readiness_materializer --project-root . --profile "$(PROFILE)" --confirm-materialize

readiness-snapshot:
ifndef PROFILE
	$(error PROFILE is required: default, demo, or local)
endif
	@PYTHONDONTWRITEBYTECODE=1 python3 -m src.readiness_engine --project-root . --profile "$(PROFILE)" --snapshot-only
```

- [ ] **Step 5: Run focused tests and prove both negative gates**

```bash
python3 -m pytest tests/test_readiness_engine.py tests/test_readiness_materializer.py tests/test_readiness_source_boundary.py tests/test_launchers.py tests/test_public_v1_release_docs.py -q
set +e
make readiness >/tmp/readiness-guard.stdout 2>/tmp/readiness-guard.stderr
READINESS_GUARD_EXIT=$?
set -e
test "$READINESS_GUARD_EXIT" -eq 2
shasum -a 256 -c "$REPO_ARTIFACT_HASHES"
find data outputs docs/assets -type f -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_PATHS" -
find data outputs docs/assets -type d -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_DIRS" -
find data outputs docs/assets -type l -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_LINK_PATHS" -
while IFS= read -r artifact_link; do printf '%s\t%s\n' "$artifact_link" "$(readlink "$artifact_link")"; done < "$REPO_ARTIFACT_LINK_PATHS" | diff -u "$REPO_ARTIFACT_LINK_TARGETS" -
```

Do not run `make readiness-snapshot` against the real dirty worktree during this plan. Its one-file, profile-bound, current-in-memory capture behavior is proved only in temporary fixtures.

- [ ] **Step 6: Commit exactly Task 3**

```bash
git diff --check
git add -- Makefile src/readiness_engine.py src/readiness_materializer.py src/readiness_source_boundary.py tests/test_readiness_engine.py tests/test_readiness_materializer.py tests/test_readiness_source_boundary.py tests/test_launchers.py tests/test_public_v1_release_docs.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Guard legacy readiness writer commands"
```

---

### Task 4: Preserve reviewed-batch proof with an in-memory current comparison

**Files:**
- Modify: `src/readiness_comparison.py`
- Modify: `src/reviewed_batch.py`
- Modify: `src/reviewed_batch_command_builder.py`
- Modify: `src/reviewed_batch_preflight.py`
- Modify: `src/readiness_queue_dashboard.py`
- Modify: `src/dashboard.py`
- Modify: `Makefile`
- Modify: `tests/test_readiness_comparison.py`
- Modify: `tests/test_reviewed_batch.py`
- Modify: `tests/test_reviewed_batch_command_builder.py`
- Modify: `tests/test_reviewed_batch_preflight.py`
- Modify: `tests/test_readiness_queue_dashboard.py`
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `tests/test_launchers.py`

**Interfaces:**
- `compare_readiness_snapshots(root, *, before=None, after=None, profile="default", top_n=25) -> ReadinessComparison`
- `before=None` resolves to the selected profile's `reports/ticker_readiness_report.previous.csv`; there is no cross-profile fallback.
- `after=None` means compose `ticker_readiness_report` for the selected profile in memory with `write_outputs=False`.
- Explicit `before`/`after` paths remain only as compatibility/test inputs and must still carry matching snapshot metadata; the Make and UI proof workflow never supplies them.
- `ReadinessComparison` carries `profile`, `before_input_identity`, `after_input_identity`, `readiness_method_version`, and an `after_source` that truthfully identifies `in-memory readiness profile=<profile>` or the explicit fixture path.

- [ ] **Step 1: Write failing in-memory comparison tests**

In `tests/test_readiness_comparison.py`, create a saved prior snapshot plus a small current-profile source fixture. Monkeypatch or invoke the real readiness builder and assert:

- the default comparison passes the selected profile's resolved data and output directories with `write_outputs=False`;
- `before=None` resolves inside the selected profile, and default/demo/local cross-profile snapshots are rejected;
- no current `data/reports/ticker_readiness_report.csv` is required;
- a deliberately contradictory tracked current report cannot change the comparison result;
- changed tickers and count deltas come from the freshly composed frame;
- `after_source` identifies the in-memory profile and the proof scaffold records that label;
- missing prior snapshot fails closed and points only to `make readiness-snapshot PROFILE=<same-profile>`;
- missing/mixed snapshot metadata, unknown schema versions, empty snapshots, inconsistent row-level identity values, and a snapshot method version different from current `READINESS_METHOD_VERSION` fail closed;
- current composition failure returns a truthful blocked result without falling back to a tracked report; and
- the complete temporary-tree manifest remains byte-identical.

Keep one explicit-`after` fixture test so deterministic historical unit tests can compare two supplied files without changing the public workflow.

- [ ] **Step 2: Write failing proof-workflow command tests**

Update reviewed-batch, preflight, command-builder, readiness-queue, dashboard, and launcher tests so the executable sequence is:

```text
make readiness-snapshot PROFILE=<default|demo|local>
<reviewed validate / preview / approved apply>
make reviewed-batch-compare PROFILE=<default|demo|local> LANE=<lane> BATCH_ID=<id> REVIEW_DATE=<yyyy-mm-dd>
```

Assert that no current proof card, Make help line, preflight row, or reviewed-batch command builder inserts `make readiness` between apply and compare. The snapshot command remains explicit and single-file; comparison is no-write.

- [ ] **Step 3: Run focused tests and confirm RED**

```bash
python3 -m pytest tests/test_readiness_comparison.py tests/test_reviewed_batch.py tests/test_reviewed_batch_command_builder.py tests/test_reviewed_batch_preflight.py tests/test_readiness_queue_dashboard.py tests/test_dashboard_helpers.py tests/test_launchers.py -q -k "readiness or reviewed_batch or comparison or proof"
```

- [ ] **Step 4: Implement current-profile in-memory comparison**

Validate the selected profile through `validate_readiness_source_boundary(root, profile)` before resolving `before=None` or reading any source. Validate the snapshot metadata and method version against current `READINESS_METHOD_VERSION`, call `build_ticker_readiness_report(root, data_dir=profile.data_dir, output_dir=profile.outputs_dir, write_outputs=False)`, compute the current input identity with the same Task 3 helper, reject an empty current frame, convert only the returned ticker-readiness frame to comparison rows, and never inspect the tracked current report in this mode. Add `--profile` with exact `default`, `demo`, and `local` choices. `main()` returns nonzero for source confinement, missing-before, identity/schema/method, cross-profile, empty-current, or current-composition blockers and ends with `raise SystemExit(main())`.

Keep the saved prior snapshot's path in the result. Add `after_source`, `profile`, `before_input_identity`, `after_input_identity`, and `readiness_method_version` fields to `ReadinessComparison`; update renderers and proof scaffolds to describe the baseline capture and post-apply row set truthfully. Do not run saved-artifact freshness logic against either newly composed row set.

- [ ] **Step 5: Migrate the active proof workflow**

Make `reviewed-batch-compare` require `PROFILE` and pass `--profile "$(PROFILE)"`; a missing profile fails before comparison. Update the reviewed-batch command builder, preflight, queue, and dashboard proof surfaces named in this task to use comparison directly after an approved apply. Preserve historical ledger text as historical evidence; do not rewrite prior proof rows.

- [ ] **Step 6: Run focused tests and prove no-write behavior**

```bash
python3 -m pytest tests/test_readiness_comparison.py tests/test_reviewed_batch.py tests/test_reviewed_batch_command_builder.py tests/test_reviewed_batch_preflight.py tests/test_readiness_queue_dashboard.py tests/test_dashboard_helpers.py tests/test_launchers.py -q -k "readiness or reviewed_batch or comparison or proof"
shasum -a 256 -c "$REPO_ARTIFACT_HASHES"
find data outputs docs/assets -type f -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_PATHS" -
find data outputs docs/assets -type d -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_DIRS" -
find data outputs docs/assets -type l -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_LINK_PATHS" -
while IFS= read -r artifact_link; do printf '%s\t%s\n' "$artifact_link" "$(readlink "$artifact_link")"; done < "$REPO_ARTIFACT_LINK_PATHS" | diff -u "$REPO_ARTIFACT_LINK_TARGETS" -
```

Do not run `make readiness-snapshot` against the real worktree. The single-file writer and the post-apply in-memory comparison are exercised in temporary fixtures.

- [ ] **Step 7: Commit exactly Task 4**

```bash
git diff --check
git add -- src/readiness_comparison.py src/reviewed_batch.py src/reviewed_batch_command_builder.py src/reviewed_batch_preflight.py src/readiness_queue_dashboard.py src/dashboard.py Makefile tests/test_readiness_comparison.py tests/test_reviewed_batch.py tests/test_reviewed_batch_command_builder.py tests/test_reviewed_batch_preflight.py tests/test_readiness_queue_dashboard.py tests/test_dashboard_helpers.py tests/test_launchers.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Compare reviewed-batch readiness in memory"
```

---

### Task 5: Convert the report pipeline and explicit dashboard refresh to in-memory frames

**Files:**
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `tests/test_data_onboarding.py`
- Modify: `tests/test_research_decisions.py`
- Modify: `src/report_generator.py`
- Modify: `src/dashboard.py`
- Modify: `src/data_onboarding.py`
- Modify: `src/research_decisions.py`

**Interfaces:**

Implement `run(base_dir: Path | None = None, *, data_dir: Path | None = None, output_dir: Path | None = None) -> dict[str, object]`. The returned mapping contains `frames`, `row_counts`, `warnings`, and path labels; this function never creates or modifies a file.

- [ ] **Step 1: Rewrite the pipeline contract test first**

Replace `test_report_generator_creates_outputs` with `test_report_generator_returns_complete_frames_without_writing`. Capture `_file_manifest(tmp_path)` after fixture creation, call `run(tmp_path)`, and assert:

- the expected pipeline, research-health, optional-context, and 11 readiness keys are present in `result["frames"]`;
- `result["row_counts"]` has exactly the same keys as `result["frames"]`, and every count equals the length of its frame;
- the same method, allowed-state, reason, missing-data, and banned-word assertions run directly against the returned frames; and
- the file manifest is byte-identical and no new directory exists.

After fixture creation, install writer spies that make
`pandas.DataFrame.to_csv`, the imported `write_research_decisions`, and the
imported `write_purpose_evaluation_summary` raise if called. Wrap every
sub-builder that retains an explicit write flag and assert the pure pipeline
passes its no-write value. The test must fail before the refactor and return the
complete in-memory bundle without reaching any writer afterward.

Update missing-price, missing-fundamentals, missing-theme-map, and holdings-only tests to read `result["frames"]` rather than CSV paths.

In `tests/test_data_onboarding.py`, add an in-memory override regression. Create absent and deliberately contradictory legacy `final_watchlist.csv`/`momentum_leaders.csv` outputs, pass the same freshly composed ticker set to `build_ticker_coverage`, and assert identical `usable_for_monthly_picks` values in both cases. Also keep one legacy-call test proving omitted overrides still read the saved outputs for callers not migrated in this slice.

In `tests/test_research_decisions.py`, pass `source_mode="in_memory"` and assert the result uses the fixed in-memory lineage text and does not claim it came from local CSV readiness outputs. Keep the default `saved_csv` label test for unmigrated callers, and assert any unsupported mode raises before a row can render.

- [ ] **Step 2: Write the dashboard refresh regression**

Replace the file-writing fake in `test_pipeline_outputs_loader_regenerates_missing_core_outputs` with a fake in-memory bundle. Assert `load_pipeline_outputs(..., allow_refresh=True)` returns all frames while the output directory stays absent. Keep `test_dashboard_loaders_are_read_only_by_default` unchanged as a second boundary.

Make the fake accept no output/materialization flag and fail if the dashboard
attempts to pass one. Spy on `load_output` calls after the in-memory bundle is
returned and assert the dashboard does not retry disk loading or call any
dashboard writer. Together with the pipeline writer spies, this proves explicit
dashboard refresh remains composition-only rather than merely restoring files
before the final manifest check.

- [ ] **Step 3: Run focused tests and confirm RED**

```bash
python3 -m pytest tests/test_pipeline.py tests/test_dashboard_helpers.py tests/test_data_onboarding.py tests/test_research_decisions.py -q -k "pipeline or loaders_are_read_only or analysis_output_tickers or source_mode"
```

- [ ] **Step 4: Refactor report composition without writers**

In `src/report_generator.py`:

- remove every `mkdir`, `to_csv`, `write_research_decisions`, and `write_purpose_evaluation_summary` call;
- use `build_optional_context_readiness_frames`;
- call `build_ticker_readiness_report(..., write_outputs=False)`;
- build decisions with `build_research_decisions_frame(readiness, final_watchlist_df, source_mode="in_memory")`;
- build the purpose summary with `build_purpose_evaluation_summary(decisions, readiness, purpose_df)`; and
- return immutable-by-convention copied DataFrames in a `frames` mapping plus row counts and warnings.

Add `analysis_output_tickers: Collection[str] | None = None` to `src.data_onboarding.build_ticker_coverage`. When it is supplied, normalize and use only that set for `usable_for_monthly_picks`; do not load `final_watchlist.csv` or `momentum_leaders.csv`. When it is omitted, retain the legacy read behavior for unmigrated callers. The pure pipeline passes the union of tickers from its newly computed final-watchlist and momentum frames, so current in-memory coverage can never be contaminated by stale generated files.

Add `source_mode: Literal["saved_csv", "in_memory"] = "saved_csv"` to `build_research_decisions_frame`. `_source_freshness_summary` maps those two closed values to internally owned fixed wording; any other runtime value raises `ValueError`. The pure pipeline passes `source_mode="in_memory"`. This parameter changes wording only and cannot alter readiness, scores, forecasts, or allowed states.

Change CLI wording from `Generated outputs` to `In-memory pipeline result; no files written` and return success without claiming a path exists.

In `src/dashboard.py`, map each `PIPELINE_FILES` filename to the corresponding frame key. When `allow_refresh=True`, call the pure pipeline once and return those frames directly. Do not retry loading files and do not materialize a fallback.

- [ ] **Step 5: Run the focused matrix and confirm GREEN**

```bash
python3 -m pytest tests/test_pipeline.py -q
python3 -m pytest tests/test_dashboard_helpers.py -q -k "pipeline or loaders_are_read_only"
python3 -m pytest tests/test_data_onboarding.py tests/test_research_decisions.py tests/test_purpose_evaluation.py tests/test_readiness_engine.py -q
```

- [ ] **Step 6: Verify bytes and commit exactly Task 5**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m src.report_generator >/tmp/in-memory-pipeline.txt
shasum -a 256 -c "$REPO_ARTIFACT_HASHES"
find data outputs docs/assets -type f -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_PATHS" -
find data outputs docs/assets -type d -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_DIRS" -
find data outputs docs/assets -type l -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_LINK_PATHS" -
while IFS= read -r artifact_link; do printf '%s\t%s\n' "$artifact_link" "$(readlink "$artifact_link")"; done < "$REPO_ARTIFACT_LINK_PATHS" | diff -u "$REPO_ARTIFACT_LINK_TARGETS" -
git diff --check
git add -- src/report_generator.py src/dashboard.py src/data_onboarding.py src/research_decisions.py tests/test_pipeline.py tests/test_dashboard_helpers.py tests/test_data_onboarding.py tests/test_research_decisions.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Compute legacy pipeline views in memory"
```

---

### Task 6: Enforce persistent-state protection around default commands

**Files:**
- Create: `src/no_write_artifact_guard.py`
- Create: `tests/test_no_write_artifact_guard.py`
- Modify: `src/dcf_readiness.py`
- Modify: `tests/test_dcf_readiness.py`
- Modify: `Makefile`
- Modify: `scripts/daily.sh`
- Modify: `scripts/validate_all.sh`
- Modify: `scripts/price_refresh_loop.sh`
- Modify: `scripts/smoke_dashboard.sh`
- Modify: `tests/test_launchers.py`
- Modify: `tests/test_github_actions_workflow.py`

**Interfaces:**
- `ArtifactState(relative_path: str, kind: Literal["file", "directory", "symlink"], digest_or_target: str)`
- `capture_artifact_manifest(project_root: Path) -> tuple[ArtifactState, ...]`
- `run_guarded_command(project_root: Path, command: Sequence[str]) -> int`
- `main(argv: list[str] | None = None) -> int`

**Protected manifest scope:**

- every file and directory under `data/`;
- every file and directory under `outputs/`, including ignored `outputs/local/` and `outputs/staging/`; and
- every file and directory under `docs/assets/`, which covers checked-in screenshot evidence;
- every symbolic link under those roots, recorded with `lstat` type plus its exact link target; and
- creation, deletion, link-target change, type change, and byte change all count as mutation.

The guard never restores, deletes, stages, or rewrites a path. It reports the exact persistent end-state mutation and returns nonzero. A before/after manifest cannot observe a transient create/modify followed by restoration, so this guard must never be cited alone as proof that no writer ran. Tasks 1 and 5 add direct writer-spy and pure-composition tests for that stronger claim. The explicit readiness materializer does not run inside this default-command guard; its separate tests enforce the single narrow `outputs/local/derived/<profile>/` allowlist. App-data storage does not exist until Slice 4 and therefore is not silently treated as covered by this repository-only guard.

- [ ] **Step 1: Write guard unit tests**

Create tests for:

- stable command success preserves its child exit code `0`;
- stable command failure preserves the child nonzero exit code;
- changed bytes, a new protected file, a deleted protected file, and file-to-directory replacement each fail with exact relative paths;
- a new symlink, changed symlink target, symlink-to-file replacement, and symlink-to-directory replacement each fail without following the link outside the repository;
- changes under `outputs/local/derived/`, `outputs/staging/`, `data/local/`, and `docs/assets/` all fail for a default guarded command; and
- the manifest itself exists only in memory; and
- a transient write followed by exact restoration is explicitly documented as
  outside before/after-manifest detection, while the direct writer-spy suites
  remain the evidence that approved default implementations never invoke a
  writer.

Use tiny `python3 -c` subprocesses against a temporary root. Do not use shell interpolation or arbitrary command strings.

- [ ] **Step 2: Write Make graph and script regressions**

In `tests/test_launchers.py`, extract the recipes for `status`, `pipeline`, `onboarding`, `daily`, `dashboard-smoke`, `test`, `verify`, and `validate-all`. Assert they contain the no-write guard or invoke only guarded targets, and contain none of:

```text
--write-output
--refresh-artifacts
src.readiness_engine
readiness-materialize
price-refresh
monthly
track-record
research-decisions
project-status --write-output
```

Also assert `scripts/daily.sh` delegates only to `make daily`, `scripts/validate_all.sh` contains no monthly/track-record writer, and the real branch of `scripts/price_refresh_loop.sh` ends with `make readiness-preview TOP_N=20` plus `make status-check TOP_N=5`, not a readiness/project-status rebuild.

- [ ] **Step 3: Write the DCF read-only CLI test**

Add `--read-only` to the parser contract and test that it builds the frame, prints counts, and leaves the temporary tree byte-identical. The existing report-writing function remains explicit and is not called by any composite target.

- [ ] **Step 4: Run the focused tests and confirm RED**

```bash
python3 -m pytest tests/test_no_write_artifact_guard.py tests/test_launchers.py tests/test_dcf_readiness.py tests/test_github_actions_workflow.py -q
```

- [ ] **Step 5: Implement the guard**

`src.no_write_artifact_guard.main(argv)` accepts only `--project-root ROOT -- COMMAND [ARG ...]`. It resolves the root, uses `lstat`/`readlink` so manifests record symlinks without following them, captures relative path/type/digest-or-link-target records in memory, runs the exact argv list with `subprocess.run(..., cwd=root, check=False)`, captures the second manifest even after child failure, and:

- returns `3` after printing changed paths if the manifest differs;
- otherwise returns the child exit code; and
- never accepts a shell command string or `shell=True`.

End the module with `raise SystemExit(main())`. Add real `python3 -m src.no_write_artifact_guard` subprocess tests proving mutation exit `3`, stable child nonzero preservation, and argument-validation exit `2`; an in-process return-value assertion alone is insufficient.

Add `PYTHONDONTWRITEBYTECODE=1` to both the dashboard smoke import and Streamlit environment so smoke checks do not create bytecode.

- [ ] **Step 6: Convert composite targets to guarded read-only behavior**

Define one Make variable:

```make
NO_WRITE_GUARD = PYTHONDONTWRITEBYTECODE=1 python3 -m src.no_write_artifact_guard --project-root . --
```

Then enforce these meanings:

- `status`: guarded `python3 -m src.project_status --check --top-n ...`;
- `pipeline`: guarded pure `python3 -m src.report_generator`;
- `onboarding`: guarded price coverage-only, DCF `--read-only`, optional-context `--read-only`, readiness preview, data-sources check, onboarding coverage, research-health check, action-queue check, and project-status check;
- `daily`: guarded `pipeline`, `validate-data`, `onboarding`, and `status-check`; all source refresh and monthly/track-record writers stay separate;
- `dashboard-smoke`: guarded `scripts/smoke_dashboard.sh`;
- `test`: guarded full pytest;
- `verify`: one outer guard around `make test pipeline validate-data onboarding`;
- `validate-all`: one outer guard around `scripts/validate_all.sh`, whose contents use only safe checks and dashboard smoke.

Update `scripts/daily.sh` to call only `make daily`. Update the price refresh loop's pre/post copy so the explicit source mutation is followed by no-write preview and status inspection, with no tracked readiness snapshot or generated status rebuild.

- [ ] **Step 7: Run focused and command-boundary verification**

```bash
python3 -m pytest tests/test_no_write_artifact_guard.py tests/test_launchers.py tests/test_dcf_readiness.py tests/test_github_actions_workflow.py -q
make status TOP_N=5
make pipeline
make onboarding TOP_N=5
make daily TOP_N=5
make dashboard-smoke
make verify
make validate-all
shasum -a 256 -c "$REPO_ARTIFACT_HASHES"
find data outputs docs/assets -type f -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_PATHS" -
find data outputs docs/assets -type d -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_DIRS" -
find data outputs docs/assets -type l -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_LINK_PATHS" -
while IFS= read -r artifact_link; do printf '%s\t%s\n' "$artifact_link" "$(readlink "$artifact_link")"; done < "$REPO_ARTIFACT_LINK_PATHS" | diff -u "$REPO_ARTIFACT_LINK_TARGETS" -
```

Expected: every command succeeds and the guard reports no protected mutation. Do not substitute `make readiness` or another writer if a command fails; debug the exact transitive writer.

- [ ] **Step 8: Commit exactly Task 6**

```bash
git diff --check
git add -- src/no_write_artifact_guard.py src/dcf_readiness.py Makefile scripts/daily.sh scripts/validate_all.sh scripts/price_refresh_loop.sh scripts/smoke_dashboard.sh tests/test_no_write_artifact_guard.py tests/test_dcf_readiness.py tests/test_launchers.py tests/test_github_actions_workflow.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Guard default workflows against artifact churn"
```

---

### Task 7: Migrate inspection and stale-recovery command copy

**Files:**
- Create: `tests/test_readiness_inspection_copy.py`
- Modify: `src/artifact_freshness.py`, `src/auto_refresh_orchestrator.py`, `src/continuation_gate.py`, `src/coverage_expansion_loop.py`, `src/data_health_console.py`, `src/data_health_feature_readiness.py`, `src/data_health_metric_readiness_console.py`, `src/data_health_overview_console.py`, `src/data_health_peer_analysis.py`, `src/data_health_peer_mapping_studio.py`, `src/data_health_peer_operator_summary.py`, `src/data_health_peer_readiness.py`, `src/data_health_peer_unlock.py`, `src/data_health_recent_progress.py`, `src/pilot_readiness.py`, `src/profile_context.py`, `src/project_status.py`, `src/public_home_workflow.py`, `src/readiness_ops.py`, `src/readiness_preview.py`, `src/research_loop.py`, `src/review_metrics.py`, `src/session_source_preflight.py`, `src/single_stock_workflow.py`, `src/source_activation_guide.py`, `src/trusted_data_pilot.py`, and `src/universe_scope_workflow.py`
- Modify as behavior requires, and always verify: every existing same-name module suite listed in the RED/GREEN command below. `src/artifact_freshness.py` has no dedicated current suite, so the exhaustive table in `tests/test_readiness_inspection_copy.py` is its direct regression coverage.

**Interfaces:** Every inspection, missing-state, mixed-profile, and stale-state CTA uses `make readiness-preview TOP_N=<n>` and explicitly says preview does not refresh or persist readiness.

- [ ] **Step 1: Write failing behavior and inventory tests**

Build a table-driven test over every module named above. Assert that its stale/missing/inspection state never exposes the standalone legacy writer, never promises refreshed saved counts, and routes to preview. Keep exact profile labels in nearby copy so users know which in-memory state they are inspecting.

- [ ] **Step 2: Run RED**

```bash
python3 -m pytest \
  tests/test_readiness_inspection_copy.py \
  tests/test_auto_refresh_orchestrator.py \
  tests/test_continuation_gate.py \
  tests/test_coverage_expansion_loop.py \
  tests/test_data_health_console.py \
  tests/test_data_health_feature_readiness.py \
  tests/test_data_health_metric_readiness_console.py \
  tests/test_data_health_overview_console.py \
  tests/test_data_health_peer_analysis.py \
  tests/test_data_health_peer_mapping_studio.py \
  tests/test_data_health_peer_operator_summary.py \
  tests/test_data_health_peer_readiness.py \
  tests/test_data_health_peer_unlock.py \
  tests/test_data_health_recent_progress.py \
  tests/test_pilot_readiness.py \
  tests/test_profile_context.py \
  tests/test_project_status.py \
  tests/test_public_home_workflow.py \
  tests/test_readiness_ops.py \
  tests/test_readiness_preview.py \
  tests/test_research_loop.py \
  tests/test_review_metrics.py \
  tests/test_session_source_preflight.py \
  tests/test_single_stock_workflow.py \
  tests/test_source_activation_guide.py \
  tests/test_trusted_data_pilot.py \
  tests/test_universe_scope_workflow.py -q
```

- [ ] **Step 3: Migrate only inspection/stale copy**

Replace legacy refresh actions in the named modules with preview actions. Do not use preview where the surface is documenting post-apply proof; leave those cases for Task 8. A surface that cannot inspect the selected profile renders a truthful unavailable state with its exact missing profile/input condition.

- [ ] **Step 4: Run GREEN, verify baseline, and commit**

```bash
python3 -m pytest \
  tests/test_readiness_inspection_copy.py \
  tests/test_auto_refresh_orchestrator.py \
  tests/test_continuation_gate.py \
  tests/test_coverage_expansion_loop.py \
  tests/test_data_health_console.py \
  tests/test_data_health_feature_readiness.py \
  tests/test_data_health_metric_readiness_console.py \
  tests/test_data_health_overview_console.py \
  tests/test_data_health_peer_analysis.py \
  tests/test_data_health_peer_mapping_studio.py \
  tests/test_data_health_peer_operator_summary.py \
  tests/test_data_health_peer_readiness.py \
  tests/test_data_health_peer_unlock.py \
  tests/test_data_health_recent_progress.py \
  tests/test_pilot_readiness.py \
  tests/test_profile_context.py \
  tests/test_project_status.py \
  tests/test_public_home_workflow.py \
  tests/test_readiness_ops.py \
  tests/test_readiness_preview.py \
  tests/test_research_loop.py \
  tests/test_review_metrics.py \
  tests/test_session_source_preflight.py \
  tests/test_single_stock_workflow.py \
  tests/test_source_activation_guide.py \
  tests/test_trusted_data_pilot.py \
  tests/test_universe_scope_workflow.py -q
shasum -a 256 -c "$REPO_ARTIFACT_HASHES"
find data outputs docs/assets -type f -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_PATHS" -
find data outputs docs/assets -type d -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_DIRS" -
find data outputs docs/assets -type l -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_LINK_PATHS" -
while IFS= read -r artifact_link; do printf '%s\t%s\n' "$artifact_link" "$(readlink "$artifact_link")"; done < "$REPO_ARTIFACT_LINK_PATHS" | diff -u "$REPO_ARTIFACT_LINK_TARGETS" -
git diff --check
git add -- src/artifact_freshness.py src/auto_refresh_orchestrator.py src/continuation_gate.py src/coverage_expansion_loop.py src/data_health_console.py src/data_health_feature_readiness.py src/data_health_metric_readiness_console.py src/data_health_overview_console.py src/data_health_peer_analysis.py src/data_health_peer_mapping_studio.py src/data_health_peer_operator_summary.py src/data_health_peer_readiness.py src/data_health_peer_unlock.py src/data_health_recent_progress.py src/pilot_readiness.py src/profile_context.py src/project_status.py src/public_home_workflow.py src/readiness_ops.py src/readiness_preview.py src/research_loop.py src/review_metrics.py src/session_source_preflight.py src/single_stock_workflow.py src/source_activation_guide.py src/trusted_data_pilot.py src/universe_scope_workflow.py tests/test_readiness_inspection_copy.py tests/test_auto_refresh_orchestrator.py tests/test_continuation_gate.py tests/test_coverage_expansion_loop.py tests/test_data_health_console.py tests/test_data_health_feature_readiness.py tests/test_data_health_metric_readiness_console.py tests/test_data_health_overview_console.py tests/test_data_health_peer_analysis.py tests/test_data_health_peer_mapping_studio.py tests/test_data_health_peer_operator_summary.py tests/test_data_health_peer_readiness.py tests/test_data_health_peer_unlock.py tests/test_data_health_recent_progress.py tests/test_pilot_readiness.py tests/test_profile_context.py tests/test_project_status.py tests/test_public_home_workflow.py tests/test_readiness_ops.py tests/test_readiness_preview.py tests/test_research_loop.py tests/test_review_metrics.py tests/test_session_source_preflight.py tests/test_single_stock_workflow.py tests/test_source_activation_guide.py tests/test_trusted_data_pilot.py tests/test_universe_scope_workflow.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Route readiness inspection to no-write preview"
```

---

### Task 8: Migrate post-apply proof command copy

**Files:**
- Create: `tests/test_readiness_proof_copy.py`
- Modify: `src/dashboard.py`, `src/data_health_batch_console.py`, `src/data_health_coverage_delta.py`, `src/data_health_coverage_proof_summary.py`, `src/data_health_dcf_source_commands.py`, `src/data_health_dcf_source_packet.py`, `src/data_health_proof_checklist.py`, `src/data_health_proof_console.py`, `src/data_health_proof_ctas.py`, `src/data_health_proof_planner.py`, `src/data_health_queue_outcome.py`, `src/data_health_trusted_fundamentals_writer.py`, `src/data_health_trusted_pilot_console.py`, `src/dcf_input_proof_queue.py`, `src/dcf_readiness.py`, `src/decision_proof_queue.py`, `src/peer_mapping_source_review.py`, `src/price_history_proof_queue.py`, `src/readiness_comparison.py`, `src/readiness_queue_dashboard.py`, `src/research_decisions.py`, `src/reviewed_batch.py`, `src/reviewed_batch_command_builder.py`, `src/reviewed_batch_preflight.py`, `src/reviewed_data_proof.py`, `src/share_count_proof_queue.py`, and `src/stock_report.py`
- Modify as behavior requires, and always verify: every existing same-name module suite listed in the RED/GREEN command below; `tests/test_dashboard_helpers.py` is the direct dashboard suite.

**Interfaces:** Post-apply proof uses the same explicit profile for `make readiness-snapshot PROFILE=<profile>` and `make reviewed-batch-compare PROFILE=<profile> ...`; historical ledger command text is visible only as non-executable evidence.

- [ ] **Step 1: Write failing proof-copy tests**

Inventory every post-apply/proof field in the named modules. Assert it uses the bound snapshot-before/apply/in-memory-compare sequence, never inserts the legacy writer, never mixes profiles, and never offers a historical command string through a copy/run control.

- [ ] **Step 2: Run RED**

```bash
python3 -m pytest \
  tests/test_readiness_proof_copy.py \
  tests/test_dashboard_helpers.py \
  tests/test_data_health_batch_console.py \
  tests/test_data_health_coverage_delta.py \
  tests/test_data_health_coverage_proof_summary.py \
  tests/test_data_health_dcf_source_commands.py \
  tests/test_data_health_dcf_source_packet.py \
  tests/test_data_health_proof_checklist.py \
  tests/test_data_health_proof_console.py \
  tests/test_data_health_proof_ctas.py \
  tests/test_data_health_proof_planner.py \
  tests/test_data_health_queue_outcome.py \
  tests/test_data_health_trusted_fundamentals_writer.py \
  tests/test_data_health_trusted_pilot_console.py \
  tests/test_dcf_input_proof_queue.py \
  tests/test_dcf_readiness.py \
  tests/test_decision_proof_queue.py \
  tests/test_peer_mapping_source_review.py \
  tests/test_price_history_proof_queue.py \
  tests/test_readiness_comparison.py \
  tests/test_readiness_queue_dashboard.py \
  tests/test_research_decisions.py \
  tests/test_reviewed_batch.py \
  tests/test_reviewed_batch_command_builder.py \
  tests/test_reviewed_batch_preflight.py \
  tests/test_reviewed_data_proof.py \
  tests/test_share_count_proof_queue.py \
  tests/test_stock_report.py -q
```

- [ ] **Step 3: Migrate proof copy and historical rendering**

Use the Task 4 profile-bound comparison command everywhere current proof is actionable. Keep prior ledger rows byte-immutable, label their command cells `Historical command (not executable)`, and remove copy/run controls for those cells. Do not replace proof with preview; preview cannot prove a before/after change.

- [ ] **Step 4: Run GREEN, verify baseline, and commit**

```bash
python3 -m pytest \
  tests/test_readiness_proof_copy.py \
  tests/test_dashboard_helpers.py \
  tests/test_data_health_batch_console.py \
  tests/test_data_health_coverage_delta.py \
  tests/test_data_health_coverage_proof_summary.py \
  tests/test_data_health_dcf_source_commands.py \
  tests/test_data_health_dcf_source_packet.py \
  tests/test_data_health_proof_checklist.py \
  tests/test_data_health_proof_console.py \
  tests/test_data_health_proof_ctas.py \
  tests/test_data_health_proof_planner.py \
  tests/test_data_health_queue_outcome.py \
  tests/test_data_health_trusted_fundamentals_writer.py \
  tests/test_data_health_trusted_pilot_console.py \
  tests/test_dcf_input_proof_queue.py \
  tests/test_dcf_readiness.py \
  tests/test_decision_proof_queue.py \
  tests/test_peer_mapping_source_review.py \
  tests/test_price_history_proof_queue.py \
  tests/test_readiness_comparison.py \
  tests/test_readiness_queue_dashboard.py \
  tests/test_research_decisions.py \
  tests/test_reviewed_batch.py \
  tests/test_reviewed_batch_command_builder.py \
  tests/test_reviewed_batch_preflight.py \
  tests/test_reviewed_data_proof.py \
  tests/test_share_count_proof_queue.py \
  tests/test_stock_report.py -q
shasum -a 256 -c "$REPO_ARTIFACT_HASHES"
find data outputs docs/assets -type f -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_PATHS" -
find data outputs docs/assets -type d -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_DIRS" -
find data outputs docs/assets -type l -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_LINK_PATHS" -
while IFS= read -r artifact_link; do printf '%s\t%s\n' "$artifact_link" "$(readlink "$artifact_link")"; done < "$REPO_ARTIFACT_LINK_PATHS" | diff -u "$REPO_ARTIFACT_LINK_TARGETS" -
git diff --check
git add -- src/dashboard.py src/data_health_batch_console.py src/data_health_coverage_delta.py src/data_health_coverage_proof_summary.py src/data_health_dcf_source_commands.py src/data_health_dcf_source_packet.py src/data_health_proof_checklist.py src/data_health_proof_console.py src/data_health_proof_ctas.py src/data_health_proof_planner.py src/data_health_queue_outcome.py src/data_health_trusted_fundamentals_writer.py src/data_health_trusted_pilot_console.py src/dcf_input_proof_queue.py src/dcf_readiness.py src/decision_proof_queue.py src/peer_mapping_source_review.py src/price_history_proof_queue.py src/readiness_comparison.py src/readiness_queue_dashboard.py src/research_decisions.py src/reviewed_batch.py src/reviewed_batch_command_builder.py src/reviewed_batch_preflight.py src/reviewed_data_proof.py src/share_count_proof_queue.py src/stock_report.py tests/test_readiness_proof_copy.py tests/test_dashboard_helpers.py tests/test_data_health_batch_console.py tests/test_data_health_coverage_delta.py tests/test_data_health_coverage_proof_summary.py tests/test_data_health_dcf_source_commands.py tests/test_data_health_dcf_source_packet.py tests/test_data_health_proof_checklist.py tests/test_data_health_proof_console.py tests/test_data_health_proof_ctas.py tests/test_data_health_proof_planner.py tests/test_data_health_queue_outcome.py tests/test_data_health_trusted_fundamentals_writer.py tests/test_data_health_trusted_pilot_console.py tests/test_dcf_input_proof_queue.py tests/test_dcf_readiness.py tests/test_decision_proof_queue.py tests/test_peer_mapping_source_review.py tests/test_price_history_proof_queue.py tests/test_readiness_comparison.py tests/test_readiness_queue_dashboard.py tests/test_research_decisions.py tests/test_reviewed_batch.py tests/test_reviewed_batch_command_builder.py tests/test_reviewed_batch_preflight.py tests/test_reviewed_data_proof.py tests/test_share_count_proof_queue.py tests/test_stock_report.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Route readiness proof to in-memory comparison"
```

---

### Task 9: Enforce the complete runtime command-copy contract

**Files:**
- Create: `tests/test_readiness_command_copy.py`
- Modify: `src/readiness_engine.py`
- Modify: `Makefile`
- Modify: `tests/test_launchers.py`
- Modify: `tests/test_public_v1_release_docs.py`

**Interfaces:** Runtime source may expose preview, profile-bound baseline/comparison, or confirmed Advanced materialization. The standalone legacy command is named only by its own deprecated non-writing guard and never as an executable next action.

- [ ] **Step 1: Write the complete runtime scanner**

Scan every `src/**/*.py` file plus current Make help/recipes for the exact standalone token while excluding hyphenated safe targets. Fail with path and line for every offered action, refresh, rebuild, prerequisite, or proof use. Permit only the readiness guard's own same-line deprecated/non-writing explanation. If this scan finds a behavior belonging to Task 7 or 8, return to that task and add a focused regression before changing it.

- [ ] **Step 2: Run RED, close residuals, and rerun GREEN**

```bash
python3 -m pytest tests/test_readiness_command_copy.py tests/test_launchers.py tests/test_public_v1_release_docs.py -q
```

Update Make help to distinguish preview, required-profile baseline capture, profile-bound comparison, and confirmed Advanced materialization. The guard must never suggest it refreshes saved state.

- [ ] **Step 3: Verify baseline and commit**

```bash
python3 -m pytest tests/test_readiness_command_copy.py tests/test_launchers.py tests/test_public_v1_release_docs.py -q
shasum -a 256 -c "$REPO_ARTIFACT_HASHES"
find data outputs docs/assets -type f -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_PATHS" -
find data outputs docs/assets -type d -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_DIRS" -
find data outputs docs/assets -type l -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_LINK_PATHS" -
while IFS= read -r artifact_link; do printf '%s\t%s\n' "$artifact_link" "$(readlink "$artifact_link")"; done < "$REPO_ARTIFACT_LINK_PATHS" | diff -u "$REPO_ARTIFACT_LINK_TARGETS" -
git diff --check
git add -- Makefile src/readiness_engine.py tests/test_readiness_command_copy.py tests/test_launchers.py tests/test_public_v1_release_docs.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Enforce readiness command copy boundaries"
```

---

### Task 10: Reconcile current documentation and roadmap truth

**Files:**
- Modify: `DECISION_OUTPUT_MODEL.md`, `READINESS_MODEL.md`, `ROADMAP.md`, `docs/DASHBOARD_QA.md`, `docs/DATA_STRATEGY.md`, `docs/DIFF_HYGIENE_AUDIT.md`, `docs/METHODOLOGY.md`, `docs/OPERATOR_GUIDE.md`, `docs/PILOT_RUNBOOK.md`, `docs/PROVENANCE_CONTRACT.md`, `docs/PUBLIC_RELEASE_CHECKLIST.md`, `docs/SOURCE_ACTIVATION_GUIDE.md`, `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`, and `docs/internal/RESEARCH_DECISION_LAB_CONTINUATION_GOAL_PROMPT.md`
- Modify: `tests/test_readiness_command_copy.py`, `tests/test_public_v1_release_docs.py`
- Do not modify historical completed specs/plans or generated reports merely to replace old command text.

**Interfaces:** Current docs may describe the standalone legacy command only as a deprecated non-writing guard; inspection, proof, baseline, and materialization instructions use their exact new commands and profile requirements.

- [ ] **Step 1: Extend the scanner to all current docs and confirm RED**

Scan repository Markdown outside `docs/superpowers/**`, `data/**`, and `outputs/**`. Classify `docs/DIFF_HYGIENE_AUDIT.md` as historical only if the matching line is clearly labeled non-executable evidence; otherwise migrate it. Assert the approved no-write contract, demo exception, one-file bound baseline, in-memory comparison, and unchanged external evidence gates.

```bash
python3 -m pytest tests/test_readiness_command_copy.py tests/test_public_v1_release_docs.py -q
```

- [ ] **Step 2: Update current docs after runtime evidence passes**

Record Slice 1 implementation as complete but final verification as pending only after Tasks 1-9 and this task's focused checks pass. Do not mark the slice fully verified, release-gated, or exact-head complete in repository docs. Record Slice 2 as the provisional next stage: route-native Research Desk, Discover, Company Workbench, and Monitor operation without legacy generated outputs. Keep public `CSV-first` wording until that primary workflow is actually migrated and verified. Set the continuation prompt anchor to the already committed Task 9 HEAD or a later verified descendant; this documentation commit is naturally a later descendant.

- [ ] **Step 3: Run GREEN, wording, baseline, and commit**

```bash
python3 -m pytest tests/test_readiness_command_copy.py tests/test_public_v1_release_docs.py -q
make public-wording-check
git diff --check
shasum -a 256 -c "$REPO_ARTIFACT_HASHES"
find data outputs docs/assets -type f -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_PATHS" -
find data outputs docs/assets -type d -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_DIRS" -
find data outputs docs/assets -type l -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_LINK_PATHS" -
while IFS= read -r artifact_link; do printf '%s\t%s\n' "$artifact_link" "$(readlink "$artifact_link")"; done < "$REPO_ARTIFACT_LINK_PATHS" | diff -u "$REPO_ARTIFACT_LINK_TARGETS" -
git add -- DECISION_OUTPUT_MODEL.md READINESS_MODEL.md ROADMAP.md docs/DASHBOARD_QA.md docs/DATA_STRATEGY.md docs/DIFF_HYGIENE_AUDIT.md docs/METHODOLOGY.md docs/OPERATOR_GUIDE.md docs/PILOT_RUNBOOK.md docs/PROVENANCE_CONTRACT.md docs/PUBLIC_RELEASE_CHECKLIST.md docs/SOURCE_ACTIVATION_GUIDE.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md docs/internal/RESEARCH_DECISION_LAB_CONTINUATION_GOAL_PROMPT.md tests/test_readiness_command_copy.py tests/test_public_v1_release_docs.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Document no-write readiness operations"
```

---

### Task 11: Full verification, exact staging audit, push, and draft-PR evidence

**Files:**
- No repository file may be modified in this task. If verification changes a documented fact or finds a product defect, return to Task 10 or the relevant earlier task, add a failing test, make an exact commit, and restart Task 11 from Step 1 on the new HEAD.

- [ ] **Step 1: Run the focused Slice 1 matrix**

```bash
python3 -m pytest \
  tests/test_universe_model.py \
  tests/test_readiness_engine.py \
  tests/test_readiness_preview.py \
  tests/test_readiness_materializer.py \
  tests/test_readiness_source_boundary.py \
  tests/test_readiness_comparison.py \
  tests/test_readiness_command_copy.py \
  tests/test_readiness_inspection_copy.py \
  tests/test_readiness_proof_copy.py \
  tests/test_no_write_artifact_guard.py \
  tests/test_pipeline.py \
  tests/test_action_queue.py \
  tests/test_research_health.py \
  tests/test_demo_data_builder.py \
  tests/test_data_onboarding.py \
  tests/test_research_decisions.py \
  tests/test_purpose_evaluation.py \
  tests/test_reviewed_batch.py \
  tests/test_reviewed_batch_command_builder.py \
  tests/test_reviewed_batch_preflight.py \
  tests/test_readiness_queue_dashboard.py \
  tests/test_dcf_readiness.py \
  tests/test_dashboard_helpers.py \
  tests/test_stock_report.py \
  tests/test_source_activation_guide.py \
  tests/test_auto_refresh_orchestrator.py \
  tests/test_data_health_peer_mapping_studio.py \
  tests/test_data_health_trusted_pilot_console.py \
  tests/test_launchers.py \
  tests/test_profile_context.py \
  tests/test_project_status.py \
  tests/test_public_v1_release_docs.py \
  tests/test_github_actions_workflow.py -q
```

- [ ] **Step 2: Run the complete required gate matrix**

```bash
python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make research-accessibility-browser-check
make public-wording-check
make public-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
```

Do not run `make readiness`, `make readiness-snapshot`, a confirmed materializer against the real worktree, `make pipeline` in any legacy-writing form, a broad refresh, report export, screenshot writer, or timing writer as extra verification.

- [ ] **Step 3: Prove the complete protected baseline and stage state**

```bash
shasum -a 256 -c "$REPO_ARTIFACT_HASHES"
find data outputs docs/assets -type f -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_PATHS" -
find data outputs docs/assets -type d -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_DIRS" -
find data outputs docs/assets -type l -print | LC_ALL=C sort | diff -u "$REPO_ARTIFACT_LINK_PATHS" -
while IFS= read -r artifact_link; do printf '%s\t%s\n' "$artifact_link" "$(readlink "$artifact_link")"; done < "$REPO_ARTIFACT_LINK_PATHS" | diff -u "$REPO_ARTIFACT_LINK_TARGETS" -
git status --short --branch
git diff --cached --name-only
make staged-hygiene-check
git diff --cached --check
```

Expected: the only unstaged modifications outside the implementation are the same 18 protected paths; no generated/canonical path is staged.

- [ ] **Step 4: Run a review subagent against the exact implementation range**

Require the reviewer to inspect:

- all default builder and Make paths for hidden writes;
- canonical-universe isolation;
- materializer path confinement, confirmation, non-duplication, and failure behavior;
- action-queue and project-status transitive refreshes;
- dashboard and pipeline no-write behavior; and
- docs that could still tell an ordinary user to run a deprecated writer.

Resolve only actionable findings with a failing test and rerun the full matrix.

- [ ] **Step 5: Push only the approved branch and update the draft PR**

```bash
git push origin codex/personal-research-mode-mvp
git rev-list --left-right --count HEAD...origin/codex/personal-research-mode-mvp
gh pr view 113 --json number,state,isDraft,mergeable,headRefName,headRefOid,url,statusCheckRollup
```

Update PR #113 with the exact Slice 1 behavior, tests, protected-hash result, generated-artifact exclusions, and remaining external/local gates. Keep it draft.

- [ ] **Step 6: Require exact-head CI**

Wait for the PR's latest workflow run and prove its head SHA equals local `HEAD`. Do not claim completion from an older green run.

Only after that exact-head run passes may the PR update and handoff call Slice 1 fully verified. Do not create a post-CI repository edit merely to change status wording; any repository edit would create a new HEAD and require the complete Task 11 cycle again.

- [ ] **Step 7: Handoff the exact next executable slice**

Report:

- repository/PR/CI status;
- no-write behavior now shipped on the feature branch;
- exact files written by the explicit materializer and why they remain ignored/local;
- confirmation that the 18 protected files stayed byte-identical and unstaged;
- unchanged research, nowcast, probability, source-rights, hosted, reviewer, and market-validation boundaries; and
- exact next task: write and approve the Slice 2 plan for route-independent Personal Research workflows.

Overall A+C completion remains active after Slice 1. It is not complete until Slices 2-5 and applicable external gates have direct evidence.
