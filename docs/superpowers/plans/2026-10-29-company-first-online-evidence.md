# Company-first UI and Online Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make selected-company research readable and search-first, and expose a source-labelled SEC annual-facts check without changing saved data.

**Architecture:** Keep the current Streamlit workflow and evidence contracts. Change only first-view ordering and visual hierarchy in the existing research renderers. Add a small pure SEC result presenter and a selected-ticker session-scoped UI action that calls the existing no-write preview once per click.

**Tech Stack:** Python, Streamlit, HTML/CSS render helpers, pytest, local browser gate.

**Spec:** `docs/superpowers/specs/2026-10-29-company-first-online-evidence-design.md`

## Task 1 — Search-first Discover and readable Company Brief

- [x] Add failing tests for search appearing before result actions, no alphabetical shortcut bar, and preserved evidence/stop-rule copy.
- [x] Run focused tests and confirm the intended failures.
- [x] Update `src/dashboard.py` Discover order and `src/research_workspace.py` Company Brief hierarchy; adjust `src/dashboard_visual_system.py` and research CSS for desktop/phone typography and navigation consistency.
- [x] Update browser geometry assertions and `ROADMAP.md` where they encode the old four-column or quick-link contract.
- [x] Run focused tests and capture current Discover and NVDA Company Workbench desktop/phone views.

## Task 2 — Selected-company SEC annual-facts presentation

- [x] Add failing synthetic tests for approved direct fields, withheld reasons, source/period metadata, malformed results, unavailable User-Agent/network state, and ticker-scoped cache behavior.
- [x] Run the tests to confirm the failures.
- [x] Implement `src/company_sec_online_preview.py` as a pure bounded view model over `build_sec_fundamentals_preview`; no canonical or disk-cache writes.
- [x] Add a selected-company Streamlit action in `src/dashboard.py` that fetches only on click, stores the result in session state by ticker, and renders the dated inspection card.
- [x] Run focused tests; verify one live NVDA read-only SEC request with no repository writes and an explicit annual-period label.

## Task 3 — Review and close

- [ ] Run the full relevant test and browser gates; inspect desktop/phone screens and any failures.
- [ ] Recheck source rights, canonical-data diff, staged hygiene, remote head, and branch history.
- [ ] Commit reviewed code, tests, and neutral docs locally; update ignored release evidence with exact results and remaining online-provider gates.
- [ ] Sync only the reviewed branch if the existing GitHub authorization still applies; do not open a PR, merge, deploy, or publish a product release.

## Review focus

- Search must remain restricted to saved company paths and never imply all-company coverage.
- An online SEC fetch must not be triggered by ordinary Streamlit rerenders.
- A ticker switch must not show a prior ticker's SEC result.
- A failed fetch or ambiguous field must be visibly withheld and never render as zero.
- No new source response, generated report, or raw ticker fixture may enter tracked branch history.
