# SEC Fundamentals No-Write Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development for each behavior change. Track steps with checkbox (`- [ ]`) syntax.

**Goal:** Build a capped official-SEC comparison that exposes coherent annual actual candidates and their blockers without modifying canonical, staged, cached, readiness, or generated data.

**Architecture:** Extend the existing SEC adapter with true no-cache reads and private per-field provenance. Add a pure comparison module that reads canonical/staged headers, fetches only official SEC JSON in memory, classifies field coherence and rights, and prints deterministic JSON. Expose it through one Make target.

**Tech Stack:** Python 3.12, urllib, pandas, YAML-backed source-rights registry, argparse, JSON, pytest, Make.

## Global Constraints

- Maximum five explicit tickers; first audited cohort AAPL, AMZN, GOOG.
- Official SEC ticker-map and Companyfacts endpoints only.
- No provider fallback, canonical apply, import staging, cache write, readiness mutation, or rights change.
- Missing facts remain unavailable; derived values are labelled derived and blocked pending exact field-scope review.
- Stage only explicit source/docs/test/Make paths. Never stage `data/`, `outputs/`, caches, or imports.

### Task 1: True No-Cache SEC Adapter

**Files:**
- Modify: `src/providers/sec_companyfacts.py`
- Modify: `tests/test_sec_companyfacts.py`

- [ ] Write RED tests proving ticker-map and Companyfacts no-cache calls make the expected official request but create no cache directory or file.
- [ ] Add a `cache=False` ticker-map path and avoid resolving a Companyfacts cache path when cache is disabled.
- [ ] Preserve existing cached staging behavior and rerun the full SEC provider test file.

### Task 2: Provenance-Aware Candidate Extraction

**Files:**
- Modify: `src/providers/sec_companyfacts.py`
- Modify: `tests/test_sec_companyfacts.py`

- [ ] Write RED tests for direct record metadata and derived component provenance.
- [ ] Add private `_field_provenance` output to the extractor; confirm staging rows still omit private keys.
- [ ] Prove missing facts stay `None` and no derived field is described as directly reported.

### Task 3: Pure Preview Comparison

**Files:**
- Create: `src/sec_fundamentals_preview.py`
- Create: `tests/test_sec_fundamentals_preview.py`

- [ ] Write RED tests for explicit input, five-ticker cap, deterministic field deltas, classification precedence, period/accession coherence, malformed payloads, staged schema deltas, AAPL mixed-period visibility, and GOOG missing shares.
- [ ] Implement input parsing, official fetch orchestration, canonical/staged read-only projection, field comparison, coherence checks, rights review, and deterministic JSON rendering.
- [ ] Keep one ticker's failure isolated and report it without fabricated values.

### Task 4: Command Surface

**Files:**
- Modify: `Makefile`
- Modify: `tests/test_launchers.py`

- [ ] Write RED tests for help text and exact command wiring.
- [ ] Add `make sec-fundamentals-preview TICKERS=AAPL,AMZN,GOOG`; require `TICKERS` and pass no output/cache/apply argument.
- [ ] Prove the target cannot invoke stage, apply, readiness, or fallback-provider commands.

### Task 5: Cohort Audit and Verification

- [ ] Run focused provider, preview, launcher, stock-report, and data-quality tests.
- [ ] Run targeted Ruff/compile checks and `git diff --check`.
- [ ] Compare all tracked `data/`/`outputs/` hashes and both ignored SEC-state hashes to their Stage 0 manifests.
- [ ] Run the live AAPL/AMZN/GOOG preview once with the configured SEC user agent and save any durable evidence only under a fresh `/tmp` directory.
- [ ] Self-review the complete diff for Critical/Important issues and resolve them before local commits.
- [ ] Commit only named source/docs/tests/Make paths. Do not push.
