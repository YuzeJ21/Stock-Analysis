# Completed Milestones

This document is the historical completion log for Stock Research Command Center. The active delivery sequence lives in [ROADMAP.md](../ROADMAP.md); exact implementation history remains available through Git commits and tests.

## 2026-11-08 — MRVL issuer after-tax reconciliation

- Exact SEC 8-K/Exhibit 99.1 linkage supports the issuer's annual aggregate GAAP-to-non-GAAP reconciliation, with signed components, tax effect, source precision and independent share/EPS checks.
- The existing Workbench reuses this optional evidence in Valuation & Peers and Data Sources. Bad sources retain independent annual evidence; no extra Companyfacts/submissions fetch, canonical field, saved schema, valuation denominator or rights promotion follows. Gain-only after-tax allocation and normalized earnings remain gaps. [Method](ONLINE_PEER_VALUATION.md#mrvl-issuer-after-tax-reconciliation), [Release evidence](MRVL_AFTER_TAX_RELEASE.md)

## 2026-11-07 — MRVL annual earnings and AVGO comparison context

- MRVL's financial refresh supports an independent, in-memory review of seven exact annual components and both named annual documents. The compact Workbench explanation retains sources, dates, units, rights and per-field gaps without preparing company CSVs.
- AVGO is a source-backed business comparison with different business mix. Its annual period remains outside the existing window; this adds no numerical admission, trusted peer role, adjusted EPS or model readiness. Saved notes, immutable SEC receipts and existing research tools retain their own scope. [Method](ONLINE_PEER_VALUATION.md), [Release evidence](MRVL_PEER_EARNINGS_RELEASE.md)

## 2026-11-07 — Online company research continuity

- Company notes and eligible SEC evidence no longer require a local price-dependent report. Online notes are scoped to the selected profile, ticker and CIK; existing ticker-scoped journals remain separate and accessible without company/model rows.
- Monitor lists user-authored follow-ups separately from saved SEC comparisons and preserves issuer-specific return context. Saved notes and receipts can reopen offline after a session restart. Drafts survive section and Monitor detours; confirmation remains explicit.
- The existing annual SEC capture/import/replay method retains its field, identity, period and rights checks. Selected-CIK guards exclude other-issuer receipts without deleting them; NEM/AMD/DUK remain the independently qualified reasoned disposition scope.
- Intermediate-width navigation now stacks with the mobile rail, while retaining desktop navigation and phone cards. [Release evidence](ONLINE_COMPANY_WORKFLOW_RELEASE.md)

The CSV-first foundation described below is historical saved-model infrastructure. The current company workflow retrieves financials and prices online and does not require preparing per-company CSV inputs.

## 2026-11-06 — Company workflow and bounded SEC pair dispositions

- The local default route presents Research Desk -> Discover -> Company Workbench -> Monitor. Saved Business Trend, valuation scenarios, peer read-through, forward view, catalysts, Decision Lab history and the offline HTML brief remain under named Workbench disclosures. The English GitHub Pages demo mirrors their questions with fictional data, while its separate AMD page is a dated read-only SEC filing case.
- Monitor pins an exact ordered pair of saved annual SEC observations for NEM, AMD or DUK. A reasoned **Reviewed** or **Still open** disposition is scoped to the issuer, pair and selected research profile in an ignored local sidecar. The immutable receipts and evidence gaps remain inspectable. The fictional public example has tab-only decision state. [Saved SEC company reviews](SEC_RESEARCH_REVIEWS.md)
- The November 6 independent NEM annual recheck found zero financial changes and one retained operating-income gap. A changed archive digest affected source-review metadata. AMD first replayed two saves of the same FY2025 observation. Its independent recheck at 19:33 ET matched all four annual fields and recorded only issuer-association metadata change, with zero financial changes or gaps. [NEM SEC evidence review](NEM_SEC_REVIEW.md), [Saved SEC company reviews](SEC_RESEARCH_REVIEWS.md)
- The November 6 independent DUK annual recheck at 19:35 ET matched all four supported FY2025 fields with zero gaps. The issuer-directory digest changed and the comparison recorded zero financial changes. [Saved SEC company reviews](SEC_RESEARCH_REVIEWS.md)
- Legacy picks, portfolio, ranking and watchlist surfaces remain Operator-only compatibility utilities. The synthetic Earnings Nowcast pilot does not establish a real-company prediction. Revisit a parked investing view only after independent researcher sessions show a repeated decision need, permitted inputs and a no-ranking/no-trading design. Real-company nowcasting additionally needs point-in-time consensus and actuals rights, leakage-safe backtests and calibration. See the active [Roadmap](../ROADMAP.md) and the [NEM method](NEM_SEC_REVIEW.md).

## 2026-10-29 — Historical research-dossier presentation

The 2026-10-29 local research-dossier revision makes this flow easier to scan: compact task navigation, shorter Discover rows, a visible Company Brief next task, a five-lane saved-evidence map before the online SEC action, and an SEC annual-field table that exposes direct fields and withheld reasons. The saved-evidence map names an input path only when its metadata supports that label; unavailable optional rows do not become source proof. These presentation changes keep saved local readiness separate from the on-demand SEC inspection, do not refresh canonical data, and do not establish source rights or current-market coverage. Desktop, tablet, phone, zoom, and accessibility results belong to the exact local release packet, not to older screenshot anchors.

## Product Foundation

- Readiness-first, CSV-first architecture with central readiness and source-status reporting.
- Preview-first import workflows, rejected-row reporting, and readiness-gated decision output.
- ETF and index-proxy exclusion from operating-company DCF, with blocked inputs withheld rather than inferred.
- Master-universe, active-universe, and analysis-ready scopes separated in reports and dashboard flows.

## Personal Research And Commercial Beta Foundation

- The primary local research flow is Research Desk -> Discover -> Company Workbench -> Monitor. Public and Operator routes remain separate, and Data Health and Proof History stay available as Advanced Evidence without changing readiness.
- Research Desk, Discover, Company Workbench, and Monitor provide answer-first, fail-closed views over saved evidence. The shared shell, responsive route matrix, observation-recency interpretation, and downloadable offline Company Workbench brief are complete as local engineering work.
- Research Decision Lab and the collapsed Company Workbench authoring flow support append-only thesis, counter-thesis, evidence, catalyst, invalidation, scenario-assumption, and outcome records through validation, exact preview, and explicit confirmation. Saving a research record cannot change readiness, forecasts, probabilities, recommendations, or another ledger.
- Priority 1 quarantines legacy portfolio, ranking, position, picks, entry-zone, and transaction-like surfaces behind an Operator-only compatibility boundary. They cannot feed Personal Research, readiness, recommendations, sizing, or transaction behavior.
- Priority 2 provides a prospective-only field-proof audit with independent technical-write and commercial-evidence eligibility, receipt revalidation, and no readiness mapping. It does not upgrade legacy narrative proof or check in sample proof rows.
- Priority 3 completes in-app research-record authoring with receipt-bound confirmation, append locking, and active-thesis lineage checks. Production verification uses temporary ledgers and does not append repository research records.
- These milestones establish a local Commercial Research Beta release candidate and controlled demo package only. They do not establish hosted operation, current-market data, source rights, independent-human or assistive-technology validation, demand, screening performance, probability calibration, or commercial launch.

## Public Workflow And Reports

- Visitor-first public workflow: Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History.
- Single-stock report mode with readiness, methodology, source readiness check, Evaluation Snapshot, Proof Checklist, Best Review Path, and DCF/peer boundaries.
- Public-facing methodology documentation, Public README/dashboard polish, demo walkthrough, research-only guardrails, and controlled-share wording.
- `make stock-report-md TICKER=...` generates clean Markdown reports for visitor demos; `make stock-report TICKER=...` remains available when optional report data is useful for inspection.
- Reports show readiness, Evaluation Snapshot, Proof Checklist, Best Review Path, analysis quality, methodology, evaluation function checks, and ETF/index/fund reports show operating-company DCF as excluded, not failed.
- `Blocked by Data - Missing Peer Mapping` remains a readiness-gated state, not a generic monitor or recommendation label.
- Data Health provides one lane answer first; raw tables, command cards, provider setup, and proof ledgers remain behind advanced/operator detail.

## Pilot Reliability And Packaging

- Fresh Streamlit startup and render-level smoke coverage for all five public routes.
- Deterministic tracked `demo` profile with manifest, checksums, selected scenarios, and known limitations.
- Ignored mutable `local` profile for refresh/import churn, separate from the public demo package.
- Hosted-demo readiness guide, blank secrets templates, and an explicit no-hosted-URL boundary.
- Browser QA and screenshot evidence gates that keep screenshots as product evidence only.
- Local performance release gate passed on the fixed demo profile across all five public routes at 1280x720 and 390x844; the command remains a regression gate and does not prove hosted performance.

## Earnings Nowcast Software Foundation

- Point-in-time quarterly actual, consensus, evidence-signal, readiness, deterministic-range, and input-hash contracts.
- Leakage-safe walk-forward diagnostics with explicit exclusion reasons, benchmarks, calibration bins, and fail-closed numerical probability gates.
- Metric-specific quarterly canonicalization, explicit revision chains, conflict blocking, and Revenue/EPS comparability checks for currency, scale, accounting, share, operations, and split basis.
- Versioned read-only append-only templates, validation, conflict-aware preview, prospective collection planning, and per-ticker readiness commands with no automatic apply path.
- Six clearly synthetic reviewer scenarios covering ready, partial, candidate-only, post-cutoff blocked, excluded, and backtest-insufficient/un-calibrated states. These are software evidence only, not real-company or predictive proof.

## Provenance And Source Boundaries

- The October 2026 code-only merge added read-only NVIDIA Q1 FY2027 SEC cash-generation packet software and a six-company field-comparison view. The exact source capture and comparison reports are local ignored inputs, so a clean checkout shows the study as unavailable. The merge did not add raw filing material, canonical financial rows, listing expansion, or source-rights approvals.
- `docs/PROVENANCE_CONTRACT.md` defines readiness state, source, as-of date, reporting period, currency, retrieved-at date, method version, missing inputs, and confidence boundary.
- Reports surface `readiness-first-v1` provenance, source records, financial as-of date, reporting period, price/financial currency when present, missing inputs, and a research-only confidence boundary.
- Public Single-Stock first view shows the selected-ticker answer and compact provenance before advanced performance, valuation, and metric summaries; missing provenance stays visible rather than inferred.
- SEC Companyfacts, SEC submissions, explicit SEC filing-document shares, Stooq, and Yahoo/yfinance are source-routed through validate/preview/apply gates.
- FMP, Alpha Vantage, Finnhub, and optional read-only IBKR remain configured only through explicit provider boundaries; setup never bypasses proof gates.

## Data-Health Operator Workflow

- Pilot Operator Runbook V1 connects the share gate, source gate, provider setup, reviewed one-ticker smoke command, validate/preview, packet, and hygiene without reopening broad proof loops.
- Data Health Command Visibility Sweep V1 keeps Proof History, Operator context, and Pilot Share Gate detail summaries from showing command snippets by default; those summaries hide command snippets by default while the explicit packet command table remains available inside advanced review detail.
- Source-activation, provider-setup, proof-queue, peer, optional-context, and batch-proof surfaces preserve supported, candidate-context-only, still-blocked, skipped, and excluded outcomes.

## Historical Product Capabilities

- Benchmark/risk review metrics, provenance labels, scoped universe review, lazy broad-universe loading, and data-honest stock reports.
- Candidate-peer versus trusted-peer separation, peer trend versus valuation readiness, and source-backed peer proof routes.
- Optional earnings and analyst-estimate import interfaces with unavailable states when trusted rows are absent.

## Continuing Boundary

Completion of a feature does not mean its underlying data lane is fully covered. Current coverage and source availability must always be read from `make readiness-ops-center`, `make project-status`, and `make session-source-preflight` rather than inferred from this history.
