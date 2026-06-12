# Roadmap

This roadmap reflects the current direction of the local Python/Streamlit stock research command center. The product principle remains:

1. Data readiness first.
2. Analysis second.
3. Research decision last.

The next phase is not to add more indicators or AI-generated summaries. The next phase should turn the product page into a shareable broad-market research workflow while continuing to prove decision-useful research through trusted fundamentals, peer metrics, earnings, and analyst estimates.

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
- [x] Visitor-first dashboard navigation with three main paths: review one stock, improve data coverage, and explore ready names, while detailed pages remain available under `More pages`.
- [x] Public data-strategy guidance that separates safe automation from human-reviewed source judgment.
- [x] Data Health freshness routine promoted into the beginner flow with read-only checks, capped price dry-run guidance, and review-required lanes.
- [x] Blocked single-stock reports hold peer-relative valuation behind fundamentals/DCF readiness so peer rows cannot bypass core company gates.
- [x] Readiness-gated benchmark and risk review metrics for single-stock reports and dashboard review.

## 2. Current Product State

The product is usable today for price, momentum, and market-direction monitoring across the current active universe and a growing analysis-ready subset of the broad master universe.

The product is partially decision-useful for DCF-ready company research, but peer-relative analysis, earnings context, and analyst-estimate context remain blocked for most tickers because trusted source data is missing or incomplete. This is expected and correct: the system should not promote conclusions when the underlying data is not ready.

Current readiness pattern:

- Master universe rows: 3,538.
- Active research rows: 12.
- Price, momentum, liquidity, and correlation coverage can improve through capped local refresh/import workflows.
- Fundamentals and DCF coverage remain limited to trusted local/SEC-backed rows.
- Peer readiness remains intentionally sparse until source-backed peer mappings and peer inputs are imported.
- Earnings and analyst estimates remain locked until trusted local CSV rows are imported.
- Decision buckets remain readiness-gated: incomplete rows stay `Blocked by Data` or `Monitor` rather than becoming recommendations.

Use `make status-check TOP_N=5`, `make readiness`, or the dashboard Home page for exact current local counts.

The product correctly withholds unavailable conclusions. The next improvement is product-page workflow clarity plus trusted data ingestion, not more indicators.

## 3. Product-Page Roadmap

Goal: turn the Streamlit page into a research command center instead of a collection of CSV tables.

- Keep the top-level page focused on readiness, blockers, next actions, and single-stock drilldowns.
- Group next actions by feature:
  - Price Coverage Batch
  - Fundamentals / DCF Proof
  - Peer Mapping Proof
  - Peer Valuation Inputs Proof
  - Earnings Import Setup
  - Analyst Estimates Import Setup
  - Single-Stock Review
- Keep dashboard commands copyable only; do not run imports, refreshes, or account actions from the product page.
- Keep broad-universe tables row-limited by default.
- Add source readiness notes wherever an action depends on local CSVs, staged import files, Yahoo price refresh, SEC staging, or manual trusted inputs.
- [x] Add source readiness context to `project_status_next_steps.csv`, `make project-status`, and dashboard next-action cards.
- Make active-universe vs master-universe language visible wherever counts differ.

### Data Readiness Operations Center V1

Goal: choose broad data-readiness lanes before drilling into individual tickers.

- [x] Add a read-only lane operations command with `make readiness-ops-center`.
- [x] Add a coverage frontier command with `make coverage-frontier TOP_N=10`.
- [x] Keep price coverage, fundamentals/DCF, peer mapping, peer valuation inputs, locked earnings, locked analyst estimates, and excluded/not-applicable states separate.
- [x] Show batch next actions and generated-churn policies in Data Health before detailed ticker tables.
- Keep frontier ranks framed as data operations impact, not security attractiveness or investment recommendation.

### Reviewed Batch Execution V1

Goal: turn a selected coverage-frontier lane into a safe reviewed run packet.

- [x] Add `make reviewed-batch LANE=prices TOP_N=10`.
- [x] Write `outputs/reviewed_batch_packet.md` and `outputs/reviewed_batch_packet.csv`.
- [x] Include snapshot, dry-run, capped execution, validate/preview/apply gates, post-run proof, expected artifacts, rollback, and proof-row template.
- [x] Warn when saved readiness artifacts are missing or stale before relying on counts.
- Keep generated packet artifacts reviewed separately; do not commit broad data refresh churn by default.

### Readiness-Gated Review Metrics V1

Goal: add useful benchmark, risk, fundamentals, valuation, and peer context without turning missing inputs into conclusions.

- [x] Add `make benchmark-risk-review TICKER=<ticker> BENCHMARK=SPY`.
- [x] Add `make metric-readiness` as an alias for the same read-only review path.
- [x] Calculate benchmark-relative return, max drawdown, rolling volatility, beta, Sharpe, and Sortino only from local price history.
- [x] Support SPY and QQQ benchmark choices when local benchmark rows exist.
- [x] Show partial/blocked states when benchmark history is missing or too short.
- [x] Label Sharpe and Sortino as historical review metrics, not recommendations.
- [x] Keep fundamentals trend partial unless multiple trusted fundamentals periods exist.
- [x] Keep valuation multiples blocked unless trusted fundamentals plus market-cap or price/share-count context exist.
- [x] Keep peer valuation dispersion blocked unless mapped peers have trusted valuation inputs.
- [x] Surface the metrics in single-stock Markdown reports and the dashboard Snapshot tab.
- [x] Add a central `make metric-readiness TOP_N=10` summary with explicit readiness freshness context.
- [x] Refine the dashboard metrics section from raw table-first output into summary cards plus an optional details table.
- [x] Add configurable risk-free-rate defaults in project config while keeping the assumption visible in report output.

Next improvements:

- Add richer multi-period fundamentals trend only when trusted historical rows are available.

## 4. Trusted Data Proof Roadmap

### A. Trusted Fundamentals Ingestion

Goal: prove fundamentals readiness without fabricating company data.

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

### B. DCF Readiness Proof

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

### C. Peer Readiness Proof

Goal: support peer analysis without pretending peer valuation is available when only partial peer data exists.

- Add source-backed peer mappings.
- Add mapped-peer price, fundamentals, market cap, and valuation inputs when mappings already exist.
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
- Reports show readiness, Evaluation Snapshot, Proof Checklist, Best Review Path, analysis quality, methodology, evaluation function checks, valuation status, research decision, source readiness check, blocked inputs, and next research steps.
- ETF/index/fund reports show operating-company DCF as excluded, not failed.
- Reports now open with a visitor scan cue, then `At A Glance`, `Reader Guide`, `Evaluation Snapshot`, `Proof Checklist`, and `Best Review Path` so first-time visitors see mode, decision view, DCF state, peer context, optional context, data-confidence cue, proof step, and next local step before methodology detail.
- The dashboard Single-Stock Report page includes At A Glance and Best Review Path cards, while Markdown reports include an Evaluation Snapshot explaining supported evaluation, valuation boundary, data-confidence cue, next proof, and stop rule before detailed sections.
- Reports include a mode guide comparing `DCF-ready review`, `Standalone DCF review`, `Price/setup review only`, `Monitor-only context`, and `Data needed before analysis`.
- Blocked and partial reports include `Copyable Proof Commands` with capped, local, research-only commands for price, fundamentals/DCF, peer mapping, optional-context imports, and the one-company trusted-data pilot packet.
- Reports flag caveated peer-relative context in At A Glance when trusted peers exist but mapped-peer valuation metrics are incomplete.

Next improvements:

- [x] Add more visible examples of richer company, standalone DCF, price/setup gated, monitor-only, and blocked-data reports on the dashboard Home page.
- [x] Link Data Health and blocked single-stock reports to `make trusted-data-pilot-packet TICKER=<ticker>` so the trusted-data pilot has one consistent before/report, review, validate/apply, and rebuild-proof path.
- Keep methodology and assumptions visible while continuing to reduce engineer-heavy wording.

Rules:

- Must stay data-honest.
- Must show blocked, partial, ready, and excluded states.
- Must not fabricate missing fundamentals, earnings, analyst estimates, peers, or valuation inputs.
- Must not produce buy/sell instructions.

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
- Empty trusted rows should render as unavailable, not as conclusions.
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

Goal: turn the public project into a usable research workflow while the data universe grows through safe, reviewable proof steps.

This stage should improve breadth without pretending the whole 3,538-ticker universe is analysis-ready. It should favor capped refreshes, preview-first imports, source readiness visibility, and plain-English next actions.

| Workstream | Next product step | Safe command path | Completion signal |
| --- | --- | --- | --- |
| Scalable price refresh | Replace manual repeated 25-ticker refreshes with capped batches and dry-run-first guidance. | `make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=yahoo`, then `make readiness-snapshot`, then capped `make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=yahoo SLEEP_SECONDS=30`, then `make diff-hygiene`. | Price-ready coverage improves without committing broad CSV churn by default. |
| Trusted fundamentals | Use SEC staging when configured, or trusted manual fundamentals imports when not. | `make sec-stage-queue TOP_N=25`, `make focus-fundamentals TICKER=...`, `make imports-validate`, `make imports-preview`, `make imports-apply`. | `fundamentals_ready` and `dcf_ready` improve only from trusted rows. |
| Source-backed peers | Prioritize active-universe and DCF-ready peer blockers before broad peer work. | `make peer-mapping-queue TOP_N=25`, `make focus-peers TICKER=...`, `make templates`, `make imports-validate`, `make imports-preview`, `make imports-apply`. | Peer trend and peer valuation states are separated; peer valuation appears only when trusted peer inputs pass readiness. |
| Optional context | Keep earnings and analyst estimates locked until trusted local rows exist. | `make optional-context-worklist TOP_N=25`, `make import-earnings`, `make import-analyst-estimates`, `make imports-validate`, `make imports-preview`, `make imports-apply`. | Empty optional context reads as intentionally locked, not broken or inferred. |
| Source readiness guidance | Make source age, rejected-row reports, and generated-data hygiene visible before interpretation. | `make project-status`, `make research-health-check TOP_N=10`, `make public-check`, `make diff-hygiene`. | Visitors can see what is fresh, what is stale, what is local-only, and what should not be committed. |
| Data strategy | Keep a public, data-honest explanation of what can refresh safely and what still needs trusted human/source review. | Read `docs/DATA_STRATEGY.md`, then use the targeted commands above for a 5-10 company pilot. | Visitors understand why broad valuation coverage is limited and how the next trusted proof step should happen. |

Public-share rules for this stage:

- Keep the README demo path and sample reports short enough for GitHub/LinkedIn visitors.
- Keep dashboard pages plain-language first, with commands and file paths behind focused help or tables.
- Keep the sidebar focused on the three main visitor paths, with `More pages` still reachable for deeper local review.
- Do not publish broad generated CSV churn unless it is the reviewed artifact for that release.
- Do not add workflows that run imports, refreshes, account actions, direct recommendations, fabricated data, or valuation labels without ready inputs.

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
- [x] Single-stock reports distinguish clean peer readiness from peer readiness with missing valuation-metric caveats.
- [x] Dashboard navigation defaults to public visitor paths while preserving `More pages` and deep links.
- [x] Public data-strategy docs explain what can be automated and what still requires trusted source judgment.
- [x] `make pipeline` passes in the latest full data-output verification run.
- [x] `make onboarding` passes in the latest full data-output verification run.
- [x] `make research-health` passes in the latest full data-output verification run.
- [x] `make readiness` passes in the latest full data-output verification run.
- [x] `make test` passes through `make public-check`.
- [x] `make dashboard-smoke` passes through `make public-check`.

Current boundary:

- The product workflow for fundamentals import, SEC staging guidance, peer blocker triage, public UI polish, and single-stock report generation is implemented and verified at the public-share gate.
- The remaining unchecked readiness-count items require real trusted data rows. They should not be closed by fabricated data or by committing broad CSV churn.
- If the next work session is data-focused, start with `make readiness-snapshot`, then run only scoped trusted-data proof loops, then run the full verification commands listed above before updating these boxes.

## Guardrails

- Do not fabricate market data.
- Do not fabricate fundamentals.
- Do not fabricate peer metrics.
- Do not fabricate earnings.
- Do not fabricate analyst estimates.
- Do not add broker integration.
- Do not add auto-trading.
- Do not produce buy/sell recommendations.
