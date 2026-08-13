# Pilot Readiness Audit

Date: 2026-06-22

Last repo-truth refresh: 2026-07-09

Historical snapshot notice: this dated audit is superseded for current lane truth. Run `make readiness-ops-center` for current selected-profile readiness; `make status-check TOP_N=5` only describes a saved generated snapshot and can be stale.

Verdict: ready for a controlled pilot with manual gates.

This audit reviews the current repository as a pilot package, not as a broad public launch. The product is research-only and readiness-first: missing trusted data must remain visible as `blocked`, `partial`, `still_blocked`, `skipped`, or `excluded` rather than being filled with placeholder analysis.

## Current Stage

Current stage: controlled GitHub/LinkedIn pilot-share package with manual gates.

The repository is past prototype/internal-alpha for the core workflow because it has a working Streamlit dashboard, single-stock reports, readiness gates, proof ledgers, screenshot evidence, and release checks. It is ready to share as a controlled GitHub/LinkedIn portfolio demo after `make public-check` passes, but it is not public launch-ready as a hosted data product. Hosted demo remains external-account-required until a public URL is deployed and verified. Provider activation remains external-key-required for FMP, Alpha Vantage, and Finnhub. Broad fundamentals, source-backed peers, earnings, analyst estimates, and full valuation inputs remain intentionally incomplete for much of the broad universe. Use `make readiness-ops-center` for current local counts before quoting them; saved generated snapshots are historical context only.

## Stage Ratings

| Category | Rating | Evidence |
| --- | --- | --- |
| Data ingestion and coverage | Yellow | Price coverage and local import workflows exist, but broad fundamentals, peer mappings, earnings, and estimates remain source-review gated. Run `make readiness-ops-center` before quoting current ticker or lane counts; use `make status-check TOP_N=5` only for saved generated-snapshot context that can be stale. |
| Evidence ledger / provenance | Green | `make pilot-readiness-check TOP_N=10` reports the reviewed batch proof ledger and latest durable outcome. |
| Readiness states | Green | `make readiness-ops-center` separates ready, partial, blocked, and excluded states for price, DCF, share count, peers, optional lanes, and not-applicable rows. |
| Stale data detection | Green | `make pilot-readiness-check TOP_N=10` reports readiness artifacts are current relative to watched source files. |
| Financial-model gating and research-only safety | Green | DCF, peer valuation, earnings, and estimates stay withheld until trusted source rows pass validation, preview, rejected-row review, apply/skip decision, rebuilt readiness, and proof recording. |
| UI/product-page clarity | Green | Public workflow is guided through Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History, with advanced/operator details kept secondary; rerun live desktop/mobile review after UI changes. |
| Operator workflow | Green | Data Health, reviewed-batch packets, pilot readiness checks, proof queues, and commit/package handoffs exist and are copy-only. |
| Test coverage | Green | Full test suite passes locally inside `make public-check`; rerun the gate before sharing so the count is current. |
| CI/release checks | Green | `make public-check` passed end-to-end in the current environment, including public wording, whitespace, full tests, dashboard smoke, browser QA evidence, and visitor-demo checks. |
| Documentation/onboarding | Green | README, LinkedIn brief, public demo walkthrough, hosted-demo deployment guide, source activation guide, release checklist, and pilot runbook all name the current share boundary. |
| Expansion roadmap | Yellow | Next expansion is source/provider dependent: configure at most one keyed provider, run one reviewed ticker smoke, and keep peer/optional lanes source-gated until trusted rows exist. |
| Maintainability | Yellow | Many dashboard helpers have been extracted and tested, but the Streamlit dashboard remains large and should continue to shrink after pilot-critical behavior stabilizes. |

## Pilot Blockers

| ID | Blocker title | Severity | Pilot impact | Evidence from repo | Fixable by code/docs | Planned fix | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PB-001 | Dedicated pilot audit missing | High | Pilot reviewer lacks one concise verdict, rating table, blocker list, and command log. | No `docs/PILOT_READINESS_AUDIT.md` before this pass. | Yes | Create this audit with stage, ratings, blockers, evidence, and validation. | Fixed |
| PB-002 | Dedicated pilot runbook missing | High | A pilot operator must stitch setup and proof flow together from README, Operator Guide, Data Strategy, and Makefile. | No `docs/PILOT_RUNBOOK.md` before this pass. | Yes | Add a runbook covering setup, environment, data files, pilot workflow, refreshes, reports, states, provenance, checks, blocked stocks, limitations, and guardrails. | Fixed |
| PB-003 | Screenshot QA status stale in docs | Medium | Reviewer could think three real workflow screenshots are still pending even though `make browser-qa-evidence` reports ready. | `docs/DASHBOARD_QA.md` listed single-stock workflow, Data Health proof lane, and queue drawer routing as manual capture pending. | Yes | Update QA status table and matching regression expectation. | Fixed |
| PB-004 | Pilot entry/exit criteria hard to find | Medium | Roadmap is comprehensive but long; a pilot reviewer needs a short stage capsule. | `ROADMAP.md` has detailed milestones but no compact controlled-pilot criteria block near current state. | Yes | Add a controlled-pilot stage gate with entry criteria, exit criteria, next priorities, post-pilot work, risks, non-goals, and what not to build before pilot. | Fixed |
| PB-005 | Broad trusted data coverage incomplete | High | Many tickers still cannot support DCF, peer mapping, earnings, or analyst-estimate context. | `make readiness-ops-center` and `make data-coverage-proof-queues TOP_N=10` show current ready, partial, blocked, excluded, and still-blocked lane counts. | Partly source-dependent | Keep lanes visibly blocked; use `make provider-setup-checklist` when source-proof queues have no unreviewed executable company candidates, then run one reviewed source-proof slice only when new source-backed rows exist. | External/manual gate |
| PB-006 | Dashboard smoke can be environment-limited | Medium | Local socket restrictions can prevent in-session product-page smoke even when code is valid, but the current environment passed dashboard smoke through `make public-check`. | `make public-check` completed dashboard smoke successfully on 2026-07-09; rerun the gate immediately before sharing. | No, environment dependent | Run `make public-check` before public sharing; if dashboard smoke later fails because a local port cannot bind, verify `make dashboard-smoke` or `make dashboard` in a normal local shell. | Manual recheck gate |
| PB-007 | Optional provider access can be unavailable | Medium | SEC/Yahoo paths may fail in restricted sessions, so broad unattended data proof cannot be guaranteed. | Session preflight commands can return `session_sec_unavailable` or `session_yfinance_unavailable`. | No, network/provider dependent | Use local reviewed rows when present; otherwise mark ticker/lane `still_blocked`, `skipped`, or `excluded` and move to the next executable lane. | External/manual gate |
| PB-008 | Keyed free-tier providers not configured | Medium | More fundamentals/share-count fallback coverage cannot expand through FMP, Alpha Vantage, or Finnhub until local keys are configured. | `make session-source-preflight` reports FMP, Alpha Vantage, and Finnhub as `provider_key_missing`; `make project-status` says the best next proof is `make provider-setup-checklist`. | No, owner setup dependent | Keep real keys out of the repo; use the reviewed one-ticker smoke command before broad batches after setup. | External/manual gate |

## Command Evidence

| Command | Result | Notes |
| --- | --- | --- |
| `git status --short --branch --untracked-files=no` | Passed with generated churn only | Rerun the live status gate before sharing. Local reviewed commits may be ahead of GitHub until pushed; dirty generated CSV/report churn and broad stock-report artifacts stay excluded by default. |
| `git log -5 --oneline` | Passed | Latest commits include public UX review completion, compact single-stock report start, and the reviewed provider smoke review sequence. |
| `make diff-hygiene-summary` | Passed | Product/code/docs/test package was clean before this audit refresh; generated/sample report churn stays local unless individually reviewed evidence. |
| `make pilot-readiness-check TOP_N=10` | Passed with manual gates | Verdict: `pilot-ready with manual gates`; public-check remains the explicit share gate. |
| `make project-status` | Passed | Reports the current local price, fundamentals/input-ready, operating-company DCF-ready, peer-ready, locked-input, provider-gap, and next-proof state. Treat exact counts as snapshot values and rerun before quoting them. |
| `make session-source-preflight` | Passed | SEC, SEC submissions, yfinance import/stage, Stooq/Yahoo price ladder, and local fundamentals are available; FMP, Alpha Vantage, and Finnhub keys are missing; IBKR remains optional and disabled. |
| `make readiness-ops-center` | Passed | Lane board confirms partial/blocked/manual/excluded states, source-proof queue exhaustion, and provider setup as the next safe proof path. |
| `make hosted-demo-readiness` | Passed with external account gate | Repo-side hosting files are ready; no public hosted Streamlit URL is configured, so GitHub remains the public link until deployment is verified. |
| `make provider-setup-checklist` | Passed | Checklist names FMP as the first keyed free-tier provider to configure and shows the reviewed smoke -> validate -> preview -> stop-before-apply sequence. |
| `make universe-preview-summary` | Passed | Read-only universe metadata preview returned 50 capped rows, with one new SMH metadata candidate and one fallback source warning. Universe membership remains metadata only and does not unlock fundamentals, share count, DCF, peers, earnings, estimates, or recommendations. |
| `make public-check` | Passed | Public wording, whitespace, full tests, dashboard smoke, browser QA evidence, and visitor-demo checks passed. |
| `make public-wording-check` | Passed | Public wording scan passed; rerun before sharing because the scanned file count changes as docs and sample artifacts change. |
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
- The remaining UI risk is not correctness; it is review freshness after future changes. Re-run browser QA, dashboard smoke, and live desktop/mobile review after UI wording, layout, route, or screenshot changes.

## Remaining External / Manual Gates

- Source coverage: trusted fundamentals, share counts, peer mappings, earnings, and analyst estimates require reviewed source rows. Code must not invent these.
- Provider setup: FMP, Alpha Vantage, and Finnhub are keyed free-tier fallbacks. Configure them only in local env files, run the reviewed one-ticker smoke command first, then validate and preview before applying any row.
- Hosted demo: no public hosted Streamlit URL is configured. Keep the GitHub repository link as the public share target until an external host/account is chosen and the hosted route passes the public gates.
- Public-check confirmation: run `make public-check` immediately before sharing so the wording, whitespace, full tests, dashboard smoke, browser QA evidence, and visitor-demo gates are fresh.
- License choice: the repository is public-reviewable under the controlled portfolio-demo license, but it should not be described as open source or reusable software unless the owner intentionally changes the license.

## Pilot Readiness Verdict

Ready for a controlled pilot with manual gates.

The current public share should focus on the GitHub/LinkedIn portfolio workflow: readiness-first product flow, real screenshots, local dashboard instructions, methodology, and visible source-proof boundaries. The next data-expansion move is not another broad proof loop; it is provider activation or reviewed source rows, one ticker at a time, through smoke, validate, preview, source-provenance review, rebuilt readiness, and proof history. The product should not be described as launch-ready, hosted, provider-backed, or full-universe analysis-ready until those external/source gates are actually satisfied.
