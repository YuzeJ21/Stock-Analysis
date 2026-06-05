# Research Methodology

This project is a local stock research command center. It does not ask a model to invent an opinion. It follows a deterministic workflow:

1. Check whether the local data is ready.
2. Run only the analysis that the ready data can support.
3. Withhold or block analysis that needs missing inputs.
4. Explain the assumptions, missing fields, and next research step.

The methodology is intentionally conservative. Missing prices, fundamentals, peers, earnings, or analyst estimates are treated as quality-control blockers, not as values to infer.

## What Is Data Versus Product Logic

The product separates source inputs from analysis logic so the report is not a black box.

| Layer | Where it comes from | What the product does |
| --- | --- | --- |
| Price rows | Local CSVs, optionally refreshed through a labeled research-grade provider adapter. | Validates enough usable rows exist, then calculates trend, momentum, liquidity, volatility context, and setup labels. |
| Fundamentals rows | Trusted local imports such as SEC/manual CSV workflows. | Checks required fields, derives ratios where supported, and decides whether DCF and quality review can run. |
| Peer mappings and peer metrics | Trusted local peer mapping and peer input CSVs. | Separates peer trend context from peer valuation, and blocks valuation when peer inputs are incomplete. |
| Earnings and analyst estimates | Trusted optional local imports. | Displays optional context only when rows pass schema and freshness checks. |
| Report wording | Project code under `src/`. | Converts readiness, calculations, source state, and blockers into plain-language sections without inventing conclusions. |

Third-party or optional provider data can supply rows, but it does not decide the research conclusion. The project code decides whether each local row is usable, which calculation is allowed, and which section must stay blocked or excluded.

## 1. How This Compares To Standard Research Workflows

The product follows a familiar equity-research sequence, but keeps each step visible and gated:

| Standard research step | What this product implements | What stays blocked |
| --- | --- | --- |
| Data collection | Local CSV and optional provider-assisted rows for prices, fundamentals, peers, earnings, and estimates. | Any field that is missing, stale, malformed, or not source-backed. |
| Quality control | Readiness gates for each analysis feature before calculations run. | Valuation, peer comparison, or optional context when required inputs are absent. |
| Intrinsic valuation | A free-cash-flow DCF with visible scenario assumptions, WACC, terminal growth, and sensitivity. | Price targets or valuation claims when DCF inputs are incomplete. |
| Relative valuation | Source-backed peer workflow and peer-input checks. | Peer valuation from guessed relationships, sector fallback, or incomplete peer metrics. |
| Research note | Single-stock report sections generated from readiness, calculations, blockers, and source/freshness state. | Unsupported recommendations, allocation instructions, or hidden analyst-opinion imports. |

Compared with a professional research terminal or analyst model, this project is intentionally narrower. It does not try to own every data feed or produce a final investment call. Its value is that the workflow is inspectable: the same project code checks data readiness, runs DCF math only when inputs exist, withholds unsupported peer valuation, and explains the next trusted input needed.

## 2. Readiness Gate

The readiness gate runs before valuation or report conclusions.

| Area | Minimum logic | Output behavior |
| --- | --- | --- |
| Price | Enough valid local price rows with positive close values. | Unlocks setup and trend context. |
| Momentum | More local price history than the basic price gate. | Unlocks momentum and market-direction context. |
| Liquidity / correlation | Longer local price history. | Unlocks risk-context review. |
| Fundamentals | Trusted local row with required numeric fields and source. | Unlocks company fundamentals review. |
| DCF | Company ticker plus price, revenue, free cash flow or FCF margin, and shares outstanding. | Unlocks standalone DCF review. |
| Peers | Source-backed peer mappings plus peer price/fundamental inputs. | Unlocks peer trend or peer valuation context depending on input depth. |
| Earnings / estimates | Trusted local optional-context rows. | Unlocks optional context only. |

The app labels each feature as `ready`, `partial`, `blocked`, or `excluded`. ETFs, index proxies, and funds are excluded from operating-company DCF because that valuation method does not fit their monitor role.

## 3. Fundamental Analysis

Fundamental analysis uses local fields such as revenue, revenue growth, free cash flow, FCF margin, operating margin, profit margin, EPS, cash, debt, shares outstanding, and source metadata.

The product does not claim a company is attractive or unattractive when core fields are missing. Instead it explains which fields are available, which fields are missing, and whether those fields are enough for DCF or peer-relative review.

Fundamental review is therefore a validation-and-interpretation layer, not a third-party analyst summary. A full company row can support revenue scale, growth, margin, free-cash-flow conversion, leverage/cash context, and DCF input quality. A partial row supports only the fields that are actually present.

The fundamental-analysis contract is:

| Question | Product logic | What remains withheld |
| --- | --- | --- |
| Is there a trusted company row? | Checks the local fundamentals row, source metadata, and required numeric fields. | Company-quality language when the row is missing or source status is unclear. |
| Is the business scale visible? | Reads revenue and revenue growth when present. | Growth interpretation when revenue history is absent or malformed. |
| Is cash generation visible? | Reads free cash flow directly, or uses revenue and FCF margin when both are trusted. | Free-cash-flow conversion claims when both FCF and FCF margin are missing. |
| Is balance-sheet context visible? | Reads cash, debt, or net-debt fields when present. | Leverage or cash-cushion language when balance-sheet fields are unavailable. |
| Can DCF run? | Requires price, revenue, free cash flow or FCF margin, shares outstanding, and valid assumptions. | Fair value/share, sensitivity, and valuation interpretation until required fields pass readiness. |
| Can peer valuation run? | Requires standalone company readiness plus source-backed peer mappings and peer valuation inputs. | Peer-relative valuation from guessed peers, sector fallback, or incomplete peer metrics. |

This means a fundamentals-ready row is not automatically a conclusion. It is permission to review the fields that are present. A DCF-ready row is permission to review scenario math. A peer-ready row is permission to review source-backed relative context. The report and dashboard keep those permissions separate so a partial fundamentals row cannot become an unsupported valuation view.

## 4. Price, Momentum, And Risk Context

Price and momentum analysis uses local OHLCV rows when they are available. The product calculates moving averages, returns, relative strength, volume ratio, setup status, and volatility context from those rows.

For volatility context:

- If local `high`, `low`, and `close` fields are available, the product reports ATR from those fields.
- If high/low inputs are missing but close prices exist, it can use a close-to-close volatility proxy.
- Proxy volatility is labeled as an approximation in reports and dashboard cards.
- If neither path is supported, the volatility field stays unavailable rather than being guessed.

This volatility context can affect local risk penalties and review notes, but it is not an allocation or trading instruction.

Theme and sector ETFs, such as a fintech proxy used for relative context, are optional benchmark inputs. If their OHLCV rows are missing, the app labels the theme/sector comparison as limited while leaving the stock's own readiness state governed by its own local data.

## 5. DCF Calculation

The DCF model is a transparent free-cash-flow workflow:

```text
Base FCF = free_cash_flow
or
Base FCF = revenue * FCF margin

Projected FCF[t] = Projected FCF[t-1] * (1 + scenario growth[t])

Discounted FCF[t] = Projected FCF[t] / (1 + WACC)^t

Terminal value = Terminal FCF / (WACC - terminal growth)

Enterprise value = Sum(discounted FCFs) + Discounted terminal value

Equity value = Enterprise value + cash - debt
or
Equity value = Enterprise value - net debt

Fair value per share = Equity value / shares outstanding
```

The default report uses bear, base, and bull scenarios. Scenario assumptions are visible in the report, including revenue growth, FCF margin, WACC, terminal growth, and forecast years. If assumptions are invalid or required inputs are missing, the DCF returns `insufficient_data`, meaning the valuation is intentionally blocked until trusted inputs exist.

DCF output is treated as scenario math, not a price target. The report should show the input path, assumptions, sensitivity, and confidence limits so a reader can challenge the model instead of trusting a hidden conclusion.

The report uses three DCF states:

- `ready`: the local company inputs are complete enough to review assumptions, scenario math, and sensitivity.
- `blocked`: one or more required company inputs are missing, so the report shows missing fields and withholds valuation interpretation.
- `excluded`: the ticker is an ETF, index proxy, or fund monitor context where operating-company DCF does not apply.

This distinction matters because a blocked DCF is not a negative company signal, and an excluded DCF is not a failed calculation. Both are product gates that prevent unsupported valuation language.

## 6. Peer And Relative Context

Peer analysis is separate from standalone DCF.

- Peer trend context can be available when mapped peers have enough local price history.
- Peer valuation context requires source-backed peer mappings and peer valuation inputs.
- Missing peer mappings or peer fundamentals block peer valuation.
- Sector or industry fallback context, if shown, must be labeled as fallback and not trusted manual peer data.

This prevents the report from pretending that peer valuation exists when only partial peer data is available.

## 7. Valuation Status

Valuation status is a gate, not a recommendation.

| Status | Meaning |
| --- | --- |
| Ready | Trusted local inputs are enough to show the relevant valuation view. |
| Partial | Some valuation context is available, but the full stack is incomplete. |
| Blocked | Required inputs are missing, so the valuation conclusion is withheld. |
| Excluded | The method does not apply, such as operating-company DCF for ETF/index/fund monitor context. |

The product does not infer valuation conclusions for blocked rows.

Confidence follows the same principle: complete trusted inputs can raise confidence for the supported section, while missing fundamentals, stale prices, missing peers, or unavailable optional context reduce confidence or keep a section locked. Confidence is never used to override a blocker.

## 8. Scores And Ranking Context

The product uses setup scores, watchlist scores, confidence scores, and monthly
candidate scores only to sort local review queues and explain why a ticker
deserves attention next.

Scores are not:

- Price targets.
- Expected returns.
- Portfolio weights.
- Allocation instructions.
- Buy/sell/hold recommendations.

Blocked data reduces confidence or keeps a section unavailable. It must not be
converted into a weak score-based conclusion.

Some compatibility output files keep legacy names, including
`outputs/undervalued_candidates.csv`. Treat that file as valuation-readiness and
re-rating context. It is not an automatic undervalued-stock list, and rows with
missing trusted inputs must stay `not_ready`, meaning not enough trusted data exists for valuation, or blocked.

## 9. Report Explanation

Single-stock reports are assembled from the same gates and calculations:

- At A Glance status: mode, decision view, DCF state, peer context, optional context, method cue, and next local step.
- What can be analyzed now.
- Which mode applies: DCF-ready review, standalone DCF review, price/setup review only, monitor-only context, or data-unlock only.
- Which calculations ran and which assumptions were used.
- Which sections are blocked or excluded.
- What local input would unlock the next useful research step.
- Copyable Unlock Commands for local, capped, research-only follow-up workflows.
- Which sources were used and how fresh they are.

The report should be read top-down: At A Glance first, supported analysis second, blocked or excluded analysis third, copyable local unlock commands next, then source/freshness and valuation detail. The commands are displayed for the operator to copy manually; the report does not execute imports, refreshes, broker actions, or trades.

When a company ticker has the full trusted local input stack, the single-stock report can show:

- At A Glance mode, method cue, and next local step.
- Analysis Quality and Evaluation Function Check summaries.
- Price, momentum, liquidity, and market-context review.
- Fundamentals quality context from the imported local company row.
- Standalone DCF assumptions, bear/base/bull scenario values, and sensitivity context.
- Peer trend or peer valuation context only when source-backed peer inputs are ready.
- Earnings or analyst-estimate context only when trusted optional rows are ready.
- Copyable local commands for optional context, peer review, or freshness checks when more trusted data is needed.
- Source/freshness notes and the next research question.

When any part of that stack is missing, only the supported sections appear. The report keeps the blocked section visible and explains the exact local input needed next, plus the local command path for inspecting or unlocking that input.

## 10. Methodology Limits

This is not a full data-vendor terminal, analyst-estimate service, or execution workflow. The useful strength is transparency: the app shows exactly what local data supports and refuses to overstate missing analysis.

The current methodology is strongest for:

- Readiness and missing-data diagnosis.
- Single-stock report explanation.
- Price and setup context when local price history exists.
- DCF-ready company review when trusted fundamentals are present.
- ETF/index/fund monitor context where company DCF is excluded.

The current methodology remains limited when:

- Fundamentals are missing or stale.
- Peer mappings or peer valuation inputs are unavailable.
- Earnings and analyst-estimate rows have not been imported.
- A ticker has too little local price history.

## 11. Where This Lives In Code

The methodology is implemented in project code, not hidden in a model prompt.

| Method layer | Main local code |
| --- | --- |
| Readiness gates | `src/readiness_engine.py`, `src/dcf_readiness.py`, optional-context readiness helpers |
| DCF and relative valuation | `src/valuation.py`, `src/value_engine.py` |
| Research decision fields | `src/research_decisions.py` |
| Single-stock report wording | `src/stock_report.py` |
| Dashboard methodology and status views | `src/dashboard.py` |

The local CSV files provide inputs. The product code decides what can be analyzed, what must stay blocked, and what explanation appears.
