# NEM SEC Review Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete NEM SEC evidence capture, replay, comparison and Monitor follow-up.
**Architecture:** A bounded normalized receipt adapter gates existing snapshot comparison; an independent UI plugs into Research Records and Monitor. Explicit profile-scoped local captures preserve source and rights boundaries.
**Tech Stack:** Python, Streamlit, pytest, existing SEC transport and research snapshots.
**Spec:** docs/superpowers/specs/2026-11-02-nem-sec-review-design.md

## Global Constraints

NEM only. No canonical data or source-rights writes. No raw SEC or Yahoo payload retention in packets. No automatic source access during replay. No merge/deploy. Sync tested code only to the authorized developer branch.

## Review Focus

- Imported JSON with duplicate keys, nonfinite values, unsupported fields or wrong digests fails closed.
- Two captures of identical observations show unchanged; capture timestamps never create financial changes.
- Missing fields and mismatched definitions/periods/units/rights remain gaps with no numeric delta.
- Profile boundaries, storage failures and malformed saved receipts never silently disappear or leak.
- Normal company and Monitor navigation works on desktop and phone without inflating process counts.

### Task 1: Bounded receipt and comparison

Files: src/sec_research_review.py, tests/test_sec_research_review.py; reuse src/research_change_snapshot.py and src/research_change_monitor.py.
Interfaces: capture_review(view, profile_key, saved_at=None); load_review(bytes); compare_reviews(before, after); save_review(packet, root); list_reviews(root, profile_key).
- [ ] Write and run failing synthetic capture/replay/comparison/storage contracts.
- [ ] Implement normalized schema, checksum, current policy check, gated comparison and immutable scoped storage.
- [ ] Run targeted tests and commit.

### Task 2: Company records and Monitor

Files: src/sec_research_review_ui.py, src/company_workbench_ui.py, src/dashboard.py, tests/test_sec_research_review_ui.py.
Interfaces: render_company_review(st, ticker, view, profile_key); render_review_monitor(st, profile_key).
- [ ] Write and run failing normal-route integration tests.
- [ ] Add explicit save, download, import and saved-pair selectors to NEM Research Records; render gaps in Monitor separately.
- [ ] Run focused tests and commit.

### Task 3: Release verification

- [ ] Capture real NEM source evidence, save twice and replay offline; report whether an independent changed source pair exists.
- [ ] Review code independently, resolve material findings, run desktop and phone checks.
- [ ] Update roadmap/method and local release packet; run complete guarded suite sequentially on final commit.
- [ ] Verify protected hashes, push authorized branch, verify remote hash and hosted check status.

## Execution decisions

Native execution follows the user's instruction to proceed without human testing. A final independent reviewer follows the executing-plans skill. The portable checksum validates consistency, not authenticity. Real receipts remain ignored and private.
