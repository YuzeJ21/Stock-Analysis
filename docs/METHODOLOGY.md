# Research Methodology

This project is a local stock research command center. It does not ask a model to invent an opinion. It follows a deterministic workflow:

1. Check whether the local data is ready.
2. Run only the analysis that the ready data can support.
3. Withhold or block analysis that needs missing inputs.
4. Explain the assumptions, missing fields, and next research step.

The methodology is intentionally conservative. Missing prices, fundamentals, peers, earnings, or analyst estimates are treated as quality-control blockers, not as values to infer.

## What Is Data Versus App Method

The product separates source inputs from analysis rules so the report is not a black box.

| Layer | Where it comes from | What the product does |
| --- | --- | --- |
| Price rows | Local CSVs, optionally refreshed through a labeled research-grade provider adapter. | Validates enough usable rows exist, then calculates trend, momentum, liquidity, volatility context, and setup labels. |
| Fundamentals rows | Trusted local imports such as SEC/manual CSV workflows. | Checks required fields, derives ratios where supported, and decides whether DCF and quality review can run. |
| Peer mappings and peer metrics | Trusted local peer mapping and peer input CSVs. | Separates peer trend context from peer valuation, and blocks valuation when peer inputs are incomplete. |
| Earnings and analyst estimates | Trusted optional local imports. | Displays optional context only when rows pass schema and source-readiness checks. |
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
| Research note | Single-stock report sections generated from readiness, calculations, blockers, and source readiness state. | Recommendations, allocation instructions, or hidden analyst-opinion imports. |

Compared with a professional research terminal or analyst model, this project is intentionally narrower. It does not try to own every data feed or produce a final investment call. Its value is that the workflow is inspectable: the same project code checks data readiness, runs DCF math only when inputs exist, withholds unsupported peer valuation, and explains the next trusted input needed.

## 2. Readiness Gate

The readiness gate runs before valuation or report conclusions.

| Area | Minimum rule | Output behavior |
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

| Question | Product rule | What remains withheld |
| --- | --- | --- |
| Is there a trusted company row? | Checks the local fundamentals row, source metadata, and required numeric fields. | Company-quality language when the row is missing or source status is unclear. |
| Is the business scale visible? | Reads revenue and revenue growth when present. | Growth interpretation when revenue history is absent or malformed. |
| Is cash generation visible? | Reads free cash flow directly, or uses revenue and FCF margin when both are trusted. | Free-cash-flow conversion claims when both FCF and FCF margin are missing. |
| Is balance-sheet context visible? | Reads cash, debt, or net-debt fields when present. | Leverage or cash-cushion language when balance-sheet fields are unavailable. |
| Can DCF run? | Requires price, revenue, free cash flow or FCF margin, shares outstanding, and valid assumptions. | Fair value/share, sensitivity, and valuation interpretation until required fields pass readiness. |
| Can peer valuation run? | Requires standalone company readiness plus source-backed peer mappings and peer valuation inputs. | Peer-relative valuation from guessed peers, sector fallback, or incomplete peer metrics. |

This means a fundamentals-ready row is not automatically a conclusion. It is permission to review the fields that are present. A DCF-ready row is permission to review scenario math. A peer-ready row is permission to review source-backed relative context. The report and dashboard keep those permissions separate so a partial fundamentals row cannot become a valuation view without ready inputs.

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

DCF output is treated as scenario math, not a price target. The report should show the input path, assumptions, sensitivity, and data-confidence limits so a reader can challenge the model instead of trusting a hidden conclusion.

### Conservative DCF Normalization

The product can normalize unusually high or unusually low assumptions before projecting cash flows. This is not a third-party opinion and it does not create new fundamentals. It is a transparent guardrail inside `src/valuation.py` to keep one extreme input from turning into a valuation story without ready inputs.

- Observed revenue growth above the conservative start-growth cap is capped before projection.
- Very negative observed revenue growth is floored before projection so the model does not compound an extreme one-period decline indefinitely.
- Projected early-year FCF growth can be capped even after the revenue-growth path is built.
- Observed FCF margin above the conservative margin cap is capped before projection.
- Normalized long-term growth is kept below WACC, and terminal growth must remain below WACC.

When one of these guardrails is used, the report shows a warning such as `Observed revenue growth ... was normalized before projection` or `Normalized growth target was reduced to keep it conservatively below WACC`. These warnings are part of the model audit trail. They mean the DCF ran with visible conservative limits, not that the product guessed missing data or changed source inputs.

The report uses three DCF states:

- `ready`: the local company inputs are complete enough to review assumptions, scenario math, and sensitivity.
- `blocked`: one or more required company inputs are missing, so the report shows missing fields and withholds valuation interpretation.
- `excluded`: the ticker is an ETF, index proxy, or fund monitor context where operating-company DCF does not apply.

This distinction matters because a blocked DCF is not a negative company signal, and an excluded DCF is not a failed calculation. Both are product gates that prevent valuation language without ready inputs.

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

Data confidence follows the same principle: complete trusted inputs can raise data confidence for the supported section, while missing fundamentals, stale prices, missing peers, or unavailable optional context reduce data confidence or keep a section locked. Data confidence is never used to override a blocker.

## 8. Confidence And Decision Scores

Data confidence is a data-quality and review-routing signal, not investment conviction.

The decision workflow first calculates a data-readiness score from feature state:

```text
Data readiness score =
  (ready features + 0.45 * partial features) / ready-or-partial-or-blocked features

Then blocked features reduce the score.
Excluded methods can reduce the score when nothing else is ready.
```

The public confidence labels follow the data-readiness score:

| Data-readiness score | Label |
| --- | --- |
| 0.80 or higher | high |
| 0.55 to below 0.80 | medium |
| 0.25 to below 0.55 | low |
| below 0.25 | blocked |

Data confidence is capped by decision bucket so a row with missing core inputs cannot look stronger than the data allows:

| Decision bucket | Data-confidence cap / behavior |
| --- | --- |
| Research Now | Uses data readiness plus local analysis score, capped below full certainty. |
| Monitor | Uses ready monitor inputs and is capped below Research Now. |
| Blocked by Data | Stays low even if some partial context exists. |
| Excluded | Can be clear about method exclusion without becoming a company valuation view. |

This means a DCF-ready company can have medium data confidence when optional context is missing, an ETF/index monitor row can have low or medium data confidence for monitoring while DCF stays excluded, and a price-blocked row stays blocked no matter how interesting the ticker might be.

## 9. Scores And Ranking Context

The product uses setup scores, watchlist scores, data-confidence scores, and monthly
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

## 10. Report Explanation

Single-stock reports are assembled from the same gates and calculations:

- At A Glance status: mode, decision view, DCF state, peer context, optional context, method cue, and next local step.
- Reader Guide: answers what can be analyzed now, what is still locked or excluded, what trusted input matters next, and the next copy-only command.
- Evaluation Snapshot: summarizes supported evaluation, valuation boundary, confidence cue, next proof step, and stop rule before the detailed sections.
- Best Review Path: tells the reader whether to review DCF and peers, unlock fundamentals, use monitor context, or start with price coverage.
- What can be analyzed now.
- Which mode applies: DCF-ready review, standalone DCF review, price/setup review only, monitor-only context, or data needed before analysis.
- Which calculations ran and which assumptions were used.
- Which sections are blocked or excluded.
- What local input would unlock the next useful research step.
- Copyable Unlock Commands for local, capped, research-only follow-up workflows.
- Which sources were used and how fresh they are.

The report should be read top-down: visitor scan cue first, At A Glance second, Reader Guide third, Evaluation Snapshot fourth, Proof Checklist fifth, Best Review Path sixth, supported analysis next, blocked or excluded analysis next, copyable local unlock commands next, then source readiness and valuation detail. The commands are displayed for the reader to copy manually; the report does not run imports or refreshes and does not connect to external accounts.

When a company ticker has the full trusted local input stack, the single-stock report can show:

- At A Glance mode, method cue, and next local step.
- Evaluation Snapshot for supported evaluation, valuation boundary, confidence cue, next proof, and stop rule.
- Best Review Path for the safest reading order and proof step.
- Analysis Quality and Evaluation Function Check summaries.
- Price, momentum, liquidity, and market-context review.
- Fundamentals quality context from the imported local company row.
- Standalone DCF assumptions, bear/base/bull scenario values, and sensitivity context.
- Peer trend or peer valuation context only when source-backed peer inputs are ready.
- Earnings or analyst-estimate context only when trusted optional rows are ready.
- Copyable local commands for optional context, peer review, or source-readiness checks when more trusted data is needed.
- Source-readiness notes and the next research question.

When any part of that stack is missing, only the supported sections appear. The report keeps the blocked section visible and explains the exact local input needed next, plus the local command path for inspecting or unlocking that input.

## 11. Data Unlock Ladder

The product uses the same unlock ladder in the dashboard, single-stock reports, and Data Health review lists:

| Step | What unlocks | What can be analyzed | What stays unavailable |
| --- | --- | --- | --- |
| 1. Prices | Trusted local price rows. | Price/setup review, trend context, basic risk context when enough history exists. | Fundamentals, DCF, peers, earnings, and estimates. |
| 2. Fundamentals / DCF inputs | Trusted company fundamentals with revenue, free cash flow or FCF margin, shares outstanding, and source metadata. | Fundamental field review and standalone DCF assumptions, scenarios, sensitivity, and fair value/share math. | Peer-relative valuation and optional earnings/estimate context. |
| 3. Source-backed peers | Trusted peer mappings plus peer valuation inputs. | Peer trend context first, then peer-relative valuation only when peer valuation inputs pass readiness. | Peer premium/discount or peer DCF comparison when peer inputs are incomplete. |
| 4. Optional context | Trusted earnings and analyst-estimate CSV rows. | Earnings timing context and analyst-estimate context. | Optional sections remain unavailable when those rows are missing. |

Each step is permission to review a specific analysis layer, not permission to invent the next layer. Price-ready does not mean fundamentals-ready. Fundamentals-ready does not mean DCF-ready unless all required DCF fields pass. DCF-ready does not mean peer-ready. Peer-ready does not mean earnings or analyst estimates are available.

The no-conclusion boundary is explicit: blocked rows must not be labeled undervalued, overvalued, DCF-ready, peer-ready, or optional-context-ready until the trusted input gate for that label passes. ETF, index proxy, and fund rows follow a separate monitor path where operating-company DCF and peer valuation are excluded, not failed.

The safe local sequence is:

1. Inspect the focused review list or report, such as `make focus-fundamentals TICKER=NVDA` or `make focus-peers TICKER=A`.
2. Stage trusted rows only in the matching local CSV path, such as `data/imports/fundamentals.csv`, `data/imports/peers.csv`, `data/staged/earnings/`, or `data/staged/analyst_estimates/`.
3. Run validation and preview before apply: `make imports-validate`, then `make imports-preview`, then `make imports-apply`.
4. Regenerate readiness, then read the report again before interpreting the newly unlocked section.

This ladder is why empty or partial outputs are useful: they show the first trustworthy unlock instead of hiding the gap behind a weak conclusion.

## 12. Methodology Limits

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

## 13. Where This Lives In Code

The methodology is implemented in project code, not hidden in a model prompt.

| Method layer | Main local code |
| --- | --- |
| Readiness gates | `src/readiness_engine.py`, `src/dcf_readiness.py`, optional-context readiness helpers |
| DCF and relative valuation | `src/valuation.py`, `src/value_engine.py` |
| Research decision fields | `src/research_decisions.py` |
| Single-stock report wording | `src/stock_report.py` |
| Dashboard methodology and status views | `src/dashboard.py` |

The local CSV files provide inputs. The product code decides what can be analyzed, what must stay blocked, and what explanation appears.
