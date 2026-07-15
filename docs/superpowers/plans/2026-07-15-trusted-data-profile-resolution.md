# Trusted-Data Profile Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every trusted-data pilot read honor the selected data profile and make the selected paths visible in CLI output.

**Architecture:** Reuse `src.paths.resolve_data_dir`, `resolve_outputs_dir`, and `format_path_context` at existing filesystem boundaries. Preserve current function APIs and default-profile behavior while eliminating direct `root / "data"` and `root / "outputs"` reads from `src/trusted_data_pilot.py`.

**Tech Stack:** Python 3, pathlib, pytest, Make, existing Stock Research Command Center path/profile helpers.

## Global Constraints

- Research-only; no investment advice, broker integration, trading, order routing, auto-trading, or direct buy/sell instructions.
- Do not fabricate or infer readiness, peers, fundamentals, estimates, or source evidence.
- Do not refresh providers, apply imports, or modify generated CSV/report/sample-report artifacts.
- Preserve default behavior when `STOCK_RESEARCH_DATA_PROFILE` is unset.
- Missing selected-profile evidence must fail closed and must not fall back to default files.

---

### Task 1: Lock Profile Selection With Failing Tests

**Files:**
- Modify: `tests/test_trusted_data_pilot.py`

**Interfaces:**
- Consumes: `load_trusted_data_pilot_candidates(root: Path, ...)` and CLI `main()`.
- Produces: regression coverage for profile-isolated candidates and visible path context.

- [ ] **Step 1: Add a profile-isolation fixture**

Create default worklists/readiness where MU is blocked and local worklists/readiness where MU is already peer-ready. Set `STOCK_RESEARCH_DATA_PROFILE=local` with `monkeypatch`.

- [ ] **Step 2: Add the candidate assertion**

```python
candidates = load_trusted_data_pilot_candidates(root=tmp_path, top_n=10)
assert "MU" not in {candidate.ticker for candidate in candidates}
```

- [ ] **Step 3: Add a CLI path-context assertion**

Invoke `main()` with the local profile and assert the output includes the resolved `data/local` and `outputs/local` paths.

- [ ] **Step 4: Run the new tests and verify failure**

Run: `python3 -m pytest tests/test_trusted_data_pilot.py -k 'profile' -q`

Expected: failure because trusted-data still reads default paths and does not print path context.

---

### Task 2: Replace Direct Data And Output Reads

**Files:**
- Modify: `src/trusted_data_pilot.py`
- Test: `tests/test_trusted_data_pilot.py`

**Interfaces:**
- Consumes: `resolve_data_dir(project_root=root)`, `resolve_outputs_dir(project_root=root)`, and `format_path_context(project_root=root)` from `src.paths`.
- Produces: profile-isolated trusted-data candidates, packets, boards, lane summaries, and evidence rows.

- [ ] **Step 1: Import existing path helpers**

```python
from src.paths import format_path_context, resolve_data_dir, resolve_outputs_dir
```

- [ ] **Step 2: Resolve paths at each filesystem boundary**

Replace direct data reads with `resolve_data_dir(project_root=root) / ...` and direct output reads with `resolve_outputs_dir(project_root=root) / ...`. Cover SEC caches, fundamentals and optional rows, reviewed proofs, imports, rejected reports, readiness reports, worklists, and stock reports.

- [ ] **Step 3: Print path context once in the CLI**

At startup, print:

```python
print(format_path_context(project_root=Path.cwd()))
```

before rendering the selected trusted-data command.

- [ ] **Step 4: Prohibit silent fallback**

Do not add any fallback from the resolved profile paths to `root / "data"` or `root / "outputs"`.

- [ ] **Step 5: Run focused tests**

Run: `python3 -m pytest tests/test_trusted_data_pilot.py tests/test_paths.py -q`

Expected: all tests pass.

---

### Task 3: Verify Live Profile Truth And Release Gates

**Files:**
- Modify only if a test exposes a defect: `src/trusted_data_pilot.py`, `tests/test_trusted_data_pilot.py`

**Interfaces:**
- Consumes: the completed profile-aware trusted-data command.
- Produces: fresh evidence that local MU is no longer returned as executable peer work.

- [ ] **Step 1: Run the local-profile candidate command**

Run: `STOCK_RESEARCH_DATA_PROFILE=local make trusted-data-pilot-candidates TOP_N=10`

Expected: output names `data/local` and `outputs/local`; MU is not reported as a peer blocker when local readiness says `peer_ready=True`.

- [ ] **Step 2: Run focused and full verification**

Run:

```bash
python3 -m pytest tests/test_trusted_data_pilot.py tests/test_paths.py tests/test_launchers.py -q
python3 -m pytest tests -q
make public-wording-check
make public-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
```

Expected: all commands exit 0; only intentional source/docs/test files are dirty.

- [ ] **Step 3: Review exact release scope**

Run: `git diff -- src/trusted_data_pilot.py tests/test_trusted_data_pilot.py docs/superpowers/specs/2026-07-15-trusted-data-profile-resolution-design.md docs/superpowers/plans/2026-07-15-trusted-data-profile-resolution.md`

Expected: no generated data or report changes.

- [ ] **Step 4: Stage, check, commit, and push**

Stage only the four intentional files, run `make staged-hygiene-check` and `git diff --cached --check`, commit with `Make trusted-data pilot profile-aware`, push `main`, and verify `origin/main...HEAD` is `0 0`.
