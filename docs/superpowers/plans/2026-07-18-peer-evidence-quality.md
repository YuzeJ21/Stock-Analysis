# Peer Evidence Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve reviewed peer role and economic-comparability evidence end to end, and withhold peer-median valuation unless a relationship is explicitly eligible to anchor it.

**Architecture:** A small pure module owns deterministic peer evidence-quality classification. Source review, local provider, readiness generation, and Company Workbench consume that shared result so relationship, trend, read-through, and valuation readiness cannot collapse into one state.

**Tech Stack:** Python 3.12, pandas, Streamlit, pytest, Markdown, CSV contracts.

## Global Constraints

- Research-only; no recommendation, transaction instruction, broker integration, order routing, or auto-trading.
- Candidate context cannot become trusted relationship or valuation evidence.
- Existing rows without explicit role and comparability evidence fail closed for valuation anchoring.
- Do not infer, backfill, or fabricate peer roles, comparability, sources, or timestamps.
- Preserve trend, result read-through, and valuation readiness as independent states.
- Keep technical evidence under Advanced unless needed to explain the primary answer.

---

### Task 1: Deterministic Peer Evidence-Quality Contract

**Files:**
- Create: `src/peer_evidence_quality.py`
- Create: `tests/test_peer_evidence_quality.py`

**Interfaces:**
- Consumes: a mapping-shaped peer relationship row.
- Produces: `assess_peer_evidence(row: Mapping[str, object]) -> PeerEvidenceQuality` and `is_valuation_anchor_eligible(row: Mapping[str, object]) -> bool`.

- [ ] Write failing tests for a fully eligible `core_peer`, a legacy row, a context-only role, an invalid role, missing comparability, and missing provenance.
- [ ] Run `python3 -m pytest tests/test_peer_evidence_quality.py -q` and confirm failures are caused by the missing module.
- [ ] Implement the immutable result type, allowed roles, normalization, blocker ordering, and fail-closed anchor decision.
- [ ] Rerun the focused test and confirm it passes.

### Task 2: Preserve Review Evidence Through Import

**Files:**
- Modify: `src/providers/local_schemas.py`
- Modify: `src/peer_mapping_source_review.py`
- Modify: `docs/TRUSTED_PEER_PILOT_SOURCE_TEMPLATE.csv`
- Modify: `tests/test_peer_mapping_source_review.py`
- Modify: `tests/test_trusted_peer_pilot_source_template.py`

**Interfaces:**
- Consumes: reviewed `peer_role`, `relationship_rationale`, `comparability_basis`, and `valuation_anchor_eligible` fields.
- Produces: exact import header and guarded CSV row that preserve those fields.

- [ ] Add failing tests proving incomplete evidence remains blocked and a complete row survives into the import scaffold.
- [ ] Run the two focused test modules and confirm the new assertions fail for the missing contract.
- [ ] Extend schema, review row, required fields, scaffold, CLI arguments, rendering, and template without adding an automatic apply path.
- [ ] Rerun the focused tests and confirm they pass.

### Task 3: Gate Provider Valuation Inputs And Readiness Independently

**Files:**
- Modify: `src/providers/local_market_data.py`
- Modify: `src/readiness_engine.py`
- Modify: `tests/test_local_market_data_provider.py`
- Modify: `tests/test_readiness_engine.py`

**Interfaces:**
- Consumes: `assess_peer_evidence` and canonical peer rows.
- Produces: relationship-quality fields in `trusted_relationships`, valuation inputs containing only eligible anchors, and readiness columns for anchor counts/blockers.

- [ ] Add failing provider tests proving legacy and context-only rows remain visible but are excluded from valuation inputs.
- [ ] Add failing readiness tests proving trend readiness can be true while valuation-anchor readiness is false, and eligible peers can unlock valuation readiness only with financial evidence.
- [ ] Run the focused tests and confirm the expected failures.
- [ ] Implement provider filtering and independent readiness classification using the shared contract.
- [ ] Rerun focused tests and confirm they pass.

### Task 4: Surface The Answer In Company Workbench

**Files:**
- Modify: `src/peer_read_through_map.py`
- Modify: `src/dashboard.py`
- Modify: `tests/test_peer_read_through_map.py`
- Modify: `tests/test_dashboard_helpers.py`

**Interfaces:**
- Consumes: provider relationship-quality fields or the shared classifier.
- Produces: compact peer rows with `Peer Role`, `Comparability`, and `Valuation Anchor`, plus answer-first summary copy.

- [ ] Add failing tests for eligible, context-only, and legacy-withheld table states and summary copy.
- [ ] Run focused tests and confirm the table assertions fail.
- [ ] Extend map edges, deterministic identity, compact rows, frame columns, and summary cards; keep raw evidence in Advanced.
- [ ] Rerun focused tests and confirm they pass.

### Task 5: Documentation And Release Verification

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/METHODOLOGY.md`
- Modify: `docs/PILOT_RUNBOOK.md`
- Modify: `docs/PROVENANCE_CONTRACT.md`
- Modify: `docs/PERSONAL_RESEARCH_MODE.md`

**Interfaces:**
- Consumes: verified behavior from Tasks 1-4.
- Produces: truthful methodology, migration boundary, pilot procedure, and next external dependency.

- [ ] Document the new independent states and the explicit legacy-row migration boundary.
- [ ] Run focused peer/schema/dashboard tests.
- [ ] Run `python3 -m pytest tests -q`.
- [ ] Run `make dashboard-smoke`, `make public-wording-check`, `make public-check`, `make pilot-readiness-check TOP_N=10`, `make diff-hygiene-summary`, and `git diff --check`.
- [ ] Stage only the exact product, test, spec, plan, template, and documentation paths; run `make staged-hygiene-check`.
- [ ] Commit one coherent slice, push only `codex/personal-research-mode-mvp`, and update draft PR #113 without changing its draft state.
