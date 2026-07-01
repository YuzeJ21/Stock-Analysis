# Source Activation Guide

This guide explains how to unlock more source-backed coverage without turning the product into a broker, recommendation, or trading workflow. It is research-only and not investment advice.

## Setup Surface

Real provider keys must stay local. Do not commit `config/provider_keys.env`, `.env`, `.env.local`, account identifiers, tokens, or broker session files.

```bash
cp config/provider_keys.env.example config/provider_keys.env
chmod 600 config/provider_keys.env
```

Use placeholder values while documenting setup:

```bash
FMP_API_KEY=REPLACE_WITH_FMP_FREE_TIER_KEY
ALPHA_VANTAGE_API_KEY=REPLACE_WITH_ALPHA_VANTAGE_FREE_TIER_KEY
FINNHUB_API_KEY=REPLACE_WITH_FINNHUB_FREE_TIER_KEY
STOOQ_API_KEY=REPLACE_WITH_STOOQ_KEY_IF_REQUIRED
```

IBKR is optional read-only daily OHLCV and disabled by default:

```bash
IBKR_HOST=REPLACE_WITH_LOCAL_IBKR_HOST
IBKR_PORT=REPLACE_WITH_LOCAL_IBKR_PORT
IBKR_CLIENT_ID=REPLACE_WITH_LOCAL_CLIENT_ID
```

Leave IBKR unset unless you intentionally run IBKR Gateway/TWS for read-only daily OHLCV. The product must not use broker order, account trading, order routing, or auto-trading APIs.

## Provider Capabilities

| Source | Setup | Can help cover | Cannot unlock by itself |
| --- | --- | --- | --- |
| SEC Companyfacts | `SEC_USER_AGENT` | fundamentals, share count when explicit facts exist | peers, earnings estimates, recommendations |
| SEC submissions | `SEC_USER_AGENT` | CIK, entity, SIC, filing recency metadata only | DCF, valuation, earnings, analyst estimates |
| SEC filing documents | `SEC_USER_AGENT` | explicit filing-document share count facts | inferred shares, revenue, free cash flow |
| Stooq | no key or `STOOQ_API_KEY` if required | price daily OHLCV | fundamentals, share count, peers |
| Yahoo/yfinance | optional dependency | price, provider-assisted fundamentals, optional context | trusted proof without validate/preview/apply |
| FMP free tier | `FMP_API_KEY` | price, fundamentals, share count fallback | unlimited batch coverage |
| Alpha Vantage free tier | `ALPHA_VANTAGE_API_KEY` | price, fundamentals, share count fallback | broad unlimited refresh |
| Finnhub free tier | `FINNHUB_API_KEY` | price, fundamentals, share count fallback | broad unlimited refresh |
| IBKR read-only | `IBKR_HOST`, `IBKR_PORT`, `IBKR_CLIENT_ID` | price read-only daily OHLCV | fundamentals, recommendations, broker actions |

Free-tier fallbacks are capped by product policy. Start with `make session-source-preflight`, then use the lane-specific dry-run/validate/preview/apply gates.

Optional earnings and analyst-estimate rows have an extra boundary. Provider-assisted rows may supply only earnings timing or price-target context. Those rows can be recorded as `candidate_context_only`, but they do not unlock the full optional readiness lane unless the row also contains the required earnings metrics or EPS/revenue estimate fields. Price-target context is research context only and must not be rendered as a recommendation.

## Non-Retry Rule

If a source path fails in a session, record the reason once and pivot:

- SEC unavailable: do not retry SEC-backed fundamentals/share-count in that session.
- yfinance unavailable: do not retry Yahoo-backed fundamentals in that session.
- keyed provider missing: mark the source as `keyed_free_tier_missing` and show the setup command.
- IBKR not configured: keep it `optional_broker_disabled`; do not treat it as a blocker.

If a source path is reachable but the current queue is already covered by reviewed
`still_blocked`, `skipped`, `excluded`, or `candidate_context_only` proof rows,
do not run the same lane again. The Source Activation Console should route to
workflow evidence or source setup until new provider data, keyed sources,
reviewed manual rows, or changed blockers appear.

The next safe command is usually:

```bash
make session-source-preflight
make coverage-frontier TOP_N=10
```

## Readiness Boundary

Source activation only makes a lane executable. It does not mark data as ready. Rows still need:

```bash
make imports-validate IMPORT_TICKERS=<ticker>
make imports-preview IMPORT_TICKERS=<ticker>
make imports-apply IMPORT_TICKERS=<ticker>
make readiness
```

Do not fabricate missing prices, fundamentals, shares, peers, earnings, estimates, valuation inputs, metrics, or recommendations.
