# Pilot Share Brief

> Data readiness first. Analysis second. Research decision last.

Use this as research-only product evidence. It summarizes what can be shown now, what is blocked by missing proof, and what must stay out of a share package.

## Current Pilot State: pilot-ready with manual gates

## What can be used now

- Price-ready setup coverage: 3537/3538.
- Momentum usable: 3535/3538.
- Fundamentals/input-ready coverage: 7/10 data sources available; 3 optional/manual lane(s) locked.
- DCF-ready operating-company coverage: 2691/3538.
- Peer-ready coverage: 29/3538.

## What is still blocked

- Leading proof queue: DCF Input Proof Batches (partial).
- Blocked items in that queue: 90.
- Top blockers: fundamentals_bundle: 242, fundamentals_bundle_plus_shares: 91.
- Next source-proof command: `make dcf-input-proof-queue TOP_N=10`.

## How coverage expands next

- Next setup view: `make provider-setup-checklist`.
- Real key values are never printed.
- FMP free tier: needs_key -> price, fundamentals, share_count; smoke: `make fmp-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> && make imports-preview IMPORT_TICKERS=<ticker>`; cannot unlock Full-universe refresh without caps, recommendations, order routing, or unreviewed valuation inputs.
- Alpha Vantage free tier: needs_key -> price, fundamentals, share_count; smoke: `make alpha-vantage-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> && make imports-preview IMPORT_TICKERS=<ticker>`; cannot unlock Full-universe refresh without caps, recommendations, order routing, or unreviewed valuation inputs.
- Finnhub free tier: needs_key -> price, fundamentals, share_count; smoke: `make finnhub-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> && make imports-preview IMPORT_TICKERS=<ticker>`; cannot unlock Full-universe refresh without caps, recommendations, order routing, or unreviewed valuation inputs.
- IBKR read-only: optional_disabled -> price; smoke: `make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=1 TOP_N=1 PROVIDER=ibkr`; cannot unlock Broker actions, order routing, auto-trading, fundamentals, shares, peers, earnings, or estimates.

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
