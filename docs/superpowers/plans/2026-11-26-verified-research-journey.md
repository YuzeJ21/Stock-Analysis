# Verified Research Journey Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans; continue inline.

**Goal:** Independently verify the complete research workflow without treating skipped or incomplete browser runs as success.

**Architecture:** A small pytest observer checks collection and all mandatory report phases; a fixed runner verifies the declared environment and executes existing cases under the artifact guard. CI runs the journey and full suite as separate checks.

**Tech Stack:** Python 3.12 CI, pytest, packaging, Playwright, Streamlit, Make, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-26-verified-research-journey-design.md`

## Global Constraints

- Reuse existing browser, source, calculation and persistence tests.
- No weakened assertions, skipped mandatory cases, provider requests or protected data changes.
- No merge, deployment, paid services or invented external evidence.

## Review Focus

- Setup/teardown failure, skip, xfail/XPASS or missing reports must not pass.
- Incomplete collection and collect-only invocations must not pass.
- An unrelated failing test must keep the whole bundle failed.
- Runtime/browser restrictions must report blocked before attempting the journey.
- Separate CI jobs must preserve the full-suite gate and exact-head checkout.

### Task 1: Implement a complete-evidence runner

**Files:** Create `src/research_journey_gate.py`, `tests/test_research_journey_gate.py`.

**Interfaces:** `JourneyEvidence(required_cases)` observes actual pytest phases; `check_runtime(pyproject_path)` checks installed declared requirements; `main()` executes the fixed journey bundle.

- [x] Write real subprocess pytest regressions for pass, skip, xfail/XPASS, missing case/call, setup/teardown failure and unrelated failure; observe RED.
- [x] Implement the observer and environment preflight, preserving nonzero exits; observe GREEN.

### Task 2: Verify and expose the release journey

**Files:** Modify `Makefile`, `.github/workflows/commercial-research-beta.yml`, `README.md`; add `docs/VERIFIED_RESEARCH_JOURNEY_RELEASE.md`.

**Interfaces:** `make research-journey-check` runs Task 1 with protected-artifact guarding; CI uses declared dev/workspace dependencies and Chromium.

- [x] Exercise the real Make command, confirming a blocked environment returns nonzero locally.
- [x] Run focused integration/storage and runner regressions; inspect the full-suite CI outcome without inferring success from partial runs.
- [x] Obtain an independent review, correct material findings, verify protected bytes, commit and sync the existing review branch.
- [ ] Inspect the exact-head journey CI result after synchronization; record remaining full-suite/external gates truthfully.
