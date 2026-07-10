# Roadmap

Stock Research Command Center follows one principle: **data readiness first, analysis second, research decision last**. It is research-only software: no investment advice, broker trading, order routing, auto-trading, direct buy/sell instructions, or fabricated data.

This is the active plan only. Completed delivery history lives in [Completed Milestones](docs/COMPLETED_MILESTONES.md).

## Current Truth

Use live, read-only commands instead of static counts:

- Master universe rows: use `make project-status` or `make status-check TOP_N=5`.
- Active research rows: use `make project-status` or the dashboard Home page.
- Lane readiness: use `make readiness-ops-center`.
- Source/provider state: use `make session-source-preflight` and `make provider-setup-checklist`.
- Package/share state: use `make pilot-readiness-check TOP_N=10` and `make public-check`.

The product deliberately separates the tracked master universe, active universe, and analysis-ready subset. It must never imply that the whole tracked universe is analysis-ready.

Public visitor flow: **Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History**.

## Now

### P0: Public Hosted Demo Verification

**Goal:** turn the deterministic `demo` profile into a verified, controlled hosted demo without exposing local refresh data or credentials.

Repository-side preparation is complete. The remaining deployment work requires an external host/account and a verified public URL.

1. Choose a Streamlit-compatible host and deploy `main` with `dashboard.py` as the entrypoint.
2. Set `STOCK_RESEARCH_DATA_PROFILE=demo` in the host environment.
3. Keep provider keys, account IDs, tokens, and broker/session files out of the repo and public app.
4. Verify the five-page workflow on the hosted URL at desktop and mobile widths.
5. Set `HOSTED_DEMO_URL` locally only after the URL opens successfully, then rerun the public gates before changing GitHub or LinkedIn copy.

**Dependencies:** external hosting account, public URL, and a human browser review of the deployed route.

**Stop rule:** keep GitHub as the public link until the hosted route is verified. Screenshots remain product evidence only, never data-freshness proof.

### P0: Controlled Pilot Review

**Goal:** validate whether an external reviewer can understand the product in under three minutes.

1. Share the GitHub demo package with 5-10 reviewers.
2. Ask reviewers to follow the public visitor flow without operator instructions.
3. Record only concrete issues: where they started, what they thought was usable, what looked blocked, and what they expected to do next.
4. Prioritize reproducible first-viewport, wording, routing, or accessibility defects. Do not use pilot feedback to weaken readiness gates.

Use [Controlled Pilot Review Feedback](docs/PILOT_REVIEW_FEEDBACK_TEMPLATE.md) to capture anonymous, reproducible workflow observations without collecting personal, portfolio, or investment-opinion data.

**Dependencies:** external reviewers and controlled feedback collection.

**Stop rule:** do not call pilot feedback data proof; it only validates product clarity and workflow reliability.

## Next

### P1: FMP One-Ticker Source Smoke

**Goal:** add one controlled keyed free-tier fallback after the public pilot foundation is stable.

1. Configure `FMP_API_KEY` outside Git in the ignored local key file or host secrets.
2. Run `make project-status-check`; only continue if it identifies a reviewed candidate scope.
3. Run `make fmp-smoke TICKER=<ticker>` for one ticker.
4. Run `make imports-validate IMPORT_TICKERS=<ticker>` and `make imports-preview IMPORT_TICKERS=<ticker>`.
5. Apply only if validation passes, preview scope is intended, rejected rows are zero, and source provenance is present.
6. Record a supported, candidate-context-only, still-blocked, skipped, or excluded outcome before any larger batch.

**Dependencies:** an FMP key and an executable reviewed candidate. The current source-proof queues have no unreviewed executable company candidates, so provider reachability alone does not unlock coverage.

**Stop rule:** no broad batch from setup alone. Provider setup/source-boundary review must happen before `make trusted-data-pilot-candidates TOP_N=10` only after source state changes.

### P1: Price History Maintenance

Price coverage uses `PROVIDER=auto` in this fixed order: **Stooq, Yahoo**, optional IBKR read-only when explicitly configured, then keyed FMP, Alpha Vantage, and Finnhub fallbacks. The remaining short-history case is a depth boundary, not a reason to rerun broad refreshes while coverage remains otherwise complete.

### P2: 25-50 Company Trusted-Peer Pilot

**Goal:** address the largest analytical-depth gap without inferring trusted peers across the full universe.

1. Select 25-50 operating companies from a few clearly comparable industries.
2. Generate candidate peer context from SIC, industry, and product context; label it `candidate_context_only`.
3. Promote a relationship only after source-backed review captures peer source, review date, rationale, and as-of context.
4. Keep peer trend readiness separate from peer valuation readiness.
5. Require trusted peer price, fundamentals, and valuation inputs before relative valuation appears.

**Dependencies:** a licensed or otherwise trustworthy peer relationship source and reviewed mappings.

**Stop rule:** sector similarity is not trusted-peer proof. Do not target broad-universe peer readiness before the pilot has repeatable evidence.

## Later

### P3: Optional Earnings And Analyst Estimates

Proceed only when a trusted provider supplies supported earnings actual/estimate fields, estimate period, source, and retrieval/as-of date. Date-only and target-price-only data remain `candidate_context_only`; optional context never unlocks DCF readiness or becomes a recommendation.

### P3: Scheduler Maturity

Add scheduled monitoring only after at least one provider pilot proves deterministic batch limits, provenance, rejection handling, and proof-ledger recording. Daily price and filing checks may be read-only; imports still require validation, preview, and source gates.

### Later: Broader Peer Expansion

Expand beyond the peer pilot only after trusted relationship sourcing, review capacity, and lane-level quality checks are repeatable.

## Dependencies And Manual Gates

| Item | State | What the repo can do | What remains external |
| --- | --- | --- | --- |
| Hosted demo | repo-ready | deterministic demo profile, deployment guide, and local public checks | hosting account, verified public URL, browser review |
| FMP fallback | optional key missing | one-ticker smoke, validation, preview, provenance gate | `FMP_API_KEY` outside Git |
| Alpha Vantage / Finnhub | optional keys missing | capped fallback interfaces and source-state checks | provider keys and a reviewed use case |
| Trusted peers | source-gated | candidate/trusted state separation and proof workflow | reviewed source relationships and rationale |
| Earnings / estimates | intentionally locked | optional-context states and import gates | trusted provider/manual rows with supported fields |

## Success Gates

### Public Demo Gate

- `make demo-data-check`
- `make demo-dashboard-smoke`
- `make demo-dashboard-render-smoke`
- `make public-check`
- `make browser-qa-evidence`
- `make public-wording-check`
- `make pilot-readiness-check TOP_N=10`
- `make diff-hygiene-summary`
- `git diff --check`

### Source-Backed Apply Gate

- A narrow, intended ticker scope.
- Source provenance and relevant as-of context.
- `make imports-validate IMPORT_TICKERS=<ticker>` passes.
- `make imports-preview IMPORT_TICKERS=<ticker>` is narrow and rejected rows are zero.
- Readiness and proof evidence are rebuilt after an approved apply.

## Permanently Out Of Scope

- Broker execution, account actions, order routing, or auto-trading.
- Direct buy/sell instructions or investment recommendations.
- Fabricated prices, fundamentals, shares, peers, earnings, estimates, valuation inputs, or metrics.
- Promoting candidate peers, stale rows, screenshots, or provider setup into trusted readiness proof.
