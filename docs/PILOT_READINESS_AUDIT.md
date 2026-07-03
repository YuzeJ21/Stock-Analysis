# Pilot Readiness Audit

Date: 2026-06-22

Last repo-truth refresh: 2026-07-02

Verdict: ready for a controlled pilot with manual gates.

This audit reviews the current repository as a pilot package, not as a broad public launch. The product is research-only and readiness-first: missing trusted data must remain visible as `blocked`, `partial`, `still_blocked`, `skipped`, or `excluded` rather than being filled with placeholder analysis.

## Current Stage

Current stage: trusted-data pilot, ready to enter a controlled external pilot after the manual public-share gate is run in the target environment.

The repository is past prototype/internal-alpha for the core workflow because it has a working Streamlit dashboard, single-stock reports, readiness gates, proof ledgers, screenshot evidence, and release checks. It is not public launch-ready because broad fundamentals, source-backed peers, earnings, analyst estimates, and full valuation inputs remain intentionally incomplete for most of the 3,538-ticker universe.

## Stage Ratings

| Category | Rating | Evidence |
| --- | --- | --- |
| Data ingestion and coverage | Yellow | Price coverage and local import workflows exist, but broad fundamentals, peer mappings, earnings, and estimates remain source-review gated. `make project-status` reports 3,538 tickers with price rows, 2,691 operating-company DCF-ready tickers, and 29 peer-ready tickers. |
| Evidence ledger / provenance | Green | `make pilot-readiness-check TOP_N=10` reports 1,151 reviewed batch proof rows; latest recorded outcome is `candidate_context_only` for optional context. |
| Readiness states | Green | `make readiness-ops-center` separates ready, partial, blocked, and excluded states for price, DCF, share count, peers, optional lanes, and not-applicable rows. |
| Stale data detection | Green | `make pilot-readiness-check TOP_N=10` reports readiness artifacts are current relative to watched source files. |
| Financial-model gating and research-only safety | Green | DCF, peer valuation, earnings, and estimates stay withheld until trusted source rows pass validation, preview, rejected-row review, apply/skip decision, rebuilt readiness, and proof recording. |
| UI/product-page clarity | Yellow | Dashboard and screenshot evidence are ready, and the controlled-pilot path is documented; pilot operators should still use the runbook to stay on the shortest share-safe path. |
| Operator workflow | Green | Data Health, reviewed-batch packets, pilot readiness checks, proof queues, and commit/package handoffs exist and are copy-only. |
| Test coverage | Green | Full test suite passes locally in the current package: `2037 passed, 1 warning` inside `make public-check`. |
| CI/release checks | Green | `make public-check` passed end-to-end in the current environment, including public wording, whitespace, full tests, dashboard smoke, browser QA evidence, and visitor-demo checks. |
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
| PB-005 | Broad trusted data coverage incomplete | High | Many tickers still cannot support DCF, peer mapping, earnings, or analyst-estimate context. | `make readiness-ops-center`: DCF ready 2,691, partial 243, blocked 90, excluded 514; share count ready 3,447 and blocked 91; peer mapping ready 29, blocked 3,507, excluded 2; earnings and estimates blocked 3,538. | Partly source-dependent | Keep lanes visibly blocked; use `make provider-setup-checklist` when source-proof queues have no unreviewed executable company candidates, then run one reviewed source-proof slice only when new source-backed rows exist. | External/manual gate |
| PB-006 | Dashboard smoke can be environment-limited | Medium | Local socket restrictions can prevent in-session product-page smoke even when code is valid, but the current environment passed dashboard smoke through `make public-check`. | `make public-check` completed dashboard smoke successfully on 2026-07-02; rerun the gate immediately before sharing. | No, environment dependent | Run `make public-check` before public sharing; if dashboard smoke later fails because a local port cannot bind, verify `make dashboard-smoke` or `make dashboard` in a normal local shell. | Manual recheck gate |
| PB-007 | Optional provider access can be unavailable | Medium | SEC/Yahoo paths may fail in restricted sessions, so broad unattended data proof cannot be guaranteed. | Session preflight commands can return `session_sec_unavailable` or `session_yfinance_unavailable`. | No, network/provider dependent | Use local reviewed rows when present; otherwise mark ticker/lane `still_blocked`, `skipped`, or `excluded` and move to the next executable lane. | External/manual gate |
| PB-008 | Keyed free-tier providers not configured | Medium | More fundamentals/share-count fallback coverage cannot expand through FMP, Alpha Vantage, or Finnhub until local keys are configured. | `make session-source-preflight` reports FMP, Alpha Vantage, and Finnhub as `provider_key_missing`; `make project-status` says the best next proof is `make provider-setup-checklist`. | No, owner setup dependent | Keep real keys out of the repo; use the reviewed one-ticker smoke command before broad batches after setup. | External/manual gate |

## Command Evidence

| Command | Result | Notes |
| --- | --- | --- |
| `git status --short --branch --untracked-files=no` | Passed with generated churn only | Current branch is ahead of origin; use the live status gate for the exact count. Reviewed local commits still need push before the GitHub pilot link is current. Dirty files are generated CSV/report churn and broad stock-report artifacts that stay excluded by default. |
| `git log -5 --oneline` | Passed | Latest commits include Data Health routing, pilot share package, provider setup, and workflow handoff improvements. |
| `make diff-hygiene-summary` | Passed | Product/code/docs/test package was clean before this audit refresh; generated/sample report churn stays local unless individually reviewed evidence. |
| `make pilot-readiness-check TOP_N=10` | Passed with manual gates | Verdict: `pilot-ready with manual gates`; public-check remains the explicit share gate. |
| `make project-status` | Passed | Reports 3,538 tickers with price rows, 2,808 fundamentals/input-ready, 2,691 operating-company DCF-ready, and 29 peer-ready tickers. |
| `make session-source-preflight` | Passed | SEC, SEC submissions, yfinance import/stage, Stooq/Yahoo price ladder, and local fundamentals are available; FMP, Alpha Vantage, and Finnhub keys are missing; IBKR remains optional and disabled. |
| `make readiness-ops-center` | Passed | Lane board confirms partial/blocked/manual/excluded states, source-proof queue exhaustion, and provider setup as the next safe proof path. |
| `make universe-preview-summary` | Passed | Read-only universe metadata preview returned 50 capped rows, with one new SMH metadata candidate and one fallback source warning. Universe membership remains metadata only and does not unlock fundamentals, share count, DCF, peers, earnings, estimates, or recommendations. |
| `make public-check` | Passed | Public wording, whitespace, full tests, dashboard smoke, browser QA evidence, and visitor-demo checks passed. |
| `make public-wording-check` | Passed | Public wording scan passed across 2,905 public files before this doc update. |
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
- Provider setup: FMP, Alpha Vantage, and Finnhub are keyed free-tier fallbacks. Configure them only in local env files, run the reviewed one-ticker smoke command first, then validate and preview before applying any row.
- Public-check confirmation: run `make public-check` immediately before sharing so the wording, whitespace, full tests, dashboard smoke, browser QA evidence, and visitor-demo gates are fresh.
- License choice: the repository is public-reviewable, but no root license means it should not be described as open source until the owner chooses a license.

## Pilot Readiness Verdict

Ready for a controlled pilot with manual gates.

The controlled pilot should focus on a small, reviewed set of companies and prove one data lane at a time. The product should not be described as launch-ready or full-universe analysis-ready until trusted coverage improves and optional context lanes have source-backed rows.
