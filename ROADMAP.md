# Roadmap

This roadmap reflects the current direction of the local Python/Streamlit stock research command center. The product principle remains:

1. Data readiness first.
2. Analysis second.
3. Research decision last.

The next phase is not to add more indicators or AI-generated summaries. The next phase should turn the product page into an operational broad-market command center while continuing to unlock decision-useful research through trusted fundamentals, peer metrics, earnings, and analyst estimates.

## 1. Completed Milestones

The following milestones are completed or mostly completed across the active-universe workflow and the broad-universe command-center foundation:

- [x] Readiness-first architecture.
- [x] CSV-first workflow.
- [x] Central readiness reporting.
- [x] Data-source status reporting.
- [x] Preview-first/manual import paths.
- [x] Price readiness for the current active universe.
- [x] Master-vs-active universe separation.
- [x] DCF gating.
- [x] ETF and index-proxy exclusion from operating-company DCF.
- [x] Final watchlist blocking when valuation is not ready.
- [x] Monthly picks staying empty when data is insufficient.
- [x] Dashboard smoke passing.
- [x] Test suite passing.
- [x] Broad-universe command center visibility for the current 3,538-ticker master universe.
- [x] Product-page readiness filters, row limits, and single-stock drilldown.
- [x] Peer Mapping Studio V1 with peer blocker filters and safe command cards.
- [x] Feature readiness summary and readiness-gated decision subtype reporting.
- [x] Single-stock report mode with readiness, methodology, source readiness check, DCF/peer gating, and ETF/index DCF exclusion.
- [x] Public-facing methodology documentation that explains readiness gates, fundamentals review, DCF formula path, peer boundaries, score limits, and report explanation.
- [x] Public README/dashboard polish for visitor-friendly demo paths, screenshot preview, generated-data hygiene, deep links, and research-only guardrails.

## 2. Current Product State

The product is usable today for price, momentum, and market-direction monitoring across the current active universe and a growing analysis-ready subset of the broad master universe.

The product is partially decision-useful for DCF-ready company research, but peer-relative analysis, earnings context, and analyst-estimate context remain blocked for most tickers because trusted source data is missing or incomplete. This is expected and correct: the system should not promote unsupported conclusions when the underlying data is not ready.

Current readiness pattern:

- Master universe rows: 3,538.
- Active research rows: 12.
- Price, momentum, liquidity, and correlation coverage can improve through capped local refresh/import workflows.
- Fundamentals and DCF coverage remain limited to trusted local/SEC-backed rows.
- Peer readiness remains intentionally sparse until source-backed peer mappings and peer inputs are imported.
- Earnings and analyst estimates remain locked until trusted local CSV rows are imported.
- Decision buckets remain readiness-gated: incomplete rows stay `Blocked by Data` or `Monitor` rather than becoming unsupported recommendations.

Use `make status-check TOP_N=5`, `make readiness`, or the dashboard Home page for exact current local counts.

The product correctly withholds unsupported conclusions. The next improvement is product-page workflow clarity plus trusted data ingestion, not more indicators.

## 3. Product-Page Roadmap

Goal: turn the Streamlit page into a research command center instead of a collection of CSV tables.

- Keep the top-level page focused on readiness, blockers, next actions, and single-stock drilldowns.
- Group next actions by feature:
  - Price Coverage Batch
  - Fundamentals / DCF Unlock
  - Peer Mapping Unlock
  - Earnings Import Setup
  - Analyst Estimates Import Setup
  - Single-Stock Review
- Keep dashboard commands copyable only; do not execute actions from the product page.
- Keep broad-universe tables row-limited by default.
- Add source readiness notes wherever an action depends on local CSVs, import drafts, Yahoo price refresh, SEC staging, or manual trusted inputs.
- [x] Add source readiness context to `project_status_next_steps.csv`, `make project-status`, and dashboard next-action cards.
- Make active-universe vs master-universe language visible wherever counts differ.

## 4. Data-Unlock Roadmap

### A. Trusted Fundamentals Ingestion

Goal: unlock fundamentals readiness without fabricating company data.

- Configure `SEC_USER_AGENT`.
- Run SEC staging for active company tickers.
- Or support trusted manual fundamentals import through existing validate/preview/apply workflows.
- Validate required fields:
  - `revenue`
  - `free_cash_flow`
  - `fcf_margin`
  - `shares_outstanding`
- Generate or update `fundamentals_coverage_report.csv`.
- Improve `fundamentals_ready` from the current broad baseline of 23/3,538.

Acceptance notes:

- SEC staging should remain preview-first and reviewable.
- Manual imports must be source-backed.
- Invalid rows must be rejected into CSV reports instead of silently dropped.

### B. DCF Readiness Unlock

Goal: allow valuation conclusions only when DCF data is genuinely ready.

- Keep ETFs and index proxies excluded from operating-company DCF.
- Do not generate undervalued or overvalued conclusions for `not_ready` tickers.
- Improve `dcf_readiness_report.csv`.
- Only allow valuation conclusions for DCF-ready companies.
- Keep missing fields explicit per ticker.

Acceptance notes:

- `undervalued_candidates.csv` must keep `valuation_status=not_ready` for incomplete rows.
- DCF-ready companies must have trusted price and fundamentals inputs.
- DCF logic should remain transparent and conservative.

### C. Peer Readiness Unlock

Goal: support peer analysis without pretending peer valuation is available when only partial peer data exists.

- Add source-backed peer mappings.
- Add peer metrics.
- Separate readiness into:
  - `peer_price_ready`
  - `peer_momentum_ready`
  - `peer_fundamentals_ready`
  - `peer_valuation_ready`
- Do not require valuation readiness for peer trend comparison.
- Do not show peer valuation if peer valuation inputs are missing.

Acceptance notes:

- Peer relationships must be source-backed or transparently labeled as sector/industry fallback.
- Peer trend comparison may use price/momentum readiness.
- Peer valuation requires valuation inputs and should remain blocked when metrics are missing.

### D. Decision-Bucket Refinement

Goal: improve decisions so they are more informative than generic monitoring rows.

Baseline issue: the system previously produced generic `Monitor` decisions when price data was ready but core company research data was blocked. Recent work has started separating company data blockers from ETF monitoring, but the roadmap should continue refining this into durable reason codes and sub-buckets.

Add reason codes or sub-buckets:

- `Monitor - Price/Momentum Ready`
- `Monitor - ETF Market Proxy`
- `Blocked by Data - Missing Fundamentals`
- `Blocked by Data - Missing Peer Mapping`
- `Excluded - DCF Not Applicable`

Rules:

- `Research Now` cannot be assigned when critical data is missing.
- Company tickers with missing fundamentals or DCF inputs should not be treated as generic monitor candidates.
- ETFs can remain monitor candidates for market/risk use while staying excluded from company DCF.

## 5. P1 Roadmap

### A. Portfolio/Risk Completeness

Goal: clarify risk readiness and reduce avoidable warnings.

- [x] Classify missing sector/theme ETF OHLCV, such as `ARKF`, as optional benchmark/proxy context rather than a core ticker price blocker.
- Improve liquidity/correlation readiness from the current broad baseline of 232/3,538 where appropriate.
- [x] Add ATR versus volatility-proxy provenance to momentum outputs, dashboard cards, monthly-pick reasons, and stock-report Markdown.
- Keep proxy-based risk notes clearly labeled as approximations in generated outputs after the next pipeline/report refresh.

### B. Single-Stock Research Mode V2

Goal: keep improving the already implemented single-ticker report so it is the clearest product surface for stock evaluation.

Current status:

- `make stock-report-md TICKER=...` generates clean Markdown reports for visitor demos.
- `make stock-report TICKER=...` remains available when optional report data is useful for inspection.
- The dashboard includes a Single-Stock Report page and local deep links such as `?page=single-stock-report`.
- Reports show readiness, analysis quality, methodology, evaluation function checks, valuation status, research decision, source readiness check, blocked inputs, and next research steps.
- ETF/index/fund reports show operating-company DCF as excluded, not failed.
- Reports now open with an `At A Glance` block so first-time visitors see mode, decision view, DCF state, peer context, optional context, and next local step before methodology detail.
- The dashboard Single-Stock Report page includes an At A Glance methodology card explaining project readiness gates and the DCF formula path before detailed tables.
- Reports include a mode guide comparing `DCF-ready review`, `Standalone DCF review`, `Price/setup review only`, `Monitor-only context`, and `Data-unlock only`.
- Blocked and partial reports include `Copyable Unlock Commands` with capped, local, research-only commands for price, fundamentals/DCF, peer mapping, and optional-context imports.

Next improvements:

- [x] Add more visible examples of richer company, standalone DCF, price/setup gated, monitor-only, and blocked-data reports on the dashboard Home page.
- Keep methodology and assumptions visible while continuing to reduce engineer-heavy wording.

Rules:

- Must stay data-honest.
- Must show blocked, partial, ready, and excluded states.
- Must not fabricate missing fundamentals, earnings, analyst estimates, peers, or valuation inputs.
- Must not produce unsupported buy/sell instructions.

### C. Market-Wide Universe Layer

Goal: support broader universe management without forcing expensive full-market analysis on dashboard load.

- Add or continue planning `universe_master.csv`.
- Keep `universe_active.csv` as the focused research subset.
- Allow single-stock lookup outside the active universe.
- Do not force full-market analysis on dashboard load.
- Support lazy/scoped analysis.
- Support active-universe, ticker-list, sector/theme, ready-only, and missing-data scopes.

## 6. P2 Roadmap

Goal: add trusted optional context workflows after fundamentals/DCF/peer readiness is no longer the main blocker.

- Trusted earnings import.
- Trusted analyst estimates import.
- Dashboard unavailable states when no trusted rows exist.
- Rejected-row reporting.
- Readiness reports for earnings and analyst estimates.

Rules:

- Earnings and analyst estimates are manual/trusted-local only until a provider interface is deliberately added.
- Empty trusted rows should render as unavailable, not as unsupported conclusions.
- Analyst consensus must not be treated as a recommendation.

## 7. Deprioritized Items

The following are intentionally deprioritized:

- More indicators.
- AI-generated recommendations.
- Monthly picks.
- Full-market ranking.
- Complex DCF model tuning.
- Additional dashboard charts.

Reason: the blocker is not the lack of indicators. The blocker is missing trusted data for fundamentals, peers, earnings, and analyst estimates.

## 8. Next Public Roadmap Stage

Goal: turn the public project into a usable research workflow while the data universe grows through safe, reviewable unlocks.

This stage should improve breadth without pretending the whole 3,538-ticker universe is analysis-ready. It should favor capped refreshes, preview-first imports, source readiness visibility, and plain-English next actions.

| Workstream | Next product step | Safe command path | Completion signal |
| --- | --- | --- | --- |
| Scalable price refresh | Replace manual repeated 25-ticker refreshes with capped batches and dry-run-first guidance. | `make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=yahoo`, then `make readiness-snapshot`, then capped `make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=yahoo SLEEP_SECONDS=30`, then `make diff-hygiene`. | Price-ready coverage improves without committing broad CSV churn by default. |
| Trusted fundamentals | Use SEC staging when configured, or trusted manual fundamentals imports when not. | `make sec-stage-queue TOP_N=25`, `make focus-fundamentals TICKER=...`, `make imports-validate`, `make imports-preview`, `make imports-apply`. | `fundamentals_ready` and `dcf_ready` improve only from trusted rows. |
| Source-backed peers | Prioritize active-universe and DCF-ready peer blockers before broad peer work. | `make peer-mapping-queue TOP_N=25`, `make focus-peers TICKER=...`, `make templates`, `make imports-validate`, `make imports-preview`, `make imports-apply`. | Peer trend and peer valuation states are separated; peer valuation appears only when trusted peer inputs pass readiness. |
| Optional context | Keep earnings and analyst estimates locked until trusted local rows exist. | `make optional-context-worklist TOP_N=25`, `make import-earnings`, `make import-analyst-estimates`, `make imports-validate`, `make imports-preview`, `make imports-apply`. | Empty optional context reads as intentionally locked, not broken or inferred. |
| Source readiness guidance | Make source age, rejected-row reports, and generated-data hygiene visible before interpretation. | `make project-status`, `make research-health-check TOP_N=10`, `make public-check`, `make diff-hygiene`. | Visitors can see what is fresh, what is stale, what is local-only, and what should not be committed. |

Public-share rules for this stage:

- Keep the README demo path and sample reports short enough for GitHub/LinkedIn visitors.
- Keep dashboard pages plain-language first, with commands and file paths behind focused help or tables.
- Do not publish broad generated CSV churn unless it is the reviewed artifact for that release.
- Do not add execution workflows, direct recommendations, fabricated data, or unsupported valuation labels.

## 9. Acceptance Criteria For The Next Roadmap Milestone

The next roadmap milestone is complete when:

- [x] The product page clearly separates the 3,538-ticker master universe, 12-ticker active universe, and analysis-ready subset through the top-level Universe Layers cards and table.
- [x] The product page includes a grouped next-action console with safe capped or ticker-targeted commands.
- [x] Next-action rows include source readiness context and clearly state that dashboard commands are copyable only.
- [x] `SEC_USER_AGENT` is detected locally, and manual fundamentals imports validate/preview through the trusted CSV workflow.
- [ ] `fundamentals_ready` improves beyond 23/3,538 with trusted data only.
- [ ] `dcf_ready` improves beyond 23/3,538 with trusted data only.
- [x] Peer readiness improves beyond 3/3,538 or peer blockers become more specific and actionable.
- [x] Decision buckets remain more informative than generic monitor rows.
- [x] `ARKF` and risk warnings are resolved or clearly classified.
- [x] Single-stock research mode can generate a data-honest report.
- [x] `make pipeline` passes in the latest full data-output verification run.
- [x] `make onboarding` passes in the latest full data-output verification run.
- [x] `make research-health` passes in the latest full data-output verification run.
- [x] `make readiness` passes in the latest full data-output verification run.
- [x] `make test` passes through `make public-check`.
- [x] `make dashboard-smoke` passes through `make public-check`.

Current boundary:

- The product workflow for fundamentals import, SEC staging guidance, peer blocker triage, public UI polish, and single-stock report generation is implemented and verified at the public-share gate.
- The remaining unchecked readiness-count items require real trusted data rows. They should not be closed by fabricated data or by committing broad CSV churn.
- If the next work session is data-focused, start with `make readiness-snapshot`, then run only scoped trusted-data unlocks, then run the full verification commands listed above before updating these boxes.

## Guardrails

- Do not fabricate market data.
- Do not fabricate fundamentals.
- Do not fabricate peer metrics.
- Do not fabricate earnings.
- Do not fabricate analyst estimates.
- Do not add broker integration.
- Do not add auto-trading.
- Do not produce unsupported buy/sell recommendations.
