# Research Thesis and Evidence Journal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a profile-scoped, append-only journal that preserves reviewed thesis revisions and evidence history without generating recommendations or mutating readiness.

**Architecture:** A focused `src/research_thesis_journal.py` module owns the immutable CSV contract, validation, derived ticker state, rendering, and CLI. The dashboard consumes only derived read-only state for the selected profile and ticker. Make targets expose read, preview, and explicitly confirmed record operations.

**Tech Stack:** Python 3.12, dataclasses, standard-library CSV/JSON/argparse, pandas-free core contract, Streamlit dashboard helpers, pytest, Make.

## Global Constraints

- Research-only; no investment advice, broker integration, trading, order routing, auto-trading, or direct buy/sell instructions.
- Journal entries never change source data or readiness.
- Generated thesis text never becomes a journal row automatically.
- Every journal read and write is scoped to an explicit selected profile.
- Ledger history is append-only; revisions preserve prior rows.
- Generated CSV/JSON/report churn stays excluded.

---

### Task 1: Journal contract and validation

**Files:**
- Create: `src/research_thesis_journal.py`
- Create: `tests/test_research_thesis_journal.py`
- Create: `data/research_thesis_journal.csv`

**Interfaces:**
- Produces `JournalEntry`, `JournalState`, `validate_journal_entry`, `load_journal_entries`, `append_journal_entry`, and `derive_journal_state`.

- [ ] Write failing tests for schema, required fields, ISO timestamps, evidence provenance, confidence bounds, duplicate IDs, profile isolation, and cross-ticker supersession.
- [ ] Run `python3 -m pytest tests/test_research_thesis_journal.py -q` and confirm failures are caused by the missing module.
- [ ] Implement the minimal append-only contract and derived state.
- [ ] Re-run the focused tests and confirm they pass.
- [ ] Commit `Add append-only research thesis journal`.

### Task 2: Read-only rendering and safe CLI

**Files:**
- Modify: `src/research_thesis_journal.py`
- Modify: `tests/test_research_thesis_journal.py`

**Interfaces:**
- Produces `render_journal_state`, `preview_journal_entry`, and CLI modes `--ticker`, `--preview`, and `--record --confirm-reviewed`.

- [ ] Write failing tests proving empty journals render `not_started`, incomplete journals stay explicit, preview does not write, recording requires confirmation, and public text contains no recommendation language.
- [ ] Run the focused tests and confirm the expected failures.
- [ ] Implement rendering and CLI behavior without provider or readiness writes.
- [ ] Re-run the focused tests and confirm they pass.
- [ ] Commit `Add safe thesis journal review commands`.

### Task 3: Makefile and hygiene integration

**Files:**
- Modify: `Makefile`
- Modify: `scripts/diff_hygiene.py`
- Modify: `tests/test_launchers.py`
- Modify: `tests/test_diff_hygiene.py`

**Interfaces:**
- Produces `thesis-journal`, `thesis-journal-preview`, and `thesis-journal-record` targets.

- [ ] Write failing launcher and hygiene tests for exact targets and the reviewed ledger classification.
- [ ] Run the focused tests and confirm they fail before implementation.
- [ ] Add the targets and classify only `data/research_thesis_journal.csv` as a reviewed product ledger.
- [ ] Re-run focused tests and confirm they pass.
- [ ] Commit `Wire thesis journal workflow commands`.

### Task 4: Single-Stock Report integration

**Files:**
- Modify: `src/dashboard.py`
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `src/browser_qa_evidence.py`
- Modify: `tests/test_browser_qa_evidence.py`

**Interfaces:**
- Produces pure helpers `research_thesis_journal_summary`, `research_thesis_journal_html`, and `load_dashboard_journal_state` plus a compact selected-ticker section.

- [ ] Write failing tests for empty, incomplete, current, overdue, profile-isolated, and Advanced-detail states.
- [ ] Run focused dashboard tests and confirm the failures.
- [ ] Integrate the compact answer after selected-ticker scope and before detailed analysis tabs; keep raw history collapsed.
- [ ] Update browser markers for the visible contract.
- [ ] Re-run focused UI tests and dashboard smoke.
- [ ] Commit `Integrate thesis journal into stock review`.

### Task 5: Documentation and completion audit

**Files:**
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `docs/METHODOLOGY.md`
- Modify: `docs/PROVENANCE_CONTRACT.md`
- Modify: `docs/OPERATOR_GUIDE.md`

**Interfaces:**
- Documents the user workflow, append-only provenance, profile boundary, and explicit deferred automation.

- [ ] Add documentation tests or update existing wording assertions before changing public copy.
- [ ] Update docs without duplicating the authoritative roadmap.
- [ ] Run focused tests, then `python3 -m pytest tests -q`.
- [ ] Run `make dashboard-smoke`, `make browser-qa-evidence`, `make public-wording-check`, `make public-check`, `make pilot-readiness-check TOP_N=10`, `make diff-hygiene-summary`, and `git diff --check`.
- [ ] Commit the coherent documentation slice only after all gates pass.
