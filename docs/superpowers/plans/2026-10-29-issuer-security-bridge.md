# Read-Only Issuer-to-Security Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a synthetic-tested, read-only same-date candidate bridge and report the actual saved source-cut mismatch.

**Architecture:** Extend the existing Nasdaq receipt loader to expose verified internal rows without changing its aggregate public output. Add a separate SEC receipt loader, then a standalone candidate classifier and CLI. No writer or canonical point-in-time package is involved.

**Tech Stack:** Python standard library, pytest, Git CLI, Makefile.

**Spec:** `docs/superpowers/specs/2026-10-29-issuer-security-bridge-design.md`

## Global constraints

- No network fetch or source-derived tracked fixture; real inputs remain ignored local captures.
- No change to `data/`, `config/`, `outputs/`, or `docs/assets/` in Git.
- All conclusions remain inspection-only and import/distribution held.
- No push, PR, merge, deploy, publish, purchase, or credential change.

## Review focus

- Matching HTTP dates must not be called an exact simultaneous source cut.
- A directory symbol appearing in two rows must enter ambiguity review, even when one is an ACT value.
- A repeated SEC ticker with distinct CIKs must not select one CIK.
- Multiple tickers under one CIK must not collapse into one security.
- A punctuation or secondary-symbol match must remain a lead, never a verified identity.

### Task 1: Expose verified directory rows

**Files:** Modify `src/us_listing_receipt_audit.py` and `tests/test_us_listing_receipt_audit.py`.

**Interface:** `load_us_listing_rows(snapshot_dir: Path) -> tuple[dict[str, object], list[dict[str, str]]]`. The first value is the unchanged public aggregate receipt report; the second contains verified non-test ACT/CQS/Nasdaq fields and source/venue fields for internal comparison.

- [ ] Add a synthetic test that fails because the loader does not yet exist; include test-issue exclusion and all three symbol fields.
- [ ] Implement the loader by parsing the same digest-checked bytes already used for the public receipt.
- [ ] Run the focused tests; verify the existing aggregate output is unchanged.

### Task 2: Verify the SEC association receipt

**Files:** Create `src/sec_association_receipt.py` and `tests/test_sec_association_receipt.py`.

**Interface:** `load_sec_association_receipt(capture_dir: Path) -> tuple[dict[str, object], list[dict[str, object]]]`. Return exact source metadata plus validated search-association rows. A repeated ticker is retained for the bridge to classify, not silently collapsed.

- [ ] Write failing synthetic tests for valid receipt, bad digest/schema/date, symlink, malformed row, and repeated ticker.
- [ ] Implement strict read-only receipt loading with bounded file sizes.
- [ ] Run the focused tests and replay the ignored real map without emitting row values.

### Task 3: Candidate bridge and CLI

**Files:** Create `src/issuer_security_bridge.py` and `tests/test_issuer_security_bridge.py`; modify `Makefile` and `ROADMAP.md`.

**Interface:** `build_issuer_security_bridge(directory_report, directory_rows, sec_report, sec_rows, *, top_n: int = 10) -> dict[str, object]`; CLI arguments `--directory-snapshot`, `--sec-capture`, `--top-n`. Exit 0 for a same-date inspection comparison, exit 2 for a verified cutoff mismatch or invalid input.

- [ ] Write failing synthetic tests for matching date, mismatch, ACT/secondary/notation leads, competing rows, repeated ticker/CIKs, multi-ticker CIK, unknown venue, and bounded deterministic queue.
- [ ] Implement the classifier and CLI; keep all eligibility and identity conclusions withheld.
- [ ] Run focused tests; replay real ignored receipts and record the expected cutoff-mismatch JSON under ignored local evidence.
- [ ] Run project tests and public/browser checks, review tracked scope, commit locally, and update the held release packet and PR draft.
