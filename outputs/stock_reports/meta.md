# META Single-Stock Research Report

Research-only local report. It summarizes readiness and does not provide allocation instructions.
Visitor scan: read At A Glance, Reader Guide, Evaluation Snapshot, and Proof Checklist first; deeper sections only explain the evidence behind those gates.

## At A Glance
- Mode: `Price/setup review only`.
- Decision view: Blocked by Data - Missing Fundamentals.
- DCF: Blocked until trusted fundamentals and DCF inputs are ready.
- Valuation support: Blocked until trusted DCF inputs are ready; missing now: shares outstanding.
- Peer context: Locked until source-backed peer inputs are ready.
- Optional context: Locked until trusted earnings and analyst-estimate rows exist.
- Method: project readiness gates decide what can appear; DCF formula output is withheld until trusted price, fundamentals, cash-flow or margin, share-count, and DCF fields pass readiness.
- Next local step: Complete trusted fundamentals for META; missing fields: shares outstanding. Run `make focus-fundamentals TICKER=META`, then use SEC staging or the manual fundamentals import workflow.

## Reader Guide
- Analyze now: Use available price or setup context only. Company-level valuation stays blocked until trusted fundamentals, free cash flow or margin inputs, share count, and DCF fields are ready.
- Still locked: Blocked features: DCF, earnings, analyst estimates. Excluded features: none. Unavailable sections are intentionally locked; missing data is not inferred.
- Trusted input: Trusted fundamentals such as revenue, free cash flow or margin, and shares outstanding.
- One-company pilot packet: `make trusted-data-pilot-packet TICKER=META` is read-only; use it to inspect local file status, rejected-row checks, and the validate/preview/apply proof path before changing readiness.
- Data Health lane: Fundamentals / DCF Proof. Suggested local check: `make focus-fundamentals TICKER=META`. Confirm with `make dcf-readiness && make readiness` before treating the lane as available.
- Next research step: Complete trusted fundamentals for META; missing fields: shares outstanding. Run `make focus-fundamentals TICKER=META`, then use SEC staging or the manual fundamentals import workflow.

## Evaluation Snapshot
- Supported evaluation: Use available price or setup context only. Company-level valuation stays blocked until trusted fundamentals, free cash flow or margin inputs, share count, and DCF fields are ready.
- Valuation boundary: Company valuation is blocked until trusted fundamentals, cash-flow or margin, share-count, and DCF inputs pass readiness.
- Confidence cue: low: price/setup context is available, but company valuation inputs are blocked.
- Next proof: Complete trusted fundamentals for META; missing fields: shares outstanding. Run `make focus-fundamentals TICKER=META`, then use SEC staging or the manual fundamentals import workflow.
- Stop rule: Blocked features: DCF, earnings, analyst estimates. Excluded features: none. Unavailable sections are intentionally locked; missing data is not inferred.

## Proof Checklist
- Current mode proof: `Price/setup review only` because price/setup may be usable, but fundamentals or DCF inputs have not passed readiness.
- Next proof step: `make focus-fundamentals TICKER=META` before reviewing company valuation.
- Withhold until proven: Blocked features: DCF, earnings, analyst estimates. Excluded features: none. Unavailable sections are intentionally locked; missing data is not inferred.
- Manual check: Complete trusted fundamentals for META; missing fields: shares outstanding. Run `make focus-fundamentals TICKER=META`, then use SEC staging or the manual fundamentals import workflow.

## Best Review Path
- First read: Start with DCF Input Triage and Missing-Data Proof Summary. Company valuation stays blocked until trusted fundamentals and DCF inputs are ready.
- Then check: What We Can Analyze Now, Valuation Boundary Checklist, and Source Readiness Check.
- Optional context: Optional earnings and analyst-estimate context remains locked unless trusted local rows exist.
- Copy-only proof step: `make focus-fundamentals TICKER=META`

## How To Read This Report
- Read top-down: readiness state first, supported analysis second, blocked or excluded analysis third.
- Current use: Price/setup review only until trusted fundamentals, DCF, and peer inputs are ready.
- Method source: project code implements readiness gates and report wording; libraries and adapters support data handling/UI, but shipped analysis comes from project code and local data.
- Boundary: this is research context only. It does not provide allocation instructions, account actions, or direct recommendations.

## Executive Summary
- Bottom line: META is in `Price/setup review only` mode. Use price and setup context only. Company valuation stays blocked until trusted fundamentals and DCF inputs exist.
- Use now: Use available price or setup context only. Company-level valuation stays blocked until trusted fundamentals, free cash flow or margin inputs, share count, and DCF fields are ready.
- Do not infer: Blocked features: DCF, earnings, analyst estimates. Excluded features: none. Unavailable sections are intentionally locked; missing data is not inferred.
- Next step: Complete trusted fundamentals for META; missing fields: shares outstanding. Run `make focus-fundamentals TICKER=META`, then use SEC staging or the manual fundamentals import workflow.

## Analysis Mode Guide
- `DCF-ready review` (other): Fullest company review: price, fundamentals, DCF, and source-backed peer context are ready.
- `Standalone DCF review` (other): Company DCF can be reviewed, but peer-relative valuation remains blocked.
- `Price/setup review only` (current): Use trend/setup context only; company valuation waits for trusted fundamentals and DCF inputs.
- `Monitor-only context` (other): Use ETF/index/fund market or risk context; operating-company DCF is excluded, not failed.
- `Data needed before analysis` (other): Reference state for tickers with no trusted local inputs yet; add the first missing input before drawing conclusions.

## One-Minute Status
META overall readiness: partial; review ready inputs first and treat locked inputs as missing-data review work. Decision: Blocked by Data - Missing Fundamentals. DCF: blocked. Primary blocker: fundamentals. Peer workflow: waits for trusted price, fundamentals, and DCF inputs first. Optional earnings or analyst-estimate context is unavailable until trusted local CSV rows exist. Next: Complete trusted fundamentals for META; missing fields: shares outstanding. Run `make focus-fundamentals TICKER=META`, then use SEC staging or the manual fundamentals import workflow.

## What We Can Analyze Now
- Ready inputs: price, momentum, market direction, liquidity, correlation, portfolio.
- Supported now: Use available price or setup context only. Company-level valuation stays blocked until trusted fundamentals, free cash flow or margin inputs, share count, and DCF fields are ready.
- Still locked or excluded: Blocked features: DCF, earnings, analyst estimates. Excluded features: none. Unavailable sections are intentionally locked; missing data is not inferred.

## Next Layer To Prove
- Current supported layer: Price/setup review only; company valuation stays locked until fundamentals and DCF inputs pass readiness.
- Next trusted input: Trusted fundamentals, free-cash-flow or margin inputs, share count, and DCF fields.
- Proof command: `make focus-fundamentals TICKER=META` before treating the next layer as available.
- Stop rule: if trusted rows are unavailable, leave the section locked; do not infer, backfill, or use placeholders.

## Data And App Method
- Source inputs: local CSV rows or labeled provider-assisted rows supply prices, fundamentals, peers, earnings, and estimates.
- Product checks: project readiness gates decide whether each input is usable before report sections appear.
- DCF method: blocked locally because required price, fundamentals, cash-flow or margin, share count, or DCF fields are missing; the report does not ask a third party or model to create a valuation opinion.
- Peer method: blocked locally until source-backed peer mappings and peer metrics exist; sector or industry fallback is not treated as trusted peer valuation.
- Optional context method: locked locally until trusted earnings and analyst-estimate rows pass import validation; empty optional files are an intentional locked state, not hidden analysis.
- Output wording: supported, blocked, partial, and excluded sections are written from project code so missing data cannot become a weak conclusion.

## Analysis Quality
- Analysis mode: Price/setup review only.
- Confidence: low: price/setup context is available, but company valuation inputs are blocked.
- Why: Use price and setup context only. Company valuation stays blocked until trusted fundamentals and DCF inputs exist.
- Optional context: Earnings and analyst estimates stay locked until trusted local rows exist.

## Methodology
- Method order: readiness gate first, supported analysis second, valuation math third, explanation last.
- Input boundary: local or provider-assisted rows supply data; project rules decide readiness, calculations, blockers, and report wording.
- Analysis recipe: prices support setup/trend review; fundamentals support field review and DCF input quality; DCF supports scenario math; source-backed peers support peer context; optional earnings and estimates add timing or consensus context only.
- Black-box check: every supported section should trace back to a ready input, a visible formula or score, or an explicit blocker listed in this report.
- Methodology proof ladder: input row -> readiness gate -> local calculation or score -> supported/blocked/excluded label -> explicit next step.
- Reader check path: start with Source Readiness, then Data Readiness, then DCF Calculation Path or Peer Workflow; if any step is missing, the related conclusion stays withheld.
- Fundamental analysis: local revenue, cash-flow, margin, share-count, cash/debt, and source fields are reviewed only when present; missing fields are not inferred.
- DCF formula path: base FCF -> projected FCF -> discounted FCF plus discounted terminal value -> enterprise value -> equity value -> fair value per share.
- DCF status boundary: ready means assumptions can be reviewed, blocked means required company inputs are missing, and excluded means the method does not fit ETF/index/fund monitor context.
- DCF method: standalone DCF stays blocked until trusted local price, revenue, free cash flow or FCF margin, shares outstanding, and DCF fields pass readiness checks.
- Peer method: peer-relative valuation stays withheld until source-backed peer mappings and peer valuation inputs are ready.
- Score boundary: setup, watchlist, confidence, and monthly scores are triage aids for review order only; they are not price targets, expected returns, or allocation instructions.
- Report method: text is built from local readiness, DCF, peer, decision, and source readiness outputs; blocked or excluded sections are explained instead of filled.

## Evaluation Function Check
- Readiness gate: strongest function; it decides ready, blocked, or excluded before any conclusion is shown.
- Price and setup: ready for local trend/setup review.
- Risk context: ready for local liquidity/correlation context.
- Fundamentals / DCF: blocked until trusted fundamentals, cash-flow or margin, share-count, and DCF inputs are ready.
- Peer comparison: blocked until source-backed peer mappings and peer valuation inputs are ready.
- Optional context: locked until trusted local earnings and analyst-estimate rows exist.
- Method source: readiness gates, DCF boundaries, peer blockers, and report wording are implemented in project code; standard libraries/adapters support data handling and UI, but shipped analysis comes from project code and local data.

## What This Stock Is
- Ticker: META
- Asset type: company
- Current role: Core Compounder. Test whether trend, fundamentals, and DCF support the long-duration thesis; current state needs thesis review.

## Decision
- Bucket: Blocked by Data
- Subtype: Blocked by Data - Missing Fundamentals
- Boundary: Missing-data proof state: fundamentals blocks evaluation, so conclusions stay withheld.
- Primary blocker: fundamentals
- Main reason: Company research is blocked by missing DCF data.
- Next action: Complete trusted fundamentals for META; missing fields: shares outstanding. Run `make focus-fundamentals TICKER=META`, then use SEC staging or the manual fundamentals import workflow.

## Purpose Evaluation
Research-only purpose brief. It separates what local data supports from what remains locked or excluded.
- Thesis: Core Compounder. Test whether trend, fundamentals, and DCF support the long-duration thesis; current state needs thesis review.
- Alignment: Purpose alignment needs review: Core Compounder depends on durable thesis support, but current local outputs flag trend/thesis conflict. Review the readiness sections below before drawing conclusions.
- Research review summary: Purpose alignment needs review: Core Compounder depends on durable thesis support, but current local outputs flag trend/thesis conflict. Next blocker: fundamentals. Withheld: DCF interpretation, peer-relative valuation or opportunity-cost comparison, earnings timing or surprise context, analyst estimate trend context, compounder thesis confirmation. Review the readiness sections below before drawing conclusions.
- Setup: Compounder setup: Thesis Review Needed; final state: Thesis Review Needed. Review the readiness sections below before drawing conclusions.
- Valuation boundary: Valuation conclusion is blocked until trusted DCF/fundamental inputs are complete.

## Supported Analysis
- Supported analysis: price history, setup and momentum context, market/theme context, liquidity context, correlation/risk context. Partial inputs present: fundamentals.

## Locked Analysis
- Currently withheld: DCF interpretation, peer-relative valuation or opportunity-cost comparison, earnings timing or surprise context, analyst estimate trend context, compounder thesis confirmation.

## Setup / Momentum
- Compounder setup: Thesis Review Needed; final state: Thesis Review Needed. Review the readiness sections below before drawing conclusions.
- 1M performance: -7.4%
- 3M performance: -4.2%
- 1Y performance: -4.0%
- ATR / volatility: Not available; missing values stay visible instead of guessed.

## Risk Notes
- Risk watchpoint: compounder purpose is under thesis review because final state is `Thesis Review Needed`. Review the readiness sections below before drawing conclusions.
- Invalidation condition: Already flagged for trend/purpose review in the current local setup state.

## Next Research Step
- Next research question: Which trusted fundamentals or DCF fields are needed to confirm whether the compounder thesis remains supported?
- Review priority: High review priority: compounder purpose conflicts with current trend/thesis state and needs manual thesis review.
- Data-confidence explanation: Data confidence is low: primary blocker is fundamentals; blocked features are DCF, peer, earnings, analyst estimates.

## Data Readiness
- Overall state: partial
- Price ready: ready
- Momentum ready: ready
- Liquidity ready: ready
- Correlation ready: ready
- Fundamentals ready: not ready
- DCF ready: not ready
- Peer ready: not ready
- Earnings ready: not ready
- Analyst estimates ready: not ready
- Blocked features: DCF, earnings, analyst estimates
- Excluded features: none

## Price Coverage
- Price rows: 616
- First date: 2023-12-07
- Last date: 2026-05-22
- Missing price reason: none

## Valuation Readiness
- DCF status: blocked.
- DCF missing inputs: shares outstanding.
- Why DCF is blocked: missing shares outstanding.
- DCF assumptions: withheld until price, fundamentals, free cash flow or FCF margin, and share-count inputs are ready.
- Sensitivity table: unavailable until the base DCF can be calculated.
- Relative valuation: withheld until trusted fundamentals and DCF readiness pass; available peer context is held back until the company DCF gate is ready (peer status=calculated; peer count=2).
- Valuation conclusion is shown only when trusted DCF and peer inputs support it; missing valuation inputs are not inferred.

## DCF Calculation Path
- State: blocked; the product withholds DCF math until trusted company inputs pass readiness checks.
- Required local inputs: trusted price, revenue, free cash flow or FCF margin, shares outstanding, and cash/debt or net-debt context.
- Missing now: shares outstanding.
- Formula path: withheld before base FCF, projected FCF, terminal value, equity value, or fair value/share are calculated.
- Sensitivity: unavailable until the base DCF can be calculated from trusted inputs.

## DCF Input Triage
- DCF input triage: blocked inputs are repair steps, not negative company signals.
- Calculation dependency: trusted price and share count anchor per-share output; revenue plus free cash flow or FCF margin builds base FCF; cash/debt adjusts enterprise value to equity value.
- Missing shares outstanding: converts equity value into fair value per share; missing share count blocks per-share DCF output. Proof path: add trusted shares outstanding in the fundamentals import, then run `make imports-validate` and `make dcf-readiness`.
- Safe sequence: `make focus-fundamentals TICKER=META` -> stage SEC or trusted manual fundamentals rows -> `make imports-validate` -> `make imports-preview` -> `make imports-apply` -> `make dcf-readiness`.

## Valuation Boundary Checklist
- DCF boundary: blocked until trusted price, fundamentals, cash-flow or margin, share-count, and DCF fields pass readiness.
- Peer-relative boundary: withheld until trusted fundamentals and DCF readiness pass first.
- Optional-context boundary: locked until trusted local earnings and analyst-estimate rows pass import validation.
- Conclusion boundary: missing or excluded inputs do not become intrinsic value, peer-relative value, undervalued, or overvalued conclusions.

## Peer Workflow
- What this means: peer valuation waits behind price, fundamentals, and standalone DCF readiness.
- What can be reviewed now: only the ready local inputs listed above; peer rows should not create valuation context yet.
- What is still locked: peer trend and peer valuation remain withheld until core company inputs are ready.
- Trusted input path: resolve fundamentals / DCF first, then use `make focus-peers TICKER=META` if peer context is still needed.
- Peer ladder: paused behind core company readiness.
- Mapping evidence: mapping status=mapped; peer count=2. Do not use peer rows to bypass missing price, fundamentals, or DCF inputs.
- Trend evidence: withheld until core company readiness passes and mapped peer price history is useful.
- Valuation evidence: withheld until standalone DCF plus source-backed peer mappings and peer valuation inputs pass readiness.
- Next safe command: `make focus-peers TICKER=META` only after the core DCF blockers are resolved.
- Peer blocker type: blocked until fundamentals / DCF
- Mapping status: waiting for price, fundamentals, and DCF
- Peer count: 2
- Trend comparison ready: not ready
- Valuation comparison ready: not ready
- DCF peer comparison ready: not ready
- Sample peers: AAPL, GOOG
- Next peer action: Peer-relative valuation should wait until trusted price, fundamentals, and DCF inputs are ready.

## Optional Context Workflow
- Optional context ladder: earnings and analyst estimates add timing, consensus, and revision context only; they never create a valuation conclusion by themselves.
- Earnings evidence: locked; missing trusted local CSV input is an intentional state, not broken analysis. Use schema-only templates first; templates are not data.
- Analyst-estimate evidence: locked; missing trusted local CSV input is an intentional state, not hidden consensus analysis.
- Earnings path: `make templates` -> place trusted rows in `data/staged/earnings/` -> `make import-earnings` -> `make imports-validate` -> `make imports-preview` -> `make imports-apply`.
- Analyst-estimates path: `make templates` -> place trusted rows in `data/staged/analyst_estimates/` -> `make import-analyst-estimates` -> `make imports-validate` -> `make imports-preview` -> `make imports-apply`.
- Rejected-row checks: review `data/rejected/earnings_import_rejected.csv` and `data/rejected/analyst_estimates_import_rejected.csv` before trusting optional context.
- Rebuild proof: run `make optional-context-readiness`, then `make stock-report-md TICKER=META` to confirm optional sections changed from locked to available.
- No-conclusion boundary: missing earnings or estimates must not appear as event timing, consensus, revision, upside, downside, undervalued, or overvalued analysis.

## Missing Data
- Fair value per share could not be derived because shares outstanding is unavailable.
- No trusted analyst-estimate CSV has been added yet.
- No trusted earnings CSV has been added yet.
- Peer input still missing: P/E unavailable for peer(s) GOOG.
- Valuation input still missing: EBITDA.
- Valuation input still missing: market cap, price, and share count.
- Valuation input still missing: shares outstanding.
- Analyst estimates: no trusted local row for this ticker; optional context stays locked.
- Earnings: no trusted local row for this ticker; optional context stays locked.

## Source Readiness
- local:prices.csv: research-grade / local; source readiness: daily CSV through 2026-05-22; Saved local research data.
- local:fundamentals.csv: research-grade / local; source readiness: dataset row as of 2017-12-31; Local fundamentals data.; Dataset row source: sec_companyfacts
- local:earnings.csv: research-grade / local; source readiness: not available in local CSVs; Earnings fields stay locked until trusted rows are imported.
- local:analyst_estimates.csv: research-grade / local; source readiness: not available in local CSVs; Analyst-estimate fields stay locked until trusted rows are imported.

## Missing-Data Proof Summary
- Data Health lane: Fundamentals / DCF Proof. Suggested local check: `make focus-fundamentals TICKER=META`. Confirm with `make dcf-readiness && make readiness` before treating the lane as available.
- Price proof path: Price history is usable now (616 local row(s)); keep it fresh before relying on setup or risk context.
- Fundamentals / DCF proof path: Fundamentals / DCF are blocked: missing shares outstanding. Inspect `make focus-fundamentals TICKER=META`, then use `make sec-stage TICKERS=META` when SEC_USER_AGENT is configured or prepare trusted manual fundamentals rows before `make imports-validate`, `make imports-preview`, `make imports-apply`, and `make dcf-readiness`.
- Peer proof path: Peer valuation should wait until trusted price, fundamentals, and DCF inputs are ready.
- Optional context proof path: Earnings and analyst estimates remain optional and locked until trusted local rows are imported with `make templates`, `make imports-validate`, `make imports-preview`, and `make imports-apply`.
- Import paths, rejected-row files, and credential state are listed in the Source Readiness Check below.

## Copyable Proof Commands
- Copy-only: these are local research commands to copy when you choose; the report does not run imports or refreshes and does not connect to external accounts.
- Inspect this ticker: `make stock-report-md TICKER=META`.
- One-company proof packet: `make trusted-data-pilot-packet TICKER=META`.
- Price source readiness: `make focus-price TICKER=META`.
- Fundamentals / DCF: `make focus-fundamentals TICKER=META`.
- SEC/manual import checklist: `make sec-stage-queue TICKERS=META TOP_N=10`.
- Fundamentals import safety: `make imports-validate && make imports-preview && make imports-apply`.
- DCF rebuild proof: `make dcf-readiness && make readiness` before reading standalone DCF output.
- Peer mapping: `make focus-peers TICKER=META`.
- Peer mapping checklist: `make peer-mapping-queue TICKERS=META TOP_N=10`.
- Peer import safety: `make templates && make imports-validate && make imports-preview && make imports-apply`.
- Peer rebuild proof: `make readiness && make peer-mapping-queue TICKERS=META TOP_N=10` before reading peer-relative valuation.
- Optional context checklist: `make optional-context-worklist TICKERS=META TOP_N=10`.
- Optional templates: `make templates`.
- Earnings import: `make import-earnings`.
- Analyst-estimates import: `make import-analyst-estimates`.
- Optional import safety: `make imports-validate && make imports-preview && make imports-apply`.
- Optional-context rebuild proof: `make optional-context-readiness && make readiness` before treating earnings or estimates as available context.

## Source Readiness Check
- Prices: ready; local source `data/prices.csv`; coverage 2023-12-07 to 2026-05-22; rows=616; import file path `data/staged/prices/` or `data/imports/prices.csv`; rejected rows `data/rejected/price_import_rejected.csv`.
- Fundamentals / DCF: blocked; local source `data/fundamentals.csv`; reason missing shares outstanding; SEC_USER_AGENT present; import file path `data/staged/fundamentals/` or `data/imports/fundamentals.csv`; rejected rows `data/rejected/fundamentals_import_rejected.csv`.
- Peers: blocked until fundamentals / DCF; local source `data/peers.csv`; import file path `data/imports/peers.csv`; next peer action Peer-relative valuation should wait until trusted price, fundamentals, and DCF inputs are ready.
- Earnings: not ready; trusted local CSV only; import file path `data/staged/earnings/`; command `make import-earnings`; rejected rows `data/rejected/earnings_import_rejected.csv`.
- Analyst estimates: not ready; trusted local CSV only; import file path `data/staged/analyst_estimates/`; command `make import-analyst-estimates`; rejected rows `data/rejected/analyst_estimates_import_rejected.csv`.
- Credentials: SEC_USER_AGENT present; STOOQ_API_KEY missing; missing remote credentials should not break local CSV reports or preview-first local import workflows.
- Report command: `make stock-report-md TICKER=META`. Research-only Markdown output; copyable command only.
