# Pilot Share Brief

> Data readiness first. Analysis second. Research decision last.

Use this as research-only product evidence. It summarizes what can be shown now, what is blocked by missing proof, and what must stay out of a share package.

## Pilot Share Answer

- Shareable now: portfolio/demo evidence with manual gates.
- Not shareable as: open-source/reuse package or data-freshness proof until the license and generated-artifact gates are resolved.
- Reuse rights: not granted until a root `LICENSE` exists.
- Keep local: broad generated CSV/JSON/report churn unless a specific artifact is reviewed evidence.
- Next gate: run `make public-check` and keep source-proof blockers visible.

## Current Pilot State: pilot-ready with manual gates

## What can be used now

- Price-ready setup coverage: 3537/3538.
- Momentum usable: 3535/3538.
- Fundamentals/input-ready coverage: 7/10 data sources available; 3 optional/manual lane(s) locked.
- DCF-ready operating-company coverage: 2691/3538.
- Peer-ready coverage: 29/3538.

## What is still blocked

- Leading proof queue: Source-proof queues reviewed or exhausted (manual).
- Blocked items in that queue: 90.
- Top blockers: 3,778 blocked and 486 partial proof item(s) remain visible, but current proof queues are already reviewed or non-actionable. Use project-status and provider setup before reopening broad proof queues.
- Next source-proof command: `make project-status`.

## How coverage expands next

- Next setup view: `make provider-setup-checklist`.
- Real key values are never printed.
- Source buckets:
  - Free public sources: SEC Companyfacts, SEC submissions, SEC filing documents, Stooq, Yahoo/yfinance
  - Keyed free-tier fallbacks: configured -; needs key FMP free tier, Alpha Vantage free tier, Finnhub free tier
  - Optional broker boundary: IBKR read-only (disabled unless explicitly configured)
- Coverage unlock decision:
  - No broad coverage batch should run from setup alone.
  - Use free/public sources for already executable proof paths; current gate says coverage_workflow_evidence.
  - Configure FMP free tier first only if you want a keyed fallback, then smoke one ticker.
  - Do not retry fundamentals_share_count_source_ladder until new source-backed rows, keyed provider data, reviewed manual rows, or changed blockers exist.
  - Provider setup only makes a source executable; readiness changes still require validate, preview, rejected-row review, source provenance, apply/skip decision, rebuilt readiness, and proof ledger evidence.
- Configure first: FMP free tier.
- Why first: Broadest keyed fallback here: price, fundamentals, share count, and the largest stated free-tier daily cap.
- Setup env: `FMP_API_KEY`.
- One-ticker smoke command: `make fmp-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> && make imports-preview IMPORT_TICKERS=<ticker>`.
- Do not configure all missing providers at once; configure one, rerun preflight, smoke one ticker, then validate/preview before any apply.
- FMP free tier: needs_key -> price, fundamentals, share_count; smoke: `make fmp-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> && make imports-preview IMPORT_TICKERS=<ticker>`; cannot unlock Full-universe refresh without caps, recommendations, order routing, or unreviewed valuation inputs.
- Alpha Vantage free tier: needs_key -> price, fundamentals, share_count; smoke: `make alpha-vantage-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> && make imports-preview IMPORT_TICKERS=<ticker>`; cannot unlock Full-universe refresh without caps, recommendations, order routing, or unreviewed valuation inputs.
- Finnhub free tier: needs_key -> price, fundamentals, share_count; smoke: `make finnhub-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> && make imports-preview IMPORT_TICKERS=<ticker>`; cannot unlock Full-universe refresh without caps, recommendations, order routing, or unreviewed valuation inputs.
- IBKR read-only: optional_disabled -> price; smoke: `make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=1 TOP_N=1 PROVIDER=ibkr`; cannot unlock Broker actions, order routing, auto-trading, fundamentals, shares, peers, earnings, or estimates.

## How to demo or review next

- Choose a focused review set first: `make universe-scope TOP_N=10`.
- Review liquidity/correlation context only after scope selection: `make risk-context`.
- Run the explicit public gate before sharing: `make public-check`.
- Screenshots and scope/risk context do not update saved data or unlock blocked inputs.

## Final share gate sequence

- GitHub sync: confirm the branch state before using the GitHub pilot link.
- generated artifact hygiene: keep broad CSV/JSON/report churn excluded unless exact artifacts are reviewed evidence.
- Public-check: run the explicit public share gate before sharing.
- license boundary: keep portfolio/demo wording until license status is selected.
- source-proof blockers stay visible; the share gate does not unlock blocked analysis inputs.

## What must stay out of the share package

- `data/analyst_estimates_readiness.csv`
- `data/dcf_readiness.csv`
- `data/earnings_readiness.csv`
- `data/fundamentals.csv`
- `data/outputs/research_decisions.csv`
- `data/price_coverage_report.csv`
- `data/prices.csv`
- `data/reports/analyst_estimates_readiness_report.csv`
- `data/reports/data_source_status.csv`
- `data/reports/dcf_readiness_report.csv`
- `data/reports/earnings_readiness_report.csv`
- `data/reports/feature_readiness_summary.csv`
- `data/reports/fundamentals_coverage_report.csv`
- `data/reports/peer_readiness_report.csv`
- `data/reports/peer_unlock_worklist.csv`
- `data/reports/price_coverage_report.csv`
- `data/reports/ticker_readiness_report.csv`
- `data/reports/universe_coverage_report.csv`
- `outputs/correlation_risk.csv`
- `outputs/data_quality_wizard.csv`
- `outputs/feature_readiness_summary.csv`
- `outputs/final_watchlist.csv`
- `outputs/liquidity_risk.csv`
- `outputs/market_direction.csv`
- `outputs/momentum_leaders.csv`
- `outputs/peer_unlock_worklist.csv`
- `outputs/purpose_classification.csv`
- `outputs/purpose_evaluation_summary.csv`
- `outputs/research_action_queue.csv`
- `outputs/research_decisions.csv`
- `outputs/undervalued_candidates.csv`
- `data/analyst_estimates.csv`
- `data/earnings.csv`
- `data/reports/ticker_readiness_report.previous.csv`
- `outputs/session_source_preflight.json`

## License boundary

- No root LICENSE file found.
- Do not claim reuse rights until a root LICENSE is selected and README wording is updated.

## Research-only boundary

- This is not investment advice, a ranking, or a recommendation.
- The product does not connect to brokers, route orders, auto-trade, or give direct trade instructions.
- Missing fundamentals, shares, peers, earnings, estimates, valuation inputs, and metrics stay blocked until trusted source proof passes.
