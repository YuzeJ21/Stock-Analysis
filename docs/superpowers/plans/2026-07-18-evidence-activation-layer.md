# Evidence Activation Layer Implementation Plan

> **For Codex:** Execute each task with test-driven development. Keep generated evidence under `/tmp` or `outputs`, never stage it, and preserve fail-closed research-only states.

**Goal:** Add the next evidence-bound personal research capabilities without creating new primary pages or turning candidate context into forecasts, valuation claims, or recommendations.

**Architecture:** Extend the existing Earnings Nowcast, Valuation, Research Thesis Journal, Change Monitor, Company Workbench, and Monitor modules. New modules expose immutable/read-only packets and append-only reviewed records. Dashboard changes consume compact helpers and keep raw evidence under Advanced.

**Tech stack:** Python 3.12, dataclasses, CSV/JSON contracts, argparse, Streamlit, pytest, Makefile launchers.

---

### Task 1: Reproduce the five-company actuals baseline

**Files:**
- Generated only: `/tmp/earnings-nowcast-sec-actuals-review-<timestamp>/`
- Verify: `src/earnings_nowcast_sec_actuals.py`
- Verify: `src/earnings_nowcast_onboarding.py`

1. Stage NVDA, AMD, AVGO, MU, and QCOM SEC actuals into a new timestamped `/tmp` directory with a current UTC cutoff.
2. Validate and preview the generated onboarding rows.
3. Run per-ticker readiness and record the actual, Q4, split-basis, consensus, and calibration blockers.
4. Confirm no repository files changed.

### Task 2: Five-company Earnings Nowcast readiness board

**Files:**
- Create: `src/earnings_nowcast_cohort.py`
- Create: `tests/test_earnings_nowcast_cohort.py`
- Modify: `Makefile`
- Modify: `src/dashboard.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`

1. Write failing tests for one immutable summary row per ticker and independent Revenue/EPS/Q4/split/consensus/calibration states.
2. Implement CSV-loading and cohort summarization from existing onboarding contracts.
3. Add a read-only `earnings-nowcast-cohort-readiness` command.
4. Add one compact Company Workbench/Monitor summary; keep source IDs and raw rows under Advanced.

### Task 3: Consensus source probe and prospective collector

**Files:**
- Create: `src/earnings_consensus_sources.py`
- Create: `src/earnings_consensus_collector.py`
- Create: `tests/test_earnings_consensus_sources.py`
- Create: `tests/test_earnings_consensus_collector.py`
- Modify: `Makefile`
- Modify: `config/provider_keys.env.example`

1. Write failing tests for deterministic provider order, missing-key classification, rights/comparability gates, and current-only estimates staying `candidate_context_only`.
2. Implement read-only probes for Alpha Vantage, FMP, Finnhub, and a generic reviewed CSV contract. Do not fetch when a key or approved source contract is absent.
3. Write failing tests for deterministic snapshot identity, deduplication, revision preservation, cutoff checks, cooldown, and no overwrite.
4. Implement plan/status/preview collection. Recording must require an explicit reviewed confirmation and append only.
5. Add source-status, collection-plan, collection-preview, and collection-status commands. No automatic promotion or apply path.

### Task 4: Historical valuation regime

**Files:**
- Create: `src/historical_valuation_regime.py`
- Create: `tests/test_historical_valuation_regime.py`
- Modify: `src/dashboard.py`
- Modify: `tests/test_dashboard_helpers.py`

1. Write failing tests for aligned point-in-time price and denominator observations, definition-change segmentation, insufficient history, stale observations, and rejection of current-denominator backfills.
2. Implement descriptive multiple observations and percentile/range context only when source timestamps and period definitions align.
3. Add a compact Valuation section answer. Keep rows and provenance under Advanced.
4. Use neutral wording; never label a stock cheap, expensive, attractive, or actionable.

### Task 5: Research outcome review

**Files:**
- Create: `src/research_outcome_review.py`
- Create: `tests/test_research_outcome_review.py`
- Modify: `Makefile`
- Modify: `src/dashboard.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`

1. Write failing tests for append-only reviewed records, immutable thesis references, observation-window validation, source timestamps, duplicate rejection, and no return/skill scoring.
2. Implement read, validate, preview, explicitly confirmed append, and derived status helpers.
3. Add preview/record/status commands.
4. Integrate a compact learning-loop answer into Thesis Journal/Monitor; keep raw records under Advanced.

### Task 6: Catalyst evidence timeline

**Files:**
- Create: `src/catalyst_evidence_timeline.py`
- Create: `tests/test_catalyst_evidence_timeline.py`
- Modify: `Makefile`
- Modify: `src/dashboard.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`

1. Write failing tests for allowed event types, provenance, publication/retrieval/effective timestamps, cutoff safety, duplicate identity, and candidate-only boundaries.
2. Implement read, validate, preview, explicitly confirmed append, and timeline derivation.
3. Add preview/record/status commands.
4. Integrate a concise upcoming/recent evidence answer into Company Workbench/Monitor. No scraping, sentiment scoring, forecast mutation, or recommendation.

### Task 7: Product integration and documentation

**Files:**
- Modify: `src/earnings_nowcast_ui.py`
- Modify: `src/forward_view.py`
- Modify: `src/dashboard.py`
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `docs/EARNINGS_NOWCAST_PILOT.md`
- Modify: `docs/METHODOLOGY.md`
- Modify: `docs/PROVENANCE_CONTRACT.md`
- Modify: `docs/PERSONAL_RESEARCH_MODE.md`
- Modify: `tests/test_earnings_nowcast_ui.py`
- Modify: `tests/test_forward_view.py`

1. Preserve the four-page Personal Research flow: Research Desk -> Discover -> Company Workbench -> Monitor.
2. Present concise answers in this order: readiness, usable evidence, withheld evidence, next research action.
3. Keep hashes, source IDs, raw events, records, and diagnostics under Advanced.
4. Document implemented software separately from real data availability, historical validation, and external dependencies.

### Task 8: Verification, commits, and draft PR

1. Run focused tests after each task and the full suite after integration.
2. Run dashboard smoke, browser QA, public wording, public check, pilot readiness, diff hygiene, and whitespace checks.
3. Stage exact product/code/docs/test files only; never use `git add -A`.
4. Commit coherent slices only after verification.
5. Push `codex/personal-research-mode-mvp` and update draft PR #113 without merging or deploying.
