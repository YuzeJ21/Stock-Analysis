# Independent Pilot Closeout Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make independently collected research-workflow feedback measurable without manufacturing pilot readiness.

**Architecture:** Extend the existing CSV with explicit provenance and aggregate it using a read-only standard-library CLI. Keep all product, source and hosting gates separate.

**Tech Stack:** Python 3.10+, csv, datetime, statistics, argparse, pytest, Make.

**Spec:** `docs/superpowers/specs/2026-11-26-independent-pilot-closeout-design.md`

## Global Constraints

- No input writes, raw feedback output, provider requests or readiness promotion.
- Preserve canonical data, source permissions and saved research.
- Only declared independent sessions qualify; never pool delivery modes or Git revisions.
- Actual user validation and hosted operation remain open.

## Review Focus

- Missing or contradictory consent must never contribute usage metrics.
- Duplicate or repeated sessions must not inflate independent reviewer counts.
- Failed or incomplete eligible attempts must remain in the initial denominator.
- Intent, earlier visits and visits in another cohort must not establish return use.
- Malformed data and error paths must not print paths, identifiers or free text.

### Task 1: Implement bounded, private, cohort-specific aggregation

**Files:** Create `src/pilot_feedback.py` and `tests/test_pilot_feedback.py`.

**Interfaces:** `summarize_pilot_feedback(path: Path, *, as_of: date) -> dict`; JSON-safe fixed categories and counts consumed by the CLI.

- [x] Write behavioral tests for a mixed log, failure-inclusive metrics, consent/retention, duplicate IDs, initial/return chronology, score missingness, cohort separation and private error output.
- [x] Run the new tests and observe failure because the module is absent.
- [x] Implement bounded CSV loading and the summary function, plus `main(argv=None) -> int` and a plain-text renderer.
- [x] Run `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_pilot_feedback.py`; expect all cases pass.

### Task 2: Connect the existing operator workflow

**Files:** Modify `Makefile`, `README.md`, `docs/PILOT_REVIEW_FEEDBACK_LOG_TEMPLATE.csv`, `docs/PILOT_REVIEW_FEEDBACK_TEMPLATE.md`, `docs/PILOT_FEEDBACK_CLOSEOUT_CHECKLIST.md`, `ROADMAP.md`; add `docs/PILOT_FEEDBACK_SUMMARY.md`.

**Interfaces:** `make pilot-feedback-summary INPUT=<external-log.csv> AS_OF=<date>` consumes Task 1; no change to the existing print-only targets.

- [x] Add a failing integration test for the Make entry point and an empty header-only template.
- [x] Add provenance columns, the Make target, and instructions for current tasks and scope-specific summaries.
- [x] Run new tests plus `tests/test_pilot_review_feedback_template.py` and `tests/test_private_beta_readiness.py`; expect all pass.
- [x] Attempt the repository suite and run public wording/hygiene and protected-data checks. Record the interrupted full run, baseline browser blocker and 145 passing focused tests in docs/INDEPENDENT_PILOT_CLOSEOUT_RELEASE.md; no full-suite pass is claimed.
- [x] Review fixes are complete; preserve the tested change in a review commit and synchronize only the authorized developer branch. The release note records the full-suite blocker; merging and release approval remain open.
