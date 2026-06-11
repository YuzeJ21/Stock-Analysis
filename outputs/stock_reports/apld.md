# APLD Single-Stock Research Report

Research-only local report. It summarizes readiness and does not provide allocation instructions.
Visitor scan: read At A Glance, Reader Guide, Evaluation Snapshot, and Proof Checklist first; deeper sections only explain the evidence behind those gates.

## At A Glance
- Mode: `Price/setup review only`.
- Decision view: Blocked by Data - Missing Fundamentals.
- DCF: Blocked until trusted fundamentals and DCF inputs are ready.
- Valuation support: Blocked until trusted DCF inputs are ready; missing now: free cash flow, shares outstanding, revenue, FCF margin.
- Peer context: Locked until source-backed peer inputs are ready.
- Optional context: Locked until trusted earnings and analyst-estimate rows exist.
- Method: project readiness gates decide what can appear; DCF uses local free-cash-flow inputs, discounted cash flows, discounted terminal value, cash/debt adjustment, and fair value per share when ready.
- Next local step: Import trusted fundamentals for APLD. If SEC_USER_AGENT is configured, use SEC staging; otherwise use the manual fundamentals import workflow.

## Reader Guide
- Analyze now: Use available price or setup context only. Company-level valuation stays blocked until trusted fundamentals, free cash flow or margin inputs, share count, and DCF fields are ready.
- Still locked: Blocked features: fundamentals, DCF, peer, earnings, analyst estimates. Excluded features: portfolio. Unavailable sections are intentionally locked; missing data is not inferred.
- Trusted input: Trusted fundamentals such as revenue, free cash flow or margin, and shares outstanding.
- Data Health lane: Fundamentals / DCF Unlock. Suggested local check: `make focus-fundamentals TICKER=APLD`. Confirm with `make dcf-readiness && make readiness` before treating the lane as unlocked.
- Next research step: Import trusted fundamentals for APLD. If SEC_USER_AGENT is configured, use SEC staging; otherwise use the manual fundamentals import workflow.

## Evaluation Snapshot
- Supported evaluation: Use available price or setup context only. Company-level valuation stays blocked until trusted fundamentals, free cash flow or margin inputs, share count, and DCF fields are ready.
- Valuation boundary: Company valuation is blocked until trusted fundamentals, cash-flow or margin, share-count, and DCF inputs pass readiness.
- Confidence cue: low: price/setup context is available, but company valuation inputs are blocked.
- Next proof: Import trusted fundamentals for APLD. If SEC_USER_AGENT is configured, use SEC staging; otherwise use the manual fundamentals import workflow.
- Stop rule: Blocked features: fundamentals, DCF, peer, earnings, analyst estimates. Excluded features: portfolio. Unavailable sections are intentionally locked; missing data is not inferred.

## Proof Checklist
- Current mode proof: `Price/setup review only` because price/setup may be usable, but fundamentals or DCF inputs have not passed readiness.
- Next unlock proof: `make focus-fundamentals TICKER=APLD` before reviewing company valuation.
- Withhold until proven: Blocked features: fundamentals, DCF, peer, earnings, analyst estimates. Excluded features: portfolio. Unavailable sections are intentionally locked; missing data is not inferred.
- Manual check: Import trusted fundamentals for APLD. If SEC_USER_AGENT is configured, use SEC staging; otherwise use the manual fundamentals import workflow.

## Best Review Path
- First read: Start with DCF Input Triage and Data Unlock Summary. Company valuation stays blocked until trusted fundamentals and DCF inputs are ready.
- Then check: What We Can Analyze Now, Valuation Boundary Checklist, and Source Readiness Check.
- Optional context: Optional earnings and analyst-estimate context remains locked unless trusted local rows exist.
- Copy-only proof step: `make focus-fundamentals TICKER=APLD`

## How To Read This Report
- Read top-down: readiness state first, supported analysis second, blocked or excluded analysis third.
- Current use: Price/setup review only until trusted fundamentals, DCF, and peer inputs are ready.
- Method source: project code implements readiness gates and report wording; libraries and adapters support data handling/UI, but shipped analysis comes from project code and local data.
- Boundary: this is research context only. It does not provide allocation instructions, account actions, or direct recommendations.

## Executive Summary
- Bottom line: APLD is in `Price/setup review only` mode. Use price and setup context only. Company valuation stays blocked until trusted fundamentals and DCF inputs exist.
- Use now: Use available price or setup context only. Company-level valuation stays blocked until trusted fundamentals, free cash flow or margin inputs, share count, and DCF fields are ready.
- Do not infer: Blocked features: fundamentals, DCF, peer, earnings, analyst estimates. Excluded features: portfolio. Unavailable sections are intentionally locked; missing data is not inferred.
- Next step: Import trusted fundamentals for APLD. If SEC_USER_AGENT is configured, use SEC staging; otherwise use the manual fundamentals import workflow.

## Analysis Mode Guide
- `DCF-ready review` (other): Fullest company review: price, fundamentals, DCF, and source-backed peer context are ready.
- `Standalone DCF review` (other): Company DCF can be reviewed, but peer-relative valuation remains blocked.
- `Price/setup review only` (current): Use trend/setup context only; company valuation waits for trusted fundamentals and DCF inputs.
- `Monitor-only context` (other): Use ETF/index/fund market or risk context; operating-company DCF is excluded, not failed.
- `Data needed before analysis` (other): Reference state for tickers with no trusted local inputs yet; add the first missing input before drawing conclusions.

## One-Minute Status
APLD overall readiness: partial; review ready inputs first and treat locked inputs as data unlock work. Decision: Blocked by Data - Missing Fundamentals. DCF: blocked. Primary blocker: fundamentals. Peer workflow: waits for trusted price, fundamentals, and DCF inputs first. Optional earnings or analyst-estimate context is unavailable until trusted local CSV rows exist. Next: Import trusted fundamentals for APLD. If SEC_USER_AGENT is configured, use SEC staging; otherwise use the manual fundamentals import workflow.

## What We Can Analyze Now
- Ready inputs: price, momentum, market direction, liquidity, correlation.
- Supported now: Use available price or setup context only. Company-level valuation stays blocked until trusted fundamentals, free cash flow or margin inputs, share count, and DCF fields are ready.
- Still locked or excluded: Blocked features: fundamentals, DCF, peer, earnings, analyst estimates. Excluded features: portfolio. Unavailable sections are intentionally locked; missing data is not inferred.

## Next Layer To Unlock
- Current supported layer: Price/setup review only; company valuation stays locked until fundamentals and DCF inputs pass readiness.
- Next trusted input: Trusted fundamentals, free-cash-flow or margin inputs, share count, and DCF fields.
- Proof command: `make focus-fundamentals TICKER=APLD` before treating the next layer as unlocked.
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
- Analysis recipe: prices unlock setup/trend review; fundamentals unlock field review and DCF input quality; DCF unlocks scenario math; source-backed peers unlock peer context; optional earnings and estimates add timing or consensus context only.
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
- Ticker: APLD
- Asset type: company
- Current role: Core Compounder. Test whether trend, fundamentals, and DCF support the long-duration thesis; current state is not prioritized.

## Decision
- Bucket: Blocked by Data
- Subtype: Blocked by Data - Missing Fundamentals
- Boundary: Data unlock state: fundamentals blocks evaluation, so conclusions stay withheld.
- Primary blocker: fundamentals
- Main reason: Company research is blocked by missing DCF, fundamentals data.
- Next action: Import trusted fundamentals for APLD. If SEC_USER_AGENT is configured, use SEC staging; otherwise use the manual fundamentals import workflow.

## Purpose Evaluation
Research-only purpose brief. It separates what local data supports from what remains locked or excluded.
- Thesis: Core Compounder. Test whether trend, fundamentals, and DCF support the long-duration thesis; current state is not prioritized.
- Alignment: Purpose alignment appears consistent with current setup `No Setup` for Core Compounder, subject to the missing-data limits below.
- Research review summary: Purpose alignment appears consistent with current setup `No Setup` for Core Compounder, subject to the missing-data limits below; Blocked by Data - Missing Fundamentals. Next blocker: fundamentals. Withheld: fundamental quality and operating-company valuation, DCF interpretation, peer-relative valuation or opportunity-cost comparison, earnings timing or surprise context, analyst estimate trend context, compounder thesis confirmation. Review the readiness sections below before drawing conclusions.
- Setup: Compounder setup: No Setup; final state: Not Prioritized. Track trend quality alongside fundamentals and DCF before treating the long-duration thesis as well supported. Not-prioritized names are left unranked.
- Valuation boundary: Valuation conclusion is blocked until trusted DCF/fundamental inputs are complete.

## Supported Analysis
- Supported analysis: price history, setup and momentum context, market/theme context, liquidity context, correlation/risk context.

## Locked Analysis
- Currently withheld: fundamental quality and operating-company valuation, DCF interpretation, peer-relative valuation or opportunity-cost comparison, earnings timing or surprise context, analyst estimate trend context, compounder thesis confirmation.

## Setup / Momentum
- Compounder setup: No Setup; final state: Not Prioritized. Track trend quality alongside fundamentals and DCF before treating the long-duration thesis as well supported. Not-prioritized names are left unranked.
- 1M performance: -10.4%
- 3M performance: 57.6%
- 1Y performance: 199.0%
- ATR / volatility: Not available; missing values stay visible instead of guessed.

## Risk Notes
- Risk watchpoint: peer-relative context is incomplete, so valuation comparison and opportunity cost remain uncertain.
- Invalidation condition: Invalidate the compounder thesis review if trend conflict persists and updated fundamentals/DCF no longer support the stated purpose.

## Next Research Step
- Next research question: Which trusted fundamentals or DCF fields are needed to confirm whether the compounder thesis remains supported?
- Review priority: Unlock priority: price context exists, but fundamentals blocks deeper analysis.
- Data-confidence explanation: Data confidence is low: primary blocker is fundamentals; blocked features are fundamentals, DCF, peer, earnings, analyst estimates.

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
- Blocked features: fundamentals, DCF, peer, earnings, analyst estimates
- Excluded features: portfolio

## Price Coverage
- Price rows: 616
- First date: 2023-12-20
- Last date: 2026-06-05
- Missing price reason: none

## Valuation Readiness
- DCF status: blocked.
- DCF missing inputs: free cash flow, shares outstanding, revenue, FCF margin.
- Why DCF is blocked: missing free cash flow, shares outstanding, revenue, FCF margin.
- DCF assumptions: withheld until price, fundamentals, free cash flow or FCF margin, and share-count inputs are ready.
- Sensitivity table: unavailable until the base DCF can be calculated.
- Relative valuation: withheld until trusted fundamentals and DCF readiness pass; available peer context is held back until the company DCF gate is ready (peer status=insufficient data; peer count=0).
- Valuation conclusion is shown only when trusted DCF and peer inputs support it; missing valuation inputs are not inferred.

## DCF Calculation Path
- State: blocked; the product withholds DCF math until trusted company inputs pass readiness checks.
- Required local inputs: trusted price, revenue, free cash flow or FCF margin, shares outstanding, and cash/debt or net-debt context.
- Missing now: free cash flow, shares outstanding, revenue, FCF margin.
- Formula path: withheld before base FCF, projected FCF, terminal value, equity value, or fair value/share are calculated.
- Sensitivity: unavailable until the base DCF can be calculated from trusted inputs.

## DCF Input Triage
- DCF input triage: blocked inputs are repair steps, not negative company signals.
- Calculation dependency: trusted price and share count anchor per-share output; revenue plus free cash flow or FCF margin builds base FCF; cash/debt adjusts enterprise value to equity value.
- Missing free cash flow: drives base FCF for projected cash flows; without it the DCF cannot calculate operating cash generation. Unlock path: add trusted free-cash-flow rows through SEC staging or `data/imports/fundamentals.csv`, then validate and preview.
- Missing shares outstanding: converts equity value into fair value per share; missing share count blocks per-share DCF output. Unlock path: add trusted shares outstanding in the fundamentals import, then run `make imports-validate` and `make dcf-readiness`.
- Missing revenue: sets the operating scale used for forecast assumptions when direct free cash flow is not enough by itself. Unlock path: use `make focus-fundamentals TICKER=APLD`, then `make sec-stage TICKERS=APLD` or trusted manual fundamentals import.
- Missing FCF margin: lets the model estimate free cash flow from revenue when direct free cash flow is unavailable. Unlock path: add a trusted FCF margin or direct free-cash-flow field before rerunning DCF readiness.
- Safe sequence: `make focus-fundamentals TICKER=APLD` -> stage SEC or trusted manual fundamentals rows -> `make imports-validate` -> `make imports-preview` -> `make imports-apply` -> `make dcf-readiness`.

## Valuation Boundary Checklist
- DCF boundary: blocked until trusted price, fundamentals, cash-flow or margin, share-count, and DCF fields pass readiness.
- Peer-relative boundary: withheld until trusted fundamentals and DCF readiness pass first.
- Optional-context boundary: locked until trusted local earnings and analyst-estimate rows pass import validation.
- Conclusion boundary: missing or excluded inputs do not become intrinsic value, peer-relative value, undervalued, or overvalued conclusions.

## Peer Workflow
- What this means: peer valuation waits behind price, fundamentals, and standalone DCF readiness.
- What can be reviewed now: only the ready local inputs listed above; peer rows should not create valuation context yet.
- What is still locked: peer trend and peer valuation remain withheld until core company inputs are ready.
- Trusted input path: resolve fundamentals / DCF first, then use `make focus-peers TICKER=APLD` if peer context is still needed.
- Peer ladder: paused behind core company readiness.
- Mapping evidence: mapping status=missing mapping; peer count=0. Do not use peer rows to bypass missing price, fundamentals, or DCF inputs.
- Trend evidence: withheld until core company readiness passes and mapped peer price history is useful.
- Valuation evidence: withheld until standalone DCF plus source-backed peer mappings and peer valuation inputs pass readiness.
- Next safe command: `make focus-peers TICKER=APLD` only after the core DCF blockers are resolved.
- Peer blocker type: blocked until fundamentals / DCF
- Mapping status: waiting for price, fundamentals, and DCF
- Peer count: 0
- Trend comparison ready: not ready
- Valuation comparison ready: not ready
- DCF peer comparison ready: not ready
- Sample peers: none configured
- Next peer action: Peer-relative valuation should wait until trusted price, fundamentals, and DCF inputs are ready.

## Optional Context Workflow
- Optional context ladder: earnings and analyst estimates add timing, consensus, and revision context only; they never create a valuation conclusion by themselves.
- Earnings evidence: locked; missing trusted local CSV input is an intentional state, not broken analysis. Use schema-only templates first; templates are not data.
- Analyst-estimate evidence: locked; missing trusted local CSV input is an intentional state, not hidden consensus analysis.
- Earnings path: `make templates` -> place trusted rows in `data/staged/earnings/` -> `make import-earnings` -> `make imports-validate` -> `make imports-preview` -> `make imports-apply`.
- Analyst-estimates path: `make templates` -> place trusted rows in `data/staged/analyst_estimates/` -> `make import-analyst-estimates` -> `make imports-validate` -> `make imports-preview` -> `make imports-apply`.
- Rejected-row checks: review `data/rejected/earnings_import_rejected.csv` and `data/rejected/analyst_estimates_import_rejected.csv` before trusting optional context.
- Rebuild proof: run `make optional-context-readiness`, then `make stock-report-md TICKER=APLD` to confirm optional sections changed from locked to available.
- No-conclusion boundary: missing earnings or estimates must not appear as event timing, consensus, revision, upside, downside, undervalued, or overvalued analysis.

## Missing Data
- EPS is unavailable from the current local fundamentals dataset.
- Free cash flow is unavailable from the current local fundamentals dataset.
- No trusted analyst-estimate CSV has been added yet.
- No trusted earnings CSV has been added yet.
- Revenue is unavailable from the current local fundamentals dataset.
- Valuation input still missing: EBITDA.
- Valuation input still missing: FCF margin.
- Valuation input still missing: cash.
- Valuation input still missing: debt.
- Valuation input still missing: eps.
- Valuation input still missing: free cash flow.
- Valuation input still missing: market cap, price, and share count.
- Valuation input still missing: revenue.
- Analyst estimates: no trusted local row for this ticker; optional context stays locked.
- Earnings: no trusted local row for this ticker; optional context stays locked.
- fundamentals has no local row for this ticker.

## Source Readiness
- local:prices.csv: research-grade / local; source readiness: daily CSV through 2026-06-05; Saved local research data.
- local:fundamentals.csv: research-grade / local; source readiness: not available in local CSVs; No local fundamentals row was found for this ticker.
- local:earnings.csv: research-grade / local; source readiness: not available in local CSVs; Earnings fields stay locked until trusted rows are imported.
- local:analyst_estimates.csv: research-grade / local; source readiness: not available in local CSVs; Analyst-estimate fields stay locked until trusted rows are imported.

## Data Unlock Summary
- Data Health lane: Fundamentals / DCF Unlock. Suggested local check: `make focus-fundamentals TICKER=APLD`. Confirm with `make dcf-readiness && make readiness` before treating the lane as unlocked.
- Price unlock: Price history is usable now (616 local row(s)); keep it fresh before relying on setup or risk context.
- Fundamentals / DCF unlock: Fundamentals / DCF are blocked: missing free cash flow, shares outstanding, revenue, FCF margin. Inspect `make focus-fundamentals TICKER=APLD`, then use `make sec-stage TICKERS=APLD` when SEC_USER_AGENT is configured or prepare trusted manual fundamentals rows before `make imports-validate`, `make imports-preview`, `make imports-apply`, and `make dcf-readiness`.
- Peer unlock: Peer valuation should wait until trusted price, fundamentals, and DCF inputs are ready.
- Optional context unlock: Earnings and analyst estimates remain optional and locked until trusted local rows are imported with `make templates`, `make imports-validate`, `make imports-preview`, and `make imports-apply`.
- Import paths, rejected-row files, and credential state are listed in the Source Readiness Check below.

## Copyable Unlock Commands
- Copy-only: these are local research commands to copy when you choose; the report does not run imports or refreshes and does not connect to external accounts.
- Inspect this ticker: `make stock-report-md TICKER=APLD`.
- One-company proof packet: `make trusted-data-pilot-packet TICKER=APLD`.
- Price source readiness: `make focus-price TICKER=APLD`.
- Fundamentals / DCF: `make focus-fundamentals TICKER=APLD`.
- SEC/manual import checklist: `make sec-stage-queue TICKERS=APLD TOP_N=10`.
- Fundamentals import safety: `make imports-validate && make imports-preview && make imports-apply`.
- DCF rebuild proof: `make dcf-readiness && make readiness` before reading standalone DCF output.
- Peer mapping: `make focus-peers TICKER=APLD`.
- Peer mapping checklist: `make peer-mapping-queue TICKERS=APLD TOP_N=10`.
- Peer import safety: `make templates && make imports-validate && make imports-preview && make imports-apply`.
- Peer rebuild proof: `make readiness && make peer-mapping-queue TICKERS=APLD TOP_N=10` before reading peer-relative valuation.
- Optional context checklist: `make optional-context-worklist TICKERS=APLD TOP_N=10`.
- Optional templates: `make templates`.
- Earnings import: `make import-earnings`.
- Analyst-estimates import: `make import-analyst-estimates`.
- Optional import safety: `make imports-validate && make imports-preview && make imports-apply`.
- Optional-context rebuild proof: `make optional-context-readiness && make readiness` before treating earnings or estimates as available context.

## Source Readiness Check
- Prices: ready; local source `data/prices.csv`; coverage 2023-12-20 to 2026-06-05; rows=616; import file path `data/staged/prices/` or `data/imports/prices.csv`; rejected rows `data/rejected/price_import_rejected.csv`.
- Fundamentals / DCF: blocked; local source `data/fundamentals.csv`; reason missing free cash flow, shares outstanding, revenue, FCF margin; SEC_USER_AGENT present; import file path `data/staged/fundamentals/` or `data/imports/fundamentals.csv`; rejected rows `data/rejected/fundamentals_import_rejected.csv`.
- Peers: blocked until fundamentals / DCF; local source `data/peers.csv`; import file path `data/imports/peers.csv`; next peer action Peer-relative valuation should wait until trusted price, fundamentals, and DCF inputs are ready.
- Earnings: not ready; trusted local CSV only; import file path `data/staged/earnings/`; command `make import-earnings`; rejected rows `data/rejected/earnings_import_rejected.csv`.
- Analyst estimates: not ready; trusted local CSV only; import file path `data/staged/analyst_estimates/`; command `make import-analyst-estimates`; rejected rows `data/rejected/analyst_estimates_import_rejected.csv`.
- Credentials: SEC_USER_AGENT present; STOOQ_API_KEY missing; missing remote credentials should not break local CSV reports or preview-first local import workflows.
- Report command: `make stock-report-md TICKER=APLD`. Research-only Markdown output; copyable command only.
