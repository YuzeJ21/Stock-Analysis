# Source Freshness Timeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, read-only selected-ticker chronology that distinguishes effective, publication, retrieval, cutoff, and report-generation times without inventing evidence.

**Architecture:** A focused `src/source_freshness_timeline.py` module converts an existing report payload into immutable timeline events and a summary. Dashboard helpers render the summary and chronology inside the existing Sources & Gaps tab; no new page or canonical ledger is introduced.

**Tech Stack:** Python dataclasses, SHA-256 identity, pandas, Streamlit, pytest.

## Global Constraints

- Research-only; no recommendation, ranking, broker, order-routing, or transaction language.
- Never infer missing timestamps or use retrieval/report time as publication/effective time.
- Never write canonical data, readiness, proof history, reports, or generated artifacts.
- Keep technical provenance collapsed and preserve the existing five-page workflow.

---

### Task 1: Timeline Contract And Builder

**Files:**
- Create: `src/source_freshness_timeline.py`
- Create: `tests/test_source_freshness_timeline.py`

**Interfaces:**
- Produces: `FreshnessTimelineEvent`, `FreshnessTimeline`, `build_source_freshness_timeline(report_payload, profile_key)`.

- [ ] Write failing tests for known/unknown timestamp events, deterministic IDs, deduplication, newest-first ordering, and stale-state preservation.
- [ ] Run `python3 -m pytest tests/test_source_freshness_timeline.py -q` and verify missing-interface failures.
- [ ] Implement immutable events, strict ISO timestamp parsing, normalization, deterministic identity, and report-payload mapping.
- [ ] Re-run the focused test and commit the coherent core slice.

### Task 2: Dashboard Integration

**Files:**
- Modify: `src/dashboard.py`
- Modify: `tests/test_dashboard_helpers.py`

**Interfaces:**
- Consumes: `build_source_freshness_timeline(report_payload, profile_key)`.
- Produces: `source_freshness_summary_cards`, `source_freshness_timeline_frame`, and Sources & Gaps rendering.

- [ ] Write failing tests for truthful summary cards, table ordering, prohibited wording, and collapsed placement under Sources & Gaps.
- [ ] Run the exact new tests and verify expected failures.
- [ ] Add one summary, one timeline expander, and one advanced provenance expander without changing first-viewport behavior.
- [ ] Run focused dashboard and single-stock tests and commit the UI slice.

### Task 3: Documentation And Release Gates

**Files:**
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `docs/METHODOLOGY.md`
- Modify: `docs/PROVENANCE_CONTRACT.md`
- Modify: `tests/test_public_v1_release_docs.py`

**Interfaces:**
- Documents the read-only/no-inference boundary and implemented roadmap status.

- [ ] Add a failing documentation contract test.
- [ ] Update existing concise public and methodology wording without increasing README complexity.
- [ ] Run focused source-freshness, dashboard, docs, and provenance tests.
- [ ] Run `make public-check`, `make pilot-readiness-check TOP_N=10`, `make diff-hygiene-summary`, and `git diff --check`.
- [ ] Commit only source, docs, and tests after staged hygiene passes.
