# External Skill Map

This project selectively adapts ideas from:

- `himself65/finance-skills`
- `himself65/trade-skills`

The adaptation rule is simple:

- use them as research workflow inspiration
- do not install or mirror them wholesale
- do not import broker, order, or recommendation behavior

## Finance Skills Mapping

Source reviewed:

- `finance-skills` README / market-analysis catalog

Relevant market-analysis concepts listed upstream:

- `company-valuation`
- `earnings-preview`
- `earnings-recap`
- `estimate-analysis`
- `stock-correlation`
- `stock-liquidity`
- `options-payoff`
- `sepa-strategy`
- `yfinance-data`
- `generative-ui`

### Already implemented in this project

- `company-valuation`
  - covered by `src/valuation.py`
  - includes DCF, relative valuation, scenarios, and sensitivity
- `yfinance-data`
  - covered through provider interfaces only
  - remains optional, unofficial, and research-grade
- `earnings-preview` / `earnings-recap`
  - partially covered through local CSV schemas, stock-report assembly, and structured earnings summaries
- `estimate-analysis`
  - partially covered through analyst-estimate schemas and stock-report summaries
- `generative-ui`
  - partially reflected as dashboard/UI inspiration only

### Not implemented yet

- `stock-correlation`
- `stock-liquidity`
- `options-payoff`
- `sepa-strategy`
- `etf-premium`
- `saas-valuation-compression`

### Safe future enhancements

- `stock-correlation`
  - research-only correlation and co-movement analysis
- `stock-liquidity`
  - research-only volume/spread/market-impact analysis
- `options-payoff`
  - education-only payoff visualization
  - must require user-supplied legs or clearly labeled examples
- `sepa-strategy`
  - transparent, rules-only screening
  - no hidden entries, no sizing advice, no order language
- improved earnings and estimate workflows
  - local CSV-first and source-transparent
- UI inspiration from `generative-ui`
  - layout and interaction ideas only

### Should stay excluded or optional

- social-reader integrations
- paid/API-key-dependent providers as required dependencies
- TradingView desktop / CDP integrations
- sentiment APIs as core dependencies
- any hidden recommendation layer
- any direct broker, execution, or auto-trading behavior

## Trade Skills Mapping

Source reviewed:

- `trade-skills` README / trade skill summary

Upstream positioning:

- multi-leg options trading assistant
- concrete strikes
- IV-aware structures
- probability-weighted scenarios
- case studies and pitfalls

### Safe concepts for this project

- options risk education
- payoff/risk explanation
- volatility-regime awareness as education
- common options pitfalls
- case-study style warnings

### Explicitly rejected for this project

- concrete strike selection
- expiration recommendations
- “enter this trade” language
- options position sizing advice
- executable order tickets
- broker/API integration
- options trade recommendations

## Project stance

This repository remains:

- CSV-first
- research-only
- explanation-first
- explicitly non-executional

Any future adaptation from external skill catalogs must preserve those constraints.
