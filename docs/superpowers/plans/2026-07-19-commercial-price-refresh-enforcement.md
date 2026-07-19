# Commercial Price Refresh Enforcement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task by task.

**Goal:** Make every Commercial Research direct price refresh fail closed unless the exact reachable and selected provider independently has approved commercial rights and registered `prices` scope.

**Architecture:** Add stable identities to concrete price sources, make the ladder validate and preserve exact child identity, and reuse the commercial field-scope review at both construction and mutation boundaries. Research mode remains compatible; injected registries provide deterministic tests without changing checked-in rights or calling providers.

**Tech Stack:** Python 3.12, pandas, pytest, YAML source-rights registry

## Global Constraints

- Do not edit `config/source_rights.yml` or approve a provider.
- Do not call an external provider or run broad price/readiness refreshes.
- Do not generate or stage CSV, JSON, report, sample-report, screenshot, or timing churn.
- Keep exact-source rights, registered field scope, technical validity, and readiness independent.
- Use exact staging only and keep PR #113 open and draft.

---

### Task 1: Lock exact price-provider identity

**Files:**
- Modify: `src/data_update.py`
- Test: `tests/test_data_update.py`

**Step 1: Write failing identity tests**

Add assertions that the six concrete implementations expose these exact IDs: `stooq`, `yahoo`, `fmp`, `alpha_vantage`, `finnhub`, and `ibkr`. Add a ladder test proving a caller label that differs from the child's exact ID raises `ValueError`.

**Step 2: Run the narrow tests and confirm RED**

Run:

```bash
python3 -m pytest tests/test_data_update.py -q -k 'source_id or ladder_rejects'
```

Expected: failures because the identities and ladder invariant do not yet exist.

**Step 3: Implement the identity contract**

Add `source_id` to `PriceHistorySource` and each concrete implementation. Add a helper that reads a nonblank exact ID. In `PriceSourceLadder.__init__`, require every route label to equal its child's `source_id`; store the possible IDs and a separate `last_source_id`. Set the latter only when that child returns usable rows.

**Step 4: Run the narrow tests and confirm GREEN**

Run the command from Step 2 and the existing ladder tests:

```bash
python3 -m pytest tests/test_data_update.py -q -k 'PriceSourceLadder or source_id or ladder'
```

### Task 2: Enforce commercial rights before provider construction

**Files:**
- Modify: `src/data_update.py`
- Test: `tests/test_data_update.py`

**Step 1: Write failing construction tests**

Build injected registries with `build_source_rights_registry`. Prove that:

- an exact commercial provider with unknown/unapproved rights raises `commercial_price_source_review_required`;
- an approved provider without `prices` scope raises `commercial_price_scope_review_required`;
- automatic commercial construction retains only independently approved and scoped legs;
- an automatic ladder with no eligible leg fails closed.

Do not fetch data in these tests.

**Step 2: Run the construction tests and confirm RED**

```bash
python3 -m pytest tests/test_data_update.py -q -k 'commercial and make_price_source'
```

**Step 3: Implement the shared review and construction filter**

Import `commercial_mode_enabled` and `review_commercial_field_scope`. Add a deterministic review helper that distinguishes rights failure from missing `prices` scope. Extend `make_price_source(provider, *, commercial_mode=None, rights_registry=None)`. In commercial mode, review exact providers before construction and build the auto ladder from lazy provider factories only after filtering each exact ID. Preserve the existing order and behavior in research mode.

**Step 4: Run the construction tests and confirm GREEN**

Run the command from Step 2, then all source-construction tests.

### Task 3: Enforce supplied and selected sources before mutation

**Files:**
- Modify: `src/data_update.py`
- Test: `tests/test_data_update.py`

**Step 1: Write failing mutation-boundary tests**

Add spy sources and temporary paths proving:

- a supplied source without exact ID fails before `fetch_history()`;
- an unapproved or scope-incomplete supplied source fails before fetch;
- no canonical or status file exists after either failure;
- an approved and scoped supplied source retains the existing successful refresh behavior;
- a source that changes its selected exact identity during fetch raises `commercial_price_source_changed` before canonical/status mutation.

**Step 2: Run the boundary tests and confirm RED**

```bash
python3 -m pytest tests/test_data_update.py -q -k 'commercial and update_local_price_data'
```

**Step 3: Implement pre-fetch and post-fetch checks**

Extend `update_local_price_data(..., commercial_mode=None, rights_registry=None)`. Resolve every reachable exact source before loading tickers or fetching and review it once. After a nonempty response, resolve the actual selected source, require it to be in the pre-reviewed set, and repeat the exact rights/scope decision before appending rows or status. Missing, changed, or composite identity must raise before mutation.

**Step 4: Run focused regression tests and confirm GREEN**

```bash
python3 -m pytest tests/test_data_update.py tests/test_commercial_source_rights.py -q
```

### Task 4: Record the verified boundary

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/METHODOLOGY.md`
- Modify: `docs/PROVENANCE_CONTRACT.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Test: `tests/test_public_v1_release_docs.py` if existing contract assertions need extension

**Step 1: Add documentation contract assertions where appropriate**

Require public/internal documentation to state that direct commercial price refresh needs exact-provider approved rights and registered `prices` scope, while no provider approval, row lineage, current readiness, or market operation is implied.

**Step 2: Update the roadmap and contracts**

Record this as a verified local enforcement slice. Keep price lineage, atomic apply, an approved provider, fresh readiness, hosted beta evidence, reviewer validation, calibration, and operating controls open.

**Step 3: Run documentation checks**

```bash
python3 -m pytest tests/test_public_v1_release_docs.py -q
make public-wording-check
make commercial-beta-check
```

### Task 5: Verify, commit, push, and update draft PR #113

**Files:** All intentionally changed files above only.

**Step 1: Run fresh focused and full verification**

```bash
python3 -m pytest tests/test_data_update.py tests/test_commercial_source_rights.py -q
python3 -m pytest tests -q
make dashboard-smoke
make research-render-smoke
make public-wording-check
make public-check
make commercial-beta-check
make commercial-beta-release-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
```

Expected: engineering checks pass; pilot/readiness verdict may remain truthfully blocked solely by declared stale or unavailable evidence.

**Step 2: Confirm generated-artifact hygiene**

Compare the tracked generated-artifact digest to the baseline, inspect `git status`, and ensure no generated CSV, JSON, report, sample-report, screenshot, or timing file changed.

**Step 3: Stage exact files and verify staging**

Stage only the implementation, tests, ROADMAP, methodology/provenance docs, continuation prompt, design, and plan files. Run:

```bash
make staged-hygiene-check
git diff --cached --check
```

**Step 4: Commit and push the coherent slice**

Create one implementation commit, push only `codex/personal-research-mode-mvp`, and verify zero ahead/behind against its remote.

**Step 5: Update and verify PR #113**

Add a concise audit-resolution note with scope, tests, truthful open boundaries, and generated-artifact exclusion. Keep the PR draft. Confirm the PR head matches the pushed commit and inspect current hosted checks without merging or deploying.
