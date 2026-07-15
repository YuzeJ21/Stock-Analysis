# Completed Milestones

This document is the historical completion log for Stock Research Command Center. The active delivery sequence lives in [ROADMAP.md](../ROADMAP.md); exact implementation history remains available through Git commits and tests.

## Product Foundation

- Readiness-first, CSV-first architecture with central readiness and source-status reporting.
- Preview-first import workflows, rejected-row reporting, and readiness-gated decision output.
- ETF and index-proxy exclusion from operating-company DCF, with blocked inputs withheld rather than inferred.
- Master-universe, active-universe, and analysis-ready scopes separated in reports and dashboard flows.

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
