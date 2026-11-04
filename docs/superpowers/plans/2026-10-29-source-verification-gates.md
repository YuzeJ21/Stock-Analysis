# Source Verification Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two read-only, synthetic-tested verification commands for the held release baseline and dated U.S. listing receipts.

**Architecture:** Keep release-path integrity and listing-receipt validation in separate modules. Each emits a bounded JSON verdict and never grants source rights or mutates data.

**Tech Stack:** Python standard library, pytest, Git CLI, Makefile.

**Spec:** `docs/superpowers/specs/2026-10-29-source-verification-gates-design.md`

## Global constraints

- No canonical data, readiness, rights-registry, generated-output, or source capture changes.
- No network request or raw source-derived test fixture.
- A passing check is an integrity or receipt result only; distribution and import stay held.
- No push, PR, merge, deploy, purchase, publication, or credential change.

## Review focus

- An added then deleted sensitive blob in branch history must still be detected.
- A duplicate or traversing manifest path must fail closed before reading outside the repo.
- A corrupt or missing disposition row must not be interpreted as approved.
- A directory test issue must be excluded, not counted as a listing.
- A matching symbol with different or unknown venue/date must not become a company identity.

### Task 1: Release baseline integrity audit

**Files:** Create `src/release_baseline_audit.py`, `tests/test_release_baseline_audit.py`.

**Interface:** `build_release_baseline_audit(repo_root: Path, inventory_path: Path, disposition_path: Path, base_ref: str, reviewed_history_path: Path) -> dict[str, object]`; CLI args `--repo-root`, `--inventory`, `--disposition`, `--reviewed-history`, `--base-ref`, JSON stdout, exit 0 only for valid integrity with held rights, exit 2 otherwise.

- [ ] Write synthetic tests for matching manifests, changed hash, path-set drift, duplicate/traversing path, disposition mismatch, unlisted added-then-deleted or reused Git blob path, and rights-registry drift.
- [ ] Run new tests and confirm the initial failure.
- [ ] Implement the strict read-only audit and CLI.
- [ ] Run new tests and confirm all pass.
- [ ] Replay the ignored 114-path files; verify exact set/hash counts and zero new sensitive history.

### Task 2: Dated listing receipt audit

**Files:** Create `src/us_listing_receipt_audit.py`, `tests/test_us_listing_receipt_audit.py`.

**Interface:** `build_us_listing_receipt_audit(snapshot_dir: Path) -> dict[str, object]`; CLI arg `--snapshot-dir`, JSON stdout, exit 0 only for validated receipts with import held, exit 2 otherwise.

- [ ] Write synthetic tests for matching pair, digest/manifest mismatch, bad date, missing column, unknown venue, duplicate symbol, and test-issue exclusion.
- [ ] Run new tests and confirm the initial failure.
- [ ] Implement the strict read-only parser and CLI.
- [ ] Run new tests and confirm all pass.
- [ ] Replay the ignored dated pair; verify source digests, 5,617 + 7,644 usable rows, 8 + 29 excluded test issues, and held import status.

### Task 3: Integration and release evidence

**Files:** Modify `Makefile`, `README.md`, `ROADMAP.md`; update ignored local release packet and held PR draft.

- [ ] Add read-only Makefile targets and concise neutral usage text.
- [ ] Run targeted tests, status/preview checks, diff/public wording hygiene, and automated desktop/phone browser gate.
- [ ] Run `make public-check` on final code and read its exact result.
- [ ] Review the whole diff for scope and source-derived material; commit locally and update the ignored evidence packet with exact head, hashes, and unresolved gates.
