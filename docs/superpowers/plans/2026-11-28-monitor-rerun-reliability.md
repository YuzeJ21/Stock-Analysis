# Monitor Rerun Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement task-by-task.

**Goal:** Close the reproduced large-snapshot Monitor rerun failure without weakening product guards.
**Architecture:** Correct only process-lifetime test-fixture configuration; exercise the real store and Monitor under controlled overlapping renders, plus the unchanged browser journey.
**Tech Stack:** Existing Python, pytest, Streamlit and Playwright; no dependencies.
**Spec:** docs/superpowers/specs/2026-11-28-monitor-rerun-reliability.md

## Global Constraints
No production guard/storage changes, source requests, original-context writes,
new credentials, merge/deploy or invented hosted/human/source evidence.
Retain the complete existing CI matrix and no-write guard. Exact-head evidence only.

## Review Focus
- Older interrupted run unwinds during a newer company selection: deterministic real-store overlap regression.
- Private-root and socket configuration leaking to later parent tests: explicit parent monkeypatch cleanup.
- Repeated reruns nesting socket guards or allowing external transport: wrap original functions; verify denial and stable rerender behavior.
- Snapshot integrity and held financial evidence: exact equality/bytes and actual held-gap output.
- Browser-only routing differences: unchanged desktop/phone Monitor and exact return checks in early CI.

### Task 1: Stable process-owned browser fixture and release verification
**Files:** tests/test_large_research_snapshot_browser.py, tests/test_large_research_snapshot_runtime.py,
.github/workflows/commercial-research-beta.yml, .github/workflows/ecb-reference-capture.yml,
docs/MONITOR_RELEASE_RELIABILITY.md, ROADMAP.md.
**Interfaces:** _run_app(root) consumes one dedicated browser-process root;
save/load/list APIs and Monitor rendering remain unchanged.
- [x] Reproduce the older-run restoration race with the actual large context and store; observe RED at the same Monitor warning.
- [x] Keep root and original-function socket guards stable for the dedicated app process; run overlap regression GREEN.
- [x] Verify repeat configuration and external-denial behavior without actual external connections.
- [x] Add runtime and existing desktop/phone cases to the early release gate; preserve every assertion and full-suite gate.
- [x] Run focused store/Monitor/UI/auth/workflow checks, protected manifest, wording and range checks.
- [x] Obtain one independent final review and correct material findings in one tested pass.
- [ ] Commit/sync a draft PR, inspect exact-head browser/journey/full engineering and subsequent startup/render gates.

Acquisition must remain restricted to original PR126; opening a later repair PR
must not repeat that source request.

No new feature should bypass this release failure. Later maturity gates require
their actual source, host, owner, review environment or researcher inputs.
