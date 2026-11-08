# Online Company Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make company notes, SEC receipts and Monitor usable from online company identity without preprepared financial or price CSVs.

**Architecture:** Reuse existing record-authoring and SEC-review engines. Add a bounded private online-note scope and Monitor projection, leaving legacy journals and models separate. The dashboard composes notes independently of report construction.

**Tech Stack:** Python, Streamlit, pytest, existing browser gates.

**Spec:** `docs/superpowers/specs/2026-11-07-online-company-workflow.md`.

## Global Constraints

- No canonical financial/readiness/universe data or source-rights changes.
- No automatic source refresh on section changes or Monitor return.
- NEM/AMD/DUK alone retain the separately qualified exact-pair Reviewed/Still open workflow.
- Browser persistence tests use disposable stores and synthetic user records; live checks do not create real research records.
- Ordinary reads and previews create no files.

## Review Focus

- Same ticker, different CIK/profile must never share notes, drafts or confirmation.
- A note without a SEC receipt must reopen after a session restart without a local ticker row.
- Failed or unsupported financial retrieval must not disable authoring for an independently checked online candidate.
- New Monitor items must not inflate SEC coverage or legacy research-process counts.
- Incomplete/corrupt/symlinked storage must not leak another scope or produce a write-ready state.

### Task 1: Isolate authoring UI state

**Files:** `src/research_record_authoring_ui.py`, `tests/test_research_record_authoring_ui.py`.

**Interfaces:** `authoring_session_key(..., identity_scope=None)` and `render_research_record_authoring(..., identity_scope=None)`; nonzero ten-digit CIK, omitted behavior unchanged. Ledger profile/ticker remain actual selected values.

- [x] Write and observe failing cross-CIK draft/confirmation/reload tests.
- [x] Thread identity scope through composer helpers and validation state.
- [x] Run current authoring UI and persistence regression groups.

### Task 2: Independent company notes and Monitor projection

**Files:** create `src/company_research_notes.py`, `src/company_research_notes_ui.py`; modify `src/company_workbench_ui.py`, `src/dashboard.py`, `src/research_workspace.py`; create `tests/test_company_research_notes.py` and integration coverage.

**Interfaces:** `CompanyNotesScope(profile_key,ticker,sec_cik)`, private authoring paths, bounded saved-scope discovery and availability; `render_company_notes(...)` and `render_company_notes_monitor(...)`. A saved `notes_cik` query identifies offline notes, never current listing/model eligibility. Extend `MonitorOrigin` compatibly for that offline identity.

- [x] Write and observe failing no-preparation save/reload, wrong-scope, corrupt-store, no-write-read and Monitor return tests.
- [x] Implement safe note storage/discovery using existing append engines.
- [x] Render legacy or online journal without a local report; keep model-dependent tools separately gated.
- [x] Connect saved note follow-ups and checked offline routes to Monitor.
- [x] Verify existing saved notes, generic SEC review and exact-pair return regressions.

### Task 3: Bind selected SEC review to issuer

**Files:** `src/sec_research_review_ui.py`, `tests/test_multi_company_review_ui.py`.

**Interface:** `render_company_review(..., expected_cik=None)`, preserving actual profile key and existing disposition allowlist.

- [x] Observe failing wrong-CIK capture/import/replay tests.
- [x] Guard selected issuer and explain other-issuer receipts without deleting history.
- [x] Run generic multi-company and qualified exact-pair UI regressions.

### Task 4: Repair responsive breakpoint

**Files:** `src/company_workbench_presentation.py`, `tests/test_workbench_intermediate_layout.py`.

- [x] Observe failing 711/726/767px browser layout assertions.
- [x] Stack outer columns at the existing mobile navigation breakpoint.
- [x] Verify 390/711/726/767/768/1440px, 44px controls, no page overflow and retained phone cards.

### Task 5: Verify and synchronize

**Files:** disposable browser fixture/tests, active roadmap, online-research documentation and release evidence.

- [x] Exercise online search → notes preview/confirm → saved SEC replay/comparison → Monitor → exact return on desktop and phone.
- [x] Check live MRVL without saving real research or provider data.
- [ ] Run appropriate broad regressions, source/privacy/hygiene checks and canonical-byte comparison.
- [x] Obtain fresh independent code review, fix findings and rerun affected checks.
- [ ] Commit tested code and accurate documentation; synchronize GitHub without force or unrelated changes and verify remote state.

## Execution record

- Baseline `9377dff2a7ad8c775af01248df8b225eb660128c`; isolated existing worktree, feature branch `codex/online-company-workflow`.
- Baseline targeted checks: 82 passed. GitHub synchronization is already authorized by the user.
- Ruling: reuse the accepted online-workflow design and proceed autonomously; no repeated design approval is required.

- Browser workflow and responsive verification: 10 passed; live MRVL desktop/phone retained the loaded observations on Monitor return. A 726px check stacks both outer columns without page overflow; model-gap caption opacity is 1. No real records were saved.
- Independent final review found no remaining actionable P1/P2 findings. Missing legacy directories and profiles fail closed without choosing another scope.
- Canonical-byte check: all 78 tracked data/config/assets files match the baseline.
- Final integrated focused suite: 241 passed in 97.48s, including authoring, SEC identity, route contracts and desktop/phone browser tests. Broad repository verification remains pending.
