# Pilot Readiness Audit

Date: 2026-06-22

Verdict: ready for a controlled pilot with manual gates.

This audit reviews the current repository as a pilot package, not as a broad public launch. The product is research-only and readiness-first: missing trusted data must remain visible as `blocked`, `partial`, `still_blocked`, `skipped`, or `excluded` rather than being filled with placeholder analysis.

## Current Stage

Current stage: trusted-data pilot, ready to enter a controlled external pilot after the manual public-share gate is run in the target environment.

The repository is past prototype/internal-alpha for the core workflow because it has a working Streamlit dashboard, single-stock reports, readiness gates, proof ledgers, screenshot evidence, and release checks. It is not public launch-ready because broad fundamentals, source-backed peers, earnings, analyst estimates, and full valuation inputs remain intentionally incomplete for most of the 3,538-ticker universe.

## Stage Ratings

| Category | Rating | Evidence |
| --- | --- | --- |
| Data ingestion and coverage | Yellow | Price coverage and local import workflows exist, but broad fundamentals, peer mappings, earnings, and estimates remain source-review gated. `make status-check TOP_N=5` reports 265 price-ready tickers, 23 DCF-ready tickers, and 9 peer-ready tickers. |
| Evidence ledger / provenance | Green | `data/reviewed_batch_proofs.csv` contains 8 reviewed batch proof rows; latest recorded outcome is `still_blocked` for ABLV share count proof. |
| Readiness states | Green | `make readiness-ops-center` separates ready, partial, blocked, and excluded states for price, DCF, share count, peers, optional lanes, and not-applicable rows. |
| Stale data detection | Green | `make pilot-readiness-check TOP_N=10` reports readiness artifacts are current relative to watched source files. |
| Financial-model gating and research-only safety | Green | DCF, peer valuation, earnings, and estimates stay withheld until trusted source rows pass validation, preview, rejected-row review, apply/skip decision, rebuilt readiness, and proof recording. |
| UI/product-page clarity | Yellow | Dashboard and screenshot evidence are ready, but pilot operators still need the runbook for the shortest controlled-pilot path and normal-shell dashboard smoke confirmation. |
| Operator workflow | Green | Data Health, reviewed-batch packets, pilot readiness checks, proof queues, and commit/package handoffs exist and are copy-only. |
| Test coverage | Green | Full test suite passes locally: `1705 passed, 1 warning`. |
| CI/release checks | Yellow | Local public checks pass in this environment with dashboard smoke treated as environment-limited when sockets cannot bind; normal-shell smoke remains the release confirmation. |
| Documentation/onboarding | Yellow | README, data strategy, public release checklist, and operator guide exist; this audit and the pilot runbook close the dedicated pilot-doc gap. |
| Expansion roadmap | Yellow | Roadmap is extensive; this pass adds a concise controlled-pilot stage capsule so pilot entry/exit criteria are easier to find. |
| Maintainability | Yellow | Many dashboard helpers have been extracted and tested, but the Streamlit dashboard remains large and should continue to shrink after pilot-critical behavior stabilizes. |

## Pilot Blockers

| ID | Blocker title | Severity | Pilot impact | Evidence from repo | Fixable by code/docs | Planned fix | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PB-001 | Dedicated pilot audit missing | High | Pilot reviewer lacks one concise verdict, rating table, blocker list, and command log. | No `docs/PILOT_READINESS_AUDIT.md` before this pass. | Yes | Create this audit with stage, ratings, blockers, evidence, and validation. | Fixed |
| PB-002 | Dedicated pilot runbook missing | High | A pilot operator must stitch setup and proof flow together from README, Operator Guide, Data Strategy, and Makefile. | No `docs/PILOT_RUNBOOK.md` before this pass. | Yes | Add a runbook covering setup, environment, data files, pilot workflow, refreshes, reports, states, provenance, checks, blocked stocks, limitations, and guardrails. | Fixed |
| PB-003 | Screenshot QA status stale in docs | Medium | Reviewer could think three real workflow screenshots are still pending even though `make browser-qa-evidence` reports ready. | `docs/DASHBOARD_QA.md` listed single-stock workflow, Data Health proof lane, and queue drawer routing as manual capture pending. | Yes | Update QA status table and matching regression expectation. | Fixed |
| PB-004 | Pilot entry/exit criteria hard to find | Medium | Roadmap is comprehensive but long; a pilot reviewer needs a short stage capsule. | `ROADMAP.md` has detailed milestones but no compact controlled-pilot criteria block near current state. | Yes | Add a controlled-pilot stage gate with entry criteria, exit criteria, next priorities, post-pilot work, risks, non-goals, and what not to build before pilot. | Fixed |
| PB-005 | Broad trusted data coverage incomplete | High | Most tickers cannot support DCF, peer valuation, earnings, or analyst-estimate context. | `make readiness-ops-center`: DCF blocked 3,498; share count blocked 3,501; peer mapping blocked 3,512; earnings and estimates blocked 3,538. | No, source-review dependent | Keep lanes visibly blocked; run one reviewed source-proof slice at a time. | External/manual gate |
| PB-006 | Dashboard smoke can be environment-limited | Medium | Local socket restrictions can prevent in-session product-page smoke even when code is valid. | Prior sandbox runs could not bind Streamlit; public checks document this as environment-limited. | No, environment dependent | Run `make dashboard-smoke` or `make dashboard` in a normal local shell before public sharing. | External/manual gate |
| PB-007 | Optional provider access can be unavailable | Medium | SEC/Yahoo paths may fail in restricted sessions, so broad unattended data proof cannot be guaranteed. | Session preflight commands can return `session_sec_unavailable` or `session_yfinance_unavailable`. | No, network/provider dependent | Use local reviewed rows when present; otherwise mark ticker/lane `still_blocked`, `skipped`, or `excluded` and move to the next executable lane. | External/manual gate |

## Command Evidence

| Command | Result | Notes |
| --- | --- | --- |
| `git status --short --branch` | Passed | Clean at start of audit: `## main...origin/main`. |
| `git log -8 --oneline` | Passed | Latest commits include `b1ca08ed Fix public command center UI interactions` and `8307e6be Record ABLV share-count proof outcome`. |
| `make diff-hygiene` | Passed | Working tree clean at audit start. |
| `make pilot-readiness-check TOP_N=10` | Passed with manual gates | Verdict: `pilot-ready with manual gates`; public-check remains the explicit share gate. |
| `make status-check TOP_N=5` | Passed | Reports 265 price-ready, 23 DCF-ready, and 9 peer-ready tickers. |
| `make readiness-ops-center` | Passed | Lane board confirms partial/blocked/manual/excluded states and next safe commands. |
| `make public-wording-check` | Passed | Public wording scan passed across 29 files before this doc update. |
| `make browser-qa-evidence` | Passed | Verdict ready; all listed screenshot evidence is ready and screenshots remain product evidence only. |

## Product UI Review

Reviewed product-facing surfaces:

- README visitor path.
- Streamlit entrypoint: `make dashboard`, public route `http://localhost:8501/?mode=public`.
- Data Health pilot evidence and proof workflow described by `make pilot-readiness-check`.
- Screenshot evidence inventory from `make browser-qa-evidence`.
- Single-stock Markdown report workflow through documented `make stock-report-md TICKER=<ticker>` commands.

Assessment:

- A pilot operator can see ready, partial, blocked, and excluded states before analysis.
- Evidence and proof routes are visible through Proof History, Data Health, reviewed batch proof rows, and pilot packets.
- Source freshness and stale readiness warnings are represented by pilot/readiness checks.
- Missing fields and coverage gaps are explicit.
- DCF and peer valuation gates remain separate and conservative.
- The research-only boundary is repeated in README, checks, runbooks, and release docs.
- The remaining UI risk is not correctness; it is density. The controlled pilot should use the runbook to keep operators on the short path.

## Remaining External / Manual Gates

- Source coverage: trusted fundamentals, share counts, peer mappings, earnings, and analyst estimates require reviewed source rows. Code must not invent these.
- Normal-shell dashboard smoke: run in an environment that can bind Streamlit sockets before external pilot sharing.
- Public-check confirmation: run `make public-check` immediately before sharing.
- License choice: the repository is public-reviewable, but no root license means it should not be described as open source until the owner chooses a license.

## Pilot Readiness Verdict

Ready for a controlled pilot with manual gates.

The controlled pilot should focus on a small, reviewed set of companies and prove one data lane at a time. The product should not be described as launch-ready or full-universe analysis-ready until trusted coverage improves and optional context lanes have source-backed rows.
